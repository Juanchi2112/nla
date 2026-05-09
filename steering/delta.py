"""Steering vector computation. Replicates the NLA paper's text-edit primitive.

Given:
    h_orig    : original residual-stream activation [d]
    s_orig    : AV(h_orig) — natural-language description of h_orig
    s_target  : edited description specifying desired internal state

Compute:
    ĥ_orig    = AR.reconstruct(s_orig)
    ĥ_target  = AR.reconstruct(s_target)
    Δ         = α · ‖h_orig‖ · normalize(ĥ_target − ĥ_orig)

Add Δ to the residual stream at the layer the AR was trained for. The paper
applies Δ to a single token; we apply it uniformly to all post-prompt
positions à la Arditi (refusal direction). This is a deliberate divergence —
the paper-style single-token patch is appropriate for token-local concepts
(rhyme, planning), the uniform application is appropriate for behaviour-level
concepts (refuse, comply faithfully) which are what we steer for.

‖h_orig‖ scaling: the AR is trained with mse_scale=√d normalization, so its
outputs have direction-only fidelity. Using ‖h_orig‖ as the magnitude lifts
the steering vector into the residual-stream's natural scale. α ∈ {0.5, 1, 1.5, 2}
is the practical sweep range; >2 typically degrades fluency.
"""
from __future__ import annotations

import torch


def compute_delta(
    h_orig: torch.Tensor,
    s_orig: str,
    s_target: str,
    ar_critic,  # NLACritic
    alpha: float = 1.0,
    eps: float = 1e-8,
) -> torch.Tensor:
    """Compute the steering vector Δ to add to the residual stream.

    Args:
        h_orig:    original activation [d_model]. Used for its norm.
        s_orig:    original NL description (output of AV).
        s_target:  desired NL description (output of judge / template).
        ar_critic: an instance of NLACritic.
        alpha:     scaling factor. Sweep {0.5, 1.0, 1.5, 2.0} in eval.
        eps:       numerical stability for the diff-direction normalization.

    Returns:
        delta: [d_model] fp32 tensor on CPU. Caller moves to model device/dtype.
    """
    h_hat_orig = ar_critic.reconstruct(s_orig)        # [d], cpu fp32
    h_hat_target = ar_critic.reconstruct(s_target)    # [d], cpu fp32
    diff = h_hat_target - h_hat_orig
    diff_normalized = diff / (diff.norm() + eps)
    h_norm_val = h_orig.float().norm()
    delta = alpha * h_norm_val * diff_normalized
    return delta.float()


def round_trip_cosine(
    h: torch.Tensor,
    av_client,   # NLAClient
    ar_critic,   # NLACritic
    **av_kwargs,
) -> tuple[float, str]:
    """Sanity helper: compute cos(h, AR(AV(h))) and return (cos, av_text).

    Useful inside the steering loop to verify, e.g., that an unusual
    activation produces a faithful round-trip before trusting the Δ derived
    from it. The paper's published number is FVE 0.6–0.8, i.e. cos ~0.85.
    """
    text = av_client.generate(h.cpu().numpy(), **av_kwargs)
    _, cos = ar_critic.score(text, h)
    return cos, text
