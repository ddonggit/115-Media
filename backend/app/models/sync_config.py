"""SyncConfig model — sync directory and extension settings."""
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin


class SyncConfig(TimestampMixin, Base):
    __tablename__ = "sync_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_dir: Mapped[str] = mapped_column(String(256), default="/", comment="Root directory to sync from")
    video_exts: Mapped[str] = mapped_column(Text, default=".mkv,.mp4,.avi,.ts,.m2ts,.iso,.bdmv,.m4v,.mov,.wmv,.flv,.webm", comment="Comma-separated video file extensions")
    cron_expr: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None, comment="Cron expression for scheduled sync")
