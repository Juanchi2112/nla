"""GPU-side autoregressive generation with NLA actor traces — standalone CLI.

Step 1 of the streaming-generation work. Validates three mechanics in isolation
before any FastAPI / SSE plumbing:

  1. Manual autoregressive loop with KV-cache (no model.generate()).
  2. Layer-K hook captures the new-token residual on every step.
  3. Async fan-out: actor.generate() calls fire as create_task while Qwen
     keeps sampling. Drain pending tasks on every iteration.

Prints token + nla_trace events with wallclock timestamps and a summary at the
end. The key validation metric is `overlap_factor` — sum of per-task actor
latencies divided by the wallclock window from first spawn to last completion.
1.0× means SGLang serialized the requests; > 1.5× means the continuous batcher
overlapped actor work with Qwen's next forwards.

Run on the GPU box AFTER SGLang is up:

    bash gpu/scripts/launch_sglang.sh                     # terminal 1
    uv run python gpu/scripts/generate_stream.py \\
        --prompt "What is the capital of France?" \\
        --max-new-tokens 64 \\
        --sniff-every-k 5

Add --jsonl for one event per line (machine-readable, ready to forward as SSE
in the follow-up endpoint work).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Allow running as `python gpu/scripts/generate_stream.py` without PYTHONPATH=.
# Same trick as gpu/scripts/decode_parquet.py: prepend gpu/ so we can import
# nla_inference directly. Plain `from gpu.nla_inference` only resolves when
# the repo root is on sys.path (e.g. via uvicorn's package import).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from nla_inference import NLAClient  # noqa: E402

QWEN_BASE_MODEL = os.environ.get("QWEN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
QWEN_LAYER_INDEX = int(os.environ.get("QWEN_LAYER_INDEX", "20"))
ACTOR_DIR = os.environ.get("ACTOR_DIR", "./actor_hf")
SGLANG_URL = os.environ.get("SGLANG_URL", "http://localhost:30000")
DEVICE = os.environ.get("EXTRACTOR_DEVICE", "cuda")


class GenerativeExtractor:
    """Qwen base, resident, with a forward hook on layer K's residual stream.

    Same hook pattern as gpu.server.Extractor and scripts/extract_activations.py
    (decoder blocks return a tuple, output[0] is the residual). The difference
    is step() handles both prefill (T tokens, past_kv=None) and decode (1 token,
    past_kv from previous step). The captured tensor is always the LAST
    position's residual — for prefill that's the position whose logits we
    sample to get the first response token; for decode it's the new token.
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
    def step(
        self,
        input_ids: torch.Tensor,
        past_kv: Any,
    ) -> tuple[torch.Tensor, torch.Tensor, Any]:
        """One forward. Returns (last_logits[V], last_residual[d], new_past_kv).

        input_ids shape: [1, T] for prefill (past_kv=None) or [1, 1] for decode.
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
    """Greedy if T<=0, else softmax-sample. Cast to fp32 for sampling stability."""
    if temperature <= 0:
        return int(logits.argmax().item())
    probs = torch.softmax(logits.float() / temperature, dim=-1)
    return int(torch.multinomial(probs, 1).item())


@dataclass
class ActorTask:
    step: int
    spawned_at: float
    task: asyncio.Task[str]


@dataclass
class RunStats:
    tokens: int = 0
    t_start: float = 0.0
    t_first_token: float = 0.0
    t_end: float = 0.0
    actor_count: int = 0
    actor_total_latency: float = 0.0
    actor_first_spawn: float = float("inf")
    actor_last_done: float = 0.0


def emit(jsonl: bool, kind: str, t: float, **fields: Any) -> None:
    """One event line. Setup logs go to stderr; events go to stdout."""
    if jsonl:
        print(json.dumps({"t": round(t, 4), "type": kind, **fields}, ensure_ascii=False))
    elif kind == "token":
        print(f"[{t:7.3f}s] step={fields['step']:3d} token={fields['text']!r}")
    elif kind == "actor_spawn":
        print(f"[{t:7.3f}s] step={fields['step']:3d} actor spawned")
    elif kind == "nla_trace":
        print(f"[{t:7.3f}s] step={fields['step']:3d} nla={fields['text']!r}")
    sys.stdout.flush()


async def run(args: argparse.Namespace) -> None:
    extractor = GenerativeExtractor(args.qwen_base, args.qwen_layer, args.device)
    print(
        f"[actor] connecting to {args.sglang_url} (checkpoint={args.actor_dir})",
        file=sys.stderr,
    )
    actor = NLAClient(args.actor_dir, sglang_url=args.sglang_url)
    tokenizer = extractor.tokenizer

    if args.raw:
        ids = tokenizer(
            args.prompt, return_tensors="pt", add_special_tokens=True
        )["input_ids"]
    else:
        ids = tokenizer.apply_chat_template(
            [{"role": "user", "content": args.prompt}],
            add_generation_prompt=True,
            return_tensors="pt",
        )
    ids = ids.to(extractor.device)
    print(
        f"[run] prompt={ids.shape[-1]} tokens, generating up to {args.max_new_tokens}",
        file=sys.stderr,
    )

    stop_id = tokenizer.eos_token_id
    stats = RunStats(t_start=time.monotonic())
    pending: list[ActorTask] = []
    all_ids: list[int] = []
    prev_text = ""

    def now() -> float:
        return time.monotonic() - stats.t_start

    def spawn_actor(step: int, residual: torch.Tensor) -> None:
        if step % args.sniff_every_k != 0:
            return
        v = residual.float().cpu().numpy().astype(np.float32)
        spawned_at = now()
        stats.actor_first_spawn = min(stats.actor_first_spawn, spawned_at)
        stats.actor_count += 1
        # to_thread releases the GIL on the httpx socket read; create_task
        # schedules but the coroutine only starts after the next yield to the
        # loop (the asyncio.sleep(0) below). Without that yield we'd queue all
        # the tasks at the end of decoding and lose every overlap opportunity.
        coro = asyncio.to_thread(
            actor.generate,
            v,
            temperature=args.actor_temperature,
            max_new_tokens=args.actor_max_new_tokens,
        )
        task = asyncio.create_task(coro)
        pending.append(ActorTask(step=step, spawned_at=spawned_at, task=task))
        emit(args.jsonl, "actor_spawn", t=spawned_at, step=step)

    async def drain() -> None:
        for at in list(pending):
            if at.task.done():
                try:
                    text = at.task.result()
                except Exception as e:
                    text = f"<actor error: {e!r}>"
                done_at = now()
                stats.actor_total_latency += done_at - at.spawned_at
                stats.actor_last_done = max(stats.actor_last_done, done_at)
                emit(args.jsonl, "nla_trace", t=done_at, step=at.step, text=text)
                pending.remove(at)

    def emit_token(step: int, next_id: int) -> None:
        nonlocal prev_text
        all_ids.append(next_id)
        cur_text = tokenizer.decode(all_ids, skip_special_tokens=False)
        chunk = cur_text[len(prev_text):]
        prev_text = cur_text
        emit(args.jsonl, "token", t=now(), step=step, text=chunk)

    # Prefill.
    logits, residual, past_kv = extractor.step(ids, None)
    stats.t_first_token = now()
    next_id = sample(logits, args.temperature)
    emit_token(0, next_id)
    stats.tokens = 1
    spawn_actor(0, residual)
    await asyncio.sleep(0)
    await drain()

    # Decode loop.
    if next_id != stop_id:
        cur_ids = torch.tensor([[next_id]], device=extractor.device)
        for step in range(1, args.max_new_tokens):
            logits, residual, past_kv = extractor.step(cur_ids, past_kv)
            next_id = sample(logits, args.temperature)
            emit_token(step, next_id)
            stats.tokens += 1
            spawn_actor(step, residual)
            await asyncio.sleep(0)
            await drain()
            if next_id == stop_id:
                break
            cur_ids = torch.tensor([[next_id]], device=extractor.device)

    # Wait for stragglers.
    if pending:
        await asyncio.wait([at.task for at in pending])
        await drain()

    stats.t_end = now()
    _print_summary(stats, args.jsonl, prev_text)


def _print_summary(stats: RunStats, jsonl: bool, full_text: str) -> None:
    wallclock = stats.t_end
    tok_per_s = stats.tokens / wallclock if wallclock > 0 else 0.0
    actor_window = (
        stats.actor_last_done - stats.actor_first_spawn
        if stats.actor_count > 0
        else 0.0
    )
    overlap = stats.actor_total_latency / actor_window if actor_window > 0 else 0.0
    summary = {
        "tokens": stats.tokens,
        "wallclock_s": round(wallclock, 3),
        "tok_per_s": round(tok_per_s, 2),
        "ttft_s": round(stats.t_first_token, 3),
        "actor_count": stats.actor_count,
        "actor_total_latency_s": round(stats.actor_total_latency, 3),
        "actor_window_s": round(actor_window, 3),
        "overlap_factor": round(overlap, 2),
    }
    if jsonl:
        print(json.dumps({"t": round(wallclock, 4), "type": "summary", **summary}))
        return
    print()
    print("─── full output ─────────────────────────────────────────")
    print(full_text)
    print("─── summary ─────────────────────────────────────────────")
    print(f"  tokens generated:        {summary['tokens']}")
    print(f"  wallclock:               {summary['wallclock_s']}s")
    print(f"  throughput:              {summary['tok_per_s']} tok/s")
    print(f"  time-to-first-token:     {summary['ttft_s']}s")
    print(f"  actor calls:             {summary['actor_count']}")
    print(f"  ΣT_actor (per-task sum): {summary['actor_total_latency_s']}s")
    print(f"  actor wallclock window:  {summary['actor_window_s']}s")
    print(f"  overlap factor:          {summary['overlap_factor']}×")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--prompt",
        default="What is the capital of France? Answer in two short sentences.",
    )
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument(
        "--sniff-every-k",
        type=int,
        default=5,
        help="Fire actor.generate() on residual every K tokens (default: %(default)s)",
    )
    ap.add_argument(
        "--temperature", type=float, default=0.7, help="Qwen sampling; <=0 for greedy"
    )
    ap.add_argument("--actor-temperature", type=float, default=0.7)
    ap.add_argument("--actor-max-new-tokens", type=int, default=200)
    ap.add_argument("--actor-dir", default=ACTOR_DIR)
    ap.add_argument("--sglang-url", default=SGLANG_URL)
    ap.add_argument("--qwen-base", default=QWEN_BASE_MODEL)
    ap.add_argument("--qwen-layer", type=int, default=QWEN_LAYER_INDEX)
    ap.add_argument("--device", default=DEVICE)
    ap.add_argument("--raw", action="store_true", help="Skip chat template")
    ap.add_argument(
        "--jsonl", action="store_true", help="Emit JSONL events instead of human-readable"
    )
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
