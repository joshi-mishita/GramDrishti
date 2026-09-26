# GramDrishti progress log

Claude Code updates this file at the end of every session. People update the "Merged" column after reviewing the pull request.

## Session status

| ID | Session | Owner | Status | PR | Merged |
|---|---|---|---|---|---|
| S0 | Repo foundation | both | merged | session-00-foundation (#1) | yes |
| S1 | Backend data layer and baselines | backend | PR open | session-01-backend-data-baselines | |
| S2 | Contract and API skeleton | backend | PR open | session-02-contract-api (stacked on S1) | |
| S3 | Frontend foundation | frontend | not started | | |
| S4 | Frontend map explorer | frontend | not started | | |
| S5 | Backend model core | backend | in progress (handoff below) | session-05-model-core | |
| S6 | Agro-variables, snapshots, forecast APIs | backend | not started | | |
| S7 | Frontend detail panel and first integration | frontend | not started | | |
| S8 | Advisory engine and review APIs | backend | not started | | |
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

## Known issues
- `gh` CLI not installed, so pull requests are opened by hand from the compare URL.
- `data/synthetic_oracle/` is git-ignored: a fresh clone must run `python data/generate_mock_data.py` (the default output is now `data/`).
- `mock_data_summary.json` regenerates with one float differing in the 16th significant digit (`tmin_std_c_mean`), because summation order differs across numpy versions. All CSV and GeoJSON files are byte-identical.
- The S1 baseline report on CALIB (data description only): B1 rain RMSE is higher than B0 at leads 1 and 2. B1 RH bias is +0.75 to +1.19 % at leads 3 and 4 while B0 is -0.65 to -0.01 %. B2 differs from B1 by at most a few hundredths for temperature. B1 corrected wet-day frequency is 0.112 to 0.134 against block truth 0.103.
- `data/README.md` said 14 AWS + 10 ARG. The file has 12 + 12, and the README is now corrected.

- S2 provisional band is not calibrated: rain p90 can be about 2x p50 on heavy days (for example 193 mm on 2024-09-10 in MB03). Do not quote coverage from it.
- S2 all Panchayats in a block share values (B1 is block-level), so the Panchayat map view looks like the block view with a flat delta per block. Real within-block variation arrives with S5.
- S2 placeholder risk is coarse: on dry monsoon dates every Panchayat gets a "high" dry-spell item, and heat reaches "severe" in late July. Thresholds are placeholders (D019).
- S2 review decisions and feedback are in memory and reset on restart.
- `starlette.testclient` prints a deprecation warning about `httpx`; harmless for now.
- S3 most mock files exist only for issue date 2024-09-09, so other dates show "No demo file" on most screens in mock mode. Use `VITE_REAL_ENDPOINTS` for other dates.
- S3 demo-date labels from `/meta.issue_date_info` are English only, also in the Hindi and Punjabi UI.
- S3/S4 at phone width the officer map controls still fill most of the first screen; the map sits below them. One-finger drag on the map pans it rather than scrolling the page.
- S4 the lazy map chunk is 1.0 MB (284 kB gzip) plus a 510 kB worker, all MapLibre; Vite prints a chunk-size warning. It loads only on `/map`.
- S4 in mock mode only lead day 1 of 2024-09-09 has map files, and only MP0103, MP0302, MP0305, MP0412 have a Panchayat forecast; other days and Panchayats show "No demo file". Use the API for the rest.
- S3 Vitest prints a Node warning about `--localstorage-file` (Node 25 with jsdom); harmless.

## Inputs needed from the team
- Enable branch protection on `main` (require pull request, require CI).
- Native Hindi and Punjabi review of `frontend/src/i18n/hi.json`, `pa.json` and the day/month names in `frontend/src/lib/format.ts` (S3), then advisory text (S13).
- Later: expert threshold review (S8).

## Model and validation log
| Date | Model version | Windows used | Notes |
|---|---|---|---|
| 2026-09-24 | baselines B0/B1/B2 (S1) | fit TRAIN, scored CALIB | `python -m gramdrishti.verify.baseline_report`. TEST window opened: never |
| 2026-09-25 | provisional API forecast (S2) | fit TRAIN; applied to issued forecasts on the 8 demo dates | No scoring. The demo date picker reads issued forecasts in the TEST period, not outcomes. `/observed` displays TEST-period truth on request; no metric uses it. TEST window opened for evaluation: never |

## Handoff for the next session
S7 (detail panel): put the fan chart in the empty slot in `features/map/DetailPanel.tsx` (`useForecastPanchayat` is already loaded there), then "Why different?", "Forecast changed" and advisories. S9: enable `RiskLayerSelect` in `features/map/MapControls.tsx`; `RISK_TOKENS` in `lib/ramps.ts` maps levels to severity tokens, and `MapView` takes any Ramp. Reuse `components/DataTable.tsx` for priority and verification lists.

Merge order: S1, then S2 (S2 is stacked on S1).

Frontend (S3/S4): the contract is **frozen at v0.1.1**. Build from `contract/examples/` (see `contract/examples/index.json` for file -> endpoint -> model) and generate types from `contract/openapi.json`. Mock file names follow `forecast_panchayat_<id>.json`, `observed_panchayat_<id>.json`, `explain_<id>.json`, `forecast_changes_<id>.json`, `risk_<type>.json`, `farmer_<id>.json`; the main demo issue date is 2024-09-09. Show a notice when `provenance` is `placeholder`.

S4 (map explorer): the shell, store, URL sync and hooks exist. Replace `MapPlaceholder` in `frontend/src/pages/MapPage.tsx` with MapLibre (`useGeoPanchayats`, `useGeoBlocks`, `useForecastMap`); controls and `viewMode` are already wired. Add `lib/ramps.ts` and the legend. Consider collapsing the controls on phones. Keep `PanchayatPicker` as the keyboard route, and add the table view.

Backend S5: models replace `provisional/forecast.py`. Keep `Service.table()`'s columns (`<var>_p10/p50/p90/block`) or change the builders in `api/service.py`. S6 snapshots should cover the dates in `demo_dates.json`. S8 replaces `_generate_advisories` and the in-memory store. S10 replaces `provisional/placeholders.py` and sets `provenance: "computed"`.

## Handoff S5 (2026-09-26, stopped at usage limit)
Branch `session-05-model-core` (worktree `../GramDrishti-s05`, from `origin/main`). Done and committed: `features/` (`make_table`), `models/{downscale,reconcile,conformal,humidity,artifacts}.py`, `pipeline/{predict,train}.py`, tests (`test_features.py`, `test_reconcile_conformal.py`, `test_model_core.py`), decisions D036-D045.
Verified here: ruff clean; new tests 22 passed (features + reconcile/conformal 15, model core 7). A 40-tree run of `python -m gramdrishti.pipeline.train --trees 40 --no-save` completed (not the final model): CALIB out-of-time MAE vs B1 was rain -9.1 % (does NOT beat B1), tmax +9.8 %, tmin +0.8 %, rh +2.0 %, wind +1.3 %; coverage after calibration 0.71-0.99 by group, rain on wet days only 0.47-0.81; isotonic calibration made Brier worse than raw in 6 of 8 half-splits; block consistency ~1e-14; constraint violations 0.
Not done: the full 400-tree `--lobo` run was still running at the stop, so there are no final numbers or artifacts. Full `pytest -q` was not run. PROGRESS/CLAUDE.md commands are not updated beyond this note. No PR yet.
Next: rerun `cd backend && python -m gramdrishti.pipeline.train --lobo`, paste the report here, run `pytest -q`, add the train command to CLAUDE.md, decide on isotonic (D043 note) and the rain interval, then push and open the PR.
Hypothesis for rain (measured on TRAIN truth): only 26 % of within-block rain variance is a persistent Panchayat x month offset, against 89-92 % for Tmax/Tmin/dew point and 70 % for wind, so rain placement inside a block is mostly day-to-day noise.
