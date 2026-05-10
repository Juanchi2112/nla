"""Shared async generator for autoregressive Qwen + NLA actor traces.

Single source of truth for the generation loop. Used by:
  - gpu/scripts/generate_stream.py (CLI smoke test, prints to stdout)
  - gpu/server.py POST /generate     (FastAPI, wraps each event as SSE)

Mechanics (validated end-to-end on the A6000 box before promotion to endpoint):
  - Manual decode loop with KV-cache (no model.generate())
  - Layer-K hook on Qwen base captures the new-token residual every step
  - actor.generate() fires as create_task; pending tasks drain on every yield

Out-of-order is expected and intentional: tokens come out at Qwen's pace
(~30ms each), actor traces arrive at SGLang's pace (~hundreds of ms,
overlapped via the continuous batcher). Each event carries `step` so the
consumer can re-correlate.

Cancellation: the caller cancels the consumer task; the `finally` block
cancels in-flight actor coroutines so SGLang doesn't keep computing for a
disconnected client. The HTTP calls already in flight on worker threads
will finish and discard their results — that's acceptable cleanup cost.
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from gpu.nla_inference import NLAClient


EventKind = Literal["token", "actor_spawn", "nla_trace", "summary"]


@dataclass
class StreamEvent:
    """One event emitted by the generation stream.

    kind:
      token       — Qwen sampled a new token. step + text set.
      actor_spawn — actor.generate() dispatched. step set.
      nla_trace   — actor result arrived. step (= step the residual was captured)
                    + text (the explanation) set.
      summary     — final stats. summary dict set.
    """

    kind: EventKind
    t: float
    step: int | None = None
    text: str | None = None
    summary: dict[str, Any] | None = None


@dataclass
class StreamConfig:
    sniff_every_k: int = 5
    max_new_tokens: int = 64
    temperature: float = 0.7
    actor_temperature: float = 0.7
    actor_max_new_tokens: int = 200
    raw: bool = False  # skip chat template — debug only


class Extractor:
    """Qwen base, resident, with a forward hook on layer K's residual stream.

    Two modes:
      extract(text) — single forward over a full text, returns (ids, hidden[T,d]).
                      Used by /decode.
      step(ids, kv) — one forward (prefill or decode), returns (last_logits,
                      last_residual, new_past_kv). Used by /generate and CLI.

    The hook accumulates into self._captured; both methods clear it at start.
    The (-1) index makes both safe regardless of leftover state from prior calls.

    Hook pattern matches gpu/scripts/extract_activations.py and the upstream
    nla repo's extractor — output[0] unwraps the decoder block's tuple return.
    """

    def __init__(self, model_name: str, layer_index: int, device: str):
        print(f"[extractor] loading {model_name} on {device}", file=sys.stderr)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map=device,
        ).eval()
        self.device = self.model.get_input_embeddings().weight.device
        self.layer_index = layer_index
        self._captured: list[torch.Tensor] = []

        def hook(_mod, _inp, output):
            h = output[0] if isinstance(output, tuple) else output
            self._captured.append(h.detach())

        self.model.model.layers[layer_index].register_forward_hook(hook)

    @torch.inference_mode()
    def extract(self, text: str) -> tuple[list[int], torch.Tensor]:
        """Single forward over `text`. Returns (token_ids, hidden[T, d_model] cpu fp32).

        Caller is the /decode endpoint — it wants every position's residual to
        decode the AV per token of the input.
        """
        self._captured.clear()
        ids = self.tokenizer(
            text,
            return_tensors="pt",
            add_special_tokens=True,
        )["input_ids"].to(self.device)
        self.model(input_ids=ids, use_cache=False)
        return ids[0].cpu().tolist(), self._captured[-1].float().cpu()[0]

    @torch.inference_mode()
    def step(
        self,
        input_ids: torch.Tensor,
        past_kv: Any,
    ) -> tuple[torch.Tensor, torch.Tensor, Any]:
        """One forward. Returns (last_logits[V], last_residual[d], new_past_kv).

        input_ids shape:
          [1, T] for prefill (past_kv=None)
          [1, 1] for decode  (the just-sampled token, past_kv from prev step)
        """
        self._captured.clear()
        out = self.model(
            input_ids=input_ids,
            past_key_values=past_kv,
            use_cache=True,
        )
        last_residual = self._captured[-1][0, -1, :]
        last_logits = out.logits[0, -1, :]
        return last_logits, last_residual, out.past_key_values


def sample(logits: torch.Tensor, temperature: float) -> int:
    """Greedy if T<=0, else softmax-sample. fp32 cast for sampling stability."""
    if temperature <= 0:
        return int(logits.argmax().item())
    probs = torch.softmax(logits.float() / temperature, dim=-1)
    return int(torch.multinomial(probs, 1).item())


@dataclass
class _ActorTask:
    step: int
    spawned_at: float
    task: asyncio.Task[str]


@dataclass
class _RunStats:
    tokens: int = 0
    t_first_token: float = 0.0
    actor_count: int = 0
    actor_total_latency: float = 0.0
    actor_first_spawn: float = field(default=float("inf"))
    actor_last_done: float = 0.0


async def stream_events(
    extractor: Extractor,
    actor: NLAClient,
    prompt: str,
    config: StreamConfig,
) -> AsyncIterator[StreamEvent]:
    """Drive autoregressive generation, yielding events as they happen.

    Caller responsibilities:
      - Hold any concurrency lock (e.g. server.py's app.state.lock) BEFORE
        calling — this generator does no locking, and concurrent invocations
        on the same Extractor/NLAClient WILL thrash the KV cache.
      - On client disconnect, cancel the task that consumes this generator;
        the finally block here will cancel any pending actor coroutines.
    """
    tokenizer = extractor.tokenizer

    if config.raw:
        ids = tokenizer(
            prompt, return_tensors="pt", add_special_tokens=True
        )["input_ids"]
    else:
        ids = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            add_generation_prompt=True,
            return_tensors="pt",
        )
    ids = ids.to(extractor.device)

    stop_id = tokenizer.eos_token_id
    t_start = time.monotonic()
    stats = _RunStats()
    pending: list[_ActorTask] = []
    all_ids: list[int] = []
    prev_text = ""

    def now() -> float:
        return time.monotonic() - t_start

    def maybe_spawn(step: int, residual: torch.Tensor) -> StreamEvent | None:
        if step % config.sniff_every_k != 0:
            return None
        v = residual.float().cpu().numpy().astype(np.float32)
        spawned_at = now()
        stats.actor_first_spawn = min(stats.actor_first_spawn, spawned_at)
        stats.actor_count += 1
        # to_thread releases the GIL on the httpx socket read; create_task
        # only schedules — the coroutine starts on the next loop yield (the
        # asyncio.sleep(0) below). Without that yield we'd queue all tasks at
        # the end and lose every overlap opportunity.
        coro = asyncio.to_thread(
            actor.generate,
            v,
            temperature=config.actor_temperature,
            max_new_tokens=config.actor_max_new_tokens,
        )
        task = asyncio.create_task(coro)
        pending.append(_ActorTask(step=step, spawned_at=spawned_at, task=task))
        return StreamEvent(kind="actor_spawn", t=spawned_at, step=step)

    def emit_token(step: int, next_id: int) -> StreamEvent:
        nonlocal prev_text
        all_ids.append(next_id)
        cur_text = tokenizer.decode(all_ids, skip_special_tokens=False)
        chunk = cur_text[len(prev_text):]
        prev_text = cur_text
        return StreamEvent(kind="token", t=now(), step=step, text=chunk)

    def collect_done() -> list[StreamEvent]:
        events: list[StreamEvent] = []
        for at in list(pending):
            if at.task.done():
                try:
                    text = at.task.result()
                except Exception as e:
                    text = f"<actor error: {e!r}>"
                done_at = now()
                stats.actor_total_latency += done_at - at.spawned_at
                stats.actor_last_done = max(stats.actor_last_done, done_at)
                events.append(
                    StreamEvent(kind="nla_trace", t=done_at, step=at.step, text=text)
                )
                pending.remove(at)
        return events

    try:
        # Prefill.
        logits, residual, past_kv = extractor.step(ids, None)
        stats.t_first_token = now()
        next_id = sample(logits, config.temperature)
        yield emit_token(0, next_id)
        stats.tokens = 1

        ev = maybe_spawn(0, residual)
        if ev is not None:
            yield ev

        await asyncio.sleep(0)
        for done_ev in collect_done():
            yield done_ev

        # Decode loop.
        if next_id != stop_id:
            cur_ids = torch.tensor([[next_id]], device=extractor.device)
            for step in range(1, config.max_new_tokens):
                logits, residual, past_kv = extractor.step(cur_ids, past_kv)
                next_id = sample(logits, config.temperature)
                yield emit_token(step, next_id)
                stats.tokens += 1

                ev = maybe_spawn(step, residual)
                if ev is not None:
                    yield ev

                await asyncio.sleep(0)
                for done_ev in collect_done():
                    yield done_ev

                if next_id == stop_id:
                    break
                cur_ids = torch.tensor([[next_id]], device=extractor.device)

        # Drain stragglers.
        if pending:
            await asyncio.wait([at.task for at in pending])
            for done_ev in collect_done():
                yield done_ev

        # Summary.
        wallclock = now()
        actor_window = (
            stats.actor_last_done - stats.actor_first_spawn
            if stats.actor_count > 0
            else 0.0
        )
        overlap = (
            stats.actor_total_latency / actor_window if actor_window > 0 else 0.0
        )
        summary = {
            "tokens": stats.tokens,
            "wallclock_s": round(wallclock, 3),
            "tok_per_s": round(stats.tokens / wallclock, 2) if wallclock > 0 else 0.0,
            "ttft_s": round(stats.t_first_token, 3),
            "actor_count": stats.actor_count,
            "actor_total_latency_s": round(stats.actor_total_latency, 3),
            "actor_window_s": round(actor_window, 3),
            "overlap_factor": round(overlap, 2),
            "full_text": prev_text,
        }
        yield StreamEvent(kind="summary", t=wallclock, summary=summary)

    finally:
        # Caller cancelled, errored, or stopped iterating. Cancel any pending
        # actor coroutines so SGLang isn't computing for a disconnected client.
        # Threads already in their httpx socket read will finish and discard.
        for at in pending:
            if not at.task.done():
                at.task.cancel()
