"""Verification, impact and data quality.

PLACEHOLDER: verification and impact numbers are seeded fake values under data_mode "mock" until the
verification job (S10). Data quality is computed from the station files.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import ERRORS, ERRORS_503, service
from gramdrishti.api.service import Service

router = APIRouter(tags=["verification"])
Svc = Annotated[Service, Depends(service)]


@router.get("/verification/summary", response_model=s.VerificationSummary, responses=ERRORS_503)
def summary(svc: Svc) -> s.VerificationSummary:
    """Model against baselines B0, B1, B2 per variable, with 95% intervals of skill."""
    return svc.verification_summary()


@router.get("/verification/reliability", response_model=s.Reliability, responses=ERRORS_503)
def reliability(svc: Svc, event: s.RainEvent) -> s.Reliability:
    """Reliability diagram points for one rain event."""
    return svc.reliability(event)


@router.get("/verification/coverage", response_model=s.Coverage, responses=ERRORS_503)
def coverage(svc: Svc) -> s.Coverage:
    """Nominal against empirical interval coverage per variable."""
    return svc.coverage()


@router.get("/verification/regions", response_model=s.Regions, responses=ERRORS_503)
def regions(svc: Svc) -> s.Regions:
    """Error per held-out block."""
    return svc.regions()


@router.get("/impact", response_model=s.Impact, responses=ERRORS_503)
def impact(svc: Svc, season: str = "monsoon_2024", decision: s.Decision = s.Decision.spray) -> s.Impact:
    """Replay of one decision over a season: model rule against block-forecast rule."""
    return svc.impact(season, decision)


@router.get("/data-quality", response_model=s.DataQuality, responses=ERRORS)
def data_quality(svc: Svc, issue_date: date | None = None) -> s.DataQuality:
    """Stations reporting, missing share over 30 days, stale inputs, as of an issue date."""
    return svc.data_quality(issue_date)
