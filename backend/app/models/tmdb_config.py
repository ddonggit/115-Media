"""TmdbConfig model — TMDB API configuration (api_key encrypted)."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin


class TmdbConfig(TimestampMixin, Base):
    __tablename__ = "tmdb_config"

    api_key: Mapped[str] = mapped_column(String(512), nullable=False, comment="encrypted")
    language: Mapped[str] = mapped_column(String(16), nullable=False, default="zh-CN")
    base_url: Mapped[str] = mapped_column(String(256), nullable=False, default="https://api.themoviedb.org/3")
    image_base_url: Mapped[str] = mapped_column(String(256), nullable=False, default="https://image.tmdb.org/t/p/")
