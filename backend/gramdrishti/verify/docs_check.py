"""Check the submission documents against the code's outputs (S16).

Three checks, all read-only:

1. Links: every relative link and image in ``README.md`` and ``docs/*.md`` points to a file that exists,
   and every ``#anchor`` into a Markdown file matches one of its headings (GitHub's slug rules).
2. Numbers: the tables between ``<!-- docs-check:<name>:start -->`` and ``:end -->`` in
   ``docs/model_card.md``, and the sentences in ``CLAIMS``, must match the verification job's files
   (``verification.json``, ``impact.json``) at the precision they are written in.
3. Mermaid: every ```` ```mermaid ```` block starts with a known diagram type. ``--mermaid-html PATH``
   also writes a page that renders every block with Mermaid in a browser, for a visual check.

Default files are the committed record of the verified model
(``gramdrishti/verify/records/<version>/``), so the check runs on a fresh clone and in CI.

Run: ``cd backend && python -m gramdrishti.verify.docs_check``
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from gramdrishti.data.config import ROOT

RECORD = Path(__file__).resolve().parent / "records" / "s5-lgbm-9b632a7b1b"
CHECK_KEYS = {"Temporal holdout": "temporal_holdout", "Leave-one-block-out": "leave_one_block_out",
              "Station check": "station"}
EVENT_KEYS = {"1 mm or more": "rain_ge_1mm", "2.5 mm or more": "rain_ge_2_5mm",
              "10 mm or more": "rain_ge_10mm", "35 mm or more": "rain_ge_35mm"}
DECISION_KEYS = {"Spray tomorrow?": "spray", "Heat alert": "heat_alert",
                 "Irrigate or wait": "irrigation_wait"}
MERMAID_TYPES = ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram",
                 "gantt", "pie", "journey", "timeline", "mindmap")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
NUM = re.compile(r"[-+]?\d[\d,]*\.?\d*(?:e[-+]?\d+)?")


@dataclass(frozen=True)
class Claim:
    """A sentence in a document that states a number from the verification files."""

    file: str
    text: str                 # must appear in the file exactly
    value: str                # the number as written inside ``text``
    path: tuple               # where to read it: ("v"|"i", keys...) into verification or impact
    scale: float = 1.0        # 100 for percent


def _b1(var: str) -> tuple:
    """MAE skill against B1 in the temporal holdout."""
    return ("metric", "temporal_holdout", var, "MAE", "skill_vs_b1")


def _imp(decision: str, forecast: str, outcome: str) -> tuple:
    """A count from the whole-TEST decision replay."""
    return ("impact", f"test_2024/{decision}", forecast, outcome)


GAP = ("block_mean_error", "rain")
WET = ("coverage", "rain", "observed_rain>=1mm")
QNA, DEMO = "docs/qna.md", "docs/demo_script.md"
CARD, OUTLINE = "docs/model_card.md", "docs/presentation_outline.md"
RELEASE, DAY = "docs/RELEASE_NOTES.md", "docs/demo_day_checklist.md"


def _release_cells() -> list[Claim]:
    """The release notes' skill table: skill and 95 % interval against B0 and B1, per variable."""
    cells = {  # as written in docs/RELEASE_NOTES.md
        "rain": ("+13.7 % (+4.0 to +27.9)", "-3.8 % (-8.1 to +0.8)"),
        "tmax": ("+6.8 % (+5.1 to +8.4)", "+5.1 % (+3.8 to +6.6)"),
        "tmin": ("+14.6 % (+13.2 to +16.2)", "+3.8 % (+2.1 to +5.5)"),
        "rh": ("+5.3 % (+4.8 to +5.8)", "+4.2 % (+3.7 to +4.6)"),
        "wind": ("+36.2 % (+34.9 to +37.4)", "+1.9 % (+1.8 to +2.0)"),
    }
    out = []
    for var, (b0, b1) in cells.items():
        for cell, skill, ci in ((b0, "skill_vs_b0", "skill_ci95"), (b1, "skill_vs_b1", "skill_vs_b1_ci95")):
            base = ("metric", "temporal_holdout", var, "MAE")
            paths = (base + (skill,), base + (ci, 0), base + (ci, 1))
            for written, path in zip(NUM.findall(cell), paths, strict=True):
                out.append(Claim(RELEASE, cell, written, path, 100))
    return out
