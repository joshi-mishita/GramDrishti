# Public demo on GitHub Pages

The web app is published as a **read-only copy** at https://joshi-mishita.github.io/GramDrishti/ once Pages is switched on (below). It opens on any phone, tablet or laptop, can be installed from the browser menu ("Add to Home screen"), and keeps working offline after the first visit.

## What the public copy is

- The snapshot variant of the app (`VITE_SNAPSHOT=1`): every GET response was exported once from the backend, so there is no server. It is the same kind of copy as the Docker offline copy on port 8081.
- **Everything is synthetic.** The ribbon "Synthetic demo data. Not real weather." is on every screen.
- **Reviews cannot be saved.** Approve, edit and reject answer "read only". Use the Docker stack (`make up`, [docker.md](docker.md)) for the full review flow.
- **Four advisories are pre-approved** so the farmer screens show advice: MP0307's and MP0311's bajra advisories on 9 Sep 2024 (demo farmers F001 and F002). Their reviewer is "Automated demo approval (no officer reviewed this)" and each carries a note saying so (D177). Every other advisory is a draft.
- The verification and impact screens show the committed verification record for model `s5-lgbm-9b632a7b1b` when the build's model version, data files and library versions match it ([validation protocol](validation_protocol.md)). Otherwise they say "not computed", and the build log has a warning. TEST is never opened by the build.
- A model trained on GitHub's Linux runner gets another version (`s5-lgbm-2576015e9e`, D122), so the verified numbers appear only when the verified model is attached to a release (setup step 2 below). Model files never go into git.

## How it is built

`.github/workflows/pages.yml`, on every push to `main` (and by hand from the Actions tab):

1. Python 3.13 with `backend/requirements.lock` (the versions of the verification record).
2. `python -m gramdrishti.pipeline.prepare_demo`: oracle, model (the released bundle with `--seed-model-from`, else trained in about two minutes), snapshots, verification record, farmers.
3. `python -m gramdrishti.pipeline.approve_demo --issue-date 2024-09-09 --panchayat MP0307 MP0311 --crop bajra` into a throwaway database.
4. `python -m gramdrishti.export_snapshot --out ../contract/snapshot` (about 22,000 files, 40 MB).
5. `BASE_PATH=/GramDrishti/ VITE_SNAPSHOT=1 npm run build`, then `404.html` (a copy of `index.html`, so deep links such as `/GramDrishti/farmer` open) and `.nojekyll`.
6. Upload and deploy with GitHub's Pages actions.

Pull requests run steps 1 to 5 only, so a change that breaks the public copy shows up before it is merged.

## One-time setup (repository owner)

1. On GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Attach the verified model, so the public verification and impact screens have numbers:
   - On the laptop that has it: `./scripts/pack_model_bundle.sh` writes `gramdrishti-model-s5-lgbm-9b632a7b1b.tar.gz` (about 11 MB).
   - On GitHub: **Releases → Draft a new release**, tag `model-bundle` (create it on `main`), title "Model bundle s5-lgbm-9b632a7b1b", attach the file, tick **Set as a pre-release**, and **Publish**. A draft is not enough: the workflow cannot see drafts.
   - Skip this and the site still works; those two screens then say "not computed".
3. Merge the pull request that adds the workflow, or run **Actions → Pages → Run workflow** on `main`.
4. After about 10 minutes the address appears on the workflow run and under Settings → Pages.

## Try the same build locally

```bash
cd backend && GRAMDRISHTI_DB=/tmp/pages.sqlite .venv/bin/python -m gramdrishti.pipeline.approve_demo --issue-date 2024-09-09 --panchayat MP0307 MP0311 --crop bajra
cd backend && GRAMDRISHTI_DB=/tmp/pages.sqlite .venv/bin/python -m gramdrishti.export_snapshot --out ../contract/snapshot
cd frontend && BASE_PATH=/GramDrishti/ VITE_SNAPSHOT=1 npm run build
```

`cd frontend && BASE_PATH=/GramDrishti/ npx vite preview` then serves it at http://localhost:4173/GramDrishti/.

## Limits

- GitHub Pages sites are public, even when the repository is private on a paid plan.
- No server: the "Listen" button uses the phone's own voice (the server's audio files are not exported), and rain reports from the farmer app are not stored.
- A normal build (without `BASE_PATH`) still serves from `/`, so Docker and `npm run dev` are unchanged.
