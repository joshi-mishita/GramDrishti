"""Advisory engine: rule file schema, one fires / does-not-fire case per rule, spray planner, confidence,
priority, de-duplication, determinism, the expert table, and no language model anywhere."""

from __future__ import annotations

import ast
import json
import tomllib
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from gramdrishti.advisory import engine, expert_table, spray
from gramdrishti.advisory.rules import (
    RULES_PATH,
    SCHEMA_PATH,
    RuleFile,
    check,
    json_schema,
    load_checked,
    load_rules,
    load_templates,
    placeholders,
)
from gramdrishti.advisory.signals import CROP_SIGNALS, LIVESTOCK, Context, any_day
from gramdrishti.data import loaders

ISSUE = date(2024, 9, 9)
PKG = Path(engine.__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def rules():
    return load_checked()


def _ctx(crop: str = "wheat", **over: object) -> Context:
    """A calm, moist, mild context in which no rule fires; ``over`` changes single signals."""
    base: dict[str, object] = {
        "p_rain_1_d1": 0.0, "p_rain_2_5_d1": 0.0, "p_rain_2_5_d2": 0.0, "p_rain_2_5_2d": 0.0,
        "p_rain_10_d1": 0.0, "p_rain_10_3d": 0.0, "p_rain_35_d1": 0.0, "p_rain_35_3d": 0.0,
        "rain_p50_3d": 0.0, "rain_p90_max_3d": 1.0, "tmax_p90_3d": 30.0, "tmin_p10_3d": 12.0,
        "tmean_3d": 22.0, "rh_mean_3d": 55.0, "wind_p90_d1": 5.0, "thi_p90": 70.0, "depletion": 0.2,
        "soil_moisture_start": 0.8,
        "dry_days": 0, "et0_3d": 3.0, "waterlog_score_3d": 0.0, "spray_d1": "good", "spray_d2": "good",
        "spray_days": "", "drain_poor": False, "drainage": "good", "low_lying": False, "texture": "loam",
        "irrigated_frac": 0.5, "month": 9, "crop": crop, "stage": "tillering", "das": 30,
        "days_to_sowing": None, "days_to_harvest": 100, "drought_sensitivity": "medium",
        "waterlog_sensitivity": "medium",
        "tmax_alert_c": 38.0, "tmin_alert_c": 2.0, "topdress_stage": False, "pest_watch_stage": False}
    if crop == LIVESTOCK:
        base |= {k: None for k in CROP_SIGNALS} | {"crop": LIVESTOCK, "topdress_stage": False,
                                                    "pest_watch_stage": False}
    base |= over
    dates = {k: ISSUE + timedelta(days=k) for k in range(1, 6)}
    return Context(ISSUE, "MP0101", "MB01", crop, base, {}, {}, dates, 3)


PRE = {"stage": "pre_sowing", "das": -5, "days_to_sowing": 5, "days_to_harvest": None}
# rule id -> (signals that make it fire, signals just on the other side of a threshold)
CASES: dict[str, tuple[dict, dict]] = {
    "sowing_heavy_rain_wait": (PRE | {"p_rain_35_3d": 0.30}, PRE | {"p_rain_35_3d": 0.29}),
    "sowing_dry_soil": (PRE | {"soil_moisture_start": 0.29}, PRE | {"soil_moisture_start": 0.30}),
    "sowing_go": (PRE | {"soil_moisture_start": 0.30, "p_rain_35_3d": 0.29},
                  PRE | {"soil_moisture_start": 0.30, "p_rain_35_3d": 0.30}),
    "irrigate_now": ({"depletion": 0.55, "p_rain_10_3d": 0.24}, {"depletion": 0.54, "p_rain_10_3d": 0.24}),
    "irrigation_hold_rain": ({"depletion": 0.4, "p_rain_10_3d": 0.5},
                             {"depletion": 0.4, "p_rain_10_3d": 0.49}),
    "spray_hold": ({"spray_d1": "avoid"}, {"spray_d1": "caution", "spray_d2": "avoid"}),
    "fertilizer_postpone": ({"topdress_stage": True, "p_rain_10_d1": 0.4},
                            {"topdress_stage": True, "p_rain_10_d1": 0.39, "waterlog_score_3d": 0.24}),
    "heat_stress_crop": ({"tmax_alert_c": 34.0, "tmax_p90_3d": 34.0},
                         {"tmax_alert_c": 34.0, "tmax_p90_3d": 33.9}),
    "frost_protect": ({"tmin_alert_c": 2.0, "tmin_p10_3d": 2.0}, {"tmin_alert_c": 2.0, "tmin_p10_3d": 2.1}),
    "waterlogging_drain": ({"p_rain_35_3d": 0.3, "drain_poor": True},
                           {"p_rain_35_3d": 0.29, "drain_poor": True}),
    "dry_spell_protect": ({"dry_days": 5, "et0_3d": 4.0, "drought_sensitivity": "high"},
                          {"dry_days": 4, "et0_3d": 4.0, "drought_sensitivity": "high"}),
    "harvest_rain_risk": ({"days_to_harvest": 10, "p_rain_10_3d": 0.4},
                          {"days_to_harvest": 11, "p_rain_10_3d": 0.4}),
    "pest_disease_humid": ({"pest_watch_stage": True, "rh_mean_3d": 80.0, "tmean_3d": 26.0},
                           {"pest_watch_stage": True, "rh_mean_3d": 79.9, "tmean_3d": 26.0}),
    "livestock_heat_severe": ({"thi_p90": 90.0}, {"thi_p90": 89.9}),
    "livestock_heat": ({"thi_p90": 80.0}, {"thi_p90": 79.9}),
}


# ---------------------------------------------------------------- rule file and schema
def test_rule_files_are_valid(rules) -> None:
    rf, tf = rules
    crops = set(loaders.load_crops()["crop"]) | set(loaders.load_calendar()["crop"])
    assert check(rf, tf, crops) == []
    assert rf.thresholds_status == "placeholder"
    for r in rf.rules:
        assert r.thresholds_status == "placeholder" and r.source == "", r.id
        assert r.priority in ("low", "moderate", "high", "severe")


def test_every_category_has_a_rule(rules) -> None:
    from gramdrishti.api.schemas import Category

    assert {r.category for r in rules[0].rules} == {c.value for c in Category}


def test_schema_file_is_current() -> None:
    assert SCHEMA_PATH.read_text(encoding="utf-8") == json_schema(), \
        "rules.schema.json is stale: run `python -m gramdrishti.advisory.rules`"


def test_every_rule_threshold_has_a_comment_for_the_expert() -> None:
    """The YAML carries a meaning for every number (the expert table is built from it)."""
    raw = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    for r in raw["rules"]:
        for name, t in r["thresholds"].items():
            assert len(t["meaning"]) >= 10 and t["unit"], (r["id"], name)


@pytest.mark.parametrize("change, message", [
    ({"when": "depletion >= made_up_signal"}, "unknown names"),
    ({"when": "__import__('os')"}, "unknown names"),
    ({"source": "Some paper"}, "placeholder rule must have an empty source"),
    ({"thresholds_status": "reviewed", "source": ""}, "reviewed rule needs a source"),
    ({"template": "no_such_template"}, "does not exist"),
    ({"evidence": ["made_up"]}, "unknown evidence signal"),
    ({"priority": "urgent"}, "priority"),
    ({"category": "weather"}, "category"),
])
def test_invalid_rules_are_rejected(change: dict, message: str) -> None:
    raw = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    raw["rules"][0].update(change)
    tf = load_templates()
    try:
        errors = check(RuleFile.model_validate(raw), tf)
    except Exception as e:  # noqa: BLE001 - schema errors are pydantic ValidationErrors
        errors = [str(e)]
    assert any(message in e for e in errors), errors


def test_unused_threshold_is_an_error() -> None:
    raw = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    raw["rules"][0]["thresholds"]["spare"] = {"value": 1, "unit": "x", "meaning": "an unused number here"}
    assert any("not used" in e for e in check(RuleFile.model_validate(raw), load_templates()))


def test_templates_cover_calendar_stages_and_crops(rules) -> None:
    _, tf = rules
    assert set(loaders.load_calendar()["stage"]) <= set(tf.stages)
    assert set(loaders.load_crops()["crop"]) <= set(tf.crops)
    assert tf.translation_status == "needs_native_review"
    for tpl in tf.templates.values():
        for part in ("action", "reason", "fallback"):
            for lang in ("en", "hi", "pa"):
                assert getattr(getattr(tpl, part), lang).strip()
    assert "{" not in "".join(placeholders(tf.no_good_spray_day.en))


# ---------------------------------------------------------------- one case per rule
def test_every_rule_has_a_case(rules) -> None:
    assert set(CASES) == {r.id for r in rules[0].rules}


def test_calm_context_fires_nothing(rules) -> None:
    rf, _ = rules
    for crop in ("wheat", LIVESTOCK):
        ctx = _ctx(crop)
        fired = [r.id for r in rf.rules if engine.applies(r, ctx) and engine.evaluate(r, ctx)]
        assert fired == [], (crop, fired)


@pytest.mark.parametrize("rule_id", sorted(CASES))
def test_rule_fires_and_does_not_fire(rules, rule_id: str) -> None:
    rf, _ = rules
    rule = rf.rule(rule_id)
    crop = LIVESTOCK if rule.crop == LIVESTOCK else "wheat"
    fire, miss = CASES[rule_id]
    assert engine.evaluate(rule, _ctx(crop, **fire)) is True
    assert engine.evaluate(rule, _ctx(crop, **miss)) is False


def test_stage_and_sensitivity_gates(rules) -> None:
    rf, _ = rules
    assert not engine.evaluate(rf.rule("irrigate_now"),
                               _ctx(depletion=0.9, p_rain_10_3d=0.0, drought_sensitivity="low"))
    assert not engine.evaluate(rf.rule("sowing_heavy_rain_wait"), _ctx(p_rain_35_3d=0.9))  # already sown
    assert not engine.evaluate(rf.rule("waterlogging_drain"),
                               _ctx(p_rain_35_3d=0.9, drain_poor=True, waterlog_sensitivity="low"))
    assert engine.evaluate(rf.rule("waterlogging_drain"), _ctx(p_rain_35_3d=0.9, low_lying=True))


def test_low_lying_frost_margin(rules) -> None:
    rule = rules[0].rule("frost_protect")
    assert engine.evaluate(rule, _ctx(tmin_alert_c=2.0, tmin_p10_3d=3.5, low_lying=True)) is True
    assert engine.evaluate(rule, _ctx(tmin_alert_c=2.0, tmin_p10_3d=3.5, low_lying=False)) is False


def test_missing_numbers_skip_the_rule(rules) -> None:
    rf, _ = rules
    assert engine.evaluate(rf.rule("heat_stress_crop"), _ctx(tmax_alert_c=None, tmax_p90_3d=50.0)) is None
    assert engine.evaluate(rf.rule("irrigate_now"), _ctx(depletion=None)) is None


def test_livestock_and_crop_rules_do_not_mix(rules) -> None:
    rf, _ = rules
    for r in rf.rules:
        assert engine.applies(r, _ctx(LIVESTOCK)) == (r.crop == LIVESTOCK), r.id
        assert engine.applies(r, _ctx("wheat")) == (r.crop != LIVESTOCK), r.id


# ---------------------------------------------------------------- spray planner, confidence, priority
TH = load_rules().spray_thresholds()


@pytest.mark.parametrize("p_today, p_next, wind, expected", [
    (0.1, 0.1, 5, spray.GOOD),
    (0.3, 0.1, 5, spray.CAUTION),
    (0.1, 0.4, 5, spray.CAUTION),
    (0.1, 0.1, 12, spray.CAUTION),
    (0.6, 0.0, 5, spray.AVOID),
    (0.1, 0.7, 5, spray.AVOID),
    (0.1, 0.1, 16, spray.AVOID),
    (None, 0.1, 5, spray.CAUTION),
    (0.1, None, None, spray.GOOD),
])
def test_spray_day_rating(p_today, p_next, wind, expected) -> None:
    assert spray.day_rating(p_today, p_next, wind, TH) == expected


def test_spray_plan_uses_the_next_day_and_is_day_level() -> None:
    assert spray.plan([0.0, 0.9, 0.0], [5, 5, 5], TH) == [spray.AVOID, spray.AVOID, spray.GOOD]
    src = Path(spray.__file__).read_text(encoding="utf-8")
    assert "DAY-LEVEL ONLY" in src and "hour-level" in src


def test_any_day_is_the_independent_union() -> None:
    assert any_day(np.array([0.5, 0.5])) == pytest.approx(0.75)
    assert any_day(np.array([0.0, 0.0, 0.0])) == 0.0


def test_confidence_follows_guide_formula(rules) -> None:
    rf, _ = rules
    rule = rf.rule("waterlogging_drain")
    ctx = _ctx(p_rain_35_3d=0.9, drain_poor=True)
    ctx.leads["p_rain_35_3d"] = 2
    ctx.widths["rain"] = {2: 20.0}
    level, score, lead = engine.confidence(rule, rf, ctx)
    # margin = (0.9 - 0.3) / (1 - 0.3); minus 0.08 x (2 - 1); minus 0.3 x 20 / 40
    assert lead == 2 and score == pytest.approx(0.6 / 0.7 - 0.08 - 0.15)
    assert level == "high"
    ctx.values["p_rain_35_3d"] = 0.32
    assert engine.confidence(rule, rf, ctx)[0] == "low"


def test_priority_adjusts_for_stage_sensitivity_and_low_confidence(rules) -> None:
    rf, _ = rules
    irrigate = rf.rule("irrigate_now")  # base moderate, sensitivity drought
    assert engine.priority(irrigate, _ctx(drought_sensitivity="high"), "high") == "high"
    assert engine.priority(irrigate, _ctx(drought_sensitivity="medium"), "high") == "moderate"
    assert engine.priority(irrigate, _ctx(drought_sensitivity="medium"), "low") == "low"
    assert engine.priority(rf.rule("spray_hold"), _ctx(), "low") == "low"


# ---------------------------------------------------------------- engine on a synthetic forecast
def _forecast(rows: dict[str, dict]) -> pd.DataFrame:
    """Five lead days per Panchayat; ``rows[pid]`` overrides columns (scalars or 5-item lists)."""
    out = []
    for pid, over in rows.items():
        for lead in range(1, 6):
            r = {"issue_date": pd.Timestamp(ISSUE), "valid_date": pd.Timestamp(ISSUE + timedelta(days=lead)),
                 "lead_day": lead, "panchayat_id": pid, "block_id": "MB0" + pid[3],
                 "prob_rain_ge_1": 0.05, "prob_rain_ge_2_5": 0.03, "prob_rain_ge_10": 0.01,
                 "prob_rain_ge_35": 0.0,
                 "rain_p10": 0.0, "rain_p50": 0.0, "rain_p90": 1.0, "tmax_p10": 30.0, "tmax_p50": 32.0,
                 "tmax_p90": 34.0, "tmin_p10": 20.0, "tmin_p50": 22.0, "tmin_p90": 24.0, "rh_p10": 50.0,
                 "rh_p50": 60.0, "rh_p90": 70.0, "wind_p10": 2.0, "wind_p50": 4.0, "wind_p90": 6.0,
                 "td_p50": 15.0,
                 "soil_moisture_frac_start": 0.8, "soil_moisture_frac": 0.78, "soil_moisture_frac_dry": 0.75,
                 "soil_moisture_frac_wet": 0.85, "dry_spell_days": lead, "et0_mm": 4.5, "waterlog_score": 0.0}
            for k, v in over.items():
                r[k] = v[lead - 1] if isinstance(v, list) else v
            out.append(r)
    return pd.DataFrame(out)


CROPS = pd.DataFrame({
    "panchayat_id": ["MP0101", "MP0102"], "season": "kharif_2024", "crop": "bajra",
    "sowing_date": pd.Timestamp("2024-07-20"), "expected_harvest_date": pd.Timestamp("2024-10-10"),
    "crop_area_fraction": 0.5})


def _run(fc: pd.DataFrame, crops: pd.DataFrame = CROPS) -> engine.EngineResult:
    return engine.generate(ISSUE, fc, loaders.load_static(), crops, loaders.load_calendar())


def test_same_block_same_crop_different_advice() -> None:
    """MP0101 has dry soil and no rain coming; MP0102 (same block, same crop, same sowing date) has
    rain likely, so one is told to irrigate and the other to hold irrigation and not spray."""
    fc = _forecast({"MP0101": {"soil_moisture_frac_start": 0.3},
                    "MP0102": {"soil_moisture_frac_start": 0.45,
                               "prob_rain_ge_2_5": [0.8, 0.7, 0.2, 0.1, 0.1],
                               "prob_rain_ge_10": [0.6, 0.3, 0.1, 0.0, 0.0], "prob_rain_ge_1": 0.9,
                               "rain_p50": [14.0, 6.0, 1.0, 0.0, 0.0], "dry_spell_days": 0}})
    res = _run(fc)
    by = {(a["panchayat_id"], a["category"]): a for a in res.advisories if a["crop"] == "bajra"}
    assert by[("MP0101", "irrigation")]["rule_id"] == "irrigate_now"
    assert by[("MP0102", "irrigation")]["rule_id"] == "irrigation_hold_rain"
    assert ("MP0102", "spray") in by and ("MP0101", "spray") not in by
    assert by[("MP0101", "irrigation")]["reason"]["en"] != by[("MP0102", "irrigation")]["reason"]["en"]


def test_drafts_are_complete_and_deterministic() -> None:
    fc = _forecast({"MP0101": {"soil_moisture_frac_start": 0.3, "tmax_p90": 41.0},
                    "MP0102": {"prob_rain_ge_2_5": 0.9, "prob_rain_ge_35": 0.5, "rain_p90": 80.0}})
    a, b = _run(fc), _run(fc)
    assert json.dumps(a.advisories, sort_keys=True) == json.dumps(b.advisories, sort_keys=True)
    ids = [x["id"] for x in a.advisories]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    for adv in a.advisories:
        assert adv["thresholds_status"] == "placeholder"
        assert adv["translation_status"] == "needs_native_review"
        for part in ("action", "reason", "fallback"):
            for lang in ("en", "hi", "pa"):
                text = adv[part][lang]
                bad = "{" in text or "}" in text or "nan" in text.lower()
                assert text and not bad, (adv["id"], text)
        assert adv["evidence"] and all(e["label"] and e["value"] for e in adv["evidence"])
        assert adv["valid_from"] == "2024-09-10" and adv["valid_to"] >= adv["valid_from"]


def test_supersedes_and_one_advisory_per_category() -> None:
    # Severe THI fires both livestock rules; only the severe one is kept. Dry and dry soil fires both
    # irrigate_now and dry_spell_protect; irrigate_now supersedes the dry-spell advice.
    fc = _forecast({"MP0101": {"tmax_p90": 45.0, "td_p50": 28.0, "soil_moisture_frac_start": 0.2}})
    res = _run(fc, CROPS[CROPS["panchayat_id"] == "MP0101"])
    rules = {(a["crop"], a["rule_id"]) for a in res.advisories}
    assert (LIVESTOCK, "livestock_heat_severe") in rules and (LIVESTOCK, "livestock_heat") not in rules
    assert ("bajra", "irrigate_now") in rules and ("bajra", "dry_spell_protect") not in rules
    assert ("MP0101:livestock", "livestock_heat", "superseded") in res.dropped
    keys = [(a["panchayat_id"], a["crop"], a["category"]) for a in res.advisories]
    assert len(keys) == len(set(keys))


def test_sowing_advice_for_planned_crops_only() -> None:
    crops = pd.DataFrame({"panchayat_id": ["MP0101", "MP0102"], "season": "rabi_2024_25", "crop": "wheat",
                          "sowing_date": [pd.Timestamp("2024-09-15"), pd.Timestamp("2024-10-30")],
                          "expected_harvest_date": pd.Timestamp("2025-04-10"), "crop_area_fraction": 0.5})
    res = _run(_forecast({"MP0101": {"soil_moisture_frac_start": 0.2}, "MP0102": {}}), crops)
    sowing = [a for a in res.advisories if a["category"] == "sowing"]
    assert [(a["panchayat_id"], a["stage"], a["rule_id"]) for a in sowing] == \
        [("MP0101", "pre_sowing", "sowing_dry_soil")]


def test_formatting_of_small_and_large_chances(rules) -> None:
    _, tf = rules
    assert engine.fmt(0.004, "prob", "en", tf) == "less than 1%"
    assert engine.fmt(0.996, "prob", "hi", tf) == "99% से अधिक"
    assert engine.fmt(0.42, "prob", "pa", tf) == "42%"
    assert engine.fmt(5, "days", "en", tf) == "5 days" and engine.fmt(1, "days", "en", tf) == "1 day"
    assert engine.fmt(None, "C", "en", tf) == "not available"


# ---------------------------------------------------------------- documents and guard rails
def test_expert_table_is_current(rules) -> None:
    assert expert_table.OUT.read_text(encoding="utf-8") == expert_table.render(*rules), \
        "docs/thresholds_for_expert_review.md is stale: run `python -m gramdrishti.advisory.expert_table`"


def test_expert_table_lists_every_threshold(rules) -> None:
    rf, _ = rules
    doc = expert_table.render(*rules)
    for r in rf.rules:
        for name in r.thresholds:
            assert f"| `{r.id}` | `{name}` |" in doc
    for name in rf.spray_planner:
        assert f"| spray planner | `{name}` |" in doc


LLM_MODULES = {"openai", "anthropic", "langchain", "langchain_core", "transformers", "google.generativeai",
               "cohere", "mistralai", "ollama", "llama_cpp", "litellm", "vertexai"}
NETWORK_MODULES = {"requests", "httpx", "urllib", "urllib3", "aiohttp", "socket", "http"}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module)
    return out


def test_no_language_model_anywhere() -> None:
    """Advisories come from YAML rules and templates only (CLAUDE.md rule 8)."""
    for path in PKG.rglob("*.py"):
        mods = _imports(path)
        roots = {m.split(".")[0] for m in mods} | mods
        assert not roots & LLM_MODULES, f"{path} imports a language-model library"
        if "advisory" in path.parts:
            assert not roots & NETWORK_MODULES, f"{path} imports a network library"
    project = tomllib.loads((PKG.parent / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    deps = " ".join(project["dependencies"] + sum(project.get("optional-dependencies", {}).values(), []))
    for name in LLM_MODULES:
        assert name.split(".")[0] not in deps.lower()
