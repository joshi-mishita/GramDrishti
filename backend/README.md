# backend/

Python package `gramdrishti` (backend person). Python 3.11+.

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python ../data/generate_mock_data.py     # recreates data/synthetic_oracle/ (git-ignored answer key)
```

## Commands

| What | Command |
|---|---|
| Tests | `pytest -q` |
| Lint | `ruff check .` |
| Baseline report (TRAIN fit, CALIB scores) | `python -m gramdrishti.verify.baseline_report` |

Tests that need `data/synthetic_oracle/` are skipped with a message when it is missing. CI regenerates it.

## Layout (Backend Guide 2.3)

| Folder | Contents | Status |
|---|---|---|
| `gramdrishti/data/` | `config.py` (mode, paths, variables, windows), `loaders.py`, `qc.py` | S1 |
| `gramdrishti/models/` | `bias.py` (bias correction), `baselines.py` (B0, B1, B2) | S1 |
| `gramdrishti/verify/` | `metrics.py`, `baseline_report.py` | S1 |
| `gramdrishti/features/`, `agro/`, `advisory/`, `store/`, `pipeline/`, `api/` | empty packages | later sessions |

## Data mode

`DATA_MODE=mock` (default) reads the synthetic files in `data/`. `DATA_MODE=real` reads the same column names from `data/real/` (git-ignored; file names in `gramdrishti/data/config.py`). In real mode `load_truth()` and `load_block_truth()` raise `RealModeError`: Panchayat truth does not exist for real data. `GRAMDRISHTI_DATA_DIR` overrides the data folder (used by tests).

## Time windows

TRAIN 2023-01-01..2024-04-30, CALIB 2024-05-01..2024-07-15, TEST 2024-07-16..2024-12-31, defined once in `gramdrishti/data/config.py`. `select_window(..., "TEST")` raises unless `allow_test=True`, which only the verification session may pass.

Model artifacts and snapshots go in `backend/artifacts/` and are git-ignored.
