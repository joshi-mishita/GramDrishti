import { useFarmer, useForecastPanchayat } from "../../api/hooks";
import { useAppStore } from "../../state/store";

/**
 * The demo farmer, their Panchayat and its forecast for the issue date. Shared by the
 * farmer top bar and screens; TanStack Query fetches each once.
 */
export function useFarmerContext() {
  const farmerId = useAppStore((s) => s.farmerId);
  const issueDate = useAppStore((s) => s.issueDate);
  const farmer = useFarmer(farmerId);
  const pid = farmer.data?.panchayat_id ?? null;
  const forecast = useForecastPanchayat(pid, issueDate);
  const village = forecast.data?.name ?? pid ?? "";
  return { farmerId, issueDate, farmer, pid, forecast, village };
}
