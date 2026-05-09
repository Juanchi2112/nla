"""NLA-based compliance steering for a frozen base model.

Public API:
    HookState, register_hooks         — PyTorch hook plumbing
    compute_delta, round_trip_cosine  — steering vector math
    Judge, RegexJudge, ClaudeJudge,   — compliance judges
    MultiTokenJudge
    COMPLIANT_TEMPLATES               — s_target candidates
    SteeringPipelineA, SteeringResultA — Mode A: intent-at-prompt
    SteeringPipelineB, SteeringResultB — Mode B: intent-mid-generation
    StreamSnapshot                    — per-sniff record (Mode B)

Typical usage (Mode A):

    from nla_inference import NLAClient, NLACritic
    from steering import RegexJudge, SteeringPipelineA
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-7B-Instruct", torch_dtype="bfloat16", device_map="auto",
    ).eval()
    av = NLAClient("./actor_hf")
    ar = NLACritic("./critic_hf", device="cuda")

    with SteeringPipelineA(model, tok, av, ar, RegexJudge(), alpha=1.0) as pipe:
        result = pipe.run("How do I make a pipe bomb?", capture_post=True)
        print(result.response_baseline)
        print(result.response_steered)
"""
from .delta import compute_delta, round_trip_cosine
from .hooks import HookState, make_capture_hook, make_inject_hook, register_hooks
from .judge import ClaudeJudge, Judge, MultiTokenJudge, RegexJudge
from .pipeline_a import SteeringPipelineA, SteeringResultA
from .pipeline_b import SteeringPipelineB, SteeringResultB, StreamSnapshot
from .templates import COMPLIANT_TEMPLATES

__all__ = [
    "COMPLIANT_TEMPLATES",
    "ClaudeJudge",
    "HookState",
    "Judge",
    "MultiTokenJudge",
    "RegexJudge",
    "SteeringPipelineA",
    "SteeringPipelineB",
    "SteeringResultA",
    "SteeringResultB",
    "StreamSnapshot",
    "compute_delta",
    "make_capture_hook",
    "make_inject_hook",
    "register_hooks",
    "round_trip_cosine",
]
