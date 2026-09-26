"""Snapshots and the endpoints that read them (built with the small test bundle from conftest).

Covers: snapshot values equal API values, block consistency inside every snapshot, explain (exactly 3
reasons with the right signs, none when there is nothing to explain), the change tracker with and
without a previous snapshot, determinism, the soil-moisture start state, and request latency.
"""

from __future__ import annotations

import shutil
import statistics
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from gramdrishti.api import schemas as s
from gramdrishti.api.main import PREFIX, create_app
from gramdrishti.api.service import EVENT_COLS, Service, num
from gramdrishti.contract.pick_demo_dates import load_demo_dates
from gramdrishti.data import loaders
from gramdrishti.data.config import RECONCILE_TOL, VARS
from gramdrishti.explain import texts
from gramdrishti.explain.shap_explain import GROUPS, NEGLIGIBLE_DELTA, check_groups, shap_contrasts
from gramdrishti.features.table import feature_names, load_inputs, make_table
from gramdrishti.pipeline.predict import predict_table
from gramdrishti.pipeline.run_daily import FRAMES, SoilState, build_snapshot, read_snapshot, write_snapshot

from .conftest import needs_oracle

pytestmark = needs_oracle
MAIN = date(2024, 9, 9)
DEMO = [date.fromisoformat(d.date) for d in load_demo_dates()]


@pytest.fixture(scope="module")
def client(snapshot_dir: Path) -> TestClient:
    svc = Service(clock=lambda: datetime(2024, 9, 9, 9, 30), snapshot_dir=snapshot_dir)
    return TestClient(create_app(svc))


def _get(client: TestClient, path: str) -> dict:
    r = client.get(PREFIX + path)
    assert r.status_code == 200, (path, r.text[:300])
    return r.json()


def _all_snapshots(root: Path) -> list[Path]:
    return sorted(p for p in root.iterdir() if p.is_dir())


# ------------------------------------------------------------------ snapshot = API
def test_snapshot_values_equal_forecast_panchayat(client: TestClient, snapshot_dir: Path) -> None:
    f = read_snapshot(snapshot_dir, MAIN).forecast
    for pid in ("MP0103", "MP0302", "MP0412"):
        body = _get(client, f"/forecast/panchayat/{pid}?issue_date={MAIN}")
        assert body["provenance"] == "computed" and body["model_version"] == "test-small"
        assert body["thresholds_status"] == "placeholder"
        rows = f[f["panchayat_id"] == pid].set_index("lead_day")
        assert [d["lead_day"] for d in body["days"]] == [1, 2, 3, 4, 5]
        for day in body["days"]:
            r = rows.loc[day["lead_day"]]
            assert day["date"] == r["valid_date"].date().isoformat()
            for v in VARS:
                q = day[v]
                assert (q["p10"], q["p50"], q["p90"], q["mean"]) == tuple(
                    num(r[f"{v}_{k}"]) for k in ("p10", "p50", "p90", "mean"))
                assert q["block"] == num(r[f"b0_{v}"]) and q["block_corrected"] == num(r[f"b1_{v}"])
            for ev, col in EVENT_COLS.items():
                assert day["prob"][ev.value] == pytest.approx(r[col], abs=0.005)
            assert day["derived"]["et0_mm"] == num(r["et0_mm"], 1)
            assert day["derived"]["soil_moisture_frac"] == num(r["soil_moisture_frac"])
            assert day["derived"]["waterlog_risk"] == r["waterlog_risk"]


