# Model card: GramDrishti Panchayat downscaling model

> **Synthetic demo data. Not real weather.** This model has been trained and tested only on the synthetic mock dataset in `data/`. Every number below shows whether the method works on data built to resemble the problem. None of it is evidence of skill on real weather.

| Item | Value |
|---|---|
| Model version | `s5-lgbm-9b632a7b1b` (the last 10 characters are the start of the training-data hash) |
| Built | 2026-09-26 (session S5), `python -m gramdrishti.pipeline.train` |
| Verified | 2026-09-27 (session S10), `python -m gramdrishti.verify.run_validation`, TEST window opened once |
| Data mode | mock (synthetic). No real-data model exists. |
| Code | `backend/gramdrishti/` (features, models, pipeline, verify) |
| Libraries in the verified run | Python 3.13.9, LightGBM 4.7.0, scikit-learn 1.9.1, pandas 3.0.6, NumPy 2.5.3 (from `frozen.library_versions` in `verification.json`) |
| Seed | 42 (LightGBM with `deterministic=True`, bootstrap) |
| Licence | MIT ([LICENSE](../LICENSE)) |
| Full numbers | [validation_report.md](validation_report.md), generated from the job's `verification.json` and `impact.json` |

## Intended use

- **What it does:** turns a block-level weather forecast (two NWP sources, lead days 1 to 5) into a forecast for every Panchayat in the block: rain, maximum and minimum temperature, relative humidity and wind, each as a middle value with a likely range (10th to 90th percentile), plus chances of rain of 1, 2.5, 10 and 35 mm or more.
- **Who uses the output:** an agriculture officer, through the officer console, and the advisory rules engine that drafts crop advice for the officer to review. Farmers see only advice an officer has approved, plus a simple five-day forecast.
- **Decisions it may inform:** day-level farm operations (spray or hold, irrigate or wait, drain fields, protect animals from heat) after officer review.

Out of scope:
- Any use on real weather before the model is retrained and verified on real data ([mock_to_real_plan.md](mock_to_real_plan.md)).
- Hour-level timing. The data is daily; spray ratings are for whole days.
- Warnings of severe weather to the public. The model is not an official forecast, and its heavy-rain chances are worse than the plain block forecast (see "Where it does not help").
- Unreviewed advice. Nothing the model or the rules produce reaches a farmer without an officer's approval.

## Data

Full details in [data_card.md](data_card.md). In short: one synthetic district, 6 blocks, 90 Panchayats, 24 stations (12 automatic weather stations, 12 rain gauges), 2023-01-01 to 2024-12-31. The mock data generator also writes a synthetic Panchayat "truth" (`data/synthetic_oracle/`, git-ignored). That truth does not exist for real data. In mock mode it is used only as a proxy training target and as the answer key for evaluation, **never as a model feature**.

## Features

55 features per Panchayat, issue date and lead day (`backend/artifacts/features.json`, built by `features/table.py`, shared by training and inference):

| Group | Features | Count |
|---|---|---|
| Position | latitude, longitude, offset from the block centre (2) | 4 |
| Static land and soil | elevation, TPI, slope, irrigated, cropland, urban, water and tree fractions, canal distance, clay, sand, silt, water holding capacity | 13 |
| Categorical codes | drainage class, soil texture | 2 |
| Contrast with the rest of the block | Panchayat minus block mean of elevation, TPI, irrigated, urban, water and tree fractions, sand | 7 |
| Calendar | day of year (sine, cosine), month, lead day | 4 |
| Forecast context | corrected block forecast B1 for the five variables and dew point, spread between the two sources, change from the previous lead day | 16 |
| Satellite | latest weekly NDVI and daytime land surface temperature ending by the issue date, their age, trend and contrast with the block | 7 |
| Recent rain | block mean station rain over the 3 and 7 days before the issue date | 2 |

Rules that keep the future out: only issued forecasts are used (never block truth), satellite values must end by the issue date, station rain stops the day before the issue date. Tests: `tests/test_features.py`, `tests/test_bias.py::test_bias_fit_uses_no_future_data_on_mock`, `tests/test_config.py`.

In the mock data every Panchayat has the soil texture "loam", so that feature carries no information here.

## Training windows

Split by time, never randomly (CLAUDE.md rule 5; `data/config.py`):

| Window | Dates | Used for |
|---|---|---|
| TRAIN | 2023-01-01 to 2024-04-30 | bias correction, LightGBM models, station offsets (B2), climatology for the Brier skill score |
| CALIB | 2024-05-01 to 2024-07-15 | isotonic calibration of rain chances, conformal interval offsets |
| TEST | 2024-07-16 to 2024-12-31 | evaluation only, opened once for this version on 2026-09-27 at 15:14:23 (`docs/test_window_ledger.json`) |

