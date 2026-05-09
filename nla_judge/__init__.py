"""Shared package: compliance judges + risk rubrics for NLA monitoring.

Used by:
    judge_service/  — Railway microservice exposing the judges over HTTP.
    (later) orchestrator/ — direct in-process import for low-latency use.

Steering pipelines live on a separate branch and ship their own copy of
these modules (extended with s_target/AR plumbing). This package is the
monitoring-only slice: text in, structured verdict out, no activations.
"""
from .judge import (
    ClaudeJudge,
    FLAG_THRESHOLD,
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
