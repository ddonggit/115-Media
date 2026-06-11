"""ErrorLog Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorLogCreate(BaseModel):
    level: str = Field(..., pattern="^(error|warning)$")
    module: str = Field(..., pattern="^(transfer|sync|organize|auth|storage)$")
    title: str = Field(..., max_length=256)
    detail: str = Field(..., max_length=2048)
    can_retry: bool = False
    checkpoint: str | None = Field(None, max_length=256)


class ErrorLogUpdate(BaseModel):
    resolved: bool | None = None


class ErrorLogResponse(BaseModel):
    id: int
    level: str
    time: datetime
    module: str
    title: str
    detail: str
    can_retry: bool
    resolved: bool
    checkpoint: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
