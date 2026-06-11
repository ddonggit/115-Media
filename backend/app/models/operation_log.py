"""OperationLog model — audit log for all system operations."""
from sqlalchemy import String, Enum as SAEnum, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import enum
from app.core.database import Base, TimestampMixin


class LogLevel(str, enum.Enum):
    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"


class LogStatus(str, enum.Enum):
    success = "success"
    failed = "failed"
    warning = "warning"


class OperationLog(TimestampMixin, Base):
    __tablename__ = "operation_log"

    action: Mapped[str] = mapped_column(String(128), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[LogLevel] = mapped_column(SAEnum(LogLevel), nullable=False, default=LogLevel.info)
    detail: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[LogStatus] = mapped_column(SAEnum(LogStatus), nullable=False, default=LogStatus.success)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Use created_at as the log timestamp
