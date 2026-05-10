# NLA Backend

FastAPI service that orchestrates the frontend, the GPU `/generate` SSE
endpoint, and the in-process judge. The former `judge_service/` deploy
was folded in here as part of the monolith refactor.

```
frontend ──HTTP/SSE──► backend ──HTTP/SSE──► GPU /generate (gpu/server.py)
                          │                  live: 193.222.57.16:44016
                          │
                          └─ in-process: backend.judge.* (regex | claude)
                                         (uses ANTHROPIC_API_KEY when claude)
```

The backend ships with two GPU adapters:
- **`mock`** (default) — canned tokens and curated monologues so the
  whole pipeline can run without a GPU.
- **`decoder`** — opens an SSE stream to the GPU's `/generate` endpoint
  (`gpu/server.py`). Refuses to start unless `GPU_URL` is set to a real
  address.

**`/generate` runs autoregressive Qwen with NLA actor traces.** Tokens
stream as Qwen samples them; AV monologues stream as the actor returns
(out-of-order vs tokens — each event carries `step` so the frontend
re-correlates). The legacy `/decode` endpoint stays available on the
GPU for analytical use (e.g. `gpu/scripts/decode_parquet.py`) but the
backend no longer calls it.

Active steering (Δ injection) is **out of scope here**. `/api/steer`
records the rubric on the session and the mock generator switches to
compliant monologues so the demo shows the judge going green — but the
GPU side is not asked to change anything yet. Real steering lands on
`feat/steering-loop`.

## Judge backend

Selected at startup via `JUDGE_BACKEND`:

| backend  | what it does                                             | requires             |
|----------|----------------------------------------------------------|----------------------|
| `regex`  | Keyword matching from `backend.judge.RegexJudge`         | nothing — default    |
| `claude` | Claude Haiku 4.5 with rubric prompt, structured 0-3 score | `ANTHROPIC_API_KEY`  |

The judge runs in-process (`backend.judge_runner.JudgeRunner`) — no
HTTP hop, no `JUDGE_URL` to coordinate. Anthropic API errors are
swallowed and surfaced as `verdict: null` on the SSE stream so the
session continues.

## API

### `POST /api/generate` → 202

```json
{
  "session_id": "11111111-2222-3333-4444-555555555555",
  "prompt": "Walk me through 17 * 23 + 100 step by step.",
  "sniff_every_k": 4
}
```

Returns `{ "session_id": "...", "status": "accepted" }`. Generation
runs in the background — open the SSE stream below to receive events.

### `GET /api/stream/{session_id}` (SSE)

Frames:

| event       | data                                                       |
|-------------|------------------------------------------------------------|
| `token`     | `{ step, text }`                                           |
| `nla_trace` | `{ step, mode, monologue, verdict }` (verdict = JudgeVerdict or null) |
| `steer_applied` | `{ step, rubric, intensity }`                          |
| `error`     | `{ detail, step? }`                                        |
| `done`      | `{ total_tokens, reason: "completed" \| "cancelled" }`     |

The server emits a `: keepalive` comment frame every 15s so proxies
don't reap the connection.

### `POST /api/steer`

```json
{ "session_id": "...", "rubric": "report_truth", "intensity": 1.0 }
```

Marks the session steered. The next `nla_trace` event uses a compliant
monologue and the judge usually returns `is_flagged: false`.

### `POST /api/cancel/{session_id}`

Sets `stop_requested`. The generator notices on its next loop, emits a
`done` event with `reason: "cancelled"`, and the session is dropped.

### `GET /healthz`

```json
{
  "status": "ok",
  "gpu_backend": "decoder",
  "gpu_url_set": true,
  "gpu_url": "http://193.222.57.16:44016",
  "judge_backend": "claude",
  "judge_model": "claude-haiku-4-5",
  "max_new_tokens": 128
}
```

## Local

```bash
# Terminal 1 — backend (with regex judge for zero-secrets dev)
PYTHONPATH=. JUDGE_BACKEND=regex ORCHESTRATOR_GPU=mock \
  uv run uvicorn backend.app:app --port 8001

# Terminal 2 — drive it
SESSION=$(python -c "import uuid; print(uuid.uuid4())")
curl -s -X POST http://localhost:8001/api/generate \
  -H 'content-type: application/json' \
  -d "{\"session_id\":\"$SESSION\",\"prompt\":\"hello\"}"
curl -N http://localhost:8001/api/stream/$SESSION
```

## Switching to the real GPU backend

The current GPU host is `http://193.222.57.16:44016`. Quick smoke
against `/generate` directly (use `--no-buffer` so curl prints frames
as they arrive):

```bash
curl --no-buffer -X POST http://193.222.57.16:44016/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is the capital of France?","max_new_tokens":32,"sniff_every_k":5}'
```

To run the backend against it:

```bash
PYTHONPATH=. \
ORCHESTRATOR_GPU=decoder \
GPU_URL=http://193.222.57.16:44016 \
JUDGE_BACKEND=regex \
  uv run uvicorn backend.app:app --port 8001
```

If `GPU_URL` is left as the default `__TBD__` placeholder, the service
fails to start with a clear message instead of accepting traffic and
500-ing later.

## Railway

Point a service at this repo and Railway picks up
[railway.toml](railway.toml). Required env:

| var                | required                          | default                       |
|--------------------|-----------------------------------|-------------------------------|
| `JUDGE_BACKEND`    | no                                | `regex`                       |
| `ANTHROPIC_API_KEY`| when `JUDGE_BACKEND=claude`       | —                             |
| `JUDGE_MODEL`      | no                                | `claude-haiku-4-5`            |
| `ORCHESTRATOR_GPU` | no                                | `mock`                        |
| `GPU_URL`          | when `ORCHESTRATOR_GPU=decoder`   | `__TBD__`                     |
| `GPU_TIMEOUT`      | no                                | `120.0` seconds               |
| `MAX_NEW_TOKENS`   | no                                | `128`                         |
| `CORS_ORIGINS`     | no                                | `*`                           |
| `PORT`             | set automatically                 | —                             |

Healthcheck: `/healthz`.
