# Known issues (S17 bug bash, v1.0-demo)

Found on 2026-09-28 by the final QA run. The run covered the fresh-clone Docker check, the demo script in headed Playwright on an isolated Docker stack, and a sweep of 15 routes × 3 languages × 2 widths (90 page loads). The sweep recorded console errors, failed requests, sideways scroll, clipped buttons, broken internal links (114 checked) and English text on Hindi and Punjabi screens. The API-down and offline checks, screenshot read-through and time-zone checks also fed in. Evidence is in [integration_checklist.md](integration_checklist.md).

Severity:
- **High**: breaks or misleads during the demo.
- **Medium**: visible in the demo, contradicts a project rule or a document, or undermines the demo's backup plan.
- **Low**: cosmetic, outside the demo path, or already explained on screen.

Every high and medium issue is fixed or has a tested procedure. None was high; 8 were medium.

Sweep totals: 0 console errors or warnings on 90 page loads; 0 broken internal links; ribbon present on every page; no page-level sideways scroll; no clipped button text.

## Medium, fixed in S17

| Id | Issue | Where | Fix | Checked |
|---|---|---|---|---|
| M1 | Demo e2e step 5b looked for "Did it rain today?" on farmer Today, but the card is on Forecast and My farm, so the step was skipped. B4 items 11 and 13 had no browser evidence. | `frontend/e2e/demo-script.spec.ts` | Step 5b now taps Listen and checks the API's audio answer. Step 5c answers the rain question on Forecast. `scripts/e2e_docker.sh` reads the tapped row back from SQLite. | `make e2e`: 9 passed, row `(1, 'MP0307', '2024-09-09', 1, 'heavy', 'app')` |
| M2 | The spray "Caution" help text said "Spray only in the calm early morning", a time of day that daily data cannot support (CLAUDE.md rule 9), next to the note "Spray ratings are for the whole day, not for hours". It showed on farmer Forecast and on the bulletin. | `frontend/src/i18n/{en,hi,pa}.json` `sprayHelp.caution` | Now "Check wind and rain before you spray", with Hindi and Punjabi drafts added to `translation_notes.md` for native review (D171). | 233 frontend tests; screen text read |
| M3 | The map's Panchayat picker cut the name to "Synthetic Panchayat MP030" at 1366 px, in the demo's step 2. | `frontend/src/styles/pages.css` | Controls column 232 → 244 px. The longest name (168 px) now has 173 px. | Measured in en, hi, pa at 1366x768; no sideways scroll |
| M4 | `demo_script.md` and `docker.md` said the live app needs "about 30 s of retries" to show its error when the API is down. Measured: 1.4 to 1.5 s. | docs | Both corrected. | API stopped on the demo stack; map, farmer, verification |
| M5 | On a clean demo database nothing is approved, so the offline copy's farmer screen says "No advice for your crops today" on 9 Sep. If the API died before step 4, the backup could not show the farmer step. | demo procedure | Before the demo, approve MP0311's two bajra advisories (farmer F002, Punjabi) and run `make offline`. Step 4 only edits MP0307, so the live walk-through is unchanged. Added to `demo_script.md` and `demo_day_checklist.md` (D172). | Snapshot bundle with MP0311 approved: F002 shows harvest plus 1 more, 0 API requests |
| M6 | Two `make e2e` runs at once (two worktrees) shared the compose project, host ports and image tags. In S17 they overlapped: one stopped the other's API, and a second `prepare` crashed on the half-written `snapshot.tmp`. Separately, the offline Playwright run wiped the demo-script run's output, so its videos were lost. | `scripts/e2e_docker.sh`, `docker-compose.yml`, `playwright.docker.config.ts` | `E2E_PORT_PREFIX` and `GRAMDRISHTI_IMAGE_TAG` (with the existing `E2E_PROJECT`) isolate a run. Each Playwright run writes its own output folder. `E2E_HEADED`, `E2E_VIDEO` and `E2E_SLOWMO` were added for rehearsal recordings (D173). | Isolated rerun passed; 13 videos kept |
| M7 | nginx turned every 503 from the API into `not_available` "The API is not reachable", including the API's deliberate `not_computed`. On a fresh clone or in CI (a model with no verification record), the verification and impact screens blamed the network instead of saying "not computed", and a missing forecast snapshot was hidden the same way. It also made the S16 pull request's Docker CI job fail at demo step 6. | `frontend/nginx/default.conf.template` | Only nginx's own 502 and 504 go to the "not reachable" answer (D175). | Reproduced in a fresh clone without a model (step 6: expected `not_computed`, received `not_available`). After the fix, the demo stack gives verification 200 through the proxy, and a stopped API still gives 503 `not_available`. Fresh-clone e2e rerun: see `integration_checklist.md`. |
| M8 | `integration_checklist.md` was the S14 record and said S13 was not merged (2 items failing). | docs | Rewritten from the S17 run: 14 pass, 1 partly. | this file's evidence |

