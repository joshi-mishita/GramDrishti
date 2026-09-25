import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { FarmerNav } from "../components/FarmerNav";
import { useAppStore } from "../state/store";

/** Phone-width column with bottom navigation, also on a desktop screen. */
export function FarmerLayout() {
  const setRole = useAppStore((s) => s.setRole);
  useEffect(() => setRole("farmer"), [setRole]);
  return (
    <div className="farmer">
      <main id="main" tabIndex={-1} className="farmer-main">
        <Outlet />
      </main>
      <FarmerNav />
    </div>
  );
}
