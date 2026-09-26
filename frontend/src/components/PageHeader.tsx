import type { ReactNode } from "react";

/** Page title with an optional one-line context. Left-aligned, sentence case. */
export function PageHeader({ title, subtitle }: { title: string; subtitle?: ReactNode }) {
  return (
    <header className="page-header">
      <h1>{title}</h1>
      {subtitle ? <p className="muted">{subtitle}</p> : null}
    </header>
  );
}
