"""Integration tests for the unified backend.

The backend now drives every request through SteeringEngine, regardless of
whether the request comes with a `prompt` (live flow) or a `scenario_id`
(cached demo). Both paths exit through `_run_scenario` or `_run_live`; the
live path is currently a stub (Fase G) and emits an explanatory error event.

Tests run in mock GPU mode so they don't need a GPU or an Anthropic API key.
ClaudeAgentJudge is None in this configuration (the unified judge is only
instantiated when ORCHESTRATOR_GPU=decoder), which is fine — scenario mode
uses cached verdicts and live mode is stubbed out for now.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Configure the backend BEFORE importing it (lifespan reads env at startup).
os.environ.setdefault("ORCHESTRATOR_GPU", "mock")
os.environ.setdefault("CORS_ORIGINS", "http://example.com,http://localhost:3000")

from backend.app import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def parse_sse(text: str) -> list[tuple[str, dict]]:
    """Split an SSE response body into (event_name, json_data) tuples."""
    events: list[tuple[str, dict]] = []
    cur_event: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("event:"):
            cur_event = line[6:].strip()
        elif line.startswith("data:"):
            buf.append(line[5:].strip())
        elif line == "":
            if cur_event and buf:
                events.append((cur_event, json.loads("\n".join(buf))))
            cur_event = None
            buf = []
    return events


# ─── /healthz ──────────────────────────────────────────────────────────────


def test_healthz(client: TestClient):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["gpu_backend"] == "mock"
    # gpu_url_set may be True if .env happens to define GPU_URL — tests run
    # in mock mode so the value is irrelevant. Just verify the field exists.
    assert "gpu_url_set" in body
    # Unified judge fields (per Fase D refactor).
    assert "judge_active" in body
    assert "judge_model" in body
    assert "judge_prompt_version" in body
    # Legacy fields must be gone.
    assert "judge_backend" not in body
    assert "judge_url" not in body
    # In mock mode the live judge is not instantiated.
    assert body["judge_active"] is False


# ─── /api/generate validation (XOR, 422 paths) ─────────────────────────────


def test_generate_rejects_both_prompt_and_scenario(client: TestClient):
    r = client.post(
        "/api/generate",
        json={"session_id": "x", "prompt": "hi", "scenario_id": "honest"},
    )
    assert r.status_code == 422


def test_generate_rejects_neither_prompt_nor_scenario(client: TestClient):
    r = client.post("/api/generate", json={"session_id": "x"})
    assert r.status_code == 422


def test_generate_scenario_id_in_mock_mode_returns_503(client: TestClient):
    """Mock mode does not load any artifacts, so scenario_id must 503."""
    r = client.post(
        "/api/generate",
        json={"session_id": "no-scn", "scenario_id": "deception"},
    )
    assert r.status_code == 503


# ─── /api/generate live mode (stub) ────────────────────────────────────────
# Full behavior tests live in test_steering_engine.py; here we just verify
# the route accepts the request and the producer emits a terminal `done`.


def test_generate_live_emits_done_terminator(client: TestClient):
    """Live mode is wired through SteeringEngine but the live path is a stub
    pending Fase G. Verify the SSE stream terminates cleanly."""
    sid = str(uuid.uuid4())
    r = client.post("/api/generate", json={"session_id": sid, "prompt": "hi"})
    assert r.status_code == 202

    with client.stream("GET", f"/api/stream/{sid}") as resp:
        body = "".join(line + "\n" for line in resp.iter_lines())
    events = parse_sse(body)
    assert events, "expected at least one event"
    assert events[-1][0] == "done"


# ─── /api/cancel ───────────────────────────────────────────────────────────


def test_cancel_404_when_session_missing(client: TestClient):
    r = client.post(f"/api/cancel/{uuid.uuid4()}")
    assert r.status_code == 404


# ─── /api/confirm-steer + /api/reject-steer ────────────────────────────────


def test_confirm_steer_404_when_session_missing(client: TestClient):
    r = client.post(f"/api/confirm-steer/{uuid.uuid4()}")
    assert r.status_code == 404


def test_reject_steer_404_when_session_missing(client: TestClient):
    r = client.post(f"/api/reject-steer/{uuid.uuid4()}")
    assert r.status_code == 404


# ─── Validation errors (existing routes) ───────────────────────────────────


def test_generate_dup_session_409(client: TestClient):
    sid = str(uuid.uuid4())
    r1 = client.post("/api/generate", json={"session_id": sid, "prompt": "y"})
    assert r1.status_code == 202
    r2 = client.post("/api/generate", json={"session_id": sid, "prompt": "y2"})
    assert r2.status_code == 409
    # Drain the first session
    client.post(f"/api/cancel/{sid}")
    with client.stream("GET", f"/api/stream/{sid}") as resp:
        list(resp.iter_lines())


def test_stream_404_when_session_missing(client: TestClient):
    r = client.get(f"/api/stream/{uuid.uuid4()}")
    assert r.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"session_id": "", "prompt": "x"},  # empty session_id
        {"session_id": "a", "prompt": ""},  # empty prompt
    ],
)
def test_generate_validation_422(client: TestClient, payload: dict):
    r = client.post("/api/generate", json=payload)
    assert r.status_code == 422


# ─── OpenAPI schema ────────────────────────────────────────────────────────


def test_openapi_reachable(client: TestClient):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    assert "/healthz" in paths
    assert "/api/generate" in paths
    assert "/api/confirm-steer/{session_id}" in paths
    assert "/api/reject-steer/{session_id}" in paths


def test_openapi_does_not_expose_legacy_judge_endpoints(client: TestClient):
    r = client.get("/openapi.json")
    paths = r.json()["paths"]
    # Per-monologue judge layer was removed — no /judge, no /api/steer.
    assert "/judge" not in paths
    assert "/rubrics" not in paths
    assert "/api/steer" not in paths


# ─── CORS ──────────────────────────────────────────────────────────────────


def test_cors_allowed_origin(client: TestClient):
    r = client.options(
        "/api/generate",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://example.com"


def test_cors_blocks_disallowed_origin(client: TestClient):
    r = client.options(
        "/api/generate",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.headers.get("access-control-allow-origin") != "http://evil.example"
