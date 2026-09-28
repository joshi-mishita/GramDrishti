# From mock data to real data

Status on 2026-09-28: **not started.** No real data has been obtained, and part of the real-mode code (training targets, verification) is deliberately not written yet because it needs real station data to design and test. This plan lists every file to replace, every code change, and how validation changes. Source names and their licences are in [data_card.md](data_card.md), all marked [verify].

The rule that makes this possible: every loader returns the same column names in mock and real mode (`backend/gramdrishti/data/loaders.py`), and the API contract does not change. The switch is the environment variable `DATA_MODE=real`; real files live in `data/real/` (git-ignored, paths in `backend/gramdrishti/data/config.py`, `FILES["real"]`).

## What already works in real mode

- Every loader reads `data/real/<file>` with the mock column names. `load_truth()` and `load_block_truth()` raise `RealModeError`: Panchayat truth does not exist for real data.
- Bias correction uses the block mean of QC-cleaned station observations as its target (`models/bias.py::block_reference`).
- `/observed` serves a station when the Panchayat has one and returns an empty series otherwise (no synthetic truth).
- Every response says `data_mode: "real"` and the mock ribbon disappears. Endpoints that would serve placeholder numbers answer 503 in real mode (DECISIONS D017).
- Real mode was tested only with copies of the mock files under `data/real/` (same columns and types), not with real data.

## What does not work yet

| Where | Today in real mode | Needed |
|---|---|---|
| `features/table.py::add_targets` | raises `NotImplementedError` | training targets from Panchayats that have a station (step 5) |
| `verify/run_validation.py::_truth` | raises `NotImplementedError` | leave-one-station-out (section "Validation") |
| `verify/baseline_report.py`, `verify/feedback_report.py` | refuse real mode | station truth instead of synthetic truth |
| `pipeline/run_daily.py` soil water start | null (no source) | a soil-moisture source, for example ERA5-Land or SMAP [verify] |
| `advisory/` rules that need soil water (irrigation, sowing, dry spell) | skipped and counted, not guessed | the soil source above |
| `data/crop_calendar_*.csv` | placeholder values | expert-reviewed calendar ([expert_review_pack.md](expert_review_pack.md)) |

## Steps, in order

Each step ends with the full test suite (`cd backend && pytest -q`) and a note in `docs/PROGRESS.md`.

1. **Stations first.** Put `data/real/stations.csv` (station id, type AWS or ARG, Panchayat id, block id, lat, lon, elevation) and `data/real/station_observations.csv` (date, station id, rain, Tmax, Tmin, RH, wind; blanks for missing) in place. Run QC (`data/qc.py`: range, consistency, spikes, stuck sensors, missing days) and read `/data-quality`. Decide with the team what share of missing days is acceptable per station.
2. **Block forecast.** Replace `block_forecast_mock_nwp.csv` with `data/real/block_forecast.csv`: one row per source, block, issue date and lead day 1 to 5, same five variables and units. The code combines sources by the `source` column, whatever their names. It has only been run with two sources; with one source the spread feature has no meaning, so check the combination and drop that feature (a new model version).
3. **Geography.** Replace `panchayats_static.csv`, `blocks.csv` and the two GeoJSON files with real boundaries and LGD ids, [longitude, latitude]. Recompute the static features per polygon (elevation, TPI, slope, land cover fractions, canal distance, soil, drainage). Check `tests/test_contract.py::test_example_geojson_is_lon_lat` still passes.
4. **Satellite and crops.** Replace `satellite_weekly.csv` (weekly NDVI and land surface temperature per Panchayat) and `panchayat_crops.csv` (crop and sowing date per Panchayat and season). Crops without calendar rows get no stage advice; list them for the expert.
5. **Training targets from stations** (new code in `features/table.py::add_targets`). Targets exist only at Panchayats with a station: all five variables at automatic weather stations, rain only at rain gauges. The model then learns from far fewer rows (24 of 90 Panchayats in the mock layout). Keep the model simple (fewer leaves, more regularisation) and say so in the model card.
6. **Soil water.** Add a loader for the chosen soil-moisture source and use it as the start state in `pipeline/run_daily.py`.
7. **Set `DATA_MODE=real`**, train (`pipeline/train.py`), which gives a new model version with `data_mode: real` in its config.
8. **Validation** as below, once, with a new protocol written before TEST is opened and a new entry in `docs/test_window_ledger.json`.
9. **Expert review** of thresholds, calendar and wording before any advice leaves the officer console.

## Validation in real mode

The mock checks use synthetic truth at every Panchayat. Real data has truth only at stations, so the checks change:

| Mock (today) | Real |
|---|---|
| Temporal holdout against synthetic truth at all 90 Panchayats | temporal holdout at station Panchayats only |
| Leave-one-block-out | kept where a block has stations; otherwise not possible |
| Station check (synthetic truth plus noise) | **leave-one-station-out**: for each station, refit without it and forecast its Panchayat |

Leave-one-station-out needs care that the held-out station leaks in nowhere:
- remove it from the training targets;
- remove it from the bias-correction reference (the block station mean) for that fold;
- remove it from the recent-rain feature (`stn_rain_prev3_mm`, `stn_rain_prev7_mm` are block station means);
- remove it from the B2 station offsets (B2 already leaves the own station out).

Everything else stays: the three windows split by time, the baselines B0, B1 and B2, skill with a moving-block bootstrap interval, win/tie/loss, strata, event scores, coverage, the decision replay, and the report generator. With few stations the intervals will be wide, and many strata will say "too few days". That is the honest answer.

## Fallback if stations are sparse: proxy training

From Backend Guide 14.4. If station coverage is too thin to train Panchayat-level models:

1. Take a fine gridded reference, IMERG for rain and ERA5-Land for temperature, humidity and wind [verify resolution and licence of both].
2. Aggregate it to Panchayat polygons as the training target, and to blocks for the bias-correction reference.
3. Train with the same code (`add_targets` reads the gridded Panchayat values instead of stations).
4. **Validate only on real stations** (leave-one-station-out as above), never on the gridded reference.
5. Label it everywhere as a proxy method: model card, verification screen ("trained on a gridded reference, checked at stations"), and the pitch.

Limits to state: a gridded reference at around 10 km may not resolve differences between neighbouring Panchayats [verify grid spacing]; the model can only learn the local patterns the reference itself contains.

## What changes for users

- The ribbon "Synthetic demo data. Not real weather." disappears only when responses say `data_mode: "real"`.
- The verification screen names stations as the truth and shows fewer forecasts.
- The demo issue dates are chosen again from the real issued forecasts (`contract/pick_demo_dates.py`), never from outcomes.
- Advice stays in draft until an officer approves it, as now.
