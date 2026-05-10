"""SteeringEngine — orchestrates the full turn-level arc for both modes.

Two sources, one orchestrator:
  - Scenario mode (session.scenario_id set): replay a cached
    ScenarioArtifact end to end. The verdict is also cached, so the
    arc runs with zero live LLM calls and auto-applies the steered
    phase when verdict.action == STEER.
  - Live mode (session.scenario_id None, session.prompt set): stream
    tokens and traces from the GPU, accumulate the turn, call the
    ClaudeAgentJudge live, and — if STEER — propose a correction the
    user must confirm before the steered phase runs.

The full live-mode flow (manual-confirm + re-decode) lands in Fase G;
this commit only ships the scenario path so the rebase compiles. Live
mode currently emits an explanatory error event.
"""

from __future__ import annotations

import asyncio
import logging

from .gpu.base import GPUClient
from .gpu.scenario import ArtifactLoader
from .judge.claude_agent_judge import ClaudeAgentJudge
from .schemas import (
    DoneEvent,
    ErrorEvent,
    JudgeSummaryEvent,
    NLATraceEvent,
    SteeringCompleteEvent,
    SteeringStartedEvent,
    TokenEvent,
)
from .sessions import SessionState

log = logging.getLogger(__name__)


class SteeringEngine:
    """Drives the per-session SSE arc for both cached and live sources."""

    def __init__(
        self,
        gpu: GPUClient,
        artifact_loader: ArtifactLoader | None,
        judge: ClaudeAgentJudge | None,
    ):
        self._gpu = gpu
        self._loader = artifact_loader
        self._judge = judge

    async def run(self, session: SessionState) -> None:
        """Single entry point. Dispatches scenario vs live and owns the
        terminal done event for both branches."""
        if session.scenario_id is not None:
            if self._loader is None:
                await self._fail(
                    session,
                    "scenario_id provided but backend is not in scenario mode "
                    "(set ORCHESTRATOR_GPU=scenario)",
                )
                return
            await self._run_scenario(session)
        else:
            await self._run_live(session)

    async def _run_live(self, session: SessionState) -> None:
        # TODO Fase G: live decode + ClaudeAgentJudge + manual-confirm flow.
        # Placeholder while the unified-judge refactor lands; emits an
        # informational error so the SSE consumer terminates cleanly.
        await session.queue.put(
            (
                "error",
                ErrorEvent(
                    detail=(
                        "Live mode (custom prompt) is being rewired to use "
                        "ClaudeAgentJudge with manual-confirm steering. Use a "
                        "scenario_id for now."
                    )
                ).model_dump(),
            )
        )
        await session.queue.put(
            ("done", DoneEvent(total_tokens=0, reason="completed").model_dump())
        )

    async def _fail(self, session: SessionState, detail: str) -> None:
        await session.queue.put(("error", ErrorEvent(detail=detail).model_dump()))
        await session.queue.put(
            ("done", DoneEvent(total_tokens=0, reason="completed").model_dump())
        )

    async def _run_scenario(self, session: SessionState) -> None:
        """Drives the cached arc on session.queue. Catches GPUClientError +
        generic Exception, always emits a terminal done event."""
        from .gpu.base import GPUClientError  # local to avoid circular at module load

        sid = session.scenario_id
        if not sid or self._loader is None:
            log.error("SteeringEngine._run_scenario called without scenario_id/loader")
            return

        queue = session.queue
        reason = "completed"

        try:
            # ── Phase 1: original ──
            original = self._loader.get_artifact(sid, "original")
            await self._stream_phase(sid, "original", session)

            await queue.put(
                (
                    "judge_summary",
                    JudgeSummaryEvent(
                        phase="original",
                        verdict=original.verdict,
                    ).model_dump(mode="json"),
                )
            )

            # ── Phase 2 (conditional): steered ──
            should_steer = (
                not session.stop_requested
                and original.verdict is not None
                and original.verdict.action == "STEER"
            )
            if should_steer:
                if not self._loader.has_phase(sid, "steered"):
                    log.warning("scenario=%s action=STEER but no steered phase in manifest", sid)
                else:
                    if not original.verdict.correction_prompt:
                        log.warning("scenario=%s action=STEER but correction_prompt is empty", sid)
                    await queue.put(
                        (
                            "steering_started",
                            SteeringStartedEvent(
                                correction_prompt=original.verdict.correction_prompt or "",
                                reason=original.verdict.summary,
                            ).model_dump(mode="json"),
                        )
                    )

                    steered = self._loader.get_artifact(sid, "steered")
                    await self._stream_phase(sid, "steered", session)

                    await queue.put(
                        (
                            "judge_summary",
                            JudgeSummaryEvent(
                                phase="steered",
                                verdict=steered.verdict,
                            ).model_dump(mode="json"),
                        )
                    )

                    if steered.verdict is not None:
                        delta = steered.verdict.trust_score - original.verdict.trust_score
                        await queue.put(
                            (
                                "steering_complete",
                                SteeringCompleteEvent(
                                    original_trust=original.verdict.trust_score,
                                    steered_trust=steered.verdict.trust_score,
                                    delta=delta,
                                ).model_dump(mode="json"),
                            )
                        )

            if session.stop_requested:
                reason = "cancelled"

        except asyncio.CancelledError:
            reason = "cancelled"
            raise
        except GPUClientError as e:
            from .schemas import ErrorEvent

            await queue.put(("error", ErrorEvent(detail=str(e)).model_dump()))
        except Exception as e:
            log.exception("steering engine crashed for session=%s", session.session_id)
            from .schemas import ErrorEvent

            await queue.put(("error", ErrorEvent(detail=f"internal: {e}").model_dump()))
        finally:
            await queue.put(
                (
                    "done",
                    DoneEvent(
                        total_tokens=session.total_tokens_emitted,
                        reason=reason,
                    ).model_dump(),
                )
            )

    async def _stream_phase(self, sid: str, phase: str, session: SessionState) -> None:
        queue = session.queue
        K = session.sniff_every_k  # noqa: N806

        async for item in self._gpu.stream_phase(sid, phase, sniff_every_k=K):
            if session.stop_requested:
                return

            await queue.put(
                (
                    "token",
                    TokenEvent(step=item.step, text=item.token).model_dump(),
                )
            )
            session.total_tokens_emitted += 1

            if item.monologue is not None:
                # Per-monologue judge is bypassed in scenario mode — the
                # turn-level verdict (cached, with provenance) is the
                # source of truth. Emit verdict=None so the frontend can
                # tell scenario monologues from live ones.
                mode = "A" if item.step < K else "B"
                await queue.put(
                    (
                        "nla_trace",
                        NLATraceEvent(
                            step=item.step,
                            mode=mode,
                            monologue=item.monologue,
                            verdict=None,
                        ).model_dump(),
                    )
                )
