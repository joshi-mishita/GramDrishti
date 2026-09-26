"""Daily agro-variables derived from the Panchayat forecast (Backend Guide section 8).

Everything here works on whole arrays: one row per (Panchayat, lead day). Every threshold and
coefficient marked PLACEHOLDER waits for expert review (``thresholds_status: "placeholder"``).

- ET0: Hargreaves-Samani (FAO-56 eq. 52) with extraterrestrial radiation Ra from latitude and
  day of year (FAO-56 eq. 21-25), from the p50 Tmax and Tmin.
- Growing degree days: max(Tmean - Tbase, 0) per crop (Tbase placeholder, the calendar has none).
- Soil water: a bucket run forward five days from the latest known state, once with p50 rain
  (central path) and once each with p10 and p90 rain (dry and wet paths).
  SM(t+1) = clip(SM(t) + rain_eff - kc * ET0 * stress, 0, capacity), capacity = whc_mm_per_m * 0.6 m.
- Depletion fraction: 1 - SM / capacity (central path).
- Waterlogging: P(rain >= 35 mm) with poor drainage or low-lying ground (tpi_z < -0.7) and a
  nearly full bucket at the start of the day.
- Livestock THI: 0.8 T + (RH / 100)(T - 14.4) + 46.4 with Tmax and an afternoon RH proxy
  (RH at Tmax from the dew point).
- Frost: P(Tmin <= threshold) from the Tmin quantiles; low-lying ground raises the level.
  Fog: a December-January proxy (cold, humid, calm). No fog variable exists.
- Dry-spell counter: consecutive forecast days with P(rain >= 1 mm) < 0.2, counted from lead day 1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from gramdrishti.models.humidity import rh_from_dewpoint

GSC = 0.0820                      # solar constant, MJ m-2 min-1
MJ_TO_MM = 0.408                  # MJ m-2 day-1 -> mm day-1 evaporation equivalent
ROOT_DEPTH_M = 0.6                # capacity = whc_mm_per_m * 0.6 m (guide)
RUNOFF_ABOVE_MM = 20.0            # PLACEHOLDER: rain above this on one day runs off (guide)
STRESS_P = 0.5                    # PLACEHOLDER: ET falls linearly once SM < 0.5 * capacity (FAO-56 p)
KC_BASE, KC_NDVI = 0.4, 0.6       # PLACEHOLDER: kc = 0.4 + 0.6 * NDVI (no crop-specific kc yet)
KC_DEFAULT = 0.8                  # PLACEHOLDER: when NDVI is missing
WATERLOG_EVENT = "prob_rain_ge_35"
WATERLOG_FULL_FRAC = 0.9          # guide: SM above 90 % of capacity
WATERLOG_TPI_Z = -0.7             # guide: low-lying
WATERLOG_WEIGHTS = {"vulnerable": 1.0, "other": 0.4, "full": 1.0, "not_full": 0.5}  # PLACEHOLDER
WATERLOG_CUTS = (0.1, 0.25, 0.5)  # PLACEHOLDER: score -> moderate, high, severe
FROST_C = 2.0                     # PLACEHOLDER generic threshold; crop thresholds arrive with rules (S8)
FROST_CUTS = (0.1, 0.3, 0.6)      # PLACEHOLDER: probability -> moderate, high, severe
FROST_TPI_Z = -0.7                # cold air pools in low-lying Panchayats
FOG_MONTHS = (12, 1)
FOG_TMIN_C, FOG_RH_PCT, FOG_WIND_KMH = 8.0, 75.0, 6.0   # PLACEHOLDER proxy
DRY_PROB = 0.2                    # guide: P(rain >= 1 mm) < 0.2 counts as a dry day
DRY_EVENT = "prob_rain_ge_1"
# PLACEHOLDER base temperatures (C). The placeholder crop calendar has no Tbase column.
TBASE_C = {"wheat": 5.0, "mustard": 5.0, "paddy": 10.0, "bajra": 10.0, "cotton": 15.0}
LEVELS = np.array(["low", "moderate", "high", "severe"])
Z90 = norm.ppf(0.9)


def extraterrestrial_radiation_mm(lat_deg: np.ndarray, doy: np.ndarray) -> np.ndarray:
    """Ra (FAO-56 eq. 21) as evaporation equivalent in mm/day."""
    phi = np.radians(np.asarray(lat_deg, dtype=float))
    j = np.asarray(doy, dtype=float)
    dr = 1 + 0.033 * np.cos(2 * np.pi * j / 365)
    delta = 0.409 * np.sin(2 * np.pi * j / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(delta), -1.0, 1.0))
    ra = (24 * 60 / np.pi) * GSC * dr * (ws * np.sin(phi) * np.sin(delta)
                                         + np.cos(phi) * np.cos(delta) * np.sin(ws))
    return MJ_TO_MM * ra


def et0_hargreaves(tmax: np.ndarray, tmin: np.ndarray, lat_deg: np.ndarray, doy: np.ndarray) -> np.ndarray:
    """ET0 = 0.0023 Ra (Tmean + 17.8) sqrt(Tmax - Tmin), mm/day, never negative."""
    tmax, tmin = np.asarray(tmax, dtype=float), np.asarray(tmin, dtype=float)
    tmean = (tmax + tmin) / 2
    et0 = 0.0023 * extraterrestrial_radiation_mm(lat_deg, doy) * (tmean + 17.8) * np.sqrt(
        np.maximum(tmax - tmin, 0.0))
    return np.maximum(et0, 0.0)


def gdd(tmax: np.ndarray, tmin: np.ndarray, tbase: float) -> np.ndarray:
    """Growing degree days for one day: max((Tmax + Tmin) / 2 - Tbase, 0)."""
    return np.maximum((np.asarray(tmax, dtype=float) + np.asarray(tmin, dtype=float)) / 2 - tbase, 0.0)


def thi(tmax: np.ndarray, rh_afternoon: np.ndarray) -> np.ndarray:
    """Livestock temperature-humidity index (guide formula) from Tmax (C) and afternoon RH (%)."""
    t = np.asarray(tmax, dtype=float)
    return 0.8 * t + (np.asarray(rh_afternoon, dtype=float) / 100) * (t - 14.4) + 46.4


def effective_rain(rain: np.ndarray) -> np.ndarray:
    """Rain that enters the soil: the part above ``RUNOFF_ABOVE_MM`` runs off."""
    return np.minimum(np.maximum(np.asarray(rain, dtype=float), 0.0), RUNOFF_ABOVE_MM)


def crop_coefficient(ndvi: np.ndarray) -> np.ndarray:
    """PLACEHOLDER kc from NDVI; ``KC_DEFAULT`` where NDVI is missing."""
    kc = KC_BASE + KC_NDVI * np.clip(np.asarray(ndvi, dtype=float), 0.0, 1.0)
    return np.where(np.isnan(kc), KC_DEFAULT, kc)


def run_bucket(sm0_mm: np.ndarray, cap_mm: np.ndarray, rain: np.ndarray, et0: np.ndarray,
               kc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Soil water forward in time.

    ``sm0_mm``, ``cap_mm`` and ``kc`` have shape (n,); ``rain`` and ``et0`` have shape (n, days).
    Returns (SM at the start of each day, SM at the end of each day), both (n, days) in mm.
    A NaN start state gives NaN throughout.
    """
    n, days = rain.shape
    start, end = np.empty((n, days)), np.empty((n, days))
    sm = np.asarray(sm0_mm, dtype=float).copy()
    cap = np.asarray(cap_mm, dtype=float)
    for t in range(days):
        start[:, t] = sm
        wet = np.minimum(sm + effective_rain(rain[:, t]), cap)
        stress = np.minimum(1.0, wet / (STRESS_P * cap))
        sm = np.clip(wet - kc * et0[:, t] * stress, 0.0, cap)
        end[:, t] = sm
    return start, end


