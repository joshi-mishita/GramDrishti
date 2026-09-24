"""data/generate_mock_data.py with the default seed reproduces the committed files."""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gramdrishti.data.config import DEFAULT_DATA

GENERATOR = DEFAULT_DATA / "generate_mock_data.py"
COMMITTED = [
    "panchayats_static.csv", "blocks.csv", "block_forecast_mock_nwp.csv", "stations.csv",
    "station_observations_mock.csv", "satellite_weekly_mock.csv", "panchayat_crops_mock.csv",
    "crop_calendar_PLACEHOLDER.csv", "farmer_feedback_mock.csv",
]
ORACLE = [
    "synthetic_oracle/panchayat_daily_SYNTHETIC_TRUTH.csv",
    "synthetic_oracle/block_daily_SYNTHETIC_TRUTH.csv",
]
# Values are rounded to 0.01 when written; a platform-dependent last-bit difference
# can flip one rounding step.
ATOL = 0.0101


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("mock")
    env = {**os.environ, "OUT": str(out), "SEED": "42"}
    subprocess.run([sys.executable, str(GENERATOR)], env=env, check=True, capture_output=True, timeout=300)
    return out


def _assert_same_csv(a: Path, b: Path) -> None:
    if a.read_bytes() == b.read_bytes():
        return
    x, y = pd.read_csv(a), pd.read_csv(b)
    assert list(x.columns) == list(y.columns) and len(x) == len(y), a.name
    for c in x.columns:
        if pd.api.types.is_numeric_dtype(x[c]):
            np.testing.assert_allclose(x[c], y[c], atol=ATOL, err_msg=f"{a.name}:{c}")
        else:
            assert x[c].equals(y[c]), f"{a.name}:{c}"


@pytest.mark.parametrize("name", COMMITTED)
def test_committed_files_reproduce(regenerated, name):
    _assert_same_csv(DEFAULT_DATA / name, regenerated / name)


@pytest.mark.parametrize("name", ORACLE)
def test_oracle_reproduces_if_present(regenerated, name):
    if not (DEFAULT_DATA / name).exists():
        pytest.skip("local oracle absent")
    _assert_same_csv(DEFAULT_DATA / name, regenerated / name)


def test_summary_reproduces(regenerated):
    a = json.loads((DEFAULT_DATA / "mock_data_summary.json").read_text())
    b = json.loads((regenerated / "mock_data_summary.json").read_text())
    assert a["rows"] == b["rows"] and a["seed"] == b["seed"] == 42
    for k, v in a["within_block_spread_planted"].items():
        assert b["within_block_spread_planted"][k] == pytest.approx(v, rel=1e-9)


def test_geojson_reproduces(regenerated):
    pytest.importorskip("shapely")
    for name in ("panchayats_SYNTHETIC.geojson", "blocks_SYNTHETIC.geojson"):
        a = json.loads((DEFAULT_DATA / name).read_text())
        b = json.loads((regenerated / name).read_text())
        assert [f["properties"] for f in a["features"]] == [f["properties"] for f in b["features"]]
        ca = np.array(a["features"][0]["geometry"]["coordinates"][0])
        cb = np.array(b["features"][0]["geometry"]["coordinates"][0])
        np.testing.assert_allclose(ca, cb, atol=1e-9)
