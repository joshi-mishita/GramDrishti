# API contract changelog

The contract is defined in Appendix A of `docs/GramDrishti_Backend_Guide.pdf` and `docs/GramDrishti_Frontend_Guide.pdf`, and implemented as `contract/openapi.json` plus `contract/examples/*.json`.

Rules (see `CONTRIBUTING.md`):
- Additive, optional fields: new minor version entry here, regenerate `openapi.json` and examples.
- Breaking changes (remove, rename, change type): agreed by both people before any code.

| Version | Date | Status | Change | Breaking |
|---|---|---|---|---|
| v0.1 | 2026-09-24 | superseded | Contract as written in Appendix A. Not yet implemented; `openapi.json` and examples arrive in S2. | n/a |
| v0.1.1 | 2026-09-25 | superseded | First implementation (S2): `openapi.json`, `examples/`. Every Appendix A shape kept; additions and definitions listed below. | no (additive) |
| v0.1.2 | 2026-09-26 | superseded | Forecast endpoints serve the S5 model through snapshots (S6). Optional fields only; see below. | no (additive) |
| v0.2.0 | 2026-09-26 | superseded | Risk, priority and advisories from the YAML rules engine; review state in SQLite (S8). Optional fields only; see below. | no (additive) |
| v0.3.0 | 2026-09-27 | superseded | Verification and impact from the verification job on the TEST window (S10). Optional fields only; see below. | no (additive) |
| v0.4.0 | 2026-09-27 | **current** | Farmer side (S12): demo farmers in SQLite, farmer advice filtered by crop with spray days, feedback checks, gTTS audio, offline snapshot export. Optional fields only; see below. | no (additive) |

## v0.4.0 (2026-09-27, S12)

Additive and optional: every v0.3.0 client and example still validates. `GET /meta` and `/health` return `api_version: "0.4.0"`. The number skips v0.3.0 because the S10 branch (verification and impact, not merged when S12 started) already uses it; when both are merged the two entries stand side by side.

New optional fields:
- `Farmer.livestock` (boolean): the demo farmer keeps livestock, so livestock advisories reach them.
- `FarmerAdvice.spray_days`: `[{date, lead_day, rating}]` for the five forecast days at the farmer's Panchayat, `rating` = `good | caution | avoid` (the same whole-day rating as `derived.spray_rating` in `/forecast/panchayat`; no hour-level windows).

Semantics changed in this version (shapes unchanged):
- Demo farmers are five profiles stored in SQLite (`store/seed_demo.py`), `F001` to `F005`, named "Demo farmer N" (not real people). `F006` is gone (404). F001 (MP0307) and F002 (MP0311) share block MB03. `crops` lists the Panchayat's own crop rows for rabi 2023-24, kharif 2024 and rabi 2024-25 that this farmer grows.
- `/farmers/{id}/advice`: only `approved` and `edited` advisories for the farmer's Panchayat **and crops** (livestock advice only when `livestock` is true), ordered by priority (severe first), then `valid_from`, then id. Drafts and rejected advisories never appear.
- `POST /feedback`: 400 `bad_request` when `date` is outside the days the block forecast covers or after today, or when `reported_rain` and `intensity` contradict each other (`true` with `none`, `false` with anything but `none`). An identical report (same Panchayat, date, answer, intensity and channel) within 10 minutes is not stored again: 200 with `stored: false`, the first report's `id` and a "we already have this report" message. The thank-you text no longer says the report "improves the forecast"; it now says it helps check it.
- `GET /audio/{advisory_id}?lang=`: MP3 (`audio/mpeg`) of the advisory's action, reason and fallback in that language, made with gTTS on first request and cached (a new file after an edit). 404 `audio_not_available` (contract error shape) when gTTS is not installed, the language has no text (for example after an English-only edit), or the file cannot be made (no internet). 404 `not_found` for an unknown advisory.
- `Advisory.audio`: approved and edited advisories now list `{lang: "/api/v1/audio/<id>?lang=<lang>"}` for each language with text that the installed gTTS supports (en, hi and pa with gTTS 2.5.4). Drafts and rejected advisories keep `{}`. A listed link can still answer 404 when the server has no internet; the UI then uses browser speech.

Examples added in S13 (no shape change, still v0.4.0): `farmer_advice_F003..F005.json`, `forecast_panchayat_<pid>.json` for each demo farmer's Panchayat (MP0307, MP0311, MP0508, MP0601), and `advisories_<pid>.json` = `GET /advisories?panchayat_id=<pid>&issue_date=2024-09-09` for the same Panchayats plus MP0103 (the bulletin reads this list and prints approved and edited items). Drafts in all five farmers' Panchayats are approved before these are written. `export_snapshot` adds the same per-Panchayat list for every Panchayat and date.

