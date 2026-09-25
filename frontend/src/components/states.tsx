import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { CircleAlert, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";

/** Grey placeholder blocks while data loads. Static: no shimmer, no entrance motion. */
export function Skeleton({ lines = 3, label }: { lines?: number; label: string }) {
  return (
    <div className="skeleton" role="status" aria-busy="true">
      <span className="visually-hidden">{label}</span>
      {Array.from({ length: lines }, (_, i) => (
        <span key={i} className="skeleton-line" aria-hidden="true" />
      ))}
    </div>
  );
}

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}

/** A plain empty state: what is missing, why, and what to do next. */
export function EmptyState({ icon: Icon, title, children, action }: EmptyStateProps) {
  return (
    <div className="empty">
      {Icon ? <Icon className="empty-icon" size={20} aria-hidden="true" /> : null}
      <div className="empty-body">
        <h2 className="empty-title">{title}</h2>
        {children}
        {action ? <div className="empty-action">{action}</div> : null}
      </div>
    </div>
  );
}

interface ErrorStateProps {
  message: string;
  detail?: string;
  onRetry?: () => void;
  retrying?: boolean;
}

/** An error the user can act on, with a retry button. Announced to screen readers. */
export function ErrorState({ message, detail, onRetry, retrying }: ErrorStateProps) {
  const { t } = useTranslation();
  return (
    <div className="error" role="alert">
      <CircleAlert className="error-icon" size={20} aria-hidden="true" />
      <div className="empty-body">
        <p>{message}</p>
        {detail ? <p className="muted small">{detail}</p> : null}
        {onRetry ? (
          <div className="empty-action">
            <button type="button" className="btn" onClick={onRetry} disabled={retrying}>
              <RefreshCw size={16} aria-hidden="true" />
              {t("states.retry")}
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
