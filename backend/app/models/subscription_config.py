"""SubscriptionConfig model — RSS check interval."""
from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin


class SubscriptionConfig(TimestampMixin, Base):
    __tablename__ = "subscription_config"

    rss_check_interval_minutes: Mapped[int] = mapped_column(Integer, default=10, comment="RSS check interval in minutes (min 5, max 1440)")
