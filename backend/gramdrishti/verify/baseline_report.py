"""Baseline report: MAE, RMSE and bias of B0, B1, B2 against Panchayat truth on the CALIB window.

Fitting uses TRAIN only. Evaluation uses CALIB only. TEST stays closed.
Run: ``cd backend && python -m gramdrishti.verify.baseline_report``
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import pandas as pd

from gramdrishti.data import loaders
from gramdrishti.data.config import COLS, LEADS, RAIN_EVENT_MM, RAIN_WET_MM, WINDOWS, data_mode, select_window
from gramdrishti.data.qc import clean_values, run_qc
from gramdrishti.models.baselines import Baselines, fit_baselines
from gramdrishti.models.bias import apply_bias, block_reference, combine_sources
from gramdrishti.verify.metrics import continuous_scores, event_scores

EVAL_WINDOW = "CALIB"
FIT_WINDOW = "TRAIN"
NAMES = ["B0", "B1", "B2"]


@dataclass
class BaselineReport:
    """Everything the report prints, as DataFrames."""

    baselines: Baselines
    scores: pd.DataFrame        # baseline, var, lead_day, n, mae, rmse, bias
    events: pd.DataFrame        # baseline, lead_day, n, hits, misses, false_alarms, pod, far, csi
    block_check: pd.DataFrame   # var, bias_raw, bias_corrected (block level, all leads)
    wet_freq: pd.DataFrame      # lead_day, forecast_raw, forecast_corrected, reference
    n_eval_dates: int


def build_report() -> BaselineReport:
    """Fit baselines on TRAIN and score them against Panchayat truth on CALIB."""
    if data_mode() != "mock":
        raise NotImplementedError(
            "baseline_report scores against Panchayat truth, which exists only in mock mode. "
            "Real-mode verification against stations (leave-one-station-out) comes with the verification job."
        )
    fc, static, stations = loaders.load_fc(), loaders.load_static(), loaders.load_stations()
    obs_clean = clean_values(run_qc(loaders.load_obs()))
    ref = block_reference(obs_clean, stations)
    baselines = fit_baselines(fc, ref, obs_clean, stations, static, FIT_WINDOW)

    fc_eval = select_window(fc, EVAL_WINDOW, "valid_date")
    truth = select_window(loaders.load_truth(), EVAL_WINDOW, "date")  # MOCK ONLY: evaluation target
    preds = baselines.predict(fc_eval)
    scores, events = _score(preds, truth)
    block_check, wet = _block_checks(fc_eval, select_window(ref, EVAL_WINDOW, "date"), baselines)
    return BaselineReport(baselines, scores, events, block_check, wet, int(truth["date"].nunique()))


def _score(preds: dict[str, pd.DataFrame], truth: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    t = truth[["date", "panchayat_id", *COLS.values()]].rename(columns={"date": "valid_date"})
    rows, ev = [], []
    for name in NAMES:
        m = preds[name].merge(t, on=["panchayat_id", "valid_date"], suffixes=("", "_obs"))
        for lead in LEADS:
            d = m[m["lead_day"] == lead]
            for var, col in COLS.items():
                rows.append({"baseline": name, "var": var, "lead_day": lead,
                             **continuous_scores(d[col].to_numpy(), d[f"{col}_obs"].to_numpy())})
            rain = COLS["rain"]
            ev.append({"baseline": name, "lead_day": lead,
                       **event_scores(d[rain].to_numpy(), d[f"{rain}_obs"].to_numpy(), RAIN_EVENT_MM)})
    return pd.DataFrame(rows), pd.DataFrame(ev)


def _block_checks(fc_eval: pd.DataFrame, ref_eval: pd.DataFrame,
                  baselines: Baselines) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Guide 5.1 check: block-level mean bias before and after correction, and wet-day frequency."""
    raw = combine_sources(fc_eval)
    cor = combine_sources(apply_bias(fc_eval, baselines.bias), baselines.bias.weights)
    r = ref_eval.rename(columns={"date": "valid_date"})
    rows = []
    on = ["valid_date", "block_id"]
    for var, col in COLS.items():
        mr = raw.merge(r[[*on, col]], on=on, suffixes=("", "_ref"))
        mc = cor.merge(r[[*on, col]], on=on, suffixes=("", "_ref"))
        rows.append({"var": var, "bias_raw_B0": (mr[col] - mr[f"{col}_ref"]).mean(),
                     "bias_corrected_B1": (mc[col] - mc[f"{col}_ref"]).mean()})
    rain = COLS["rain"]
    wet = []
    for lead in LEADS:
        mr = raw[raw["lead_day"] == lead].merge(r[["valid_date", "block_id", rain]],
                                               on=["valid_date", "block_id"], suffixes=("", "_ref"))
        mc = cor[cor["lead_day"] == lead]
        wet.append({"lead_day": lead, "forecast_raw_B0": (mr[rain] >= RAIN_WET_MM).mean(),
                    "forecast_corrected_B1": (mc[rain] >= RAIN_WET_MM).mean(),
                    "reference": (mr[f"{rain}_ref"] >= RAIN_WET_MM).mean()})
    return pd.DataFrame(rows), pd.DataFrame(wet)


