"""Client for the GPU-side /generate SSE endpoint (gpu/server.py).

Wire format — events streamed as Server-Sent Events frames:

    request (POST /generate):
        { "prompt": str, "sniff_every_k": int, "max_new_tokens": int,
          "temperature": float, "actor_temperature": float,
          "actor_max_new_tokens": int, "raw": bool }

    response (text/event-stream):
        event: token       data: {"step": int, "text": str}
        event: nla_trace   data: {"step": int, "text": str}
        event: actor_spawn data: {"step": int}                 (debug, ignored)
        event: error       data: {"detail": str}               (raises)
        event: done        data: {summary stats + full_text}   (terminator)

Tokens and traces arrive INDEPENDENTLY: tokens stream at Qwen's pace
(~30ms/each), traces at SGLang's pace (hundreds of ms, overlapped). Each
event carries `step`, so consumers re-correlate token N with trace N when
both are present. The orchestrator (_produce in backend/app.py) handles
items where token or monologue is None — see backend/gpu/base.py.

When ORCHESTRATOR_GPU=decoder is set, the client refuses to start without
an explicit GPU_URL — there is no silent fallback to a default host so
deploys can't accidentally point at the wrong box.

NB: the legacy /decode endpoint stays available on gpu/server.py for
analytical use (decode_parquet, debugging). This client no longer hits it.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

from .base import GPUClient, GPUClientError, GPUNotConfiguredError, GPUStreamItem

log = logging.getLogger(__name__)

# Sentinel: when GPU_URL is left at this value, the client refuses to
# start. Meant to be a clear "you forgot to set it" signal in deploy logs.
URL_PLACEHOLDER = "__TBD__"


class _SSEParser:
    """Minimal SSE frame parser.

    Feed it lines from httpx.aiter_lines() (which strips line terminators
    but yields "" for blank lines, marking frame boundaries). Returns
    (event_name, data) when a frame completes.

    We don't implement `id:` or `retry:` — server doesn't emit them. Lines
    starting with ":" are SSE comments (used for keepalives) and ignored.
    """

    def __init__(self) -> None:
        self._event: str | None = None
        self._data: list[str] = []

    def feed(self, line: str) -> tuple[str, str] | None:
        if line == "":
            if self._event is None and not self._data:
                return None  # no frame in progress
            event = self._event or "message"
            data = "\n".join(self._data)
            self._event = None
            self._data = []
            return (event, data)
        if line.startswith(":"):
            return None
        if line.startswith("event:"):
            self._event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            # Strip exactly one leading space if present (per SSE spec).
            chunk = line[len("data:"):]
            if chunk.startswith(" "):
                chunk = chunk[1:]
            self._data.append(chunk)
        return None


class DecoderEndpointClient(GPUClient):
    """Streams Qwen tokens + NLA actor traces from gpu/server.py /generate.

    The class name is historical (the original client hit /decode and
    replayed rows). The wire is now real SSE — token and trace events
    arrive in real time, possibly out-of-order, mapped 1:1 to GPUStreamItems.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 120.0,
        temperature: float = 0.7,
        actor_max_new_tokens: int = 200,
        actor_temperature: float = 0.7,
    ):
        if not base_url or base_url == URL_PLACEHOLDER:
            raise GPUNotConfiguredError(
                "ORCHESTRATOR_GPU=decoder but GPU_URL is unset (or left at "
                f"the placeholder {URL_PLACEHOLDER!r}). Set GPU_URL to the "
                "actual server.py base URL before starting the orchestrator."
            )
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._temperature = temperature
        self._actor_max_new_tokens = actor_max_new_tokens
        self._actor_temperature = actor_temperature
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
        max_new_tokens: int,
    ) -> AsyncIterator[GPUStreamItem]:
        http = await self._ensure_http()
        body = {
            "prompt": prompt,
            # system_prompt is forwarded to gpu/server.py; today the /generate
            # endpoint ignores extras (Pydantic default), so this is a no-op
            # until streaming.py threads it through Qwen's chat template.
            # Tracked as follow-up: tie system_prompt to chat formatting.
            "system_prompt": system_prompt,
            "sniff_every_k": sniff_every_k,
            "max_new_tokens": max_new_tokens,
            "temperature": self._temperature,
            "actor_temperature": self._actor_temperature,
            "actor_max_new_tokens": self._actor_max_new_tokens,
            "raw": False,
        }
        parser = _SSEParser()

        try:
            async with http.stream("POST", "/generate", json=body) as resp:
                if resp.status_code >= 400:
                    # Read the body so we can include it in the error. SSE
                    # responses are streamed, but error responses are usually
                    # JSON one-shot — this is safe.
                    detail = (await resp.aread()).decode(errors="replace")[:200]
                    raise GPUClientError(
                        f"GPU /generate HTTP {resp.status_code}: {detail}"
                    )

                async for line in resp.aiter_lines():
                    frame = parser.feed(line)
                    if frame is None:
                        continue
                    event, data = frame

                    if event == "token":
                        payload = json.loads(data)
                        yield GPUStreamItem(
                            step=payload["step"], token=payload["text"]
                        )
                    elif event == "nla_trace":
                        payload = json.loads(data)
                        yield GPUStreamItem(
                            step=payload["step"], monologue=payload["text"]
                        )
                    elif event == "actor_spawn":
                        # Debug-only: tells us when actor.generate() was
                        # dispatched. Useful for measuring overlap from logs;
                        # not part of the orchestrator's contract.
                        continue
                    elif event == "error":
                        payload = json.loads(data)
                        raise GPUClientError(
                            f"GPU /generate: {payload.get('detail', 'unknown error')}"
                        )
                    elif event == "done":
                        # Terminator. Summary stats live in `data` if needed
                        # for telemetry; the orchestrator doesn't read them.
                        return
                    else:
                        log.debug("ignoring unknown SSE event %r", event)

        except httpx.HTTPError as e:
            raise GPUClientError(f"GPU /generate transport error: {e}") from e
        except json.JSONDecodeError as e:
            raise GPUClientError(f"GPU /generate sent malformed JSON: {e}") from e
