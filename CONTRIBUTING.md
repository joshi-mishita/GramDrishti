# Contributing to GramDrishti

Two people work in this repo: one on the backend, one on the frontend. These rules keep us from stepping on each other.

## Who touches what

| Folder | Owner |
|---|---|
| `backend/` | backend person |
| `frontend/` | frontend person |
| `contract/` | both, through a reviewed pull request only |
| `data/`, `docs/`, `scripts/`, `.github/` | either, keep changes small |

## Branches

- Never commit to `main` directly. `main` only changes through merged pull requests.
- One branch per session: `session-<nn>-<name>`, for example `session-01-backend-data-baselines`.
- Small fixes outside a session: `fix/<short-name>`.
- Start from an up-to-date `main`: `git checkout main && git pull && git checkout -b session-<nn>-<name>`.

## Commits

Conventional style, one logical change per commit:

```
feat(backend): add QC flags for stuck sensors
fix(frontend): handle null p90 in fan chart
test: cover block-mean reconciliation
docs: update PROGRESS for S1
chore(ci): cache pip downloads
```

## Pull requests

- Fill in the pull request template, including the "Not verified" section.
- **Never merge a pull request with failing CI.**
- The other person reads every pull request that touches `contract/`. Anything else can be merged by its owner once CI is green and the "You verify" checks for the session are done.
- After merging, tick the session in the "Merged" column of `docs/PROGRESS.md`.

## Changing the API contract

The contract (Appendix A of the guides, implemented as `contract/openapi.json` and `contract/examples/`) is shared. **v0.1.1 is frozen** (see `contract/CHANGELOG.md`).

1. Additive, optional fields are allowed. Add a line to `contract/CHANGELOG.md` with the new version, regenerate `contract/openapi.json` and the examples, and tell the other person.
2. Anything that removes, renames or changes the type of a field is a breaking change. It needs agreement from both people before any code is written.
3. Never edit `contract/` in two open pull requests at the same time.

### How to change the contract (backend steps)

1. Edit the Pydantic models in `backend/gramdrishti/api/schemas.py` and bump `API_VERSION` there (minor bump for additive changes).
2. Add a row and a section for the new version to `contract/CHANGELOG.md`, marked additive or breaking.
3. Regenerate the contract files from `backend/`:
   ```bash
   python -m gramdrishti.export_openapi           # contract/openapi.json
   python -m gramdrishti.contract.make_examples   # contract/examples/*.json, *.geojson, index.json
   ```
4. Run `pytest -q`. The contract tests fail if `openapi.json` or any example is stale, if an example no longer validates, or if an endpoint has no example.
5. Open a pull request that touches `contract/` and ask the frontend person to review it. They run `npm run gen:types`; a changed field then breaks their build instead of the demo.

Demo issue dates are chosen by `python -m gramdrishti.contract.pick_demo_dates`, which prints why each date was picked and writes `backend/gramdrishti/contract/demo_dates.json`. Changing them changes `/meta`, so treat it like a contract change.

## Data honesty

- All current data is synthetic. Every API response carries `data_mode`, and the UI shows the mock ribbon when it is `"mock"`.
- Accuracy numbers come only from the verification job. Never type them by hand.
- Do not use `data/synthetic_oracle/` as a model feature.

## Running the project

Placeholders until the backend and frontend exist (sessions S1 to S3).

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest -q
uvicorn gramdrishti.api.main:app --reload --port 8000

# frontend
cd frontend
npm ci
npm run lint && npm test && npm run build
npm run dev
```
