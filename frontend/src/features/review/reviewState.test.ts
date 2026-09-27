import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { Advisory, AdvisoryList } from "../../api/types";
import {
  blockedReason,
  buildEdited,
  changedCells,
  droppedTranslations,
  filterQueue,
  isDirty,
  missingEnglish,
  moveIndex,
  readQueue,
  reviewRequest,
  setText,
  shortcutKind,
  sortQueue,
  textsOf,
  writeQueue,
} from "./reviewState";

const EXAMPLES = resolve(__dirname, "../../../../contract/examples");
const detail = JSON.parse(
  readFileSync(resolve(EXAMPLES, "advisory_detail.json"), "utf8"),
) as Advisory;
const list = JSON.parse(readFileSync(resolve(EXAMPLES, "advisories.json"), "utf8")) as AdvisoryList;

describe("editable texts", () => {
  const original = textsOf(detail);

  it("starts from the advisory, with empty strings for missing translations", () => {
    expect(original.action.en).toBe(detail.action.en);
    const partial = textsOf({ ...detail, fallback: { en: "x", hi: null, pa: null } });
    expect(partial.fallback).toEqual({ en: "x", hi: "", pa: "" });
  });

  it("is clean until a cell changes; spaces at the ends do not count", () => {
    expect(isDirty(original, original)).toBe(false);
    const spaced = setText(original, "reason", "en", `  ${original.reason.en} `);
    expect(isDirty(original, spaced)).toBe(false);
    const changed = setText(original, "action", "hi", "नया पाठ");
    expect(changedCells(original, changed)).toEqual([{ field: "action", lang: "hi" }]);
    // setText does not touch the original.
    expect(original.action.hi).toBe(detail.action.hi);
  });

  it("requires English in every field", () => {
    expect(missingEnglish(original)).toEqual([]);
    expect(missingEnglish(setText(original, "fallback", "en", "   "))).toEqual(["fallback"]);
  });
});

describe("edit request", () => {
  const original = textsOf(detail);

  it("sends nothing when nothing changed", () => {
    expect(buildEdited(original, original)).toBeNull();
    expect(() => reviewRequest("edit", { reviewer: "A", original, current: original })).toThrow();
  });

  it("drops translations of a field whose English changed, and warns about them first", () => {
    const current = setText(original, "action", "en", "No spraying on 10 September.");
    expect(droppedTranslations(original, current)).toEqual([
      { field: "action", lang: "hi" },
      { field: "action", lang: "pa" },
    ]);
    expect(buildEdited(original, current)).toEqual({
      action: { en: "No spraying on 10 September.", hi: null, pa: null },
    });
  });

  it("keeps a translation that was edited along with the English", () => {
    let current = setText(original, "action", "en", "No spraying on 10 September.");
    current = setText(current, "action", "hi", "10 सितंबर को छिड़काव न करें।");
    expect(droppedTranslations(original, current)).toEqual([{ field: "action", lang: "pa" }]);
    expect(buildEdited(original, current)?.action).toEqual({
      en: "No spraying on 10 September.",
      hi: "10 सितंबर को छिड़काव न करें।",
      pa: null,
    });
  });

  it("keeps English and the other translation when only one translation changed", () => {
    const current = setText(original, "reason", "pa", "  ਨਵਾਂ ਕਾਰਨ ");
    expect(droppedTranslations(original, current)).toEqual([]);
    expect(buildEdited(original, current)).toEqual({
      reason: { en: detail.reason.en, hi: detail.reason.hi, pa: "ਨਵਾਂ ਕਾਰਨ" },
    });
  });

  it("builds the three request bodies with the reviewer and note", () => {
    const current = setText(original, "fallback", "en", "Spray early if it is calm.");
    expect(
      reviewRequest("approve", { reviewer: " Officer A ", original, current: original }),
    ).toEqual({ action: "approve", reviewer: "Officer A", note: "" });
    expect(
      reviewRequest("reject", { reviewer: "Officer A", note: " Wrong crop ", original, current }),
    ).toEqual({ action: "reject", reviewer: "Officer A", note: "Wrong crop" });
    const edit = reviewRequest("edit", { reviewer: "Officer A", original, current });
    expect(edit.action).toBe("edit");
    expect(Object.keys(edit.edited ?? {})).toEqual(["fallback"]);
  });
});

