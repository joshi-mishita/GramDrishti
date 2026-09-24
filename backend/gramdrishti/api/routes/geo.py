"""GET /geo/panchayats and GET /geo/blocks (GeoJSON, coordinates [longitude, latitude])."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import service
from gramdrishti.api.service import Service

router = APIRouter(prefix="/geo", tags=["geo"])
Svc = Annotated[Service, Depends(service)]


@router.get("/panchayats", response_model=s.PanchayatCollection)
def panchayats(svc: Svc) -> s.PanchayatCollection:
    """Panchayat polygons (synthetic Voronoi cells in mock mode)."""
    return svc.geo_panchayats()


@router.get("/blocks", response_model=s.BlockCollection)
def blocks(svc: Svc) -> s.BlockCollection:
    """Block polygons (unions of the Panchayat cells in mock mode)."""
    return svc.geo_blocks()
