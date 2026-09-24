#!/usr/bin/env python3
"""
GramDrishti - MOCK (SYNTHETIC) data generator.
Everything produced here is artificial. Names, coordinates and values do not
describe any real Panchayat, station or forecast. Use only to develop and demo
the pipeline; never report results on it as validation.
"""
import os, json
import numpy as np
import pandas as pd

SEED = int(os.environ.get("SEED", 42))
OUT = os.environ.get("OUT", os.path.dirname(os.path.abspath(__file__)))  # default: this data/ folder
rng = np.random.default_rng(SEED)
os.makedirs(f"{OUT}/synthetic_oracle", exist_ok=True)

dates = pd.date_range("2023-01-01", "2024-12-31", freq="D")
T = len(dates)
doy = dates.dayofyear.values
month = dates.month.values

# ------------------------------------------------------------------ geometry
ny, nx = 9, 10                                   # 90 Panchayats, jittered grid
lat0, lon0, dlat, dlon = 28.95, 75.40, 0.035, 0.045   # ~4 x 4.4 km cells
gi, gj = np.meshgrid(np.arange(ny), np.arange(nx), indexing="ij")
lat = lat0 + (gi.ravel() + 0.5 + rng.uniform(-0.35, 0.35, ny * nx)) * dlat
lon = lon0 + (gj.ravel() + 0.5 + rng.uniform(-0.35, 0.35, ny * nx)) * dlon
P = len(lat)
centers = np.array([[lat0 + ny * dlat * a, lon0 + nx * dlon * b]
                    for a in (0.25, 0.75) for b in (1 / 6, 0.5, 5 / 6)])
B = len(centers)
cosl = np.cos(np.radians(lat.mean()))
dy = (lat[:, None] - centers[None, :, 0]) * 111
dx = (lon[:, None] - centers[None, :, 1]) * 111 * cosl
bidx = np.argmin(dx ** 2 + dy ** 2, axis=1)      # nearest block centre
assert len(np.unique(bidx)) == B
block_ids = np.array([f"MB{b + 1:02d}" for b in range(B)])
pid = np.empty(P, dtype=object)
for b in range(B):
    for k, p in enumerate(np.where(bidx == b)[0]):
        pid[p] = f"MP{b + 1:02d}{k + 1:02d}"
M = np.zeros((B, P))
for b in range(B):
    M[b, bidx == b] = 1.0 / (bidx == b).sum()
bmean = lambda x: x @ M.T                        # (T,P) -> (T,B)
expand = lambda x: x[:, bidx]                    # (T,B) -> (T,P)

Dkm = np.hypot((lon[:, None] - lon[None, :]) * 111 * cosl, (lat[:, None] - lat[None, :]) * 111)
def smoother(L):
    W = np.exp(-0.5 * (Dkm / L) ** 2)
    return W / np.sqrt((W ** 2).sum(1, keepdims=True))   # unit-variance filter
Wn = {L: smoother(L) for L in (10, 12, 15, 20, 25)}
Wmean10 = np.exp(-0.5 * (Dkm / 10) ** 2); Wmean10 /= Wmean10.sum(1, keepdims=True)
sfield = lambda L: Wn[L] @ rng.standard_normal(P)        # static smooth field
cnoise = lambda L: rng.standard_normal((T, P)) @ Wn[L].T # spatially correlated daily noise
zs = lambda x: (x - x.mean()) / x.std()

