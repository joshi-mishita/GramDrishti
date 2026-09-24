"""Pick the demo issue dates served by ``/meta`` and print why each one was chosen.

Selection reads only the issued block forecast (plain mean of the NWP sources, baseline B0). It never
reads observations or the synthetic oracle, so choosing dates inside the TEST window does not look at
TEST outcomes. Six dates come from TEST; two are labelled training-period replays.

Run: ``cd backend && python -m gramdrishti.contract.pick_demo_dates`` (writes ``demo_dates.json``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from gramdrishti.data import loaders
from gramdrishti.data.config import COLS, WINDOWS, window_bounds
from gramdrishti.models.bias import combine_sources

OUT = Path(__file__).with_name("demo_dates.json")
LAST_TEST_ISSUE = "2024-12-26"   # every lead 1-5 still falls inside the data


@dataclass
class DemoDate:
    """One demo issue date and the reason it was picked."""

    date: str
    label: str
    split: str
    category: str
    reason: str


def split_of(date: str | pd.Timestamp) -> str:
    """Name of the window (train, calib, test) that contains ``date``, or "outside"."""
    d = pd.Timestamp(date)
    for name in WINDOWS:
        start, end = window_bounds(name)
        if start <= d <= end:
            return name.lower()
    return "outside"


def issued_summary(fc: pd.DataFrame) -> pd.DataFrame:
    """Per issue date: district statistics of the issued block forecast (B0) used for scoring."""
    b0 = combine_sources(fc)
    r, tx, tn, rh, wd = (COLS[v] for v in ("rain", "tmax", "tmin", "rh", "wind"))
    lead1 = b0[b0["lead_day"] == 1].groupby("issue_date").agg(
        rain1_max=(r, "max"), rain1_std=(r, "std"), rain1_mean=(r, "mean"),
        tmax1=(tx, "mean"), tmin1=(tn, "mean"), rh1=(rh, "mean"), wind1=(wd, "mean"))
    by_block = b0.groupby(["issue_date", "block_id"])[r].sum()
    five = by_block.groupby("issue_date").agg(rain5_total=("mean"), rain5_block_max=("max"))
    n_leads = b0.groupby("issue_date")["lead_day"].nunique().rename("n_leads")
    out = lead1.join(five).join(n_leads).reset_index()
    return out[out["n_leads"] == 5]


def _between(s: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    d = s["issue_date"]
    return s[(d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))]


def _z(x: pd.Series) -> pd.Series:
    return (x - x.mean()) / (x.std() or 1.0)


def pick(summary: pd.DataFrame) -> list[DemoDate]:
    """Choose eight dates, one per situation, never the same date twice."""
    taken: set[pd.Timestamp] = set()

    def best(frame: pd.DataFrame, score: pd.Series, largest: bool = True) -> pd.Series:
        f = frame.assign(score=score).loc[~frame["issue_date"].isin(taken)]
        row = f.sort_values(["score", "issue_date"], ascending=[not largest, True]).iloc[0]
        taken.add(row["issue_date"])
        return row

    def iso(row: pd.Series) -> str:
        return row["issue_date"].strftime("%Y-%m-%d")

    test_end = LAST_TEST_ISSUE
    monsoon = _between(summary, WINDOWS["TEST"][0], "2024-09-30")
    picks: list[DemoDate] = []

    r = best(monsoon, monsoon["rain1_max"])
    picks.append(DemoDate(iso(r), "Heavy monsoon rain", "test", "heavy_rain",
                          f"Wettest block forecast for tomorrow in the TEST monsoon: {r.rain1_max:.1f} mm "
                          f"(district mean {r.rain1_mean:.1f} mm)."))

    r = best(monsoon, monsoon["rain1_std"])
    picks.append(DemoDate(iso(r), "Patchy rain, blocks disagree", "test", "patchy_rain",
                          f"Largest spread of tomorrow's rain between blocks: standard deviation "
                          f"{r.rain1_std:.1f} mm across 6 blocks."))

    r = best(monsoon, monsoon["rain5_block_max"], largest=False)
    picks.append(DemoDate(iso(r), "Monsoon break, dry days ahead", "test", "dry_spell",
                          f"Driest 5-day outlook in the TEST monsoon: at most {r.rain5_block_max:.1f} mm "
                          "in any block over leads 1-5."))

    octo = _between(summary, "2024-10-01", "2024-10-31")
    r = best(octo, octo["tmax1"])
    picks.append(DemoDate(iso(r), "Hot post-monsoon day", "test", "heat",
                          f"Highest district-mean Tmax forecast for tomorrow in October: {r.tmax1:.1f} C."))

    dec = _between(summary, "2024-12-01", test_end)
    fog = _z(dec["rh1"]) - _z(dec["tmin1"]) - _z(dec["wind1"])
    r = best(dec, fog)
    picks.append(DemoDate(iso(r), "Cold, calm December morning (fog-prone)", "test", "cold_fog",
                          f"Highest cold, humid and calm score in December: Tmin {r.tmin1:.1f} C, "
                          f"RH {r.rh1:.0f} %, wind {r.wind1:.1f} km/h. No fog variable exists, so "
                          "this is a proxy for a fog-prone morning."))

    nov = _between(summary, "2024-11-01", "2024-11-30")
    cols = ["rain5_total", "tmax1", "tmin1", "rh1", "wind1"]
    typical = sum((_z(nov[c])).abs() for c in cols)
    r = best(nov, typical, largest=False)
    picks.append(DemoDate(iso(r), "Ordinary day", "test", "ordinary",
                          f"Closest to a typical November day on rain, Tmax, Tmin, RH and wind "
                          f"(sum of |z| = {typical.loc[r.name]:.2f})."))

    mar = _between(summary, "2024-03-01", "2024-03-31")
    r = best(mar, mar["tmax1"])
    picks.append(DemoDate(iso(r), "Training-period replay: March wheat heat", "train", "heat_replay",
                          f"Hottest March 2024 forecast for tomorrow ({r.tmax1:.1f} C) near the end of wheat "
                          "grain fill (placeholder crop calendar). Inside TRAIN: shown as a replay, not "
                          "as a held-out result."))

    jan = _between(summary, "2024-01-01", "2024-01-31")
    r = best(jan, jan["tmin1"], largest=False)
    picks.append(DemoDate(iso(r), "Training-period replay: January cold night", "train", "cold_replay",
                          f"Coldest January 2024 night forecast ({r.tmin1:.1f} C district mean), a frost "
                          "check. Inside TRAIN: shown as a replay, not as a held-out result."))

    for p in picks:
        assert split_of(p.date) == p.split, (p.date, p.split)
    return sorted(picks, key=lambda p: p.date)


def load_demo_dates(path: Path = OUT) -> list[DemoDate]:
    """Read the committed demo dates."""
    return [DemoDate(**d) for d in json.loads(path.read_text())]


def main() -> None:
    """Pick the dates, print the reasons and write ``demo_dates.json``."""
    picks = pick(issued_summary(loaders.load_fc()))
    for p in picks:
        print(f"{p.date}  [{p.split:5}]  {p.label}\n    {p.reason}")
    OUT.write_text(json.dumps([asdict(p) for p in picks], indent=2) + "\n")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