def _fmt(x: float | None, nd: int = 2) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{x:.{nd}f}"


def format_report(rep: BaselineReport) -> str:
    """Plain-text report with fixed-width tables."""
    b = rep.baselines
    lines = [
        "GramDrishti baseline report",
        f"data_mode: {data_mode()}  (synthetic proxy validation, not real weather)",
        f"fit window: {FIT_WINDOW} {WINDOWS[FIT_WINDOW][0]}..{WINDOWS[FIT_WINDOW][1]}; latest date read when "
        f"fitting: bias {b.bias.data_max_date.date()}, station offsets {b.offsets.data_max_date.date()}",
        f"evaluation window: {EVAL_WINDOW} {WINDOWS[EVAL_WINDOW][0]}..{WINDOWS[EVAL_WINDOW][1]} "
        f"({rep.n_eval_dates} valid dates); TEST not opened",
        "",
        "Panchayat-level scores (prediction minus truth). Units: rain mm, tmax/tmin C, rh %, wind km/h.",
    ]
    hdr = f"{'var':<5} {'lead':>4} {'n':>6} | {'MAE B0':>7} {'B1':>7} {'B2':>7} | " \
          f"{'RMSE B0':>7} {'B1':>7} {'B2':>7} | {'bias B0':>7} {'B1':>7} {'B2':>7}"
    lines += [hdr, "-" * len(hdr)]
    s = rep.scores.set_index(["var", "lead_day", "baseline"])
    for var in COLS:
        for lead in LEADS:
            r = {n: s.loc[(var, lead, n)] for n in NAMES}
            cells = [f"{var:<5} {lead:>4} {int(r['B0']['n']):>6} |"]
            for metric in ("mae", "rmse", "bias"):
                cells.append(" ".join(f"{_fmt(r[n][metric]):>7}" for n in NAMES) + " |")
            lines.append(" ".join(cells).rstrip(" |"))
    lines += ["", f"Rain events at >= {RAIN_EVENT_MM} mm (Panchayat level)"]
    hdr = (f"{'baseline':<8} {'lead':>4} {'hits':>6} {'misses':>6} {'f.alarm':>7} | "
           f"{'POD':>5} {'FAR':>5} {'CSI':>5}")
    lines += [hdr, "-" * len(hdr)]
    for _, r in rep.events.sort_values(["baseline", "lead_day"]).iterrows():
        lines.append(f"{r['baseline']:<8} {r['lead_day']:>4} {r['hits']:>6} {r['misses']:>6} "
                     f"{r['false_alarms']:>7} | {_fmt(r['pod']):>5} {_fmt(r['far']):>5} {_fmt(r['csi']):>5}")
    lines += ["", "Block-level mean bias on the evaluation window, all leads (forecast minus block truth)"]
    hdr = f"{'var':<5} {'raw (B0)':>9} {'corrected (B1)':>15}"
    lines += [hdr, "-" * len(hdr)]
    for _, r in rep.block_check.iterrows():
        lines.append(f"{r['var']:<5} {_fmt(r['bias_raw_B0'], 3):>9} {_fmt(r['bias_corrected_B1'], 3):>15}")
    lines += ["", f"Block-level wet-day frequency (rain >= {RAIN_WET_MM} mm)"]
    hdr = f"{'lead':>4} {'raw (B0)':>9} {'corrected (B1)':>15} {'block truth':>12}"
    lines += [hdr, "-" * len(hdr)]
    for _, r in rep.wet_freq.iterrows():
        lines.append(f"{int(r['lead_day']):>4} {_fmt(r['forecast_raw_B0'], 3):>9} "
                     f"{_fmt(r['forecast_corrected_B1'], 3):>15} {_fmt(r['reference'], 3):>12}")
    return "\n".join(lines)


def main() -> int:
    """Build and print the baseline report."""
    print(format_report(build_report()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
