"""OrganizeRule Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field


class OrganizeRuleCreate(BaseModel):
    name: str = Field(..., max_length=128)
    priority: int = 0
    media_type: str = Field(..., pattern="^(movie|tv)$")
    genre_ids: str | None = Field(None, max_length=256, description="comma-separated TMDB genre IDs")
    original_language: str | None = Field(None, max_length=128, description="comma-separated ISO 639-1")
    origin_country: str | None = Field(None, max_length=128, description="comma-separated ISO 3166-1")
    target_cid: str = Field(..., max_length=64)
    rename_pattern: str = Field(..., max_length=1024)
    enabled: bool = True


class OrganizeRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    priority: int | None = None
    genre_ids: str | None = None
    original_language: str | None = None
    origin_country: str | None = None
    target_cid: str | None = Field(None, max_length=64)
    rename_pattern: str | None = Field(None, max_length=1024)
    enabled: bool | None = None


class OrganizeRuleResponse(BaseModel):
    id: int
    name: str
    priority: int
    media_type: str
    genre_ids: str | None
    original_language: str | None
    origin_country: str | None
    target_cid: str
    rename_pattern: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
