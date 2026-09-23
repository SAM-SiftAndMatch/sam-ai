import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Response
from pydantic import BaseModel
import uvicorn

from db.mongodb import connect_to_mongo, close_mongo_connection, ping_mongo

# Load environment variables
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Sam AI")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    try:
        await connect_to_mongo()
    except Exception as e:
        print(f"[Warning] Could not connect to MongoDB on startup: {e}")
    yield
    await close_mongo_connection()


app = FastAPI(
    title=APP_NAME,
    version="0.1.0",
    description="Minimal FastAPI service for Sam AI with MongoDB Atlas",
    lifespan=lifespan,
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
        "message": f"Welcome to {APP_NAME}!",
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
        app_name=APP_NAME,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
    )
