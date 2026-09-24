"""Block-level bias correction of the NWP sources (Backend Guide 5.1).

- tmax, tmin, rh: additive mean bias per source, lead day and season group.
- wind: multiplicative ratio per source and lead day.
- rain: empirical quantile mapping on wet days after matching wet-day frequency, fitted
  separately for monsoon (Jun-Sep) and the other months, per source and lead day.
- sources are combined with weights proportional to 1 / MSE per variable and lead day.

Fitting reads only rows whose valid date lies inside the fitting window (TRAIN by default).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from gramdrishti.data import loaders
from gramdrishti.data.config import (
    COLS,
    RAIN_WET_MM,
    data_mode,
    rain_season,
    season_group,
    select_window,
    window_bounds,
)

KEYS = ["block_id", "issue_date", "valid_date", "lead_day"]
ADDITIVE = [COLS["tmax"], COLS["tmin"], COLS["rh"]]
WIND = COLS["wind"]
RAIN = COLS["rain"]
VALUE_COLS = list(COLS.values())


# ---------------------------------------------------------------- quantile mapping
def fit_qm(fc: np.ndarray, obs: np.ndarray, n: int = 99) -> tuple[np.ndarray, np.ndarray]:
    """Forecast and observed quantiles at ``n`` evenly spaced levels between 0.01 and 0.99."""
    qs = np.linspace(0.01, 0.99, n)
    return np.quantile(fc, qs), np.quantile(obs, qs)


def apply_qm(x: np.ndarray, fq: np.ndarray, oq: np.ndarray) -> np.ndarray:
    """Map ``x`` through the quantile pairs; flat extrapolation outside the fitted range."""
    return np.interp(x, fq, oq)


def fit_rain_qm(fc: np.ndarray, obs: np.ndarray, wet_thr: float = RAIN_WET_MM) -> dict:
    """Fit wet-day frequency matching plus quantile mapping of wet-day amounts.

    ``cut`` is the forecast amount above which the forecast is wet as often as the observations.
    """
    fc, obs = np.asarray(fc, dtype=float), np.asarray(obs, dtype=float)
    wet_freq = float((obs >= wet_thr).mean())
    if wet_freq == 0.0 or not (fc > 0).any():
        return {"cut": float("inf"), "wet_freq": wet_freq, "qm": None}
    cut = float(np.quantile(fc, 1.0 - wet_freq))
    if cut <= 0.0:
        # Forecast is dry more often than observed: every positive forecast counts as wet.
        cut = float(fc[fc > 0].min())
    wet_fc = fc[fc >= cut]
    return {"cut": cut, "wet_freq": wet_freq, "qm": fit_qm(wet_fc, obs[obs >= wet_thr])}


def apply_rain_qm(x: np.ndarray, params: dict) -> np.ndarray:
    """Apply ``fit_rain_qm`` parameters: below ``cut`` becomes 0, above is quantile mapped. NaN stays NaN."""
    x = np.asarray(x, dtype=float)
    y = np.where(np.isnan(x), np.nan, 0.0)
    if params["qm"] is None:
        return y
    m = x >= params["cut"]
    y[m] = apply_qm(x[m], *params["qm"])
    return y


# ---------------------------------------------------------------- reference target
def block_reference(
    obs_clean: pd.DataFrame | None = None, stations: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Daily block reference (date, block_id, value columns) used as the bias-correction target.

    Mock: the synthetic block truth (proxy target, MOCK ONLY, never a feature).
    Real: block mean of QC-cleaned station observations.
    """
    if data_mode() == "mock":
        return loaders.load_block_truth()  # MOCK ONLY: proxy training target
    if obs_clean is None or stations is None:
        raise ValueError("Real mode needs QC-cleaned observations and station metadata.")
    m = obs_clean.merge(stations[["station_id", "block_id"]], on="station_id")
    return m.groupby(["date", "block_id"], as_index=False)[VALUE_COLS].mean()


# ---------------------------------------------------------------- fitted model
@dataclass
class BiasModel:
    """Fitted bias-correction parameters and the dates they were fitted on."""

    window: str
    fit_start: pd.Timestamp
    fit_end: pd.Timestamp
    data_max_date: pd.Timestamp   # latest valid date actually used in fitting
    additive: pd.DataFrame        # col, source, lead_day, season, offset (forecast minus reference)
    wind_ratio: pd.DataFrame      # source, lead_day, ratio (reference / forecast)
    rain_qm: dict[tuple[str, int, str], dict] = field(default_factory=dict)
    weights: pd.DataFrame = field(default_factory=pd.DataFrame)  # col, source, lead_day, weight


def pair_with_reference(fc: pd.DataFrame, ref: pd.DataFrame) -> pd.DataFrame:
    """Join forecasts to the reference on block and valid date; reference columns get ``ref_`` prefix."""
    r = ref[["date", "block_id", *VALUE_COLS]].rename(columns={"date": "valid_date"})
    r = r.rename(columns={c: f"ref_{c}" for c in VALUE_COLS})
    return fc.merge(r, on=["block_id", "valid_date"], how="inner")


