"""FastAPI app exposing the NLA judges over HTTP.

Railway-deployable. No GPU required — the judges either run locally
(RegexJudge) or call the Anthropic API (ClaudeJudge).

Endpoints:
    POST /judge       — score one AV decoding against the rubrics.
    GET  /rubrics     — list rubrics (optionally filtered by mode).
    GET  /healthz     — liveness + config snapshot.

Env (all optional except ANTHROPIC_API_KEY when JUDGE_BACKEND=claude):
    JUDGE_BACKEND     "claude" (default) | "regex"
    JUDGE_MODEL       "claude-haiku-4-5" (default)
    FLAG_THRESHOLD    "2" (default)
    CORS_ORIGINS      "*" (default; comma-separated)
    ANTHROPIC_API_KEY required when JUDGE_BACKEND=claude
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from nla_judge import (
    FLAG_THRESHOLD,
    RUBRICS,
    ClaudeJudge,
    Judge,
    RegexJudge,
    rubrics_for_mode,
)

from .schemas import (
    HealthResponse,
    JudgeRequest,
    JudgeResponse,
    RubricInfo,
)

JUDGE_BACKEND = os.environ.get("JUDGE_BACKEND", "claude").lower()
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "claude-haiku-4-5")
THRESHOLD = int(os.environ.get("FLAG_THRESHOLD", str(FLAG_THRESHOLD)))


def _build_judge() -> Judge:
    if JUDGE_BACKEND == "regex":
        return RegexJudge()
    if JUDGE_BACKEND == "claude":
        # Fail fast on missing key — anthropic SDK validates lazily, so
        # without this the service would silently boot and 500 on first call.
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "JUDGE_BACKEND=claude but ANTHROPIC_API_KEY is not set. "
                "Set it in the Railway dashboard (or your shell) and restart."
            )
        return ClaudeJudge(model=JUDGE_MODEL, flag_threshold=THRESHOLD)
    raise ValueError(f"unknown JUDGE_BACKEND={JUDGE_BACKEND!r}; expected 'claude' or 'regex'")


_state: dict[str, Judge] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["judge"] = _build_judge()
    yield
    _state.clear()


app = FastAPI(
    title="NLA Judge Service",
    description=(
        "LLM-as-judge for NLA-decoded internal monologues. "
        "Scores text against compliance rubrics; the orchestrator decides "
        "what to do with the verdict."
    ),
    version="0.1.0",
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


# Translate Anthropic API failures into 502s with a structured body, so the
# orchestrator can distinguish "judge backend broken" from "service buggy".
try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None


if _anthropic is not None:

    @app.exception_handler(_anthropic.APIStatusError)
    async def _anthropic_status_handler(request: Request, exc):
        return JSONResponse(
            status_code=502,
            content={
                "detail": "judge backend error",
                "type": type(exc).__name__,
                "status": getattr(exc, "status_code", None),
                "message": str(exc)[:300],
            },
        )

    @app.exception_handler(_anthropic.APIConnectionError)
    async def _anthropic_conn_handler(request: Request, exc):
        return JSONResponse(
            status_code=502,
            content={
                "detail": "judge backend unreachable",
                "type": type(exc).__name__,
                "message": str(exc)[:300],
            },
        )


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    backend_label = JUDGE_BACKEND
    model_label = JUDGE_MODEL if JUDGE_BACKEND == "claude" else "n/a"
    return HealthResponse(
        status="ok" if "judge" in _state else "starting",
        backend=backend_label,
        judge_model=model_label,
        flag_threshold=THRESHOLD,
        rubrics_by_mode={
            "A": [r.name for r in rubrics_for_mode("A")],
            "B": [r.name for r in rubrics_for_mode("B")],
        },
    )


@app.get("/rubrics", response_model=list[RubricInfo])
async def list_rubrics(
    mode: Literal["A", "B"] | None = Query(
        None,
        description="Filter to rubrics active in this mode. Omit for all.",
    ),
) -> list[RubricInfo]:
    items = rubrics_for_mode(mode) if mode else list(RUBRICS.values())
    return [
        RubricInfo(
            name=r.name,
            description=r.description,
            examples=list(r.examples),
            modes=list(r.modes),
        )
        for r in items
    ]


@app.post("/judge", response_model=JudgeResponse)
async def judge(req: JudgeRequest) -> JudgeResponse:
    judge_obj = _state.get("judge")
    if judge_obj is None:
        raise HTTPException(503, "judge not initialized")

    # ClaudeJudge does a blocking HTTPS call — keep the event loop free.
    result = await run_in_threadpool(judge_obj.evaluate, req.s, req.mode)

    return JudgeResponse(
        is_flagged=result.is_flagged,
        fired_rubric=result.fired_rubric,
        severity=result.severity,
        evidence=result.evidence,
        scores=result.raw_scores,
    )
