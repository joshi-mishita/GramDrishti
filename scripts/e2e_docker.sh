#!/usr/bin/env bash
# End-to-end demo test against the Docker stack (S14), in an isolated compose project.
#
#   ./scripts/e2e_docker.sh            (or: make e2e)
#
# 1. starts project "gramdrishti-e2e" on ports 18000 / 18080 / 18081 with its own volumes (scripts/demo.sh)
# 2. Playwright: the demo script (frontend/e2e/demo-script.spec.ts)
# 3. feedback: POST /feedback through the web proxy and read the row back from SQLite in the API container
# 4. stops the API and runs frontend/e2e/demo-offline.spec.ts: the offline copy still shows the demo, and
#    the live app shows its error state instead of hanging
# 5. removes the project and its volumes (E2E_KEEP=1 keeps them for a look)
#
# Needs Docker with Compose v2 and the frontend's npm install (Playwright browsers: npx playwright install).
set -euo pipefail
cd "$(dirname "$0")/.."

export COMPOSE_PROJECT_NAME=${E2E_PROJECT:-gramdrishti-e2e}
export WEB_PORT=18080 OFFLINE_PORT=18081 API_PORT=18000
export E2E_BASE_URL=http://localhost:$WEB_PORT E2E_OFFLINE_URL=http://localhost:$OFFLINE_PORT
# With a trained model in this checkout the stack serves its verification numbers, and the test demands
# them; a fresh clone trains its own model version, which has none (docs/DECISIONS.md D122).
if [ -f backend/artifacts/config.json ]; then export E2E_REQUIRE_VERIFICATION=1; fi

say() { printf '[e2e] %s\n' "$*"; }
cleanup() {
  if [ "${E2E_KEEP:-0}" = 1 ]; then say "kept project $COMPOSE_PROJECT_NAME (docker compose -p $COMPOSE_PROJECT_NAME down -v)"
  else docker compose down -v --remove-orphans >/dev/null 2>&1 || true; say "removed project $COMPOSE_PROJECT_NAME"; fi
}
trap cleanup EXIT

t0=$(date +%s)
./scripts/demo.sh
t1=$(date +%s)

say "Playwright: demo script against $E2E_BASE_URL"
(cd frontend && npx playwright test --config playwright.docker.config.ts e2e/demo-script.spec.ts)

say "feedback: POST /feedback, then read it back from SQLite"
resp=$(curl -fsS -X POST "$E2E_BASE_URL/api/v1/feedback" -H 'Content-Type: application/json' -H 'X-Role: farmer' \
  -d '{"panchayat_id":"MP0307","date":"2024-09-08","reported_rain":true,"intensity":"heavy","channel":"app"}')
say "response: $resp"
case "$resp" in *'"stored":true'*) ;; *) say "FAIL: feedback not stored"; exit 1 ;; esac
docker compose exec -T api python - <<'EOF'
import os, sqlite3
con = sqlite3.connect(os.environ["GRAMDRISHTI_DB"])
rows = con.execute("SELECT id, panchayat_id, date, reported_rain, intensity, channel FROM feedback "
                   "WHERE panchayat_id = 'MP0307' AND date = '2024-09-08'").fetchall()
print(f"[e2e] SQLite feedback rows for MP0307 on 2024-09-08: {rows}")
assert rows and rows[-1][3:] == (1, "heavy", "app"), rows
EOF

say "stopping the API; the offline copy must keep the demo running"
docker compose stop api
(cd frontend && E2E_API_DOWN=1 npx playwright test --config playwright.docker.config.ts e2e/demo-offline.spec.ts)
t2=$(date +%s)
say "passed: stack up $((t1 - t0)) s, tests $((t2 - t1)) s"
