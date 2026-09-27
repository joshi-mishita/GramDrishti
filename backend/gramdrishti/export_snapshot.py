"""Export every GET response the frontend asks for into ``contract/snapshot/`` (offline demo insurance).

Run: ``cd backend && python -m gramdrishti.export_snapshot``
(needs the forecast snapshots from ``python -m gramdrishti.pipeline.run_daily --all-demo-dates``;
``--panchayats demo`` keeps only the demo farmers' and example Panchayats for a quick export).

The frontend runs with ``VITE_SNAPSHOT=1`` from these files and never calls a server (Backend Guide
Appendix B6). ``npm run sync:mock`` copies the folder to ``frontend/public/snapshot/``.

How it works: the real app is called in-process, the same way ``contract/make_examples.py`` does, so every
file is an actual API response and is validated against its Pydantic model before it is written. The
review state (approved, edited, rejected) is read from the local SQLite store, so advisories approved
before the export are what the farmer app shows offline. ``index.json`` has the same format as
``contract/examples/index.json``: one entry per request (method, path with query, status, model, file).
The frontend matches a request by its path plus sorted query, so the requests below mirror exactly what
``frontend/src/api/hooks.ts`` sends. A request that answers with an error is kept with its status, and
the frontend replays it as that error. Audio is not exported; the farmer app falls back to browser speech.

The output is git-ignored (tens of thousands of small files); rebuild it on the demo machine.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import BaseModel

from gramdrishti.api import schemas as s
from gramdrishti.api.main import PREFIX, create_app
from gramdrishti.api.service import LEAD_MAX, LEAD_MIN, Service
from gramdrishti.contract.make_examples import PANCHAYATS as EXAMPLE_PANCHAYATS
from gramdrishti.data.config import ROOT
from gramdrishti.verify.impact import SEASONS as IMPACT_SEASONS

OUT = ROOT / "contract" / "snapshot"
LEADS = range(LEAD_MIN, LEAD_MAX + 1)


@dataclass(frozen=True)
class Req:
    """One GET request and the file its response goes to."""

    file: str
    path: str
    model: type[BaseModel]


def _q(**params: object) -> str:
    return "?" + "&".join(f"{k}={v}" for k, v in params.items())


def requests(svc: Service, pids: list[str]) -> Iterator[Req]:
    """Every request to export, in a stable order."""
    yield Req("health.json", "/health", s.Health)
    yield Req("meta.json", "/meta", s.Meta)
    yield Req("panchayats.geojson", "/geo/panchayats", s.PanchayatCollection)
    yield Req("blocks.geojson", "/geo/blocks", s.BlockCollection)
    yield Req("verification_summary.json", "/verification/summary", s.VerificationSummary)
    for ev in s.RainEvent:
        yield Req(f"verification_reliability_{ev.value}.json",
                  f"/verification/reliability{_q(event=ev.value)}", s.Reliability)
    yield Req("verification_coverage.json", "/verification/coverage", s.Coverage)
    yield Req("verification_regions.json", "/verification/regions", s.Regions)
    for season in IMPACT_SEASONS:
        for dec in s.Decision:
            yield Req(f"impact_{dec.value}_{season}.json", f"/impact{_q(season=season, decision=dec.value)}",
                      s.Impact)
    yield Req("data_quality.json", "/data-quality", s.DataQuality)
    for fid in sorted(svc.farmers):
        yield Req(f"farmer_{fid}.json", f"/farmers/{fid}", s.Farmer)

    for issue in svc.issue_dates:
        d = issue.isoformat()
        yield Req(f"data_quality_{d}.json", f"/data-quality{_q(issue_date=d)}", s.DataQuality)
        for lead in LEADS:
            for var in s.Var:
                yield Req(f"forecast_map_{var.value}_{d}_lead{lead}.json",
                          f"/forecast/map{_q(issue_date=d, lead_day=lead, var=var.value)}", s.ForecastMap)
            for rtype in s.RiskType:
                yield Req(f"risk_{rtype.value}_{d}_lead{lead}.json",
                          f"/risk{_q(issue_date=d, lead_day=lead, type=rtype.value)}", s.Risk)
            yield Req(f"priority_{d}_h{lead}.json", f"/priority{_q(issue_date=d, horizon_days=lead)}",
                      s.Priority)
        yield Req(f"advisories_{d}.json", f"/advisories{_q(issue_date=d)}", s.AdvisoryList)
        for st in s.Status:
            yield Req(f"advisories_{st.value}_{d}.json", f"/advisories{_q(status=st.value, issue_date=d)}",
                      s.AdvisoryList)
        for a in svc.advisories(None, None, issue).items:
            yield Req(f"advisory_{a.id}.json", f"/advisories/{a.id}", s.Advisory)
        for fid in sorted(svc.farmers):
            yield Req(f"farmer_advice_{fid}_{d}.json", f"/farmers/{fid}/advice{_q(issue_date=d)}",
                      s.FarmerAdvice)
        first, last = issue + timedelta(days=LEAD_MIN), issue + timedelta(days=LEAD_MAX)
        for pid in pids:
            yield Req(f"forecast_panchayat_{pid}_{d}.json", f"/forecast/panchayat/{pid}{_q(issue_date=d)}",
                      s.PanchayatForecast)
            yield Req(f"forecast_changes_{pid}_{d}.json", f"/forecast/changes/{pid}{_q(issue_date=d)}",
                      s.ForecastChanges)
            yield Req(f"observed_panchayat_{pid}_{first}_{last}.json",
                      f"/observed/panchayat/{pid}{_q(**{'from': first, 'to': last})}", s.Observed)
            for lead in LEADS:
                for var in s.Var:
                    yield Req(f"explain_{pid}_{var.value}_{d}_lead{lead}.json",
                              f"/explain/{pid}{_q(issue_date=d, lead_day=lead, var=var.value)}", s.Explain)


def demo_panchayats(svc: Service) -> list[str]:
    """The demo farmers' Panchayats plus the ones the contract examples use."""
    return sorted({f["panchayat_id"] for f in svc.farmers.values()} | set(EXAMPLE_PANCHAYATS))