def _level(x: np.ndarray, cuts: tuple[float, float, float]) -> np.ndarray:
    """0..3 index into ``LEVELS``; NaN stays NaN."""
    x = np.asarray(x, dtype=float)
    idx = np.searchsorted(np.asarray(cuts), x, side="right").astype(float)
    return np.where(np.isnan(x), np.nan, idx)


def _names(idx: np.ndarray) -> np.ndarray:
    return np.array([None if np.isnan(i) else LEVELS[int(i)] for i in idx], dtype=object)


def waterlog_score(p35: np.ndarray, vulnerable: np.ndarray, sm_start_frac: np.ndarray) -> np.ndarray:
    """PLACEHOLDER score in [0, 1]; NaN when the soil state is unknown."""
    w = WATERLOG_WEIGHTS
    drain = np.where(vulnerable, w["vulnerable"], w["other"])
    sm = np.asarray(sm_start_frac, dtype=float)
    full = np.where(sm >= WATERLOG_FULL_FRAC, w["full"], w["not_full"])
    return np.where(np.isnan(sm), np.nan, np.asarray(p35, dtype=float) * drain * full)


def prob_below(threshold: float, p10: np.ndarray, p50: np.ndarray, p90: np.ndarray) -> np.ndarray:
    """P(X <= threshold) from three quantiles with a split normal (lower and upper spreads)."""
    p10, p50, p90 = (np.asarray(a, dtype=float) for a in (p10, p50, p90))
    lo = np.maximum((p50 - p10) / Z90, 0.05)
    hi = np.maximum((p90 - p50) / Z90, 0.05)
    x = threshold - p50
    return norm.cdf(np.where(x < 0, x / lo, x / hi))


