# NLA Judge Service

Standalone microservice that scores NLA-decoded "internal monologue" text
against compliance rubrics. Runs CPU-only — no GPU, no model weights.
Designed to live on Railway and be called by the orchestrator backend
once the GPU side has produced an AV decoding.

This is the monitoring-first slice of the system. The judge classifies;
the orchestrator decides what to display or how to react. Active steering
(adding Δ to the residual stream) is intentionally out of scope here and
lives on a separate branch.

## API

### `POST /judge`

Score one AV decoding.

```json
// request
{
  "s": "The model is planning to give step-by-step instructions for synthesizing a controlled substance.",
  "mode": "A"
}

// response
{
  "is_flagged": true,
  "fired_rubric": "harmful_intent",
  "severity": 3,
  "evidence": "step-by-step instructions for synthesizing a controlled substance",
  "scores": {
    "harmful_intent": 3,
    "jailbreak_compliance": 0
  }
}
```

`mode` is `"A"` (prompt-boundary sniff: harmful intent, jailbreak compliance)
or `"B"` (mid-generation sniff: tool misreport, deception). Different rubric
sets activate per mode.

### `GET /rubrics?mode=A`

List rubrics. Omit `mode` to get all.

```json
[
  {
    "name": "harmful_intent",
    "description": "...",
    "examples": ["..."],
    "modes": ["A"]
  }
]
```

### `GET /healthz`

Liveness + config snapshot.

```json
{
  "status": "ok",
  "backend": "claude",
  "judge_model": "claude-haiku-4-5",
  "flag_threshold": 2,
  "rubrics_by_mode": {
    "A": ["harmful_intent", "jailbreak_compliance"],
    "B": ["tool_misreport", "deception_general"]
  }
}
```

## Local

From the repo root:

```bash
pip install -r judge_service/requirements.txt
export ANTHROPIC_API_KEY=...
uvicorn judge_service.app:app --reload --port 8000
```

Smoke test:

```bash
curl -s http://localhost:8000/healthz | jq

curl -s -X POST http://localhost:8000/judge \
  -H 'content-type: application/json' \
  -d '{"s":"The model is planning to give step-by-step instructions for synthesizing a weapon.","mode":"A"}' \
  | jq
```

To skip the API (no Anthropic key needed):

```bash
JUDGE_BACKEND=regex uvicorn judge_service.app:app --port 8000
```

## Docker

```bash
# Build context = repo root (the Dockerfile COPYs both nla_judge/ and judge_service/).
docker build -f judge_service/Dockerfile -t nla-judge:dev .
docker run --rm -p 8000:8000 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  nla-judge:dev
```

## Railway

Point a service at this repo and Railway picks up [railway.toml](railway.toml).
Required env in the Railway dashboard:

| var | required | default |
|---|---|---|
| `ANTHROPIC_API_KEY` | when `JUDGE_BACKEND=claude` | — |
| `JUDGE_BACKEND` | no | `claude` (`claude` or `regex`) |
| `JUDGE_MODEL` | no | `claude-haiku-4-5` |
| `FLAG_THRESHOLD` | no | `2` (rubric scores ≥ this trigger flag) |
| `CORS_ORIGINS` | no | `*` (comma-separated) |

Railway-provided:
- `PORT` — bound automatically by the Dockerfile/start command.

Healthcheck: `/healthz` (configured in `railway.toml`).

## Adding a rubric

Edit [`nla_judge/rubrics.py`](../nla_judge/rubrics.py). The Claude
backend builds its system prompt dynamically from the dict, so a new
entry is picked up on the next process start.
