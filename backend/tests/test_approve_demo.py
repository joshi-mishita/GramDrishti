"""Pre-approval for the public read-only build (S18): only the named drafts, with an honest reviewer name."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from gramdrishti.api import schemas as s
from gramdrishti.api.service import Service
from gramdrishti.pipeline.approve_demo import REVIEWER, approve

ISSUE = date(2024, 9, 9)


def test_approves_only_the_named_drafts(snapshot_dir: Path, tmp_path: Path) -> None:
    svc = Service(clock=lambda: datetime(2024, 9, 9, 9, 30), snapshot_dir=snapshot_dir,
                  db_path=tmp_path / "approve.sqlite")
    drafts = svc.advisories(s.Status.draft, None, ISSUE).items
    target = next(a for a in drafts if a.crop == "bajra")
    ids = approve(svc, ISSUE, [target.panchayat_id], "bajra")

    assert target.id in ids
    approved = svc.advisories(s.Status.approved, None, ISSUE).items
    assert {a.id for a in approved} == set(ids)
    assert all(a.panchayat_id == target.panchayat_id and a.crop == "bajra" for a in approved)
    assert all(a.reviewed_by == REVIEWER for a in approved)
    # A second run finds no drafts left for them and changes nothing.
    assert approve(svc, ISSUE, [target.panchayat_id], "bajra") == []
