import numpy as np
import pandas as pd
import pytest

from gramdrishti.data.config import COLS, window_bounds
from gramdrishti.models.bias import (
    apply_bias,
    apply_qm,
    apply_rain_qm,
    block_reference,
    combine_sources,
    fit_bias,
    fit_rain_qm,
)

from .conftest import needs_oracle

TRAIN_END = window_bounds("TRAIN")[1]


def synthetic(days: int = 900, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reference weather plus two sources with known, planted errors, over TRAIN and later dates."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=days, freq="D")
    rain = np.where(rng.random(days) < 0.2, rng.gamma(0.8, 8.0, days), 0.0)
    ref = pd.DataFrame({"date": dates, "block_id": "B1", "rain_mm": rain,
                        "tmax_c": 30 + 5 * rng.standard_normal(days),
                        "tmin_c": 15 + 4 * rng.standard_normal(days),
                        "rh_mean_pct": 60 + 10 * rng.standard_normal(days), "wind_kmh": 6 + rng.random(days)})
    frames = []
    for src, t_off, noise, wind_f in (("a", 2.0, 0.5, 1.25), ("b", -1.0, 1.5, 0.8)):
        f = ref.rename(columns={"date": "valid_date"}).copy()
        f["source"], f["lead_day"] = src, 1
        f["issue_date"] = f["valid_date"] - pd.Timedelta(days=1)
        f["tmax_c"] = f["tmax_c"] + t_off + noise * rng.standard_normal(days)
        f["tmin_c"] = f["tmin_c"] + t_off + noise * rng.standard_normal(days)
        f["rh_mean_pct"] = f["rh_mean_pct"] - 3 * t_off
        f["wind_kmh"] = f["wind_kmh"] * wind_f
        f["rain_mm"] = np.where(rng.random(days) < 0.15, rng.gamma(0.5, 3.0, days), 0.0) + 1.5 * f["rain_mm"]
        frames.append(f)
    return pd.concat(frames, ignore_index=True), ref


# ------------------------------------------------------------------ quantile mapping
def test_apply_qm_is_flat_outside_range():
    fq, oq = np.array([0.0, 1.0, 2.0]), np.array([10.0, 20.0, 30.0])
    assert apply_qm(np.array([-5.0, 0.5, 9.0]), fq, oq).tolist() == [10.0, 15.0, 30.0]


def test_rain_qm_matches_wet_day_frequency_and_stays_non_negative():
    rng = np.random.default_rng(1)
    obs = np.where(rng.random(5000) < 0.1, rng.gamma(0.8, 10, 5000) + 1.0, 0.0)
    fc = np.where(rng.random(5000) < 0.3, rng.gamma(0.8, 5, 5000), 0.0)
    p = fit_rain_qm(fc, obs)
    y = apply_rain_qm(fc, p)
    assert (y >= 0).all()
    assert abs((y >= 1.0).mean() - (obs >= 1.0).mean()) < 0.01
    assert np.isnan(apply_rain_qm(np.array([np.nan]), p)[0])


def test_rain_qm_when_forecast_is_too_dry():
    obs = np.array([0.0] * 50 + [5.0] * 50)
    fc = np.array([0.0] * 90 + [3.0] * 10)
    p = fit_rain_qm(fc, obs)
    assert p["cut"] == 3.0
    assert (apply_rain_qm(np.array([0.0, 3.0]), p) == np.array([0.0, 5.0])).all()
    assert fit_rain_qm(np.zeros(10), np.zeros(10))["qm"] is None


# ------------------------------------------------------------------ planted biases
def test_fit_recovers_planted_biases():
    fc, ref = synthetic()
    model = fit_bias(fc, ref)
    add = model.additive.set_index(["col", "source", "season"])["offset"]
    assert add.loc[("tmax_c", "a", "monsoon")] == pytest.approx(2.0, abs=0.2)
    assert add.loc[("tmax_c", "b", "winter")] == pytest.approx(-1.0, abs=0.3)
    assert add.loc[("rh_mean_pct", "a", "winter")] == pytest.approx(-6.0, abs=1e-6)
    ratio = model.wind_ratio.set_index("source")["ratio"]
    assert ratio["a"] == pytest.approx(1 / 1.25) and ratio["b"] == pytest.approx(1 / 0.8)
    w = model.weights.set_index(["col", "source"])["weight"]
    assert w[("tmax_c", "a")] > w[("tmax_c", "b")]   # the less noisy source gets more weight
    assert model.weights.groupby(["col", "lead_day"])["weight"].sum().round(12).eq(1.0).all()


def test_combine_sources_mean_spread_and_missing_source():
    fc, _ = synthetic(days=3)
    b0 = combine_sources(fc)
    a, b = fc[fc.source == "a"].reset_index(drop=True), fc[fc.source == "b"].reset_index(drop=True)
    assert np.allclose(b0["tmax_c"], (a["tmax_c"] + b["tmax_c"]) / 2)
    assert np.allclose(b0["tmax_c_spread"], (a["tmax_c"] - b["tmax_c"]).abs())
    only_a = combine_sources(fc[fc.source == "a"])
    assert np.allclose(only_a["tmax_c"], a["tmax_c"]) and (only_a["tmax_c_spread"] == 0).all()


# ------------------------------------------------------------------ leakage
def _corrupt_after_train(fc: pd.DataFrame, ref: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fc2, ref2 = fc.copy(), ref.copy()
    for df, col in ((fc2, "valid_date"), (ref2, "date")):
        late = df[col] > TRAIN_END
        assert late.any()
        for c in COLS.values():
            df.loc[late, c] = df.loc[late, c] * 7 + 50
    return fc2, ref2


def _assert_same_model(m1, m2):
    pd.testing.assert_frame_equal(m1.additive, m2.additive)
    pd.testing.assert_frame_equal(m1.wind_ratio, m2.wind_ratio)
    pd.testing.assert_frame_equal(m1.weights, m2.weights)
    assert m1.rain_qm.keys() == m2.rain_qm.keys()
    for k in m1.rain_qm:
        assert m1.rain_qm[k]["cut"] == m2.rain_qm[k]["cut"]
        np.testing.assert_array_equal(m1.rain_qm[k]["qm"][1], m2.rain_qm[k]["qm"][1])


def test_bias_fit_ignores_data_after_train_synthetic():
    fc, ref = synthetic()
    m1 = fit_bias(fc, ref)
    assert m1.data_max_date <= TRAIN_END
    _assert_same_model(m1, fit_bias(*_corrupt_after_train(fc, ref)))


@needs_oracle
def test_bias_fit_uses_no_future_data_on_mock(fc, block_truth):
    m1 = fit_bias(fc, block_truth)
    assert m1.fit_end == TRAIN_END
    assert m1.data_max_date == TRAIN_END            # uses TRAIN up to its last day, never beyond
    _assert_same_model(m1, fit_bias(*_corrupt_after_train(fc, block_truth)))


# ------------------------------------------------------------------ effect on CALIB
@needs_oracle
def test_b1_reduces_mean_bias_on_calib(fc, block_truth):
    """Block-level mean bias on CALIB: B1 (corrected) is smaller than B0 (raw) for at least one variable."""
    model = fit_bias(fc, block_truth)
    lo, hi = window_bounds("CALIB")
    fc_c = fc[(fc.valid_date >= lo) & (fc.valid_date <= hi)]
    ref = block_truth.rename(columns={"date": "valid_date"})
    improved = {}
    for name, frame in (("B0", combine_sources(fc_c)),
                        ("B1", combine_sources(apply_bias(fc_c, model), model.weights))):
        m = frame.merge(ref, on=["block_id", "valid_date"], suffixes=("", "_ref"))
        improved[name] = {c: abs((m[c] - m[f"{c}_ref"]).mean()) for c in COLS.values()}
    better = [c for c in COLS.values() if improved["B1"][c] < improved["B0"][c]]
    assert better, f"B1 did not reduce |mean bias| for any variable: {improved}"


def test_block_reference_real_mode_uses_station_means(monkeypatch):
    monkeypatch.setenv("DATA_MODE", "real")
    obs = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"] * 2), "station_id": ["s1", "s2"],
                        "rain_mm": [1.0, 3.0], "tmax_c": [20.0, np.nan], "tmin_c": [5.0, 7.0],
                        "rh_mean_pct": [50.0, 70.0], "wind_kmh": [4.0, 6.0]})
    st = pd.DataFrame({"station_id": ["s1", "s2"], "block_id": ["B1", "B1"]})
    ref = block_reference(obs, st)
    assert ref.loc[0, "rain_mm"] == 2.0 and ref.loc[0, "tmax_c"] == 20.0
    with pytest.raises(ValueError):
        block_reference()
