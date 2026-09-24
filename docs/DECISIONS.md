# Decisions

Judgment calls made during the build. Add a row whenever a choice is not dictated by the guides or `CLAUDE.md`.

| ID | Date | Session | Decision | Why | Alternatives considered | Revisit when |
|---|---|---|---|---|---|---|
| D001 | 2026-09-24 | S0 | Licence: MIT, copyright "GramDrishti contributors". | Chosen by the team. | Apache-2.0, GPL-3.0, none. | n/a |
| D002 | 2026-09-24 | S0 | Mock data files sit directly in `data/`; the source zip and `data/synthetic_oracle/` are git-ignored. | `CLAUDE.md` and the session prompts expect `data/README.md` and `data/generate_mock_data.py`; the oracle is the answer key (4.4 MB) and can be regenerated. | Commit the oracle; keep the zip's nested folder. | If CI ever needs the oracle, generate it in the job. |
| D003 | 2026-09-24 | S0 | CI uses a `detect` job that sets outputs; backend and frontend jobs are skipped when their project files do not exist. | Job-level `if` cannot inspect files. Skipped jobs count as passing for required checks, so branch protection works from day one. | `hashFiles` in step-level `if` on every step. | n/a |
