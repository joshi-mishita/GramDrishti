"""Conformalised quantile regression and output constraints (Backend Guide 7.1).

One additive offset per variable and lead-day group (days 1-2, days 3-5), fitted on CALIB rows
only: the final 80 % interval is [p10 - q, p90 + q]. A negative q narrows an interval that was too
wide. CALIB spans May to mid-July only, so season groups are not split (too little data, and
winter would be absent anyway).

After the offsets, ``enforce_constraints`` makes p10 <= p50 <= p90, rain and wind >= 0,
RH within 0..100, and Tmin < Tmax at every quantile level.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gramdrishti.data.config import INTERVAL_LEVEL, LEAD_GROUPS, VARS

Q = ["p10", "p50", "p90"]
BOUNDS = {"rain": (0.0, None), "wind": (0.0, None), "rh": (0.0, 100.0), "tmax": (None, None),
          "tmin": (None, None)}
TMIN_TMAX_GAP_C = 0.1


def cqr_offset(lo: np.ndarray, hi: np.ndarray, y: np.ndarray, level: float = INTERVAL_LEVEL) -> float:
    """Conformity-score quantile: how far to widen [lo, hi] so it holds ``level`` of ``y``."""
    score = np.maximum(np.asarray(lo) - y, np.asarray(y) - hi)
    n = len(score)
    k = min(1.0, np.ceil((n + 1) * level) / n)
    return float(np.quantile(score, k))


def lead_group(lead_day: pd.Series) -> pd.Series:
    """Map lead day to "d1_2" or "d3_5"."""
    return lead_day.map(LEAD_GROUPS)


def fit_offsets(pred: pd.DataFrame, obs: pd.DataFrame, level: float = INTERVAL_LEVEL) -> pd.DataFrame:
    """Offsets per (var, lead_group) from predictions and ``obs_<var>`` columns on the same index."""
    groups = lead_group(pred["lead_day"])
    rows = []
    for var in VARS:
        y = obs[f"obs_{var}"]
        for g in sorted(groups.unique()):
            m = (groups == g) & y.notna()
            q = cqr_offset(pred.loc[m, f"{var}_p10"].to_numpy(), pred.loc[m, f"{var}_p90"].to_numpy(),
                           y[m].to_numpy(), level)
            rows.append({"var": var, "lead_group": g, "q": q, "n": int(m.sum())})
    return pd.DataFrame(rows)


def apply_offsets(pred: pd.DataFrame, offsets: pd.DataFrame) -> pd.DataFrame:
    """Widen (or narrow) each interval by its (var, lead_group) offset. Returns a copy."""
    out = pred.copy()
    groups = lead_group(out["lead_day"]).to_numpy()
    for r in offsets.itertuples():
        m = groups == r.lead_group
        out.loc[m, f"{r.var}_p10"] = out.loc[m, f"{r.var}_p10"] - r.q
        out.loc[m, f"{r.var}_p90"] = out.loc[m, f"{r.var}_p90"] + r.q
    return out


def enforce_constraints(pred: pd.DataFrame) -> pd.DataFrame:
    """Sort quantiles, clip to physical ranges and keep Tmin below Tmax. Means are clipped only to ranges."""
    out = pred.copy()
    for var in VARS:
        cols = [f"{var}_{q}" for q in Q]
        out[cols] = np.sort(out[cols].to_numpy(dtype=float), axis=1)
        lo, hi = BOUNDS[var]
        for c in [*cols, f"{var}_mean"]:
            if lo is not None or hi is not None:
                out[c] = out[c].clip(lower=lo, upper=hi)
    # Lowering tmin_q by the same monotone rule at each level keeps tmin_p10 <= p50 <= p90.
    for q in Q:
        out[f"tmin_{q}"] = np.minimum(out[f"tmin_{q}"], out[f"tmax_{q}"] - TMIN_TMAX_GAP_C)
    return out


WET_MM = 1.0


def coverage_table(pred: pd.DataFrame, obs: pd.DataFrame) -> pd.DataFrame:
    """Empirical coverage of [p10, p90] and mean width per (var, lead_group).

    Adds ``rain_wet`` (observed rain >= 1 mm only): dry days dominate rain coverage and hide
    how the interval does when it rains.
    """
    groups = lead_group(pred["lead_day"])
    rows = []
    for var in [*VARS, "rain_wet"]:
        y = obs[f"obs_{var.removesuffix('_wet')}"]
        subset = y >= WET_MM if var == "rain_wet" else True
        col = var.removesuffix("_wet")
        for g in sorted(groups.unique()):
            m = (groups == g) & y.notna() & subset
            lo, hi = pred.loc[m, f"{col}_p10"], pred.loc[m, f"{col}_p90"]
            inside = (y[m] >= lo) & (y[m] <= hi)
            rows.append({"var": var, "lead_group": g, "n": int(m.sum()), "coverage": float(inside.mean()),
                         "width": float((hi - lo).mean())})
    return pd.DataFrame(rows)
