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
