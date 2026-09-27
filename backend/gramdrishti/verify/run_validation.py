"""Verification job (Backend Guide 11): does the Panchayat forecast beat the block forecast?

Checks, all scored against the frozen model bundle in ``backend/artifacts/``:
- temporal holdout: the production model (fitted on TRAIN, calibrated on CALIB) forecasts every issue date
  of the evaluation window (TEST); scored against synthetic Panchayat truth;
- leave-one-block-out: the mean models are refitted on TRAIN six times, each time without one block, and
  forecast that block over the evaluation window (unseen place and unseen time);
- station check: the production forecasts at the 24 Panchayats with a station, scored against the
  QC-cleaned station values (in mock mode these are the synthetic truth plus measurement noise);
- strata of the temporal holdout by lead day, season, observed rain intensity and drainage class.

Baselines: B0 raw block forecast, B1 corrected block forecast (what the model is reconciled to), B2 B1 plus
lapse rate and station offsets. Skill = 1 - score_model / score_baseline with a 95 % moving-block bootstrap
interval (7-day blocks of daily errors). A variable is a win only when the whole interval is above 0.

TEST is opened once per model version (``docs/validation_protocol.md``). The opening is written to
``docs/test_window_ledger.json`` before any TEST truth is read. ``--window CALIB`` is a dry run of the
same code on CALIB (in-sample for the conformal offsets and isotonic maps) that never touches TEST.

Run: ``cd backend && python -m gramdrishti.verify.run_validation [--window CALIB] [--no-lobo]``
Writes ``artifacts/verification.json``, ``artifacts/impact.json`` and the scored predictions
``artifacts/verification_predictions.parquet`` (all git-ignored), then prints the summary table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from gramdrishti.data import loaders
from gramdrishti.data.config import (
    ART,
    COLS,
    FILES,
    LEADS,
    RAIN_EVENTS_MM,
    ROOT,
    SEED,
    VARS,
    WINDOWS,
    data_dir,
    data_mode,
    season_group,
    select_window,
)
from gramdrishti.features.table import (
    TARGETS,
    Inputs,
    event_name,
    load_inputs,
    make_table,
    window_issue_dates,
)
from gramdrishti.models.artifacts import Bundle, load_bundle, table_hash
from gramdrishti.models.baselines import apply_b2, fit_station_offsets, idw_offsets
from gramdrishti.models.bias import block_reference
from gramdrishti.models.downscale import fit_mean_only
from gramdrishti.models.reconcile import max_block_error
from gramdrishti.pipeline.predict import predict_table
from gramdrishti.pipeline.train import Prepared, prepare
from gramdrishti.verify import ledger
from gramdrishti.verify import metrics as mt

UNITS = {"rain": "mm", "tmax": "C", "tmin": "C", "rh": "%", "wind": "km/h"}
BASELINES = ("b0", "b1", "b2")
QUANT = {0.1: "p10", 0.5: "p50", 0.9: "p90"}
WET_MM = 1.0
EVENT_YES_PROB = 0.5
INTENSITY = [("dry_lt_1mm", -np.inf, 1.0), ("light_1_10mm", 1.0, 10.0),
             ("moderate_10_35mm", 10.0, 35.0), ("heavy_ge_35mm", 35.0, np.inf)]
METHOD = "temporal_holdout + leave_one_block_out + station_check"
SYNTHETIC_NOTE = ("Synthetic demo data: every number comes from the mock data generator, not real weather. "
                  "This is proxy validation on synthetic truth, not evidence of real-world skill.")
TRUTH = {"temporal_holdout": "synthetic Panchayat truth (mock data generator)",
         "leave_one_block_out": "synthetic Panchayat truth (mock data generator)",
         "station": "QC-cleaned station values at 24 station Panchayats (mock: synthetic truth plus noise)"}
DESCRIPTION = {
    "temporal_holdout": "Production model fitted on TRAIN, calibrated on CALIB, forecasting every issue date "
                        "of the evaluation window.",
    "leave_one_block_out": "Mean models refitted on TRAIN without one block (6 folds) and forecasting that "
                           "block over the evaluation window. Point forecasts only (no intervals or event "
                           "probabilities).",
    "station": "Production forecasts at the Panchayats that have a station, against the station values. "
               "Rain gauges (ARG) score rain only. B2 leaves the Panchayat's own station out.",
}
OUT_NAMES = {"verification": "verification.json", "impact": "impact.json",
             "predictions": "verification_predictions.parquet"}


# ---------------------------------------------------------------- frozen inputs
def file_hashes() -> dict[str, str]:
    """sha256 of every data file the job reads, so the evaluated data can be shown to be unchanged."""
    keys = ["fc", "obs", "static", "blocks", "stations", "sat", "truth"]
    out = {}
    for k in keys:
        p = data_dir() / FILES[data_mode()][k]
        if p.exists():
            out[FILES[data_mode()][k]] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def code_commit() -> str:
    """Current git commit (with ``-dirty`` when there are uncommitted changes), or ``unknown``."""
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def check_frozen(bundle: Bundle, prep: Prepared) -> str:
    """Recompute the model's data hash from the TRAIN and CALIB tables and refuse to go on if it differs
    from the bundle's (the model would not be the frozen version). Returns the hash."""
    h = table_hash(prep.train[[*prep.features, *[f"y_{t}" for t in TARGETS]]],
                   prep.calib[[*prep.features, *[f"obs_{v}" for v in VARS]]])
    if h != bundle.config["data_hash_sha256"]:
        raise RuntimeError(f"data hash {h[:10]} does not match bundle {bundle.config['model_version']}; "
                           "retrain or restore the frozen artifacts before verification.")
    return h