# ------------------------------------------------------- static Panchayat data
elev = 215 + 4 * sfield(25) + 1.5 * rng.standard_normal(P)
tpi = elev - Wmean10 @ elev
tpi_z = zs(tpi)
irrig = np.clip(0.55 + 0.25 * sfield(20) + 0.10 * rng.standard_normal(P), 0.05, 0.98)
canal_km = np.round(rng.exponential(3.0, P) * (1.3 - irrig), 2)
urban = np.clip(rng.beta(1, 14, P), 0, 0.6)
water = np.clip(rng.beta(1, 40, P), 0, 0.3)
tree = rng.beta(1.5, 15, P)
other = 0.5 * rng.beta(1, 30, P)
cropland = np.clip(1 - urban - water - tree - other, 0.05, 1)
clay = np.clip(22 + 7 * sfield(20) + 3 * rng.standard_normal(P), 8, 45)
sand = np.clip(60 - 0.9 * clay + 4 * rng.standard_normal(P), 10, 85)
silt = np.clip(100 - clay - sand, 3, None)
whc = np.round(100 + 2.0 * clay - 0.3 * (sand - 45), 1)          # mm per m
dscore = clay / 10 - 0.7 * tpi_z + 0.3 * rng.standard_normal(P)
drain = np.where(dscore > 3.0, "poor", np.where(dscore < 1.6, "good", "moderate"))
tex = np.where(clay >= 35, "clay", np.where(clay >= 27, "clay_loam", np.where(sand >= 60, "sandy_loam", "loam")))
rain_factor = np.exp(0.12 * sfield(25) - 0.05 * tpi_z)
wind_factor = np.exp(0.08 * sfield(15) - 0.5 * (tree - tree.mean()) - 0.3 * (urban - urban.mean()))

panchayats = pd.DataFrame({
    "panchayat_id": pid, "panchayat_name": [f"Synthetic Panchayat {x}" for x in pid],
    "block_id": block_ids[bidx], "lat": lat.round(5), "lon": lon.round(5),
    "elevation_m": elev.round(1), "tpi_z": tpi_z.round(3),
    "slope_deg": (np.abs(rng.normal(0.4, 0.3, P)) + 0.05).round(2),
    "irrigated_frac": irrig.round(3), "canal_dist_km": canal_km,
    "cropland_frac": cropland.round(3), "urban_frac": urban.round(3),
    "water_frac": water.round(3), "tree_frac": tree.round(3),
    "clay_pct": clay.round(1), "sand_pct": sand.round(1), "silt_pct": silt.round(1),
    "soil_texture": tex, "whc_mm_per_m": whc, "drainage_class": drain,
})
panchayats.to_csv(f"{OUT}/panchayats_static.csv", index=False)
blocks = pd.DataFrame({"block_id": block_ids, "block_name": [f"Synthetic Block {i + 1}" for i in range(B)],
                       "n_panchayats": [(bidx == b).sum() for b in range(B)],
                       "centre_lat": centers[:, 0].round(4), "centre_lon": centers[:, 1].round(4)})
blocks.to_csv(f"{OUT}/blocks.csv", index=False)

# --------------------------------------------------------- weather generator
def clim(arr):
    mid = np.array([15, 46, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349])
    return np.interp(doy, np.concatenate([mid - 365, mid, mid + 365]), np.tile(arr, 3))
def ar1(n, phi, sd):
    e = rng.standard_normal(n) * sd * np.sqrt(1 - phi ** 2)
    x = np.zeros(n); x[0] = rng.standard_normal() * sd
    for t in range(1, n): x[t] = phi * x[t - 1] + e[t]
    return x
def es(t): return np.exp(17.625 * t / (243.04 + t))
def ra_mm(lat_deg):
    phi = np.radians(lat_deg); dr = 1 + 0.033 * np.cos(2 * np.pi * doy / 365)
    dec = 0.409 * np.sin(2 * np.pi * doy / 365 - 1.39)
    ws = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1, 1))
    return 0.408 * (24 * 60 / np.pi) * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))

TMAX = [20, 24, 30, 37, 41, 41, 36, 34, 35, 34, 28, 22]
TMIN = [6, 9, 14, 20, 25, 28, 27, 26, 24, 18, 11, 7]
PWET = [.05, .06, .05, .04, .05, .10, .35, .35, .20, .04, .01, .03]
RMU = [4, 4, 4, 5, 6, 8, 14, 14, 10, 6, 4, 4]
DEP = [6, 7, 10, 15, 16, 12, 5, 4, 5, 9, 8, 6]
WIND = [6, 7, 8, 9, 11, 12, 10, 8, 7, 5, 5, 5]

