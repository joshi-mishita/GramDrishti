"""Baselines the downscaling model must beat (Backend Guide section 5).

- B0 raw block: plain mean of the NWP sources at the block, copied to every Panchayat.
- B1 corrected block: B0 after bias correction and inverse-MSE source weights, copied to every Panchayat.
- B2 simple physical: B1 plus a lapse-rate term (-6.5 C/km, tmax and tmin) and inverse-distance
  weighted station offsets. The target Panchayat's own station is excluded.

Station offsets are static local anomalies fitted on TRAIN (station minus block reference, per season
group), not same-day observations: on the valid date the observation does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from gramdrishti.data.config import (
    COLS,
    IDW_MIN_KM,
    IDW_POWER,
    LAPSE_C_PER_M,
    rain_season,
    season_group,
    select_window,
    window_bounds,
)
from gramdrishti.models.bias import KEYS, VALUE_COLS, BiasModel, apply_bias, combine_sources, fit_bias

ADDITIVE_OFFSET = [COLS["tmax"], COLS["tmin"], COLS["rh"]]
RATIO_OFFSET = [COLS["rain"], COLS["wind"]]
LAPSE_COLS = [COLS["tmax"], COLS["tmin"]]
MIN_OFFSET_DAYS = 10
RAIN_MIN_REF_MM = 5.0          # need at least this much reference rain to estimate a rain ratio
RATIO_CLIP = (0.5, 2.0)


def _season_for(col: str, dates: pd.Series) -> np.ndarray:
    return (rain_season(dates) if col == COLS["rain"] else season_group(dates)).to_numpy()


def block_elevation(static: pd.DataFrame) -> pd.Series:
    """Mean Panchayat elevation per block (equal weights, as in reconciliation)."""
    return static.groupby("block_id")["elevation_m"].mean()


def to_panchayats(block_fc: pd.DataFrame, static: pd.DataFrame) -> pd.DataFrame:
    """Copy each block forecast to every Panchayat in the block."""
    return static[["panchayat_id", "block_id"]].merge(block_fc, on="block_id", how="inner")


# ---------------------------------------------------------------- station offsets (B2)
@dataclass
class StationOffsets:
    """Per-station local offsets fitted on one window.

    ``table`` columns: station_id, col, season, value. Additive columns hold (obs - ref - lapse);
    rain and wind hold log(obs / ref).
    """

    window: str
    fit_end: pd.Timestamp
    data_max_date: pd.Timestamp
    table: pd.DataFrame


def fit_station_offsets(obs_clean: pd.DataFrame, stations: pd.DataFrame, static: pd.DataFrame,
                        ref: pd.DataFrame, window: str = "TRAIN") -> StationOffsets:
    """Fit station offsets relative to the block reference, using only dates inside ``window``."""
    _, end = window_bounds(window)
    obs_w = select_window(obs_clean, window, "date")
    ref_w = select_window(ref, window, "date")
    st = stations[["station_id", "block_id", "elevation_m"]]
    r = ref_w[["date", "block_id", *VALUE_COLS]].rename(columns={c: f"ref_{c}" for c in VALUE_COLS})
    m = obs_w.merge(st, on="station_id").merge(r, on=["date", "block_id"], how="inner")
    data_max = m["date"].max()
    assert data_max <= end, "station offsets read data after their window"
    dz = m["elevation_m"] - m["block_id"].map(block_elevation(static))

    rows = []
    for col in VALUE_COLS:
        d = pd.DataFrame({"station_id": m["station_id"], "season": _season_for(col, m["date"]),
                          "obs": m[col], "ref": m[f"ref_{col}"]})
        if col in LAPSE_COLS:
            d["obs"] = d["obs"] - LAPSE_C_PER_M * dz
        d = d.dropna(subset=["obs", "ref"])
        g = d.groupby(["station_id", "season"]).agg(n=("obs", "size"), obs=("obs", "sum"), ref=("ref", "sum"))
        g = g[g["n"] >= MIN_OFFSET_DAYS]
        if col in ADDITIVE_OFFSET:
            value = (g["obs"] - g["ref"]) / g["n"]
        else:
            floor = RAIN_MIN_REF_MM if col == COLS["rain"] else 1e-6
            g = g[(g["ref"] >= floor) & (g["obs"] > 0)]
            value = np.log((g["obs"] / g["ref"]).clip(*RATIO_CLIP))
        rows.append(value.rename("value").reset_index().assign(col=col))
    table = pd.concat(rows, ignore_index=True)[["station_id", "col", "season", "value"]]
    return StationOffsets(window, end, data_max, table)


def _distance_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Equirectangular distance matrix in km (fine at district scale)."""
    cosl = np.cos(np.radians((lat1.mean() + lat2.mean()) / 2))
    dy = (lat1[:, None] - lat2[None, :]) * 111.0
    dx = (lon1[:, None] - lon2[None, :]) * 111.0 * cosl
    return np.hypot(dx, dy)


