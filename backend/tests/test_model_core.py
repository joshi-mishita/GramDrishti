"""Trained-model tests on the mock data with a small, fast model (few trees, every 4th TRAIN issue date).

Covers block consistency on every block-day, output constraints, determinism, the irrigation sanity
check, artifact round trip, and that TEST-window data never influences anything S5 builds.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gramdrishti.data import loaders
from gramdrishti.data.config import COLS, RECONCILE_TOL, TEST, VARS, window_bounds
from gramdrishti.features.table import Inputs, load_inputs
from gramdrishti.models.artifacts import Bundle, load_bundle, save_bundle
from gramdrishti.models.downscale import fit_downscale, fit_mean_only, lgbm_params
from gramdrishti.models.reconcile import max_block_error
from gramdrishti.pipeline.predict import predict_table
from gramdrishti.pipeline.train import Prepared, fit_all, irrigation_check, prepare

from .conftest import needs_oracle

pytestmark = needs_oracle
FAST = {"n_estimators": 30, "num_leaves": 15}


@pytest.fixture(scope="module")
def prep() -> Prepared:
    p = prepare()
    keep = p.train["issue_date"].isin(p.train["issue_date"].drop_duplicates().iloc[::4])
    return replace(p, train=p.train[keep].reset_index(drop=True))


@pytest.fixture(scope="module")
def fitted(prep: Prepared):
    models, offsets, _ = fit_all(prep, lgbm_params(FAST))
    return models, offsets, predict_table(models, prep.calib, offsets)


def test_block_mean_equals_block_forecast_for_every_block_day(fitted) -> None:
    _, _, pred = fitted
    for prefix in [*VARS, "td"]:
        assert max_block_error(pred, prefix, f"b1_{prefix}") < RECONCILE_TOL, prefix
    # and the check really looks at every block-day
    n_block_days = pred.groupby(["issue_date", "lead_day", "block_id"]).ngroups
    assert n_block_days == pred["issue_date"].nunique() * 5 * 6


def test_output_constraints(fitted) -> None:
    _, _, pred = fitted
    for v in VARS:
        assert (pred[f"{v}_p10"] <= pred[f"{v}_p50"]).all(), v
        assert (pred[f"{v}_p50"] <= pred[f"{v}_p90"]).all(), v
    for s in ("mean", "p10", "p50", "p90"):
        assert (pred[f"rain_{s}"] >= 0).all()
        assert (pred[f"wind_{s}"] >= 0).all()
        assert pred[f"rh_{s}"].between(0, 100).all()
        assert (pred[f"tmin_{s}"] < pred[f"tmax_{s}"]).all()
    probs = pred.filter(like="prob_rain_ge_")
    assert probs.to_numpy().min() >= 0 and probs.to_numpy().max() <= 1
    assert (probs.diff(axis=1).iloc[:, 1:] <= 1e-12).all().all()       # P(>=1) >= P(>=2.5) >= ...
    assert not pred.filter(regex="_(mean|p10|p50|p90)$").isna().any().any()


def test_training_and_calibration_windows_do_not_overlap(prep: Prepared) -> None:
    assert prep.train["valid_date"].max() < prep.calib["issue_date"].min()
    assert prep.calib["valid_date"].max() < window_bounds("TEST")[0]
    assert prep.bias.data_max_date <= window_bounds("TRAIN")[1]


def test_same_seed_same_model(prep: Prepared) -> None:
    small = prep.train.iloc[:20000]
    a = fit_mean_only(small, prep.features, lgbm_params(FAST), targets=["tmax"])
    b = fit_mean_only(small, prep.features, lgbm_params(FAST), targets=["tmax"])
    x = prep.calib.iloc[:2000]
    np.testing.assert_array_equal(a.predict_raw(x).to_numpy(), b.predict_raw(x).to_numpy())
    e1 = fit_downscale(small, prep.features, lgbm_params(FAST), targets=[]).events[10.0]
    e2 = fit_downscale(small, prep.features, lgbm_params(FAST), targets=[]).events[10.0]
    np.testing.assert_array_equal(e1.predict_proba(x[prep.features]), e2.predict_proba(x[prep.features]))


def test_tmax_anomaly_falls_as_irrigation_rises(fitted, prep: Prepared) -> None:
    models, _, _ = fitted
    res = irrigation_check(models, prep.train)
    assert res["mean_tmax_anomaly_c"].is_monotonic_decreasing
    assert res["mean_tmax_anomaly_c"].iloc[0] - res["mean_tmax_anomaly_c"].iloc[-1] > 0.1


def test_bundle_round_trip(fitted, prep: Prepared, tmp_path: Path) -> None:
    models, offsets, pred = fitted
    config = {"targets": list(models.regressors)}
    save_bundle(Bundle(models, offsets, prep.bias, prep.encodings, config), tmp_path)
    b = load_bundle(tmp_path)
    again = predict_table(b.models, prep.calib, b.offsets)
    pd.testing.assert_frame_equal(pred, again)


def test_test_window_never_influences_s5(monkeypatch: pytest.MonkeyPatch) -> None:
    """Poison every TEST-window value (truth, forecasts, observations, satellite): the tables and
    the bias model built by ``prepare`` must be identical to the clean run."""
    clean = prepare()
    start = pd.Timestamp(TEST[0])
    truth, block_truth = loaders.load_truth(), loaders.load_block_truth()  # MOCK ONLY: poisoned copies
    for df in (truth, block_truth):
        df.loc[df["date"] >= start, [COLS[v] for v in VARS]] = 999.0
    truth.loc[truth["date"] >= start, "dewpoint_c"] = 999.0
    monkeypatch.setattr(loaders, "load_truth", lambda: truth.copy())
    monkeypatch.setattr(loaders, "load_block_truth", lambda: block_truth.copy())
    inp = load_inputs()
    fc, obs, sat = inp.fc.copy(), inp.obs_clean.copy(), inp.sat.copy()
    fc.loc[fc["valid_date"] >= start, [COLS[v] for v in VARS]] = 999.0
    obs.loc[obs["date"] >= start, [COLS[v] for v in VARS]] = 999.0
    sat.loc[sat["week_start"] >= start - pd.Timedelta(days=7), ["ndvi", "lst_day_c"]] = 9.0
    poisoned = prepare(Inputs(fc, inp.static, inp.blocks, sat, obs, inp.stations))
    pd.testing.assert_frame_equal(clean.train, poisoned.train)
    pd.testing.assert_frame_equal(clean.calib, poisoned.calib)
    pd.testing.assert_frame_equal(clean.bias.additive, poisoned.bias.additive)
