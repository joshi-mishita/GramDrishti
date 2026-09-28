#!/usr/bin/env bash
# Pack the trained model bundle in backend/artifacts/ for a GitHub Release (S18, docs/deploy.md).
# The Pages workflow downloads it from the release tagged "model-bundle", so the public copy serves the
# model that went through the verification job instead of a Linux retrain with another version (D122).
# Model files stay out of git (CLAUDE.md rule 11). Output: gramdrishti-model-<version>.tar.gz in the
# current folder.
set -euo pipefail
ART="$(cd "$(dirname "$0")/../backend/artifacts" && pwd)"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["model_version"])' "$ART/config.json")"
TARGETS="$(python3 -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["targets"]))' "$ART/config.json")"
FILES=(config.json events.joblib bias.joblib conformal.json features.json)
for t in $TARGETS; do FILES+=("model_$t.joblib"); done
OUT="$PWD/gramdrishti-model-$VERSION.tar.gz"
tar -czf "$OUT" -C "$ART" "${FILES[@]}"
echo "$OUT ($(du -h "$OUT" | cut -f1)), model $VERSION"
