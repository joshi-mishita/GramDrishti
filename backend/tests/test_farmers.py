"""S12: demo farmers, farmer advice, feedback checks, audio, the feedback report and the snapshot export."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from gramdrishti import export_snapshot
from gramdrishti.advisory import audio
from gramdrishti.api import schemas as s
from gramdrishti.api.main import PREFIX, create_app
from gramdrishti.api.service import Service
from gramdrishti.contract.pick_demo_dates import load_demo_dates
from gramdrishti.store.db import Store
from gramdrishti.store.seed_demo import DEMO_FARMERS, demo_farmers
from gramdrishti.verify import feedback_report

from .conftest import needs_oracle

MAIN = "2024-09-09"
NOW = datetime(2024, 9, 12, 9, 30)
RANK = {"low": 0, "moderate": 1, "high": 2, "severe": 3}


def offline(text: str, lang: str, path: Path) -> None:
    raise OSError("no internet in tests")


class FakeTTS:
    """Writes a tiny fake MP3 and counts calls, so tests never reach Google."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def __call__(self, text: str, lang: str, path: Path) -> None:
        self.calls.append((text, lang))
        path.write_bytes(b"ID3fake-mp3")


def _client(snapshot_dir: Path, tmp: Path, synth: audio.Synth = offline) -> TestClient:
    svc = Service(clock=lambda: NOW, snapshot_dir=snapshot_dir, db_path=tmp / "farmers.sqlite",
                  audio_dir=tmp / "audio", synth=synth)
    return TestClient(create_app(svc))


def _get(client: TestClient, path: str, model: type[s.ApiModel]) -> dict:
    r = client.get(PREFIX + path)
    assert r.status_code == 200, (path, r.text[:300])
    model.model_validate(r.json())
    return r.json()


def _review(client: TestClient, adv_id: str, action: str, **extra: object) -> dict:
    r = client.post(f"{PREFIX}/advisories/{adv_id}/review",
                    json={"action": action, "reviewer": "Officer Demo", "note": "", **extra})
    assert r.status_code == 200, r.text
    return r.json()


def _drafts(client: TestClient, pid: str, issue: str = MAIN) -> list[dict]:
    return _get(client, f"/advisories?status=draft&issue_date={issue}&panchayat_id={pid}",
                s.AdvisoryList)["items"]


# ---------------------------------------------------------------- seed
def test_demo_farmers_are_distinct_demo_profiles() -> None:
    farmers = demo_farmers()
    assert len(farmers) == 5
    assert all(f["name"].startswith("Demo farmer") for f in farmers)
    assert len({f["panchayat_id"] for f in farmers}) == 5
    assert {f["language"] for f in farmers} == {"en", "hi", "pa"}
    assert len({tuple(sorted({c["crop"] for c in f["crops"]})) for f in farmers}) == 5
    sowing = [c["sowing_date"] for f in farmers for c in f["crops"] if c["season"] == "kharif_2024"]
    assert len(set(sowing)) == len(sowing)
    static = pd.read_csv(Path(__file__).parents[2] / "data" / "panchayats_static.csv")
    static = static.set_index("panchayat_id")
    blocks = [static.loc[f.panchayat_id, "block_id"] for f in DEMO_FARMERS]
    assert blocks[0] == blocks[1], "F001 and F002 share a block for the same-block demo"


def test_seed_is_idempotent_and_round_trips(tmp_path: Path) -> None:
    from gramdrishti.store.seed_demo import seed

    store = Store(tmp_path / "seed.sqlite")
    assert seed(store) == 5 and seed(store) == 5
    farmers = store.farmers()
    assert list(farmers) == ["F001", "F002", "F003", "F004", "F005"]
    f1 = farmers["F001"]
    assert f1["livestock"] is True and f1["panchayat_id"] == "MP0307"
    assert {c["crop"] for c in f1["crops"]} == {"bajra", "wheat"}


