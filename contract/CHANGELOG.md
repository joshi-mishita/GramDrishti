# API contract changelog

The contract is defined in Appendix A of `docs/GramDrishti_Backend_Guide.pdf` and `docs/GramDrishti_Frontend_Guide.pdf`, and implemented as `contract/openapi.json` plus `contract/examples/*.json`.

Rules (see `CONTRIBUTING.md`):
- Additive, optional fields: new minor version entry here, regenerate `openapi.json` and examples.
- Breaking changes (remove, rename, change type): agreed by both people before any code.

| Version | Date | Status | Change | Breaking |
|---|---|---|---|---|
| v0.1 | 2026-09-24 | draft | Contract as written in Appendix A. Not yet implemented; `openapi.json` and examples arrive in S2. | n/a |
