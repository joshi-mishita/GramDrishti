"""Reconcile Panchayat forecasts with the block forecast (Backend Guide 7.2).

After reconciliation the plain (equal-weight) mean of the Panchayat ``mean`` values in a block
equals the block target for every block, issue date and lead day. The correction is computed from
the mean-model output and applied to the mean and to every quantile.

- additive (tmax, tmin, dew point): shift = target - block mean;
- multiplicative (rain, wind): ratio = target / block mean. When the block mean is ~0 but the target
  is not, the ratio is undefined and the difference is added instead, so the identity still holds;
- bounded additive (RH): additive, but members pinned at 0 or 100 % stop moving and the rest take up
  the remainder.

Equal Panchayat weights for now. Production should weight by polygon area (future work).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gramdrishti.models.downscale import STATS

GROUP = ["issue_date", "lead_day", "block_id"]
EPS = 1e-6


def _block_mean(df: pd.DataFrame, col: str) -> pd.Series:
    return df.groupby(GROUP)[col].transform("mean")


def reconcile(df: pd.DataFrame, prefix: str, target_col: str, mode: str) -> pd.DataFrame:
    """Reconcile ``<prefix>_{mean,p10,p50,p90}`` in ``df`` to ``target_col``. Returns a copy."""
    out = df.copy()
    g = _block_mean(out, f"{prefix}_mean").to_numpy()
    target = out[target_col].to_numpy(dtype=float)
    cols = [f"{prefix}_{s}" for s in STATS]
    if mode == "add":
        shift = target - g
        for c in cols:
            out[c] = out[c].to_numpy() + shift
    elif mode == "mult":
        ok = g > EPS
        ratio = np.where(ok, target / np.where(ok, g, 1.0), 1.0)
        shift = np.where(ok, 0.0, target - g)
        for c in cols:
            out[c] = out[c].to_numpy() * ratio + shift
    else:
        raise ValueError(f"mode must be 'add' or 'mult', got {mode!r}")
    return out


def reconcile_bounded(df: pd.DataFrame, prefix: str, target_col: str, lo: float, hi: float,
                      max_iter: int = 100) -> pd.DataFrame:
    """Additive reconciliation that keeps the mean inside [lo, hi] (water-filling).

    Each Panchayat's quantiles get the same total shift as its mean. Needs lo <= target <= hi.
    """
    out = df.copy()
    mean_col = f"{prefix}_mean"
    start = out[mean_col].to_numpy(dtype=float).copy()
    x = np.clip(start, lo, hi)
    target = out[target_col].to_numpy(dtype=float)
    keys = out[GROUP]
    for _ in range(max_iter):
        s = pd.Series(x, index=out.index)
        resid = target - s.groupby([keys[k] for k in GROUP]).transform("mean").to_numpy()
        if np.abs(resid).max() < 1e-10:
            break
        free = np.where(resid > 0, x < hi - 1e-12, x > lo + 1e-12)
        n = s.groupby([keys[k] for k in GROUP]).transform("size").to_numpy()
        n_free = pd.Series(free.astype(float), index=out.index).groupby(
            [keys[k] for k in GROUP]).transform("sum").to_numpy()
        step = np.where(free & (n_free > 0), resid * n / np.maximum(n_free, 1.0), 0.0)
        x = np.clip(x + step, lo, hi)
    shift = x - start
    for s in STATS:
        out[f"{prefix}_{s}"] = out[f"{prefix}_{s}"].to_numpy() + shift
    out[mean_col] = x
    return out


def max_block_error(df: pd.DataFrame, prefix: str, target_col: str) -> float:
    """Largest |block mean of ``<prefix>_mean`` - block target| over all block-days (0 if empty)."""
    g = df.groupby(GROUP).agg(m=(f"{prefix}_mean", "mean"), t=(target_col, "first"))
    return float((g["m"] - g["t"]).abs().max()) if len(g) else 0.0
