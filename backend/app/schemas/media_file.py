"""MediaFile Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class MediaFileCreate(BaseModel):
    cid: str = Field(..., max_length=64)
    file_name: str = Field(..., max_length=512)
    file_path: str = Field(..., max_length=2048)
    file_size: int = Field(..., description="bytes")
    media_type: str = "unknown"
    tmdb_id: int | None = None
    year: int | None = None
    resolution: str | None = Field(None, max_length=32)
    version: str | None = Field(None, max_length=64)
    country: str | None = Field(None, max_length=64)
    effect: str | None = Field(None, max_length=64)
    source: str | None = Field(None, max_length=64)
    video_codec: str | None = Field(None, max_length=64)
    audio_codec: str | None = Field(None, max_length=64)
    fps: str | None = Field(None, max_length=32)


class MediaFileUpdate(BaseModel):
    media_type: str | None = None
    tmdb_id: int | None = None
    year: int | None = None
    resolution: str | None = None
    version: str | None = None
    country: str | None = None
    effect: str | None = None
    source: str | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    fps: str | None = None
    recognized: bool | None = None
    organized: bool | None = None
    strm_generated: bool | None = None


class MediaFileResponse(BaseModel):
    id: int
    cid: str
    file_name: str
    file_path: str
    file_size: int
    media_type: str
    tmdb_id: int | None
    year: int | None
    resolution: str | None
    version: str | None
    country: str | None
    effect: str | None
    source: str | None
    video_codec: str | None
    audio_codec: str | None
    fps: str | None
    recognized: bool
    organized: bool
    retry_count: int
    strm_generated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