Only issue dates whose five lead days all fall inside a window are used in that window. The code refuses to read TEST unless the verification job has first written the opening to the ledger.

Rows: 216,450 training rows and 31,950 calibration rows (`backend/artifacts/config.json`).

## Methods

In the order the pipeline runs (`pipeline/train.py`, `pipeline/predict.py`, `pipeline/run_daily.py`):

1. **Bias correction of the block forecast** (`models/bias.py`), fitted on TRAIN per source and lead day. Temperature and humidity: additive bias per season group. Wind: a ratio. Rain: quantile mapping on wet days after matching wet-day frequency, separately for the monsoon (June to September) and the other months. The two sources are combined with weights of 1 / mean squared error per variable and lead day. The result is **B1**, the corrected block forecast.
2. **Downscaling with LightGBM** (`models/downscale.py`), one set of models per target: a mean model and quantile models at 0.1, 0.5 and 0.9. Temperature targets are the Panchayat's departure from B1; dew point likewise (relative humidity is derived later from temperature and dew point); wind is the log ratio to B1 wind; rain is the Panchayat amount in mm. 400 trees, learning rate 0.05, 31 leaves.
3. **Rain chances**: one LightGBM classifier per threshold (1, 2.5, 10, 35 mm), calibrated with isotonic regression on CALIB. Chances are then forced to fall as the threshold rises.
4. **Reconciliation** (`models/reconcile.py`): the Panchayat values are shifted (temperature, dew point) or scaled (rain, wind) so that the plain average of the Panchayat means in each block equals B1 exactly. Humidity uses a bounded shift that keeps values within 0 to 100 %. The same correction is applied to every quantile. Equal weights per Panchayat (area weights are future work). A test enforces a gap below 1e-6; on TEST the largest gap was 1.4e-14.
5. **Conformal intervals** (`models/conformal.py`): conformalised quantile regression, one additive offset per variable and lead-day group (days 1 to 2, days 3 to 5), fitted on CALIB, for a nominal 80 % interval [p10, p90]. Then constraints: p10 <= p50 <= p90, rain and wind at least 0, humidity within 0 to 100 %, minimum below maximum temperature.
6. **Farm variables** (`agro/derived.py`): reference evapotranspiration (Hargreaves), a five-day soil water bucket on the p10, p50 and p90 rain paths, waterlogging score, livestock heat index (THI), frost chance, a December to January fog proxy, dry-spell count, growing degree days. Their thresholds are placeholders (DECISIONS D051).
7. **Explanation** (`explain/`): SHAP values of the mean model, Panchayat minus block average, grouped into 25 feature groups; the top three become plain English sentences ("Lower ground than the rest of the block, so it is likely wetter than the block average"). Hindi and Punjabi sentences do not exist yet.

The daily run (`run_daily`) writes one snapshot per issue date; the API only reads those files. Advisories come from YAML rules (`advisory/rules.yaml`), never from a language model.

## Validation protocol

Written down before TEST was opened: [validation_protocol.md](validation_protocol.md). In short:

- Three checks: **temporal holdout** (the production model forecasts every TEST issue date), **leave-one-block-out** (mean models refitted six times on TRAIN without one block, forecasting that block over TEST; point forecasts only) and a **station check** (forecasts at the 24 station Panchayats against the station values; in mock mode these are synthetic truth plus noise).
- Baselines: **B0** the raw block forecast (average of the two sources) copied to every Panchayat; **B1** the corrected block forecast, which the model is reconciled to, so skill against B1 is what the Panchayat model itself adds; **B2** B1 plus a lapse-rate term and station offsets.
- Skill = 1 minus model error divided by baseline error. The 95 % interval comes from a moving-block bootstrap of daily errors (7-day blocks, 1,000 resamples, seed 42). **Win** when the whole interval is above 0, **loss** when below 0, **tie** when it contains 0.
- Truth in mock mode is the synthetic Panchayat truth, so this is **proxy validation**.

## Results

Copied from `verification.json` for `s5-lgbm-9b632a7b1b` (committed copy: `backend/gramdrishti/verify/records/s5-lgbm-9b632a7b1b/verification.json`). 164 TEST issue dates, 90 Panchayats, lead days 1 to 5: 73,800 forecasts per variable for the temporal holdout and leave-one-block-out; fewer for the station check (rain 18,681, others about 9,400). `python -m gramdrishti.verify.docs_check` checks this table against the file.

Mean absolute error (lower is better), skill in percent with the 95 % interval:

