# Demo script

The six-minute walk-through from Backend Guide Appendix B7, with exact clicks, dates and words, then a two-minute version, then what to do when something breaks. Every screen shows "Synthetic demo data. Not real weather." Say it out loud once, early, and never let a number sound like a real-world result.

The clicks below were walked through on 2026-09-28 against the S16 branch (API plus the dev frontend on the real endpoints, 1366x768 and 360x740). The same steps are automated in `frontend/e2e/demo-script.spec.ts` (`make e2e`).

Roles (Guide B6): the frontend person drives the screens; the backend person explains model, uncertainty and validation.

## Before the demo

1. `make up` on the demo laptop (about 33 s when everything is built; 7 to 8 minutes on a machine with nothing built). It prints three addresses. Leave the terminal open.
2. Open `http://localhost:8080` in Chrome at 1366x768 or larger. Open a second tab on `http://localhost:8081` (the offline copy) and leave it there.
3. Check the verification screen shows numbers, not "not computed". It needs the verified model `s5-lgbm-9b632a7b1b` in `backend/artifacts/` (a fresh clone trains a different version, DECISIONS D122).
4. Check MP0307 still has draft bajra advisories: `http://localhost:8080/review?date=2024-09-09&block=MB03&crop=bajra` lists MP0307 twice under "Waiting for review". If a rehearsal approved them, see "Reset after a rehearsal" at the end.
5. Phone view: Chrome DevTools device toolbar at 360 px, or a second window narrowed to phone width.
6. Internet on or off: with internet the API makes the audio (gTTS); without it the app falls back to the laptop's own voice (Hindi worked on the team's Mac; there was no Punjabi voice).

## Six-minute version

### 1. Map: block forecast against Panchayat forecast (0:00 to 1:00)

Clicks:
- Issue date menu (top bar): **Mon 9 Sep 2024 · Heavy monsoon rain**. Left menu **Map**.
- Under **Show** pick **Rain**; under **View** pick **Block**. Each block is one flat colour.
- Under **View** pick **Panchayat**. For rain on this date the colours barely change.
- Under **Show** pick **Max temperature**. Now the Panchayats inside each block differ.

Say:
- "This is a synthetic district: 6 blocks, 90 Panchayats. Today a farmer gets the block number, one colour for the whole block."
- "For rain, our Panchayat middle value is the same as the corrected block forecast here. That is honest: on the test period our rain model does not beat the corrected block forecast, and the map shows it."
- "For temperature it does add detail: irrigated Panchayats come out cooler, the pattern planted in the synthetic data. Temperature is where the model beats the corrected block forecast on the test period."

### 2. Two Panchayats in the same block (1:00 to 2:00)

Clicks:
- Back to **Show: Rain**. Panchayat picker (bottom of the left column): **Synthetic Panchayat MP0307**. The right panel opens: rain on Tue 10 Sep **103.8 mm, likely between 0 and 156.2 mm**, block forecast 105.8 mm, and a five-day chart with the shaded likely range.
- Scroll the panel to **Chance of rain**: heavy rain 35 mm or more, **possible, 48%**. Then **Why is it different from the block?** ("Lower ground than the rest of the block, so it is likely wetter").
- Left menu **Review**, then **Block: MB03**, **Crop: Bajra**. Click the MP0307 items, then the MP0311 items.

Say:
- "The range matters more than the middle number: 0 to 156 mm tomorrow. That is why the advice uses chances, not one number."
- "Same block, same crop, different advice. MP0307 is low-lying: clear the field drains, and do not spray on 10 September (82% chance of rain). MP0311's bajra is near harvest: harvest before the rain, and hold irrigation. Each card carries its reason and the numbers behind it."
- "These come from rules in a YAML file, not from a language model. Every threshold is a placeholder until a KVK or university expert reviews it; the card says so."

### 3. What really happened (2:00 to 2:30)

Clicks: left menu **Map**, picker **MP0307**, tick **Show what happened** under the chart.

Say: "This line is what happened. In this demo it is the synthetic truth from our data generator, not a measurement, and the screen says so."

### 4. Officer review and audit trail (2:30 to 3:30)

Clicks:
- **Review**, **Block: MB03**, **Crop: Bajra**, click **Synthetic Panchayat MP0307, Waterlogging**.
- In **Action**, add a sentence at the end, for example "Check the field drains before evening." Click **Save edit and approve**. The status changes to "Edited and approved" and the history shows the change and the reviewer name.
- Click **Synthetic Panchayat MP0307, Spray**, then **Approve**.

Say: "Nothing reaches a farmer until an officer approves it. Every edit is stored with before and after text and who did it. An English edit clears the Hindi and Punjabi text, and the screen says so, so a stale translation never goes out."

