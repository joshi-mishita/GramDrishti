# GramDrishti frontend

Vite + React + TypeScript (strict). Officer console and farmer app on the API contract in
`../contract/`. Read `../CLAUDE.md` and `../docs/GramDrishti_Frontend_Guide.pdf` first.

## Setup

Node 22 (`.nvmrc`). Then:

```bash
npm install
npm run dev          # http://localhost:5173, copies contract/examples to public/mock first
```

## Scripts

| Script                | What it does                                                          |
| --------------------- | --------------------------------------------------------------------- |
| `npm run dev`         | Dev server. `/api` is proxied to `http://localhost:8000`              |
| `npm run build`       | Type check and production build into `dist/`                          |
| `npm test`            | Vitest, once (`npm run test:watch` to watch)                          |
| `npm run lint`        | ESLint and Prettier check (`npm run format` to fix)                   |
| `npm run gen:types`   | `src/api/schema.d.ts` from `../contract/openapi.json`                 |
| `npm run check:types` | Regenerates types and fails if the committed file is stale            |
| `npm run sync:mock`   | Copies `../contract/examples/` into `public/mock/` (git-ignored)      |
| `npm run shots`       | Screenshots of listed routes into `../docs/screens/` (see its README) |

## Data sources

Set in `.env.local` (see `.env.example`):

- `VITE_REAL_ENDPOINTS`: comma-separated endpoint groups served by the API, for example
  `meta,geo,forecast`. Everything else reads `public/mock/`.
- `VITE_SNAPSHOT=1`: read only `public/snapshot/`, never call a server.
- `VITE_API_BASE`: default `/api/v1` through the dev proxy.

Mock and snapshot requests are matched against `index.json` by path and sorted query. A request
without an example file shows "No demo file ... Demo files exist for <dates>" instead of another
date's data. Most examples are for issue date 2024-09-09.

## Layout

```
src/api/        client.ts (mock switch), hooks.ts (TanStack Query), errors.ts, types.ts, schema.d.ts
src/components/ shell and shared UI
src/layouts/    AppShell, OfficerLayout, FarmerLayout
src/pages/      one file per route (lazy-loaded)
src/state/      zustand store and URL mirror (date, var, pid)
src/i18n/       en.json, hi.json, pa.json (hi and pa need native review)
src/styles/     tokens.css, base.css, shell.css, components.css, pages.css, print.css
e2e/            Playwright screenshot pass
```
