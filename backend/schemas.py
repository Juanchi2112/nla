"""Pydantic schemas for the orchestrator HTTP and SSE surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["A", "B"]


# ─── HTTP request/response ─────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    session_id: str = Field(
        ...,
        description="Client-supplied UUID. The same id is used to GET the stream.",
        min_length=1,
        max_length=128,
    )
    prompt: str = Field(..., min_length=1, max_length=4000)
    system_prompt: str | None = Field(
        None,
        description="System prompt for the model under test. Passed to the GPU as a chat-formatted message.",
    )
    model: str | None = Field(
        None,
        description="Hint for the GPU side. Ignored by the mock backend.",
    )
    sniff_every_k: int = Field(
        4,
        ge=1,
        le=64,
        description="Emit an nla_trace event every K tokens.",
    )


class GenerateResponse(BaseModel):
    session_id: str
    status: Literal["accepted"] = "accepted"


class SteerRequest(BaseModel):
    session_id: str
    rubric: str = Field(
        ...,
        description="Name of the rubric to steer toward (e.g. 'report_truth').",
    )
    intensity: float = Field(1.0, ge=0.0, le=4.0)


class SteerResponse(BaseModel):
    session_id: str
    active_rubric: str
    intensity: float


class CancelResponse(BaseModel):
    session_id: str
    stopped: bool


# ─── SSE event payloads ────────────────────────────────────────────────────
# These are what's serialized into the `data:` line of each SSE frame.


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    step: int
    text: str


class JudgeVerdict(BaseModel):
    """Mirrors the judge service's POST /judge response."""

    is_flagged: bool
    fired_rubric: str | None = None
    severity: int = 0
    evidence: str | None = None
    scores: dict[str, int] = Field(default_factory=dict)


class NLATraceEvent(BaseModel):
    type: Literal["nla_trace"] = "nla_trace"
    step: int
    mode: Mode
    monologue: str
    verdict: JudgeVerdict | None = Field(
        None,
        description="None when the judge service was unreachable.",
    )


class SteerAppliedEvent(BaseModel):
    """Emitted when an active steer is consumed by the generator."""

    type: Literal["steer_applied"] = "steer_applied"
    step: int
    rubric: str
    intensity: float


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    detail: str
    step: int | None = None


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    total_tokens: int
    reason: Literal["completed", "cancelled"] = "completed"


SSEPayload = TokenEvent | NLATraceEvent | SteerAppliedEvent | ErrorEvent | DoneEvent
