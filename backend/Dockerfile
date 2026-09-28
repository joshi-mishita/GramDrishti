# GramDrishti API image (S14). Build context: the repository root (docker-compose.yml does this).
# The package keeps the repo layout (/app/backend, /app/data) because gramdrishti.data.config finds the
# data folder relative to its own file. Trained models, snapshots, the SQLite store and the synthetic oracle
# are volumes, never baked into the image.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_MODE=mock \
    GRAMDRISHTI_DB=/app/state/gramdrishti.sqlite \
    GRAMDRISHTI_LOG_FORMAT=json \
    MPLCONFIGDIR=/tmp/matplotlib

# LightGBM needs the OpenMP runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin app

WORKDIR /app
COPY backend/requirements.lock backend/requirements.lock
RUN pip install -r backend/requirements.lock

COPY backend/pyproject.toml backend/README.md backend/
COPY backend/gramdrishti backend/gramdrishti
RUN pip install --no-deps -e backend
COPY data data

# Mount points for the volumes, owned by the app user so a new named volume inherits the owner.
RUN mkdir -p backend/artifacts state offline data/synthetic_oracle \
    && chown -R app:app backend/artifacts state offline data/synthetic_oracle

USER app
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status != 200)"]
# One worker: the Service keeps in-memory caches and the SQLite store is single-writer.
# The JSON access log (gramdrishti.access) replaces uvicorn's, which would record client addresses.
CMD ["uvicorn", "gramdrishti.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", \
     "--timeout-graceful-shutdown", "5"]