CLAIMS: list[Claim] = [
    Claim("README.md", "maximum temperature (+5.1 %)", "+5.1", _b1("tmax"), 100),
    Claim("README.md", "minimum temperature (+3.8 %)", "+3.8", _b1("tmin"), 100),
    Claim("README.md", "humidity (+4.2 %)", "+4.2", _b1("rh"), 100),
    Claim("README.md", "wind (+1.9 %)", "+1.9", _b1("wind"), 100),
    Claim("README.md", "(-3.8 %, a tie)", "-3.8", _b1("rain"), 100),
    Claim("README.md", "largest gap 1.4e-14", "1.4e-14", GAP),
    Claim(QNA, "wind (1.9 % to 5.1 %)", "1.9", _b1("wind"), 100),
    Claim(QNA, "wind (1.9 % to 5.1 %)", "5.1", _b1("tmax"), 100),
    Claim(QNA, "the largest gap was 1.4e-14", "1.4e-14", GAP),
    Claim(QNA, "covers 78 % for maximum temperature", "78", ("coverage", "tmax", "all"), 100),
    Claim(QNA, "81 % for minimum temperature", "81", ("coverage", "tmin", "all"), 100),
    Claim(QNA, "85 % for humidity", "85", ("coverage", "rh", "all"), 100),
    Claim(QNA, "90 % for wind", "90", ("coverage", "wind", "all"), 100),
    Claim(QNA, "it covers only 51 %", "51", WET, 100),
    Claim(QNA, "(1,628 against 527)", "1,628", _imp("heat_alert", "model", "wasted_wait")),
    Claim(QNA, "(1,628 against 527)", "527", _imp("heat_alert", "block_baseline", "wasted_wait")),
    Claim(DEMO, "by 1.9 to 5.1 percent", "1.9", _b1("wind"), 100),
    Claim(DEMO, "by 1.9 to 5.1 percent", "5.1", _b1("tmax"), 100),
    Claim(DEMO, "217 with ours", "217", _imp("spray", "model", "wasted_wait")),
    Claim(DEMO, "554 unnecessary waits", "554", _imp("spray", "block_baseline", "wasted_wait")),
    Claim(DEMO, "179 against 68", "179", _imp("spray", "model", "washed_off")),
    Claim(DEMO, "179 against 68", "68", _imp("spray", "block_baseline", "washed_off")),
    Claim(CARD, "(mean width 28.7 mm)", "28.7", ("coverage_width", "rain", "observed_rain>=1mm")),
    Claim(CARD, "on TEST the largest gap was 1.4e-14", "1.4e-14", GAP),
    Claim(OUTLINE, "(217 against 554)", "217", _imp("spray", "model", "wasted_wait")),
    Claim(OUTLINE, "(217 against 554)", "554", _imp("spray", "block_baseline", "wasted_wait")),
    Claim(OUTLINE, "(179 against 68)", "179", _imp("spray", "model", "washed_off")),
    Claim(OUTLINE, "51 % for rain on wet days", "51", WET, 100),
    Claim(RELEASE, "The largest gap is 1.4e-14", "1.4e-14", GAP),
    Claim(DAY, "(rain MAE 1.070 for the model)", "1.070",
          ("metric", "temporal_holdout", "rain", "MAE", "model")),
    *_release_cells(),
]


# ---------------------------------------------------------------- reading the job's files
def load_record(verification: Path, impact: Path) -> tuple[dict, dict]:
    """Return the parsed verification and impact files."""
    return json.loads(verification.read_text()), json.loads(impact.read_text())


