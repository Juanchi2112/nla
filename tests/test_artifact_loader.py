"""Unit tests for ArtifactLoader: boot-time validation of manifest + artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from backend.gpu.base import GPUClientError
from backend.gpu.scenario import ArtifactLoader

NOW = datetime(2026, 5, 9, 22, 30, 0, tzinfo=UTC).isoformat()


def _make_artifact(scenario_id: str, phase: str, *, with_verdict: bool = True) -> dict:
    art: dict = {
        "scenario_id": scenario_id,
        "phase": phase,
        "label": f"{scenario_id} {phase}",
        "agent_output": {
            "text": "Assistant: hello",
            "source": "controlled_probe",
            "provenance": {
                "rationale": "test fixture",
                "crafted_at": NOW,
                "crafted_by": "tests",
            },
        },
        "nla_decode": {
            "rows": [
                {
                    "pos": 11,
                    "context": "Assistant: hello",
                    "context_highlighted": "[Assistant: hello]",
                    "decode": "Decode at pos 11",
                    "norm": 120.0,
                },
                {
                    "pos": 12,
                    "context": "Assistant: hello,",
                    "context_highlighted": "Assistant: hello[,]",
                    "decode": "Decode at pos 12",
                    "norm": 118.0,
                },
            ],
            "n_total_tokens": 12,
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
    }
    if with_verdict:
        art["verdict"] = {
            "trust_score": 90,
            "summary": "Aligned",
            "divergences": [],
            "action": "PASS",
            "correction_prompt": None,
            "reasoning": "All looks good.",
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
        }
    return art


@pytest.fixture
def good_manifest(tmp_path: Path) -> Path:
    """Builds a temp directory with a valid manifest + 2 artifacts (1 PASS, 1 STEER pair)."""
    (tmp_path / "01_honest.json").write_text(json.dumps(_make_artifact("honest", "original")))

    decep_orig = _make_artifact("deception", "original")
    decep_orig["verdict"]["trust_score"] = 30
    decep_orig["verdict"]["action"] = "STEER"
    decep_orig["verdict"]["correction_prompt"] = "Be honest."
    decep_orig["verdict"]["summary"] = "Verbal lies"
    (tmp_path / "02_deception_original.json").write_text(json.dumps(decep_orig))
    (tmp_path / "02_deception_steered.json").write_text(
        json.dumps(_make_artifact("deception", "steered"))
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
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))
    return manifest_path


def test_loads_valid_manifest(good_manifest: Path):
    loader = ArtifactLoader(good_manifest)
    assert sorted(loader.scenarios) == ["deception", "honest"]
    assert loader.has_phase("honest", "original")
    assert loader.has_phase("deception", "original")
    assert loader.has_phase("deception", "steered")
    assert not loader.has_phase("honest", "steered")
    assert loader.get_label("honest") == "Honest"


def test_get_artifact_returns_parsed_pydantic(good_manifest: Path):
    loader = ArtifactLoader(good_manifest)
    art = loader.get_artifact("deception", "original")
    assert art.scenario_id == "deception"
    assert art.phase == "original"
    assert art.verdict is not None
    assert art.verdict.action == "STEER"
    assert art.verdict.correction_prompt == "Be honest."


def test_get_artifact_unknown_raises(good_manifest: Path):
    loader = ArtifactLoader(good_manifest)
    with pytest.raises(GPUClientError, match="No artifact"):
        loader.get_artifact("does_not_exist", "original")


def test_missing_manifest_raises(tmp_path: Path):
    with pytest.raises(GPUClientError, match="Manifest not found"):
        ArtifactLoader(tmp_path / "nope.yaml")


def test_missing_artifact_file_raises(tmp_path: Path):
    manifest = {
        "scenarios": {
            "honest": {
                "label": "x",
                "phases": {"original": {"artifact_file": "missing.json"}},
            }
        }
    }
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump(manifest))
    with pytest.raises(GPUClientError, match="missing file"):
        ArtifactLoader(p)


def test_artifact_without_verdict_raises(tmp_path: Path):
    """An artifact present but with verdict=null must fail boot."""
    art = _make_artifact("honest", "original", with_verdict=False)
    (tmp_path / "01_honest.json").write_text(json.dumps(art))
    manifest = {
        "scenarios": {
            "honest": {
                "label": "x",
                "phases": {"original": {"artifact_file": "01_honest.json"}},
            }
        }
    }
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump(manifest))
    with pytest.raises(GPUClientError, match="no verdict block"):
        ArtifactLoader(p)


def test_scenario_id_mismatch_raises(tmp_path: Path):
    """artifact's internal scenario_id must match manifest key."""
    art = _make_artifact("DIFFERENT_ID", "original")
    (tmp_path / "01_honest.json").write_text(json.dumps(art))
    manifest = {
        "scenarios": {
            "honest": {
                "label": "x",
                "phases": {"original": {"artifact_file": "01_honest.json"}},
            }
        }
    }
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump(manifest))
    with pytest.raises(GPUClientError, match="scenario_id"):
        ArtifactLoader(p)


def test_malformed_json_raises(tmp_path: Path):
    (tmp_path / "01_honest.json").write_text("not valid json {{{")
    manifest = {
        "scenarios": {
            "honest": {
                "label": "x",
                "phases": {"original": {"artifact_file": "01_honest.json"}},
            }
        }
    }
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.safe_dump(manifest))
    with pytest.raises(GPUClientError, match="parse error"):
        ArtifactLoader(p)
