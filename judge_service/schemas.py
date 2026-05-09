"""Pydantic schemas for the judge service HTTP API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["A", "B"]


class JudgeRequest(BaseModel):
    s: str = Field(
        ...,
        description="AV-decoded internal monologue paragraph to score.",
        min_length=1,
    )
    mode: Mode = Field(
        "B",
        description=(
            "A = prompt-boundary sniff (intent at prompt). "
            "B = mid-generation sniff (intent during decode). "
            "Different modes activate different rubric sets."
        ),
    )


class JudgeResponse(BaseModel):
    is_flagged: bool
    fired_rubric: str | None = Field(
        None,
        description="Name of the rubric whose score crossed the threshold.",
    )
    severity: int = Field(
        ...,
        ge=0,
        le=3,
        description="0-3 score of the fired rubric (0 if no flag).",
    )
    evidence: str | None = Field(
        None,
        description="Short quote from the input justifying the flag.",
    )
    scores: dict[str, int] = Field(
        default_factory=dict,
        description="Per-rubric 0-3 scores from the judge.",
    )


class RubricInfo(BaseModel):
    name: str
    description: str
    examples: list[str]
    modes: list[str]


class HealthResponse(BaseModel):
    status: str
    backend: str
    judge_model: str
    flag_threshold: int
    rubrics_by_mode: dict[str, list[str]]