# rainfall: district wet-day Markov chain, block occurrence, gamma amounts
pm = clim(PWET); wet = np.zeros(T, bool)
for t in range(T):
    prev = wet[t - 1] if t else False
    p = min(0.9, 0.7 * pm[t] + 0.3) if prev else 0.7 * pm[t]
    wet[t] = rng.random() < p
d_amt = rng.gamma(0.7, clim(RMU) / 0.7)
bw = (wet[:, None] & (rng.random((T, B)) < 0.85)) | (~wet[:, None] & (rng.random((T, B)) < 0.02))
R_b = np.clip(bw * d_amt[:, None] * rng.lognormal(0, 0.5, (T, B)), 0, 250)
R_b[R_b < 0.2] = 0

# Panchayat rainfall = block total redistributed by local factors (patchy in monsoon)
cn_mask, cn_amt = cnoise(12), cnoise(15)
thr = np.where(np.isin(month, [6, 7, 8, 9]), -0.7, -1.6)[:, None]
w = rain_factor[None, :] * np.exp(0.6 * cn_amt) * (cn_mask > thr)
rain = np.zeros((T, P))
for b in range(B):
    idx = bidx == b
    wb = w[:, idx].mean(1)
    rain[:, idx] = w[:, idx] * np.where(wb > 0, R_b[:, b] / np.where(wb > 0, wb, 1), 0)[:, None]
rain = np.round(rain, 2)
Rd = bmean(rain)

# temperature
anom = ar1(T, 0.7, 2.5)
fog = np.isin(month, [12, 1]) & (rng.random(T) < 0.2)
tmax_b = clim(TMAX)[:, None] + anom[:, None] + 0.6 * rng.standard_normal((T, B)) - 3.0 * fog[:, None]
tmax_b -= np.minimum(7, 1.2 * np.sqrt(Rd))
tmin_b = clim(TMIN)[:, None] + 0.8 * anom[:, None] + 0.5 * rng.standard_normal((T, B)) + 0.5 * fog[:, None]
gain = np.clip((tmax_b.mean(1) - 22) / 14, 0.15, 1.3) * np.where(Rd.mean(1) > 1, 0.5, 1.0)
st_tmax = -3.2 * (irrig - irrig.mean()) + 8.0 * (urban - urban.mean()) + 0.05 * (sand - sand.mean())
tmax_p = expand(tmax_b) + gain[:, None] * st_tmax[None, :] + 0.35 * cnoise(12)
tmax_p += expand(tmax_b - bmean(tmax_p))
wg = np.clip((18 - tmin_b.mean(1)) / 14, 0, 1)
tmin_p = expand(tmin_b) + wg[:, None] * (0.9 * tpi_z)[None, :] + (3.0 * (urban - urban.mean()))[None, :] + 0.3 * cnoise(12)
tmin_p += expand(tmin_b - bmean(tmin_p))
tmin_p = np.minimum(tmin_p, tmax_p - 2.0)

# humidity (via dew point) and wind
tmean_p = 0.5 * (tmax_p + tmin_p)
td_b = bmean(tmean_p) - clim(DEP)[:, None] - 3 * (Rd > 1) + 0.8 * rng.standard_normal((T, B))
td_p = expand(td_b) + (2.0 * (irrig - irrig.mean()) + 8.0 * (water - water.mean()))[None, :] + 0.3 * cnoise(12)
td_p += expand(td_b - bmean(td_p))
rh_p = np.clip(100 * es(td_p) / es(tmean_p), 5, 100)
wind_b = clim(WIND)[:, None] * np.exp(ar1(T, 0.6, 0.3))[:, None] * rng.lognormal(0, 0.15, (T, B))
wind_p = expand(wind_b) * wind_factor[None, :] * np.exp(0.1 * cnoise(12))
wind_p *= expand(wind_b / bmean(wind_p))

# NDVI (true), ET0, soil-water bucket
gauss = lambda c, s: np.exp(-0.5 * (np.minimum(abs(doy - c), 365 - abs(doy - c)) / s) ** 2)
rabi, khar = gauss(60, 35), gauss(250, 35)
ndvi_true = np.clip(0.18 + cropland[None, :] * (0.55 * rabi[:, None] * (0.7 + 0.3 * irrig)[None, :]
                    + 0.45 * khar[:, None] * (0.6 + 0.4 * irrig)[None, :]), 0.1, 0.9)