New, outside the API: `contract/snapshot/` (git-ignored) from `python -m gramdrishti.export_snapshot` holds every GET response the frontend asks for on the demo dates, with an `index.json` in the same format as `contract/examples/index.json` (one entry per request: `file`, `method`, `path` with query, `status`, `model`). Top-level keys: `contract_version`, `data_mode`, `issue_dates`, `model_versions`, `panchayats`, `generated_on`, `generated_by`, `files`. File names follow the example names with the date and lead day added, for example `forecast_map_rain_2024-09-09_lead1.json`, `explain_MP0307_tmax_2024-09-09_lead1.json`, `farmer_advice_F001_2024-09-09.json`.

## v0.3.0 (2026-09-27, S10)

Additive and optional: every v0.2.0 client and example still validates. `GET /meta` and `/health` return `api_version: "0.3.0"`.

Semantics changed (shapes unchanged):
- `/verification/summary`, `/verification/reliability`, `/verification/coverage`, `/verification/regions` and `/impact` now serve the files written by `python -m gramdrishti.verify.run_validation` (`backend/artifacts/verification.json`, `impact.json`) with `provenance: "computed"`. The seeded placeholder numbers are gone. A missing file, or one built in another data mode, answers 503 `not_computed`. The API never computes or changes a score.
- `/verification/summary.variables` is the temporal holdout on TEST (the production model). `method` is `temporal_holdout + leave_one_block_out + station_check`. `period` is the valid dates scored (2024-07-17..2024-12-31).
- `/verification/regions`: `region_type: "block"` rows are leave-one-block-out MAE for the held-out block; `"station"` rows are the production forecast against each station (rain only for rain gauges).
- `/impact`: seasons `monsoon_2024` (default), `post_monsoon_2024`, `winter_2024`, `test_2024`. For `heat_alert` and `irrigation_wait` the count names keep the spray wording: `wasted_wait` = acted (alert, wait) and the event did not come; `washed_off` = did not act and the event came. `block_baseline` uses the raw block forecast B0.
- `/data-quality` carries `provenance: "computed"` (was `provisional`); numbers unchanged.

New optional fields:
- `MetricRow.skill_vs_b1`, `MetricRow.skill_vs_b1_ci95`: skill against the corrected block forecast B1 (what the model is reconciled to) with its 95 % interval. Metric names now include `quantile_loss` (not for leave-one-block-out) and, for rain, `MAE_wet_days_obs_ge_1mm`.
- `EventSummary.n`, `base_rate`, `frequency_bias`, `yes_rule`, `baselines[]` (`EventBaselineScores`: B0 and B1 yes/no scores: pod, far, csi, frequency_bias, brier).
- `VerificationSummary.model_version`, `window`, `test_first_opened_at`, `test_reused`, `checks[]` (`CheckSummary`: temporal_holdout, leave_one_block_out, station, each with `variables`), `strata[]` (`StratumRow`: MAE by lead_day, season, rain_intensity, drainage_class with skills and intervals), `verdicts[]` (`Verdict`: win / tie / loss / too_few_days from the MAE-skill interval).
- `ReliabilityPoint.mean_forecast_prob`: the mean forecast inside the bin (`forecast_prob` stays the bin centre).
- `CoverageItem.stratum`: `all`, `lead_day=<n>`, `season=<name>` or `observed_rain>=1mm`. `items` now has one row per variable and stratum; filter `stratum == "all"` for the old view.
- `RegionItem.b1`, `RegionItem.b2`.
- `Impact.block_corrected` (the block rule on B1), `events_observed`, `period`, `lead_day`, `threshold`, `unit`.

## v0.2.0 (2026-09-26, S8)

Additive and optional: every v0.1.2 client and example still validates. `GET /meta` and `/health` return `api_version: "0.2.0"`. The minor step follows Appendix A1 ("contract changes bump the minor") and the S8 session plan.

New optional fields:
- `Advisory.rule_id`: the `rules.yaml` rule that produced the advisory (for example `irrigate_now`).
- `AuditEntry.before` and `AuditEntry.after`: the fields a review changed, as JSON objects (`status`, and `action` / `reason` / `fallback` when edited). The `created` entry has `before: null`, `after: {"status": "draft"}`.
- `Derived.spray_rating` (in `/forecast/panchayat` days): `good | caution | avoid`, a **whole-day** spray rating from P(rain >= 2.5 mm) that day and the next and the p90 wind. The data is daily, so there are no hour-level spray windows.