# ---------------------------------------------------------------- farmer advice
@needs_oracle
def test_farmer_advice_shows_only_reviewed_items_for_the_right_farmer(snapshot_dir, tmp_path: Path) -> None:
    c = _client(snapshot_dir, tmp_path)
    f1, f2 = _get(c, "/farmers/F001", s.Farmer), _get(c, "/farmers/F002", s.Farmer)
    assert f1["block_id"] == f2["block_id"] and f1["panchayat_id"] != f2["panchayat_id"]
    issue = next(d.date for d in load_demo_dates() if len(_drafts(c, f1["panchayat_id"], d.date)) >= 3)
    assert _get(c, f"/farmers/F001/advice?issue_date={issue}", s.FarmerAdvice)["items"] == []

    drafts = _drafts(c, f1["panchayat_id"], issue)
    approved, rejected, edited = drafts[:3]
    _review(c, approved["id"], "approve")
    _review(c, rejected["id"], "reject")
    _review(c, edited["id"], "edit", edited={"action": {"en": "Edited text."}})

    advice = _get(c, f"/farmers/F001/advice?issue_date={issue}", s.FarmerAdvice)
    ids = [a["id"] for a in advice["items"]]
    assert approved["id"] in ids and rejected["id"] not in ids
    assert all(a["status"] in ("approved", "edited") for a in advice["items"])
    assert edited["id"] in ids
    remaining = {a["id"] for a in _drafts(c, f1["panchayat_id"], issue)}
    assert not remaining & set(ids), "drafts never reach farmers"
    keys = [(-RANK[a["priority"]], a["valid_from"], a["id"]) for a in advice["items"]]
    assert keys == sorted(keys)

    other = _get(c, f"/farmers/F002/advice?issue_date={issue}", s.FarmerAdvice)
    assert not set(ids) & {a["id"] for a in other["items"]}, "same block, other Panchayat: not shown"


@needs_oracle
def test_farmer_advice_filters_crops_and_livestock(snapshot_dir, tmp_path: Path) -> None:
    c = _client(snapshot_dir, tmp_path)
    issue = next(d.date for d in load_demo_dates()
                 if {a["crop"] for a in _drafts(c, "MP0103", d.date)} - {"wheat"})
    for a in _drafts(c, "MP0103", issue):
        _review(c, a["id"], "approve")
    advice = _get(c, f"/farmers/F005/advice?issue_date={issue}", s.FarmerAdvice)
    assert all(a["crop"] == "wheat" for a in advice["items"]), "F005 grows wheat only, keeps no livestock"

    livestock = [a for d in load_demo_dates() for a in _drafts(c, "MP0307", d.date)
                 if a["crop"] == "livestock"]
    assert livestock, "MP0307 gets livestock advice on some demo date"
    _review(c, livestock[0]["id"], "approve")
    f1 = _get(c, f"/farmers/F001/advice?issue_date={livestock[0]['issue_date']}", s.FarmerAdvice)
    assert livestock[0]["id"] in [a["id"] for a in f1["items"]], "F001 keeps livestock"


@needs_oracle
def test_spray_days_match_the_forecast_panchayat_ratings(snapshot_dir, tmp_path: Path) -> None:
    c = _client(snapshot_dir, tmp_path)
    advice = _get(c, f"/farmers/F003/advice?issue_date={MAIN}", s.FarmerAdvice)
    fc = _get(c, f"/forecast/panchayat/{advice['panchayat_id']}?issue_date={MAIN}", s.PanchayatForecast)
    assert [(d["date"], d["rating"]) for d in advice["spray_days"]] == \
        [(d["date"], d["derived"]["spray_rating"]) for d in fc["days"]]
    assert [d["lead_day"] for d in advice["spray_days"]] == [1, 2, 3, 4, 5]


@needs_oracle
def test_unknown_farmer_is_404(snapshot_dir, tmp_path: Path) -> None:
    c = _client(snapshot_dir, tmp_path)
    for path in ("/farmers/F006", f"/farmers/F999/advice?issue_date={MAIN}"):
        r = c.get(PREFIX + path)
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


