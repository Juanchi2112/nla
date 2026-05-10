"""SteeringEngine — orchestrates the full turn-level arc for both modes.

Two sources, one orchestrator:
  - Scenario mode (session.scenario_id set): replay a cached
    ScenarioArtifact end to end. The verdict is also cached, so the
    arc runs with zero live LLM calls and AUTO-applies the steered
    phase when verdict.action == STEER.
  - Live mode (session.scenario_id None, session.prompt set): stream
    tokens and traces from the GPU, accumulate the turn, call the
    ClaudeAgentJudge live, and — if STEER — propose a correction the
    user must MANUALLY confirm via /api/confirm-steer before the
    steered phase runs.

Manual-vs-auto steering split is by source, not by user choice: cached
scenarios are vetted offline so we trust the verdict; live data is
fresh and the user gets the final say on intervention.
"""

from __future__ import annotations

import asyncio
import logging

from .gpu.base import GPUClient
from .gpu.scenario import ArtifactLoader
from .judge.claude_agent_judge import ClaudeAgentJudge, ClaudeAgentJudgeError
from .schemas import (
    DecodeRow,
    DoneEvent,
    ErrorEvent,
    JudgeSummaryEvent,
    NLATraceEvent,
    SteeringCompleteEvent,
    SteeringProposedEvent,
    SteeringRejectedEvent,
    SteeringStartedEvent,
    TokenEvent,
)
from .sessions import SessionState

log = logging.getLogger(__name__)

# Default seconds to wait for /api/confirm-steer or /api/reject-steer before
# auto-rejecting. Overridable via constructor for tests.
DEFAULT_STEERING_TIMEOUT_SECONDS = 60


