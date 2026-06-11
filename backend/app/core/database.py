"""Database configuration — SQLite async, WAL mode."""
import os
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./data/115-media.db",
)

engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _utcnow() -> datetime:
    """Return naive UTC datetime (replacement for deprecated datetime.utcnow)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Mixin that adds id, created_at, updated_at to every table."""
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)


async def init_db():
    """Create all tables. Call once at startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # ── Safe migration: add new columns if they don't exist ──
        try:
            await conn.exec_driver_sql("ALTER TABLE media_file ADD COLUMN retry_count INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await conn.exec_driver_sql("ALTER TABLE media_file ADD COLUMN strm_generated BOOLEAN DEFAULT 0")
        except Exception:
            pass
        try:
            await conn.exec_driver_sql("ALTER TABLE rss_source ADD COLUMN episode INTEGER DEFAULT 0")
        except Exception:
            pass
    # Enable WAL mode
    async with engine.connect() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        await conn.commit()


async def get_session() -> AsyncSession:
    """Yield an async session — use as dependency."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
