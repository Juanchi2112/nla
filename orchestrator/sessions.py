"""In-memory session registry.

One process holds all sessions in a global dict. Each session owns:
    - an asyncio.Queue of pending SSE events (producer = generator task,
      consumer = stream endpoint)
    - a stop flag (cooperative cancellation, checked by the generator)
    - an active_rubric flag (set by /api/steer, read by the generator)
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
from typing import Any, Optional


@dataclass
class SessionState:
    session_id: str
    prompt: str
    sniff_every_k: int = 4
    created_at: float = field(default_factory=time.time)

    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    task: Optional[asyncio.Task] = None

    stop_requested: bool = False
    active_rubric: Optional[str] = None
    steer_intensity: float = 1.0
    # Set when /api/steer is called; the generator consumes this on its
    # next loop iteration and clears it after emitting steer_applied.
    update_pending: bool = False

    total_tokens_emitted: int = 0


class SessionRegistry:
    """Simple dict-of-sessions. Async-safe enough for our single-process use:
    the asyncio event loop serializes all dict mutations."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def create(self, session_id: str, prompt: str, sniff_every_k: int) -> SessionState:
        if session_id in self._sessions:
            raise KeyError(f"session_id={session_id!r} already exists")
        s = SessionState(
            session_id=session_id, prompt=prompt, sniff_every_k=sniff_every_k,
        )
        self._sessions[session_id] = s
        return s

    def get(self, session_id: str) -> Optional[SessionState]:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def request_stop(self, session_id: str) -> bool:
        s = self._sessions.get(session_id)
        if s is None:
            return False
        s.stop_requested = True
        return True

    def request_steer(self, session_id: str, rubric: str, intensity: float) -> bool:
        s = self._sessions.get(session_id)
        if s is None:
            return False
        s.active_rubric = rubric
        s.steer_intensity = intensity
        s.update_pending = True
        return True

    async def shutdown(self) -> None:
        """Cancel every running task. Called from app lifespan exit."""
        for s in list(self._sessions.values()):
            if s.task is not None and not s.task.done():
                s.task.cancel()
        self._sessions.clear()
