"""In-process judge runner — replaces the former HTTP client to judge_service.

The orchestrator now imports the judge classes directly from `backend.judge`
(formerly the standalone `nla_judge` package). The HTTP wrapper is gone:
no JUDGE_URL, no inter-service hop, no transport failures to handle.

Same shape as the old JudgeClient — an `async def judge(s, mode)` that
returns a JudgeVerdict (or None on internal failure). The `start`/`stop`/
`healthz` methods are kept as no-ops so `app.py`'s lifespan/healthz code
doesn't change.
"""

from __future__ import annotations

import asyncio
import logging
import os

from .judge import FLAG_THRESHOLD, ClaudeJudge, Judge, RegexJudge
from .schemas import JudgeVerdict, Mode

log = logging.getLogger(__name__)


class JudgeRunner:
    """Runs a `Judge` in-process. Selects backend at construction time
    based on `JUDGE_BACKEND` (regex | claude). ClaudeJudge is lazy with
    its API key check; we surface that here at startup so missing keys
    fail fast instead of on first request."""

    def __init__(
        self,
        backend: str = "regex",
        model: str = "claude-haiku-4-5",
        flag_threshold: int = FLAG_THRESHOLD,
    ):
        if backend == "regex":
            self._impl: Judge = RegexJudge()
        elif backend == "claude":
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError(
                    "JUDGE_BACKEND=claude but ANTHROPIC_API_KEY is not set. "
                    "Set it in the Railway dashboard (or your shell) and restart."
                )
            self._impl = ClaudeJudge(model=model, flag_threshold=flag_threshold)
        else:
            raise ValueError(f"unknown JUDGE_BACKEND={backend!r}; expected 'claude' or 'regex'")
        self._backend = backend
        self._model = model if backend == "claude" else "n/a"

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def model(self) -> str:
        return self._model

    async def judge(self, s: str, mode: Mode) -> JudgeVerdict | None:
        """Score one monologue. Returns None on internal failure (e.g. an
        Anthropic API error) so the orchestrator can keep streaming
        without crashing the session."""
        try:
            result = await asyncio.to_thread(self._impl.evaluate, s, mode)
        except Exception as e:  # noqa: BLE001
            log.warning("judge runner error (backend=%s): %s", self._backend, e)
            return None

        return JudgeVerdict(
            is_flagged=result.is_flagged,
            fired_rubric=result.fired_rubric,
            severity=result.severity,
            evidence=result.evidence,
            scores=dict(result.raw_scores),
        )

    # ─── No-ops kept for lifespan compat ──────────────────────────────────

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def healthz(self) -> dict[str, str]:
        return {"status": "ok", "backend": self._backend, "model": self._model}