# ---------------------------------------------------------------- feedback
@needs_oracle
def test_feedback_validation_and_duplicates(snapshot_dir, tmp_path: Path) -> None:
    c = _client(snapshot_dir, tmp_path)
    body = {"panchayat_id": "MP0307", "date": "2024-09-10", "reported_rain": True, "intensity": "heavy",
            "channel": "app"}
    first = c.post(PREFIX + "/feedback", json=body).json()
    assert first["stored"] is True
    again = c.post(PREFIX + "/feedback", json=body)
    assert again.status_code == 200
    dup = s.FeedbackResponse.model_validate(again.json())
    assert dup.stored is False and dup.id == first["id"]
    other = c.post(PREFIX + "/feedback", json={**body, "channel": "ivr"}).json()
    assert other["stored"] is True and other["id"] != first["id"]

    bad = [({**body, "date": "2024-09-13"}, 400),            # after the clock's today
           ({**body, "date": "2019-06-01"}, 400),            # before the data period
           ({**body, "intensity": "none"}, 400),             # rain but no intensity
           ({**body, "reported_rain": False}, 400),          # no rain but heavy
           ({**body, "panchayat_id": "MP9999"}, 404),
           ({**body, "date": "10-09-2024"}, 422)]
    for b, status in bad:
        r = c.post(PREFIX + "/feedback", json=b)
        assert r.status_code == status, (b, r.text)
        assert set(r.json()) == {"error"} and set(r.json()["error"]) == {"code", "message"}


# ---------------------------------------------------------------- audio
@needs_oracle
def test_audio_offline_is_contract_404(snapshot_dir, tmp_path: Path) -> None:
    c = _client(snapshot_dir, tmp_path)
    adv = _drafts(c, "MP0307")[0]
    r = c.get(f"{PREFIX}/audio/{adv['id']}?lang=hi")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "audio_not_available"
    r = c.get(f"{PREFIX}/audio/ADV-2024-09-09-MP0307-bajra-nothing?lang=hi")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = c.get(f"{PREFIX}/audio/{adv['id']}?lang=fr")
    assert r.status_code == 422


@needs_oracle
def test_audio_without_gtts_is_404(snapshot_dir, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio, "supported_langs", lambda: frozenset())
    c = _client(snapshot_dir, tmp_path, synth=audio.gtts_synth)
    adv = _drafts(c, "MP0307")[0]
    r = c.get(f"{PREFIX}/audio/{adv['id']}?lang=pa")
    assert r.status_code == 404 and "not installed" in r.json()["error"]["message"]
    approved = _review(c, adv["id"], "approve")
    assert approved["audio"] == {}, "no links when gTTS is missing"


@needs_oracle
def test_audio_is_generated_once_and_follows_edits(snapshot_dir, tmp_path: Path) -> None:
    tts = FakeTTS()
    c = _client(snapshot_dir, tmp_path, synth=tts)
    adv = _drafts(c, "MP0307")[0]
    assert adv["audio"] == {}, "drafts carry no audio links"
    approved = _review(c, adv["id"], "approve")
    assert approved["audio"] == {lang: f"/api/v1/audio/{adv['id']}?lang={lang}"
                                 for lang in ("en", "hi", "pa")}

    for _ in range(2):
        r = c.get(approved["audio"]["hi"])
        assert r.status_code == 200 and r.headers["content-type"] == "audio/mpeg"
        assert r.content.startswith(b"ID3")
    assert len(tts.calls) == 1 and tts.calls[0][1] == "hi"
    assert tts.calls[0][0].startswith(adv["action"]["hi"])

    edited = _review(c, adv["id"], "edit", edited={"action": {"en": "Shorter English text."}})
    assert set(edited["audio"]) == {"en"}, "hi and pa were nulled by the English-only edit"
    assert c.get(f"{PREFIX}/audio/{adv['id']}?lang=hi").status_code == 404
    assert c.get(edited["audio"]["en"]).status_code == 200
    assert len(list((tmp_path / "audio").glob(f"{adv['id']}_*.mp3"))) == 2


