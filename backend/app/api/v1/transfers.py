"""Transfers API — CRUD with 3-layer retry mechanism."""
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.models.transfer_task import TransferTask, TransferStatus
from app.schemas.transfer_task import (
    TransferTaskCreate,
    TransferTaskUpdate,
    TransferTaskResponse,
)

router = APIRouter(prefix="/transfers", tags=["transfers"])

# Default retry config
SUBMIT_RETRY_INTERVAL = 600  # 10 minutes
MAX_WAIT_DAYS = 7


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/", response_model=list[TransferTaskResponse])
async def list_transfers(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    auth=Depends(get_current_user),
):
    async with async_session_factory() as session:
        stmt = select(TransferTask)
        if status:
            stmt = stmt.where(TransferTask.status == status)
        stmt = stmt.order_by(TransferTask.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


@router.post("/", response_model=TransferTaskResponse, status_code=201)
async def create_transfer(data: TransferTaskCreate, auth=Depends(get_current_user)):
    """Create a transfer task and attempt submission."""
    async with async_session_factory() as session:
        task = TransferTask(
            transfer_type=data.transfer_type,
            url=data.url,
            target_dir=data.target_dir,
            auto_organize=data.auto_organize,
            media_name=data.media_name,
            tmdb_id=data.tmdb_id,
            size=data.size,
            status=TransferStatus.submitted,
            max_submit_retry=3,
            max_download_retry=3,
        )
        session.add(task)
        await session.commit()
        # Log
        from app.services.log_service import log_action
        await log_action(
            action="create_transfer",
            module="transfer",
            detail=f"创建转存: url={data.url[:60]}..., target={data.target_dir}",
        )
        # Queue Celery task for async submission
        try:
            from app.core.celery_app import celery_app
            celery_app.send_task("app.tasks.transfer.transfer_task", args=[task.id])
        except Exception:
            pass
        return task


@router.get("/{task_id}", response_model=TransferTaskResponse)
async def get_transfer(task_id: int, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(TransferTask).where(TransferTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Transfer task not found")
        return task


@router.post("/{task_id}/retry")
async def retry_transfer(task_id: int, auth=Depends(get_current_user)):
    """Retry a failed transfer (Layer 2: download retry)."""
    async with async_session_factory() as session:
        result = await session.execute(select(TransferTask).where(TransferTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Transfer task not found")
        if task.status not in (TransferStatus.submit_failed, TransferStatus.download_failed):
            raise HTTPException(status_code=400, detail="Task is not in a retryable state")
        # Reset retry state
        task.status = TransferStatus.submitted
        task.download_retry_count = 0
        task.error_message = None
        await session.commit()
        # Queue Celery retry
        try:
            from app.core.celery_app import celery_app
            celery_app.send_task("app.tasks.transfer.transfer_task", args=[task.id])
        except Exception:
            pass
        return task


@router.post("/cleanup")
async def cleanup_expired(auth=Depends(get_current_user)):
    """Manually trigger cleanup of expired transfers (Layer 3)."""
    async with async_session_factory() as session:
        now = _utcnow()
        stmt = select(TransferTask).where(
            TransferTask.status == TransferStatus.submitted,
            TransferTask.expires_at < now,
        )
        result = await session.execute(stmt)
        count = 0
        for task in result.scalars().all():
            task.status = TransferStatus.download_failed
            task.error_message = f"Expired after max_wait_days={MAX_WAIT_DAYS}"
            count += 1
        await session.commit()
        return {"message": f"cleaned up {count} expired tasks"}


@router.get("/errors")
async def get_transfer_errors(auth=Depends(get_current_user)):
    """Get failed transfers with error info for Dashboard error card."""
    async with async_session_factory() as session:
        stmt = (
            select(TransferTask)
            .where(
                TransferTask.status.in_([TransferStatus.submit_failed, TransferStatus.download_failed])
            )
            .order_by(TransferTask.created_at.desc())
            .limit(50)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        items = [
            {
                "id": t.id,
                "media_name": t.media_name,
                "url": t.url[:80] if t.url else None,
                "status": t.status,
                "error_message": t.error_message,
                "download_retry_count": t.download_retry_count,
                "max_download_retry": t.max_download_retry,
                "submit_retry_count": t.submit_retry_count,
                "max_submit_retry": t.max_submit_retry,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]
        return {"data": items}


@router.delete("/{task_id}")
async def delete_transfer(task_id: int, auth=Depends(get_current_user)):
    """Delete a transfer task."""
    async with async_session_factory() as session:
        result = await session.execute(select(TransferTask).where(TransferTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail="Transfer task not found")
        await session.delete(task)
        await session.commit()
        return {"message": "deleted"}


class ResolveUrlRequest(BaseModel):
    url: str = Field(..., min_length=1)


@router.post("/resolve-url")
async def resolve_url(data: ResolveUrlRequest, auth=Depends(get_current_user)):
    """Resolve a 115 share link to get the file name without receiving."""
    from app.core.p115_wrapper import get_client
    from p115client.fs import P115ShareFileSystem

    url = data.url.strip()

    # Magnet — extract dn= parameter
    m = re.search(r'[?&]dn=([^&]+)', url, re.IGNORECASE)
    if m:
        try:
            name = re.sub(r'\.[^.]+$', '', urllib.parse.unquote(m.group(1)))
        except Exception:
            name = re.sub(r'\.[^.]+$', '', m.group(1))
        return {"data": {"media_name": name, "url_type": "magnet"}}

    # ED2K — extract |file|...|
    m = re.search(r'ed2k://\|file\|([^|]+)\|', url, re.IGNORECASE)
    if m:
        name = re.sub(r'\.[^.]+$', '', m.group(1))
        return {"data": {"media_name": name, "url_type": "ed2k"}}

    # 115 share link
    parsed = urllib.parse.urlparse(url)
    if not parsed.hostname or '115' not in parsed.hostname.lower():
        return {"data": {"media_name": None, "url_type": "unknown"}}

    client = get_client()
    if not client:
        raise HTTPException(status_code=400, detail="115 账号未登录")

    try:
        fs = P115ShareFileSystem.from_url(client, url)
        share_data = await fs.get_share_data(async_=True, timeout=10)
        if isinstance(share_data, dict):
            info = share_data.get("shareinfo", {})
            name = info.get("share_title", "")
            files = share_data.get("list", [])
            return {"data": {
                "media_name": name,
                "url_type": "share",
                "file_count": len(files),
            }}
        return {"data": {"media_name": None, "url_type": "share"}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"解析分享链接失败: {e}")
