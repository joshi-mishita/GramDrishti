import type { ReactNode } from "react";

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
}: Props<T>) {
  return (
    <fieldset className={`seg seg-${variant}`}>
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
    </fieldset>
  );
}
