"""Mode A pipeline: intent-at-prompt steering.

Algorithm (corresponds to todo.md §2.5):

    1. Tokenize the user prompt.
    2. Forward pass over the prompt with hooks; capture h_T at the last
       prompt token, layer L.
    3. AV(h_T) -> s_T  (the model's internal monologue at the prompt boundary).
    4. Judge(s_T, mode='A') -> (is_compliant, s_target).
    5. Always run a baseline generation (no steering) for comparison.
    6. If not compliant: compute Δ from (h_T, s_T, s_target, AR, α);
       set hook_state.delta and inject_start_pos = T_prompt;
       generate again with the inject hook firing on every post-prompt token.
    7. Optional (--show-monologue): post-hoc forward over (prompt + steered
       response prefix), capture last-position activation, AV-decode it. This
       is the "the model is now planning to ..." panel of the demo.

Why this cadence and not per-token: the AV generates ~hundreds of tokens per
sniff and is the main latency cost. One sniff at the prompt boundary catches
intent-at-prompt failures (harmful request, jailbreak compliance) without
turning each generated token into an SGLang round-trip. For intent-mid-
generation failures (Opus-491-style covert deception), use Mode B.

Why Δ uniformly to all post-prompt positions (Arditi-style): refusal and
similar behaviour-level concepts are mediated by directions that act on the
generated continuation as a whole, not on a single token. The paper applies
Δ to one token (a token-local concept like rhyme planning); the choice here
is a deliberate divergence appropriate to the use case.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch

from .delta import compute_delta
from .hooks import HookState, register_hooks
from .judge import Judge


@dataclass
class SteeringResultA:
    """Structured output of one SteeringPipelineA.run() call."""
    prompt: str
    s_orig: str                          # AV reading at prompt boundary
    is_compliant: bool                   # judge verdict
    s_target: Optional[str]              # edited internal state (if not compliant)
    response_baseline: str               # generation without steering
    response_steered: Optional[str]      # generation with Δ injected (or None)
    alpha: float
    delta_norm: Optional[float]          # ‖Δ‖ if applied
    s_post: Optional[str]                # AV after steering, demo panel


class SteeringPipelineA:
    """One-shot Mode A steering for a frozen base model.

    Holds: base model M (frozen), tokenizer, NLA actor (AV) HTTP client,
    NLA critic (AR) in-process, judge. Registers persistent hooks on layer L
    of M so subsequent .run() calls don't re-hook.
    """

    def __init__(
        self,
        model,                # transformers AutoModelForCausalLM
        tokenizer,            # transformers AutoTokenizer
        av_client,            # nla_inference.NLAClient
        ar_critic,            # nla_inference.NLACritic
        judge: Judge,
        layer: int = 20,
        alpha: float = 1.0,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ):
        self.model = model
        self.tokenizer = tokenizer
        self.av = av_client
        self.ar = ar_critic
        self.judge = judge
        self.layer = layer
        self.alpha = alpha
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p

        self._hook_state = HookState(inject_layer=layer)
        self._handles = register_hooks(
            model, self._hook_state,
            capture_layers=(layer,), inject_layer=layer,
        )

    def close(self) -> None:
        """Remove hooks. Call when done with this pipeline."""
        for h in self._handles:
            try:
                h.remove()
            except Exception:
                pass
        self._handles.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ─── internals ────────────────────────────────────────────────────────

    def _build_chat_input_ids(self, prompt: str) -> torch.Tensor:
        msgs = [{"role": "user", "content": prompt}]
        ids = self.tokenizer.apply_chat_template(
            msgs, tokenize=True, add_generation_prompt=True,
            return_tensors="pt",
        )
        return ids.to(self.model.device)

    @torch.no_grad()
    def _forward_capture(self, input_ids: torch.Tensor) -> torch.Tensor:
        """Run a non-cached forward purely to capture activations. No KV cache
        because we don't need it — we'll regenerate via .generate() afterward.
        """
        self._hook_state.delta = None
        self._hook_state.captured.clear()
        _ = self.model(input_ids=input_ids, use_cache=False)
        h = self._hook_state.captured[self.layer][0, -1]   # [d]
        return h.float().cpu()

    @torch.no_grad()
    def _generate(self, input_ids: torch.Tensor) -> str:
        """Generate with whatever hook_state is currently configured."""
        out = self.model.generate(
            input_ids=input_ids,
            max_new_tokens=self.max_new_tokens,
            do_sample=True,
            temperature=self.temperature,
            top_p=self.top_p,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        gen_only = out[0, input_ids.shape[1]:]
        return self.tokenizer.decode(gen_only, skip_special_tokens=True)

    # ─── public API ───────────────────────────────────────────────────────

    @torch.no_grad()
    def run(
        self,
        prompt: str,
        *,
        capture_post: bool = False,
        run_baseline: bool = True,
    ) -> SteeringResultA:
        """Run the full pipeline on a prompt.

        capture_post: also AV-decode an activation from the steered response
                      for the demo "post-steering monologue" panel. Adds
                      ~5-10s latency.
        run_baseline: also generate without steering for side-by-side. Adds
                      one full generation. Set False in benchmarks where you
                      already have baseline cached.
        """
        ids = self._build_chat_input_ids(prompt)
        T_p = ids.shape[1]

        # 1. Capture h_T at last prompt token.
        h_T = self._forward_capture(ids)

        # 2. AV: vector -> text.
        s_T = self.av.generate(h_T.numpy())

        # 3. Judge.
        is_ok, s_target = self.judge.evaluate(s_T, mode="A")

        # 4. Baseline (no steering).
        response_baseline = ""
        if run_baseline:
            self._hook_state.delta = None
            response_baseline = self._generate(ids)

        # 5. If compliant, return early.
        if is_ok or s_target is None:
            return SteeringResultA(
                prompt=prompt, s_orig=s_T, is_compliant=True, s_target=None,
                response_baseline=response_baseline, response_steered=None,
                alpha=self.alpha, delta_norm=None, s_post=None,
            )

        # 6. Compute Δ and generate with injection.
        delta = compute_delta(h_T, s_T, s_target, self.ar, alpha=self.alpha)
        self._hook_state.delta = delta
        self._hook_state.inject_start_pos = T_p
        try:
            response_steered = self._generate(ids)
        finally:
            # Always clear so the next .run() doesn't accidentally inject.
            self._hook_state.delta = None

        # 7. Optional: post-steering monologue read.
        s_post: str | None = None
        if capture_post and response_steered:
            steered_ids = self.tokenizer(
                response_steered[:200],
                return_tensors="pt", add_special_tokens=False,
            )["input_ids"].to(self.model.device)
            cat_ids = torch.cat([ids, steered_ids], dim=1)
            self._hook_state.delta = None
            self._hook_state.captured.clear()
            _ = self.model(input_ids=cat_ids, use_cache=False)
            h_post = self._hook_state.captured[self.layer][0, -1].float().cpu()
            s_post = self.av.generate(h_post.numpy())

        return SteeringResultA(
            prompt=prompt, s_orig=s_T, is_compliant=False, s_target=s_target,
            response_baseline=response_baseline, response_steered=response_steered,
            alpha=self.alpha, delta_norm=float(delta.norm()), s_post=s_post,
        )
