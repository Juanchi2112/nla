"""Abstract GPU client used by the orchestrator's generation loop.

The orchestrator never imports a concrete client directly — it goes
through this ABC so we can swap mock / real / fake implementations
without touching the route or generator code.

The protocol is intentionally lean: produce a stream of (token, optional
monologue) pairs at the orchestrator's pace. The concrete clients can
fulfil this either by streaming token-by-token from sglang or by
batching a single /decode call and replaying it on a timer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Optional


@dataclass
class GPUStreamItem:
    """One step of the generation stream.

    `token`: text fragment to forward to the SSE consumer.
    `monologue`: AV decoding at this position. Present only on sniff
        steps (every K tokens); None on plain token steps.
    """
    step: int
    token: str
    monologue: Optional[str] = None


class GPUClientError(RuntimeError):
    """Base for any GPU-side failure surfaced to the orchestrator."""


class GPUNotConfiguredError(GPUClientError):
    """Raised when the user picks a GPU backend but hasn't supplied
    the URL / credentials it needs. Translated to a 503 by the route."""


class GPUClient(ABC):
    """Stream tokens + optional monologues for one prompt."""

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        *,
        sniff_every_k: int,
        max_new_tokens: int,
    ) -> AsyncIterator[GPUStreamItem]: ...

    async def aclose(self) -> None:
        """Hook for clients that hold network resources. Default no-op."""
        return None
