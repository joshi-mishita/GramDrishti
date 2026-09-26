"""Provisional forecast and placeholder helpers."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from gramdrishti.api.service import num
from gramdrishti.provisional import agro, placeholders
from gramdrishti.provisional.forecast import prob_exceed


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

