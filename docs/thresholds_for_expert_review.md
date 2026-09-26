# Thresholds for expert review

This file is for the KVK or SAU agrometeorology expert who reviews GramDrishti's advisory rules. It is generated from the code by `cd backend && python -m gramdrishti.advisory.expert_table`; do not edit it by hand.

**Every number below is a placeholder chosen by the development team, not by an agronomist.** The prototype runs on synthetic data, and every advisory it drafts says `thresholds_status: placeholder` until these numbers are reviewed.

How to review:
1. For each row, write the value you recommend in **Expert value** (or "ok" to keep it) and the reference in **Source** (a publication, a KVK or SAU recommendation, or "expert judgement").
2. Note any rule that should not exist, is missing, or needs a different condition.
3. Return the file. The team copies each value into `rules.yaml` (or the calendar), fills `source`, and sets `thresholds_status: reviewed` on that rule.

Counts: 15 rules with 21 rule thresholds, 6 spray-planner thresholds, 5 risk types, the crop calendar and 2 general settings.
Probabilities are written 0 to 1 (0.35 means 35 %). Rain in mm, temperature in C, wind in km/h. "Upper estimate" is the forecast's 90th percentile (p90), "lower estimate" its 10th (p10).

## 1. Advisory rules (`backend/gramdrishti/advisory/rules.yaml`)

Each row is one number inside a rule. Rules without their own numbers use the crop calendar (section 5) or the spray planner (section 2); they are listed in section 1b.

| Rule | Threshold | Current value | Unit | What it means | Expert value | Source |
|---|---|---|---|---|---|---|
| `sowing_heavy_rain_wait` | `heavy_rain_prob` | 0.3 | probability | Delay sowing when the chance of heavy rain (35 mm or more) in the next 3 days reaches this. | |
| `sowing_dry_soil` | `min_soil_moisture` | 0.3 | fraction of capacity | Below this soil water the seed bed is too dry to sow without a pre-sowing irrigation. | |
| `sowing_go` | `min_soil_moisture` | 0.3 | fraction of capacity | At or above this soil water the seed bed is moist enough to sow. | |
| `sowing_go` | `heavy_rain_prob` | 0.3 | probability | Sowing is advised only while the chance of heavy rain in the next 3 days stays below this. | |
| `irrigate_now` | `depletion_trigger` | 0.55 | fraction of capacity | Irrigate when this share of the root-zone water is used up (Guide 9.3 example). | |
| `irrigate_now` | `useful_rain_prob` | 0.25 | probability | Irrigate only if the chance of useful rain (10 mm or more) in the next 3 days is below this. | |
| `irrigation_hold_rain` | `depletion_watch` | 0.4 | fraction of capacity | Only fields this dry would be irrigated soon, so only they get the hold message. | |
| `irrigation_hold_rain` | `useful_rain_prob` | 0.5 | probability | Hold irrigation when the chance of 10 mm or more in the next 3 days reaches this. | |
| `fertilizer_postpone` | `rain_prob` | 0.4 | probability | Postpone urea when the chance of 10 mm or more tomorrow reaches this (washing and loss). | |
| `fertilizer_postpone` | `waterlog_score_min` | 0.25 | score 0..1 | Postpone urea when the waterlogging score in the next 3 days reaches this ("high"). | |
| `frost_protect` | `low_lying_margin_c` | 1.5 | C | Low-lying Panchayats get frost advice this many degrees above the crop's cold alert. | |
| `waterlogging_drain` | `heavy_rain_prob` | 0.3 | probability | Advise drain clearing when the chance of 35 mm or more in the next 3 days reaches this. | |
| `dry_spell_protect` | `min_dry_days` | 5 | days | Dry-spell advice when this many days in a row from tomorrow are dry (chance of 1 mm below 20 %). | |
| `dry_spell_protect` | `min_et0` | 4 | mm/day | Only when crops lose at least this much water a day (reference evapotranspiration, 3-day mean). | |
| `harvest_rain_risk` | `harvest_window_days` | 10 | days | Harvest advice applies from this many days before the expected harvest date. | |
| `harvest_rain_risk` | `rain_prob` | 0.4 | probability | Warn when the chance of 10 mm or more in the next 3 days reaches this. | |
| `pest_disease_humid` | `humid_rh` | 80 | % | Scouting advice when the 3-day mean humidity reaches this. | |
| `pest_disease_humid` | `warm_min_c` | 20 | C | Lowest 3-day mean temperature at which the warm-humid watch applies. | |
| `pest_disease_humid` | `warm_max_c` | 32 | C | Highest 3-day mean temperature at which the warm-humid watch applies. | |
| `livestock_heat_severe` | `thi_severe` | 90 | THI | Severe heat stress for cattle and buffalo at or above this index. | |
| `livestock_heat` | `thi_moderate` | 80 | THI | Moderate heat stress for cattle and buffalo at or above this index. | |