@pytest.mark.parametrize("var", [v.value for v in s.Var])
def test_snapshot_values_equal_forecast_map(client: TestClient, snapshot_dir: Path, var: str) -> None:
    snap = read_snapshot(snapshot_dir, MAIN)
    for lead in (1, 4):
        body = _get(client, f"/forecast/map?issue_date={MAIN}&lead_day={lead}&var={var}")
        f = snap.forecast[snap.forecast["lead_day"] == lead].set_index("panchayat_id")
        assert len(body["panchayat_layer"]) == len(f)
        for p in body["panchayat_layer"]:
            r = f.loc[p["panchayat_id"]]
            assert (p["p10"], p["p50"], p["p90"], p["mean"], p["block_value"]) == (
                num(r[f"{var}_p10"]), num(r[f"{var}_p50"]), num(r[f"{var}_p90"]), num(r[f"{var}_mean"]),
                num(r[f"b0_{var}"]))
            assert p["delta"] == num(r[f"{var}_p50"] - r[f"b0_{var}"])
            if var == "rain":
                assert p["event"] == "rain_ge_2_5mm"
                assert p["prob_event"] == pytest.approx(r["prob_rain_ge_2_5"], abs=0.005)
            else:
                assert p["prob_event"] is None and p["event"] is None
        b = snap.block[snap.block["lead_day"] == lead].set_index("block_id")
        for bl in body["block_layer"]:
            assert bl["value"] == num(b.loc[bl["block_id"], f"b0_{var}"])
            assert bl["corrected"] == num(b.loc[bl["block_id"], f"b1_{var}"])
            # the user's check through the API: block average of Panchayat means = corrected block value,
            # up to rounding (each mean and the block value are rounded to 0.01: at most 0.005 + 0.005)
            means = [p["mean"] for p in body["panchayat_layer"] if p["block_id"] == bl["block_id"]]
            assert np.mean(means) == pytest.approx(bl["corrected"], abs=0.0101)


def test_two_panchayats_in_one_block_differ(client: TestClient) -> None:
    a = _get(client, f"/forecast/panchayat/MP0101?issue_date={MAIN}")["days"][0]
    b = _get(client, f"/forecast/panchayat/MP0102?issue_date={MAIN}")["days"][0]
    assert a["tmax"]["block"] == b["tmax"]["block"]
    assert a["tmax"]["mean"] != b["tmax"]["mean"]


# ------------------------------------------------------------------ invariants inside snapshots
def test_reconcile_invariant_and_constraints_in_every_snapshot(snapshot_dir: Path) -> None:
    dirs = _all_snapshots(snapshot_dir)
    assert len(dirs) == 16
    for d in dirs:
        snap = read_snapshot(snapshot_dir, date.fromisoformat(d.name))
        f = snap.forecast
        g = f.groupby(["block_id", "lead_day"])
        for v in [*VARS, "td"]:
            err = (g[f"{v}_mean"].mean() - g[f"b1_{v}"].first()).abs().max()
            assert err < RECONCILE_TOL, (d.name, v, err)
        for v in VARS:
            assert (f[f"{v}_p10"] <= f[f"{v}_p50"]).all() and (f[f"{v}_p50"] <= f[f"{v}_p90"]).all(), v
            assert np.allclose(snap.block[f"pmean_{v}_mean"], snap.block[f"b1_{v}"], atol=RECONCILE_TOL)
        assert (f["rain_p10"] >= 0).all() and (f["wind_p10"] >= 0).all()
        assert f["rh_p10"].between(0, 100).all() and f["rh_p90"].between(0, 100).all()
        assert (f["tmin_p50"] < f["tmax_p50"]).all()
        probs = f[[c for c in f.columns if c.startswith("prob_rain_ge_")]].to_numpy()
        assert ((probs >= 0) & (probs <= 1)).all() and (np.diff(probs, axis=1) <= 1e-12).all()
        assert set(f["lead_day"]) == {1, 2, 3, 4, 5} and f["panchayat_id"].nunique() * 5 == len(f)


def test_manifest_and_roles(snapshot_dir: Path) -> None:
    import json

    index = json.loads((snapshot_dir / "index.json").read_text())
    for d in DEMO:
        assert index["snapshots"][d.isoformat()] == "demo"
        assert index["snapshots"][(d - timedelta(days=1)).isoformat()] == "previous"
    m = read_snapshot(snapshot_dir, MAIN).manifest
    assert m["data_mode"] == "mock" and m["model_version"] == "test-small"
    assert "MOCK ONLY" in m["initial_soil_moisture"]
    assert set(m["files"]) == {f"{n}.parquet" for n in FRAMES}


# ------------------------------------------------------------------ explain
def test_every_feature_has_an_explain_group() -> None:
    check_groups(feature_names())
    for g, (_, _, kind) in GROUPS.items():
        text = texts.phrase_for(g, 1, "clay_loam")
        assert text and text != texts.SAME_PHRASE or kind == "numeric", g


