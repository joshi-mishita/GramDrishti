import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { apiPost } from "../api/client";
import { isApiError } from "../api/errors";
import { FarmerNav } from "../components/FarmerNav";
import { LastUpdated } from "../components/LastUpdated";
import { DemoControls } from "../features/farmer/DemoControls";
import { flushOutbox } from "../features/farmer/outbox";
import { useOnline } from "../lib/network";
import { useAppStore } from "../state/store";

/** Phone-width column with bottom navigation, also on a desktop screen. */
export function FarmerLayout() {
  const setRole = useAppStore((s) => s.setRole);
  const online = useOnline();
  useEffect(() => setRole("farmer"), [setRole]);

  // Feedback given offline is sent once the phone is back online.
  useEffect(() => {
    if (!online) return;
    void flushOutbox(
      (body) => apiPost("/feedback", body),
      (e) => isApiError(e) && e.code === "network_error",
    );
  }, [online]);

  return (
    <div className="farmer">
      <main id="main" tabIndex={-1} className="farmer-main">
        <LastUpdated />
        <Outlet />
        <DemoControls />
      </main>
      <FarmerNav />
    </div>
  );
}
