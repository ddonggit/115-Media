"""TransferTask Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field
import enum


class TransferStatus(str, enum.Enum):
    submitted = "submitted"
    submit_failed = "submit_failed"
    done = "done"
    download_failed = "download_failed"


class TransferTaskCreate(BaseModel):
    transfer_type: str = "magnet"
    url: str = Field(..., max_length=2048)
    target_dir: str = Field(..., max_length=1024)
    auto_organize: bool = True
    media_name: str | None = Field(None, max_length=256)
    tmdb_id: int | None = None
    size: str | None = Field(None, max_length=64)


class TransferTaskUpdate(BaseModel):
    status: TransferStatus | None = None
    progress: int | None = Field(None, ge=0, le=100)
    error_message: str | None = None
    download_retry_count: int | None = None
    submit_retry_count: int | None = None


class TransferTaskResponse(BaseModel):
    id: int
    transfer_type: str
    url: str
    target_dir: str
    auto_organize: bool
    media_name: str | None
    tmdb_id: int | None
    size: str | None
    status: TransferStatus
    progress: int | None
    error_message: str | None
    download_retry_count: int
    max_download_retry: int
    next_download_retry_at: datetime | None
    submitted_at: datetime | None
    expires_at: datetime | None
    submit_retry_count: int
    max_submit_retry: int
    next_submit_retry_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
