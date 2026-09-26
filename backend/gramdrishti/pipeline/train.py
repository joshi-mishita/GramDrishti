"""Train the downscaling models reproducibly and print a development report.

Windows: models on TRAIN; isotonic calibration and conformal offsets on CALIB. TEST is never read.
Development checks (Guide 6.2 and CLAUDE.md rule 5):
- 80 % interval coverage on one half of CALIB with offsets fitted on the other half (both ways);
- rain-event Brier scores on CALIB halves (isotonic fitted on the other half);
- out-of-time point error on CALIB against B0 and B1 (point models never see CALIB);
- with ``--lobo``: leave-one-block-out on TRAIN, error against B0 and B1.

Run: ``cd backend && python -m gramdrishti.pipeline.train [--lobo] [--trees N] [--no-save]``
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from gramdrishti.data.config import (
    ART,
    CALIB,
    INTERVAL_LEVEL,
    LEAD_GROUPS,
    MODEL_VERSION_PREFIX,
    QUANTILES,
    RAIN_EVENTS_MM,
    SEED,
    TRAIN,
    VARS,
    data_mode,
    window_bounds,
)
from gramdrishti.features.static import fit_encodings
from gramdrishti.features.table import TARGETS, Inputs, event_name, feature_names, load_inputs, make_table
from gramdrishti.models.artifacts import Bundle, library_versions, save_bundle, table_hash
from gramdrishti.models.bias import BiasModel, block_reference, fit_bias
from gramdrishti.models.conformal import apply_offsets, coverage_table, enforce_constraints, fit_offsets
from gramdrishti.models.downscale import DownscaleModels, fit_downscale, fit_mean_only, lgbm_params
from gramdrishti.models.reconcile import max_block_error
from gramdrishti.pipeline.predict import predict_table
from gramdrishti.verify.metrics import continuous_scores

UNITS = {"rain": "mm", "rain_wet": "mm", "tmax": "C", "tmin": "C", "rh": "%", "wind": "km/h", "td": "C"}


@dataclass
class Prepared:
    """Inputs, B1 bias model, category codes and the TRAIN and CALIB tables."""

    inputs: Inputs
    bias: BiasModel
    encodings: dict
    features: list[str]
    train: pd.DataFrame
    calib: pd.DataFrame


@dataclass
class TrainResult:
    """Fitted models plus everything the dev report needs."""

    prepared: Prepared
    models: DownscaleModels
    offsets: pd.DataFrame
    calib_pred: pd.DataFrame
    config: dict
    sections: dict[str, pd.DataFrame] = field(default_factory=dict)


def prepare(inputs: Inputs | None = None) -> Prepared:
    """Fit the B1 bias correction on TRAIN and build the TRAIN and CALIB tables."""
    inputs = inputs or load_inputs()
    bias = fit_bias(inputs.fc, block_reference(inputs.obs_clean, inputs.stations), "TRAIN")
    enc = fit_encodings(inputs.static)
    train = make_table("train", inputs, bias, enc, window="TRAIN")
    calib = make_table("train", inputs, bias, enc, window="CALIB")
    _, train_end = window_bounds("TRAIN")
    _, calib_end = window_bounds("CALIB")
    assert train["valid_date"].max() <= train_end < calib["issue_date"].min(), "TRAIN overlaps CALIB"
    assert calib["valid_date"].max() <= calib_end, "CALIB table reaches past CALIB"
    return Prepared(inputs, bias, enc, feature_names(), train, calib)


def split_halves(t: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Boolean masks for the first and second half of CALIB by valid date (disjoint truth days)."""
    start, end = window_bounds("CALIB")
    mid = start + (end - start) / 2
    first = t["valid_date"] <= mid
    return first, ~first


def fit_all(prep: Prepared, params: dict) -> tuple[DownscaleModels, pd.DataFrame, pd.DataFrame]:
    """Fit models on TRAIN, isotonic maps and conformal offsets on all of CALIB.

    Returns the models, the offsets and the CALIB predictions before offsets and constraints.
    """
    models = fit_downscale(prep.train, prep.features, params)
    models.isotonic = models.fit_isotonic(prep.calib)
    pre = predict_table(models, prep.calib, offsets=None, events=False, constrain=False)
    return models, fit_offsets(pre, prep.calib), pre