def frost_level(prob: np.ndarray, tpi_z: np.ndarray) -> np.ndarray:
    """Level from the frost probability; low-lying ground raises moderate and above by one level."""
    idx = _level(prob, FROST_CUTS)
    bump = (np.asarray(tpi_z, dtype=float) < FROST_TPI_Z) & (idx >= 1)
    return _names(np.minimum(idx + bump, 3))


def fog_proxy(month: np.ndarray, tmin: np.ndarray, rh: np.ndarray, wind: np.ndarray) -> np.ndarray:
    """December-January cold, humid, calm day. A proxy only: no fog variable exists."""
    return (np.isin(month, FOG_MONTHS) & (tmin <= FOG_TMIN_C) & (rh >= FOG_RH_PCT) & (wind <= FOG_WIND_KMH))


def dry_spell_counter(p_wet: np.ndarray) -> np.ndarray:
    """Running count of consecutive dry forecast days, shape (n, days) -> (n, days) ints."""
    dry = np.asarray(p_wet, dtype=float) < DRY_PROB
    out = np.zeros(dry.shape, dtype=int)
    run = np.zeros(dry.shape[0], dtype=int)
    for t in range(dry.shape[1]):
        run = np.where(dry[:, t], run + 1, 0)
        out[:, t] = run
    return out


def _grid(df: pd.DataFrame, col: str, pids: pd.Index, leads: list[int]) -> np.ndarray:
    return df.pivot(index="panchayat_id", columns="lead_day", values=col).reindex(
        index=pids, columns=leads).to_numpy(dtype=float)


