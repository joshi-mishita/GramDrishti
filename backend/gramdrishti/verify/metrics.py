"""Forecast verification scores. Undefined scores are returned as None, never NaN."""

from __future__ import annotations

import numpy as np


def _clean(pred: np.ndarray, obs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pred, obs = np.asarray(pred, dtype=float), np.asarray(obs, dtype=float)
    ok = ~(np.isnan(pred) | np.isnan(obs))
    return pred[ok], obs[ok]


def continuous_scores(pred: np.ndarray, obs: np.ndarray) -> dict[str, float | int | None]:
    """n, MAE, RMSE and bias (mean of prediction minus observation)."""
    p, o = _clean(pred, obs)
    if len(p) == 0:
        return {"n": 0, "mae": None, "rmse": None, "bias": None}
    err = p - o
    return {"n": int(len(p)), "mae": float(np.abs(err).mean()), "rmse": float(np.sqrt((err ** 2).mean())),
            "bias": float(err.mean())}


def event_scores(pred: np.ndarray, obs: np.ndarray, threshold: float) -> dict[str, float | int | None]:
    """Contingency counts and POD, FAR, CSI for the event value >= threshold."""
    p, o = _clean(pred, obs)
    fe, oe = p >= threshold, o >= threshold
    hits, misses, fa = int((fe & oe).sum()), int((~fe & oe).sum()), int((fe & ~oe).sum())

    def ratio(a: int, b: int) -> float | None:
        return a / b if b > 0 else None

    return {"n": int(len(p)), "hits": hits, "misses": misses, "false_alarms": fa,
            "pod": ratio(hits, hits + misses), "far": ratio(fa, hits + fa),
            "csi": ratio(hits, hits + misses + fa)}
