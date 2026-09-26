import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useQuery } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/errors";
import { renderWithProviders } from "../test/render";
import { QueryBoundary } from "./QueryBoundary";

function Harness({ fn, items }: { fn: () => Promise<string[]>; items?: boolean }) {
  const q = useQuery({ queryKey: ["t", fn], queryFn: fn });
  return (
    <QueryBoundary
      query={q}
      what="the test list"
      isEmpty={(d) => d.length === 0}
      empty={<p>Nothing here for this date.</p>}
    >
      {(d) => <p>{items ? d.join(", ") : `${d.length} items`}</p>}
    </QueryBoundary>
  );
}

describe("QueryBoundary", () => {
  it("shows a loading state first, then the data", async () => {
    renderWithProviders(<Harness fn={async () => ["MP0103", "MP0412"]} items />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading the test list");
    expect(await screen.findByText("MP0103, MP0412")).toBeInTheDocument();
  });

  it("shows the empty state for an empty result", async () => {
    renderWithProviders(<Harness fn={async () => []} />);
    expect(await screen.findByText("Nothing here for this date.")).toBeInTheDocument();
  });

  it("shows an actionable error and retries", async () => {
    const fn = vi
      .fn<() => Promise<string[]>>()
      .mockRejectedValueOnce(
        new ApiError({ status: 500, code: "internal_error", message: "boom", url: "/x" }),
      )
      .mockResolvedValueOnce(["MP0101"]);
    renderWithProviders(<Harness fn={fn} />);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Could not load the test list. Check the server is running, then try again.",
    );
    expect(alert).toHaveTextContent("500 internal_error: boom");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("1 items")).toBeInTheDocument();
  });

  it("explains a missing demo file as an empty state, naming the dates that exist", async () => {
    const fn = async (): Promise<string[]> => {
      throw new ApiError({
        status: 404,
        code: "not_in_mock",
        message: "",
        url: "/mock/x",
        mockDates: ["2024-09-09"],
      });
    };
    renderWithProviders(<Harness fn={fn} />);
    expect(await screen.findByText(/No demo file for the test list/)).toBeInTheDocument();
    expect(screen.getByText(/Mon 9 Sep 2024/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
