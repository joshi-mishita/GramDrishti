/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api to the local FastAPI stub, so the default
// VITE_API_BASE ("/api/v1") needs no CORS. See .env.example.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: false },
    },
  },
  preview: {
    port: 4173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: false },
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
