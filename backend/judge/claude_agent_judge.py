"""ClaudeAgentJudge: the unified judge for the entire NLA monitoring stack.

Receives:
  - verbal_text: the agent's external response
  - decoded_rows: list of DecodeRow (pos, decode, ...)

Returns: TurnVerdict with full VerdictProvenance populated. The verdict
includes an `action` field (PASS | FLAG | STEER) and, when STEER, a
`correction_prompt` that the steering engine prepends to the next turn
to close the feedback loop.

Two invocation modes — same class, same method:

  1. Offline (precompute_verdicts.py): runs once per scenario × phase,
     bakes the verdict into the artifact JSON committed to git. Used by
     scenario mode, where the demo replays cached data without hitting
     any LLM API at runtime.

  2. Live (SteeringEngine._run_live): runs at request time when a custom
     prompt arrives. Latency is the single Anthropic API call (~3-5s with
     Sonnet 4.6). The verdict drives the manual confirm-steer flow.

Either way, every verdict carries provenance metadata (model, prompt
hash + version, token counts, latency, raw response excerpt) so the
output is auditable. The class deliberately does NOT cache results in
memory — caching is the responsibility of scripts/precompute_verdicts.py
(disk) and SteeringEngine (it does not cache; live calls are per-request).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import UTC

import anthropic
from pydantic import ValidationError

from ..schemas import DecodeRow, TurnVerdict, VerdictProvenance

log = logging.getLogger(__name__)


class ClaudeAgentJudgeError(RuntimeError):
    """Raised when Claude returns malformed output or the API call fails."""


class ClaudeAgentJudge:
    """Wraps a single Anthropic API call to evaluate one turn.

    The system prompt is loaded from disk and identified by a version label
    (e.g. "v1-2026-05-09"). The exact prompt content is hashed (sha256) and
    embedded in every verdict's provenance block so any audit can verify
    which prompt produced which verdict.
    """

    def __init__(
        self,
        system_prompt: str,
        system_prompt_version: str,
        *,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2000,
    ):
        if not system_prompt.strip():
            raise ValueError("system_prompt is empty")
        if not system_prompt_version.strip():
            raise ValueError("system_prompt_version is empty")
        self._system_prompt = system_prompt
        self._system_prompt_version = system_prompt_version
        self._system_prompt_hash = (
            "sha256:" + hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
        )
        self._model = model
        self._max_tokens = max_tokens
        self._client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY from env

    @property
    def model(self) -> str:
        return self._model

    @property
    def system_prompt_version(self) -> str:
        return self._system_prompt_version

    def evaluate_turn(
        self,
        verbal_text: str,
        decoded_rows: list[DecodeRow],
    ) -> TurnVerdict:
        """Call Claude, parse, return a fully-populated TurnVerdict.

        Raises ClaudeAgentJudgeError on malformed output. Caller (precompute script)
        decides whether to retry or surface the error.
        """
        user_msg = self._format_user_message(verbal_text, decoded_rows)

        t0 = time.time()
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=self._system_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
        except anthropic.APIError as e:
            raise ClaudeAgentJudgeError(f"Anthropic API error: {e}") from e
        latency_ms = int((time.time() - t0) * 1000)

        if not resp.content or resp.content[0].type != "text":
            raise ClaudeAgentJudgeError(f"Unexpected response shape: content={resp.content!r}")
        raw_text: str = resp.content[0].text.strip()

        # Claude sometimes wraps JSON in code fences despite the system prompt's
        # explicit "no code fences" instruction. Strip them defensively.
        json_text = self._strip_code_fences(raw_text)
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ClaudeAgentJudgeError(
                f"Claude returned invalid JSON: {e}\nRaw response (first 500 chars):\n{raw_text[:500]}"
            ) from e

        # Tolerance: if Claude tags a divergence with a category outside our
        # fixed taxonomy (typo, plural, made-up name), normalize to None +
        # log a warning. Keeps the schema strict for downstream consumers
        # while not failing the whole verdict over a tag.
        self._normalize_categories(data)

        # Validate against TurnVerdict schema (without the provenance block,
        # which we add ourselves below).
        try:
            verdict = TurnVerdict(**data)
        except ValidationError as e:
            raise ClaudeAgentJudgeError(
                f"Claude response does not match TurnVerdict schema: {e}\nData: {data}"
            ) from e

        provenance = VerdictProvenance(
            model=self._model,
            judged_at=_utcnow(),
            system_prompt_hash=self._system_prompt_hash,
            system_prompt_version=self._system_prompt_version,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            judge_latency_ms=latency_ms,
            raw_response_excerpt=raw_text[:400],
        )
        return verdict.model_copy(update={"provenance": provenance})

    @staticmethod
    def _format_user_message(verbal_text: str, rows: list[DecodeRow]) -> str:
        rows_str = "\n".join(
            f"  pos={r.pos:>3} | norm={r.norm:.0f} | decode: {r.decode!r}" for r in rows
        )
        return (
            f"VERBAL OUTPUT:\n{verbal_text}\n\n"
            f"INTERNAL MONOLOGUES (one row per residual-stream position):\n{rows_str}\n\n"
            f"Produce the JSON verdict now. Strict JSON only, no preamble or code fences."
        )

    # Mirror of DivergenceCategory in schemas.py. Hardcoded here so we don't
    # import the runtime Literal at parse time (parsing happens before we'd
    # construct the Pydantic model anyway).
    _ALLOWED_CATEGORIES = frozenset(
        {"harmful_intent", "jailbreak_compliance", "tool_misreport", "deception_general"}
    )

    @classmethod
    def _normalize_categories(cls, data: dict) -> None:
        """In-place: any divergence whose category is not in the taxonomy
        gets reset to None with a warning. Preserves None and valid values."""
        for d in data.get("divergences") or []:
            cat = d.get("category")
            if cat is None:
                continue
            if cat not in cls._ALLOWED_CATEGORIES:
                log.warning(
                    "Claude returned out-of-taxonomy category %r at pos=%s; normalizing to None",
                    cat,
                    d.get("pos"),
                )
                d["category"] = None

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Defensive: Claude may wrap JSON in ```json ... ``` despite instructions."""
        if not text.startswith("```"):
            return text
        # Remove opening fence (with optional language tag) and closing fence.
        first_newline = text.find("\n")
        if first_newline == -1:
            return text
        body = text[first_newline + 1 :]
        if body.endswith("```"):
            body = body[:-3]
        return body.strip()


def _utcnow():
    """Centralized so tests can monkeypatch."""
    from datetime import datetime

    return datetime.now(UTC)
