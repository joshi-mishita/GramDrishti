"""Quality control for station observations (Backend Guide 3.1).

Every check adds boolean flag columns. No row is ever deleted and no value is changed.
Flag columns: ``qc_missing_<col>``, ``qc_range_<col>``, ``qc_stuck_<col>``, ``qc_spike_tmax_c``,
``qc_spike_tmin_c``, ``qc_consistency``, and the summaries ``qc_bad_<col>`` and ``qc_any``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gramdrishti.data.config import COLS

VALUE_COLS = list(COLS.values())
RANGES = {
    "rain_mm": (0.0, 400.0),
    "tmax_c": (-5.0, 52.0),
    "tmin_c": (-10.0, 35.0),
    "rh_mean_pct": (0.0, 100.0),
    "wind_kmh": (0.0, 120.0),
}
DIURNAL_MIN_C, DIURNAL_MAX_C = 1.0, 25.0
SPIKE_C = 12.0
STUCK_DAYS = 5


def flag_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Flag NaN values per variable."""
    for col in VALUE_COLS:
        df[f"qc_missing_{col}"] = df[col].isna()
    return df


def flag_range(df: pd.DataFrame) -> pd.DataFrame:
    """Flag values outside the plausible physical range. NaN is not a range failure."""
    for col, (lo, hi) in RANGES.items():
        v = df[col]
        df[f"qc_range_{col}"] = v.notna() & ((v < lo) | (v > hi))
    return df


def flag_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Flag days where tmin >= tmax or the diurnal range is below 1 C or above 25 C."""
    rng = df["tmax_c"] - df["tmin_c"]
    df["qc_consistency"] = rng.notna() & ((rng < DIURNAL_MIN_C) | (rng > DIURNAL_MAX_C))
    return df


def _previous_day(df: pd.DataFrame, col: str, id_col: str, date_col: str) -> pd.Series:
    """Value of ``col`` on the previous calendar day at the same station (NaN if that day is absent)."""
    prev = df[[id_col, date_col, col]].copy()
    prev[date_col] = prev[date_col] + pd.Timedelta(days=1)
    prev = prev.drop_duplicates([id_col, date_col]).rename(columns={col: "_prev"})
    merged = df[[id_col, date_col]].merge(prev, on=[id_col, date_col], how="left")
    return pd.Series(merged["_prev"].to_numpy(), index=df.index)


def flag_spike(df: pd.DataFrame, id_col: str = "station_id", date_col: str = "date") -> pd.DataFrame:
    """Flag a temperature jump above 12 C from the previous calendar day at the same station."""
    for col in ("tmax_c", "tmin_c"):
        jump = (df[col] - _previous_day(df, col, id_col, date_col)).abs()
        df[f"qc_spike_{col}"] = jump > SPIKE_C
    return df


def flag_stuck(df: pd.DataFrame, id_col: str = "station_id", date_col: str = "date") -> pd.DataFrame:
    """Flag every day of a run of the same non-zero value on 5 or more consecutive calendar days."""
    order = df.sort_values([id_col, date_col]).index
    s = df.loc[order]
    new_day_run = (s[date_col].diff() != pd.Timedelta(days=1)) | (s[id_col] != s[id_col].shift())
    for col in VALUE_COLS:
        v = s[col]
        breaks = new_day_run | (v != v.shift()) | v.isna()
        run_id = breaks.cumsum()
        run_len = run_id.map(run_id.value_counts())
        stuck = v.notna() & (v != 0) & (run_len >= STUCK_DAYS)
        df[f"qc_stuck_{col}"] = stuck.reindex(df.index)
    return df


def run_qc(obs: pd.DataFrame, id_col: str = "station_id", date_col: str = "date") -> pd.DataFrame:
    """Return a copy of ``obs`` with all QC flag columns added. Rows and values are unchanged."""
    df = obs.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    flag_missing(df)
    flag_range(df)
    flag_consistency(df)
    flag_spike(df, id_col, date_col)
    flag_stuck(df, id_col, date_col)
    for col in VALUE_COLS:
        bad = df[f"qc_range_{col}"] | df[f"qc_stuck_{col}"]
        if col in ("tmax_c", "tmin_c"):
            bad = bad | df["qc_consistency"] | df[f"qc_spike_{col}"]
        df[f"qc_bad_{col}"] = bad
    df["qc_any"] = df[[f"qc_bad_{c}" for c in VALUE_COLS]].any(axis=1)
    return df


def clean_values(flagged: pd.DataFrame) -> pd.DataFrame:
    """Copy of QC-flagged data where values that failed QC are set to NaN (rows kept)."""
    out = flagged.copy()
    for col in VALUE_COLS:
        out.loc[out[f"qc_bad_{col}"], col] = np.nan
    return out


def qc_summary(flagged: pd.DataFrame, id_col: str = "station_id", date_col: str = "date") -> pd.DataFrame:
    """Per station and month: expected days, missing days and flag counts per variable.

    Missing counts include calendar days with no row at all, within the overall date range of the data.
    Intended for the ``/data-quality`` endpoint.
    """
    df = flagged.copy()
    df["month"] = df[date_col].dt.to_period("M")
    first, last = df[date_col].min(), df[date_col].max()
    days = pd.DataFrame({"date": pd.date_range(first, last, freq="D")})
    expected = days.groupby(days["date"].dt.to_period("M")).size().rename("expected_days")

    agg: dict[str, pd.NamedAgg] = {"rows": pd.NamedAgg(date_col, "nunique")}
    for col in VALUE_COLS:
        agg[f"present_{col}"] = pd.NamedAgg(col, "count")
        agg[f"flagged_{col}"] = pd.NamedAgg(f"qc_bad_{col}", "sum")
    out = df.groupby([id_col, "month"]).agg(**agg)
    grid = pd.MultiIndex.from_product([df[id_col].unique(), expected.index], names=[id_col, "month"])
    out = out.reindex(grid, fill_value=0).reset_index()  # months with no rows at all count as fully missing
    out = out.merge(expected, left_on="month", right_index=True, how="left")
    for col in VALUE_COLS:
        out[f"missing_{col}"] = out["expected_days"] - out.pop(f"present_{col}")
    out["month"] = out["month"].astype(str)
    lead = [id_col, "month", "expected_days", "rows"]
    return out[lead + [c for c in out.columns if c not in lead]]
