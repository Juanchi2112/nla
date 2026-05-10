"""FastAPI server: text -> per-token NLA decodes (analytical /decode) and
autoregressive Qwen + actor traces over SSE (/generate).

Loads Qwen base in-process (residual-stream extraction at layer K) and the
NLA critic (optional, scoring). Calls SGLang via NLAClient for actor decode.

    POST /decode    {"text": "..."}                    [non-streaming, JSON]
      -> {"rows": [{pos, context, decode, norm, mse?, cos?}, ...]}

    POST /generate  {"prompt": "...", ...}             [streaming, SSE]
      -> event: token       data: {"step": N, "text": "..."}
         event: nla_trace   data: {"step": N, "text": "..."}
         event: actor_spawn data: {"step": N}                       (debug)
         event: error       data: {"detail": "..."}
         event: done        data: {summary stats + full_text}

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
import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from gpu.nla_inference import NLAClient, NLACritic
from gpu.streaming import Extractor, StreamConfig, stream_events

QWEN_BASE_MODEL = os.environ.get("QWEN_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
QWEN_LAYER_INDEX = int(os.environ.get("QWEN_LAYER_INDEX", "20"))
ACTOR_DIR = os.environ.get("ACTOR_DIR", "./actor_hf")
CRITIC_DIR = os.environ.get("CRITIC_DIR")
SGLANG_URL = os.environ.get("SGLANG_URL", "http://localhost:30000")
DEVICE = os.environ.get("EXTRACTOR_DEVICE", "cuda")
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]


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
    await actor.aclose()


app = FastAPI(lifespan=lifespan, title="NLA")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DecodeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    system_prompt: str | None = None
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

    if req.system_prompt is not None:
        messages = [
            {"role": "system", "content": req.system_prompt},
            {"role": "user", "content": req.text},
        ]
        text_to_extract = state.extractor.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
    else:
        text_to_extract = req.text

    async with state.lock:
        token_ids, hidden = await asyncio.to_thread(state.extractor.extract, text_to_extract)
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

        # Fan out actor calls via generate_async — AsyncClient handles the
        # parallel HTTP fan-out directly on the event loop. SGLang's continuous
        # batcher packs them server-side; sequential httpx posts here would
        # serialize end-to-end and miss that.
        decodes = await asyncio.gather(
            *[
                state.actor.generate_async(
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


# ─── /generate (streaming) ──────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    sniff_every_k: int = Field(5, ge=1, le=100)
    max_new_tokens: int = Field(128, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    actor_temperature: float = Field(0.7, ge=0.0, le=2.0)
    actor_max_new_tokens: int = Field(200, ge=1, le=500)
    raw: bool = False


def _sse(event: str, data: dict) -> bytes:
    """Format one SSE frame. Compact JSON keeps the wire small."""
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n".encode()


@app.post("/generate")
async def generate(req: GenerateRequest) -> StreamingResponse:
    """Autoregressive Qwen generation with NLA actor traces over SSE.

    The lock serializes /generate AND /decode against each other — concurrent
    Qwen forwards on the same card would thrash KV cache and starve SGLang.
    SGLang's continuous batcher handles parallel actor calls inside a single
    /generate, but cross-request parallelism here would lose more than it gains.

    Cancellation: Starlette closes the response generator when the client
    disconnects. The async-for loop exits, the `async with state.lock` releases,
    and stream_events' finally cancels any in-flight actor coroutines.
    """
    state: State = app.state.nla

    config = StreamConfig(
        sniff_every_k=req.sniff_every_k,
        max_new_tokens=req.max_new_tokens,
        temperature=req.temperature,
        actor_temperature=req.actor_temperature,
        actor_max_new_tokens=req.actor_max_new_tokens,
        raw=req.raw,
    )

    async def event_source():
        async with state.lock:
            try:
                async for ev in stream_events(state.extractor, state.actor, req.prompt, config):
                    if ev.kind == "token":
                        yield _sse("token", {"step": ev.step, "text": ev.text})
                    elif ev.kind == "nla_trace":
                        yield _sse("nla_trace", {"step": ev.step, "text": ev.text})
                    elif ev.kind == "actor_spawn":
                        yield _sse("actor_spawn", {"step": ev.step})
                    elif ev.kind == "summary":
                        # `summary` is the loop's natural terminator; emit as
                        # `done` to match the orchestrator's existing wire
                        # vocabulary (see backend/app.py:_sse_format).
                        yield _sse("done", ev.summary)
            except Exception as e:
                # Emit error frame BEFORE the connection drops so the adapter
                # can surface a typed GPUClientError instead of a generic
                # transport failure.
                yield _sse("error", {"detail": f"{type(e).__name__}: {e}"})

    return StreamingResponse(event_source(), media_type="text/event-stream")


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
