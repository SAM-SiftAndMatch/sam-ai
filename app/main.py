from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.mongodb import close_mongo_connection, connect_to_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    try:
        await connect_to_mongo()
    except Exception as e:  # noqa: BLE001
        print(f"[Warning] Could not connect to MongoDB on startup: {e}")
    yield
    await close_mongo_connection()


def create_app() -> FastAPI:
    """Application factory for Sam AI."""
    app_instance = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description=f"FastAPI service for {settings.APP_NAME} with MongoDB Atlas and AI Modules",
        lifespan=lifespan,
    )

    # CORS Configuration
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