## Low, open

| Id | Issue | Where | Note |
|---|---|---|---|
| L1 | ~~With the API down, the live app (8080) shows its error state without the mock ribbon.~~ **Fixed in S18:** the ribbon is hidden only once a response says "real" (D178). | shell | Checked with the API unreachable: ribbon at 0.6 s and on the error state. |
| L2 | Detail panel: "103.8 mm", block "105.8 mm", "Difference from block -1.9 mm". The difference is computed from unrounded values, so the displayed numbers do not subtract exactly. | detail panel | If asked: rounding. |
| L3 | English API text on Hindi and Punjabi screens: the truth source inside the verification method sentence ("synthetic Panchayat truth (mock data generator)"), demo date reasons in the issue date menu, impact rules, verification notes, review evidence rows. All are marked `lang="en"`. | API texts | From S11 and S15. Everything else English on those screens is a name (product, synthetic Panchayats and stations, model id). |
| L4 | The spray-hold fallback says "If the day turns out dry and calm, you can spray in the early morning." | `advisory/templates.yaml` | Conditional agronomic advice, not a forecast claim. The expert should confirm or reword; changing it changes advisory text and the examples. |
| L5 | Reliability note from the API prints "73800 forecasts." without a thousands separator; the tables print 73,800. | verification | API note text. |
| L6 | Dev server only: React StrictMode's double mount aborts one `/meta` request per page (and some others). | `npm run dev` | The production build on the demo stack has no failed requests and no console messages. |
| L7 | On a network that is connected but reaches no internet, Listen waits up to gTTS's 10 s timeout before the 404 and the phone's voice. | audio | With no network at all gTTS fails at once (0.0 s measured). Tap Listen once before the demo to know which case you are in. From S12. |
| L8 | Two review filters changed in the same event-loop tick lose the first one. | review | Not seen with human input. From S16. |
| L9 | Farmer route LCP 3.17 s on Lighthouse's slow mobile profile. | farmer | From S15. |
| L10 | Open design items: "0 mm, likely about 0 mm" headline on dry days; verification page about 7,300 px tall; repeated "Why" text on heavy-rain days in Priority. | several | From S15 `design_review.md`. |
| L11 | Rain middle values (p50) are one value per block on 9 Sep, so the rain map barely changes between Block and Panchayat views. | model | Demo step 1 says so and switches to Max temperature. From S14. |
| L12 | Officer map at phone width: the controls filled the first screen. **Improved in S18:** view, risk layer and Panchayat picker fold into "More map options" below 768 px; the map starts at 546 px instead of 771 px on a 360x740 screen (D180). | map | Day and variable stay in view; the map is partly on the first screen, not all of it. |
| L13 | `docs/DECISIONS.md` has 25 ids used twice (D046 to D065, D080 to D086). | docs | Renumbering needs someone to decide which session keeps each id. From S15. |
| L14 | `click` 8.1.8 CVE-2026-7246 in the API image (gTTS pins `click<8.2`). | backend deps | `click.edit()` is unreachable (D127). |
| L15 | Node 25 on the build Mac, while `.nvmrc` says 22. Tests and the build pass on 25; Docker and CI use 22. | tooling | Use `nvm use` before `npm` commands on demo day. |

## Not checked in S17

- Firefox, Safari, a real phone, a screen reader, a projector.
- Turning Wi-Fi off on the laptop, and the phone-voice fallback heard by a person. These are the owner's rehearsals.
- A person new to the farmer app using it without instructions.

## Found and fixed in S18

| Id | Issue | Where | Fix | Checked |
|---|---|---|---|---|
| S18-1 | The printable bulletin in any snapshot build (the Docker offline copy on 8081 and the new public copy) said "No demo file for the approved advice": it asks `/advisories?panchayat_id=…&issue_date=…`, which the export never wrote. | `backend/gramdrishti/export_snapshot.py` | The export writes that request for every exported Panchayat and date (+720 files). | `tests/test_farmers.py`; bulletin of MP0307 on the Pages build shows the approved spray advice |
| S18-2 | Farmer rain read "Likely, 0 to 156 mm" when the most likely amount was 104 mm; dry days read "about 0 mm". | `frontend/src/features/farmer/forecastText.ts` | "Likely, about 104 mm, could reach 156 mm"; dry days give only the chance word (D179). | `forecastText.test.ts`, screen text |
