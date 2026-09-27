/// <reference lib="webworker" />
/**
 * Service worker (Frontend Guide 10.2), built by vite-plugin-pwa (injectManifest).
 *
 * - The app shell (HTML, JS, CSS, fonts, icons) is precached, so the app opens offline.
 * - Every same-origin GET for data (/api/v1/..., demo files in /mock/, the offline
 *   snapshot in /snapshot/) is network first with a fallback to the last copy. Audio is
 *   not cached: the farmer app falls back to the phone's own speech when it is missing.
 * - A stored copy carries X-GD-Fetched-At; a copy used instead of the network carries
 *   X-GD-From-Cache: 1. The app reads both to show the offline pill's "Last updated" line.
 * - Only 200 responses are stored; POST (reviews, feedback) never touches the cache.
 */
import { clientsClaim, type WorkboxPlugin } from "workbox-core";
import { ExpirationPlugin } from "workbox-expiration";
import {
  cleanupOutdatedCaches,
  createHandlerBoundToURL,
  precacheAndRoute,
} from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";
import { NetworkFirst } from "workbox-strategies";

declare let self: ServiceWorkerGlobalScope;

const FROM_CACHE = "X-GD-From-Cache";
const FETCHED_AT = "X-GD-Fetched-At";
const DATA_PATHS = /^\/(api\/v1\/(?!audio\/)|mock\/|snapshot\/)/;

// registerType "autoUpdate": a new version takes over at once.
void self.skipWaiting();
clientsClaim();

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

// Reloading any route offline serves the precached index.html.
registerRoute(
  new NavigationRoute(createHandlerBoundToURL("/index.html"), {
    denylist: [/^\/api\//, /^\/mock\//, /^\/snapshot\//],
  }),
);

async function withHeader(response: Response, name: string, value: string): Promise<Response> {
  const headers = new Headers(response.headers);
  headers.set(name, value);
  return new Response(await response.blob(), {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

const stampPlugin: WorkboxPlugin = {
  cacheWillUpdate: async ({ response }) =>
    response.status === 200 ? withHeader(response, FETCHED_AT, new Date().toISOString()) : null,
  cachedResponseWillBeUsed: async ({ cachedResponse }) =>
    cachedResponse ? withHeader(cachedResponse, FROM_CACHE, "1") : null,
};

registerRoute(
  ({ url, request }) =>
    request.method === "GET" &&
    url.origin === self.location.origin &&
    DATA_PATHS.test(url.pathname),
  new NetworkFirst({
    cacheName: "gd-data",
    // A phone on a weak signal gets the last copy after 5 s instead of a long wait.
    networkTimeoutSeconds: 5,
    plugins: [stampPlugin, new ExpirationPlugin({ maxEntries: 600, maxAgeSeconds: 30 * 86_400 })],
  }),
);
