"""Client for the GPU-side /decode endpoint (server.py).

Wire format — verified live against http://193.222.57.16:44016/decode:

    request:
        { "text": str, "skip_first": int, "score": bool,
          "temperature": float, "max_new_tokens": int }

    response:
        { "text": str, "activation_layer": int, "n_total_tokens": int,
          "rows": [ { "pos": int, "context": str,
                      "context_highlighted": str, "norm": float,
                      "decode": str, "mse": float|null, "cos": float|null }
                    ... ] }

Important semantics: /decode analyses an existing text — it does NOT
generate new tokens. Each row carries the AV's monologue ("decode") at
one residual-stream position of the input. The orchestrator replays
those rows on a small timer to fit its streaming contract; the
"tokens" we emit are the new-chunks of `context` between consecutive
rows, not anything the model produced.

Rows start at position `skip_first` (server.py default = 10). For a
short text (n ≤ skip_first) the response has zero rows. Either lengthen
the prompt or set GPU_SKIP_FIRST lower in the orchestrator config.

When ORCHESTRATOR_GPU=decoder is set, this client refuses to start
without an explicit GPU_URL — there is no silent fallback to a default
host so deploys can't accidentally point at the wrong box.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from .base import GPUClient, GPUClientError, GPUNotConfiguredError, GPUStreamItem

log = logging.getLogger(__name__)

# Sentinel: when GPU_URL is left at this value, the client refuses to
# start. Meant to be a clear "you forgot to set it" signal in deploy logs.
URL_PLACEHOLDER = "__TBD__"


class DecoderEndpointClient(GPUClient):
    """Calls server.py's /decode; replays the rows as a stream item series.

    /decode is non-streaming (single request, full response). To match
    the orchestrator's streaming contract we replay rows one at a time
    on a small interval. When the GPU side gains a true streaming
    endpoint, swap the body of .stream() to consume that and keep the
    GPUStreamItem shape.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 120.0,
        replay_interval: float = 0.05,
        skip_first: int = 10,
        av_max_new_tokens: int = 200,
        av_temperature: float = 0.7,
    ):
        if not base_url or base_url == URL_PLACEHOLDER:
            raise GPUNotConfiguredError(
                "ORCHESTRATOR_GPU=decoder but GPU_URL is unset (or left at "
                f"the placeholder {URL_PLACEHOLDER!r}). Set GPU_URL to the "
                "actual /decode endpoint before starting the orchestrator."
            )
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._replay_interval = replay_interval
        self._skip_first = skip_first
        self._av_max_new_tokens = av_max_new_tokens
        self._av_temperature = av_temperature
        self._http: httpx.AsyncClient | None = None

    async def _ensure_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self._timeout),
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def stream(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        sniff_every_k: int,
        max_new_tokens: int,  # ignored: /decode does not generate
    ) -> AsyncIterator[GPUStreamItem]:
        http = await self._ensure_http()
        body = {
            "text": prompt,
            "system_prompt": system_prompt,
            "skip_first": self._skip_first,
            "score": False,
            "temperature": self._av_temperature,
            "max_new_tokens": self._av_max_new_tokens,
        }
        try:
            r = await http.post("/decode", json=body)
            r.raise_for_status()
            payload: dict[str, Any] = r.json()
        except httpx.HTTPStatusError as e:
            raise GPUClientError(
                f"GPU /decode HTTP {e.response.status_code}: {e.response.text[:200]}"
            ) from e
        except (httpx.HTTPError, ValueError) as e:
            raise GPUClientError(f"GPU /decode transport error: {e}") from e

        rows = payload.get("rows") or []
        if not rows:
            # Most common cause: text shorter than skip_first. Surface it
            # as a typed GPU error so the orchestrator emits an `error`
            # SSE frame rather than a confusingly empty stream.
            n = payload.get("n_total_tokens")
            raise GPUClientError(
                f"GPU /decode returned 0 rows (n_total_tokens={n}, "
                f"skip_first={self._skip_first}). Lengthen the input "
                "or lower GPU_SKIP_FIRST."
            )

        for i, row in enumerate(rows):
            # /decode returns one row per residual-stream position. `context`
            # is the cumulative decoded prefix up to and including that
            # position; `decode` is the AV's monologue at that position. We
            # treat every row as a step and emit a monologue every K rows.
            token_text = self._extract_new_chunk(rows, i)
            monologue = row.get("decode") if (i % sniff_every_k == 0) else None
            yield GPUStreamItem(step=i, token=token_text, monologue=monologue)
            await asyncio.sleep(self._replay_interval)

    @staticmethod
    def _extract_new_chunk(rows: list[dict[str, Any]], i: int) -> str:
        cur = rows[i].get("context") or ""
        prev = rows[i - 1].get("context") if i > 0 else ""
        prev = prev or ""
        return cur[len(prev) :] if cur.startswith(prev) else cur