def train(params_override: dict | None = None, lobo: bool = False, prep: Prepared | None = None,
          log=print) -> TrainResult:
    """Fit everything and compute the dev report sections. Does not write files."""
    prep = prep or prepare()
    params = lgbm_params(params_override)
    t0 = time.time()
    models, offsets, pre = fit_all(prep, params)
    log(f"fitted {len(models.regressors) * 4 + len(models.events)} models in {time.time() - t0:.0f} s")
    calib_pred = predict_table(models, prep.calib, offsets)
    data_hash = table_hash(prep.train[[*prep.features, *[f"y_{t}" for t in TARGETS]]],
                           prep.calib[[*prep.features, *[f"obs_{v}" for v in VARS]]])
    config = {
        "model_version": f"{MODEL_VERSION_PREFIX}-{data_hash[:10]}", "data_mode": data_mode(),
        "data_hash_sha256": data_hash, "seed": SEED, "targets": TARGETS, "quantiles": list(QUANTILES),
        "rain_events_mm": list(RAIN_EVENTS_MM), "interval_level": INTERVAL_LEVEL, "lead_groups": LEAD_GROUPS,
        "windows": {"models": TRAIN, "calibration": CALIB, "test": "not opened"},
        "rows": {"train": len(prep.train), "calib": len(prep.calib)},
        "max_dates_read": {"train_valid": prep.train["valid_date"].max(),
                           "calib_valid": prep.calib["valid_date"].max(),
                           "bias_fit": prep.bias.data_max_date},
        "training_target": ("synthetic Panchayat truth (MOCK ONLY proxy)" if data_mode() == "mock"
                            else "stations"),
        "reconciliation_weights": "equal",
        "versions": library_versions(),
    }
    res = TrainResult(prep, models, offsets, calib_pred, config)
    res.sections["coverage"] = calib_half_coverage(prep, pre)
    res.sections["offsets"] = offsets
    res.sections["events"] = calib_half_events(prep, models)
    res.sections["calib_point"] = point_scores(calib_pred, prep.calib)
    res.sections["consistency"] = consistency(calib_pred)
    res.sections["constraints"] = constraint_violations(calib_pred)
    res.sections["irrigation"] = irrigation_check(models, prep.train)
    if lobo:
        t0 = time.time()
        res.sections["lobo"] = run_lobo(prep, params)
        log(f"leave-one-block-out done in {time.time() - t0:.0f} s")
    return res


# ---------------------------------------------------------------- dev checks
def calib_half_coverage(prep: Prepared, pre: pd.DataFrame) -> pd.DataFrame:
    """Coverage and width on one CALIB half with offsets fitted on the other half, both directions."""
    first, second = split_halves(prep.calib)
    rows = []
    splits = ((first, second, "fit 1st half, score 2nd"), (second, first, "fit 2nd half, score 1st"))
    for fit_m, eval_m, label in splits:
        off = fit_offsets(pre[fit_m], prep.calib[fit_m])
        raw = coverage_table(enforce_constraints(pre[eval_m]), prep.calib[eval_m])
        cal = coverage_table(enforce_constraints(apply_offsets(pre[eval_m], off)), prep.calib[eval_m])
        m = raw.merge(cal, on=["var", "lead_group", "n"], suffixes=("_raw", "_cal"))
        q = off.set_index(["var", "lead_group"])["q"]
        m["q"] = [q[(v.removesuffix("_wet"), g)] for v, g in zip(m["var"], m["lead_group"], strict=True)]
        rows.append(m.assign(split=label))
    return pd.concat(rows, ignore_index=True)


def brier(p: np.ndarray, y: np.ndarray) -> float:
    """Mean squared difference between probability and outcome."""
    return float(np.mean((np.asarray(p, dtype=float) - y) ** 2))