### 1b. What each rule does

| Rule | Advice (category, base priority) | Fires when | Numbers it uses | Advice text (English) |
|---|---|---|---|---|
| `sowing_heavy_rain_wait` | sowing, high | `stage == 'pre_sowing' and p_rain_35_3d >= heavy_rain_prob` | `heavy_rain_prob` | Wait before sowing {crop_name}. Sow after the heavy rain has passed and the field can be worked. |
| `sowing_dry_soil` | sowing, moderate | `stage == 'pre_sowing' and soil_moisture_start < min_soil_moisture` | `min_soil_moisture` | Give a pre-sowing irrigation before you sow {crop_name}, then sow when the soil is moist but workable. |
| `sowing_go` | sowing, low | `stage == 'pre_sowing' and soil_moisture_start >= min_soil_moisture and p_rain_35_3d < heavy_rain_prob` | `min_soil_moisture`, `heavy_rain_prob` | Conditions suit sowing {crop_name} in the next 3 days. |
| `irrigate_now` | irrigation, moderate | `depletion >= depletion_trigger and p_rain_10_3d < useful_rain_prob and drought_sensitivity in ['high', 'medium']` | `depletion_trigger`, `useful_rain_prob`; calendar: `drought_sensitivity` | Irrigate {crop_name} by {day}. Skip it if you irrigated in the last 3 days. |
| `irrigation_hold_rain` | irrigation, moderate | `depletion >= depletion_watch and p_rain_10_3d >= useful_rain_prob` | `depletion_watch`, `useful_rain_prob` | Hold irrigation of {crop_name} for now and check again on {valid_to_day}. |
| `spray_hold` | spray, moderate | `spray_d1 == 'avoid'` | none of its own; spray planner (section 2) | Do not spray pesticide or fertiliser on {crop_name} on {day}. The next good spray day is {next_spray_day}. |
| `fertilizer_postpone` | fertilizer, moderate | `topdress_stage and (p_rain_10_d1 >= rain_prob or waterlog_score_3d >= waterlog_score_min)` | `rain_prob`, `waterlog_score_min`; calendar: `topdress_stage` | Postpone the urea top-dressing of {crop_name}. Apply it on a day when no rain is forecast. |
| `heat_stress_crop` | heat_stress, high | `tmax_p90_3d >= tmax_alert_c` | none of its own; calendar: `tmax_alert_c` | Give {crop_name} a light irrigation in the evening, and avoid spraying or other field work in the afternoon heat until {valid_to_day}. |
| `frost_protect` | frost, high | `tmin_p10_3d <= tmin_alert_c or (low_lying and tmin_p10_3d <= tmin_alert_c + low_lying_margin_c)` | `low_lying_margin_c`; calendar: `tmin_alert_c` | Give {crop_name} a light irrigation on the evening before {day}, and cover nurseries and young plants overnight. |
| `waterlogging_drain` | waterlogging, high | `p_rain_35_3d >= heavy_rain_prob and (drain_poor or low_lying) and waterlog_sensitivity != 'low'` | `heavy_rain_prob`; calendar: `waterlog_sensitivity` | Clear the field drains before the heavy rain expected around {day} so rainwater can run off, and hold fertiliser until the field has drained. |
| `dry_spell_protect` | dry_spell, moderate | `dry_days >= min_dry_days and et0_3d >= min_et0 and drought_sensitivity == 'high'` | `min_dry_days`, `min_et0`; calendar: `drought_sensitivity` | Plan irrigation for {crop_name}, which is at the {stage_name} stage, and mulch where you can to keep moisture in the soil. |
| `harvest_rain_risk` | harvest, high | `days_to_harvest <= harvest_window_days and p_rain_10_3d >= rain_prob` | `harvest_window_days`, `rain_prob` | Plan the {crop_name} harvest around the rain. If the crop is ready, harvest before the rain expected on {day}, and keep harvested produce covered and off the ground. |
| `pest_disease_humid` | pest_disease, moderate | `pest_watch_stage and rh_mean_3d >= humid_rh and warm_min_c <= tmean_3d <= warm_max_c` | `humid_rh`, `warm_min_c`, `warm_max_c`; calendar: `pest_watch_stage` | Check {crop_name} fields for pests and disease from {day}. Spray only if an agriculture officer confirms a problem. |
| `livestock_heat_severe` | livestock, high | `thi_p90 >= thi_severe` | `thi_severe` | Keep cattle and buffalo in shade from late morning to evening, give plenty of fresh water, and avoid grazing or work in the midday heat until {valid_to_day}. |
| `livestock_heat` | livestock, moderate | `thi_p90 >= thi_moderate` | `thi_moderate` | Give animals shade and plenty of fresh water, and graze them in the cooler morning and evening hours until {valid_to_day}. |

