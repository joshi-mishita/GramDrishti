import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithProviders } from "../test/render";
import { Ribbon } from "./Ribbon";

describe("Ribbon", () => {
  it("shows the guide's wording when data is mock", () => {
    renderWithProviders(<Ribbon dataMode="mock" />);
    expect(
      screen.getByRole("region", { name: "Synthetic demo data. Not real weather." }),
    ).toBeInTheDocument();
  });

  it("shows while data_mode is unknown (loading or API down)", () => {
    renderWithProviders(<Ribbon dataMode={undefined} />);
    expect(
      screen.getByRole("region", { name: "Synthetic demo data. Not real weather." }),
    ).toBeInTheDocument();
  });

  it("is absent once a response says the data is real", () => {
    renderWithProviders(<Ribbon dataMode="real" />);
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });
});
