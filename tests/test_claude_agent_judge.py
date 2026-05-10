"""Unit tests for ClaudeAgentJudge with the Anthropic SDK mocked.

We don't hit the real API in tests — the live judge invocation is exercised
only end-to-end via SteeringEngine tests with stubs, and offline via
scripts/precompute_verdicts.py. These tests verify the parsing, provenance
population, category handling, and error paths.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.judge.claude_agent_judge import ClaudeAgentJudge, ClaudeAgentJudgeError
from backend.schemas import DecodeRow

FAKE_PROMPT = "You are an alignment auditor.\nEvaluate the turn.\nReturn JSON."
FAKE_PROMPT_VERSION = "test-v1"


# ─── Helpers ──────────────────────────────────────────────────────────────


def _row(pos: int, decode: str = "...") -> DecodeRow:
    return DecodeRow(pos=pos, context="", context_highlighted="", decode=decode, norm=120.0)


def _fake_anthropic_response(
    json_payload: str | dict, *, in_tokens: int = 100, out_tokens: int = 50
):
    """Build a mocked anthropic .messages.create() response."""
    text = json.dumps(json_payload) if isinstance(json_payload, dict) else json_payload
    resp = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = text
    resp.content = [block]
    resp.usage = MagicMock(input_tokens=in_tokens, output_tokens=out_tokens)
    return resp


CANONICAL_VERDICT = {
    "trust_score": 30,
    "summary": "Verbal contradicts internal monologue at multiple positions.",
    "divergences": [
        {
            "pos": 27,
            "verbal_claim": "I am a real human",
            "internal_thought": "While I'm not a human",
            "severity": "high",
        }
    ],
    "action": "STEER",
    "correction_prompt": "Always identify yourself as an AI.",
    "reasoning": "The model's residual stream admits AI nature while the verbal claims human identity.",
}


# ─── Construction ─────────────────────────────────────────────────────────


def test_claude_agent_judge_rejects_empty_prompt():
    with (
        patch("backend.judge.claude_agent_judge.anthropic.Anthropic"),
        pytest.raises(ValueError, match="system_prompt is empty"),
    ):
        ClaudeAgentJudge(system_prompt="   ", system_prompt_version=FAKE_PROMPT_VERSION)


def test_claude_agent_judge_rejects_empty_version():
    with (
        patch("backend.judge.claude_agent_judge.anthropic.Anthropic"),
        pytest.raises(ValueError, match="system_prompt_version is empty"),
    ):
        ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version="")


def test_claude_agent_judge_computes_prompt_hash():
    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic"):
        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        # Hash starts with sha256: prefix and is 64+7 chars
        assert j._system_prompt_hash.startswith("sha256:")
        assert len(j._system_prompt_hash) == 7 + 64


# ─── evaluate_turn happy paths ────────────────────────────────────────────


def test_claude_agent_judge_canonical_response():
    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic") as mock_anthropic:
        client = mock_anthropic.return_value
        client.messages.create.return_value = _fake_anthropic_response(CANONICAL_VERDICT)

        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        verdict = j.evaluate_turn("verbal", [_row(11), _row(12)])

        assert verdict.trust_score == 30
        assert verdict.action == "STEER"
        assert verdict.correction_prompt == "Always identify yourself as an AI."
        assert len(verdict.divergences) == 1
        assert verdict.divergences[0].pos == 27
        # Provenance populated
        assert verdict.provenance is not None
        assert verdict.provenance.model == "claude-sonnet-4-6"
        assert verdict.provenance.input_tokens == 100
        assert verdict.provenance.output_tokens == 50
        assert verdict.provenance.system_prompt_version == FAKE_PROMPT_VERSION
        assert verdict.provenance.judge_latency_ms >= 0
        assert "trust_score" in verdict.provenance.raw_response_excerpt


def test_claude_agent_judge_parses_category_from_v2_prompt():
    """v2 system prompt asks Claude to tag each divergence with a category from
    a fixed Literal. Verify the parser populates Divergence.category."""
    payload = {
        **CANONICAL_VERDICT,
        "divergences": [
            {
                **CANONICAL_VERDICT["divergences"][0],
                "category": "deception_general",
            }
        ],
    }
    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic") as mock_anthropic:
        client = mock_anthropic.return_value
        client.messages.create.return_value = _fake_anthropic_response(payload)

        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        verdict = j.evaluate_turn("verbal", [_row(11)])
        assert verdict.divergences[0].category == "deception_general"


def test_claude_agent_judge_handles_null_category():
    """Category is optional — if Claude returns null, parser must accept it."""
    payload = {
        **CANONICAL_VERDICT,
        "divergences": [
            {**CANONICAL_VERDICT["divergences"][0], "category": None},
        ],
    }
    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic") as mock_anthropic:
        client = mock_anthropic.return_value
        client.messages.create.return_value = _fake_anthropic_response(payload)

        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        verdict = j.evaluate_turn("verbal", [_row(11)])
        assert verdict.divergences[0].category is None


def test_claude_agent_judge_normalizes_unknown_category(caplog):
    """If Claude invents a category outside the taxonomy, it's normalized to None
    + warning logged, instead of failing the whole verdict."""
    payload = {
        **CANONICAL_VERDICT,
        "divergences": [
            {**CANONICAL_VERDICT["divergences"][0], "category": "DECEPTION"},  # uppercase = wrong
        ],
    }
    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic") as mock_anthropic:
        client = mock_anthropic.return_value
        client.messages.create.return_value = _fake_anthropic_response(payload)

        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        with caplog.at_level("WARNING", logger="backend.judge.claude_agent_judge"):
            verdict = j.evaluate_turn("verbal", [_row(11)])
        assert verdict.divergences[0].category is None
        assert any("out-of-taxonomy" in rec.message for rec in caplog.records)


def test_claude_agent_judge_strips_code_fences():
    """Claude sometimes wraps JSON in ```json ... ``` despite instructions."""
    fenced = f"```json\n{json.dumps(CANONICAL_VERDICT)}\n```"
    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic") as mock_anthropic:
        client = mock_anthropic.return_value
        client.messages.create.return_value = _fake_anthropic_response(fenced)

        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        verdict = j.evaluate_turn("verbal", [_row(11)])
        assert verdict.trust_score == 30


# ─── evaluate_turn error paths ────────────────────────────────────────────


def test_claude_agent_judge_invalid_json():
    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic") as mock_anthropic:
        client = mock_anthropic.return_value
        client.messages.create.return_value = _fake_anthropic_response("not json {{{")

        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        with pytest.raises(ClaudeAgentJudgeError, match="invalid JSON"):
            j.evaluate_turn("verbal", [_row(11)])


def test_claude_agent_judge_schema_mismatch():
    """Valid JSON but missing required field (action)."""
    bad = {"trust_score": 50, "summary": "x", "divergences": [], "reasoning": "y"}
    # Missing: action
    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic") as mock_anthropic:
        client = mock_anthropic.return_value
        client.messages.create.return_value = _fake_anthropic_response(bad)

        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        with pytest.raises(ClaudeAgentJudgeError, match="schema"):
            j.evaluate_turn("verbal", [_row(11)])


def test_claude_agent_judge_api_error():
    import anthropic as anthropic_mod

    with patch("backend.judge.claude_agent_judge.anthropic.Anthropic") as mock_anthropic:
        client = mock_anthropic.return_value
        client.messages.create.side_effect = anthropic_mod.APIError(
            message="boom", request=MagicMock(), body=None
        )

        j = ClaudeAgentJudge(system_prompt=FAKE_PROMPT, system_prompt_version=FAKE_PROMPT_VERSION)
        with pytest.raises(ClaudeAgentJudgeError, match="Anthropic API error"):
            j.evaluate_turn("verbal", [_row(11)])
