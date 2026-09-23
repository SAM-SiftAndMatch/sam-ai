from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import settings
from db.mongodb import close_mongo_connection, connect_to_mongo, ping_mongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    try:
        await connect_to_mongo()
    except Exception as e:  # noqa: BLE001
        print(f"[Warning] Could not connect to MongoDB on startup: {e}")
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description=f"Minimal FastAPI service for {settings.APP_NAME} with MongoDB Atlas",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    database: str
    app_name: str
    version: str
    timestamp: str


@app.get("/", tags=["General"])
def read_root():
    return {
        "message": f"Welcome to {settings.APP_NAME}!",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    is_db_connected = await ping_mongo()
    return HealthResponse(
        status="healthy",
        database="connected" if is_db_connected else "disconnected",
        app_name=settings.APP_NAME,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
