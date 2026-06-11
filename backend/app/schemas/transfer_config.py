"""TransferConfig Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class TransferConfigCreate(BaseModel):
    max_submit_retry: int = Field(3, ge=1, le=10)
    submit_retry_interval_seconds: int = Field(600, ge=60, le=3600)
    max_download_retry: int = Field(3, ge=1, le=10)
    max_wait_days: int = Field(7, ge=1, le=30)


class TransferConfigUpdate(BaseModel):
    max_submit_retry: int | None = Field(None, ge=1, le=10)
    submit_retry_interval_seconds: int | None = Field(None, ge=60, le=3600)
    max_download_retry: int | None = Field(None, ge=1, le=10)
    max_wait_days: int | None = Field(None, ge=1, le=30)


class TransferConfigResponse(BaseModel):
    id: int
    max_submit_retry: int
    submit_retry_interval_seconds: int
    max_download_retry: int
    max_wait_days: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
