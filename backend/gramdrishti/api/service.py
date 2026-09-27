"""Builds every API response from forecast snapshots, the rules engine, the SQLite store and the data files.

Forecast values come from the snapshots written by ``pipeline/run_daily.py`` (model output, agro-variables
and SHAP reasons; no model inference per request). A missing snapshot is a 503 ``not_computed``.
Risk, priority and advisories come from the YAML rules engine (``advisory/``) on top of the snapshot; every
threshold is a placeholder until expert review (``thresholds_status: "placeholder"``). Advisories, the
review audit log and farmer feedback live in SQLite (``store/db.py``); ``run_daily`` writes the drafts, and
the API writes them on first use when they are missing. Verification and impact come from the files the
verification job writes (``verify/run_validation.py``: ``artifacts/verification.json`` and ``impact.json``);
the API never computes or edits a score, and a missing file is a 503 ``not_computed``.

Nothing is loaded at import time; snapshots are read on first use and cached per issue date.
"""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable
from datetime import date, datetime, timedelta
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd

from gramdrishti.advisory import audio, spray
from gramdrishti.advisory.drafts import create_drafts
from gramdrishti.advisory.engine import EngineResult, fmt, generate
from gramdrishti.advisory.risk import RISK_TYPES, risk_scores
from gramdrishti.advisory.rules import RuleFile, TemplateFile, load_checked
from gramdrishti.api import schemas as s
from gramdrishti.api.errors import ApiError, not_found
from gramdrishti.contract.pick_demo_dates import DemoDate, load_demo_dates
from gramdrishti.data import loaders
from gramdrishti.data.config import ART, COLS, LEADS, VARS, data_mode
from gramdrishti.data.qc import clean_values, run_qc
from gramdrishti.explain.shap_explain import NEGLIGIBLE_DELTA
from gramdrishti.pipeline.run_daily import SNAPSHOTS, Snapshot, read_snapshot
from gramdrishti.provisional import agro, texts
from gramdrishti.store.db import VISIBLE_TO_FARMERS, Store
from gramdrishti.store.seed_demo import seed as seed_farmers

QS = ("p10", "p50", "p90", "block", "mean", "block_corrected")
# rain_ge_2_5mm -> snapshot column prob_rain_ge_2_5
EVENT_COLS = {e: "prob_" + e.value.removesuffix("mm") for e in s.RainEvent}
MAP_EVENT = s.RainEvent.rain_ge_2_5mm
SNAPSHOT_ENV = "GRAMDRISHTI_SNAPSHOT_DIR"
VERIFICATION_ENV = "GRAMDRISHTI_VERIFICATION_DIR"
VERIFICATION_FILES = {"verification": "verification.json", "impact": "impact.json"}
EXPLAIN_METHOD = "shap_tree_explainer_mean_model_block_contrast"
DISTRICT_MOCK = "Synthetic District"
MATERIAL_CHANGE = {"rain": 5.0, "tmax": 1.5, "tmin": 1.5, "rh": 10.0, "wind": 5.0}
MATERIAL_PROB_CHANGE = 0.15
MAX_OBSERVED_DAYS = 62
FEEDBACK_DUPLICATE_WINDOW = timedelta(minutes=10)
AUDIO_PATH = "/api/v1/audio/"
LEVEL_RANK = {"low": 0, "moderate": 1, "high": 2, "severe": 3}
RISK_ORDER = {t: i for i, t in enumerate(RISK_TYPES)}
# Advisory categories that count as "affected" by each risk type in /priority.
RISK_CATEGORIES = {"heavy_rain": {"spray", "fertilizer", "harvest", "sowing", "waterlogging", "irrigation"},
                   "heat": {"heat_stress"}, "frost": {"frost"},
                   "waterlogging": {"waterlogging", "fertilizer"}, "dry_spell": {"dry_spell", "irrigation"}}
