# Integration checklist (Backend Guide B4), S14

Checked on 2026-09-28 on the demo MacBook against the Docker stack (`make up`, model `s5-lgbm-9b632a7b1b`)
and the isolated e2e stack (`make e2e`). Branch `session-14-integration`, S13 not merged. Screenshot paths
are under `docs/screens/` (git-ignored: run `make e2e` to make them again). The full e2e log is
`docs/screens/s14-e2e-run.log`.

Result: **12 pass, 1 partly, 2 fail**. Both failures are farmer-app UI that S13 builds; they need a recheck
after S13 merges.

| # | Check | Owner | Result | Evidence |
|---|---|---|---|---|
| 1 | Every example JSON validates against its Pydantic model | Backend | Pass | `pytest -q tests/test_contract.py -k "example_validates or index_lists or every_path or lon_lat or openapi"`: 77 passed. CI job "Contract (openapi, types, examples)" runs the same. |
| 2 | openapi.json regenerated after last API change; types regenerated | Both | Pass | `python -m gramdrishti.export_openapi` then `git diff --exit-code contract/openapi.json`: no diff (S14 changed no response shape). `npm run check:types`: no diff. Both are CI steps now and fail the build on drift. |
| 3 | No NaN or Infinity anywhere in real responses | Backend | Pass | Sweep of the live Docker API: 275 requests (every GET in `contract/examples/index.json` plus `/forecast/map` for 8 dates × 5 variables × 5 lead days and `/forecast/panchayat/MP0307` for 8 dates), 4.4 MB, parsed with NaN and Infinity rejected: none. The only non-200 answers are the contract's deliberate error examples (422 lead day 9, 404 unknown Panchayat, 404 unknown date). |
| 4 | GeoJSON is [longitude, latitude]; map renders in the right place | Both | Pass | Same sweep: 748 coordinates, all longitude 68 to 98 and latitude 6 to 38. `tests/test_contract.py::test_example_geojson_is_lon_lat` passes. Map renders: `s14-1-map-block.png`, `s14-1-map-panchayat.png`, `s14-offline-map.png`. |
| 5 | All ISO dates, no time-zone shifts on the map slider | Frontend | Pass | Chrome with `timezoneId` America/Los_Angeles, Asia/Kolkata and Pacific/Kiritimati: day buttons "Tue 10 Sep" to "Sat 14 Sep" for API dates 2024-09-10 to 2024-09-14 in all three. `TZ=<each> npx vitest run`: 202 passed in each zone. |
| 6 | Panchayat quantile order p10 <= p50 <= p90 everywhere | Backend | Pass | Same sweep: 18,750 p10/p50/p90 triples, all ordered. Backend `test_reconcile_invariant_and_constraints_in_every_snapshot` passes. |
| 7 | Block mean of Panchayat values equals block value | Backend | Pass | `pytest -q -k "consisten or reconcil or block_mean"`: 12 passed, including `test_reconcile_invariant_and_constraints_in_every_snapshot` (1e-6). Full backend suite: 421 passed. |
| 8 | Mock ribbon visible on every screen when data_mode = mock | Frontend | Pass | Every e2e step waits for `.ribbon` (English text checked exactly in step 1; Hindi and Punjabi texts in `s14-farmer-hi-fonts.png`, `s14-farmer-pa-fonts.png`). Map, detail panel, review, farmer, verification, impact, offline copy: all pass. Known gap: with the API down the live app shows no ribbon, because no response has told it the data mode (the offline copy does show it). |
| 9 | Empty, loading and error states exist for each screen | Frontend | Partly | Map, priority, review, verification, impact, farmer Today and Farm use `QueryBoundary` (tests: `QueryBoundary.test.tsx` "shows a loading state first", "shows an actionable error and retries", "shows the empty state for an empty result"; `DetailPanel.test.tsx`; `PriorityPage.test.tsx`). Seen live: map error state with the API stopped (`s14-api-down.png`), farmer empty state before approval (`s14-farmer-pa-fonts.png`). Bulletin and farmer Forecast are still S3 placeholders (an empty state only) until S13. |
| 10 | Approve on officer screen changes what the farmer app shows | Both | Pass | e2e step 4 edits one MP0307 bajra advisory and approves another (audit trail: `s14-4-edited-audit.png`, `s14-4-approved-audit.png`); step 5a opens F001's farmer screen in Hindi and finds the approved Hindi action text (`s14-5-farmer-hi.png`). |
| 11 | Farmer feedback tap is stored and visible in database | Both | **Fail (UI)** | Backend half passes: `POST /feedback` through the web proxy answered `"stored":true`, id `FB-00001`, and SQLite returned `(1, 'MP0307', '2024-09-08', 1, 'heavy', 'app')` (`s14-e2e-run.log`). The tap itself: e2e step 5b is skipped because the "Did it rain today?" card is S13's and not in this build. |
| 12 | All three languages render (fonts loaded, no boxes) on the demo laptop | Frontend | Pass | Farmer screen in en, hi, pa at 360 px in Chrome: `document.fonts` shows Source Sans 3, Noto Sans Devanagari and Noto Sans Gurmukhi loaded, no request leaves the origin (self-hosted). Screens `s14-farmer-{en,hi,pa}-fonts.png`, no boxes. The issue-date label ("Heavy monsoon rain") stays English: it comes from the API. |
| 13 | Audio plays, or fallback to browser speech works offline | Both | **Fail (UI)** | Backend half passes: `GET /audio/ADV-2024-09-09-MP0307-bajra-spray?lang=hi` from the Docker API answered 200 `audio/mpeg`, 244,608 bytes (gTTS needs internet; without it the API answers 404 `audio_not_available`). The play button and the browser-speech fallback are S13's farmer app, not in this build. |
| 14 | Offline snapshot mode works if the API is killed | Frontend | Pass | `scripts/e2e_docker.sh` runs `docker compose stop api`, then `demo-offline.spec.ts`: API answers 503 `not_available`; the offline copy on 18081 shows the map, the MP0307 panel, the verification table and the farmer screen with zero `/api` requests; the live app shows its error state (4 passed). `s14-offline-map.png`, `s14-offline-farmer.png`, `s14-api-down.png`. |
| 15 | Verification numbers on screen equal artifacts/verification.json | Both | Pass | e2e step 6: every Model, B0, B1 and B2 cell of the comparison table equals `/verification/summary` within the shown rounding (for example rain MAE 1.070 / 1.240 / 1.031 / 1.032 against 1.07045 / 1.23993 / 1.03107 / 1.03153); `test_verification_endpoints_return_exactly_the_files_numbers` checks the endpoint returns the file. Step 7 does the same for the impact counts. `s14-6-verification.png`, `s14-7-impact.png`. |

## To recheck after S13 merges

1. Merge `main` into `session-14-integration`, `make up`, `make e2e`: step 5b must pass (not skip).
2. Items 11 and 13 in the browser: tap "Did it rain today?", then read the row back:
   `docker compose exec api python -c "import os,sqlite3; print(sqlite3.connect(os.environ['GRAMDRISHTI_DB']).execute('select * from feedback order by id desc limit 3').fetchall())"`.
   Play the audio with the network on, then off (browser speech).
3. Item 9 for the bulletin and farmer Forecast screens.