def _find_metric(v: dict, check: str, var: str, name: str) -> dict:
    checks = {c["check"]: c for c in v["summary"]["checks"]}
    variables = checks[check]["variables"] if check in checks else v["summary"]["variables"]
    for row in variables:
        if row["var"] == var:
            for m in row["metrics"]:
                if m["name"] == name:
                    return m
    raise KeyError(f"{check} {var} {name}")


def _event(v: dict, key: str) -> dict:
    return next(e for e in v["summary"]["events"] if e["event"] == key)


def lookup(v: dict, imp: dict, path: tuple) -> float:
    """Read one number from the verification or impact file."""
    kind = path[0]
    if kind == "metric":
        value = _find_metric(v, path[1], path[2], path[3])[path[4]]
        return value[path[5]] if len(path) > 5 else value   # path[5]: 0 or 1 of a 95 % interval
    if kind == "block_mean_error":
        return v["summary"]["block_mean_error"][path[1]]
    if kind in ("coverage", "coverage_width"):
        row = next(c for c in v["coverage"]["items"] if c["var"] == path[1] and c["stratum"] == path[2])
        return row["empirical" if kind == "coverage" else "mean_width"]
    if kind == "impact":
        item = imp["items"][path[1]]
        return item[path[2]][path[3]]
    raise KeyError(path)


# ---------------------------------------------------------------- comparing numbers
def _decimals(written: str) -> int:
    s = written.replace(",", "").lstrip("+-")
    if "e" in s.lower():
        mant = s.lower().split("e")[0]
        return len(mant.split(".")[1]) if "." in mant else 0
    return len(s.split(".")[1]) if "." in s else 0


def matches(written: str, actual: float, scale: float = 1.0) -> bool:
    """True when ``written`` equals ``actual * scale`` at the precision it is written with."""
    s = written.replace(",", "")
    value = float(s)
    target = actual * scale
    if "e" in s.lower():
        exp = int(s.lower().split("e")[1])
        tol = 0.5 * 10 ** (exp - _decimals(written))
    else:
        tol = 0.5 * 10 ** -_decimals(written)
    return abs(value - target) <= tol * (1 + 1e-9)   # relative slack only for float noise


def _verdict(ci: list[float] | None) -> str:
    if ci is None:
        return "too_few_days"
    return "win" if ci[0] > 0 else "loss" if ci[1] < 0 else "tie"


def _section(text: str, name: str) -> list[list[str]]:
    m = re.search(rf"<!-- docs-check:{name}:start -->\n(.*?)<!-- docs-check:{name}:end -->", text, re.S)
    if not m:
        raise ValueError(f"no docs-check:{name} section")
    rows = [r.strip() for r in m.group(1).strip().splitlines()]
    return [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]   # skip header and rule


def _skill(cell: str) -> tuple[str, str, str]:
    """'+13.7 (+4.0 to +27.9)' -> ('+13.7', '+4.0', '+27.9')."""
    m = re.fullmatch(r"([-+]\d+\.\d) \(([-+]\d+\.\d) to ([-+]\d+\.\d)\)", cell)
    if not m:
        raise ValueError(f"cannot read skill cell {cell!r}")
    return m.group(1), m.group(2), m.group(3)


def check_mae_table(text: str, v: dict) -> list[str]:
    """Compare the model card's MAE table with the verification file."""
    errors = []
    for check, var, _unit, model, b0, b1, s0, s1, verdicts in _section(text, "mae"):
        m = _find_metric(v, CHECK_KEYS[check], var, "MAE")
        where = f"model_card MAE {check} {var}"
        cells = (("model", model, m["model"]), ("B0", b0, m["b0"]), ("B1", b1, m["b1"]))
        for label, written, actual in cells:
            if not matches(written, actual):
                errors.append(f"{where}: {label} {written} but the file has {actual}")
        for label, cell, skill, ci in (("vs B0", s0, m["skill_vs_b0"], m["skill_ci95"]),
                                       ("vs B1", s1, m["skill_vs_b1"], m["skill_vs_b1_ci95"])):
            point, lo, hi = _skill(cell)
            for w, a in ((point, skill), (lo, ci[0]), (hi, ci[1])):
                if not matches(w, a, 100):
                    errors.append(f"{where}: skill {label} {w} but the file has {100 * a:.3f}")
        expected = f"{_verdict(m['skill_ci95'])} / {_verdict(m['skill_vs_b1_ci95'])}"
        if verdicts != expected:
            errors.append(f"{where}: verdict {verdicts!r} but the intervals give {expected!r}")
    return errors