## 2. Spray planner (`spray_planner` in rules.yaml)

Rates each forecast day Good, Caution or Avoid for spraying. Whole days only: the data is daily, so the prototype cannot give hour-level spray windows.

| Setting | Threshold | Current value | Unit | What it means | Expert value | Source |
|---|---|---|---|---|---|---|
| spray planner | `avoid_rain_today` | 0.5 | probability | Chance of 2.5 mm or more on the day itself at or above this makes the day Avoid. | |
| spray planner | `avoid_rain_next_day` | 0.6 | probability | Chance of 2.5 mm or more on the following day at or above this makes the day Avoid (wash-off). | |
| spray planner | `avoid_wind` | 15 | km/h | Upper estimate (p90) of daily wind at or above this makes the day Avoid (drift). | |
| spray planner | `caution_rain_today` | 0.25 | probability | Chance of 2.5 mm or more on the day at or above this makes the day Caution. | |
| spray planner | `caution_rain_next_day` | 0.35 | probability | Chance of 2.5 mm or more on the following day at or above this makes the day Caution. | |
| spray planner | `caution_wind` | 10 | km/h | Upper estimate (p90) of daily wind at or above this makes the day Caution. | |

## 3. Risk map and priority list (`risk` in rules.yaml)

Each risk type gives a score from 0 to 1. The three cuts turn the score into moderate, high and severe (below the first cut is low).

| Risk type | How the score is made | Cuts (moderate, high, severe) | Expert cuts | Source |
|---|---|---|---|---|
| heavy_rain | Chance of 35 mm or more on the day (calibrated rain classifier). | 0.1, 0.3, 0.6 | |
| heat | Chance that the day's maximum reaches the lowest heat alert of the crops in season there. | 0.1, 0.3, 0.6 | |
| frost | Chance that the day's minimum falls to the highest cold alert of the crops in season there. | 0.1, 0.3, 0.6 | |
| waterlogging | Waterlogging score from agro/derived.py (heavy rain chance x drainage x soil wetness). | 0.1, 0.25, 0.5 | |
| dry_spell | Dry days in a row from tomorrow, divided by full_days, times (0.5 + 0.5 x soil water used). | 0.25, 0.5, 0.75 | |

| Risk type | Threshold | Current value | Unit | What it means | Expert value | Source |
|---|---|---|---|---|---|---|
| heat | `generic_heat_c` | 40 | C | Heat threshold for a Panchayat with no crop in season, or no crop with a heat alert. | |
| frost | `generic_frost_c` | 2 | C | Frost threshold for a Panchayat with no crop in season, or no crop with a cold alert. | |
| dry_spell | `full_days` | 5 | days | This many forecast dry days in a row gives the full dry-spell score. | |

## 4. Confidence and general settings (rules.yaml)

Confidence follows Backend Guide 9.5: score = margin beyond the threshold - lead penalty x (lead day - 1) - width weight x (forecast spread / reference width).

| Setting | Threshold | Current value | Unit | What it means | Expert value | Source |
|---|---|---|---|---|---|---|
| confidence | `lead_penalty` | 0.08 | per lead day | Confidence lost per day of lead time (Guide 9.5). | |
| confidence | `width_weight` | 0.3 | score | Weight of forecast spread in the confidence score (Guide 9.5). | |
| confidence | `high_above` | 0.25 | score | A score above this is high confidence (Guide 9.5). | |
| confidence | `medium_above` | 0.05 | score | A score above this is medium confidence (Guide 9.5). | |
| reference width | `rain` | 40 | mm | A rain spread this wide counts as fully uncertain. | |
| reference width | `tmax` | 6 | C | A maximum-temperature spread this wide counts as fully uncertain. | |
| reference width | `tmin` | 6 | C | A minimum-temperature spread this wide counts as fully uncertain. | |
| reference width | `wind` | 15 | km/h | A wind spread this wide counts as fully uncertain. | |
| reference width | `rh` | 30 | % | A humidity spread this wide counts as fully uncertain. | |
| reference width | `soil` | 0.5 | fraction | A soil-water spread (dry vs wet rain path) this wide counts as fully uncertain. | |
| context | `sowing_lookahead_days` | 10 | days | Look this many days ahead for a planned sowing date; those fields get sowing advice. | |
| context | `low_lying_tpi_z` | -0.7 | z-score of topographic position | A Panchayat below this is low-lying (cold air and water collect there). Guide 8 value. | |

## 5. Crop calendar (`data/crop_calendar_PLACEHOLDER.csv`)

