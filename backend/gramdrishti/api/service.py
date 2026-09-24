"""Builds every API response from the data files, the PROVISIONAL B1 forecast and placeholder generators.

Nothing is loaded at import time. The first request that needs data loads the files and fits the B1
parameters on TRAIN (well under a second on the mock data); results are cached per issue date.
Advisory review state and farmer feedback live in memory until the SQLite store arrives (S8, S12).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from functools import cached_property

import numpy as np
import pandas as pd

from gramdrishti.api import schemas as s
from gramdrishti.api.errors import ApiError, not_found
from gramdrishti.contract.pick_demo_dates import DemoDate, load_demo_dates
from gramdrishti.data import loaders
from gramdrishti.data.config import COLS, LEADS, VARS, data_mode
from gramdrishti.data.qc import clean_values, run_qc
from gramdrishti.models.baselines import Baselines
from gramdrishti.provisional import agro, placeholders, texts
from gramdrishti.provisional.forecast import block_quantiles, event_probs, fit_provisional, prob_exceed
from gramdrishti.provisional.risk import RISK_TYPES, risk_scores

QS = ("p10", "p50", "p90", "block")
DISTRICT_MOCK = "Synthetic District"
MATERIAL_CHANGE = {"rain": 5.0, "tmax": 1.5, "tmin": 1.5, "rh": 10.0, "wind": 5.0}
MATERIAL_PROB_CHANGE = 0.15
MAX_OBSERVED_DAYS = 62
N_DEMO_FARMERS = 6
FARMER_SEASONS = ("kharif_2024", "rabi_2024_25")
FARMER_LANGS = ("hi", "pa", "en")
ADVISORY_HORIZON = 3
ADVISORY_MIN_LEVELS = ("high", "severe")
LEVEL_RANK = {"low": 0, "moderate": 1, "high": 2, "severe": 3}


def num(x: object, nd: int = 2) -> float | None:
    """Round to ``nd`` decimals; NaN, Infinity and None become None (JSON null)."""
    if x is None:
        return None
    try:
        v = float(x)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return round(v, nd) if np.isfinite(v) else None


def prob(x: float | None) -> float | None:
    """Probability rounded to 2 decimals and clipped to [0, 1]."""
    v = num(x)
    return None if v is None else min(max(v, 0.0), 1.0)


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


class Service:
    """All response builders. One instance per app; thread-safe for the in-memory stores."""

    def __init__(self, demo_dates: list[DemoDate] | None = None,
                 clock: Callable[[], datetime] = _now) -> None:
        self._demo = demo_dates
        self.clock = clock
        self._lock = threading.Lock()
        self._tables: dict[date, pd.DataFrame] = {}
        self._advisories: dict[str, dict] | None = None
        self._feedback: list[s.FeedbackResponse] = []

    # ------------------------------------------------------------ data
    @property
    def mode(self) -> s.DataMode:
        return s.DataMode(data_mode())

    @cached_property
    def demo_dates(self) -> list[DemoDate]:
        return self._demo if self._demo is not None else load_demo_dates()

    @cached_property
    def issue_dates(self) -> list[date]:
        return [date.fromisoformat(d.date) for d in self.demo_dates]

    @cached_property
    def static(self) -> pd.DataFrame:
        return loaders.load_static()

    @cached_property
    def blocks(self) -> pd.DataFrame:
        return loaders.load_blocks()

    @cached_property
    def stations(self) -> pd.DataFrame:
        return loaders.load_stations()

    @cached_property
    def crops(self) -> pd.DataFrame:
        return loaders.load_crops()

    @cached_property
    def calendar(self) -> pd.DataFrame:
        return loaders.load_calendar()

    @cached_property
    def fc(self) -> pd.DataFrame:
        return loaders.load_fc()

    @cached_property
    def qc_obs(self) -> pd.DataFrame:
        return run_qc(loaders.load_obs())

    @cached_property
    def obs_clean(self) -> pd.DataFrame:
        return clean_values(self.qc_obs)

    @cached_property
    def baselines(self) -> Baselines:
        return fit_provisional()

    @cached_property
    def truth(self) -> pd.DataFrame:
        return loaders.load_truth()  # MOCK ONLY: served by /observed for display, never used as a feature

    @cached_property
    def pids(self) -> set[str]:
        return set(self.static["panchayat_id"])

    # ------------------------------------------------------------ checks
    def check_issue(self, issue: date) -> date:
        if issue not in self.issue_dates:
            avail = ", ".join(d.isoformat() for d in self.issue_dates)
            raise ApiError(404, "issue_date_not_available",
                           f"Issue date {issue.isoformat()} is not available. Available: {avail}")
        return issue

    def check_panchayat(self, pid: str) -> pd.Series:
        if pid not in self.pids:
            raise not_found(f"Panchayat {pid} does not exist")
        return self.static.set_index("panchayat_id").loc[pid]

    def require_mock_for_placeholder(self, what: str) -> None:
        """Placeholder numbers may only ever be served under data_mode "mock"."""
        if self.mode != s.DataMode.mock:
            raise ApiError(503, "not_computed", f"{what} has not been computed yet for real data.")

    # ------------------------------------------------------------ forecast table
    def table(self, issue: date) -> pd.DataFrame:
        """Wide Panchayat table for one issue date: <var>_<q> columns, lead_day, valid_date, statics."""
        with self._lock:
            if issue not in self._tables:
                ts = pd.Timestamp(issue)
                bq = block_quantiles(self.fc[self.fc["issue_date"] == ts], self.baselines)
                wide = bq.pivot_table(index=["block_id", "valid_date", "lead_day"], columns="var",
                                      values=list(QS), aggfunc="first")
                wide.columns = [f"{v}_{q}" for q, v in wide.columns]
                wide = wide.reset_index()
                st = self.static[["panchayat_id", "block_id", "lat", "drainage_class"]]
                t = st.merge(wide, on="block_id", how="inner").sort_values(["panchayat_id", "lead_day"])
                self._tables[issue] = t.reset_index(drop=True)
            return self._tables[issue]

    def _row(self, issue: date, pid: str, lead: int) -> pd.Series:
        t = self.table(issue)
        r = t[(t["panchayat_id"] == pid) & (t["lead_day"] == lead)]
        if r.empty:
            raise not_found(f"No forecast for {pid} at lead day {lead}")
        return r.iloc[0]

    # ------------------------------------------------------------ meta and geo
    def health(self) -> s.Health:
        return s.Health(status="ok", api_version=s.API_VERSION, data_mode=self.mode)

    def meta(self) -> s.Meta:
        return s.Meta(
            api_version=s.API_VERSION, data_mode=self.mode,
            district=DISTRICT_MOCK if self.mode == s.DataMode.mock else "District",
            available_issue_dates=self.issue_dates, languages=list(s.Lang),
            crops=sorted(self.crops["crop"].unique().tolist()),
            vars=[s.VarInfo(var=v, unit=s.UNITS[v]) for v in s.Var],
            issue_date_info=[s.IssueDateInfo(date=date.fromisoformat(d.date), label=d.label, split=d.split)
                             for d in self.demo_dates])

    @staticmethod
    def _round_coords(c: object) -> object:
        if isinstance(c, list) and c and isinstance(c[0], (int, float)):
            return [round(float(c[0]), 5), round(float(c[1]), 5)]
        return [Service._round_coords(x) for x in c]  # type: ignore[union-attr]

    def _features(self, gj: dict, props: Callable[[dict], dict]) -> list[dict]:
        return [{"type": "Feature", "properties": props(f["properties"]),
                 "geometry": {"type": f["geometry"]["type"],
                              "coordinates": self._round_coords(f["geometry"]["coordinates"])}}
                for f in gj["features"]]

    def geo_panchayats(self) -> s.PanchayatCollection:
        names = self.static.set_index("panchayat_id")["panchayat_name"]
        feats = self._features(loaders.load_panchayat_geojson(), lambda p: {
            "panchayat_id": p["panchayat_id"], "name": str(names.get(p["panchayat_id"], p["panchayat_id"])),
            "block_id": p["block_id"]})
        return s.PanchayatCollection(type="FeatureCollection", data_mode=self.mode, features=feats)

    def geo_blocks(self) -> s.BlockCollection:
        names = self.blocks.set_index("block_id")["block_name"]
        feats = self._features(loaders.load_block_geojson(), lambda p: {
            "block_id": p["block_id"], "name": str(names.get(p["block_id"], p["block_id"]))})
        return s.BlockCollection(type="FeatureCollection", data_mode=self.mode, features=feats)

    # ------------------------------------------------------------ forecast endpoints
    def forecast_map(self, issue: date, lead: int, var: s.Var) -> s.ForecastMap:
        self.check_issue(issue)
        t = self.table(issue)
        t = t[t["lead_day"] == lead]
        v = var.value
        block = t.drop_duplicates("block_id").sort_values("block_id")
        layer = []
        for r in t.itertuples(index=False):
            rd = r._asdict()
            pe = event = None
            if var == s.Var.rain:
                event = s.RainEvent.rain_ge_2_5mm
                pe = prob(prob_exceed(2.5, rd["rain_p10"], rd["rain_p50"], rd["rain_p90"]))
            layer.append(s.PanchayatMapValue(
                panchayat_id=rd["panchayat_id"], block_id=rd["block_id"], p10=num(rd[f"{v}_p10"]),
                p50=num(rd[f"{v}_p50"]), p90=num(rd[f"{v}_p90"]), block_value=num(rd[f"{v}_block"]),
                delta=num(rd[f"{v}_p50"] - rd[f"{v}_block"]), prob_event=pe, event=event))
        return s.ForecastMap(
            issue_date=issue, valid_date=issue + timedelta(days=lead), lead_day=lead, var=var,
            unit=s.UNITS[var],
            data_mode=self.mode, provenance=s.Provenance.provisional,
            block_layer=[s.BlockMapValue(block_id=b.block_id, value=num(getattr(b, f"{v}_block")))
                         for b in block.itertuples(index=False)],
            panchayat_layer=layer)

    def _quantiles(self, r: pd.Series, var: str) -> s.Quantiles:
        return s.Quantiles(**{q: num(r[f"{var}_{q}"]) for q in QS})

    def forecast_panchayat(self, pid: str, issue: date) -> s.PanchayatForecast:
        st = self.check_panchayat(pid)
        self.check_issue(issue)
        t = self.table(issue)
        days = []
        for _, r in t[t["panchayat_id"] == pid].sort_values("lead_day").iterrows():
            valid = r["valid_date"].date()
            probs = event_probs(r["rain_p10"], r["rain_p50"], r["rain_p90"])
            tmean = (r["tmax_p50"] + r["tmin_p50"]) / 2
            days.append(s.ForecastDay(
                date=valid, lead_day=int(r["lead_day"]),
                **{v: self._quantiles(r, v) for v in VARS},
                prob=s.EventProbs(**{k: prob(p) for k, p in probs.items()}),
                derived=s.Derived(
                    et0_mm=num(agro.et0_hargreaves(r["tmax_p50"], r["tmin_p50"], float(st["lat"]), valid), 1),
                    soil_moisture_frac=None, thi=num(agro.thi(tmean, r["rh_p50"]), 1), waterlog_risk=None)))
        return s.PanchayatForecast(
            panchayat_id=pid, name=str(st["panchayat_name"]), block_id=str(st["block_id"]), issue_date=issue,
            data_mode=self.mode, provenance=s.Provenance.provisional,
            static=s.StaticInfo(elevation_m=num(st["elevation_m"], 1), soil_texture=str(st["soil_texture"]),
                                drainage_class=str(st["drainage_class"]),
                                irrigated_frac=num(st["irrigated_frac"])),
            days=days)

    def observed(self, pid: str, start: date, end: date) -> s.Observed:
        self.check_panchayat(pid)
        if end < start:
            raise ApiError(400, "bad_request", "'to' must be on or after 'from'")
        if (end - start).days + 1 > MAX_OBSERVED_DAYS:
            raise ApiError(400, "bad_request", f"At most {MAX_OBSERVED_DAYS} days per request")
        st = self.stations[self.stations["panchayat_id"] == pid].sort_values("station_id")
        station_id: str | None = None
        if not st.empty:
            station_id = str(st.iloc[0]["station_id"])
            src, df = s.ObservedSource.station, self.obs_clean[self.obs_clean["station_id"] == station_id]
        elif self.mode == s.DataMode.mock:
            src, df = s.ObservedSource.synthetic_truth, self.truth[self.truth["panchayat_id"] == pid]
        else:
            src, df = s.ObservedSource.none, self.obs_clean.iloc[0:0]
        df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))].sort_values("date")
        days = [s.ObservedDay(date=r["date"].date(), **{v: num(r[COLS[v]]) for v in VARS})
                for _, r in df.iterrows()]
        return s.Observed(panchayat_id=pid, from_=start, to=end, source=src, station_id=station_id,
                          data_mode=self.mode, days=days)

    def explain(self, pid: str, issue: date, lead: int, var: s.Var) -> s.Explain:
        self.check_panchayat(pid)
        self.check_issue(issue)
        self.require_mock_for_placeholder("Explain")
        r = self._row(issue, pid, lead)
        v = var.value
        return s.Explain(panchayat_id=pid, issue_date=issue, lead_day=lead, var=var,
                         delta_vs_block=num(r[f"{v}_p50"] - r[f"{v}_block"]),
                         reasons=placeholders.explain_reasons(self.static, pid, v), data_mode=self.mode,
                         provenance=s.Provenance.placeholder, method="placeholder_static_contrast")

    def changes(self, pid: str, issue: date) -> s.ForecastChanges:
        self.check_panchayat(pid)
        self.check_issue(issue)
        prev_issue = issue - timedelta(days=1)
        cur = self.table(issue)
        cur = cur[cur["panchayat_id"] == pid].set_index("valid_date")
        prev_all = self._table_any(prev_issue)
        if prev_all is None:
            return s.ForecastChanges(panchayat_id=pid, issue_date=issue, previous_issue_date=None,
                                     data_mode=self.mode, provenance=s.Provenance.provisional, changes=[],
                                     event_changes=[], advice_changed=None, summary=texts.CHANGES_NONE)
        prev = prev_all[prev_all["panchayat_id"] == pid].set_index("valid_date")
        changes, events = [], []
        for vd in sorted(set(cur.index) & set(prev.index)):
            c, p = cur.loc[vd], prev.loc[vd]
            for v in VARS:
                d = c[f"{v}_p50"] - p[f"{v}_p50"]
                changes.append(s.VarChange(valid_date=vd.date(), var=v, previous_p50=num(p[f"{v}_p50"]),
                                           current_p50=num(c[f"{v}_p50"]), delta=num(d),
                                           material=bool(abs(d) >= MATERIAL_CHANGE[v])))
            pc = event_probs(c["rain_p10"], c["rain_p50"], c["rain_p90"])
            pp = event_probs(p["rain_p10"], p["rain_p50"], p["rain_p90"])
            for ev in s.RainEvent:
                a, b = pp[ev.value], pc[ev.value]
                if a is not None and b is not None and abs(b - a) >= MATERIAL_PROB_CHANGE:
                    events.append(s.EventChange(valid_date=vd.date(), event=ev, previous_prob=prob(a),
                                                current_prob=prob(b)))
        n = sum(ch.material for ch in changes)
        summary = texts.CHANGES_NONE if n == 0 else texts.fill(texts.CHANGES_SOME, prev_issue, n=n)
        return s.ForecastChanges(panchayat_id=pid, issue_date=issue, previous_issue_date=prev_issue,
                                 data_mode=self.mode, provenance=s.Provenance.provisional, changes=changes,
                                 event_changes=events, advice_changed=None,
                                 summary=s.LocalizedText(**summary))

    def _table_any(self, issue: date) -> pd.DataFrame | None:
        """Forecast table for any issue date present in the data (used for the previous day)."""
        if not (self.fc["issue_date"] == pd.Timestamp(issue)).any():
            return None
        return self.table(issue)

    # ------------------------------------------------------------ risk and priority
    def _risks(self, issue: date) -> pd.DataFrame:
        return risk_scores(self.table(issue))

    def risk(self, issue: date, lead: int, rtype: s.RiskType) -> s.Risk:
        self.check_issue(issue)
        r = self._risks(issue)
        r = r[(r["lead_day"] == lead) & (r["type"] == rtype.value)].sort_values("panchayat_id")
        items = [s.RiskItem(panchayat_id=x.panchayat_id, block_id=x.block_id, level=x.level,
                            score=prob(x.score))
                 for x in r.itertuples(index=False)]
        return s.Risk(issue_date=issue, valid_date=issue + timedelta(days=lead), lead_day=lead, type=rtype,
                      data_mode=self.mode, provenance=s.Provenance.provisional,
                      thresholds_status=s.ThresholdsStatus.placeholder, items=items)

    def _top_risks(self, issue: date, horizon: int) -> pd.DataFrame:
        """One row per Panchayat: its highest risk within the horizon, moderate or above only."""
        r = self._risks(issue)
        r = r[r["lead_day"] <= horizon].sort_values(["panchayat_id", "score", "lead_day", "type"],
                                                    ascending=[True, False, True, True])
        top = r.drop_duplicates("panchayat_id")
        top = top[top["level"] != "low"]
        return top.sort_values(["score", "panchayat_id"], ascending=[False, True]).reset_index(drop=True)

    def _crops_now(self, pid: str, on: date) -> pd.DataFrame:
        return agro.crops_in_season(self.crops, pid, pd.Timestamp(on))

    def _headline(self, issue: date, row: pd.Series) -> s.LocalizedText:
        f = self._row(issue, row["panchayat_id"], int(row["lead_day"]))
        vals = {"tmax": f"{f['tmax_p90']:.0f}", "tmin": f"{f['tmin_p10']:.0f}"}
        return s.LocalizedText(**texts.fill(texts.HEADLINE[row["type"]], row["valid_date"].date(), **vals))

    def priority(self, issue: date, horizon: int) -> s.Priority:
        self.check_issue(issue)
        items = []
        for _, row in self._top_risks(issue, horizon).iterrows():
            crops = sorted(self._crops_now(row["panchayat_id"], issue)["crop"].unique().tolist())
            items.append(s.PriorityItem(
                panchayat_id=row["panchayat_id"], block_id=row["block_id"], top_risk=row["type"],
                level=row["level"], score=prob(row["score"]), crops_affected=crops,
                headline=self._headline(issue, row), valid_date=row["valid_date"].date()))
        return s.Priority(issue_date=issue, horizon_days=horizon, data_mode=self.mode,
                          provenance=s.Provenance.provisional,
                          thresholds_status=s.ThresholdsStatus.placeholder, items=items)

    # ------------------------------------------------------------ advisories (placeholder generator)
    def _evidence(self, issue: date, category: str, row: pd.Series, stage: str | None) -> list[dict]:
        f = self._row(issue, row["panchayat_id"], int(row["lead_day"]))
        day = texts.day_text(row["valid_date"].date(), "en")
        ev: list[dict] = []
        if category == "spray":
            p = prob_exceed(2.5, f["rain_p10"], f["rain_p50"], f["rain_p90"]) or 0.0
            ev += [{"label": f"Chance of rain over 2.5 mm on {day}", "value": f"{p:.0%}"},
                   {"label": f"Rain expected on {day}",
                    "value": f"{f['rain_p50']:.0f} mm (range {f['rain_p10']:.0f} to {f['rain_p90']:.0f} mm)"}]
        elif category == "waterlogging":
            p = prob_exceed(10.0, f["rain_p10"], f["rain_p50"], f["rain_p90"]) or 0.0
            ev += [{"label": f"Chance of rain over 10 mm on {day}", "value": f"{p:.0%}"},
                   {"label": "Soil drainage", "value": str(f["drainage_class"])}]
        elif category == "heat_stress":
            ev.append({"label": f"Highest temperature, upper estimate, {day}",
                       "value": f"{f['tmax_p90']:.1f} C"})
        elif category == "frost":
            ev.append({"label": f"Lowest temperature, lower estimate, {day}",
                       "value": f"{f['tmin_p10']:.1f} C"})
        else:
            ev.append({"label": "Rain expected over the next 5 days",
                       "value": f"{self._rain5(issue, row):.0f} mm"})
        if stage:
            ev.append({"label": "Crop stage (placeholder calendar)", "value": stage.replace("_", " ")})
        return ev

    def _rain5(self, issue: date, row: pd.Series) -> float:
        t = self.table(issue)
        return float(t.loc[t["panchayat_id"] == row["panchayat_id"], "rain_p50"].sum())

    def _generate_advisories(self, issue: date) -> list[dict]:
        out = []
        created = datetime.combine(issue, time(8, 0, 0))
        top = self._top_risks(issue, ADVISORY_HORIZON)
        for _, row in top[top["level"].isin(ADVISORY_MIN_LEVELS)].iterrows():
            category = texts.CATEGORY_FOR_RISK[row["type"]]
            f = self._row(issue, row["panchayat_id"], int(row["lead_day"]))
            vals = {"tmax": f"{f['tmax_p90']:.0f}", "tmin": f"{f['tmin_p10']:.0f}",
                    "rain5": f"{self._rain5(issue, row):.0f}"}
            tpl = texts.ADVISORY[category]
            vd = row["valid_date"].date()
            lead = int(row["lead_day"])
            for _, c in self._crops_now(row["panchayat_id"], issue).sort_values("crop").iterrows():
                stage = agro.crop_stage(self.calendar, c["crop"], c["sowing_date"], pd.Timestamp(issue))
                adv_id = f"ADV-{issue.isoformat()}-{row['panchayat_id']}-{c['crop']}-{category}"
                out.append({
                    "id": adv_id, "issue_date": issue, "panchayat_id": row["panchayat_id"],
                    "block_id": row["block_id"], "crop": c["crop"], "stage": stage, "category": category,
                    "priority": row["level"], "valid_from": issue + timedelta(days=1),
                    "valid_to": issue + timedelta(days=ADVISORY_HORIZON),
                    **{k: texts.fill(tpl[k], vd, **vals) for k in ("action", "reason", "fallback")},
                    "confidence": "high" if lead == 1 else "medium" if lead <= 3 else "low",
                    "evidence": self._evidence(issue, category, row, stage),
                    "thresholds_status": "placeholder", "status": "draft",
                    "reviewed_by": None, "reviewed_at": None,
                    "audit": [{"at": created, "actor": "system", "action": "created",
                               "note": "Placeholder generator (S2). Rules engine arrives in S8."}],
                    "audio": {}, "provenance": "placeholder", "translation_status": "needs_native_review"})
        return out

    def _store(self) -> dict[str, dict]:
        with self._lock:
            store = self._advisories
        if store is None:
            store = {a["id"]: a for d in self.issue_dates for a in self._generate_advisories(d)}
            with self._lock:
                if self._advisories is None:
                    self._advisories = store
                store = self._advisories
        return store

    def _advisory(self, a: dict) -> s.Advisory:
        return s.Advisory(**a, data_mode=self.mode)

    def advisories(self, status: s.Status | None, pid: str | None, issue: date | None) -> s.AdvisoryList:
        if pid is not None:
            self.check_panchayat(pid)
        if issue is not None:
            self.check_issue(issue)
        items = [a for a in self._store().values()
                 if (status is None or a["status"] == status.value)
                 and (pid is None or a["panchayat_id"] == pid)
                 and (issue is None or a["issue_date"] == issue)]
        items.sort(key=lambda a: (a["issue_date"], -LEVEL_RANK[a["priority"]], a["id"]))
        return s.AdvisoryList(data_mode=self.mode, provenance=s.Provenance.placeholder, total=len(items),
                              items=[self._advisory(a) for a in items])

    def advisory(self, adv_id: str) -> s.Advisory:
        a = self._store().get(adv_id)
        if a is None:
            raise not_found(f"Advisory {adv_id} does not exist")
        return self._advisory(a)

    def review(self, adv_id: str, req: s.ReviewRequest) -> s.Advisory:
        store = self._store()
        if adv_id not in store:
            raise not_found(f"Advisory {adv_id} does not exist")
        edited = req.edited.model_dump(exclude_none=True) if req.edited else {}
        if req.action == s.ReviewAction.edit and not edited:
            raise ApiError(400, "bad_request", "An edit needs at least one of edited.action, edited.reason, "
                                               "edited.fallback")
        status = {"approve": "approved", "edit": "edited", "reject": "rejected"}[req.action.value]
        now = self.clock()
        with self._lock:
            a = store[adv_id]
            for field, text in edited.items():
                a[field] = {**a[field], **text}
            a["status"], a["reviewed_by"], a["reviewed_at"] = status, req.reviewer, now
            a["audit"] = [*a["audit"], {"at": now, "actor": req.reviewer, "action": status, "note": req.note}]
        return self._advisory(a)

    # ------------------------------------------------------------ farmers and feedback
    @cached_property
    def farmers(self) -> dict[str, dict]:
        """Deterministic demo farmers: one per block, preferring a Panchayat with a station."""
        with_station = set(self.stations["panchayat_id"])
        out = {}
        for i, b in enumerate(sorted(self.static["block_id"].unique())[:N_DEMO_FARMERS]):
            ps = sorted(self.static.loc[self.static["block_id"] == b, "panchayat_id"])
            has_crops = [p for p in ps if (self.crops["panchayat_id"] == p).any()]
            pick = next((p for p in has_crops if p in with_station), has_crops[0] if has_crops else ps[0])
            fid = f"F{i + 1:03d}"
            out[fid] = {"farmer_id": fid, "name": f"Demo farmer {i + 1}", "panchayat_id": pick, "block_id": b,
                        "language": FARMER_LANGS[i % len(FARMER_LANGS)]}
        return out

    def _farmer(self, fid: str) -> dict:
        f = self.farmers.get(fid)
        if f is None:
            raise not_found(f"Farmer {fid} does not exist")
        return f

    def farmer(self, fid: str) -> s.Farmer:
        f = self._farmer(fid)
        c = self.crops[(self.crops["panchayat_id"] == f["panchayat_id"])
                       & self.crops["season"].isin(FARMER_SEASONS)]
        crops = [s.FarmerCrop(crop=r["crop"], season=r["season"], sowing_date=r["sowing_date"].date(),
                              expected_harvest_date=r["expected_harvest_date"].date(),
                              area_fraction=num(r["crop_area_fraction"]))
                 for _, r in c.sort_values(["sowing_date", "crop"]).iterrows()]
        return s.Farmer(**f, crops=crops, data_mode=self.mode)

    def farmer_advice(self, fid: str, issue: date) -> s.FarmerAdvice:
        f = self._farmer(fid)
        self.check_issue(issue)
        items = [a for a in self._store().values()
                 if a["panchayat_id"] == f["panchayat_id"] and a["issue_date"] == issue
                 and a["status"] in ("approved", "edited")]
        items.sort(key=lambda a: (-LEVEL_RANK[a["priority"]], a["id"]))
        return s.FarmerAdvice(farmer_id=fid, panchayat_id=f["panchayat_id"], issue_date=issue,
                              language=f["language"], data_mode=self.mode,
                              items=[self._advisory(a) for a in items])

    def feedback(self, req: s.FeedbackRequest) -> s.FeedbackResponse:
        self.check_panchayat(req.panchayat_id)
        with self._lock:
            resp = s.FeedbackResponse(id=f"FB-{len(self._feedback) + 1:05d}", stored=True,
                                      received_at=self.clock(),
                                      data_mode=self.mode, feedback=req,
                                      message=s.LocalizedText(**texts.FEEDBACK_THANKS))
            self._feedback.append(resp)
        return resp

    # ------------------------------------------------------------ verification and impact (placeholders)
    def verification_summary(self) -> s.VerificationSummary:
        self.require_mock_for_placeholder("Verification")
        return s.VerificationSummary(**placeholders.verification_summary(), data_mode=self.mode,
                                     provenance=s.Provenance.placeholder)

    def reliability(self, event: s.RainEvent) -> s.Reliability:
        self.require_mock_for_placeholder("Verification")
        return s.Reliability(**placeholders.reliability(event.value), data_mode=self.mode,
                             provenance=s.Provenance.placeholder)

    def coverage(self) -> s.Coverage:
        self.require_mock_for_placeholder("Verification")
        return s.Coverage(**placeholders.coverage(), data_mode=self.mode, provenance=s.Provenance.placeholder)

    def regions(self) -> s.Regions:
        self.require_mock_for_placeholder("Verification")
        return s.Regions(**placeholders.regions(sorted(self.blocks["block_id"])), data_mode=self.mode,
                         provenance=s.Provenance.placeholder)

    def impact(self, season: str, decision: s.Decision) -> s.Impact:
        self.require_mock_for_placeholder("Impact")
        if season not in placeholders.IMPACT_SEASONS:
            avail = ", ".join(placeholders.IMPACT_SEASONS)
            raise not_found(f"Season {season} does not exist. Available: {avail}")
        return s.Impact(**placeholders.impact(season, decision.value, len(self.pids)),
                        data_mode=self.mode, provenance=s.Provenance.placeholder)

    # ------------------------------------------------------------ data quality
    def data_quality(self, as_of: date | None) -> s.DataQuality:
        as_of = self.check_issue(as_of) if as_of is not None else self.issue_dates[-1]
        end = pd.Timestamp(as_of)
        start = end - pd.Timedelta(days=29)
        q = self.qc_obs[(self.qc_obs["date"] >= start) & (self.qc_obs["date"] <= end)]
        hist = self.qc_obs[self.qc_obs["date"] <= end]
        value_cols = list(COLS.values())
        rows, missing_all, expected_all = [], 0, 0
        for st in self.stations.sort_values("station_id").itertuples(index=False):
            cols = [COLS["rain"]] if st.station_type == "ARG" else value_cols
            sq, sh = q[q["station_id"] == st.station_id], hist[hist["station_id"] == st.station_id]
            present = sh[sh[cols].notna().any(axis=1)]["date"]
            last = present.max() if not present.empty else None
            expected = 30 * len(cols)
            missing = expected - int(sq[cols].notna().sum().sum())
            missing_all, expected_all = missing_all + missing, expected_all + expected
            rows.append(s.StationStatus(
                station_id=st.station_id, station_type=st.station_type, block_id=st.block_id,
                last_report=last.date() if last is not None else None,
                reported_last_24h=bool(last is not None and last >= end - pd.Timedelta(days=1)),
                missing_share_30d=prob(missing / expected),
                flagged_share_30d=prob(sq["qc_any"].mean()) if len(sq) else None))
        stale = []
        inputs = (("block_forecast", self.fc["issue_date"]), ("station_observations", self.qc_obs["date"]),
                  ("satellite_weekly", loaders.load_sat()["week_start"]))
        for name, series in inputs:
            last = series[series <= end].max()
            ok = pd.notna(last)
            stale.append(s.StaleInput(input=name, last_date=last.date() if ok else None,
                                      days_stale=int((end - last).days) if ok else None))
        return s.DataQuality(as_of=as_of, data_mode=self.mode, provenance=s.Provenance.provisional,
                             stations_total=len(rows),
                             stations_reporting_24h=sum(r.reported_last_24h for r in rows),
                             missing_share_30d=prob(missing_all / expected_all) if expected_all else None,
                             stale_inputs=stale, stations=rows)


# Leads served by the forecast endpoints (1..5) and risk types, re-exported for the routes.
LEAD_MIN, LEAD_MAX = min(LEADS), max(LEADS)
__all__ = ["Service", "LEAD_MIN", "LEAD_MAX", "RISK_TYPES"]
