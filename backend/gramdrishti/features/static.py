"""Static local and position features, one row per Panchayat (Backend Guide section 4)."""

from __future__ import annotations

import pandas as pd

NUMERIC = ["elevation_m", "tpi_z", "slope_deg", "irrigated_frac", "canal_dist_km", "cropland_frac",
           "urban_frac", "water_frac", "tree_frac", "clay_pct", "sand_pct", "silt_pct", "whc_mm_per_m"]
CATEGORICAL = ["drainage_class", "soil_texture"]
# Panchayat minus block mean (equal weights). The model predicts departures from the block forecast,
# so contrasts with the rest of the block carry the signal directly.
RELATIVE = ["elevation_m", "tpi_z", "irrigated_frac", "urban_frac", "water_frac", "tree_frac", "sand_pct"]
POSITION = ["lat", "lon", "dlat_block", "dlon_block"]

Encodings = dict[str, dict[str, int]]


def fit_encodings(static: pd.DataFrame) -> Encodings:
    """Integer codes for categorical columns: sorted unique values -> 0..n-1. Saved with the model."""
    return {c: {v: i for i, v in enumerate(sorted(static[c].dropna().astype(str).unique()))}
            for c in CATEGORICAL}


def static_features(static: pd.DataFrame, blocks: pd.DataFrame, encodings: Encodings) -> pd.DataFrame:
    """panchayat_id, block_id and every static and position feature. Unknown categories become -1."""
    out = static[["panchayat_id", "block_id", "lat", "lon", *NUMERIC]].copy()
    for c in CATEGORICAL:
        out[f"{c}_code"] = static[c].astype(str).map(encodings[c]).fillna(-1).astype(int)
    for c in RELATIVE:
        out[f"{c}_rel"] = static[c] - static.groupby("block_id")[c].transform("mean")
    centre = blocks.set_index("block_id")
    out["dlat_block"] = out["lat"] - out["block_id"].map(centre["centre_lat"])
    out["dlon_block"] = out["lon"] - out["block_id"].map(centre["centre_lon"])
    return out


def static_feature_names() -> list[str]:
    """Feature columns produced by ``static_features`` (ids excluded)."""
    return [*POSITION, *NUMERIC, *[f"{c}_code" for c in CATEGORICAL], *[f"{c}_rel" for c in RELATIVE]]
