import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Self-hosted fonts, bundled by Vite (font-display: swap). One subset per script keeps
// the download small; the browser fetches a subset only when its characters appear.
import "@fontsource/source-sans-3/latin-400.css";
import "@fontsource/source-sans-3/latin-500.css";
import "@fontsource/source-sans-3/latin-700.css";
import "@fontsource/noto-sans-devanagari/devanagari-400.css";
import "@fontsource/noto-sans-devanagari/devanagari-500.css";
import "@fontsource/noto-sans-devanagari/devanagari-700.css";
import "@fontsource/noto-sans-gurmukhi/gurmukhi-400.css";
import "@fontsource/noto-sans-gurmukhi/gurmukhi-500.css";
import "@fontsource/noto-sans-gurmukhi/gurmukhi-700.css";

import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/shell.css";
import "./styles/components.css";
import "./styles/pages.css";
import "./styles/print.css";

import { AppRoutes } from "./App";
import { initI18n } from "./i18n";
import { useAppStore } from "./state/store";

initI18n(useAppStore.getState().lang);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => count < 1 && !("status" in error && error.status === 404),
      refetchOnWindowFocus: false,
    },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("#root missing from index.html");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
