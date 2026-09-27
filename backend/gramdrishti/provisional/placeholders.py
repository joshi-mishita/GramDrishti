"""PLACEHOLDER content for endpoints whose real producers come in later sessions.

- Verification and impact (S10): numbers are drawn from a seeded random generator so the frontend can build
  its tables and charts. They are NOT results. Every payload carries ``provenance: "placeholder"`` and a note
  saying so, and they are only ever served with ``data_mode: "mock"``.
- Explain (S10 SHAP): a static-contrast heuristic, not a model explanation. It ranks the Panchayat's static
  features by how far they are from the block mean (z-score) and attaches a direction from a small table of
  physical priors. ``method`` says ``placeholder_static_contrast``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gramdrishti.data.config import VARS, WINDOWS
from gramdrishti.provisional.texts import FEATURE_TEXT, IMPACT_RULES

SEED = 20240716
PLACEHOLDER_NOTE = ("PLACEHOLDER: generated numbers for building the screens. Not verification results. "
                    "The verification job (S10) replaces them.")
PROXY_NOTE = "Proxy validation on synthetic truth. Real-station validation follows when data is available."
UNITS = {"rain": "mm", "tmax": "C", "tmin": "C", "rh": "%", "wind": "km/h"}
TYPICAL_MAE = {"rain": 4.0, "tmax": 1.2, "tmin": 1.1, "rh": 6.0, "wind": 2.0}
EVENTS = ["rain_ge_1mm", "rain_ge_2_5mm", "rain_ge_10mm", "rain_ge_35mm"]
IMPACT_SEASONS = {"monsoon_2024": ("2024-07-16", "2024-09-30"),
                  "post_monsoon_2024": ("2024-10-01", "2024-11-30"),
                  "test_2024": WINDOWS["TEST"]}


def _stable_rng(label: str) -> np.random.Generator:
    """Seed from the label's bytes (``hash`` is salted per process, so it is not used)."""
    return np.random.default_rng([SEED, *label.encode()])


def _r(x: float, nd: int = 2) -> float:
    return round(float(x), nd)


def verification_summary() -> dict:
    """Seeded placeholder for /verification/summary."""
    rng = _stable_rng("summary")
    variables = []
    for var in VARS:
        metrics = []
        for name, scale in (("MAE", 1.0), ("RMSE", 1.35)):
            b0 = TYPICAL_MAE[var] * scale * rng.uniform(0.9, 1.1)
            b1 = b0 * rng.uniform(0.85, 1.0)
            b2 = b1 * rng.uniform(0.95, 1.02)
            model = b1 * rng.uniform(0.8, 1.05)
            skill = 1 - model / b0
            half = rng.uniform(0.02, 0.06)
            metrics.append({"name": name, "unit": UNITS[var], "model": _r(model), "b0": _r(b0), "b1": _r(b1),
                            "b2": _r(b2), "skill_vs_b0": _r(skill, 3),
                            "skill_ci95": [_r(skill - half, 3), _r(skill + half, 3)]})
        variables.append({"var": var, "n": int(rng.integers(12000, 15000)), "metrics": metrics})
    events = []
    for ev in EVENTS:
        pod = rng.uniform(0.5, 0.85)
        far = rng.uniform(0.15, 0.45)
        events.append({"event": ev, "pod": _r(pod, 3), "far": _r(far, 3),
                       "csi": _r(1 / (1 / pod + 1 / (1 - far) - 1), 3),
                       "brier": _r(rng.uniform(0.04, 0.15), 3),
                       "brier_skill_vs_climatology": _r(rng.uniform(-0.05, 0.3), 3)})
    return {"method": "leave_one_block_out + temporal_holdout",
            "period": {"start": WINDOWS["TEST"][0], "end": WINDOWS["TEST"][1]},
            "variables": variables, "events": events,
            "block_mean_error": {v: _r(rng.uniform(0, 1e-6), 9) for v in VARS},
            "notes": [PLACEHOLDER_NOTE, PROXY_NOTE]}


def reliability(event: str) -> dict:
    """Seeded placeholder reliability points for one rain event (10 bins)."""
    rng = _stable_rng(f"reliability-{event}")
    points = []
    for i in range(10):
        fp = (i + 0.5) / 10
        points.append({"forecast_prob": _r(fp), "observed_freq": _r(np.clip(fp + rng.normal(0, 0.06), 0, 1)),
                       "n": int(rng.integers(40, 900) * (1.0 - 0.08 * i))})
    return {"event": event, "points": points, "notes": [PLACEHOLDER_NOTE, PROXY_NOTE]}


