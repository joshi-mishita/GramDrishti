"""Save and load the trained model bundle in ``backend/artifacts/`` (git-ignored).

Files: ``model_<target>.joblib`` (mean + quantile regressors), ``events.joblib`` (classifiers and
isotonic maps), ``bias.joblib`` (B1 bias correction, needed at inference), ``conformal.json``,
``features.json`` (ordered feature list and category codes), ``config.json`` (parameters, windows,
data hash, model version, library versions).
"""

from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from pathlib import Path

import joblib
import lightgbm
import numpy as np
import pandas as pd
import sklearn

from gramdrishti.features.static import Encodings
from gramdrishti.models.bias import BiasModel
from gramdrishti.models.downscale import DownscaleModels


@dataclass
class Bundle:
    """Everything inference needs."""

    models: DownscaleModels
    offsets: pd.DataFrame
    bias: BiasModel
    encodings: Encodings
    config: dict


def table_hash(*tables: pd.DataFrame) -> str:
    """sha256 over the exact rows and columns the models were fitted and calibrated on."""
    h = hashlib.sha256()
    for t in tables:
        h.update(",".join(t.columns).encode())
        h.update(pd.util.hash_pandas_object(t, index=False).to_numpy().tobytes())
    return h.hexdigest()


def library_versions() -> dict[str, str]:
    """Versions that affect the fitted models."""
    return {"python": platform.python_version(), "lightgbm": lightgbm.__version__,
            "scikit-learn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__}


def save_bundle(bundle: Bundle, out: Path) -> list[Path]:
    """Write the bundle into ``out``; returns the files written."""
    out.mkdir(parents=True, exist_ok=True)
    m = bundle.models
    written = []
    for target, regs in m.regressors.items():
        written.append(out / f"model_{target}.joblib")
        joblib.dump(regs, written[-1])
    written.append(out / "events.joblib")
    joblib.dump({thr: {"clf": m.events[thr], "iso": m.isotonic.get(thr)} for thr in m.events}, written[-1])
    written.append(out / "bias.joblib")
    joblib.dump(bundle.bias, written[-1])
    written.append(out / "conformal.json")
    written[-1].write_text(json.dumps(bundle.offsets.to_dict(orient="records"), indent=2))
    written.append(out / "features.json")
    written[-1].write_text(json.dumps({"features": m.features, "encodings": bundle.encodings}, indent=2))
    written.append(out / "config.json")
    written[-1].write_text(json.dumps({**bundle.config, "lgbm_params": m.params}, indent=2, default=str))
    return written


def load_bundle(src: Path) -> Bundle:
    """Load a bundle written by ``save_bundle``."""
    config = json.loads((src / "config.json").read_text())
    feats = json.loads((src / "features.json").read_text())
    regs = {t: joblib.load(src / f"model_{t}.joblib") for t in config["targets"]}
    ev = joblib.load(src / "events.joblib")
    models = DownscaleModels(feats["features"], config["lgbm_params"], regs,
                             {float(k): v["clf"] for k, v in ev.items()},
                             {float(k): v["iso"] for k, v in ev.items() if v["iso"] is not None})
    offsets = pd.DataFrame(json.loads((src / "conformal.json").read_text()))
    return Bundle(models, offsets, joblib.load(src / "bias.joblib"), feats["encodings"], config)
