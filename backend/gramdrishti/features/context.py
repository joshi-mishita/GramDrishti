"""Forecast-context features per block, issue date and lead day (Backend Guide section 4).

Only issued forecasts are used, never block truth: at inference time only the forecast exists.
- ``b1_<var>``: bias-corrected, inverse-MSE-weighted block forecast (baseline B1). Also the target the
  Panchayat values are reconciled to.
- ``spread_<var>``: spread between the bias-corrected NWP sources (a crude uncertainty).
- ``chg_<var>``: change from the previous lead day of the same issue (missing at lead 1).
- ``b1_td``: block dew point derived from B1 mean temperature and RH.
- B1 Tmin and Tmax are repaired to a diurnal range of at least ``DIURNAL_MIN_C`` around their midpoint:
  the issued sources sometimes forecast Tmin >= Tmax on rainy days, and a block target like that
  would force Panchayats to break Tmin < Tmax after reconciliation (DECISIONS D048).
- ``b0_<var>``: the plain block forecast (baseline B0). Kept for scoring, not a model feature.
"""

from __future__ import annotations

import pandas as pd

from gramdrishti.data.config import COLS, VARS
from gramdrishti.data.qc import DIURNAL_MIN_C
from gramdrishti.models.bias import KEYS, BiasModel, apply_bias, combine_sources
from gramdrishti.models.humidity import dewpoint_from_rh

NAMES = [*[f"b1_{v}" for v in VARS], "b1_td", *[f"spread_{v}" for v in VARS], *[f"chg_{v}" for v in VARS]]


def forecast_context(fc: pd.DataFrame, bias: BiasModel) -> pd.DataFrame:
    """One row per (block_id, issue_date, valid_date, lead_day) with B0, B1, spread and change columns."""
    b0 = combine_sources(fc)
    b1 = combine_sources(apply_bias(fc, bias), bias.weights)
    out = b1[KEYS].copy()
    for v in VARS:
        out[f"b1_{v}"] = b1[COLS[v]].to_numpy()
        out[f"spread_{v}"] = b1[f"{COLS[v]}_spread"].to_numpy()
    mid = (out["b1_tmax"] + out["b1_tmin"]) / 2
    narrow = (out["b1_tmax"] - out["b1_tmin"]) < DIURNAL_MIN_C
    out.loc[narrow, "b1_tmax"] = mid[narrow] + DIURNAL_MIN_C / 2
    out.loc[narrow, "b1_tmin"] = mid[narrow] - DIURNAL_MIN_C / 2
    out["b1_td"] = dewpoint_from_rh((out["b1_tmax"] + out["b1_tmin"]) / 2, out["b1_rh"])
    out = out.sort_values(["block_id", "issue_date", "lead_day"]).reset_index(drop=True)
    grp = out.groupby(["block_id", "issue_date"])
    for v in VARS:
        out[f"chg_{v}"] = out[f"b1_{v}"] - grp[f"b1_{v}"].shift(1)
    b0 = b0.rename(columns={COLS[v]: f"b0_{v}" for v in VARS})
    return out.merge(b0[[*KEYS, *[f"b0_{v}" for v in VARS]]], on=KEYS, how="left")
