import numpy as np
import pandas as pd

from gramdrishti.data.qc import VALUE_COLS, clean_values, qc_summary, run_qc


def rows(station: str, start: str, values: list[dict]) -> pd.DataFrame:
    """One row per consecutive day; unspecified variables get ordinary, varying values."""
    out = []
    for i, v in enumerate(values):
        base = {"rain_mm": 0.0, "tmax_c": 30.0 + 0.1 * i, "tmin_c": 18.0 + 0.1 * i,
                "rh_mean_pct": 50.0 + i, "wind_kmh": 5.0 + 0.1 * i}
        base.update(v)
        out.append({"date": pd.Timestamp(start) + pd.Timedelta(days=i), "station_id": station, **base})
    return pd.DataFrame(out)


def test_clean_rows_get_no_flags():
    f = run_qc(rows("S1", "2024-01-01", [{}] * 6))
    assert not f["qc_any"].any()
    assert not f[[c for c in f.columns if c.startswith("qc_")]].any().any()


def test_range_flags():
    f = run_qc(rows("S1", "2024-01-01", [
        {"rain_mm": -1.0}, {"rain_mm": 401.0}, {"tmax_c": 60.0, "tmin_c": 40.0},
        {"rh_mean_pct": 105.0}, {"wind_kmh": 130.0}, {"tmin_c": -11.0, "tmax_c": 5.0},
    ]))
    assert f["qc_range_rain_mm"].tolist() == [True, True, False, False, False, False]
    assert f["qc_range_tmax_c"].tolist() == [False, False, True, False, False, False]
    assert f["qc_range_tmin_c"].tolist() == [False, False, True, False, False, True]
    assert f["qc_range_rh_mean_pct"].tolist() == [False, False, False, True, False, False]
    assert f["qc_range_wind_kmh"].tolist() == [False, False, False, False, True, False]


def test_consistency_flags():
    f = run_qc(rows("S1", "2024-01-01", [
        {"tmax_c": 20.0, "tmin_c": 22.0},   # tmin above tmax
        {"tmax_c": 20.0, "tmin_c": 19.5},   # diurnal range 0.5
        {"tmax_c": 40.0, "tmin_c": 10.0},   # diurnal range 30
        {"tmax_c": 30.0, "tmin_c": 20.0},   # fine
        {"tmax_c": np.nan, "tmin_c": 20.0},  # cannot check
    ]))
    assert f["qc_consistency"].tolist() == [True, True, True, False, False]
    assert f["qc_bad_tmax_c"].tolist()[:3] == [True, True, True]


def test_spike_uses_previous_calendar_day_only():
    a = rows("S1", "2024-03-01", [{"tmax_c": 30.0}, {"tmax_c": 43.0}, {"tmax_c": 42.0}])
    b = rows("S1", "2024-03-10", [{"tmax_c": 20.0}])         # 7-day gap: not a spike
    c = rows("S2", "2024-03-02", [{"tmax_c": 45.0}])         # other station: not a spike
    f = run_qc(pd.concat([a, b, c], ignore_index=True))
    assert f["qc_spike_tmax_c"].tolist() == [False, True, False, False, False]
    assert not f["qc_spike_tmin_c"].any()


def test_stuck_sensor():
    five = rows("S1", "2024-05-01", [{"rh_mean_pct": 55.0}] * 5)
    four = rows("S2", "2024-05-01", [{"rh_mean_pct": 55.0}] * 4)
    zeros = rows("S3", "2024-05-01", [{"rain_mm": 0.0}] * 10)
    gap = pd.concat([rows("S4", "2024-05-01", [{"wind_kmh": 9.0}] * 3),
                     rows("S4", "2024-05-05", [{"wind_kmh": 9.0}] * 2)])   # 2024-05-04 absent
    f = run_qc(pd.concat([five, four, zeros, gap], ignore_index=True))
    by = f.groupby("station_id")
    assert by["qc_stuck_rh_mean_pct"].all()["S1"]
    assert not by["qc_stuck_rh_mean_pct"].any()["S2"]
    assert not by["qc_stuck_rain_mm"].any()["S3"]
    assert not by["qc_stuck_wind_kmh"].any()["S4"]


def test_missing_flags_and_rows_never_deleted():
    raw = rows("S1", "2024-01-01", [{"tmax_c": np.nan}, {"rain_mm": -5.0}, {}])
    f = run_qc(raw)
    assert len(f) == len(raw)
    pd.testing.assert_frame_equal(f[raw.columns], raw)          # values untouched
    assert f["qc_missing_tmax_c"].tolist() == [True, False, False]
    cleaned = clean_values(f)
    assert len(cleaned) == len(raw) and np.isnan(cleaned.loc[1, "rain_mm"])


def test_summary_counts_absent_days_and_empty_months():
    a = rows("S1", "2024-01-01", [{}] * 31)
    a.loc[3, "rain_mm"] = np.nan
    a.loc[5, "rh_mean_pct"] = 120.0
    b = rows("S2", "2024-01-01", [{}] * 20)       # 11 January days absent, no February rows at all
    c = rows("S1", "2024-02-01", [{}] * 29)
    s = qc_summary(run_qc(pd.concat([a, b, c], ignore_index=True))).set_index(["station_id", "month"])
    assert s.loc[("S1", "2024-01"), "expected_days"] == 31
    assert s.loc[("S1", "2024-01"), "missing_rain_mm"] == 1
    assert s.loc[("S1", "2024-01"), "flagged_rh_mean_pct"] == 1
    assert s.loc[("S2", "2024-01"), "missing_rain_mm"] == 11
    assert s.loc[("S2", "2024-02"), "missing_rain_mm"] == 29
    assert {f"missing_{c}" for c in VALUE_COLS} <= set(s.columns)


def test_qc_on_mock_observations(obs):
    f = run_qc(obs)
    assert len(f) == len(obs)
    assert f["qc_missing_rain_mm"].sum() == obs["rain_mm"].isna().sum()
