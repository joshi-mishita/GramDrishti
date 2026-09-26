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
