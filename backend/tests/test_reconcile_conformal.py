"""Unit tests on hand-made frames: reconciliation, conformal offsets, constraints and humidity."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gramdrishti.models.conformal import (
    apply_offsets,
    coverage_table,
    cqr_offset,
    enforce_constraints,
    fit_offsets,
)
from gramdrishti.models.humidity import dewpoint_from_rh, rh_from_dewpoint
from gramdrishti.models.reconcile import GROUP, max_block_error, reconcile, reconcile_bounded

STATS = ["mean", "p10", "p50", "p90"]


def _frame(values: list[list[float]], target: list[float], prefix: str = "x") -> pd.DataFrame:
    """One block-day per entry of ``values`` (Panchayat means); quantiles at mean -1, mean, mean +1."""
    rows = []
    for day, (vals, tgt) in enumerate(zip(values, target, strict=True)):
        for i, v in enumerate(vals):
            rows.append({"issue_date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=day), "lead_day": 1,
                         "block_id": "B1", "pid": i, f"{prefix}_mean": v, f"{prefix}_p10": v - 1,
                         f"{prefix}_p50": v, f"{prefix}_p90": v + 1, "target": tgt})
    return pd.DataFrame(rows)


def test_additive_reconcile_hits_target_and_keeps_offsets() -> None:
    df = _frame([[30.0, 31.0, 35.0], [10.0, 12.0, 14.0]], [32.0, 11.0])
    out = reconcile(df, "x", "target", "add")
    assert max_block_error(out, "x", "target") < 1e-12
    np.testing.assert_allclose(out["x_p90"] - out["x_p10"], 2.0)          # same shift for all quantiles
    np.testing.assert_allclose(np.diff(out["x_mean"][:3]), np.diff(df["x_mean"][:3]))


def test_multiplicative_reconcile_scales_and_handles_zero_block_mean() -> None:
    df = _frame([[2.0, 4.0, 6.0], [0.0, 0.0, 0.0], [1.0, 2.0, 3.0]], [8.0, 5.0, 0.0])
    out = reconcile(df, "x", "target", "mult")
    assert max_block_error(out, "x", "target") < 1e-12
    np.testing.assert_allclose(out["x_mean"][:3], [4.0, 8.0, 12.0])        # ratio 2 keeps the pattern
    np.testing.assert_allclose(out["x_mean"][3:6], [5.0, 5.0, 5.0])        # model dry, block wet: even
    np.testing.assert_allclose(out["x_mean"][6:], 0.0)                     # block dry: all dry
    assert (out[[f"x_{s}" for s in STATS]].iloc[6:] <= 0).all().all()


def test_bounded_reconcile_respects_bounds_and_target() -> None:
    df = _frame([[99.0, 95.0, 60.0], [2.0, 1.0, 30.0]], [98.0, 3.0], prefix="rh")
    out = reconcile_bounded(df, "rh", "target", 0.0, 100.0)
    assert max_block_error(out, "rh", "target") < 1e-9
    assert out["rh_mean"].between(0, 100).all()
    # quantiles move with their mean
    np.testing.assert_allclose(out["rh_p90"] - out["rh_mean"], 1.0)


def test_group_keys_are_issue_lead_block() -> None:
    assert GROUP == ["issue_date", "lead_day", "block_id"]


def test_cqr_offset_matches_hand_computation() -> None:
    lo, hi = np.zeros(9), np.ones(9)
    y = np.array([-2, -1, 0.5, 0.5, 0.5, 0.5, 2, 3, 4], dtype=float)   # scores 2 1 -.5 -.5 -.5 -.5 1 2 3
    k = min(1.0, np.ceil(10 * 0.8) / 9)
    assert cqr_offset(lo, hi, y, 0.8) == pytest.approx(np.quantile([2, 1, -.5, -.5, -.5, -.5, 1, 2, 3], k))


def test_conformal_restores_coverage_on_iid_data() -> None:
    rng = np.random.default_rng(0)
    n = 4000
    y = rng.normal(0, 2, n)
    pred = pd.DataFrame({"lead_day": rng.integers(1, 6, n)})
    for v in ("rain", "tmax", "tmin", "rh", "wind"):
        pred[f"{v}_p10"], pred[f"{v}_p50"], pred[f"{v}_p90"] = -1.0, 0.0, 1.0    # far too narrow
    obs = pd.DataFrame({f"obs_{v}": y for v in ("tmax", "tmin", "rh", "wind", "rain")})
    half = np.arange(n) < n // 2
    off = fit_offsets(pred[half], obs[half])
    cov = coverage_table(apply_offsets(pred[~half], off), obs[~half])
    tmax = cov[cov["var"] == "tmax"]["coverage"]
    assert tmax.between(0.76, 0.84).all()


def test_enforce_constraints() -> None:
    row = {"lead_day": 1}
    for v, (a, b, c) in {"rain": (-1.0, 3.0, 2.0), "tmax": (30.0, 29.0, 31.0), "tmin": (29.5, 31.0, 32.0),
                         "rh": (-5.0, 50.0, 120.0), "wind": (-2.0, 1.0, 3.0)}.items():
        row |= {f"{v}_p10": a, f"{v}_p50": b, f"{v}_p90": c, f"{v}_mean": b}
    out = enforce_constraints(pd.DataFrame([row])).iloc[0]
    for v in ("rain", "tmax", "tmin", "rh", "wind"):
        assert out[f"{v}_p10"] <= out[f"{v}_p50"] <= out[f"{v}_p90"]
    assert out["rain_p10"] >= 0 and out["wind_p10"] >= 0
    assert out["rh_p10"] >= 0 and out["rh_p90"] <= 100
    for q in ("p10", "p50", "p90"):
        assert out[f"tmin_{q}"] < out[f"tmax_{q}"]


def test_humidity_round_trip() -> None:
    t = np.array([5.0, 20.0, 35.0, 42.0])
    rh = np.array([95.0, 60.0, 30.0, 12.0])
    np.testing.assert_allclose(rh_from_dewpoint(t, dewpoint_from_rh(t, rh)), rh, atol=1e-9)
    assert (dewpoint_from_rh(t, rh) <= t).all()
