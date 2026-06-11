"""RSSSource Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class RSSSourceCreate(BaseModel):
    name: str = Field(..., max_length=128)
    url: str = Field(..., max_length=1024)
    category: str = Field(..., pattern="^(movie|tv)$")
    provider: str = Field(default="bt4g", pattern="^bt4g$")
    enabled: bool = True
    season: int = 0
    episode: int = 0
    include_keywords: list[str] | str | None = Field(None, description="comma-separated string or list")
    exclude_keywords: list[str] | str | None = Field(None, description="comma-separated string or list")

    @field_validator("include_keywords", "exclude_keywords", mode="before")
    @classmethod
    def coerce_to_list(cls, v):
        """Accept both comma-separated str and list; always output list for model."""
        if v is None:
            return None
        if isinstance(v, list):
            return [item.strip() for item in v if item.strip()]
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()] or None
        return v


class RSSSourceUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    url: str | None = Field(None, max_length=1024)
    category: str | None = Field(None, pattern="^(movie|tv|anime)$")
    enabled: bool | None = None
    season: int | None = None
    episode: int | None = None
    include_keywords: list[str] | str | None = None
    exclude_keywords: list[str] | str | None = None

    @field_validator("include_keywords", "exclude_keywords", mode="before")
    @classmethod
    def coerce_to_list(cls, v):
        """Accept both comma-separated str and list; always output list for model."""
        if v is None:
            return None
        if isinstance(v, list):
            return [item.strip() for item in v if item.strip()]
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()] or None
        return v


class RSSSourceResponse(BaseModel):
    id: int
    name: str
    url: str
    category: str
    provider: str
    enabled: bool
    season: int
    episode: int
    include_keywords: str | None
    exclude_keywords: str | None
    sync_status: str
    last_sync_at: datetime | None
    error_message: str | None
    item_count: int
    created_at: datetime
    updated_at: datetime

    @field_validator("include_keywords", "exclude_keywords", mode="before")
    @classmethod
    def coerce_keywords(cls, v):
        """Accept list[str] from JSON column."""
        if isinstance(v, list):
            return ",".join(v) if v else None
        return v

    class Config:
        from_attributes = True