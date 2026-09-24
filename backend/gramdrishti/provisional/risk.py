"""PROVISIONAL risk scores with PLACEHOLDER thresholds (thresholds_status = "placeholder").

Every number below is a placeholder until an agro-meteorology expert reviews it (S8). Scores are in [0, 1]
and map to levels: < 0.25 low, < 0.5 moderate, < 0.75 high, otherwise severe.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gramdrishti.provisional.forecast import prob_exceed

HEAVY_RAIN_MM = 35.0                 # placeholder
WATERLOG_RAIN_MM = 10.0              # placeholder
HEAT_START_C, HEAT_FULL_C = 35.0, 45.0      # placeholder
FROST_START_C, FROST_FULL_C = 4.0, -2.0     # placeholder
DRY_5DAY_MM = 10.0                   # placeholder: 5-day p50 total below this counts as dry
DRY_MONSOON_WEIGHT = 0.6             # a dry week alone reaches "high", never "severe"
DRY_OFF_SEASON_WEIGHT = 0.3          # dry days outside Jun-Sep matter less
DRAINAGE_WEIGHT = {"poor": 1.0, "moderate": 0.6, "good": 0.3}
LEVEL_CUTS = [(0.25, "low"), (0.5, "moderate"), (0.75, "high")]
RISK_TYPES = ["heavy_rain", "heat", "frost", "waterlogging", "dry_spell"]


def level_of(score: float) -> str:
    """Map a score in [0, 1] to low / moderate / high / severe."""
    for cut, name in LEVEL_CUTS:
        if score < cut:
            return name
    return "severe"


def _p(thr: float, row: pd.Series) -> float:
    return prob_exceed(thr, row["rain_p10"], row["rain_p50"], row["rain_p90"]) or 0.0


def risk_scores(pq: pd.DataFrame) -> pd.DataFrame:
    """Long table: panchayat_id, block_id, lead_day, valid_date, type, score, level.

    ``pq`` is the wide Panchayat table with ``<var>_p10/p50/p90`` columns and ``drainage_class``.
    """
    df = pq.copy()
    heavy = df.apply(lambda r: _p(HEAVY_RAIN_MM, r), axis=1)
    wet = df.apply(lambda r: _p(WATERLOG_RAIN_MM, r), axis=1)
    heat = ((df["tmax_p90"] - HEAT_START_C) / (HEAT_FULL_C - HEAT_START_C)).clip(0, 1)
    frost = ((FROST_START_C - df["tmin_p10"]) / (FROST_START_C - FROST_FULL_C)).clip(0, 1)
    waterlog = wet * df["drainage_class"].map(DRAINAGE_WEIGHT).fillna(0.6)
    rain5 = df.groupby("panchayat_id")["rain_p50"].transform("sum")
    monsoon = pd.to_datetime(df["valid_date"]).dt.month.between(6, 9)
    dry = (1 - rain5 / DRY_5DAY_MM).clip(0, 1) * np.where(monsoon, DRY_MONSOON_WEIGHT, DRY_OFF_SEASON_WEIGHT)

    scores = {"heavy_rain": heavy, "heat": heat, "frost": frost, "waterlogging": waterlog, "dry_spell": dry}
    keys = df[["panchayat_id", "block_id", "lead_day", "valid_date"]]
    out = pd.concat([keys.assign(type=t, score=s.astype(float).round(2).to_numpy())
                     for t, s in scores.items()], ignore_index=True)
    out["level"] = out["score"].map(level_of)
    return out