et0 = 0.0023 * (tmean_p + 17.8) * np.sqrt(np.maximum(tmax_p - tmin_p, 0.5)) * ra_mm(lat.mean())[:, None]
cap = whc * 0.6
sm = 0.6 * cap.copy()
sm_frac = np.zeros((T, P)); wl = np.zeros((T, P), bool)
vulnerable = (drain == "poor") | (tpi_z < -0.7)
for t in range(T):
    r = rain[t]
    eff = r - 0.15 * np.maximum(r - 20, 0)
    tot = sm + eff
    excess = np.maximum(tot - cap, 0)
    sm = np.minimum(tot, cap)
    wl[t] = (excess > 15) & vulnerable
    aet = et0[t] * (0.4 + 0.6 * ndvi_true[t]) * np.minimum(1, sm / (0.5 * cap))
    sm = np.maximum(sm - aet, 0.02 * cap)
    irr = (irrig > 0.4) & (ndvi_true[t] > 0.35) & (sm < 0.45 * cap) & (rng.random(P) < 0.5)
    sm = np.where(irr, sm + 45, sm)
    sm = np.minimum(sm, cap)
    sm_frac[t] = sm / cap

# ------------------------------------------------- oracle (synthetic truth)
flat = lambda x: x.ravel()
truth = pd.DataFrame({
    "date": np.repeat(dates.values, P), "panchayat_id": np.tile(pid, T), "block_id": np.tile(block_ids[bidx], T),
    "rain_mm": flat(rain), "tmax_c": flat(tmax_p).round(2), "tmin_c": flat(tmin_p).round(2),
    "rh_mean_pct": flat(rh_p).round(1), "dewpoint_c": flat(td_p).round(2), "wind_kmh": flat(wind_p).round(2),
    "et0_mm": flat(et0).round(2), "soil_moisture_frac": flat(sm_frac).round(3), "waterlog_flag": flat(wl).astype(int)})
truth.to_csv(f"{OUT}/synthetic_oracle/panchayat_daily_SYNTHETIC_TRUTH.csv", index=False)
blk = {"rain": bmean(rain), "tmax": bmean(tmax_p), "tmin": bmean(tmin_p), "rh": bmean(rh_p), "wind": bmean(wind_p)}
pd.DataFrame({"date": np.repeat(dates.values, B), "block_id": np.tile(block_ids, T),
              "rain_mm": flat(blk["rain"]).round(2), "tmax_c": flat(blk["tmax"]).round(2),
              "tmin_c": flat(blk["tmin"]).round(2), "rh_mean_pct": flat(blk["rh"]).round(1),
              "wind_kmh": flat(blk["wind"]).round(2)}
             ).to_csv(f"{OUT}/synthetic_oracle/block_daily_SYNTHETIC_TRUTH.csv", index=False)

# ---------------------------------------- mock NWP block forecasts (lead 1-5)
SRC = {"mock_nwp_a": dict(tb_hot=0.8, tb_cool=-0.5, t0=0.7, t1=0.45, rh_b=-5, rmu=-0.1, r0=0.35, r1=0.15, miss=(.08, .04), fa=(.05, .02)),
       "mock_nwp_b": dict(tb_hot=-0.4, tb_cool=0.3, t0=0.6, t1=0.40, rh_b=3, rmu=0.1, r0=0.30, r1=0.14, miss=(.07, .04), fa=(.06, .02))}
