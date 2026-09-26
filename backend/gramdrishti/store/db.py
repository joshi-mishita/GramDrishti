"""SQLite store for advisories, the review audit log, farmer feedback and demo farmers (Backend Guide 10).

Tables follow Guide 10 exactly; ``schema_version`` and ``generation_runs`` are bookkeeping. Migrations are
plain SQL scripts applied in order by ``init_db`` (``python -m gramdrishti.store.init_db``); each runs once.

Review states: draft -> approved | edited | rejected. A reviewed advisory can be reviewed again (an officer
may change their mind); every review writes one ``audit_log`` row with the before and after JSON of the
fields it changed, the actor and the time. Only approved and edited advisories reach farmers.

Regenerating an issue date replaces its drafts and never touches reviewed advisories. SQLite is the
prototype store; production would use Postgres/PostGIS. One short-lived connection per call keeps it
safe under FastAPI's thread pool.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import date, datetime
from pathlib import Path

from gramdrishti.data.config import ART

DB_ENV = "GRAMDRISHTI_DB"
DEFAULT_DB = ART / "gramdrishti.sqlite"
VISIBLE_TO_FARMERS = ("approved", "edited")
REVIEW_STATUS = {"approve": "approved", "edit": "edited", "reject": "rejected"}
TEXT_FIELDS = ("action", "reason", "fallback")
INSERT_AUDIT = ("INSERT INTO audit_log(advisory_id, action, actor, before_json, after_json, note, at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)")
INSERT_FEEDBACK = ("INSERT INTO feedback(panchayat_id, date, reported_rain, intensity, channel, at) "
                   "VALUES (?, ?, ?, ?, ?, ?)")

MIGRATIONS: list[tuple[int, str]] = [
    (1, """
CREATE TABLE advisories(id TEXT PRIMARY KEY, issue_date TEXT, panchayat_id TEXT, crop TEXT, stage TEXT,
  category TEXT, priority TEXT, valid_from TEXT, valid_to TEXT, payload_json TEXT, status TEXT,
  reviewed_by TEXT, reviewed_at TEXT);
CREATE TABLE audit_log(id INTEGER PRIMARY KEY AUTOINCREMENT, advisory_id TEXT, action TEXT, actor TEXT,
  before_json TEXT, after_json TEXT, note TEXT, at TEXT);
CREATE TABLE feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, panchayat_id TEXT, date TEXT,
  reported_rain INTEGER, intensity TEXT, channel TEXT, at TEXT);
CREATE TABLE farmers(id TEXT PRIMARY KEY, name TEXT, panchayat_id TEXT, language TEXT, crops_json TEXT);
CREATE TABLE generation_runs(issue_date TEXT PRIMARY KEY, data_mode TEXT, rules_version INTEGER,
  model_version TEXT, n_advisories INTEGER, at TEXT);
CREATE INDEX advisories_issue ON advisories(issue_date, status);
CREATE INDEX advisories_panchayat ON advisories(panchayat_id);
CREATE INDEX audit_advisory ON audit_log(advisory_id, id);
"""),
]


def db_path() -> Path:
    """``GRAMDRISHTI_DB`` if set, else ``backend/artifacts/gramdrishti.sqlite`` (git-ignored)."""
    return Path(os.environ.get(DB_ENV, DEFAULT_DB))


def _json(x: object) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _iso(t: datetime) -> str:
    return t.replace(microsecond=0).isoformat()


def init_db(path: Path) -> int:
    """Create the file if needed and apply pending migrations. Returns the schema version."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as con, con:
        con.execute("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL)")
        row = con.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current = row[0] or 0
        for version, sql in MIGRATIONS:
            if version > current:
                con.executescript(sql)
                con.execute("INSERT INTO schema_version(version) VALUES (?)", (version,))
                current = version
    return current


