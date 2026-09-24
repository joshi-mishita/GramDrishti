"""GET /risk and GET /priority (provisional scores, placeholder thresholds)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import ERRORS, service
from gramdrishti.api.service import LEAD_MAX, LEAD_MIN, Service

router = APIRouter(tags=["risk"])
Svc = Annotated[Service, Depends(service)]


@router.get("/risk", response_model=s.Risk, responses=ERRORS)
def risk(svc: Svc, issue_date: date, lead_day: Annotated[int, Query(ge=LEAD_MIN, le=LEAD_MAX)],
         type: s.RiskType) -> s.Risk:  # noqa: A002 - contract parameter name
    """Risk level and score per Panchayat for one risk type and lead day."""
    return svc.risk(issue_date, lead_day, type)


@router.get("/priority", response_model=s.Priority, responses=ERRORS)
def priority(svc: Svc, issue_date: date,
             horizon_days: Annotated[int, Query(ge=LEAD_MIN, le=LEAD_MAX)] = 2) -> s.Priority:
    """Panchayats needing attention within the horizon, highest score first (moderate and above)."""
    return svc.priority(issue_date, horizon_days)
