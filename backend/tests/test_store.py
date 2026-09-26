"""SQLite store: migrations, draft replacement, review workflow and audit log, feedback."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pytest

from gramdrishti.store.db import MIGRATIONS, VISIBLE_TO_FARMERS, Store, init_db

ISSUE = date(2024, 9, 9)
AT = datetime(2024, 9, 9, 8, 0)


def _adv(pid: str, category: str, **over: object) -> dict:
    a = {"id": f"ADV-2024-09-09-{pid}-bajra-{category}", "issue_date": "2024-09-09", "panchayat_id": pid,
         "block_id": "MB01", "crop": "bajra", "stage": "flowering_grain", "category": category,
         "priority": "moderate", "valid_from": "2024-09-10", "valid_to": "2024-09-12",
         "action": {"en": "Do A.", "hi": "क करें।", "pa": "ਕ ਕਰੋ।"}, "reason": {"en": "Because.", "hi": "क्योंकि।",
                                                                               "pa": "ਕਿਉਂਕਿ।"},
         "fallback": {"en": "Else B.", "hi": "नहीं तो ख।", "pa": "ਨਹੀਂ ਤਾਂ ਖ।"}, "confidence": "high",
         "evidence": [{"label": "x", "value": "1"}], "thresholds_status": "placeholder",
         "translation_status": "needs_native_review", "rule_id": "irrigate_now"}
    return a | over


@pytest.fixture
def store(tmp_path: Path) -> Store:
    s = Store(tmp_path / "t.sqlite")
    s.replace_drafts(ISSUE, [_adv("MP0101", "irrigation"), _adv("MP0102", "spray")], AT, data_mode="mock",
                     rules_version=1, model_version="m1", note="test run")
    return s


def test_tables_match_guide_and_migrations_run_once(tmp_path: Path) -> None:
    db = tmp_path / "m.sqlite"
    assert init_db(db) == max(v for v, _ in MIGRATIONS)
    assert init_db(db) == max(v for v, _ in MIGRATIONS)
    con = sqlite3.connect(db)
    cols = {t: [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
            for t in ("advisories", "audit_log", "feedback", "farmers")}
    assert cols["advisories"] == ["id", "issue_date", "panchayat_id", "crop", "stage", "category",
                                  "priority", "valid_from", "valid_to", "payload_json", "status",
                                  "reviewed_by", "reviewed_at"]
    assert cols["audit_log"] == ["id", "advisory_id", "action", "actor", "before_json", "after_json",
                                 "note", "at"]
    assert cols["feedback"] == ["id", "panchayat_id", "date", "reported_rain", "intensity", "channel", "at"]
    assert cols["farmers"] == ["id", "name", "panchayat_id", "language", "crops_json"]
    assert con.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == len(MIGRATIONS)


def test_drafts_start_with_a_created_audit_row(store: Store) -> None:
    a = store.get("ADV-2024-09-09-MP0101-bajra-irrigation")
    assert a is not None and a["status"] == "draft" and a["reviewed_by"] is None
    audit = [(e["action"], e["actor"], e["at"]) for e in a["audit"]]
    assert audit == [("created", "system", "2024-09-09T08:00:00")]
    assert store.run_info(ISSUE)["n_advisories"] == 2


def test_approve_edit_reject_write_audit_with_before_and_after(store: Store) -> None:
    aid = "ADV-2024-09-09-MP0101-bajra-irrigation"
    t1, t2, t3 = (datetime(2024, 9, 9, 10, m) for m in (1, 2, 3))
    out = store.review(aid, "approve", "Officer A", "fine", {}, t1)
    assert out["status"] == "approved" and out["reviewed_by"] == "Officer A"
    assert out["reviewed_at"] == "2024-09-09T10:01:00"

    out = store.review(aid, "edit", "Officer B", "shorter", {"action": {"en": "Irrigate tomorrow."}}, t2)
    assert out["status"] == "edited"
    # A language left out of an edit becomes null: an old Hindi text never survives new English.
    assert out["action"] == {"en": "Irrigate tomorrow.", "hi": None, "pa": None}
    assert out["reason"]["hi"] == "क्योंकि।"

    out = store.review(aid, "reject", "Officer C", "wrong crop", {}, t3)
    assert out["status"] == "rejected"

    rows = store.audit_rows(aid)
    assert [(r["action"], r["actor"], r["note"]) for r in rows] == [
        ("created", "system", "test run"), ("approved", "Officer A", "fine"),
        ("edited", "Officer B", "shorter"), ("rejected", "Officer C", "wrong crop")]
    edit = rows[2]
    assert json.loads(edit["before_json"]) == {"status": "approved",
                                               "action": {"en": "Do A.", "hi": "क करें।", "pa": "ਕ ਕਰੋ।"}}
    assert json.loads(edit["after_json"]) == {"status": "edited",
                                              "action": {"en": "Irrigate tomorrow.", "hi": None, "pa": None}}
    assert json.loads(rows[3]["before_json"]) == {"status": "edited"}
    assert json.loads(rows[3]["after_json"]) == {"status": "rejected"}
    api = store.get(aid)["audit"]
    assert api[2]["before"]["action"]["en"] == "Do A."
    assert api[2]["after"]["action"]["en"] == "Irrigate tomorrow."


def test_unknown_id_returns_none(store: Store) -> None:
    assert store.review("ADV-nope", "approve", "x", "", {}, AT) is None
    assert store.get("ADV-nope") is None


def test_only_approved_and_edited_are_visible_to_farmers(store: Store) -> None:
    a, b = "ADV-2024-09-09-MP0101-bajra-irrigation", "ADV-2024-09-09-MP0102-bajra-spray"
    assert store.list(issue=ISSUE, statuses=VISIBLE_TO_FARMERS) == []
    store.review(a, "approve", "O", "", {}, AT)
    store.review(b, "reject", "O", "", {}, AT)
    assert [x["id"] for x in store.list(issue=ISSUE, statuses=VISIBLE_TO_FARMERS)] == [a]
    store.review(b, "edit", "O", "", {"reason": {"en": "New reason."}}, AT)
    assert [x["id"] for x in store.list(issue=ISSUE, statuses=VISIBLE_TO_FARMERS)] == [a, b]


def test_filters(store: Store) -> None:
    assert len(store.list()) == 2
    assert [x["panchayat_id"] for x in store.list(panchayat_id="MP0102")] == ["MP0102"]
    assert store.list(status="approved") == []
    assert store.list(issue=date(2024, 9, 10)) == []


def test_regeneration_replaces_drafts_and_keeps_reviewed(store: Store) -> None:
    reviewed = "ADV-2024-09-09-MP0101-bajra-irrigation"
    store.review(reviewed, "approve", "O", "", {}, AT)
    new = [_adv("MP0101", "irrigation", priority="high"), _adv("MP0103", "frost")]
    written, kept = store.replace_drafts(ISSUE, new, AT, data_mode="mock", rules_version=1,
                                         model_version="m2", note="rerun")
    assert (written, kept) == (1, 1)
    ids = [x["id"] for x in store.list(issue=ISSUE)]
    assert ids == [reviewed, "ADV-2024-09-09-MP0103-bajra-frost"]  # MP0102's old draft is gone
    kept_adv = store.get(reviewed)
    assert kept_adv["status"] == "approved" and kept_adv["priority"] == "moderate"  # untouched
    assert len(store.audit_rows("ADV-2024-09-09-MP0102-bajra-spray")) == 0
    assert store.run_info(ISSUE)["model_version"] == "m2"


def test_feedback_rows(store: Store) -> None:
    first = store.add_feedback("MP0101", date(2024, 9, 10), True, "heavy", "app", AT)
    second = store.add_feedback("MP0102", date(2024, 9, 10), False, "none", "ivr", AT)
    assert second == first + 1
    row = sqlite3.connect(store.path).execute("SELECT * FROM feedback WHERE id = ?", (first,)).fetchone()
    assert row[1:] == ("MP0101", "2024-09-10", 1, "heavy", "app", "2024-09-09T08:00:00")
