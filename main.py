import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Load environment variables
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Sam AI")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

app = FastAPI(
    title=APP_NAME,
    version="0.1.0",
    description="Minimal FastAPI service for Sam AI",
)


class HealthResponse(BaseModel):
    status: str
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


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return HealthResponse(
        status="healthy",
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
