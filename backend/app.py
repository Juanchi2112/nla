"""FastAPI backend for NLA monitoring.

Single producer flow: every /api/generate request — whether it provides a
custom `prompt` (live mode) or a `scenario_id` (cached demo) — is handled by
the SteeringEngine, which dispatches internally to either:

  - `_run_scenario`: replay a cached ScenarioArtifact (zero LLM calls at
    runtime; verdict was pre-computed offline by precompute_verdicts.py).
  - `_run_live`: call gpu.decode_full(), then ClaudeAgentJudge.evaluate_turn(),
    then optionally manual-confirm a steering re-decode.

There is one judge class in the system: ClaudeAgentJudge. It is instantiated
lazily — only when ORCHESTRATOR_GPU=decoder, because that's the mode where
live judging happens. Scenario mode does not need an Anthropic API key at
runtime.

Endpoints:
    POST /api/generate                         start a session (prompt XOR scenario_id)
    GET  /api/stream/{id}                      SSE stream of all events
    POST /api/cancel/{id}                      cooperative cancel
    POST /api/confirm-steer/{id}               accept a proposed steering (live mode only)
    POST /api/reject-steer/{id}                reject a proposed steering (live mode only)
    GET  /healthz                              liveness + config snapshot

Env:
    PORT                  set by Railway
    CORS_ORIGINS          "*" (default; comma-separated)
    ORCHESTRATOR_GPU      "scenario" | "decoder" | "hybrid" | "mock"
                          - scenario: cached only (no API key needed)
                          - decoder:  live only (needs GPU_URL + API key)
                          - hybrid:   BOTH cached + live (recommended for demo)
                          - mock:     dev/CI stub (no GPU, no judge)
    GPU_URL               required when mode in {decoder, hybrid}
    GPU_TIMEOUT           "120.0" seconds
    MAX_NEW_TOKENS        "128"
    SCENARIO_DIR          "./demo_data" (used when mode in {scenario, hybrid})
    SCENARIO_MANIFEST     "manifest.yaml"
    JUDGE_MODEL           "claude-sonnet-4-6" (live judge model)
    JUDGE_PROMPT_VERSION  "v2-2026-05-10" (system prompt version)
    ANTHROPIC_API_KEY     required for live judge in {decoder, hybrid}
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .gpu import (
    DecoderEndpointClient,
    GPUClient,
    GPUClientError,
    GPUNotConfiguredError,
)
from .gpu.decoder_endpoint import URL_PLACEHOLDER
from .gpu.scenario import ArtifactLoader, ScenarioGPUClient
from .judge.claude_agent_judge import ClaudeAgentJudge
from .mock_generator import MockGPUClient
from .schemas import (
    CancelResponse,
    GenerateRequest,
    GenerateResponse,
    SteeringDecisionResponse,
)
from .sessions import SessionRegistry, SessionState
from .steering_engine import SteeringEngine

# Load .env from the repo root (or any parent of cwd) BEFORE reading any
# module-level os.environ values below. In Railway/Vercel/Docker there is no
# .env file and this is a no-op; platform-injected env vars take precedence
# (load_dotenv does not override existing keys by default).
load_dotenv()

log = logging.getLogger("backend")
logging.basicConfig(level=logging.INFO)


# ─── Config ───────────────────────────────────────────────────────────────

ORCH_GPU = os.environ.get("ORCHESTRATOR_GPU", "scenario").lower()
GPU_URL = os.environ.get("GPU_URL", URL_PLACEHOLDER)
GPU_TIMEOUT = float(os.environ.get("GPU_TIMEOUT", "120.0"))
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "128"))
SCENARIO_DIR = os.environ.get("SCENARIO_DIR", "./demo_data")
SCENARIO_MANIFEST = os.environ.get("SCENARIO_MANIFEST", "manifest.yaml")
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-6")
JUDGE_PROMPT_VERSION = os.environ.get("JUDGE_PROMPT_VERSION", "v2-2026-05-10")


_VALID_MODES = ("mock", "scenario", "decoder", "hybrid")


def _build_scenario_path() -> tuple[ScenarioGPUClient | None, ArtifactLoader | None]:
    """Try to enable the cached-scenario path. Returns (None, None) if unavailable.

    Active only for ORCHESTRATOR_GPU in {scenario, hybrid}. In hybrid mode an
    invalid manifest is non-fatal — we log a warning and continue with live
    only. In scenario mode an invalid manifest fails the boot (the user
    explicitly asked for scenarios).
    """
    if ORCH_GPU not in ("scenario", "hybrid"):
        return None, None
    manifest_path = Path(SCENARIO_DIR) / SCENARIO_MANIFEST
    try:
        loader = ArtifactLoader(manifest_path)
    except GPUClientError as e:
        if ORCH_GPU == "scenario":
            raise
        log.warning("hybrid: scenario path unavailable: %s", e)
        return None, None
    return ScenarioGPUClient(loader), loader


def _build_live_path() -> tuple[GPUClient | None, ClaudeAgentJudge | None]:
    """Try to enable the live GPU + judge path. Returns (None, None) if unavailable.

    - mock mode: MockGPUClient with a None judge (mock is dev only).
    - decoder/hybrid mode: DecoderEndpointClient + (optional) ClaudeAgentJudge.
      In hybrid mode a missing GPU_URL is non-fatal; in decoder mode it raises
      GPUNotConfiguredError so the explicit live-only request fails fast.
    """
    if ORCH_GPU == "mock":
        return MockGPUClient(), None
    if ORCH_GPU not in ("decoder", "hybrid"):
        return None, None
    try:
        gpu = DecoderEndpointClient(GPU_URL, timeout=GPU_TIMEOUT)
    except GPUNotConfiguredError as e:
        if ORCH_GPU == "decoder":
            raise
        log.warning("hybrid: live path unavailable (GPU): %s", e)
        return None, None
    return gpu, _build_live_judge()


def _build_live_judge() -> ClaudeAgentJudge | None:
    """Instantiate ClaudeAgentJudge for the live path. Returns None if
    unavailable (no API key, missing system prompt). Used only when
    _build_live_path() succeeds in setting up the GPU."""
    if ORCH_GPU not in ("decoder", "hybrid"):
        return None

    sys_prompt_path = Path(SCENARIO_DIR) / "_system_prompts" / f"{JUDGE_PROMPT_VERSION}.txt"
    if not sys_prompt_path.exists():
        log.warning("Live judge unavailable: system prompt %s missing", sys_prompt_path)
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.warning("Live judge unavailable: ANTHROPIC_API_KEY not set")
        return None
    try:
        return ClaudeAgentJudge(
            system_prompt=sys_prompt_path.read_text(),
            system_prompt_version=JUDGE_PROMPT_VERSION,
            model=JUDGE_MODEL,
        )
    except Exception as e:  # noqa: BLE001 — boot must not crash on judge issues
        log.warning("Live judge unavailable: %s", e)
        return None


# ─── Lifespan ─────────────────────────────────────────────────────────────


class AppState:
    sessions: SessionRegistry
    # Cached path (scenarios) — active when ORCH_GPU in {scenario, hybrid}.
    scenario_gpu: ScenarioGPUClient | None
    artifact_loader: ArtifactLoader | None
    # Live path — active when ORCH_GPU in {mock, decoder, hybrid}. Note that
    # mock has no judge (it's a dev-only stub).
    live_gpu: GPUClient | None
    judge: ClaudeAgentJudge | None
    steering: SteeringEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    if ORCH_GPU not in _VALID_MODES:
        raise ValueError(f"unknown ORCHESTRATOR_GPU={ORCH_GPU!r}; expected one of {_VALID_MODES}")

    state = AppState()
    state.sessions = SessionRegistry()
    state.scenario_gpu, state.artifact_loader = _build_scenario_path()
    state.live_gpu, state.judge = _build_live_path()

    # Hybrid degradation guard: at least one path must be active for the
    # backend to be useful. The non-hybrid modes already raise inside their
    # builders if their explicit dependency is missing.
    if state.scenario_gpu is None and state.live_gpu is None:
        raise RuntimeError(
            f"ORCHESTRATOR_GPU={ORCH_GPU!r} but neither scenario nor live "
            "path could be initialized. Check SCENARIO_DIR and GPU_URL."
        )

    state.steering = SteeringEngine(
        scenario_gpu=state.scenario_gpu,
        artifact_loader=state.artifact_loader,
        live_gpu=state.live_gpu,
        judge=state.judge,
    )

    log.info(
        "backend ready — mode=%s scenario_active=%s live_active=%s judge_active=%s",
        ORCH_GPU,
        state.scenario_gpu is not None,
        state.live_gpu is not None,
        state.judge is not None,
    )
    if state.artifact_loader is not None:
        log.info(
            "scenarios available (%d): %s",
            len(state.artifact_loader.scenarios),
            state.artifact_loader.scenarios,
        )

    app.state.orch = state
    try:
        yield
    finally:
        await state.sessions.shutdown()
        if state.scenario_gpu is not None:
            await state.scenario_gpu.aclose()
        if state.live_gpu is not None:
            await state.live_gpu.aclose()


app = FastAPI(
    title="NLA Backend",
    description=(
        "Orchestrator for NLA monitoring with a unified ClaudeAgentJudge. "
        "One protocol covers cached demo scenarios and live custom prompts; "
        "the SteeringEngine decides per request whether the source is "
        "cached or live."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.exception_handler(GPUNotConfiguredError)
async def _gpu_not_configured(request: Request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(GPUClientError)
async def _gpu_error(request: Request, exc):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


# ─── Helpers ──────────────────────────────────────────────────────────────


def _state(req: Request) -> AppState:
    return req.app.state.orch


def _sse_format(event: str, data: dict[str, Any]) -> bytes:
    """Format one SSE frame. Compact JSON keeps the wire small."""
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode()


async def _produce(state: AppState, session: SessionState) -> None:
    """Single entry into the SteeringEngine. Cooperative cancellation +
    terminal `done` event are owned by the engine itself."""
    await state.steering.run(session)


# ─── Routes ───────────────────────────────────────────────────────────────


@app.get("/healthz")
async def healthz(request: Request) -> dict[str, Any]:
    state = _state(request)
    payload: dict[str, Any] = {
        "status": "ok",
        "mode": ORCH_GPU,
        "scenario_active": state.scenario_gpu is not None,
        "live_active": state.live_gpu is not None,
        "judge_active": state.judge is not None,
        "judge_model": state.judge.model if state.judge is not None else None,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "max_new_tokens": MAX_NEW_TOKENS,
    }
    if state.scenario_gpu is not None and state.artifact_loader is not None:
        payload["available_scenarios"] = state.artifact_loader.scenarios
    if state.live_gpu is not None:
        payload["gpu_url_set"] = GPU_URL != URL_PLACEHOLDER
        payload["gpu_url"] = GPU_URL if GPU_URL != URL_PLACEHOLDER else None
    return payload


@app.post("/api/generate", response_model=GenerateResponse, status_code=202)
async def api_generate(req: GenerateRequest, request: Request) -> GenerateResponse:
    state = _state(request)
    if state.sessions.get(req.session_id) is not None:
        raise HTTPException(409, f"session_id={req.session_id!r} already exists")

    if req.scenario_id is not None:
        if state.scenario_gpu is None or state.artifact_loader is None:
            raise HTTPException(
                503,
                "Scenario path is not active. Set ORCHESTRATOR_GPU=scenario "
                "or hybrid with a valid SCENARIO_DIR to enable.",
            )
        if req.scenario_id not in state.artifact_loader.scenarios:
            raise HTTPException(
                404,
                f"scenario_id={req.scenario_id!r} not found. "
                f"Available: {state.artifact_loader.scenarios}",
            )
    elif state.live_gpu is None:
        raise HTTPException(
            503,
            "Live path is not active. Set ORCHESTRATOR_GPU=decoder or hybrid "
            "with a valid GPU_URL to enable.",
        )

    session = state.sessions.create(
        req.session_id,
        prompt=req.prompt or "",
        sniff_every_k=req.sniff_every_k,
        scenario_id=req.scenario_id,
        system_prompt=req.system_prompt,
    )
    session.task = asyncio.create_task(_produce(state, session))
    return GenerateResponse(session_id=req.session_id)


@app.get("/api/stream/{session_id}")
async def api_stream(session_id: str, request: Request) -> StreamingResponse:
    state = _state(request)
    session = state.sessions.get(session_id)
    if session is None:
        raise HTTPException(404, f"session_id={session_id!r} not found")

    async def event_source():
        while True:
            if await request.is_disconnected():
                break
            try:
                event_name, data = await asyncio.wait_for(session.queue.get(), timeout=15.0)
            except TimeoutError:
                yield b": keepalive\n\n"
                continue

            yield _sse_format(event_name, data)
            if event_name == "done":
                break

        state.sessions.delete(session_id)

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.post("/api/cancel/{session_id}", response_model=CancelResponse)
async def api_cancel(session_id: str, request: Request) -> CancelResponse:
    state = _state(request)
    ok = state.sessions.request_stop(session_id)
    if not ok:
        raise HTTPException(404, f"session_id={session_id!r} not found")
    return CancelResponse(session_id=session_id, stopped=True)


@app.post("/api/confirm-steer/{session_id}", response_model=SteeringDecisionResponse)
async def api_confirm_steer(session_id: str, request: Request) -> SteeringDecisionResponse:
    state = _state(request)
    session = state.sessions.get(session_id)
    if session is None:
        raise HTTPException(404, f"session_id={session_id!r} not found")
    if not state.sessions.request_confirm_steer(session_id):
        raise HTTPException(409, "session is not awaiting a steering decision")
    return SteeringDecisionResponse(session_id=session_id, decision="confirm")


@app.post("/api/reject-steer/{session_id}", response_model=SteeringDecisionResponse)
async def api_reject_steer(session_id: str, request: Request) -> SteeringDecisionResponse:
    state = _state(request)
    session = state.sessions.get(session_id)
    if session is None:
        raise HTTPException(404, f"session_id={session_id!r} not found")
    if not state.sessions.request_reject_steer(session_id):
        raise HTTPException(409, "session is not awaiting a steering decision")
    return SteeringDecisionResponse(session_id=session_id, decision="reject")
