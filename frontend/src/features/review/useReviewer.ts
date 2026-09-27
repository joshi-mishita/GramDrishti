import { useState } from "react";

const KEY = "gramdrishti.reviewer";
/** Name written into the audit trail. There is no login in the prototype. */
export const DEFAULT_REVIEWER = "Demo officer";

function read(): string {
  try {
    return localStorage.getItem(KEY) ?? DEFAULT_REVIEWER;
  } catch {
    return DEFAULT_REVIEWER;
  }
}

/** The reviewer name, remembered in this browser only (storage may be blocked). */
export function useReviewer(): [string, (name: string) => void] {
  const [name, setName] = useState(read);
  const update = (next: string) => {
    setName(next);
    try {
      localStorage.setItem(KEY, next);
    } catch {
      // Storage blocked: the name lasts for this page only.
    }
  };
  return [name, update];
}
