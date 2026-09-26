# Font licences

The frontend self-hosts three font families through Fontsource npm packages. Vite bundles the
font files into `frontend/dist/assets/`, so the app needs no font CDN and works offline.

| Family | npm package | Weights and subset used | Licence | Copy |
|---|---|---|---|---|
| Source Sans 3 | `@fontsource/source-sans-3` | 400, 500, 700; latin | SIL Open Font License 1.1 | `source-sans-3-OFL.txt` |
| Noto Sans Devanagari | `@fontsource/noto-sans-devanagari` | 400, 500, 700; devanagari | SIL Open Font License 1.1 | `noto-sans-devanagari-OFL.txt` |
| Noto Sans Gurmukhi | `@fontsource/noto-sans-gurmukhi` | 400, 500, 700; gurmukhi | SIL Open Font License 1.1 | `noto-sans-gurmukhi-OFL.txt` |

The `.txt` files are copied unchanged from each package's `LICENSE` (package version 5.3.0).
OFL 1.1 allows bundling and redistribution with the app; the fonts may not be sold on their own.
Every `@font-face` uses `font-display: swap` (Fontsource default, checked in the build output).
