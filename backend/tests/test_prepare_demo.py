"""The one-command prepare step (S14): skips work already done and copies a verification record only when it
describes the local model."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gramdrishti.data.config import data_dir
from gramdrishti.models.artifacts import library_versions
from gramdrishti.pipeline import prepare_demo as p

VERSION = "s5-lgbm-9b632a7b1b"


def _record(tmp: Path, data: Path, libs: dict[str, str], version: str = VERSION) -> Path:
    """A fake record whose frozen block matches ``data`` and ``libs``."""
    (data / "a.csv").write_text("x\n1\n")
    rec = tmp / "records" / version
    rec.mkdir(parents=True)
    frozen = {"model_version": version, "data_files_sha256": {"a.csv": p.sha256(data / "a.csv")},
              "library_versions": libs}
    (rec / "verification.json").write_text(json.dumps({"summary": {}, "frozen": frozen}))
    (rec / "impact.json").write_text(json.dumps({"items": {}}))
    return tmp / "records"


def _art(tmp: Path, version: str = VERSION) -> Path:
    art = tmp / "art"
    art.mkdir()
    (art / "config.json").write_text(json.dumps({"model_version": version, "targets": ["rain"]}))
    return art


def test_record_is_copied_when_everything_matches(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    records = _record(tmp_path, data, library_versions())
    art = _art(tmp_path)
    status = p.ensure_verification(art, records, data)
    assert status.startswith("copied"), status
    assert (art / "verification.json").read_bytes() == (records / VERSION / "verification.json").read_bytes()
    assert p.ensure_verification(art, records, data) == "present"


@pytest.mark.parametrize("change", ["version", "data", "lightgbm", "python"])
def test_record_is_refused_on_any_mismatch(tmp_path: Path, change: str) -> None:
    data = tmp_path / "data"
    data.mkdir()
    libs = dict(library_versions())
    if change == "lightgbm":
        libs["lightgbm"] = "0.0.1"
    if change == "python":
        libs["python"] = "2.7.18"
    records = _record(tmp_path, data, libs)
    if change == "data":
        (data / "a.csv").write_text("x\n2\n")
    art = _art(tmp_path, "s5-lgbm-other" if change == "version" else VERSION)
    status = p.ensure_verification(art, records, data)
    assert status.startswith("MISSING"), status
    assert not (art / "verification.json").exists()


def test_committed_record_matches_its_own_job_output() -> None:
    """The committed record is a full job output for the version it is filed under."""
    rec = p.RECORDS / VERSION
    v = json.loads((rec / "verification.json").read_text())
    i = json.loads((rec / "impact.json").read_text())
    assert v["frozen"]["model_version"] == VERSION
    assert v["summary"]["data_mode"] == i["data_mode"] == "mock"
    assert {"summary", "reliability", "coverage", "regions"} <= set(v)


@pytest.mark.oracle
def test_committed_record_hashes_match_the_repo_data() -> None:
    frozen = json.loads((p.RECORDS / VERSION / "verification.json").read_text())["frozen"]
    for name, want in frozen["data_files_sha256"].items():
        assert p.sha256(data_dir() / name) == want, name


def test_model_ready_needs_every_file(tmp_path: Path) -> None:
    art = _art(tmp_path)
    assert not p.model_ready(art)
    for f in ("model_rain.joblib", "events.joblib", "bias.joblib", "conformal.json", "features.json"):
        (art / f).write_text("")
    assert p.model_ready(art)
    assert not p.model_ready(tmp_path / "nowhere")


def test_missing_snapshots_lists_the_demo_plan(tmp_path: Path) -> None:
    from gramdrishti.pipeline.run_daily import demo_plan
    plan = [d.isoformat() for d, _ in demo_plan()]
    assert p.missing_snapshots(tmp_path) == plan
    (tmp_path / plan[0]).mkdir()
    (tmp_path / plan[0] / "manifest.json").write_text("{}")
    assert p.missing_snapshots(tmp_path) == plan[1:]


def test_run_steps_reports_each_step() -> None:
    lines: list[str] = []
    done = p.run_steps([("a", lambda: "ok"), ("b", lambda: "fine")], log=lambda s, **_: lines.append(s))
    assert [(n, s) for n, s, _ in done] == [("a", "ok"), ("b", "fine")]
    assert lines[1].startswith("[prepare] a: ok (")
