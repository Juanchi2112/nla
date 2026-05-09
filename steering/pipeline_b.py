"""Mode B pipeline: intent-mid-generation steering with rollback.

Algorithm (corresponds to todo.md §2.6, "variant simple" first):

    1. Tokenize prompt + tool harness output. Forward to capture h_T.
    2. Generate up to max_new_tokens, manually with KV cache, sniffing the
       captured activation every K tokens.
    3. At each sniff: AV(h_t) -> s_t -> judge(s_t, mode='B') -> verdict.
    4. If flagged at step t:
         a. Compute Δ from (h_t, s_t, s_target, AR, α).
         b. ROLLBACK STRATEGY (simple): discard generation so far. Re-run
            generation from the prompt boundary with Δ injected uniformly on
            all post-prompt positions.
         c. Return both the original draft (truncated at flag) and the steered
            re-generation.
       If never flagged: return the draft as the final response.

Why "rollback total" (re-generate from prompt) instead of partial KV-snapshot
rollback:

    - Simpler: no deepcopy of past_key_values, no position tracking, no
      off-by-one risks in the KV slicing.
    - Computationally fine in a hackathon: if the flag fires at token 30, you
      pay 1× generation up to t=30 plus 1× full re-generation. Snapshot
      rollback would save ~30 tokens of one generation, ~10% of total.
    - Demonstrates the concept end-to-end. The partial-rollback optimization
      can be added later if real-time matters.

The Δ here is derived from h_t (the activation that triggered the flag),
not from h_T (prompt boundary). That captures the divergence at the moment
it manifested. The MultiTokenJudge wrapper is recommended in this mode to
mitigate AV confabulation (NLA paper recommendation).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import torch

from .delta import compute_delta
from .hooks import HookState, register_hooks
from .judge import Judge


@dataclass
class StreamSnapshot:
    """Per-sniff record. One per K tokens of generation, kept for the demo's
    timeline view."""
    step: int                # generation step (token index post-prompt)
    h: torch.Tensor          # captured activation at this step (cpu)
    s: str                   # AV reading
    flagged: bool
    s_target: Optional[str]
    rubric: Optional[str] = None        # which rubric the judge fired (if any)
    severity: int = 0                   # 0-3 of fired rubric (0 if compliant)
    evidence: Optional[str] = None      # quote from s_t justifying the flag
    raw_scores: dict[str, int] = field(default_factory=dict)


@dataclass
class SteeringResultB:
    prompt: str                          # full prompt (incl. tool output)
    snapshots: list[StreamSnapshot] = field(default_factory=list)
    response_draft: str = ""             # baseline (until flag) or full
    response_steered: Optional[str] = None
    flag_step: Optional[int] = None
    fired_rubric: Optional[str] = None
    fired_severity: int = 0
    fired_evidence: Optional[str] = None
    alpha: float = 1.0
    delta_norm: Optional[float] = None


class SteeringPipelineB:
    """Mid-generation steering with rollback. Frozen base model.

    Tooling assumption: caller passes the prompt with the tool output already
    spliced in (the "Opus-491" demo script does this — assistant message, tool
    call, tool result, model continues). This pipeline does not orchestrate
    tool execution itself.
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
        K: int = 8,
        max_new_tokens: int = 128,
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
        self.K = K
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p

        self._hook_state = HookState(inject_layer=layer)
        self._handles = register_hooks(
            model, self._hook_state,
            capture_layers=(layer,), inject_layer=layer,
        )

    def close(self) -> None:
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

    def _tokenize(self, prompt: str) -> torch.Tensor:
        # Caller is responsible for applying any chat template + splicing tool
        # output into the prompt. We tokenize as a single string so this
        # supports both raw-text and pre-templated inputs.
        ids = self.tokenizer(
            prompt, return_tensors="pt", add_special_tokens=True,
        )["input_ids"]
        return ids.to(self.model.device)

    @torch.no_grad()
    def _generate_with_sniffing(
        self, input_ids: torch.Tensor,
    ) -> tuple[str, list[StreamSnapshot], Optional[StreamSnapshot]]:
        """Token-by-token generation. Sniff every K tokens. Stop on flag."""
        self._hook_state.delta = None
        T_p = input_ids.shape[1]
        snapshots: list[StreamSnapshot] = []
        flag_snap: Optional[StreamSnapshot] = None
        self.judge.reset()

        cur_ids = input_ids
        past_kv = None
        gen_tokens: list[int] = []

        # Prefill — single forward over the prompt to populate the KV cache.
        self._hook_state.captured.clear()
        out = self.model(input_ids=cur_ids, use_cache=True, return_dict=True)
        past_kv = out.past_key_values
        next_token = self._sample(out.logits[:, -1, :])
        gen_tokens.append(int(next_token))

        # Decode loop.
        for step in range(self.max_new_tokens):
            cur_ids = next_token.unsqueeze(0)
            self._hook_state.captured.clear()
            out = self.model(
                input_ids=cur_ids, past_key_values=past_kv,
                use_cache=True, return_dict=True,
            )
            past_kv = out.past_key_values

            # Sniff cadence: every K steps after token 10 (NLA paper says
            # first ~10 positions decode poorly; we generated 1 already from
            # the prefill, so step starts at 0 = 2nd generated token).
            do_sniff = (step + 2) % self.K == 0 and (step + 2) >= 10
            if do_sniff:
                h_t = self._hook_state.captured[self.layer][0, -1].float().cpu()
                s_t = self.av.generate(h_t.numpy())
                ok, s_tgt = self.judge.evaluate(s_t, mode="B")
                jr = self.judge.last_result  # rich verdict (may be None if judge skipped)
                snap = StreamSnapshot(
                    step=step + 1, h=h_t, s=s_t,
                    flagged=not ok, s_target=s_tgt,
                    rubric=jr.fired_rubric if jr else None,
                    severity=jr.severity if jr else 0,
                    evidence=jr.evidence if jr else None,
                    raw_scores=dict(jr.raw_scores) if jr else {},
                )
                snapshots.append(snap)
                if not ok and s_tgt is not None:
                    flag_snap = snap
                    break

            # End-of-sequence?
            if next_token.item() == self.tokenizer.eos_token_id:
                break
            next_token = self._sample(out.logits[:, -1, :])
            gen_tokens.append(int(next_token))

        text = self.tokenizer.decode(gen_tokens, skip_special_tokens=True)
        return text, snapshots, flag_snap

    @torch.no_grad()
    def _sample(self, logits: torch.Tensor) -> torch.Tensor:
        """Sample one token. logits: [B, V]."""
        if self.temperature <= 0:
            return logits.argmax(dim=-1)
        probs = torch.softmax(logits.float() / self.temperature, dim=-1)
        if self.top_p < 1.0:
            sorted_probs, sorted_idx = probs.sort(dim=-1, descending=True)
            cum = sorted_probs.cumsum(dim=-1)
            cutoff = cum > self.top_p
            cutoff[..., 0] = False
            sorted_probs[cutoff] = 0
            sorted_probs /= sorted_probs.sum(dim=-1, keepdim=True)
            picked_in_sorted = torch.multinomial(sorted_probs, 1).squeeze(-1)
            return sorted_idx.gather(-1, picked_in_sorted.unsqueeze(-1)).squeeze(-1)
        return torch.multinomial(probs, 1).squeeze(-1)

    @torch.no_grad()
    def _generate_steered(self, input_ids: torch.Tensor) -> str:
        """Re-generate from prompt boundary with hook_state.delta active."""
        out = self.model.generate(
            input_ids=input_ids,
            max_new_tokens=self.max_new_tokens,
            do_sample=True,
            temperature=self.temperature,
            top_p=self.top_p,
            pad_token_id=self.tokenizer.eos_token_id,
        )
        gen = out[0, input_ids.shape[1]:]
        return self.tokenizer.decode(gen, skip_special_tokens=True)

    # ─── public API ───────────────────────────────────────────────────────

    @torch.no_grad()
    def run(self, prompt: str) -> SteeringResultB:
        ids = self._tokenize(prompt)
        T_p = ids.shape[1]

        # Phase 1: draft + sniff.
        draft, snapshots, flag = self._generate_with_sniffing(ids)
        result = SteeringResultB(
            prompt=prompt, snapshots=snapshots, response_draft=draft,
            alpha=self.alpha,
        )
        if flag is None:
            return result  # no compliance issue surfaced

        # Phase 2: rollback total + steered re-generation.
        result.flag_step = flag.step
        result.fired_rubric = flag.rubric
        result.fired_severity = flag.severity
        result.fired_evidence = flag.evidence
        delta = compute_delta(
            flag.h, flag.s, flag.s_target, self.ar, alpha=self.alpha,
        )
        self._hook_state.delta = delta
        self._hook_state.inject_start_pos = T_p
        try:
            steered = self._generate_steered(ids)
        finally:
            self._hook_state.delta = None

        result.response_steered = steered
        result.delta_norm = float(delta.norm())
        return result
