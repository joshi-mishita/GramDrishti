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

The contract in Appendix A of the guides (`contract/openapi.json` and `contract/examples/`) is shared.

1. Additive, optional fields are allowed. Add a line to `contract/CHANGELOG.md` with the new version, regenerate `contract/openapi.json` and the examples, and tell the other person.
2. Anything that removes, renames or changes the type of a field is a breaking change. It needs agreement from both people before any code is written.
3. Never edit `contract/` in two open pull requests at the same time.

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
