"""Prepare everything the demo needs, skipping each step that is already done (S14, one-command start).

Steps, in order:

1. ``oracle``: the git-ignored synthetic truth (``data/synthetic_oracle/``). Missing: run
   ``data/generate_mock_data.py`` into a temporary folder, copy only ``synthetic_oracle/``, and check the
   committed data files come out byte-identical (the generator is seeded).
2. ``model``: the trained bundle in ``artifacts/``. Missing: ``pipeline.train`` (a few minutes).
3. ``snapshots``: one forecast snapshot per demo date and the day before. Any missing:
   ``pipeline.run_daily --all-demo-dates`` (snapshots and draft advisories).
4. ``verification``: ``artifacts/verification.json`` and ``impact.json``. Missing: copy the committed
   record for this model version (``verify/records/<version>/``) when the model version, the data file
   hashes and the library versions match; otherwise leave them missing and say why. TEST is never opened.
5. ``farmers``: seed the five demo farmers (idempotent).
6. ``offline`` (only with ``--offline-out``): export every GET response for snapshot mode
   (``export_snapshot``), unless it exists and ``--refresh-offline`` is not given.

Run: ``cd backend && python -m gramdrishti.pipeline.prepare_demo [--offline-out DIR] [--refresh-offline]``
The Docker stack runs it as the ``prepare`` service before the API starts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from gramdrishti.data.config import ART, ROOT, data_dir

ORACLE_FILES = ("panchayat_daily_SYNTHETIC_TRUTH.csv", "block_daily_SYNTHETIC_TRUTH.csv")
RECORDS = Path(__file__).resolve().parents[1] / "verify" / "records"
VERIFICATION_FILES = ("verification.json", "impact.json")
# Library versions that must equal the record's for its numbers to describe this model.
EXACT_LIBRARIES = ("lightgbm", "scikit-learn", "pandas", "numpy")


def sha256(path: Path) -> str:
    """Hex sha256 of a file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_oracle(data: Path | None = None) -> str:
    """Generate the synthetic oracle if it is missing. Returns a one-line status."""
    data = data or data_dir()
    oracle = data / "synthetic_oracle"
    if all((oracle / f).exists() for f in ORACLE_FILES):
        return "present"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, str(ROOT / "data" / "generate_mock_data.py")], check=True,
                       env={**os.environ, "OUT": tmp}, stdout=subprocess.DEVNULL)
        oracle.mkdir(parents=True, exist_ok=True)
        for f in (Path(tmp) / "synthetic_oracle").iterdir():
            shutil.copy2(f, oracle / f.name)
        changed = [p.name for p in sorted(Path(tmp).glob("*.csv"))
                   if (data / p.name).exists() and sha256(p) != sha256(data / p.name)]
    if changed:
        raise RuntimeError(f"generate_mock_data.py no longer reproduces the committed files: {changed}")
    return "generated (committed data files reproduced byte for byte)"


def model_ready(art: Path = ART) -> bool:
    """True when ``art`` holds a complete trained bundle."""
    cfg = art / "config.json"
    if not cfg.exists():
        return False
    targets = json.loads(cfg.read_text())["targets"]
    needed = [f"model_{t}.joblib" for t in targets] + ["events.joblib", "bias.joblib", "conformal.json",
                                                         "features.json"]
    return all((art / f).exists() for f in needed)


def ensure_model(art: Path = ART) -> str:
    """Train when the bundle is missing."""
    if model_ready(art):
        return f"present ({json.loads((art / 'config.json').read_text())['model_version']})"
    from gramdrishti.pipeline import train
    if train.main(["--out", str(art)]) != 0:
        raise RuntimeError("training failed")
    return f"trained ({json.loads((art / 'config.json').read_text())['model_version']})"


def missing_snapshots(root: Path) -> list[str]:
    """Demo-plan dates without a complete snapshot under ``root``."""
    from gramdrishti.pipeline.run_daily import demo_plan
    return [d.isoformat() for d, _ in demo_plan() if not (root / d.isoformat() / "manifest.json").exists()]


