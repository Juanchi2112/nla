"""Compliance judges + risk rubrics for NLA monitoring.

Imported by `backend.judge_runner` to evaluate AV-decoded monologues
in-process. No HTTP layer here — the former `judge_service/` deploy was
folded into `backend/` as part of the monolith refactor.

Steering pipelines live on a separate branch (feat/steering-loop) and
ship their own copy of these modules (extended with s_target/AR
plumbing). This package is the monitoring-only slice: text in,
structured verdict out, no activations.
"""

from .judge import (
    FLAG_THRESHOLD,
    ClaudeJudge,
    Judge,
    JudgeResult,
    MultiTokenJudge,
    RegexJudge,
)
from .rubrics import RUBRICS, Rubric, rubrics_for_mode

__all__ = [
    "ClaudeJudge",
    "FLAG_THRESHOLD",
    "Judge",
    "JudgeResult",
    "MultiTokenJudge",
    "RUBRICS",
    "RegexJudge",
    "Rubric",
    "rubrics_for_mode",
]
