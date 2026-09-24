"""Contract error shape ``{"error": {"code", "message"}}`` and the handlers that enforce it."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("gramdrishti.api")

HTTP_CODES = {400: "bad_request", 404: "not_found", 405: "method_not_allowed", 409: "conflict",
              422: "validation_error", 500: "internal_error", 503: "not_available"}


class ApiError(Exception):
    """Raise anywhere in a request to return the contract error shape."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def not_found(what: str) -> ApiError:
    """404 with code ``not_found``."""
    return ApiError(404, "not_found", what)


def error_body(code: str, message: str) -> dict:
    """The JSON body for an error."""
    return {"error": {"code": code, "message": message}}


def _validation_message(exc: RequestValidationError) -> str:
    parts = []
    for e in exc.errors():
        loc = ".".join(str(x) for x in e.get("loc", ()) if x not in ("query", "path", "body"))
        parts.append(f"{loc or 'request'}: {e.get('msg', 'invalid')}")
    return "; ".join(parts) or "Invalid request"


def install_handlers(app: FastAPI) -> None:
    """Register handlers so every error leaves the API in the contract shape."""

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(error_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            return JSONResponse(detail, status_code=exc.status_code)
        code = HTTP_CODES.get(exc.status_code, "error")
        return JSONResponse(error_body(code, str(detail)), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(error_body("validation_error", _validation_message(exc)), status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error", exc_info=exc)
        return JSONResponse(error_body("internal_error", "Internal server error"), status_code=500)
