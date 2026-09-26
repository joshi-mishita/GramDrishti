"""API tests: every route answers for the demo dates, validates against its model, and never emits NaN."""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from gramdrishti.api import schemas as s
from gramdrishti.api.main import PREFIX, create_app
from gramdrishti.api.service import Service
from gramdrishti.contract.pick_demo_dates import load_demo_dates

from .conftest import needs_oracle

pytestmark = needs_oracle

DEMO = [d.date for d in load_demo_dates()]
MAIN = "2024-09-09"
PID = "MP0103"


@pytest.fixture(scope="module")
def client(snapshot_dir, tmp_path_factory: pytest.TempPathFactory) -> TestClient:  # noqa: ANN001
    db = tmp_path_factory.mktemp("db") / "api.sqlite"
    svc = Service(clock=lambda: datetime(2024, 9, 9, 9, 30), snapshot_dir=snapshot_dir, db_path=db)
    return TestClient(create_app(svc))


def _walk_finite(x: Any, path: str = "$") -> None:
    """Fail on any non-finite number or NaN-like string anywhere in a JSON document."""
    if isinstance(x, float):
        assert math.isfinite(x), f"non-finite number at {path}"
    elif isinstance(x, str):
        assert x not in ("NaN", "nan", "Infinity", "-Infinity"), f"NaN string at {path}"
    elif isinstance(x, dict):
        for k, v in x.items():
            _walk_finite(v, f"{path}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            _walk_finite(v, f"{path}[{i}]")


def _get_ok(client: TestClient, path: str, model: type[s.ApiModel]) -> dict:
    r = client.get(PREFIX + path)
    assert r.status_code == 200, (path, r.text[:300])
    body = json.loads(r.text, parse_constant=lambda c: pytest.fail(f"{c} in {path}"))
    _walk_finite(body)
    model.model_validate(body)
    return body


def _routes(d: str) -> list[tuple[str, type[s.ApiModel]]]:
    return [
        ("/health", s.Health), ("/meta", s.Meta),
        ("/geo/panchayats", s.PanchayatCollection), ("/geo/blocks", s.BlockCollection),
        *[(f"/forecast/map?issue_date={d}&lead_day={lead}&var={v.value}", s.ForecastMap)
          for v in s.Var for lead in (1, 5)],
        (f"/forecast/panchayat/{PID}?issue_date={d}", s.PanchayatForecast),
        (f"/forecast/panchayat/MP0302?issue_date={d}", s.PanchayatForecast),
        (f"/observed/panchayat/{PID}?from={d}&to={d}", s.Observed),
        (f"/observed/panchayat/MP0302?from={d}&to={d}", s.Observed),
        *[(f"/explain/{PID}?issue_date={d}&lead_day=1&var={v.value}", s.Explain) for v in s.Var],
        (f"/forecast/changes/{PID}?issue_date={d}", s.ForecastChanges),
        *[(f"/risk?issue_date={d}&lead_day=1&type={t.value}", s.Risk) for t in s.RiskType],
        (f"/priority?issue_date={d}&horizon_days=3", s.Priority),
        (f"/advisories?issue_date={d}", s.AdvisoryList),
        ("/farmers/F001", s.Farmer), (f"/farmers/F001/advice?issue_date={d}", s.FarmerAdvice),
        ("/verification/summary", s.VerificationSummary),
        *[(f"/verification/reliability?event={e.value}", s.Reliability) for e in s.RainEvent],
        ("/verification/coverage", s.Coverage), ("/verification/regions", s.Regions),
        *[(f"/impact?season=monsoon_2024&decision={x.value}", s.Impact) for x in s.Decision],
        (f"/data-quality?issue_date={d}", s.DataQuality),
    ]


@pytest.mark.parametrize(("path", "model"), _routes(MAIN), ids=lambda p: str(p)[:70])
def test_every_route_ok_on_main_date(client: TestClient, path: str, model: type[s.ApiModel]) -> None:
    body = _get_ok(client, path, model)
    if isinstance(body, dict) and "data_mode" in model.model_fields:
        assert body["data_mode"] == "mock"


@pytest.mark.parametrize("d", DEMO)
def test_forecast_routes_ok_on_every_demo_date(client: TestClient, d: str) -> None:
    for path, model in _routes(d):
        if "issue_date" in path:
            _get_ok(client, path, model)


def test_meta_lists_demo_dates_with_labels(client: TestClient) -> None:
    m = _get_ok(client, "/meta", s.Meta)
    assert m["available_issue_dates"] == DEMO == sorted(DEMO)
    info = m["issue_date_info"]
    assert [i["date"] for i in info] == DEMO
    splits = [i["split"] for i in info]
    assert splits.count("train") <= 2 and splits.count("calib") == 0
    assert splits.count("test") == len(DEMO) - splits.count("train") >= 6
    assert all("replay" in i["label"].lower() for i in info if i["split"] == "train")
    assert m["languages"] == ["en", "hi", "pa"]
    assert {v["var"]: v["unit"] for v in m["vars"]} == {"rain": "mm", "tmax": "C", "tmin": "C", "rh": "%",
                                                       "wind": "km/h"}


def test_geojson_is_lon_lat(client: TestClient, static) -> None:  # noqa: ANN001
    g = _get_ok(client, "/geo/panchayats", s.PanchayatCollection)
    assert len(g["features"]) == len(static)
    st = static.set_index("panchayat_id")
    for f in g["features"]:
        ring = f["geometry"]["coordinates"][0]
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        row = st.loc[f["properties"]["panchayat_id"]]
        assert min(xs) <= row["lon"] <= max(xs), "first coordinate must be longitude"
        assert min(ys) <= row["lat"] <= max(ys), "second coordinate must be latitude"
        assert f["properties"]["block_id"] == row["block_id"]
    b = _get_ok(client, "/geo/blocks", s.BlockCollection)
    for f in b["features"]:
        for ring in f["geometry"]["coordinates"]:
            assert all(68 < x < 98 and 6 < y < 38 for x, y in ring)


def test_forecast_map_layers(client: TestClient, static) -> None:  # noqa: ANN001
    m = _get_ok(client, f"/forecast/map?issue_date={MAIN}&lead_day=1&var=rain", s.ForecastMap)
    assert m["valid_date"] == "2024-09-10"
    assert len(m["panchayat_layer"]) == len(static)
    assert len(m["block_layer"]) == static["block_id"].nunique()
    blocks = {b["block_id"]: b["value"] for b in m["block_layer"]}
    for p in m["panchayat_layer"]:
        assert p["p10"] <= p["p50"] <= p["p90"]
        assert p["block_value"] == blocks[p["block_id"]]
        assert p["delta"] == pytest.approx(p["p50"] - p["block_value"], abs=0.011)
        assert p["event"] == "rain_ge_2_5mm" and 0 <= p["prob_event"] <= 1


@pytest.mark.parametrize("path", [
    f"/forecast/panchayat/MP9999?issue_date={MAIN}",
    f"/forecast/changes/MP9999?issue_date={MAIN}",
    f"/explain/MP9999?issue_date={MAIN}&lead_day=1&var=tmax",
    "/observed/panchayat/MP9999?from=2024-09-10&to=2024-09-12",
    "/advisories/ADV-does-not-exist",
    "/advisories?panchayat_id=MP9999",
    "/audio/ADV-does-not-exist?lang=hi",
    "/farmers/F999",
    "/farmers/F999/advice?issue_date=2024-09-09",
    f"/forecast/panchayat/{PID}?issue_date=2024-09-10",
    "/impact?season=kharif_1999",
    "/no/such/route",
])
def test_unknown_ids_give_contract_error(client: TestClient, path: str) -> None:
    r = client.get(PREFIX + path)
    assert r.status_code == 404
    body = r.json()
    s.ErrorResponse.model_validate(body)
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message"}
    assert body["error"]["message"]


@pytest.mark.parametrize("path", [
    f"/forecast/map?issue_date={MAIN}&lead_day=0&var=rain",
    f"/forecast/map?issue_date={MAIN}&lead_day=1&var=snow",
    "/forecast/map?issue_date=not-a-date&lead_day=1&var=rain",
    "/verification/reliability?event=rain_ge_7mm",
])
def test_invalid_params_give_contract_error(client: TestClient, path: str) -> None:
    r = client.get(PREFIX + path)
    assert r.status_code == 422
    body = r.json()
    s.ErrorResponse.model_validate(body)
    assert body["error"]["code"] == "validation_error"


def test_observed_range_checks(client: TestClient) -> None:
    r = client.get(PREFIX + f"/observed/panchayat/{PID}?from=2024-09-12&to=2024-09-10")
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"
    r = client.get(PREFIX + f"/observed/panchayat/{PID}?from=2024-01-01&to=2024-12-31")
    assert r.status_code == 400


def test_observed_sources(client: TestClient) -> None:
    st = _get_ok(client, f"/observed/panchayat/{PID}?from=2024-09-10&to=2024-09-14", s.Observed)
    assert st["source"] == "station" and st["station_id"] == "MOCK_AWS_01" and len(st["days"]) == 5
    arg = _get_ok(client, "/observed/panchayat/MP0412?from=2024-09-10&to=2024-09-14", s.Observed)
    assert arg["source"] == "station" and all(d["tmax"] is None for d in arg["days"])
    tr = _get_ok(client, "/observed/panchayat/MP0302?from=2024-09-10&to=2024-09-14", s.Observed)
    assert tr["source"] == "synthetic_truth" and tr["station_id"] is None


def test_review_flow_reaches_farmer(client: TestClient) -> None:
    queue = _get_ok(client, f"/advisories?status=draft&issue_date={MAIN}&panchayat_id={PID}", s.AdvisoryList)
    assert queue["total"] >= 1
    adv = queue["items"][0]
    assert adv["thresholds_status"] == "placeholder" and adv["translation_status"] == "needs_native_review"

    r = client.post(f"{PREFIX}/advisories/{adv['id']}/review", json={"action": "edit", "reviewer": "Officer"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"

    body = {"action": "approve", "reviewer": "Officer Demo", "note": "ok"}
    r = client.post(f"{PREFIX}/advisories/{adv['id']}/review", json=body)
    assert r.status_code == 200
    out = s.Advisory.model_validate(r.json())
    assert out.status == s.Status.approved and out.reviewed_by == "Officer Demo"
    assert [a.action for a in out.audit] == ["created", "approved"]

    advice = _get_ok(client, f"/farmers/F001/advice?issue_date={MAIN}", s.FarmerAdvice)
    assert adv["id"] in [a["id"] for a in advice["items"]]

    r = client.post(f"{PREFIX}/advisories/{adv['id']}/review",
                    json={"action": "reject", "reviewer": "Officer Demo", "note": "wrong crop"})
    assert r.json()["status"] == "rejected" and len(r.json()["audit"]) == 3
    advice = _get_ok(client, f"/farmers/F001/advice?issue_date={MAIN}", s.FarmerAdvice)
    assert adv["id"] not in [a["id"] for a in advice["items"]]


def test_review_unknown_body_field_is_rejected(client: TestClient) -> None:
    adv = _get_ok(client, f"/advisories?issue_date={MAIN}", s.AdvisoryList)["items"][0]
    r = client.post(f"{PREFIX}/advisories/{adv['id']}/review",
                    json={"action": "approve", "reviewer": "x", "surprise": 1})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_feedback(client: TestClient) -> None:
    body = {"panchayat_id": PID, "date": "2024-09-10", "reported_rain": True, "intensity": "heavy",
            "channel": "whatsapp"}
    r = client.post(PREFIX + "/feedback", json=body)
    assert r.status_code == 200
    out = s.FeedbackResponse.model_validate(r.json())
    assert out.stored and out.feedback.intensity == s.Intensity.heavy
    r = client.post(PREFIX + "/feedback", json={**body, "panchayat_id": "MP9999"})
    assert r.status_code == 404
    r = client.post(PREFIX + "/feedback", json={**body, "intensity": "torrential"})
    assert r.status_code == 422


def test_audio_missing_is_404_contract_shape(client: TestClient) -> None:
    adv = _get_ok(client, f"/advisories?issue_date={MAIN}", s.AdvisoryList)["items"][0]
    r = client.get(f"{PREFIX}/audio/{adv['id']}?lang=hi")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_placeholders_are_labelled(client: TestClient) -> None:
    for path, model in [("/verification/summary", s.VerificationSummary),
                        ("/verification/coverage", s.Coverage),
                        ("/impact?season=monsoon_2024", s.Impact)]:
        body = _get_ok(client, path, model)
        assert body["provenance"] == "placeholder" and body["data_mode"] == "mock"
        assert any("PLACEHOLDER" in n for n in body["notes"])
    imp = _get_ok(client, "/impact?season=monsoon_2024", s.Impact)
    for side in ("model", "block_baseline"):
        assert sum(imp[side].values()) == imp["n_decisions"]


def test_placeholders_refused_in_real_mode(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_MODE", "real")
    for path in ("/verification/summary", "/verification/coverage", "/verification/regions",
                 "/verification/reliability?event=rain_ge_1mm", "/impact"):
        r = client.get(PREFIX + path)
        assert r.status_code == 503, path
        assert r.json()["error"]["code"] == "not_computed"
        assert r.headers["X-Data-Mode"] == "real"


def test_data_mode_header_and_cors(client: TestClient) -> None:
    r = client.get(PREFIX + "/health")
    assert r.headers["X-Data-Mode"] == "mock"
    pre = client.options(PREFIX + "/meta", headers={"Origin": "http://localhost:5173",
                                                    "Access-Control-Request-Method": "GET"})
    assert pre.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_every_app_route_is_tested() -> None:
    tested = {p.split("?")[0] for p, _ in _routes(MAIN)}
    app = create_app(Service())
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith(PREFIX) or path.endswith(("/review", "/feedback")) or "/audio/" in path:
            continue
        pattern = path[len(PREFIX):]
        concrete = {t for t in tested if len(t.split("/")) == len(pattern.split("/"))
                    and all(a == b or b.startswith("{") for a, b in zip(t.split("/"), pattern.split("/"),
                                                                        strict=True))}
        assert concrete, f"route {path} is not covered by test_every_route_ok_on_main_date"


# ---------------------------------------------------------------- S8: rules engine, risk, priority, review
LEVEL_RANK = {"low": 0, "moderate": 1, "high": 2, "severe": 3}


@pytest.mark.parametrize("d", DEMO)
def test_priority_is_ranked_with_plain_headlines(client: TestClient, d: str) -> None:
    body = _get_ok(client, f"/priority?issue_date={d}&horizon_days=3", s.Priority)
    assert body["provenance"] == "computed" and body["thresholds_status"] == "placeholder"
    items = body["items"]
    keys = [(-LEVEL_RANK[i["level"]], -i["score"], i["panchayat_id"]) for i in items]
    assert keys == sorted(keys)
    assert len({i["panchayat_id"] for i in items}) == len(items)
    for i in items:
        assert i["level"] != "low" and "livestock" not in i["crops_affected"]
        for lang in ("en", "hi", "pa"):
            text = i["headline"][lang]
            assert text and "{" not in text and "nan" not in text.lower()


def test_priority_matches_risk_levels(client: TestClient) -> None:
    pri = _get_ok(client, f"/priority?issue_date={MAIN}&horizon_days=1", s.Priority)["items"]
    assert pri, "the heavy-rain demo date should have Panchayats needing attention"
    for item in pri[:5]:
        risk = _get_ok(client, f"/risk?issue_date={MAIN}&lead_day=1&type={item['top_risk']}", s.Risk)
        row = next(r for r in risk["items"] if r["panchayat_id"] == item["panchayat_id"])
        assert (row["level"], row["score"]) == (item["level"], item["score"])


def test_risk_levels_follow_rule_file_cuts(client: TestClient) -> None:
    from gramdrishti.advisory.rules import load_rules

    cuts = load_rules().risk["heavy_rain"].cuts
    body = _get_ok(client, f"/risk?issue_date={MAIN}&lead_day=1&type=heavy_rain", s.Risk)
    assert body["provenance"] == "computed"
    for r in body["items"]:
        expected = "low" if r["score"] < cuts[0] else "moderate" if r["score"] < cuts[1] else \
            "high" if r["score"] < cuts[2] else "severe"
        assert r["level"] == expected, r


def test_advisories_come_from_rules(client: TestClient) -> None:
    body = _get_ok(client, f"/advisories?issue_date={MAIN}", s.AdvisoryList)
    assert body["provenance"] == "computed" and body["total"] == len(body["items"]) > 0
    for a in body["items"]:
        assert a["rule_id"] and a["id"].startswith(f"ADV-{MAIN}-{a['panchayat_id']}-{a['crop']}-")
        assert a["thresholds_status"] == "placeholder" and a["translation_status"] == "needs_native_review"
        assert a["audit"][0]["action"] == "created" and a["audit"][0]["actor"] == "system"
    one = _get_ok(client, f"/advisories?issue_date={MAIN}&panchayat_id=MP0305", s.AdvisoryList)
    assert {a["panchayat_id"] for a in one["items"]} == {"MP0305"}
    approved = _get_ok(client, f"/advisories?issue_date={MAIN}&status=approved", s.AdvisoryList)
    assert all(a["status"] == "approved" for a in approved["items"])


def test_advisory_ids_outside_demo_dates_are_404(client: TestClient) -> None:
    for bad in ("ADV-2024-09-10-MP0101-bajra-spray", "ADV-garbage", "ADV-2024-09-09-MP0101-rice-spray"):
        r = client.get(f"{PREFIX}/advisories/{bad}")
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found", bad


def test_review_edit_audit_has_before_and_after(client: TestClient) -> None:
    items = _get_ok(client, "/advisories?issue_date=2024-12-24&status=draft", s.AdvisoryList)["items"]
    adv = next(a for a in items if a["category"] == "frost")
    r = client.post(f"{PREFIX}/advisories/{adv['id']}/review",
                    json={"action": "approve", "reviewer": "O", "edited": {"action": {"en": "x"}}})
    assert r.status_code == 400
    body = {"action": "edit", "reviewer": "Officer Demo", "note": "shorter",
            "edited": {"action": {"en": "Light irrigation this evening.", "hi": "आज शाम हल्की सिंचाई करें।"}}}
    out = client.post(f"{PREFIX}/advisories/{adv['id']}/review", json=body).json()
    assert out["status"] == "edited" and out["action"]["pa"] is None
    last = out["audit"][-1]
    assert last["action"] == "edited" and last["actor"] == "Officer Demo" and last["note"] == "shorter"
    assert last["before"]["action"]["en"] == adv["action"]["en"]
    assert last["after"] == {"status": "edited", "action": body["edited"]["action"] | {"pa": None}}
    again = _get_ok(client, f"/advisories/{adv['id']}", s.Advisory)
    assert again["audit"] == out["audit"]


def test_advice_changed_is_computed(client: TestClient) -> None:
    for pid in ("MP0103", "MP0305", "MP0412"):
        body = _get_ok(client, f"/forecast/changes/{pid}?issue_date={MAIN}", s.ForecastChanges)
        assert isinstance(body["advice_changed"], bool)


def test_forecast_days_carry_spray_rating(client: TestClient) -> None:
    body = _get_ok(client, f"/forecast/panchayat/{PID}?issue_date={MAIN}", s.PanchayatForecast)
    ratings = [d["derived"]["spray_rating"] for d in body["days"]]
    assert len(ratings) == 5 and set(ratings) <= {"good", "caution", "avoid"}


def test_run_daily_writes_drafts(snapshot_dir, tmp_path) -> None:  # noqa: ANN001
    from gramdrishti.pipeline.run_daily import demo_plan, write_advisories
    from gramdrishti.store.db import Store

    store = Store(tmp_path / "rd.sqlite")
    counts = write_advisories(demo_plan(), snapshot_dir, store, log=lambda *_: None)
    assert set(counts) == {date.fromisoformat(d) for d in DEMO}
    for d, by_cat in counts.items():
        assert store.counts(d)["category"] == by_cat
        assert store.counts(d)["status"] == ({"draft": sum(by_cat.values())} if by_cat else {})
    again = write_advisories(demo_plan(), snapshot_dir, store, log=lambda *_: None)
    assert again == counts
