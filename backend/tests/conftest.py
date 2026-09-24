"""Shared fixtures. Tests that need the synthetic oracle skip with a clear message when it is absent."""

from __future__ import annotations

import pandas as pd
import pytest

from gramdrishti.data import loaders
from gramdrishti.data.config import DEFAULT_DATA, FILES

ORACLE_PRESENT = (DEFAULT_DATA / FILES["mock"]["truth"]).exists()
needs_oracle = pytest.mark.skipif(
    not ORACLE_PRESENT, reason="data/synthetic_oracle/ missing: run `python data/generate_mock_data.py`"
)


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts in mock mode on the repo's data folder unless it changes that itself."""
    monkeypatch.setenv("DATA_MODE", "mock")
    monkeypatch.delenv("GRAMDRISHTI_DATA_DIR", raising=False)


@pytest.fixture(scope="session")
def fc() -> pd.DataFrame:
    return loaders.load_fc()


@pytest.fixture(scope="session")
def static() -> pd.DataFrame:
    return loaders.load_static()


@pytest.fixture(scope="session")
def stations() -> pd.DataFrame:
    return loaders.load_stations()


@pytest.fixture(scope="session")
def obs() -> pd.DataFrame:
    return loaders.load_obs()


@pytest.fixture(scope="session")
def block_truth() -> pd.DataFrame:
    if not ORACLE_PRESENT:
        pytest.skip("data/synthetic_oracle/ missing: run `python data/generate_mock_data.py`")
    return loaders.load_block_truth()  # MOCK ONLY: proxy target in tests
