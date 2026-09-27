import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Advisory, AdvisoryList, FeedbackRequest } from "../../api/types";
import { firstSentence, publishedInOrder, shareText, whatsappUrl } from "./farmerData";
import { flushOutbox, queueFeedback, readOutbox } from "./outbox";
import { pickVoice, spokenText } from "./speech";

const EXAMPLES = resolve(__dirname, "../../../../contract/examples");
const load = <T>(f: string): T => JSON.parse(readFileSync(resolve(EXAMPLES, f), "utf8")) as T;

describe("firstSentence", () => {
  it("cuts English at the first full stop", () => {
    expect(firstSentence("Rain or wind would waste the spray. Chance of rain is 82%.")).toBe(
      "Rain or wind would waste the spray.",
    );
  });
  it("cuts Hindi and Punjabi at the danda", () => {
    expect(firstSentence("बारिश से छिड़काव बेकार हो जाएगा। 10 सितंबर को 82%।")).toBe(
      "बारिश से छिड़काव बेकार हो जाएगा।",
    );
    expect(firstSentence("ਮੀਂਹ ਨਾਲ ਛਿੜਕਾਅ ਬੇਕਾਰ ਹੋ ਜਾਵੇਗਾ। ਹਵਾ 4 ਕਿ.ਮੀ.")).toBe(
      "ਮੀਂਹ ਨਾਲ ਛਿੜਕਾਅ ਬੇਕਾਰ ਹੋ ਜਾਵੇਗਾ।",
    );
  });
  it("keeps decimals and single sentences whole", () => {
    expect(firstSentence("Up to 32.7 C on Wednesday")).toBe("Up to 32.7 C on Wednesday");
  });
});

describe("publishedInOrder", () => {
  it("keeps approved and edited only, most urgent first", () => {
    const list = load<AdvisoryList>("advisories.json"); // all drafts
    expect(publishedInOrder(list.items)).toEqual([]);
    const statuses: Advisory["status"][] = ["approved", "edited", "rejected", "approved"];
    const levels: Advisory["priority"][] = ["low", "severe", "severe", "moderate"];
    const items: Advisory[] = list.items.slice(0, 4).map((a, i) => ({
      ...a,
      status: statuses[i] ?? "draft",
      priority: levels[i] ?? "low",
    }));
    expect(publishedInOrder(items).map((a) => [a.status, a.priority])).toEqual([
      ["edited", "severe"],
      ["approved", "moderate"],
      ["approved", "low"],
    ]);
  });
});

describe("share", () => {
  it("builds a wa.me link without a phone number, with the mock notice", () => {
    const text = shareText({
      action: "Do not spray on 10 September.",
      reason: "Rain would wash it off.",
      source: "GramDrishti, Synthetic Panchayat MP0307, Mon 9 Sep 2024",
      notice: "Synthetic demo data. Not real weather.",
    });
    expect(text.split("\n")).toHaveLength(4);
    const url = whatsappUrl(text);
    expect(url.startsWith("https://wa.me/?text=")).toBe(true);
    expect(decodeURIComponent(url.slice("https://wa.me/?text=".length))).toBe(text);
  });
  it("leaves the notice out for real data", () => {
    expect(shareText({ action: "a", reason: "b", source: "c", notice: null })).toBe("a\nb\n- c");
  });
});

const voice = (lang: string, name = lang) => ({ lang, name }) as SpeechSynthesisVoice;

describe("pickVoice", () => {
  const voices = [voice("en-US"), voice("en-IN", "Rishi"), voice("hi_IN", "Lekha")];
  it("prefers the Indian tag and accepts an underscore", () => {
    expect(pickVoice(voices, "en")?.name).toBe("Rishi");
    expect(pickVoice(voices, "hi")?.name).toBe("Lekha");
  });
  it("falls back to another voice of the same language only", () => {
    expect(pickVoice([voice("en-GB")], "en")?.lang).toBe("en-GB");
    expect(pickVoice(voices, "pa")).toBeNull();
  });
});

describe("spokenText", () => {
  const a = load<AdvisoryList>("advisories.json").items[0] as Advisory;
  it("reads action, reason and fallback in one language", () => {
    const s = spokenText(a, "hi");
    expect(s.lang).toBe("hi");
    expect(s.text).toContain(a.action.hi ?? "");
    expect(s.text).toContain(a.reason.hi ?? "");
  });
  it("uses English for every part when the action has no translation", () => {
    const s = spokenText({ ...a, action: { ...a.action, pa: null } }, "pa");
    expect(s.lang).toBe("en");
    expect(s.text).toContain(a.reason.en);
  });
});

describe("feedback outbox", () => {
  const body: FeedbackRequest = {
    panchayat_id: "MP0307",
    date: "2024-09-09",
    reported_rain: true,
    intensity: "light",
    channel: "app",
  };
  // An in-memory storage: Node's own localStorage stub can shadow jsdom's in tests.
  beforeEach(() => {
    const data = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => data.get(k) ?? null,
      setItem: (k: string, v: string) => void data.set(k, v),
      removeItem: (k: string) => void data.delete(k),
    });
    return () => vi.unstubAllGlobals();
  });

  it("keeps network failures and drops refused answers", async () => {
    queueFeedback(body);
    queueFeedback({ ...body, intensity: "heavy" });
    const network = new Error("offline");
    const sent = await flushOutbox(
      async (b) => {
        if (b.intensity === "light") throw network;
        throw new Error("400");
      },
      (e) => e === network,
    );
    expect(sent).toBe(0);
    expect(readOutbox()).toEqual([body]);
  });

  it("empties once everything is sent", async () => {
    queueFeedback(body);
    const send = vi.fn(async () => ({}));
    expect(await flushOutbox(send, () => true)).toBe(1);
    expect(send).toHaveBeenCalledWith(body);
    expect(readOutbox()).toEqual([]);
  });
});
