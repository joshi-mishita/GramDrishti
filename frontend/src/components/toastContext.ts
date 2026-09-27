import { createContext, useContext } from "react";

export type ToastTone = "success" | "error";
export type Show = (message: string, tone?: ToastTone) => void;

export const ToastContext = createContext<Show | null>(null);

/** Returns show(message, tone). Outside a ToastProvider it does nothing. */
export function useToast(): Show {
  return useContext(ToastContext) ?? noop;
}

function noop(): void {}
