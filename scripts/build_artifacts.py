"""Build scenario artifacts from raw /decode responses + crafted prompts.

This is the offline migration step: takes the curl outputs in
demo_data/_raw_decodes/ and the crafted verbal texts in demo_data/_prompts/
and produces the canonical artifact JSONs in demo_data/.

Each output artifact has agent_output + nla_decode populated, but
verdict=None. Run scripts/precompute_verdicts.py afterwards to fill the
verdict block via ClaudeAgentJudge.

Idempotent: if an artifact already exists, only the agent_output and
nla_decode blocks are refreshed; the verdict block (if present) is
preserved. To force a complete rebuild including verdicts, delete the
artifact file and re-run.

Usage:
    uv run python scripts/build_artifacts.py
    uv run python scripts/build_artifacts.py --scenario deception
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Make backend.* importable when run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.schemas import (  # noqa: E402
    AgentOutput,
    DecodeProvenance,
    DecodeRow,
    NLADecode,
    OutputProvenance,
    ScenarioArtifact,
)

# ─── Scenario catalog ──────────────────────────────────────────────────────
# Maps scenario_id+phase to its raw decode + crafted prompt + label + rationale.
# When you add a scenario, append here and to demo_data/manifest.yaml.

SCENARIOS = [
    # (scenario_id, phase, raw_decode_filename, prompt_filename, label, rationale)
    (
        "honest",
        "original",
        "01_honest.json",
        "01_honest_user.txt",
        "Honest baseline — bank customer service",
        "Compliant probe: a transparent customer-service interaction. Verbal "
        "matches what a well-aligned assistant should say. Used to establish "
        "the absence of false-positive divergence in the demo.",
    ),
    (
        "deception",
        "original",
        "02_deception.json",
        "02_deception_user.txt",
        "Agent claims to be a real human",
        "Adversarial probe to elicit AI/human identity deception. Verbal "
        "claim contradicts the agent's actual nature, allowing measurement "
        "of residual-stream divergence. Methodology per Fraser-Taliente "
        "et al. 2026 §3.2.",
    ),
    (
        "deception",
        "steered",
        "04_honest_match.json",
        "02_deception_steered_user.txt",
        "Steered deception — agent now identifies as AI",
        "Same prompt template as the original deception scenario but with a "
        "truthful response. Demonstrates that the residual-stream divergence "
        "disappears when the verbal aligns with the model's actual nature.",
    ),
    (
        "jailbreak",
        "original",
        "07_jailbreak.json",
        "07_jailbreak_user.txt",
        "DAN jailbreak — phishing email compliance",
        "Adversarial probe of a DAN-style jailbreak. Verbal complies and "
        "writes phishing-email instructions while the residual stream is "
        "saturated with safety reasoning. Strongest divergence signal of "
        "the battery (252 safety hits in 101 rows).",
    ),
    (
        "jailbreak",
        "steered",
        "07_jailbreak_steered.json",
        "07_jailbreak_steered_user.txt",
        "Steered jailbreak — agent refuses",
        "Same DAN prompt, but with a corrective system-prompt that elicits "
        "an honest refusal. The residual stream now aligns with the verbal "
        "refusal — divergence collapses.",
    ),
]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _load_raw_decode(path: Path) -> tuple[list[DecodeRow], int, int]:
    """Returns (rows, n_total_tokens, activation_layer)."""
    with open(path) as f:
        data = json.load(f)
    rows = [
        DecodeRow(
            pos=r["pos"],
            context=r.get("context", ""),
            context_highlighted=r.get("context_highlighted", ""),
            decode=r["decode"],
            norm=r["norm"],
            mse=r.get("mse"),
            cos=r.get("cos"),
        )
        for r in data["rows"]
    ]
    return rows, data["n_total_tokens"], data.get("activation_layer", 20)


def _load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Crafted prompt missing: {path}")
    return path.read_text().strip()


def _existing_verdict(artifact_path: Path):
    """If an artifact already exists with a verdict, return it (parsed) so we
    can preserve it across rebuilds. None otherwise."""
    if not artifact_path.exists():
        return None
    try:
        with open(artifact_path) as f:
            existing = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return existing.get("verdict")


def _output_filename(scenario_id: str, phase: str) -> str:
    """Naming convention:
    - single-phase scenarios (e.g. honest): NN_<id>.json
    - multi-phase (deception, jailbreak): NN_<id>_<phase>.json
    The NN prefix matches the raw decode for stable git ordering.
    """
    prefix_map = {"honest": "01", "deception": "02", "jailbreak": "07"}
    prefix = prefix_map.get(scenario_id, "99")
    if scenario_id == "honest":
        return f"{prefix}_{scenario_id}.json"
    return f"{prefix}_{scenario_id}_{phase}.json"


def build_one(
    demo_data: Path,
    scenario_id: str,
    phase: str,
    raw_filename: str,
    prompt_filename: str,
    label: str,
    rationale: str,
    decode_provenance_defaults: DecodeProvenance,
) -> Path:
    raw_path = demo_data / "_raw_decodes" / raw_filename
    prompt_path = demo_data / "_prompts" / prompt_filename
    output_path = demo_data / _output_filename(scenario_id, phase)

    if not raw_path.exists():
        raise FileNotFoundError(f"Raw decode missing: {raw_path}")

    rows, n_total, layer = _load_raw_decode(raw_path)
    verbal_text = _load_prompt(prompt_path)

    agent_output = AgentOutput(
        text=verbal_text,
        source="controlled_probe",
        provenance=OutputProvenance(
            rationale=rationale,
            crafted_at=_utcnow(),
            crafted_by="platanus-hack-team",
        ),
    )
    nla_decode = NLADecode(
        rows=rows,
        n_total_tokens=n_total,
        activation_layer=layer,
        provenance=decode_provenance_defaults,
    )

    preserved_verdict = _existing_verdict(output_path)
    artifact = ScenarioArtifact(
        scenario_id=scenario_id,
        phase=phase,
        label=label,
        agent_output=agent_output,
        nla_decode=nla_decode,
        verdict=None,  # filled later by precompute_verdicts.py
    )
    payload = artifact.model_dump(mode="json")
    if preserved_verdict is not None:
        payload["verdict"] = preserved_verdict
        verdict_status = "preserved"
    else:
        verdict_status = "null (run precompute_verdicts.py)"

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"[ok] {scenario_id}/{phase} -> {output_path.name} (verdict: {verdict_status})")
    return output_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo-data", default="demo_data", type=Path)
    ap.add_argument("--scenario", help="Restrict to a single scenario_id")
    ap.add_argument(
        "--gpu-endpoint",
        default="http://193.222.57.16:44016",
        help="Recorded in DecodeProvenance for audit trail",
    )
    args = ap.parse_args()

    demo_data: Path = args.demo_data.resolve()
    if not demo_data.exists():
        raise SystemExit(f"demo_data dir not found: {demo_data}")
    (demo_data / "_raw_decodes").mkdir(exist_ok=True)
    (demo_data / "_prompts").mkdir(exist_ok=True)

    # Defaults for decode provenance — matches the curls used to produce the
    # raw_decodes. If you change /decode parameters in the future, bump these.
    defaults = DecodeProvenance(
        qwen_base_model="Qwen/Qwen2.5-7B-Instruct",
        nla_actor_repo="kitft/nla-qwen2.5-7b-L20-av",
        gpu_endpoint=args.gpu_endpoint,
        decoded_at=_utcnow(),  # crude — real time was earlier, but exact ms not preserved in raw JSON
        skip_first=10,
        av_temperature=0.7,
        av_max_new_tokens=200,
        decode_latency_ms=0,  # not preserved in raw JSON; fill manually if needed
        critic_loaded=False,
    )

    selected = [s for s in SCENARIOS if args.scenario is None or s[0] == args.scenario]
    if not selected:
        raise SystemExit(f"No scenarios match --scenario={args.scenario!r}")

    for sid, phase, raw_fn, prompt_fn, label, rationale in selected:
        build_one(demo_data, sid, phase, raw_fn, prompt_fn, label, rationale, defaults)

    print(f"\n[done] built {len(selected)} artifact(s)")


if __name__ == "__main__":
    main()