def fit_bias(fc: pd.DataFrame, ref: pd.DataFrame, window: str = "TRAIN") -> BiasModel:
    """Fit all bias-correction parameters on rows whose valid date is inside ``window``."""
    start, end = window_bounds(window)
    fc_w = select_window(fc, window, "valid_date")
    ref_w = select_window(ref, window, "date")
    pairs = pair_with_reference(fc_w, ref_w)
    data_max = pairs["valid_date"].max()
    assert data_max <= end and pairs["issue_date"].max() <= end, "bias fitting read data after its window"
    pairs["season"] = season_group(pairs["valid_date"]).to_numpy()
    pairs["rain_season"] = rain_season(pairs["valid_date"]).to_numpy()

    additive = []
    for col in ADDITIVE:
        d = pairs.assign(err=pairs[col] - pairs[f"ref_{col}"]).dropna(subset=["err"])
        g = d.groupby(["source", "lead_day", "season"], as_index=False)["err"].mean()
        additive.append(g.rename(columns={"err": "offset"}).assign(col=col))
    additive_df = pd.concat(additive, ignore_index=True)

    w = pairs.dropna(subset=[WIND, f"ref_{WIND}"])
    wind = w.groupby(["source", "lead_day"]).agg(fc=(WIND, "sum"), ref=(f"ref_{WIND}", "sum")).reset_index()
    wind["ratio"] = np.where(wind["fc"] > 0, wind["ref"] / wind["fc"].where(wind["fc"] > 0, 1.0), 1.0)

    rain_qm = {}
    r = pairs.dropna(subset=[RAIN, f"ref_{RAIN}"])
    for (src, lead, season), g in r.groupby(["source", "lead_day", "rain_season"]):
        params = fit_rain_qm(g[RAIN].to_numpy(), g[f"ref_{RAIN}"].to_numpy())
        rain_qm[(str(src), int(lead), str(season))] = params

    model = BiasModel(window, start, end, data_max, additive_df,
                      wind[["source", "lead_day", "ratio"]], rain_qm)
    model.weights = _inverse_mse_weights(apply_bias(pairs, model))
    return model


def apply_bias(fc: pd.DataFrame, model: BiasModel) -> pd.DataFrame:
    """Bias-corrected copy of per-source forecasts. Unknown groups fall back to no correction."""
    out = fc.copy()
    seasons = season_group(out["valid_date"]).to_numpy()
    for col in ADDITIVE:
        off = model.additive[model.additive["col"] == col]
        keys = pd.DataFrame({"source": out["source"].to_numpy(), "lead_day": out["lead_day"].to_numpy(),
                             "season": seasons})
        o = keys.merge(off, on=["source", "lead_day", "season"], how="left")["offset"].fillna(0.0)
        out[col] = out[col].to_numpy() - o.to_numpy()
    out[COLS["rh"]] = out[COLS["rh"]].clip(0, 100)

    keys = out[["source", "lead_day"]].reset_index(drop=True)
    ratio = keys.merge(model.wind_ratio, on=["source", "lead_day"], how="left")["ratio"].fillna(1.0)
    out[WIND] = out[WIND].to_numpy() * ratio.to_numpy()

    rs = rain_season(out["valid_date"]).to_numpy()
    rain = out[RAIN].to_numpy(dtype=float).copy()
    for (src, lead, season), params in model.rain_qm.items():
        m = (out["source"].to_numpy() == src) & (out["lead_day"].to_numpy() == lead) & (rs == season)
        rain[m] = apply_rain_qm(rain[m], params)
    out[RAIN] = rain
    return out


def _inverse_mse_weights(corrected_pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in VALUE_COLS:
        se = (corrected_pairs[col] - corrected_pairs[f"ref_{col}"]) ** 2
        mse = corrected_pairs.assign(se=se).dropna(subset=["se"]).groupby(["source", "lead_day"])["se"].mean()
        inv = 1.0 / mse.clip(lower=1e-9)
        wts = inv / inv.groupby(level="lead_day").transform("sum")
        rows.append(wts.rename("weight").reset_index().assign(col=col))
    return pd.concat(rows, ignore_index=True)[["col", "source", "lead_day", "weight"]]


def combine_sources(fc: pd.DataFrame, weights: pd.DataFrame | None = None) -> pd.DataFrame:
    """One block forecast per (block, issue, valid, lead): weighted mean over sources plus source spread.

    ``weights=None`` gives the plain mean (baseline B0). Missing sources are skipped and weights renormalised.
    """
    long = fc.melt(id_vars=[*KEYS, "source"], value_vars=VALUE_COLS, var_name="col", value_name="value")
    long = long.dropna(subset=["value"])
    if weights is None:
        long["weight"] = 1.0
    else:
        long = long.merge(weights, on=["col", "source", "lead_day"], how="left")
        long["weight"] = long["weight"].fillna(0.0)
    long["wv"] = long["weight"] * long["value"]
    g = long.groupby([*KEYS, "col"]).agg(wv=("wv", "sum"), w=("weight", "sum"),
                                          vmax=("value", "max"), vmin=("value", "min"))
    g["value"] = np.where(g["w"] > 0, g["wv"] / g["w"].where(g["w"] > 0, 1.0), np.nan)
    g["spread"] = g["vmax"] - g["vmin"]
    wide = g["value"].unstack("col")
    spread = g["spread"].unstack("col").add_suffix("_spread")
    out = wide.join(spread).reset_index()
    out.columns.name = None
    return out[[*KEYS, *VALUE_COLS, *[f"{c}_spread" for c in VALUE_COLS]]]