class Store:
    """All reads and writes. Advisory payloads are the engine's JSON-ready dicts."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or db_path()
        init_db(self.path)

    @contextmanager
    def _con(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    # ------------------------------------------------------------ generation
    def run_info(self, issue: date) -> dict | None:
        with self._con() as con:
            r = con.execute("SELECT * FROM generation_runs WHERE issue_date = ?",
                            (issue.isoformat(),)).fetchone()
        return dict(r) if r else None

    def replace_drafts(self, issue: date, advisories: list[dict], created_at: datetime, *, data_mode: str,
                       rules_version: int, model_version: str | None, note: str) -> tuple[int, int]:
        """Replace the drafts of ``issue`` with ``advisories``; reviewed ones stay as they are.

        Returns (drafts written, reviewed advisories kept). Each new draft gets a ``created`` audit row.
        """
        day = issue.isoformat()
        with self._con() as con:
            reviewed = {r["id"] for r in con.execute(
                "SELECT id FROM advisories WHERE issue_date = ? AND status != 'draft'", (day,))}
            old = [r["id"] for r in con.execute(
                "SELECT id FROM advisories WHERE issue_date = ? AND status = 'draft'", (day,))]
            con.executemany("DELETE FROM audit_log WHERE advisory_id = ?", [(i,) for i in old])
            con.execute("DELETE FROM advisories WHERE issue_date = ? AND status = 'draft'", (day,))
            written = 0
            for a in sorted(advisories, key=lambda x: x["id"]):
                if a["id"] in reviewed:
                    continue
                con.execute(
                    "INSERT INTO advisories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', NULL, NULL)",
                    (a["id"], a["issue_date"], a["panchayat_id"], a["crop"], a["stage"], a["category"],
                     a["priority"], a["valid_from"], a["valid_to"], _json(a)))
                con.execute(INSERT_AUDIT, (a["id"], "created", "system", None, _json({"status": "draft"}),
                                           note, _iso(created_at)))
                written += 1
            con.execute("INSERT OR REPLACE INTO generation_runs VALUES (?, ?, ?, ?, ?, ?)",
                        (day, data_mode, rules_version, model_version, len(advisories), _iso(created_at)))
        return written, len(reviewed)

    # ------------------------------------------------------------ reads
    def _audit(self, con: sqlite3.Connection, ids: list[str]) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {i: [] for i in ids}
        for chunk in (ids[i:i + 500] for i in range(0, len(ids), 500)):
            q = f"SELECT * FROM audit_log WHERE advisory_id IN ({','.join('?' * len(chunk))}) ORDER BY id"
            for r in con.execute(q, chunk):
                out[r["advisory_id"]].append({
                    "at": r["at"], "actor": r["actor"], "action": r["action"], "note": r["note"] or "",
                    "before": json.loads(r["before_json"]) if r["before_json"] else None,
                    "after": json.loads(r["after_json"]) if r["after_json"] else None})
        return out

    @staticmethod
    def _merge(row: sqlite3.Row, audit: list[dict]) -> dict:
        a = json.loads(row["payload_json"])
        a.update(status=row["status"], reviewed_by=row["reviewed_by"], reviewed_at=row["reviewed_at"],
                 audit=audit)
        return a

    def list(self, status: str | None = None, panchayat_id: str | None = None,
             issue: date | None = None, statuses: tuple[str, ...] | None = None) -> list[dict]:
        """Advisories matching the filters (with audit trails), ordered by issue date and id."""
        where, args = [], []
        if status is not None:
            where.append("status = ?")
            args.append(status)
        if statuses is not None:
            where.append(f"status IN ({','.join('?' * len(statuses))})")
            args += list(statuses)
        if panchayat_id is not None:
            where.append("panchayat_id = ?")
            args.append(panchayat_id)
        if issue is not None:
            where.append("issue_date = ?")
            args.append(issue.isoformat())
        sql = "SELECT * FROM advisories" + (" WHERE " + " AND ".join(where) if where else "")
        with self._con() as con:
            rows = con.execute(sql + " ORDER BY issue_date, id", args).fetchall()
            audit = self._audit(con, [r["id"] for r in rows])
        return [self._merge(r, audit[r["id"]]) for r in rows]

    def get(self, adv_id: str) -> dict | None:
        with self._con() as con:
            r = con.execute("SELECT * FROM advisories WHERE id = ?", (adv_id,)).fetchone()
            return self._merge(r, self._audit(con, [adv_id])[adv_id]) if r else None

    # ------------------------------------------------------------ review
    def review(self, adv_id: str, action: str, reviewer: str, note: str, edited: dict[str, dict],
               at: datetime) -> dict | None:
        """Apply approve / edit / reject and write one audit row. None when the id does not exist.

        ``edited`` maps action / reason / fallback to ``{en, hi?, pa?}``. A language left out of an edit
        is set to null, so an old translation never survives a changed English text (D062).
        """
        status = REVIEW_STATUS[action]
        with self._con() as con:
            r = con.execute("SELECT * FROM advisories WHERE id = ?", (adv_id,)).fetchone()
            if r is None:
                return None
            payload = json.loads(r["payload_json"])
            before: dict[str, object] = {"status": r["status"]}
            after: dict[str, object] = {"status": status}
            for part, text in edited.items():
                new = {"en": text["en"], "hi": text.get("hi"), "pa": text.get("pa")}
                if new != payload[part]:
                    before[part], after[part] = payload[part], new
                    payload[part] = new
            con.execute("UPDATE advisories SET status = ?, reviewed_by = ?, reviewed_at = ?, "
                        "payload_json = ? WHERE id = ?", (status, reviewer, _iso(at), _json(payload), adv_id))
            con.execute(INSERT_AUDIT, (adv_id, status, reviewer, _json(before), _json(after), note, _iso(at)))
        return self.get(adv_id)

    def audit_rows(self, adv_id: str) -> list[dict]:
        """Raw audit rows for one advisory (tests and debugging)."""
        with self._con() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM audit_log WHERE advisory_id = ? ORDER BY id", (adv_id,))]

    # ------------------------------------------------------------ feedback
    def add_feedback(self, panchayat_id: str, day: date, reported_rain: bool, intensity: str, channel: str,
                     at: datetime) -> int:
        with self._con() as con:
            cur = con.execute(INSERT_FEEDBACK, (panchayat_id, day.isoformat(), int(reported_rain), intensity,
                                                channel, _iso(at)))
            return int(cur.lastrowid or 0)

    def counts(self, issue: date) -> dict[str, dict[str, int]]:
        """Advisory counts by category and by status for one issue date."""
        with self._con() as con:
            q = "SELECT {c}, COUNT(*) n FROM advisories WHERE issue_date = ? GROUP BY {c} ORDER BY {c}"
            cat = con.execute(q.format(c="category"), (issue.isoformat(),)).fetchall()
            st = con.execute(q.format(c="status"), (issue.isoformat(),)).fetchall()
        return {"category": {r["category"]: r["n"] for r in cat}, "status": {r["status"]: r["n"] for r in st}}