def idw_offsets(offsets: StationOffsets, stations: pd.DataFrame, static: pd.DataFrame) -> pd.DataFrame:
    """IDW-interpolate station offsets to every Panchayat, excluding stations inside that Panchayat.

    Returns panchayat_id, col, season, value.
    """
    st = stations.set_index("station_id")
    pid = static["panchayat_id"].to_numpy()
    out = []
    for (col, season), g in offsets.table.groupby(["col", "season"]):
        s = st.loc[g["station_id"]]
        dist = _distance_km(static["lat"].to_numpy(), static["lon"].to_numpy(),
                            s["lat"].to_numpy(), s["lon"].to_numpy())
        w = 1.0 / np.maximum(dist, IDW_MIN_KM) ** IDW_POWER
        w[pid[:, None] == s["panchayat_id"].to_numpy()[None, :]] = 0.0   # leave the own station out
        wsum = w.sum(axis=1)
        val = np.where(wsum > 0, (w @ g["value"].to_numpy()) / np.where(wsum > 0, wsum, 1.0), 0.0)
        out.append(pd.DataFrame({"panchayat_id": pid, "col": col, "season": season, "value": val}))
    return pd.concat(out, ignore_index=True)


def apply_b2(b1_panchayat: pd.DataFrame, idw: pd.DataFrame, static: pd.DataFrame) -> pd.DataFrame:
    """B2 = B1 + lapse-rate term + IDW station offsets (additive or multiplicative per variable)."""
    out = b1_panchayat.copy()
    elev = out["panchayat_id"].map(static.set_index("panchayat_id")["elevation_m"])
    dz = elev - out["block_id"].map(block_elevation(static))
    for col in VALUE_COLS:
        keys = pd.DataFrame({"panchayat_id": out["panchayat_id"].to_numpy(), "col": col,
                             "season": _season_for(col, out["valid_date"])})
        v = keys.merge(idw, on=["panchayat_id", "col", "season"], how="left")["value"].fillna(0.0).to_numpy()
        if col in LAPSE_COLS:
            out[col] = out[col].to_numpy() + LAPSE_C_PER_M * dz.to_numpy() + v
        elif col in ADDITIVE_OFFSET:
            out[col] = np.clip(out[col].to_numpy() + v, 0, 100)
        else:
            out[col] = out[col].to_numpy() * np.exp(v)
    return out


# ---------------------------------------------------------------- all baselines
@dataclass
class Baselines:
    """Fitted B1 and B2 parameters. ``predict`` returns Panchayat-level forecasts for all three."""

    bias: BiasModel
    offsets: StationOffsets
    idw: pd.DataFrame
    static: pd.DataFrame

    def predict(self, fc: pd.DataFrame) -> dict[str, pd.DataFrame]:
        """Panchayat forecasts from B0, B1 and B2 for every forecast row in ``fc``."""
        b0 = to_panchayats(combine_sources(fc), self.static)
        b1_block = combine_sources(apply_bias(fc, self.bias), self.bias.weights)
        b1 = to_panchayats(b1_block, self.static)
        b2 = apply_b2(b1, self.idw, self.static)
        cols = ["panchayat_id", *KEYS, *VALUE_COLS]
        return {"B0": b0[cols], "B1": b1[cols], "B2": b2[cols]}


def fit_baselines(fc: pd.DataFrame, ref: pd.DataFrame, obs_clean: pd.DataFrame, stations: pd.DataFrame,
                  static: pd.DataFrame, window: str = "TRAIN") -> Baselines:
    """Fit bias correction and station offsets on ``window`` (TRAIN by default)."""
    bias = fit_bias(fc, ref, window)
    offsets = fit_station_offsets(obs_clean, stations, static, ref, window)
    return Baselines(bias, offsets, idw_offsets(offsets, stations, static), static)
