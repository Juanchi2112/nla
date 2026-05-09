"""FastAPI orchestrator for NLA monitoring.

Wires the frontend to two upstream services:
    - Judge service (this repo, judge_service/)  — POST /judge per monologue.
    - GPU /decode endpoint (this repo, server.py) — TBD URL, opt-in via env.

Default backend is the local mock generator: produces canned tokens and
curated monologues at a realistic pace so the rest of the stack
(frontend, SSE, judge) can be exercised without a GPU.

Endpoints:
    POST /api/generate          — start a generation session
    GET  /api/stream/{id}       — SSE stream of token + nla_trace events
    POST /api/steer             — set the session's active rubric
    POST /api/cancel/{id}       — request stop
    GET  /healthz               — liveness + config snapshot

Env (all optional except as noted):
    PORT                  set by Railway
    CORS_ORIGINS          "*" (default; comma-separated)
    JUDGE_URL             "http://localhost:8000" (judge service base URL)
    JUDGE_TIMEOUT         "5.0" seconds
    ORCHESTRATOR_GPU      "mock" (default) | "decoder"
    GPU_URL               required when ORCHESTRATOR_GPU=decoder
    MAX_NEW_TOKENS        "128"
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

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
from .judge_client import JudgeClient
from .mock_generator import COMPLIANT_MONOLOGUES, MockGPUClient
from .schemas import (
    CancelResponse,
    DoneEvent,
    ErrorEvent,
    GenerateRequest,
    GenerateResponse,
    JudgeVerdict,
    NLATraceEvent,
    SteerAppliedEvent,
    SteerRequest,
    SteerResponse,
    TokenEvent,
)
from .sessions import SessionRegistry, SessionState

log = logging.getLogger("orchestrator")
logging.basicConfig(level=logging.INFO)


# ─── Config ───────────────────────────────────────────────────────────────

JUDGE_URL = os.environ.get("JUDGE_URL", "http://localhost:8000")
JUDGE_TIMEOUT = float(os.environ.get("JUDGE_TIMEOUT", "5.0"))
ORCH_GPU = os.environ.get("ORCHESTRATOR_GPU", "mock").lower()
GPU_URL = os.environ.get("GPU_URL", URL_PLACEHOLDER)
GPU_SKIP_FIRST = int(os.environ.get("GPU_SKIP_FIRST", "10"))
GPU_TIMEOUT = float(os.environ.get("GPU_TIMEOUT", "120.0"))
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "128"))


def _build_gpu_client() -> GPUClient:
    if ORCH_GPU == "mock":
        return MockGPUClient()
    if ORCH_GPU == "decoder":
        # Raises GPUNotConfiguredError if GPU_URL is the placeholder.
        return DecoderEndpointClient(
            GPU_URL,
            timeout=GPU_TIMEOUT,
            skip_first=GPU_SKIP_FIRST,
        )
    raise ValueError(
        f"unknown ORCHESTRATOR_GPU={ORCH_GPU!r}; expected 'mock' or 'decoder'"
    )


# ─── Lifespan ─────────────────────────────────────────────────────────────

class AppState:
    judge: JudgeClient
    gpu: GPUClient
    sessions: SessionRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    state = AppState()
    state.sessions = SessionRegistry()
    state.judge = JudgeClient(JUDGE_URL, timeout=JUDGE_TIMEOUT)
    await state.judge.start()
    state.gpu = _build_gpu_client()
    app.state.orch = state
    log.info(
        "orchestrator ready — gpu=%s judge=%s", ORCH_GPU, JUDGE_URL,
    )
    try:
        yield
    finally:
        await state.sessions.shutdown()
        await state.judge.stop()
        await state.gpu.aclose()


app = FastAPI(
    title="NLA Orchestrator",
    description=(
        "Coordinates the frontend, the judge service, and the GPU /decode "
        "endpoint. Streams tokens + judge verdicts over SSE."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")
           if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


# Translate GPU configuration errors into 503s with a clear body.
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


# ─── Generation task ──────────────────────────────────────────────────────

async def _produce(state: AppState, session: SessionState) -> None:
    """Async producer: drives the GPU client, talks to the judge,
    and pushes structured events into the session's queue.

    Cancellation is cooperative: we check session.stop_requested between
    items. A direct asyncio.CancelledError (from app shutdown) is also
    honoured — we emit a final cancelled `done` event, then return.
    """
    queue = session.queue
    judge = state.judge
    gpu = state.gpu
    K = session.sniff_every_k
    total = 0
    reason = "completed"

    try:
        async for item in gpu.stream(
            session.prompt,
            sniff_every_k=K,
            max_new_tokens=MAX_NEW_TOKENS,
        ):
            if session.stop_requested:
                reason = "cancelled"
                break

            # Emit any pending steer ack BEFORE the next token, so the
            # frontend can render the cause→effect ordering cleanly.
            if session.update_pending and session.active_rubric:
                await queue.put(("steer_applied", SteerAppliedEvent(
                    step=item.step,
                    rubric=session.active_rubric,
                    intensity=session.steer_intensity,
                ).model_dump()))
                session.update_pending = False

            await queue.put(("token", TokenEvent(
                step=item.step, text=item.token,
            ).model_dump()))
            total += 1

            if item.monologue is not None:
                # When the session is steered, override the canned monologue
                # with a compliant one so the demo shows the judge going
                # green. Real steering lands in a follow-up PR.
                monologue = item.monologue
                if session.active_rubric:
                    monologue = COMPLIANT_MONOLOGUES[
                        item.step % len(COMPLIANT_MONOLOGUES)
                    ]
                # First sniff = mode A (intent-at-prompt), the rest = mode B.
                mode = "A" if item.step < K else "B"
                verdict = await judge.judge(monologue, mode)
                await queue.put(("nla_trace", NLATraceEvent(
                    step=item.step,
                    mode=mode,
                    monologue=monologue,
                    verdict=verdict,
                ).model_dump()))

        session.total_tokens_emitted = total

    except asyncio.CancelledError:
        reason = "cancelled"
        raise
    except GPUClientError as e:
        await queue.put(("error", ErrorEvent(detail=str(e)).model_dump()))
        reason = "completed"   # we still close the stream cleanly
    except Exception as e:
        log.exception("generator crashed for session=%s", session.session_id)
        await queue.put(("error", ErrorEvent(detail=f"internal: {e}").model_dump()))
        reason = "completed"
    finally:
        await queue.put(("done", DoneEvent(
            total_tokens=total, reason=reason,
        ).model_dump()))


# ─── Routes ───────────────────────────────────────────────────────────────

@app.get("/healthz")
async def healthz(request: Request) -> dict[str, Any]:
    state = _state(request)
    judge_health = await state.judge.healthz()
    return {
        "status": "ok",
        "gpu_backend": ORCH_GPU,
        "gpu_url_set": GPU_URL != URL_PLACEHOLDER,
        "gpu_url": GPU_URL if GPU_URL != URL_PLACEHOLDER else None,
        "gpu_skip_first": GPU_SKIP_FIRST,
        "judge_url": JUDGE_URL,
        "judge_reachable": judge_health is not None,
        "max_new_tokens": MAX_NEW_TOKENS,
    }


@app.post("/api/generate", response_model=GenerateResponse, status_code=202)
async def api_generate(req: GenerateRequest, request: Request) -> GenerateResponse:
    state = _state(request)
    if state.sessions.get(req.session_id) is not None:
        raise HTTPException(409, f"session_id={req.session_id!r} already exists")
    session = state.sessions.create(
        req.session_id, req.prompt, req.sniff_every_k,
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
        # Drain the queue until we see a `done` event. Honor client
        # disconnects via Starlette's request.is_disconnected.
        while True:
            if await request.is_disconnected():
                break
            try:
                event_name, data = await asyncio.wait_for(
                    session.queue.get(), timeout=15.0,
                )
            except asyncio.TimeoutError:
                # Periodic comment frame keeps proxies + browsers from
                # closing the connection during long waits.
                yield b": keepalive\n\n"
                continue

            yield _sse_format(event_name, data)
            if event_name == "done":
                break

        # Drop session once the stream closes (caller is gone, or done).
        state.sessions.delete(session_id)

    return StreamingResponse(event_source(), media_type="text/event-stream")


@app.post("/api/steer", response_model=SteerResponse)
async def api_steer(req: SteerRequest, request: Request) -> SteerResponse:
    state = _state(request)
    ok = state.sessions.request_steer(req.session_id, req.rubric, req.intensity)
    if not ok:
        raise HTTPException(404, f"session_id={req.session_id!r} not found")
    return SteerResponse(
        session_id=req.session_id,
        active_rubric=req.rubric,
        intensity=req.intensity,
    )


@app.post("/api/cancel/{session_id}", response_model=CancelResponse)
async def api_cancel(session_id: str, request: Request) -> CancelResponse:
    state = _state(request)
    ok = state.sessions.request_stop(session_id)
    if not ok:
        raise HTTPException(404, f"session_id={session_id!r} not found")
    return CancelResponse(session_id=session_id, stopped=True)
