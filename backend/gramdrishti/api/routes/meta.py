"""GET /health and GET /meta."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import service
from gramdrishti.api.service import Service

router = APIRouter(tags=["meta"])
Svc = Annotated[Service, Depends(service)]


@router.get("/health", response_model=s.Health)
def health(svc: Svc) -> s.Health:
    """Liveness check."""
    return svc.health()


@router.get("/meta", response_model=s.Meta)
def meta(svc: Svc) -> s.Meta:
    """District, data mode, API version, demo issue dates (with labels), languages, crops, variables."""
    return svc.meta()
