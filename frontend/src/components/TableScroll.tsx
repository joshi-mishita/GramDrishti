import type { ReactNode } from "react";

/**
 * Scrolling box around a wide or long table. It is focusable and named after the table, so a
 * keyboard user can tab to it and scroll with the arrow keys (WCAG 2.1.1, axe
 * scrollable-region-focusable).
 */
export function TableScroll({
  label,
  className,
  children,
}: {
  label: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={className ? `table-wrap ${className}` : "table-wrap"}
      role="region"
      aria-label={label}
      tabIndex={0}
    >
      {children}
    </div>
  );
}