Semantics changed in this version (shapes unchanged):
- `/risk`, `/priority` and `/advisories` carry `provenance: "computed"` (rules engine output) and `thresholds_status: "placeholder"` (every threshold waits for expert review; `docs/thresholds_for_expert_review.md`). They were `provisional` / `placeholder` before.
- Risk scores: `heavy_rain` is the calibrated P(rain >= 35 mm); `heat` and `frost` are the chance of crossing the heat or cold alert of the crops in season at that Panchayat (placeholder crop calendar), else a generic 40 C / 2 C; `waterlogging` is the agro waterlogging score; `dry_spell` grows with dry days in a row and soil water used. Levels come from the cuts in `rules.yaml`. A Panchayat whose waterlogging score is unknown (no soil state, real mode) has no waterlogging item.
- `/priority`: one item per Panchayat (its worst risk within the horizon, moderate or above), ranked by level, then score, then Panchayat id. `crops_affected` lists crops with an advisory in a category linked to that risk (may be empty). `headline` is filled from `templates.yaml` in en, hi and pa (hi and pa need native review).
- Advisories: ids stay `ADV-<issue>-<panchayat>-<crop>-<category>`; livestock advice uses crop `livestock`. At most one advisory per Panchayat, crop and category. `stage` can be `pre_sowing` for a crop sown within the next 10 days. `audio` stays `{}`.
- `POST /advisories/{id}/review`: `edited` is only accepted with `action: "edit"` (400 otherwise). A language left out of an edited text becomes null, so a stale translation never survives a changed English text. A reviewed advisory can be reviewed again; each review appends one audit entry.
- Review state and feedback persist in SQLite across restarts. `POST /feedback` ids count up from the database.
- `/forecast/changes`: `advice_changed` is now `true` or `false` (the rules engine's advice for that Panchayat differs between the two issue dates by crop, category or rule); still `null` without a previous snapshot.

## v0.1.2 (2026-09-26, S6)

Additive and optional: every v0.1.1 client and example still validates. `GET /meta` and `/health` return `api_version: "0.1.2"`. Forecast, explain and change responses now carry `provenance: "computed"` (model output from snapshots) instead of `provisional`/`placeholder`.

New optional fields:
- `Quantiles` (in `/forecast/panchayat` days): `mean` (model mean) and `block_corrected` (corrected block forecast B1).
- `/forecast/map`: `panchayat_layer[].mean`, `block_layer[].corrected` (B1), and `model_version`.
- `Derived`: `soil_moisture_frac_dry` and `soil_moisture_frac_wet` (soil water on the p10 and p90 rain paths; `soil_moisture_frac` is the p50 path), `depletion_frac`, `gdd` (`{crop: degree days}` for crops in season at that Panchayat), `frost_prob`, `frost_risk` (level), `fog_proxy` (bool, a December-January proxy), `dry_spell_days` (consecutive forecast days with P(rain >= 1 mm) < 0.2, counted from lead day 1).
- `/forecast/panchayat`: `model_version`, `thresholds_status` (`placeholder`: the waterlogging and frost levels use placeholder thresholds).
- `/explain` and `/forecast/changes`: `model_version`.

Semantics fixed or clarified in this version:
- Block consistency holds for the model **mean**: the plain average of a block's Panchayat `mean` values equals `block_corrected` (map: `block_layer[].corrected`) to within 1e-6 before rounding (0.01 after rounding each value to 2 decimals). It does not hold for `p50`, and `block` / `block_value` stay the raw block forecast B0, so `delta = p50 - block_value` includes the bias correction.
- Rain probabilities (`prob`, map `prob_event`) come from calibrated event classifiers, not from the quantiles.
- `/explain`: `delta_vs_block` is `mean - block_corrected`, the quantity the reasons explain (SHAP on the mean model, Panchayat minus block average). `reasons` holds exactly 3 items, or is empty when that difference is negligible (for example rain in a block forecast to get 0 mm). `text.hi` and `text.pa` are null until written by a native speaker. `method` is `shap_tree_explainer_mean_model_block_contrast`.
- `/forecast/changes` compares with the snapshot of the previous day's issue (the builder writes one for each demo date). Without it, `previous_issue_date` is null, the lists are empty and `summary` says there is nothing to compare with. The summary count now includes event changes.
- A forecast, explain, change, risk, priority or advisory request for a demo date without a snapshot answers 503 `not_computed`.

## v0.1.1 (frozen 2026-09-25)

Status: **frozen**. From now on, changes follow "How to change the contract" in `CONTRIBUTING.md`. `GET /meta` returns `api_version: "0.1.1"`.

Additive fields (all present in every response the stub sends; optional ones are marked):
- `GET /meta`: `issue_date_info: [{date, label, split}]` (optional), `split` is `train | calib | test`. Explains why each demo issue date exists; training-period replays say so in `label`.
- `data_mode` on every JSON response (rule 1 of `CLAUDE.md`), including the GeoJSON FeatureCollections (a foreign member). Also sent as header `X-Data-Mode`.
- `provenance: provisional | placeholder | computed` on forecast, risk, priority, advisory, explain, verification, impact and data-quality responses. `placeholder` means generated numbers that must never be quoted.
- Advisory: `translation_status: needs_native_review | reviewed`, `data_mode`, `provenance`. `audio` is `{}` until audio exists.
- `/priority` items: `valid_date` (optional), the day the top risk applies to.
- `/impact`: query `decision=spray|heat_alert|irrigation_wait` (optional, default `spray`); response adds `season`, `data_mode`, `provenance`, `rule` (optional) and `notes`. Seasons: `monsoon_2024`, `post_monsoon_2024`, `test_2024`.
- Verification responses carry `notes` (the wording the UI footnote uses); `/verification/reliability` echoes `event`.
- `/explain` adds `issue_date`, `lead_day`, `data_mode`, `provenance`, `method`. `effect` is `warmer | cooler | wetter | drier | more_humid | less_humid | windier | calmer`.

Definitions for shapes Appendix A lists without a payload (see `openapi.json` and the example named in brackets):
- `GET /health` -> `{status: "ok", api_version, data_mode}` (`health.json`).
- `GET /geo/panchayats`, `GET /geo/blocks`: FeatureCollection of Polygon or MultiPolygon, coordinates `[longitude, latitude]`, properties `{panchayat_id, name, block_id}` and `{block_id, name}`.
- `GET /observed/panchayat/{id}?from&to` -> `{panchayat_id, from, to, source: station | synthetic_truth | none, station_id, data_mode, days: [{date, rain, tmax, tmin, rh, wind}]}`. At most 62 days; the Panchayat's own station if it has one (rain gauges give null for other variables), otherwise synthetic truth in mock mode.
- `GET /risk?issue_date&lead_day&type` -> `{issue_date, valid_date, lead_day, type, data_mode, provenance, thresholds_status, items: [{panchayat_id, block_id, level, score}]}`.
- `GET /priority` items only include level moderate and above. `horizon_days` defaults to 2 (1 to 5).
- `GET /advisories` -> `{data_mode, provenance, total, items: [Advisory]}`.
- `POST /advisories/{id}/review` -> the updated Advisory (status approve -> `approved`, edit -> `edited`, reject -> `rejected`; audit entry appended). An edit with no `edited` fields is 400.
- `GET /audio/{id}?lang` -> `audio/mpeg`, or 404 in the error shape when no audio exists.
- `GET /farmers/{id}` -> `{farmer_id, name, panchayat_id, block_id, language, crops: [{crop, season, sowing_date, expected_harvest_date, area_fraction}], data_mode}`. Demo farmers are `F001` to `F006`.
- `GET /farmers/{id}/advice?issue_date` -> `{farmer_id, panchayat_id, issue_date, language, data_mode, items: [Advisory]}` with status `approved` or `edited` only.
- `POST /feedback` -> `{id, stored, received_at, data_mode, feedback, message}`; `channel` is `app | whatsapp | ivr`.
- `GET /forecast/changes/{id}?issue_date` -> `{panchayat_id, issue_date, previous_issue_date, data_mode, provenance, changes: [{valid_date, var, previous_p50, current_p50, delta, material}], event_changes: [{valid_date, event, previous_prob, current_prob}], advice_changed, summary}`. `advice_changed` is null until the rules engine exists.
- `GET /verification/coverage` -> `{data_mode, provenance, items: [{var, unit, nominal, empirical, mean_width, n}], notes}`.
- `GET /verification/regions` -> `{data_mode, provenance, method, items: [{region_type: block | station, region_id, var, metric, unit, model, b0, n}], notes}`.
- `GET /data-quality?issue_date` (optional, default the last demo date) -> `{as_of, data_mode, provenance, stations_total, stations_reporting_24h, missing_share_30d, stale_inputs: [{input, last_date, days_stale}], stations: [{station_id, station_type, block_id, last_report, reported_last_24h, missing_share_30d, flagged_share_30d}]}`.

Semantics fixed in this version:
- Quantile `block` and map `block_value` are the issued block forecast (plain mean of the NWP sources, baseline B0). `delta = p50 - block_value`.
- Forecast endpoints accept only `issue_date` values from `/meta.available_issue_dates`; any other date is 404 with code `issue_date_not_available`.
- Error codes: `not_found`, `issue_date_not_available`, `bad_request` (400), `validation_error` (422), `not_computed` (503, placeholder endpoints in real mode), `internal_error` (500).
- POST endpoints answer 200.
- `LocalizedText` is `{en, hi?, pa?}`; `hi` and `pa` may be null or missing.