Stages by days after sowing (DAS) and the stage alerts used by the heat and frost rules and the risk map. Empty cells mean the rule does not apply at that stage. Sensitivities raise or lower an advisory's priority by one level (high / low).

| Crop | Stage | DAS from | DAS to | Heat alert (C) | Cold alert (C) | Drought sensitivity | Waterlogging sensitivity | Key operations | Expert values | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| wheat | germination_crown_root | 0 | 25 |  | 4 | high | medium | sowing; first irrigation ~CRI | |
| wheat | tillering | 25 | 60 |  | 2 | medium | medium | top-dress nitrogen; weed control | |
| wheat | jointing_booting | 60 | 90 | 30 | 0 | high | medium | irrigation; spray timing | |
| wheat | flowering_grain_fill | 90 | 130 | 34 | 0 | high | low | terminal heat-stress watch; light irrigation | |
| wheat | maturity_harvest | 130 | 145 |  |  | low | low | harvest planning; avoid rain on harvested produce | |
| paddy | transplant_establishment | 0 | 20 | 38 |  | medium | low | standing water; nursery care | |
| paddy | tillering | 20 | 55 | 38 |  | medium | low | nitrogen top-dress | |
| paddy | panicle_flowering | 55 | 90 | 35 |  | high | medium | avoid water stress; disease watch | |
| paddy | grain_fill_maturity | 90 | 120 | 38 |  | medium | high | drain field; harvest window | |
| cotton | germination_seedling | 0 | 30 | 42 |  | medium | high | avoid waterlogging | |
| cotton | squaring_flowering | 30 | 100 | 40 |  | high | high | irrigation; pest scouting | |
| cotton | boll_development_picking | 100 | 180 | 40 |  | medium | high | spray timing; picking before rain | |
| mustard | vegetative | 0 | 45 |  | 0 | medium | high | thinning; irrigation | |
| mustard | flowering_pod | 45 | 100 | 30 | 0 | high | high | aphid watch; frost/fog risk | |
| mustard | maturity | 100 | 130 |  |  | low | medium | harvest timing | |
| bajra | establishment | 0 | 25 | 42 |  | medium | high | gap filling | |
| bajra | tillering_boot | 25 | 55 | 42 |  | high | high | nitrogen top-dress | |
| bajra | flowering_grain | 55 | 85 | 40 |  | high | medium | heat/dry-spell watch | |

Crops in the mock crop table with no calendar rows (no stage, no stage alerts): gram.

## 6. Agro-variables (`backend/gramdrishti/agro/derived.py`)

Numbers inside the soil water, waterlogging, frost and fog calculations that feed the rules.

| Quantity | Constant | Current value | Unit | What it means | Expert value | Source |
|---|---|---|---|---|---|---|
| Effective rain | `RUNOFF_ABOVE_MM` | 20 | mm | Rain above this on one day runs off and does not enter the soil. | |
| Soil water | `ROOT_DEPTH_M` | 0.6 | m | Root-zone depth: capacity = water holding x depth. | |
| Soil water | `STRESS_P` | 0.5 | fraction | Crop water use falls once soil water drops below this share of capacity (FAO-56 p). | |
| Crop coefficient | `KC_BASE`, `KC_NDVI` | 0.4, 0.6 |  | kc = KC_BASE + KC_NDVI x NDVI (no crop-specific kc yet). | |
| Crop coefficient | `KC_DEFAULT` | 0.8 |  | kc when NDVI is missing. | |
| Waterlogging | `WATERLOG_WEIGHTS` | vulnerable 1, other 0.4, full 1, not_full 0.5 |  | Score = P(rain >= 35 mm) x drainage weight x soil wetness weight. | |
| Waterlogging | `WATERLOG_CUTS` | 0.1, 0.25, 0.5 | score | Score cuts for moderate, high and severe in the forecast panel. | |
| Waterlogging | `WATERLOG_FULL_FRAC` | 0.9 | fraction | Soil counts as full above this share of capacity (Guide 8). | |
| Frost (forecast panel) | `FROST_C` | 2 | C | Generic frost threshold for the frost level in the forecast panel. | |
| Frost (forecast panel) | `FROST_CUTS` | 0.1, 0.3, 0.6 | probability | Chance of frost cuts for moderate, high and severe. | |
| Fog proxy | `FOG_TMIN_C`, `FOG_RH_PCT`, `FOG_WIND_KMH` | 8, 75, 6 | C, %, km/h | December-January day with Tmin at most, RH at least and wind at most these values. | |
| Dry day | `DRY_PROB` | 0.2 | probability | A forecast day counts as dry when the chance of 1 mm or more is below this (Guide 8). | |
| Growing degree days | `TBASE_C` | wheat 5, mustard 5, paddy 10, bajra 10, cotton 15 | C | Base temperature per crop. | |
