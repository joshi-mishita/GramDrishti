"""Forecast verification scores (Backend Guide 11.2). Undefined scores are returned as None, never NaN.

Every function takes plain arrays so it can be checked on tiny hand-computed cases.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

BOOT_BLOCK_DAYS = 7
BOOT_N = 1000
RELIABILITY_BINS = 10


def _clean(pred: np.ndarray, obs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    pred, obs = np.asarray(pred, dtype=float), np.asarray(obs, dtype=float)
    ok = ~(np.isnan(pred) | np.isnan(obs))
    return pred[ok], obs[ok]


def _ratio(a: float, b: float) -> float | None:
    return float(a / b) if b > 0 else None


def continuous_scores(pred: np.ndarray, obs: np.ndarray) -> dict[str, float | int | None]:
    """n, MAE, RMSE and bias (mean of prediction minus observation)."""
    p, o = _clean(pred, obs)
    if len(p) == 0:
        return {"n": 0, "mae": None, "rmse": None, "bias": None}
    err = p - o
    return {"n": int(len(p)), "mae": float(np.abs(err).mean()), "rmse": float(np.sqrt((err ** 2).mean())),
            "bias": float(err.mean())}


def skill(score_model: float | None, score_base: float | None) -> float | None:
    """1 - score_model / score_base for a negatively oriented score (MAE, RMSE, Brier, quantile loss)."""
    if score_model is None or score_base is None or score_base <= 0:
        return None
    return float(1.0 - score_model / score_base)


def contingency(obs: np.ndarray, fc: np.ndarray) -> dict[str, float | int | None]:
    """Counts, POD, FAR, CSI and frequency bias from boolean arrays of observed and forecast events."""
    obs, fc = np.asarray(obs, dtype=bool), np.asarray(fc, dtype=bool)
    h, m, f = int((obs & fc).sum()), int((obs & ~fc).sum()), int((~obs & fc).sum())
    return {"n": int(len(obs)), "hits": h, "misses": m, "false_alarms": f,
            "pod": _ratio(h, h + m), "far": _ratio(f, h + f), "csi": _ratio(h, h + m + f),
            "frequency_bias": _ratio(h + f, h + m)}


def event_scores(pred: np.ndarray, obs: np.ndarray, threshold: float) -> dict[str, float | int | None]:
    """Contingency scores for the event value >= threshold, from amounts."""
    p, o = _clean(pred, obs)
    return contingency(o >= threshold, p >= threshold)


def brier(p: np.ndarray, o: np.ndarray) -> float | None:
    """Mean squared difference between probability and 0/1 outcome."""
    p, o = np.asarray(p, dtype=float), np.asarray(o, dtype=float)
    return float(np.mean((p - o) ** 2)) if len(p) else None


def brier_skill(p: np.ndarray, o: np.ndarray, p_ref: np.ndarray) -> float | None:
    """Brier skill score of ``p`` against a reference probability (for example climatology)."""
    return skill(brier(p, o), brier(p_ref, o))


def reliability(p: np.ndarray, o: np.ndarray, bins: int = RELIABILITY_BINS) -> list[dict]:
    """Reliability diagram points: equal-width probability bins, empty bins left out.

    ``forecast_prob`` is the bin centre (Guide 11.2); ``mean_forecast_prob`` is the mean forecast inside it.
    """
    p, o = np.asarray(p, dtype=float), np.asarray(o, dtype=float)
    b = np.clip((p * bins).astype(int), 0, bins - 1)
    pts = []
    for i in range(bins):
        m = b == i
        if m.any():
            pts.append({"forecast_prob": (i + 0.5) / bins, "mean_forecast_prob": float(p[m].mean()),
                        "observed_freq": float(o[m].mean()), "n": int(m.sum())})
    return pts


def interval_coverage(lo: np.ndarray, hi: np.ndarray, y: np.ndarray) -> dict[str, float | int | None]:
    """Share of observations inside [lo, hi] and the mean width. Rows with a missing value are dropped."""
    lo, hi, y = (np.asarray(a, dtype=float) for a in (lo, hi, y))
    ok = ~(np.isnan(lo) | np.isnan(hi) | np.isnan(y))
    lo, hi, y = lo[ok], hi[ok], y[ok]
    if not len(y):
        return {"n": 0, "coverage": None, "mean_width": None}
    return {"n": int(len(y)), "coverage": float(((y >= lo) & (y <= hi)).mean()),
            "mean_width": float((hi - lo).mean())}


def pinball(q_pred: np.ndarray, y: np.ndarray, q: float) -> np.ndarray:
    """Quantile (pinball) loss per row for quantile level ``q``."""
    d = np.asarray(y, dtype=float) - np.asarray(q_pred, dtype=float)
    return np.maximum(q * d, (q - 1) * d)


def quantile_loss_rows(preds: dict[float, np.ndarray], y: np.ndarray) -> np.ndarray:
    """Mean pinball loss over the given quantile levels, per row. A point forecast passes the same array
    for every level (a forecast with no spread)."""
    return np.mean([pinball(v, y, q) for q, v in preds.items()], axis=0)


def daily_sums(days: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sum of ``values`` per day, ordered by day. Returns (sorted unique days, sums)."""
    days = np.asarray(days)
    uniq, inv = np.unique(days, return_inverse=True)
    return uniq, np.bincount(inv, weights=np.asarray(values, dtype=float), minlength=len(uniq))


def block_bootstrap_ci(day_err_model: np.ndarray, day_err_base: np.ndarray, block: int = BOOT_BLOCK_DAYS,
                       n_boot: int = BOOT_N, seed: int = 0, squared: bool = False,
                       level: float = 0.95) -> list[float] | None:
    """Confidence interval of the skill 1 - err_model / err_base from a moving-block bootstrap (Guide 11.2).

    Inputs are one aggregate error per day, ordered by date, over the same rows for model and baseline:
    a mean over Panchayats (the guide) or a sum (equal to the mean when every day has the same rows, and
    consistent with the pooled score when days differ in size). Blocks of ``block`` consecutive days are
    resampled with replacement, which keeps the day-to-day correlation of weather errors.
    ``squared=True`` treats the inputs as squared errors and returns the interval of RMSE skill.
    Returns None when there are fewer than two blocks of days.
    """
    m, b = np.asarray(day_err_model, dtype=float), np.asarray(day_err_base, dtype=float)
    n = len(m)
    if n < 2 * block:
        return None
    rng = np.random.default_rng(seed)
    starts = rng.choice(np.arange(0, n - block + 1), size=(n_boot, n // block))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n_boot, -1)
    sm, sb = m[idx].sum(axis=1), b[idx].sum(axis=1)
    if squared:
        sm, sb = np.sqrt(sm), np.sqrt(sb)
    ok = sb > 0
    if not ok.any():
        return None
    out = 1.0 - sm[ok] / sb[ok]
    tail = (1 - level) / 2 * 100
    lo, hi = np.percentile(out, [tail, 100 - tail])
    return [float(lo), float(hi)]


def verdict(ci: Sequence[float] | None) -> str:
    """"win" when the whole skill interval is above 0, "loss" when below 0, "tie" when it contains 0
    (cannot tell apart), "too_few_days" without an interval."""
    if ci is None:
        return "too_few_days"
    if ci[0] > 0:
        return "win"
    if ci[1] < 0:
        return "loss"
    return "tie"
