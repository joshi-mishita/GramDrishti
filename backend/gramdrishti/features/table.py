"""``make_table(kind)``: one row per (issue_date, lead_day, panchayat_id) with features and, for
training, targets. The same feature code runs for ``train`` and ``infer`` (Backend Guide section 4).

Leakage rules enforced here:
- features for issue date D use forecasts issued on D, satellite weeks that ended by D and station
  observations dated before D; never the synthetic oracle;
- ``train`` tables cover one named window (TRAIN or CALIB). An issue date is kept only when all five
  lead days fall inside the window (the purge in Guide 6.2). TEST raises: only verification opens it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from gramdrishti.data import loaders
from gramdrishti.data.config import (
    COLS,
    LEADS,
    RAIN_EVENTS_MM,
    WIND_FLOOR_KMH,
    data_mode,
    select_window,
    window_bounds,
)
from gramdrishti.data.qc import clean_values, run_qc
from gramdrishti.features import calendar, context, dynamic
from gramdrishti.features.static import Encodings, static_feature_names, static_features
from gramdrishti.models.bias import BiasModel

ID_COLS = ["issue_date", "valid_date", "lead_day", "panchayat_id", "block_id"]
TARGETS = ["tmax", "tmin", "td", "wind", "rain"]   # what the regressors learn (Guide 6.1)
OBS = ["tmax", "tmin", "rh", "td", "wind", "rain"]


def feature_names() -> list[str]:
    """Model feature columns in a fixed order. Saved with every model."""
    return [*static_feature_names(), *calendar.NAMES, *context.NAMES, *dynamic.SAT_NAMES, *dynamic.RAIN_NAMES]


def event_name(thr: float) -> str:
    """Column name of a rain event, e.g. ``ev_rain_ge_2_5``."""
    return "ev_rain_ge_" + f"{thr:g}".replace(".", "_")


@dataclass
class Inputs:
    """Everything the features read. The synthetic oracle is deliberately not part of it."""

    fc: pd.DataFrame
    static: pd.DataFrame
    blocks: pd.DataFrame
    sat: pd.DataFrame
    obs_clean: pd.DataFrame
    stations: pd.DataFrame


def load_inputs() -> Inputs:
    """Load all feature inputs for the active data mode."""
    return Inputs(fc=loaders.load_fc(), static=loaders.load_static(), blocks=loaders.load_blocks(),
                  sat=loaders.load_sat(), obs_clean=clean_values(run_qc(loaders.load_obs())),
                  stations=loaders.load_stations())


def window_issue_dates(fc: pd.DataFrame, window: str) -> pd.DatetimeIndex:
    """Issue dates whose five lead days all fall inside ``window``. TEST raises (D009)."""
    start, end = window_bounds(window)
    in_window = select_window(fc, window, "valid_date")          # raises for TEST
    issues = pd.DatetimeIndex(sorted(in_window["issue_date"].unique()))
    return issues[(issues >= start) & (issues + pd.Timedelta(days=max(LEADS)) <= end)]


def make_table(kind: str, inputs: Inputs, bias: BiasModel, encodings: Encodings, *,
               window: str | None = None, issue_dates: list | pd.DatetimeIndex | None = None) -> pd.DataFrame:
    """Build the model table.

    ``kind="train"`` needs ``window`` and adds targets; ``kind="infer"`` needs ``issue_dates`` and
    never touches truth. Audit columns ``*_source_date`` record the latest input date each dynamic
    feature used.
    """
    if kind == "train":
        if window is None:
            raise ValueError("make_table('train') needs a window")
        issues = window_issue_dates(inputs.fc, window)
    elif kind == "infer":
        if issue_dates is None:
            raise ValueError("make_table('infer') needs issue_dates")
        issues = pd.DatetimeIndex(pd.to_datetime(list(issue_dates)))
    else:
        raise ValueError(f"kind must be 'train' or 'infer', got {kind!r}")

    fc = inputs.fc[inputs.fc["issue_date"].isin(issues)]
    ctx = context.forecast_context(fc, bias)
    st = static_features(inputs.static, inputs.blocks, encodings)
    t = st.merge(ctx, on="block_id", how="inner")
    cal = calendar.calendar_features(t["valid_date"], t["lead_day"]).drop(columns="lead_day")
    t = pd.concat([t, cal], axis=1)
    sat = dynamic.satellite_features(inputs.sat, t[["panchayat_id", "block_id", "issue_date"]])
    t = t.merge(sat, on=["panchayat_id", "issue_date"], how="left")
    rain = dynamic.recent_rain_features(inputs.obs_clean, inputs.stations, t["issue_date"])
    t = t.merge(rain, on=["issue_date", "block_id"], how="left")
    t = t.sort_values(["issue_date", "lead_day", "panchayat_id"]).reset_index(drop=True)
    feats = [f for f in feature_names() if f not in ID_COLS]      # lead_day is both an id and a feature
    t = t[[*ID_COLS, *feats, *[c for c in t.columns if c.startswith("b0_")], *dynamic.AUDIT]]
    if kind == "train":
        t = add_targets(t, window)
    return t


def add_targets(t: pd.DataFrame, window: str) -> pd.DataFrame:
    """Attach observed values (``obs_*``), regression targets (``y_*``) and rain events (``ev_*``)."""
    if data_mode() != "mock":
        raise NotImplementedError(
            "Real-mode targets come only from Panchayats with a station (Backend Guide 14.4); "
            "not built yet. Panchayat truth does not exist for real data."
        )
    # MOCK ONLY: synthetic Panchayat truth as the proxy training target. Never a feature.
    truth = select_window(loaders.load_truth(), window, "date")
    truth = truth.rename(columns={"date": "valid_date", "dewpoint_c": "obs_td",
                                  **{COLS[v]: f"obs_{v}" for v in COLS}})
    t = t.merge(truth[["valid_date", "panchayat_id", *[f"obs_{v}" for v in OBS]]],
                on=["valid_date", "panchayat_id"], how="inner")
    t["y_tmax"] = t["obs_tmax"] - t["b1_tmax"]
    t["y_tmin"] = t["obs_tmin"] - t["b1_tmin"]
    t["y_td"] = t["obs_td"] - t["b1_td"]
    t["y_wind"] = np.log(np.maximum(t["obs_wind"], WIND_FLOOR_KMH) / np.maximum(t["b1_wind"], WIND_FLOOR_KMH))
    t["y_rain"] = t["obs_rain"]
    for thr in RAIN_EVENTS_MM:
        t[event_name(thr)] = (t["obs_rain"] >= thr).astype(int)
    return t
