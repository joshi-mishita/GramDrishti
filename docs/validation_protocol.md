# Validation protocol

Written on 2026-09-27, before the TEST window was opened. It fixes what is evaluated, how, and what happens if anything changes after the results are seen.

## What is frozen

| Item | Value |
|---|---|
| Model version | `s5-lgbm-9b632a7b1b` (S5 bundle, the one the snapshots use) |
| Model data hash (TRAIN feature/target rows + CALIB feature/outcome rows) | `9b632a7b1bd008853fa0118350b9cad545722b970ebf358c95a8472d2b23114d` |
| Verification code | commit `4101fe4` (`backend/gramdrishti/verify/`) |
| Seed | 42 (LightGBM, bootstrap) |
| Data mode | mock (synthetic) |

sha256 of the data files the job reads:

| File | sha256 |
|---|---|
| `block_forecast_mock_nwp.csv` | `4495a7444fddb4494f951cd5246aebed41d623e85a68b4d8f736121e5e7a8d97` |
| `station_observations_mock.csv` | `10a6b30570c7a59f273cee5849705cac9e0320d3828210dbf7ec25f84213a2d6` |
| `panchayats_static.csv` | `6efd11e8707edbb19107f664e35f6dad13bdd59ec2af9de2c188e045c3651529` |
| `blocks.csv` | `9f4ec06bc6429afff86a41ea74ffcd6ab3ea55d48dcefc2932d960b41d2e6b74` |
| `stations.csv` | `b1da999a5c85709a8a7eaae6812cd39183666a996c2c351657a20aabdd2a56ee` |
| `satellite_weekly_mock.csv` | `a06da8bac5f4209c84a032335f72a8ec35c665b4dd61fcabcc086f5a6b663802` |
| `synthetic_oracle/panchayat_daily_SYNTHETIC_TRUTH.csv` | `14a3e1d799e89d1e83e9a6ec7838341eb3e31ac9c73138731c58ec6dedaecacb` |

The job recomputes the model data hash from the TRAIN and CALIB tables and stops if it differs from the bundle. It writes the file hashes and the code commit into `verification.json` (`frozen`).

## Windows

- TRAIN 2023-01-01..2024-04-30: models, B1 bias correction, B2 station offsets, climatology for the Brier skill score.
- CALIB 2024-05-01..2024-07-15: isotonic maps and conformal offsets. Used for the dry run of this job (in-sample for those two steps; the numbers are never quoted as results).
- TEST 2024-07-16..2024-12-31: evaluation. Issue dates whose five lead days all fall inside TEST (2024-07-16..2024-12-26), the same purge as TRAIN and CALIB.

## Opening TEST

- TEST is opened once per model version, by `python -m gramdrishti.verify.run_validation`.
- Before any TEST truth is read, the job writes the opening time, model version, data hash and code commit to `docs/test_window_ledger.json` (committed). The code refuses to read TEST without that entry.
- Re-running the same frozen version (same data hash) reproduces the same numbers. It is recorded as another run, not a new opening.
- The first opening time is also written to `docs/PROGRESS.md` (model and validation log).

## If anything changes after TEST results are seen

- Any change to the model, features, calibration, baselines or thresholds after seeing TEST gives a new model version number, logged in `docs/PROGRESS.md` and `docs/DECISIONS.md`.
- The ledger then shows TEST was opened before for another version. The job sets `test_reused: true` and writes a note in `verification.json` and the report: **TEST was reused, so it is not a clean holdout**.
- Nobody tunes against TEST. A variable that does not beat the baseline is reported as it is, with the likely reason.
- Changes to presentation only (report wording, API, frontend) do not change a number and need no new version.

## Checks (fixed before opening)

1. Temporal holdout: the production model forecasts every TEST issue date, scored against synthetic Panchayat truth.
2. Leave-one-block-out: mean models refitted on TRAIN without one block (6 folds, production parameters), forecasting the held-out block over TEST. Point forecasts only.
3. Station check: production forecasts at the 24 station Panchayats against QC-cleaned station values (in mock mode, synthetic truth plus noise). Rain gauges score rain only. B2 leaves the own station out.
4. Strata of the temporal holdout: lead day 1-5, season (monsoon, post-monsoon, winter), observed rain intensity (under 1, 1-10, 10-35, 35 mm and over), drainage class.

## Metrics (fixed before opening)

- Continuous (all five variables): MAE, RMSE, bias. Model value = reconciled mean. Skill = 1 - score_model / score_baseline against B0 (raw block), B1 (corrected block, what the model is reconciled to) and B2 (B1 plus lapse rate and station offsets).
- Rain amount: MAE on observed wet days (1 mm or more); quantile loss (mean pinball over p10, p50, p90; a baseline is scored as a point forecast, so this mainly rewards having an interval and is not used for verdicts).
- Rain events 1, 2.5, 10, 35 mm: POD, FAR, CSI, frequency bias with the model saying yes when P >= 0.5 and B0 / B1 when the block value reaches the threshold; Brier score and Brier skill against TRAIN monthly climatology; reliability points in 10 equal bins.
- Intervals: empirical coverage and mean width of [p10, p90] (nominal 80 %), overall, by lead day, by season, and rain on wet days.
- Integrity: largest |block mean of Panchayat means - B1| per variable.
- Confidence: 95 % interval of skill from a moving-block bootstrap of daily errors (7-day blocks, 1000 resamples, seed 42).
- Verdict per variable and stratum on MAE skill: **win** when the whole interval is above 0, **loss** when it is below 0, **tie** when it contains 0, **too_few_days** when there are fewer than 14 days.

## Decision replay (fixed before opening)

Lead day 1, every Panchayat, every TEST issue date; seasons monsoon (2024-07-16..09-30), post-monsoon (10-01..11-30), winter (12-01..12-31) and all of TEST.

| Decision | Model acts when | Block acts when (B0, and B1 as a second baseline) | Event |
|---|---|---|---|
| Spray | P(rain >= 2.5 mm) >= 0.3 (hold spraying) | block rain >= 2.5 mm | rain >= 2.5 mm |
| Heat alert | p90 Tmax >= 35 C | block Tmax >= 35 C | Tmax >= 35 C |
| Irrigation wait | P(rain >= 5 mm) >= 0.5, i.e. p50 >= 5 mm | block rain >= 5 mm | rain >= 5 mm |

35 C is the placeholder paddy heat alert (the lowest heat alert of a crop in season from July to December). It was chosen from TRAIN only: the generic 40 C was reached on 0.4 % of TRAIN July-December Panchayat-days, 35 C on 18.8 %. Outcomes: correct, wasted wait (acted, event did not come), washed off (did not act, event came). Counts and rates only.
