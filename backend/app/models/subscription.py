"""Subscription model — TMDB-based media subscription with quality/strategy."""
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from app.core.database import Base, TimestampMixin


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


class Source(str, enum.Enum):
    bt4g = "bt4g"


class SubStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscription"

    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="REQUIRED FK to TMDB")
    media_name: Mapped[str] = mapped_column(String(256), nullable=False)
    media_type: Mapped[MediaType] = mapped_column(SAEnum(MediaType), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality: Mapped[Quality] = mapped_column(SAEnum(Quality), nullable=False, default=Quality.bluray)
    upgrade_strategy: Mapped[UpgradeStrategy] = mapped_column(SAEnum(UpgradeStrategy), nullable=False, default=UpgradeStrategy.coexist)
    season: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="tv only: which season to follow")
    episode_start: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="tv only: first episode to match, default 1")
    episode_end: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="tv only: last episode, null=unlimited")
    episode_current: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="tv only: latest matched episode")
    source: Mapped[Source] = mapped_column(SAEnum(Source), nullable=False, default=Source.bt4g)
    status: Mapped[SubStatus] = mapped_column(SAEnum(SubStatus), nullable=False, default=SubStatus.active)
    include_hd_keyword: Mapped[bool] = mapped_column(Boolean, default=True, comment="append 高清 keyword to BT4G RSS URL")
    last_match_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
