"""End-to-end audit CLI.

    uv run python -m audit.run --rules audit/rules.yaml --n 5 --out audit/report.md

Stages:
  1. Load rules.yaml.
  2. Generate N adversarial probes per rule (Claude, tool use).
  3. Run each probe through the live backend (SSE).
  4. Judge each run against its rule (output-only + thought-stream-only).
  5. Aggregate and write markdown + JSON.

Probes are run sequentially with a progress line per probe. Failures
on individual probes are recorded in the artifact's `error` field and
the audit continues; they show up in the report as missing verdicts.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import yaml
from anthropic import Anthropic

from .generator import generate_probes
from .judge import judge_run
from .report import build_report, render_markdown
from .runner import run_probe
from .schemas import AuditVerdict, Probe, RulesFile, RunArtifact

log = logging.getLogger("audit.run")


def _load_rules(path: Path) -> RulesFile:
    with open(path) as f:
        return RulesFile.model_validate(yaml.safe_load(f))


async def _run_one(
    probe: Probe,
    system_prompt: str,
    runs_dir: Path,
) -> RunArtifact:
    artifact = await run_probe(
        probe_id=probe.probe_id,
        rule_id=probe.rule_id,
        system_prompt=system_prompt,
        user_message=probe.user_message,
    )
    (runs_dir / f"{probe.probe_id}.json").write_text(artifact.model_dump_json(indent=2))
    return artifact


async def amain(args: argparse.Namespace) -> int:
    rules_file = _load_rules(Path(args.rules))
    deployment = rules_file.deployment
    rules = rules_file.rules

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(exist_ok=True)

    client = Anthropic()

    # --- 1. Generate probes (or load from cache if --probes-cache exists) -----
    cache_path = out_dir / "probes.json"
    probes: list[Probe] = []
    if args.use_cache and cache_path.exists():
        log.info("loading cached probes from %s", cache_path)
        probes = [Probe.model_validate(p) for p in json.loads(cache_path.read_text())]
    else:
        for r in rules:
            print(f"[gen] {r.id} ...", flush=True)
            probes.extend(generate_probes(r, deployment, args.n, client=client))
        cache_path.write_text(json.dumps([p.model_dump() for p in probes], indent=2))
        print(f"[gen] wrote {len(probes)} probes to {cache_path}")

    # --- 2. Run each probe through the backend -------------------------------
    artifacts: list[RunArtifact] = []
    for i, p in enumerate(probes, 1):
        print(f"[run {i}/{len(probes)}] {p.probe_id} ({p.rule_id}) ...", flush=True)
        try:
            art = await _run_one(p, deployment.system_prompt, runs_dir)
            tag = (
                f"err: {art.error}"
                if art.error
                else f"{len(art.output_text)}c output, {len(art.traces)} traces"
            )
            print(f"           -> {tag}", flush=True)
            artifacts.append(art)
        except Exception as e:
            log.exception("run failed for %s", p.probe_id)
            print(f"           -> RUNNER EXCEPTION: {e}", flush=True)

    # --- 3. Judge each run --------------------------------------------------
    rule_by_id = {r.id: r for r in rules}
    probe_by_id = {p.probe_id: p for p in probes}
    verdicts: list[AuditVerdict] = []
    for i, art in enumerate(artifacts, 1):
        if art.error or not art.output_text:
            print(
                f"[judge {i}/{len(artifacts)}] {art.probe_id} skipped (error or empty)", flush=True
            )
            continue
        rule = rule_by_id[art.rule_id]
        probe = probe_by_id[art.probe_id]
        try:
            v = judge_run(rule, probe.user_message, art, client=client)
            verdicts.append(v)
            print(
                f"[judge {i}/{len(artifacts)}] {art.probe_id}: {v.status}"
                f" (internal={v.internal_state}, conf={v.internal_confidence})",
                flush=True,
            )
        except Exception as e:
            log.exception("judge failed for %s", art.probe_id)
            print(f"[judge {i}/{len(artifacts)}] {art.probe_id}: JUDGE EXCEPTION: {e}", flush=True)

    # --- 4. Build & render report ------------------------------------------
    report = build_report(deployment, rules, verdicts)
    md_path = out_dir / "report.md"
    json_path = out_dir / "report.json"
    probes_by_id = {p.probe_id: p.user_message for p in probes}
    md_path.write_text(render_markdown(report, probes_by_id=probes_by_id))
    json_path.write_text(report.model_dump_json(indent=2))
    print(f"\nReport written to:\n  {md_path}\n  {json_path}")

    return 0


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    p = argparse.ArgumentParser()
    p.add_argument("--rules", default="audit/rules.yaml")
    p.add_argument("--n", type=int, default=5, help="probes per rule")
    p.add_argument("--out-dir", default="audit", help="where probes.json, runs/, report.md land")
    p.add_argument("--use-cache", action="store_true", help="reuse audit/probes.json if present")
    args = p.parse_args()
    sys.exit(asyncio.run(amain(args)))


if __name__ == "__main__":
    main()
