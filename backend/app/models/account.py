"""Account115 model — 115 account with encrypted cookie."""
from sqlalchemy import String, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.core.database import Base, TimestampMixin


class Account115(TimestampMixin, Base):
    __tablename__ = "account115"

    cookie: Mapped[str] = mapped_column(String(4096), nullable=False, comment="encrypted cookie")
    uid: Mapped[str] = mapped_column(String(64), nullable=True)
    username: Mapped[str] = mapped_column(String(128), nullable=True)
    total_space: Mapped[int] = mapped_column(BigInteger, nullable=True, comment="bytes")
    used_space: Mapped[int] = mapped_column(BigInteger, nullable=True, comment="bytes")
    expire_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="UTC")