<!-- docs-check:mae:start -->
| Check | Variable | Unit | Model | B0 | B1 | Skill vs B0 (95 % interval) | Skill vs B1 (95 % interval) | Verdict vs B0 / B1 |
|---|---|---|---|---|---|---|---|---|
| Temporal holdout | rain | mm | 1.070 | 1.240 | 1.031 | +13.7 (+4.0 to +27.9) | -3.8 (-8.1 to +0.8) | win / tie |
| Temporal holdout | tmax | C | 1.076 | 1.154 | 1.134 | +6.8 (+5.1 to +8.4) | +5.1 (+3.8 to +6.6) | win / win |
| Temporal holdout | tmin | C | 1.099 | 1.286 | 1.142 | +14.6 (+13.2 to +16.2) | +3.8 (+2.1 to +5.5) | win / win |
| Temporal holdout | rh | % | 5.668 | 5.987 | 5.914 | +5.3 (+4.8 to +5.8) | +4.2 (+3.7 to +4.6) | win / win |
| Temporal holdout | wind | km/h | 1.074 | 1.684 | 1.095 | +36.2 (+34.9 to +37.4) | +1.9 (+1.8 to +2.0) | win / win |
| Leave-one-block-out | rain | mm | 1.067 | 1.240 | 1.031 | +13.9 (+4.4 to +27.7) | -3.5 (-6.8 to +0.1) | win / tie |
| Leave-one-block-out | tmax | C | 1.084 | 1.154 | 1.134 | +6.1 (+4.6 to +7.6) | +4.5 (+3.3 to +5.7) | win / win |
| Leave-one-block-out | tmin | C | 1.101 | 1.286 | 1.142 | +14.4 (+13.0 to +15.9) | +3.6 (+2.0 to +5.2) | win / win |
| Leave-one-block-out | rh | % | 5.690 | 5.987 | 5.914 | +5.0 (+4.5 to +5.4) | +3.8 (+3.4 to +4.2) | win / win |
| Leave-one-block-out | wind | km/h | 1.079 | 1.684 | 1.095 | +35.9 (+34.6 to +37.1) | +1.4 (+1.3 to +1.5) | win / win |
| Station check | rain | mm | 1.005 | 1.162 | 0.957 | +13.5 (+1.3 to +33.3) | -5.0 (-11.5 to +4.4) | win / tie |
| Station check | tmax | C | 1.089 | 1.137 | 1.111 | +4.2 (+3.1 to +5.2) | +2.0 (+1.4 to +2.6) | win / win |
| Station check | tmin | C | 1.112 | 1.297 | 1.139 | +14.3 (+13.1 to +15.7) | +2.4 (+1.5 to +3.5) | win / win |
| Station check | rh | % | 5.953 | 6.095 | 6.038 | +2.3 (+1.6 to +3.0) | +1.4 (+1.0 to +1.8) | win / win |
| Station check | wind | km/h | 1.185 | 1.781 | 1.203 | +33.5 (+31.5 to +35.1) | +1.5 (+0.9 to +1.9) | win / win |
<!-- docs-check:mae:end -->

How to read it:
- Against the raw block forecast B0, the model wins on every variable in all three checks.
- Against the corrected block forecast B1, the model wins on temperature, humidity and wind, by small margins (1.4 % to 5.1 % in the temporal holdout). **For rain it ties**: it is not better than B1.
- Most of the gain over B0 comes from the block bias correction, not from the Panchayat detail: all of it for rain, 77 % for minimum temperature and 97 % for wind (validation report, "Reading guide").

Interval coverage (nominal 80 %, temporal holdout): maximum temperature 0.776, minimum temperature 0.814, humidity 0.853, wind 0.899, rain 0.934 on all days but **0.509 on days with 1 mm or more observed** (mean width 28.7 mm).

Rain events (model says yes at a chance of 0.5 or more):

<!-- docs-check:events:start -->
| Event | CSI model | CSI B0 | CSI B1 | Brier skill vs monthly climatology |
|---|---|---|---|---|
| 1 mm or more | 0.432 | 0.276 | 0.305 | 0.385 |
| 2.5 mm or more | 0.487 | 0.363 | 0.400 | 0.458 |
| 10 mm or more | 0.504 | 0.519 | 0.522 | 0.450 |
| 35 mm or more | 0.141 | 0.349 | 0.371 | -0.016 |
<!-- docs-check:events:end -->

Decision replay (lead day 1, every Panchayat, whole TEST period, 14,760 decisions each; placeholder thresholds, no costs applied):

<!-- docs-check:impact:start -->
| Decision | Model: correct / wasted wait / washed off | Block forecast B0 | Corrected block B1 |
|---|---|---|---|
| Spray tomorrow? | 14,364 / 217 / 179 | 14,138 / 554 / 68 | 14,224 / 399 / 137 |
| Heat alert | 13,110 / 1,628 / 22 | 13,958 / 527 / 275 | 14,029 / 392 / 339 |
| Irrigate or wait | 14,442 / 126 / 192 | 14,527 / 153 / 80 | 14,535 / 118 / 107 |
<!-- docs-check:impact:end -->

