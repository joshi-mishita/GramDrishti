# API contract changelog

The contract is defined in Appendix A of `docs/GramDrishti_Backend_Guide.pdf` and `docs/GramDrishti_Frontend_Guide.pdf`, and implemented as `contract/openapi.json` plus `contract/examples/*.json`.

Rules (see `CONTRIBUTING.md`):
- Additive, optional fields: new minor version entry here, regenerate `openapi.json` and examples.
- Breaking changes (remove, rename, change type): agreed by both people before any code.

| Version | Date | Status | Change | Breaking |
|---|---|---|---|---|
| v0.1 | 2026-09-24 | superseded | Contract as written in Appendix A. Not yet implemented; `openapi.json` and examples arrive in S2. | n/a |
| v0.1.1 | 2026-09-25 | **frozen** | First implementation (S2): `openapi.json`, `examples/`. Every Appendix A shape kept; additions and definitions listed below. | no (additive) |

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

