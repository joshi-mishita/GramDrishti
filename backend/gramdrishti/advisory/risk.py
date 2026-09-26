"""Risk scores per Panchayat, lead day and risk type for ``GET /risk`` and ``GET /priority``.

Scores are in [0, 1] and turn into low / moderate / high / severe with the PLACEHOLDER cuts in
``rules.yaml`` (``risk``). Heat and frost use the crop-stage alerts of the crops in season at that
Panchayat (placeholder calendar), so the map shows the hazard for what is growing there:
- heavy_rain: P(rain >= 35 mm), calibrated classifier;
- heat: P(Tmax >= lowest heat alert of the crops in season), else the generic heat threshold;
- frost: P(Tmin <= highest cold alert of the crops in season), else the generic frost threshold;
  low-lying Panchayats go one level up from moderate (cold air pools there, as in agro/derived.py);
- waterlogging: the waterlogging score from agro/derived.py (unknown soil state: no item);
- dry_spell: (dry days in a row up to that day / full_days) x (0.5 + 0.5 x soil water used),
  with 0.75 for the soil factor when soil water is unknown.
Temperature probabilities come from the p10/p50/p90 quantiles through a split normal (agro/derived.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gramdrishti.advisory.rules import RuleFile
from gramdrishti.advisory.signals import LIVESTOCK, Context
from gramdrishti.agro.derived import prob_below

RISK_TYPES = ("heavy_rain", "heat", "frost", "waterlogging", "dry_spell")
LEVELS = np.array(["low", "moderate", "high", "severe"])
UNKNOWN_SOIL_FACTOR = 0.75


def levels(score: np.ndarray, cuts: list[float]) -> np.ndarray:
    """Level names from scores and three increasing cuts (below the first cut is low)."""
    idx = np.searchsorted(np.asarray(cuts), np.asarray(score, dtype=float), side="right")
    return LEVELS[np.clip(idx, 0, 3)]


def crop_alerts(contexts: list[Context]) -> pd.DataFrame:
    """Per Panchayat: lowest heat alert and highest cold alert of its crops in the field (not pre-sowing)."""
    rows = []
    for c in contexts:
        if c.crop == LIVESTOCK or c.values.get("stage") in (None, "pre_sowing"):
            continue
        rows.append({"panchayat_id": c.panchayat_id, "tmax_alert_c": c.values.get("tmax_alert_c"),
                     "tmin_alert_c": c.values.get("tmin_alert_c")})
    df = pd.DataFrame(rows, columns=["panchayat_id", "tmax_alert_c", "tmin_alert_c"]).astype(
        {"tmax_alert_c": float, "tmin_alert_c": float})
    return df.groupby("panchayat_id").agg(heat_c=("tmax_alert_c", "min"), frost_c=("tmin_alert_c", "max"))


def risk_scores(forecast: pd.DataFrame, static: pd.DataFrame, contexts: list[Context],
                rf: RuleFile) -> pd.DataFrame:
    """Long table: panchayat_id, block_id, lead_day, valid_date, type, score, level, threshold_c."""
    df = forecast.merge(static[["panchayat_id", "tpi_z"]], on="panchayat_id", how="left")
    df = df.sort_values(["panchayat_id", "lead_day"]).reset_index(drop=True)
    alerts = crop_alerts(contexts).reindex(df["panchayat_id"])
    heat_c = alerts["heat_c"].fillna(rf.risk["heat"].thresholds["generic_heat_c"].value).to_numpy()
    frost_c = alerts["frost_c"].fillna(rf.risk["frost"].thresholds["generic_frost_c"].value).to_numpy()

    heat = 1 - prob_below(heat_c, df["tmax_p10"], df["tmax_p50"], df["tmax_p90"])
    frost = prob_below(frost_c, df["tmin_p10"], df["tmin_p50"], df["tmin_p90"])
    full = rf.risk["dry_spell"].thresholds["full_days"].value
    soil = (0.5 + 0.5 * (1 - df["soil_moisture_frac"]).clip(0, 1)).fillna(UNKNOWN_SOIL_FACTOR)
    dry = (df["dry_spell_days"] / full).clip(0, 1) * soil

    parts = {"heavy_rain": (df["prob_rain_ge_35"].to_numpy(dtype=float), None),
             "heat": (np.asarray(heat, dtype=float), heat_c),
             "frost": (np.asarray(frost, dtype=float), frost_c),
             "waterlogging": (df["waterlog_score"].to_numpy(dtype=float), None),
             "dry_spell": (dry.to_numpy(dtype=float), None)}
    keys = df[["panchayat_id", "block_id", "lead_day", "valid_date"]]
    frames = []
    for rtype, (score, thr) in parts.items():
        f = keys.assign(type=rtype, score=np.round(np.clip(score, 0, 1), 2),
                        threshold_c=np.nan if thr is None else thr)
        f = f[np.isfinite(score)]
        lv = levels(f["score"].to_numpy(), rf.risk[rtype].cuts)
        if rtype == "frost":
            low = (df.loc[f.index, "tpi_z"] < rf.context["low_lying_tpi_z"].value).to_numpy()
            idx = np.array([list(LEVELS).index(x) for x in lv])
            lv = LEVELS[np.minimum(idx + (low & (idx >= 1)), 3)]
        frames.append(f.assign(level=lv))
    return pd.concat(frames, ignore_index=True)
