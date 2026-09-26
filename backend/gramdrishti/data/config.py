"""Single source of truth for data mode, paths, variables, leads and time windows.

Nothing here touches the disk at import time. ``data_mode()`` and ``data_dir()`` read the
environment on every call so tests can switch modes with ``monkeypatch.setenv``.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA = ROOT / "data"
ART = ROOT / "backend" / "artifacts"

MODES = ("mock", "real")
LEADS = [1, 2, 3, 4, 5]
VARS = ["rain", "tmax", "tmin", "rh", "wind"]
COLS = {"rain": "rain_mm", "tmax": "tmax_c", "tmin": "tmin_c", "rh": "rh_mean_pct", "wind": "wind_kmh"}
SOURCES = ["mock_nwp_a", "mock_nwp_b"]

# Time windows (inclusive). Split by time, never randomly. TEST opens only in the verification session.
TRAIN = ("2023-01-01", "2024-04-30")
CALIB = ("2024-05-01", "2024-07-15")
TEST = ("2024-07-16", "2024-12-31")
WINDOWS = {"TRAIN": TRAIN, "CALIB": CALIB, "TEST": TEST}

# Seasons. Additive bias uses four groups; rain quantile mapping uses monsoon versus the rest.
SEASON_GROUPS = {
    12: "winter", 1: "winter", 2: "winter",
    3: "pre_monsoon", 4: "pre_monsoon", 5: "pre_monsoon",
    6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "monsoon",
    10: "post_monsoon", 11: "post_monsoon",
}
MONSOON_MONTHS = (6, 7, 8, 9)

RAIN_WET_MM = 1.0        # wet day for quantile mapping and wet-day frequency
RAIN_EVENT_MM = 2.5      # event threshold for POD/FAR/CSI in baseline_report
LAPSE_C_PER_M = -0.0065  # -6.5 C per km
IDW_POWER = 2.0
IDW_MIN_KM = 1.0         # distance floor so a very close station does not get infinite weight

# File names per mode. Real files keep the same column names and live in data/real/ (git-ignored).
FILES = {
    "mock": {
        "static": "panchayats_static.csv",
        "blocks": "blocks.csv",
        "stations": "stations.csv",
        "obs": "station_observations_mock.csv",
        "fc": "block_forecast_mock_nwp.csv",
        "sat": "satellite_weekly_mock.csv",
        "crops": "panchayat_crops_mock.csv",
        "calendar": "crop_calendar_PLACEHOLDER.csv",
        "feedback": "farmer_feedback_mock.csv",
        "panchayat_geojson": "panchayats_SYNTHETIC.geojson",
        "block_geojson": "blocks_SYNTHETIC.geojson",
        "truth": "synthetic_oracle/panchayat_daily_SYNTHETIC_TRUTH.csv",
        "block_truth": "synthetic_oracle/block_daily_SYNTHETIC_TRUTH.csv",
    },
    "real": {
        "static": "real/panchayats_static.csv",
        "blocks": "real/blocks.csv",
        "stations": "real/stations.csv",
        "obs": "real/station_observations.csv",
        "fc": "real/block_forecast.csv",
        "sat": "real/satellite_weekly.csv",
        "crops": "real/panchayat_crops.csv",
        "calendar": "real/crop_calendar.csv",
        "feedback": "real/farmer_feedback.csv",
        "panchayat_geojson": "real/panchayats.geojson",
        "block_geojson": "real/blocks.geojson",
    },
}


def data_mode() -> str:
    """Return the active data mode from ``DATA_MODE`` ("mock" by default)."""
    mode = os.getenv("DATA_MODE", "mock").strip().lower()
    if mode not in MODES:
        raise ValueError(f"DATA_MODE must be one of {MODES}, got {mode!r}")
    return mode


def data_dir() -> Path:
    """Return the data folder; ``GRAMDRISHTI_DATA_DIR`` overrides the repo's ``data/``."""
    override = os.getenv("GRAMDRISHTI_DATA_DIR")
    return Path(override) if override else DEFAULT_DATA


def window_bounds(name: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return inclusive (start, end) timestamps of a named window."""
    start, end = WINDOWS[name]
    return pd.Timestamp(start), pd.Timestamp(end)


def select_window(df: pd.DataFrame, name: str, date_col: str, *, allow_test: bool = False) -> pd.DataFrame:
    """Rows of ``df`` whose ``date_col`` falls inside window ``name``.

    Selecting TEST raises unless ``allow_test=True``; only the verification session may pass it.
    """
    if name == "TEST" and not allow_test:
        raise PermissionError("The TEST window is closed. Only the verification session may open it.")
    start, end = window_bounds(name)
    dates = pd.to_datetime(df[date_col])
    return df.loc[(dates >= start) & (dates <= end)].copy()


def season_group(dates: pd.Series) -> pd.Series:
    """Map dates to winter / pre_monsoon / monsoon / post_monsoon."""
    return pd.to_datetime(dates).dt.month.map(SEASON_GROUPS)


def rain_season(dates: pd.Series) -> pd.Series:
    """Map dates to "monsoon" (Jun-Sep) or "non_monsoon"."""
    months = pd.to_datetime(dates).dt.month
    return pd.Series(np.where(months.isin(MONSOON_MONTHS), "monsoon", "non_monsoon"), index=months.index)


# ---------------------------------------------------------------- downscaling model (S5)
SEED = 42
# Backend Guide 6.3 defaults. Tune only num_leaves, min_child_samples, n_estimators, and only on CALIB.
LGBM_BASE = {"n_estimators": 400, "learning_rate": 0.05, "num_leaves": 31, "min_child_samples": 50,
             "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "n_jobs": -1, "verbose": -1}
# Same inputs, same parameters and the same machine give the same model.
LGBM_DETERMINISM = {"random_state": SEED, "deterministic": True, "force_row_wise": True}
QUANTILES = (0.1, 0.5, 0.9)
RAIN_EVENTS_MM = (1.0, 2.5, 10.0, 35.0)
INTERVAL_LEVEL = 0.8                    # p10..p90
LEAD_GROUPS = {1: "d1_2", 2: "d1_2", 3: "d3_5", 4: "d3_5", 5: "d3_5"}
WIND_FLOOR_KMH = 0.1                    # floor inside log(Panchayat / block) for the wind target
RECONCILE_TOL = 1e-6                    # block mean of Panchayat means must equal the block forecast
MODEL_VERSION_PREFIX = "s5-lgbm"
