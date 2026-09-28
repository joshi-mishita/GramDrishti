# Demo day checklist

For the SIH 2026 demo of GramDrishti `v1.0-demo`. The walk-through itself is in [demo_script.md](demo_script.md); this page is everything around it. Everything shown is synthetic mock data: say "Synthetic demo data. Not real weather." once, early.

## The day before

| Done | Step | Command or detail |
|---|---|---|
| [ ] | Demo laptop on the tagged commit | `git fetch --tags && git checkout v1.0-demo` (a detached HEAD is fine; nothing is committed on demo day) |
| [ ] | Verified model present | `backend/artifacts/config.json` says `"model_version": "s5-lgbm-9b632a7b1b"`. Without it the verification and impact screens say "not computed" (D122). |
| [ ] | Docker VM running with room | `colima start --cpu 4 --memory 8 --disk 40` (or Docker Desktop). `docker info` answers. |
| [ ] | Stack up | `make up`: about 33 s when built, 7 to 8 min from nothing. Wait for its three addresses. |
| [ ] | Full rehearsal on the stack | [demo_script.md](demo_script.md), six-minute version, timed. Then a second one with Wi-Fi off (see "Network off" below). |
| [ ] | Reset the review database after rehearsing | `docker compose down && docker volume rm gramdrishti_state && make up` (about 40 s). MP0307's bajra advisories are drafts again. |
| [ ] | Backup farmer has advice | After the reset, approve MP0311's two bajra advisories (`http://localhost:8080/review?date=2024-09-09&block=MB03&crop=bajra`, Harvest and Irrigation), then `make offline` (1 to 2 min). The offline copy then shows Demo farmer 2 (F002, Punjabi) with advice. Leave MP0307 as drafts for the live step 4. |
| [ ] | USB copy made | see "USB copy" below. Check it opens on a second machine. |
| [ ] | Bulletins printed | see "Printed bulletins" below. |
| [ ] | Charger, adapters, phone hotspot charged | see "Power and network". |

## Laptop setup (30 minutes before)

1. Plug in the charger. Turn off sleep: `caffeinate -dimsu &` in a spare terminal (stop with `kill %1` afterwards). Turn off notifications (Focus: Do Not Disturb).
2. `colima start` (if the laptop restarted), then `make up` in the repository. Leave that terminal open.
3. Chrome, one window, 1366x768 or larger, zoom 100 %:
   - Tab 1: `http://localhost:8080/map?date=2024-09-09` (live app).
   - Tab 2: `http://localhost:8081/map?date=2024-09-09` (offline copy, the backup).
   - Tab 3: `docs/validation_report.md` on GitHub (backup for the verification screen).
4. A second Chrome window for the farmer view at 360 px wide: `http://localhost:8080/farmer?date=2024-09-09`, or DevTools device toolbar at 360 x 740.
5. Check, in this order (1 minute):
   - The ribbon "Synthetic demo data. Not real weather." shows on the map.
   - `http://localhost:8080/verification` shows numbers (rain MAE 1.070 for the model), not "not computed".
   - `http://localhost:8080/review?date=2024-09-09&block=MB03&crop=bajra` lists MP0307 twice under "Waiting for review".
   - The farmer window shows the Hindi text after tapping हिन्दी.
6. Projector: mirror the display, and check the map colours are readable from the back row. If the projector is below 1366x768, zoom Chrome to 90 %.

## Ports

| Port | What | Needed for |
|---|---|---|
| 8080 | Officer console and farmer app (nginx, proxies `/api` to the API) | the demo |
| 8081 | Offline copy (snapshot mode, never calls the API) | the backup |
| 8000 | API and its docs (`/docs`) | questions about the API only |

All bind to 127.0.0.1. If another program holds a port, set `WEB_PORT`, `OFFLINE_PORT` or `API_PORT` in `.env` (copy `.env.example`) and run `make up` again. Check with `lsof -nP -iTCP:8080 -sTCP:LISTEN`.

## Commands on the day

