"""Write ``docs/thresholds_for_expert_review.md``: every placeholder threshold, for a KVK or SAU expert.

Run: ``cd backend && python -m gramdrishti.advisory.expert_table``

The document is generated from ``rules.yaml``, ``templates.yaml``, the crop calendar and the agro-variable
constants, so it always matches what the engine uses; a test fails when the committed file is stale.
"""

from __future__ import annotations

import math

from gramdrishti.advisory.rules import RuleFile, TemplateFile, Threshold, load_checked
from gramdrishti.agro import derived
from gramdrishti.data import loaders
from gramdrishti.data.config import ROOT

OUT = ROOT / "docs" / "thresholds_for_expert_review.md"
BLANK = "| |"  # the expert's value and source columns


def _v(x: float) -> str:
    return f"{x:g}"


def _cell(text: object) -> str:
    return str(text).replace("|", "/").replace("\n", " ")


def _row(*cells: object) -> str:
    return "| " + " | ".join(_cell(c) for c in cells) + " " + BLANK


def _threshold_rows(where: str, items: dict[str, Threshold]) -> list[str]:
    return [_row(where, f"`{name}`", _v(t.value), t.unit, t.meaning) for name, t in items.items()]


def _rules_section(rf: RuleFile, tf: TemplateFile) -> list[str]:
    lines = ["## 1. Advisory rules (`backend/gramdrishti/advisory/rules.yaml`)", "",
             "Each row is one number inside a rule. Rules without their own numbers use the crop calendar "
             "(section 5) or the spray planner (section 2); they are listed in section 1b.", "",
             "| Rule | Threshold | Current value | Unit | What it means | Expert value | Source |",
             "|---|---|---|---|---|---|---|"]
    for r in rf.rules:
        lines += _threshold_rows(f"`{r.id}`", r.thresholds)
    lines += ["", "### 1b. What each rule does", "",
              "| Rule | Advice (category, base priority) | Fires when | Numbers it uses "
              "| Advice text (English) |",
              "|---|---|---|---|---|"]
    for r in rf.rules:
        uses = ", ".join(f"`{n}`" for n in r.thresholds) or "none of its own"
        cal = [n for n in ("tmax_alert_c", "tmin_alert_c", "drought_sensitivity", "waterlog_sensitivity",
                           "topdress_stage", "pest_watch_stage") if n in r.when]
        if cal:
            uses += "; calendar: " + ", ".join(f"`{n}`" for n in cal)
        if "spray_d1" in r.when:
            uses += "; spray planner (section 2)"
        lines.append(f"| `{r.id}` | {r.category}, {r.priority} | `{_cell(r.when)}` | {uses} | "
                     f"{_cell(tf.templates[r.template].action.en)} |")
    return lines