# ---------------------------------------------------------------- predictions
def _truth(window: str) -> pd.DataFrame:
    if data_mode() != "mock":
        raise NotImplementedError("Verification against Panchayat truth exists only in mock mode. Real mode "
                                  "needs leave-one-station-out against real stations (Guide 14.4).")
    # MOCK ONLY: the synthetic truth is the answer key, never a feature.
    t = select_window(loaders.load_truth(), window, "date", allow_test=window == "TEST")
    return t.rename(columns={"date": "valid_date", **{c: f"obs_{v}" for v, c in COLS.items()}})[
        ["valid_date", "panchayat_id", *[f"obs_{v}" for v in VARS]]]


def _stations(inputs: Inputs, window: str) -> pd.DataFrame:
    o = select_window(inputs.obs_clean, window, "date", allow_test=window == "TEST")
    o = o.merge(inputs.stations[["station_id", "station_type", "panchayat_id"]], on="station_id")
    return o.rename(columns={"date": "valid_date", **{c: f"stn_{v}" for v, c in COLS.items()}})[
        ["valid_date", "panchayat_id", "station_id", "station_type", *[f"stn_{v}" for v in VARS]]]


def add_b2(pred: pd.DataFrame, inputs: Inputs) -> pd.DataFrame:
    """B2 = the pipeline's B1 plus lapse rate and IDW station offsets fitted on TRAIN (own station out)."""
    ref = block_reference(inputs.obs_clean, inputs.stations)
    off = fit_station_offsets(inputs.obs_clean, inputs.stations, inputs.static, ref, "TRAIN")
    idw = idw_offsets(off, inputs.stations, inputs.static)
    b1 = pred[["panchayat_id", "block_id", "valid_date"]].copy()
    for v in VARS:
        b1[COLS[v]] = pred[f"b1_{v}"].to_numpy()
    b2 = apply_b2(b1, idw, inputs.static)
    out = pred.copy()
    for v in VARS:
        out[f"b2_{v}"] = b2[COLS[v]].to_numpy()
    return out


def evaluation_issue_dates(inputs: Inputs, window: str) -> pd.DatetimeIndex:
    """Issue dates whose five lead days all fall inside the window (same purge as TRAIN and CALIB)."""
    return window_issue_dates(inputs.fc, window, allow_test=window == "TEST")


