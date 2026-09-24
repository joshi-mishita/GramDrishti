"""Advisory review queue, review action and audio.

PLACEHOLDER: advisories come from a small template generator until the YAML rules engine (S8).
Review state is kept in memory and resets when the server restarts (SQLite arrives in S8).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import ERRORS, ERRORS_400, service
from gramdrishti.api.errors import not_found
from gramdrishti.api.service import Service
from gramdrishti.data.config import ART

router = APIRouter(tags=["advisories"])
Svc = Annotated[Service, Depends(service)]


@router.get("/advisories", response_model=s.AdvisoryList, responses=ERRORS)
def advisories(svc: Svc, status: s.Status | None = None, panchayat_id: str | None = None,
               issue_date: date | None = None) -> s.AdvisoryList:
    """Advisories filtered by status, Panchayat and issue date."""
    return svc.advisories(status, panchayat_id, issue_date)


@router.get("/advisories/{advisory_id}", response_model=s.Advisory, responses=ERRORS)
def advisory(svc: Svc, advisory_id: str) -> s.Advisory:
    """One advisory with evidence and audit trail."""
    return svc.advisory(advisory_id)


@router.post("/advisories/{advisory_id}/review", response_model=s.Advisory, responses=ERRORS_400)
def review(svc: Svc, advisory_id: str, body: s.ReviewRequest) -> s.Advisory:
    """Approve, edit or reject. Appends to the audit trail and returns the updated advisory."""
    return svc.review(advisory_id, body)


@router.get("/audio/{advisory_id}", response_class=FileResponse,
            responses={200: {"content": {"audio/mpeg": {}}, "description": "MP3 of the advisory text"},
                       **ERRORS})
def audio(svc: Svc, advisory_id: str, lang: s.Lang) -> FileResponse:
    """MP3 of the advisory text, or 404 when no audio exists (the UI then falls back to browser speech)."""
    svc.advisory(advisory_id)
    path = ART / "audio" / f"{advisory_id}_{lang.value}.mp3"
    if not path.is_file():
        raise not_found(f"Audio for {advisory_id} in {lang.value} is not available")
    return FileResponse(path, media_type="audio/mpeg")