def _calendar_section() -> list[str]:
    cal = loaders.load_calendar()
    lines = ["## 5. Crop calendar (`data/crop_calendar_PLACEHOLDER.csv`)", "",
             "Stages by days after sowing (DAS) and the stage alerts used by the heat and frost rules "
             "and the risk map. Empty cells mean the rule does not apply at that stage. Sensitivities "
             "raise or lower an advisory's priority by one level (high / low).", "",
             "| Crop | Stage | DAS from | DAS to | Heat alert (C) | Cold alert (C) | Drought sensitivity | "
             "Waterlogging sensitivity | Key operations | Expert values | Source |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]

    def num(x: object) -> str:
        return "" if x is None or (isinstance(x, float) and math.isnan(x)) else _v(float(x))  # type: ignore[arg-type]

    for r in cal.itertuples(index=False):
        lines.append("| " + " | ".join(_cell(c) for c in (
            r.crop, r.stage, r.das_start, r.das_end, num(r.tmax_alert_c), num(r.tmin_alert_c),
            r.drought_sensitivity, r.waterlog_sensitivity, r.key_operations)) + " " + BLANK)
    crops = sorted(set(loaders.load_crops()["crop"]) - set(cal["crop"]))
    if crops:
        lines += ["", f"Crops in the mock crop table with no calendar rows (no stage, no stage alerts): "
                      f"{', '.join(crops)}."]
    return lines


def _agro_section() -> list[str]:
    d = derived
    rows = [
        ("Effective rain", "`RUNOFF_ABOVE_MM`", _v(d.RUNOFF_ABOVE_MM), "mm",
         "Rain above this on one day runs off and does not enter the soil."),
        ("Soil water", "`ROOT_DEPTH_M`", _v(d.ROOT_DEPTH_M), "m",
         "Root-zone depth: capacity = water holding x depth."),
        ("Soil water", "`STRESS_P`", _v(d.STRESS_P), "fraction",
         "Crop water use falls once soil water drops below this share of capacity (FAO-56 p)."),
        ("Crop coefficient", "`KC_BASE`, `KC_NDVI`", f"{_v(d.KC_BASE)}, {_v(d.KC_NDVI)}", "",
         "kc = KC_BASE + KC_NDVI x NDVI (no crop-specific kc yet)."),
        ("Crop coefficient", "`KC_DEFAULT`", _v(d.KC_DEFAULT), "", "kc when NDVI is missing."),
        ("Waterlogging", "`WATERLOG_WEIGHTS`",
         ", ".join(f"{k} {_v(v)}" for k, v in d.WATERLOG_WEIGHTS.items()), "",
         "Score = P(rain >= 35 mm) x drainage weight x soil wetness weight."),
        ("Waterlogging", "`WATERLOG_CUTS`", ", ".join(_v(c) for c in d.WATERLOG_CUTS), "score",
         "Score cuts for moderate, high and severe in the forecast panel."),
        ("Waterlogging", "`WATERLOG_FULL_FRAC`", _v(d.WATERLOG_FULL_FRAC), "fraction",
         "Soil counts as full above this share of capacity (Guide 8)."),
        ("Frost (forecast panel)", "`FROST_C`", _v(d.FROST_C), "C",
         "Generic frost threshold for the frost level in the forecast panel."),
        ("Frost (forecast panel)", "`FROST_CUTS`", ", ".join(_v(c) for c in d.FROST_CUTS), "probability",
         "Chance of frost cuts for moderate, high and severe."),
        ("Fog proxy", "`FOG_TMIN_C`, `FOG_RH_PCT`, `FOG_WIND_KMH`",
         f"{_v(d.FOG_TMIN_C)}, {_v(d.FOG_RH_PCT)}, {_v(d.FOG_WIND_KMH)}", "C, %, km/h",
         "December-January day with Tmin at most, RH at least and wind at most these values."),
        ("Dry day", "`DRY_PROB`", _v(d.DRY_PROB), "probability",
         "A forecast day counts as dry when the chance of 1 mm or more is below this (Guide 8)."),
        ("Growing degree days", "`TBASE_C`", ", ".join(f"{k} {_v(v)}" for k, v in d.TBASE_C.items()), "C",
         "Base temperature per crop."),
    ]
    lines = ["## 6. Agro-variables (`backend/gramdrishti/agro/derived.py`)", "",
             "Numbers inside the soil water, waterlogging, frost and fog calculations that feed the rules.",
             "",
             "| Quantity | Constant | Current value | Unit | What it means | Expert value | Source |",
             "|---|---|---|---|---|---|---|"]
    return lines + [_row(*r) for r in rows]


def render(rf: RuleFile, tf: TemplateFile) -> str:
    """The whole document as Markdown."""
    n_rules = sum(len(r.thresholds) for r in rf.rules)
    lines = [
        "# Thresholds for expert review", "",
        "This file is for the KVK or SAU agrometeorology expert who reviews GramDrishti's advisory rules. "
        "It is generated from the code by `cd backend && python -m gramdrishti.advisory.expert_table`; do "
        "not edit it by hand.", "",
        "**Every number below is a placeholder chosen by the development team, not by an agronomist.** The "
        "prototype runs on synthetic data, and every advisory it drafts says `thresholds_status: "
        "placeholder` until these numbers are reviewed.", "",
        "How to review:",
        "1. For each row, write the value you recommend in **Expert value** (or \"ok\" to keep it) and the "
        "reference in **Source** (a publication, a KVK or SAU recommendation, or \"expert judgement\").",
        "2. Note any rule that should not exist, is missing, or needs a different condition.",
        "3. Return the file. The team copies each value into `rules.yaml` (or the calendar), fills `source`, "
        "and sets `thresholds_status: reviewed` on that rule.", "",
        f"Counts: {len(rf.rules)} rules with {n_rules} rule thresholds, "
        f"{len(rf.spray_planner)} spray-planner thresholds, {len(rf.risk)} risk types, the crop calendar "
        f"and {len(rf.context)} general settings.",
        "Probabilities are written 0 to 1 (0.35 means 35 %). Rain in mm, temperature in C, wind in km/h. "
        "\"Upper estimate\" is the forecast's 90th percentile (p90), \"lower estimate\" its 10th (p10).", "",
    ]
    lines += _rules_section(rf, tf)
    lines += ["", "## 2. Spray planner (`spray_planner` in rules.yaml)", "",
              "Rates each forecast day Good, Caution or Avoid for spraying. Whole days only: the data is "
              "daily, so the prototype cannot give hour-level spray windows.", "",
              "| Setting | Threshold | Current value | Unit | What it means | Expert value | Source |",
              "|---|---|---|---|---|---|---|"]
    lines += _threshold_rows("spray planner", rf.spray_planner)
    lines += ["", "## 3. Risk map and priority list (`risk` in rules.yaml)", "",
              "Each risk type gives a score from 0 to 1. The three cuts turn the score into moderate, high "
              "and severe (below the first cut is low).", "",
              "| Risk type | How the score is made | Cuts (moderate, high, severe) | Expert cuts | Source |",
              "|---|---|---|---|---|"]
    for name, cfg in rf.risk.items():
        lines.append(f"| {name} | {_cell(cfg.score)} | {', '.join(_v(c) for c in cfg.cuts)} {BLANK}")
    extra = {f"{name}": cfg.thresholds for name, cfg in rf.risk.items() if cfg.thresholds}
    lines += ["", "| Risk type | Threshold | Current value | Unit | What it means | Expert value | Source |",
              "|---|---|---|---|---|---|---|"]
    for name, items in extra.items():
        lines += _threshold_rows(name, items)
    c = rf.confidence
    lines += ["", "## 4. Confidence and general settings (rules.yaml)", "",
              "Confidence follows Backend Guide 9.5: score = margin beyond the threshold - lead penalty x "
              "(lead day - 1) - width weight x (forecast spread / reference width).", "",
              "| Setting | Threshold | Current value | Unit | What it means | Expert value | Source |",
              "|---|---|---|---|---|---|---|"]
    lines += _threshold_rows("confidence", {"lead_penalty": c.lead_penalty, "width_weight": c.width_weight,
                                            "high_above": c.high_above, "medium_above": c.medium_above})
    lines += _threshold_rows("reference width", dict(c.reference_width))
    lines += _threshold_rows("context", dict(rf.context))
    lines += [""] + _calendar_section() + [""] + _agro_section() + [""]
    return "\n".join(lines)


def main() -> None:
    """Write the document."""
    rf, tf = load_checked()
    OUT.write_text(render(rf, tf), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

