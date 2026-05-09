"""Async HTTP client for the judge service.

Wraps POST /judge with sane timeouts. Designed to be polled mid-stream
(once per K tokens) so failures must not bring the orchestrator down —
on a transport / 5xx error we return None and the caller decides
whether to emit an error event or carry on without a verdict.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from .schemas import JudgeVerdict, Mode

log = logging.getLogger(__name__)


class JudgeClient:
    """Thin async wrapper. One client per app, reused across sessions."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        max_retries: int = 0,
    ):
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._http: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self._timeout),
        )

    async def stop(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def healthz(self) -> Optional[dict[str, Any]]:
        if self._http is None:
            return None
        try:
            r = await self._http.get("/healthz")
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            log.warning("judge healthz failed: %s", e)
            return None

    async def judge(self, s: str, mode: Mode) -> Optional[JudgeVerdict]:
        """Score one monologue. Returns None on transport / parse failure."""
        if self._http is None:
            log.warning("judge_client.judge called before .start()")
            return None
        try:
            r = await self._http.post("/judge", json={"s": s, "mode": mode})
            r.raise_for_status()
            payload = r.json()
        except httpx.HTTPStatusError as e:
            log.warning("judge HTTP %s: %s", e.response.status_code, e)
            return None
        except (httpx.HTTPError, ValueError) as e:
            log.warning("judge transport/parse error: %s", e)
            return None

        return JudgeVerdict(
            is_flagged=bool(payload.get("is_flagged")),
            fired_rubric=payload.get("fired_rubric"),
            severity=int(payload.get("severity", 0)),
            evidence=payload.get("evidence"),
            scores=dict(payload.get("scores") or {}),
        )
