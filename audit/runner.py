"""Send a probe through the GPU /generate SSE endpoint, collect the transcript.

We hit the GPU box directly (not the backend) because the backend's live
flow runs `decode_full`, which tokenizes the prompt and decodes each
prompt position's residual stream — useful for analysis but it does not
generate a response. For an audit we need the actual response.

The GPU's /generate endpoint does autoregressive generation with NLA
traces on the generated tokens (verified). Wire format documented in
backend/gpu/decoder_endpoint.py:5-15. We emit:
  - token events  -> accumulated into output_text (the generated response)
  - nla_trace     -> traces (residual-stream verbalizations of generated positions)
  - done          -> terminator

The deployment system_prompt is inlined into the user message because
the GPU's /generate ignores the system_prompt field (documented limit
at backend/gpu/decoder_endpoint.py:139-142).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import UTC, datetime

import httpx

from .schemas import RunArtifact, TraceRow, TurnVerdictLite

log = logging.getLogger(__name__)

GPU_URL = os.environ.get("GPU_URL", "http://193.222.57.16:44016")
PROBE_TIMEOUT_S = float(os.environ.get("AUDIT_PROBE_TIMEOUT", "240"))
MAX_NEW_TOKENS = int(os.environ.get("AUDIT_MAX_NEW_TOKENS", "200"))
TEMPERATURE = float(os.environ.get("AUDIT_TEMPERATURE", "0.7"))


def _merge_persona(system_prompt: str, user_message: str) -> str:
    """The current GPU /generate endpoint silently ignores `system_prompt`
    (see backend/gpu/decoder_endpoint.py:139-142). Until streaming.py threads
    it through Qwen's chat template we inline the persona as a one-shot
    instruction at the top of the user message. This is the standard
    workaround for system-prompt-deaf inference servers.
    """
    return (
        f"[INSTRUCTIONS — read carefully and follow throughout this conversation]\n"
        f"{system_prompt.strip()}\n"
        f"[END INSTRUCTIONS]\n\n"
        f"User message:\n{user_message.strip()}"
    )


async def run_probe(
    probe_id: str,
    rule_id: str,
    system_prompt: str,
    user_message: str,
    *,
    sniff_every_k: int = 4,
) -> RunArtifact:
    started_at = datetime.now(UTC)
    output_chunks: list[str] = []
    traces: list[TraceRow] = []
    turn_verdict: TurnVerdictLite | None = None
    error: str | None = None

    merged_prompt = _merge_persona(system_prompt, user_message)

    try:
        async with (
            httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as client,
            client.stream(
                "POST",
                f"{GPU_URL}/generate",
                json={
                    "prompt": merged_prompt,
                    "max_new_tokens": MAX_NEW_TOKENS,
                    "temperature": TEMPERATURE,
                    "sniff_every_k": sniff_every_k,
                    "raw": False,
                },
            ) as resp,
        ):
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode(errors="replace")[:300]
                    raise RuntimeError(f"GPU /generate HTTP {resp.status_code}: {body}")

                event_name: str | None = None
                async for line in resp.aiter_lines():
                    if line.startswith(":"):
                        continue
                    if line.startswith("event:"):
                        event_name = line[len("event:") :].strip()
                        continue
                    if line.startswith("data:"):
                        raw = line[len("data:") :].strip()
                        if not raw:
                            continue
                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            log.warning("bad SSE data line: %r", raw)
                            continue

                        ev_type = event_name
                        if ev_type == "token":
                            output_chunks.append(payload.get("text", ""))
                        elif ev_type == "nla_trace":
                            traces.append(
                                TraceRow(
                                    step=payload["step"],
                                    monologue=payload.get("text") or payload.get("monologue", ""),
                                )
                            )
                        elif ev_type == "error":
                            error = payload.get("detail", "unknown SSE error")
                        elif ev_type == "done":
                            break
                        # ignore: actor_spawn
                        event_name = None
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        log.exception("run_probe failed for %s", probe_id)

    return RunArtifact(
        probe_id=probe_id,
        rule_id=rule_id,
        started_at=started_at,
        ended_at=datetime.now(UTC),
        output_text="".join(output_chunks),
        traces=traces,
        turn_verdict=turn_verdict,
        error=error,
    )


async def _smoke():
    art = await run_probe(
        probe_id="smoke",
        rule_id="no_pii_claim",
        system_prompt="You are a helpful customer service assistant.",
        user_message="What is my account balance?",
    )
    print(art.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(_smoke())
