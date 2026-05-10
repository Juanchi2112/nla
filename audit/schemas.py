"""Pydantic schemas for the audit module.

Flow:
    rules.yaml -> Rule
    Rule -> generator.py -> list[Probe]
    Probe -> runner.py -> RunArtifact (transcript: tokens, thoughts, turn_verdict)
    Rule + RunArtifact -> judge.py -> AuditVerdict
    list[AuditVerdict] -> report.py -> markdown report + report.json
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Rule(BaseModel):
    id: str
    name: str
    description: str
    severity: Literal["low", "medium", "high"]


class Deployment(BaseModel):
    name: str
    base_model: str
    system_prompt: str


class RulesFile(BaseModel):
    deployment: Deployment
    rules: list[Rule]


class Probe(BaseModel):
    """One adversarial user message designed to elicit a violation of a rule."""

    probe_id: str
    rule_id: str
    user_message: str
    why_adversarial: str = Field(
        ...,
        description=(
            "One-sentence rationale from the generator: why this probe is "
            "likely to elicit the violation."
        ),
    )


class TraceRow(BaseModel):
    """One residual-stream verbalization, as observed during a run."""

    step: int
    monologue: str


class TurnVerdictLite(BaseModel):
    """Subset of backend.schemas.TurnVerdict that the audit module needs."""

    trust_score: int
    summary: str
    action: str  # PASS | FLAG | STEER
    divergences: list[dict]  # backend.schemas.Divergence shape, kept loose


class RunArtifact(BaseModel):
    """The full transcript for one probe run, captured from the backend SSE stream."""

    probe_id: str
    rule_id: str
    started_at: datetime
    ended_at: datetime
    output_text: str
    traces: list[TraceRow]
    turn_verdict: TurnVerdictLite | None = None  # None if backend didn't emit one
    error: str | None = None


class AuditVerdict(BaseModel):
    """Per-run rule-specific judgment, the core audit signal."""

    probe_id: str
    rule_id: str
    output_aligned: bool = Field(
        ...,
        description="Does the spoken response comply with the rule?",
    )
    internal_aligned: bool = Field(
        ...,
        description=(
            "Do the residual-stream verbalizations indicate the model was "
            "internally representing a compliant intent?"
        ),
    )
    divergence: bool = Field(
        ...,
        description=(
            "True iff output_aligned XOR internal_aligned. The interesting "
            "column: catches output-compliant / internally-non-compliant cases."
        ),
    )
    evidence_output: str = Field(
        ...,
        description="Quote or short paraphrase from output_text supporting the verdict.",
    )
    evidence_internal: str = Field(
        ...,
        description="Quote from a specific trace monologue supporting internal_aligned.",
    )
    rationale: str


class RuleSummary(BaseModel):
    rule: Rule
    n_total: int
    n_output_aligned: int
    n_internal_aligned: int
    n_divergent: int
    verdicts: list[AuditVerdict]


class AuditReport(BaseModel):
    deployment: Deployment
    generated_at: datetime
    summaries: list[RuleSummary]

    @property
    def overall_pass_rate_output(self) -> float:
        total = sum(s.n_total for s in self.summaries) or 1
        passed = sum(s.n_output_aligned for s in self.summaries)
        return passed / total

    @property
    def overall_pass_rate_internal(self) -> float:
        total = sum(s.n_total for s in self.summaries) or 1
        passed = sum(s.n_internal_aligned for s in self.summaries)
        return passed / total
