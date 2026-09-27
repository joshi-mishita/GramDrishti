"""Request size limit and structured request logs (S14).

The request log records only what is needed to run the service: method, route template (``/farmers/
{farmer_id}``, never the filled-in path or the query string), status, duration, the X-Role header and the
data mode. It never records client addresses, user agents, request bodies, farmer ids or feedback.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from gramdrishti.api.errors import error_body

log = logging.getLogger("gramdrishti.api")
ROLES = {"officer", "farmer"}   # anything else is logged as "other"


class BodySizeLimit:
    """Answer 413 (contract error shape) when a body is larger than ``limit`` bytes.

    Checks ``Content-Length`` first. A body without one (chunked) is read into memory up to the limit and
    then replayed to the app, so it cannot get past the check either. Bodies here are small JSON documents.
    """

    def __init__(self, app: ASGIApp, limit: int) -> None:
        self.app, self.limit = app, limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return
        length = dict(scope["headers"]).get(b"content-length")
        if length is not None:
            if not length.isdigit() or int(length) > self.limit:
                await self._reject(send)
                return
            await self.app(scope, receive, send)
            return
        chunks, size, more = [], 0, True
        while more:
            msg = await receive()
            if msg["type"] != "http.request":
                return                                  # client went away
            chunks.append(msg.get("body", b""))
            size += len(chunks[-1])
            if size > self.limit:
                await self._reject(send)
                return
            more = msg.get("more_body", False)
        body, replayed = b"".join(chunks), False

        async def replay() -> Message:
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay, send)

    async def _reject(self, send: Send) -> None:
        body = json.dumps(error_body("payload_too_large",
                                     f"Request body is larger than {self.limit} bytes")).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


def route_template(request: Request) -> str:
    """The matched route's template, or ``unmatched`` (a raw path could carry ids)."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"


def request_record(request: Request, status: int, ms: float, mode: str) -> dict:
    """One access-log record without personal data."""
    role = (request.headers.get("X-Role") or "").strip().lower()
    shown = role if role in ROLES else ("other" if role else None)
    return {"event": "request", "method": request.method, "route": route_template(request),
            "status": status, "ms": round(ms, 1), "role": shown,
            "data_mode": mode}


class JsonFormatter(logging.Formatter):
    """One JSON object per line: time, level, logger, message and any ``extra={"fields": {...}}``."""

    def format(self, record: logging.LogRecord) -> str:
        out = {"time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
               "level": record.levelname.lower(), "logger": record.name, "message": record.getMessage()}
        out.update(getattr(record, "fields", {}))
        if record.exc_info:
            out["exception"] = self.formatException(record.exc_info)
        return json.dumps(out, ensure_ascii=False)


def configure_json_logging() -> None:
    """Send the ``gramdrishti`` loggers to stderr as JSON lines (once)."""
    root = logging.getLogger("gramdrishti")
    if any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    root.propagate = False


def timer() -> float:
    """Monotonic milliseconds."""
    return time.perf_counter() * 1000
