"""Dew point and relative humidity (Magnus formula, Alduchov and Eskridge 1996 constants).

RH is never modelled directly: the model downscales dew point, and RH is derived from the
downscaled mean temperature and dew point (Backend Guide 6.1), which keeps them consistent.
"""

from __future__ import annotations

import numpy as np

MAGNUS_A = 17.625
MAGNUS_B = 243.04  # C
RH_FLOOR_PCT = 1.0  # log(RH) needs RH > 0


def saturation_ratio(t_c: np.ndarray) -> np.ndarray:
    """exp(a t / (b + t)), proportional to the saturation vapour pressure at ``t_c``."""
    t = np.asarray(t_c, dtype=float)
    return np.exp(MAGNUS_A * t / (MAGNUS_B + t))


def dewpoint_from_rh(t_c: np.ndarray, rh_pct: np.ndarray) -> np.ndarray:
    """Dew point in C from temperature (C) and relative humidity (%)."""
    t = np.asarray(t_c, dtype=float)
    rh = np.clip(np.asarray(rh_pct, dtype=float), RH_FLOOR_PCT, 100.0)
    gamma = np.log(rh / 100.0) + MAGNUS_A * t / (MAGNUS_B + t)
    return MAGNUS_B * gamma / (MAGNUS_A - gamma)


def rh_from_dewpoint(t_c: np.ndarray, td_c: np.ndarray) -> np.ndarray:
    """Relative humidity in %, clipped to 0..100, from temperature and dew point (C)."""
    return np.clip(100.0 * saturation_ratio(td_c) / saturation_ratio(t_c), 0.0, 100.0)
