"""StrmConfig model — STRM file generation settings."""
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin


class StrmConfig(TimestampMixin, Base):
    __tablename__ = "strm_config"

    strm_base_url: Mapped[str] = mapped_column(String(512), nullable=False, default="http://localhost:8095/115")
    media_library_path: Mapped[str] = mapped_column(String(1024), nullable=False, comment="local path for STRM files")
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=True)