def export(out: Path = OUT, svc: Service | None = None, panchayats: str = "all",
           log=print) -> list[dict]:  # noqa: ANN001
    """Write the snapshot into ``out`` (replacing it) and return the index entries.

    Files are written to a sibling temporary folder first and swapped in at the end, so a failed export
    leaves the previous snapshot untouched.
    """
    svc = svc or Service()
    client = TestClient(create_app(svc))
    pids = sorted(svc.pids) if panchayats == "all" else demo_panchayats(svc)
    tmp = out.with_name(out.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    index: list[dict] = []
    seen: set[str] = set()
    t0 = time.perf_counter()
    for req in requests(svc, pids):
        if req.file in seen:
            raise ValueError(f"two requests write {req.file}")
        seen.add(req.file)
        r = client.get(PREFIX + req.path)
        model = req.model if r.status_code == 200 else s.ErrorResponse
        payload = r.json()
        model.model_validate(payload)
        (tmp / req.file).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
                                    encoding="utf-8")
        index.append({"file": req.file, "method": "GET", "path": PREFIX + req.path, "status": r.status_code,
                      "model": model.__name__, "note": ""})
        if len(index) % 2000 == 0:
            log(f"  {len(index)} files, {time.perf_counter() - t0:.0f} s")
    versions = sorted({v for d in svc.issue_dates if (v := svc.model_version(d))})
    meta = {"contract_version": s.API_VERSION, "data_mode": svc.mode.value,
            "issue_dates": [d.isoformat() for d in svc.issue_dates], "model_versions": versions,
            "panchayats": panchayats, "generated_on": date.today().isoformat(),
            "generated_by": "python -m gramdrishti.export_snapshot", "files": index}
    (tmp / "index.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    shutil.rmtree(out, ignore_errors=True)
    tmp.rename(out)
    return index


def main() -> None:
    """Export the snapshot and print a summary."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--panchayats", choices=("all", "demo"), default="all",
                    help="all 90 Panchayats (default) or only the demo farmers' and example Panchayats")
    a = ap.parse_args()
    t0 = time.perf_counter()
    index = export(a.out, panchayats=a.panchayats)
    errors = [e for e in index if e["status"] != 200]
    size = sum(p.stat().st_size for p in a.out.iterdir())
    print(f"{len(index)} responses ({len(errors)} errors kept as errors) + index.json in {a.out}, "
          f"{size / 1e6:.1f} MB, {time.perf_counter() - t0:.0f} s")
    for e in errors[:10]:
        print(f"  {e['status']} {e['path']}")


if __name__ == "__main__":
    main()
