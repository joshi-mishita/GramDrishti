"""Small agro helpers used by the provisional API. S6 replaces them with the agro-variable module.

- THI: NRC (1971) temperature-humidity index from daily mean temperature and mean RH.
- ET0: Hargreaves-Samani (FAO-56 eq. 52) from Tmax, Tmin and extraterrestrial radiation.
- Crop stage: days after sowing looked up in the PLACEHOLDER crop calendar.
Soil moisture and waterlogging risk need a water balance and are served as null until S6.
"""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

GSC = 0.0820  # solar constant, MJ m-2 min-1


def thi(tmean_c: float | None, rh_pct: float | None) -> float | None:
    """NRC 1971 THI: (1.8 T + 32) - (0.55 - 0.0055 RH) (1.8 T - 26)."""
    if tmean_c is None or rh_pct is None:
        return None
    return (1.8 * tmean_c + 32) - (0.55 - 0.0055 * rh_pct) * (1.8 * tmean_c - 26)


def extraterrestrial_radiation_mm(lat_deg: float, day: date) -> float:
    """Ra (FAO-56 eq. 21) expressed as evaporation equivalent in mm/day (x 0.408)."""
    j = day.timetuple().tm_yday
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * j / 365)
    delta = 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    ra = (24 * 60 / math.pi) * GSC * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))
    return 0.408 * ra


def et0_hargreaves(tmax_c: float | None, tmin_c: float | None, lat_deg: float, day: date) -> float | None:
    """ET0 = 0.0023 Ra (Tmean + 17.8) sqrt(Tmax - Tmin), mm/day."""
    if tmax_c is None or tmin_c is None:
        return None
    tmean = (tmax_c + tmin_c) / 2
    return 0.0023 * extraterrestrial_radiation_mm(lat_deg, day) * (tmean + 17.8) * math.sqrt(
        max(tmax_c - tmin_c, 0.0))


def crops_in_season(crops: pd.DataFrame, panchayat_id: str, on: pd.Timestamp) -> pd.DataFrame:
    """Crop rows of a Panchayat whose sowing-to-harvest period contains ``on``."""
    c = crops[crops["panchayat_id"] == panchayat_id]
    return c[(c["sowing_date"] <= on) & (c["expected_harvest_date"] >= on)]


def crop_stage(calendar: pd.DataFrame, crop: str, sowing: pd.Timestamp, on: pd.Timestamp) -> str | None:
    """Stage name from the placeholder calendar, or None when the crop or day is not covered."""
    das = (on - sowing).days
    c = calendar[(calendar["crop"] == crop) & (calendar["das_start"] <= das) & (calendar["das_end"] > das)]
    return None if c.empty else str(c.iloc[0]["stage"])
