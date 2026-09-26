/**
 * Aliases for generated contract types. Never hand-write response shapes:
 * regenerate schema.d.ts with `npm run gen:types` after the contract changes.
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type DataMode = Schemas["DataMode"];
export type Provenance = Schemas["Provenance"];
export type Lang = Schemas["Lang"];
export type Var = Schemas["Var"];
export type Level = Schemas["Level"];
export type LocalizedText = Schemas["LocalizedText"];
export type ErrorResponse = Schemas["ErrorResponse"];

export type Health = Schemas["Health"];
export type Meta = Schemas["Meta"];
export type IssueDateInfo = Schemas["IssueDateInfo"];
export type PanchayatCollection = Schemas["PanchayatCollection"];
export type BlockCollection = Schemas["BlockCollection"];
export type ForecastMap = Schemas["ForecastMap"];
export type PanchayatMapValue = Schemas["PanchayatMapValue"];
export type PanchayatForecast = Schemas["PanchayatForecast"];
export type ForecastDay = Schemas["ForecastDay"];
export type Quantiles = Schemas["Quantiles"];
export type EventProbs = Schemas["EventProbs"];
export type Derived = Schemas["Derived"];
export type Observed = Schemas["Observed"];
export type ObservedDay = Schemas["ObservedDay"];
export type ObservedSource = Schemas["ObservedSource"];
export type Explain = Schemas["Explain"];
export type ExplainReason = Schemas["ExplainReason"];
export type Effect = Schemas["Effect"];
export type ForecastChanges = Schemas["ForecastChanges"];
export type VarChange = Schemas["VarChange"];
export type EventChange = Schemas["EventChange"];
export type RainEvent = Schemas["RainEvent"];
export type Confidence = Schemas["Confidence"];
export type Priority = Schemas["Priority"];
export type AdvisoryList = Schemas["AdvisoryList"];
export type Advisory = Schemas["Advisory"];
export type Status = Schemas["Status"];
export type VerificationSummary = Schemas["VerificationSummary"];
export type Impact = Schemas["Impact"];
export type Decision = Schemas["Decision"];
export type Farmer = Schemas["Farmer"];
export type FarmerAdvice = Schemas["FarmerAdvice"];

export const VARS: readonly Var[] = ["rain", "tmax", "tmin", "rh", "wind"];
export const LANGS: readonly Lang[] = ["en", "hi", "pa"];
export const LEVELS: readonly Level[] = ["low", "moderate", "high", "severe"];
/** Rain events from lightest to heaviest; keys of EventProbs match RainEvent values. */
export const RAIN_EVENTS: readonly RainEvent[] = [
  "rain_ge_1mm",
  "rain_ge_2_5mm",
  "rain_ge_10mm",
  "rain_ge_35mm",
];