def derive(pred: pd.DataFrame, static: pd.DataFrame, sm0_frac: pd.Series) -> pd.DataFrame:
    """Agro-variables for one issue date.

    ``pred``: one row per (panchayat_id, lead_day) with ``valid_date``, ``<var>_p10/p50/p90``,
    ``td_p50``, ``prob_rain_ge_1`` and ``prob_rain_ge_35`` and ``ndvi``.
    ``static``: panchayat_id, lat, whc_mm_per_m, drainage_class, tpi_z.
    ``sm0_frac``: soil moisture fraction per panchayat_id at the start of lead day 1 (NaN if unknown).
    Returns panchayat_id, lead_day and the derived columns.
    """
    if pred.duplicated(["panchayat_id", "lead_day"]).any():
        raise ValueError("derive() expects one issue date: one row per Panchayat and lead day")
    df = pred.merge(static[["panchayat_id", "lat", "whc_mm_per_m", "drainage_class", "tpi_z"]],
                    on="panchayat_id", how="left", validate="many_to_one")
    vd = pd.to_datetime(df["valid_date"])
    out = df[["panchayat_id", "lead_day"]].copy()
    out["et0_mm"] = et0_hargreaves(df["tmax_p50"], df["tmin_p50"], df["lat"], vd.dt.dayofyear)
    for crop, tbase in TBASE_C.items():
        out[f"gdd_{crop}"] = gdd(df["tmax_p50"], df["tmin_p50"], tbase)
    out["rh_afternoon"] = rh_from_dewpoint(df["tmax_p50"], df["td_p50"])
    out["thi"] = thi(df["tmax_p50"], out["rh_afternoon"])
    out["frost_prob"] = prob_below(FROST_C, df["tmin_p10"], df["tmin_p50"], df["tmin_p90"])
    out["frost_risk"] = frost_level(out["frost_prob"].to_numpy(), df["tpi_z"].to_numpy())
    out["fog_proxy"] = fog_proxy(vd.dt.month.to_numpy(), df["tmin_p50"].to_numpy(), df["rh_p50"].to_numpy(),
                                 df["wind_p50"].to_numpy())

    # Soil water on a (Panchayat x lead day) grid.
    per_p = df.drop_duplicates("panchayat_id").set_index("panchayat_id")
    pids = per_p.index
    leads = sorted(df["lead_day"].unique())
    cap = per_p["whc_mm_per_m"].to_numpy(dtype=float) * ROOT_DEPTH_M
    sm0 = sm0_frac.reindex(pids).to_numpy(dtype=float) * cap
    ndvi = per_p["ndvi"].to_numpy(dtype=float) if "ndvi" in per_p else np.full(len(pids), np.nan)
    kc = crop_coefficient(ndvi)
    et0 = out.assign(panchayat_id=df["panchayat_id"]).pipe(_grid, "et0_mm", pids, leads)
    paths = {}
    for name, q in (("", "p50"), ("_dry", "p10"), ("_wet", "p90")):
        start, end = run_bucket(sm0, cap, _grid(df, f"rain_{q}", pids, leads), et0, kc)
        paths[name] = (start / cap[:, None], end / cap[:, None])
    vulnerable = ((per_p["drainage_class"] == "poor") | (per_p["tpi_z"] < WATERLOG_TPI_Z)).to_numpy()
    p35 = _grid(df, WATERLOG_EVENT, pids, leads)
    wl = waterlog_score(p35, vulnerable[:, None], paths[""][0])
    dry = dry_spell_counter(_grid(df, DRY_EVENT, pids, leads))

    grid = pd.DataFrame({
        "panchayat_id": np.repeat(pids.to_numpy(), len(leads)),
        "lead_day": np.tile(leads, len(pids)),
        "soil_moisture_frac": paths[""][1].ravel(),
        "soil_moisture_frac_dry": paths["_dry"][1].ravel(),
        "soil_moisture_frac_wet": paths["_wet"][1].ravel(),
        "soil_moisture_frac_start": paths[""][0].ravel(),
        "depletion_frac": 1 - paths[""][1].ravel(),
        "waterlog_score": wl.ravel(),
        "waterlog_risk": _names(_level(wl.ravel(), WATERLOG_CUTS)),
        "dry_spell_days": dry.ravel(),
    })
    return out.merge(grid, on=["panchayat_id", "lead_day"], how="left", validate="one_to_one")