frames = []
for name, q in SRC.items():
    for L in range(1, 6):
        n = lambda sd: rng.normal(0, sd, (T, B))
        hot = blk["tmax"] > 30
        tmax_f = blk["tmax"] + np.where(hot, q["tb_hot"], q["tb_cool"]) + n(q["t0"] + q["t1"] * L)
        tmin_f = blk["tmin"] + 0.7 + n(q["t0"] + q["t1"] * L)
        rh_f = np.clip(blk["rh"] + q["rh_b"] + n(4 + 2 * L), 5, 100)
        wind_f = blk["wind"] * np.exp(rng.normal(0.15, 0.15 + 0.05 * L, (T, B)))
        hit = rng.random((T, B)) > (q["miss"][0] + q["miss"][1] * L)
        fa = rng.random((T, B)) < (q["fa"][0] + q["fa"][1] * L)
        rain_f = np.where(blk["rain"] > 0.1,
                          np.where(hit, blk["rain"] * np.exp(rng.normal(q["rmu"], q["r0"] + q["r1"] * L, (T, B))), 0.0),
                          np.where(fa, rng.gamma(1.0, 3.0, (T, B)), 0.0))
        frames.append(pd.DataFrame({
            "source": name, "block_id": np.tile(block_ids, T), "valid_date": np.repeat(dates.values, B),
            "issue_date": np.repeat((dates - pd.Timedelta(days=L)).values, B), "lead_day": L,
            "rain_mm": flat(rain_f).round(2), "tmax_c": flat(tmax_f).round(2), "tmin_c": flat(tmin_f).round(2),
            "rh_mean_pct": flat(rh_f).round(1), "wind_kmh": flat(wind_f).round(2)}))
pd.concat(frames).to_csv(f"{OUT}/block_forecast_mock_nwp.csv", index=False)

# ------------------------------------------------------- station observations
st_rows, obs = [], []
sid = 0
for b in range(B):
    members = np.where(bidx == b)[0]
    for k, p in enumerate(rng.choice(members, size=min(4, len(members)), replace=False)):
        sid += 1
        typ = "AWS" if k < 2 else "ARG"
        s_id = f"MOCK_{typ}_{sid:02d}"
        st_rows.append({"station_id": s_id, "station_type": typ, "panchayat_id": pid[p], "block_id": block_ids[bidx[p]],
                        "lat": round(lat[p] + rng.normal(0, 0.005), 5), "lon": round(lon[p] + rng.normal(0, 0.005), 5),
                        "elevation_m": round(elev[p], 1)})
        r = np.clip(rain[:, p] * (1 + 0.05 * rng.standard_normal(T)), 0, None)
        d = pd.DataFrame({"date": dates.values, "station_id": s_id,
                          "rain_mm": np.round(r * 2) / 2 if typ == "ARG" else r.round(1)})
        if typ == "AWS":
            d["tmax_c"] = (tmax_p[:, p] + rng.normal(0, 0.3, T)).round(1)
            d["tmin_c"] = (tmin_p[:, p] + rng.normal(0, 0.3, T)).round(1)
            d["rh_mean_pct"] = np.clip(rh_p[:, p] + rng.normal(0, 2.5, T), 5, 100).round(0)
            d["wind_kmh"] = np.clip(wind_p[:, p] + rng.normal(0, 0.6, T), 0, None).round(1)
        else:
            for c in ("tmax_c", "tmin_c", "rh_mean_pct", "wind_kmh"): d[c] = np.nan
        mask = rng.random(T) < 0.04
        if rng.random() < 0.3:
            s0 = rng.integers(0, T - 45); mask[s0:s0 + rng.integers(20, 45)] = True
        d.loc[mask, ["rain_mm", "tmax_c", "tmin_c", "rh_mean_pct", "wind_kmh"]] = np.nan
        obs.append(d)
pd.DataFrame(st_rows).to_csv(f"{OUT}/stations.csv", index=False)
pd.concat(obs).to_csv(f"{OUT}/station_observations_mock.csv", index=False)

# ------------------------------- weekly satellite features (NDVI, LST) with gaps
wk = np.arange(0, T - 6, 7)
sat = []
for s in wk:
    sl = slice(s, s + 7)
    nd = ndvi_true[sl].mean(0)
    gap = rng.random(P) < (0.4 if month[s] in (7, 8, 9) else 0.08)
    lst = tmax_p[sl].mean(0) + 6 * (1 - nd) + rng.normal(0, 1.5, P)
    sat.append(pd.DataFrame({"week_start": dates[s], "panchayat_id": pid,
                             "ndvi": np.where(gap, np.nan, nd + rng.normal(0, 0.03, P)).round(3),
                             "lst_day_c": np.where(gap, np.nan, lst).round(1)}))
