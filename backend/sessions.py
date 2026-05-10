"""In-memory session registry.

One process holds all sessions in a global dict. Each session owns:
    - an asyncio.Queue of pending SSE events (producer = generator task,
      consumer = stream endpoint)
    - a stop flag (cooperative cancellation, checked by the generator)
    - a steering_decision flag (set by /api/confirm-steer or
      /api/reject-steer in live mode; awaited by SteeringEngine)
    - the producer task itself (so we can cancel it on shutdown)

Hackathon constraints — no Redis, no DB, no TTL eviction. A session
lives until generation finishes (or is cancelled), then it is dropped
from the registry. A long-running deployment would need a sweep, but
for a demo the user controls when sessions exit.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SessionState:
    session_id: str
    prompt: str
    system_prompt: str | None = None
    sniff_every_k: int = 4
    created_at: float = field(default_factory=time.time)

    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: asyncio.Task | None = None

    stop_requested: bool = False
    total_tokens_emitted: int = 0

    # Set when /api/generate received a scenario_id instead of a prompt.
    # SteeringEngine.run() branches on this: scenario_id set → cached source
    # (auto-steer); else → live source (manual confirm steer via the
    # decision flag below).
    scenario_id: str | None = None

    # Live-mode manual steering decision. Set to "pending" by
    # SteeringEngine when it emits steering_proposed; flipped to
    # "confirm" or "reject" by the corresponding endpoint, which also
    # sets steering_decision_event so the engine wakes up.
    steering_decision: Literal["pending", "confirm", "reject"] | None = None
    steering_decision_event: asyncio.Event = field(default_factory=asyncio.Event)


class SessionRegistry:
    """Simple dict-of-sessions. Async-safe enough for our single-process use:
    the asyncio event loop serializes all dict mutations."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create(
        self,
        session_id: str,
        prompt: str = "",
        sniff_every_k: int = 4,
        scenario_id: str | None = None,
        system_prompt: str | None = None,
    ) -> SessionState:
        if session_id in self._sessions:
            raise KeyError(f"session_id={session_id!r} already exists")
        s = SessionState(
            session_id=session_id,
            prompt=prompt,
            system_prompt=system_prompt,
            sniff_every_k=sniff_every_k,
            scenario_id=scenario_id,
        )
        self._sessions[session_id] = s
        return s

    def get(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def request_stop(self, session_id: str) -> bool:
        s = self._sessions.get(session_id)
        if s is None:
            return False
        s.stop_requested = True
        # Unblock any awaiter on the steering decision event.
        s.steering_decision_event.set()
        return True

    def request_confirm_steer(self, session_id: str) -> bool:
        """Returns True only if the session is awaiting a decision."""
        return self._set_steering_decision(session_id, "confirm")

    def request_reject_steer(self, session_id: str) -> bool:
        return self._set_steering_decision(session_id, "reject")

    def _set_steering_decision(
        self, session_id: str, decision: Literal["confirm", "reject"]
    ) -> bool:
        s = self._sessions.get(session_id)
        if s is None or s.steering_decision != "pending":
            return False
        s.steering_decision = decision
        s.steering_decision_event.set()
        return True

    async def shutdown(self) -> None:
        """Cancel every running task. Called from app lifespan exit."""
        for s in list(self._sessions.values()):
            if s.task is not None and not s.task.done():
                s.task.cancel()
        self._sessions.clear()