def test_contrasts_sum_to_the_served_departure(small_bundle) -> None:  # noqa: ANN001
    """For additive variables the group contrasts add up exactly to mean - corrected block forecast."""
    inputs = load_inputs()
    table = make_table("infer", inputs, small_bundle.bias, small_bundle.encodings, issue_dates=[MAIN])
    pred = predict_table(small_bundle.models, table, small_bundle.offsets)
    for var in ("tmax", "tmin"):
        c = shap_contrasts(small_bundle.models, table, var)
        assert np.allclose(c.sum(axis=1), pred[f"{var}_mean"] - pred[f"b1_{var}"], atol=1e-6), var


@pytest.mark.parametrize("var", [v.value for v in s.Var])
def test_explain_three_reasons_with_the_right_signs(client: TestClient, snapshot_dir: Path, var: str) -> None:
    snap = read_snapshot(snapshot_dir, MAIN)
    f = snap.forecast[snap.forecast["lead_day"] == 1].set_index("panchayat_id")
    e = snap.explain[(snap.explain["lead_day"] == 1) & (snap.explain["var"] == var)]
    checked = 0
    for pid in ("MP0101", "MP0103", "MP0302", "MP0305", "MP0412", "MP0508"):
        body = _get(client, f"/explain/{pid}?issue_date={MAIN}&lead_day=1&var={var}")
        s.Explain.model_validate(body)
        assert body["provenance"] == "computed" and body["method"].startswith("shap_tree_explainer")
        delta = f.loc[pid, f"{var}_mean"] - f.loc[pid, f"b1_{var}"]
        assert body["delta_vs_block"] == num(delta)
        if abs(delta) < NEGLIGIBLE_DELTA[var]:
            assert body["reasons"] == []
            continue
        rows = e[e["panchayat_id"] == pid].sort_values("rank")
        assert len(body["reasons"]) == 3 and rows["rank"].tolist() == [1, 2, 3]
        assert (rows["contribution"].abs().diff().dropna() <= 0).all()      # largest first
        for reason, (_, r) in zip(body["reasons"], rows.iterrows(), strict=True):
            assert reason["feature"] == r["feature"]
            want = texts.EFFECT_POS[var] if r["contribution"] > 0 else texts.EFFECT_NEG[var]
            assert reason["effect"] == want
            assert texts.EFFECT_WORD[want] in reason["text"]["en"]
            assert reason["text"]["hi"] is None and reason["text"]["pa"] is None
        checked += 1
    assert checked >= 1


def test_explain_direction_words_follow_the_feature(snapshot_dir: Path, static) -> None:  # noqa: ANN001
    e = read_snapshot(snapshot_dir, MAIN).explain
    irr = e[e["feature"] == "irrigated"]
    assert not irr.empty
    block_mean = static.groupby("block_id")["irrigated_frac"].transform("mean")
    above = dict(zip(static["panchayat_id"], static["irrigated_frac"] > block_mean, strict=True))
    for _, r in irr.iterrows():
        assert r["text_en"].startswith("More irrigated" if above[r["panchayat_id"]] else "Fewer irrigated")


def test_explain_has_no_reasons_where_the_block_is_dry(client: TestClient, snapshot_dir: Path) -> None:
    f = read_snapshot(snapshot_dir, MAIN).forecast
    dry = f[(f["b1_rain"] == 0) & (f["lead_day"] == 1)]
    assert not dry.empty, "expected a dry block on 2024-09-09"
    pid = dry["panchayat_id"].iloc[0]
    body = _get(client, f"/explain/{pid}?issue_date={MAIN}&lead_day=1&var=rain")
    assert body["reasons"] == [] and body["delta_vs_block"] == 0.0


