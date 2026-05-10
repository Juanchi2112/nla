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
    ORCHESTRATOR_GPU      "scenario" | "decoder" | "mock"
    GPU_URL               required when ORCHESTRATOR_GPU=decoder
    GPU_TIMEOUT           "120.0" seconds
    MAX_NEW_TOKENS        "128"
    SCENARIO_DIR          "./demo_data" (used when ORCHESTRATOR_GPU=scenario)
    SCENARIO_MANIFEST     "manifest.yaml"
    JUDGE_MODEL           "claude-sonnet-4-6" (live judge model when decoder mode)
    JUDGE_PROMPT_VERSION  "v2-2026-05-10" (system prompt version for live judge)
    ANTHROPIC_API_KEY     required for live judge (decoder mode)
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


def _build_gpu_client() -> tuple[GPUClient, ArtifactLoader | None]:
    """Build the GPU client and (when applicable) the cached-scenario loader."""
    if ORCH_GPU == "mock":
        return MockGPUClient(), None
    if ORCH_GPU == "decoder":
        # Raises GPUNotConfiguredError if GPU_URL is the placeholder.
        # The /generate SSE endpoint does not take skip_first; that
        # parameter belonged to the old /decode replay client.
        return DecoderEndpointClient(GPU_URL, timeout=GPU_TIMEOUT), None
    if ORCH_GPU == "scenario":
        manifest_path = Path(SCENARIO_DIR) / SCENARIO_MANIFEST
        loader = ArtifactLoader(manifest_path)
        return ScenarioGPUClient(loader), loader
    raise ValueError(
        f"unknown ORCHESTRATOR_GPU={ORCH_GPU!r}; expected 'mock', 'decoder', or 'scenario'"
    )


def _build_live_judge() -> ClaudeAgentJudge | None:
    """Instantiate ClaudeAgentJudge for live mode. Returns None if unavailable
    (no API key, missing system prompt). Live mode without a judge surfaces an
    error per request rather than failing the whole boot."""
    if ORCH_GPU != "decoder":
        return None  # scenario uses cached verdicts; mock is dev-only

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
    gpu: GPUClient
    sessions: SessionRegistry
    artifact_loader: ArtifactLoader | None
    judge: ClaudeAgentJudge | None
    steering: SteeringEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.sessions = SessionRegistry()
    state.gpu, state.artifact_loader = _build_gpu_client()
    state.judge = _build_live_judge()
    state.steering = SteeringEngine(
        gpu=state.gpu,
        artifact_loader=state.artifact_loader,
        judge=state.judge,
    )

    if state.artifact_loader is not None:
        log.info(
            "scenario mode — %d scenarios available: %s",
            len(state.artifact_loader.scenarios),
            state.artifact_loader.scenarios,
        )
    log.info(
        "backend ready — gpu=%s live_judge=%s",
        ORCH_GPU,
        "active" if state.judge is not None else "inactive",
    )

    app.state.orch = state
    try:
        yield
    finally:
        await state.sessions.shutdown()
        await state.gpu.aclose()


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
        "gpu_backend": ORCH_GPU,
        "gpu_url_set": GPU_URL != URL_PLACEHOLDER,
        "gpu_url": GPU_URL if GPU_URL != URL_PLACEHOLDER else None,
        "judge_active": state.judge is not None,
        "judge_model": state.judge.model if state.judge is not None else None,
        "judge_prompt_version": JUDGE_PROMPT_VERSION,
        "max_new_tokens": MAX_NEW_TOKENS,
    }
    if state.artifact_loader is not None:
        payload["available_scenarios"] = state.artifact_loader.scenarios
    return payload


@app.post("/api/generate", response_model=GenerateResponse, status_code=202)
async def api_generate(req: GenerateRequest, request: Request) -> GenerateResponse:
    state = _state(request)
    if state.sessions.get(req.session_id) is not None:
        raise HTTPException(409, f"session_id={req.session_id!r} already exists")

    if req.scenario_id is not None:
        if state.artifact_loader is None:
            raise HTTPException(
                503,
                "Backend is not in scenario mode. Set ORCHESTRATOR_GPU=scenario to enable.",
            )
        if req.scenario_id not in state.artifact_loader.scenarios:
            raise HTTPException(
                404,
                f"scenario_id={req.scenario_id!r} not found. "
                f"Available: {state.artifact_loader.scenarios}",
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