def calib_half_events(prep: Prepared, models: DownscaleModels) -> pd.DataFrame:
    """Brier scores on each CALIB half: raw classifier, isotonic fitted on the other half, TRAIN
    climatology, and B1 as a yes/no forecast."""
    first, second = split_halves(prep.calib)
    raw = models.event_proba(prep.calib, calibrated=False)
    rows = []
    splits = ((first, second, "iso 1st, score 2nd"), (second, first, "iso 2nd, score 1st"))
    for fit_m, eval_m, label in splits:
        sub = DownscaleModels(models.features, models.params, {}, models.events)
        iso = sub.fit_isotonic(prep.calib[fit_m])
        for thr in RAIN_EVENTS_MM:
            ev = event_name(thr)
            y = prep.calib.loc[eval_m, ev].to_numpy()
            p_raw = raw.loc[eval_m, f"prob_{ev[3:]}"].to_numpy()
            x_eval = prep.calib.loc[eval_m, models.features]
            p_iso = iso[thr].predict(models.events[thr].predict_proba(x_eval)[:, 1])
            clim = prep.train[ev].mean()
            b1 = (prep.calib.loc[eval_m, "b1_rain"] >= thr).astype(float).to_numpy()
            rows.append({"split": label, "threshold_mm": thr, "n": len(y), "base_rate": float(y.mean()),
                         "brier_raw": brier(p_raw, y), "brier_isotonic": brier(p_iso, y),
                         "brier_climatology": brier(np.full(len(y), clim), y),
                         "brier_b1_yes_no": brier(b1, y)})
    return pd.DataFrame(rows)


def point_scores(pred: pd.DataFrame, table: pd.DataFrame, by_lead: bool = False) -> pd.DataFrame:
    """MAE, RMSE and bias of B0, B1 and the model's reconciled mean against ``obs_<var>``."""
    rows = []
    groups = [("all", pred.index)] if not by_lead else list(pred.groupby("lead_day").groups.items())
    for lead, idx in groups:
        for var in VARS:
            y = table.loc[idx, f"obs_{var}"].to_numpy()
            row = {"var": var, "lead_day": lead}
            for name, col in (("B0", f"b0_{var}"), ("B1", f"b1_{var}"), ("model", f"{var}_mean")):
                s = continuous_scores(pred.loc[idx, col].to_numpy(), y)
                row |= {"n": s["n"], f"mae_{name}": s["mae"], f"rmse_{name}": s["rmse"],
                        f"bias_{name}": s["bias"]}
            rows.append(row)
    out = pd.DataFrame(rows)
    out["mae_skill_vs_B1"] = 1 - out["mae_model"] / out["mae_B1"]
    return out


def consistency(pred: pd.DataFrame) -> pd.DataFrame:
    """Largest block-mean error per variable after reconciliation."""
    return pd.DataFrame([{"var": v, "max_abs_error": max_block_error(pred, v, f"b1_{v}")}
                         for v in [*VARS, "td"]])


def constraint_violations(pred: pd.DataFrame) -> pd.DataFrame:
    """Counts of rows breaking each output constraint (all should be 0)."""
    rows = []
    for v in VARS:
        rows.append({"check": f"{v}: p10 <= p50 <= p90",
                     "violations": int(((pred[f"{v}_p10"] > pred[f"{v}_p50"]) |
                                        (pred[f"{v}_p50"] > pred[f"{v}_p90"])).sum())})
    rows.append({"check": "rain >= 0 (mean, p10)",
                 "violations": int(((pred["rain_mean"] < 0) | (pred["rain_p10"] < 0)).sum())})
    rows.append({"check": "rh within 0..100", "violations": int(sum(
        ((pred[f"rh_{s}"] < 0) | (pred[f"rh_{s}"] > 100)).sum() for s in ("mean", "p10", "p50", "p90")))})
    rows.append({"check": "tmin < tmax (mean, p10, p50, p90)", "violations": int(sum(
        (pred[f"tmin_{s}"] >= pred[f"tmax_{s}"]).sum() for s in ("mean", "p10", "p50", "p90")))})
    return pd.DataFrame(rows)


