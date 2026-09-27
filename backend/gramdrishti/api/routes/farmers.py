"""Demo farmer profiles, farmer advice and "Did it rain?" feedback (all stored in SQLite)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import ERRORS, ERRORS_400, ERRORS_503, service
from gramdrishti.api.service import Service

router = APIRouter(tags=["farmers"])
Svc = Annotated[Service, Depends(service)]


@router.get("/farmers/{farmer_id}", response_model=s.Farmer, responses=ERRORS)
def farmer(svc: Svc, farmer_id: str) -> s.Farmer:
    """Demo farmer profile (not a real person): Panchayat, language, crops with sowing dates, livestock."""
    return svc.farmer(farmer_id)


@router.get("/farmers/{farmer_id}/advice", response_model=s.FarmerAdvice, responses=ERRORS_503)
def farmer_advice(svc: Svc, farmer_id: str, issue_date: date) -> s.FarmerAdvice:
    """Approved or edited advisories for the farmer's Panchayat and crops, most urgent first, with
    whole-day spray ratings for the next days. Drafts and rejected advisories never appear."""
    return svc.farmer_advice(farmer_id, issue_date)


@router.post("/feedback", response_model=s.FeedbackResponse, responses=ERRORS_400)
def feedback(svc: Svc, body: s.FeedbackRequest) -> s.FeedbackResponse:
    """Farmer tapped "Did it rain?". 400 for a date outside the data period or a contradictory report;
    an identical report within 10 minutes answers ``stored: false`` with the first report's id."""
    return svc.feedback(body)
