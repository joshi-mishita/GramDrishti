"""Provisional forecast, risk and placeholder helpers."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from gramdrishti.api.service import Service, num
from gramdrishti.contract.pick_demo_dates import load_demo_dates
from gramdrishti.provisional import agro, placeholders
from gramdrishti.provisional.forecast import prob_exceed
from gramdrishti.provisional.risk import level_of

from .conftest import needs_oracle


def test_prob_exceed_bounds_and_monotone() -> None:
    thr = np.linspace(-5, 80, 200)
    p = [prob_exceed(t, 0.0, 6.0, 20.0) for t in thr]
    assert all(0.0 <= x <= 1.0 for x in p)
    assert all(a >= b for a, b in zip(p, p[1:], strict=False))
    assert prob_exceed(6.0, 0.0, 6.0, 20.0) == pytest.approx(0.5)
    assert prob_exceed(20.0, 0.0, 6.0, 20.0) == pytest.approx(0.1)
    assert prob_exceed(1.0, 0.0, 0.0, 0.0) == 0.0
    assert prob_exceed(1.0, float("nan"), 1.0, 2.0) is None


def test_num_never_returns_non_finite() -> None:
    assert num(float("nan")) is None and num(float("inf")) is None and num(None) is None
    assert num(1.23456) == 1.23


def test_level_cuts() -> None:
    assert [level_of(x) for x in (0.0, 0.3, 0.6, 0.9)] == ["low", "moderate", "high", "severe"]


def test_thi_and_et0() -> None:
    assert agro.thi(30.0, 70.0) == pytest.approx(81.38, abs=0.01)  # 86 - 0.165 * 28
    summer = agro.et0_hargreaves(40.0, 25.0, 29.0, date(2024, 6, 1))
    winter = agro.et0_hargreaves(20.0, 5.0, 29.0, date(2024, 12, 21))
    assert summer is not None and winter is not None and summer > winter > 0


def test_placeholders_are_deterministic() -> None:
    assert placeholders.verification_summary() == placeholders.verification_summary()
    args = ("monsoon_2024", "spray", 90)
    assert placeholders.impact(*args) == placeholders.impact(*args)


def test_explain_reasons(static) -> None:  # noqa: ANN001
    r = placeholders.explain_reasons(static, "MP0103", "tmax")
    assert 1 <= len(r) <= 3
    assert all(x["effect"] in ("warmer", "cooler") for x in r)
    assert placeholders.explain_reasons(static, "MP0103", "tmax") == r


@needs_oracle
@pytest.mark.parametrize("d", [p.date for p in load_demo_dates()])
def test_block_consistency_and_ordering(d: str) -> None:
    """Rule 6: the block mean of Panchayat p50 equals the block target within 1e-6 (trivial for B1)."""
    svc = Service()
    t = svc.table(date.fromisoformat(d))
    assert set(t["lead_day"]) == {1, 2, 3, 4, 5}
    for var in ("rain", "tmax", "tmin", "rh", "wind"):
        g = t.groupby(["block_id", "lead_day"])[f"{var}_p50"]
        assert np.allclose(g.mean(), g.first(), atol=1e-6)
        assert (t[f"{var}_p10"] <= t[f"{var}_p50"] + 1e-9).all()
        assert (t[f"{var}_p50"] <= t[f"{var}_p90"] + 1e-9).all()
    assert (t["rain_p10"] >= 0).all()
    assert t["rh_p10"].between(0, 100).all() and t["rh_p90"].between(0, 100).all()
    assert (t["tmin_p50"] < t["tmax_p50"]).all()