def irrigation_check(models: DownscaleModels, train: pd.DataFrame, months: tuple[int, ...] = (4, 5),
                     n: int = 20000) -> pd.DataFrame:
    """Mean predicted Tmax anomaly when every Panchayat's irrigated_frac is set to the 10th, 50th and
    90th percentile of the static table (hot dry months of TRAIN; the relative feature moves with it)."""
    rows = train[train["month"].isin(months)]
    rows = rows.sample(min(n, len(rows)), random_state=SEED)
    levels = np.quantile(train.drop_duplicates("panchayat_id")["irrigated_frac"], [0.1, 0.5, 0.9])
    out = []
    for q, v in zip((10, 50, 90), levels, strict=True):
        x = rows[models.features].copy()
        x["irrigated_frac_rel"] = x["irrigated_frac_rel"] + (v - x["irrigated_frac"])
        x["irrigated_frac"] = v
        out.append({"percentile": q, "irrigated_frac": float(v),
                    "mean_tmax_anomaly_c": float(models.regressors["tmax"]["mean"].predict(x).mean())})
    return pd.DataFrame(out)


def run_lobo(prep: Prepared, params: dict) -> pd.DataFrame:
    """Leave-one-block-out on TRAIN: fit mean models without one block, predict it, reconcile, score.

    The B1 bias correction stays fitted on all TRAIN blocks, so B0, B1 and the model share the same
    block forecast and differ only in how it is spread over Panchayats.
    """
    parts = []
    for block in sorted(prep.train["block_id"].unique()):
        hold = prep.train["block_id"] == block
        m = fit_mean_only(prep.train[~hold], prep.features, params)
        parts.append(predict_table(m, prep.train[hold], events=False))
    pred = pd.concat(parts).loc[prep.train.index]
    return pd.concat([point_scores(pred, prep.train), point_scores(pred, prep.train, by_lead=True)],
                     ignore_index=True)


# ---------------------------------------------------------------- report
def _f(x: float | None, nd: int = 3) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{x:.{nd}f}"


def _scores_block(df: pd.DataFrame, title: str) -> list[str]:
    lines = [title, f"{'var':<5} {'unit':<5} {'n':>7} | {'MAE B0':>7} {'B1':>7} {'model':>7} | "
             f"{'RMSE B0':>7} {'B1':>7} {'model':>7} | {'MAE skill vs B1':>15}  verdict"]
    lines.append("-" * len(lines[-1]))
    for r in df[df["lead_day"] == "all"].itertuples():
        if r.mae_model < r.mae_B1 and r.rmse_model < r.rmse_B1:
            verdict = "beats B1"
        elif r.mae_model >= r.mae_B1 and r.rmse_model >= r.rmse_B1:
            verdict = "does NOT beat B1"
        else:
            verdict = "mixed (MAE vs RMSE)"
        lines.append(f"{r.var:<5} {UNITS[r.var]:<5} {r.n:>7} | {_f(r.mae_B0):>7} {_f(r.mae_B1):>7} "
                     f"{_f(r.mae_model):>7} | {_f(r.rmse_B0):>7} {_f(r.rmse_B1):>7} {_f(r.rmse_model):>7} | "
                     f"{_f(100 * r.mae_skill_vs_B1, 1):>14}%  {verdict}")
    by = df[df["lead_day"] != "all"]
    if len(by):
        lines.append("MAE by lead day, B1 -> model:")
        for var in VARS:
            cells = [f"L{int(r.lead_day)} {_f(r.mae_B1)}->{_f(r.mae_model)}"
                     for r in by[by["var"] == var].itertuples()]
            lines.append(f"  {var:<5} " + "  ".join(cells))
    return lines


