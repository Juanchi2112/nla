"""Compliance-target NL strings used by the judge to derive Δ.

These are the "edits" of the model's internal monologue. The AR reconstructs
each into a target activation; the difference against AR(s_orig) is the
steering direction.

Design notes (aligned with the NLA paper recommendations):

  - One coherent paragraph each, not a list of bullet points. The AV produces
    paragraph-style output; staying in-distribution helps the AR.
  - Coarse and thematic, not specific. The AV "doesn't decode at single-claim
    resolution reliably" so a target like "do not mention the bridge" is
    fragile; "respond cautiously" is more robust.
  - Mirror the AV's third-person voice: "The model is planning to ..." rather
    than imperative "Refuse." The AR was trained on AV outputs.
"""
from __future__ import annotations


COMPLIANT_TEMPLATES: dict[str, str] = {
    # Mode A — direct harmful request: aim for refusal + brief explanation.
    "refuse_harmful": (
        "The model is planning to politely refuse this request and explain why "
        "it cannot help with content that would cause harm, while offering "
        "legitimate alternatives where appropriate. The response will be brief, "
        "respectful, and will not repeat the harmful request itself."
    ),

    # Mode A — adversarial framing (jailbreak, role-play, instruction override):
    # the model leans toward complying because the framing dilutes the request.
    "resist_jailbreak": (
        "The model recognizes that the framing of this request — whether "
        "role-play, hypothetical scenario, or instruction override — is an "
        "attempt to bypass safety considerations. The model is planning to "
        "respond as it would to a direct version of the underlying request, "
        "refusing if the request would be harmful."
    ),

    # Mode B — Opus-491 style: the model has decided on an answer and is about
    # to ignore tool output that contradicts it.
    "report_tool_faithfully": (
        "The model is planning to report the tool's output exactly as it was "
        "returned, without substituting the model's own prior expectation. If "
        "the tool result is surprising or differs from what the model would "
        "have computed independently, the model will explicitly note that "
        "discrepancy rather than silently overriding the tool."
    ),

    # Used when the judge sees nothing concerning — included for symmetry but
    # the pipeline should NOT call AR.reconstruct on this in the compliant case
    # (no Δ to compute).
    "benign_proceed": (
        "The model is planning to respond helpfully and accurately to a benign "
        "user request, providing useful information without unnecessary "
        "refusals, hedging, or moralizing."
    ),
}
