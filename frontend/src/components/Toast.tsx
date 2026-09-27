import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { CircleAlert, CircleCheck, X } from "lucide-react";
import { useTranslation } from "react-i18next";

import { ToastContext, type Show, type ToastTone } from "./toastContext";

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

const SHOW_MS = 5000;

/**
 * Short confirmations after an action ("Approved"). One live region announces them to
 * screen readers; each toast closes itself after a few seconds or with its close button.
 * No entrance animation (Guide 2).
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [items, setItems] = useState<ToastItem[]>([]);
  const next = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const close = useCallback((id: number) => {
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
    setItems((xs) => xs.filter((x) => x.id !== id));
  }, []);

  const show = useCallback<Show>(
    (message, tone = "success") => {
      const id = next.current++;
      // Keep the newest three; older ones are already announced.
      setItems((xs) => [...xs.slice(-2), { id, message, tone }]);
      timers.current.set(
        id,
        setTimeout(() => close(id), SHOW_MS),
      );
    },
    [close],
  );

  useEffect(() => {
    const map = timers.current;
    return () => map.forEach(clearTimeout);
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className="toasts" aria-live="polite">
        {items.map((x) => {
          const Icon = x.tone === "success" ? CircleCheck : CircleAlert;
          return (
            <div key={x.id} className={`toast toast-${x.tone}`}>
              <Icon size={18} aria-hidden="true" />
              <span>{x.message}</span>
              <button
                type="button"
                className="btn-bare"
                onClick={() => close(x.id)}
                aria-label={t("toast.close")}
              >
                <X size={16} aria-hidden="true" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
