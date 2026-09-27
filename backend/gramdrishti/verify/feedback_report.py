"""Monthly feedback check: farmers' "Did it rain?" reports against what was observed (DEMO OF THE LOOP).

Run: ``cd backend && python -m gramdrishti.verify.feedback_report --month 2023-08``
(writes ``docs/feedback_loop_demo.md``; ``--no-store`` leaves out reports stored by the API).

What it does, per Panchayat and for the whole district:
- takes the month's reports (the mock file ``farmer_feedback_mock.csv`` plus reports stored by
  ``POST /feedback`` in SQLite);
- finds what really happened that day: the Panchayat's own station when it has one with a rain value
  that passed QC, else (mock mode only) the synthetic truth; in real mode such reports stay unchecked;
- compares rain yes/no (1 mm or more counts as rain) and the intensity class;
- counts how many Panchayats had any ground check that month from stations alone and with the reports.

What it does NOT do: it does not retrain or adjust any model and does not score the forecast. It shows
the first step of the loop: reports reach Panchayats that have no station, and they can be checked for
reliability before anyone relies on them. Scoring forecasts against reports would belong in the
verification job.

TEST window: months inside TEST (2024-07-16 onwards) are refused. The synthetic truth there is the
answer key of the one-time verification run, so this demo stays in TRAIN and CALIB months.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from gramdrishti.data import loaders
from gramdrishti.data.config import ROOT, data_mode, window_bounds
from gramdrishti.data.qc import clean_values, run_qc
from gramdrishti.store.db import Store

OUT = ROOT / "docs" / "feedback_loop_demo.md"
DEFAULT_MONTH = "2023-08"
RAIN_MM = 1.0
# Intensity classes for this check (mm per day). Our own placeholder bins, not the IMD categories.
INTENSITY_BINS = ((1.0, "none"), (10.0, "light"), (35.0, "moderate"), (np.inf, "heavy"))


@dataclass
class FeedbackCheck:
    """The month's checked reports and the summary numbers."""

    month: str
    rows: pd.DataFrame          # one row per report with truth source and agreement
    per_panchayat: pd.DataFrame
    n_panchayats: int
    station_panchayats: int     # Panchayats whose station reported rain on at least one day that month
    reported_panchayats: int    # Panchayats with at least one report
    reported_without_station: int


def intensity_class(rain_mm: float) -> str | None:
    """Intensity class of a daily rain amount; None when the amount is unknown."""
    if pd.isna(rain_mm):
        return None
    return next(label for upper, label in INTENSITY_BINS if rain_mm < upper)


