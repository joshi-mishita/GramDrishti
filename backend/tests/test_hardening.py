"""S14 hardening: body size limit, CORS from configuration, access log without personal data."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gramdrishti.api.hardening import JsonFormatter
from gramdrishti.api.main import PREFIX, create_app
from gramdrishti.api.service import Service
from gramdrishti.data import config


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("GRAMDRISHTI_MAX_BODY_BYTES", "1000")
    monkeypatch.setenv("GRAMDRISHTI_CORS_ORIGINS", "http://demo.test:8080, http://localhost:5173/")
    return TestClient(create_app(Service(db_path=tmp_path / "h.sqlite", snapshot_dir=tmp_path)))


def test_oversized_body_is_refused_with_the_contract_error(client: TestClient) -> None:
    r = client.post(f"{PREFIX}/feedback", content=b"{" + b" " * 2000 + b"}",
                    headers={"Content-Type": "application/json"})
    assert r.status_code == 413
    assert r.json() == {"error": {"code": "payload_too_large",
                                  "message": "Request body is larger than 1000 bytes"}}


def test_oversized_chunked_body_is_refused(client: TestClient) -> None:
    def chunks():  # no Content-Length: the middleware counts the streamed bytes
        for _ in range(5):
            yield b" " * 400

    r = client.post(f"{PREFIX}/feedback", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_small_body_still_reaches_the_route(client: TestClient) -> None:
    r = client.post(f"{PREFIX}/feedback", json={})
    assert r.status_code == 422          # validation, not the size limit
    assert r.json()["error"]["code"] == "validation_error"


def test_cors_allows_only_configured_origins(client: TestClient) -> None:
    ok = client.get(f"{PREFIX}/health", headers={"Origin": "http://demo.test:8080"})
    assert ok.headers["access-control-allow-origin"] == "http://demo.test:8080"
    trailing = client.get(f"{PREFIX}/health", headers={"Origin": "http://localhost:5173"})
    assert trailing.headers["access-control-allow-origin"] == "http://localhost:5173"
    bad = client.get(f"{PREFIX}/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in bad.headers
    pre = client.options(f"{PREFIX}/feedback", headers={
        "Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
    assert pre.status_code == 400


def test_wildcard_origin_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GRAMDRISHTI_CORS_ORIGINS", "*")
    with pytest.raises(ValueError):
        config.cors_origins()


def test_access_log_has_route_template_and_no_personal_data(client: TestClient,
                                                            caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="gramdrishti.access"):
        client.get(f"{PREFIX}/farmers/F001/advice?date=2024-09-09&secret=x",
                   headers={"X-Role": "farmer", "User-Agent": "Phone/1.0"})
        client.get(f"{PREFIX}/no/such/path", headers={"X-Role": "Priya Sharma"})
    records = [r.fields for r in caplog.records if r.name == "gramdrishti.access"]
    assert records[0]["route"].endswith("/farmers/{farmer_id}/advice")
    assert records[0]["role"] == "farmer"
    assert records[1] == {**records[1], "route": "unmatched", "role": "other", "status": 404}
    text = json.dumps(records)
    for leaked in ("F001", "secret", "Phone/1.0", "Priya", "testclient"):
        assert leaked not in text


def test_json_formatter_writes_one_object_per_line() -> None:
    rec = logging.LogRecord("gramdrishti.access", logging.INFO, __file__, 1, "request", None, None)
    rec.fields = {"route": "/x", "status": 200}
    out = json.loads(JsonFormatter().format(rec))
    assert out["message"] == "request" and out["route"] == "/x" and out["level"] == "info"
