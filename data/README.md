# GramDrishti - MOCK (synthetic) dataset

**Everything here is artificial.** Names, coordinates, stations and values do not describe any real Panchayat, station or forecast. Use it to build and demo the pipeline. **Never report model results on it as validation.**

Setup: a fictional semi-arid northern-plains district (6 blocks, 90 Panchayats, 24 stations), 2023-01-01 to 2024-12-31 (731 days), regenerate with `python generate_mock_data.py` (`SEED` and `OUT` env vars).

## Files and the real source that replaces each

| File | Contents | Real replacement |
|---|---|---|
| `panchayats_static.csv` | 90 rows: elevation, TPI, slope, irrigated/urban/water/tree/cropland fractions, canal distance, clay/sand/silt, texture, water holding capacity, drainage class | DEM, WorldCover, SoilGrids, JRC water, canal layers, aggregated per Panchayat |
| `blocks.csv`, `*_SYNTHETIC.geojson` | Block table; Voronoi polygons for Panchayats and blocks | LGD codes + real boundaries (Bhuvan, DataMeet, SHRUG, state GIS centre) |
| `block_forecast_mock_nwp.csv` | Block-level forecasts from two mock NWP sources, lead 1-5 days (rain, Tmax, Tmin, RH, wind) with lead-dependent bias/noise, misses and false alarms | GFS/ECMWF aggregated to blocks, or official IMD block forecast |
| `stations.csv`, `station_observations_mock.csv` | 14 AWS (all variables) + 10 ARG (rain only, 0.5 mm resolution), measurement noise, ~5% missing days, some multi-week outages | State AWS/ARG, IMD, SAU/KVK, CPCB stations |
| `satellite_weekly_mock.csv` | Weekly NDVI and daytime LST per Panchayat, with cloud gaps (heavier in Jul-Sep) | Sentinel-2 / MODIS composites |
| `panchayat_crops_mock.csv` | Crop and sowing date per Panchayat for 5 seasons (rabi/kharif) | State crop calendars, Meri Fasal Mera Byora, crop maps |
| `crop_calendar_PLACEHOLDER.csv` | Crop stages (DAS), alert thresholds, sensitivities, key operations. **Placeholders, not expert-reviewed.** | KVK/SAU-validated table |
| `farmer_feedback_mock.csv` | 800 mock "did it rain?" reports (~88% correct) | WhatsApp/IVR/app feedback |
| `synthetic_oracle/` | Full Panchayat-level daily truth (rain, Tmax, Tmin, RH, dew point, wind, ET0, soil moisture, waterlogging flag) and block truth | **Does not exist in reality.** Use only for proxy tests, never for training the real model |

## Units and conventions
Rain mm/day; temperatures °C; RH daily mean %; wind km/h; ET0 mm/day (Hargreaves); soil_moisture_frac = root-zone water / capacity (0-1); `waterlog_flag` = 1 when saturation excess > 15 mm on a poorly drained or low-lying Panchayat. Missing observations are blank/NaN.

## What is planted in the data (so you know what the model can learn)
- Panchayat rainfall = block total redistributed by spatially correlated patchiness, an occurrence mask (patchier in monsoon) and a static local factor. Block mean is preserved exactly (checked in `mock_data_summary.json`).
- Tmax offset: cooler with more irrigation, warmer with urban/sandy land, strongest in the hot dry season, weaker on rainy days.
- Tmin offset: low-lying (TPI) Panchayats colder on winter nights; urban warmer. Fog days lower Tmax.
- RH derived from dew point and temperature (irrigation/water raise dew point). Wind scaled by tree cover and urban fraction.
- Block forecasts are built from the block truth, so forecast errors are realistic in form but **known and simple**.

## Limits
- Planted relationships are far simpler than real weather. A model that beats the block baseline here proves the code works, not that the method works on real data.
- Within-block Tmax spread is deliberately modest (~0.1-0.8 °C by season), in line with plains terrain. Rain is patchy.
- Two years is enough to exercise train/test splits, not to represent climate variability.
- Forecast errors are independent across lead days and stations sample only Panchayats, unlike real networks.

## Swapping in real data
Keep the same column names. Replace files one at a time: `stations` + `station_observations` first, then `block_forecast`, then static features and satellite. Delete `synthetic_oracle/` from any real-data run and switch validation to leave-one-station-out on real stations.
