# Presentation outline

Fourteen slides for the jury. Each has one main message and what to put on it. **No statistic appears on a slide unless it is in this outline with its source**; there are no real-world figures in this project, so the problem slides use reasons and the synthetic example, not national numbers. If you want a real-world figure (for example how many farmers get block advisories), find a citable source first and add it here with the reference.

Every slide with a number or a screenshot carries the footer "Synthetic demo data. Not real weather."

Screenshots: `docs/screens/after/readme-*.png` (committed), or regenerate the full sets with `cd frontend && SHOTS_SET=after npm run shots`.

| # | Slide | Main message | What to show |
|---|---|---|---|
| 1 | Title | GramDrishti: Panchayat-level forecasts and reviewed crop advice from block forecasts. SIH 2026, problem SIH26074. | Product name, one-line description, team name, "Synthetic demo data" footer. |
| 2 | Problem | Agromet advice is issued per block, but the decisions it drives (spray, irrigate, drain, harvest) happen field by field. | The problem statement text. A block outline with its Panchayats inside. No numbers. |
| 3 | Why block level fails | Inside one block, rain, temperature and drainage differ; one number gives everyone the same advice. | The synthetic example from the demo: block MB03 on 9 Sep 2024, MP0307 (low-lying) should clear drains and hold spraying, MP0311 (bajra near harvest) should harvest before the rain. Say it is synthetic. |
| 4 | Solution flow | Block forecast, bias correction, Panchayat downscaling with a range, reconcile to the block, farm variables, rule-based advice, officer review, farmer in three languages, verification against the block forecast. | The Mermaid flow from the README, redrawn as one row of boxes. |
| 5 | Data | Today everything is synthetic: 6 blocks, 90 Panchayats, 24 stations, two years. The same columns take real data later. | Table from [data_card.md](data_card.md): mock file on the left, intended real source on the right, each marked "to be verified". State: no data agreement exists. |
| 6 | Method | LightGBM predicts each Panchayat's departure from the corrected block forecast using terrain, land cover, soil, satellite and recent rain. | Feature groups (55 features) and the four model outputs: mean, p10, p50, p90, plus rain chances. One SHAP reason sentence as an example. |
| 7 | Uncertainty | Every forecast has a likely range, calibrated on a separate window, and Panchayats always average back to the block (largest gap 1.4e-14 on the test period). | The fan chart from the detail panel (MP0307, 0 to 156 mm on 10 Sep). Coverage honestly: 78 % to 90 % for the 80 % range, 51 % for rain on wet days ([model_card.md](model_card.md)). |
| 8 | Advisory engine | Advice comes from readable YAML rules with placeholder thresholds, not from a language model; each card has reason, evidence, confidence and a fallback. | One rule from `rules.yaml` next to the card it produces. The "Thresholds pending expert review" label. |
| 9 | Officer review and farmer | Nothing reaches a farmer until an officer approves it; the farmer sees it in Hindi, Punjabi or English, can listen, share, and report rain. | Review screen with the audit trail; farmer Today screen in Hindi at phone width; the printed bulletin. |
| 10 | What makes it different | Honest by design: the block forecast is the baseline, losses are shown as clearly as wins, and advice needs a human to approve it. | Three short points: beats the plain block forecast on the test period; says where it does not help; every advisory reviewed and audited. Avoid "first", "only" or "best" unless you can prove it. |
| 11 | Validation | On the held-out test period the model beats the raw block forecast on all five variables; against the corrected block forecast it wins on temperature, humidity and wind and ties on rain. Proxy validation on synthetic truth. | The MAE table from [model_card.md](model_card.md) (temporal holdout rows only) and the "Where it does not help" list. |
| 12 | Impact | Replaying spray decisions: fewer unnecessary waits (217 against 554) but more washed-off sprays (179 against 68); heat alerts raise more false alarms. Costs from an expert decide which is better. | Spray and heat rows of the decision replay table from [model_card.md](model_card.md). No money values. |
| 13 | Deployment and roadmap | Runs today with one command on a laptop, with an offline copy. Next: real stations, leave-one-station-out validation, expert thresholds, native-speaker review; later PostgreSQL, a scheduler, a model registry. | `make up` output; the production path table from [architecture.md](architecture.md), labelled "future". Roadmap from the README. |
| 14 | Team | Who built what, and what we need: data access, an agronomist, native speakers. | Names and roles. The "Inputs needed" list from the README. |

## Speaker notes to keep

- Slide 3: say "synthetic example" before naming the Panchayats.
- Slide 11: say "proxy validation on synthetic data" in the same sentence as the first number.
- Slide 12: say "placeholder thresholds, counts only, no costs".
- If asked for a real-world number you do not have, say so; [qna.md](qna.md) has the short answers.
