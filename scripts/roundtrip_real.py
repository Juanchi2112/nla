"""roundtrip_real.py — Validate AV+AR round-trip on real Qwen activations.

The strongest sanity test before investing in the steering loop:

    h_real = Qwen2.5-7B residual stream @ L20 on a real prompt
    s = AV(h_real) via SGLang  (text)
    ĥ = AR.reconstruct(s) in-process
    cos(h_real, ĥ) >= 0.85 ⇒ NLA pair faithfully closes the loop on real
    activations and compute_delta will produce meaningful steering directions.

If cos < 0.7, compute_delta will be noisy — the AR's text→vector mapping
won't correspond to the model's actual representations and the steering Δ
will point at artifacts rather than the desired behavioural shift.

Two-pass workflow (required when GPU < ~50 GB; the standard hackathon path):

    1. python scripts/extract_activations.py --output vectors.parquet
       (loads Qwen base on GPU, extracts L20 residuals, frees VRAM on exit)

    2. bash scripts/launch_sglang.sh                       # terminal 1
       (SGLang serves AV on the now-empty GPU)

    3. python scripts/roundtrip_real.py --parquet vectors.parquet
       (reads parquet, calls AV via HTTP, runs AR in-process,
        scores cos per row, summarizes)

On A100 80GB you can also run all three components simultaneously, but the
two-pass version works on every GPU ≥ 16 GB and is cheaper to debug.

Reports:
    - per-row text excerpt, AV output snippet, cos, MSE
    - summary: mean / median / min cos, % >= 0.7, % >= 0.85
    - verdict: PASS (>=0.85) / MARGINAL (>=0.7) / FAIL (<0.7)
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import torch

# Allow running as `python scripts/roundtrip_real.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nla_inference import NLAClient, NLACritic


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parquet", required=True,
                    help="Parquet from scripts/extract_activations.py")
    ap.add_argument("--actor-dir", default="./actor_hf",
                    help="AV checkpoint dir (must match what SGLang is serving)")
    ap.add_argument("--critic-dir", default="./critic_hf",
                    help="AR checkpoint dir")
    ap.add_argument("--sglang-url", default="http://localhost:30000")
    ap.add_argument("--device", default="cpu",
                    help="Device for AR. Default 'cpu' because SGLang usually "
                         "owns the GPU. Use 'cuda' on A100 80GB to speed up "
                         "(~10× faster reconstructs).")
    ap.add_argument("--n", type=int, default=20, help="rows to test")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-new-tokens", type=int, default=200)
    ap.add_argument("--verbose-rows", type=int, default=5,
                    help="Print full diagnostics for the first N rows")
    args = ap.parse_args()

    print(f"[roundtrip] AV client → {args.sglang_url}")
    av = NLAClient(args.actor_dir, sglang_url=args.sglang_url)

    print(f"[roundtrip] Loading AR critic on {args.device}")
    ar = NLACritic(args.critic_dir, device=args.device, dtype=torch.bfloat16)

    print(f"[roundtrip] Reading {args.parquet}")
    pf = pq.ParquetFile(args.parquet)
    table = pf.read()
    n_total = len(table)
    n = min(args.n, n_total)
    print(f"[roundtrip] {n_total} rows in parquet, testing {n}\n")

    cos_scores: list[float] = []
    mse_scores: list[float] = []
    norms: list[float] = []
    fails: list[tuple[int, str, float, str]] = []  # (idx, text_tail, cos, av_excerpt)

    for i in range(n):
        row = table.slice(i, 1).to_pylist()[0]
        h = np.array(row["activation_vector"], dtype=np.float32)
        text_excerpt = row["detokenized_text_truncated"]
        n_tok = row["n_raw_tokens"]
        norms.append(float(np.linalg.norm(h)))

        # AV: vector → text
        try:
            explanation = av.generate(
                h, temperature=args.temperature,
                max_new_tokens=args.max_new_tokens,
            )
        except Exception as e:
            print(f"  [{i:3d}] AV FAILED: {type(e).__name__}: {e}")
            continue

        # AR: text → vector, score against original. NLACritic.score does both
        # the reconstruct and the L2-normalized cosine/MSE under mse_scale=√d.
        try:
            mse, cos = ar.score(explanation, h)
        except Exception as e:
            print(f"  [{i:3d}] AR FAILED: {type(e).__name__}: {e}")
            continue

        cos_scores.append(cos)
        mse_scores.append(mse)
        if cos < 0.7:
            fails.append((i, text_excerpt[-80:], cos, explanation[:100]))

        if i < args.verbose_rows:
            print(f"  ─── [{i:3d}]  tok#{n_tok}  ‖h‖={norms[-1]:6.1f}  "
                  f"cos={cos:+.3f}  mse={mse:.3f}")
            print(f"       context-tail : ...{text_excerpt[-70:]!r}")
            print(f"       AV explanation: {explanation[:120]!r}")
            print()

    if not cos_scores:
        print("\n[roundtrip] FAIL — no rows produced a score. Check SGLang is up "
              "and the parquet matches the AV checkpoint (same base model, same layer).")
        sys.exit(2)

    mean_cos = statistics.mean(cos_scores)
    median_cos = statistics.median(cos_scores)
    min_cos = min(cos_scores)
    max_cos = max(cos_scores)
    over_70 = sum(1 for c in cos_scores if c >= 0.7) / len(cos_scores)
    over_85 = sum(1 for c in cos_scores if c >= 0.85) / len(cos_scores)
    mean_mse = statistics.mean(mse_scores)

    print("=" * 60)
    print(f"[roundtrip] {len(cos_scores)} successful rows  "
          f"(‖h‖ range: {min(norms):.0f}–{max(norms):.0f})")
    print(f"  mean cos     = {mean_cos:+.3f}")
    print(f"  median cos   = {median_cos:+.3f}")
    print(f"  min / max    = {min_cos:+.3f} / {max_cos:+.3f}")
    print(f"  % cos ≥ 0.70 = {over_70:.0%}")
    print(f"  % cos ≥ 0.85 = {over_85:.0%}")
    print(f"  mean MSE     = {mean_mse:.3f}   (range [0,4]; ~0.2 good, ~1 mediocre)")

    if fails:
        print(f"\n  {len(fails)} row(s) below cos=0.70:")
        for idx, txt, c, av_snip in fails[:10]:
            print(f"    [{idx:3d}] cos={c:+.3f}  ctx=...{txt!r}")
            print(f"           AV={av_snip!r}")

    print()
    if mean_cos >= 0.85:
        print("[roundtrip] ✓ PASS — high round-trip fidelity. "
              "Steering loop is viable; AR will produce meaningful directions.")
    elif mean_cos >= 0.70:
        print("[roundtrip] ~ MARGINAL — fidelity is usable but not great.")
        print("            Steering may still work; expect ~50% success rate as in paper.")
        print("            Consider checking high-norm activations or early positions.")
    else:
        print("[roundtrip] ✗ FAIL — round-trip fidelity too low.")
        print("            Steering Δ will be noise. Check before continuing:")
        print("              - injection_scale (Qwen=150) in nla_meta.yaml")
        print("              - embed_scale (Qwen=1.0, Gemma=√d)")
        print("              - prompt template matches sidecar exactly")
        print("              - layer 20 in extract_activations.py matches AV training")
        print("              - parquet from THIS run, not stale from a different model")
        sys.exit(1)


if __name__ == "__main__":
    main()