def format_report(res: TrainResult) -> str:
    """Plain-text dev report. Numbers are printed as measured."""
    c, s = res.config, res.sections
    L = [
        "GramDrishti S5 model dev report",
        f"model_version: {c['model_version']}   data_mode: {c['data_mode']} "
        "(synthetic proxy validation, not real weather)",
        f"models fitted on TRAIN {TRAIN[0]}..{TRAIN[1]} ({c['rows']['train']} rows, latest valid date "
        f"{c['max_dates_read']['train_valid'].date()}); isotonic + conformal on CALIB {CALIB[0]}..{CALIB[1]} "
        f"({c['rows']['calib']} rows, latest valid date {c['max_dates_read']['calib_valid'].date()})",
        "TEST window: not opened. Training target: " + c["training_target"] + ".",
        "",
        f"1. {int(INTERVAL_LEVEL * 100)} % interval [p10, p90] on CALIB halves "
        "(offsets fitted on the other half)",
    ]
    hdr = (f"{'split':<24} {'var':<5} {'lead':<5} {'n':>6} | {'cov raw':>7} {'cov cal':>7} | "
           f"{'width raw':>9} {'width cal':>9} | {'offset q':>8}")
    L += [hdr, "-" * len(hdr)]
    for r in s["coverage"].itertuples():
        L.append(f"{r.split:<24} {r.var:<5} {r.lead_group:<5} {r.n:>6} | {_f(r.coverage_raw):>7} "
                 f"{_f(r.coverage_cal):>7} | {_f(r.width_raw, 2):>9} {_f(r.width_cal, 2):>9} | {_f(r.q):>8}")
    cov = s["coverage"][s["coverage"]["var"] != "rain_wet"]
    L.append(f"all days, 5 variables: mean coverage after calibration {_f(cov['coverage_cal'].mean())} "
             f"(nominal {INTERVAL_LEVEL}), range {_f(cov['coverage_cal'].min())}.."
             f"{_f(cov['coverage_cal'].max())}; "
             "rain_wet = days with observed rain >= 1 mm")
    L += ["", "Production offsets (fitted on all of CALIB):"]
    L += [f"  {r.var:<5} {r.lead_group:<5} q = {_f(r.q)} {UNITS[r.var]} (n={r.n})"
          for r in s["offsets"].itertuples()]

    if "lobo" in s:
        title = "2. Leave-one-block-out on TRAIN (6 folds), Panchayat-level scores of the reconciled mean"
        L += [""] + _scores_block(s["lobo"], title)
    else:
        L += ["", "2. Leave-one-block-out: not run (use --lobo)"]
    title = "3. Out-of-time check on CALIB (point models never saw CALIB)"
    L += [""] + _scores_block(s["calib_point"], title)

    L += ["", "4. Rain events on CALIB halves: Brier score (lower is better)"]
    hdr = (f"{'split':<20} {'thr mm':>6} {'base':>6} | {'raw':>6} {'isotonic':>8} {'climatol.':>9} "
           f"{'B1 yes/no':>9}")
    L += [hdr, "-" * len(hdr)]
    for r in s["events"].itertuples():
        L.append(f"{r.split:<20} {r.threshold_mm:>6g} {_f(r.base_rate):>6} | {_f(r.brier_raw, 4):>6} "
                 f"{_f(r.brier_isotonic, 4):>8} {_f(r.brier_climatology, 4):>9} "
                 f"{_f(r.brier_b1_yes_no, 4):>9}")

    L += ["", "5. Block consistency on CALIB predictions: "
              "max |block mean of Panchayat means - B1 block forecast|"]
    L += [f"  {r.var:<5} {r.max_abs_error:.2e}" for r in s["consistency"].itertuples()]
    L += ["", "6. Constraint violations on CALIB predictions"]
    L += [f"  {r.check:<40} {r.violations}" for r in s["constraints"].itertuples()]
    L += ["", "7. Sanity: mean predicted Tmax anomaly vs irrigated_frac "
              "(TRAIN Apr-May rows, partial dependence)"]
    L += [f"  p{r.percentile:<3} irrigated_frac={r.irrigated_frac:.3f}  "
          f"anomaly={r.mean_tmax_anomaly_c:+.3f} C"
          for r in s["irrigation"].itertuples()]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--lobo", action="store_true", help="add leave-one-block-out CV on TRAIN")
    ap.add_argument("--trees", type=int, default=None, help="override n_estimators (quick runs only)")
    ap.add_argument("--out", type=Path, default=ART, help="artifact folder (default backend/artifacts)")
    ap.add_argument("--no-save", action="store_true", help="do not write artifacts")
    args = ap.parse_args(argv)
    override = {"n_estimators": args.trees} if args.trees else None
    res = train(override, lobo=args.lobo)
    report = format_report(res)
    print(report)
    if not args.no_save:
        bundle = Bundle(res.models, res.offsets, res.prepared.bias, res.prepared.encodings, res.config)
        files = save_bundle(bundle, args.out)
        (args.out / "dev_report.txt").write_text(report + "\n")
        print(f"\nwrote {len(files) + 1} files to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
