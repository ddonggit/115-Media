"""RSSSource model — BT4G RSS feed source."""
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from app.core.database import Base, TimestampMixin


class RSSProvider(str, enum.Enum):
    bt4g = "bt4g"


class RSSCategory(str, enum.Enum):
    movie = "movie"
    tv = "tv"


class SyncStatus(str, enum.Enum):
    ok = "ok"
    syncing = "syncing"
    error = "error"
    idle = "idle"


class RSSSource(TimestampMixin, Base):
    __tablename__ = "rss_source"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    category: Mapped[RSSCategory] = mapped_column(SAEnum(RSSCategory), nullable=False, default=RSSCategory.movie)
    provider: Mapped[RSSProvider] = mapped_column(SAEnum(RSSProvider), nullable=False, default=RSSProvider.bt4g)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    season: Mapped[int] = mapped_column(Integer, default=0)
    episode: Mapped[int] = mapped_column(Integer, default=0)
    include_keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="keywords that must appear")
    exclude_keywords: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="keywords that must NOT appear")
    sync_status: Mapped[SyncStatus] = mapped_column(SAEnum(SyncStatus), nullable=False, default=SyncStatus.idle)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
