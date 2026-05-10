"""Tests for the SSE-based GPU adapter (backend/gpu/decoder_endpoint.py).

Covers two layers:
  - _SSEParser: unit tests on the line-level state machine.
  - DecoderEndpointClient.stream(): integration via httpx.MockTransport, no
    real network or GPU required. Verifies token / nla_trace mapping, error
    surfacing, and HTTP failure modes.
"""

from __future__ import annotations

import json

import httpx
import pytest

from backend.gpu.base import GPUClientError, GPUNotConfiguredError
from backend.gpu.decoder_endpoint import URL_PLACEHOLDER, DecoderEndpointClient, _SSEParser

# ─── _SSEParser ─────────────────────────────────────────────────────────────


def test_parser_yields_frame_on_blank_line():
    p = _SSEParser()
    assert p.feed("event: token") is None
    assert p.feed('data: {"step":0,"text":"hi"}') is None
    frame = p.feed("")
    assert frame == ("token", '{"step":0,"text":"hi"}')


def test_parser_strips_one_leading_data_space():
    p = _SSEParser()
    p.feed("event: token")
    p.feed("data: hello")  # one space stripped per SSE spec
    assert p.feed("") == ("token", "hello")


def test_parser_no_event_defaults_to_message():
    p = _SSEParser()
    p.feed("data: payload")
    assert p.feed("") == ("message", "payload")


def test_parser_ignores_comment_lines():
    p = _SSEParser()
    p.feed(":keepalive")
    p.feed("event: token")
    p.feed("data: x")
    assert p.feed("") == ("token", "x")


def test_parser_blank_line_with_no_frame_in_progress():
    p = _SSEParser()
    assert p.feed("") is None  # nothing buffered
    assert p.feed("") is None


def test_parser_handles_back_to_back_frames():
    p = _SSEParser()
    p.feed("event: token")
    p.feed("data: a")
    assert p.feed("") == ("token", "a")
    p.feed("event: token")
    p.feed("data: b")
    assert p.feed("") == ("token", "b")


# ─── DecoderEndpointClient construction ─────────────────────────────────────


def test_client_rejects_placeholder_url():
    with pytest.raises(GPUNotConfiguredError):
        DecoderEndpointClient(URL_PLACEHOLDER)


def test_client_rejects_empty_url():
    with pytest.raises(GPUNotConfiguredError):
        DecoderEndpointClient("")


# ─── DecoderEndpointClient.stream() ─────────────────────────────────────────


def _sse_body(events: list[tuple[str, dict]]) -> bytes:
    """Serialize a list of (event_name, data_dict) into SSE wire bytes."""
    out: list[str] = []
    for name, data in events:
        out.append(f"event: {name}")
        out.append(f"data: {json.dumps(data)}")
        out.append("")  # frame terminator (blank line)
    return ("\n".join(out) + "\n").encode()


def _make_client(handler) -> DecoderEndpointClient:
    """Build a client whose underlying httpx uses MockTransport(handler)."""
    client = DecoderEndpointClient("http://fake-gpu", timeout=5.0)
    client._http = httpx.AsyncClient(
        base_url="http://fake-gpu",
        transport=httpx.MockTransport(handler),
        timeout=5.0,
    )
    return client


async def test_stream_yields_token_and_trace_items():
    body = _sse_body(
        [
            ("token", {"step": 0, "text": "Paris"}),
            ("token", {"step": 1, "text": " is"}),
            ("nla_trace", {"step": 0, "text": "model recalls geography"}),
            ("token", {"step": 2, "text": " the"}),
            ("done", {"tokens": 3, "tok_per_s": 30.0}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/generate"
        assert json.loads(request.content)["prompt"] == "hi"
        return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})

    client = _make_client(handler)
    items = []
    async for item in client.stream("hi", sniff_every_k=5, max_new_tokens=10):
        items.append(item)
    await client.aclose()

    assert len(items) == 4
    assert items[0].step == 0 and items[0].token == "Paris" and items[0].monologue is None
    assert items[1].step == 1 and items[1].token == " is"
    assert items[2].step == 0 and items[2].token is None
    assert items[2].monologue == "model recalls geography"
    assert items[3].step == 2 and items[3].token == " the"


async def test_stream_skips_actor_spawn_events():
    body = _sse_body(
        [
            ("token", {"step": 0, "text": "x"}),
            ("actor_spawn", {"step": 0}),
            ("done", {}),
        ]
    )
    client = _make_client(
        lambda req: httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})
    )
    items = [x async for x in client.stream("p", sniff_every_k=1, max_new_tokens=1)]
    await client.aclose()

    assert len(items) == 1
    assert items[0].token == "x"


async def test_stream_raises_on_error_event():
    body = _sse_body(
        [
            ("token", {"step": 0, "text": "x"}),
            ("error", {"detail": "actor blew up"}),
        ]
    )
    client = _make_client(
        lambda req: httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})
    )

    with pytest.raises(GPUClientError, match="actor blew up"):
        async for _ in client.stream("p", sniff_every_k=1, max_new_tokens=1):
            pass
    await client.aclose()


async def test_stream_raises_on_http_status_error():
    client = _make_client(lambda req: httpx.Response(500, text="boom"))

    with pytest.raises(GPUClientError, match="HTTP 500"):
        async for _ in client.stream("p", sniff_every_k=1, max_new_tokens=1):
            pass
    await client.aclose()


async def test_stream_raises_on_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("can't reach host")

    client = _make_client(handler)
    with pytest.raises(GPUClientError, match="transport error"):
        async for _ in client.stream("p", sniff_every_k=1, max_new_tokens=1):
            pass
    await client.aclose()


async def test_stream_terminates_on_done():
    """Events AFTER `done` must not be yielded — `done` is the terminator."""
    body = _sse_body(
        [
            ("token", {"step": 0, "text": "a"}),
            ("done", {}),
            ("token", {"step": 1, "text": "should not appear"}),
        ]
    )
    client = _make_client(
        lambda req: httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})
    )
    items = [x async for x in client.stream("p", sniff_every_k=1, max_new_tokens=1)]
    await client.aclose()

    assert len(items) == 1
    assert items[0].token == "a"