def check_events_table(text: str, v: dict) -> list[str]:
    """Compare the model card's rain-event table with the verification file."""
    errors = []
    for label, csi, csi_b0, csi_b1, bss in _section(text, "events"):
        e = _event(v, EVENT_KEYS[label])
        base = {b["baseline"]: b for b in e["baselines"]}
        for name, w, a in (("CSI", csi, e["csi"]), ("CSI B0", csi_b0, base["b0"]["csi"]),
                           ("CSI B1", csi_b1, base["b1"]["csi"]),
                           ("Brier skill", bss, e["brier_skill_vs_climatology"])):
            if not matches(w, a):
                errors.append(f"model_card events {label}: {name} {w} but the file has {a}")
    return errors


def check_impact_table(text: str, imp: dict) -> list[str]:
    """Compare the model card's decision replay table (whole TEST) with the impact file."""
    errors = []
    for label, *cells in _section(text, "impact"):
        item = imp["items"][f"test_2024/{DECISION_KEYS[label]}"]
        for cell, key in zip(cells, ("model", "block_baseline", "block_corrected"), strict=True):
            written = [c.strip() for c in cell.split("/")]
            actual = [item[key][k] for k in ("correct", "wasted_wait", "washed_off")]
            for w, a in zip(written, actual, strict=True):
                if not matches(w, a):
                    errors.append(f"model_card impact {label} {key}: {w} but the file has {a}")
    return errors


def check_claims(root: Path, v: dict, imp: dict, claims: list[Claim] = CLAIMS) -> list[str]:
    """Every claim sentence must be in its file and its number must match the files."""
    errors = []
    for c in claims:
        text = (root / c.file).read_text()
        if c.text not in text:
            errors.append(f"{c.file}: claim text not found: {c.text!r}")
            continue
        if c.value not in c.text:
            errors.append(f"{c.file}: {c.value!r} is not inside {c.text!r}")
            continue
        actual = lookup(v, imp, c.path)
        if not matches(c.value, actual, c.scale):
            errors.append(f"{c.file}: {c.text!r} says {c.value} but the file has {actual * c.scale:.4g}")
    return errors