def ensure_snapshots(art: Path = ART) -> str:
    """Build snapshots and drafts for every demo date when any is missing."""
    from gramdrishti.pipeline import run_daily
    missing = missing_snapshots(run_daily.SNAPSHOTS)
    if not missing:
        return "present"
    if run_daily.main(["--all-demo-dates", "--artifacts", str(art)]) != 0:
        raise RuntimeError("run_daily failed")
    return f"built ({len(missing)} were missing)"


def record_mismatches(frozen: dict, model_version: str, data: Path, libs: dict[str, str]) -> list[str]:
    """Reasons a verification record does not describe the local model; empty when it does."""
    out = []
    if frozen["model_version"] != model_version:
        out.append(f"model version {frozen['model_version']} != {model_version}")
    for name, want in frozen["data_files_sha256"].items():
        p = data / name
        if not p.exists() or sha256(p) != want:
            out.append(f"data file {name} differs")
    rec = frozen["library_versions"]
    if rec["python"].split(".")[:2] != libs["python"].split(".")[:2]:
        out.append(f"python {rec['python']} != {libs['python']}")
    out += [f"{k} {rec[k]} != {libs.get(k)}" for k in EXACT_LIBRARIES if rec.get(k) != libs.get(k)]
    return out


def ensure_verification(art: Path = ART, records: Path = RECORDS, data: Path | None = None) -> str:
    """Copy the committed verification record when it matches this model; never runs the job."""
    if all((art / f).exists() for f in VERIFICATION_FILES):
        return "present"
    from gramdrishti.models.artifacts import library_versions
    version = json.loads((art / "config.json").read_text())["model_version"]
    rec = records / version
    if not (rec / "verification.json").exists():
        return (f"MISSING: no record for {version}; the verification and impact screens will say 'not "
                "computed' until the job runs (docs/validation_protocol.md)")
    frozen = json.loads((rec / "verification.json").read_text())["frozen"]
    why = record_mismatches(frozen, version, data or data_dir(), library_versions())
    if why:
        return "MISSING: record not copied (" + "; ".join(why) + ")"
    for f in VERIFICATION_FILES:
        shutil.copy2(rec / f, art / f)
    return f"copied from verify/records/{version}/ (TEST not opened)"


def seed_farmers() -> str:
    """Seed the demo farmers into the store."""
    from gramdrishti.store.db import Store
    from gramdrishti.store.seed_demo import seed
    store = Store()
    return f"{seed(store)} demo farmers in {store.path}"


def ensure_offline(out: Path, refresh: bool) -> str:
    """Export the snapshot-mode files unless they exist (``refresh`` forces a new export)."""
    if (out / "index.json").exists() and not refresh:
        return f"present in {out} (refresh with --refresh-offline)"
    from gramdrishti.export_snapshot import export
    index = export(out)
    return f"{len(index)} responses exported to {out}"


def run_steps(steps: list[tuple[str, Callable[[], str]]], log=print) -> list[tuple[str, str, float]]:
    """Run each step, print its status and time, and stop on the first error."""
    done = []
    for name, fn in steps:
        log(f"[prepare] {name} ...", flush=True)
        t0 = time.perf_counter()
        status = fn()
        secs = time.perf_counter() - t0
        log(f"[prepare] {name}: {status} ({secs:.1f} s)", flush=True)
        done.append((name, status, secs))
    return done


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline-out", type=Path, default=None,
                    help="also export snapshot-mode files here (for the offline web service)")
    ap.add_argument("--refresh-offline", action="store_true", help="export again even if present")
    a = ap.parse_args(argv)
    steps: list[tuple[str, Callable[[], str]]] = [
        ("oracle", ensure_oracle), ("model", ensure_model), ("snapshots", ensure_snapshots),
        ("verification", ensure_verification), ("farmers", seed_farmers)]
    if a.offline_out is not None:
        steps.append(("offline", lambda: ensure_offline(a.offline_out, a.refresh_offline)))
    t0 = time.perf_counter()
    done = run_steps(steps)
    print(f"[prepare] done in {time.perf_counter() - t0:.1f} s: "
          + ", ".join(f"{n} {s:.0f} s" for n, _, s in done))
    return 0


if __name__ == "__main__":
    sys.exit(main())
