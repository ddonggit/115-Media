"""Dashboard API — stats, error cards with resolve/retry."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.models.subscription import Subscription
from app.models.transfer_task import TransferTask
from app.models.media_file import MediaFile
from app.models.error_log import ErrorLog
from app.models.account import Account115
from app.schemas.error_log import ErrorLogResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats(auth=Depends(get_current_user)):
    """Get dashboard statistics."""
    from app.core.p115_wrapper import get_client, validate_client

    # Validate 115 cookie freshness before returning cached space info
    client = get_client()
    cookie_valid = False
    if client:
        cookie_valid = await validate_client(client)

    async with async_session_factory() as session:
        # Subscriptions
        active_subs = await session.scalar(
            select(func.count(Subscription.id)).where(Subscription.status == "active")
        )
        total_subs = await session.scalar(select(func.count(Subscription.id)))

        # Transfers today
        from datetime import datetime, timezone, timedelta
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_transfers = await session.scalar(
            select(func.count(TransferTask.id)).where(TransferTask.created_at >= today_start)
        )

        # Pending organize (unrecognized + unorganized files)
        pending_organize = await session.scalar(
            select(func.count(MediaFile.id)).where(
                MediaFile.organized == False,
                MediaFile.recognized == True,
            )
        )

        # Space usage from account only if cookie is still valid
        account_result = await session.execute(select(Account115).limit(1))
        account = account_result.scalar_one_or_none()
        space_pct = None
        total_space = 0
        used_space = 0
        if cookie_valid and account and account.total_space and account.total_space > 0:
            space_pct = round(account.used_space / account.total_space * 100, 1)
            total_space = account.total_space
            used_space = account.used_space

        # Error count
        error_count = await session.scalar(
            select(func.count(ErrorLog.id)).where(ErrorLog.resolved == False)
        )

        return {
            "data": {
                "active_subscriptions": active_subs or 0,
                "total_subscriptions": total_subs or 0,
                "today_transfers": today_transfers or 0,
                "pending_organize": pending_organize or 0,
                "space_usage_pct": space_pct,
                "total_space": total_space,
                "used_space": used_space,
                "unresolved_errors": error_count or 0,
            }
        }


@router.get("/errors", response_model=list[ErrorLogResponse])
async def get_errors(auth=Depends(get_current_user)):
    """Get unresolved error cards."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(ErrorLog)
            .where(ErrorLog.resolved == False)
            .order_by(ErrorLog.time.desc())
            .limit(20)
        )
        return result.scalars().all()


@router.post("/errors/{error_id}/resolve")
async def resolve_error(error_id: int, auth=Depends(get_current_user)):
    """Mark an error as resolved."""
    async with async_session_factory() as session:
        result = await session.execute(select(ErrorLog).where(ErrorLog.id == error_id))
        err = result.scalar_one_or_none()
        if not err:
            raise HTTPException(status_code=404, detail="Error not found")
        err.resolved = True
        await session.commit()
        return {"message": "resolved"}


@router.post("/errors/{error_id}/retry")
async def retry_error(error_id: int, auth=Depends(get_current_user)):
    """Retry the operation that caused this error."""
    async with async_session_factory() as session:
        result = await session.execute(select(ErrorLog).where(ErrorLog.id == error_id))
        err = result.scalar_one_or_none()
        if not err:
            raise HTTPException(status_code=404, detail="Error not found")
        if not err.can_retry:
            raise HTTPException(status_code=400, detail="This error cannot be retried")
        # Mark resolved, then queue a retry via Celery
        err.resolved = True
        await session.commit()
        
        # Route retry based on module
        module_retry_map = {
            "transfer": ("app.tasks.transfer.transfer_task", {"error_id": error_id}),
            "sync": ("app.tasks.sync.incremental_sync_task", {"checkpoint": err.checkpoint}),
        }
        if err.module in module_retry_map:
            try:
                from app.core.celery_app import celery_app
                task_name, kwargs = module_retry_map[err.module]
                celery_app.send_task(task_name, kwargs=kwargs)
            except Exception:
                pass
        
        return {"message": "retry queued"}
