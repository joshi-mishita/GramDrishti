"""Contract artefacts: examples validate, openapi.json and examples are up to date, demo dates reproduce."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gramdrishti.api import schemas as s
from gramdrishti.contract import make_examples
from gramdrishti.contract.pick_demo_dates import OUT as DEMO_FILE
from gramdrishti.contract.pick_demo_dates import issued_summary, load_demo_dates, pick, split_of
from gramdrishti.data import loaders
from gramdrishti.data.config import ROOT
from gramdrishti.export_openapi import OUT as OPENAPI_FILE
from gramdrishti.export_openapi import openapi_text

from .conftest import needs_oracle

EXAMPLES = ROOT / "contract" / "examples"
INDEX = json.loads((EXAMPLES / "index.json").read_text())


@pytest.mark.parametrize("entry", INDEX["files"], ids=lambda e: e["file"])
def test_example_validates(entry: dict) -> None:
    payload = json.loads((EXAMPLES / entry["file"]).read_text(encoding="utf-8"))
    getattr(s, entry["model"]).model_validate(payload)
    if entry["model"] != "ErrorResponse" and isinstance(payload, dict) and "data_mode" in payload:
        assert payload["data_mode"] == "mock"


def test_index_lists_every_file() -> None:
    on_disk = {p.name for p in EXAMPLES.iterdir() if p.suffix in (".json", ".geojson")} - {"index.json"}
    assert on_disk == {e["file"] for e in INDEX["files"]}


def test_every_path_has_an_example() -> None:
    doc = json.loads(OPENAPI_FILE.read_text())
    covered = {e["path"].split("?")[0] for e in INDEX["files"]}
    for path in doc["paths"]:
        parts = path.split("/")
        assert any(len(c.split("/")) == len(parts) and all(a == b or b.startswith("{")
                                                            for a, b in zip(c.split("/"), parts, strict=True))
                   for c in covered), f"no example for {path}"


def test_example_geojson_is_lon_lat() -> None:
    for name in ("panchayats.geojson", "blocks.geojson"):
        g = json.loads((EXAMPLES / name).read_text())
        for f in g["features"]:
            for ring in f["geometry"]["coordinates"]:
                assert all(68 < lon < 98 and 6 < lat < 38 for lon, lat in ring)


def test_openapi_is_up_to_date() -> None:
    assert OPENAPI_FILE.read_text(encoding="utf-8") == openapi_text(), \
        "contract/openapi.json is stale: run `python -m gramdrishti.export_openapi`"


def test_openapi_version_matches_changelog() -> None:
    doc = json.loads(OPENAPI_FILE.read_text())
    assert doc["info"]["version"] == s.API_VERSION
    assert f"v{s.API_VERSION}" in (ROOT / "contract" / "CHANGELOG.md").read_text()


@needs_oracle
def test_examples_are_up_to_date(tmp_path: Path) -> None:
    make_examples.build(tmp_path)
    for p in sorted(tmp_path.iterdir()):
        assert p.read_text(encoding="utf-8") == (EXAMPLES / p.name).read_text(encoding="utf-8"), \
            f"{p.name} is stale: run `python -m gramdrishti.contract.make_examples`"


def test_demo_dates_reproduce_without_the_oracle(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse() -> None:
        raise AssertionError("demo date selection must not read the synthetic oracle")

    monkeypatch.setattr(loaders, "load_truth", refuse)
    monkeypatch.setattr(loaders, "load_block_truth", refuse)
    monkeypatch.setattr(loaders, "load_obs", refuse)
    picks = pick(issued_summary(loaders.load_fc()))
    assert [p.__dict__ for p in picks] == [p.__dict__ for p in load_demo_dates(DEMO_FILE)]


def test_demo_dates_splits() -> None:
    picks = load_demo_dates()
    assert len(picks) == 8 and len({p.date for p in picks}) == 8
    assert all(split_of(p.date) == p.split for p in picks)
    assert sum(p.split == "train" for p in picks) <= 2
    assert all(p.split in ("train", "test") for p in picks)