def predict_window(bundle: Bundle, inputs: Inputs, window: str,
                   issue_dates: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Production forecasts for the issue dates with B0, B1, B2, truth and station values attached.
    Returns (scored frame, feature table)."""
    table = make_table("infer", inputs, bundle.bias, bundle.encodings, issue_dates=issue_dates)
    pred = add_b2(predict_table(bundle.models, table, bundle.offsets), inputs)
    pred = pred.merge(_truth(window), on=["valid_date", "panchayat_id"], how="left", validate="many_to_one")
    pred = pred.merge(_stations(inputs, window), on=["valid_date", "panchayat_id"], how="left",
                      validate="many_to_one")
    pred = pred.merge(inputs.static[["panchayat_id", "drainage_class"]], on="panchayat_id", how="left")
    pred["season"] = season_group(pred["valid_date"]).to_numpy()
    return pred, table


def lobo_predictions(prep: Prepared, table: pd.DataFrame, params: dict,
                     log: Callable[[str], None] = print) -> pd.DataFrame:
    """Leave-one-block-out: mean models fitted on TRAIN without the block, forecasting it on ``table``."""
    parts = []
    for block in sorted(table["block_id"].unique()):
        t0 = time.time()
        m = fit_mean_only(prep.train[prep.train["block_id"] != block], prep.features, params)
        parts.append(predict_table(m, table[table["block_id"] == block], events=False))
        log(f"  leave out {block}: {time.time() - t0:.0f} s")
    return pd.concat(parts).loc[table.index]


# ---------------------------------------------------------------- scoring helpers
def _losses(kind: str, f: np.ndarray, y: np.ndarray, quantiles: dict[float, np.ndarray] | None = None):
    if kind == "MAE":
        return np.abs(f - y)
    if kind == "RMSE":
        return (f - y) ** 2
    if kind == "bias":
        return f - y
    if kind == "quantile_loss":
        return mt.quantile_loss_rows(quantiles or dict.fromkeys(QUANT, f), y)
    raise ValueError(kind)


def _agg(kind: str, loss: np.ndarray) -> float | None:
    if not len(loss):
        return None
    return float(np.sqrt(loss.mean())) if kind == "RMSE" else float(loss.mean())


def score_metric(d: pd.DataFrame, var: str, kind: str, obs_col: str, model_col: str,
                 quantiles: bool, n_boot: int, name: str | None = None) -> dict:
    """One MetricRow: model and baselines, skill against B0 and B1 with bootstrap intervals."""
    d = d[d[obs_col].notna()]
    y = d[obs_col].to_numpy(dtype=float)
    days = d["valid_date"].to_numpy()
    q = {lv: d[f"{var}_{c}"].to_numpy(dtype=float) for lv, c in QUANT.items()} if quantiles else None
    lm = _losses(kind, d[model_col].to_numpy(dtype=float), y, q)
    lb = {b: _losses(kind, d[f"{b}_{var}"].to_numpy(dtype=float), y) for b in BASELINES}
    row = {"name": name or kind, "unit": UNITS[var], "model": _agg(kind, lm),
           **{b: _agg(kind, lb[b]) for b in BASELINES}}
    for b, key in (("b0", ""), ("b1", "_vs_b1")):
        if kind == "bias":
            row[f"skill{key or '_vs_b0'}"], ci = None, None
        else:
            row[f"skill{key or '_vs_b0'}"] = mt.skill(row["model"], row[b])
            _, sm = mt.daily_sums(days, lm)
            _, sb = mt.daily_sums(days, lb[b])
            ci = mt.block_bootstrap_ci(sm, sb, n_boot=n_boot, seed=SEED, squared=kind == "RMSE")
        row["skill_ci95" if b == "b0" else "skill_vs_b1_ci95"] = ci
    row["n"] = int(len(y))
    return row


def variable_summaries(d: pd.DataFrame, obs_prefix: str, quantiles: bool, n_boot: int) -> list[dict]:
    """MAE, RMSE and bias for every variable (plus quantile loss when the forecast has quantiles, and rain
    MAE on observed wet days)."""
    out = []
    for var in VARS:
        obs = f"{obs_prefix}_{var}"
        kinds = ["MAE", "RMSE", "bias"] + (["quantile_loss"] if quantiles else [])
        rows = [score_metric(d, var, k, obs, f"{var}_mean", quantiles, n_boot) for k in kinds]
        if var == "rain":
            wet = d[d[obs] >= WET_MM]
            rows.append(score_metric(wet, var, "MAE", obs, f"{var}_mean", quantiles, n_boot,
                                     name=f"MAE_wet_days_obs_ge_{WET_MM:g}mm"))
        n = rows[0].pop("n")
        for r in rows:
            r.pop("n", None)
        out.append({"var": var, "n": n, "metrics": rows})
    return out


def _strata(d: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
    out = [("lead_day", str(lead), d["lead_day"] == lead) for lead in LEADS]
    out += [("season", s, d["season"] == s) for s in ("monsoon", "post_monsoon", "winter", "pre_monsoon")
            if (d["season"] == s).any()]
    out += [("rain_intensity", name, (d["obs_rain"] >= lo) & (d["obs_rain"] < hi))
            for name, lo, hi in INTENSITY]
    out += [("drainage_class", c, d["drainage_class"] == c)
            for c in sorted(d["drainage_class"].dropna().unique())]
    return out


def strata_rows(d: pd.DataFrame, n_boot: int) -> list[dict]:
    """MAE by stratum for every variable, temporal holdout. Rain intensity is the observed rain that day."""
    rows = []
    for dim, name, mask in _strata(d):
        sub = d[mask]
        for var in VARS:
            r = score_metric(sub, var, "MAE", f"obs_{var}", f"{var}_mean", False, n_boot)
            if r["n"]:
                rows.append({"dimension": dim, "stratum": name, "var": var, "metric": "MAE",
                             "unit": r["unit"],
                             "n": r["n"], "model": r["model"], **{b: r[b] for b in BASELINES},
                             "skill_vs_b0": r["skill_vs_b0"], "skill_ci95": r["skill_ci95"],
                             "skill_vs_b1": r["skill_vs_b1"], "skill_vs_b1_ci95": r["skill_vs_b1_ci95"]})
    return rows


def monthly_climatology(thr: float) -> pd.Series:
    """Event frequency per calendar month over TRAIN synthetic truth (the Brier skill reference)."""
    t = select_window(loaders.load_truth(), "TRAIN", "date")  # MOCK ONLY: TRAIN window, reference only
    return (t[COLS["rain"]] >= thr).groupby(t["date"].dt.month).mean()


def event_summaries(d: pd.DataFrame) -> tuple[list[dict], dict[str, list[dict]]]:
    """Rain events: model probabilities (yes when P >= 0.5) and B0 / B1 yes/no, plus reliability points."""
    events, rel = [], {}
    month = d["valid_date"].dt.month
    y_rain = d["obs_rain"].to_numpy(dtype=float)
    for thr in RAIN_EVENTS_MM:
        ev = event_name(thr)[3:]                      # rain_ge_2_5
        api_ev = f"{ev}mm"
        o = y_rain >= thr
        p = d[f"prob_{ev}"].to_numpy(dtype=float)
        clim = month.map(monthly_climatology(thr)).fillna(0.0).to_numpy(dtype=float)
        c = mt.contingency(o, p >= EVENT_YES_PROB)
        base = []
        for b in ("b0", "b1"):
            yes = d[f"{b}_rain"].to_numpy(dtype=float) >= thr
            cb = mt.contingency(o, yes)
            base.append({"baseline": b, "pod": cb["pod"], "far": cb["far"], "csi": cb["csi"],
                         "frequency_bias": cb["frequency_bias"], "brier": mt.brier(yes.astype(float), o)})
        events.append({"event": api_ev, "pod": c["pod"], "far": c["far"], "csi": c["csi"],
                       "brier": mt.brier(p, o), "brier_skill_vs_climatology": mt.brier_skill(p, o, clim),
                       "n": int(len(o)), "base_rate": float(o.mean()), "frequency_bias": c["frequency_bias"],
                       "yes_rule": f"model says yes when P >= {EVENT_YES_PROB}; B0 and B1 when the block "
                                   f"forecast is >= {thr:g} mm; climatology = TRAIN frequency per month",
                       "baselines": base})
        rel[api_ev] = mt.reliability(p, o)
    return events, rel


def coverage_items(d: pd.DataFrame, nominal: float) -> list[dict]:
    """Empirical coverage and mean width of [p10, p90]: all rows, by lead day, by season, rain on wet days."""
    items = []

    def add(var: str, sub: pd.DataFrame, stratum: str) -> None:
        c = mt.interval_coverage(sub[f"{var}_p10"], sub[f"{var}_p90"], sub[f"obs_{var}"])
        if c["n"]:
            items.append({"var": var, "unit": UNITS[var], "nominal": nominal, "empirical": c["coverage"],
                          "mean_width": c["mean_width"], "n": c["n"], "stratum": stratum})

    for var in VARS:
        add(var, d, "all")
        for lead in LEADS:
            add(var, d[d["lead_day"] == lead], f"lead_day={lead}")
        for s in ("monsoon", "post_monsoon", "winter", "pre_monsoon"):
            add(var, d[d["season"] == s], f"season={s}")
    add("rain", d[d["obs_rain"] >= WET_MM], f"observed_rain>={WET_MM:g}mm")
    return items


def region_items(d: pd.DataFrame, region_type: str, id_col: str, obs_prefix: str) -> list[dict]:
    """MAE of the model and baselines per held-out block or per station."""
    items = []
    for rid, g in d.groupby(id_col, sort=True):
        for var in VARS:
            obs = f"{obs_prefix}_{var}"
            sub = g[g[obs].notna()]
            if sub.empty:
                continue
            y = sub[obs].to_numpy(dtype=float)
            mae = {k: float(np.abs(sub[c].to_numpy(dtype=float) - y).mean())
                   for k, c in (("model", f"{var}_mean"), *((b, f"{b}_{var}") for b in BASELINES))}
            items.append({"region_type": region_type, "region_id": str(rid), "var": var, "metric": "MAE",
                          "unit": UNITS[var], "n": int(len(y)), **mae})
    return items


def verdicts(checks: list[dict], strata: list[dict]) -> list[dict]:
    """Win / tie / loss of MAE skill against B0 and B1 for every check, variable and stratum."""
    out = []
    for c in checks:
        for v in c["variables"]:
            m = next(r for r in v["metrics"] if r["name"] == "MAE")
            for b, sk, ci in (("b0", m["skill_vs_b0"], m["skill_ci95"]),
                              ("b1", m["skill_vs_b1"], m["skill_vs_b1_ci95"])):
                out.append({"check": c["check"], "var": v["var"], "dimension": "all", "stratum": "all",
                            "baseline": b, "metric": "MAE", "skill": sk, "ci95": ci,
                            "result": mt.verdict(ci)})
    for r in strata:
        for b, sk, ci in (("b0", r["skill_vs_b0"], r["skill_ci95"]),
                          ("b1", r["skill_vs_b1"], r["skill_vs_b1_ci95"])):
            out.append({"check": "temporal_holdout", "var": r["var"], "dimension": r["dimension"],
                        "stratum": r["stratum"], "baseline": b, "metric": "MAE", "skill": sk, "ci95": ci,
                        "result": mt.verdict(ci)})
    return out


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:+.1f}%"


def _ci(ci: list[float] | None) -> str:
    return "no interval" if ci is None else f"95% CI {100 * ci[0]:+.1f}% to {100 * ci[1]:+.1f}%"


def loss_notes(vd: list[dict], checks: list[dict], events: list[dict]) -> list[str]:
    """One note per place where the model does not beat B0 or B1 (ties and losses), grouped, plus point
    losses on the other metrics and event scores. Empty only when the model wins everywhere."""
    notes = []
    for check in ("temporal_holdout", "leave_one_block_out", "station"):
        for b in ("b0", "b1"):
            for var in VARS:
                rows = [v for v in vd if v["check"] == check and v["baseline"] == b and v["var"] == var
                        and v["result"] != "win"]
                if not rows:
                    continue
                parts = []
                for v in rows:
                    where = "overall" if v["dimension"] == "all" else f"{v['dimension']} {v['stratum']}"
                    parts.append(f"{where}: {v['result']} ({_pct(v['skill'])}, {_ci(v['ci95'])})")
                notes.append(f"Does NOT beat {b.upper()} on {var} MAE ({check}): " + "; ".join(parts) + ".")
    for c in checks:
        for v in c["variables"]:
            for m in v["metrics"]:
                if m["name"] == "MAE" or m["name"] == "bias":
                    continue
                for b, key in (("b0", "skill_vs_b0"), ("b1", "skill_vs_b1")):
                    if m[key] is not None and m[key] <= 0:
                        notes.append(f"Worse than or equal to {b.upper()} on {v['var']} {m['name']} "
                                     f"({c['check']}): skill {_pct(m[key])}.")
    for e in events:
        if e["brier_skill_vs_climatology"] is not None and e["brier_skill_vs_climatology"] <= 0:
            notes.append(f"{e['event']}: Brier score no better than monthly climatology "
                         f"(skill {_pct(e['brier_skill_vs_climatology'])}).")
        for bl in e["baselines"]:
            if e["csi"] is not None and bl["csi"] is not None and e["csi"] < bl["csi"]:
                notes.append(f"{e['event']}: model yes/no CSI {e['csi']:.3f} is below "
                             f"{bl['baseline'].upper()} ({bl['csi']:.3f}).")
    return notes


# ---------------------------------------------------------------- the job
@dataclass
class Result:
    """Everything the job writes."""

    verification: dict
    impact: dict
    predictions: pd.DataFrame


def validate(bundle: Bundle, inputs: Inputs, prep: Prepared, window: str = "TEST",
             issue_dates: pd.DatetimeIndex | None = None, lobo: bool = True, n_boot: int = mt.BOOT_N,
             opening: ledger.Opening | None = None, frozen: dict | None = None,
             log: Callable[[str], None] = print) -> Result:
    """Run every check on ``window`` and build the verification and impact payloads (plain dicts in the
    contract shapes). Opening TEST must be recorded by the caller first (``ledger.open_test``)."""
    from gramdrishti.verify.impact import replay_all

    if window == "TEST" and opening is None:
        raise PermissionError("Record the TEST opening in the ledger before reading TEST (ledger.open_test).")
    issues = issue_dates if issue_dates is not None else evaluation_issue_dates(inputs, window)
    t0 = time.time()
    pred, table = predict_window(bundle, inputs, window, issues)
    log(f"forecast {len(issues)} issue dates, {len(pred)} rows in {time.time() - t0:.0f} s")
    mode, prov = data_mode(), "computed"
    start, end = pred["valid_date"].min().date(), pred["valid_date"].max().date()

    temporal = {"check": "temporal_holdout", "description": DESCRIPTION["temporal_holdout"],
                "truth": TRUTH["temporal_holdout"], "n": int(pred["obs_tmax"].notna().sum()),
                "variables": variable_summaries(pred, "obs", True, n_boot)}
    checks = [temporal]
    regions = []
    if lobo:
        t0 = time.time()
        lp = lobo_predictions(prep, table, bundle.models.params, log)
        lo = pred[["valid_date", "lead_day", "panchayat_id", "block_id", *[f"obs_{v}" for v in VARS],
                   *[f"{b}_{v}" for b in BASELINES for v in VARS]]].copy()
        for v in VARS:
            lo[f"{v}_mean"] = lp[f"{v}_mean"].to_numpy()
            pred[f"lobo_{v}_mean"] = lp[f"{v}_mean"].to_numpy()
        log(f"leave-one-block-out done in {time.time() - t0:.0f} s")
        checks.append({"check": "leave_one_block_out", "description": DESCRIPTION["leave_one_block_out"],
                       "truth": TRUTH["leave_one_block_out"], "n": int(lo["obs_tmax"].notna().sum()),
                       "variables": variable_summaries(lo, "obs", False, n_boot)})
        regions += region_items(lo, "block", "block_id", "obs")
    st = pred[pred["station_id"].notna()]
    checks.append({"check": "station", "description": DESCRIPTION["station"], "truth": TRUTH["station"],
                   "n": int(st["stn_rain"].notna().sum()),
                   "variables": variable_summaries(st, "stn", True, n_boot)})
    regions += region_items(st, "station", "station_id", "stn")

    strata = strata_rows(pred, n_boot)
    events, rel = event_summaries(pred)
    vd = verdicts(checks, strata)
    nominal = float(bundle.config.get("interval_level", 0.8))

    window_note = (f"Evaluation window {window} {start}..{end}, {len(issues)} issue dates, lead days 1-5, "
                   f"model {bundle.config['model_version']}.")
    if opening is not None:
        first = opening.first_opened_at.isoformat(timespec="seconds")
        window_note += f" TEST first opened {first} for this model version."
        if opening.reused:
            window_note += (" TEST WAS REUSED: it had already been opened for "
                            f"{', '.join(opening.earlier_versions)}, so this is not a clean holdout.")
    else:
        window_note += " DRY RUN: not the TEST window; do not quote these numbers as results."
    method_note = ("Skill = 1 - score_model / score_baseline. 95% intervals from a moving-block bootstrap of "
                   f"daily errors (7-day blocks, {n_boot} resamples, seed {SEED}). Win = whole MAE-skill "
                   "interval above 0; loss = whole interval below 0; tie = interval contains 0. The model "
                   "value is the reconciled mean; intervals are p10..p90 after conformal offsets.")
    baseline_note = ("B0 = raw block forecast (mean of the two NWP sources) copied to every Panchayat; "
                     "B1 = bias-corrected block forecast, which the model is reconciled to, so skill against "
                     "B1 is what the Panchayat model itself adds; B2 = B1 plus lapse rate and station "
                     "offsets.")
    notes = [SYNTHETIC_NOTE, window_note, method_note, baseline_note, *loss_notes(vd, checks, events)]

    summary = {
        "data_mode": mode, "provenance": prov, "method": METHOD,
        "period": {"start": str(start), "end": str(end)},
        "variables": temporal["variables"], "events": events,
        "block_mean_error": {v: max_block_error(pred, v, f"b1_{v}") for v in VARS},
        "notes": notes, "model_version": bundle.config["model_version"], "window": window.lower(),
        "test_first_opened_at": opening.first_opened_at.isoformat(timespec="seconds") if opening else None,
        "test_reused": opening.reused if opening else None,
        "checks": checks, "strata": strata, "verdicts": vd,
    }
    short = [SYNTHETIC_NOTE, window_note]
    verification = {
        "summary": summary,
        "reliability": [{"event": ev, "data_mode": mode, "provenance": prov, "points": pts,
                         "notes": [*short, "Model probabilities from the calibrated classifiers; 10 equal "
                                   f"bins; forecast_prob is the bin centre. {len(pred)} forecasts."]}
                        for ev, pts in rel.items()],
        "coverage": {"data_mode": mode, "provenance": prov, "items": coverage_items(pred, nominal),
                     "notes": [*short, f"Nominal {nominal:.0%} interval [p10, p90]. Report width next to "
                               "coverage: a wide interval covers easily."]},
        "regions": {"data_mode": mode, "provenance": prov,
                    "method": "leave_one_block_out (blocks) + station_check (stations)" if lobo
                    else "station_check", "items": regions,
                    "notes": [*short, "Blocks: MAE of the leave-one-block-out forecast for the held-out "
                              "block. Stations: MAE of the production forecast against the station."]},
        "frozen": frozen or {},
    }
    seasons = None if window == "TEST" else {f"{window.lower()}_dry_run": WINDOWS[window]}
    impact = replay_all(pred, mode, [SYNTHETIC_NOTE, window_note], seasons)
    return Result(verification, impact, pred)


def _json_default(x: object) -> object:
    if isinstance(x, (np.floating, np.integer)):
        return x.item()
    if isinstance(x, (pd.Timestamp, datetime)):
        return x.isoformat()
    raise TypeError(type(x))


def _finite(x: object) -> object:
    """Round floats to 6 significant digits and turn NaN or infinity into None (JSON hygiene)."""
    if isinstance(x, float):
        return None if not np.isfinite(x) else float(f"{x:.6g}")
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_finite(v) for v in x]
    return x


def write(res: Result, out: Path) -> list[Path]:
    """Write verification.json, impact.json and the scored predictions."""
    out.mkdir(parents=True, exist_ok=True)
    paths = [out / OUT_NAMES[k] for k in ("verification", "impact", "predictions")]
    for p, payload in zip(paths[:2], (res.verification, res.impact), strict=True):
        clean = _finite(json.loads(json.dumps(payload, default=_json_default)))
        p.write_text(json.dumps(clean, indent=1) + "\n")
    res.predictions.to_parquet(paths[2], index=False)
    return paths


# ---------------------------------------------------------------- printing
def summary_table(v: dict) -> str:
    """Plain-text table: MAE and RMSE per variable and check, skill vs B0 and B1 with intervals, verdict."""
    s = v["summary"]
    lines = [f"GramDrishti verification ({s['data_mode']} data, synthetic proxy validation)",
             f"model {s['model_version']}  window {s['window']} {s['period']['start']}..{s['period']['end']}",
             ""]
    hdr = (f"{'check':<20} {'var':<5} {'metric':<14} {'model':>8} {'B0':>8} {'B1':>8} {'B2':>8} | "
           f"{'skill vs B0 [95% CI]':>27} | {'skill vs B1 [95% CI]':>27} | verdict B0/B1")
    lines += [hdr, "-" * len(hdr)]

    def f(x: float | None) -> str:
        return "n/a" if x is None else f"{x:.3f}"

    def sk(x: float | None, ci: list[float] | None) -> str:
        if x is None:
            return ""
        return f"{100 * x:+6.1f}% [{100 * ci[0]:+6.1f},{100 * ci[1]:+6.1f}]" if ci else f"{100 * x:+6.1f}%"

    for c in s["checks"]:
        for var in c["variables"]:
            for m in var["metrics"]:
                if m["name"] == "bias":
                    continue
                verd = ""
                if m["name"] == "MAE":
                    verd = "/".join(mt.verdict(m[k]) for k in ("skill_ci95", "skill_vs_b1_ci95"))
                lines.append(f"{c['check']:<20} {var['var']:<5} {m['name'][:14]:<14} {f(m['model']):>8} "
                             f"{f(m['b0']):>8} {f(m['b1']):>8} {f(m['b2']):>8} | "
                             f"{sk(m['skill_vs_b0'], m['skill_ci95']):>27} | "
                             f"{sk(m['skill_vs_b1'], m['skill_vs_b1_ci95']):>27} | {verd}")
    lines += ["", f"{'event':<14} {'base':>6} {'POD':>6} {'FAR':>6} {'CSI':>6} {'fbias':>6} {'Brier':>7} "
                  f"{'BSS clim':>8} | {'B0 CSI':>6} {'B1 CSI':>6}"]
    for e in s["events"]:
        b = {x["baseline"]: x for x in e["baselines"]}
        lines.append(f"{e['event']:<14} {f(e['base_rate']):>6} {f(e['pod']):>6} {f(e['far']):>6} "
                     f"{f(e['csi']):>6} {f(e['frequency_bias']):>6} {f(e['brier']):>7} "
                     f"{f(e['brier_skill_vs_climatology']):>8} | {f(b['b0']['csi']):>6} "
                     f"{f(b['b1']['csi']):>6}")
    lines += ["", "80% interval coverage (all rows): " + ", ".join(
        f"{i['var']} {i['empirical']:.3f} (width {i['mean_width']:.2f} {i['unit']})"
        for i in v["coverage"]["items"] if i["stratum"] == "all")]
    lines.append("block-mean error (max |block mean of Panchayat means - B1|): " +
                 ", ".join(f"{k} {x:.1e}" for k, x in s["block_mean_error"].items()))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--window", choices=["TEST", "CALIB"], default="TEST",
                    help="TEST (the verification run, recorded in the ledger) or CALIB (dry run)")
    ap.add_argument("--artifacts", type=Path, default=ART, help="frozen model bundle")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default artifacts, or "
                    "artifacts/dryrun_calib for CALIB)")
    ap.add_argument("--no-lobo", action="store_true", help="skip leave-one-block-out (quick runs)")
    ap.add_argument("--n-boot", type=int, default=mt.BOOT_N)
    args = ap.parse_args(argv)
    out = args.out or (ART if args.window == "TEST" else ART / "dryrun_calib")

    bundle = load_bundle(args.artifacts)
    inputs = load_inputs()
    t0 = time.time()
    prep = prepare(inputs)
    data_hash = check_frozen(bundle, prep)
    frozen = {"model_version": bundle.config["model_version"], "data_hash_sha256": data_hash,
              "data_files_sha256": file_hashes(), "code_commit": code_commit(),
              "library_versions": bundle.config.get("versions", {})}
    print(f"frozen model {frozen['model_version']} hash verified ({time.time() - t0:.0f} s); "
          f"code {frozen['code_commit']}")
    opening = None
    if args.window == "TEST":
        opening = ledger.open_test(frozen["model_version"], data_hash, frozen["code_commit"], datetime.now())
        print(f"TEST window opened (first opened {opening.first_opened_at.isoformat(timespec='seconds')}"
              f"{', REUSED after ' + ', '.join(opening.earlier_versions) if opening.reused else ''})")
    res = validate(bundle, inputs, prep, args.window, lobo=not args.no_lobo, n_boot=args.n_boot,
                   opening=opening, frozen=frozen)
    paths = write(res, out)
    print()
    print(summary_table(json.loads(paths[0].read_text())))
    print("\n" + "\n".join(f"wrote {p}" for p in paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