ADVISORY_ID_DATE = slice(4, 14)  # "ADV-2024-09-09-..." -> "2024-09-09"


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

    def __init__(
    self,
    demo_dates: list[DemoDate] | None = None,
    clock: Callable[[], datetime] = _now,
    snapshot_dir: Path | None = None,
    db_path: Path | None = None,
    audio_dir: Path | None = None,
    verification_dir: Path | None = None,
    synth: audio.Synth = audio.gtts_synth,
) -> None:
    self._demo = demo_dates
    self.clock = clock

    self.snapshot_dir = (
        snapshot_dir
        or Path(os.environ.get(SNAPSHOT_ENV, SNAPSHOTS))
    )

    self._db_path = db_path

    # Farmer/audio support
    self.audio_dir = audio_dir or audio.AUDIO_DIR
    self.synth = synth

    # Verification/impact support
    self.verification_dir = (
        verification_dir
        or Path(os.environ.get(VERIFICATION_ENV, ART))
    )
    self._verif: dict[str, tuple[int, dict]] = {}

    self._lock = threading.Lock()
    self._drafts_lock = threading.Lock()
    self._snaps: dict[date, Snapshot] = {}
    self._tables: dict[date, pd.DataFrame] = {}
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
    def truth(self) -> pd.DataFrame:
        return loaders.load_truth()  # MOCK ONLY: served by /observed for display, never used as a feature

    @cached_property
    def pids(self) -> set[str]:
        return set(self.static["panchayat_id"])

    @cached_property
    def rules(self) -> tuple[RuleFile, TemplateFile]:
        """Checked rules.yaml and templates.yaml (a broken file fails loudly on first use)."""
        return load_checked()

    @cached_property
    def store(self) -> Store:
        """SQLite store: ``db_path`` if given, else ``GRAMDRISHTI_DB`` or ``artifacts/gramdrishti.sqlite``."""
        return Store(self._db_path)

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

    # ------------------------------------------------------------ snapshots and forecast table
    def snapshot(self, issue: date, required: bool = True) -> Snapshot | None:
        """The snapshot for ``issue`` (cached). Missing: 503 ``not_computed`` if required, else None."""
        with self._lock:
            snap = self._snaps.get(issue)
        if snap is None:
            snap = read_snapshot(self.snapshot_dir, issue)
            if snap is not None:
                if snap.manifest.get("data_mode") != self.mode.value:
                    built = snap.manifest.get("data_mode")
                    raise ApiError(503, "not_computed", f"The snapshot for {issue.isoformat()} was built in "
                                   f"{built} mode, the API runs in {self.mode.value}")
                with self._lock:
                    snap = self._snaps.setdefault(issue, snap)
        if snap is None and required:
            raise ApiError(503, "not_computed",
                           f"No forecast snapshot for {issue.isoformat()}. Run `cd backend && python -m "
                           "gramdrishti.pipeline.run_daily --all-demo-dates`.")
        return snap

    def model_version(self, issue: date) -> str | None:
        snap = self.snapshot(issue)
        return snap.manifest.get("model_version") if snap else None

    def table(self, issue: date) -> pd.DataFrame:
        """Wide Panchayat table for one issue date from its snapshot.

        Columns: ids, ``<var>_{p10,p50,p90,mean}``, ``<var>_block`` (raw block forecast B0),
        ``<var>_block_corrected`` (B1), ``prob_rain_ge_*``, agro-variables, lat and drainage_class.
        """
        with self._lock:
            cached = self._tables.get(issue)
        if cached is not None:
            return cached
        f = self.snapshot(issue).forecast.copy()
        for v in VARS:
            f[f"{v}_block"] = f[f"b0_{v}"]
            f[f"{v}_block_corrected"] = f[f"b1_{v}"]
        st = self.static[["panchayat_id", "lat", "drainage_class"]]
        t = f.merge(st, on="panchayat_id", how="left").sort_values(["panchayat_id", "lead_day"])
        t = t.reset_index(drop=True)
        th = self.rules[0].spray_thresholds()
        t["spray_rating"] = [r for _, g in t.groupby("panchayat_id", sort=False) for r in spray.plan(
            [prob(x) for x in g["prob_rain_ge_2_5"]], [num(x) for x in g["wind_p90"]], th)]
        with self._lock:
            return self._tables.setdefault(issue, t)

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
        snap = self.snapshot(issue)
        t = self.table(issue)
        t = t[t["lead_day"] == lead]
        v = var.value
        ev = MAP_EVENT if var == s.Var.rain else None
        layer = [s.PanchayatMapValue(
            panchayat_id=r["panchayat_id"], block_id=r["block_id"], p10=num(r[f"{v}_p10"]),
            p50=num(r[f"{v}_p50"]), p90=num(r[f"{v}_p90"]), block_value=num(r[f"{v}_block"]),
            delta=num(r[f"{v}_p50"] - r[f"{v}_block"]), prob_event=prob(r[EVENT_COLS[ev]]) if ev else None,
            event=ev, mean=num(r[f"{v}_mean"]))
            for _, r in t.iterrows()]
        b = snap.block[snap.block["lead_day"] == lead].sort_values("block_id")
        return s.ForecastMap(
            issue_date=issue, valid_date=issue + timedelta(days=lead), lead_day=lead, var=var,
            unit=s.UNITS[var], data_mode=self.mode, provenance=s.Provenance.computed,
            block_layer=[s.BlockMapValue(block_id=r["block_id"], value=num(r[f"b0_{v}"]),
                                         corrected=num(r[f"b1_{v}"])) for _, r in b.iterrows()],
            panchayat_layer=layer, model_version=snap.manifest.get("model_version"))

    def _quantiles(self, r: pd.Series, var: str) -> s.Quantiles:
        return s.Quantiles(**{q: num(r[f"{var}_{q}"]) for q in QS})

    def _derived(self, r: pd.Series, crops_now: list[str]) -> s.Derived:
        def level(x: object) -> str | None:
            return x if isinstance(x, str) else None

        def whole(x: object) -> int | None:
            v = num(x, 0)
            return None if v is None else int(v)

        return s.Derived(
            et0_mm=num(r["et0_mm"], 1), soil_moisture_frac=num(r["soil_moisture_frac"]), thi=num(r["thi"], 1),
            waterlog_risk=level(r["waterlog_risk"]),
            soil_moisture_frac_dry=num(r["soil_moisture_frac_dry"]),
            soil_moisture_frac_wet=num(r["soil_moisture_frac_wet"]),
            depletion_frac=num(r["depletion_frac"]),
            gdd={c: v for c in crops_now if (v := num(r[f"gdd_{c}"], 1)) is not None},
            frost_prob=prob(r["frost_prob"]), frost_risk=level(r["frost_risk"]),
            fog_proxy=bool(r["fog_proxy"]), dry_spell_days=whole(r["dry_spell_days"]),
            spray_rating=r["spray_rating"])

    def forecast_panchayat(self, pid: str, issue: date) -> s.PanchayatForecast:
        st = self.check_panchayat(pid)
        self.check_issue(issue)
        t = self.table(issue)
        crops_now = sorted(c for c in self._crops_now(pid, issue)["crop"].unique()
                           if f"gdd_{c}" in t.columns)
        days = []
        for _, r in t[t["panchayat_id"] == pid].sort_values("lead_day").iterrows():
            days.append(s.ForecastDay(
                date=r["valid_date"].date(), lead_day=int(r["lead_day"]),
                **{v: self._quantiles(r, v) for v in VARS},
                prob=s.EventProbs(**{e.value: prob(r[col]) for e, col in EVENT_COLS.items()}),
                derived=self._derived(r, crops_now)))
        return s.PanchayatForecast(
            panchayat_id=pid, name=str(st["panchayat_name"]), block_id=str(st["block_id"]), issue_date=issue,
            data_mode=self.mode, provenance=s.Provenance.computed,
            static=s.StaticInfo(elevation_m=num(st["elevation_m"], 1), soil_texture=str(st["soil_texture"]),
                                drainage_class=str(st["drainage_class"]),
                                irrigated_frac=num(st["irrigated_frac"])),
            days=days, model_version=self.model_version(issue),
            thresholds_status=s.ThresholdsStatus.placeholder)

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
        """Top 3 SHAP reasons. ``delta_vs_block`` is the model mean minus the corrected block forecast
        (the quantity the reasons explain); no reasons when that difference is negligible."""
        self.check_panchayat(pid)
        self.check_issue(issue)
        snap = self.snapshot(issue)
        r = self._row(issue, pid, lead)
        v = var.value
        delta = float(r[f"{v}_mean"] - r[f"{v}_block_corrected"])
        e = snap.explain
        e = e[(e["panchayat_id"] == pid) & (e["lead_day"] == lead) & (e["var"] == v)].sort_values("rank")
        reasons = [] if abs(delta) < NEGLIGIBLE_DELTA[v] else [
            s.ExplainReason(feature=x["feature"], effect=x["effect"],
                            text=s.LocalizedText(en=x["text_en"], hi=None, pa=None))
            for _, x in e.iterrows()]
        return s.Explain(panchayat_id=pid, issue_date=issue, lead_day=lead, var=var,
                         delta_vs_block=num(delta), reasons=reasons, data_mode=self.mode,
                         provenance=s.Provenance.computed, method=EXPLAIN_METHOD,
                         model_version=snap.manifest.get("model_version"))

    def changes(self, pid: str, issue: date) -> s.ForecastChanges:
        """Compare with the snapshot of the previous day's issue for the valid dates both cover."""
        self.check_panchayat(pid)
        self.check_issue(issue)
        cur = self.table(issue)
        cur = cur[cur["panchayat_id"] == pid].set_index("valid_date")
        prev_issue = issue - timedelta(days=1)
        common = {"panchayat_id": pid, "issue_date": issue, "data_mode": self.mode,
                  "provenance": s.Provenance.computed, "model_version": self.model_version(issue)}
        if self.snapshot(prev_issue, required=False) is None:
            return s.ForecastChanges(**common, advice_changed=None, previous_issue_date=None, changes=[],
                                     event_changes=[], summary=s.LocalizedText(**texts.CHANGES_NO_PREVIOUS))
        common["advice_changed"] = self._advice_keys(issue, pid) != self._advice_keys(prev_issue, pid)
        prev = self.table(prev_issue)
        prev = prev[prev["panchayat_id"] == pid].set_index("valid_date")
        changes, events = [], []
        for vd in sorted(set(cur.index) & set(prev.index)):
            c, p = cur.loc[vd], prev.loc[vd]
            for v in VARS:
                d = c[f"{v}_p50"] - p[f"{v}_p50"]
                changes.append(s.VarChange(valid_date=vd.date(), var=v, previous_p50=num(p[f"{v}_p50"]),
                                           current_p50=num(c[f"{v}_p50"]), delta=num(d),
                                           material=bool(abs(d) >= MATERIAL_CHANGE[v])))
            for ev, col in EVENT_COLS.items():
                a, b = p[col], c[col]
                if pd.notna(a) and pd.notna(b) and abs(b - a) >= MATERIAL_PROB_CHANGE:
                    events.append(s.EventChange(valid_date=vd.date(), event=ev, previous_prob=prob(a),
                                                current_prob=prob(b)))
        n = sum(ch.material for ch in changes) + len(events)
        summary = texts.CHANGES_NONE if n == 0 else texts.fill(texts.CHANGES_SOME, prev_issue, n=n)
        return s.ForecastChanges(**common, previous_issue_date=prev_issue, changes=changes,
                                 event_changes=events, summary=s.LocalizedText(**summary))

    # ------------------------------------------------------------ rules engine, risk and priority
    def engine(self, issue: date) -> EngineResult:
        """Rules engine output for any date with a snapshot (cached). Not stored; see ``ensure_drafts``."""
        with self._lock:
            cached = self._engine.get(issue)
        if cached is not None:
            return cached
        snap = self.snapshot(issue)
        res = generate(issue, snap.forecast, self.static, self.crops, self.calendar, *self.rules)
        with self._lock:
            return self._engine.setdefault(issue, res)

    def _advice_keys(self, issue: date, pid: str) -> set[tuple[str, str, str]]:
        return {(a["crop"], a["category"], a["rule_id"]) for a in self.engine(issue).advisories
                if a["panchayat_id"] == pid}

    def _risks(self, issue: date) -> pd.DataFrame:
        with self._lock:
            cached = self._risk.get(issue)
        if cached is not None:
            return cached
        ctxs = self.engine(issue).contexts
        r = risk_scores(self.snapshot(issue).forecast, self.static, ctxs, self.rules[0])
        with self._lock:
            return self._risk.setdefault(issue, r)

    def risk(self, issue: date, lead: int, rtype: s.RiskType) -> s.Risk:
        self.check_issue(issue)
        r = self._risks(issue)
        r = r[(r["lead_day"] == lead) & (r["type"] == rtype.value)].sort_values("panchayat_id")
        items = [s.RiskItem(panchayat_id=x.panchayat_id, block_id=x.block_id, level=x.level,
                            score=prob(x.score))
                 for x in r.itertuples(index=False)]
        return s.Risk(issue_date=issue, valid_date=issue + timedelta(days=lead), lead_day=lead, type=rtype,
                      data_mode=self.mode, provenance=s.Provenance.computed,
                      thresholds_status=s.ThresholdsStatus.placeholder, items=items)

    def _top_risks(self, issue: date, horizon: int) -> pd.DataFrame:
        """One row per Panchayat: its worst risk within the horizon (level, then score, then the earlier day),
        moderate or above only, ranked by level, then score, then Panchayat id."""
        r = self._risks(issue)
        r = r[(r["lead_day"] <= horizon) & (r["level"] != "low")].copy()
        r["rank"] = r["level"].map(LEVEL_RANK)
        r["order"] = r["type"].map(RISK_ORDER)
        r = r.sort_values(["panchayat_id", "rank", "score", "lead_day", "order"],
                          ascending=[True, False, False, True, True])
        top = r.drop_duplicates("panchayat_id")
        return top.sort_values(["rank", "score", "panchayat_id"], ascending=[False, False, True]).reset_index(
            drop=True)

    def _crops_now(self, pid: str, on: date) -> pd.DataFrame:
        return agro.crops_in_season(self.crops, pid, pd.Timestamp(on))

    def _headline(self, issue: date, row: pd.Series) -> s.LocalizedText:
        """Plain one-line headline from templates.yaml with the numbers behind the risk."""
        tf = self.rules[1]
        f = self._row(issue, row["panchayat_id"], int(row["lead_day"]))
        out = {}
        for lang in ("en", "hi", "pa"):
            vals = {"day": texts.day_text(row["valid_date"].date(), lang),
                    "score": fmt(row["score"], "prob", lang, tf),
                    "tmax_p90": fmt(f["tmax_p90"], "C", lang, tf),
                    "tmin_p10": fmt(f["tmin_p10"], "C", lang, tf),
                    "dry_days": fmt(f["dry_spell_days"], "days", lang, tf)}
            out[lang] = getattr(tf.headlines[row["type"]], lang).format_map(vals)
        return s.LocalizedText(**out)

    def priority(self, issue: date, horizon: int) -> s.Priority:
        self.check_issue(issue)
        advs = self.engine(issue).advisories
        items = []
        for _, row in self._top_risks(issue, horizon).iterrows():
            cats = RISK_CATEGORIES[row["type"]]
            crops = sorted({a["crop"] for a in advs if a["panchayat_id"] == row["panchayat_id"]
                            and a["category"] in cats and a["crop"] != "livestock"})
            items.append(s.PriorityItem(
                panchayat_id=row["panchayat_id"], block_id=row["block_id"], top_risk=row["type"],
                level=row["level"], score=prob(row["score"]), crops_affected=crops,
                headline=self._headline(issue, row), valid_date=row["valid_date"].date()))
        return s.Priority(issue_date=issue, horizon_days=horizon, data_mode=self.mode,
                          provenance=s.Provenance.computed,
                          thresholds_status=s.ThresholdsStatus.placeholder, items=items)

    # ------------------------------------------------------------ advisories (rules engine + SQLite)
    def ensure_drafts(self, issue: date) -> None:
        """Write the engine's drafts for ``issue`` into the store unless a run already did."""
        info = self.store.run_info(issue)
        if info is None:
            with self._drafts_lock:
                if self.store.run_info(issue) is None:
                    snap = self.snapshot(issue)
                    create_drafts(self.store, issue, snap.forecast, self.static, self.crops, self.calendar,
                                  data_mode=self.mode.value, model_version=snap.manifest.get("model_version"),
                                  rules=self.rules)
                    info = self.store.run_info(issue)
        if info is not None and info["data_mode"] != self.mode.value:
            raise ApiError(503, "not_computed", f"Advisories for {issue.isoformat()} were built in "
                           f"{info['data_mode']} mode, the API runs in {self.mode.value}")

    def _audio_links(self, a: dict) -> dict[str, str]:
        """Audio URLs for advisories farmers can see, in the languages gTTS lists and the text exists.
        A link can still answer 404 (no internet to make the file); the UI then uses browser speech."""
        if a["status"] not in VISIBLE_TO_FARMERS:
            return {}
        langs = audio.supported_langs() if self.synth is audio.gtts_synth else frozenset(audio.LANGS)
        return {lang: f"{AUDIO_PATH}{a['id']}?lang={lang}" for lang in audio.LANGS
                if lang in langs and audio.speech_text(a, lang) is not None}

    def _advisory(self, a: dict) -> s.Advisory:
        return s.Advisory(**a, audio=self._audio_links(a), data_mode=self.mode,
                          provenance=s.Provenance.computed)

    def audio(self, adv_id: str, lang: s.Lang) -> Path:
        """Cached MP3 of an advisory's text; 404 ``audio_not_available`` when it cannot be made."""
        self.ensure_drafts(self._issue_of(adv_id))
        a = self.store.get(adv_id)
        if a is None:
            raise not_found(f"Advisory {adv_id} does not exist")
        try:
            return audio.audio_file(a, lang.value, self.audio_dir, self.synth)
        except audio.AudioUnavailable as exc:
            raise ApiError(404, "audio_not_available", str(exc)) from None

    def advisories(self, status: s.Status | None, pid: str | None, issue: date | None) -> s.AdvisoryList:
        if pid is not None:
            self.check_panchayat(pid)
        if issue is not None:
            self.check_issue(issue)
        for d in [issue] if issue is not None else self.issue_dates:
            self.ensure_drafts(d)
        items = self.store.list(status.value if status else None, pid, issue)
        items.sort(key=lambda a: (a["issue_date"], -LEVEL_RANK[a["priority"]], a["id"]))
        return s.AdvisoryList(data_mode=self.mode, provenance=s.Provenance.computed, total=len(items),
                              items=[self._advisory(a) for a in items])

    def _issue_of(self, adv_id: str) -> date:
        try:
            issue = date.fromisoformat(adv_id[ADVISORY_ID_DATE])
        except ValueError:
            raise not_found(f"Advisory {adv_id} does not exist") from None
        if issue not in self.issue_dates:
            raise not_found(f"Advisory {adv_id} does not exist")
        return issue

    def advisory(self, adv_id: str) -> s.Advisory:
        self.ensure_drafts(self._issue_of(adv_id))
        a = self.store.get(adv_id)
        if a is None:
            raise not_found(f"Advisory {adv_id} does not exist")
        return self._advisory(a)

    def review(self, adv_id: str, req: s.ReviewRequest) -> s.Advisory:
        self.ensure_drafts(self._issue_of(adv_id))
        edited = req.edited.model_dump(exclude_none=True) if req.edited else {}
        if req.action == s.ReviewAction.edit and not edited:
            raise ApiError(400, "bad_request", "An edit needs at least one of edited.action, edited.reason, "
                                               "edited.fallback")
        if req.action != s.ReviewAction.edit and edited:
            raise ApiError(400, "bad_request", "Only an edit may change the text; send action 'edit'")
        a = self.store.review(adv_id, req.action.value, req.reviewer, req.note, edited, self.clock())
        if a is None:
            raise not_found(f"Advisory {adv_id} does not exist")
        return self._advisory(a)

    # ------------------------------------------------------------ farmers and feedback
    @property
    def farmers(self) -> dict[str, dict]:
        """Demo farmers from the store, seeded from ``store/seed_demo.py`` when the table is empty."""
        farmers = self.store.farmers()
        if not farmers:
            with self._drafts_lock:
                farmers = self.store.farmers()
                if not farmers:
                    seed_farmers(self.store)
                    farmers = self.store.farmers()
        return farmers

    def _farmer(self, fid: str) -> dict:
        f = self.farmers.get(fid)
        if f is None:
            raise not_found(f"Farmer {fid} does not exist")
        return f

    def farmer(self, fid: str) -> s.Farmer:
        f = self._farmer(fid)
        block = self.check_panchayat(f["panchayat_id"])["block_id"]
        crops = [s.FarmerCrop(**c) for c in f["crops"]]
        return s.Farmer(farmer_id=fid, name=f["name"], panchayat_id=f["panchayat_id"], block_id=block,
                        language=f["language"], crops=crops, livestock=f["livestock"], data_mode=self.mode)

    def spray_days(self, pid: str, issue: date) -> list[s.SprayDay]:
        """Whole-day spray ratings for the five forecast days at one Panchayat."""
        t = self.table(issue)
        t = t[t["panchayat_id"] == pid].sort_values("lead_day")
        return [s.SprayDay(date=r.valid_date.date(), lead_day=int(r.lead_day), rating=r.spray_rating)
                for r in t.itertuples(index=False)]

    def farmer_advice(self, fid: str, issue: date) -> s.FarmerAdvice:
        """Approved or edited advisories for the farmer's Panchayat and crops (livestock advice only for
        farmers who keep livestock), most urgent first, plus day-level spray ratings."""
        f = self._farmer(fid)
        self.check_issue(issue)
        self.ensure_drafts(issue)
        crops = {c["crop"] for c in f["crops"]} | ({"livestock"} if f["livestock"] else set())
        items = [a for a in self.store.list(panchayat_id=f["panchayat_id"], issue=issue,
                                            statuses=VISIBLE_TO_FARMERS) if a["crop"] in crops]
        items.sort(key=lambda a: (-LEVEL_RANK[a["priority"]], a["valid_from"], a["id"]))
        return s.FarmerAdvice(farmer_id=fid, panchayat_id=f["panchayat_id"], issue_date=issue,
                              language=f["language"], data_mode=self.mode,
                              items=[self._advisory(a) for a in items],
                              spray_days=self.spray_days(f["panchayat_id"], issue))

    @cached_property
    def feedback_dates(self) -> tuple[date, date]:
        """First and last date a report can be about: the days the block forecast covers."""
        return self.fc["valid_date"].min().date(), self.fc["valid_date"].max().date()

    def feedback(self, req: s.FeedbackRequest) -> s.FeedbackResponse:
        """Store a "Did it rain?" report. The Panchayat must exist and the date must lie inside the data
        period and not in the future. An identical report within 10 minutes is not stored again: the
        answer carries the first report's id and ``stored: false``."""
        self.check_panchayat(req.panchayat_id)
        now = self.clock()
        first, last = self.feedback_dates
        last = min(last, now.date())
        if not first <= req.date <= last:
            raise ApiError(400, "bad_request", f"Reports can be about {first.isoformat()} to "
                           f"{last.isoformat()}; {req.date.isoformat()} is outside that period")
        if req.intensity == s.Intensity.none and req.reported_rain:
            raise ApiError(400, "bad_request", "reported_rain is true but intensity is 'none'")
        if req.intensity != s.Intensity.none and not req.reported_rain:
            raise ApiError(400, "bad_request", "reported_rain is false, so intensity must be 'none'")
        args = (req.panchayat_id, req.date, req.reported_rain, req.intensity.value, req.channel.value)
        dup = self.store.recent_feedback(*args, since=now - FEEDBACK_DUPLICATE_WINDOW)
        if dup is not None:
            return s.FeedbackResponse(id=f"FB-{dup:05d}", stored=False, received_at=now, data_mode=self.mode,
                                      feedback=req, message=s.LocalizedText(**texts.FEEDBACK_DUPLICATE))
        fid = self.store.add_feedback(*args, now)
        return s.FeedbackResponse(id=f"FB-{fid:05d}", stored=True, received_at=now, data_mode=self.mode,
                                  feedback=req, message=s.LocalizedText(**texts.FEEDBACK_THANKS))

    # ------------------------------------------------------------ verification and impact
    def _verification_file(self, key: str) -> dict:
        """``verification.json`` or ``impact.json`` from the verification job (cached per file mtime).
        Missing, or built in another data mode: 503 ``not_computed``."""
        path = self.verification_dir / VERIFICATION_FILES[key]
        if not path.exists():
            raise ApiError(503, "not_computed", f"{VERIFICATION_FILES[key]} has not been computed. Run "
                           "`cd backend && python -m gramdrishti.verify.run_validation`.")
        mtime = path.stat().st_mtime_ns
        with self._lock:
            cached = self._verif.get(key)
        if cached is None or cached[0] != mtime:
            cached = (mtime, json.loads(path.read_text()))
            with self._lock:
                self._verif[key] = cached
        payload = cached[1]
        built = payload["data_mode"] if key == "impact" else payload["summary"]["data_mode"]
        if built != self.mode.value:
            raise ApiError(503, "not_computed", f"{VERIFICATION_FILES[key]} was computed in {built} mode, "
                           f"the API runs in {self.mode.value}")
        return payload

    def verification_summary(self) -> s.VerificationSummary:
        return s.VerificationSummary.model_validate(self._verification_file("verification")["summary"])

    def reliability(self, event: s.RainEvent) -> s.Reliability:
        items = self._verification_file("verification")["reliability"]
        found = next((r for r in items if r["event"] == event.value), None)
        if found is None:
            raise ApiError(503, "not_computed", f"No reliability points for {event.value}")
        return s.Reliability.model_validate(found)

    def coverage(self) -> s.Coverage:
        return s.Coverage.model_validate(self._verification_file("verification")["coverage"])

    def regions(self) -> s.Regions:
        return s.Regions.model_validate(self._verification_file("verification")["regions"])

    def impact(self, season: str, decision: s.Decision) -> s.Impact:
        items = self._verification_file("impact")["items"]
        found = items.get(f"{season}/{decision.value}")
        if found is None:
            seasons = sorted({k.split("/")[0] for k in items})
            raise not_found(f"Season {season} does not exist. Available: {', '.join(seasons)}")
        return s.Impact.model_validate(found)

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
        return s.DataQuality(as_of=as_of, data_mode=self.mode, provenance=s.Provenance.computed,
                             stations_total=len(rows),
                             stations_reporting_24h=sum(r.reported_last_24h for r in rows),
                             missing_share_30d=prob(missing_all / expected_all) if expected_all else None,
                             stale_inputs=stale, stations=rows)


# Leads served by the forecast endpoints (1..5) and risk types, re-exported for the routes.
LEAD_MIN, LEAD_MAX = min(LEADS), max(LEADS)
__all__ = ["Service", "LEAD_MIN", "LEAD_MAX", "RISK_TYPES"]
