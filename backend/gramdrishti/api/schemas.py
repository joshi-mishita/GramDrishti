"""Pydantic models for every endpoint of the API contract (Appendix A, contract v0.1.1).

Rules that hold for every model:
- Missing numbers are ``null``. NaN and Infinity are rejected (``allow_inf_nan=False``).
- Unknown fields are rejected (``extra="forbid"``), so examples cannot drift from the models.
- Dates are ISO ``YYYY-MM-DD``; units are fixed: rain mm, temperature C, RH %, wind km/h.

Shapes that Appendix A does not spell out (for example ``/observed``, ``/risk``, ``/farmers``,
``/forecast/changes``, ``/verification/coverage``, ``/data-quality``) are defined here and recorded in
``contract/CHANGELOG.md`` and ``docs/DECISIONS.md``.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

API_VERSION = "0.1.1"


class ApiModel(BaseModel):
    """Base for all contract models: strict about extra fields and non-finite numbers."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, populate_by_name=True)


Num = float | None
Prob = Annotated[float, Field(ge=0.0, le=1.0)]


# ---------------------------------------------------------------- enums (A1)
class DataMode(StrEnum):
    mock = "mock"
    real = "real"


class Var(StrEnum):
    rain = "rain"
    tmax = "tmax"
    tmin = "tmin"
    rh = "rh"
    wind = "wind"


UNITS: dict[Var, str] = {Var.rain: "mm", Var.tmax: "C", Var.tmin: "C", Var.rh: "%", Var.wind: "km/h"}


class RiskType(StrEnum):
    heavy_rain = "heavy_rain"
    heat = "heat"
    frost = "frost"
    waterlogging = "waterlogging"
    dry_spell = "dry_spell"


class Level(StrEnum):
    low = "low"
    moderate = "moderate"
    high = "high"
    severe = "severe"


class Category(StrEnum):
    sowing = "sowing"
    irrigation = "irrigation"
    spray = "spray"
    fertilizer = "fertilizer"
    harvest = "harvest"
    heat_stress = "heat_stress"
    frost = "frost"
    waterlogging = "waterlogging"
    dry_spell = "dry_spell"
    pest_disease = "pest_disease"
    livestock = "livestock"


class Status(StrEnum):
    draft = "draft"
    approved = "approved"
    edited = "edited"
    rejected = "rejected"


