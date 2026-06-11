"""TransferTask model — magnet/share-link transfer with 3-layer retry."""
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from app.core.database import Base, TimestampMixin


class TransferType(str, enum.Enum):
    magnet = "magnet"
    share_link = "share_link"


class TransferStatus(str, enum.Enum):
    submitted = "submitted"
    submit_failed = "submit_failed"
    done = "done"
    download_failed = "download_failed"


class TransferTask(TimestampMixin, Base):
    __tablename__ = "transfer_task"

    transfer_type: Mapped[TransferType] = mapped_column(SAEnum(TransferType), nullable=False, default=TransferType.magnet)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_dir: Mapped[str] = mapped_column(String(1024), nullable=False)
    auto_organize: Mapped[bool] = mapped_column(Boolean, default=True)
    media_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="from subscription")
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[TransferStatus] = mapped_column(SAEnum(TransferStatus), nullable=False, default=TransferStatus.submitted)
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    download_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_download_retry: Mapped[int] = mapped_column(Integer, default=3)
    next_download_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submit_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_submit_retry: Mapped[int] = mapped_column(Integer, default=3)
    next_submit_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
