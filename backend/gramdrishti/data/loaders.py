"""One loader per data file. Mock and real data come back with the same column names.

The rest of the backend only sees these DataFrames and never needs to know the data mode,
except for ``load_truth`` and ``load_block_truth``, which exist in mock mode only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from gramdrishti.data.config import FILES, data_dir, data_mode


class RealModeError(RuntimeError):
    """Raised when mock-only data (the synthetic oracle) is requested in real mode."""


class DataFileError(FileNotFoundError):
    """Raised when a data file is missing or lacks required columns."""


REQUIRED: dict[str, list[str]] = {
    "static": ["panchayat_id", "panchayat_name", "block_id", "lat", "lon", "elevation_m", "tpi_z",
               "slope_deg", "irrigated_frac", "canal_dist_km", "cropland_frac", "urban_frac", "water_frac",
               "tree_frac", "clay_pct", "sand_pct", "silt_pct", "soil_texture", "whc_mm_per_m",
               "drainage_class"],
    "blocks": ["block_id", "block_name", "n_panchayats", "centre_lat", "centre_lon"],
    "stations": ["station_id", "station_type", "panchayat_id", "block_id", "lat", "lon", "elevation_m"],
    "obs": ["date", "station_id", "rain_mm", "tmax_c", "tmin_c", "rh_mean_pct", "wind_kmh"],
    "fc": ["source", "block_id", "valid_date", "issue_date", "lead_day", "rain_mm", "tmax_c", "tmin_c",
           "rh_mean_pct", "wind_kmh"],
    "sat": ["week_start", "panchayat_id", "ndvi", "lst_day_c"],
    "crops": ["panchayat_id", "season", "crop", "sowing_date", "expected_harvest_date", "crop_area_fraction"],
    "calendar": ["crop", "stage", "das_start", "das_end", "tmax_alert_c", "tmin_alert_c",
                 "drought_sensitivity", "waterlog_sensitivity", "key_operations", "status"],
    "feedback": ["date", "panchayat_id", "reported_rain", "reported_intensity", "channel"],
    "truth": ["date", "panchayat_id", "block_id", "rain_mm", "tmax_c", "tmin_c", "rh_mean_pct",
              "dewpoint_c", "wind_kmh", "et0_mm", "soil_moisture_frac", "waterlog_flag"],
    "block_truth": ["date", "block_id", "rain_mm", "tmax_c", "tmin_c", "rh_mean_pct", "wind_kmh"],
}
ID_COLS = {"panchayat_id": str, "block_id": str, "station_id": str, "source": str}


def _path(key: str) -> Path:
    mode = data_mode()
    if key not in FILES[mode]:
        raise RealModeError(f"'{key}' does not exist in {mode} mode.")
    return data_dir() / FILES[mode][key]


def _csv(key: str, dates: tuple[str, ...] = ()) -> pd.DataFrame:
    path = _path(key)
    if not path.exists():
        hint = ""
        if data_mode() == "mock":
            hint = " Regenerate mock data with `python data/generate_mock_data.py`."
        raise DataFileError(f"Missing data file: {path}.{hint}")
    df = pd.read_csv(path, dtype={c: t for c, t in ID_COLS.items()})
    missing = [c for c in REQUIRED[key] if c not in df.columns]
    if missing:
        raise DataFileError(f"{path.name} is missing required columns: {missing}")
    for col in dates:
        df[col] = pd.to_datetime(df[col], format="%Y-%m-%d")
    return df


def _mock_only(what: str) -> None:
    if data_mode() != "mock":
        raise RealModeError(
            f"{what} is the synthetic answer key and exists only in DATA_MODE=mock. "
            "Panchayat truth does not exist for real data: use station observations "
            "(leave-one-station-out) for training targets and verification."
        )


def load_static() -> pd.DataFrame:
    """Static Panchayat attributes (one row per Panchayat)."""
    return _csv("static")


def load_blocks() -> pd.DataFrame:
    """Block table with centre coordinates."""
    return _csv("blocks")


def load_stations() -> pd.DataFrame:
    """Station metadata (AWS: all variables, ARG: rain only)."""
    return _csv("stations")


def load_obs() -> pd.DataFrame:
    """Daily station observations; missing values are NaN."""
    return _csv("obs", dates=("date",))


def load_fc() -> pd.DataFrame:
    """Block forecasts from all NWP sources, lead days 1 to 5."""
    return _csv("fc", dates=("valid_date", "issue_date"))


def load_sat() -> pd.DataFrame:
    """Weekly NDVI and daytime LST per Panchayat, with cloud gaps."""
    return _csv("sat", dates=("week_start",))


def load_crops() -> pd.DataFrame:
    """Crop and sowing date per Panchayat and season."""
    return _csv("crops", dates=("sowing_date", "expected_harvest_date"))


def load_calendar() -> pd.DataFrame:
    """Crop stage calendar. Thresholds are placeholders until expert review."""
    return _csv("calendar")


def load_feedback() -> pd.DataFrame:
    """Farmer "did it rain?" reports."""
    return _csv("feedback", dates=("date",))


def load_panchayat_geojson() -> dict[str, Any]:
    """Panchayat polygons as a GeoJSON FeatureCollection ([lon, lat] coordinates)."""
    return json.loads(_path("panchayat_geojson").read_text())


def load_block_geojson() -> dict[str, Any]:
    """Block polygons as a GeoJSON FeatureCollection ([lon, lat] coordinates)."""
    return json.loads(_path("block_geojson").read_text())


def load_truth() -> pd.DataFrame:
    """MOCK ONLY. Synthetic Panchayat daily truth: proxy target and evaluation, never a feature."""
    _mock_only("load_truth()")
    return _csv("truth", dates=("date",))


def load_block_truth() -> pd.DataFrame:
    """MOCK ONLY. Synthetic block daily truth: proxy target and evaluation, never a feature."""
    _mock_only("load_block_truth()")
    return _csv("block_truth", dates=("date",))
