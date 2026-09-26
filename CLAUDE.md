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
- Backend setup: `cd backend && python -m venv .venv && .venv/bin/pip install -e ".[dev]"`
- Regenerate mock data (incl. git-ignored oracle): `python data/generate_mock_data.py`
- Baseline report (TRAIN fit, CALIB scores): `cd backend && python -m gramdrishti.verify.baseline_report`
- Train models (writes git-ignored `backend/artifacts/`; add `--lobo` for leave-one-block-out): `cd backend && python -m gramdrishti.pipeline.train`
- Build forecast snapshots and draft advisories (needs trained artifacts; the API reads them; drafts go to SQLite `backend/artifacts/gramdrishti.sqlite` or `GRAMDRISHTI_DB`, `--no-advisories` skips them): `cd backend && python -m gramdrishti.pipeline.run_daily --all-demo-dates` (or `--issue-date YYYY-MM-DD`)
- Create or migrate the SQLite store (optional, run_daily and the API do it too): `cd backend && python -m gramdrishti.store.init_db`
- Validate advisory rules and templates, write `rules.schema.json`: `cd backend && python -m gramdrishti.advisory.rules`
- Expert thresholds table (writes `docs/thresholds_for_expert_review.md`; a test checks it is current): `cd backend && python -m gramdrishti.advisory.expert_table`
- Read stored advisories in plain text: `cd backend && python -m gramdrishti.advisory.show --issue-date 2024-09-09` (`--panchayat MP0307 MP0311`, `--lang hi`, `--counts`)
- Run API: `cd backend && uvicorn gramdrishti.api.main:app --reload --port 8000`
- Export contract: `cd backend && python -m gramdrishti.export_openapi`
- Contract examples (calls the app, validates, writes `contract/examples/`; needs the snapshots above): `cd backend && python -m gramdrishti.contract.make_examples`
- Pick demo issue dates (prints reasons, writes `demo_dates.json`): `cd backend && python -m gramdrishti.contract.pick_demo_dates`
- Frontend setup (Node 22, see `frontend/.nvmrc`): `cd frontend && npm install`
- Frontend dev / build / test / lint: `cd frontend && npm run dev | build | test | lint`
- Frontend with the real API for some endpoints: `cd frontend && VITE_REAL_ENDPOINTS=meta npm run dev` (backend on port 8000)
- Frontend types from contract: `cd frontend && npm run gen:types` (CI runs `npm run check:types`)
- Copy contract examples to `frontend/public/mock/` (runs before dev and build): `cd frontend && npm run sync:mock`
- Screenshots for visual review: `cd frontend && npm run shots` (add `SHOTS_BROWSER_CHANNEL=chrome` if Playwright's Chromium cannot be downloaded)

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
