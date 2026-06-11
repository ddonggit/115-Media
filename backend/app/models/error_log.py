"""ErrorLog model — dashboard error card entries."""
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from app.core.database import Base, TimestampMixin


class ErrorLevel(str, enum.Enum):
    error = "error"
    warning = "warning"


class ErrorModule(str, enum.Enum):
    transfer = "transfer"
    sync = "sync"
    organize = "organize"
    auth = "auth"
    storage = "storage"


class ErrorLog(TimestampMixin, Base):
    __tablename__ = "error_log"

    level: Mapped[ErrorLevel] = mapped_column(SAEnum(ErrorLevel), nullable=False, default=ErrorLevel.error)
    time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    module: Mapped[ErrorModule] = mapped_column(SAEnum(ErrorModule), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    detail: Mapped[str] = mapped_column(String(2048), nullable=False)
    can_retry: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    checkpoint: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="for sync resume")
