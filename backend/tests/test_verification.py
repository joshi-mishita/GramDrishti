"""Verification job, TEST ledger and decision replay (S10).

The job itself is exercised on CALIB with the small test bundle: tests never open the TEST window.
"""

from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from gramdrishti.api import schemas as s
from gramdrishti.verify import impact, ledger
from gramdrishti.verify import run_validation as rv

from .conftest import needs_oracle


# ---------------------------------------------------------------- ledger
def test_ledger_records_first_opening_and_reuse(tmp_path) -> None:
    path = tmp_path / "ledger.json"
    t1, t2, t3 = datetime(2026, 9, 27, 10), datetime(2026, 9, 27, 11), datetime(2026, 9, 28, 9)
    first = ledger.open_test("m-1", "hash1", "abc", t1, path)
    assert first.first_opened_at == t1 and not first.reused
    again = ledger.open_test("m-1", "hash1", "abd", t2, path)
    assert again.first_opened_at == t1 and not again.reused          # a rerun is not a new opening
    later = ledger.open_test("m-2", "hash2", "abe", t3, path)
    assert later.reused and later.earlier_versions == ["m-1"]
    led = json.loads(path.read_text())
    assert [len(e["runs"]) for e in led["entries"]] == [2, 1]
    with pytest.raises(RuntimeError, match="new version"):
        ledger.open_test("m-1", "changed", "abf", t3, path)


def test_validate_refuses_test_without_ledger_entry() -> None:
    with pytest.raises(PermissionError, match="ledger"):
        rv.validate(None, None, None, window="TEST")  # type: ignore[arg-type]


# ---------------------------------------------------------------- impact
def test_decision_counts() -> None:
    act = np.array([1, 1, 0, 0, 1], bool)
    event = np.array([1, 0, 1, 0, 0], bool)
    assert impact.counts(act, event) == {"correct": 2, "wasted_wait": 2, "washed_off": 1}


def test_replay_spray_rule_by_hand() -> None:
    d = pd.DataFrame({
        "lead_day": [1, 1, 1, 1, 2],
        "prob_rain_ge_2_5": [0.5, 0.1, 0.2, 0.4, 0.9],     # model holds spraying on rows 0 and 3
        "b0_rain": [3.0, 3.0, 0.0, 0.0, 9.0],              # block holds on rows 0 and 1
        "b1_rain": [0.0, 0.0, 0.0, 0.0, 9.0],              # corrected block never holds
        "obs_rain": [4.0, 0.0, 6.0, 0.0, 9.0],             # rain on rows 0 and 2; row 4 is lead day 2
    })
    r = impact.replay(d, impact.RULES["spray"])
    assert r["n_decisions"] == 4 and r["events_observed"] == 2
    assert r["model"] == {"correct": 2, "wasted_wait": 1, "washed_off": 1}
    assert r["block_baseline"] == {"correct": 2, "wasted_wait": 1, "washed_off": 1}
    assert r["block_corrected"] == {"correct": 2, "wasted_wait": 0, "washed_off": 2}


# ---------------------------------------------------------------- notes
def _check(skill: float, ci: list[float]) -> dict:
    row = {"name": "MAE", "unit": "mm", "model": 1.0, "b0": 1.0, "b1": 1.0, "b2": 1.0,
           "skill_vs_b0": skill, "skill_ci95": ci, "skill_vs_b1": skill, "skill_vs_b1_ci95": ci}
    return {"check": "temporal_holdout", "variables": [{"var": "rain", "n": 10, "metrics": [row]}]}


def test_loss_notes_list_every_loss_and_nothing_when_all_win() -> None:
    losing = [_check(-0.1, [-0.2, -0.05])]
    notes = rv.loss_notes(rv.verdicts(losing, []), losing, [])
    assert len(notes) == 2 and all("Does NOT beat" in n and "rain" in n for n in notes)
    tie = [_check(0.02, [-0.01, 0.05])]
    assert len(rv.loss_notes(rv.verdicts(tie, []), tie, [])) == 2
    winning = [_check(0.1, [0.05, 0.2])]
    assert rv.loss_notes(rv.verdicts(winning, []), winning, []) == []


# ---------------------------------------------------------------- the job on CALIB with the small bundle
@pytest.fixture(scope="module")
def calib_run(small_bundle, small_prep):  # noqa: ANN001
    issues = rv.evaluation_issue_dates(small_prep.inputs, "CALIB")[:21]
    return rv.validate(small_bundle, small_prep.inputs, small_prep, window="CALIB", issue_dates=issues,
                       lobo=True, n_boot=100, log=lambda *_: None), issues


@needs_oracle
def test_validation_payloads_match_the_contract(calib_run) -> None:  # noqa: ANN001
    res, _ = calib_run
    v = res.verification
    summ = s.VerificationSummary.model_validate(v["summary"])
    assert summ.provenance == s.Provenance.computed and summ.data_mode == s.DataMode.mock
    assert [c.check for c in summ.checks] == ["temporal_holdout", "leave_one_block_out", "station"]
    assert {r.dimension for r in summ.strata} == {"lead_day", "season", "rain_intensity", "drainage_class"}
    assert len(v["reliability"]) == 4
    for r in v["reliability"]:
        s.Reliability.model_validate(r)
    s.Coverage.model_validate(v["coverage"])
    regs = s.Regions.model_validate(v["regions"])
    assert {i.region_type for i in regs.items} == {"block", "station"}
    for it in res.impact["items"].values():
        imp = s.Impact.model_validate(it)
        for side in (imp.model, imp.block_baseline, imp.block_corrected):
            assert side.correct + side.wasted_wait + side.washed_off == imp.n_decisions
    assert "DRY RUN" in summ.notes[1] and "Synthetic" in summ.notes[0]


@needs_oracle
def test_validation_block_consistency_and_losses_noted(calib_run) -> None:  # noqa: ANN001
    res, _ = calib_run
    summ = res.verification["summary"]
    assert all(e < 1e-6 for e in summ["block_mean_error"].values())
    if any(x["result"] != "win" for x in summ["verdicts"]):
        assert any(n.startswith("Does NOT beat") for n in summ["notes"])


@needs_oracle
def test_validation_is_deterministic(small_bundle, small_prep, calib_run, tmp_path) -> None:  # noqa: ANN001
    res, issues = calib_run
    again = rv.validate(small_bundle, small_prep.inputs, small_prep, window="CALIB", issue_dates=issues,
                        lobo=True, n_boot=100, log=lambda *_: None)
    a, b = rv.write(res, tmp_path / "a"), rv.write(again, tmp_path / "b")
    assert a[0].read_bytes() == b[0].read_bytes() and a[1].read_bytes() == b[1].read_bytes()
