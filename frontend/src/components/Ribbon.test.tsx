import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "../test/render";
import { Ribbon } from "./Ribbon";

describe("Ribbon", () => {
  it("shows the guide's wording when data is mock", () => {
    renderWithProviders(<Ribbon dataMode="mock" />);
    expect(screen.getByRole("note")).toHaveTextContent("Synthetic demo data. Not real weather.");
  });

  it("is absent for real data and while data_mode is unknown", () => {
    renderWithProviders(
      <>
        <Ribbon dataMode="real" />
        <Ribbon dataMode={undefined} />
      </>,
    );
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });
});
