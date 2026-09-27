# GramDrishti progress log

Claude Code updates this file at the end of every session. People update the "Merged" column after reviewing the pull request.

## Session status

| ID | Session | Owner | Status | PR | Merged |
|---|---|---|---|---|---|
| S0 | Repo foundation | both | merged | session-00-foundation (#1) | yes |
| S1 | Backend data layer and baselines | backend | merged | session-01-backend-data-baselines (#2) | yes |
| S2 | Contract and API skeleton | backend | merged | session-02-contract-api (#3, #5) | yes |
| S3 | Frontend foundation | frontend | merged | session-03-frontend-foundation (#4) | yes |
| S4 | Frontend map explorer | frontend | merged | session-04-map-explorer (#6) | yes |
| S5 | Backend model core | backend | merged | session-05-model-core (#7) | yes |
| S6 | Agro-variables, snapshots, forecast APIs | backend | merged | session-06-snapshots-forecast-api (#9) | yes |
| S7 | Frontend detail panel and first integration | frontend | PR open | session-07-detail-panel | |
| S8 | Advisory engine and review APIs | backend | merged | session-08-advisory-engine (#11) | yes |
| S9 | Frontend priority, risk and review | frontend | not started | | |
| S10 | Verification and impact | backend | not started | | |
| S11 | Frontend verification and impact | frontend | not started | | |
| S12 | Farmer-side backend and snapshot export | backend | PR open | session-12-farmer-backend | |
| S7 | Frontend detail panel and first integration | frontend | merged | session-07-detail-panel (#10) | yes |
| S8 | Advisory engine and review APIs | backend | merged | session-08-advisory-engine (#11) | yes |
| S9 | Frontend priority, risk and review | frontend | merged | session-09-priority-review (#13) | yes |
| S10 | Verification and impact | backend | merged | session-10-verification-impact (#14) | yes |
| S11 | Frontend verification and impact | frontend | merged | session-11-verification-impact-ui (#15) | yes |
| S12 | Farmer-side backend and snapshot export | backend | pushed, no PR; merged into S13 | session-12-farmer-backend | |
| S13 | Frontend farmer app, languages, bulletin, offline | frontend | pushed, no PR (no `gh`); contains S12 | session-13-farmer-app | |
| S14 | Integration, Docker and end-to-end tests | both | not started | | |
| S15 | Design and accessibility polish | frontend | not started | | |
| S16 | Documentation and submission assets | both | not started | | |
| S17 | Final QA and demo freeze | both | not started | | |

## Current state
S0: repo skeleton, README, contribution rules, PR template, CI.

S1: `backend/` package `gramdrishti` with `pyproject.toml` (ruff and pytest config). Built:
- `data/config.py`: DATA_MODE, paths, VARS, COLS, LEADS, windows, season groups, and `select_window`, which refuses TEST.
- `data/loaders.py`: one loader per file, the same columns in mock and real mode. `load_truth()` and `load_block_truth()` raise `RealModeError` in real mode.
- `data/qc.py`: range, consistency, spike, stuck-sensor and missing flags, plus `clean_values` and `qc_summary` for the later `/data-quality` endpoint.
- `models/bias.py` and `models/baselines.py`: B0, B1 and B2.
- `verify/metrics.py` and `verify/baseline_report.py`.
- 64 tests.

CI now runs the backend job and regenerates the oracle first. The generator's default output is `data/`. It reproduces the committed files with seed 42.

S2: contract v0.1.1 **frozen**, stub API running. Built:
- `api/schemas.py` (all Appendix A models plus the shapes Appendix A left open), `api/errors.py` (contract error shape for 4xx/5xx and validation), `api/service.py`, `api/routes/*`, `api/main.py` (`/api/v1`, CORS for `http://localhost:5173`, `X-Data-Mode` header).
- `provisional/`: B1-based forecast with a two-source spread band (D014), placeholder risk (D019), templates in en/hi/pa, and seeded placeholders for verification, impact and explain.
- `contract/pick_demo_dates.py` writes `demo_dates.json` (8 dates, printed reasons). `contract/make_examples.py` writes 60 files to `contract/examples/` plus `index.json`. `export_openapi.py` writes `contract/openapi.json`.
- 227 tests (163 new).

Demo issue dates (from the issued block forecast only):
| Date | Split | Label | Why |
|---|---|---|---|
| 2024-01-12 | train | Training-period replay: January cold night | Coldest January 2024 night forecast, 4.8 C district mean |
| 2024-03-31 | train | Training-period replay: March wheat heat | Hottest March 2024 forecast, 37.9 C, late wheat grain fill |
| 2024-07-31 | test | Patchy rain, blocks disagree | Largest spread of tomorrow's rain between blocks, SD 15.8 mm |
| 2024-08-15 | test | Monsoon break, dry days ahead | Driest 5-day outlook in the TEST monsoon, at most 0.9 mm in any block |
| 2024-09-09 | test | Heavy monsoon rain | Wettest block forecast for tomorrow, 105.8 mm (district mean 20.7 mm) |
| 2024-10-13 | test | Hot post-monsoon day | Highest October Tmax forecast, 35.1 C district mean |
| 2024-11-16 | test | Ordinary day | Closest to a typical November day on all five variables |
| 2024-12-24 | test | Cold, calm December morning (fog-prone) | Tmin 2.1 C, RH 65 %, wind 2.6 km/h; a proxy, no fog variable exists |

S3: `frontend/` app shell on the frozen contract. Built:
- Vite 8 + React 19 + TypeScript 5.9 strict, ESLint (typescript-eslint strict, react-hooks) + Prettier, Vitest, Playwright `npm run shots` (1366x768 and 360x740, full page, into `docs/screens/`).
- `src/styles/tokens.css` (Guide 2.3 and section 4 exactly, plus derived tokens in `docs/design.md`), `base.css` (Hindi/Punjabi line height 1.65), `print.css` stub. Self-hosted fonts via Fontsource (Source Sans 3, Noto Sans Devanagari, Noto Sans Gurmukhi; 400/500/700; `font-display: swap`), licences in `docs/licences/fonts/`.
- Shell: brand top bar (product, district from `/meta`, issue date select with each date's reason, Officer/Farmer switch, language switch in its own script), 28 px mock ribbon when `data_mode` is mock, left icon+label navigation (bottom bar below 768 px), farmer layout with three-item bottom navigation. All Guide 5 routes (`/`, `/map`, `/priority`, `/review`, `/verification`, `/impact`, `/farmer` with Today/Forecast/My farm, `/bulletin/:pid`, 404), lazy-loaded.
- Placeholder screens load the data they will use and show real counts or text with loading, empty and error states: map controls (day buttons with dates, variable, view mode, Panchayat picker) plus loaded boundaries and value range; detail panel empty state; priority counts by level; review queue count; verification method and notes (no numbers); impact rules (no numbers); farmer approved advice and profile.
- State: zustand store (issueDate, leadDay, variable, viewMode, selectedPid, lang, role); `date`, `var`, `pid` mirrored into the URL; language saved in localStorage and set on `<html lang>`.
- API: `client.ts` with per-endpoint switch (`VITE_REAL_ENDPOINTS`, `VITE_SNAPSHOT`), mock requests resolved through `index.json` (D028), `ApiError`, TanStack Query hooks, `QueryBoundary`. Types only from generated `schema.d.ts`.
- i18n: en/hi/pa UI strings (hi and pa are drafts needing native review, `src/i18n/README.md`), parity test.
- 49 frontend tests (7 files). CI frontend job now uses Node 22 and checks generated types.

S4: map explorer on the frozen contract (no contract change). Built:
- `lib/ramps.ts`: one config for ramps and breaks (Blues rain 0/1/5/15/35/65, YlOrRd Tmax and reversed YlGnBu Tmin in 3 C steps, GnBu humidity, Greys wind, RdBu difference, severity tokens for risk) plus `fillColorExpression` for MapLibre. `Legend` is built from the same Ramp, with units and a "No value" key.
- `features/map/MapView.tsx`: MapLibre GL, no basemap, GeoJSON sources with `promoteId: "panchayat_id"`, fill by feature-state, white Panchayat outlines, dark block outlines, hover and selection outlines. Sources and layers are added once; new values call `setFeatureState` and a new ramp calls `setPaintProperty`. Fits the district, and re-fits on resize until the user moves the map. Falls back to a message if WebGL is missing.
- Controls: day buttons with dates, variable, view mode (Block, Panchayat, Difference from block), risk layer selector disabled with a reason, Panchayat picker.
- Hover tooltip (name, forecast, range, block or difference); click selects, updates `pid` in the URL and opens the panel. `day` and `view` are in the URL too.
- Right panel v1: name and block, the chosen day's value with a plain-language range, block value and difference, an empty fan-chart slot, all variables for the day.
- "Show as table": sortable `DataTable` (sticky header, 36 px rows, keyboard sort buttons with `aria-sort`), name buttons select a Panchayat.
- Toggling view mode is instant: view mode is not in the query key; a test checks no second request.
- 86 frontend tests (11 files, 35 new). Screenshots: `map`, `map-block`, `map-delta`, `map-tmax-delta`, `map-selected`, `map-selected-wet` at desktop and phone.

Screenshot review (2024-09-09, rain, lead day 1):
- Block and Panchayat views look almost identical. Correct for the provisional data: p50 differs from the block forecast by a flat -4.5 mm in MB03 (101.3 vs 105.8 mm) and +0.9 mm in MB05, which is invisible on the rain scale. The Difference view shows it clearly (MB03 red, MB05 pale blue, others white). The map says so in a note (D043). The demo moment needs S5 data to be convincing.
- Tmax difference is one-sided: every Panchayat is 0 to 0.4 C cooler than its block (bias correction), so the whole map is shades of blue.
- Panchayat outlines are hard to see on the palest rain colour; block outlines are clear.
- At phone width the controls still come before the map (now wrapped into rows).
S5: Panchayat model core (not yet served by the API; S6 wires it in). Built:
- `features/`: `make_table(kind)` for train and infer: static + block-relative contrasts, position, calendar, forecast context (B1, source spread, lead-day change, block dew point), satellite (latest week ended by the issue date), station rain over the 3 and 7 days before the issue date. TRAIN/CALIB tables keep only issue dates whose 5 leads fit the window; TEST raises.
- `models/downscale.py` (LightGBM mean + p10/p50/p90, rain event classifiers + isotonic), `reconcile.py` (additive, multiplicative, bounded for RH), `conformal.py` (CQR per variable and lead group, constraints), `humidity.py`, `artifacts.py`.
- `pipeline/predict.py`, `pipeline/train.py` (`--lobo`, dev report, artifacts with data hash).
- 22 new tests (249 total).

S5 dev report (full model, `python -m gramdrishti.pipeline.train --lobo`; mock data, synthetic proxy validation):
- LOBO on TRAIN, MAE vs B1: tmax 1.156 -> 1.096 C (+5.2 %), tmin 1.124 -> 1.074 C (+4.4 %), rh 5.826 -> 5.642 % (+3.2 %), wind 1.452 -> 1.431 km/h (+1.4 %), **rain 0.711 -> 0.716 mm (-0.7 %, does NOT beat B1)**.
- Out-of-time on CALIB, MAE vs B1: tmax +12.4 %, tmin +1.2 %, rh +3.1 %, wind +2.1 %, **rain -15.8 % (RMSE 4.743 -> 5.940 mm), does NOT beat B1**.
- 80 % interval, offsets fitted on one CALIB half, scored on the other: 0.734..0.971 (mean 0.823) across variables and lead groups. Rain on wet days only: 0.42..0.72 (undercovered). RH days 3-5 when fitted on the monsoon half and scored on May: 0.734.
- Rain events: isotonic calibration was worse than the raw classifier in 5 of 8 half-splits (the halves differ: base rate 0.19 vs 0.013 at 1 mm).
- Block consistency max error 1.4e-14; 0 constraint violations; Tmax anomaly +0.456 / -0.086 / -0.384 C at irrigated_frac p10 / p50 / p90.
- Hypothesis for rain (TRAIN truth): only 26 % of within-block rain variance is a persistent Panchayat x month offset, against 89-92 % for Tmax, Tmin and dew point and 70 % for wind. Rain placement inside a block is mostly day-to-day noise, so moving rain between Panchayats adds error.

S5 (written up in S6 from the S5 handoff and `backend/artifacts/dev_report.txt`): `features/` (`make_table`, shared by train and infer), `models/{downscale,reconcile,conformal,humidity,artifacts}.py`, `pipeline/{predict,train}.py`. LightGBM mean + p10/p50/p90 per target (tmax, tmin, dew point, wind, rain), rain event classifiers with isotonic calibration, reconciliation to the corrected block forecast B1, conformal offsets per variable and lead group. Final bundle `s5-lgbm-9b632a7b1b` (400 trees, TRAIN fit, CALIB calibration, TEST not opened). Results (synthetic proxy validation, mock data): leave-one-block-out on TRAIN, MAE skill vs B1: tmax +5.2 %, tmin +4.4 %, RH +3.2 %, wind +1.4 %, **rain -0.7 % (does not beat B1)**. Out-of-time on CALIB: tmax +12.4 %, tmin +1.2 %, RH +3.1 %, wind +2.1 %, **rain -15.8 % (does not beat B1)**. 80 % interval coverage on CALIB halves after calibration 0.73 to 0.98 (mean 0.82); on wet days rain coverage is 0.42 to 0.72. Isotonic made Brier worse than the raw classifier in 5 of 8 half-splits. Block consistency ~1e-14, constraint violations 0.

S6: forecast endpoints serve the S5 model through precomputed snapshots. Contract v0.1.2 (additive). Built:
- `agro/derived.py`: vectorised ET0 (Hargreaves, Ra from latitude and day of year), GDD per crop, soil bucket run five days on the p50, p10 and p90 rain paths from the latest known state, depletion, waterlogging score and level, THI (Tmax with afternoon RH from dew point), frost probability and level, a December-January fog proxy, dry-spell counter. Placeholder numbers in D051.
- `explain/`: SHAP TreeExplainer on the mean model, Panchayat minus block-average contrast, 25 feature groups, top 3, sign-aware English sentence dictionary (hi and pa null). D052.
- `pipeline/run_daily.py`: `--issue-date` or `--all-demo-dates` (8 demo dates plus the day before each = 16 snapshots, 4.5 MB, 34 s). Checks block consistency before writing. Deterministic: a rebuild is byte-identical (manifests carry sha256 per file).
- API: `/forecast/map`, `/forecast/panchayat/{id}`, `/explain/{id}`, `/forecast/changes/{id}` read snapshots (`provenance: computed`, `model_version`); `/observed` unchanged (files, D053); a missing snapshot is 503 `not_computed`. Risk, priority and advisories run on the model table with the S2 placeholder thresholds (D054).
- Contract v0.1.2 (`contract/CHANGELOG.md`): optional `mean`, `block_corrected`, map `corrected`, extra `derived` fields, `model_version`, `thresholds_status`; explain and change semantics written down. Examples regenerated from the real snapshots (62 files); frontend types regenerated and two map-test fixture values updated.
- Tests: 279 backend (`test_agro.py` and `test_snapshots.py` new), 86 frontend.

Measured (local, 2026-09-26): median HTTP latency with curl, 50 warm requests each: `/forecast/map` 6.2 ms, `/forecast/panchayat` 4.1 ms, `/observed` 4.0 ms, `/explain` 3.2 ms, `/forecast/changes` 4.2 ms. First request for a new date 19 ms. In-process test: median 3.9 ms.

Explain texts that read awkwardly (demo dates, served reasons only):
- "The block forecast for this day, combined with local conditions, ..." and "The time of year, combined with local conditions, ...": block-wide groups are 23 % of all reasons and **69 % of rank-1 rain reasons**, 34 % of RH reasons. They mean "an interaction the model found" and tell a farmer nothing.
- Counter-intuitive directions from the model: "Fewer irrigated fields than the rest of the block, so it is likely cooler" (154 Tmax reasons), "More built-up land ..., so it is likely cooler" (38).
- Satellite groups for rain and RH, for example "Crops greening more slowly than the rest of the block (satellite), so it is likely wetter": probably spurious.
- RH reasons come from the dew point model ("more humid" means more moisture at the same temperature).
- "Its loam soil ..." / "Its moderate soil drainage ..." do not say why the class matters.
- All sentences share one template ("..., so it is likely X than the block average.") and are English only.

S8: advisory engine, risk and priority from YAML rules, review workflow in SQLite. Contract v0.2.0 (additive). Built:
- `advisory/signals.py`: signals per Panchayat, crop and issue date (Guide 9.2) from the snapshot, static features and the placeholder calendar, with a registry (`SIGNALS`) that rules are checked against. Stage from das on lead day 1; crops sown within 10 days get `pre_sowing`. One livestock context per Panchayat.
- `advisory/rules.yaml`: 15 rules covering all 11 categories (sowing x3, irrigate, hold irrigation, spray hold, fertilizer, heat stress, frost, waterlogging, dry spell, harvest, pest/disease, livestock x2), simpleeval `when`, named thresholds with unit and meaning, `thresholds_status: placeholder`, empty `source`, priority, confidence keys, evidence, `supersedes`. Also the spray-planner thresholds, risk cuts, confidence settings. `rules.py` is the schema (pydantic, exported to `rules.schema.json`) plus meaning checks.
- `advisory/templates.yaml`: English action, reason and fallback for each rule, Hindi and Punjabi drafts (`translation_status: needs_native_review`), crop and stage names, priority headlines, units. `docs/translation_notes.md` lists the terms we were unsure about.
- `advisory/spray.py`: whole-day Good / Caution / Avoid from P(rain >= 2.5 mm) that day and the next and p90 wind; no hour windows.
- `advisory/engine.py`: evaluate, fill templates, evidence rows, confidence (Guide 9.5), priority (base +/- stage sensitivity, -1 for low confidence), de-duplication (`supersedes`, then one per Panchayat, crop and category). Deterministic; about 0.5 s per issue date.
- `advisory/risk.py`: risk scores per Panchayat and lead day (crop-aware heat and frost). `store/db.py` + `store/init_db.py`: Guide 10 tables plus `schema_version`, `generation_runs`; migrations as SQL scripts.
- API: `/risk`, `/priority` (ranked by level, score, id; headlines in en/hi/pa), `/advisories` (filters), `/advisories/{id}`, `POST /advisories/{id}/review` (approve / edit / reject, audit row with before and after), `/farmers/{id}/advice` (approved and edited only), `/feedback` (stored). `/forecast/changes` sets `advice_changed`; `/forecast/panchayat` days carry `spray_rating`. Provenance `computed`, thresholds `placeholder`.
- `run_daily` writes drafts for the 8 demo dates after the snapshots. `advisory/expert_table.py` writes `docs/thresholds_for_expert_review.md` (the file for the KVK or SAU expert); `advisory/show.py` prints stored advisories.
- Tests: 359 backend (80 new: `test_advisory.py`, `test_store.py`, S8 API tests), 86 frontend.

Draft advisories per demo date (placeholder thresholds, mock data):
| Date | Drafts | By category |
|---|---|---|
| 2024-01-12 | 125 | frost 26, irrigation 83, spray 16 |
| 2024-03-31 | 109 | heat_stress 12, irrigation 7, livestock 90 |
| 2024-07-31 | 285 | fertilizer 37, heat_stress 11, irrigation 67, livestock 90, spray 68, waterlogging 12 |
| 2024-08-15 | 197 | dry_spell 52, irrigation 31, livestock 90, pest_disease 8, spray 16 |
| 2024-09-09 (heavy rain) | 198 | dry_spell 20, harvest 3, irrigation 53, livestock 90, spray 29, waterlogging 3 |
| 2024-10-13 | 96 | irrigation 6, livestock 90 |
| 2024-11-16 | 84 | irrigation 50, sowing 34 |
| 2024-12-24 (cold) | 157 | frost 73, irrigation 84 |

Same block, same crop, different advice (2024-09-09, bajra, block MB03): MP0307 is low-lying (tpi_z -2.6) and gets "clear the field drains" (48 % chance of 35 mm or more by 12 September) and "do not spray on 10 September" (82 % chance of rain). MP0311's bajra is due for harvest in 10 days, so it gets "harvest before the rain expected on 10 September" (80 % chance of 10 mm or more), which supersedes its spray hold, and "hold irrigation" (84 % of root-zone water used, 80 % chance of useful rain).

Measured (local, 2026-09-26, uvicorn, 30 warm requests each): `/priority` 70 ms, `/risk` 2.5 ms, `/advisories?issue_date` 10.5 ms, `/advisories/{id}` 1.5 ms. The first risk or priority request per issue date takes 0.45 to 0.7 s (engine and risk scores, then cached).

S12: farmer side, feedback loop demo, audio and the offline snapshot. Contract v0.4.0 (additive; v0.3.0 is S10's). Built:
- `store/seed_demo.py`: five demo profiles (D093), migration 2 (`farmers.livestock`, D094). The API seeds an empty table.
- `/farmers/{id}` from SQLite; `/farmers/{id}/advice`: approved or edited only, farmer's Panchayat and crops (livestock only for F001 and F004), severe first, plus optional `spray_days` (D095).
- `POST /feedback`: date inside the data period and not in the future, answer and intensity must agree (400), identical report within 10 minutes answers `stored: false` with the first id (D096). Thank-you text no longer claims the forecast improves (D098).
- `advisory/audio.py` + `/audio/{id}?lang=`: gTTS, cached by text hash under `artifacts/audio/`, 404 `audio_not_available` on any failure; `Advisory.audio` links for approved and edited advisories. **Punjabi works with gTTS 2.5.4** (D097).
- `verify/feedback_report.py` writes `docs/feedback_loop_demo.md`: 2023-08 had 40 reports, rain yes/no agrees 92 % (37 of 40) with station or synthetic truth, and Panchayats with any ground check go from 24 (stations) to 48 of 90 with reports. Demo of the loop, no retraining, no forecast scoring, TEST months refused; no observation nudge (D099).
- `gramdrishti/export_snapshot.py`: 21,965 validated GET responses for the 8 demo dates, all 90 Panchayats and the 5 farmers, 39 MB, 64 s, into git-ignored `contract/snapshot/`; `npm run sync:mock` copies it to `frontend/public/snapshot/` (D100). Checked in the browser with the API stopped: farmer screen shows F001's three approved advisories, the map shows 27 Dec 2024 lead 3 Tmin.
- Tests: 375 backend (16 new in `test_farmers.py`, 2 in `test_store.py`), 120 frontend.

Same block MB03, 2024-09-09, after approving every draft in MP0307 and MP0311 (6 advisories): F001 (MP0307, hi, keeps livestock) sees spray hold, clear drains, livestock heat; F002 (MP0311, pa, no livestock) sees harvest before the rain, hold irrigation, and not the approved livestock item. F005 (MP0103, wheat only) sees nothing on that date.
S10: verification and impact on the TEST window, once, for `s5-lgbm-9b632a7b1b` (protocol in `docs/validation_protocol.md`, report in `docs/validation_report.md`). Contract v0.3.0 (additive). Built:
- `verify/metrics.py`: contingency with frequency bias, Brier and Brier skill, reliability, interval coverage, pinball and quantile loss, daily sums, moving-block bootstrap CI (7-day blocks), win/tie/loss.
- `verify/run_validation.py`: temporal holdout, leave-one-block-out (6 refits on TRAIN) and station check against B0, B1 and B2; strata by lead day, season, observed rain intensity and drainage class; events; reliability; coverage; block-mean error; notes listing every place the model does not beat B0 or B1. `--window CALIB` dry run. About 90 s.
- `verify/ledger.py` + `docs/test_window_ledger.json`: TEST opening per model version. `verify/impact.py`: spray, heat alert and irrigation-wait replay at lead day 1. `verify/report.py`: the Markdown report from the job's files.
- API: `/verification/*` and `/impact` read `artifacts/verification.json` and `impact.json` (503 when missing); the S2 placeholders are removed. `/data-quality` provenance `computed`.
- Tests: 384 backend (metrics on hand-computed cases, bootstrap reproducibility, ledger, TEST guard, impact by hand, notes, the job on CALIB with the small bundle, determinism, API returns exactly the file's numbers, report), 163 frontend.

S10 results (TEST 2024-07-17..2024-12-31, 164 issue dates x 90 Panchayats x 5 leads = 73,800 rows; synthetic proxy validation, mock data). MAE skill with 95 % interval, temporal holdout:
| Var | vs B0 (raw block) | vs B1 (corrected block) | Verdict B0 / B1 |
|---|---|---|---|
| rain | +13.7 % (+4.0 to +27.9) | -3.8 % (-8.1 to +0.8) | win / **tie** |
| tmax | +6.8 % (+5.1 to +8.4) | +5.1 % (+3.8 to +6.6) | win / win |
| tmin | +14.6 % (+13.2 to +16.2) | +3.8 % (+2.1 to +5.5) | win / win |
| rh | +5.3 % (+4.8 to +5.8) | +4.2 % (+3.7 to +4.6) | win / win |
| wind | +36.2 % (+34.9 to +37.4) | +1.9 % (+1.8 to +2.0) | win / win |

Leave-one-block-out and the station check give the same verdicts (rain vs B1: -3.5 % and -5.0 %, ties). Where the model does not help:
- Rain is not better than B1 overall, on any lead day or season (ties); worse than B1 on light (-6.4 %) and moderate (-14.0 %) observed rain and in poorly drained Panchayats (-33.3 %); worse than B1 on wet-day MAE (-7.2 %) and RMSE (-4.3 %). All of rain's gain over B0 comes from the bias correction.
- Most of the gain over B0 is bias correction for wind (97 %) and Tmin (77 %).
- Events: model CSI beats B0 and B1 at 1 and 2.5 mm, is slightly below at 10 mm and far below at 35 mm (0.141 vs 0.349 / 0.371); Brier skill vs monthly climatology is -0.016 at 35 mm. High-probability bins are overconfident (P 0.9-1.0 for 1 mm verifies 0.76).
- Coverage of the 80 % interval: tmax 0.776 (too narrow), tmin 0.814, rh 0.853 and wind 0.899 (too wide), rain 0.934 on all days but 0.509 on wet days (width 28.7 mm).
- Decisions (whole TEST, lead day 1, 14,760 per decision): spray hold is correct more often (97.3 % vs 95.8 % B0) with fewer wasted waits (217 vs 554) but more wash-offs (179 vs 68). The p90 heat alert is correct less often (88.8 % vs 94.6 %: 1,628 false alarms vs 527, 22 misses vs 275). Irrigation wait is correct less often (97.8 % vs 98.4 %) with more misses (192 vs 80). December has no rain or heat events.
- Block consistency: largest block-mean error 1.4e-14.

S11: verification and impact screens on contract v0.3.0 (no contract change). Built:
- `lib/verify.ts`: fixed decimals per metric with a row-level widening when rounding would hide a difference, best value per row (lower, higher, nearest 0, nearest 1; ties share), signed skill percents that never print a non-zero value as 0, interval readings (better, worse, no clear difference), outcome shares, strata parsing, loss-note split.
- Verification screen: one-sentence method summary (model, period, truth, checks) with the synthetic notice, TEST opening and block-consistency line; comparison table for the held-out period, held-out block or stations (Model, B0, B1, B2, skill vs B0 and vs B1 with 95 % intervals and a word), best value bold, losing rows unchanged; rain-event yes/no table (POD, FAR, CSI, frequency bias, Brier; model, B0, B1); reliability plot (event selector, diagonal, dot size by count) with its table; coverage bars against the 80 % aim with a strata table and widths; regions table per variable with model minus B0; "Where the model does not help" from the job's notes; footnotes from the API notes.
- Impact screen: decision and period selectors, two stacked bars (model, B0) with numbers on or directly under the segments, the two rules in words, what each mistake means for the chosen decision, placeholder-threshold line, counts table with B1, API notes.
- Every chart has a table next to it; bars carry an `aria-label` with every number.
- Tests: 202 frontend (39 new: formatting, best-value highlighting, strata, page tests against the contract examples, including a losing row read in words).
- Screenshots `verification-{en,hi}-{desktop,phone}.png`, `impact-{en,pa}-{desktop,phone}.png` reviewed; fixes made from the review (empty space above the summary, mixed decimals in the regions columns, a coverage label on the 80 % line, a capitalised decision name mid-sentence, narrow row names on phone).
- Checked against the job's files: with the API on `backend/artifacts/verification.json` and `impact.json`, the screen showed rain MAE 1.070 / 1.240 / 1.031 / 1.032, skill vs B1 on wet days -7.2 % (-12.0 % to -0.04 %, worse), wet-day rain coverage 50.9 % at 28.7 mm, MB01 rain 0.941 (-0.092 vs B0) and spray counts 14,364 / 217 / 179 against 14,138 / 554 / 68; the files hold 1.07045, 1.23993, 1.03107, 1.03153, -0.071987 (-0.120287 to -0.000365), 0.509421, 28.6671, 0.940999 (-0.091651) and the same counts.
S12: farmer side, feedback loop demo, audio and the offline snapshot. Contract v0.4.0 (additive; v0.3.0 is S10's). Built:
- `store/seed_demo.py`: five demo profiles (D093), migration 2 (`farmers.livestock`, D094). The API seeds an empty table.
- `/farmers/{id}` from SQLite; `/farmers/{id}/advice`: approved or edited only, farmer's Panchayat and crops (livestock only for F001 and F004), severe first, plus optional `spray_days` (D095).
- `POST /feedback`: date inside the data period and not in the future, answer and intensity must agree (400), identical report within 10 minutes answers `stored: false` with the first id (D096). Thank-you text no longer claims the forecast improves (D098).
- `advisory/audio.py` + `/audio/{id}?lang=`: gTTS, cached by text hash under `artifacts/audio/`, 404 `audio_not_available` on any failure; `Advisory.audio` links for approved and edited advisories. **Punjabi works with gTTS 2.5.4** (D097).
- `verify/feedback_report.py` writes `docs/feedback_loop_demo.md`: 2023-08 had 40 reports, rain yes/no agrees 92 % (37 of 40) with station or synthetic truth, and Panchayats with any ground check go from 24 (stations) to 48 of 90 with reports. Demo of the loop, no retraining, no forecast scoring, TEST months refused; no observation nudge (D099).
- `gramdrishti/export_snapshot.py`: 21,965 validated GET responses for the 8 demo dates, all 90 Panchayats and the 5 farmers, 39 MB, 64 s, into git-ignored `contract/snapshot/`; `npm run sync:mock` copies it to `frontend/public/snapshot/` (D100). Checked in the browser with the API stopped: farmer screen shows F001's three approved advisories, the map shows 27 Dec 2024 lead 3 Tmin.
- Tests: 375 backend (16 new in `test_farmers.py`, 2 in `test_store.py`), 120 frontend.

Same block MB03, 2024-09-09, after approving every draft in MP0307 and MP0311 (6 advisories): F001 (MP0307, hi, keeps livestock) sees spray hold, clear drains, livestock heat; F002 (MP0311, pa, no livestock) sees harvest before the rain, hold irrigation, and not the approved livestock item. F005 (MP0103, wheat only) sees nothing on that date.

S13: farmer app, languages, bulletin and offline (contract v0.4.0, examples added, no shape change). Built:
- S12 merged into the S13 branch (D102); conflicts with S10 resolved, `openapi.json` and examples regenerated.
- Contract examples for every demo farmer: their Panchayat forecasts, F003 to F005 advice, `/advisories?panchayat_id=&issue_date=` for the bulletin; `export_snapshot` exports the same list per Panchayat (D111).
- `/farmer`: phone-width column, farmer top bar (Panchayat name, offline pill, three languages), demo control at the foot of each screen (D109). Today: the most urgent approved advisory as a block (category icon, 24 px action, first sentence of the reason, confidence word, Listen, Share, "Why, and what if"), then "Also today (n)" as a list, then the printable bulletin link. Forecast: five days with rain word and mm, temperature, wind and spray suitability as icon plus word, whole-day note (D103, D104). My farm: Panchayat, block, language, crops with sowing dates, local-only editing that says it is not saved.
- "Did it rain today?": Yes, then light, moderate or heavy; No; posts to `/feedback` and shows the API's thank-you; demo files say the answer was not sent; offline answers wait in localStorage and go out when online (D107).
- Share: `https://wa.me/?text=` with action, reason, source and the mock notice (D112). Listen: server MP3 on the real API, else hi-IN, pa-IN or en-IN speech; playing state; a message when the phone has no voice for the language (D108).
- PWA: manifest and icons, `src/sw.ts` (injectManifest) precaching the shell and fonts and serving GETs network first with a cache fallback; offline pill in both top bars and "Saved copy. Last updated ..." when a screen shows cached data (D105). `sync:snapshot`, and `VITE_SNAPSHOT=1` copies the snapshot in one step (D106).
- `/bulletin/:pid?lang=`: A4 sheet in its own language: Panchayat, issue date, 3-day table, up to four approved actions with reasons, officer-review line, model and placeholder status line, mock notice in the footer; print CSS fits one A4 page at 12 pt minimum in black on white (D110).
- hi.json and pa.json cover every new string (drafts, `docs/translation_notes.md`).
- Tests: 412 backend, 226 frontend (24 new: first sentence, share link, voice choice, spoken text, outbox, offline bookkeeping, local timestamps, Today, Forecast, My farm, bulletin in en and pa). Playwright `npm run e2e:farmer` 5 passed (journey at 360 px in en, hi, pa; offline reload; bulletin print); `npm run shots` 52 passed; `npm run e2e` 19 passed.
- Checked in the in-app browser: server MP3 played for F001 on the real API (gTTS 200); on demo files Hindi was spoken by the Mac's hi-IN voice and Punjabi showed "no Punjabi voice"; feedback on the real API answered 200 with the thank-you; snapshot mode showed the MP0307 bulletin for 24 Dec 2024 with no API call.

Screenshot review (all three languages, 360 px, read at full size) and fixes made: the header with the demo control pushed the advice below the fold (moved the control to the foot); the crop editor clipped the date at 360 px (date on its own row); the bulletin heading printed the Panchayat id twice; the spray cell and the hi/pa "Avoid" word repeated the help line; the bulletin ran to a second A4 page (print spacing tightened, now one page, tested). Remaining: full-page screenshots show the sticky bottom navigation in mid-page (a capture artifact; on screen it stays at the bottom).

## Decisions
- D001 Licence MIT.
- D002 Mock data flattened into `data/`; zip and `synthetic_oracle/` git-ignored.
- D003 CI detect job skips missing halves.
- D004 B2 station offsets: static per-station, per-season offsets fitted on TRAIN, IDW, own station excluded.
- D005 Bias target: block truth in mock mode, station block means in real mode.
- D006 Season groups; wind ratio of sums; inverse-MSE weights per variable and lead.
- D007 Rain QM edge cases.
- D008 Real data in `data/real/`, same columns.
- D009 TEST window guard in code.
- D010 Generator default OUT and CI oracle regeneration.
- D011 Dependencies with minimum versions, pin in S14.
- D012 QC edge cases.
- D013 S2 branch stacked on S1.
- D014 Provisional forecast: p50 = B1, band from source spread.
- D015 `block` = raw block forecast B0.
- D016 Demo dates from issued forecasts only; forecast endpoints accept only demo dates.
- D017 `data_mode` everywhere, `provenance`, placeholders refused in real mode.
- D018 Shapes defined for endpoints Appendix A left open.
- D019 Placeholder risk thresholds and advisory generator, in-memory stores.
- D020 `/observed` serves station or synthetic truth for display.
- D021 Explain placeholder static contrast.
- D022 THI and Hargreaves ET0; soil moisture null.
- D023 Examples generated through the app, stale-file tests.
- D024 Hindi and Punjabi drafts need native review.
- D025 S3 branch stacked on S2.
- D026 Node 22, TypeScript 5.9, Vitest 4.1.
- D027 `public/mock` git-ignored and synced; `schema.d.ts` committed with CI staleness check.
- D028 Mock requests matched through `index.json`; `not_in_mock` empty state; snapshot format assumed.
- D029 Default issue date 2024-09-09.
- D030 Fixed date-name tables in three languages (Chrome lacks Punjabi months).
- D031 Extra design tokens, contrast-tested.
- D032 URL keys and role from route.
- D033 Placeholder numbers never displayed.
- D034 Screenshots can use installed Chrome.
- D035 Map, chart and PWA packages installed for later sessions.
- D036 S4 branch stacked on S3.
- D037 Linear colour interpolation, one ramp config for map and legend.
- D038 Temperature breaks 3 C over the values on screen; shared block/Panchayat ramp.
- D039 Difference ramp: symmetric, nice half-width with a floor, five stops.
- D040 URL keys `day` and `view`, omitted at defaults.
- D041 MapLibre worker handling in dev and production.
- D042 Panel headline from the map layer, variables table from `/forecast/panchayat`.
- D043 Note when values are flat within blocks.
- D044 Fixed-height map layout on wide screens; re-fit on resize.
- S5-D036 to S5-D045 (model core; the numbers repeat S4's, see D046): worktree, extra features, purge, diurnal repair, dew point and RH reconciliation, block consistency on the mean, CQR per lead group, LOBO design, multiplicative fallback, reproducibility.
- D046 S6 numbering from D046; D036-D045 used twice.
- D047 Snapshots use the S5 bundle s5-lgbm-9b632a7b1b, hash re-verified.
- D048 p50 and B0 `block` unchanged; `mean` and `block_corrected` added; consistency holds for mean vs B1; contract 0.1.2.
- D049 Snapshot layout, previous-day snapshots, 503 when missing.
- D050 Soil start state from the oracle at the end of D-1 (mock only); issue day not simulated.
- D051 Agro placeholder numbers; THI per Guide 8.
- D052 SHAP block contrast, 25 groups, no reasons when negligible, hi/pa null.
- D053 `/observed` stays on data files.
- D054 Event probabilities from classifiers; risk and advisories still placeholder.
- D055 Small-bundle test fixture; example freshness test needs matching local snapshots.
- D056 Change summary counts event changes.
- D057 S8 stacked on S6 in a separate worktree.
- D058 Signals: independent-days union for multi-day chances, das on lead day 1, `pre_sowing` look-ahead, livestock context everywhere.
- D059 Named thresholds in rules.yaml, calendar alerts, generated expert table, schema and checks.
- D060 Confidence keys, margins and reference widths.
- D061 Priority from base level, stage sensitivity and low confidence; irrigation starts moderate.
- D062 De-duplication with `supersedes`, then one per Panchayat, crop and category.
- D063 Review: edits null omitted languages, re-review allowed, audit before/after, drafts at 08:00.
- D064 SQLite store, lazy drafts in the API, tests on temporary databases, farmers table not seeded yet.
- D065 Crop-aware risk scores, priority ranking and crops_affected.
- D066 Contract v0.2.0 and `advice_changed`.
- D067 Spray hold uses the day-level planner.
- D068 Text formatting, English-only evidence, no gender agreement with crop names.
- D069 Removed the S2 placeholder risk and advisory texts.
- D092 S12 from `main` in a worktree, D092+ and contract v0.4.0 to avoid S9/S10 numbers.
- D093 Five demo farmers, Panchayat crop rows, F001/F002 share MB03.
- D094 `farmers.livestock`; livestock advice only to farmers who keep livestock.
- D095 Farmer advice filter, order and `spray_days`.
- D096 Feedback checks and 10-minute duplicate answer.
- D097 gTTS audio, Punjabi supported (2.5.4), text-hash cache, 404 on failure.
- D098 Thank-you text says "check", not "improve".
- D099 Feedback report: station or synthetic truth, TEST refused, no nudge.
- D100 Snapshot export of the frontend's exact requests, git-ignored.
- D101 Tests never call Google.
- D057 S7 stacked on S6.
- D058 Headline and chart middle line on p50.
- D059 Chart variable switch shares the map variable.
- D060 Probability and confidence words.
- D061 Change list wording and merging.
- D062 Observed overlay off by default, source labelled.
- D063 Real endpoints in `.env.example`; `SHOTS_REAL` panel screenshots.
- D064 Explain difference labelled apart from the headline difference.
- D065 Fan chart y domain.
- D070 TEST opened once, ledger, rerun reproduced byte for byte; `-dirty` came from another session's frontend files.
- D071 TEST issue-date purge and CALIB dry run.
- D072 Verdicts from the MAE-skill bootstrap interval; daily sums; quantile loss not used for verdicts.
- D073 Event yes at P >= 0.5; monthly TRAIN climatology.
- D074 Leave-one-block-out refits mean models only.
- D075 Station check; B2 from the pipeline's B1.
- D076 Decision replay rules, 35 C heat threshold from TRAIN, count names.
- D077 Contract v0.3.0; files or 503; placeholders removed.
- D078 Observed rain-intensity strata.
- D079 Data quality stays a 30-day view, provenance computed.
- D080 S11 worktree stacked on S10.
- D081 Skill against B0 and B1, words from the interval.
- D082 Number rules: fixed decimals, widening only to show a difference, best-value rules.
- D083 Loss notes split by the job's wording.
- D084 Reliability dots at mean probability, coverage chart rows.
- D085 Impact bars: true widths, labels under narrow segments, decision-specific outcome names.
- D086 `.env.example` serves verification and impact from the API.
- D080 S9 in a separate worktree after a parallel session shared the checkout; decisions from D080 (S10 uses D070-D079).
- D081 Reviews need the API; demo files are read-only.
- D082 Reviewer name field, default "Demo officer", no login.
- D083 Review button rules and Ctrl+Enter.
- D084 Translations cleared by an English edit are announced, edited ones kept.
- D085 One word per action: Approved, Edited and approved, Rejected.
- D086 The reviewed advisory stays open; the queue refetches.
- D087 Queue order, filters and keyboard listbox.
- D088 Priority filters, rank, column order, map link, print.
- D089 Risk layer: categorical colours, URL key, view mode off, panel level; navigation keeps shared keys only.
- D090 `npm run e2e` runs its own API with a throwaway database.
- D091 Audit times shown as the server wrote them.
- D102 S13 merges the unmerged S12 branch; S10 conflicts resolved.
- D103 Farmer forecast days stacked vertically.
- D104 Farmer rain word from P(1 mm), whole-number ranges.
- D105 injectManifest service worker with fetched-at stamps; offlineFirst queries.
- D106 Snapshot copied only with VITE_SNAPSHOT=1.
- D107 Feedback about the demo issue date; offline outbox.
- D108 Audio: server MP3 or same-language phone voice, never another language.
- D109 Demo farmer control at the foot of each screen.
- D110 Bulletin route, own language, one A4 page.
- D111 Examples for all demo farmers and per-Panchayat advisory lists.
- D112 Shared WhatsApp text carries the mock notice.

## Not verified
- S0: Mermaid checked with the mermaid parser locally, not seen rendered on GitHub.
- S1: CI has not run on GitHub from this session (no `gh`); check the pull request's checks. That includes the oracle regeneration step and the generator reproduction test on Linux with Python 3.11. Local runs used Python 3.13.9, pandas 3.0.6 and numpy 2.5.3 on macOS.
- S1: real mode was tested only with copies of mock files under `data/real/` (column and dtype equality). No real data exists.
- S1: B2 IDW and lapse terms are unit-tested on hand-made data. Their effect on the mock data is small because mock elevations vary by only about 8 m.
- S2: CI has not run this branch (no `gh`). `test_examples_are_up_to_date` compares regenerated examples byte for byte; numbers are rounded to 2 decimals, but a different numpy/pandas on Linux could still flip a last digit. If it fails in CI only, regenerate there or loosen that test to a numeric tolerance.
- S2: `/docs` was checked to answer 200, not clicked through in a browser.
- S2: the Hindi and Punjabi strings are unreviewed drafts.
- S3: the Hindi and Punjabi UI strings and date names are unreviewed drafts. Screenshots show no missing-glyph boxes in Chrome 153 on macOS; not checked on Windows, Android or a low-end phone.
- S3: CI has not run the frontend job (no `gh`), including Node 22 via `.nvmrc` and `npm run check:types` on Linux.
- S3: `VITE_SNAPSHOT=1` is unit-tested with contract examples only; no backend snapshot export exists yet.
- S3: screenshots came from the installed Google Chrome, not Playwright's Chromium (download blocked here, D034). Keyboard use and a screen reader were not tried by hand.
- S4: map hover, click, view toggle, table sort and lead-day switching were tried by hand in the in-app browser (dev server) on mock data and against the local API (`VITE_REAL_ENDPOINTS=meta,geo,forecast`, dates 2024-09-09 and 2024-07-31). Screenshots come from the production build in installed Chrome. Not tried on a touch device, in Firefox or Safari, or with a screen reader; the map canvas itself is not keyboard-operable beyond MapLibre's own pan and zoom keys (the table is the keyboard route).
- S4: the WebGL fallback message was not triggered (no browser without WebGL here).
- S4: CI has not run this branch.
- S2: `DATA_MODE=real` was tested only for the 503 answers of placeholder endpoints; the rest of real mode needs real files.
- S6: CI has not run this branch (no `gh`). In CI the example freshness test is skipped (no trained model there, D055); every other test builds its own small model.
- S6: snapshots were built with the S5 bundle copied from the S5 worktree (hash re-verified from this checkout).
- S6: real mode for snapshots is untested: `run_daily` needs a trained real-mode model, which cannot exist yet; soil fields would be null.
- S6: Hindi and Punjabi explain texts do not exist (null); the new Hindi and Punjabi change summary ("No earlier forecast to compare with") is a draft needing native review.
- S6: the frontend was not run against the new API in a browser this session (types, tests, lint and build only).
- S8: CI has not run this branch (no `gh`). The branch is stacked on S6; its PR diff includes S6 until S6 merges.
- S8: the frontend was not run against the new endpoints in a browser (types regenerated; tests, lint and build pass with the main checkout's `node_modules` linked in).
- S8: Hindi and Punjabi advisory text, crop and stage names and headlines are unreviewed drafts. Every threshold is a placeholder.
- S8: real mode is untested for advisories: soil signals would be missing, so irrigation, sowing and dry-spell rules would be skipped (counted, not guessed).
- S8: `sowing_go` and `sowing_heavy_rain_wait` fire on no demo date (November soil is dry in the mock data); only their unit cases cover them.

- S7: CI has not run this branch (no `gh`). The `SHOTS_REAL` screenshots need the local API with snapshots and are not part of CI.
- S7: keyboard use of the chart (the SVG is hidden from assistive tech; the table is the route) and the confidence tooltip were not tried with a real screen reader. Chart hover was checked with a dispatched mouse event; the in-app browser's hover emulation did not trigger it in a scaled viewport.
- S7: Hindi and Punjabi panel strings are drafts (word order in "कल: सूखा (4%)। अब: ..." is built from parts and uses "." rather than "।").
- S7: tested in Chrome only; not in Firefox, Safari or on a touch device.

- S12: CI has not run this branch (no `gh`). The examples freshness test needs local snapshots.
- S12: nobody has listened to the generated Hindi or Punjabi audio; only the file type (MPEG layer III, 24 kHz) and size were checked. Pronunciation of numbers and units ("मिमी", "ਮਿਲੀਮੀਟਰ") is unknown.
- S12: snapshot mode was checked in the in-app browser on two screens (farmer Today, map with detail panel), not screen by screen; the full export was not built in production mode (`npm run build` copies 104 MB of snapshot into `dist/`).
- S12: the new hi/pa feedback texts are drafts needing native review.
- S12: the feedback report used the mock file only (`--no-store`); with API reports it adds them the same way (unit-tested).
- S10: CI has not run this branch (no `gh`). In CI there is no trained model or `verification.json`: the job's tests run on CALIB with the small bundle, and the example and report freshness tests are skipped.
- S10: real mode is not verified: the job raises in real mode (no Panchayat truth); leave-one-station-out against real stations is future work.
- S10: the frontend verification and impact screens were not run against the new endpoints (types regenerated; frontend tests pass).
- S10: `docs/validation_report.md` was checked as Markdown text, not seen rendered on GitHub.
- S11: CI has not run this branch (no `gh`). The branch is stacked on S10; its PR diff includes S9 and S10 until they merge.
- S11: the screens were checked against the real API in the in-app browser (dev server, English) and in screenshots from the production build on mock files (Chrome). Not tried with a screen reader, on a touch device, in Firefox or Safari. Chart tooltips were not hovered by hand; the tables carry the same numbers.
- S11: the Hindi and Punjabi strings for both screens are drafts needing native review. API notes, rules and check descriptions stay English (the API has no translations for them).
- S11: in this worktree's dev server the Devanagari and Gurmukhi fonts answer 403, because `node_modules` is a symlink to the main checkout and Vite refuses files outside its root. The production build and the main checkout are not affected.
- S9: CI has not run this branch (no `gh`). `npm run e2e` needs the backend venv, trained artifacts and snapshots, so it is not part of CI; it was run locally (Chrome 153, macOS).
- S9: tested in Chrome only. Keyboard use was tested with Playwright and the in-app browser, not with a screen reader. `field-sizing: content` (auto-growing text areas) is Chrome-only; other browsers keep a fixed height with a scrollbar.
- S9: printing was checked with print-media emulation and a screenshot, not on paper or as a PDF from the print dialog.
- S9: new Hindi and Punjabi UI strings (risk, priority, review, statuses, categories) are drafts needing native review. Stage names come from `templates.yaml` (also drafts).
- S9: the farmer advice query is invalidated after a review, but the farmer screen is not built yet (S13), so the effect on it is untested.
- S12: CI has not run this branch (no `gh`). The examples freshness test needs local snapshots.
- S12: nobody has listened to the generated Hindi or Punjabi audio; only the file type (MPEG layer III, 24 kHz) and size were checked. Pronunciation of numbers and units ("मिमी", "ਮਿਲੀਮੀਟਰ") is unknown.
- S12: snapshot mode was checked in the in-app browser on two screens (farmer Today, map with detail panel), not screen by screen; the full export was not built in production mode (`npm run build` copies 104 MB of snapshot into `dist/`).
- S12: the new hi/pa feedback texts are drafts needing native review.
- S12: the feedback report used the mock file only (`--no-store`); with API reports it adds them the same way (unit-tested).
- S13: CI has not run this branch (no `gh`). `npm run e2e:farmer` builds the app and needs a browser; it was run locally with `SHOTS_BROWSER_CHANNEL=chrome` (Playwright's headless shell is not downloaded here), not in CI.
- S13: not tried on a real phone. Offline was tested with Playwright's offline mode in desktop Chrome at 360 px, not airplane mode on a device. Voices differ per phone: only the Mac's voices were tried (Hindi yes, Punjabi none). The server MP3 was played once for English; nobody listened to Hindi or Punjabi audio.
- S13: WhatsApp sharing was checked as a link (text and encoding in tests); the link was not opened in WhatsApp.
- S13: printing was checked with print emulation, a screenshot and a Chrome PDF (A4, one page), not on paper and not in Firefox or Safari.
- S13: all hi/pa farmer and bulletin strings are drafts; no native speaker has read the screens.
- S13: the install prompt (Add to home screen) was not tried; the manifest and icons were only checked in the build output.

## Known issues
- S12 the snapshot is 21,965 files (39 MB of JSON, about 104 MB on disk); `npm run sync:mock` copies it on every `dev` and `build` when `contract/snapshot/` exists, and a build then carries it in `dist/`. Delete `contract/snapshot/` when not rehearsing the offline demo.
- S12 spray days are identical for F001 and F002 on 2024-09-09: rain chances are flat within MB03 (the S8 known issue).
- S12 an audio request without internet waits for gTTS's 10 s timeout before the 404.
- S12 in the worktree, Vite answers 403 for font files through the symlinked `node_modules`; not a problem in a normal checkout.
- S5 rain does not beat B1 (LOBO -0.7 %, CALIB -15.8 % MAE). The rain CQR offset is 0 because dry days dominate, and wet-day coverage is 0.42..0.72. Options for discussion (not tuning): serve B1 rain amount with model event probabilities, or a wet-day-conditional interval.
- S5 isotonic calibration is kept as the guide says but did not help on CALIB halves. Discuss before S6.
- S5 CALIB covers May to mid-July only, so coverage in winter is unmeasured until TEST (S10).
- S5 the oracle loader parses the whole CSV; TEST-window rows are dropped immediately in `add_targets`/`fit_bias` before any computation.
- `gh` CLI not installed, so pull requests are opened by hand from the compare URL.
- `data/synthetic_oracle/` is git-ignored: a fresh clone must run `python data/generate_mock_data.py` (the default output is now `data/`).
- `mock_data_summary.json` regenerates with one float differing in the 16th significant digit (`tmin_std_c_mean`), because summation order differs across numpy versions. All CSV and GeoJSON files are byte-identical.
- The S1 baseline report on CALIB (data description only): B1 rain RMSE is higher than B0 at leads 1 and 2. B1 RH bias is +0.75 to +1.19 % at leads 3 and 4 while B0 is -0.65 to -0.01 %. B2 differs from B1 by at most a few hundredths for temperature. B1 corrected wet-day frequency is 0.112 to 0.134 against block truth 0.103.
- `data/README.md` said 14 AWS + 10 ARG. The file has 12 + 12, and the README is now corrected.

- S2 provisional band is not calibrated: rain p90 can be about 2x p50 on heavy days (for example 193 mm on 2024-09-10 in MB03). Do not quote coverage from it.
- S2 all Panchayats in a block share values (B1 is block-level). Resolved in S6 for Tmax, Tmin, RH and wind. **Rain p50 is still almost flat inside a block** (MB03 on 2024-09-10: 103.84 mm for all 16 Panchayats; the model mean ranges 65 to 124 mm). The rain model does not beat B1 at Panchayat level (S5), so the within-block rain differences are not skilful anyway.
- S6 rain quantiles and event classifiers are separate models and can disagree: rain p10 is 0 mm where P(rain >= 1 mm) is 0.91. After the non-increasing clamp some days show equal probabilities for 1, 2.5 and 10 mm (0.54 each for MP0305 on 2024-09-13).
- S6 map `delta` is p50 minus the raw block forecast B0, so it includes the bias correction (Tmax is cooler than B0 almost everywhere). The Panchayat-versus-corrected-block difference is `mean - block_corrected`.
- S6 soil water skips the issue day itself (D050) and simulates no irrigation, so irrigated Panchayats dry out faster than the oracle over five days.
- S6 explain texts: see "Explain texts that read awkwardly" above.
- S2 placeholder risk is coarse: on dry monsoon dates every Panchayat gets a "high" dry-spell item, and heat reaches "severe" in late July. Thresholds are placeholders (D019).
- S2 review decisions and feedback are in memory and reset on restart.
- `starlette.testclient` prints a deprecation warning about `httpx`; harmless for now.
- S3 most mock files exist only for issue date 2024-09-09, so other dates show "No demo file" on most screens in mock mode. Use `VITE_REAL_ENDPOINTS` for other dates.
- S3 demo-date labels from `/meta.issue_date_info` are English only, also in the Hindi and Punjabi UI.
- S3/S4 at phone width the officer map controls still fill most of the first screen; the map sits below them. One-finger drag on the map pans it rather than scrolling the page.
- S4 the lazy map chunk is 1.0 MB (284 kB gzip) plus a 510 kB worker, all MapLibre; Vite prints a chunk-size warning. It loads only on `/map`.
- S4 in mock mode only lead day 1 of 2024-09-09 has map files, and only MP0103, MP0302, MP0305, MP0412 have a Panchayat forecast; other days and Panchayats show "No demo file". Use the API for the rest.
- S7 the map chunk grew from 1.0 MB to 1.43 MB (395 kB gzip) with Recharts. It loads only on `/map`; lazy-loading the chart would let the map paint first.
- S7 rain event probabilities often repeat across thresholds (1, 2.5 and 10 mm all 28 % for MP0305 on 1 Aug 2024), a result of the S6 clamp. The panel shows them as they are.
- S7 the ribbon scrolls off-screen on phone once the page is scrolled (it is not sticky).
- S3 Vitest prints a Node warning about `--localstorage-file` (Node 25 with jsdom); harmless.
- S8 mock soil water is very dry all winter (depletion 0.9 to 0.98 in rabi; the start state comes from the oracle and no irrigation is simulated, D050), so almost every sown field gets "irrigate" in November to January (83 on 2024-01-12, 84 on 2024-12-24).
- S8 livestock heat advice fires in all 90 Panchayats on four demo dates (THI p90 is 80 to 96 in the monsoon with the upper maximum temperature). It is weather-wide, not local, and makes the review queue long; the expert should set the THI thresholds.
- S8 heavy-rain chances are the same for every Panchayat in a block on some days (MB03 on 2024-09-10: 0.64 everywhere), so heavy-rain risk and priority are flat within those blocks.
- S8 `/priority` answers in about 70 ms warm (headline lookups per item); fine for 90 Panchayats.
- S8 the first `/advisories` request for an issue date without a `run_daily` run writes that date's drafts (about 0.5 s).

- S10 rain: the Panchayat rain forecast does not beat the corrected block forecast B1 on TEST (MAE -3.8 %, tie; wet days, light and moderate rain and poorly drained Panchayats worse). Serving B1 rain amounts with the model's event probabilities is an option to discuss (not tuning; it would be a new model version and TEST would count as reused).
- S10 heavy rain: the 35 mm classifier is worse than climatology and far below B0/B1 CSI; heavy-rain risk and waterlogging advice lean on it.
- S10 intervals: Tmax under-covers (0.776), wind and RH over-cover (0.899, 0.853); rain on wet days 0.509.
- S10 decisions: the p90 heat rule trades misses for many false alarms (1,628 vs 527 at B0); spray and irrigation replays wash off more often than the block rule. Costs are needed from an expert before calling any trade-off better.
- S10 `verification_summary.json` example is 130 kB (strata and verdicts); the frontend may want to fetch strata lazily.
- S11 the reliability plot's 0-10 % dot holds 94 % of forecasts, so the other dots are drawn near the minimum size; the table gives the counts.
- S11 the impact bars are dominated by "correct" (83 to 99 %); the differences between forecasts are in the small segments and the table. Without expert costs the screen does not say which forecast is better overall.
- S11 the method sentence inserts the API's English truth text ("synthetic Panchayat truth (mock data generator)") into Hindi and Punjabi sentences.
- S10 another session committed S9 frontend work (`b8d86b0`, `35c056e`) on `session-10-verification-impact`, because both sessions share this checkout. The S10 pull request therefore contains those commits.
- S9 the review queue is long on monsoon dates (198 drafts on 2024-09-09, 90 livestock); there is no bulk approve. Worth asking officers whether one decision per rule and block would do.
- S9 priority rank (#) is the API's rank in the full list, so a filtered list shows gaps (1 to 19, then 62). Intentional, so a printed filtered list still shows overall urgency.
- S9 the risk layer uses `/risk` per lead day; the map has no "worst over the next days" view (the priority list has it).
- S9 `session-10-verification-impact` (unpushed) also contains the seven S9 commits and one S9 commit there deletes `provisional/placeholders.py` (a deletion S10 had staged). See the handoff.
- S13 the service worker caches data only as it is fetched: a screen never opened online is not available offline (the snapshot demo has the same limit). The precache includes the officer console's MapLibre chunk (2.9 MB total).
- S13 on demo files, feedback cannot be stored and says so; on the real API it needs `farmers,feedback` in `VITE_REAL_ENDPOINTS`, and the farmer's Today stays empty until an officer approves drafts in that Panchayat.
- S13 Panchayat names are English ("Synthetic Panchayat MP0307") on Hindi and Punjabi screens: the geography has no translated names.
- S13 feedback answers queued offline are kept per browser; if storage is blocked the answer is lost (the screen says it was saved only when storing worked).

## Inputs needed from the team
- Enable branch protection on `main` (require pull request, require CI).
- Native Hindi and Punjabi review of `frontend/src/i18n/hi.json`, `pa.json` and the day/month names in `frontend/src/lib/format.ts` (S3), then advisory text (S13).
- Expert threshold review: send `docs/thresholds_for_expert_review.md` to a KVK or SAU expert (every rule, spray-planner, risk, confidence, crop-calendar and agro placeholder, with blank columns for their value and source).
- Native Hindi and Punjabi review of `backend/gramdrishti/advisory/templates.yaml` (see `docs/translation_notes.md`).
- Which cotton the district grows (ਨਰਮਾ or ਕਪਾਹ in Punjabi text), and whether livestock advice should go to every Panchayat.
- Expert review of the S6 agro placeholders (D051): runoff, kc, waterlogging and frost thresholds, fog proxy, crop base temperatures.
- Native Hindi and Punjabi writing of the explain sentence dictionary (`backend/gramdrishti/explain/texts.py`), about 50 phrases.
- For real mode: a soil-moisture source (ERA5-Land or SMAP) for the water balance start state.
- Decide with the team how to present rain (B1 amounts plus model event probabilities, or keep the model and show the tie). Any change means a new model version and a report that says TEST was reused.
- Costs of a washed-off spray, a wasted wait and a missed heat alert (for the impact screen to weigh counts), from an expert.
- Try the built farmer app on a real low-end Android phone on the same network: airplane mode and reload, Listen in all three languages (which voices exist), Share into WhatsApp.
- A Hindi and a Punjabi speaker to read the farmer screens and the printed bulletin (`docs/translation_notes.md`, S13 table).

## Model and validation log
| Date | Model version | Windows used | Notes |
|---|---|---|---|
| 2026-09-24 | baselines B0/B1/B2 (S1) | fit TRAIN, scored CALIB | `python -m gramdrishti.verify.baseline_report`. TEST window opened: never |
| 2026-09-26 | s5-lgbm (S5) | models TRAIN; isotonic + CQR CALIB; dev checks TRAIN LOBO and CALIB halves | `python -m gramdrishti.pipeline.train --lobo`. TEST window opened: never |
| 2026-09-25 | provisional API forecast (S2) | fit TRAIN; applied to issued forecasts on the 8 demo dates | No scoring. The demo date picker reads issued forecasts in the TEST period, not outcomes. `/observed` displays TEST-period truth on request; no metric uses it. TEST window opened for evaluation: never |
| 2026-09-26 | s5-lgbm-9b632a7b1b (S5) | models fit TRAIN; isotonic and conformal on CALIB; leave-one-block-out on TRAIN; out-of-time on CALIB | `python -m gramdrishti.pipeline.train --lobo`, report in `backend/artifacts/dev_report.txt` (numbers under "Current state"). Rain does not beat B1. Re-run without `--lobo` in S6: 114 s, byte-identical model files. TEST window opened: never |
| 2026-09-26 | rules.yaml v1 on s5-lgbm-9b632a7b1b snapshots (S8) | inference snapshots of the 8 demo dates and the day before each (unchanged from S6) | Rules engine drafts for the 8 demo dates; `/forecast/changes` runs the engine on the previous-day snapshots too. No scoring, no training. TEST window opened for evaluation: never |
| 2026-09-27 | s5-lgbm-9b632a7b1b snapshots, rules.yaml v1 (S12) | feedback report on 2023-08 (TRAIN); snapshot export of the 8 demo dates | Feedback report compares mock reports with station rain or synthetic truth for one TRAIN month; no forecast scoring, TEST months refused in code. The export serves existing snapshots and `/observed` (display, D020). TEST window opened for evaluation: never |
| 2026-09-26 | s5-lgbm-9b632a7b1b applied (S6) | inference on issued forecasts for the 8 demo dates and the day before each (6 of them in TEST) | `python -m gramdrishti.pipeline.run_daily --all-demo-dates`. No scoring. The soil water balance starts from oracle soil moisture on the day before each issue date (mock stand-in, D050); no metric uses it. TEST window opened for evaluation: never |

## S10 validation protocol (recorded before TEST was opened)
Full protocol: `docs/validation_protocol.md`. Frozen: model `s5-lgbm-9b632a7b1b`, data hash `9b632a7b1b...`, verification code commit `4101fe4`, seed 42, sha256 of every data file read. TEST (2024-07-16..2024-12-31) is opened once for this model version by `python -m gramdrishti.verify.run_validation`, which writes the opening time to `docs/test_window_ledger.json` before reading any TEST truth. Any model, feature, calibration, baseline or threshold change after seeing TEST gets a new version number, and the report then says TEST was reused. No tuning against TEST. The dry run of the same code on CALIB (2026-09-27) reproduced the S5 CALIB numbers (rain MAE -15.8 % vs B1, Tmax +12.4 %).
| 2026-09-27 | s5-lgbm-9b632a7b1b (S10) | models TRAIN; isotonic + CQR CALIB; evaluated on TEST (issue dates 2024-07-16..2024-12-26) | `python -m gramdrishti.verify.run_validation`. **TEST window first opened 2026-09-27T15:14:23** for this version (ledger `docs/test_window_ledger.json`); rerun at 15:23:42 gave identical numbers. Dry run of the same code on CALIB earlier the same day. Report: `docs/validation_report.md`. TEST reused: no |

## Handoff for the next session
S13 (2026-09-28): branch `session-13-farmer-app` in worktree `../GramDrishti-s13`, from `main` plus the unmerged S12 branch (D102). Merge order: S12, then S13 (after S12 merges, this PR shows only S13). Farmer screens live in `pages/farmer/` and `features/farmer/` (helpers in `farmerData.ts`, `forecastText.ts`, `speech.ts`, `outbox.ts`). Offline: `src/sw.ts`, `lib/network.ts`, `components/OfflinePill.tsx`, `LastUpdated.tsx`. S14: add `farmers,feedback,audio` to the Docker Compose `VITE_REAL_ENDPOINTS`, run `npm run e2e:farmer` in CI with a browser, and consider a feedback flow test against the API (checked by hand here). S15: screen reader pass on the farmer app and bulletin, 200 % zoom, the long officer queue.

Frontend (S11 done): `/verification` and `/impact` are built on contract v0.3.0 and read the job's files when `verification,impact` are in `VITE_REAL_ENDPOINTS`. Number rules live in `lib/verify.ts` (reuse `formatFixed`, `rowDigits`, `bestIndexes`, `formatSkill` wherever scores are shown, for example in the bulletin or README figures). If the job changes the wording of its loss notes, `splitNotes` puts them under "About these numbers" instead; a contract field would be sturdier. S15: check both screens with a screen reader and at 200 % zoom. When an expert supplies costs, the impact screen can weigh wasted waits against wash-offs (D085). Merge order: S10, then S11.

Frontend (S11): contract **v0.3.0**. `/verification/summary` has `checks[]` (temporal_holdout, leave_one_block_out, station), `strata[]`, `verdicts[]` (win / tie / loss / too_few_days) and per metric `skill_vs_b1` with `skill_vs_b1_ci95`; show B1 next to B0, because B1 is what isolates the Panchayat model. `/verification/coverage` items have `stratum` (`all`, `lead_day=n`, `season=x`, `observed_rain>=1mm`). `/verification/regions` has block (leave-one-block-out) and station rows with `b1`, `b2`. `/impact?season=monsoon_2024|post_monsoon_2024|winter_2024|test_2024&decision=...` has `block_corrected`, `events_observed`, `threshold`, `unit`; for heat and irrigation, `wasted_wait` means a false alarm and `washed_off` a miss (say so on screen). Every number is in `notes` and `docs/validation_report.md`; show the "Where the model does not help" notes, not only wins. Mock files: `verification_*.json`, `impact_<decision>.json` (monsoon) and `impact_<season>_<decision>.json`.
Backend: run order is now train, run_daily, run_validation (writes `verification.json`, `impact.json`), then `verify.report` and `make_examples`. A new model version must go through `docs/validation_protocol.md` (the ledger will mark TEST as reused).
S9 (2026-09-27): a parallel S10 session worked in the same checkout. It switched the branch to `session-10-verification-impact` right after S9 created its branch, so the seven S9 commits first landed on that branch, interleaved with S10's (nothing was pushed). S9 then built `session-09-priority-review` in a separate worktree (`../GramDrishti-s09`) by cherry-picking those commits onto `main`, and restored `backend/gramdrishti/provisional/placeholders.py` there. That file's deletion had been staged by S10 and swept into the S9 review-screen commit. The S9 branch differs from `main` only in `frontend/` and these docs. Before opening the S10 pull request, decide how to take the S9 commits out of `session-10-verification-impact` (for example: build S10's branch again from `main` with only its own commits, or merge S9 first and then `main` into S10). Choosing needs you, because it means rewriting an unpushed branch or accepting a mixed history.

Frontend S11/S13 from S9: `components/Toast.tsx` + `toastContext.ts` (toasts), `features/review/StatusChip.tsx`, `labels.ts` (advisory titles), `lib/format.formatDateTime`, `useRisk`, `useAdvisory`, `useReviewAdvisory` (invalidates `advisories`, `priority`, `farmerAdvice`). The farmer app must show only `approved` and `edited` advice (the API already filters). Detail panel advisories for the selected Panchayat are still to do (S13 or S15). `.env.example` now serves `risk,priority,advisories` from the API.
S12 (2026-09-27): branch `session-12-farmer-backend` from `main`. Merge order: S9, S10, then S12; after S10 merges, merge `main` into S12, rerun `python -m gramdrishti.export_openapi` and `python -m gramdrishti.contract.make_examples`, and keep both changelog entries (v0.3.0 S10, v0.4.0 S12). `export_snapshot` imports `IMPACT_SEASONS` from `provisional/placeholders.py`; after S10 it should take the seasons S10's impact endpoint serves.
Frontend (S13): `F001` stays the default farmer (`DEMO_FARMER_ID`), now MP0307 in Hindi; F002 is the same-block neighbour in Punjabi. `FarmerAdvice.spray_days` gives five whole-day ratings; `Advisory.audio[lang]` is a URL that can still 404 (`audio_not_available`), so keep the browser-speech fallback. `POST /feedback` can answer 400 (date or contradictory answer) and `stored: false` for a repeat. `VITE_SNAPSHOT=1` works after `python -m gramdrishti.export_snapshot` and `npm run sync:mock`.

Merge order: S6 (`session-06-snapshots-forecast-api`), then S8 (`session-08-advisory-engine`, stacked on S6, D057). After S6 merges, merge `main` into S8 and rerun `pytest`.

Local run: `cd backend && python -m gramdrishti.pipeline.train` (once, about 2 minutes), then `python -m gramdrishti.pipeline.run_daily --all-demo-dates` (snapshots and draft advisories, about 40 s), then the API. `python -m gramdrishti.advisory.show --issue-date 2024-09-09` prints advisories; `--counts` prints counts.

Frontend (S9): contract **v0.2.0** (additive, `contract/CHANGELOG.md`). `/risk`, `/priority` and `/advisories` are real rules-engine output with `provenance: computed` and `thresholds_status: placeholder` (show the placeholder notice from `thresholds_status`, not from provenance). Review screen: `POST /advisories/{id}/review` returns the updated advisory; audit entries carry optional `before` / `after` for a diff view; an edit that sends only `en` nulls `hi` and `pa` (D063), so say so in the edit form. `Advisory.rule_id` names the rule. Priority `crops_affected` can be empty. `derived.spray_rating` (good / caution / avoid) is per whole day, for a spray strip in the detail panel. New mock file `advisories_2024-12-24.json`; `risk_dry_spell.json` is now lead day 5 (dry spells build up over the days); `forecast_changes_*.json` has a boolean `advice_changed`.

Backend (S10): verification can replay decisions from the engine (`advisory.engine.generate` on any snapshot) and the spray planner (`advisory.spray.plan`); confidence levels are there to be checked against outcomes. S12: seed the `farmers` table (created, empty) and move `/farmers` onto it; feedback is already stored in SQLite. When the expert returns values: edit `rules.yaml` and the calendar, fill `source`, set `thresholds_status: reviewed` per rule, then regenerate the expert table and examples.
Frontend (S9): the panel now ends with "Forecast changed". Add advisories for the selected Panchayat under it and use `components/ConfidenceLabel` in advisory cards. Enable `RiskLayerSelect` in `features/map/MapControls.tsx` (`RISK_TOKENS` in `lib/ramps.ts`); reuse `components/DataTable.tsx`. Add `risk,priority,advisories` to `VITE_REAL_ENDPOINTS` once S8 serves rules. S6 is merged (#9); `main` was merged into S7, so the S7 pull request targets `main`.

Mock files (`contract/examples/`, main date 2024-09-09) follow `forecast_panchayat_<id>.json`, `observed_panchayat_<id>.json`, `explain_<id>.json` (plus `explain_MP0305_rain.json` and `explain_MP0103_rain_dry_block.json`), `forecast_changes_<id>.json`, `risk_<type>.json`, `farmer_<id>.json`, `advisories.json`, `advisories_2024-12-24.json`, `priority.json`, `priority_2024-12-24.json`. Show a notice when `provenance` or `thresholds_status` is `placeholder`.
