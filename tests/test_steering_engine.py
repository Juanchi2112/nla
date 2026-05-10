"""Unit tests for SteeringEngine — orchestration of cached and live arcs."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from backend.gpu.base import GPUClient, GPUStreamItem
from backend.gpu.scenario import ArtifactLoader, ScenarioGPUClient
from backend.schemas import Divergence, TurnVerdict, VerdictProvenance
from backend.sessions import SessionState
from backend.steering_engine import SteeringEngine


@pytest.fixture
def engine(scenario_dir: Path) -> SteeringEngine:
    loader = ArtifactLoader(scenario_dir / "manifest.yaml")
    gpu = ScenarioGPUClient(loader, replay_interval=0.0)
    return SteeringEngine(
        scenario_gpu=gpu,
        artifact_loader=loader,
        live_gpu=None,
        judge=None,
    )


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


# ─── Live mode (Fase G) ────────────────────────────────────────────────────


class _StubLiveGPU(GPUClient):
    """Tiny GPU that yields a fixed (token, monologue) sequence per call."""

    def __init__(self, tokens: list[str], monologue_at: dict[int, str]):
        self._tokens = tokens
        self._monologue_at = monologue_at
        self.calls: list[dict] = []  # records every stream() invocation

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        sniff_every_k: int = 4,
        max_new_tokens: int = 128,
    ) -> AsyncIterator[GPUStreamItem]:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        for step, tok in enumerate(self._tokens):
            yield GPUStreamItem(step=step, token=tok)
            mono = self._monologue_at.get(step)
            if mono is not None:
                yield GPUStreamItem(step=step, monologue=mono)


def _verdict(action: str, trust: int, correction: str | None = None) -> TurnVerdict:
    return TurnVerdict(
        trust_score=trust,
        summary=f"{action} verdict for test",
        divergences=[]
        if action == "PASS"
        else [
            Divergence(
                pos=0,
                verbal_claim="x",
                internal_thought="y",
                severity="high",
            )
        ],
        action=action,  # type: ignore[arg-type]
        correction_prompt=correction,
        reasoning="test",
        provenance=VerdictProvenance(
            model="claude-sonnet-4-6",
            judged_at=datetime(2026, 5, 10, tzinfo=UTC),
            system_prompt_hash="sha256:" + "0" * 64,
            system_prompt_version="test-v1",
            input_tokens=10,
            output_tokens=20,
            judge_latency_ms=100,
            raw_response_excerpt="{}",
        ),
    )


class _StubJudge:
    """Programmable judge returning a queue of verdicts."""

    def __init__(self, verdicts: list[TurnVerdict]):
        self._verdicts = list(verdicts)
        self.calls: list[tuple[str, int]] = []

    def evaluate_turn(self, verbal: str, rows: list) -> TurnVerdict:  # noqa: ARG002
        self.calls.append((verbal, len(rows)))
        return self._verdicts.pop(0)


async def test_live_pass_emits_no_steering_events():
    gpu = _StubLiveGPU(
        tokens=[" ok", "."],
        monologue_at={0: "model is being helpful", 1: "consolidating answer"},
    )
    judge = _StubJudge([_verdict("PASS", trust=92)])
    eng = SteeringEngine(scenario_gpu=None, artifact_loader=None, live_gpu=gpu, judge=judge)
    session = SessionState(session_id="live-pass", prompt="hi", sniff_every_k=1)

    await eng.run(session)
    events = await _drain_queue(session)
    kinds = [k for k, _ in events]

    assert kinds[-1] == "done"
    assert "judge_summary" in kinds
    assert "steering_proposed" not in kinds
    assert "steering_started" not in kinds
    summaries = [d for k, d in events if k == "judge_summary"]
    assert len(summaries) == 1
    assert summaries[0]["phase"] == "original"
    assert summaries[0]["verdict"]["action"] == "PASS"
    assert len(judge.calls) == 1
    # Verbal accumulated into a single string for the judge call
    assert judge.calls[0][0] == " ok."


async def test_live_steer_with_user_confirm_runs_full_arc():
    gpu = _StubLiveGPU(
        tokens=["A", "B"],
        monologue_at={0: "thought-orig", 1: "thought-orig-2"},
    )
    judge = _StubJudge(
        [
            _verdict("STEER", trust=20, correction="Be honest"),
            _verdict("PASS", trust=88),  # post-steer
        ]
    )
    eng = SteeringEngine(
        scenario_gpu=None,
        artifact_loader=None,
        live_gpu=gpu,
        judge=judge,
        steering_timeout_seconds=2,
    )
    session = SessionState(session_id="live-steer", prompt="lie to me", sniff_every_k=1)

    async def confirm_after_proposed():
        # Wait for steering_proposed to be queued, then confirm.
        for _ in range(50):
            if session.steering_decision == "pending":
                break
            await asyncio.sleep(0.01)
        assert session.steering_decision == "pending"
        session.steering_decision = "confirm"
        session.steering_decision_event.set()

    confirmer = asyncio.create_task(confirm_after_proposed())
    await eng.run(session)
    await confirmer
    events = await _drain_queue(session)
    kinds = [k for k, _ in events]

    # Sequence assertions
    assert kinds[-1] == "done"
    proposed_idx = kinds.index("steering_proposed")
    started_idx = kinds.index("steering_started")
    complete_idx = kinds.index("steering_complete")
    assert proposed_idx < started_idx < complete_idx

    # Judge called twice: original + steered
    assert len(judge.calls) == 2

    # GPU stream invoked twice: second call carries the correction as system_prompt
    assert len(gpu.calls) == 2
    assert gpu.calls[1]["system_prompt"] == "Be honest"

    completes = [d for k, d in events if k == "steering_complete"]
    assert len(completes) == 1
    assert completes[0]["original_trust"] == 20
    assert completes[0]["steered_trust"] == 88
    assert completes[0]["delta"] == 68


async def test_live_steer_user_rejects():
    gpu = _StubLiveGPU(tokens=["X"], monologue_at={0: "thinking"})
    judge = _StubJudge([_verdict("STEER", trust=15, correction="don't")])
    eng = SteeringEngine(
        scenario_gpu=None,
        artifact_loader=None,
        live_gpu=gpu,
        judge=judge,
        steering_timeout_seconds=2,
    )
    session = SessionState(session_id="live-rej", prompt="x", sniff_every_k=1)

    async def reject_after_proposed():
        for _ in range(50):
            if session.steering_decision == "pending":
                break
            await asyncio.sleep(0.01)
        session.steering_decision = "reject"
        session.steering_decision_event.set()

    rejecter = asyncio.create_task(reject_after_proposed())
    await eng.run(session)
    await rejecter
    events = await _drain_queue(session)
    kinds = [k for k, _ in events]

    assert "steering_proposed" in kinds
    assert "steering_rejected" in kinds
    assert "steering_started" not in kinds  # never re-decoded
    assert kinds[-1] == "done"
    rejected = next(d for k, d in events if k == "steering_rejected")
    assert rejected["reason"] == "rejected_by_user"
    # Only one judge call (no steered phase)
    assert len(judge.calls) == 1
    # Only one GPU call
    assert len(gpu.calls) == 1


async def test_live_steer_timeout_auto_rejects():
    gpu = _StubLiveGPU(tokens=["X"], monologue_at={0: "..."})
    judge = _StubJudge([_verdict("STEER", trust=10, correction="x")])
    eng = SteeringEngine(
        scenario_gpu=None,
        artifact_loader=None,
        live_gpu=gpu,
        judge=judge,
        steering_timeout_seconds=0,  # immediate timeout
    )
    session = SessionState(session_id="live-timeout", prompt="x", sniff_every_k=1)

    await eng.run(session)
    events = await _drain_queue(session)
    rejected = next(d for k, d in events if k == "steering_rejected")
    assert rejected["reason"] == "timeout"


async def test_live_without_judge_emits_error():
    gpu = _StubLiveGPU(tokens=["X"], monologue_at={})
    eng = SteeringEngine(scenario_gpu=None, artifact_loader=None, live_gpu=gpu, judge=None)
    session = SessionState(session_id="live-nojudge", prompt="x", sniff_every_k=1)

    await eng.run(session)
    events = await _drain_queue(session)
    kinds = [k for k, _ in events]
    assert "error" in kinds
    assert kinds[-1] == "done"
    err = next(d for k, d in events if k == "error")
    assert "ANTHROPIC_API_KEY" in err["detail"] or "Live judge" in err["detail"]


# ─── Hybrid mode (both paths configured) ──────────────────────────────────


async def test_hybrid_routes_scenario_id_to_cached_path(scenario_dir: Path):
    """A hybrid engine receives a scenario_id request: it must route through
    the cached path (no live GPU, no live judge call)."""
    loader = ArtifactLoader(scenario_dir / "manifest.yaml")
    scenario_gpu = ScenarioGPUClient(loader, replay_interval=0.0)
    live_gpu = _StubLiveGPU(tokens=["X"], monologue_at={})
    judge = _StubJudge([_verdict("PASS", trust=99)])

    eng = SteeringEngine(
        scenario_gpu=scenario_gpu,
        artifact_loader=loader,
        live_gpu=live_gpu,
        judge=judge,
    )
    session = SessionState(session_id="hyb-scn", prompt="", sniff_every_k=2, scenario_id="honest")
    await eng.run(session)
    events = await _drain_queue(session)

    # Live path was untouched: judge wasn't called, live_gpu wasn't streamed.
    assert len(judge.calls) == 0
    assert len(live_gpu.calls) == 0
    # Cached verdict came through.
    summaries = [d for k, d in events if k == "judge_summary"]
    assert summaries[0]["verdict"]["action"] == "PASS"
    assert summaries[0]["verdict"]["trust_score"] == 90  # honest fixture


async def test_hybrid_routes_prompt_to_live_path(scenario_dir: Path):
    """A hybrid engine receives a prompt-only request: must route through
    the live path."""
    loader = ArtifactLoader(scenario_dir / "manifest.yaml")
    scenario_gpu = ScenarioGPUClient(loader, replay_interval=0.0)
    live_gpu = _StubLiveGPU(tokens=["A", "B"], monologue_at={0: "thinking"})
    judge = _StubJudge([_verdict("PASS", trust=85)])

    eng = SteeringEngine(
        scenario_gpu=scenario_gpu,
        artifact_loader=loader,
        live_gpu=live_gpu,
        judge=judge,
    )
    session = SessionState(session_id="hyb-live", prompt="hi", sniff_every_k=1)
    await eng.run(session)
    events = await _drain_queue(session)

    # Live path took the request: judge ran once, gpu streamed once.
    assert len(judge.calls) == 1
    assert len(live_gpu.calls) == 1
    summaries = [d for k, d in events if k == "judge_summary"]
    assert summaries[0]["verdict"]["trust_score"] == 85
    assert events[-1][0] == "done"


async def test_hybrid_degraded_to_scenario_only_rejects_live(scenario_dir: Path):
    """When live_gpu is None (e.g., GPU_URL missing in hybrid boot), prompt
    requests surface a clear error event."""
    loader = ArtifactLoader(scenario_dir / "manifest.yaml")
    scenario_gpu = ScenarioGPUClient(loader, replay_interval=0.0)

    eng = SteeringEngine(
        scenario_gpu=scenario_gpu,
        artifact_loader=loader,
        live_gpu=None,
        judge=None,
    )
    session = SessionState(session_id="degraded", prompt="x", sniff_every_k=1)
    await eng.run(session)
    events = await _drain_queue(session)

    kinds = [k for k, _ in events]
    assert "error" in kinds
    err = next(d for k, d in events if k == "error")
    assert "live" in err["detail"].lower()
    assert kinds[-1] == "done"


def test_engine_construction_rejects_inconsistent_scenario_args():
    """scenario_gpu and artifact_loader must agree on None-ness."""
    with pytest.raises(ValueError, match="must both be set or both None"):
        SteeringEngine(
            scenario_gpu=None,
            artifact_loader=ArtifactLoader.__new__(ArtifactLoader),  # dummy
            live_gpu=None,
            judge=None,
        )