For the heat alert and irrigation, "wasted wait" means a false alarm and "washed off" a miss.

## Where it does not help

Taken from the job's notes; the full list is in the validation report.

- **Rain amounts.** Not better than B1 overall, on any lead day or in any season (all ties). Worse than B1 on light (1 to 10 mm, -6.4 %) and moderate (10 to 35 mm, -14.0 %) observed rain, in poorly drained Panchayats (-33.3 %), and on wet-day MAE (-7.2 %). Worse than even B0 on light rain (-47.4 %).
- **Heavy rain.** The 35 mm chance is worse than monthly climatology (Brier skill -0.016) and its CSI (0.141) is far below the block forecast's (0.349 B0, 0.371 B1). Heavy-rain risk and waterlogging advice lean on it.
- **10 mm events.** CSI 0.504, slightly below B0 (0.519) and B1 (0.522).
- **Overconfident high chances.** Forecasts of 90 to 100 % for 1 mm verify 76 % of the time.
- **Intervals.** Maximum temperature under-covers (0.776, lead day 5: 0.708); humidity and wind over-cover (0.853, 0.899); rain on wet days covers only half the time.
- **Heat alert decision.** The p90 rule is correct less often than the block rule (88.8 % against 94.6 %): 1,628 false alarms against 527, in exchange for 22 misses against 275.
- **Irrigation decision.** Correct less often (97.8 % against 98.4 %) with more misses (192 against 80).
- **Spray decision.** Correct more often (97.3 % against 95.8 %) with fewer wasted waits (217 against 554), but more washed-off sprays (179 against 68). Which is better depends on costs nobody has supplied yet.
- **Heavy observed rain days** (35 mm or more): too few days in TEST for an interval on any variable.

## Known failure modes

- **Rain middle value is flat inside a block on some days.** On 2024-09-09 the rain p50 for all 16 Panchayats of block MB03 is 103.84 mm on lead day 1, while the model mean ranges from 65 to 124 mm. The rain map then looks the same in Block and Panchayat view; only the likely range differs. Quantile and mean models are separate and reconciliation adjusts each (PROGRESS known issues, S14).
- **Rain chances can disagree with the rain quantiles.** On some days p10 is 0 mm while the chance of 1 mm is 0.91, and the chances for 1, 2.5 and 10 mm come out equal after the non-increasing clamp.
- **Heavy-rain chances are identical across a block on some days** (MB03 on 2024-09-10: 0.64 everywhere), so heavy-rain risk is flat within those blocks.
- **Soil water starts from synthetic truth** on the day before the issue date (mock only) and simulates no irrigation, so irrigated Panchayats dry out too fast over five days and winter soils look very dry. In real mode soil water is empty until a soil-moisture source is added.
- **Explanations can read oddly.** "Fewer irrigated fields than the rest of the block, so it is likely cooler" appears 154 times; satellite reasons for rain are probably spurious; about a quarter of reasons are block-wide interactions that tell a farmer little.
- **Calibration window is short.** CALIB covers May to mid-July only, so interval offsets were never fitted on winter data. Isotonic calibration made the Brier score worse than the raw classifier in 5 of 8 CALIB half-splits during development.
- **Retraining on another machine changes the version.** A Linux retrain gets `s5-lgbm-2576015e9e` (last-bit floating point differences), which has no verification record; the screens then say "not computed" (DECISIONS D122).

## Mock and real data status

| Part | Mock mode (today) | Real mode |
|---|---|---|
| Loaders | all files | same columns from `data/real/`; the synthetic truth raises `RealModeError` |
| Bias correction target | synthetic block truth | block mean of QC-cleaned station observations (written, not run on real data) |
| Training targets | synthetic Panchayat truth (proxy) | **not built**: `add_targets` raises `NotImplementedError` (needs station Panchayats only) |
| Verification | synthetic truth, three checks | **not built**: the job raises; needs leave-one-station-out |
| Soil water start | synthetic truth, day before issue | empty (null) until a soil-moisture source is added |
| Advisories | placeholder thresholds | same rules; thresholds need expert review either way |

The UI shows "Synthetic demo data. Not real weather." whenever `data_mode` is `mock`, which is true for every response today.

## Reproduce

```bash
python data/generate_mock_data.py                       # synthetic truth (git-ignored)
cd backend && python -m gramdrishti.pipeline.train      # about 2 minutes, writes backend/artifacts/
python -m gramdrishti.pipeline.run_daily --all-demo-dates
python -m gramdrishti.verify.docs_check                 # tables above against the verification record
```

Rerunning `run_validation` for the same version reproduces every number byte for byte (DECISIONS D070); a new version must follow the validation protocol and will be marked "TEST reused".
