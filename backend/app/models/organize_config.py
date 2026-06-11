"""OrganizeConfig model — three key cid directories for auto-organize."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, TimestampMixin


class OrganizeConfig(TimestampMixin, Base):
    __tablename__ = "organize_config"

    source_cid: Mapped[str] = mapped_column(String(64), nullable=False, comment="source folder cid, e.g. yunxiazai")
    duplicate_cid: Mapped[str] = mapped_column(String(64), nullable=False, comment="target cid when duplicate name")
    processed_cid: Mapped[str] = mapped_column(String(64), nullable=False, comment="target cid after organize done")
