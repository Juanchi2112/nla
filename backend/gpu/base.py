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


@dataclass
class GPUStreamItem:
    """One step of the generation stream.

    Either `token`, `monologue`, or both may be set on a given item.
    Real-streaming GPUs (gpu/server.py /generate) emit them independently
    because actor traces arrive out-of-order vs Qwen's tokens; legacy clients
    (mock, /decode replay) set both at once. Consumers must check each field.

    `step`: the residual-stream position this item corresponds to. Tokens and
        their later-arriving monologue trace share a step number.
    `token`: text fragment from Qwen at this step. None for monologue-only
        items (the trace for an earlier step that's still in flight).
    `monologue`: AV decoding of the residual at this step. Present on sniff
        steps (every K tokens); None on plain token-only steps.
    """

    step: int
    token: str | None = None
    monologue: str | None = None


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
        system_prompt: str | None = None,
        sniff_every_k: int,
        max_new_tokens: int,
    ) -> AsyncIterator[GPUStreamItem]: ...

    async def aclose(self) -> None:
        """Hook for clients that hold network resources. Default no-op."""
        return None
