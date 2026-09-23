from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    app_name: str
    version: str
    timestamp: str
