/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// The dev server proxies /api to the local FastAPI app, so the default
// VITE_API_BASE ("/api/v1") needs no CORS. See .env.example. API_PROXY_TARGET points the
// proxy elsewhere (the Playwright flow runs its own API on another port).
const apiTarget = process.env.API_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [
    react(),
    // PWA (Frontend Guide 10.2): manifest plus the service worker in src/sw.ts. The worker
    // is built for `build` and `preview` only; the dev server runs without it.
    VitePWA({
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      registerType: "autoUpdate",
      injectRegister: false,
      manifest: {
        name: "GramDrishti",
        short_name: "GramDrishti",
        description: "Village weather forecast and crop advice. Prototype on synthetic data.",
        lang: "en",
        start_url: "/farmer",
        scope: "/",
        display: "standalone",
        orientation: "portrait",
        theme_color: "#24594A",
        background_color: "#ffffff",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          {
            src: "/icons/icon-maskable-512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      injectManifest: {
        // The shell only. Demo files and the snapshot are cached as they are used (sw.ts):
        // the snapshot alone is tens of thousands of files.
        globPatterns: ["**/*.{js,css,html,svg,png,woff2}"],
        globIgnores: ["mock/**", "snapshot/**"],
        // MapLibre's chunk is over the 2 MB default.
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
      },
      devOptions: { enabled: false },
    }),
  ],
  // MapLibre 6 loads its worker relative to its own module; pre-bundling moves the module
  // away from the worker file. See src/features/map/MapView.tsx.
  optimizeDeps: { exclude: ["maplibre-gl"] },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: false },
    },
  },
  preview: {
    port: 4173,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
