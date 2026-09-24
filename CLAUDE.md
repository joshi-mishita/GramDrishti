# GramDrishti: standing instructions for Claude Code

Read this file and `docs/PROGRESS.md` at the start of every session. These rules apply to every session and override convenience.

## What this project is
SIH 2026 problem SIH26074: downscale block-level weather forecasts to Panchayat level for agro-meteorological advisory services.
GramDrishti turns a coarse block forecast into Panchayat forecasts with calibrated uncertainty, then into crop-stage advisories that an officer reviews before farmers receive them in English, Hindi and Punjabi. Its value is proven by comparing against the plain block forecast.

- Repo: https://github.com/joshi-mishita/GramDrishti.git
- Specs: `docs/GramDrishti_Backend_Guide.pdf`, `docs/GramDrishti_Frontend_Guide.pdf`. Appendix A in both is the API CONTRACT. Appendix B is the integration plan.
- Data: `data/` holds a SYNTHETIC mock dataset (see `data/README.md`). Regenerate with `python data/generate_mock_data.py`.

## Layout
```
contract/   openapi.json, examples/*.json, CHANGELOG.md      (shared, both people)
data/       mock data + generator
backend/    Python package `gramdrishti`, tests, artifacts/    (backend person)
frontend/   Vite React TypeScript app                          (frontend person)
docs/       guides, PROGRESS.md, DECISIONS.md, model card, demo script
scripts/    helper scripts
```

## Stack
Backend: Python 3.11+, FastAPI, Pydantic, pandas, NumPy, PyArrow, LightGBM, scikit-learn, SHAP, joblib, PyYAML, simpleeval, SQLite, pytest, httpx, ruff.
Frontend: React + TypeScript + Vite, React Router, TanStack Query, Zustand, MapLibre GL JS, Recharts, i18next, lucide-react, openapi-typescript, vite-plugin-pwa, Vitest, Playwright. Plain CSS with design tokens. No UI kit, no Tailwind.
Shared: Docker Compose, GitHub Actions.

## Commands (update this section whenever a command is created)
- Backend tests: `cd backend && pytest -q`
- Backend lint: `cd backend && ruff check .`
- Run API: `cd backend && uvicorn gramdrishti.api.main:app --reload --port 8000`
- Export contract: `cd backend && python -m gramdrishti.export_openapi`
- Frontend dev / build / test: `cd frontend && npm run dev | build | test`
- Frontend types from contract: `cd frontend && npm run gen:types`
- Screenshots for visual review: `cd frontend && npm run shots`

## Non-negotiable rules
1. **Everything current is synthetic.** Every API response carries `data_mode` ("mock" or "real"). The UI shows the ribbon "Synthetic demo data. Not real weather." whenever it is "mock".
2. **Never invent accuracy numbers.** Metrics shown anywhere come only from the verification job's output. Fixtures use clearly fake numbers with `data_mode: mock`. Report losses to the baseline as clearly as wins.
3. **Thresholds are placeholders** until an expert reviews them. Mark `thresholds_status: "placeholder"` in rules and advisory payloads. Leave `source` empty. Hindi and Punjabi text drafted by you is marked as needing native review.
4. **Contract first.** Do not change JSON shapes from Appendix A silently. Additive, optional fields are allowed with an entry in `contract/CHANGELOG.md` and a regenerated `contract/openapi.json`. Breaking changes need my approval.
5. **No leakage.** Never use `data/synthetic_oracle/` as a model feature (it is the answer key; it is used only as proxy training targets in mock mode and for evaluation). Split by time and by block, never randomly. Windows: TRAIN 2023-01-01..2024-04-30, CALIB 2024-05-01..2024-07-15, TEST 2024-07-16..2024-12-31. **TEST is opened only in the verification session, once per model version.** Development checks use TRAIN with leave-one-block-out, and CALIB halves.
6. **Block consistency is mandatory:** after reconciliation the block mean of Panchayat values equals the block forecast within 1e-6. A test enforces it.
7. **JSON hygiene:** no NaN or Infinity in API responses (use null). GeoJSON coordinates are [longitude, latitude]. Dates are ISO `YYYY-MM-DD`. Units fixed: rain mm, temperature C, RH %, wind km/h.
8. **Advisories come from YAML rules, never from an LLM.**
9. **Spray planning is day-level** (data is daily). Do not claim hour-level windows.
10. **Frontend design:** follow section 2 of the Frontend Guide. Palette tokens, Source Sans 3 + Noto Sans Devanagari/Gurmukhi (self-hosted), no gradients, no emoji, no purple/indigo, no all-caps eyebrow labels, no row of identical KPI cards, no entrance animations, sentence case, real data and units on every screen, loading/empty/error states everywhere.
11. **Security and hygiene:** no secrets, `.env` files, `node_modules`, `.venv`, model artifacts or large generated data in git. No force-push, no history rewriting, never touch git config or credentials, never install global packages without telling me.

## Session workflow (every session)
1. Read this file, `docs/PROGRESS.md`, and the spec sections named in the session prompt. Check `git status` and current branch.
2. Show a short plan (files to create or change, risks) and wait for my "go" if the plan changes scope. Otherwise proceed.
3. Create branch `session-<nn>-<short-name>` from an up-to-date `main`.
4. Implement in small logical commits (`feat(backend): ...`, `fix(frontend): ...`, `test: ...`, `docs: ...`).
5. **Run everything you claim works** (tests, build, the actual job or app) and show me the real output. Never report success from reading code. If something cannot be run here, say so plainly under "Not verified".
6. Fix failures before moving on. Do not weaken or delete tests to make them pass.
7. Update `docs/PROGRESS.md` (status, decisions, not verified, known issues, next session) and `docs/DECISIONS.md` for any judgment call.
8. Push the branch and open a pull request with `gh` if available (otherwise print the compare URL). Do not merge and do not push to `main`.
9. End with a summary: what was built, how I can verify it in under five minutes, test results, decisions, Not verified, and what I must supply (data, expert input, translations, licence choice).
10. If the context is getting long, stop at a clean commit, write a handoff into `docs/PROGRESS.md` and tell me to start a fresh session.

## Code standards
- Backend: type hints, small functions, docstrings for public functions, `ruff` clean, deterministic seeds, config in one module, no work at import time.
- Frontend: TypeScript strict, no `any` without a comment, generated API types only (never hand-write response types), CSS variables from tokens, keyboard and screen-reader friendly, no inline colours.
- Tests accompany every feature. Keep them fast.
- Prefer boring, readable solutions over clever ones.

## When unsure
Ask me one clear question, or choose a sensible default, record it in `docs/DECISIONS.md` and continue. Never fabricate data sources, government partnerships, APIs or accuracy.
