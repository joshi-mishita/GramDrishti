"""Signals for the advisory rules (Backend Guide 9.2), per Panchayat, crop and issue date.

A signal is one plain number, word or yes/no that a rule in ``rules.yaml`` can test. They come from the
forecast snapshot (quantiles, calibrated rain-event probabilities, agro-variables), the static features
and the crop calendar. ``SIGNALS`` lists every name a rule may use, with its unit and an English label
for the evidence rows; ``check_rules`` rejects any other name.

Conventions:
- "d1" is lead day 1 (tomorrow), "d2" lead day 2; "_2d" and "_3d" cover lead days 1-2 and 1-3.
- "Chance of X on at least one of several days" combines the daily probabilities as if the days were
  independent: 1 - prod(1 - p). Wet days cluster, so this is an upper bound (D058).
- Stage comes from the sowing date and the PLACEHOLDER crop calendar: das = valid date of lead day 1
  minus sowing date. A crop whose sowing date falls within the look-ahead gets stage ``pre_sowing``.
- Missing numbers (for example soil water in real mode) are None; a rule that needs one is skipped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from gramdrishti.advisory import spray
from gramdrishti.agro.derived import thi
from gramdrishti.models.humidity import rh_from_dewpoint

PRE_SOWING = "pre_sowing"
LIVESTOCK = "livestock"
WINDOW = (1, 2, 3)
VARS_WITH_INTERVAL = ("rain", "tmax", "tmin", "wind", "rh")


@dataclass(frozen=True)
class SignalSpec:
    """One signal: ``kind`` drives formatting (prob, frac, C, mm, mm/day, km/h, pct, days, index, score,
    text, bool); ``label`` is the English evidence label ({d1}, {d2}, {d3} become short dates)."""

    kind: str
    label: str


NUMERIC_KINDS = {"prob", "frac", "C", "mm", "mm/day", "km/h", "pct", "days", "index", "score"}

SIGNALS: dict[str, SignalSpec] = {
    # rain chances (calibrated event classifiers)
    "p_rain_1_d1": SignalSpec("prob", "Chance of 1 mm or more of rain on {d1}"),
    "p_rain_2_5_d1": SignalSpec("prob", "Chance of 2.5 mm or more of rain on {d1}"),
    "p_rain_2_5_d2": SignalSpec("prob", "Chance of 2.5 mm or more of rain on {d2}"),
    "p_rain_2_5_2d": SignalSpec("prob", "Chance of 2.5 mm or more on {d1} or {d2}"),
    "p_rain_10_d1": SignalSpec("prob", "Chance of 10 mm or more of rain on {d1}"),
    "p_rain_10_3d": SignalSpec("prob", "Chance of 10 mm or more on at least one day, {d1} to {d3}"),
    "p_rain_35_d1": SignalSpec("prob", "Chance of 35 mm or more of rain on {d1}"),
    "p_rain_35_3d": SignalSpec("prob", "Chance of 35 mm or more on at least one day, {d1} to {d3}"),
    # amounts and temperatures (quantiles)
    "rain_p50_3d": SignalSpec("mm", "Expected rain, total {d1} to {d3} (median)"),
    "rain_p90_max_3d": SignalSpec("mm", "Wettest day, upper estimate (p90), {d1} to {d3}"),
    "tmax_p90_3d": SignalSpec("C", "Highest maximum temperature, upper estimate (p90), {d1} to {d3}"),
    "tmin_p10_3d": SignalSpec("C", "Lowest minimum temperature, lower estimate (p10), {d1} to {d3}"),
    "tmean_3d": SignalSpec("C", "Mean temperature, {d1} to {d3}"),
    "rh_mean_3d": SignalSpec("pct", "Mean relative humidity, {d1} to {d3}"),
    "wind_p90_d1": SignalSpec("km/h", "Wind, upper estimate (p90), {d1}"),
    "thi_p90": SignalSpec("index", "Livestock heat index (THI) with the upper maximum temperature, "
                                   "highest {d1} to {d3}"),
    # soil water and dryness (agro-variables)
    "depletion": SignalSpec("frac", "Share of root-zone water already used, start of {d1}"),
    "soil_moisture_start": SignalSpec("frac", "Root-zone water as a share of capacity, start of {d1}"),
    "dry_days": SignalSpec("days", "Dry days in a row from {d1} (chance of 1 mm below 20 %)"),
    "et0_3d": SignalSpec("mm/day", "Crop water demand (reference evapotranspiration), mean {d1} to {d3}"),
    "waterlog_score_3d": SignalSpec("score", "Waterlogging score (0 to 1), highest {d1} to {d3}"),
    # spray planner (day level)
    "spray_d1": SignalSpec("text", "Spray day rating, {d1}"),
    "spray_d2": SignalSpec("text", "Spray day rating, {d2}"),
    "spray_days": SignalSpec("text", "Spray day ratings (whole days, not hours)"),
    # static features
    "drain_poor": SignalSpec("bool", "Poorly drained soil"),
    "drainage": SignalSpec("text", "Soil drainage class"),
    "low_lying": SignalSpec("bool", "Low-lying Panchayat"),
    "texture": SignalSpec("text", "Soil texture"),
    "irrigated_frac": SignalSpec("frac", "Irrigated share of the area"),
    "month": SignalSpec("index", "Month of {d1}"),
    # crop and stage (placeholder calendar)
    "crop": SignalSpec("text", "Crop"),
    "stage": SignalSpec("text", "Crop stage (placeholder calendar)"),
    "das": SignalSpec("days", "Days after sowing, {d1}"),
    "days_to_sowing": SignalSpec("days", "Days to the planned sowing date"),
    "days_to_harvest": SignalSpec("days", "Days to the expected harvest date"),
    "drought_sensitivity": SignalSpec("text", "Stage sensitivity to drought (placeholder calendar)"),
    "waterlog_sensitivity": SignalSpec("text", "Stage sensitivity to waterlogging (placeholder calendar)"),
    "tmax_alert_c": SignalSpec("C", "Heat alert for this crop stage (placeholder calendar)"),
    "tmin_alert_c": SignalSpec("C", "Cold alert for this crop stage (placeholder calendar)"),
    "topdress_stage": SignalSpec("bool", "Nitrogen top-dressing stage (placeholder calendar)"),
    "pest_watch_stage": SignalSpec("bool", "Pest or disease watch stage (placeholder calendar)"),
}

CROP_SIGNALS = ("crop", "stage", "das", "days_to_sowing", "days_to_harvest", "drought_sensitivity",
                "waterlog_sensitivity", "tmax_alert_c", "tmin_alert_c", "topdress_stage", "pest_watch_stage")


@dataclass
class Context:
    """Everything a rule sees for one Panchayat and one crop (or livestock) on one issue date."""

    issue_date: date
    panchayat_id: str
    block_id: str
    crop: str
    values: dict[str, object]
    leads: dict[str, int] = field(default_factory=dict)      # lead day each signal refers to
    widths: dict[str, dict[int, float]] = field(default_factory=dict)  # p90 - p10 per var and lead
    dates: dict[int, date] = field(default_factory=dict)     # lead day -> valid date
    next_spray_lead: int | None = None


def any_day(p: np.ndarray) -> float:
    """Chance of the event on at least one of the days, treating days as independent (upper bound)."""
    p = np.clip(np.asarray(p, dtype=float), 0.0, 1.0)
    return float(1 - np.prod(1 - p))


def _num(x: object) -> float | None:
    try:
        v = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def _argbest(values: pd.Series, how: str) -> tuple[float | None, int]:
    """(best value, its lead day) of a lead-indexed series; NaN-safe; lead 1 when all missing."""
    v = values.dropna()
    if v.empty:
        return None, 1
    lead = int(v.idxmax() if how == "max" else v.idxmin())
    return float(v.loc[lead]), lead


Widths = dict[str, dict[int, float]]


def weather_context(rows: pd.DataFrame, st: pd.Series, spray_th: dict[str, float], low_lying_z: float,
                    ) -> tuple[dict[str, object], dict[str, int], Widths, dict[int, date], int | None]:
    """Weather, soil and static signals for one Panchayat from its five forecast rows."""
    r = rows.set_index("lead_day").sort_index()
    w = r.loc[list(WINDOW)]
    dates = {int(k): pd.Timestamp(v).date() for k, v in r["valid_date"].items()}
    vals: dict[str, object] = {}
    leads: dict[str, int] = {}

    def prob_window(col: str, name: str) -> None:
        vals[name] = any_day(w[col].fillna(0.0).to_numpy())
        leads[name] = _argbest(w[col], "max")[1]

    vals["p_rain_1_d1"] = _num(r.at[1, "prob_rain_ge_1"])
    vals["p_rain_2_5_d1"] = _num(r.at[1, "prob_rain_ge_2_5"])
    vals["p_rain_2_5_d2"] = _num(r.at[2, "prob_rain_ge_2_5"])
    leads["p_rain_2_5_d2"] = 2
    vals["p_rain_2_5_2d"] = any_day(r.loc[[1, 2], "prob_rain_ge_2_5"].fillna(0.0).to_numpy())
    leads["p_rain_2_5_2d"] = _argbest(r.loc[[1, 2], "prob_rain_ge_2_5"], "max")[1]
    vals["p_rain_10_d1"] = _num(r.at[1, "prob_rain_ge_10"])
    prob_window("prob_rain_ge_10", "p_rain_10_3d")
    vals["p_rain_35_d1"] = _num(r.at[1, "prob_rain_ge_35"])
    prob_window("prob_rain_ge_35", "p_rain_35_3d")

    vals["rain_p50_3d"] = _num(w["rain_p50"].sum())
    vals["rain_p90_max_3d"], leads["rain_p90_max_3d"] = _argbest(w["rain_p90"], "max")
    vals["tmax_p90_3d"], leads["tmax_p90_3d"] = _argbest(w["tmax_p90"], "max")
    vals["tmin_p10_3d"], leads["tmin_p10_3d"] = _argbest(w["tmin_p10"], "min")
    vals["tmean_3d"] = _num(((w["tmax_p50"] + w["tmin_p50"]) / 2).mean())
    vals["rh_mean_3d"] = _num(w["rh_p50"].mean())
    vals["wind_p90_d1"] = _num(r.at[1, "wind_p90"])
    rh_hot = rh_from_dewpoint(w["tmax_p90"], w["td_p50"])
    thi90 = pd.Series(np.asarray(thi(w["tmax_p90"], rh_hot), dtype=float), index=w.index)
    vals["thi_p90"], leads["thi_p90"] = _argbest(thi90, "max")

    start = _num(r.at[1, "soil_moisture_frac_start"])
    vals["soil_moisture_start"] = start
    vals["depletion"] = None if start is None else 1 - start
    dry = 0
    for lead, n in r["dry_spell_days"].items():
        if int(n) == int(lead):
            dry = int(lead)
    vals["dry_days"] = dry
    leads["dry_days"] = max(dry, 1)
    vals["et0_3d"] = _num(w["et0_mm"].mean())
    vals["waterlog_score_3d"], leads["waterlog_score_3d"] = _argbest(w["waterlog_score"], "max")

    # Day-level spray planner. The data is daily, so a rating covers the whole day; hour-level spray
    # windows need hourly NWP (GFS gives 3-hourly fields) and are future work.
    p25 = [_num(r.at[k, "prob_rain_ge_2_5"]) for k in r.index]
    wind = [_num(r.at[k, "wind_p90"]) for k in r.index]
    ratings = spray.plan(p25, wind, spray_th)
    for k, rating in zip(r.index, ratings, strict=True):
        if k in (1, 2):
            vals[f"spray_d{k}"] = rating
    vals["spray_days"] = "; ".join(f"{dates[int(k)].day} {dates[int(k)]:%b}: {rt}"
                                   for k, rt in zip(r.index, ratings, strict=True))
    next_good = next((int(k) for k, rt in zip(r.index, ratings, strict=True) if rt == spray.GOOD), None)

    drainage = str(st["drainage_class"])
    vals.update(drain_poor=drainage == "poor", drainage=drainage,
                low_lying=bool(float(st["tpi_z"]) < low_lying_z), texture=str(st["soil_texture"]),
                irrigated_frac=_num(st["irrigated_frac"]), month=dates[1].month)

    widths: Widths = {
        v: {int(k): float(x) for k, x in (r[f"{v}_p90"] - r[f"{v}_p10"]).items() if np.isfinite(x)}
        for v in VARS_WITH_INTERVAL}
    soil = r["soil_moisture_frac_wet"] - r["soil_moisture_frac_dry"]
    widths["soil"] = {int(k): float(x) for k, x in soil.items() if np.isfinite(x)}
    return vals, leads, widths, dates, next_good


def crop_rows(crops: pd.DataFrame, pid: str, day1: pd.Timestamp, lookahead_days: int) -> pd.DataFrame:
    """Crops in the field on ``day1`` plus crops planned for sowing within the look-ahead."""
    c = crops[crops["panchayat_id"] == pid]
    in_season = (c["sowing_date"] <= day1) & (c["expected_harvest_date"] >= day1)
    upcoming = (c["sowing_date"] > day1) & (c["sowing_date"] <= day1 + pd.Timedelta(days=lookahead_days))
    return c[in_season | upcoming].sort_values(["crop", "sowing_date"])


def crop_values(row: pd.Series, calendar: pd.DataFrame, day1: pd.Timestamp) -> dict[str, object]:
    """Crop and stage signals for one crop row (calendar thresholds are placeholders)."""
    das = int((day1 - row["sowing_date"]).days)
    base: dict[str, object] = {
        "crop": row["crop"], "das": das, "days_to_sowing": max(-das, 0) if das < 0 else None,
        "days_to_harvest": int((row["expected_harvest_date"] - day1).days),
        "stage": None, "drought_sensitivity": None, "waterlog_sensitivity": None,
        "tmax_alert_c": None, "tmin_alert_c": None, "topdress_stage": False, "pest_watch_stage": False}
    if das < 0:
        base["stage"] = PRE_SOWING
        base["days_to_harvest"] = None
        return base
    cal = calendar[(calendar["crop"] == row["crop"]) & (calendar["das_start"] <= das)
                   & (calendar["das_end"] > das)]
    if cal.empty:
        return base
    c = cal.iloc[0]
    ops = str(c["key_operations"]).lower()
    base.update(stage=str(c["stage"]), drought_sensitivity=str(c["drought_sensitivity"]),
                waterlog_sensitivity=str(c["waterlog_sensitivity"]),
                tmax_alert_c=_num(c["tmax_alert_c"]), tmin_alert_c=_num(c["tmin_alert_c"]),
                topdress_stage=("nitrogen" in ops or "top-dress" in ops),
                pest_watch_stage=any(w in ops for w in ("disease", "pest", "aphid")))
    return base


def build_contexts(issue: date, forecast: pd.DataFrame, static: pd.DataFrame, crops: pd.DataFrame,
                   calendar: pd.DataFrame, spray_th: dict[str, float], lookahead_days: int,
                   low_lying_z: float) -> list[Context]:
    """One context per (Panchayat, crop in the field or about to be sown) plus one livestock context
    per Panchayat, in a fixed order (Panchayat id, then livestock, then crop name)."""
    st = static.set_index("panchayat_id")
    out: list[Context] = []
    for pid, rows in forecast.groupby("panchayat_id", sort=True):
        wvals, leads, widths, dates, next_good = weather_context(rows, st.loc[pid], spray_th, low_lying_z)
        block = str(rows["block_id"].iloc[0])
        day1 = pd.Timestamp(dates[1])
        empty = {k: None for k in CROP_SIGNALS} | {"topdress_stage": False, "pest_watch_stage": False}

        def ctx(crop: str, cvals: dict[str, object], wv=wvals, lv=leads, wd=widths, dt=dates, ng=next_good,
                p=pid, b=block) -> Context:
            return Context(issue, str(p), b, crop, {**wv, **cvals}, dict(lv), wd, dt, ng)

        out.append(ctx(LIVESTOCK, {**empty, "crop": LIVESTOCK}))
        seen: set[str] = set()
        for _, row in crop_rows(crops, str(pid), day1, lookahead_days).iterrows():
            if row["crop"] in seen:   # one context per crop: the earliest-sown row wins
                continue
            seen.add(row["crop"])
            out.append(ctx(str(row["crop"]), crop_values(row, calendar, day1)))
    return out