def coverage() -> dict:
    """Seeded placeholder for nominal 80% interval coverage per variable."""
    rng = _stable_rng("coverage")
    items = [{"var": v, "unit": UNITS[v], "nominal": 0.8, "empirical": _r(rng.uniform(0.7, 0.88)),
              "mean_width": _r(TYPICAL_MAE[v] * rng.uniform(2.2, 3.2)), "n": int(rng.integers(12000, 15000))}
             for v in VARS]
    return {"items": items, "notes": [PLACEHOLDER_NOTE, PROXY_NOTE]}


def regions(block_ids: list[str]) -> dict:
    """Seeded placeholder error per held-out block for rain and tmax."""
    rng = _stable_rng("regions")
    items = []
    for b in block_ids:
        for v in ("rain", "tmax"):
            b0 = TYPICAL_MAE[v] * rng.uniform(0.85, 1.15)
            items.append({"region_type": "block", "region_id": b, "var": v, "metric": "MAE", "unit": UNITS[v],
                          "model": _r(b0 * rng.uniform(0.8, 1.05)), "b0": _r(b0),
                          "n": int(rng.integers(2000, 2600))})
    return {"method": "leave_one_block_out", "items": items, "notes": [PLACEHOLDER_NOTE, PROXY_NOTE]}


def impact(season: str, decision: str, n_panchayats: int) -> dict:
    """Seeded placeholder counts for one decision replayed over a season."""
    start, end = IMPACT_SEASONS[season]
    n = n_panchayats * ((pd.Timestamp(end) - pd.Timestamp(start)).days + 1)
    rng = _stable_rng(f"impact-{season}-{decision}")

    def split(correct_share: float) -> dict[str, int]:
        correct = int(n * correct_share)
        wasted = int((n - correct) * rng.uniform(0.3, 0.7))
        return {"correct": correct, "wasted_wait": wasted, "washed_off": n - correct - wasted}

    block_share = rng.uniform(0.7, 0.85)
    model_rule, block_rule = IMPACT_RULES[decision]
    return {"season": season, "decision": decision, "n_decisions": n,
            "model": split(min(block_share + rng.uniform(-0.02, 0.08), 0.98)),
            "block_baseline": split(block_share),
            "rule": {"model": {"en": model_rule}, "block": {"en": block_rule}},
            "notes": [PLACEHOLDER_NOTE,
                      "Counts and rates only. No money values until an expert supplies costs."]}


# ---------------------------------------------------------------- explain
# Direction when the Panchayat's feature is ABOVE its block mean (physical priors, placeholder).
EFFECT_IF_HIGHER = {
    "elevation_m": {"tmax": "cooler", "tmin": "cooler", "rain": "wetter"},
    "irrigated_frac": {"tmax": "cooler", "rh": "more_humid"},
    "urban_frac": {"tmax": "warmer", "tmin": "warmer", "rh": "less_humid"},
    "water_frac": {"tmax": "cooler", "rh": "more_humid"},
    "tree_frac": {"tmax": "cooler", "wind": "calmer"},
    "tpi_z": {"tmin": "warmer", "wind": "windier"},
}
FLIP = {"warmer": "cooler", "cooler": "warmer", "wetter": "drier", "drier": "wetter",
        "more_humid": "less_humid", "less_humid": "more_humid", "windier": "calmer", "calmer": "windier"}
MIN_Z = 0.25


def explain_reasons(static: pd.DataFrame, panchayat_id: str, var: str, top: int = 3) -> list[dict]:
    """Top static features that set this Panchayat apart from its block, with a prior direction."""
    row = static.set_index("panchayat_id").loc[panchayat_id]
    block = static[static["block_id"] == row["block_id"]]
    cands = []
    for feat, effects in EFFECT_IF_HIGHER.items():
        if var not in effects:
            continue
        sd = block[feat].std() or 1.0
        z = (row[feat] - block[feat].mean()) / sd
        if abs(z) >= MIN_Z:
            cands.append((abs(z), feat, z))
    reasons = []
    for _, feat, z in sorted(cands, key=lambda c: (-c[0], c[1]))[:top]:
        higher = z > 0
        effect = EFFECT_IF_HIGHER[feat][var] if higher else FLIP[EFFECT_IF_HIGHER[feat][var]]
        reasons.append({"feature": feat, "effect": effect, "text": FEATURE_TEXT[feat][0 if higher else 1]})
    return reasons
