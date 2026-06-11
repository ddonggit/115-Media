"""OperationLog Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class OperationLogCreate(BaseModel):
    action: str = Field(..., max_length=128)
    module: str = Field(..., max_length=64)
    level: str = Field(default="info", pattern="^(debug|info|warning|error)$")
    detail: str = Field(..., max_length=4096)
    status: str = Field(default="success", pattern="^(success|failed|warning)$")
    error_message: str | None = Field(None, max_length=1024)


class OperationLogResponse(BaseModel):
    id: int
    action: str
    module: str
    level: str
    detail: str
    status: str
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True
