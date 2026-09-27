"""Write ``docs/validation_report.md`` from ``artifacts/verification.json`` and ``impact.json``.

Every number in the report is read from those files; the wording around them is fixed or chosen by
simple rules (win / tie / loss from the confidence interval). Nothing is typed by hand.

Run: ``cd backend && python -m gramdrishti.verify.report``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from gramdrishti.data.config import ART, ROOT, VARS

OUT = ROOT / "docs" / "validation_report.md"
NAMES = {"rain": "Rain", "tmax": "Maximum temperature", "tmin": "Minimum temperature",
         "rh": "Relative humidity", "wind": "Wind speed"}
CHECK_NAMES = {"temporal_holdout": "Temporal holdout", "leave_one_block_out": "Leave-one-block-out",
               "station": "Station check"}
DECISION_NAMES = {"spray": "Spray tomorrow?", "heat_alert": "Heat alert",
                  "irrigation_wait": "Irrigate or wait"}
RESULT_WORDS = {"win": "better", "loss": "worse", "tie": "no clear difference",
                "too_few_days": "too few days"}


def _n(x: float | None, nd: int = 2) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def _p(x: float | None, nd: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:+.{nd}f}%"


def _ci(ci: list[float] | None) -> str:
    return "n/a" if ci is None else f"{100 * ci[0]:+.1f} to {100 * ci[1]:+.1f}%"


def _verdict(ci: list[float] | None) -> str:
    if ci is None:
        return "too_few_days"
    return "win" if ci[0] > 0 else "loss" if ci[1] < 0 else "tie"


def _metric(var: dict, name: str) -> dict | None:
    return next((m for m in var["metrics"] if m["name"] == name), None)


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    return out + ["| " + " | ".join(r) + " |" for r in rows]


def headline(s: dict) -> list[str]:
    """One sentence per variable: temporal holdout MAE against B0 and B1, in words, with the numbers."""
    temporal = next(c for c in s["checks"] if c["check"] == "temporal_holdout")
    lines = []
    for v in temporal["variables"]:
        m = _metric(v, "MAE")
        r0, r1 = _verdict(m["skill_ci95"]), _verdict(m["skill_vs_b1_ci95"])
        lines.append(
            f"- **{NAMES[v['var']]}**: against the plain block forecast (B0) the Panchayat forecast is "
            f"**{RESULT_WORDS[r0]}** (MAE {_n(m['model'])} vs {_n(m['b0'])} {m['unit']}, skill "
            f"{_p(m['skill_vs_b0'])}, 95% CI {_ci(m['skill_ci95'])}); against the corrected block forecast "
            f"(B1) it is **{RESULT_WORDS[r1]}** (MAE {_n(m['b1'])} {m['unit']}, "
            f"skill {_p(m['skill_vs_b1'])}, "
            f"95% CI {_ci(m['skill_vs_b1_ci95'])}).")
    return lines


def correction_share(s: dict) -> list[str]:
    """Where most of the MAE gain over B0 already comes from the block bias correction (B1)."""
    temporal = next(c for c in s["checks"] if c["check"] == "temporal_holdout")
    out = []
    for v in temporal["variables"]:
        m = _metric(v, "MAE")
        gain, corr = m["b0"] - m["model"], m["b0"] - m["b1"]
        if gain > 0 and corr >= gain:
            out.append(f"- {NAMES[v['var']]}: the corrected block forecast B1 alone (MAE {_n(m['b1'], 3)} "
                       f"{m['unit']}) is at least as good as the Panchayat forecast ({_n(m['model'], 3)}); "
                       f"all of the gain over B0 ({_n(m['b0'], 3)}) comes from the block bias correction.")
        elif gain > 0 and corr / gain > 0.5:
            out.append(f"- {NAMES[v['var']]}: {corr / gain:.0%} of the MAE gain over B0 "
                       f"({_n(m['b0'], 3)} to {_n(m['model'], 3)} {m['unit']}) is already in B1, the "
                       "corrected block forecast; the Panchayat detail adds the rest.")
    return out


def checks_table(s: dict) -> list[str]:
    rows = []
    for c in s["checks"]:
        for v in c["variables"]:
            m = _metric(v, "MAE")
            rows.append([CHECK_NAMES[c["check"]], v["var"], m["unit"], str(v["n"]), _n(m["model"], 3),
                         _n(m["b0"], 3), _n(m["b1"], 3), _n(m["b2"], 3),
                         f"{_p(m['skill_vs_b0'])} ({_ci(m['skill_ci95'])})",
                         f"{_p(m['skill_vs_b1'])} ({_ci(m['skill_vs_b1_ci95'])})",
                         f"{_verdict(m['skill_ci95'])} / {_verdict(m['skill_vs_b1_ci95'])}"])
    return _table(["Check", "Var", "Unit", "n", "Model MAE", "B0", "B1", "B2", "Skill vs B0 (95% CI)",
                   "Skill vs B1 (95% CI)", "Verdict B0 / B1"], rows)


def other_metrics_table(s: dict) -> list[str]:
    rows = []
    for c in s["checks"]:
        for v in c["variables"]:
            for m in v["metrics"]:
                if m["name"] == "MAE":
                    continue
                bias = m["name"] == "bias"
                skill0 = "" if bias else f"{_p(m['skill_vs_b0'])} ({_ci(m['skill_ci95'])})"
                skill1 = "" if bias else f"{_p(m['skill_vs_b1'])} ({_ci(m['skill_vs_b1_ci95'])})"
                rows.append([CHECK_NAMES[c["check"]], v["var"], m["name"], m["unit"], _n(m["model"], 3),
                             _n(m["b0"], 3), _n(m["b1"], 3), _n(m["b2"], 3), skill0, skill1])
    return _table(["Check", "Var", "Metric", "Unit", "Model", "B0", "B1", "B2", "Skill vs B0 (95% CI)",
                   "Skill vs B1 (95% CI)"], rows)


def events_table(s: dict) -> list[str]:
    rows = []
    for e in s["events"]:
        b = {x["baseline"]: x for x in e["baselines"]}
        rows.append([e["event"], _n(e["base_rate"], 3), _n(e["pod"], 3), _n(e["far"], 3), _n(e["csi"], 3),
                     _n(e["frequency_bias"], 2), _n(e["brier"], 4), _n(e["brier_skill_vs_climatology"], 3),
                     f"{_n(b['b0']['csi'], 3)} / {_n(b['b1']['csi'], 3)}",
                     f"{_n(b['b0']['pod'], 3)} / {_n(b['b1']['pod'], 3)}",
                     f"{_n(b['b0']['far'], 3)} / {_n(b['b1']['far'], 3)}"])
    return _table(["Event", "Observed rate", "POD", "FAR", "CSI", "Freq. bias", "Brier",
                   "Brier skill vs clim.",
                   "CSI B0 / B1", "POD B0 / B1", "FAR B0 / B1"], rows)


def reliability_table(v: dict) -> list[str]:
    out = []
    for r in v["reliability"]:
        cells = [f"{_n(p['forecast_prob'], 2)}: {_n(p['observed_freq'], 3)} (n={p['n']})"
                 for p in r["points"]]
        out.append(f"- `{r['event']}` (bin centre: observed frequency): " + "; ".join(cells))
    return out


def coverage_table(v: dict) -> list[str]:
    rows = [[i["var"], i["stratum"] or "all", str(i["n"]), f"{i['nominal']:.2f}", _n(i["empirical"], 3),
             f"{_n(i['mean_width'], 2)} {i['unit']}"] for i in v["coverage"]["items"]]
    return _table(["Var", "Rows", "n", "Nominal", "Empirical coverage", "Mean width"], rows)


def strata_tables(s: dict) -> list[str]:
    out = []
    for dim in ("lead_day", "season", "rain_intensity", "drainage_class"):
        rows = [[r["stratum"], r["var"], str(r["n"]), _n(r["model"], 3), _n(r["b0"], 3), _n(r["b1"], 3),
                 f"{_p(r['skill_vs_b0'])} ({_ci(r['skill_ci95'])})",
                 f"{_p(r['skill_vs_b1'])} ({_ci(r['skill_vs_b1_ci95'])})",
                 f"{_verdict(r['skill_ci95'])} / {_verdict(r['skill_vs_b1_ci95'])}"]
                for r in s["strata"] if r["dimension"] == dim]
        out += ["", f"By {dim.replace('_', ' ')} (MAE, temporal holdout):", ""]
        out += _table(["Stratum", "Var", "n", "Model", "B0", "B1", "Skill vs B0 (95% CI)",
                       "Skill vs B1 (95% CI)", "Verdict B0 / B1"], rows)
    return out


def _rate(c: dict, n: int) -> str:
    return f"{c['correct']} ({c['correct'] / n:.1%}) / {c['wasted_wait']} / {c['washed_off']}" if n else "n/a"


def impact_table(imp: dict) -> list[str]:
    rows = []
    for it in imp["items"].values():
        n = it["n_decisions"]
        rows.append([it["season"], DECISION_NAMES[it["decision"]], str(n), str(it["events_observed"]),
                     _rate(it["model"], n), _rate(it["block_baseline"], n), _rate(it["block_corrected"], n)])
    return _table(["Season", "Decision", "Decisions", "Events observed",
                   "Model: correct / wasted wait / washed off", "Block B0", "Corrected block B1"], rows)


def impact_losses(imp: dict) -> list[str]:
    """Plain statements wherever the model rule does worse than a block rule on any count."""
    out = []
    for it in imp["items"].values():
        m, name = it["model"], f"{DECISION_NAMES[it['decision']]} ({it['season']})"
        for key, label in (("block_baseline", "B0"), ("block_corrected", "B1")):
            b = it[key]
            worse = []
            if m["correct"] < b["correct"]:
                worse.append(f"fewer correct decisions ({m['correct']} vs {b['correct']})")
            if m["washed_off"] > b["washed_off"]:
                worse.append(f"more misses, called washed off ({m['washed_off']} vs {b['washed_off']})")
            if m["wasted_wait"] > b["wasted_wait"]:
                worse.append("more false alarms, called wasted waits "
                             f"({m['wasted_wait']} vs {b['wasted_wait']})")
            if worse:
                out.append(f"- {name}, against {label}: " + "; ".join(worse) + ".")
    return out


def build(v: dict, imp: dict) -> str:
    """The whole report as Markdown."""
    s = v["summary"]
    fr = v.get("frozen", {})
    reused = s.get("test_reused")
    L = [
        "# Validation report",
        "",
        "Generated by `python -m gramdrishti.verify.report` from `backend/artifacts/verification.json` and "
        "`impact.json`. Do not edit by hand; rerun the job and the generator instead.",
        "",
        "> **Synthetic demo data. Not real weather.** The truth here is the mock data generator's synthetic "
        "Panchayat values (proxy validation). These numbers show whether the method works on data built to "
        "resemble the problem. They are not evidence of skill on real weather.",
        "",
        "## What was tested",
        "",
        f"- Model `{s['model_version']}`, window **{s['window']}** {s['period']['start']} to "
        f"{s['period']['end']} (lead days 1 to 5).",
    ]
    if s.get("test_first_opened_at"):
        L.append(f"- TEST window first opened {s['test_first_opened_at']} for this model version "
                 f"(`docs/test_window_ledger.json`). TEST reused by an earlier version: "
                 f"{'**yes**, so this is not a clean holdout' if reused else 'no'}.")
    if fr:
        L.append(f"- Frozen: model data hash `{fr.get('data_hash_sha256', '')[:16]}...`, code "
                 f"`{fr.get('code_commit', '')}`, sha256 of every data file in `verification.json`.")
    L += [
        "- Baselines: **B0** the raw block forecast (mean of the two NWP sources) copied to every Panchayat; "
        "**B1** the bias-corrected block forecast, which the Panchayat forecast is reconciled to (skill "
        "against B1 is what the Panchayat model itself adds); **B2** B1 plus a lapse-rate term and station "
        "offsets.",
        "- Skill = 1 - model error / baseline error. The 95% interval comes from a moving-block bootstrap of "
        "daily errors (7-day blocks). **Better** = the whole interval is above 0; **worse** = below 0; "
        "**no clear difference** = the interval contains 0.",
        "",
        "## Answer",
        "",
        "Does the Panchayat forecast beat the block forecast? Temporal holdout, mean absolute error:",
        "",
        *headline(s),
        "",
        "## Where the model does not help",
        "",
        "Every variable and stratum where the Panchayat forecast is not clearly better than B0 or B1, taken "
        "from the job's notes, then the decisions where it gives worse advice.",
        "",
        *[f"- {n}" for n in s["notes"][4:]],
        *impact_losses(imp),
        "",
        "Reading guide: \"tie\" means the data cannot tell the model and the baseline apart; it is not "
        "a win.",
        *correction_share(s),
        "",
        "## Three checks, mean absolute error",
        "",
        *checks_table(s),
        "",
        "## Other scores",
        "",
        "Quantile loss scores the p10, p50 and p90 forecast. The baselines have no interval and are scored "
        "as point forecasts, so this score mainly rewards having an interval; it is not used for verdicts. "
        "Bias is forecast minus truth.",
        "",
        *other_metrics_table(s),
        "",
        "## Rain events",
        "",
        "The model says yes when its calibrated probability is 0.5 or more; B0 and B1 say yes when the block "
        "forecast reaches the threshold. Brier skill is against TRAIN monthly climatology.",
        "",
        *events_table(s),
        "",
        "Reliability (a well-calibrated forecast has observed frequency close to the bin centre):",
        "",
        *reliability_table(v),
        "",
        "## Interval coverage",
        "",
        "Nominal 80% interval [p10, p90]. Width is shown next to coverage because a wide interval covers "
        "easily. Rain coverage on all days is dominated by dry days; see the wet-day row.",
        "",
        *coverage_table(v),
        "",
        "## Block consistency",
        "",
        "Largest |block mean of Panchayat forecasts - corrected block forecast| on TEST: " +
        ", ".join(f"{k} {x:.1e}" for k, x in s["block_mean_error"].items() if k in VARS)
        + " (must be below 1e-6).",
        "",
        "## Strata",
        *strata_tables(s),
        "",
        "## Decision replay",
        "",
        "Lead day 1, every Panchayat, every issue date. Correct = acted and the event came, or did not act "
        "and it stayed away; wasted wait = acted (held spraying, alerted, waited) and the event did not "
        "come; washed off = did not act and the event came. Counts and rates only, no money values. "
        "Thresholds are placeholders awaiting expert review.",
        "",
        *[f"- {DECISION_NAMES[r]}: model rule \"{it['rule']['model']['en']}\" Block rule "
          f"\"{it['rule']['block']['en']}\""
          for r, it in {i["decision"]: i for i in imp["items"].values()}.items()],
        "",
        *impact_table(imp),
        "",
        "## Notes from the job",
        "",
        *[f"- {n}" for n in s["notes"][:4]],
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    """Read the job's files and write the report."""
    art = Path(argv[0]) if argv else ART
    v = json.loads((art / "verification.json").read_text())
    imp = json.loads((art / "impact.json").read_text())
    OUT.write_text(build(v, imp))
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