describe("button rules", () => {
  const ok = {
    dirty: false,
    missing: [],
    reviewer: "Officer A",
    note: "",
    writable: true,
    status: "draft" as const,
  };

  it("allows Approve on a clean draft and Save edit and approve only with edits", () => {
    expect(blockedReason("approve", ok)).toBeNull();
    expect(blockedReason("edit", ok)).toBe("noEdits");
    expect(blockedReason("approve", { ...ok, dirty: true })).toBe("hasEdits");
    expect(blockedReason("edit", { ...ok, dirty: true })).toBeNull();
    expect(blockedReason("edit", { ...ok, dirty: true, missing: ["action"] })).toBe(
      "missingEnglish",
    );
  });

  it("needs a reason to reject, a reviewer name, and the API", () => {
    expect(blockedReason("reject", ok)).toBe("noReason");
    expect(blockedReason("reject", { ...ok, note: "Wrong stage" })).toBeNull();
    expect(blockedReason("approve", { ...ok, reviewer: " " })).toBe("noReviewer");
    expect(blockedReason("approve", { ...ok, writable: false })).toBe("readOnly");
  });

  it("does not approve an approved text twice, or reject a rejected one twice", () => {
    expect(blockedReason("approve", { ...ok, status: "approved" })).toBe("alreadyApproved");
    expect(blockedReason("approve", { ...ok, status: "edited" })).toBe("alreadyApproved");
    // New edits to an approved advisory can still be saved; a rejected one can be approved.
    expect(blockedReason("edit", { ...ok, status: "approved", dirty: true })).toBeNull();
    expect(blockedReason("approve", { ...ok, status: "rejected" })).toBeNull();
    expect(blockedReason("reject", { ...ok, status: "approved", note: "Wrong crop" })).toBeNull();
    expect(blockedReason("reject", { ...ok, status: "rejected", note: "x" })).toBe(
      "alreadyRejected",
    );
  });

  it("makes Ctrl+Enter approve, saving edits first when there are any", () => {
    expect(shortcutKind(false)).toBe("approve");
    expect(shortcutKind(true)).toBe("edit");
  });
});

describe("queue", () => {
  it("orders by priority, then Panchayat, crop and category", () => {
    const q = sortQueue(list.items);
    expect(q).toHaveLength(list.items.length);
    const rank = { severe: 3, high: 2, moderate: 1, low: 0 } as const;
    for (let i = 1; i < q.length; i++) {
      expect(rank[(q[i - 1] as Advisory).priority]).toBeGreaterThanOrEqual(
        rank[(q[i] as Advisory).priority],
      );
    }
  });

  it("filters by block and crop", () => {
    const mb03 = filterQueue(list.items, { block: "MB03", crop: null });
    expect(mb03.length).toBe(45);
    expect(mb03.every((a) => a.block_id === "MB03")).toBe(true);
    const cotton = filterQueue(list.items, { block: "MB03", crop: "cotton" });
    expect(cotton.every((a) => a.crop === "cotton" && a.block_id === "MB03")).toBe(true);
    expect(filterQueue(list.items, { block: null, crop: null })).toHaveLength(198);
  });

  it("moves with arrow keys, Home and End, and stops at the ends", () => {
    expect(moveIndex(0, "ArrowDown", 3)).toBe(1);
    expect(moveIndex(2, "ArrowDown", 3)).toBe(2);
    expect(moveIndex(0, "ArrowUp", 3)).toBe(0);
    expect(moveIndex(-1, "ArrowDown", 3)).toBe(0);
    expect(moveIndex(-1, "ArrowUp", 3)).toBe(2);
    expect(moveIndex(1, "Home", 3)).toBe(0);
    expect(moveIndex(1, "End", 3)).toBe(2);
    expect(moveIndex(1, "a", 3)).toBeNull();
    expect(moveIndex(0, "ArrowDown", 0)).toBeNull();
  });

  it("keeps filters and the open advisory in the URL", () => {
    expect(readQueue("")).toEqual({ status: "draft", block: null, crop: null, adv: null });
    expect(
      readQueue("?status=all&block=MB03&crop=cotton&adv=ADV-2024-09-09-MP0301-cotton-spray"),
    ).toEqual({
      status: "all",
      block: "MB03",
      crop: "cotton",
      adv: "ADV-2024-09-09-MP0301-cotton-spray",
    });
    expect(readQueue("?status=done&adv=<x>")).toMatchObject({ status: "draft", adv: null });
    const q = new URLSearchParams(
      writeQueue("?date=2024-09-09&status=approved", { status: "draft", adv: "ADV-1" }),
    );
    expect(q.get("date")).toBe("2024-09-09");
    expect(q.has("status")).toBe(false);
    expect(q.get("adv")).toBe("ADV-1");
  });
});
