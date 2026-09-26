"""Advisory engine (Backend Guide 9): rules + signals + templates. No language model is involved.

For one issue date:
1. build a context per Panchayat and crop (plus one livestock context per Panchayat) from the snapshot;
2. evaluate every applicable rule's ``when`` with simpleeval (a safe expression evaluator);
3. for each rule that fires, fill its template in en, hi and pa, attach evidence rows, compute the
   confidence (Guide 9.5) and the priority;
4. drop overlapping advisories: rules a fired rule ``supersedes``, then one advisory per Panchayat, crop
   and category (highest priority, then confidence, then rule order in the file);
5. return drafts sorted by id. The same snapshot and files give byte-identical output.

Priority: the rule's base level, one level up when the calendar marks the stage highly sensitive to
the rule's ``sensitivity`` (drought or waterlogging), one level down when it marks it low, and one level
down when confidence is low; kept within low..severe.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache

import pandas as pd
from simpleeval import EvalWithCompoundTypes

from gramdrishti.advisory.rules import (
    ConfidenceKey,
    Rule,
    RuleFile,
    TemplateFile,
    expression_names,
    load_checked,
)
from gramdrishti.advisory.signals import (
    CROP_SIGNALS,
    LIVESTOCK,
    NUMERIC_KINDS,
    SIGNALS,
    Context,
    build_contexts,
)
from gramdrishti.provisional.texts import day_text

LEVELS = ("low", "moderate", "high", "severe")
CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}
LANGS = ("en", "hi", "pa")
PARTS = ("action", "reason", "fallback")


@dataclass
class EngineResult:
    """Drafts for one issue date plus what happened on the way (for logs and tests)."""

    issue_date: date
    advisories: list[dict]
    contexts: list[Context]
    fired: Counter = field(default_factory=Counter)
    skipped_missing: Counter = field(default_factory=Counter)   # a forecast or soil number is missing
    not_applicable: Counter = field(default_factory=Counter)    # the calendar has no value for the stage
    dropped: list[tuple[str, str, str]] = field(default_factory=list)  # (panchayat:crop, rule, reason)

    def counts_by_category(self) -> dict[str, int]:
        return dict(sorted(Counter(a["category"] for a in self.advisories).items()))


# ---------------------------------------------------------------- rule evaluation
@lru_cache(maxsize=256)
def _names(expr: str) -> frozenset[str]:
    return frozenset(expression_names(expr))


def applies(rule: Rule, ctx: Context) -> bool:
    """``crop: any`` covers every crop but not livestock; ``crop: livestock`` only livestock."""
    if rule.crop == "any":
        return ctx.crop != LIVESTOCK
    return rule.crop == ctx.crop


def missing_numbers(rule: Rule, ctx: Context) -> set[str]:
    """Numeric signals the rule needs that are None for this context."""
    return {n for n in _names(rule.when)
            if n in SIGNALS and SIGNALS[n].kind in NUMERIC_KINDS and ctx.values.get(n) is None}


def evaluate(rule: Rule, ctx: Context) -> bool | None:
    """True or False, or None when the rule needs a number that is missing (the rule is skipped)."""
    names = _names(rule.when)
    if missing_numbers(rule, ctx):
        return None
    env: dict[str, object] = {n: ctx.values.get(n) for n in names if n in SIGNALS}
    env |= {n: t.value for n, t in rule.thresholds.items()}
    return bool(EvalWithCompoundTypes(names=env).eval(rule.when))


# ---------------------------------------------------------------- confidence and priority
def _threshold(key: ConfidenceKey, rule: Rule, rf: RuleFile, ctx: Context) -> float | None:
    t = key.threshold
    if isinstance(t, (int, float)):
        return float(t)
    if t in rule.thresholds:
        return rule.thresholds[t].value
    if t in rf.spray_planner:
        return rf.spray_planner[t].value
    v = ctx.values.get(t)
    return float(v) if isinstance(v, (int, float)) else None


def margin(key: ConfidenceKey, rule: Rule, rf: RuleFile, ctx: Context) -> float | None:
    """How far the key signal is beyond its threshold, scaled to 0..1 (Guide 9.5 ``prob_margin``)."""
    v, thr = ctx.values.get(key.signal), _threshold(key, rule, rf, ctx)
    if not isinstance(v, (int, float)) or thr is None:
        return None
    scale = key.scale if key.scale is not None else max((1 - thr) if key.direction == "above" else thr, 0.05)
    m = (v - thr) / scale if key.direction == "above" else (thr - v) / scale
    return min(max(m, 0.0), 1.0)


def confidence(rule: Rule, rf: RuleFile, ctx: Context) -> tuple[str, float, int]:
    """(level, score, lead day of the advice). score = margin - 0.08 (lead - 1) - 0.3 width ratio."""
    margins = [(margin(k, rule, rf, ctx), i) for i, k in enumerate(rule.confidence)]
    scored = [(m, i) for m, i in margins if m is not None]
    best_m, best_i = max(scored, key=lambda x: (x[0], -x[1])) if scored else (0.0, 0)
    key = rule.confidence[best_i]
    lead = ctx.leads.get(rule.day_signal or key.signal, 1)
    c = rf.confidence
    width = ctx.widths.get(key.interval, {}).get(lead) if key.interval != "none" else None
    ref = c.reference_width.get(key.interval) if key.interval != "none" else None  # type: ignore[call-overload]
    ratio = 0.0 if width is None or ref is None else min(max(width, 0.0) / ref.value, 1.0)
    score = best_m - c.lead_penalty.value * (lead - 1) - c.width_weight.value * ratio
    level = "high" if score > c.high_above.value else "medium" if score > c.medium_above.value else "low"
    return level, round(score, 6), lead


def priority(rule: Rule, ctx: Context, conf: str) -> str:
    """Base level, adjusted by the stage's sensitivity (calendar) and by low confidence."""
    idx = LEVELS.index(rule.priority)
    if rule.sensitivity != "none":
        sens = ctx.values.get(f"{rule.sensitivity}_sensitivity")
        idx += {"high": 1, "low": -1}.get(str(sens), 0)
    if conf == "low":
        idx -= 1
    return LEVELS[min(max(idx, 0), len(LEVELS) - 1)]


