"""MockGPUClient: canned tokens + curated monologues for local dev.

Used when ORCHESTRATOR_GPU=mock (no GPU available, no network calls). Produces
a deterministic-but-varied stream so the SSE pipeline, frontend, and steering
engine can be exercised end-to-end without infrastructure.

The mock does NOT pretend to do real NLA analysis — it just serves canned
data shaped like a /decode response. SteeringEngine in live mode will skip
the ClaudeAgentJudge call when running against a mock GPU (judge=None
because mock mode does not configure a live judge).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from .gpu.base import GPUClient, GPUStreamItem

# How fast we replay tokens (seconds). Slow enough that an SSE consumer
# sees them tick in real time; not so slow that the demo drags.
TOKEN_INTERVAL = 0.06

CANNED_RESPONSE = (
    "I will work through this step by step. First, let me consider the "
    "context and the user's intent. Based on the available evidence I "
    "believe the most likely answer involves a careful application of "
    "the relevant principles. Final answer: 491."
)

# Curated monologues — pseudo-decodes shaped like real NLA verbalizations.
# Cycled with sniff_every_k so the demo UX has visible variation.
MONOLOGUE_CYCLE = [
    "The model is working through the user's request and planning a "
    "helpful answer that draws on standard knowledge.",
    "The model is fabricating a tool result and is about to override "
    "the tool's actual output by reporting a different value to the user.",
    "The model is consolidating its reasoning and is about to render a "
    "concise final answer to the user.",
    "The model is preparing to assert a false claim about having "
    "verified the file even though no verification happened.",
]


class MockGPUClient(GPUClient):
    """Streams CANNED_RESPONSE word-by-word with curated monologues.

    Holds no network state. One instance is fine for the whole app.
    Used when ORCHESTRATOR_GPU=mock for local dev without a GPU.
    """

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        sniff_every_k: int,
        max_new_tokens: int,
    ) -> AsyncIterator[GPUStreamItem]:
        words = CANNED_RESPONSE.split()
        n = min(len(words), max_new_tokens)
        for step in range(n):
            tok = (" " if step > 0 else "") + words[step]
            monologue = (
                MONOLOGUE_CYCLE[step % len(MONOLOGUE_CYCLE)] if step % sniff_every_k == 0 else None
            )
            yield GPUStreamItem(step=step, token=tok, monologue=monologue)
            await asyncio.sleep(TOKEN_INTERVAL)
