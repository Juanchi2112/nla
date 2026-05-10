"""Re-run the audit judge on cached RunArtifacts in audit/runs/.

Useful for iterating on the judge prompt without burning GPU time.
Reuses audit/probes.json and audit/runs/*.json; produces a fresh
audit/report.md and audit/report.json.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import yaml
from anthropic import Anthropic

from .judge import judge_run
from .report import build_report, render_markdown
from .schemas import AuditVerdict, Probe, RulesFile, RunArtifact

log = logging.getLogger("audit.rejudge")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("audit")
    rules_path = out_dir / "rules.yaml"
    probes_path = out_dir / "probes.json"
    runs_dir = out_dir / "runs"

    rules_file = RulesFile.model_validate(yaml.safe_load(rules_path.read_text()))
    rules = rules_file.rules
    deployment = rules_file.deployment
    rule_by_id = {r.id: r for r in rules}

    probes = [Probe.model_validate(p) for p in json.loads(probes_path.read_text())]
    probe_by_id = {p.probe_id: p for p in probes}

    artifacts: list[RunArtifact] = []
    for f in sorted(runs_dir.glob("*.json")):
        artifacts.append(RunArtifact.model_validate_json(f.read_text()))

    print(f"Re-judging {len(artifacts)} cached runs from {runs_dir} ...")
    client = Anthropic()
    verdicts: list[AuditVerdict] = []
    for i, art in enumerate(artifacts, 1):
        if art.error or not art.output_text:
            print(f"[{i}/{len(artifacts)}] {art.probe_id}: skipped")
            continue
        rule = rule_by_id[art.rule_id]
        probe = probe_by_id[art.probe_id]
        try:
            v = judge_run(rule, probe.user_message, art, client=client)
            verdicts.append(v)
            print(
                f"[{i}/{len(artifacts)}] {art.probe_id}: {v.status}"
                f" (internal={v.internal_state}, conf={v.internal_confidence})"
            )
        except Exception as e:
            log.exception("judge failed for %s", art.probe_id)
            print(f"[{i}/{len(artifacts)}] {art.probe_id}: JUDGE EXCEPTION {e}")

    report = build_report(deployment, rules, verdicts)
    probes_by_id = {p.probe_id: p.user_message for p in probes}
    (out_dir / "report.md").write_text(render_markdown(report, probes_by_id=probes_by_id))
    (out_dir / "report.json").write_text(report.model_dump_json(indent=2))
    print(f"\nReport written to {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
