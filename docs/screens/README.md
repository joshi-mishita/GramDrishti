# Screens

Screenshots for visual review. The PNG files are git-ignored; only this README is committed.

Generate them with:

```bash
cd frontend && npm run shots
```

This builds the app, serves it with `vite preview` on mock data (`VITE_REAL_ENDPOINTS` empty) and
saves `<screen>-<lang>-<desktop|wide|phone>.png` here at 1366x768, 1920x1080 and 360x740 (full
page): every screen in English, Hindi and Punjabi, the map variants in English (126 files).
The route and language list is in `frontend/e2e/shots.spec.ts`. `SHOTS_SET=before` (or `after`)
writes into `before/` (or `after/`) instead.

## Before and after S15 (committed)

`before/readme-*.png` and `after/readme-*.png` are the only committed screenshots: cropped pairs
from the S15 design pass, reduced to 128 colours, for the README and the design review
(`docs/design_review.md`). Everything else in these folders is git-ignored.

| File | Shows |
|---|---|
| `readme-map-panel-desktop.png` | Map with the detail panel, 1366x768: day strip, variable list, title, fan chart axis |
| `readme-map-hindi-desktop.png` | The same in Hindi |
| `readme-verification-top.png` | Verification intro and comparison table |
| `readme-verification-losses.png` | "Where the model does not help": job output before, readable list after |
| `readme-priority-phone.png` | Priority list at 360 px |
| `readme-farmer-desktop.png` | Farmer app on a desktop: ribbon inside the phone column |
| `readme-farmer-today-hindi-phone.png` | Farmer Today in Hindi at 360 px |
| `readme-impact-punjabi-desktop.png` | Impact in Punjabi |

If Playwright cannot download its Chromium (for example behind a TLS-intercepting proxy), use the
installed Google Chrome:

```bash
cd frontend && SHOTS_BROWSER_CHANNEL=chrome npm run shots
```

`npm run e2e` also writes `s9-<screen>-<lang>-<desktop|phone>.png` (priority, review, risk layer) and
`s9-priority-print.png` from a real API it starts itself (see `frontend/playwright.e2e.config.ts`).
