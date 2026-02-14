"""
FastAPI主应用
"""

import logging
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from .config import settings
from .database import init_db, get_db
from .routes import auth, users, plugins, projects, simulations

# Configure logging format for the application
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# OpenAPI tags for organized documentation
tags_metadata = [
    {
        "name": "Authentication",
        "description": "User registration, login, token management, and password operations.",
    },
    {
        "name": "Users",
        "description": "User profile retrieval and updates.",
    },
    {
        "name": "Projects",
        "description": "Hydraulic simulation project management (CRUD).",
    },
    {
        "name": "Simulation Jobs",
        "description": "Create, run, monitor, and retrieve results for hydraulic simulation jobs.",
    },
    {
        "name": "Plugins",
        "description": "Browse, publish, rate, and comment on community simulation plugins.",
    },
]

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "HydroClaude Hydraulic Simulation Platform API.\n\n"
        "Provides endpoints for hydraulic modeling, open-channel flow simulation "
        "(Saint-Venant / Shallow Water Equations), project management, and a "
        "community plugin marketplace.\n\n"
        "**Authentication**: All protected endpoints require a Bearer token obtained "
        "via the `/api/auth/login` endpoint."
    ),
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(plugins.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(simulations.router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return consistent JSON for validation errors."""
    errors = []
    for err in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", "Validation error"),
            "type": err.get("type", "value_error"),
        })
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": errors},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return consistent JSON for all HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global catch-all: log the full traceback, return a safe error ID to the client."""
    error_id = str(uuid.uuid4())[:8]
    logger.error(f"[{error_id}] Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_id": error_id},
    )


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    try:
        init_db()
        logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} started")
        logger.info(f"API docs: http://{settings.HOST}:{settings.PORT}/docs")
    except Exception as e:
        logger.error(f"FATAL: Database initialization failed: {e}")
        raise


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring systems."""
    db = None
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "version": settings.APP_VERSION}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "disconnected"})
    finally:
        if db is not None:
            db.close()
