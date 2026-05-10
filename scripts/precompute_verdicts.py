"""Run ClaudeAgentJudge over every scenario in the manifest, write verdict block in-place.

Reads each artifact JSON, calls Claude with the system prompt loaded from
demo_data/_system_prompts/<version>.txt, and writes the resulting verdict
(plus full provenance metadata) directly into the artifact's `verdict`
field.

The artifact files are committed to git afterwards — the git diff is the
audit trail. DO NOT edit verdict blocks by hand: if a verdict reads wrong,
either iterate the system prompt (bump version, e.g. v1 -> v2) and re-run
with --force, or change the agent output to make the desired behavior
obvious.

Usage:
    ANTHROPIC_API_KEY=sk-ant-... uv run python scripts/precompute_verdicts.py
    ... --scenario deception
    ... --force                # re-run even if a verdict is already present
    ... --system-prompt-version v2-2026-05-10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.judge.claude_agent_judge import ClaudeAgentJudge, ClaudeAgentJudgeError  # noqa: E402
from backend.schemas import DecodeRow, ScenarioArtifact  # noqa: E402

# Load .env BEFORE main() reads ANTHROPIC_API_KEY. Platform env vars (CI/Docker)
# take precedence — load_dotenv does not override existing keys by default.
load_dotenv()


def _load_system_prompt(demo_data: Path, version: str) -> str:
    p = demo_data / "_system_prompts" / f"{version}.txt"
    if not p.exists():
        raise SystemExit(f"system prompt file not found: {p}")
    return p.read_text()


def _enumerate_phases(manifest_path: Path) -> list[tuple[str, str, Path]]:
    with open(manifest_path) as f:
        data = yaml.safe_load(f)
    out: list[tuple[str, str, Path]] = []
    root = manifest_path.parent
    for sid, scn in data["scenarios"].items():
        for phase, info in scn.get("phases", {}).items():
            out.append((sid, phase, root / info["artifact_file"]))
    return out


def _judge_one(judge: ClaudeAgentJudge, artifact_path: Path, force: bool) -> bool:
    """Returns True if the artifact was updated."""
    with open(artifact_path) as f:
        payload = json.load(f)
    artifact = ScenarioArtifact(**payload)

    if artifact.verdict is not None and not force:
        print(f"[skip] {artifact_path.name}: verdict present (use --force to overwrite)")
        return False

    rows: list[DecodeRow] = artifact.nla_decode.rows
    print(
        f"[judge] {artifact_path.name}: {len(rows)} rows, "
        f"{artifact.scenario_id}/{artifact.phase}..."
    )
    try:
        verdict = judge.evaluate_turn(artifact.agent_output.text, rows)
    except ClaudeAgentJudgeError as e:
        print(f"[FAIL] {artifact_path.name}: {e}", file=sys.stderr)
        return False

    payload["verdict"] = verdict.model_dump(mode="json")
    with open(artifact_path, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(
        f"[ok]   {artifact_path.name}: trust={verdict.trust_score} "
        f"action={verdict.action} divergences={len(verdict.divergences)} "
        f"latency={verdict.provenance.judge_latency_ms}ms"
    )
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo-data", default="demo_data", type=Path)
    ap.add_argument("--manifest", default="manifest.yaml")
    ap.add_argument("--scenario", help="Restrict to a single scenario_id")
    ap.add_argument("--force", action="store_true", help="Overwrite existing verdicts")
    ap.add_argument(
        "--system-prompt-version",
        default="v2-2026-05-10",
        help="Loads demo_data/_system_prompts/<version>.txt",
    )
    ap.add_argument("--model", default="claude-sonnet-4-6")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set in environment")

    demo_data: Path = args.demo_data.resolve()
    manifest_path = demo_data / args.manifest
    if not manifest_path.exists():
        raise SystemExit(f"manifest not found: {manifest_path}")

    system_prompt = _load_system_prompt(demo_data, args.system_prompt_version)
    judge = ClaudeAgentJudge(
        system_prompt=system_prompt,
        system_prompt_version=args.system_prompt_version,
        model=args.model,
    )

    phases = _enumerate_phases(manifest_path)
    if args.scenario:
        phases = [p for p in phases if p[0] == args.scenario]
        if not phases:
            raise SystemExit(f"no phases match --scenario={args.scenario!r}")

    print(
        f"[setup] manifest={manifest_path.name} model={args.model} "
        f"prompt_version={args.system_prompt_version} prompt_hash={judge._system_prompt_hash[:23]}..."
    )

    updated = 0
    for sid, phase, path in phases:
        if not path.exists():
            print(f"[FAIL] {sid}/{phase}: artifact missing at {path}", file=sys.stderr)
            continue
        if _judge_one(judge, path, force=args.force):
            updated += 1

    print(f"\n[done] updated {updated}/{len(phases)} artifact(s)")


if __name__ == "__main__":
    main()
