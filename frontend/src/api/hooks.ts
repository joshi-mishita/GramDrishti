/**
 * One TanStack Query hook per endpoint (Frontend Guide 9.1). Server data stays in the
 * query cache; never copy it into the zustand store.
 */
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";
import type {
  AdvisoryList,
  BlockCollection,
  Decision,
  Farmer,
  FarmerAdvice,
  ForecastMap,
  PanchayatForecast,
  Impact,
  Meta,
  PanchayatCollection,
  Priority,
  Status,
  Var,
  VerificationSummary,
} from "./types";

const MINUTE = 60_000;

export const queryKeys = {
  meta: ["meta"] as const,
  geoPanchayats: ["geo", "panchayats"] as const,
  geoBlocks: ["geo", "blocks"] as const,
  forecastMap: (issueDate: string, leadDay: number, variable: Var) =>
    ["forecastMap", issueDate, leadDay, variable] as const,
  forecastPanchayat: (pid: string, issueDate: string) =>
    ["forecastPanchayat", pid, issueDate] as const,
  priority: (issueDate: string, horizonDays: number) =>
    ["priority", issueDate, horizonDays] as const,
  advisories: (status: Status | undefined, issueDate: string) =>
    ["advisories", status ?? "all", issueDate] as const,
  verificationSummary: ["verification", "summary"] as const,
  impact: (decision: Decision, season: string) => ["impact", decision, season] as const,
  farmer: (id: string) => ["farmer", id] as const,
  farmerAdvice: (id: string, issueDate: string) => ["farmerAdvice", id, issueDate] as const,
};

export const useMeta = () =>
  useQuery({
    queryKey: queryKeys.meta,
    queryFn: ({ signal }) => apiGet<Meta>("/meta", {}, undefined, signal),
    staleTime: 10 * MINUTE,
  });

export const useGeoPanchayats = () =>
  useQuery({
    queryKey: queryKeys.geoPanchayats,
    queryFn: ({ signal }) => apiGet<PanchayatCollection>("/geo/panchayats", {}, undefined, signal),
    staleTime: Infinity,
  });

export const useGeoBlocks = () =>
  useQuery({
    queryKey: queryKeys.geoBlocks,
    queryFn: ({ signal }) => apiGet<BlockCollection>("/geo/blocks", {}, undefined, signal),
    staleTime: Infinity,
  });

export const useForecastMap = (issueDate: string | null, leadDay: number, variable: Var) =>
  useQuery({
    queryKey: queryKeys.forecastMap(issueDate ?? "", leadDay, variable),
    queryFn: ({ signal }) =>
      apiGet<ForecastMap>(
        "/forecast/map",
        { issue_date: issueDate, lead_day: leadDay, var: variable },
        undefined,
        signal,
      ),
    enabled: !!issueDate,
    staleTime: 5 * MINUTE,
  });

/** 5-day forecast of one Panchayat, all variables. Disabled until a Panchayat is chosen. */
export const useForecastPanchayat = (pid: string | null, issueDate: string | null) =>
  useQuery({
    queryKey: queryKeys.forecastPanchayat(pid ?? "", issueDate ?? ""),
    queryFn: ({ signal }) =>
      apiGet<PanchayatForecast>(
        `/forecast/panchayat/${encodeURIComponent(pid ?? "")}`,
        { issue_date: issueDate },
        undefined,
        signal,
      ),
    enabled: !!pid && !!issueDate,
    staleTime: 5 * MINUTE,
  });

export const usePriority = (issueDate: string | null, horizonDays = 2) =>
  useQuery({
    queryKey: queryKeys.priority(issueDate ?? "", horizonDays),
    queryFn: ({ signal }) =>
      apiGet<Priority>(
        "/priority",
        { issue_date: issueDate, horizon_days: horizonDays },
        undefined,
        signal,
      ),
    enabled: !!issueDate,
    staleTime: 5 * MINUTE,
  });

/** Review queue: staleTime 0 so a decision made elsewhere shows up (Guide 9.1). */
export const useAdvisories = (issueDate: string | null, status?: Status) =>
  useQuery({
    queryKey: queryKeys.advisories(status, issueDate ?? ""),
    queryFn: ({ signal }) =>
      apiGet<AdvisoryList>("/advisories", { status, issue_date: issueDate }, undefined, signal),
    enabled: !!issueDate,
    staleTime: 0,
  });

export const useVerificationSummary = () =>
  useQuery({
    queryKey: queryKeys.verificationSummary,
    queryFn: ({ signal }) =>
      apiGet<VerificationSummary>("/verification/summary", {}, undefined, signal),
    staleTime: 10 * MINUTE,
  });

export const useImpact = (decision: Decision, season = "monsoon_2024") =>
  useQuery({
    queryKey: queryKeys.impact(decision, season),
    queryFn: ({ signal }) => apiGet<Impact>("/impact", { season, decision }, undefined, signal),
    staleTime: 10 * MINUTE,
  });

export const useFarmer = (id: string) =>
  useQuery({
    queryKey: queryKeys.farmer(id),
    queryFn: ({ signal }) => apiGet<Farmer>(`/farmers/${id}`, {}, undefined, signal),
    staleTime: 10 * MINUTE,
  });

export const useFarmerAdvice = (id: string, issueDate: string | null) =>
  useQuery({
    queryKey: queryKeys.farmerAdvice(id, issueDate ?? ""),
    queryFn: ({ signal }) =>
      apiGet<FarmerAdvice>(`/farmers/${id}/advice`, { issue_date: issueDate }, undefined, signal),
    enabled: !!issueDate,
    staleTime: 0,
  });
