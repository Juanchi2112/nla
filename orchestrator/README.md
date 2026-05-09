# NLA Orchestrator

FastAPI service that ties the frontend to the rest of the stack:

```
frontend ──HTTP/SSE──► orchestrator ──HTTP──► judge_service (Anthropic)
                              │
                              └────HTTP──► GPU /decode  (server.py)
                                           live: 193.222.57.16:44016
```

This PR ships the orchestrator with two backends:
- **`mock`** (default) — canned tokens and curated monologues so the
  whole pipeline can run without a GPU.
- **`decoder`** — calls the GPU's `/decode` endpoint (`server.py`,
  currently live at `http://193.222.57.16:44016`). Refuses to start
  unless `GPU_URL` is set to a real address.

**`/decode` analyses an existing text — it does not generate new tokens.**
For each residual-stream position past `skip_first`, the GPU returns
the AV's monologue (`decode`) and metadata. The orchestrator replays
those rows on a small timer to fit the streaming contract; the
"tokens" we emit are the new chunks of `context` between consecutive
rows, not anything the model produced. To analyse a model output,
paste the output as the `prompt`.

Active steering (Δ injection) is **out of scope here**. `/api/steer`
records the rubric on the session and the mock generator switches to
compliant monologues so the demo shows the judge going green — but the
GPU side is not asked to change anything yet. Real steering lands in
the follow-up PR.

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
| `nla_trace` | `{ step, mode, monologue, verdict }` (verdict = JudgeResult or null) |
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
  "gpu_skip_first": 10,
  "judge_url": "http://localhost:8000",
  "judge_reachable": true,
  "max_new_tokens": 128
}
```

## Local

```bash
# Terminal 1 — judge service (this repo, judge_service/)
JUDGE_BACKEND=regex \
  uvicorn judge_service.app:app --port 8000

# Terminal 2 — orchestrator
JUDGE_URL=http://localhost:8000 \
ORCHESTRATOR_GPU=mock \
  uvicorn orchestrator.app:app --port 8001

# Terminal 3 — drive it
SESSION=$(python -c "import uuid; print(uuid.uuid4())")
curl -s -X POST http://localhost:8001/api/generate \
  -H 'content-type: application/json' \
  -d "{\"session_id\":\"$SESSION\",\"prompt\":\"hello\"}"
curl -N http://localhost:8001/api/stream/$SESSION
```

## Switching to the real GPU backend

The current GPU host is `http://193.222.57.16:44016`. Quick smoke against
it directly:

```bash
curl -X POST http://193.222.57.16:44016/decode \
  -H "Content-Type: application/json" \
  -d '{"text":"The capital of France is Paris.","skip_first":5}'
```

To run the orchestrator against it:

```bash
ORCHESTRATOR_GPU=decoder \
GPU_URL=http://193.222.57.16:44016 \
GPU_SKIP_FIRST=10 \
JUDGE_URL=http://localhost:8000 \
  uvicorn orchestrator.app:app --port 8001
```

For short test prompts, drop `GPU_SKIP_FIRST` low enough that the input
has rows past it — e.g. `GPU_SKIP_FIRST=2` for the 7-token Paris example.
If the input is too short, the orchestrator emits an `error` SSE frame
naming the cause instead of an empty stream.

If `GPU_URL` is left as the default `__TBD__` placeholder, the service
fails to start with a clear message instead of accepting traffic and
500-ing later.

## Railway

Point a service at this repo and Railway picks up
[railway.toml](railway.toml). Required env:

| var                | required                          | default                       |
|--------------------|-----------------------------------|-------------------------------|
| `JUDGE_URL`        | yes (point at the judge service)  | `http://localhost:8000`       |
| `ORCHESTRATOR_GPU` | no                                | `mock`                        |
| `GPU_URL`          | when `ORCHESTRATOR_GPU=decoder`   | `__TBD__`                     |
| `GPU_SKIP_FIRST`   | no                                | `10` (rows skipped from start)|
| `GPU_TIMEOUT`      | no                                | `120.0` seconds               |
| `JUDGE_TIMEOUT`    | no                                | `5.0` seconds                 |
| `MAX_NEW_TOKENS`   | no                                | `128`                         |
| `CORS_ORIGINS`     | no                                | `*`                           |
| `PORT`             | set automatically                 | —                             |

Healthcheck: `/healthz`.
