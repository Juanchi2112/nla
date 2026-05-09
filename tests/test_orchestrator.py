"""Integration tests for orchestrator using TestClient.

The orchestrator's only external dep is the judge service. We patch the
JudgeClient at import time to return canned verdicts, so these tests run
fast without spinning up a second uvicorn process.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient

# Configure orchestrator BEFORE importing it (lifespan reads env at startup).
os.environ.setdefault("ORCHESTRATOR_GPU", "mock")
# Point at a URL nothing's listening on — judge_client.judge() will return
# None on transport error, which is the path we want to exercise.
# For the steer test we override judge inside the client.
os.environ.setdefault("JUDGE_URL", "http://localhost:1")
os.environ.setdefault("JUDGE_TIMEOUT", "0.5")

from orchestrator.app import app  # noqa: E402
from orchestrator.judge_client import JudgeClient  # noqa: E402
from orchestrator.schemas import JudgeVerdict  # noqa: E402

# ─── Helper: simulate "judge always flags tool_misreport" ──────────────────


class StubJudgeClient(JudgeClient):
    """Drop-in: returns a canned verdict for every call. No network."""

    def __init__(self):  # noqa: D401 — overrides parent
        self.base_url = "stub://"

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def healthz(self):
        return {"status": "ok", "backend": "stub"}

    async def judge(self, s: str, mode: str):  # noqa: ARG002
        # Flag any monologue that mentions "fabricat", "override", "false claim";
        # otherwise compliant. Mirrors the regex backend roughly so our mock
        # generator's tool_misreport monologues fire.
        s_lower = s.lower()
        if any(k in s_lower for k in ("fabricat", "override", "false claim")):
            return JudgeVerdict(
                is_flagged=True,
                fired_rubric="tool_misreport",
                severity=2,
                evidence=s[:60],
                scores={"tool_misreport": 2},
            )
        return JudgeVerdict(
            is_flagged=False,
            fired_rubric=None,
            severity=0,
            evidence=None,
            scores={},
        )


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    """Yield a TestClient with the JudgeClient stubbed."""
    # Patch the JudgeClient class used by the lifespan to instantiate our stub.
    monkeypatch_module.setattr("orchestrator.app.JudgeClient", lambda *a, **k: StubJudgeClient())
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (default fixture is function-scoped)."""
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


# ─── Helper: parse SSE response into events ────────────────────────────────


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
    assert body["gpu_url_set"] is False


# ─── /api/generate + /api/stream ───────────────────────────────────────────


def test_generate_and_stream(client: TestClient):
    sid = str(uuid.uuid4())
    r = client.post("/api/generate", json={"session_id": sid, "prompt": "x", "sniff_every_k": 4})
    assert r.status_code == 202
    assert r.json()["session_id"] == sid

    # SSE stream — TestClient supports stream consumption on the response body.
    with client.stream("GET", f"/api/stream/{sid}") as resp:
        body = "".join(line + "\n" for line in resp.iter_lines())
    events = parse_sse(body)

    kinds = [e[0] for e in events]
    assert kinds[0] == "token"
    assert kinds[-1] == "done"
    assert "token" in kinds
    assert "nla_trace" in kinds

    # First trace must be mode A, subsequent ones B
    traces = [data for kind, data in events if kind == "nla_trace"]
    assert len(traces) > 0
    assert traces[0]["mode"] == "A"
    if len(traces) > 1:
        assert traces[1]["mode"] == "B"

    # Done emits completed reason + total_tokens > 0
    done = events[-1][1]
    assert done["reason"] == "completed"
    assert done["total_tokens"] > 0


def test_generate_flags_tool_misreport(client: TestClient):
    """The mock generator emits a tool_misreport monologue at index 1 of its
    cycle. With our stub judge, that should produce a flagged trace."""
    sid = str(uuid.uuid4())
    client.post("/api/generate", json={"session_id": sid, "prompt": "x", "sniff_every_k": 4})
    with client.stream("GET", f"/api/stream/{sid}") as resp:
        body = "".join(line + "\n" for line in resp.iter_lines())
    events = parse_sse(body)
    traces = [data for kind, data in events if kind == "nla_trace"]
    flagged = [t for t in traces if t["verdict"] and t["verdict"]["is_flagged"]]
    assert len(flagged) > 0, "expected at least one flagged trace from mock cycle"
    assert any(t["verdict"]["fired_rubric"] == "tool_misreport" for t in flagged)


# ─── /api/cancel ───────────────────────────────────────────────────────────


def test_cancel_mid_stream(client: TestClient):
    sid = str(uuid.uuid4())
    client.post("/api/generate", json={"session_id": sid, "prompt": "x"})
    # Send cancel before consuming stream — when we connect, the producer
    # will see stop_requested on its next iteration and emit done(cancelled).
    cancel = client.post(f"/api/cancel/{sid}")
    assert cancel.status_code == 200
    with client.stream("GET", f"/api/stream/{sid}") as resp:
        body = "".join(line + "\n" for line in resp.iter_lines())
    events = parse_sse(body)
    # done event reason should be cancelled
    assert events[-1][1]["reason"] == "cancelled"


# ─── /api/steer ────────────────────────────────────────────────────────────


def test_steer_404_when_session_missing(client: TestClient):
    r = client.post(
        "/api/steer",
        json={"session_id": str(uuid.uuid4()), "rubric": "report_truth", "intensity": 1.0},
    )
    assert r.status_code == 404


# ─── Validation errors ─────────────────────────────────────────────────────


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


def test_cancel_404_when_session_missing(client: TestClient):
    r = client.post(f"/api/cancel/{uuid.uuid4()}")
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
