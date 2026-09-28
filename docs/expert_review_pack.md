# Expert review pack

For an agrometeorologist or agronomist at a Krishi Vigyan Kendra (KVK) or state agricultural university (SAU). About one hour of reading.

**What GramDrishti is.** A student prototype for Smart India Hackathon 2026 (problem SIH26074). It turns a block-level weather forecast into Panchayat-level forecasts and drafts crop advice from fixed rules. An agriculture officer approves or edits every piece of advice before a farmer sees it. **All data is synthetic** (a made-up district); nothing here is about a real place.

**Why we need you.** Every threshold in the rules was chosen by us as a placeholder. The app marks all advice "pending expert review" until someone qualified has checked the numbers. We have not asked any expert before you, and we will not name you or your institution anywhere without your written permission.

## What to review

| # | What | File | What we ask |
|---|---|---|---|
| 1 | Advisory thresholds | [thresholds_for_expert_review.md](thresholds_for_expert_review.md) | Section 1: 15 rules with 21 thresholds (sowing, irrigation, spray, fertiliser, heat, frost, waterlogging, dry spell, harvest, pest and disease, livestock). For each row, write your value (or "ok") and a source. Say if a rule should not exist or is missing. |
| 2 | Spray planner, risk levels, confidence | same file, sections 2 to 4 | Whole-day spray ratings (good, caution, avoid) from rain chance and wind; the cut-offs for low to severe risk. Our data is daily, so we give no hour-level spray windows. |
| 3 | Crop calendar | same file, section 5, from `data/crop_calendar_PLACEHOLDER.csv` | Stages in days after sowing, heat and cold alert temperatures per stage, drought and waterlogging sensitivity, for bajra, cotton, mustard, paddy and wheat. Gram is grown in the mock data but has no calendar rows. |
| 4 | Farm-variable settings | same file, section 6 | Runoff, crop coefficients, waterlogging and frost thresholds, the fog proxy, crop base temperatures. |
| 5 | Advisory wording | `backend/gramdrishti/advisory/templates.yaml`; to see it in context, the Review screen of the running app | Is the action clear and safe? Is the reason right? Is the fallback ("if things change") sensible? English first; Hindi and Punjabi are drafts for a native speaker. |
| 6 | Hindi and Punjabi terms (optional) | [translation_notes.md](translation_notes.md) | Farm words we were unsure of, for example पलेवा / ਰੌਣੀ (pre-sowing irrigation), पाला / ਕੋਰਾ (frost), ਵੱਤਰ (workable soil moisture). |

Two open questions from the team:
- Should livestock heat advice go to every Panchayat, or only where animals are kept? On hot monsoon days it currently fires in all 90 Panchayats.
- Which cotton does the district grow (ਨਰਮਾ or ਕਪਾਹ in Punjabi text)?

Useful to know while reviewing: probabilities are written 0 to 1 (0.35 means 35 %); "upper estimate" is the forecast's 90th percentile (p90), "lower estimate" its 10th (p10); rain in mm, temperature in C, wind in km/h.

## How to send comments

1. Fill in the **Expert value** and **Source** columns of `thresholds_for_expert_review.md` (a copy, a printout or a spreadsheet is fine). A source can be a publication, a KVK or SAU recommendation, or "expert judgement".
2. Write any other comments (rules to add or remove, wording, calendar) as a numbered list, each pointing to a rule name or a row.
3. Send both to the team contact: [team contact to be filled in by the team], or open an issue on https://github.com/joshi-mishita/GramDrishti with the title "Expert review".

## What the team does with your comments

- Copies each value into `backend/gramdrishti/advisory/rules.yaml` or the crop calendar, fills the rule's `source`, and changes that rule's `thresholds_status` from `placeholder` to `reviewed`.
- Regenerates the thresholds table and the example files, and runs the tests (one test per rule checks that it fires and does not fire when it should not).
- Records each change and who asked for it in `docs/DECISIONS.md`.
- Sends you the list of what changed. Rules you did not review stay marked "placeholder".
