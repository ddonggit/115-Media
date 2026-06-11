"""TmdbConfig Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class TmdbConfigCreate(BaseModel):
    api_key: str = Field(..., max_length=256, description="will be encrypted")
    language: str = "zh-CN"
    base_url: str = "https://api.themoviedb.org/3"
    image_base_url: str = "https://image.tmdb.org/t/p/"


class TmdbConfigUpdate(BaseModel):
    api_key: str | None = Field(None, max_length=256)
    language: str | None = None
    base_url: str | None = None
    image_base_url: str | None = None


class TmdbConfigResponse(BaseModel):
    id: int
    api_key: str
    language: str
    base_url: str
    image_base_url: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
