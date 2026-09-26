"""Dynamic features known at issue time (Backend Guide section 4).

- Satellite: the latest week that ended on or before the issue date (``week_start + 7 days <= D``),
  taken separately for NDVI and LST because cloud gaps differ; NDVI trend against the previous
  available week; Panchayat minus block mean of the same features.
- Recent weather: block rainfall over the previous 3 and 7 days from QC-cleaned station
  observations dated strictly before the issue date.

Each builder also returns an audit column (``*_source_date``, not a feature) with the latest data
date it used, so tests can prove that nothing after the issue date was read.
"""

from __future__ import annotations

import pandas as pd

from gramdrishti.data.config import COLS

SAT_WEEK_DAYS = 7
SAT_NAMES = ["ndvi", "ndvi_trend", "ndvi_age_days", "ndvi_rel", "lst_day_c", "lst_age_days", "lst_rel"]
RAIN_NAMES = ["stn_rain_prev3_mm", "stn_rain_prev7_mm"]
AUDIT = ["ndvi_source_date", "lst_source_date", "stn_source_date"]


def _latest(sat: pd.DataFrame, keys: pd.DataFrame, col: str) -> pd.DataFrame:
    """Per (panchayat_id, issue_date): the latest non-missing ``col`` whose week ended by the issue date."""
    s = sat.dropna(subset=[col])[["panchayat_id", "week_start", col]].copy()
    s["avail_date"] = s["week_start"] + pd.Timedelta(days=SAT_WEEK_DAYS)
    s = s.sort_values(["panchayat_id", "avail_date"])
    s[f"{col}_prev"] = s.groupby("panchayat_id")[col].shift(1)
    k = keys.sort_values("issue_date")
    m = pd.merge_asof(k, s.sort_values("avail_date"), left_on="issue_date", right_on="avail_date",
                      by="panchayat_id", direction="backward", allow_exact_matches=True)
    return m


def satellite_features(sat: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    """Satellite features for ``keys`` (columns panchayat_id, block_id, issue_date)."""
    keys = keys[["panchayat_id", "block_id", "issue_date"]].drop_duplicates()
    nd = _latest(sat, keys, "ndvi")
    ls = _latest(sat, keys, "lst_day_c")
    out = nd[["panchayat_id", "block_id", "issue_date", "ndvi"]].copy()
    out["ndvi_trend"] = nd["ndvi"] - nd["ndvi_prev"]
    out["ndvi_age_days"] = (nd["issue_date"] - nd["avail_date"]).dt.days
    out["ndvi_source_date"] = nd["avail_date"]
    lst = ls[["panchayat_id", "issue_date", "lst_day_c", "avail_date"]]
    out = out.merge(lst, on=["panchayat_id", "issue_date"])
    out["lst_age_days"] = (out["issue_date"] - out["avail_date"]).dt.days
    out = out.rename(columns={"avail_date": "lst_source_date"})
    grp = out.groupby(["block_id", "issue_date"])
    out["ndvi_rel"] = out["ndvi"] - grp["ndvi"].transform("mean")
    out["lst_rel"] = out["lst_day_c"] - grp["lst_day_c"].transform("mean")
    return out[["panchayat_id", "issue_date", *SAT_NAMES, "ndvi_source_date", "lst_source_date"]]


def recent_rain_features(obs_clean: pd.DataFrame, stations: pd.DataFrame,
                         issue_dates: pd.Series) -> pd.DataFrame:
    """Block rain totals over the 3 and 7 days before each issue date (station mean per day).

    Days without any report count as missing; a total needs at least 2 of 3 (or 5 of 7) days.
    """
    rain = COLS["rain"]
    o = obs_clean.merge(stations[["station_id", "block_id"]], on="station_id")
    daily = o.dropna(subset=[rain]).groupby(["block_id", "date"])[rain].mean().unstack("block_id")
    issues = pd.DatetimeIndex(sorted(pd.to_datetime(issue_dates).unique()))
    full = pd.date_range(min(daily.index.min(), issues.min() - pd.Timedelta(days=7)),
                         max(daily.index.max(), issues.max()), freq="D")
    daily = daily.reindex(full)
    # Value at D sums D-k .. D-1: shift(1) drops the issue day itself.
    prev3 = daily.rolling(3, min_periods=2).sum().shift(1)
    prev7 = daily.rolling(7, min_periods=5).sum().shift(1)
    out = pd.DataFrame({
        "stn_rain_prev3_mm": prev3.reindex(issues).stack(future_stack=True),
        "stn_rain_prev7_mm": prev7.reindex(issues).stack(future_stack=True),
    })
    out.index = out.index.set_names(["issue_date", "block_id"])
    out = out.reset_index()
    out["stn_source_date"] = out["issue_date"] - pd.Timedelta(days=1)
    return out
