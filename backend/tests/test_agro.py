"""Agro-variables: formulas, the soil bucket, risk levels and the dry-spell counter on hand-made inputs."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from gramdrishti.agro import derived as d
from gramdrishti.provisional import agro as scalar_agro


def test_et0_matches_scalar_hargreaves() -> None:
    for tmax, tmin, lat, day in [(40.0, 25.0, 29.0, date(2024, 6, 1)), (20.0, 5.0, 29.5, date(2024, 12, 21))]:
        vec = d.et0_hargreaves(np.array([tmax]), np.array([tmin]), np.array([lat]),
                               np.array([day.timetuple().tm_yday]))[0]
        assert vec == pytest.approx(scalar_agro.et0_hargreaves(tmax, tmin, lat, day), rel=1e-12)


def test_et0_never_negative_and_zero_without_diurnal_range() -> None:
    et0 = d.et0_hargreaves(np.array([10.0, 15.0]), np.array([12.0, 15.0]), np.array([29.0, 29.0]),
                           np.array([10, 10]))
    assert (et0 == 0).all()


def test_gdd_and_thi() -> None:
    assert d.gdd(np.array([30.0, 8.0]), np.array([20.0, 2.0]), 10.0).tolist() == [15.0, 0.0]
    assert d.thi(np.array([35.0]), np.array([40.0]))[0] == pytest.approx(0.8 * 35 + 0.4 * (35 - 14.4) + 46.4)


def test_effective_rain_removes_runoff_above_20mm() -> None:
    assert d.effective_rain(np.array([0.0, 5.0, 20.0, 80.0])).tolist() == [0.0, 5.0, 20.0, 20.0]


def test_bucket_dries_without_rain_and_never_leaves_its_range() -> None:
    cap = np.array([80.0, 80.0])
    start, end = d.run_bucket(np.array([20.0, 80.0]), cap, np.zeros((2, 5)), np.full((2, 5), 5.0),
                              np.array([1.0, 1.0]))
    assert (np.diff(end, axis=1) <= 0).all()
    assert ((end >= 0) & (end <= cap[:, None])).all()
    assert (start[:, 1:] == end[:, :-1]).all()
    # below half capacity ET is reduced (stress), so the drier bucket loses less water on day 1
    assert (start[0, 0] - end[0, 0]) < (start[1, 0] - end[1, 0])


def test_bucket_fills_to_capacity_and_unknown_state_stays_unknown() -> None:
    _, end = d.run_bucket(np.array([70.0, np.nan]), np.array([80.0, 80.0]), np.full((2, 3), 50.0),
                          np.zeros((2, 3)), np.array([1.0, 1.0]))
    assert end[0].tolist() == [80.0, 80.0, 80.0]
    assert np.isnan(end[1]).all()


def test_rain_paths_order_soil_moisture() -> None:
    cap, sm0, et0, kc = np.array([80.0]), np.array([30.0]), np.full((1, 5), 4.0), np.array([0.9])
    ends = [d.run_bucket(sm0, cap, np.full((1, 5), r), et0, kc)[1] for r in (0.0, 2.0, 12.0)]
    assert (ends[0] <= ends[1]).all() and (ends[1] <= ends[2]).all()


def test_dry_spell_counter() -> None:
    p = np.array([[0.1, 0.1, 0.5, 0.05, 0.1], [0.9, 0.9, 0.9, 0.9, 0.9]])
    assert d.dry_spell_counter(p).tolist() == [[1, 2, 0, 1, 2], [0, 0, 0, 0, 0]]


def test_frost_probability_and_levels() -> None:
    p = d.prob_below(2.0, np.array([-1.0, 3.0, 8.0]), np.array([1.0, 5.0, 10.0]), np.array([3.0, 7.0, 12.0]))
    assert p[0] > 0.5 > p[1] > p[2] >= 0
    assert d.prob_below(5.0, np.array([3.0]), np.array([5.0]), np.array([7.0]))[0] == pytest.approx(0.5)
    levels = d.frost_level(np.array([0.05, 0.2, 0.2, 0.7]), np.array([0.0, 0.0, -1.0, -1.0]))
    assert levels.tolist() == ["low", "moderate", "high", "severe"]


def test_waterlog_score_needs_known_soil_state() -> None:
    s = d.waterlog_score(np.array([0.8, 0.8, 0.8, 0.8]), np.array([True, False, True, True]),
                         np.array([0.95, 0.95, 0.5, np.nan]))
    assert s[0] > s[1] and s[0] > s[2]
    assert np.isnan(s[3])
    assert d._names(d._level(s, d.WATERLOG_CUTS)).tolist() == ["severe", "high", "high", None]


def test_fog_proxy_only_in_cold_humid_calm_winter() -> None:
    f = d.fog_proxy(np.array([12, 12, 7]), np.array([5.0, 5.0, 5.0]), np.array([90.0, 50.0, 90.0]),
                    np.array([3.0, 3.0, 3.0]))
    assert f.tolist() == [True, False, False]


def _pred(pids: list[str], rain_p50: float) -> pd.DataFrame:
    rows = []
    for pid in pids:
        for lead in range(1, 6):
            rows.append({"panchayat_id": pid, "lead_day": lead, "valid_date": pd.Timestamp(2024, 9, 9 + lead),
                         "tmax_p50": 33.0, "tmin_p10": 23.0, "tmin_p50": 25.0, "tmin_p90": 27.0,
                         "td_p50": 24.0, "rh_p50": 80.0, "wind_p50": 5.0, "rain_p10": 0.0,
                         "rain_p50": rain_p50, "rain_p90": 3 * rain_p50, "prob_rain_ge_1": 0.1,
                         "prob_rain_ge_35": 0.6, "ndvi": 0.6})
    return pd.DataFrame(rows)


def test_derive_shapes_ranges_and_waterlogging() -> None:
    static = pd.DataFrame({"panchayat_id": ["A", "B"], "lat": [29.0, 29.0], "whc_mm_per_m": [130.0, 130.0],
                           "drainage_class": ["poor", "good"], "tpi_z": [0.0, 0.0]})
    out = d.derive(_pred(["A", "B"], 30.0), static, pd.Series({"A": 0.95, "B": 0.95}))
    assert len(out) == 10 and not out.duplicated(["panchayat_id", "lead_day"]).any()
    for c in ("soil_moisture_frac", "soil_moisture_frac_dry", "soil_moisture_frac_wet"):
        assert out[c].between(0, 1).all()
    assert (out["soil_moisture_frac_dry"] <= out["soil_moisture_frac"] + 1e-12).all()
    assert (out["soil_moisture_frac"] <= out["soil_moisture_frac_wet"] + 1e-12).all()
    assert np.allclose(out["depletion_frac"], 1 - out["soil_moisture_frac"])
    lead1 = out[out["lead_day"] == 1].set_index("panchayat_id")
    assert lead1.loc["A", "waterlog_score"] > lead1.loc["B", "waterlog_score"]   # poor drainage
    assert out["dry_spell_days"].tolist()[:5] == [1, 2, 3, 4, 5]
    assert set(out.columns) >= {f"gdd_{c}" for c in d.TBASE_C}


def test_derive_without_soil_state_gives_nulls_not_errors() -> None:
    static = pd.DataFrame({"panchayat_id": ["A"], "lat": [29.0], "whc_mm_per_m": [130.0],
                           "drainage_class": ["poor"], "tpi_z": [0.0]})
    out = d.derive(_pred(["A"], 5.0), static, pd.Series({"A": np.nan}))
    assert out["soil_moisture_frac"].isna().all() and out["waterlog_risk"].isna().all()
    assert out["et0_mm"].notna().all() and out["thi"].notna().all()
