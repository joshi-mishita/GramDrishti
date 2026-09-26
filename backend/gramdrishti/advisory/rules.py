"""Schema, loading and checks for ``rules.yaml`` and ``templates.yaml``.

The pydantic models below are the schema (``rules.schema.json`` is exported from them for editors).
``load_rules`` and ``load_templates`` validate the shape; ``check`` then validates meaning: every name in
a ``when`` expression is a known signal or one of the rule's thresholds, the expression parses under
simpleeval, templates exist and use only known placeholders, and placeholder thresholds carry no source.
Loading never runs at import time.
"""

from __future__ import annotations

import ast
import json
import string
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gramdrishti.advisory import spray
from gramdrishti.advisory.signals import LIVESTOCK, SIGNALS

HERE = Path(__file__).resolve().parent
RULES_PATH = HERE / "rules.yaml"
TEMPLATES_PATH = HERE / "templates.yaml"
SCHEMA_PATH = HERE / "rules.schema.json"

Level = Literal["low", "moderate", "high", "severe"]
Category = Literal["sowing", "irrigation", "spray", "fertilizer", "harvest", "heat_stress", "frost",
                   "waterlogging", "dry_spell", "pest_disease", "livestock"]
RiskName = Literal["heavy_rain", "heat", "frost", "waterlogging", "dry_spell"]
Interval = Literal["rain", "tmax", "tmin", "wind", "rh", "soil", "none"]
Lang = Literal["en", "hi", "pa"]
# Names a template may use besides the signals.
TEMPLATE_EXTRAS = {"day", "valid_to_day", "crop_name", "stage_name", "next_spray_day"}
HEADLINE_NAMES = {"day", "score", "tmax_p90", "tmin_p10", "dry_days"}
EXPRESSION_CONSTANTS = {"True", "False", "None"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Threshold(Strict):
    """One placeholder number with its unit and a one-line meaning for the expert."""

    value: float
    unit: str
    meaning: str = Field(min_length=10)


class ConfidenceKey(Strict):
    """A key signal for confidence (Guide 9.5): how far it is beyond ``threshold``.

    ``threshold`` is a number, the name of one of the rule's thresholds, a spray-planner threshold, or a
    signal (for example the calendar's ``tmax_alert_c``). ``scale`` turns the distance into a 0..1 margin;
    for probabilities it defaults to the room left between the threshold and 1 (or 0).
    """

    signal: str
    threshold: str | float
    direction: Literal["above", "below"]
    scale: float | None = Field(default=None, gt=0)
    interval: Interval


class Rule(Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    crop: str
    category: Category
    priority: Level
    when: str
    thresholds: dict[str, Threshold] = {}
    template: str
    window_days: int = Field(ge=1, le=5)
    confidence: list[ConfidenceKey] = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    sensitivity: Literal["drought", "waterlog", "none"]
    supersedes: list[str] = []
    day_signal: str | None = None
    thresholds_status: Literal["placeholder", "reviewed"]
    source: str

    @model_validator(mode="after")
    def _source_matches_status(self) -> Rule:
        if self.thresholds_status == "placeholder" and self.source:
            raise ValueError(f"{self.id}: a placeholder rule must have an empty source")
        if self.thresholds_status == "reviewed" and not self.source.strip():
            raise ValueError(f"{self.id}: a reviewed rule needs a source")
        return self


class RiskConfig(Strict):
    score: str
    cuts: list[float] = Field(min_length=3, max_length=3)
    thresholds: dict[str, Threshold] = {}

    @field_validator("cuts")
    @classmethod
    def _increasing(cls, v: list[float]) -> list[float]:
        if not (0 < v[0] < v[1] < v[2] <= 1):
            raise ValueError("cuts must increase within (0, 1]")
        return v


class ConfidenceConfig(Strict):
    lead_penalty: Threshold
    width_weight: Threshold
    high_above: Threshold
    medium_above: Threshold
    reference_width: dict[Literal["rain", "tmax", "tmin", "wind", "rh", "soil"], Threshold]


class RuleFile(Strict):
    version: int
    thresholds_status: Literal["placeholder", "reviewed"]
    context: dict[Literal["sowing_lookahead_days", "low_lying_tpi_z"], Threshold]
    spray_planner: dict[str, Threshold]
    risk: dict[RiskName, RiskConfig]
    confidence: ConfidenceConfig
    rules: list[Rule] = Field(min_length=1)

    def spray_thresholds(self) -> dict[str, float]:
        return {k: t.value for k, t in self.spray_planner.items()}

    def rule(self, rule_id: str) -> Rule:
        return next(r for r in self.rules if r.id == rule_id)


class Text3(Strict):
    en: str
    hi: str
    pa: str


class Template(Strict):
    action: Text3
    reason: Text3
    fallback: Text3


class TemplateFile(Strict):
    translation_status: Literal["needs_native_review", "reviewed"]
    crops: dict[str, Text3]
    stages: dict[str, Text3]
    no_good_spray_day: Text3
    templates: dict[str, Template]
    headlines: dict[RiskName, Text3]
    units: dict[str, Text3]


def _read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_rules(path: Path = RULES_PATH) -> RuleFile:
    """Parse and shape-check the rules file (see ``check`` for meaning checks)."""
    return RuleFile.model_validate(_read_yaml(path))


def load_templates(path: Path = TEMPLATES_PATH) -> TemplateFile:
    """Parse and shape-check the templates file."""
    return TemplateFile.model_validate(_read_yaml(path))


@lru_cache(maxsize=4)
def _cached(rules_path: str, templates_path: str) -> tuple[RuleFile, TemplateFile]:
    rf, tf = load_rules(Path(rules_path)), load_templates(Path(templates_path))
    errors = check(rf, tf)
    if errors:
        raise ValueError("advisory rules are invalid:\n- " + "\n- ".join(errors))
    return rf, tf


def load_checked(rules_path: Path = RULES_PATH,
                 templates_path: Path = TEMPLATES_PATH) -> tuple[RuleFile, TemplateFile]:
    """Rules and templates after every check passed (cached per path)."""
    return _cached(str(rules_path), str(templates_path))


def expression_names(expr: str) -> set[str]:
    """Every bare name used in a ``when`` expression."""
    return {n.id for n in ast.walk(ast.parse(expr, mode="eval")) if isinstance(n, ast.Name)}


def placeholders(text: str) -> set[str]:
    """``{name}`` fields in a template string."""
    return {f for _, f, _, _ in string.Formatter().parse(text) if f}


def _check_expression(rule: Rule) -> list[str]:
    from simpleeval import EvalWithCompoundTypes

    try:
        names = expression_names(rule.when)
    except SyntaxError as e:
        return [f"{rule.id}: `when` does not parse: {e.msg}"]
    errors = []
    unknown = names - set(SIGNALS) - set(rule.thresholds) - EXPRESSION_CONSTANTS
    if unknown:
        errors.append(f"{rule.id}: unknown names in `when`: {sorted(unknown)}")
    overlap = set(rule.thresholds) & set(SIGNALS)
    if overlap:
        errors.append(f"{rule.id}: threshold names clash with signals: {sorted(overlap)}")
    unused = set(rule.thresholds) - names
    if unused:
        errors.append(f"{rule.id}: thresholds not used in `when`: {sorted(unused)}")
    if not unknown:
        # A dry run with harmless values proves simpleeval accepts every operator used.
        sample = {n: 0.5 for n in names} | {n: t.value for n, t in rule.thresholds.items()}
        sample |= {n: "x" for n in names if n in SIGNALS and SIGNALS[n].kind == "text"}
        sample |= {n: False for n in names if n in SIGNALS and SIGNALS[n].kind == "bool"}
        try:
            EvalWithCompoundTypes(names=sample).eval(rule.when)
        except Exception as e:  # noqa: BLE001 - report any evaluator refusal as a rule error
            errors.append(f"{rule.id}: simpleeval refuses `when`: {type(e).__name__}: {e}")
    return errors


def check(rf: RuleFile, tf: TemplateFile, crops: set[str] | None = None) -> list[str]:
    """Meaning checks beyond the schema. Returns a list of errors (empty when valid)."""
    errors: list[str] = []
    ids = [r.id for r in rf.rules]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f"duplicate rule ids: {sorted(dup)}")
    missing_spray = set(spray.THRESHOLD_NAMES) - set(rf.spray_planner)
    if missing_spray:
        errors.append(f"spray_planner lacks {sorted(missing_spray)}")
    allowed_placeholders = set(SIGNALS) | TEMPLATE_EXTRAS
    for r in rf.rules:
        errors += _check_expression(r)
        if r.crop not in ("any", LIVESTOCK) and crops is not None and r.crop not in crops:
            errors.append(f"{r.id}: unknown crop {r.crop}")
        for s in r.supersedes:
            if s not in ids or s == r.id:
                errors.append(f"{r.id}: supersedes unknown rule {s}")
        for e in r.evidence:
            if e not in SIGNALS:
                errors.append(f"{r.id}: unknown evidence signal {e}")
        if r.day_signal is not None and r.day_signal not in SIGNALS:
            errors.append(f"{r.id}: unknown day_signal {r.day_signal}")
        for k in r.confidence:
            if k.signal not in SIGNALS:
                errors.append(f"{r.id}: unknown confidence signal {k.signal}")
            elif SIGNALS[k.signal].kind not in ("prob",) and k.scale is None:
                errors.append(f"{r.id}: confidence key {k.signal} is not a probability and needs a scale")
            if isinstance(k.threshold, str) and k.threshold not in (
                    set(r.thresholds) | set(rf.spray_planner) | set(SIGNALS)):
                errors.append(f"{r.id}: unknown confidence threshold {k.threshold}")
        tpl = tf.templates.get(r.template)
        if tpl is None:
            errors.append(f"{r.id}: template {r.template} does not exist")
            continue
        for part in ("action", "reason", "fallback"):
            texts = getattr(tpl, part)
            sets = {lang: placeholders(getattr(texts, lang)) for lang in ("en", "hi", "pa")}
            bad = set().union(*sets.values()) - allowed_placeholders
            if bad:
                errors.append(f"template {r.template}.{part}: unknown placeholders {sorted(bad)}")
            if len({frozenset(v) for v in sets.values()}) != 1:
                errors.append(f"template {r.template}.{part}: languages use different placeholders {sets}")
    for name, text in tf.headlines.items():
        sets = {lang: placeholders(getattr(text, lang)) for lang in ("en", "hi", "pa")}
        bad = set().union(*sets.values()) - HEADLINE_NAMES
        if bad:
            errors.append(f"headline {name}: unknown placeholders {sorted(bad)}")
    unused = set(tf.templates) - {r.template for r in rf.rules}
    if unused:
        errors.append(f"templates not used by any rule: {sorted(unused)}")
    return errors


def json_schema() -> str:
    """JSON Schema of the rules file, for editors and external validators."""
    return json.dumps(RuleFile.model_json_schema(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    """Validate both files and write ``rules.schema.json``."""
    rf, tf = load_rules(), load_templates()
    errors = check(rf, tf)
    SCHEMA_PATH.write_text(json_schema(), encoding="utf-8")
    if errors:
        raise SystemExit("invalid:\n- " + "\n- ".join(errors))
    print(f"{len(rf.rules)} rules and {len(tf.templates)} templates valid; wrote {SCHEMA_PATH.name}")


if __name__ == "__main__":
    main()
