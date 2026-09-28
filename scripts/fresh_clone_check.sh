#!/usr/bin/env bash
# Fresh-clone check (S14): clone into a temp folder, follow the README quick start literally, hit the
# key endpoints and the frontend, then remove the clone, its containers and its volumes.
#
#   ./scripts/fresh_clone_check.sh              clones this checkout's current branch (committed work only)
#   FRESH_SOURCE=https://github.com/joshi-mishita/GramDrishti.git FRESH_BRANCH=main ./scripts/fresh_clone_check.sh
#
# The quick start is the bash block between <!-- quickstart:start --> and <!-- quickstart:end --> in
# README.md. Every line runs as written, in the clone, except `git clone ...` (done here from
# FRESH_SOURCE) and `cd GramDrishti`. The stack runs as compose project "gramdrishti-fresh" on ports
# 28000 / 28080 / 28081 so it never touches the demo stack. A fresh clone has no trained model, so it
# trains one (about 2 minutes); FRESH_KEEP=1 keeps everything for a look.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
source_repo=${FRESH_SOURCE:-$here}
branch=${FRESH_BRANCH:-$(git -C "$here" rev-parse --abbrev-ref HEAD)}

export COMPOSE_PROJECT_NAME=gramdrishti-fresh WEB_PORT=28080 OFFLINE_PORT=28081 API_PORT=28000
say() { printf '[fresh] %s\n' "$*"; }
fail() { printf '[fresh] FAIL: %s\n' "$*" >&2; exit 1; }

tmp=$(mktemp -d "${TMPDIR:-/tmp}/gramdrishti-fresh.XXXXXX")
cleanup() {
  if [ "${FRESH_KEEP:-0}" = 1 ]; then say "kept $tmp and project $COMPOSE_PROJECT_NAME"; return; fi
  (cd "$tmp/GramDrishti" 2>/dev/null && docker compose down -v --remove-orphans >/dev/null 2>&1) || true
  rm -rf "$tmp"
  say "removed $tmp, its containers and volumes"
}
trap cleanup EXIT

t0=$(date +%s)
say "git clone --branch $branch $source_repo -> $tmp/GramDrishti"
git clone --quiet --branch "$branch" "$source_repo" "$tmp/GramDrishti"
cd "$tmp/GramDrishti"
say "commit $(git rev-parse --short HEAD); untracked model files: $(ls backend/artifacts 2>/dev/null | wc -l | tr -d ' ')"

steps=$(awk '/<!-- quickstart:start -->/{on=1; next} /<!-- quickstart:end -->/{on=0} on' README.md \
  | grep -v '^```' | sed 's/[[:space:]]*#.*$//' | grep -v '^[[:space:]]*$' || true)
[ -n "$steps" ] || fail "no quick start block in README.md"
while IFS= read -r line; do
  case "$line" in
    "git clone "*|"cd GramDrishti") say "skip (done above): $line" ;;
    *) say "\$ $line"; bash -c "$line" < /dev/null ;;
  esac
done <<< "$steps"
t1=$(date +%s)

api=http://localhost:$API_PORT/api/v1 web=http://localhost:$WEB_PORT offline=http://localhost:$OFFLINE_PORT
hit() {  # label url expected-status expected-substring
  local code body
  body=$(curl -sS --max-time 20 -o - -w '\n%{http_code}' "$2") || fail "$1: no answer from $2"
  code=${body##*$'\n'}; body=${body%$'\n'*}
  [ "$code" = "$3" ] || fail "$1: HTTP $code (wanted $3) from $2"
  case "$body" in *"$4"*) say "ok  $code  $1" ;; *) fail "$1: '$4' not in the answer from $2" ;; esac
}
hit "health"                     "$api/health" 200 '"status":"ok"'
hit "meta (8 demo dates)"        "$api/meta" 200 '"2024-09-09"'
hit "geo panchayats"             "$api/geo/panchayats" 200 '"FeatureCollection"'
hit "forecast map"               "$api/forecast/map?issue_date=2024-09-09&var=rain&lead_day=1" 200 '"MP0307"'
hit "forecast MP0307"            "$api/forecast/panchayat/MP0307?issue_date=2024-09-09" 200 '"p90"'
hit "observed MP0307"            "$api/observed/panchayat/MP0307?from=2024-09-10&to=2024-09-14" 200 '"data_mode":"mock"'
hit "advisories (drafts)"        "$api/advisories?issue_date=2024-09-09" 200 '"status":"draft"'
hit "farmer F001"                "$api/farmers/F001" 200 '"panchayat_id":"MP0307"'
hit "web app"                    "$web/" 200 '<div id="root">'
hit "web /api proxy"             "$web/api/v1/meta" 200 '"data_mode":"mock"'
hit "web unknown route -> app"   "$web/no/such/page" 200 '<div id="root">'
hit "offline copy"               "$offline/" 200 '<div id="root">'
hit "offline snapshot index"     "$offline/snapshot/index.json" 200 '"files"'
verif=$(curl -sS -o /dev/null -w '%{http_code}' "$api/verification/summary")
case "$verif" in
  200) say "ok  200  verification summary (record matches this model)" ;;
  503) hit "verification: not computed" "$api/verification/summary" 503 '"not_computed"'
       say "     a fresh clone trains its own model version, which has no verification record (D122)" ;;
  *) fail "verification summary: HTTP $verif" ;;
esac
say "quick start $((t1 - t0)) s (clone, build, prepare incl. training, start); all checks passed"
