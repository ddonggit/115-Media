"""SyncRecord model — full/incremental sync state with checkpoint support."""
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from app.core.database import Base, TimestampMixin, _utcnow


class SyncType(str, enum.Enum):
    full = "full"
    incremental = "incremental"


class SyncStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    interrupted = "interrupted"


class SyncRecord(TimestampMixin, Base):
    __tablename__ = "sync_record"

    type: Mapped[SyncType] = mapped_column(SAEnum(SyncType), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(SAEnum(SyncStatus), nullable=False, default=SyncStatus.running)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    checkpoint_cid: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="for resume")
    current_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    scanned_files: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    can_resume: Mapped[bool] = mapped_column(Boolean, default=False)
