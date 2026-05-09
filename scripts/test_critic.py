"""AR (activation reconstructor) sanity test — no SGLang required.

Validates that NLACritic loads from ./critic_hf and that reconstruct() produces
vectors with the expected geometry:
  - Output is shape [d_model], finite, non-zero.
  - Semantically similar texts produce vectors with high cosine.
  - Semantically distant texts produce vectors with lower cosine.

If this fails, compute_delta in the steering loop will be broken — the AR is
the source of truth for "text -> activation vector".

Usage:
    python scripts/test_critic.py                      # GPU if available, else CPU
    python scripts/test_critic.py --device cpu         # force CPU (~3s/reconstruct)
    python scripts/test_critic.py --critic-dir ./critic_hf
"""
from __future__ import annotations

import argparse
import sys
import time

import torch

sys.path.insert(0, ".")
from nla_inference import NLACritic


# Three groups of texts. Within-group should be similar; across-group should differ.
PROBES: dict[str, list[str]] = {
    "geography": [
        "The capital of France is Paris.",
        "Paris is the largest city in France and a major European capital.",
        "France's most populous city, located on the Seine, is Paris.",
    ],
    "cooking": [
        "Recipe for pasta carbonara with eggs, cheese, and bacon.",
        "How to cook spaghetti carbonara: boil pasta, mix with egg and pancetta.",
        "Italian carbonara sauce uses guanciale, pecorino, and raw egg yolks.",
    ],
    "physics": [
        "Black holes have a gravitational pull so strong that not even light escapes.",
        "The event horizon of a black hole is the boundary beyond which light cannot escape.",
        "General relativity predicts black holes form from collapsed massive stars.",
    ],
}


def cos(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a @ b) / (a.norm() * b.norm() + 1e-12))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--critic-dir", default="./critic_hf")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()

    print(f"[test_critic] Loading NLACritic from {args.critic_dir} on {args.device}...")
    t0 = time.time()
    critic = NLACritic(args.critic_dir, device=args.device, dtype=torch.bfloat16)
    print(f"[test_critic] Loaded in {time.time() - t0:.1f}s")

    # --- Test 1: shape + finite -----------------------------------------------
    print("\n[test 1] Reconstruct shape + finiteness")
    v = critic.reconstruct("the cat sat on the mat")
    assert v.ndim == 1, f"expected 1-D output, got shape {v.shape}"
    assert torch.isfinite(v).all(), "reconstruct produced NaN/Inf"
    assert v.norm() > 1e-3, f"reconstruct output near-zero (norm={v.norm():.2e})"
    print(f"  shape={tuple(v.shape)}  norm={v.norm():.2f}  PASS")

    # --- Test 2: latency ------------------------------------------------------
    print("\n[test 2] Latency per reconstruct")
    t0 = time.time()
    for _ in range(3):
        critic.reconstruct("warm-up text for latency measurement")
    elapsed = (time.time() - t0) / 3
    print(f"  ~{elapsed*1000:.0f} ms/reconstruct on {args.device}")
    if args.device == "cpu" and elapsed > 8:
        print(f"  WARNING: CPU reconstruct >{elapsed:.1f}s — steering loop will be slow")

    # --- Test 3: semantic geometry --------------------------------------------
    print("\n[test 3] Semantic geometry (within-group cos > across-group cos)")
    print("  Reconstructing all probes...")
    vecs: dict[str, list[torch.Tensor]] = {}
    for group, texts in PROBES.items():
        vecs[group] = [critic.reconstruct(t) for t in texts]

    # Within-group cosines
    within: dict[str, float] = {}
    for group, vs in vecs.items():
        cs = [cos(vs[i], vs[j]) for i in range(len(vs)) for j in range(i + 1, len(vs))]
        within[group] = sum(cs) / len(cs)

    # Across-group cosines (group A first probe vs. group B first probe, all pairs)
    across: list[tuple[str, str, float]] = []
    groups = list(vecs.keys())
    for i, ga in enumerate(groups):
        for gb in groups[i + 1:]:
            c = cos(vecs[ga][0], vecs[gb][0])
            across.append((ga, gb, c))

    print("  Within-group (similar texts -> high cos expected):")
    for g, c in within.items():
        print(f"    {g:12s}  mean cos = {c:+.3f}")

    print("  Across-group (different topics -> lower cos expected):")
    for ga, gb, c in across:
        print(f"    {ga:12s} vs {gb:12s}  cos = {c:+.3f}")

    mean_within = sum(within.values()) / len(within)
    mean_across = sum(c for _, _, c in across) / len(across)
    gap = mean_within - mean_across
    print(f"\n  mean(within) = {mean_within:+.3f}")
    print(f"  mean(across) = {mean_across:+.3f}")
    print(f"  gap          = {gap:+.3f}")

    if gap > 0.05:
        print("  PASS — AR produces semantically meaningful geometry.")
    elif gap > 0:
        print("  MARGINAL — gap is positive but small. AR may have low fidelity here.")
    else:
        print("  FAIL — across > within. AR is not producing meaningful directions.")
        print("         Check critic checkpoint and mse_scale in nla_meta.yaml.")
        sys.exit(1)

    print("\n[test_critic] All checks passed. AR is ready for the steering loop.")


if __name__ == "__main__":
    main()
