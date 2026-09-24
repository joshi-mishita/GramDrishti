import pandas as pd
import pytest

from gramdrishti.data import config
from gramdrishti.data.config import CALIB, TEST, TRAIN, WINDOWS, select_window, window_bounds

from .conftest import needs_oracle


def test_windows_ordered_contiguous_and_disjoint():
    bounds = [window_bounds(n) for n in ("TRAIN", "CALIB", "TEST")]
    for start, end in bounds:
        assert start <= end
    for (_, end), (next_start, _) in zip(bounds, bounds[1:], strict=False):
        assert end < next_start, "windows overlap"
        assert next_start - end == pd.Timedelta(days=1), "gap between windows"


def test_windows_match_spec():
    assert TRAIN == ("2023-01-01", "2024-04-30")
    assert CALIB == ("2024-05-01", "2024-07-15")
    assert TEST == ("2024-07-16", "2024-12-31")
    assert set(WINDOWS) == {"TRAIN", "CALIB", "TEST"}


def _assert_covered(dates: pd.Series) -> None:
    start, end = window_bounds("TRAIN")[0], window_bounds("TEST")[1]
    assert dates.min() == start and dates.max() == end
    days = pd.Series(pd.to_datetime(dates.unique()))
    inside = sum(len(select_window(pd.DataFrame({"d": days}), n, "d", allow_test=True)) for n in WINDOWS)
    assert inside == len(days), "every data date falls in exactly one window"


def test_windows_cover_forecast_and_obs(fc, obs):
    _assert_covered(fc["valid_date"])
    _assert_covered(obs["date"])


@needs_oracle
def test_windows_cover_truth(block_truth):
    _assert_covered(block_truth["date"])


def test_test_window_is_closed_by_default():
    df = pd.DataFrame({"d": pd.to_datetime(["2024-08-01", "2024-01-01"])})
    with pytest.raises(PermissionError):
        select_window(df, "TEST", "d")
    assert len(select_window(df, "TEST", "d", allow_test=True)) == 1
    assert len(select_window(df, "TRAIN", "d")) == 1


def test_data_mode(monkeypatch):
    assert config.data_mode() == "mock"
    monkeypatch.setenv("DATA_MODE", "REAL")
    assert config.data_mode() == "real"
    monkeypatch.setenv("DATA_MODE", "demo")
    with pytest.raises(ValueError):
        config.data_mode()


def test_seasons():
    d = pd.Series(pd.to_datetime(["2024-01-10", "2024-04-10", "2024-07-10", "2024-10-10", "2024-12-31"]))
    assert list(config.season_group(d)) == ["winter", "pre_monsoon", "monsoon", "post_monsoon", "winter"]
    expected = ["non_monsoon", "non_monsoon", "monsoon", "non_monsoon", "non_monsoon"]
    assert list(config.rain_season(d)) == expected
