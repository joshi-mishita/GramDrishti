"""Feature table: windows, purge, no oracle features, no data after the issue date."""

from __future__ import annotations

import pandas as pd
import pytest

from gramdrishti.data import loaders
from gramdrishti.data.config import LEADS, window_bounds
from gramdrishti.features.static import fit_encodings
from gramdrishti.features.table import Inputs, feature_names, load_inputs, make_table
from gramdrishti.models.bias import block_reference, fit_bias

from .conftest import needs_oracle

# The B1 bias model is fitted against block truth (MOCK ONLY target), so the whole module needs the oracle.
pytestmark = needs_oracle

ORACLE_ONLY = {"dewpoint_c", "et0_mm", "soil_moisture_frac", "waterlog_flag"}


@pytest.fixture(scope="module")
def setup() -> tuple[Inputs, object, dict]:
    inputs = load_inputs()
    bias = fit_bias(inputs.fc, block_reference(inputs.obs_clean, inputs.stations), "TRAIN")
    return inputs, bias, fit_encodings(inputs.static)


def test_feature_names_have_no_targets_or_oracle_columns() -> None:
    names = feature_names()
    assert len(names) == len(set(names))
    assert not [n for n in names if n.startswith(("obs_", "y_", "ev_", "b0_")) or n in ORACLE_ONLY]


def test_infer_table_never_touches_the_oracle(setup, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs, bias, enc = setup

    def boom() -> None:
        raise AssertionError("oracle read while building features")

    monkeypatch.setattr(loaders, "load_truth", boom)
    monkeypatch.setattr(loaders, "load_block_truth", boom)
    t = make_table("infer", inputs, bias, enc, issue_dates=["2024-03-31", "2024-09-09"])
    assert len(t) == 2 * len(LEADS) * len(inputs.static)
    assert not [c for c in t.columns if c.startswith(("obs_", "y_", "ev_"))]


def test_test_window_is_refused(setup) -> None:
    inputs, bias, enc = setup
    with pytest.raises(PermissionError):
        make_table("train", inputs, bias, enc, window="TEST")


def test_windows_and_purge(setup) -> None:
    inputs, bias, enc = setup
    tr = make_table("train", inputs, bias, enc, window="TRAIN")
    ca = make_table("train", inputs, bias, enc, window="CALIB")
    (tr_start, tr_end), (ca_start, ca_end) = window_bounds("TRAIN"), window_bounds("CALIB")
    assert tr["valid_date"].max() < ca["valid_date"].min()
    assert tr["issue_date"].max() < ca["issue_date"].min()
    assert tr["issue_date"].min() >= tr_start and tr["valid_date"].max() <= tr_end
    assert ca["issue_date"].min() >= ca_start and ca["valid_date"].max() <= ca_end
    # every kept issue date has all five lead days (purge drops partial windows)
    assert (tr.groupby("issue_date")["lead_day"].nunique() == len(LEADS)).all()
    assert (ca.groupby("issue_date")["lead_day"].nunique() == len(LEADS)).all()


def test_dynamic_features_use_only_data_before_the_issue_date(setup) -> None:
    inputs, bias, enc = setup
    issues = pd.date_range("2023-06-01", "2024-06-30", freq="17D")
    t = make_table("infer", inputs, bias, enc, issue_dates=issues)
    assert (t["ndvi_source_date"].dropna() <= t["issue_date"][t["ndvi_source_date"].notna()]).all()
    assert (t["lst_source_date"].dropna() <= t["issue_date"][t["lst_source_date"].notna()]).all()
    assert (t["stn_source_date"] < t["issue_date"]).all()
    assert (t["valid_date"] - t["issue_date"]).dt.days.eq(t["lead_day"]).all()


def test_features_ignore_everything_after_the_issue_date(setup) -> None:
    """Poison every input dated after D (and forecasts issued after D): features for D must not change."""
    inputs, bias, enc = setup
    D = pd.Timestamp("2024-02-15")
    before = make_table("infer", inputs, bias, enc, issue_dates=[D])
    fc, sat, obs = inputs.fc.copy(), inputs.sat.copy(), inputs.obs_clean.copy()
    fc.loc[fc["issue_date"] > D, ["rain_mm", "tmax_c"]] = 999.0
    sat.loc[sat["week_start"] + pd.Timedelta(days=7) > D, ["ndvi", "lst_day_c"]] = 9.0
    obs.loc[obs["date"] >= D, "rain_mm"] = 999.0
    poisoned = Inputs(fc, inputs.static, inputs.blocks, sat, obs, inputs.stations)
    after = make_table("infer", poisoned, bias, enc, issue_dates=[D])
    pd.testing.assert_frame_equal(before[feature_names()], after[feature_names()])


def test_relative_static_features_sum_to_zero_per_block(setup) -> None:
    inputs, bias, enc = setup
    t = make_table("infer", inputs, bias, enc, issue_dates=["2024-01-12"])
    one = t[t["lead_day"] == 1]
    sums = one.groupby("block_id")[["irrigated_frac_rel", "tpi_z_rel"]].sum()
    assert sums.abs().max().max() < 1e-9
