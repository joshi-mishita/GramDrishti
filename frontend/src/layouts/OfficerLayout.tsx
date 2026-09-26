import { useEffect } from "react";
import { Outlet } from "react-router-dom";
import { SideNav } from "../components/SideNav";
import { useAppStore } from "../state/store";

export function OfficerLayout() {
  const setRole = useAppStore((s) => s.setRole);
  useEffect(() => setRole("officer"), [setRole]);
  return (
    <div className="officer">
      <SideNav />
      <main id="main" tabIndex={-1} className="officer-main">
        <Outlet />
      </main>
    </div>
  );
}
