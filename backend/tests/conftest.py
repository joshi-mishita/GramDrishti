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


@pytest.fixture(scope="session")
def _test_db(tmp_path_factory: pytest.TempPathFactory):
    return tmp_path_factory.mktemp("store") / "default.sqlite"


@pytest.fixture(autouse=True)
def _mock_mode(monkeypatch: pytest.MonkeyPatch, _test_db) -> None:
    """Every test starts in mock mode on the repo's data folder unless it changes that itself, and never
    writes to the real advisory database in ``backend/artifacts/``."""
    monkeypatch.setenv("DATA_MODE", "mock")
    monkeypatch.delenv("GRAMDRISHTI_DATA_DIR", raising=False)
    monkeypatch.setenv("GRAMDRISHTI_DB", str(_test_db))


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
def small_prep():
    """Prepared TRAIN and CALIB tables with every 4th TRAIN issue date (fast fits)."""
    if not ORACLE_PRESENT:
        pytest.skip("data/synthetic_oracle/ missing: run `python data/generate_mock_data.py`")
    from dataclasses import replace

    from gramdrishti.pipeline.train import prepare

    prep = prepare()
    keep = prep.train["issue_date"].isin(prep.train["issue_date"].drop_duplicates().iloc[::4])
    return replace(prep, train=prep.train[keep].reset_index(drop=True))


@pytest.fixture(scope="session")
def small_bundle(small_prep):
    """A fast model bundle (30 trees, every 4th TRAIN issue date) for API and snapshot tests."""
    from gramdrishti.models.artifacts import Bundle
    from gramdrishti.models.downscale import lgbm_params
    from gramdrishti.pipeline.train import fit_all

    prep = small_prep
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


@pytest.fixture(scope="session")
def calib_validation(small_bundle, small_prep):  # noqa: ANN001
    """The verification job run on 21 CALIB issue dates with the small bundle (never on TEST).
    Returns (Result, issue dates)."""
    from gramdrishti.verify import run_validation as rv

    issues = rv.evaluation_issue_dates(small_prep.inputs, "CALIB")[:21]
    res = rv.validate(small_bundle, small_prep.inputs, small_prep, window="CALIB", issue_dates=issues,
                      lobo=True, n_boot=100, log=lambda *_: None)
    return res, issues


@pytest.fixture(scope="session")
def verification_dir(calib_validation, tmp_path_factory: pytest.TempPathFactory):  # noqa: ANN001
    """``verification.json`` and ``impact.json`` from ``calib_validation`` in a temporary folder."""
    from gramdrishti.verify import run_validation as rv

    out = tmp_path_factory.mktemp("verification")
    rv.write(calib_validation[0], out)
    return out
