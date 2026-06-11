"""SyncConfig Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class SyncConfigCreate(BaseModel):
    source_dir: str = Field("/", max_length=256)
    video_exts: str = Field(".mkv,.mp4,.avi,.ts,.m2ts,.iso,.bdmv,.m4v,.mov,.wmv,.flv,.webm")
    cron_expr: str | None = Field(None, max_length=64)


class SyncConfigUpdate(BaseModel):
    source_dir: str | None = Field(None, max_length=256)
    video_exts: str | None = None
    cron_expr: str | None = Field(None, max_length=64)


class SyncConfigResponse(BaseModel):
    id: int
    source_dir: str
    video_exts: str
    cron_expr: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
