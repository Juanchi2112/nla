"""Unit tests for ScenarioGPUClient streaming behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.gpu.base import GPUClientError
from backend.gpu.scenario import ArtifactLoader, ScenarioGPUClient


@pytest.fixture
def loader(scenario_dir: Path) -> ArtifactLoader:
    return ArtifactLoader(scenario_dir / "manifest.yaml")


@pytest.fixture
def client(loader: ArtifactLoader) -> ScenarioGPUClient:
    return ScenarioGPUClient(loader, replay_interval=0.0)


async def test_stream_phase_yields_one_item_per_row(client: ScenarioGPUClient):
    items = [item async for item in client.stream_phase("honest", "original", sniff_every_k=4)]
    # honest fixture has 6 rows
    assert len(items) == 6
    # steps are 0..5
    assert [it.step for it in items] == list(range(6))


async def test_stream_phase_emits_monologue_every_k_rows(client: ScenarioGPUClient):
    """With sniff_every_k=2, monologue should be present at steps 0, 2, 4 and absent at 1, 3, 5."""
    items = [item async for item in client.stream_phase("honest", "original", sniff_every_k=2)]
    monologue_present = [it.monologue is not None for it in items]
    assert monologue_present == [True, False, True, False, True, False]


async def test_stream_phase_unknown_scenario_raises(client: ScenarioGPUClient):
    with pytest.raises(GPUClientError, match="No artifact"):
        async for _ in client.stream_phase("nope", "original", sniff_every_k=4):
            pass


async def test_stream_direct_not_implemented(client: ScenarioGPUClient):
    """Calling .stream() directly should raise — scenario mode goes through stream_phase()."""
    with pytest.raises(NotImplementedError, match="stream_phase"):
        async for _ in client.stream(prompt="x", sniff_every_k=4, max_new_tokens=10):
            pass
