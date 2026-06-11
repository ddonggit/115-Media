"""Sync API — full/incremental sync with checkpoint resume."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.models.sync_record import SyncRecord
from app.models.sync_config import SyncConfig
from app.schemas.sync_record import SyncRecordResponse
from app.schemas.sync_config import SyncConfigUpdate, SyncConfigResponse

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/", response_model=list[SyncRecordResponse])
async def list_sync_records(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(
            select(SyncRecord).order_by(SyncRecord.created_at.desc()).limit(20)
        )
        return result.scalars().all()


@router.post("/start", response_model=SyncRecordResponse)
async def start_sync(
    sync_type: str = Query("full", pattern="^(full|incremental)$"),
    auth=Depends(get_current_user),
):
    """Start a sync task. sync_type: full or incremental (SPEC-compliant)."""
    async with async_session_factory() as session:
        record = SyncRecord(
            type=sync_type,
            status="running",
            progress=0,
            total_files=0,
            scanned_files=0,
        )
        session.add(record)
        await session.commit()
        from app.services.log_service import log_action
        await log_action(action=f"start_{sync_type}_sync", module="sync", detail=f"{'全量同步' if sync_type=='full' else '增量同步'}已加入队列")
        try:
            from app.core.celery_app import celery_app
            task_name = "app.tasks.sync.full_sync_task" if sync_type == "full" else "app.tasks.sync.incremental_sync_task"
            celery_app.send_task(task_name, args=[record.id])
        except Exception:
            pass
        return record


@router.post("/full", response_model=SyncRecordResponse)
async def start_full_sync(auth=Depends(get_current_user)):
    """Start a full sync task."""
    async with async_session_factory() as session:
        record = SyncRecord(
            type="full",
            status="running",
            progress=0,
            total_files=0,
            scanned_files=0,
        )
        session.add(record)
        await session.commit()
        from app.services.log_service import log_action
        await log_action(action="start_full_sync", module="sync", detail="全量同步已加入队列")
        # Queue Celery task
        try:
            from app.core.celery_app import celery_app
            celery_app.send_task("app.tasks.sync.full_sync_task", args=[record.id])
        except Exception:
            pass
        return record


@router.post("/incremental", response_model=SyncRecordResponse)
async def start_incremental_sync(auth=Depends(get_current_user)):
    """Start an incremental sync task."""
    async with async_session_factory() as session:
        record = SyncRecord(
            type="incremental",
            status="running",
            progress=0,
            total_files=0,
            scanned_files=0,
        )
        session.add(record)
        await session.commit()
        from app.services.log_service import log_action
        await log_action(action="start_incremental_sync", module="sync", detail="增量同步已加入队列")
        try:
            from app.core.celery_app import celery_app
            celery_app.send_task("app.tasks.sync.incremental_sync_task", args=[record.id])
        except Exception:
            pass
        return record


@router.post("/resume/{record_id}", response_model=SyncRecordResponse)
async def resume_sync(record_id: int, auth=Depends(get_current_user)):
    """Resume an interrupted sync from its checkpoint."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(SyncRecord).where(SyncRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(status_code=404, detail="Sync record not found")
        if not record.can_resume:
            raise HTTPException(status_code=400, detail="This record cannot be resumed")
        record.status = "running"
        await session.commit()
        try:
            from app.core.celery_app import celery_app
            celery_app.send_task(
                "app.tasks.sync.full_sync_task" if record.type == "full" else "app.tasks.sync.incremental_sync_task",
                args=[record.id, record.checkpoint_cid],
            )
        except Exception:
            pass
        return record


# ── Sync Config ─────────────────────────────────────────────────────


async def _get_or_create_sync_config(session):
    result = await session.execute(select(SyncConfig).limit(1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = SyncConfig()
        session.add(cfg)
        await session.commit()
    return cfg


@router.get("/config", response_model=SyncConfigResponse)
async def get_sync_config(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        cfg = await _get_or_create_sync_config(session)
        return cfg


@router.put("/config", response_model=SyncConfigResponse)
async def update_sync_config(data: SyncConfigUpdate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        cfg = await _get_or_create_sync_config(session)
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(cfg, key, val)
        await session.commit()
        return cfg
