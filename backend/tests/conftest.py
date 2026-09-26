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


SMALL_MODEL = {"n_estimators": 30, "num_leaves": 15}


@pytest.fixture(scope="session")
def small_bundle():
    """A fast model bundle (30 trees, every 4th TRAIN issue date) for API and snapshot tests."""
    if not ORACLE_PRESENT:
        pytest.skip("data/synthetic_oracle/ missing: run `python data/generate_mock_data.py`")
    from dataclasses import replace

    from gramdrishti.models.artifacts import Bundle
    from gramdrishti.models.downscale import lgbm_params
    from gramdrishti.pipeline.train import fit_all, prepare

    prep = prepare()
    keep = prep.train["issue_date"].isin(prep.train["issue_date"].drop_duplicates().iloc[::4])
    prep = replace(prep, train=prep.train[keep].reset_index(drop=True))
    models, offsets, _ = fit_all(prep, lgbm_params(SMALL_MODEL))
    config = {"model_version": "test-small", "data_hash_sha256": "test", "targets": list(models.regressors)}
    return Bundle(models, offsets, prep.bias, prep.encodings, config)


@pytest.fixture(scope="session")
def snapshot_dir(small_bundle, tmp_path_factory: pytest.TempPathFactory):
    """Snapshots for every demo date and the day before each, built with the small bundle."""
    from gramdrishti.pipeline.run_daily import demo_plan, run

    out = tmp_path_factory.mktemp("snapshots")
    run(demo_plan(), out=out, bundle=small_bundle, log=lambda *_: None)
    return out
