import numpy as np
import pandas as pd
import pytest

from gramdrishti.data.config import COLS, window_bounds
from gramdrishti.data.qc import clean_values, run_qc
from gramdrishti.models.baselines import (
    StationOffsets,
    apply_b2,
    fit_baselines,
    fit_station_offsets,
    idw_offsets,
    to_panchayats,
)

from .conftest import needs_oracle

TRAIN_END = window_bounds("TRAIN")[1]


def tiny_static() -> pd.DataFrame:
    return pd.DataFrame({"panchayat_id": ["P1", "P2", "P3"], "block_id": ["B1", "B1", "B1"],
                         "lat": [29.00, 29.00, 29.00], "lon": [75.00, 75.05, 75.10],
                         "elevation_m": [200.0, 200.0, 350.0]})


def tiny_stations() -> pd.DataFrame:
    return pd.DataFrame({"station_id": ["S1", "S2"], "panchayat_id": ["P1", "P2"], "block_id": ["B1", "B1"],
                         "lat": [29.00, 29.00], "lon": [75.00, 75.05], "elevation_m": [200.0, 200.0]})


def test_to_panchayats_copies_block_value():
    block = pd.DataFrame({"block_id": ["B1"], "valid_date": [pd.Timestamp("2024-05-01")], "tmax_c": [33.0]})
    out = to_panchayats(block, tiny_static())
    assert len(out) == 3 and (out["tmax_c"] == 33.0).all()


def test_idw_excludes_own_station():
    table = pd.DataFrame({"station_id": ["S1", "S2"], "col": "tmax_c", "season": "winter",
                          "value": [1.0, 5.0]})
    off = StationOffsets("TRAIN", TRAIN_END, TRAIN_END, table)
    v = idw_offsets(off, tiny_stations(), tiny_static()).set_index("panchayat_id")["value"]
    assert v["P1"] == pytest.approx(5.0)   # only S2 may inform P1
    assert v["P2"] == pytest.approx(1.0)   # only S1 may inform P2
    assert 1.0 < v["P3"] < 5.0 and v["P3"] > 3.0   # both, nearer S2 weighs more


def test_apply_b2_lapse_and_offsets():
    static = tiny_static()
    b1 = pd.DataFrame({"panchayat_id": ["P1", "P3"], "block_id": "B1",
                       "valid_date": pd.Timestamp("2024-01-10"), "rain_mm": 10.0, "tmax_c": 20.0,
                       "tmin_c": 8.0, "rh_mean_pct": 99.0, "wind_kmh": 5.0})
    idw = pd.DataFrame({"panchayat_id": ["P1", "P1", "P1"], "col": ["rh_mean_pct", "wind_kmh", "rain_mm"],
                        "season": ["winter", "winter", "non_monsoon"],
                        "value": [3.0, np.log(2.0), np.log(0.5)]})
    out = apply_b2(b1, idw, static).set_index("panchayat_id")
    block_mean = static["elevation_m"].mean()   # 250 m
    assert out.loc["P3", "tmax_c"] == pytest.approx(20.0 - 0.0065 * (350 - block_mean))
    assert out.loc["P1", "tmin_c"] == pytest.approx(8.0 - 0.0065 * (200 - block_mean))
    assert out.loc["P1", "rh_mean_pct"] == 100.0            # 99 + 3 clipped
    assert out.loc["P1", "wind_kmh"] == pytest.approx(10.0)
    assert out.loc["P1", "rain_mm"] == pytest.approx(5.0)
    assert out.loc["P3", "rain_mm"] == 10.0                  # no offset available: unchanged


def test_station_offsets_recover_planted_anomaly():
    dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
    ref = pd.DataFrame({"date": dates, "block_id": "B1", "rain_mm": 2.0, "tmax_c": 30.0, "tmin_c": 15.0,
                        "rh_mean_pct": 60.0, "wind_kmh": 5.0})
    obs = pd.DataFrame({"date": dates, "station_id": "S1", "rain_mm": 3.0, "tmax_c": 29.0, "tmin_c": 15.5,
                        "rh_mean_pct": 64.0, "wind_kmh": 4.0})
    late = obs["date"] > TRAIN_END
    obs.loc[late, "tmax_c"] = 99.0      # garbage after TRAIN must not matter
    off = fit_station_offsets(obs, tiny_stations(), tiny_static(), ref)
    assert off.data_max_date <= TRAIN_END
    t = off.table.set_index(["col", "season"])["value"]
    lapse = -0.0065 * (200 - 250)       # S1 sits 50 m below the block mean
    assert t[("tmax_c", "winter")] == pytest.approx(-1.0 - lapse)
    assert t[("rh_mean_pct", "monsoon")] == pytest.approx(4.0)
    assert t[("wind_kmh", "winter")] == pytest.approx(np.log(0.8))
    assert t[("rain_mm", "monsoon")] == pytest.approx(np.log(1.5))


@needs_oracle
def test_baselines_on_mock_calib(fc, static, stations, obs, block_truth):
    b = fit_baselines(fc, block_truth, clean_values(run_qc(obs)), stations, static)
    assert b.bias.data_max_date <= TRAIN_END and b.offsets.data_max_date <= TRAIN_END
    lo, hi = window_bounds("CALIB")
    preds = b.predict(fc[(fc.valid_date >= lo) & (fc.valid_date <= hi)])
    n = 76 * len(static) * 5
    for name, p in preds.items():
        assert len(p) == n, name
        assert not p[list(COLS.values())].isna().any().any(), name
        assert (p["rain_mm"] >= 0).all() and p["rh_mean_pct"].between(0, 100).all()
    # B0 and B1 are constant within a block; B2 varies
    for name, varies in (("B0", False), ("B1", False), ("B2", True)):
        spread = preds[name].groupby(["block_id", "valid_date", "lead_day"])["tmax_c"].std().max()
        assert bool(spread > 1e-9) == varies, name
