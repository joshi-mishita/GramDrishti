"""SHAP reasons for the difference between a Panchayat and its block (Backend Guide section 13).

``shap.TreeExplainer`` on each variable's mean model (RH uses the dew point model, since RH is
derived from dew point). A Panchayat's forecast is its block forecast plus the model's departure;
reconciliation removes the block average of that departure. So we explain the *contrast*
SHAP(Panchayat) - mean SHAP(Panchayats of the same block, issue date and lead day): the contrasts sum
to the Panchayat's departure from the block average of the model (exactly for the additive
variables), and features with one value per block largely cancel.

Related features are summed into one group (for example ``irrigated_frac`` and ``irrigated_frac_rel``)
so a reason never appears twice. SHAP values are additive, so group sums are valid.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap

from gramdrishti.data.config import VARS
from gramdrishti.explain import texts
from gramdrishti.models.downscale import DownscaleModels

TOP_K = 3
# Below these differences (served mean minus corrected block forecast) there is nothing to explain,
# for example rain on a block forecast of 0 mm, where reconciliation sets every Panchayat to 0.
NEGLIGIBLE_DELTA = {"rain": 0.05, "tmax": 0.01, "tmin": 0.01, "rh": 0.1, "wind": 0.01}
MODEL_FOR_VAR = {"rain": "rain", "tmax": "tmax", "tmin": "tmin", "rh": "td", "wind": "wind"}
GROUP_KEYS = ["issue_date", "lead_day", "block_id"]

# group -> (features, representative feature for the direction, kind)
GROUPS: dict[str, tuple[list[str], str | None, str]] = {
    "position_ns": (["lat", "dlat_block"], "lat", "numeric"),
    "position_ew": (["lon", "dlon_block"], "lon", "numeric"),
    "elevation": (["elevation_m", "elevation_m_rel"], "elevation_m", "numeric"),
    "tpi": (["tpi_z", "tpi_z_rel"], "tpi_z", "numeric"),
    "slope": (["slope_deg"], "slope_deg", "numeric"),
    "irrigated": (["irrigated_frac", "irrigated_frac_rel"], "irrigated_frac", "numeric"),
    "canal_distance": (["canal_dist_km"], "canal_dist_km", "numeric"),
    "cropland": (["cropland_frac"], "cropland_frac", "numeric"),
    "urban": (["urban_frac", "urban_frac_rel"], "urban_frac", "numeric"),
    "water": (["water_frac", "water_frac_rel"], "water_frac", "numeric"),
    "trees": (["tree_frac", "tree_frac_rel"], "tree_frac", "numeric"),
    "clay": (["clay_pct"], "clay_pct", "numeric"),
    "sand": (["sand_pct", "sand_pct_rel"], "sand_pct", "numeric"),
    "silt": (["silt_pct"], "silt_pct", "numeric"),
    "water_holding": (["whc_mm_per_m"], "whc_mm_per_m", "numeric"),
    "drainage": (["drainage_class_code"], "drainage_class", "category"),
    "soil_texture": (["soil_texture_code"], "soil_texture", "category"),
    "vegetation": (["ndvi", "ndvi_rel"], "ndvi", "numeric"),
    "greening": (["ndvi_trend"], "ndvi_trend", "numeric"),
    "land_surface_temp": (["lst_day_c", "lst_rel"], "lst_day_c", "numeric"),
    "satellite_age": (["ndvi_age_days", "lst_age_days"], None, "block"),
    "season": (["doy_sin", "doy_cos", "month"], None, "block"),
    "lead_day": (["lead_day"], None, "block"),
    "block_forecast": ([*[f"{p}_{v}" for p in ("b1", "spread", "chg") for v in VARS], "b1_td"], None,
                       "block"),
    "recent_rain": (["stn_rain_prev3_mm", "stn_rain_prev7_mm"], None, "block"),
}


def check_groups(features: list[str]) -> None:
    """Every model feature belongs to exactly one group."""
    grouped = [f for feats, _, _ in GROUPS.values() for f in feats]
    missing, extra = set(features) - set(grouped), set(grouped) - set(features)
    if missing or extra or len(grouped) != len(set(grouped)):
        raise ValueError(f"explain groups out of date: missing {sorted(missing)}, unknown {sorted(extra)}")


def shap_contrasts(models: DownscaleModels, table: pd.DataFrame, var: str) -> pd.DataFrame:
    """Per row of ``table`` and feature group: SHAP value minus its block average. Columns = groups."""
    check_groups(models.features)
    X = table[models.features]
    sv = shap.TreeExplainer(models.regressors[MODEL_FOR_VAR[var]]["mean"]).shap_values(X)
    per_feat = pd.DataFrame(sv, columns=models.features, index=table.index)
    keys = [table[k] for k in GROUP_KEYS]
    contrast = per_feat - per_feat.groupby(keys).transform("mean")
    return pd.DataFrame({g: contrast[feats].sum(axis=1) for g, (feats, _, _) in GROUPS.items()})


def directions(table: pd.DataFrame) -> pd.DataFrame:
    """+1 / -1 / 0: the group's representative value above, below or equal to the block average."""
    out = {}
    keys = [table[k] for k in GROUP_KEYS]
    for g, (_, rep, kind) in GROUPS.items():
        if kind != "numeric":
            out[g] = np.zeros(len(table), dtype=int)
            continue
        diff = table[rep] - table[rep].groupby(keys).transform("mean")
        out[g] = np.sign(diff.round(9)).fillna(0).astype(int).to_numpy()
    return pd.DataFrame(out, index=table.index)


def top_reasons(models: DownscaleModels, table: pd.DataFrame, static: pd.DataFrame,
                top_k: int = TOP_K) -> pd.DataFrame:
    """Long table: issue_date, lead_day, panchayat_id, block_id, var, rank, feature (group), contribution
    (target-model units), direction, effect, text_en. ``top_k`` rows per (Panchayat, lead day, var)."""
    cats = static.set_index("panchayat_id")[["drainage_class", "soil_texture"]].astype(str)
    dirs = directions(table)
    ids = table[["issue_date", "lead_day", "panchayat_id", "block_id"]]
    rows = []
    for var in VARS:
        c = shap_contrasts(models, table, var)
        vals = c.to_numpy()
        names = np.array(c.columns)
        # Largest |contribution| first; a stable sort breaks ties by group order, so output is deterministic.
        order = np.argsort(-np.abs(vals), axis=1, kind="stable")
        for i, (idx, r) in enumerate(ids.iterrows()):
            for rank, j in enumerate(order[i, :top_k], start=1):
                g, contrib = names[j], float(vals[i, j])
                d = int(dirs.at[idx, g])
                value = cats.at[r["panchayat_id"], GROUPS[g][1]] if GROUPS[g][2] == "category" else None
                rows.append({**r.to_dict(), "var": var, "rank": rank, "feature": g, "contribution": contrib,
                             "direction": d, "effect": texts.effect_for(var, contrib),
                             "text_en": texts.sentence(g, d, var, contrib, value)["en"]})
    return pd.DataFrame(rows)