### 5. Farmer phone view (3:30 to 4:30)

Clicks:
- Top bar **Farmer** (or open `http://localhost:8080/farmer?date=2024-09-09`) at phone width. Tap **हिन्दी**.
- The Today screen shows the approved spray advice in Hindi for demo farmer 1 (MP0307). Tap **Listen** (सुनें).
- Bottom menu **Forecast** (पूर्वानुमान). Scroll to "Did it rain today (Mon 9 Sep)?", tap **Yes**, then **Heavy**. A thank-you line appears.

Say:
- "The farmer sees only approved advice, in their language, with audio for people who prefer to listen. The Hindi and Punjabi text are our drafts and still need a native speaker's review."
- "The rain report is stored with the Panchayat and date, no phone number. Today we use reports only to check forecasts, not to change them."

### 6. Verification (4:30 to 5:20)

Clicks: switch back to desktop width, **Officer**, left menu **Verification**. Scroll to **Where the model does not help**.

Say:
- "Test period July to December 2024, held out and opened once, recorded in a ledger. Three checks: held-out period, held-out block, stations."
- "Against the plain block forecast the model wins on all five variables. Against the corrected block forecast it wins on temperature, humidity and wind, by 1.9 to 5.1 percent, and ties on rain."
- "And here is where it does not help: rain on light and moderate rain days, poorly drained Panchayats, heavy-rain chances worse than climatology. We show losses as clearly as wins. All of this is synthetic proxy validation."

### 7. Impact (5:20 to 5:45)

Clicks: left menu **Impact**. **Decision: Spray**, **Period: Whole test period**. Then **Heat alert**.

Say: "Replaying the spray decision on every Panchayat and day: 554 unnecessary waits with the block forecast, 217 with ours, but more washed-off sprays, 179 against 68. For heat alerts ours raises more false alarms. Which trade-off is better depends on costs an expert has to give us; we do not pretend to know them."

### 8. Close: mock to real (5:45 to 6:00)

Say: "Everything you saw runs on synthetic data. The real-data path keeps the same API: stations first, then real block forecasts, validated leave-one-station-out. The plan is in `docs/mock_to_real_plan.md`."

## Two-minute version

1. (0:00) Map, 9 Sep 2024, **Max temperature**, toggle **Block** then **Panchayat**: "One number per block today; Panchayat detail with a likely range. Synthetic data."
2. (0:25) **Review**, **Block: MB03**, **Crop: Bajra**: MP0307 gets "clear the drains, do not spray", MP0311 gets "harvest before the rain". "Rules, not a language model. Nothing goes out without approval." Click **Approve** on MP0307 Spray.
3. (1:00) **Farmer** at phone width, **हिन्दी**: the approved advice in Hindi, **Listen**.
4. (1:25) **Verification**: "Wins over the plain block forecast on all five variables; ties on rain against the corrected block forecast; this list shows where it does not help."
5. (1:50) "Synthetic proxy validation. Real stations next, same API."

## If something breaks

| What happens | Do this | Say |
|---|---|---|
| The API stops answering (screens show "Could not load", after about 30 s of retries) | switch to the second tab, `http://localhost:8081`, and continue. It reads exported files and never calls the API. | "This is the offline snapshot mode, built for exactly this." |
| Offline copy does not show the approvals you just made | expected: it shows reviews as of its export. Show the farmer screen for a Panchayat approved in rehearsal, or skip step 4. Before the demo, `make offline` after rehearsing. | |
| Verification says "not computed" | the running model is not the verified version (D122). Show `docs/validation_report.md` on GitHub instead. | "The screen refuses to show numbers for a model that was not verified. Here is the report for the verified version." |
| Listen gives no sound | no internet (the API audio needs it) and no voice for that language on this laptop. Read the text aloud. | "On a phone the app uses the phone's own voice when there is no internet." |
| Map is blank | WebGL off or the tab needs a reload. Use **Show as table** on the map screen. | |
| Everything is down | `make down && make up` (about 33 s when built). Meanwhile show `docs/screens/after/` screenshots or the README. | |

Recovery commands: `docker compose start api` (the API alone, healthy in about 10 s), `make logs`, `make ps`.

## Reset after a rehearsal

A rehearsal approves MP0307's drafts, so step 4 has nothing left to approve. Options:

- Use another Panchayat of block MB03 in step 4 (the list shows every draft still waiting), or MP0311.
- Or clear the review database only, keeping the model and snapshots: `docker compose down`, `docker volume rm gramdrishti_state`, `make up`. The API seeds the five demo farmers again and writes new drafts on the first request for a date. This deletes every review and feedback report.
- `make clean` deletes everything, including the model; the next `make up` retrains and verification then says "not computed" unless the verified model is in `backend/artifacts/`.
