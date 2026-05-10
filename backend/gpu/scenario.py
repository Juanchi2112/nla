"""Scenario GPU client: replays cached scenario artifacts as if from a live GPU.

When `ORCHESTRATOR_GPU=scenario`, the backend uses these classes instead of
hitting the real /decode endpoint. The wire shape (GPUStreamItem) stays
identical to DecoderEndpointClient so downstream code (orchestrator,
SteeringEngine) doesn't care where rows come from.

Two pieces:
  - ArtifactLoader: reads manifest.yaml at boot, validates every referenced
    artifact JSON parses as ScenarioArtifact and has a non-null verdict.
    Fails fast with a concrete error message if anything is wrong.
  - ScenarioGPUClient: implements GPUClient. Its `stream_phase()` reads
    the cached artifact and yields GPUStreamItem on the same `replay_interval`
    timer that DecoderEndpointClient uses, preserving the dramatic effect.

The plain GPUClient.stream() entry point is intentionally not implemented —
scenario mode is driven through SteeringEngine which knows about phases.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

import yaml

from ..schemas import ScenarioArtifact
from .base import GPUClient, GPUClientError, GPUStreamItem

log = logging.getLogger(__name__)


class ArtifactLoader:
    """Loads + validates manifest and every artifact at startup.

    Raises GPUClientError on any inconsistency so the lifespan crashes
    with a readable error in Railway logs (rather than a runtime KeyError
    when a user actually requests a scenario).
    """

    def __init__(self, manifest_path: Path):
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            raise GPUClientError(f"Manifest not found: {manifest_path}")
        with open(manifest_path) as f:
            data = yaml.safe_load(f) or {}
        self.root = manifest_path.parent
        self._manifest: dict = data.get("scenarios") or {}
        if not self._manifest:
            raise GPUClientError(f"Manifest {manifest_path} has no scenarios")

        self._artifacts: dict[tuple[str, str], ScenarioArtifact] = {}
        errors: list[str] = []
        for sid, scn in self._manifest.items():
            phases = (scn or {}).get("phases") or {}
            if not phases:
                errors.append(f"{sid}: scenario has no phases")
                continue
            for phase, info in phases.items():
                if phase not in ("original", "steered"):
                    errors.append(f"{sid}/{phase}: unknown phase (expected original|steered)")
                    continue
                fname = (info or {}).get("artifact_file")
                if not fname:
                    errors.append(f"{sid}/{phase}: missing artifact_file in manifest")
                    continue
                p = self.root / fname
                if not p.exists():
                    errors.append(f"{sid}/{phase}: missing file {p}")
                    continue
                try:
                    with open(p) as f:
                        artifact = ScenarioArtifact(**json.load(f))
                except Exception as e:
                    errors.append(f"{sid}/{phase}: parse error in {p.name}: {e}")
                    continue
                if artifact.verdict is None:
                    errors.append(
                        f"{sid}/{phase}: artifact has no verdict block "
                        "(run scripts/precompute_verdicts.py)"
                    )
                    continue
                # Sanity: scenario_id and phase inside the artifact must match
                # the manifest entry; otherwise audit trails get confusing.
                if artifact.scenario_id != sid:
                    errors.append(
                        f"{sid}/{phase}: artifact scenario_id={artifact.scenario_id!r} "
                        f"does not match manifest key {sid!r}"
                    )
                    continue
                if artifact.phase != phase:
                    errors.append(
                        f"{sid}/{phase}: artifact phase={artifact.phase!r} "
                        f"does not match manifest entry {phase!r}"
                    )
                    continue
                self._artifacts[(sid, phase)] = artifact

        if errors:
            raise GPUClientError(
                "Scenario manifest validation failed:\n  - " + "\n  - ".join(errors)
            )

        log.info(
            "ArtifactLoader: %d artifacts across %d scenarios",
            len(self._artifacts),
            len(self._manifest),
        )

    @property
    def scenarios(self) -> list[str]:
        return list(self._manifest.keys())

    def get_label(self, scenario_id: str) -> str:
        scn = self._manifest.get(scenario_id)
        if scn is None:
            raise GPUClientError(f"Unknown scenario_id={scenario_id!r}")
        return scn.get("label") or scenario_id

    def get_artifact(self, scenario_id: str, phase: str) -> ScenarioArtifact:
        try:
            return self._artifacts[(scenario_id, phase)]
        except KeyError:
            raise GPUClientError(
                f"No artifact for scenario_id={scenario_id!r} phase={phase!r}. "
                f"Available: {sorted(self._artifacts.keys())}"
            ) from None

    def has_phase(self, scenario_id: str, phase: str) -> bool:
        return (scenario_id, phase) in self._artifacts


class ScenarioGPUClient(GPUClient):
    """Streams cached artifact rows on a timer, mimicking DecoderEndpointClient."""

    def __init__(self, loader: ArtifactLoader, *, replay_interval: float = 0.05):
        self.loader = loader
        self._replay_interval = replay_interval

    async def aclose(self) -> None:
        return None

    async def stream(
        self,
        prompt: str,
        *,
        sniff_every_k: int,
        max_new_tokens: int,
    ) -> AsyncIterator[GPUStreamItem]:
        # Scenario mode goes through SteeringEngine.run() → stream_phase().
        # Calling .stream() directly is a misuse; signal it loudly.
        raise NotImplementedError(
            "ScenarioGPUClient.stream() is not implemented. "
            "Use SteeringEngine which calls stream_phase() with a scenario_id."
        )
        # Make this a generator (so the function signature stays AsyncIterator):
        if False:  # noqa: SIM108
            yield  # type: ignore[unreachable]

    async def stream_phase(
        self,
        scenario_id: str,
        phase: str,
        *,
        sniff_every_k: int,
    ) -> AsyncIterator[GPUStreamItem]:
        artifact = self.loader.get_artifact(scenario_id, phase)
        rows = artifact.nla_decode.rows
        if not rows:
            raise GPUClientError(f"{scenario_id}/{phase}: artifact has 0 rows")

        for i, row in enumerate(rows):
            token_text = self._extract_new_chunk(rows, i)
            monologue = row.decode if (i % sniff_every_k == 0) else None
            yield GPUStreamItem(step=i, token=token_text, monologue=monologue)
            await asyncio.sleep(self._replay_interval)

    @staticmethod
    def _extract_new_chunk(rows, i: int) -> str:
        cur = rows[i].context or ""
        prev = rows[i - 1].context if i > 0 else ""
        prev = prev or ""
        return cur[len(prev) :] if cur.startswith(prev) else cur
