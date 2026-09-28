"""Approve named demo advisories before an offline export, for a published read-only copy (S18).

The GitHub Pages build (``.github/workflows/pages.yml``) starts from an empty review database, so its farmer
screens would show no advice. Like the demo procedure in D172, it approves a short, named list of advisories
first. The reviewer name says that no officer looked at them, and the audit trail keeps it. The live demo's
database is never touched: this runs only where it is called.

Run: ``cd backend && python -m gramdrishti.pipeline.approve_demo --issue-date 2024-09-09 --panchayat MP0307
MP0311 --crop bajra``
"""

from __future__ import annotations

import argparse
from datetime import date

from gramdrishti.api import schemas as s
from gramdrishti.api.service import Service

REVIEWER = "Automated demo approval (no officer reviewed this)"
NOTE = ("Approved by the public demo build so the read-only copy has farmer advice. "
        "Thresholds are placeholders.")


def approve(svc: Service, issue: date, panchayats: list[str], crop: str | None = None) -> list[str]:
    """Approve the drafts of ``panchayats`` (and ``crop``, when given) on ``issue``; return their ids."""
    drafts = svc.advisories(s.Status.draft, None, issue).items
    ids = [a.id for a in drafts if a.panchayat_id in panchayats and (crop is None or a.crop == crop)]
    req = s.ReviewRequest(action=s.ReviewAction.approve, reviewer=REVIEWER, note=NOTE)
    for adv_id in ids:
        svc.review(adv_id, req)
    return ids


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--issue-date", type=date.fromisoformat, required=True)
    ap.add_argument("--panchayat", nargs="+", required=True)
    ap.add_argument("--crop", default=None)
    args = ap.parse_args(argv)
    ids = approve(Service(), args.issue_date, args.panchayat, args.crop)
    print(f"approved {len(ids)} advisories: {', '.join(ids) or 'none (no matching drafts)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
