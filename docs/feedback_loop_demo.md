# Feedback loop demo: 2023-08

**Demo of the feedback loop, not a result.** Synthetic data (`data_mode: mock`): the reports are
generated (about 88 % correct by construction) and the truth is synthetic. Nothing here retrains or
adjusts a model, and the forecast is not scored.

Generated 2026-09-27 by `python -m gramdrishti.verify.feedback_report --month 2023-08`.
Rain counts as "yes" from 1 mm a day. Intensity classes for this check: none under 1 mm, light
1 to 10 mm, moderate 10 to 35 mm, heavy 35 mm or more (placeholder bins, not IMD categories).

## District

| Item | Value |
|---|---|
| Reports this month | 40 (0 from the API, 40 from the mock file) |
| Reports checked against station or synthetic truth | 40 |
| Rain yes/no agrees with what happened | 92% (37 of 40) |
| Intensity class agrees | 98% (39 of 40) |
| Checked against a station | 22% (9 of 40) |
| Panchayats with a station rain value this month | 24 of 90 |
| Panchayats with at least one report | 33 of 90 |
| ... of which have no station | 24 |
| Panchayats with any ground check (stations, plus reports) | 24 -> 48 of 90 |

## What this shows

Stations give a ground check in 24 of 90 Panchayats. This month's reports add 24 Panchayats without a station. Reports can be
wrong, so the check against station or synthetic truth comes first: it says how far a report
can be trusted before it is used to judge a forecast. With real reports the truth would be the
station network only, and reports from Panchayats without a station would stay unchecked.

Next step, not done here: the verification job could score rain occurrence at report points,
weighted by this agreement rate, to see the forecast where no station exists.

## Per Panchayat

| Panchayat | Block | Station | Reports | Checked | Rain agrees | Intensity agrees | Truth source |
|---|---|---|---|---|---|---|---|
| MP0102 | MB01 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0105 | MB01 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0111 | MB01 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0113 | MB01 | yes | 1 | 1 | 1 | 1 | station |
| MP0201 | MB02 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0203 | MB02 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0209 | MB02 | no | 2 | 2 | 2 | 2 | synthetic_truth |
| MP0212 | MB02 | yes | 1 | 1 | 1 | 1 | station |
| MP0215 | MB02 | yes | 1 | 1 | 1 | 1 | station |
| MP0301 | MB03 | yes | 1 | 1 | 1 | 1 | station |
| MP0303 | MB03 | no | 3 | 3 | 2 | 3 | synthetic_truth |
| MP0305 | MB03 | yes | 1 | 1 | 1 | 1 | station |
| MP0306 | MB03 | no | 2 | 2 | 2 | 2 | synthetic_truth |
| MP0307 | MB03 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0309 | MB03 | no | 2 | 2 | 2 | 2 | synthetic_truth |
| MP0310 | MB03 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0312 | MB03 | yes | 1 | 1 | 1 | 1 | station |
| MP0313 | MB03 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0314 | MB03 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0316 | MB03 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0402 | MB04 | no | 2 | 2 | 2 | 2 | synthetic_truth |
| MP0404 | MB04 | no | 1 | 1 | 0 | 0 | synthetic_truth |
| MP0405 | MB04 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0406 | MB04 | yes | 1 | 1 | 1 | 1 | station |
| MP0411 | MB04 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0501 | MB05 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0505 | MB05 | yes | 1 | 1 | 1 | 1 | station |
| MP0506 | MB05 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0508 | MB05 | yes | 1 | 1 | 1 | 1 | station |
| MP0509 | MB05 | no | 2 | 2 | 2 | 2 | synthetic_truth |
| MP0609 | MB06 | no | 1 | 1 | 1 | 1 | synthetic_truth |
| MP0612 | MB06 | no | 1 | 1 | 0 | 1 | synthetic_truth |
| MP0613 | MB06 | no | 1 | 1 | 1 | 1 | synthetic_truth |

Few reports per Panchayat in a month (40 in 33 Panchayats): per-Panchayat agreement rates would be noise, so the table shows counts only.