# ---------------------------------------------------------------- links
def slug(heading: str) -> str:
    """GitHub's heading anchor: lower case, punctuation removed, spaces to hyphens."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def anchors(md: str) -> set[str]:
    """Anchors of every Markdown heading outside code blocks."""
    out, in_code = set(), False
    for line in md.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and line.startswith("#"):
            out.add(slug(line.lstrip("#")))
    return out


def _strip_code(md: str) -> str:
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    return re.sub(r"`[^`]*`", "", md)


def check_links(root: Path, files: list[Path]) -> tuple[list[str], int]:
    """Broken relative links and anchors, and the number of links checked."""
    errors, n = [], 0
    for f in files:
        for target in LINK.findall(_strip_code(f.read_text())):
            if re.match(r"^[a-z]+:", target):          # http:, https:, mailto:
                continue
            n += 1
            path, _, anchor = target.partition("#")
            dest = (f.parent / path).resolve() if path else f
            rel = f.relative_to(root)
            if not dest.exists():
                errors.append(f"{rel}: link to missing {target}")
            elif anchor and dest.suffix == ".md" and anchor not in anchors(dest.read_text()):
                errors.append(f"{rel}: no heading for #{anchor} in {dest.relative_to(root)}")
    return errors, n


# ---------------------------------------------------------------- mermaid
def mermaid_blocks(files: list[Path]) -> list[tuple[Path, str]]:
    """Every ```mermaid block with its file."""
    out = []
    for f in files:
        for block in re.findall(r"```mermaid\n(.*?)```", f.read_text(), re.S):
            out.append((f, block))
    return out


def check_mermaid(blocks: list[tuple[Path, str]], root: Path) -> list[str]:
    """Each block starts with a known diagram type and has balanced brackets and quotes."""
    errors = []
    for f, block in blocks:
        first = block.strip().split()[0]
        if first not in MERMAID_TYPES:
            errors.append(f"{f.relative_to(root)}: mermaid block starts with {first!r}")
        for a, b in ("[]", "()", "{}"):
            if block.count(a) != block.count(b):
                errors.append(f"{f.relative_to(root)}: unbalanced {a}{b} in a mermaid block")
        if block.count('"') % 2:
            errors.append(f"{f.relative_to(root)}: odd number of quotes in a mermaid block")
    return errors


def mermaid_html(blocks: list[tuple[Path, str]], root: Path) -> str:
    """A page that renders every block with Mermaid and writes OK or the error per block."""
    parts = []
    for i, (f, block) in enumerate(blocks):
        parts.append(f'<h2>{i + 1}. {html.escape(str(f.relative_to(root)))}</h2>'
                     f'<pre class="src" id="src{i}">{html.escape(block)}</pre><div id="out{i}"></div>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Mermaid check</title>
<style>body{{font-family:system-ui;margin:16px}} pre.src{{display:none}}</style></head>
<body><h1>Mermaid check</h1><pre id="result">rendering...</pre>{''.join(parts)}
<script type="module">
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
mermaid.initialize({{startOnLoad: false, securityLevel: "strict"}});
const lines = [];
for (let i = 0; i < {len(blocks)}; i++) {{
  const src = document.getElementById("src" + i).textContent;
  try {{
    await mermaid.parse(src);
    const {{svg}} = await mermaid.render("m" + i, src);
    document.getElementById("out" + i).innerHTML = svg;
    lines.push((i + 1) + " OK");
  }} catch (e) {{ lines.push((i + 1) + " ERROR " + (e.message || e)); }}
}}
document.getElementById("result").textContent = lines.join("\\n");
</script></body></html>"""


# ---------------------------------------------------------------- main
def doc_files(root: Path) -> list[Path]:
    """README plus every Markdown file in docs/."""
    return [root / "README.md", *sorted((root / "docs").glob("*.md"))]


def run(root: Path, verification: Path, impact: Path) -> tuple[list[str], dict]:
    """Run every check; return the errors and counts for the summary."""
    v, imp = load_record(verification, impact)
    files = doc_files(root)
    card = (root / "docs" / "model_card.md").read_text()
    errors = [*check_mae_table(card, v), *check_events_table(card, v), *check_impact_table(card, imp),
              *check_claims(root, v, imp)]
    link_errors, n_links = check_links(root, files)
    blocks = mermaid_blocks(files)
    errors += link_errors + check_mermaid(blocks, root)
    counts = {"files": len(files), "links": n_links, "mermaid": len(blocks), "claims": len(CLAIMS),
              "table_rows": sum(len(_section(card, s)) for s in ("mae", "events", "impact"))}
    return errors, counts


def main(argv: list[str] | None = None) -> int:
    """Command line entry point; exit code 1 when any check fails."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verification", type=Path, default=RECORD / "verification.json")
    ap.add_argument("--impact", type=Path, default=RECORD / "impact.json")
    ap.add_argument("--mermaid-html", type=Path, help="also write a page that renders every Mermaid block")
    args = ap.parse_args(argv)
    errors, counts = run(ROOT, args.verification, args.impact)
    if args.mermaid_html:
        args.mermaid_html.write_text(mermaid_html(mermaid_blocks(doc_files(ROOT)), ROOT))
        print(f"wrote {args.mermaid_html}")
    print(f"checked {counts['files']} files: {counts['links']} relative links, {counts['mermaid']} mermaid "
          f"blocks, {counts['table_rows']} model card table rows, {counts['claims']} numeric claims "
          f"against {args.verification.name} and {args.impact.name}")
    for e in errors:
        print(f"FAIL {e}")
    print("all checks passed" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
