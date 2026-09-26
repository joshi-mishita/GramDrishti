import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAppStore } from "./store";
import { readUrlState, writeUrlState } from "./urlState";

/**
 * Two-way mirror between the store and the URL for issueDate, variable and selectedPid.
 * URL -> store when the location changes (links, back button); store -> URL with
 * replace, so changing a control does not flood the history.
 */
export function useUrlSync(): void {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const fromUrl = readUrlState(location.search);
    const s = useAppStore.getState();
    if (fromUrl.issueDate && fromUrl.issueDate !== s.issueDate) s.setIssueDate(fromUrl.issueDate);
    if (fromUrl.variable && fromUrl.variable !== s.variable) s.setVariable(fromUrl.variable);
    if (fromUrl.selectedPid !== s.selectedPid) s.setSelectedPid(fromUrl.selectedPid);
  }, [location.search]);

  const issueDate = useAppStore((s) => s.issueDate);
  const variable = useAppStore((s) => s.variable);
  const selectedPid = useAppStore((s) => s.selectedPid);

  useEffect(() => {
    // Read the live store, not this render's values: on first mount the effect above has
    // just copied the URL into the store, and the render values are still the defaults.
    const s = useAppStore.getState();
    const next = writeUrlState(location.search, s);
    if (next !== location.search) {
      navigate({ pathname: location.pathname, search: next }, { replace: true });
    }
    // location is read, not watched: this effect reacts to store changes only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issueDate, variable, selectedPid]);
}
