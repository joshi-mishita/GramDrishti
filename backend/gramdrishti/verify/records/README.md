# Verification records

The output of the verification job (`python -m gramdrishti.verify.run_validation`), kept in git so a fresh
clone or a Docker build can show the verification and impact screens without opening TEST again
(`docs/validation_protocol.md`: TEST is opened once per model version).

One folder per model version, holding the job's `verification.json` and `impact.json` exactly as written to
`backend/artifacts/`. Nothing here is edited by hand.

`python -m gramdrishti.pipeline.prepare_demo` copies a record into `backend/artifacts/` only when all of
these match the local setup, and otherwise leaves the screens on "not computed":

- `frozen.model_version` equals `artifacts/config.json`;
- every file in `frozen.data_files_sha256` has that sha256 in `data/`;
- `frozen.library_versions`: the same Python minor version and the same LightGBM, scikit-learn, pandas and
  NumPy versions.

| Model version | TEST first opened | Report |
|---|---|---|
| `s5-lgbm-9b632a7b1b` | 2026-09-27T15:14:23 (`docs/test_window_ledger.json`) | `docs/validation_report.md` |
