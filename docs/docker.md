# Running GramDrishti with Docker

Everything in this stack is synthetic mock data. Every screen shows "Synthetic demo data. Not real weather."

## One command

```bash
make up            # same as ./scripts/demo.sh
```

What it does, in order:

1. **Build** three images from this checkout: `gramdrishti-api:local` (Python 3.13 slim, pinned
   `backend/requirements.lock`, non-root user, healthcheck), `gramdrishti-web:local` (Node build, then
   nginx-unprivileged on port 8080, `/api` proxied to the API) and `gramdrishti-web-offline:local` (the same
   app built with `VITE_SNAPSHOT=1`).
2. **Prepare** (`python -m gramdrishti.pipeline.prepare_demo` in the API image). Each step is skipped when its
   output is already in the volumes:
   - `oracle`: generate the git-ignored synthetic truth; the committed data files must come out byte for byte;
   - `model`: copy the trained model from `backend/artifacts/` when this checkout has one, else train (D122);
   - `snapshots`: forecast snapshots and draft advisories for the 8 demo dates and the day before each;
   - `verification`: copy the committed verification record when it belongs to this model (TEST is never
     opened here);
   - `farmers`: seed the five demo farmers;
   - `offline`: export every GET response for the offline copy (about 22,000 files, 39 MB).
3. **Start** `api` (8000), `web` (8080) and `web-offline` (8081), wait for their healthchecks, then check
   four URLs and print where to go.

Plain `docker compose up` works too: the `prepare` service runs first and the API waits for it. It cannot
see `backend/artifacts/`, so it trains its own model.

| Service | Port | What |
|---|---|---|
| `web` | 8080 | officer console and farmer app, `/api` proxied to `api` |
| `web-offline` | 8081 | the same app on the exported responses; needs no API |
| `api` | 8000 | FastAPI, docs at `/docs` |
| `prepare` | none | one-shot, exits 0 |

Volumes: `artifacts` (model, snapshots, verification files, audio cache), `state` (SQLite: advisories,
reviews, farmers, feedback), `oracle` (synthetic truth), `offline` (the export). `make down` keeps them;
`make clean` deletes them (the next `make up` retrains and loses every review).

## Timings (measured 2026-09-28 on the demo MacBook, Apple silicon, Colima 4 CPU / 8 GB)

| Run | Build | Prepare | Start | Total |
|---|---|---|---|---|
| Cold: no images, no build cache, no volumes, host model present | 223 s | 171 s (snapshots 45 s, offline export 124 s) | 20 s | **414 s** (6.9 min) |
| Fresh clone (`make fresh-check`, images cached): trains in the container | 1 s | 170 s (training 68 s, snapshots 31 s, export 70 s) | 18 s | 190 s |
| Warm: `make up` again, everything present | 17 s | 2 s | 13 s | **33 s** |

A fresh clone on a machine with no images therefore takes about 8 minutes: the cold build, training, snapshots
and the export. The export time varies between 66 and 124 s between runs.

## Demo insurance: the API dies on stage

```bash
docker compose stop api          # what happens if the API crashes
```

- `http://localhost:8081` keeps working: map, Panchayat panel, review list, verification, impact and the
  farmer screens all read the exported files. It never calls the API (the e2e checks this).
- `http://localhost:8080` shows each screen's error state ("Could not load ... Check the server is running")
  within about 2 s (1.4 to 1.5 s measured in S17 on the map, farmer and verification screens), with the message "The API is not reachable. Snapshot mode keeps the demo
  running without it." The mock ribbon is not shown there, because no response has told the app its data mode.
- The offline copy shows reviews as they were when it was exported. After approving advisories for the demo,
  run `make offline` (about 1 to 2 minutes) so the offline copy shows them too.
- `docker compose start api` brings the API back (healthy in about 10 s).

## Tests against the stack

```bash
make e2e           # ./scripts/e2e_docker.sh: isolated project on ports 180xx, removed afterwards
make fresh-check   # ./scripts/fresh_clone_check.sh: README quick start in a temp clone, ports 280xx
```

On a Mac where Playwright's own Chromium is not downloaded, add `SHOTS_BROWSER_CHANNEL=chrome` to use the
installed Google Chrome.

Two runs at once (for example from two worktrees) must not share a project, ports or images: give the second
one `E2E_PROJECT=<name> E2E_PORT_PREFIX=190 GRAMDRISHTI_IMAGE_TAG=<tag>` (D173). `E2E_HEADED=1 E2E_VIDEO=1
E2E_SLOWMO=250` shows the browser and keeps a video of every step (`frontend/test-results/e2e-docker/`). Screens go to `docs/screens/s14-*.png` (git-ignored).

## Configuration

Copy `.env.example` to `.env` to change ports (`WEB_PORT`, `OFFLINE_PORT`, `API_PORT`), the bind address
(`BIND_ADDRESS`, default 127.0.0.1), CORS origins (`GRAMDRISHTI_CORS_ORIGINS`) or the body limit
(`GRAMDRISHTI_MAX_BODY_BYTES`). Nothing in it is secret.

## Hardening in the stack

- API: request bodies over 64 KiB get 413 `payload_too_large` (chunked bodies too); CORS allows only the
  configured origins, GET and POST, and the headers the app sends; errors keep the contract shape.
- Logs: one JSON line per request (`docker compose logs api`) with method, route template, status, duration,
  role and data mode. No client address, user agent, query string, farmer id or request body.
- nginx: non-root on port 8080, `server_tokens off`, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, 64 KiB body limit, JSON 503 for `/api/` when the API is down, a static page for other
  server errors. No Content-Security-Policy yet (D124).
- Ports bind to 127.0.0.1 unless `.env` says otherwise.

## Dependency audit (2026-09-28)

| Tool | Scope | Result |
|---|---|---|
| `pip-audit 2.10.1 -r backend/requirements.lock` | 45 pinned runtime packages | 1 finding: `click` 8.1.8, CVE-2026-7246 (PYSEC-2026-2132), command injection in `click.edit()`, fixed in 8.3.3. Not upgraded: gTTS 2.5.4 requires `click<8.2`, and nothing in GramDrishti or the uvicorn server path calls `click.edit()` (D127). |
| `npm audit` (frontend, all dependencies) | 1,421 packages in the tree | 0 vulnerabilities |

Nothing was upgraded automatically.

## Troubleshooting

- **Colima** shares only your home folder with containers. `scripts/demo.sh` mounts `backend/artifacts/`
  read-only, so keep the checkout under `$HOME`.
- **Docker without BuildKit** (Colima's plain `docker` CLI) uses the classic builder, which works but prints
  a deprecation note. `brew install docker-buildx` removes it.
- **Verification says "not computed"** after a fresh clone: expected, see D122. Put the verified model in
  `backend/artifacts/` (or run the verification job for the new version in a verification session).
