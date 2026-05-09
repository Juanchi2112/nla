"""PyTorch forward hooks for capturing and injecting at the residual stream.

Two hooks operate on the same transformer block (layer L):

    Capture hook:  reads the block's output tensor [B, T, d] and stores a
                   detached clone in HookState.captured. Pure passthrough,
                   does NOT modify the forward.

    Inject hook:   if HookState.delta is set, adds it to all positions
                   >= HookState.inject_start_pos. CRITICAL: returns the
                   modified tensor, otherwise the change does not propagate
                   to layers L+1, L+2, ..., N.

Why one shared HookState dataclass: capture and inject must coordinate. The
pipeline first runs a forward without injection to capture h_T, then derives
Δ from it, sets state.delta, and runs a second forward where inject fires.
Centralizing state avoids closures-over-mutable-globals.

Layer choice (L=20 for Qwen2.5-7B) is fixed by the NLA training: the AR was
trained to map text -> activation at exactly that layer. Inject anywhere else
and the Δ direction is meaningless.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import torch


@dataclass
class HookState:
    """Mutable state shared between capture + inject hooks.

    captured:           {layer_idx: Tensor[B, T, d]} — set by capture hooks.
    delta:              [d] vector to add at inject_layer; None disables injection.
    inject_start_pos:   add delta to positions >= this index (token position).
                        For Mode A: T_prompt (inject only on generated tokens).
                        For Mode B post-rollback: same.
    inject_layer:       which transformer block the inject hook fires on.
                        Must match the layer the AR was trained for (L=20 Qwen).
    """
    captured: dict[int, torch.Tensor] = field(default_factory=dict)
    delta: Optional[torch.Tensor] = None
    inject_start_pos: int = 0
    inject_layer: int = 20


def make_capture_hook(layer_idx: int, state: HookState):
    """Forward hook: stores a detached clone of the block output in state.captured.

    Qwen2 decoder blocks return Tensor[B, T, d] (sometimes wrapped in a tuple
    whose first element is the residual). We unwrap, detach (so the clone
    doesn't keep autograd alive), clone (so subsequent in-place ops upstream
    don't mutate it), and stash. Pure passthrough — output is not modified.
    """
    def hook(module, inputs, output):  # noqa: ARG001
        h = output[0] if isinstance(output, tuple) else output
        state.captured[layer_idx] = h.detach().clone()
        return output
    return hook


def make_inject_hook(layer_idx: int, state: HookState):
    """Forward hook: adds state.delta to residual stream from inject_start_pos.

    Returns the modified tensor (or tuple) so layers L+1..N see the change.
    Returning None or the original would mean the addition is silently dropped.

    No-ops when state.delta is None or layer_idx != state.inject_layer (so the
    same hook can be safely registered on multiple layers; only the configured
    one fires).
    """
    def hook(module, inputs, output):  # noqa: ARG001
        if state.delta is None or state.inject_layer != layer_idx:
            return output
        is_tuple = isinstance(output, tuple)
        h = output[0] if is_tuple else output

        seq_len = h.shape[1]
        start = state.inject_start_pos
        if start >= seq_len:
            return output  # nothing to inject yet

        new_h = h.clone()
        delta = state.delta.to(new_h.device, new_h.dtype)
        # delta is [d]; broadcast over batch and the slice [:, start:, :]
        new_h[:, start:, :] = new_h[:, start:, :] + delta
        return (new_h,) + output[1:] if is_tuple else new_h
    return hook


def register_hooks(
    model,
    state: HookState,
    *,
    capture_layers: tuple[int, ...] = (20,),
    inject_layer: Optional[int] = 20,
) -> list:
    """Register capture+inject hooks; returns handles for cleanup.

    Caller is responsible for calling .remove() on each handle (or letting the
    pipeline destructor do it). Forgetting to remove leaks hooks across calls
    and produces extremely confusing failures.
    """
    handles = []
    for li in capture_layers:
        h = model.model.layers[li].register_forward_hook(make_capture_hook(li, state))
        handles.append(h)
    if inject_layer is not None:
        h = model.model.layers[inject_layer].register_forward_hook(
            make_inject_hook(inject_layer, state)
        )
        handles.append(h)
    return handles
