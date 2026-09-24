# GramDrishti progress log

Claude Code updates this file at the end of every session. People update the "Merged" column after reviewing the pull request.

## Session status

| ID | Session | Owner | Status | PR | Merged |
|---|---|---|---|---|---|
| S0 | Repo foundation | both | PR open | session-00-foundation | |
| S1 | Backend data layer and baselines | backend | not started | | |
| S2 | Contract and API skeleton | backend | not started | | |
| S3 | Frontend foundation | frontend | not started | | |
| S4 | Frontend map explorer | frontend | not started | | |
| S5 | Backend model core | backend | not started | | |
| S6 | Agro-variables, snapshots, forecast APIs | backend | not started | | |
| S7 | Frontend detail panel and first integration | frontend | not started | | |
| S8 | Advisory engine and review APIs | backend | not started | | |
| S9 | Frontend priority, risk and review | frontend | not started | | |
| S10 | Verification and impact | backend | not started | | |
| S11 | Frontend verification and impact | frontend | not started | | |
| S12 | Farmer-side backend and snapshot export | backend | not started | | |
| S13 | Frontend farmer app, languages, bulletin, offline | frontend | not started | | |
| S14 | Integration, Docker and end-to-end tests | both | not started | | |
| S15 | Design and accessibility polish | frontend | not started | | |
| S16 | Documentation and submission assets | both | not started | | |
| S17 | Final QA and demo freeze | both | not started | | |

## Current state
Repo skeleton, README with architecture diagram, contribution rules, PR template and CI are in place (S0). No backend or frontend code yet; CI skips both jobs until `backend/pyproject.toml` and `frontend/package.json` exist.

## Decisions
- D001 Licence MIT.
- D002 Mock data flattened into `data/`; zip and `synthetic_oracle/` git-ignored.
- D003 CI detect job skips missing halves.

## Not verified
- S0: CI has not run on GitHub yet from this session; check the pull request's checks. Mermaid checked with the mermaid parser locally, not seen rendered on GitHub.

## Known issues
- `gh` CLI not installed, so pull requests are opened by hand from the compare URL.
- `data/synthetic_oracle/` is git-ignored: a fresh clone must regenerate it with `OUT=data python data/generate_mock_data.py`. The generator's default `OUT` is `/mnt/user-data/outputs/...`, which does not exist locally; S1 should make the default `data/` and verify the committed files reproduce (S1 task 5).

## Inputs needed from the team
- Enable branch protection on `main` (require pull request, require CI).
- Later: expert threshold review (S8), native Hindi/Punjabi review (S3, S13).

## Model and validation log
| Date | Model version | Windows used | Notes |
|---|---|---|---|
| | | | TEST window opened: never |

## Handoff for the next session
S0 is complete once its PR is merged. Next: S1 (backend) and S3 (frontend) can start in parallel from `main`.
