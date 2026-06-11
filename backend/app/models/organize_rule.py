"""OrganizeRule model — TMDB-based classification rules (top-down priority)."""
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from app.core.database import Base, TimestampMixin


class RuleMediaType(str, enum.Enum):
    movie = "movie"
    tv = "tv"


class OrganizeRule(TimestampMixin, Base):
    __tablename__ = "organize_rule"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, comment="lower = checked first")
    media_type: Mapped[RuleMediaType] = mapped_column(SAEnum(RuleMediaType), nullable=False)
    genre_ids: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="comma-separated TMDB genre IDs")
    original_language: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="comma-separated ISO 639-1")
    origin_country: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="comma-separated ISO 3166-1")
    target_cid: Mapped[str] = mapped_column(String(64), nullable=False, comment="115 cloud directory cid")
    rename_pattern: Mapped[str] = mapped_column(String(1024), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