class Confidence(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class Lang(StrEnum):
    en = "en"
    hi = "hi"
    pa = "pa"


class ReviewAction(StrEnum):
    approve = "approve"
    edit = "edit"
    reject = "reject"


class Intensity(StrEnum):
    none = "none"
    light = "light"
    moderate = "moderate"
    heavy = "heavy"


class Channel(StrEnum):
    app = "app"
    whatsapp = "whatsapp"
    ivr = "ivr"


class RainEvent(StrEnum):
    rain_ge_1mm = "rain_ge_1mm"
    rain_ge_2_5mm = "rain_ge_2_5mm"
    rain_ge_10mm = "rain_ge_10mm"
    rain_ge_35mm = "rain_ge_35mm"


class Split(StrEnum):
    train = "train"
    calib = "calib"
    test = "test"


class Provenance(StrEnum):
    """Where the numbers in a response come from (additive field, v0.1.1).

    provisional: computed from the data with an interim method (corrected block forecast B1).
    placeholder: generated example content; numbers are not results and must not be quoted.
    computed: produced by the final pipeline or verification job.
    """

    provisional = "provisional"
    placeholder = "placeholder"
    computed = "computed"


class ThresholdsStatus(StrEnum):
    placeholder = "placeholder"
    reviewed = "reviewed"


class TranslationStatus(StrEnum):
    needs_native_review = "needs_native_review"
    reviewed = "reviewed"


class ObservedSource(StrEnum):
    station = "station"
    synthetic_truth = "synthetic_truth"
    none = "none"


class Effect(StrEnum):
    warmer = "warmer"
    cooler = "cooler"
    wetter = "wetter"
    drier = "drier"
    more_humid = "more_humid"
    less_humid = "less_humid"
    windier = "windier"
    calmer = "calmer"


class Decision(StrEnum):
    spray = "spray"
    heat_alert = "heat_alert"
    irrigation_wait = "irrigation_wait"


# ---------------------------------------------------------------- shared objects
class ErrorBody(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    """Every 4xx/5xx body: ``{"error": {"code", "message"}}``."""

    error: ErrorBody


class LocalizedText(ApiModel):
    """Text in English, Hindi and Punjabi. Hindi and Punjabi may be null when not yet written."""

    en: str
    hi: str | None = None
    pa: str | None = None


class Quantiles(ApiModel):
    """p10, p50, p90 of the Panchayat forecast plus the block-level value for the same day."""

    p10: Num
    p50: Num
    p90: Num
    block: Num


# ---------------------------------------------------------------- health and meta
class Health(ApiModel):
    status: Literal["ok"]
    api_version: str
    data_mode: DataMode


class VarInfo(ApiModel):
    var: Var
    unit: str


class IssueDateInfo(ApiModel):
    """Why a demo issue date exists and which data window it sits in (additive, v0.1.1)."""

    date: date
    label: str
    split: Split


class Meta(ApiModel):
    api_version: str
    data_mode: DataMode
    district: str
    available_issue_dates: list[date]
    languages: list[Lang]
    crops: list[str]
    vars: list[VarInfo]
    issue_date_info: list[IssueDateInfo] | None = None


# ---------------------------------------------------------------- geo
Position = list[float]  # [longitude, latitude]


class PolygonGeometry(ApiModel):
    type: Literal["Polygon"]
    coordinates: list[list[Position]]


class MultiPolygonGeometry(ApiModel):
    type: Literal["MultiPolygon"]
    coordinates: list[list[list[Position]]]


Geometry = Annotated[PolygonGeometry | MultiPolygonGeometry, Field(discriminator="type")]


class PanchayatProperties(ApiModel):
    panchayat_id: str
    name: str
    block_id: str


class BlockProperties(ApiModel):
    block_id: str
    name: str


class PanchayatFeature(ApiModel):
    type: Literal["Feature"]
    geometry: Geometry
    properties: PanchayatProperties


class BlockFeature(ApiModel):
    type: Literal["Feature"]
    geometry: Geometry
    properties: BlockProperties


class PanchayatCollection(ApiModel):
    type: Literal["FeatureCollection"]
    data_mode: DataMode
    features: list[PanchayatFeature]


class BlockCollection(ApiModel):
    type: Literal["FeatureCollection"]
    data_mode: DataMode
    features: list[BlockFeature]


# ---------------------------------------------------------------- forecast
class BlockMapValue(ApiModel):
    block_id: str
    value: Num


class PanchayatMapValue(ApiModel):
    panchayat_id: str
    block_id: str
    p10: Num
    p50: Num
    p90: Num
    block_value: Num
    delta: Num
    prob_event: Prob | None
    event: RainEvent | None


class ForecastMap(ApiModel):
    issue_date: date
    valid_date: date
    lead_day: int
    var: Var
    unit: str
    data_mode: DataMode
    provenance: Provenance
    block_layer: list[BlockMapValue]
    panchayat_layer: list[PanchayatMapValue]


class StaticInfo(ApiModel):
    elevation_m: Num
    soil_texture: str | None
    drainage_class: str | None
    irrigated_frac: Num


class EventProbs(ApiModel):
    rain_ge_1mm: Prob | None
    rain_ge_2_5mm: Prob | None
    rain_ge_10mm: Prob | None
    rain_ge_35mm: Prob | None


class Derived(ApiModel):
    et0_mm: Num
    soil_moisture_frac: Num
    thi: Num
    waterlog_risk: Level | None


class ForecastDay(ApiModel):
    date: date
    lead_day: int
    rain: Quantiles
    tmax: Quantiles
    tmin: Quantiles
    rh: Quantiles
    wind: Quantiles
    prob: EventProbs
    derived: Derived


class PanchayatForecast(ApiModel):
    panchayat_id: str
    name: str
    block_id: str
    issue_date: date
    data_mode: DataMode
    provenance: Provenance
    static: StaticInfo
    days: list[ForecastDay]


class ObservedDay(ApiModel):
    date: date
    rain: Num
    tmax: Num
    tmin: Num
    rh: Num
    wind: Num


class Observed(ApiModel):
    panchayat_id: str
    from_: date = Field(alias="from")
    to: date
    source: ObservedSource
    station_id: str | None
    data_mode: DataMode
    days: list[ObservedDay]


class ExplainReason(ApiModel):
    feature: str
    effect: Effect
    text: LocalizedText


class Explain(ApiModel):
    panchayat_id: str
    issue_date: date
    lead_day: int
    var: Var
    delta_vs_block: Num
    reasons: list[ExplainReason]
    data_mode: DataMode
    provenance: Provenance
    method: str


class VarChange(ApiModel):
    valid_date: date
    var: Var
    previous_p50: Num
    current_p50: Num
    delta: Num
    material: bool


class EventChange(ApiModel):
    valid_date: date
    event: RainEvent
    previous_prob: Prob | None
    current_prob: Prob | None


class ForecastChanges(ApiModel):
    panchayat_id: str
    issue_date: date
    previous_issue_date: date | None
    data_mode: DataMode
    provenance: Provenance
    changes: list[VarChange]
    event_changes: list[EventChange]
    advice_changed: bool | None
    summary: LocalizedText


# ---------------------------------------------------------------- risk and priority
class RiskItem(ApiModel):
    panchayat_id: str
    block_id: str
    level: Level
    score: Prob


class Risk(ApiModel):
    issue_date: date
    valid_date: date
    lead_day: int
    type: RiskType
    data_mode: DataMode
    provenance: Provenance
    thresholds_status: ThresholdsStatus
    items: list[RiskItem]


class PriorityItem(ApiModel):
    panchayat_id: str
    block_id: str
    top_risk: RiskType
    level: Level
    score: Prob
    crops_affected: list[str]
    headline: LocalizedText
    valid_date: date | None = None


class Priority(ApiModel):
    issue_date: date
    horizon_days: int
    data_mode: DataMode
    provenance: Provenance
    thresholds_status: ThresholdsStatus
    items: list[PriorityItem]


# ---------------------------------------------------------------- advisories
class EvidenceItem(ApiModel):
    label: str
    value: str


class AuditEntry(ApiModel):
    at: datetime
    actor: str
    action: str
    note: str


class Advisory(ApiModel):
    id: str
    issue_date: date
    panchayat_id: str
    block_id: str
    crop: str
    stage: str | None
    category: Category
    priority: Level
    valid_from: date
    valid_to: date
    action: LocalizedText
    reason: LocalizedText
    fallback: LocalizedText
    confidence: Confidence
    evidence: list[EvidenceItem]
    thresholds_status: ThresholdsStatus
    status: Status
    reviewed_by: str | None
    reviewed_at: datetime | None
    audit: list[AuditEntry]
    audio: dict[Lang, str]
    data_mode: DataMode
    provenance: Provenance
    translation_status: TranslationStatus


class AdvisoryList(ApiModel):
    data_mode: DataMode
    provenance: Provenance
    total: int
    items: list[Advisory]


class EditedFields(ApiModel):
    action: LocalizedText | None = None
    reason: LocalizedText | None = None
    fallback: LocalizedText | None = None


class ReviewRequest(ApiModel):
    action: ReviewAction
    reviewer: str = Field(min_length=1)
    note: str = ""
    edited: EditedFields | None = None


# ---------------------------------------------------------------- farmers and feedback
class FarmerCrop(ApiModel):
    crop: str
    season: str
    sowing_date: date
    expected_harvest_date: date | None
    area_fraction: Num


class Farmer(ApiModel):
    farmer_id: str
    name: str
    panchayat_id: str
    block_id: str
    language: Lang
    crops: list[FarmerCrop]
    data_mode: DataMode


class FarmerAdvice(ApiModel):
    farmer_id: str
    panchayat_id: str
    issue_date: date
    language: Lang
    data_mode: DataMode
    items: list[Advisory]


class FeedbackRequest(ApiModel):
    panchayat_id: str
    date: date
    reported_rain: bool
    intensity: Intensity
    channel: Channel


class FeedbackResponse(ApiModel):
    id: str
    stored: bool
    received_at: datetime
    data_mode: DataMode
    feedback: FeedbackRequest
    message: LocalizedText


# ---------------------------------------------------------------- verification and impact
class Period(ApiModel):
    start: date
    end: date


class MetricRow(ApiModel):
    name: str
    unit: str
    model: Num
    b0: Num
    b1: Num
    b2: Num
    skill_vs_b0: Num
    skill_ci95: Annotated[list[float], Field(min_length=2, max_length=2)] | None


class VariableSummary(ApiModel):
    var: Var
    n: int | None
    metrics: list[MetricRow]


class EventSummary(ApiModel):
    event: RainEvent
    pod: Num
    far: Num
    csi: Num
    brier: Num
    brier_skill_vs_climatology: Num


class VerificationSummary(ApiModel):
    data_mode: DataMode
    provenance: Provenance
    method: str
    period: Period
    variables: list[VariableSummary]
    events: list[EventSummary]
    block_mean_error: dict[Var, Num]
    notes: list[str]


class ReliabilityPoint(ApiModel):
    forecast_prob: Prob
    observed_freq: Prob | None
    n: int


class Reliability(ApiModel):
    event: RainEvent
    data_mode: DataMode
    provenance: Provenance
    points: list[ReliabilityPoint]
    notes: list[str]


class CoverageItem(ApiModel):
    var: Var
    unit: str
    nominal: Prob
    empirical: Prob | None
    mean_width: Num
    n: int | None


class Coverage(ApiModel):
    data_mode: DataMode
    provenance: Provenance
    items: list[CoverageItem]
    notes: list[str]


class RegionItem(ApiModel):
    region_type: Literal["block", "station"]
    region_id: str
    var: Var
    metric: str
    unit: str
    model: Num
    b0: Num
    n: int | None


class Regions(ApiModel):
    data_mode: DataMode
    provenance: Provenance
    method: str
    items: list[RegionItem]
    notes: list[str]


class DecisionCounts(ApiModel):
    correct: int
    wasted_wait: int
    washed_off: int


class ImpactRule(ApiModel):
    model: LocalizedText
    block: LocalizedText


class Impact(ApiModel):
    season: str
    decision: Decision
    data_mode: DataMode
    provenance: Provenance
    model: DecisionCounts
    block_baseline: DecisionCounts
    n_decisions: int
    rule: ImpactRule | None = None
    notes: list[str] = []


# ---------------------------------------------------------------- data quality
class StationStatus(ApiModel):
    station_id: str
    station_type: str
    block_id: str
    last_report: date | None
    reported_last_24h: bool
    missing_share_30d: Prob | None
    flagged_share_30d: Prob | None


class StaleInput(ApiModel):
    input: str
    last_date: date | None
    days_stale: int | None


class DataQuality(ApiModel):
    as_of: date
    data_mode: DataMode
    provenance: Provenance
    stations_total: int
    stations_reporting_24h: int
    missing_share_30d: Prob | None
    stale_inputs: list[StaleInput]
    stations: list[StationStatus]
