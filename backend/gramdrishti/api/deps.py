"""FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from gramdrishti.api.schemas import ErrorResponse
from gramdrishti.api.service import Service

# Error responses documented on every route (the handlers in errors.py produce this shape).
ERRORS = {404: {"model": ErrorResponse, "description": "Unknown id or issue date"},
          422: {"model": ErrorResponse, "description": "Invalid parameters"}}
ERRORS_400 = {**ERRORS, 400: {"model": ErrorResponse, "description": "Bad request"}}
ERRORS_503 = {**ERRORS, 503: {"model": ErrorResponse,
                              "description": "No forecast snapshot, or placeholder in real mode"}}


def service(request: Request) -> Service:
    """The app's single Service instance."""
    return request.app.state.service
