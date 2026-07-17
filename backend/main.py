"""
FIFA World Cup 2026 GenAI Smart Stadium Copilot -- backend entrypoint.

Run with:
    uvicorn backend.main:app --reload
"""

from __future__ import annotations

import os
import uuid

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.api.auth import router as auth_router
from backend.api.routes import router as chat_router
from backend.core.config import settings
from backend.core.logging_config import configure_logging, get_logger
from backend.core.rate_limit import limiter

configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="FIFA World Cup 2026 GenAI Smart Stadium Copilot",
    version="0.1.0",
    description="MVP backend: LangGraph orchestration over navigation, "
    "crowd, accessibility, and emergency agents with RAG + mocked live "
    "stadium data.",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS configuration restricted to settings config (CORS protection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Enable GZip compression for responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)


# Inject standard security headers
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Secure error handling: never leak stack traces or internal exception
    detail to the client. Log the real error server-side with a
    correlation ID the client can quote when reporting an issue.
    """
    error_id = str(uuid.uuid4())
    logger.error("Unhandled exception [error_id=%s]: %s", error_id, exc, exc_info=not settings.is_production)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "error_id": error_id},
    )


app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
