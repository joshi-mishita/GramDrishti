"""Decision replay (Backend Guide 11.3): would the Panchayat forecast have given better advice than the block
forecast, day by day and Panchayat by Panchayat, over the evaluation window?

Each decision is made on the issue date for the next day (lead day 1) in every Panchayat:

| decision | model acts when | block acts when | event (from truth) |
|---|---|---|---|
| spray | P(rain >= 2.5 mm) >= 0.3 (hold spraying) | block rain >= 2.5 mm | rain >= 2.5 mm |
| heat_alert | p90 Tmax >= 35 C (alert) | block Tmax >= 35 C | Tmax >= 35 C |
| irrigation_wait | P(rain >= 5 mm) >= 0.5, i.e. p50 >= 5 mm (wait) | block rain >= 5 mm | rain >= 5 mm |

"Acting" is the protective choice (hold spraying, warn, wait). Outcomes: ``correct`` = acted and the event
came, or did not act and it stayed away; ``wasted_wait`` = acted but the event did not come (a false
alarm); ``washed_off`` = did not act and the event came (a miss). Counts and rates only; no money values
until an expert supplies costs. The block rule is run on B0 (the plain block forecast, ``block_baseline``)
and on B1 (the corrected block forecast, ``block_corrected``).

35 C is the placeholder paddy heat alert from the crop calendar, the lowest heat alert of a crop in season
from July to December (the generic 40 C was reached on 0.4 % of TRAIN July-December Panchayat-days).
It was fixed before TEST was opened (docs/validation_protocol.md).

Run on its own (reads ``artifacts/verification_predictions.parquet``):
``cd backend && python -m gramdrishti.verify.impact``
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from gramdrishti.data.config import ART, WINDOWS, data_mode

LEAD = 1
SEASONS = {"monsoon_2024": ("2024-07-16", "2024-09-30"),
           "post_monsoon_2024": ("2024-10-01", "2024-11-30"),
           "winter_2024": ("2024-12-01", "2024-12-31"),
           "test_2024": WINDOWS["TEST"]}


@dataclass(frozen=True)
class DecisionRule:
    """One replayed decision: columns and thresholds for the model, the block forecast and the outcome."""

    name: str
    var: str
    threshold: float
    unit: str
    model_col: str
    model_cut: float
    block_prefix: str   # "b0" or "b1" is prepended to f"_{var}"
    model_text: str
    block_text: str


RULES = {
    "spray": DecisionRule("spray", "rain", 2.5, "mm", "prob_rain_ge_2_5", 0.3, "rain",
                          "Advise spraying tomorrow when the chance of 2.5 mm rain or more is under 30%.",
                          "Advise spraying tomorrow when the block forecast is under 2.5 mm."),
    "heat_alert": DecisionRule("heat_alert", "tmax", 35.0, "C", "tmax_p90", 35.0, "tmax",
                               "Alert when the upper estimate (p90) of tomorrow's maximum is 35 C or more.",
                               "Alert when the block forecast of tomorrow's maximum is 35 C or more."),
    "irrigation_wait": DecisionRule("irrigation_wait", "rain", 5.0, "mm", "rain_p50", 5.0, "rain",
                                    "Wait to irrigate when the chance of 5 mm rain or more tomorrow is 50% "
                                    "or more (the median forecast is 5 mm or more).",
                                    "Wait to irrigate when the block forecast for tomorrow is 5 mm or more."),
}


def counts(act: np.ndarray, event: np.ndarray) -> dict[str, int]:
    """correct / wasted_wait / washed_off from boolean arrays of 'acted' and 'event happened'."""
    act, event = np.asarray(act, dtype=bool), np.asarray(event, dtype=bool)
    return {"correct": int((act == event).sum()), "wasted_wait": int((act & ~event).sum()),
            "washed_off": int((~act & event).sum())}


def replay(pred: pd.DataFrame, rule: DecisionRule) -> dict:
    """Counts for one decision over the rows of ``pred`` (lead day 1, observed value present)."""
    d = pred[(pred["lead_day"] == LEAD) & pred[f"obs_{rule.var}"].notna()]
    event = d[f"obs_{rule.var}"].to_numpy(dtype=float) >= rule.threshold
    model_act = d[rule.model_col].to_numpy(dtype=float) >= rule.model_cut
    out = {"model": counts(model_act, event), "n_decisions": int(len(d)), "events_observed": int(event.sum())}
    for key, b in (("block_baseline", "b0"), ("block_corrected", "b1")):
        out[key] = counts(d[f"{b}_{rule.var}"].to_numpy(dtype=float) >= rule.threshold, event)
    return out


def replay_all(pred: pd.DataFrame, mode: str, notes: list[str],
               seasons: dict[str, tuple[str, str]] | None = None) -> dict:
    """Every season x decision as ``Impact`` payloads (plain dicts), keyed ``<season>/<decision>``."""
    seasons = SEASONS if seasons is None else seasons
    items = {}
    for season, (start, end) in seasons.items():
        sub = pred[(pred["valid_date"] >= start) & (pred["valid_date"] <= end)]
        if sub.empty:
            continue
        for rule in RULES.values():
            r = replay(sub, rule)
            items[f"{season}/{rule.name}"] = {
                "season": season, "decision": rule.name, "data_mode": mode, "provenance": "computed",
                **r, "rule": {"model": {"en": rule.model_text}, "block": {"en": rule.block_text}},
                "period": {"start": str(sub["valid_date"].min().date()),
                           "end": str(sub["valid_date"].max().date())},
                "lead_day": LEAD, "threshold": rule.threshold, "unit": rule.unit,
                "notes": [*notes,
                          "Decisions for the next day (lead day 1) in every Panchayat, one per issue date.",
                          "correct = acted and the event came, or did not act and it stayed away; "
                          "wasted_wait = acted (held spraying, alerted, waited) but the event did not come; "
                          "washed_off = did not act and the event came.",
                          "block_baseline uses the raw block forecast B0; block_corrected uses the corrected "
                          "block forecast B1.",
                          "Counts and rates only. No money values until an expert supplies costs.",
                          "Thresholds are placeholders awaiting expert review."]}
    return {"data_mode": mode, "seasons": {k: list(v) for k, v in seasons.items()}, "items": items}


def main(argv: list[str] | None = None) -> int:
    """Replay the decisions from the saved scored predictions and write ``impact.json``."""
    art = Path(argv[0]) if argv else ART
    pred = pd.read_parquet(art / "verification_predictions.parquet")
    notes = json.loads((art / "verification.json").read_text())["summary"]["notes"][:2]
    res = replay_all(pred, data_mode(), notes)
    (art / "impact.json").write_text(json.dumps(res, indent=1) + "\n")
    for key, it in res["items"].items():
        n = it["n_decisions"]
        sides = ("model", "block_baseline", "block_corrected")
        cells = "  ".join(f"{x}: correct {it[x]['correct'] / n:.1%} wasted {it[x]['wasted_wait']} "
                          f"washed {it[x]['washed_off']}" for x in sides)
        print(f"{key:<32} n={n:<6} events={it['events_observed']:<5} {cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
