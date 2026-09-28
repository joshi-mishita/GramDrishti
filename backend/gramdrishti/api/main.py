"""FastAPI app. Run: ``cd backend && uvicorn gramdrishti.api.main:app --reload --port 8000``.

Creating the app loads no data; the Service loads files on the first request that needs them.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from gramdrishti.api.errors import install_handlers
from gramdrishti.api.hardening import BodySizeLimit, configure_json_logging, request_record, timer
from gramdrishti.api.routes import advisories, farmers, forecast, geo, meta, risk, verification
from gramdrishti.api.schemas import API_VERSION
from gramdrishti.api.service import Service
from gramdrishti.data.config import cors_origins, data_mode, log_json, max_body_bytes

PREFIX = "/api/v1"
log = logging.getLogger("gramdrishti.api")
access = logging.getLogger("gramdrishti.access")


def create_app(svc: Service | None = None) -> FastAPI:
    """Build the app. Tests and the example generator pass their own Service (for example a fixed clock)."""
    app = FastAPI(title="GramDrishti API", version=API_VERSION,
                  description="Panchayat-level forecasts and advisories. Contract: Appendix A of the guides. "
                              "Every response carries data_mode; 'mock' means synthetic data.")
    app.state.service = svc or Service()
    if log_json():
        configure_json_logging()
    # Origins come from GRAMDRISHTI_CORS_ORIGINS; only the methods and headers the frontend sends.
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins(), allow_methods=["GET", "POST"],
                       allow_headers=["Accept", "Content-Type", "X-Role"], expose_headers=["X-Data-Mode"])
    install_handlers(app)

    @app.middleware("http")
    async def data_mode_header(request: Request, call_next) -> Response:  # noqa: ANN001
        t0, mode = timer(), data_mode()
        response = await call_next(request)
        response.headers["X-Data-Mode"] = mode
        # Access log without personal data (hardening.request_record); the X-Role header is logging only.
        access.info("request", extra={"fields": request_record(request, response.status_code, timer() - t0,
                                                                 mode)})
        return response

    # Outermost, so an oversized body is refused before any route reads it.
    app.add_middleware(BodySizeLimit, limit=max_body_bytes())

    for r in (meta, geo, forecast, risk, advisories, farmers, verification):
        app.include_router(r.router, prefix=PREFIX)
    return app


app = create_app()
