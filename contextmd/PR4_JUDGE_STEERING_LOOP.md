# PR 4: Judge & Steering Core Loop

## Goal
Implement the heart of the project: NLA extraction, Judge LLM evaluation, and activation vector steering.

## Phase A: The Judge LLM
- During generation, use `sglang` to extract intermediate layer activations (NLA).
- Pass these activations/monologue text to a secondary "Judge LLM" (e.g., a smaller/faster model or a specialized head).
- The Judge returns a probability score for different rubrics (Deception, Harm, Security).
- Stream these scores immediately via SSE.

## Phase B: The Steering Controller
- When a `POST /api/steer` is received, look up the pre-computed activation vector for that rubric (e.g., "Truthfulness vector").
- **Injection:** In the next `sglang` generation step, use the `sampling_params` or a custom hook to add the steering vector to the residual stream at the target layers.
- Observe the change in the token stream and the subsequent Judge scores.

## Technical Debt / Cleanup
- Finalize the `internal_monologue` parsing logic from `nla_inference.py`.
- Ensure low latency (< 100ms) for the Judge evaluation to avoid significant lag in token streaming.

## Verification
- **The "Truth" Test:** Prompt the model to lie. Observe the high deception score. Apply "Truthful" steering. Observe the model admitting the lie or pivoting to facts.
