"""MediaFile model — 115 cloud file snapshot with recognition fields."""
from sqlalchemy import String, Integer, Boolean, BigInteger, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from app.core.database import Base, TimestampMixin


class MediaFileType(str, enum.Enum):
    movie = "movie"
    tv = "tv"
    unknown = "unknown"


class MediaFile(TimestampMixin, Base):
    __tablename__ = "media_file"

    cid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, comment="115 file ID")
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="bytes")
    media_type: Mapped[MediaFileType] = mapped_column(SAEnum(MediaFileType), nullable=False, default=MediaFileType.unknown)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="e.g. 2160p, 1080p")
    version: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="e.g. IMAX, 3D, CC")
    country: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="e.g. USA.UHD, NF")
    effect: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="e.g. DV.HDR, HDR, SDR")
    source: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="e.g. BluRay, WEB-DL")
    video_codec: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="e.g. x265.10bit, REMUX")
    audio_codec: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="e.g. TrueHD.7.1, DTS-HD")
    fps: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="e.g. 60FPS")
    recognized: Mapped[bool] = mapped_column(Boolean, default=False)
    organized: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="recognition retry count")
    strm_generated: Mapped[bool] = mapped_column(Boolean, default=False)
