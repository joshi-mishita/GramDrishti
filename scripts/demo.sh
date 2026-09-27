#!/usr/bin/env bash
# One command for the demo (S14): build the images, prepare the data, start everything, check it answers.
#
#   ./scripts/demo.sh        (or: make up)
#
# Prepare (python -m gramdrishti.pipeline.prepare_demo in the API image) skips every step already done:
# oracle, model (copied from backend/artifacts when this checkout has a trained model, else trained in
# the container), snapshots for the demo dates, the verification record, the demo farmers and the offline
# export. Needs Docker with Compose v2. Environment: COMPOSE_PROJECT_NAME, WEB_PORT, OFFLINE_PORT,
# API_PORT, BIND_ADDRESS (see .env.example).
set -euo pipefail
cd "$(dirname "$0")/.."

say() { printf '[demo] %s\n' "$*"; }
die() { printf '[demo] ERROR: %s\n' "$*" >&2; exit 1; }
now() { date +%s; }

command -v docker >/dev/null || die "docker not found. Install Docker Desktop, OrbStack or Colima first."
docker compose version >/dev/null 2>&1 || die "'docker compose' (Compose v2) not found."
docker info >/dev/null 2>&1 || die "the Docker daemon is not running (Colima: colima start)."

WEB_PORT=${WEB_PORT:-8080}
OFFLINE_PORT=${OFFLINE_PORT:-8081}
API_PORT=${API_PORT:-8000}
if [ -f .env ]; then
  # Ports from .env, so the printed URLs match what compose binds.
  eval "$(grep -E '^(WEB_PORT|OFFLINE_PORT|API_PORT)=[0-9]+$' .env || true)"
fi

t0=$(now)
say "1/3 building images"
docker compose build
t1=$(now)

say "2/3 preparing data (first run trains the model: about 2 minutes on a laptop)"
run_args=()
prep_args=(python -m gramdrishti.pipeline.prepare_demo --offline-out /app/offline/snapshot)
if [ -f backend/artifacts/config.json ]; then
  host_art=$(cd backend/artifacts && pwd -P)
  say "using the trained model in $host_art"
  run_args=(-v "$host_art:/host-artifacts:ro")
  prep_args+=(--seed-model-from /host-artifacts)
fi
docker compose run --rm ${run_args[@]+"${run_args[@]}"} prepare "${prep_args[@]}"
t2=$(now)

say "3/3 starting api, web and web-offline"
docker compose up -d --wait
t3=$(now)

check() {  # name url expected-substring
  local body
  body=$(curl -fsS --max-time 10 "$2") || die "$1 did not answer: $2"
  case "$body" in *"$3"*) say "ok   $1  $2" ;; *) die "$1 answered without '$3': $2" ;; esac
}
check "api health  " "http://localhost:$API_PORT/api/v1/health" '"status"'
check "web app     " "http://localhost:$WEB_PORT/" '<div id="root">'
check "web via /api" "http://localhost:$WEB_PORT/api/v1/meta" '"data_mode":"mock"'
check "offline app " "http://localhost:$OFFLINE_PORT/snapshot/index.json" '"files"'

say "build $((t1 - t0)) s, prepare $((t2 - t1)) s, start $((t3 - t2)) s, total $((t3 - t0)) s"
say "Synthetic demo data. Not real weather."
say "Officer console and farmer app:  http://localhost:$WEB_PORT/"
say "Offline copy (no API needed):    http://localhost:$OFFLINE_PORT/"
say "API docs:                        http://localhost:$API_PORT/docs"
say "Stop: make down.  Logs: make logs.  After approving advisories, refresh the offline copy: make offline."
