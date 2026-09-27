"""Advisory review queue, review action and audio.

Advisories come from the YAML rules engine (placeholder thresholds); review state lives in SQLite.
Audio is made with gTTS on first request and cached under ``artifacts/audio/``.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from gramdrishti.api import schemas as s
from gramdrishti.api.deps import ERRORS, ERRORS_400, ERRORS_503, service
from gramdrishti.api.service import Service

router = APIRouter(tags=["advisories"])
Svc = Annotated[Service, Depends(service)]


@router.get("/advisories", response_model=s.AdvisoryList, responses=ERRORS_503)
def advisories(svc: Svc, status: s.Status | None = None, panchayat_id: str | None = None,
               issue_date: date | None = None) -> s.AdvisoryList:
    """Advisories filtered by status, Panchayat and issue date."""
    return svc.advisories(status, panchayat_id, issue_date)


@router.get("/advisories/{advisory_id}", response_model=s.Advisory, responses=ERRORS_503)
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
    """MP3 of the advisory's action, reason and fallback in one language (gTTS, cached).

    404 ``not_found`` for an unknown advisory; 404 ``audio_not_available`` when the audio cannot be made
    (gTTS missing, language not supported, no text in that language, or no internet). The UI then falls
    back to the browser's own speech.
    """
    return FileResponse(svc.audio(advisory_id, lang), media_type="audio/mpeg")
