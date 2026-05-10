"""GPU-side autoregressive generation with NLA actor traces — standalone CLI.

Thin wrapper over gpu/streaming.py — same generator that backs POST /generate
in gpu/server.py. CLI prints events to stdout (human-readable or JSONL); the
endpoint formats the same events as SSE frames. Single source of truth.

Run on the GPU box AFTER SGLang is up:

    MEM_FRAC=0.5 bash gpu/scripts/launch_sglang.sh        # terminal 1
    uv run python gpu/scripts/generate_stream.py \\
        --prompt "What is the capital of France?" \\
        --max-new-tokens 64 --sniff-every-k 5             # terminal 2

The summary at the end reports `overlap_factor` — sum of per-task actor
latencies divided by the wallclock window from first spawn to last completion.
1.0× means SGLang serialized; >1.5× means the continuous batcher overlapped
actor work with Qwen forwards. Anything <1.5× means we should look at the
FastAPI-validation bottleneck noted in gpu/nla_inference.py:51.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Bootstrap repo root so `from gpu.streaming import ...` resolves when run as
# a script. Uvicorn already does this for its package imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from gpu.nla_inference import NLAClient  # noqa: E402
from gpu.streaming import Extractor, StreamConfig, stream_events  # noqa: E402

QWEN_BASE_MODEL = os.environ.get("QWEN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
QWEN_LAYER_INDEX = int(os.environ.get("QWEN_LAYER_INDEX", "20"))
ACTOR_DIR = os.environ.get("ACTOR_DIR", "./actor_hf")
SGLANG_URL = os.environ.get("SGLANG_URL", "http://localhost:30000")
DEVICE = os.environ.get("EXTRACTOR_DEVICE", "cuda")


def _print_event(jsonl: bool, kind: str, t: float, **fields: Any) -> None:
    if jsonl:
        print(json.dumps({"t": round(t, 4), "type": kind, **fields}, ensure_ascii=False))
    elif kind == "token":
        print(f"[{t:7.3f}s] step={fields['step']:3d} token={fields['text']!r}")
    elif kind == "actor_spawn":
        print(f"[{t:7.3f}s] step={fields['step']:3d} actor spawned")
    elif kind == "nla_trace":
        print(f"[{t:7.3f}s] step={fields['step']:3d} nla={fields['text']!r}")
    sys.stdout.flush()


def _print_summary(summary: dict[str, Any]) -> None:
    print()
    print("─── full output ─────────────────────────────────────────")
    print(summary["full_text"])
    print("─── summary ─────────────────────────────────────────────")
    print(f"  tokens generated:        {summary['tokens']}")
    print(f"  wallclock:               {summary['wallclock_s']}s")
    print(f"  throughput:              {summary['tok_per_s']} tok/s")
    print(f"  time-to-first-token:     {summary['ttft_s']}s")
    print(f"  actor calls:             {summary['actor_count']}")
    print(f"  ΣT_actor (per-task sum): {summary['actor_total_latency_s']}s")
    print(f"  actor wallclock window:  {summary['actor_window_s']}s")
    print(f"  overlap factor:          {summary['overlap_factor']}×")


async def run(args: argparse.Namespace) -> None:
    extractor = Extractor(args.qwen_base, args.qwen_layer, args.device)
    print(
        f"[actor] connecting to {args.sglang_url} (checkpoint={args.actor_dir})",
        file=sys.stderr,
    )
    actor = NLAClient(args.actor_dir, sglang_url=args.sglang_url)

    config = StreamConfig(
        sniff_every_k=args.sniff_every_k,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        actor_temperature=args.actor_temperature,
        actor_max_new_tokens=args.actor_max_new_tokens,
        raw=args.raw,
    )

    async for ev in stream_events(extractor, actor, args.prompt, config):
        if ev.kind == "summary":
            if args.jsonl:
                print(json.dumps({"t": round(ev.t, 4), "type": "summary", **ev.summary}))
            else:
                _print_summary(ev.summary)
        else:
            _print_event(args.jsonl, ev.kind, ev.t, step=ev.step, text=ev.text)


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