# ---------------------------------------------------------------- text
def fmt(value: object, kind: str, lang: str, tf: TemplateFile) -> str:
    """A signal value as text with its unit in the given language. Western digits everywhere."""
    if value is None:
        return getattr(tf.units["n/a"], lang)
    u = {k: getattr(t, lang) for k, t in tf.units.items()}
    if kind == "bool":
        return "yes" if value else "no"
    if kind == "text":
        return str(value)
    v = float(value)  # type: ignore[arg-type]
    if kind in ("prob", "frac"):
        pct = round(v * 100)
        if kind == "prob" and pct < 1:
            return u["under_1_pct"]
        if kind == "prob" and pct > 99:
            return u["over_99_pct"]
        return f"{pct:.0f}%"
    if kind == "pct":
        return f"{v:.0f}%"
    if kind == "C":
        return f"{v:.1f} {u['C']}"
    if kind == "mm":
        return f"{v:.1f} {u['mm']}" if v < 10 else f"{v:.0f} {u['mm']}"
    if kind == "mm/day":
        return f"{v:.1f} {u['mm/day']}"
    if kind == "km/h":
        return f"{v:.0f} {u['km/h']}"
    if kind == "days":
        n = int(round(v))
        return f"{n} {u['day'] if n == 1 else u['days']}"
    if kind == "score":
        return f"{v:.2f}"
    return f"{v:.0f}"


def _stage_text(stage: object, lang: str, tf: TemplateFile) -> str:
    t = tf.stages.get(str(stage)) if stage is not None else None
    return getattr(t or tf.stages["unknown"], lang)


def fill(rule: Rule, ctx: Context, tf: TemplateFile, lead: int, valid_to: date) -> dict[str, dict[str, str]]:
    """Action, reason and fallback in en, hi and pa with every placeholder filled."""
    tpl = tf.templates[rule.template]
    out: dict[str, dict[str, str]] = {p: {} for p in PARTS}
    for lang in LANGS:
        vals = {n: fmt(v, SIGNALS[n].kind, lang, tf) for n, v in ctx.values.items() if n in SIGNALS}
        crop = tf.crops.get(ctx.crop)
        nxt = ctx.next_spray_lead
        vals |= {"day": day_text(ctx.dates[lead], lang), "valid_to_day": day_text(valid_to, lang),
                 "crop_name": getattr(crop, lang) if crop else ctx.crop,
                 "stage_name": _stage_text(ctx.values.get("stage"), lang, tf),
                 "next_spray_day": (day_text(ctx.dates[nxt], lang) if nxt
                                    else getattr(tf.no_good_spray_day, lang))}
        for part in PARTS:
            out[part][lang] = getattr(getattr(tpl, part), lang).format_map(vals)
    return out


