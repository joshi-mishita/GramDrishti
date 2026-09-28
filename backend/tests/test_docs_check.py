"""The submission documents agree with the verification record, and the checker catches drift (S16)."""

from __future__ import annotations

from pathlib import Path

import pytest

from gramdrishti.data.config import ROOT
from gramdrishti.verify import docs_check as dc

VER, IMP = dc.RECORD / "verification.json", dc.RECORD / "impact.json"


@pytest.fixture(scope="module")
def record() -> tuple[dict, dict]:
    return dc.load_record(VER, IMP)


def test_repository_docs_pass() -> None:
    errors, counts = dc.run(ROOT, VER, IMP)
    assert errors == []
    assert counts["table_rows"] == 15 + 4 + 3
    assert counts["mermaid"] >= 3


def test_matches_uses_the_written_precision() -> None:
    assert dc.matches("1.070", 1.07045)
    assert not dc.matches("1.071", 1.07045)
    assert dc.matches("+13.7", 0.136683, 100)
    assert not dc.matches("+13.8", 0.136683, 100)
    assert dc.matches("1,628", 1628)
    assert dc.matches("1.4e-14", 1.42109e-14)
    assert not dc.matches("2.4e-14", 1.42109e-14)


def test_a_wrong_number_in_the_mae_table_is_caught(record) -> None:
    card = (ROOT / "docs" / "model_card.md").read_text()
    bad = card.replace("| Temporal holdout | rain | mm | 1.070 |", "| Temporal holdout | rain | mm | 1.050 |")
    assert bad != card
    assert any("model 1.050" in e for e in dc.check_mae_table(bad, record[0]))


def test_a_wrong_verdict_is_caught(record) -> None:
    card = (ROOT / "docs" / "model_card.md").read_text()
    bad = card.replace("| -3.8 (-8.1 to +0.8) | win / tie |", "| -3.8 (-8.1 to +0.8) | win / win |", 1)
    assert bad != card
    assert any("verdict" in e for e in dc.check_mae_table(bad, record[0]))


def test_a_wrong_impact_count_is_caught(record) -> None:
    card = (ROOT / "docs" / "model_card.md").read_text()
    bad = card.replace("14,364 / 217 / 179", "14,364 / 117 / 179")
    assert any("117" in e for e in dc.check_impact_table(bad, record[1]))


def test_a_claim_that_drifts_is_caught(tmp_path: Path, record) -> None:
    (tmp_path / "a.md").write_text("Heat: (1,700 against 527).")
    claim = dc.Claim("a.md", "(1,700 against 527)", "1,700",
                     ("impact", "test_2024/heat_alert", "model", "wasted_wait"))
    errors = dc.check_claims(tmp_path, *record, claims=[claim])
    assert errors and "1628" in errors[0]
    missing = dc.Claim("a.md", "not in the file", "1", ("block_mean_error", "rain"))
    assert "not found" in dc.check_claims(tmp_path, *record, claims=[missing])[0]


def test_release_notes_skill_intervals_are_checked(tmp_path: Path, record) -> None:
    """S17: interval ends are read from the record; a wrong end in the release table is caught."""
    claims = [c for c in dc.CLAIMS if c.file == dc.RELEASE and c.path[-1] in (0, 1)]
    assert len(claims) == 20          # 5 variables x (B0, B1) x (low, high)
    cell = "+13.7 % (+4.0 to +27.9)"
    (tmp_path / "docs").mkdir()
    (tmp_path / dc.RELEASE).write_text(cell.replace("+4.0", "+5.0"))
    low = next(c for c in claims if c.text == cell and c.value == "+4.0")
    wrong = dc.Claim(dc.RELEASE, cell.replace("+4.0", "+5.0"), "+5.0", low.path, 100)
    assert "says +5.0" in dc.check_claims(tmp_path, *record, claims=[wrong])[0]


def test_broken_links_and_anchors_are_caught(tmp_path: Path) -> None:
    (tmp_path / "b.md").write_text("# Production path (future, not built)\n")
    a = tmp_path / "a.md"
    a.write_text("[ok](b.md#production-path-future-not-built) [gone](c.md) [bad](b.md#nope) "
                 "[web](https://example.org) `[code](x.md)`")
    errors, n = dc.check_links(tmp_path, [a])
    assert n == 3
    assert any("missing c.md" in e for e in errors)
    assert any("#nope" in e for e in errors)
    assert len(errors) == 2


def test_mermaid_blocks_are_checked(tmp_path: Path) -> None:
    f = tmp_path / "m.md"
    f.write_text("```mermaid\nflowchart LR\n  A[x] --> B\n```\n```mermaid\nflowchat LR\n  A[x --> B\n```\n")
    blocks = dc.mermaid_blocks([f])
    assert len(blocks) == 2
    errors = dc.check_mermaid(blocks, tmp_path)
    assert any("'flowchat'" in e for e in errors) and any("unbalanced" in e for e in errors)
    assert "mermaid.render" in dc.mermaid_html(blocks, tmp_path)
