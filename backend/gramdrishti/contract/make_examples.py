"""Write one example per endpoint to ``contract/examples/`` by calling the real app, then validate each one.

Run: ``cd backend && python -m gramdrishti.contract.make_examples``

Every example is a real response of the API with a fixed clock, so the files are reproducible and
match the Pydantic models by construction. ``index.json`` maps each file to its endpoint and model and
records the model version of the snapshots used.
Forecast, explain and change numbers come from the snapshots in ``backend/artifacts/snapshots`` (run
``python -m gramdrishti.pipeline.run_daily --all-demo-dates`` first). Risk and priority are PROVISIONAL
(placeholder thresholds); verification, impact and advisory content is PLACEHOLDER (``provenance`` says
which). All of it is ``data_mode: "mock"``.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pydantic import BaseModel

from gramdrishti.api import schemas as s
from gramdrishti.api.main import PREFIX, create_app
from gramdrishti.api.service import Service
from gramdrishti.data.config import ROOT

OUT = ROOT / "contract" / "examples"
FIXED_NOW = datetime(2024, 9, 9, 9, 30, 0)

MAIN_DATE = "2024-09-09"      # heavy monsoon rain
PANCHAYATS = {
    "MP0103": "AWS station in the Panchayat, dry block MB01",
    "MP0305": "AWS station, wettest block MB03",
    "MP0412": "rain gauge only (other variables null), poorly drained soil",
    "MP0302": "no station: observed comes from synthetic truth",
}
RISK_DATES = {"heavy_rain": MAIN_DATE, "waterlogging": "2024-07-31", "heat": "2024-03-31",
              "frost": "2024-12-24", "dry_spell": "2024-08-15"}


def _validate(model: type[BaseModel], payload: Any) -> None:
    model.model_validate(payload)


class Writer:
    """Collects example files and their index entries."""

    def __init__(self, client: TestClient, out: Path) -> None:
        self.client, self.out = client, out
        self.index: list[dict] = []

    def _save(self, name: str, payload: Any) -> None:
        indent = None if name.endswith(".geojson") else 2   # polygons stay compact
        text = json.dumps(payload, indent=indent, ensure_ascii=False)
        (self.out / name).write_text(text + "\n", encoding="utf-8")

    def get(self, name: str, path: str, model: type[BaseModel], note: str = "", status: int = 200) -> Any:
        r = self.client.get(PREFIX + path)
        assert r.status_code == status, (path, r.status_code, r.text[:300])
        payload = r.json()
        _validate(model, payload)
        self._save(name, payload)
        self.index.append({"file": name, "method": "GET", "path": PREFIX + path, "status": status,
                           "model": model.__name__, "note": note})
        return payload

    def post(self, name: str, path: str, body: dict, model: type[BaseModel], request_name: str,
             request_model: type[BaseModel], note: str = "", status: int = 200) -> Any:
        _validate(request_model, body)
        self._save(request_name, body)
        self.index.append({"file": request_name, "method": "POST", "path": PREFIX + path, "status": None,
                           "model": request_model.__name__, "note": "request body. " + note})
        r = self.client.post(PREFIX + path, json=body)
        assert r.status_code == status, (path, r.status_code, r.text[:300])
        payload = r.json()
        _validate(model, payload)
        self._save(name, payload)
        self.index.append({"file": name, "method": "POST", "path": PREFIX + path, "status": status,
                           "model": model.__name__, "note": note})
        return payload


def _geojson(w: Writer, name: str, path: str, model: type[BaseModel]) -> None:
    w.get(name, path, model, "GeoJSON FeatureCollection, coordinates [longitude, latitude]")


def build(out: Path = OUT) -> list[dict]:
    """Write every example into ``out`` and return the index entries."""
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("*.json")) + list(out.glob("*.geojson")):
        old.unlink()
    svc = Service(clock=lambda: FIXED_NOW)
    client = TestClient(create_app(svc))
    w = Writer(client, out)
    d = MAIN_DATE

    w.get("health.json", "/health", s.Health)
    w.get("meta.json", "/meta", s.Meta, "issue_date_info is additive in v0.1.1")
    _geojson(w, "panchayats.geojson", "/geo/panchayats", s.PanchayatCollection)
    _geojson(w, "blocks.geojson", "/geo/blocks", s.BlockCollection)

    for var in s.Var:
        w.get(f"forecast_map_{var.value}.json", f"/forecast/map?issue_date={d}&lead_day=1&var={var.value}",
              s.ForecastMap, "model snapshot; block_value = raw block forecast B0, block_layer.corrected = "
              "B1; block mean of Panchayat mean = corrected")
    for pid, why in PANCHAYATS.items():
        w.get(f"forecast_panchayat_{pid}.json", f"/forecast/panchayat/{pid}?issue_date={d}",
              s.PanchayatForecast, f"model snapshot; agro levels use placeholder thresholds. {why}")
        w.get(f"observed_panchayat_{pid}.json", f"/observed/panchayat/{pid}?from=2024-09-10&to=2024-09-14",
              s.Observed, why)
        w.get(f"explain_{pid}.json", f"/explain/{pid}?issue_date={d}&lead_day=1&var=tmax", s.Explain,
              "SHAP block contrast on the mean model; hi and pa null until written")
        w.get(f"forecast_changes_{pid}.json", f"/forecast/changes/{pid}?issue_date={d}", s.ForecastChanges,
              "against the 2024-09-08 snapshot; advice_changed is null until the rules engine (S8)")

    for rtype, rdate in RISK_DATES.items():
        w.get(f"risk_{rtype}.json", f"/risk?issue_date={rdate}&lead_day=1&type={rtype}", s.Risk,
              "PROVISIONAL scores, placeholder thresholds")
    w.get("priority.json", f"/priority?issue_date={d}&horizon_days=2", s.Priority,
          "PROVISIONAL scores, placeholder thresholds")
    w.get("priority_2024-12-24.json", "/priority?issue_date=2024-12-24&horizon_days=2", s.Priority,
          "Cold December morning")

    queue = w.get("advisories.json", f"/advisories?status=draft&issue_date={d}", s.AdvisoryList,
                  "PLACEHOLDER advisory generator until S8. Hindi and Punjabi need native review")
    items = queue["items"]
    spray = next(a for a in items if a["category"] == "spray")
    w.get("advisory_detail.json", f"/advisories/{spray['id']}", s.Advisory, "one advisory with audit trail")
    w.post("advisory_review_response.json", f"/advisories/{spray['id']}/review",
           {"action": "edit", "reviewer": "Officer Demo", "note": "Shortened wording",
            "edited": {"action": {"en": "No spraying before 10 September.",
                                  "hi": "10 सितंबर से पहले छिड़काव न करें।",
                                  "pa": "10 ਸਤੰਬਰ ਤੋਂ ਪਹਿਲਾਂ ਛਿੜਕਾਅ ਨਾ ਕਰੋ।"}}},
           s.Advisory, "advisory_review_request.json", s.ReviewRequest, "action: approve | edit | reject")

    farmers = [w.get(f"farmer_F{i:03d}.json", f"/farmers/F{i:03d}", s.Farmer, "demo farmer")
               for i in range(1, 7)]
    f1 = farmers[0]
    for a in items:
        if a["panchayat_id"] == f1["panchayat_id"]:
            r = client.post(f"{PREFIX}/advisories/{a['id']}/review",
                            json={"action": "approve", "reviewer": "Officer Demo", "note": ""})
            assert r.status_code == 200, r.text
    w.get("farmer_advice_F001.json", f"/farmers/F001/advice?issue_date={d}", s.FarmerAdvice,
          "after the officer approved this Panchayat's advisories")
    w.post("feedback_response.json", "/feedback",
           {"panchayat_id": "MP0103", "date": "2024-09-10", "reported_rain": True, "intensity": "moderate",
            "channel": "app"},
           s.FeedbackResponse, "feedback_request.json", s.FeedbackRequest,
           "intensity: none | light | moderate | heavy")

    w.get("verification_summary.json", "/verification/summary", s.VerificationSummary,
          "PLACEHOLDER numbers, not results (S10)")
    for ev in s.RainEvent:
        w.get(f"verification_reliability_{ev.value}.json", f"/verification/reliability?event={ev.value}",
              s.Reliability, "PLACEHOLDER numbers, not results (S10)")
    w.get("verification_coverage.json", "/verification/coverage", s.Coverage, "PLACEHOLDER numbers (S10)")
    w.get("verification_regions.json", "/verification/regions", s.Regions, "PLACEHOLDER numbers (S10)")
    for dec in s.Decision:
        w.get(f"impact_{dec.value}.json", f"/impact?season=monsoon_2024&decision={dec.value}", s.Impact,
              "PLACEHOLDER counts, not results (S10)")
    w.get("data_quality.json", "/data-quality?issue_date=2024-12-24", s.DataQuality,
          "computed from the station files")

    w.get("error_not_found.json", f"/forecast/panchayat/MP9999?issue_date={d}", s.ErrorResponse,
          "unknown id", status=404)
    w.get("error_issue_date_not_available.json", "/forecast/panchayat/MP0103?issue_date=2024-09-10",
          s.ErrorResponse, "issue date not in /meta.available_issue_dates", status=404)
    w.get("error_validation.json", f"/forecast/map?issue_date={d}&lead_day=9&var=rain", s.ErrorResponse,
          "invalid parameter", status=422)
    w.get("error_audio_not_available.json", f"/audio/{spray['id']}?lang=hi", s.ErrorResponse,
          "no audio yet: the UI falls back to browser speech", status=404)

    w.get("explain_MP0305_rain.json", f"/explain/MP0305?issue_date={d}&lead_day=1&var=rain", s.Explain,
          "rain reasons in the wettest block")
    w.get("explain_MP0103_rain_dry_block.json", f"/explain/MP0103?issue_date={d}&lead_day=1&var=rain",
          s.Explain, "dry block: every Panchayat is 0 mm, so there is nothing to explain (reasons empty)")
    index = {"contract_version": s.API_VERSION, "data_mode": "mock", "main_issue_date": d,
             "model_version": svc.model_version(date.fromisoformat(d)),
             "generated_by": "python -m gramdrishti.contract.make_examples", "files": w.index}
    (out / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return w.index


def main() -> None:
    """Regenerate ``contract/examples``."""
    index = build()
    for e in index:
        print(f"{e['method']:4} {e['status'] or '':3} {e['file']:48} {e['model']}")
    print(f"\n{len(index)} files written to {OUT}")


if __name__ == "__main__":
    main()
