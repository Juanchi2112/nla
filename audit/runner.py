"""Send a probe through the live Verbalize backend, collect the SSE transcript.

Hits POST /api/generate with the deployment system_prompt + probe.user_message,
then opens GET /api/stream/{session_id} (SSE) and accumulates:
  - all `token` events into output_text
  - all `nla_trace` events into traces
  - the final `judge_summary` (if any) into turn_verdict

Returns a RunArtifact ready for the audit judge.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import httpx

from .schemas import RunArtifact, TraceRow, TurnVerdictLite

log = logging.getLogger(__name__)

BACKEND_URL = os.environ.get("AUDIT_BACKEND_URL", "http://localhost:8001")
PROBE_TIMEOUT_S = float(os.environ.get("AUDIT_PROBE_TIMEOUT", "180"))


async def run_probe(
    probe_id: str,
    rule_id: str,
    system_prompt: str,
    user_message: str,
    *,
    sniff_every_k: int = 4,
) -> RunArtifact:
    session_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    output_chunks: list[str] = []
    traces: list[TraceRow] = []
    turn_verdict: TurnVerdictLite | None = None
    error: str | None = None

    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_S) as client:
            r = await client.post(
                f"{BACKEND_URL}/api/generate",
                json={
                    "session_id": session_id,
                    "prompt": user_message,
                    "system_prompt": system_prompt,
                    "sniff_every_k": sniff_every_k,
                },
            )
            r.raise_for_status()

            async with client.stream("GET", f"{BACKEND_URL}/api/stream/{session_id}") as s:
                event_name: str | None = None
                async for line in s.aiter_lines():
                    if line.startswith(":"):
                        continue  # keepalive
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

                        ev_type = event_name or payload.get("type")
                        if ev_type == "token":
                            output_chunks.append(payload.get("text", ""))
                        elif ev_type == "nla_trace":
                            traces.append(
                                TraceRow(
                                    step=payload["step"],
                                    monologue=payload.get("monologue") or payload.get("text", ""),
                                )
                            )
                        elif ev_type == "judge_summary":
                            v = payload.get("verdict") or {}
                            turn_verdict = TurnVerdictLite(
                                trust_score=v.get("trust_score", 0),
                                summary=v.get("summary", ""),
                                action=v.get("action", "PASS"),
                                divergences=v.get("divergences", []),
                            )
                        elif ev_type == "error":
                            error = payload.get("detail", "unknown SSE error")
                        elif ev_type == "done":
                            break
                        # ignore: actor_spawn, steering_*, etc.
                        event_name = None
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        log.exception("run_probe failed for %s", probe_id)

    return RunArtifact(
        probe_id=probe_id,
        rule_id=rule_id,
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
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
