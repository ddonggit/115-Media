"""Subscription Pydantic schemas."""
from datetime import datetime
from pydantic import BaseModel, Field
import enum


class MediaType(str, enum.Enum):
    movie = "movie"
    tv = "tv"


class Quality(str, enum.Enum):
    FHD = "1080p"
    UHD = "4k"
    bluray = "bluray"
    bluray_4k = "bluray+4k"


class UpgradeStrategy(str, enum.Enum):
    coexist = "coexist"
    skip = "skip"
    max_size = "max_size"
    min_size = "min_size"


class SubStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


class SubscriptionCreate(BaseModel):
    tmdb_id: int = Field(..., description="REQUIRED FK to TMDB")
    media_name: str = Field(..., max_length=256)
    media_type: MediaType
    year: int | None = None
    quality: Quality = Quality.bluray
    upgrade_strategy: UpgradeStrategy = UpgradeStrategy.coexist
    season: int | None = Field(None, description="tv only")
    episode_start: int | None = Field(None, description="tv only, default 1")
    episode_end: int | None = Field(None, description="tv only, null=unlimited")
    include_hd_keyword: bool = True


class SubscriptionUpdate(BaseModel):
    media_name: str | None = Field(None, max_length=256)
    quality: Quality | None = None
    upgrade_strategy: UpgradeStrategy | None = None
    season: int | None = None
    episode_start: int | None = None
    episode_end: int | None = None
    status: SubStatus | None = None
    include_hd_keyword: bool | None = None


class SubscriptionResponse(BaseModel):
    id: int
    tmdb_id: int
    media_name: str
    media_type: MediaType
    year: int | None
    quality: Quality
    upgrade_strategy: UpgradeStrategy
    season: int | None
    episode_start: int | None
    episode_end: int | None
    episode_current: int | None
    source: str
    status: SubStatus
    last_match_at: datetime | None
    matched_count: int
    include_hd_keyword: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
