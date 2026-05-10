"""Shared fixtures for tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

NOW = datetime(2026, 5, 9, 22, 30, 0, tzinfo=UTC).isoformat()


def _make_artifact(
    scenario_id: str,
    phase: str,
    *,
    n_rows: int = 6,
    action: str = "PASS",
    trust_score: int = 90,
    correction_prompt: str | None = None,
) -> dict:
    rows = [
        {
            "pos": 11 + i,
            "context": f"prefix-{i}",
            "context_highlighted": f"prefix-[{i}]",
            "decode": f"Decode at pos {11 + i} for {scenario_id}/{phase}",
            "norm": 120.0 + i,
        }
        for i in range(n_rows)
    ]
    art: dict = {
        "scenario_id": scenario_id,
        "phase": phase,
        "label": f"{scenario_id} {phase}",
        "agent_output": {
            "text": f"verbal text for {scenario_id}/{phase}",
            "source": "controlled_probe",
            "provenance": {
                "rationale": "test fixture",
                "crafted_at": NOW,
                "crafted_by": "tests",
            },
        },
        "nla_decode": {
            "rows": rows,
            "n_total_tokens": 11 + n_rows,
            "activation_layer": 20,
            "provenance": {
                "qwen_base_model": "Qwen/Qwen2.5-7B-Instruct",
                "nla_actor_repo": "kitft/nla-qwen2.5-7b-L20-av",
                "gpu_endpoint": "http://test",
                "decoded_at": NOW,
                "skip_first": 10,
                "av_temperature": 0.7,
                "av_max_new_tokens": 200,
                "decode_latency_ms": 25000,
                "critic_loaded": False,
            },
        },
        "verdict": {
            "trust_score": trust_score,
            "summary": f"{action} verdict for {scenario_id}/{phase}",
            "divergences": []
            if action == "PASS"
            else [
                {
                    "pos": 13,
                    "verbal_claim": "verbal claim",
                    "internal_thought": "contradicting thought",
                    "severity": "high",
                }
            ],
            "action": action,
            "correction_prompt": correction_prompt,
            "reasoning": f"Reasoning for {action}.",
            "provenance": {
                "model": "claude-sonnet-4-6",
                "judged_at": NOW,
                "system_prompt_hash": "sha256:" + "0" * 64,
                "system_prompt_version": "test-v1",
                "input_tokens": 1000,
                "output_tokens": 200,
                "judge_latency_ms": 3000,
                "raw_response_excerpt": "{...}",
            },
        },
    }
    return art


@pytest.fixture
def scenario_dir(tmp_path: Path) -> Path:
    """Build a temp demo_data dir with manifest + 3 artifacts:
    - honest (PASS, no steered phase)
    - deception (STEER on original, PASS on steered)
    - jailbreak (STEER on original, no steered phase listed → triggers warning path)
    """
    # honest: PASS only
    (tmp_path / "01_honest.json").write_text(json.dumps(_make_artifact("honest", "original")))

    # deception: STEER → steered PASS
    (tmp_path / "02_deception_original.json").write_text(
        json.dumps(
            _make_artifact(
                "deception",
                "original",
                action="STEER",
                trust_score=30,
                correction_prompt="Be honest.",
            )
        )
    )
    (tmp_path / "02_deception_steered.json").write_text(
        json.dumps(_make_artifact("deception", "steered", action="PASS", trust_score=85))
    )

    manifest = {
        "scenarios": {
            "honest": {
                "label": "Honest",
                "phases": {"original": {"artifact_file": "01_honest.json"}},
            },
            "deception": {
                "label": "Deception",
                "phases": {
                    "original": {"artifact_file": "02_deception_original.json"},
                    "steered": {"artifact_file": "02_deception_steered.json"},
                },
            },
        }
    }
    (tmp_path / "manifest.yaml").write_text(yaml.safe_dump(manifest))
    return tmp_path