| When | Command |
|---|---|
| Start | `make up` |
| Status | `make ps` (all three services "healthy"), `make logs` |
| API stopped answering | switch to tab 2 (port 8081) and carry on; then `docker compose start api` (healthy in about 10 s) |
| Everything is down | `make down && make up` (about 33 s); meanwhile show `docs/screens/after/` or the README |
| After approving advice, before showing the offline copy | `make offline` |
| Reset reviews between two presentations | `docker compose down && docker volume rm gramdrishti_state && make up` |
| Never on the day | `make clean` (deletes the verified model's volume; the next `make up` retrains and verification says "not computed") |

## Power and network

- Power: charger plus a spare. The stack runs on battery for a whole demo but Colima uses about 8 GB of memory; close other apps.
- The demo needs no internet. The only thing that uses it is the Listen button's server audio (gTTS). Without internet the API answers 404 after about 10 s and the app uses the laptop's own voice (Hindi exists on the team's Mac, Punjabi does not). If there is no voice, read the advice aloud.
- Keep a phone hotspot as a backup network, but prefer demoing offline: it removes the 10 s wait on Listen. With Wi-Fi off, tap Listen once before the demo so you know which case you are in.
- Network off rehearsal: turn Wi-Fi off, reload both tabs, walk the whole script. Everything except server audio should work: the stack runs on localhost, and S17 checked the API-down case and the offline copy with no API requests ([integration_checklist.md](integration_checklist.md)). S17 did not turn Wi-Fi off; that is the owner's rehearsal. Note what happens on Listen.

## USB copy (backup laptop or a borrowed one)

Make it the day before, on the demo laptop, from the repository root:

```bash
git bundle create /Volumes/USB/gramdrishti-v1.0-demo.bundle v1.0-demo
tar -czf /Volumes/USB/gramdrishti-artifacts.tgz backend/artifacts
docker compose cp web-offline:/srv/offline/snapshot /Volumes/USB/snapshot
```

The last line copies the stack's own offline export (21,969 files, 105 MB, about 8 s in S17), so the USB holds the same approvals as port 8081.

- `git clone gramdrishti-v1.0-demo.bundle GramDrishti` restores the code without internet.
- `tar -xzf gramdrishti-artifacts.tgz` inside the clone restores the verified model, so `make up` does not retrain and verification shows numbers.
- `snapshot/` is the offline export. On a machine without Docker: `cd frontend && npm ci && VITE_SNAPSHOT=1 npm run build && npx vite preview --port 8081`, after copying `snapshot/` to `contract/snapshot/`. That needs Node 22 and an `npm ci` (internet) once.
- Docker images are not on the USB (1.4 GB). A borrowed laptop needs Docker and internet for the first build, about 8 minutes.
- Also copy `docs/screens/after/` and the PDF of the presentation.

## Printed bulletins

Print from the live app after approving the demo advisories, in Chrome (Print, A4, margins default, background graphics off). Each fits one page.

| Copies | Page |
|---|---|
| 3 | `http://localhost:8080/bulletin/MP0307?date=2024-09-09&lang=hi` (Hindi, the farmer in the demo) |
| 3 | `http://localhost:8080/bulletin/MP0311?date=2024-09-09&lang=pa` (Punjabi, the same-block neighbour) |
| 2 | `http://localhost:8080/bulletin/MP0307?date=2024-09-09&lang=en` (English, for the jury) |

Every printed page carries the mock notice in its footer; do not hand out a page without it. The Hindi and Punjabi texts are team drafts awaiting native review; say so if asked.

## Who says what

Roles from the Backend Guide B6 and [demo_script.md](demo_script.md): the frontend person drives the screens, the backend person explains model, uncertainty and validation.

| Time | Screen | Drives | Speaks |
|---|---|---|---|
| 0:00 to 1:00 | Map, block against Panchayat | frontend | frontend (the problem), backend (rain tie, temperature detail) |
| 1:00 to 2:00 | MP0307 panel, review of MP0307 and MP0311 | frontend | backend (range, chances), frontend (same block, different advice) |
| 2:00 to 2:30 | Show what happened | frontend | backend (synthetic truth, not a measurement) |
| 2:30 to 3:30 | Review, edit, approve, audit | frontend | frontend |
| 3:30 to 4:30 | Farmer phone, Hindi, Listen, rain report | frontend | frontend |
| 4:30 to 5:20 | Verification, "Where the model does not help" | frontend | backend |
| 5:20 to 5:45 | Impact, spray and heat alert | frontend | backend |
| 5:45 to 6:00 | Mock to real | nobody | backend |

Questions: the backend person takes model, data and validation; the frontend person takes app, languages, offline and accessibility. Answers come from [qna.md](qna.md). If a question needs a number that is not in the verification report, say you do not have it.

## Timing

- Six-minute version: the table above. Hold a phone stopwatch; at 4:30 skip to Verification whatever is on screen.
- Two-minute version: [demo_script.md](demo_script.md), "Two-minute version".
- Over time at 5:00: skip Impact, go straight to the close.
- Buffer: arrive 45 minutes early. Setup takes 30 minutes including one quick click-through.

## If something breaks

The failure table in [demo_script.md](demo_script.md#if-something-breaks) has the steps and the words. The short version: API gone, use tab 2 (port 8081); verification "not computed", show the validation report on GitHub; map blank, use "Show as table"; no sound, read it aloud.
