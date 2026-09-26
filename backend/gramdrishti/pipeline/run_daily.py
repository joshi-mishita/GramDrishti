"""Snapshot builder (Backend Guide 12.3): model output for one issue date, precomputed for the API.

Steps per issue date: 1 build the inference table (features only, never truth) 2 bias-correct the
block forecast (inside the table: B1) 3 predict, calibrate (conformal offsets) and reconcile to the
block 4 derive agro-variables 5 SHAP reasons. Output in ``artifacts/snapshots/<date>/``:

- ``forecast.parquet``: one row per Panchayat and lead day: B0 and B1 block values, ``<var>_{mean,p10,
  p50,p90}`` (plus dew point), rain event probabilities, agro-variables;
- ``block.parquet``: one row per block and lead day: B0, B1 and the block mean of the Panchayat means;
- ``explain.parquet``: top 3 SHAP reasons per Panchayat, lead day and variable;
- ``manifest.json``: model version, data mode, row counts, soil-moisture source, file hashes.

``--all-demo-dates`` also builds the day before each demo date (role ``previous``), which
``/forecast/changes`` compares against. Output is deterministic: no timestamps, fixed row order.

Afterwards the rules engine writes draft advisories for every demo-role date into the SQLite store
(``GRAMDRISHTI_DB`` or ``artifacts/gramdrishti.sqlite``), replacing earlier drafts and keeping reviewed
advisories. ``--no-advisories`` skips that step.

Run: ``cd backend && python -m gramdrishti.pipeline.run_daily --issue-date 2024-09-09``
     ``cd backend && python -m gramdrishti.pipeline.run_daily --all-demo-dates``
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from gramdrishti.advisory.drafts import create_drafts
from gramdrishti.agro import derived
from gramdrishti.contract.pick_demo_dates import load_demo_dates
from gramdrishti.data import loaders
from gramdrishti.data.config import ART, RECONCILE_TOL, VARS, data_mode
from gramdrishti.explain.shap_explain import top_reasons
from gramdrishti.features.table import Inputs, load_inputs, make_table
from gramdrishti.models.artifacts import Bundle, load_bundle
from gramdrishti.models.reconcile import max_block_error
from gramdrishti.pipeline.predict import predict_table
from gramdrishti.store.db import Store

SNAPSHOTS = ART / "snapshots"
FRAMES = ("forecast", "block", "explain")
ROLE_DEMO, ROLE_PREVIOUS = "demo", "previous"
SM_SOURCE_MOCK = ("synthetic_oracle soil_moisture_frac at the end of the day before the issue date "
                  "(MOCK ONLY; real mode needs ERA5-Land or SMAP)")
SM_SOURCE_NONE = "none: real mode needs ERA5-Land or SMAP soil moisture (not connected)"


@dataclass
class Snapshot:
    """All frames for one issue date plus its manifest."""

    issue_date: date
    forecast: pd.DataFrame
    block: pd.DataFrame
    explain: pd.DataFrame
    manifest: dict


class SoilState:
    """Latest known soil moisture per Panchayat at issue time.

    Mock mode: the synthetic oracle's value at the end of the day before the issue date (the latest
    state known on the issue morning). It is an initial condition for the water balance, never a
    model feature. Real mode: not connected yet, so every value is NaN and soil outputs are null.
    """

    def __init__(self) -> None:
        self._truth: pd.DataFrame | None = None

    @property
    def source(self) -> str:
        return SM_SOURCE_MOCK if data_mode() == "mock" else SM_SOURCE_NONE

    def at(self, issue: date, pids: pd.Index) -> pd.Series:
        if data_mode() != "mock":
            return pd.Series(np.nan, index=pids)
        if self._truth is None:
            t = loaders.load_truth()  # MOCK ONLY: initial soil state, not a feature
            self._truth = t[["date", "panchayat_id", "soil_moisture_frac"]]
        day = pd.Timestamp(issue) - pd.Timedelta(days=1)
        t = self._truth[self._truth["date"] == day].set_index("panchayat_id")["soil_moisture_frac"]
        return t.reindex(pids)


def build_snapshot(bundle: Bundle, inputs: Inputs, issue: date, soil: SoilState,
                   role: str = ROLE_DEMO) -> Snapshot:
    """Model output, agro-variables and reasons for one issue date."""
    table = make_table("infer", inputs, bundle.bias, bundle.encodings, issue_dates=[issue])
    if table.empty:
        raise ValueError(f"No block forecast issued on {issue.isoformat()}")
    pred = predict_table(bundle.models, table, bundle.offsets)
    for v in [*VARS, "td"]:
        err = max_block_error(pred, v, f"b1_{v}")
        if err >= RECONCILE_TOL:
            raise AssertionError(f"block consistency broken for {v} on {issue}: {err:.2e}")
    pred["ndvi"] = table["ndvi"].to_numpy()
    pids = pd.Index(sorted(pred["panchayat_id"].unique()))
    agro = derived.derive(pred, inputs.static, soil.at(issue, pids))
    forecast = pred.merge(agro, on=["panchayat_id", "lead_day"], how="left", validate="one_to_one")
    forecast = forecast.sort_values(["lead_day", "panchayat_id"]).reset_index(drop=True)

    grp = forecast.groupby(["block_id", "lead_day", "valid_date"], sort=True)
    block = grp[[*[f"b0_{v}" for v in VARS], *[f"b1_{v}" for v in VARS]]].first()
    block = block.join(grp[[f"{v}_mean" for v in VARS]].mean().add_prefix("pmean_"))
    block = block.join(grp[[f"{v}_p50" for v in VARS]].mean().add_prefix("pmean_"))
    block = block.reset_index().sort_values(["lead_day", "block_id"]).reset_index(drop=True)

    explain = top_reasons(bundle.models, table, inputs.static)
    explain = explain.sort_values(["lead_day", "panchayat_id", "var", "rank"]).reset_index(drop=True)

    manifest = {
        "issue_date": issue.isoformat(), "role": role, "model_version": bundle.config["model_version"],
        "data_mode": data_mode(), "data_hash_sha256": bundle.config["data_hash_sha256"],
        "rows": {"forecast": len(forecast), "block": len(block), "explain": len(explain)},
        "initial_soil_moisture": soil.source, "thresholds_status": "placeholder",
        "reconciliation": "block mean of <var>_mean equals b1_<var> (corrected block forecast)",
        "generated_by": "python -m gramdrishti.pipeline.run_daily",
    }
    return Snapshot(issue, forecast, block, explain, manifest)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_snapshot(snap: Snapshot, root: Path = SNAPSHOTS) -> Path:
    """Write the frames and manifest into ``root/<issue_date>/``; returns that folder."""
    out = root / snap.issue_date.isoformat()
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for name in FRAMES:
        p = out / f"{name}.parquet"
        getattr(snap, name).to_parquet(p, index=False, engine="pyarrow", compression="zstd")
        files[p.name] = _sha256(p)
    (out / "manifest.json").write_text(json.dumps({**snap.manifest, "files": files}, indent=2) + "\n")
    return out


def read_snapshot(root: Path, issue: date) -> Snapshot | None:
    """Load a snapshot written by ``write_snapshot``; None when it does not exist."""
    d = root / issue.isoformat()
    if not (d / "manifest.json").exists():
        return None
    frames = {n: pd.read_parquet(d / f"{n}.parquet") for n in FRAMES}
    return Snapshot(issue, frames["forecast"], frames["block"], frames["explain"],
                    json.loads((d / "manifest.json").read_text()))


def demo_plan() -> list[tuple[date, str]]:
    """Every demo issue date plus the day before each (for the change tracker), sorted, no duplicates."""
    plan: dict[date, str] = {}
    for d in load_demo_dates():
        issue = date.fromisoformat(d.date)
        plan.setdefault(issue - timedelta(days=1), ROLE_PREVIOUS)
        plan[issue] = ROLE_DEMO
    return sorted(plan.items())


def run(plan: list[tuple[date, str]], out: Path = SNAPSHOTS, artifacts: Path = ART,
        bundle: Bundle | None = None, log=print) -> list[Path]:
    """Build and write every snapshot in ``plan``; also writes ``out/index.json``."""
    bundle = bundle or load_bundle(artifacts)
    inputs, soil = load_inputs(), SoilState()
    written = []
    for issue, role in plan:
        t0 = time.time()
        snap = build_snapshot(bundle, inputs, issue, soil, role)
        written.append(write_snapshot(snap, out))
        log(f"{issue.isoformat()} {role:<8} {snap.manifest['rows']['forecast']:>4} forecast rows "
            f"{snap.manifest['rows']['explain']:>5} reasons  {time.time() - t0:.1f} s")
    index_path = out / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {"snapshots": {}}
    for issue, role in plan:
        index["snapshots"][issue.isoformat()] = role
    index["snapshots"] = dict(sorted(index["snapshots"].items()))
    index["model_version"] = bundle.config["model_version"]
    index_path.write_text(json.dumps(index, indent=2) + "\n")
    return written


def write_advisories(plan: list[tuple[date, str]], snapshots: Path = SNAPSHOTS, store: Store | None = None,
                     log=print) -> dict[date, dict[str, int]]:
    """Draft advisories for every demo-role date in ``plan``; returns counts by category per date."""
    store = store or Store()
    inputs = (loaders.load_static(), loaders.load_crops(), loaders.load_calendar())
    out = {}
    for issue, role in plan:
        if role != ROLE_DEMO:
            continue
        snap = read_snapshot(snapshots, issue)
        if snap is None:
            raise FileNotFoundError(f"no snapshot for {issue.isoformat()} in {snapshots}")
        res, written, kept = create_drafts(store, issue, snap.forecast, *inputs, data_mode=data_mode(),
                                           model_version=snap.manifest.get("model_version"))
        out[issue] = res.counts_by_category()
        cats = ", ".join(f"{k} {v}" for k, v in out[issue].items()) or "none"
        log(f"{issue.isoformat()} {len(res.advisories):>4} drafts ({written} written, {kept} reviewed kept): "
            f"{cats}")
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--issue-date", type=date.fromisoformat, help="one issue date, YYYY-MM-DD")
    g.add_argument("--all-demo-dates", action="store_true",
                   help="every date in demo_dates.json plus the day before each")
    ap.add_argument("--out", type=Path, default=SNAPSHOTS, help="snapshot root (default artifacts/snapshots)")
    ap.add_argument("--artifacts", type=Path, default=ART, help="trained model bundle (default artifacts)")
    ap.add_argument("--no-advisories", action="store_true", help="only build snapshots, no draft advisories")
    args = ap.parse_args(argv)
    plan = demo_plan() if args.all_demo_dates else [(args.issue_date, ROLE_DEMO)]
    t0 = time.time()
    written = run(plan, args.out, args.artifacts)
    size = sum(p.stat().st_size for d in written for p in d.iterdir())
    print(f"\nwrote {len(written)} snapshots to {args.out} ({size / 1e6:.2f} MB) in {time.time() - t0:.1f} s")
    if not args.no_advisories:
        store = Store()
        print(f"\ndraft advisories -> {store.path}")
        write_advisories(plan, args.out, store)
    return 0


if __name__ == "__main__":
    sys.exit(main())
