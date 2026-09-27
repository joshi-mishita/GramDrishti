import { useId, type ReactNode } from "react";

export interface SegmentOption<T extends string> {
  value: T;
  label: ReactNode;
  /** BCP 47 tag when the label is in another language than the UI. */
  lang?: string;
  /** Secondary text under the label (list variant only). */
  hint?: ReactNode;
}

interface Props<T extends string> {
  legend: string;
  /** Show the legend as a visible label above the options. */
  showLegend?: boolean;
  name: string;
  value: T;
  options: readonly SegmentOption<T>[];
  onChange: (value: T) => void;
  /** "bar": inline segments on the top bar. "list": stacked rows. "wrap": wrapping pills. */
  variant?: "bar" | "list" | "wrap";
  /** Disables every option (native fieldset disabled). */
  disabled?: boolean;
  /** Short text under the options, read with the group (for example why it is disabled). */
  note?: string;
}

/**
 * A group of native radio buttons styled as segments. Native radios give arrow-key
 * movement and screen-reader semantics for free.
 */
export function SegmentedControl<T extends string>({
  legend,
  showLegend = false,
  name,
  value,
  options,
  onChange,
  variant = "bar",
  disabled = false,
  note,
}: Props<T>) {
  const noteId = useId();
  return (
    <fieldset
      className={`seg seg-${variant}`}
      disabled={disabled}
      aria-describedby={note ? noteId : undefined}
    >
      <legend className={showLegend ? "seg-legend" : "visually-hidden"}>{legend}</legend>
      <div className="seg-options">
        {options.map((o) => (
          <label key={o.value} className="seg-opt">
            <input
              type="radio"
              name={name}
              value={o.value}
              checked={o.value === value}
              onChange={() => onChange(o.value)}
            />
            <span className="seg-face">
              <span lang={o.lang}>{o.label}</span>
              {o.hint ? <span className="seg-hint">{o.hint}</span> : null}
            </span>
          </label>
        ))}
      </div>
      {note ? (
        <p id={noteId} className="muted small">
          {note}
        </p>
      ) : null}
    </fieldset>
  );
}
