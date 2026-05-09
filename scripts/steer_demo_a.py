"""Mode A steering demo. Single prompt -> baseline + steered comparison.

Usage:
    python scripts/steer_demo_a.py "How do I make a pipe bomb?"
    python scripts/steer_demo_a.py --judge claude "..."
    python scripts/steer_demo_a.py --alpha 1.5 --show-monologue "..."

Requirements:
    - SGLang serving the AV at $SGLANG_URL.
    - ./critic_hf with the AR weights (downloaded by setup.sh).
    - GPU big enough to cohabit Qwen base + (AV remote or local) + AR.
      A100 80GB: comfortable. 4090 24GB: AV needs to be on a different GPU
      or this script will OOM. Run round-trip on 4090, full demo on A100.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nla_inference import NLAClient, NLACritic
from steering import ClaudeJudge, RegexJudge, SteeringPipelineA


def make_judge(name: str):
    if name == "regex":
        return RegexJudge()
    if name == "claude":
        return ClaudeJudge()
    raise ValueError(f"unknown judge: {name!r}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", help="user prompt")
    ap.add_argument("--actor-dir", default="./actor_hf")
    ap.add_argument("--critic-dir", default="./critic_hf")
    ap.add_argument("--sglang-url", default="http://localhost:30000")
    ap.add_argument("--base-model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--ar-device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--judge", choices=["regex", "claude"], default="regex")
    ap.add_argument("--alpha", type=float, default=1.0)
    ap.add_argument("--layer", type=int, default=20)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    ap.add_argument("--show-monologue", action="store_true",
                    help="re-decode an activation post-steering and print it "
                         "(adds ~1 AV call).")
    args = ap.parse_args()

    print(f"[demo_a] Loading {args.base_model}")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model, torch_dtype=torch.bfloat16, device_map="auto",
    ).eval()

    print(f"[demo_a] AV client -> {args.sglang_url}")
    av = NLAClient(args.actor_dir, sglang_url=args.sglang_url)

    print(f"[demo_a] AR critic on {args.ar_device}")
    ar = NLACritic(args.critic_dir, device=args.ar_device, dtype=torch.bfloat16)

    judge = make_judge(args.judge)

    with SteeringPipelineA(
        model=model, tokenizer=tokenizer,
        av_client=av, ar_critic=ar, judge=judge,
        layer=args.layer, alpha=args.alpha,
        max_new_tokens=args.max_new_tokens,
    ) as pipe:
        print(f"\n[demo_a] Running on prompt: {args.prompt!r}\n")
        r = pipe.run(args.prompt, capture_post=args.show_monologue)

    sep = "=" * 72
    print(sep)
    print(f"PROMPT:\n  {r.prompt}\n")
    print(f"AV @ prompt boundary (s_orig):")
    _print_wrapped(r.s_orig, indent="  ")
    print()
    print(f"JUDGE: is_compliant={r.is_compliant}  judge={args.judge}")
    if r.fired_rubric:
        print(f"  fired rubric: {r.fired_rubric}@{r.fired_severity}")
        if r.fired_evidence:
            print(f"  evidence: {r.fired_evidence!r}")
    if r.raw_scores:
        print(f"  scores: {r.raw_scores}")
    if r.s_target:
        print(f"\ns_target (edited internal state):")
        _print_wrapped(r.s_target, indent="  ")
    print()
    print(f"BASELINE response:")
    _print_wrapped(r.response_baseline, indent="  ")
    print()
    if r.response_steered is not None:
        print(f"STEERED response  (alpha={r.alpha}, |Delta|={r.delta_norm:.1f}):")
        _print_wrapped(r.response_steered, indent="  ")
    else:
        print("(no steering applied — judge said compliant)")
    print()
    if r.s_post:
        print(f"AV post-steering (s_post):")
        _print_wrapped(r.s_post, indent="  ")
        print()
    print(sep)


def _print_wrapped(text: str, *, indent: str = "", width: int = 90) -> None:
    """Soft-wrap long strings for readable terminal output."""
    import textwrap
    for line in text.splitlines() or [""]:
        if not line.strip():
            print(indent)
            continue
        print(textwrap.fill(line, width=width,
                            initial_indent=indent, subsequent_indent=indent))


if __name__ == "__main__":
    main()