def evidence(rule: Rule, ctx: Context, tf: TemplateFile) -> list[dict[str, str]]:
    """English evidence rows: label with dates, value with unit."""
    short = {f"d{k}": f"{d.day} {d:%b}" for k, d in ctx.dates.items()}
    rows = []
    for name in rule.evidence:
        spec = SIGNALS[name]
        v = ctx.values.get(name)
        value = _stage_text(v, "en", tf) if name == "stage" else fmt(v, spec.kind, "en", tf)
        rows.append({"label": spec.label.format(**short), "value": value})
    return rows


# ---------------------------------------------------------------- the run
def _draft(rule: Rule, rf: RuleFile, tf: TemplateFile, ctx: Context, issue: date) -> dict:
    conf, _score, lead = confidence(rule, rf, ctx)
    valid_to = issue + timedelta(days=rule.window_days)
    lead = min(lead, rule.window_days)
    text = fill(rule, ctx, tf, lead, valid_to)
    stage = ctx.values.get("stage")
    return {
        "id": f"ADV-{issue.isoformat()}-{ctx.panchayat_id}-{ctx.crop}-{rule.category}",
        "issue_date": issue.isoformat(), "panchayat_id": ctx.panchayat_id, "block_id": ctx.block_id,
        "crop": ctx.crop, "stage": None if stage is None else str(stage), "category": rule.category,
        "priority": priority(rule, ctx, conf),
        "valid_from": (issue + timedelta(days=1)).isoformat(), "valid_to": valid_to.isoformat(),
        **text, "confidence": conf, "evidence": evidence(rule, ctx, tf),
        "thresholds_status": rule.thresholds_status, "translation_status": tf.translation_status,
        "rule_id": rule.id,
    }


def _dedupe(drafts: list[tuple[int, dict]], rules: list[Rule], result: EngineResult) -> list[dict]:
    """Apply ``supersedes``, then keep one advisory per (Panchayat, crop, category)."""
    by_ctx: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    for order, a in drafts:
        by_ctx.setdefault((a["panchayat_id"], a["crop"]), []).append((order, a))
    kept: list[dict] = []
    for (pid, crop), items in sorted(by_ctx.items()):
        fired = {a["rule_id"] for _, a in items}
        superseded = {s for r in rules if r.id in fired for s in r.supersedes}
        live = []
        for order, a in items:
            if a["rule_id"] in superseded:
                result.dropped.append((f"{pid}:{crop}", a["rule_id"], "superseded"))
            else:
                live.append((order, a))
        best: dict[str, tuple[int, dict]] = {}
        for order, a in live:
            cur = best.get(a["category"])
            rank = (LEVELS.index(a["priority"]), CONFIDENCE_RANK[a["confidence"]], -order)
            if cur is None or rank > (LEVELS.index(cur[1]["priority"]), CONFIDENCE_RANK[cur[1]["confidence"]],
                                      -cur[0]):
                if cur is not None:
                    result.dropped.append((f"{pid}:{crop}", cur[1]["rule_id"], "same category"))
                best[a["category"]] = (order, a)
            else:
                result.dropped.append((f"{pid}:{crop}", a["rule_id"], "same category"))
        kept += [a for _, a in best.values()]
    return sorted(kept, key=lambda a: a["id"])


def generate(issue: date, forecast: pd.DataFrame, static: pd.DataFrame, crops: pd.DataFrame,
             calendar: pd.DataFrame, rf: RuleFile | None = None,
             tf: TemplateFile | None = None) -> EngineResult:
    """Draft advisories for one issue date from its snapshot forecast frame (five lead days)."""
    if rf is None or tf is None:
        rf, tf = load_checked()
    f = forecast
    if "issue_date" in f:
        f = f[pd.to_datetime(f["issue_date"]).dt.date == issue]
    ctxs = build_contexts(issue, f, static, crops, calendar, rf.spray_thresholds(),
                          int(rf.context["sowing_lookahead_days"].value), rf.context["low_lying_tpi_z"].value)
    result = EngineResult(issue, [], ctxs)
    drafts: list[tuple[int, dict]] = []
    for ctx in ctxs:
        for order, rule in enumerate(rf.rules):
            if not applies(rule, ctx):
                continue
            ok = evaluate(rule, ctx)
            if ok is None:
                crop_only = missing_numbers(rule, ctx) <= set(CROP_SIGNALS)
                (result.not_applicable if crop_only else result.skipped_missing)[rule.id] += 1
            elif ok:
                result.fired[rule.id] += 1
                drafts.append((order, _draft(rule, rf, tf, ctx, issue)))
    result.advisories = _dedupe(drafts, rf.rules, result)
    return result
