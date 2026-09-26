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
| S6 | Agro-variables, snapshots, forecast APIs | backend | PR open | session-06-snapshots-forecast-api | |
| S7 | Frontend detail panel and first integration | frontend | not started | | |
| S8 | Advisory engine and review APIs | backend | PR open (stacked on S6) | session-08-advisory-engine | |
| S9 | Frontend priority, risk and review | frontend | not started | | |
| S10 | Verification and impact | backend | not started | | |
| S11 | Frontend verification and impact | frontend | not started | | |
| S12 | Farmer-side backend and snapshot export | backend | not started | | |
| S13 | Frontend farmer app, languages, bulletin, offline | frontend | not started | | |
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

## Known issues
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
- S3 Vitest prints a Node warning about `--localstorage-file` (Node 25 with jsdom); harmless.
- S8 mock soil water is very dry all winter (depletion 0.9 to 0.98 in rabi; the start state comes from the oracle and no irrigation is simulated, D050), so almost every sown field gets "irrigate" in November to January (83 on 2024-01-12, 84 on 2024-12-24).
- S8 livestock heat advice fires in all 90 Panchayats on four demo dates (THI p90 is 80 to 96 in the monsoon with the upper maximum temperature). It is weather-wide, not local, and makes the review queue long; the expert should set the THI thresholds.
- S8 heavy-rain chances are the same for every Panchayat in a block on some days (MB03 on 2024-09-10: 0.64 everywhere), so heavy-rain risk and priority are flat within those blocks.
- S8 `/priority` answers in about 70 ms warm (headline lookups per item); fine for 90 Panchayats.
- S8 the first `/advisories` request for an issue date without a `run_daily` run writes that date's drafts (about 0.5 s).

## Inputs needed from the team
- Enable branch protection on `main` (require pull request, require CI).
- Native Hindi and Punjabi review of `frontend/src/i18n/hi.json`, `pa.json` and the day/month names in `frontend/src/lib/format.ts` (S3), then advisory text (S13).
- Expert threshold review: send `docs/thresholds_for_expert_review.md` to a KVK or SAU expert (every rule, spray-planner, risk, confidence, crop-calendar and agro placeholder, with blank columns for their value and source).
- Native Hindi and Punjabi review of `backend/gramdrishti/advisory/templates.yaml` (see `docs/translation_notes.md`).
- Which cotton the district grows (ਨਰਮਾ or ਕਪਾਹ in Punjabi text), and whether livestock advice should go to every Panchayat.
- Expert review of the S6 agro placeholders (D051): runoff, kc, waterlogging and frost thresholds, fog proxy, crop base temperatures.
- Native Hindi and Punjabi writing of the explain sentence dictionary (`backend/gramdrishti/explain/texts.py`), about 50 phrases.
- For real mode: a soil-moisture source (ERA5-Land or SMAP) for the water balance start state.

## Model and validation log
| Date | Model version | Windows used | Notes |
|---|---|---|---|
| 2026-09-24 | baselines B0/B1/B2 (S1) | fit TRAIN, scored CALIB | `python -m gramdrishti.verify.baseline_report`. TEST window opened: never |
| 2026-09-25 | provisional API forecast (S2) | fit TRAIN; applied to issued forecasts on the 8 demo dates | No scoring. The demo date picker reads issued forecasts in the TEST period, not outcomes. `/observed` displays TEST-period truth on request; no metric uses it. TEST window opened for evaluation: never |
| 2026-09-26 | s5-lgbm-9b632a7b1b (S5) | models fit TRAIN; isotonic and conformal on CALIB; leave-one-block-out on TRAIN; out-of-time on CALIB | `python -m gramdrishti.pipeline.train --lobo`, report in `backend/artifacts/dev_report.txt` (numbers under "Current state"). Rain does not beat B1. Re-run without `--lobo` in S6: 114 s, byte-identical model files. TEST window opened: never |
| 2026-09-26 | rules.yaml v1 on s5-lgbm-9b632a7b1b snapshots (S8) | inference snapshots of the 8 demo dates and the day before each (unchanged from S6) | Rules engine drafts for the 8 demo dates; `/forecast/changes` runs the engine on the previous-day snapshots too. No scoring, no training. TEST window opened for evaluation: never |
| 2026-09-26 | s5-lgbm-9b632a7b1b applied (S6) | inference on issued forecasts for the 8 demo dates and the day before each (6 of them in TEST) | `python -m gramdrishti.pipeline.run_daily --all-demo-dates`. No scoring. The soil water balance starts from oracle soil moisture on the day before each issue date (mock stand-in, D050); no metric uses it. TEST window opened for evaluation: never |

## Handoff for the next session
Merge order: S6 (`session-06-snapshots-forecast-api`), then S8 (`session-08-advisory-engine`, stacked on S6, D057). After S6 merges, merge `main` into S8 and rerun `pytest`.

Local run: `cd backend && python -m gramdrishti.pipeline.train` (once, about 2 minutes), then `python -m gramdrishti.pipeline.run_daily --all-demo-dates` (snapshots and draft advisories, about 40 s), then the API. `python -m gramdrishti.advisory.show --issue-date 2024-09-09` prints advisories; `--counts` prints counts.

Frontend (S9): contract **v0.2.0** (additive, `contract/CHANGELOG.md`). `/risk`, `/priority` and `/advisories` are real rules-engine output with `provenance: computed` and `thresholds_status: placeholder` (show the placeholder notice from `thresholds_status`, not from provenance). Review screen: `POST /advisories/{id}/review` returns the updated advisory; audit entries carry optional `before` / `after` for a diff view; an edit that sends only `en` nulls `hi` and `pa` (D063), so say so in the edit form. `Advisory.rule_id` names the rule. Priority `crops_affected` can be empty. `derived.spray_rating` (good / caution / avoid) is per whole day, for a spray strip in the detail panel. New mock file `advisories_2024-12-24.json`; `risk_dry_spell.json` is now lead day 5 (dry spells build up over the days); `forecast_changes_*.json` has a boolean `advice_changed`.

Backend (S10): verification can replay decisions from the engine (`advisory.engine.generate` on any snapshot) and the spray planner (`advisory.spray.plan`); confidence levels are there to be checked against outcomes. S12: seed the `farmers` table (created, empty) and move `/farmers` onto it; feedback is already stored in SQLite. When the expert returns values: edit `rules.yaml` and the calendar, fill `source`, set `thresholds_status: reviewed` per rule, then regenerate the expert table and examples.

Mock files (`contract/examples/`, main date 2024-09-09) follow `forecast_panchayat_<id>.json`, `observed_panchayat_<id>.json`, `explain_<id>.json` (plus `explain_MP0305_rain.json` and `explain_MP0103_rain_dry_block.json`), `forecast_changes_<id>.json`, `risk_<type>.json`, `farmer_<id>.json`, `advisories.json`, `advisories_2024-12-24.json`, `priority.json`, `priority_2024-12-24.json`. Show a notice when `provenance` or `thresholds_status` is `placeholder`.
