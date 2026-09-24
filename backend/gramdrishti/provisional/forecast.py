"""PROVISIONAL forecast source for the API until the Panchayat models exist (S5/S6).

What the API serves today, per block, issue date, lead day and variable:
- ``block``: the issued block forecast, the plain mean of the NWP sources (baseline B0). This is the
  "plain block forecast" the product is compared against.
- ``p50``: the corrected block forecast B1 (bias-corrected sources, inverse-MSE weights, fitted on TRAIN).
- ``p10`` / ``p90``: p50 minus / plus a half-width taken from the spread of the two bias-corrected sources,
  with a floor per variable. This is a crude, uncalibrated band, not a conformal interval.
- Event probabilities: read off a piecewise-linear CDF through (p10, 0.1), (p50, 0.5), (p90, 0.9).

B1 is a block-level value, so every Panchayat in a block gets the same p10/p50/p90 today. Block
consistency (block mean of Panchayat p50 equals the block target) therefore holds exactly.
Replace this module with snapshots from ``pipeline/run_daily.py`` in S6. See DECISIONS D013-D015.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gramdrishti.data import loaders
from gramdrishti.data.config import COLS, VARS
from gramdrishti.data.qc import clean_values, run_qc
from gramdrishti.models.baselines import Baselines, fit_baselines
from gramdrishti.models.bias import KEYS, apply_bias, block_reference, combine_sources

# Half-width of the provisional band: max(source spread, floor + rel * |p50|). Rain is right-skewed.
MIN_HALF = {"rain": 0.5, "tmax": 1.0, "tmin": 1.0, "rh": 5.0, "wind": 1.5}
REL_HALF = {"rain": 0.6, "tmax": 0.0, "tmin": 0.0, "rh": 0.0, "wind": 0.2}
RAIN_UPPER_STRETCH = 1.5
BOUNDS = {"rain": (0.0, None), "tmax": (None, None), "tmin": (None, None), "rh": (0.0, 100.0),
          "wind": (0.0, None)}
EVENTS = {"rain_ge_1mm": 1.0, "rain_ge_2_5mm": 2.5, "rain_ge_10mm": 10.0, "rain_ge_35mm": 35.0}


def fit_provisional() -> Baselines:
    """Fit B0-B2 parameters on TRAIN (bias correction target per D005)."""
    fc, static, stations = loaders.load_fc(), loaders.load_static(), loaders.load_stations()
    obs_clean = clean_values(run_qc(loaders.load_obs()))
    ref = block_reference(obs_clean, stations)
    return fit_baselines(fc, ref, obs_clean, stations, static, "TRAIN")


def block_quantiles(fc_issue: pd.DataFrame, baselines: Baselines) -> pd.DataFrame:
    """Long table: block_id, issue_date, valid_date, lead_day, var, p10, p50, p90, block.

    ``fc_issue`` holds the per-source forecasts of one or more issue dates.
    """
    b0 = combine_sources(fc_issue)
    b1 = combine_sources(apply_bias(fc_issue, baselines.bias), baselines.bias.weights)
    rows = []
    for var in VARS:
        col = COLS[var]
        m = b1[[*KEYS, col, f"{col}_spread"]].merge(b0[[*KEYS, col]].rename(columns={col: "block"}), on=KEYS)
        p50 = m[col].to_numpy(dtype=float)
        floor = MIN_HALF[var] + REL_HALF[var] * np.abs(p50)
        half = np.maximum(m[f"{col}_spread"].to_numpy(dtype=float), floor)
        upper = half * (RAIN_UPPER_STRETCH if var == "rain" else 1.0)
        lo, hi = BOUNDS[var]
        clip = (lambda x, lo=lo, hi=hi: np.clip(x, lo, hi))   # noqa: E731
        rows.append(pd.DataFrame({
            **{k: m[k].to_numpy() for k in KEYS}, "var": var,
            "p10": clip(p50 - half), "p50": clip(p50), "p90": clip(p50 + upper),
            "block": m["block"].to_numpy(),
        }))
    return pd.concat(rows, ignore_index=True)


def prob_exceed(threshold: float, p10: float, p50: float, p90: float) -> float | None:
    """P(X >= threshold) from a piecewise-linear CDF through the three quantiles, clipped to [0, 1].

    Outside [p10, p90] the CDF continues with the slope of the nearest segment. PROVISIONAL.
    """
    if any(v is None or not np.isfinite(v) for v in (p10, p50, p90)):
        return None
    xs, ps = [p10, p50, p90], [0.1, 0.5, 0.9]
    if p90 - p10 < 1e-9:
        return 1.0 if threshold <= p50 else 0.0
    if threshold <= p10:
        slope_x = max(p50 - p10, 1e-9)
        cdf = 0.1 - 0.4 * (p10 - threshold) / slope_x
    elif threshold >= p90:
        slope_x = max(p90 - p50, 1e-9)
        cdf = 0.9 + 0.4 * (threshold - p90) / slope_x
    else:
        cdf = float(np.interp(threshold, xs, ps))
    return float(np.clip(1.0 - cdf, 0.0, 1.0))


def event_probs(p10: float, p50: float, p90: float) -> dict[str, float | None]:
    """Probabilities of the four rain events."""
    return {name: prob_exceed(thr, p10, p50, p90) for name, thr in EVENTS.items()}
