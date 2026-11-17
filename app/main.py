import time
import uuid
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from app.core.config import get_settings
from app.core.logging import logger
from app.core.errors import AppError, error_response
from app.api.routes import router as api_router
from app.db.database import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    stats = db.get_stats()
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.VERSION} "
        f"[Provider: {settings.resolve_provider()} | DB Items: {stats['items_count']}]"
    )
    yield
    # Shutdown
    logger.info("Shutting down AI Knowledge Inbox.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description=(
            "A minimal, production-grade AI Knowledge Inbox with asynchronous content ingestion "
            "(notes and web URLs), recursive semantic chunking, SQLite vector storage, and grounded RAG question answering."
        ),
        lifespan=lifespan,
    )

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Structured Logging & Request ID Middleware
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        req_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["x-request-id"] = req_id
        response.headers["x-response-time-ms"] = f"{duration_ms:.2f}"

        # Exclude static assets from noisy logs
        if not request.url.path.startswith("/static"):
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code}",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )

        return response

    # 3. Custom Exception Handlers
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning(f"Application error [{exc.code}]: {exc.message}")
        return error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        details = []
        for error in exc.errors():
            loc = " -> ".join(str(l) for l in error.get("loc", []))
            details.append({
                "field": loc,
                "message": error.get("msg", ""),
                "type": error.get("type", "")
            })
        logger.warning(f"Validation error on {request.url.path}: {details}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "The request payload failed validation.",
                    "details": details,
                }
            }
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred.",
                    "details": str(exc) if settings.DEBUG else None,
                }
            }
        )

    # 4. Mount API Routes: both at root level (/ingest, /items, /query) and /api level (/api/ingest, etc.)
    app.include_router(api_router, tags=["Knowledge Inbox"])
    app.include_router(api_router, prefix="/api", tags=["API V1"])

    # 5. Serve React SPA static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/", include_in_schema=False)
        async def serve_index():
            index_path = os.path.join(static_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return JSONResponse({"message": "Turium AI Knowledge Inbox API running. Visit /docs for OpenAPI specs."})

    return app


app = create_app()
