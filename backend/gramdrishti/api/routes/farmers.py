"""Farmer profile, farmer advice and feedback (demo farmers; feedback stored in memory until S12)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import ERRORS, ERRORS_503, service
from gramdrishti.api.service import Service

router = APIRouter(tags=["farmers"])
Svc = Annotated[Service, Depends(service)]


@router.get("/farmers/{farmer_id}", response_model=s.Farmer, responses=ERRORS)
def farmer(svc: Svc, farmer_id: str) -> s.Farmer:
    """Demo farmer profile: Panchayat, language, crops with sowing dates."""
    return svc.farmer(farmer_id)


@router.get("/farmers/{farmer_id}/advice", response_model=s.FarmerAdvice, responses=ERRORS_503)
def farmer_advice(svc: Svc, farmer_id: str, issue_date: date) -> s.FarmerAdvice:
    """Approved (or edited and approved) advisories for the farmer's Panchayat on this issue date."""
    return svc.farmer_advice(farmer_id, issue_date)


@router.post("/feedback", response_model=s.FeedbackResponse, responses=ERRORS)
def feedback(svc: Svc, body: s.FeedbackRequest) -> s.FeedbackResponse:
    """Farmer tapped "Did it rain?"."""
    return svc.feedback(body)
