"""TransferConfig model — retry parameter settings."""
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin


class TransferConfig(TimestampMixin, Base):
    __tablename__ = "transfer_config"

    max_submit_retry: Mapped[int] = mapped_column(Integer, default=3, comment="Max submit retry count")
    submit_retry_interval_seconds: Mapped[int] = mapped_column(Integer, default=600, comment="Seconds between submit retries")
    max_download_retry: Mapped[int] = mapped_column(Integer, default=3, comment="Max download retry count")
    max_wait_days: Mapped[int] = mapped_column(Integer, default=7, comment="Max days to wait before expiry")
