"""NotifyConfig model — Feishu / Telegram notification channels."""
from sqlalchemy import String, Boolean, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column
import enum
from app.core.database import Base, TimestampMixin


class NotifyChannel(str, enum.Enum):
    feishu = "feishu"
    telegram = "telegram"


class NotifyConfig(TimestampMixin, Base):
    __tablename__ = "notify_config"

    channel: Mapped[NotifyChannel] = mapped_column(SAEnum(NotifyChannel), nullable=False)
    webhook_url: Mapped[str] = mapped_column(String(1024), nullable=False, comment="encrypted")
    bot_token: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="encrypted, telegram only")
    chat_id: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="telegram only")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_on: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="e.g. ['transfer_done','organize_done','cookie_expired']")
