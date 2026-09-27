import { useEffect, useId, useRef, type KeyboardEvent } from "react";
import { useTranslation } from "react-i18next";
import type { Advisory } from "../../api/types";
import { RiskChip } from "../../components/RiskChip";
import { StatusChip } from "./StatusChip";
import { advisoryTitle, placeLabel } from "./labels";
import { moveIndex } from "./reviewState";

interface Props {
  items: readonly Advisory[];
  /** Advisory shown in the editor. */
  openId: string | null;
  /** Keyboard position in the list (may differ from the open advisory until Enter). */
  active: number;
  onActive: (index: number) => void;
  onOpen: (a: Advisory) => void;
  names: ReadonlyMap<string, string>;
  label: string;
}

/**
 * The review queue as a listbox (Guide 6.3): arrow keys, Home and End move through it,
 * Enter opens the advisory in the editor, a click does both.
 */
export function ReviewQueue({ items, openId, active, onActive, onOpen, names, label }: Props) {
  const { t } = useTranslation();
  const base = useId();
  const listRef = useRef<HTMLDivElement>(null);
  const optionId = (i: number) => `${base}-${i}`;
  const current = items[active];

  // Keep the keyboard position in view (jsdom has no scrollIntoView).
  useEffect(() => {
    const el = document.getElementById(optionId(active));
    el?.scrollIntoView?.({ block: "nearest" });
    // optionId only depends on base, which never changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" && !e.ctrlKey && !e.metaKey) {
      if (current) {
        e.preventDefault();
        onOpen(current);
      }
      return;
    }
    const next = moveIndex(active, e.key, items.length);
    if (next !== null) {
      e.preventDefault();
      onActive(next);
    }
  };

  return (
    <div
      ref={listRef}
      className="queue"
      role="listbox"
      tabIndex={0}
      aria-label={label}
      aria-activedescendant={current ? optionId(active) : undefined}
      onKeyDown={onKeyDown}
    >
      {items.map((a, i) => {
        const place = placeLabel(names.get(a.panchayat_id) ?? a.panchayat_id, a.panchayat_id);
        return (
          <div
            key={a.id}
            id={optionId(i)}
            role="option"
            aria-selected={a.id === openId}
            className={[
              "queue-item",
              i === active ? "is-active" : "",
              a.id === openId ? "is-open" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => {
              onActive(i);
              onOpen(a);
              listRef.current?.focus();
            }}
          >
            <span className="queue-main">
              <span className="queue-title">
                {place.name}
                {place.id ? <span className="muted"> {place.id}</span> : null}
              </span>
              <span className="queue-sub">{advisoryTitle(t, a).replace(": ", " · ")}</span>
            </span>
            <span className="queue-side">
              <RiskChip level={a.priority} />
              {a.status !== "draft" ? <StatusChip status={a.status} /> : null}
            </span>
          </div>
        );
      })}
    </div>
  );
}
