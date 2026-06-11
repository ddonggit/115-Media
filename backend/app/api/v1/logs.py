"""Logs API — operation log viewer with module/level/time filters."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, delete
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.models.operation_log import OperationLog
from app.schemas.operation_log import OperationLogResponse

router = APIRouter(prefix="/logs", tags=["logs"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/", response_model=list[OperationLogResponse])
async def list_logs(
    module: str | None = Query(None),
    level: str | None = Query(None, pattern="^(debug|info|warning|error)$"),
    time_range: str | None = Query(None, alias="range", description="24h|7d|30d|all"),
    limit: int = Query(100, ge=1, le=500),
    auth=Depends(get_current_user),
):
    """List operation logs with filters."""
    async with async_session_factory() as session:
        stmt = select(OperationLog)
        
        if module:
            stmt = stmt.where(OperationLog.module == module)
        if level:
            stmt = stmt.where(OperationLog.level == level)
        if time_range and time_range != "all":
            hours = {"24h": 24, "7d": 168, "30d": 720}.get(time_range, 24)
            cutoff = _utcnow() - timedelta(hours=hours)
            stmt = stmt.where(OperationLog.created_at >= cutoff)
        
        stmt = stmt.order_by(OperationLog.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


@router.delete("/")
async def clear_logs(auth=Depends(get_current_user)):
    """Clear all operation logs."""
    async with async_session_factory() as session:
        await session.execute(delete(OperationLog))
        await session.commit()
        return {"message": "logs cleared"}


@router.get("/modules")
async def list_modules(auth=Depends(get_current_user)):
    """List distinct log modules."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(OperationLog.module).distinct().order_by(OperationLog.module)
        )
        modules = [row[0] for row in result.all()]
        return {"data": modules}


@router.get("/stats")
async def log_stats(auth=Depends(get_current_user)):
    """Get log statistics grouped by level and module."""
    from sqlalchemy import func
    async with async_session_factory() as session:
        # By level
        level_result = await session.execute(
            select(OperationLog.level, func.count(OperationLog.id))
            .group_by(OperationLog.level)
        )
        by_level = {row[0]: row[1] for row in level_result.all()}
        # By module
        module_result = await session.execute(
            select(OperationLog.module, func.count(OperationLog.id))
            .group_by(OperationLog.module)
        )
        by_module = {row[0]: row[1] for row in module_result.all()}
        return {"data": {"by_level": by_level, "by_module": by_module}}
