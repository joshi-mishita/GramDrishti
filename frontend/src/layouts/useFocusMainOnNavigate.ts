import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

/**
 * After moving to another screen (a new path, not a changed query such as the day), put
 * keyboard focus on <main id="main">. Otherwise focus stays on the navigation link, which in
 * the farmer app is the last thing on the page, and the next Tab leaves the page. Screen
 * readers also start reading the new screen. The first load is left alone.
 */
export function useFocusMainOnNavigate() {
  const { pathname } = useLocation();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    document.getElementById("main")?.focus();
  }, [pathname]);
}
