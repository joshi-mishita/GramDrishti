import numpy as np
import pytest

from gramdrishti.verify.metrics import continuous_scores, event_scores


def test_continuous_scores():
    s = continuous_scores(np.array([1.0, 3.0, np.nan]), np.array([2.0, 1.0, 5.0]))
    assert s["n"] == 2
    assert s["mae"] == pytest.approx(1.5)
    assert s["rmse"] == pytest.approx(np.sqrt(2.5))
    assert s["bias"] == pytest.approx(0.5)
    assert continuous_scores(np.array([]), np.array([]))["mae"] is None


def test_event_scores():
    pred = np.array([3.0, 3.0, 0.0, 0.0, 5.0])
    obs = np.array([3.0, 0.0, 3.0, 0.0, 2.5])
    s = event_scores(pred, obs, 2.5)
    assert (s["hits"], s["misses"], s["false_alarms"]) == (2, 1, 1)
    assert s["pod"] == pytest.approx(2 / 3)
    assert s["far"] == pytest.approx(1 / 3)
    assert s["csi"] == pytest.approx(0.5)
    none = event_scores(np.zeros(3), np.zeros(3), 2.5)
    assert none["pod"] is None and none["far"] is None and none["csi"] is None


# ---------------------------------------------------------------- S10 metrics on hand-computed cases
from gramdrishti.verify import metrics as mt  # noqa: E402


def test_contingency_and_frequency_bias():
    obs = np.array([1, 1, 1, 0, 0, 0, 0, 0], dtype=bool)
    fc = np.array([1, 1, 0, 1, 1, 0, 0, 0], dtype=bool)
    c = mt.contingency(obs, fc)
    assert (c["hits"], c["misses"], c["false_alarms"]) == (2, 1, 2)
    assert c["pod"] == pytest.approx(2 / 3)
    assert c["far"] == pytest.approx(2 / 4)
    assert c["csi"] == pytest.approx(2 / 5)
    assert c["frequency_bias"] == pytest.approx(4 / 3)       # forecast yes 4 times, observed 3 times
    none = mt.contingency(np.zeros(3, bool), np.zeros(3, bool))
    assert none["pod"] is None and none["frequency_bias"] is None


def test_brier_and_skill():
    p, o = np.array([0.9, 0.1, 0.5, 0.0]), np.array([1, 0, 1, 0])
    assert mt.brier(p, o) == pytest.approx((0.01 + 0.01 + 0.25 + 0) / 4)
    clim = np.full(4, 0.5)
    assert mt.brier(clim, o) == pytest.approx(0.25)
    assert mt.brier_skill(p, o, clim) == pytest.approx(1 - 0.0675 / 0.25)
    assert mt.skill(1.0, 2.0) == pytest.approx(0.5)
    assert mt.skill(3.0, 2.0) == pytest.approx(-0.5)
    assert mt.skill(1.0, 0.0) is None and mt.skill(None, 1.0) is None


def test_reliability_points():
    p = np.array([0.05, 0.08, 0.95, 1.0, 0.55])
    o = np.array([0, 1, 1, 1, 0])
    pts = mt.reliability(p, o)
    # empty bins are left out; p = 1.0 falls in the top bin
    assert [pt["forecast_prob"] for pt in pts] == [0.05, 0.55, 0.95]
    assert [pt["n"] for pt in pts] == [2, 1, 2]
    assert pts[0]["observed_freq"] == 0.5 and pts[0]["mean_forecast_prob"] == pytest.approx(0.065)
    assert pts[2]["observed_freq"] == 1.0


def test_interval_coverage_and_width():
    c = mt.interval_coverage(np.array([0, 0, 0, np.nan]), np.array([2, 4, 2, 1]), np.array([1, 5, 2, 0]))
    assert c == {"n": 3, "coverage": pytest.approx(2 / 3), "mean_width": pytest.approx(8 / 3)}
    assert mt.interval_coverage(np.array([]), np.array([]), np.array([]))["coverage"] is None


def test_pinball_and_quantile_loss():
    y = np.array([10.0, 0.0])
    assert mt.pinball(np.array([8.0, 2.0]), y, 0.9).tolist() == pytest.approx([1.8, 0.2])
    assert mt.pinball(np.array([8.0, 2.0]), y, 0.1).tolist() == pytest.approx([0.2, 1.8])
    # a point forecast scored at 0.1, 0.5 and 0.9 loses half its absolute error
    point = np.array([8.0, 2.0])
    ql = mt.quantile_loss_rows(dict.fromkeys((0.1, 0.5, 0.9), point), y)
    assert ql.tolist() == pytest.approx((np.abs(point - y) / 2).tolist())


def test_daily_sums_orders_days():
    days = np.array(["2024-01-02", "2024-01-01", "2024-01-02"])
    days, sums = mt.daily_sums(days, np.array([1.0, 2.0, 3.0]))
    assert days.tolist() == ["2024-01-01", "2024-01-02"] and sums.tolist() == [2.0, 4.0]


def test_block_bootstrap_ci_exact_and_reproducible():
    rng = np.random.default_rng(1)
    base = rng.uniform(1, 3, 60)
    # model error is exactly half the baseline error every day: every resample gives skill 0.5
    assert mt.block_bootstrap_ci(base / 2, base) == pytest.approx([0.5, 0.5])
    assert mt.block_bootstrap_ci(base / 4, base, squared=True) == pytest.approx([0.5, 0.5])
    noisy = base * rng.uniform(0.6, 1.2, 60)
    a = mt.block_bootstrap_ci(noisy, base, seed=7)
    assert a == mt.block_bootstrap_ci(noisy, base, seed=7)                  # same seed, same interval
    assert a != mt.block_bootstrap_ci(noisy, base, seed=8)
    point = 1 - noisy.sum() / base.sum()
    assert a[0] < point < a[1]
    assert mt.block_bootstrap_ci(noisy[:13], base[:13]) is None             # fewer than two 7-day blocks


def test_verdict_from_interval():
    assert mt.verdict([0.01, 0.2]) == "win"
    assert mt.verdict([-0.2, -0.01]) == "loss"
    assert mt.verdict([-0.1, 0.1]) == "tie"
    assert mt.verdict(None) == "too_few_days"