pd.concat(sat).to_csv(f"{OUT}/satellite_weekly_mock.csv", index=False)

# ------------------------------------------------------- crops and calendar
DUR = {"wheat": 145, "mustard": 130, "gram": 120, "paddy": 120, "cotton": 180, "bajra": 85}
seasons = [("rabi_2022_23", 2022, "rabi"), ("kharif_2023", 2023, "kharif"), ("rabi_2023_24", 2023, "rabi"),
           ("kharif_2024", 2024, "kharif"), ("rabi_2024_25", 2024, "rabi")]
crop_rows = []
for p in range(P):
    kh = "paddy" if (irrig[p] > 0.65 and clay[p] > 24) else ("cotton" if irrig[p] > 0.45 else "bajra")
    rb = "wheat" if rng.random() < 0.6 + 0.3 * irrig[p] else ("mustard" if rng.random() < 0.7 else "gram")
    offr, offk = rng.integers(-8, 15), rng.integers(-7, 10)
    for name, yr, kind in seasons:
        crop = rb if kind == "rabi" else kh
        base = pd.Timestamp(f"{yr}-11-15") if kind == "rabi" else pd.Timestamp(
            {"paddy": f"{yr}-07-01", "cotton": f"{yr}-05-10", "bajra": f"{yr}-07-05"}[crop])
        sow = base + pd.Timedelta(days=int((offr if kind == "rabi" else offk) + rng.integers(-5, 6)))
        crop_rows.append({"panchayat_id": pid[p], "season": name, "crop": crop, "sowing_date": sow.date(),
                          "expected_harvest_date": (sow + pd.Timedelta(days=DUR[crop])).date(),
                          "crop_area_fraction": round(float(rng.uniform(0.5, 0.9)), 2)})
pd.DataFrame(crop_rows).to_csv(f"{OUT}/panchayat_crops_mock.csv", index=False)

cal = [  # crop, stage, das_start, das_end, tmax_alert_c, tmin_alert_c, drought_sens, waterlog_sens, operations
    ("wheat", "germination_crown_root", 0, 25, None, 4, "high", "medium", "sowing; first irrigation ~CRI"),
    ("wheat", "tillering", 25, 60, None, 2, "medium", "medium", "top-dress nitrogen; weed control"),
    ("wheat", "jointing_booting", 60, 90, 30, 0, "high", "medium", "irrigation; spray timing"),
    ("wheat", "flowering_grain_fill", 90, 130, 34, 0, "high", "low", "terminal heat-stress watch; light irrigation"),
    ("wheat", "maturity_harvest", 130, 145, None, None, "low", "low", "harvest planning; avoid rain on harvested produce"),
    ("paddy", "transplant_establishment", 0, 20, 38, None, "medium", "low", "standing water; nursery care"),
    ("paddy", "tillering", 20, 55, 38, None, "medium", "low", "nitrogen top-dress"),
    ("paddy", "panicle_flowering", 55, 90, 35, None, "high", "medium", "avoid water stress; disease watch"),
    ("paddy", "grain_fill_maturity", 90, 120, 38, None, "medium", "high", "drain field; harvest window"),
    ("cotton", "germination_seedling", 0, 30, 42, None, "medium", "high", "avoid waterlogging"),
    ("cotton", "squaring_flowering", 30, 100, 40, None, "high", "high", "irrigation; pest scouting"),
    ("cotton", "boll_development_picking", 100, 180, 40, None, "medium", "high", "spray timing; picking before rain"),
    ("mustard", "vegetative", 0, 45, None, 0, "medium", "high", "thinning; irrigation"),
    ("mustard", "flowering_pod", 45, 100, 30, 0, "high", "high", "aphid watch; frost/fog risk"),
    ("mustard", "maturity", 100, 130, None, None, "low", "medium", "harvest timing"),
    ("bajra", "establishment", 0, 25, 42, None, "medium", "high", "gap filling"),
    ("bajra", "tillering_boot", 25, 55, 42, None, "high", "high", "nitrogen top-dress"),
    ("bajra", "flowering_grain", 55, 85, 40, None, "high", "medium", "heat/dry-spell watch"),
]
pd.DataFrame(cal, columns=["crop", "stage", "das_start", "das_end", "tmax_alert_c", "tmin_alert_c",
                           "drought_sensitivity", "waterlog_sensitivity", "key_operations"]
             ).assign(status="PLACEHOLDER_needs_expert_review").to_csv(f"{OUT}/crop_calendar_PLACEHOLDER.csv", index=False)