class SteeringEngine:
    """Drives the per-session SSE arc for both cached and live sources."""

    def __init__(
        self,
        gpu: GPUClient,
        artifact_loader: ArtifactLoader | None,
        judge: ClaudeAgentJudge | None,
        *,
        steering_timeout_seconds: int = DEFAULT_STEERING_TIMEOUT_SECONDS,
        max_new_tokens: int = 128,
    ):
        self._gpu = gpu
        self._loader = artifact_loader
        self._judge = judge
        self._steering_timeout_s = steering_timeout_seconds
        self._max_new_tokens = max_new_tokens

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
        """Live flow: stream + accumulate + judge + manual-confirm + (steered).

        Always emits a terminal done event via finally. Cancellation,
        ClaudeAgentJudgeError, and unexpected exceptions all map to an
        error SSE frame followed by done.
        """
        if self._judge is None:
            await self._fail(
                session,
                "Live judge unavailable (no ANTHROPIC_API_KEY or no system "
                "prompt). Live mode requires a configured ClaudeAgentJudge.",
            )
            return

        queue = session.queue
        reason = "completed"

        try:
            # ── Phase 1: stream original turn from GPU + accumulate ──
            verbal_orig, rows_orig = await self._stream_and_collect_live(
                session=session,
                prompt=session.prompt,
                system_prompt=session.system_prompt,
            )
            if session.stop_requested:
                reason = "cancelled"
                return

            verdict_orig = await self._run_judge_safely(queue, verbal_orig, rows_orig)
            if verdict_orig is None:
                return  # error already emitted

            await queue.put(
                (
                    "judge_summary",
                    JudgeSummaryEvent(phase="original", verdict=verdict_orig).model_dump(
                        mode="json"
                    ),
                )
            )

            if verdict_orig.action != "STEER":
                return

            # ── Phase 2: manual confirm flow ──
            correction = verdict_orig.correction_prompt or ""
            await queue.put(
                (
                    "steering_proposed",
                    SteeringProposedEvent(
                        correction_prompt=correction,
                        reason=verdict_orig.summary,
                        timeout_seconds=self._steering_timeout_s,
                    ).model_dump(),
                )
            )

            session.steering_decision = "pending"
            session.steering_decision_event.clear()
            timed_out = False
            try:
                await asyncio.wait_for(
                    session.steering_decision_event.wait(),
                    timeout=self._steering_timeout_s,
                )
            except TimeoutError:
                timed_out = True
                session.steering_decision = "reject"

            if session.stop_requested:
                reason = "cancelled"
                return

            if session.steering_decision != "confirm":
                await queue.put(
                    (
                        "steering_rejected",
                        SteeringRejectedEvent(
                            reason="timeout" if timed_out else "rejected_by_user"
                        ).model_dump(),
                    )
                )
                return

            # ── Phase 3: re-decode with the correction prepended ──
            await queue.put(
                (
                    "steering_started",
                    SteeringStartedEvent(
                        correction_prompt=correction, reason=verdict_orig.summary
                    ).model_dump(),
                )
            )

            steered_system = self._compose_steered_system_prompt(session.system_prompt, correction)
            verbal_steered, rows_steered = await self._stream_and_collect_live(
                session=session,
                prompt=session.prompt,
                system_prompt=steered_system,
            )
            if session.stop_requested:
                reason = "cancelled"
                return

            verdict_steered = await self._run_judge_safely(queue, verbal_steered, rows_steered)
            if verdict_steered is None:
                return

            await queue.put(
                (
                    "judge_summary",
                    JudgeSummaryEvent(phase="steered", verdict=verdict_steered).model_dump(
                        mode="json"
                    ),
                )
            )
            await queue.put(
                (
                    "steering_complete",
                    SteeringCompleteEvent(
                        original_trust=verdict_orig.trust_score,
                        steered_trust=verdict_steered.trust_score,
                        delta=verdict_steered.trust_score - verdict_orig.trust_score,
                    ).model_dump(),
                )
            )

        except asyncio.CancelledError:
            reason = "cancelled"
            raise
        except Exception as e:  # noqa: BLE001
            log.exception("live steering crashed for session=%s", session.session_id)
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

    async def _stream_and_collect_live(
        self,
        session: SessionState,
        prompt: str,
        system_prompt: str | None,
    ) -> tuple[str, list[DecodeRow]]:
        """Iterate the GPU stream, relay tokens + traces, return
        (verbal_text, rows) when the stream completes. Items may carry
        token-only, monologue-only, or both — each branch handled."""
        from .gpu.base import GPUClientError

        queue = session.queue
        verbal_buf: list[str] = []
        rows: list[DecodeRow] = []
        K = session.sniff_every_k  # noqa: N806

        try:
            async for item in self._gpu.stream(
                prompt,
                system_prompt=system_prompt,
                sniff_every_k=K,
                max_new_tokens=self._max_new_tokens,
            ):
                if session.stop_requested:
                    return "".join(verbal_buf), rows

                if item.token is not None:
                    verbal_buf.append(item.token)
                    await queue.put(
                        (
                            "token",
                            TokenEvent(step=item.step, text=item.token).model_dump(),
                        )
                    )
                    session.total_tokens_emitted += 1

                if item.monologue is not None:
                    mode = "A" if item.step < K else "B"
                    rows.append(
                        DecodeRow(
                            pos=item.step,
                            context="",  # not tracked in live; judge prompt does not use it
                            context_highlighted="",
                            decode=item.monologue,
                            norm=0.0,  # /generate does not expose norm today
                        )
                    )
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
        except GPUClientError as e:
            await queue.put(("error", ErrorEvent(detail=str(e)).model_dump()))
            # Re-raise so the outer flow can short-circuit cleanly.
            raise

        return "".join(verbal_buf), rows

    async def _run_judge_safely(
        self,
        queue: asyncio.Queue,
        verbal: str,
        rows: list[DecodeRow],
    ):
        """Wrap the judge call to convert errors into SSE error events.
        Returns the verdict or None on failure."""
        try:
            # ClaudeAgentJudge.evaluate_turn is sync; run on a thread so we
            # don't block the event loop on the Anthropic SDK call.
            return await asyncio.to_thread(self._judge.evaluate_turn, verbal, rows)
        except ClaudeAgentJudgeError as e:
            await queue.put(("error", ErrorEvent(detail=f"judge error: {e}").model_dump()))
            return None

    @staticmethod
    def _compose_steered_system_prompt(original_system: str | None, correction: str) -> str:
        """Prepend the correction_prompt as a system directive. If the user
        already passed a system_prompt, the correction precedes it so the
        directive wins on contention."""
        if not original_system:
            return correction
        return f"{correction}\n\n{original_system}"

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