def test_speech_text_and_cache_path(tmp_path: Path) -> None:
    a = {"id": "ADV-x", "action": {"en": "Do it.", "hi": None}, "reason": {"en": "Why."},
         "fallback": {"en": ""}}
    assert audio.speech_text(a, "en") == "Do it. Why."
    assert audio.speech_text(a, "hi") is None
    p1, p2 = audio.cache_path(tmp_path, "ADV-x", "en", "a"), audio.cache_path(tmp_path, "ADV-x", "en", "b")
    assert p1 != p2 and p1.name.startswith("ADV-x_en_") and p1.suffix == ".mp3"


# ---------------------------------------------------------------- feedback report
def test_intensity_classes_and_test_window_refused() -> None:
    assert [feedback_report.intensity_class(x) for x in (0, 0.99, 1, 9.9, 10, 35, 120)] == \
        ["none", "none", "light", "light", "moderate", "heavy", "heavy"]
    assert feedback_report.intensity_class(float("nan")) is None
    with pytest.raises(PermissionError):
        feedback_report.month_bounds("2024-07")
    assert feedback_report.month_bounds("2024-06")[1] == pd.Timestamp("2024-06-30")


@needs_oracle
def test_feedback_report_counts_api_and_file_reports(tmp_path: Path) -> None:
    store = Store(tmp_path / "fb.sqlite")
    store.add_feedback("MP0307", date(2023, 8, 10), True, "light", "app", datetime(2023, 8, 10, 9))
    c = feedback_report.check_month("2023-08", store)
    r = c.rows
    assert (r["source"] == "api").sum() == 1 and (r["source"] == "mock_file").sum() >= 1
    assert r["truth_source"].isin(["station", "synthetic_truth"]).all()
    assert r.loc[r["has_station"], "truth_source"].eq("station").mean() > 0.5
    assert c.reported_without_station <= c.reported_panchayats <= c.n_panchayats == 90
    assert c.per_panchayat["reports"].sum() == len(r)
    text = feedback_report.render(c, date(2026, 9, 27))
    assert "not a result" in text and "retrain" in text and "MP0307" in text


# ---------------------------------------------------------------- snapshot export
def _key(path: str) -> str:
    """The frontend's request key: path without the API prefix plus sorted query."""
    u = urlsplit(path)
    q = "&".join(f"{k}={v}" for k, v in sorted(parse_qsl(u.query)))
    return u.path.removeprefix(PREFIX) + (f"?{q}" if q else "")


@needs_oracle
def test_snapshot_export_files_validate(snapshot_dir, verification_dir, tmp_path: Path) -> None:  # noqa: ANN001
    main = [d for d in load_demo_dates() if d.date == MAIN]
    svc = Service(demo_dates=main, clock=lambda: NOW, snapshot_dir=snapshot_dir,
                  db_path=tmp_path / "snap.sqlite", verification_dir=verification_dir, synth=offline)
    out = tmp_path / "snapshot"
    index = export_snapshot.export(out, svc, panchayats="demo", log=lambda *_: None)
    meta = json.loads((out / "index.json").read_text())
    assert meta["files"] == index and meta["data_mode"] == "mock" and meta["issue_dates"] == [MAIN]
    assert len({_key(e["path"]) for e in index}) == len(index), "every request key is unique"
    assert {p.name for p in out.iterdir()} == {e["file"] for e in index} | {"index.json"}
    for e in index:
        assert e["status"] == 200, e
        body = json.loads((out / e["file"]).read_text(), parse_constant=lambda x: pytest.fail(x))
        getattr(s, e["model"]).model_validate(body)
    keys = {_key(e["path"]) for e in index}
    for fid in ("F001", "F002", "F003", "F004", "F005"):
        assert f"/farmers/{fid}" in keys and f"/farmers/{fid}/advice?issue_date={MAIN}" in keys
    assert f"/forecast/map?issue_date={MAIN}&lead_day=3&var=rh" in keys
    assert f"/explain/MP0307?issue_date={MAIN}&lead_day=5&var=wind" in keys
    assert "/observed/panchayat/MP0307?from=2024-09-10&to=2024-09-14" in keys
    assert f"/advisories?issue_date={MAIN}&status=draft" in keys
    assert f"/advisories?issue_date={MAIN}&panchayat_id=MP0307" in keys, "the bulletin's request"
    assert not (tmp_path / "snapshot.tmp").exists()