# ------------------------------------------------------------------ changes
def test_changes_against_the_previous_day(client: TestClient, snapshot_dir: Path) -> None:
    body = _get(client, f"/forecast/changes/MP0103?issue_date={MAIN}")
    assert body["previous_issue_date"] == "2024-09-08" and body["provenance"] == "computed"
    cur = read_snapshot(snapshot_dir, MAIN).forecast
    prev = read_snapshot(snapshot_dir, date(2024, 9, 8)).forecast
    cur = cur[cur["panchayat_id"] == "MP0103"].set_index("valid_date")
    prev = prev[prev["panchayat_id"] == "MP0103"].set_index("valid_date")
    common = sorted(set(cur.index) & set(prev.index))
    assert len(common) == 4 and len(body["changes"]) == 4 * len(VARS)
    for ch in body["changes"]:
        vd = pd.Timestamp(ch["valid_date"])
        assert ch["current_p50"] == num(cur.loc[vd, f"{ch['var']}_p50"])
        assert ch["previous_p50"] == num(prev.loc[vd, f"{ch['var']}_p50"])
    for ev in body["event_changes"]:
        col = EVENT_COLS[s.RainEvent(ev["event"])]
        vd = pd.Timestamp(ev["valid_date"])
        assert abs(cur.loc[vd, col] - prev.loc[vd, col]) >= 0.15


def test_changes_without_a_previous_snapshot(snapshot_dir: Path, tmp_path: Path) -> None:
    shutil.copytree(snapshot_dir / DEMO[0].isoformat(), tmp_path / DEMO[0].isoformat())
    c = TestClient(create_app(Service(snapshot_dir=tmp_path)))
    body = _get(c, f"/forecast/changes/MP0103?issue_date={DEMO[0]}")
    s.ForecastChanges.model_validate(body)
    assert body["previous_issue_date"] is None and body["changes"] == [] and body["event_changes"] == []
    assert body["summary"]["en"] == "No earlier forecast to compare with."
    # and a date without any snapshot is a clear 503, not a crash
    r = c.get(f"{PREFIX}/forecast/map?issue_date={MAIN}&lead_day=1&var=rain")
    assert r.status_code == 503 and r.json()["error"]["code"] == "not_computed"


# ------------------------------------------------------------------ builder
def test_build_is_deterministic(small_bundle, tmp_path: Path) -> None:  # noqa: ANN001
    inputs = load_inputs()
    a = write_snapshot(build_snapshot(small_bundle, inputs, MAIN, SoilState()), tmp_path / "a")
    b = write_snapshot(build_snapshot(small_bundle, inputs, MAIN, SoilState()), tmp_path / "b")
    for name in ["manifest.json", *[f"{n}.parquet" for n in FRAMES]]:
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


def test_soil_start_state_is_the_day_before_issue(snapshot_dir: Path) -> None:
    f = read_snapshot(snapshot_dir, MAIN).forecast
    truth = loaders.load_truth()  # MOCK ONLY: checking the documented start state
    before = truth[truth["date"] == pd.Timestamp(MAIN - timedelta(days=1))].set_index("panchayat_id")
    lead1 = f[f["lead_day"] == 1].set_index("panchayat_id")
    assert np.allclose(lead1["soil_moisture_frac_start"], before.loc[lead1.index, "soil_moisture_frac"])


# ------------------------------------------------------------------ latency
def test_median_latency_under_200_ms(client: TestClient) -> None:
    paths = [f"/forecast/map?issue_date={MAIN}&lead_day=1&var=rain",
             f"/forecast/panchayat/MP0103?issue_date={MAIN}",
             "/observed/panchayat/MP0302?from=2024-09-10&to=2024-09-14",
             f"/explain/MP0103?issue_date={MAIN}&lead_day=1&var=tmax",
             f"/forecast/changes/MP0103?issue_date={MAIN}"]
    for p in paths:                                   # warm caches (first request reads parquet and CSVs)
        _get(client, p)
    times = {p: [] for p in paths}
    for _ in range(20):
        for p in paths:
            t0 = time.perf_counter()
            _get(client, p)
            times[p].append((time.perf_counter() - t0) * 1000)
    medians = {p.split("?")[0]: statistics.median(t) for p, t in times.items()}
    overall = statistics.median([x for t in times.values() for x in t])
    rounded = {k: round(v, 1) for k, v in medians.items()}
    print("\nmedian ms per endpoint:", rounded, "overall", round(overall, 1))
    assert overall < 200 and max(medians.values()) < 200
