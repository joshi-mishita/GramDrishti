# Screens

Screenshots for visual review. The PNG files are git-ignored; only this README is committed.

Generate them with:

```bash
cd frontend && npm run shots
```

This builds the app, serves it with `vite preview` on mock data (`VITE_REAL_ENDPOINTS` empty) and
saves `<screen>-<lang>-<desktop|phone>.png` here at 1366x768 and 360x740 (full page).
The route and language list is in `frontend/e2e/shots.spec.ts`.

If Playwright cannot download its Chromium (for example behind a TLS-intercepting proxy), use the
installed Google Chrome:

```bash
cd frontend && SHOTS_BROWSER_CHANNEL=chrome npm run shots
```
