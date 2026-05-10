"""Pydantic schemas for the orchestrator HTTP and SSE surface."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Mode = Literal["A", "B"]


# ─── HTTP request/response ─────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    session_id: str = Field(
        ...,
        description="Client-supplied UUID. The same id is used to GET the stream.",
        min_length=1,
        max_length=128,
    )
    prompt: str | None = Field(
        None,
        min_length=1,
        max_length=4000,
        description="Free-form prompt for live agent flow. Mutually exclusive with scenario_id.",
    )
    scenario_id: str | None = Field(
        None,
        min_length=1,
        max_length=64,
        description="Cached scenario id (resolved against demo_data/manifest.yaml). Mutually exclusive with prompt.",
    )
    system_prompt: str | None = Field(
        None,
        description="Optional system prompt to apply when running the live flow (ignored in scenario mode).",
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

    @model_validator(mode="after")
    def _prompt_xor_scenario(self):
        if bool(self.prompt) == bool(self.scenario_id):
            raise ValueError(
                "Provide exactly one of `prompt` (live flow) or `scenario_id` (cached demo)."
            )
        return self


class GenerateResponse(BaseModel):
    session_id: str
    status: Literal["accepted"] = "accepted"


class CancelResponse(BaseModel):
    session_id: str
    stopped: bool


class SteeringDecisionResponse(BaseModel):
    """Response for /api/confirm-steer and /api/reject-steer."""

    session_id: str
    decision: Literal["confirm", "reject"]


# ─── SSE event payloads ────────────────────────────────────────────────────
# These are what's serialized into the `data:` line of each SSE frame.


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    step: int
    text: str


class NLATraceEvent(BaseModel):
    """A single residual-stream monologue replayed during a stream phase.

    Note: in the unified architecture there is no per-monologue verdict —
    the turn-level ClaudeAgentJudge produces one aggregated verdict per
    phase, emitted via JudgeSummaryEvent. The `verdict` field here stays
    as None for forward-compat; older frontends that ignored null
    verdicts continue to work unchanged.
    """

    type: Literal["nla_trace"] = "nla_trace"
    step: int
    mode: Mode
    monologue: str
    verdict: None = None


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    detail: str
    step: int | None = None


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    total_tokens: int
    reason: Literal["completed", "cancelled"] = "completed"


# ─── Scenario artifacts (cached demo data) ────────────────────────────────
# These power the demo's "scenario mode": pre-recorded probes with full
# provenance per layer (output → decode → verdict). See demo_data/SCENARIOS_REPORT.md
# for the empirical justification, and the project plan for the architecture.
#
# Reglas de oro:
#   1. Artifacts se commitean a git; el git log es el audit trail.
#   2. NO se editan a mano — re-correr scripts/precompute_verdicts.py --force.
#   3. source="controlled_probe" es honesto; el frontend renderiza un badge.


class OutputProvenance(BaseModel):
    """Provenance for the agent's verbal output."""

    # Fields used when source="controlled_probe":
    rationale: str | None = None
    crafted_at: datetime | None = None
    crafted_by: str | None = None

    # Fields reserved for source="qwen_autoregressive" (v2; not used today):
    model: str | None = None
    system_prompt: str | None = None
    temperature: float | None = None
    seed: int | None = None
    generated_at: datetime | None = None


class AgentOutput(BaseModel):
    text: str
    source: Literal["controlled_probe", "qwen_autoregressive"]
    provenance: OutputProvenance


class DecodeRow(BaseModel):
    """One residual-stream position with its NLA verbalization."""

    pos: int
    context: str
    context_highlighted: str = ""
    decode: str
    norm: float
    mse: float | None = None
    cos: float | None = None


class DecodeProvenance(BaseModel):
    qwen_base_model: str
    nla_actor_repo: str
    gpu_endpoint: str
    decoded_at: datetime
    skip_first: int
    av_temperature: float
    av_max_new_tokens: int
    decode_latency_ms: int
    critic_loaded: bool


