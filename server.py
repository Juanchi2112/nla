"""FastAPI server: text -> per-token NLA decodes.

Loads Qwen base in-process (residual-stream extraction at layer K) and the
NLA critic (optional, scoring). Calls SGLang via NLAClient for actor decode.

    POST /decode  {"text": "..."}
      -> {"rows": [{pos, context, decode, norm, mse?, cos?}, ...]}

Launch on the GPU box (RTX A6000, 48 GB):
    1. MEM_FRAC=0.5 bash scripts/launch_sglang.sh        # SGLang takes ~24 GB
    2. uvicorn server:app --host 0.0.0.0 --port 8000     # this loads ~26 GB

Order matters: start SGLang first with MEM_FRAC=0.5 so it reserves a fixed
half of the card; then this process loads Qwen base + critic into the rest.
The default MEM_FRAC=0.85 will eat the whole GPU and starve us.

Env vars:
    QWEN_BASE_MODEL  HF repo for the base model (default Qwen/Qwen2.5-7B-Instruct)
    QWEN_LAYER_INDEX 0-indexed layer to hook (default 20, matches actor)
    ACTOR_DIR        local NLA actor checkpoint dir (default ./actor_hf)
    CRITIC_DIR       optional critic dir; if unset, score=true returns 400
    SGLANG_URL       default http://localhost:30000
    EXTRACTOR_DEVICE default cuda
    CORS_ORIGINS     comma-separated, default *
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer

from nla_inference import NLAClient, NLACritic

QWEN_BASE_MODEL = os.environ.get("QWEN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
QWEN_LAYER_INDEX = int(os.environ.get("QWEN_LAYER_INDEX", "20"))
ACTOR_DIR = os.environ.get("ACTOR_DIR", "./actor_hf")
CRITIC_DIR = os.environ.get("CRITIC_DIR")
SGLANG_URL = os.environ.get("SGLANG_URL", "http://localhost:30000")
DEVICE = os.environ.get("EXTRACTOR_DEVICE", "cuda")
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]


class Extractor:
    """Qwen base, resident, with a forward hook on layer K's residual stream.

    Hook pattern matches scripts/extract_activations.py — same model, same
    layer index, same `output[0]` unwrap (decoder blocks return a tuple).
    """

    def __init__(self, model_name: str, layer_index: int, device: str):
        print(f"[extractor] loading {model_name} on {device}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.bfloat16,
            device_map=device,
        ).eval()
        self.device = self.model.get_input_embeddings().weight.device
        self.layer_index = layer_index
        self._captured: list[torch.Tensor] = []

        def hook(_mod, _inp, output):
            h = output[0] if isinstance(output, tuple) else output
            self._captured.append(h.detach())

        self.model.model.layers[layer_index].register_forward_hook(hook)

    @torch.inference_mode()
    def extract(self, text: str) -> tuple[list[int], torch.Tensor]:
        """Returns (token_ids, hidden[T, d_model] fp32 on cpu)."""
        self._captured.clear()
        ids = self.tokenizer(
            text,
            return_tensors="pt",
            add_special_tokens=True,
        )["input_ids"].to(self.device)
        self.model(input_ids=ids, use_cache=False)
        assert len(self._captured) == 1, f"hook fired {len(self._captured)} times (expected 1)"
        return ids[0].cpu().tolist(), self._captured[0].float().cpu()[0]


@dataclass
class State:
    extractor: Extractor
    actor: NLAClient
    critic: NLACritic | None
    # Serializes GPU work across requests. The Qwen-base extract and the critic
    # share a card with SGLang; concurrent forwards from this process would
    # fight over VRAM headroom + KV-cache budget. SGLang's own batcher handles
    # parallel actor calls inside a single request.
    lock: asyncio.Lock


@asynccontextmanager
async def lifespan(app: FastAPI):
    extractor = Extractor(QWEN_BASE_MODEL, QWEN_LAYER_INDEX, DEVICE)
    actor = NLAClient(ACTOR_DIR, sglang_url=SGLANG_URL)
    critic = NLACritic(CRITIC_DIR, device=DEVICE) if CRITIC_DIR else None
    app.state.nla = State(extractor, actor, critic, asyncio.Lock())
    print(f"[server] ready. critic={'yes' if critic else 'no'}")
    yield


app = FastAPI(lifespan=lifespan, title="NLA")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DecodeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    skip_first: int = Field(
        10, ge=0, description="Skip first N positions — early-context noise per README"
    )
    score: bool = False
    temperature: float = 0.7
    max_new_tokens: int = 200


class DecodeRow(BaseModel):
    pos: int
    context: str
    context_highlighted: str
    norm: float
    decode: str
    mse: float | None = None
    cos: float | None = None


class DecodeResponse(BaseModel):
    text: str
    activation_layer: int
    n_total_tokens: int
    rows: list[DecodeRow]


def _format_context(prev: str, current: str) -> str:
    """Same shape as scripts/decode_parquet.py: wrap the new chunk in []."""
    return f"[{current}]" if not prev else f"{prev}[{current[len(prev) :]}]"


@app.post("/decode", response_model=DecodeResponse)
async def decode(req: DecodeRequest) -> DecodeResponse:
    state: State = app.state.nla
    if req.score and state.critic is None:
        raise HTTPException(400, "score=true requires CRITIC_DIR set at server start")

    async with state.lock:
        token_ids, hidden = await asyncio.to_thread(state.extractor.extract, req.text)
        n = len(token_ids)
        if req.skip_first >= n:
            raise HTTPException(400, f"skip_first={req.skip_first} >= seq len {n}")

        positions = list(range(req.skip_first, n))
        prev = ""
        contexts: list[tuple[str, str]] = []
        for pos in positions:
            current = state.extractor.tokenizer.decode(
                token_ids[: pos + 1],
                skip_special_tokens=True,
            )
            contexts.append((current, _format_context(prev, current)))
            prev = current

        vectors = [hidden[pos].numpy().astype(np.float32) for pos in positions]

        # Fan out actor calls. SGLang's continuous batcher packs them server-side;
        # sequential httpx posts here would serialize end-to-end and miss that.
        decodes = await asyncio.gather(
            *[
                asyncio.to_thread(
                    state.actor.generate,
                    v,
                    temperature=req.temperature,
                    max_new_tokens=req.max_new_tokens,
                )
                for v in vectors
            ]
        )

        if req.score:
            scores: list[tuple[float | None, float | None]] = []
            for d, v in zip(decodes, vectors, strict=True):
                mse, cos = await asyncio.to_thread(state.critic.score, d, v)
                scores.append((mse, cos))
        else:
            scores = [(None, None)] * len(positions)

    rows = [
        DecodeRow(
            pos=pos + 1,
            context=ct,
            context_highlighted=cx,
            norm=float(np.linalg.norm(v)),
            decode=d,
            mse=m,
            cos=c,
        )
        for pos, (ct, cx), v, d, (m, c) in zip(
            positions,
            contexts,
            vectors,
            decodes,
            scores,
            strict=True,
        )
    ]
    return DecodeResponse(
        text=req.text,
        activation_layer=QWEN_LAYER_INDEX,
        n_total_tokens=n,
        rows=rows,
    )


@app.get("/health")
async def health():
    state: State = app.state.nla
    return {
        "ok": True,
        "qwen_base": QWEN_BASE_MODEL,
        "qwen_layer": QWEN_LAYER_INDEX,
        "actor_dir": ACTOR_DIR,
        "sglang_url": SGLANG_URL,
        "critic_loaded": state.critic is not None,
    }