def month_bounds(month: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """First and last day of ``YYYY-MM``. Refuses months that reach into the TEST window."""
    start = pd.Timestamp(f"{month}-01")
    end = start + pd.offsets.MonthEnd(0)
    test_start = window_bounds("TEST")[0]
    if end >= test_start:
        raise PermissionError(f"{month} reaches into the TEST window (from {test_start.date()}); "
                              "the feedback demo uses TRAIN and CALIB months only")
    return start, end


def load_reports(start: pd.Timestamp, end: pd.Timestamp, store: Store | None) -> pd.DataFrame:
    """Reports in the month from the mock file and (optionally) the SQLite store, one schema."""
    f = loaders.load_feedback()
    f = pd.DataFrame({"date": f["date"], "panchayat_id": f["panchayat_id"],
                      "reported_rain": f["reported_rain"].eq("yes"), "intensity": f["reported_intensity"],
                      "channel": f["channel"], "source": "mock_file"})
    parts = [f]
    if store is not None:
        rows = store.feedback_rows()
        if rows:
            db = pd.DataFrame(rows)
            parts.append(pd.DataFrame({"date": pd.to_datetime(db["date"]), "panchayat_id": db["panchayat_id"],
                                       "reported_rain": db["reported_rain"].astype(bool),
                                       "intensity": db["intensity"], "channel": db["channel"],
                                       "source": "api"}))
    out = pd.concat(parts, ignore_index=True)
    out = out[(out["date"] >= start) & (out["date"] <= end)]
    return out.sort_values(["date", "panchayat_id"]).reset_index(drop=True)


def observed_rain(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Daily rain per Panchayat and its source: QC-passed station values, else synthetic truth (mock only)."""
    stations = loaders.load_stations()[["station_id", "panchayat_id"]]
    obs = clean_values(run_qc(loaders.load_obs()))
    obs = obs[(obs["date"] >= start) & (obs["date"] <= end)].merge(stations, on="station_id")
    obs = obs.dropna(subset=["rain_mm"])[["date", "panchayat_id", "rain_mm"]].assign(truth_source="station")
    if data_mode() != "mock":
        return obs.reset_index(drop=True)
    truth = loaders.load_truth()  # MOCK ONLY: display and checking, never a feature
    truth = truth[(truth["date"] >= start) & (truth["date"] <= end)][["date", "panchayat_id", "rain_mm"]]
    truth = truth.assign(truth_source="synthetic_truth")
    both = pd.concat([obs, truth], ignore_index=True)
    return both.drop_duplicates(["date", "panchayat_id"], keep="first").reset_index(drop=True)


def check_month(month: str = DEFAULT_MONTH, store: Store | None = None) -> FeedbackCheck:
    """Compare the month's reports with observed rain and summarise per Panchayat."""
    start, end = month_bounds(month)
    static = loaders.load_static()[["panchayat_id", "block_id"]]
    with_station = set(loaders.load_stations()["panchayat_id"])
    obs = observed_rain(start, end)
    rows = load_reports(start, end, store).merge(obs, on=["date", "panchayat_id"], how="left")
    rows["truth_source"] = rows["truth_source"].fillna("none")
    rows["truth_rain"] = rows["rain_mm"].ge(RAIN_MM).where(rows["rain_mm"].notna())
    rows["truth_intensity"] = rows["rain_mm"].map(intensity_class)
    checked = rows["rain_mm"].notna()
    rows["rain_agrees"] = (rows["reported_rain"] == rows["truth_rain"]).where(checked)
    rows["intensity_agrees"] = (rows["intensity"] == rows["truth_intensity"]).where(checked)
    rows["has_station"] = rows["panchayat_id"].isin(with_station)

    g = rows.groupby("panchayat_id")
    per = pd.DataFrame({"reports": g.size(), "checked": g["rain_mm"].count(),
                        "rain_agrees": g["rain_agrees"].sum(),
                        "intensity_agrees": g["intensity_agrees"].sum(),
                        "truth_source": g["truth_source"].agg(lambda x: "/".join(sorted(set(x))))})
    per = per.reset_index().merge(static, on="panchayat_id", how="left")
    per["has_station"] = per["panchayat_id"].isin(with_station)
    station_pids = set(obs.loc[obs["truth_source"] == "station", "panchayat_id"])
    reported = set(rows["panchayat_id"])
    return FeedbackCheck(month=month, rows=rows, per_panchayat=per, n_panchayats=len(static),
                         station_panchayats=len(station_pids), reported_panchayats=len(reported),
                         reported_without_station=len(reported - with_station))


def _pct(a: float, b: float) -> str:
    return f"{100 * a / b:.0f}% ({int(a)} of {int(b)})" if b else "n/a (0 checked)"


def render(c: FeedbackCheck, generated: date) -> str:
    """Markdown report."""
    r = c.rows
    ok = r["rain_agrees"].notna()
    covered = c.station_panchayats + c.reported_without_station
    lines = [
        f"# Feedback loop demo: {c.month}",
        "",
        "**Demo of the feedback loop, not a result.** Synthetic data (`data_mode: mock`): the reports are",
        "generated (about 88 % correct by construction) and the truth is synthetic. Nothing here retrains or",
        "adjusts a model, and the forecast is not scored.",
        "",
        f"Generated {generated.isoformat()} by "
        f"`python -m gramdrishti.verify.feedback_report --month {c.month}`.",
        "Rain counts as \"yes\" from 1 mm a day. Intensity classes for this check: none under 1 mm, light",
        "1 to 10 mm, moderate 10 to 35 mm, heavy 35 mm or more (placeholder bins, not IMD categories).",
        "",
        "## District",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Reports this month | {len(r)} ({int((r['source'] == 'api').sum())} from the API, "
        f"{int((r['source'] == 'mock_file').sum())} from the mock file) |",
        f"| Reports checked against station or synthetic truth | {int(ok.sum())} |",
        f"| Rain yes/no agrees with what happened | {_pct(r['rain_agrees'].sum(), ok.sum())} |",
        f"| Intensity class agrees | {_pct(r['intensity_agrees'].sum(), ok.sum())} |",
        f"| Checked against a station | {_pct((r['truth_source'] == 'station').sum(), ok.sum())} |",
        f"| Panchayats with a station rain value this month | {c.station_panchayats} of {c.n_panchayats} |",
        f"| Panchayats with at least one report | {c.reported_panchayats} of {c.n_panchayats} |",
        f"| ... of which have no station | {c.reported_without_station} |",
        f"| Panchayats with any ground check (stations, plus reports) | {c.station_panchayats} -> {covered} "
        f"of {c.n_panchayats} |",
        "",
        "## What this shows",
        "",
        f"Stations give a ground check in {c.station_panchayats} of {c.n_panchayats} Panchayats. This "
        f"month's reports add {c.reported_without_station} Panchayats without a station. Reports can be",
        "wrong, so the check against station or synthetic truth comes first: it says how far a report",
        "can be trusted before it is used to judge a forecast. With real reports the truth would be the",
        "station network only, and reports from Panchayats without a station would stay unchecked.",
        "",
        "Next step, not done here: the verification job could score rain occurrence at report points,",
        "weighted by this agreement rate, to see the forecast where no station exists.",
        "",
        "## Per Panchayat",
        "",
        "| Panchayat | Block | Station | Reports | Checked | Rain agrees | Intensity agrees | Truth source |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p in c.per_panchayat.sort_values(["block_id", "panchayat_id"]).itertuples(index=False):
        station = "yes" if p.has_station else "no"
        lines.append(f"| {p.panchayat_id} | {p.block_id} | {station} | {p.reports} | {p.checked} | "
                     f"{int(p.rain_agrees)} | {int(p.intensity_agrees)} | {p.truth_source} |")
    lines += ["", f"Few reports per Panchayat in a month ({len(r)} in {c.reported_panchayats} Panchayats): "
              "per-Panchayat agreement rates would be noise, so the table shows counts only.", ""]
    return "\n".join(lines)


def main() -> None:
    """Write the monthly feedback report."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--month", default=DEFAULT_MONTH, help="YYYY-MM, a TRAIN or CALIB month")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--no-store", action="store_true", help="leave out reports stored by the API")
    a = ap.parse_args()
    c = check_month(a.month, None if a.no_store else Store())
    a.out.write_text(render(c, date.today()), encoding="utf-8")
    ok = c.rows["rain_agrees"].notna()
    print(f"{c.month}: {len(c.rows)} reports, {int(ok.sum())} checked, rain agrees "
          f"{_pct(c.rows['rain_agrees'].sum(), ok.sum())}; Panchayats with a ground check "
          f"{c.station_panchayats} -> {c.station_panchayats + c.reported_without_station} "
          f"of {c.n_panchayats}")
    print(f"written {a.out}")


if __name__ == "__main__":
    main()