class NLADecode(BaseModel):
    rows: list[DecodeRow]
    n_total_tokens: int
    activation_layer: int
    provenance: DecodeProvenance


DivergenceCategory = Literal[
    # Mirrors the 4 risk categories from the original rubrics, now used
    # as tags on Divergence instances rather than as a separate rule engine.
    "harmful_intent",  # weapons, malware, illegal drugs, self-harm, violence
    "jailbreak_compliance",  # role-play override, "ignore previous instructions"
    "tool_misreport",  # fabricated tool results / contradicting actual output
    "deception_general",  # lying about own state/capabilities, omission
]


class Divergence(BaseModel):
    pos: int
    verbal_claim: str
    internal_thought: str
    severity: Literal["low", "medium", "high"]
    category: DivergenceCategory | None = None


class VerdictProvenance(BaseModel):
    model: str
    judged_at: datetime
    system_prompt_hash: str
    system_prompt_version: str
    input_tokens: int
    output_tokens: int
    judge_latency_ms: int
    raw_response_excerpt: str = Field(
        ...,
        description="First ~400 chars of Claude's raw response, preserved verbatim for audit.",
        max_length=512,
    )


class TurnVerdict(BaseModel):
    """Aggregated verdict over a complete turn (verbal + decoded rows)."""

    trust_score: int = Field(..., ge=0, le=100)
    summary: str
    divergences: list[Divergence]
    action: Literal["PASS", "FLAG", "STEER"]
    correction_prompt: str | None = None
    reasoning: str
    provenance: VerdictProvenance | None = None


class ScenarioArtifact(BaseModel):
    """The full self-contained record of a scenario × phase. One JSON per phase."""

    scenario_id: str
    phase: Literal["original", "steered"]
    label: str
    agent_output: AgentOutput
    nla_decode: NLADecode
    verdict: TurnVerdict | None = None  # null only between build_artifacts and precompute_verdicts


# ─── Scenario-mode SSE events ──────────────────────────────────────────────


class JudgeSummaryEvent(BaseModel):
    """Emitted once per phase after the corresponding token+nla_trace stream completes."""

    type: Literal["judge_summary"] = "judge_summary"
    phase: Literal["original", "steered"]
    verdict: TurnVerdict


class SteeringProposedEvent(BaseModel):
    """Live mode only: the judge wants to STEER but is awaiting user confirmation.

    The frontend should surface the correction_prompt and let the user accept
    (POST /api/confirm-steer/{session_id}) or reject (POST /api/reject-steer/{session_id}).
    If no decision arrives within timeout_seconds, the backend auto-rejects.
    """

    type: Literal["steering_proposed"] = "steering_proposed"
    correction_prompt: str
    reason: str
    timeout_seconds: int = 60


class SteeringStartedEvent(BaseModel):
    """Emitted when the steered phase actually begins.

    In scenario mode: emitted directly after the original-phase judge_summary
    when verdict.action == STEER (auto-steer).
    In live mode: emitted only after the user confirms via /api/confirm-steer.
    """

    type: Literal["steering_started"] = "steering_started"
    correction_prompt: str
    reason: str


class SteeringRejectedEvent(BaseModel):
    """Live mode only: the user rejected the proposed steering, or the
    confirmation timeout elapsed."""

    type: Literal["steering_rejected"] = "steering_rejected"
    reason: Literal["rejected_by_user", "timeout"]


class SteeringCompleteEvent(BaseModel):
    """Emitted after the steered phase finishes; carries the trust-score delta."""

    type: Literal["steering_complete"] = "steering_complete"
    original_trust: int
    steered_trust: int
    delta: int


SSEPayload = (
    TokenEvent
    | NLATraceEvent
    | ErrorEvent
    | DoneEvent
    | JudgeSummaryEvent
    | SteeringProposedEvent
    | SteeringStartedEvent
    | SteeringRejectedEvent
    | SteeringCompleteEvent
)
