/**
 * Feedback answers given without a connection wait here (localStorage) and are sent when
 * the phone is back online. The API stores an identical report only once within 10
 * minutes (D096), so sending twice after a flaky connection does no harm.
 */
import type { FeedbackRequest } from "../../api/types";

export const OUTBOX_KEY = "gramdrishti.feedbackOutbox";

export function readOutbox(): FeedbackRequest[] {
  try {
    const raw = localStorage.getItem(OUTBOX_KEY);
    const list: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(list) ? (list as FeedbackRequest[]) : [];
  } catch {
    return [];
  }
}

function writeOutbox(list: FeedbackRequest[]): void {
  try {
    if (list.length) localStorage.setItem(OUTBOX_KEY, JSON.stringify(list));
    else localStorage.removeItem(OUTBOX_KEY);
  } catch {
    // Storage blocked: the answer is lost with the page, and the screen said so.
  }
}

/** Keeps an answer for later. Returns false when the phone cannot store it. */
export function queueFeedback(body: FeedbackRequest): boolean {
  writeOutbox([...readOutbox(), body]);
  return readOutbox().some((b) => JSON.stringify(b) === JSON.stringify(body));
}

/**
 * Sends every waiting answer in order. An answer that fails for lack of a network stays;
 * one the API refuses (400) is dropped, because sending it again cannot succeed.
 * Returns how many were sent.
 */
export async function flushOutbox(
  send: (body: FeedbackRequest) => Promise<unknown>,
  isNetworkError: (e: unknown) => boolean,
): Promise<number> {
  const waiting = readOutbox();
  const done: FeedbackRequest[] = [];
  let sent = 0;
  for (const body of waiting) {
    try {
      await send(body);
      sent += 1;
      done.push(body);
    } catch (e) {
      if (!isNetworkError(e)) done.push(body);
    }
  }
  // Re-read: an answer queued while this ran must not be lost.
  const left = readOutbox();
  for (const body of done) {
    const i = left.findIndex((b) => JSON.stringify(b) === JSON.stringify(body));
    if (i >= 0) left.splice(i, 1);
  }
  writeOutbox(left);
  return sent;
}
