import shutil

import pandas as pd
import pytest

from gramdrishti.data import loaders
from gramdrishti.data.config import COLS, DEFAULT_DATA, FILES
from gramdrishti.data.loaders import REQUIRED, DataFileError, RealModeError

from .conftest import needs_oracle

TABLE_LOADERS = {
    "static": loaders.load_static, "blocks": loaders.load_blocks, "stations": loaders.load_stations,
    "obs": loaders.load_obs, "fc": loaders.load_fc, "sat": loaders.load_sat, "crops": loaders.load_crops,
    "calendar": loaders.load_calendar, "feedback": loaders.load_feedback,
}


@pytest.mark.parametrize("key", TABLE_LOADERS)
def test_mock_loaders_return_required_columns(key):
    df = TABLE_LOADERS[key]()
    assert len(df) > 0
    assert set(REQUIRED[key]) <= set(df.columns)


def test_dates_are_parsed_and_ids_are_strings(fc, obs, static):
    assert pd.api.types.is_datetime64_any_dtype(fc["valid_date"])
    assert pd.api.types.is_datetime64_any_dtype(fc["issue_date"])
    assert pd.api.types.is_datetime64_any_dtype(obs["date"])
    assert (fc["valid_date"] - fc["issue_date"]).dt.days.equals(fc["lead_day"].astype("int64"))
    assert pd.api.types.is_string_dtype(static["panchayat_id"])


def test_forecast_and_obs_share_variable_columns(fc, obs):
    for col in COLS.values():
        assert col in fc.columns and col in obs.columns


def test_geojson_is_lon_lat(static):
    fc = loaders.load_panchayat_geojson()
    assert fc["type"] == "FeatureCollection"
    lon, lat = fc["features"][0]["geometry"]["coordinates"][0][0]
    assert static["lon"].min() - 1 < lon < static["lon"].max() + 1
    assert static["lat"].min() - 1 < lat < static["lat"].max() + 1
    assert loaders.load_block_geojson()["type"] == "FeatureCollection"


@needs_oracle
def test_truth_loads_in_mock_mode():
    assert set(REQUIRED["truth"]) <= set(loaders.load_truth().columns)
    assert set(REQUIRED["block_truth"]) <= set(loaders.load_block_truth().columns)


@pytest.mark.parametrize("fn", [loaders.load_truth, loaders.load_block_truth])
def test_truth_raises_clear_error_in_real_mode(monkeypatch, fn):
    monkeypatch.setenv("DATA_MODE", "real")
    with pytest.raises(RealModeError, match="exists only in DATA_MODE=mock"):
        fn()


def test_real_mode_uses_same_columns(monkeypatch, tmp_path):
    """Real files with the mock columns load to identical column names and dtypes."""
    real = tmp_path / "real"
    real.mkdir()
    for key in ("static", "obs", "fc"):
        shutil.copy(DEFAULT_DATA / FILES["mock"][key], tmp_path / FILES["real"][key])
    mock = {k: TABLE_LOADERS[k]() for k in ("static", "obs", "fc")}
    monkeypatch.setenv("DATA_MODE", "real")
    monkeypatch.setenv("GRAMDRISHTI_DATA_DIR", str(tmp_path))
    for key, df in mock.items():
        got = TABLE_LOADERS[key]()
        assert list(got.columns) == list(df.columns)
        assert list(got.dtypes) == list(df.dtypes)


def test_missing_real_file_names_the_path(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_MODE", "real")
    monkeypatch.setenv("GRAMDRISHTI_DATA_DIR", str(tmp_path))
    with pytest.raises(DataFileError, match="station_observations.csv"):
        loaders.load_obs()


def test_missing_column_is_reported(monkeypatch, tmp_path):
    df = pd.read_csv(DEFAULT_DATA / FILES["mock"]["stations"]).drop(columns=["elevation_m"])
    df.to_csv(tmp_path / FILES["mock"]["stations"], index=False)
    monkeypatch.setenv("GRAMDRISHTI_DATA_DIR", str(tmp_path))
    with pytest.raises(DataFileError, match="elevation_m"):
        loaders.load_stations()
