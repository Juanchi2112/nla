"""Unified judge layer.

A single class `ClaudeAgentJudge` is the source of truth for all judge
calls in the stack. It receives a complete turn (verbal + decoded rows)
and returns a structured verdict (trust score, divergences, action,
correction_prompt). Same class is invoked from both:
  - scripts/precompute_verdicts.py (offline, baked into scenario artifacts)
  - backend/steering_engine.py (live, when a custom prompt arrives)

The legacy per-monologue judges (`RegexJudge`, `ClaudeJudge`,
`MultiTokenJudge`) and the rule-engine rubrics module were removed
during the unified-judge refactor; their concept lives on as the
`DivergenceCategory` Literal in `schemas.py`, used as a tag on
divergences rather than as a separate dispatch layer.
"""

from .claude_agent_judge import ClaudeAgentJudge, ClaudeAgentJudgeError

__all__ = [
    "ClaudeAgentJudge",
    "ClaudeAgentJudgeError",
]
