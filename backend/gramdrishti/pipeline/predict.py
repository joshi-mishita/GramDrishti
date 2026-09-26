"""Model table -> Panchayat forecasts with calibrated intervals that reconcile to the block forecast.

Steps: raw model output -> physical values -> reconcile (tmax, tmin, dew point additive; rain, wind
multiplicative) -> RH from mean temperature and dew point, then bounded-additive reconciliation of
RH -> conformal offsets (if given) -> constraints -> event probabilities.
"""

from __future__ import annotations

import pandas as pd

from gramdrishti.data.config import VARS
from gramdrishti.features.table import ID_COLS
from gramdrishti.models.conformal import apply_offsets, enforce_constraints
from gramdrishti.models.downscale import STATS, DownscaleModels, to_values
from gramdrishti.models.humidity import rh_from_dewpoint
from gramdrishti.models.reconcile import reconcile, reconcile_bounded

MODES = {"tmax": "add", "tmin": "add", "td": "add", "rain": "mult", "wind": "mult"}


def predict_table(models: DownscaleModels, table: pd.DataFrame, offsets: pd.DataFrame | None = None,
                  events: bool = True, constrain: bool = True) -> pd.DataFrame:
    """Wide frame: ids, ``b0_*``/``b1_*`` block values, ``<var>_{mean,p10,p50,p90}`` for rain, tmax,
    tmin, rh, wind and td, and ``prob_rain_ge_*`` when ``events``. ``constrain=False`` (with no offsets)
    gives the reconciled output that conformal offsets are fitted on."""
    vals = to_values(table, models.predict_raw(table))
    base = [*ID_COLS, *[f"b1_{v}" for v in VARS], "b1_td", *[f"b0_{v}" for v in VARS]]
    df = pd.concat([table[base], vals], axis=1)
    for prefix, mode in MODES.items():
        if f"{prefix}_mean" in df:
            df = reconcile(df, prefix, f"b1_{prefix}", mode)
    tmean = (df["tmax_mean"] + df["tmin_mean"]) / 2
    for s in STATS:
        df[f"rh_{s}"] = rh_from_dewpoint(tmean, df[f"td_{s}"])
    df = reconcile_bounded(df, "rh", "b1_rh", 0.0, 100.0)
    if offsets is not None:
        df = apply_offsets(df, offsets)
    if constrain:
        df = enforce_constraints(df)
    if events and models.events:
        df = pd.concat([df, models.event_proba(table)], axis=1)
    return df