# --------------------------------------------- mock farmer feedback (for loop)
n_fb = 800
ti, pi = rng.integers(0, T, n_fb), rng.integers(0, P, n_fb)
r_true = rain[ti, pi]
correct = rng.random(n_fb) < 0.88
said_rain = np.where(correct, r_true > 1, r_true <= 1)
bins = np.where(r_true < 1, "none", np.where(r_true < 10, "light", np.where(r_true < 35, "moderate", "heavy")))
pd.DataFrame({"date": dates.values[ti], "panchayat_id": pid[pi], "reported_rain": np.where(said_rain, "yes", "no"),
              "reported_intensity": np.where(correct, bins, rng.choice(["none", "light", "moderate", "heavy"], n_fb)),
              "channel": rng.choice(["whatsapp", "ivr", "app"], n_fb, p=[.5, .3, .2])}
             ).sort_values("date").to_csv(f"{OUT}/farmer_feedback_mock.csv", index=False)

# --------------------------------------------------------------- GeoJSON
try:
    from shapely.geometry import MultiPoint, Point, box, mapping
    from shapely.ops import voronoi_diagram, unary_union
    pts = [Point(x, y) for x, y in zip(lon, lat)]
    env = box(lon.min() - 0.03, lat.min() - 0.02, lon.max() + 0.03, lat.max() + 0.02)
    vd = list(voronoi_diagram(MultiPoint(pts), envelope=env).geoms)
    cells = [next(g for g in vd if g.contains(pt)).intersection(env) for pt in pts]
    feats = [{"type": "Feature", "properties": {"panchayat_id": pid[i], "block_id": block_ids[bidx[i]]},
              "geometry": mapping(cells[i])} for i in range(P)]
    json.dump({"type": "FeatureCollection", "features": feats}, open(f"{OUT}/panchayats_SYNTHETIC.geojson", "w"))
    bf = [{"type": "Feature", "properties": {"block_id": block_ids[b]},
           "geometry": mapping(unary_union([cells[i] for i in np.where(bidx == b)[0]]))} for b in range(B)]
    json.dump({"type": "FeatureCollection", "features": bf}, open(f"{OUT}/blocks_SYNTHETIC.geojson", "w"))
    geo = "ok"
except Exception as e:
    geo = f"skipped ({e})"

# --------------------------------------------------------------- QA summary
wet_p = rain > 1
qa = {
    "seed": SEED, "days": int(T), "n_blocks": int(B), "n_panchayats": int(P), "n_stations": int(sid),
    "geojson": geo,
    "block_mean_consistency_max_abs_err": {
        "rain_mm": float(np.abs(bmean(rain) - blk["rain"]).max()), "tmax_c": float(np.abs(bmean(tmax_p) - blk["tmax"]).max())},
    "within_block_spread_planted": {
        "tmax_std_c_mean": float((tmax_p - expand(bmean(tmax_p))).std()),
        "tmin_std_c_mean": float((tmin_p - expand(bmean(tmin_p))).std()),
        "wet_day_rain_cv_within_block": float(np.nanmean(np.where(wet_p.any(1, keepdims=True), rain.std(1) / np.maximum(rain.mean(1), 1e-6), np.nan))),
        "share_panchayat_days_rain_gt1mm": float(wet_p.mean())},
    "annual_rain_mm_district_mean": float(rain.mean() * 365.25),
    "rows": {"truth": int(len(truth)), "block_forecast": int(sum(len(f) for f in frames)),
             "station_obs": int(sum(len(o) for o in obs))},
}
json.dump(qa, open(f"{OUT}/mock_data_summary.json", "w"), indent=2)
print(json.dumps(qa, indent=2))
