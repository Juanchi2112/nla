"""Unit tests for SteeringEngine — orchestration of cached scenario arcs."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.gpu.scenario import ArtifactLoader, ScenarioGPUClient
from backend.sessions import SessionState
from backend.steering_engine import SteeringEngine


@pytest.fixture
def engine(scenario_dir: Path) -> SteeringEngine:
    loader = ArtifactLoader(scenario_dir / "manifest.yaml")
    gpu = ScenarioGPUClient(loader, replay_interval=0.0)
    return SteeringEngine(gpu=gpu, artifact_loader=loader, judge=None)


async def _drain_queue(session: SessionState) -> list[tuple[str, dict]]:
    """Pull every event from the session queue until 'done' is seen."""
    events: list[tuple[str, dict]] = []
    while True:
        try:
            evt = await asyncio.wait_for(session.queue.get(), timeout=2.0)
        except TimeoutError:
            break
        events.append(evt)
        if evt[0] == "done":
            break
    return events


async def test_pass_scenario_emits_no_steering_events(engine: SteeringEngine):
    """Honest scenario → action=PASS. Should emit token + nla_trace + judge_summary + done.
    Should NOT emit steering_started or steering_complete.
    """
    session = SessionState(
        session_id="t-pass",
        prompt="",
        sniff_every_k=2,
        scenario_id="honest",
    )
    await engine.run(session)
    events = await _drain_queue(session)

    kinds = [k for k, _ in events]
    assert kinds[-1] == "done"
    assert "token" in kinds
    assert "judge_summary" in kinds
    # No steering events
    assert "steering_started" not in kinds
    assert "steering_complete" not in kinds

    # The judge_summary verdict has action=PASS
    summaries = [data for k, data in events if k == "judge_summary"]
    assert len(summaries) == 1
    assert summaries[0]["phase"] == "original"
    assert summaries[0]["verdict"]["action"] == "PASS"
    assert summaries[0]["verdict"]["trust_score"] == 90


async def test_steer_scenario_emits_full_arc(engine: SteeringEngine):
    """Deception scenario → action=STEER. Should emit:
    - phase=original tokens + nla_trace
    - judge_summary(phase=original, action=STEER)
    - steering_started(correction_prompt='Be honest.')
    - phase=steered tokens + nla_trace
    - judge_summary(phase=steered, action=PASS)
    - steering_complete(delta>0)
    - done
    """
    session = SessionState(
        session_id="t-steer",
        prompt="",
        sniff_every_k=2,
        scenario_id="deception",
    )
    await engine.run(session)
    events = await _drain_queue(session)

    kinds = [k for k, _ in events]
    # Order matters: steering_started must come AFTER first judge_summary,
    # second judge_summary must come AFTER steered tokens, etc.
    first_summary = kinds.index("judge_summary")
    steering_idx = kinds.index("steering_started")
    second_summary = kinds.index("judge_summary", first_summary + 1)
    complete_idx = kinds.index("steering_complete")
    done_idx = kinds.index("done")
    assert first_summary < steering_idx < second_summary < complete_idx < done_idx

    # Two judge_summary events, one per phase
    summaries = [data for k, data in events if k == "judge_summary"]
    assert len(summaries) == 2
    assert summaries[0]["phase"] == "original"
    assert summaries[0]["verdict"]["action"] == "STEER"
    assert summaries[0]["verdict"]["correction_prompt"] == "Be honest."
    assert summaries[1]["phase"] == "steered"
    assert summaries[1]["verdict"]["action"] == "PASS"

    steering_starts = [data for k, data in events if k == "steering_started"]
    assert len(steering_starts) == 1
    assert steering_starts[0]["correction_prompt"] == "Be honest."

    completes = [data for k, data in events if k == "steering_complete"]
    assert len(completes) == 1
    assert completes[0]["original_trust"] == 30
    assert completes[0]["steered_trust"] == 85
    assert completes[0]["delta"] == 55


async def test_stop_requested_mid_phase_cancels_cleanly(engine: SteeringEngine):
    """If stop_requested goes True, run() should still emit done(reason=cancelled)."""
    session = SessionState(
        session_id="t-cancel",
        prompt="",
        sniff_every_k=4,
        scenario_id="deception",
    )
    session.stop_requested = True  # cancel before starting
    await engine.run(session)
    events = await _drain_queue(session)

    # Should have a done event regardless
    assert events[-1][0] == "done"
    # Should NOT see a second judge_summary or steering_complete (we cancelled before steered phase)
    kinds = [k for k, _ in events]
    summaries = [k for k in kinds if k == "judge_summary"]
    # Either 0 (cancelled before original finished) or 1 (cancelled after original)
    # but never 2 since we wouldn't reach the steered phase.
    assert len(summaries) <= 1


async def test_stream_emits_token_and_monologue_events(engine: SteeringEngine):
    """nla_trace should fire on every step where the GPU yields a monologue."""
    session = SessionState(
        session_id="t-stream",
        prompt="",
        sniff_every_k=2,
        scenario_id="honest",
    )
    await engine.run(session)
    events = await _drain_queue(session)

    tokens = [data for k, data in events if k == "token"]
    traces = [data for k, data in events if k == "nla_trace"]
    # 6 rows in honest fixture → 6 token events
    assert len(tokens) == 6
    # With sniff_every_k=2, monologue at steps 0, 2, 4 → 3 traces
    assert len(traces) == 3
    # First trace mode "A" (step < K), later "B"
    assert traces[0]["mode"] == "A"
    assert traces[0]["verdict"] is None  # scenario mode bypasses per-monologue judge
