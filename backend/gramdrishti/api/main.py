"""FastAPI app. Run: ``cd backend && uvicorn gramdrishti.api.main:app --reload --port 8000``.

Creating the app loads no data; the Service loads files on the first request that needs them.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from gramdrishti.api.errors import install_handlers
from gramdrishti.api.routes import advisories, farmers, forecast, geo, meta, risk, verification
from gramdrishti.api.schemas import API_VERSION
from gramdrishti.api.service import Service
from gramdrishti.data.config import data_mode

PREFIX = "/api/v1"
ORIGINS = ["http://localhost:5173"]
log = logging.getLogger("gramdrishti.api")


def create_app(svc: Service | None = None) -> FastAPI:
    """Build the app. Tests and the example generator pass their own Service (for example a fixed clock)."""
    app = FastAPI(title="GramDrishti API", version=API_VERSION,
                  description="Panchayat-level forecasts and advisories. Contract: Appendix A of the guides. "
                              "Every response carries data_mode; 'mock' means synthetic data.")
    app.state.service = svc or Service()
    app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"],
                       expose_headers=["X-Data-Mode"])
    install_handlers(app)

    @app.middleware("http")
    async def data_mode_header(request: Request, call_next) -> Response:  # noqa: ANN001
        role = request.headers.get("X-Role")
        if role:
            log.info("%s %s role=%s", request.method, request.url.path, role)  # logging only, no auth
        response = await call_next(request)
        response.headers["X-Data-Mode"] = data_mode()
        return response

    for r in (meta, geo, forecast, risk, advisories, farmers, verification):
        app.include_router(r.router, prefix=PREFIX)
    return app


app = create_app()
