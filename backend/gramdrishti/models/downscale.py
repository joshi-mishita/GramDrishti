"""Panchayat downscaling models (Backend Guide 6.1 and 6.3).

Per target a LightGBM mean model (L2) and quantile models at 0.1, 0.5 and 0.9:
- tmax, tmin: anomaly = Panchayat value - corrected block forecast (B1);
- td (dew point): anomaly against the B1 block dew point; RH is derived later from T and dew point;
- wind: log(Panchayat / B1 block wind);
- rain: Panchayat amount in mm (zero-heavy).
Rain events (>= 1, 2.5, 10, 35 mm): one classifier per threshold, isotonic calibration fitted on CALIB.

Models are fitted on TRAIN rows only. ``to_values`` turns target-space predictions into physical
units; reconciliation, conformal offsets and constraints happen in ``pipeline/predict.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from gramdrishti.data.config import LGBM_BASE, LGBM_DETERMINISM, QUANTILES, RAIN_EVENTS_MM
from gramdrishti.features.table import TARGETS, event_name

STATS = ["mean", "p10", "p50", "p90"]
_QNAME = {0.1: "p10", 0.5: "p50", 0.9: "p90"}


def lgbm_params(overrides: dict | None = None) -> dict:
    """Guide 6.3 defaults plus fixed seeds, with optional overrides (tests use fewer trees)."""
    return {**LGBM_BASE, **LGBM_DETERMINISM, **(overrides or {})}


def fit_var(X: pd.DataFrame, y: np.ndarray, params: dict) -> dict[str, lgb.LGBMRegressor]:
    """Mean model plus one quantile model per level in ``QUANTILES``."""
    models = {"mean": lgb.LGBMRegressor(objective="regression", **params).fit(X, y)}
    for a in QUANTILES:
        models[_QNAME[a]] = lgb.LGBMRegressor(objective="quantile", alpha=a, **params).fit(X, y)
    return models


def fit_event(X: pd.DataFrame, y: np.ndarray, params: dict) -> lgb.LGBMClassifier:
    """Binary classifier for one rain threshold."""
    return lgb.LGBMClassifier(**params).fit(X, y)


@dataclass
class DownscaleModels:
    """All fitted models plus the ordered feature list they expect."""

    features: list[str]
    params: dict
    regressors: dict[str, dict[str, lgb.LGBMRegressor]]
    events: dict[float, lgb.LGBMClassifier]
    isotonic: dict[float, IsotonicRegression] = field(default_factory=dict)

    def predict_raw(self, table: pd.DataFrame) -> pd.DataFrame:
        """Target-space predictions ``<target>_<stat>`` aligned to ``table``'s index."""
        X = table[self.features]
        out = {f"{t}_{s}": self.regressors[t][s].predict(X) for t in self.regressors for s in STATS}
        return pd.DataFrame(out, index=table.index)

    def event_proba(self, table: pd.DataFrame, calibrated: bool = True) -> pd.DataFrame:
        """P(rain >= threshold) per threshold, isotonic-calibrated when available, and non-increasing
        with the threshold."""
        X = table[self.features]
        cols = {}
        for thr in RAIN_EVENTS_MM:
            p = self.events[thr].predict_proba(X)[:, 1]
            if calibrated and thr in self.isotonic:
                p = self.isotonic[thr].predict(p)
            cols[f"prob_{event_name(thr)[3:]}"] = p
        df = pd.DataFrame(cols, index=table.index)
        return df.cummin(axis=1).clip(0.0, 1.0)

    def fit_isotonic(self, table: pd.DataFrame) -> dict[float, IsotonicRegression]:
        """Isotonic calibration of each event classifier on ``table`` (CALIB). Returns the fitted maps."""
        X = table[self.features]
        fitted = {}
        for thr in RAIN_EVENTS_MM:
            raw = self.events[thr].predict_proba(X)[:, 1]
            iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
            fitted[thr] = iso.fit(raw, table[event_name(thr)].to_numpy())
        return fitted


def fit_downscale(train: pd.DataFrame, features: list[str], params: dict,
                  targets: list[str] = TARGETS, events: bool = True) -> DownscaleModels:
    """Fit every regressor (and optionally the event classifiers) on a TRAIN table."""
    X = train[features]
    regs = {t: fit_var(X, train[f"y_{t}"].to_numpy(), params) for t in targets}
    evs = {}
    if events:
        evs = {thr: fit_event(X, train[event_name(thr)].to_numpy(), params) for thr in RAIN_EVENTS_MM}
    return DownscaleModels(features, params, regs, evs)


def fit_mean_only(train: pd.DataFrame, features: list[str], params: dict,
                  targets: list[str] = TARGETS) -> DownscaleModels:
    """Mean models only (leave-one-block-out checks). Quantile slots reuse the mean model."""
    X = train[features]
    regs = {}
    for t in targets:
        m = lgb.LGBMRegressor(objective="regression", **params).fit(X, train[f"y_{t}"].to_numpy())
        regs[t] = dict.fromkeys(STATS, m)
    return DownscaleModels(features, params, regs, {})


def to_values(table: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Physical values ``<target>_<stat>`` from target-space predictions (before reconciliation)."""
    out = pd.DataFrame(index=table.index)
    for s in STATS:
        out[f"tmax_{s}"] = table["b1_tmax"] + raw[f"tmax_{s}"]
        out[f"tmin_{s}"] = table["b1_tmin"] + raw[f"tmin_{s}"]
        out[f"td_{s}"] = table["b1_td"] + raw[f"td_{s}"]
        out[f"wind_{s}"] = table["b1_wind"] * np.exp(raw[f"wind_{s}"])
        out[f"rain_{s}"] = np.maximum(raw[f"rain_{s}"], 0.0)
    return out
