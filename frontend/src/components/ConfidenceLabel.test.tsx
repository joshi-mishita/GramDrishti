import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "../test/render";
import { ConfidenceLabel } from "./ConfidenceLabel";

describe("ConfidenceLabel", () => {
  it.each([
    ["high", "Likely", /High confidence/],
    ["medium", "Possible", /Medium confidence/],
    ["low", "Uncertain", /Low confidence/],
  ] as const)("shows %s as %s with an explanation", (confidence, word, tip) => {
    renderWithProviders(<ConfidenceLabel confidence={confidence} />);
    const label = screen.getByText(word).parentElement as HTMLElement;
    expect(label).toHaveAttribute("tabindex", "0");
    expect(label).toHaveAccessibleDescription(tip);
    expect(screen.getByRole("tooltip")).toHaveTextContent(tip);
  });

  it("never shows a score", () => {
    renderWithProviders(<ConfidenceLabel confidence="high" />);
    expect(document.body.textContent).not.toMatch(/\d/);
  });
});
