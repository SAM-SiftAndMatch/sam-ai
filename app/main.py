from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middlewares import RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.db.mongodb import close_mongo_connection, connect_to_mongo

# Initialize application logging
setup_logging(debug=settings.DEBUG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


def create_app() -> FastAPI:
    """Application factory for Sam AI with security & production middleware."""
    app_instance = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description=f"FastAPI service for {settings.APP_NAME} with MongoDB Atlas and AI Modules",
        lifespan=lifespan,
    )

    # Attach rate limiter state & handler
    app_instance.state.limiter = limiter
    app_instance.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Register centralized exception handlers
    register_exception_handlers(app_instance)

    # Middlewares (Executed in reverse order of addition: Security -> Logging -> CORS)
    app_instance.add_middleware(SecurityHeadersMiddleware)
    app_instance.add_middleware(RequestLoggingMiddleware)
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # General endpoints
    @app_instance.get("/", tags=["General"])
    def read_root():
        return {
            "message": f"Welcome to {settings.APP_NAME}!",
            "docs": "/docs",
            "health": "/health",
            "api_v1": f"{settings.API_V1_PREFIX}/health",
        }

    @app_instance.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return Response(status_code=204)

    # Mount API routes
    app_instance.include_router(api_router)

    return app_instance


app = create_app()
