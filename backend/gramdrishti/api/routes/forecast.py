"""Forecast endpoints: map, Panchayat detail, observed, explain, changes.

Forecast values, reasons and changes are read from the snapshots written by
``python -m gramdrishti.pipeline.run_daily``; a missing snapshot answers 503 ``not_computed``.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import ERRORS_400, ERRORS_503, service
from gramdrishti.api.service import LEAD_MAX, LEAD_MIN, Service

router = APIRouter(tags=["forecast"])
Svc = Annotated[Service, Depends(service)]
Lead = Annotated[int, Query(ge=LEAD_MIN, le=LEAD_MAX, description="Lead day, 1 = tomorrow")]
Issue = Annotated[date, Query(description="Issue date, one of /meta.available_issue_dates")]


@router.get("/forecast/map", response_model=s.ForecastMap, responses=ERRORS_503)
def forecast_map(svc: Svc, issue_date: Issue, lead_day: Lead, var: s.Var) -> s.ForecastMap:
    """Block layer and Panchayat layer for one variable and lead day."""
    return svc.forecast_map(issue_date, lead_day, var)


@router.get("/forecast/panchayat/{panchayat_id}", response_model=s.PanchayatForecast,
            responses=ERRORS_503)
def forecast_panchayat(svc: Svc, panchayat_id: str, issue_date: Issue) -> s.PanchayatForecast:
    """5-day detail with quantiles, event probabilities and derived agro-variables."""
    return svc.forecast_panchayat(panchayat_id, issue_date)


@router.get("/observed/panchayat/{panchayat_id}", response_model=s.Observed, responses=ERRORS_400)
def observed(svc: Svc, panchayat_id: str, from_: Annotated[date, Query(alias="from")],
             to: date) -> s.Observed:
    """What happened: the Panchayat's station if it has one, else synthetic truth (mock only)."""
    return svc.observed(panchayat_id, from_, to)


@router.get("/explain/{panchayat_id}", response_model=s.Explain, responses=ERRORS_503)
def explain(svc: Svc, panchayat_id: str, issue_date: Issue, lead_day: Lead, var: s.Var) -> s.Explain:
    """Top 3 SHAP reasons this Panchayat differs from its corrected block forecast (none if negligible)."""
    return svc.explain(panchayat_id, issue_date, lead_day, var)


@router.get("/forecast/changes/{panchayat_id}", response_model=s.ForecastChanges, responses=ERRORS_503)
def forecast_changes(svc: Svc, panchayat_id: str, issue_date: Issue) -> s.ForecastChanges:
    """What changed since the previous day's forecast."""
    return svc.changes(panchayat_id, issue_date)
