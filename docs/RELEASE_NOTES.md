# Release notes: v1.0-demo

GramDrishti, SIH 2026 problem SIH26074: block-level weather forecasts downscaled to Panchayat level, turned into crop-stage advisories that an officer reviews before farmers receive them in English, Hindi and Punjabi.

**Everything in this release runs on synthetic mock data.** Every API response carries `data_mode: "mock"` and every screen shows "Synthetic demo data. Not real weather." No number in this release is evidence of skill on real weather.

| | |
|---|---|
| Tag | `v1.0-demo` (demo freeze, S17) |
| API contract | v0.4.0 (`contract/openapi.json`, [changelog](../contract/CHANGELOG.md)); every change since v0.1 was additive |
| Model | `s5-lgbm-9b632a7b1b`, trained on TRAIN (2023-01-01 to 2024-04-30), calibrated on CALIB (2024-05-01 to 2024-07-15), verified once on TEST ([ledger](test_window_ledger.json)) |
| Advisory rules | `backend/gramdrishti/advisory/rules.yaml` v1, 15 rules, `thresholds_status: placeholder` |
| Demo issue dates | 8, from 2024-01-12 to 2024-12-24; main date 2024-09-09 (heavy monsoon rain) |
| Licence | MIT |

## What is in it

- **Panchayat forecasts** for 90 synthetic Panchayats in 6 blocks, lead days 1 to 5: rain, maximum and minimum temperature, humidity and wind. The block forecast is bias-corrected, LightGBM models add Panchayat detail, and reconciliation keeps the block mean equal to the corrected block forecast. The largest gap is 1.4e-14, and a test enforces 1e-6.
- **Uncertainty**: 10th to 90th percentile ranges with conformal calibration, plus rain chances at 1, 2.5, 10 and 35 mm.
- **Reasons**: SHAP-based plain-English sentences on why a Panchayat differs from its block.
- **Advisories from YAML rules, never from a language model**: 15 rules in 11 categories, crop-stage aware, each with a reason, evidence, confidence and fallback. The spray planner works per whole day, never per hour.
- **Officer console**: map explorer (block, Panchayat and difference views, table view), detail panel with a fan chart and observed overlay, risk layer, priority list, review queue (approve, edit or reject), and an audit log with before and after text.
- **Farmer app** at phone width in three languages: Today, Forecast, My farm, Listen (server MP3 or the phone's voice), WhatsApp share text, the "Did it rain today?" report, offline use through a service worker, and a one-page printable bulletin.
- **Verification and impact**: a one-time TEST run against the raw (B0), corrected (B1) and station-adjusted (B2) block forecasts, with bootstrap intervals, three checks (held-out period, held-out block, stations), strata, event scores, reliability, coverage and decision replay. Losses are listed as plainly as wins.
- **One-command demo**: `make up` (Docker Compose: API, web, offline copy) and `make e2e` (the demo script in Playwright on an isolated stack, including the API-down case).
- **Offline insurance**: port 8081 serves the whole demo from exported responses (`VITE_SNAPSHOT=1`) and never calls the API.

## Results (synthetic proxy validation, TEST 2024-07-17 to 2024-12-31)

Mean absolute error skill with 95 % interval, temporal holdout. Source: [validation_report.md](validation_report.md).

| Variable | vs raw block B0 | vs corrected block B1 |
|---|---|---|
| Rain | +13.7 % (+4.0 to +27.9), better | -3.8 % (-8.1 to +0.8), **no clear difference** |
| Maximum temperature | +6.8 % (+5.1 to +8.4), better | +5.1 % (+3.8 to +6.6), better |
| Minimum temperature | +14.6 % (+13.2 to +16.2), better | +3.8 % (+2.1 to +5.5), better |
| Relative humidity | +5.3 % (+4.8 to +5.8), better | +4.2 % (+3.7 to +4.6), better |
| Wind | +36.2 % (+34.9 to +37.4), better | +1.9 % (+1.8 to +2.0), better |

Where it does not help: rain against B1 on light and moderate rain days and in poorly drained Panchayats. The 35 mm rain chance is worse than climatology. Maximum temperature intervals are too narrow, and wet-day rain coverage is about half. The heat-alert replay raises more false alarms than the block rule. Most of the gain over B0 comes from bias correction.

## Quality checks for this release (S17)

The full evidence is in [integration_checklist.md](integration_checklist.md) (Backend Guide B4, rerun in S17) and [known_issues.md](known_issues.md).

- Backend: 441 tests pass, ruff clean.
- Frontend: 233 unit tests pass; lint, type check against the contract and production build clean.
- Fresh clone with Docker (`scripts/fresh_clone_check.sh`, README quick start in a temp folder): 394 s, all 14 endpoint checks pass. Verification answers "not computed" there, as designed (D122).
- The demo script on Docker with the verified model (`make e2e`, headed Chrome with video): 9 of 9 steps passed; the tapped rain report was read back from SQLite; with the API stopped, 4 of 4 passed.
- The same e2e in a fresh clone with no model (CI conditions): 7 passed and 2 skipped as designed ("not computed"). It failed before the nginx fix in this release ([known_issues.md](known_issues.md) M7).
- B4 integration checklist: 14 pass, 1 partly.
- CI on GitHub: `main` is green at `db1f997`. The S16 pull request's Docker job failed on the nginx bug fixed here, and CI has not run on this branch yet.

## Freeze: what must not change before the demo

From the `v1.0-demo` tag until the demo, only the changes listed at the end of this section are allowed. Any other change means rerunning `make e2e`, the fresh-clone check and a rehearsal.

In git:

| Path | Why |
|---|---|
| `backend/gramdrishti/` (all code, including `advisory/rules.yaml`, `advisory/templates.yaml`, `verify/records/s5-lgbm-9b632a7b1b/`) | The verified model's code path, the rules and the texts the demo script quotes |
| `backend/pyproject.toml`, `backend/requirements.lock`, `backend/Dockerfile` | Library versions the verification record is valid for (D121, D122) |
| `data/` (mock data and generator) | The data hash is part of the model version |
| `contract/openapi.json`, `contract/examples/` | Contract v0.4.0, and the frontend's generated types |
| `frontend/src/`, `frontend/package-lock.json`, `frontend/Dockerfile`, `frontend/nginx/`, `frontend/public/` | The screens the demo script clicks through |
| `docker-compose.yml`, `Makefile`, `scripts/demo.sh`, `.env.example` | The one-command start and its ports |
| `docs/test_window_ledger.json`, `docs/validation_report.md`, `docs/model_card.md` | Numbers shown to the jury; `docs_check` ties them to the record |
| `docs/demo_script.md`, `docs/demo_day_checklist.md` | What the presenters rehearsed |

Not in git, on the demo laptop:

| What | Why |
|---|---|
| `backend/artifacts/` (model `s5-lgbm-9b632a7b1b`) | Without it the verification and impact screens say "not computed" (D122) |
| Docker volumes `gramdrishti_artifacts`, `gramdrishti_offline`, `gramdrishti_oracle` | Model, snapshots and the offline export; `make clean` deletes them |
| Docker images `gramdrishti-*:local` built from the tag | A rebuild from another branch replaces them (D173) |

Allowed during the freeze: `docs/PROGRESS.md`, `docs/known_issues.md` (new findings), this file, typo fixes in documents without numbers, and resetting the `gramdrishti_state` volume as the demo script describes.

## Known limitations

- Synthetic data only. No real data source is connected and there is no data-sharing agreement with any organisation.
- Every advisory threshold and agro constant is a placeholder until a KVK or agricultural university expert reviews it ([expert_review_pack.md](expert_review_pack.md)).
- Hindi and Punjabi texts are team drafts needing native review. Panchayat names and some API texts stay English.
- Only the 8 demo issue dates are precomputed. No login: the reviewer name is free text.
- Not tried on a real phone, in Firefox or Safari, or with a screen reader.
- A fresh clone trains a different model version on another machine, so its verification screen says "not computed"; the verified numbers are in the report.
- Open issues with severity: [known_issues.md](known_issues.md).

## Needed from the team or outside

- Expert values and sources for the thresholds, and costs for a washed-off spray, a wasted wait and a missed heat alert.
- Native Hindi and Punjabi review of the UI, advisory templates and bulletin.
- A decision on how to serve rain, for example corrected block amounts with the model's rain chances. That would be a new model version, and TEST would be reported as reused.
- Branch protection on `main`.
