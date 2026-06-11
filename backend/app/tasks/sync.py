"""Celery tasks — sync (full + incremental + checkpoint resume).

Uses p115client SDK tools for 115 file iteration:
- iter_files_with_path_skim: fast full directory walk (5000+ files/sec)
- iter_files: incremental cid-based diff
- export_dir_parse_iter: fallback for very large directories (1M+ files)
"""
import logging
from datetime import datetime, timezone
from app.core.celery_app import celery_app
from app.core.websocket import manager as ws_manager

logger = logging.getLogger(__name__)

SYNC_CHUNK_SIZE = 100  # DB batch insert/update chunk size


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _broadcast(event: str, data: dict) -> None:
    try:
        await ws_manager.broadcast(event, data)
    except Exception as e:
        logger.warning("WebSocket broadcast failed: %s", e)


async def _notify_sync_done(sync_type: str, data: dict) -> None:
    """Dispatch sync completion notification."""
    try:
        from app.services.notify_service import dispatch_notification
        await dispatch_notification("sync_done", {"type": sync_type, **data})
    except Exception as e:
        logger.warning("Failed to dispatch sync notification: %s", e)


def _calc_progress(scanned: int, total: int) -> int:
    if total <= 0:
        return 0
    return min(100, int(scanned * 100 / total))


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def full_sync_task(self, record_id: int, checkpoint_cid: str | None = None) -> dict:
    """Full sync of 115 cloud files into MediaFile table.

    Uses iter_files_with_path_skim for fast full directory traversal.
    Saves checkpoint_cid on interruption for resume.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.sync_record import SyncRecord
    from app.models.media_file import MediaFile
    from app.core.p115_wrapper import get_client
    from p115client.tool import iter_files_with_path_skim

    import asyncio

    async def _run():
        logger.info("Full sync started: record_id=%s, checkpoint=%s",
                   record_id, checkpoint_cid)

        client = get_client()
        if not client:
            logger.error("Full sync: No 115 client available")
            return {"status": "failed", "error": "No client"}

        await _broadcast("sync.start", {"type": "full", "record_id": record_id})

        # Determine root CID: either from OrganizeConfig or default "0"
        root_cid = checkpoint_cid or "0"

        try:
            scanned = 0
            total_estimate = 0
            batch: list[dict] = []

            async for item in iter_files_with_path_skim(client, root_cid, async_=True):
                # item is typically a tuple or dict — normalize
                if isinstance(item, dict):
                    cid = str(item.get("id") or item.get("cid", ""))
                    name = item.get("name", "")
                    path = item.get("path", "")
                    is_dir = item.get("is_dir", False) or item.get("isDirectory", False) or item.get("folder", False)
                    size = item.get("size", 0)
                    create_time = item.get("create_time") or item.get("createTime")
                elif isinstance(item, (list, tuple)):
                    # Tuple format: (cid, name, path, is_dir, size, create_time)
                    cid = str(item[0]) if len(item) > 0 else ""
                    name = str(item[1]) if len(item) > 1 else ""
                    path = str(item[2]) if len(item) > 2 else ""
                    is_dir = bool(item[3]) if len(item) > 3 else False
                    size = int(item[4]) if len(item) > 4 else 0
                    create_time = str(item[5]) if len(item) > 5 else None
                else:
                    continue

                scanned += 1

                batch.append({
                    "cid": cid,
                    "file_name": name,
                    "file_path": path,
                    "file_size": size,
                    "media_type": "unknown",
                    "recognized": False,
                    "organized": False,
                    "create_time": create_time,
                })

                # Batch insert and broadcast progress every chunk
                if len(batch) >= SYNC_CHUNK_SIZE:
                    await _flush_batch(batch, record_id)
                    progress = _calc_progress(scanned, total_estimate or scanned)
                    await _broadcast("sync.progress", {
                        "type": "full", "record_id": record_id,
                        "progress": progress, "scanned": scanned,
                    })
                    batch = []

            # Flush remaining
            if batch:
                await _flush_batch(batch, record_id)

            # Mark sync as completed
            async with async_session_factory() as session:
                result = await session.execute(
                    select(SyncRecord).where(SyncRecord.id == record_id)
                )
                record = result.scalar_one_or_none()
                if record:
                    record.status = "completed"
                    record.progress = 100
                    record.scanned_files = scanned
                    record.total_files = scanned
                    record.finished_at = _utcnow()
                    record.can_resume = False
                    await session.commit()

            await _broadcast("sync.done", {
                "type": "full", "record_id": record_id,
                "scanned": scanned,
            })
            await _notify_sync_done("full", {"record_id": record_id, "scanned": scanned})
            logger.info("Full sync completed: %d files scanned", scanned)
            return {"status": "completed", "files": scanned}

        except asyncio.CancelledError:
            logger.warning("Full sync interrupted: record_id=%s", record_id)
            await _save_checkpoint(record_id, root_cid, scanned)
            await _log_sync_error(record_id, "同步中断", f"全量同步在 cid={root_cid} 处中断", can_retry=True, checkpoint=root_cid)
            return {"status": "interrupted"}

        except Exception as e:
            logger.error("Full sync failed: %s", e)
            await _save_checkpoint(record_id, root_cid, scanned)
            await _log_sync_error(record_id, "同步失败", f"全量同步错误: {e}", can_retry=True, checkpoint=root_cid)
            return {"status": "failed", "error": str(e)}

    return asyncio.run(_run())


async def _flush_batch(batch: list[dict], record_id: int) -> None:
    """Batch upsert MediaFile records — pre-fetch existing cids to avoid N+1 queries."""
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.media_file import MediaFile

    async with async_session_factory() as session:
        # Pre-fetch all existing cids in this batch to avoid per-item SELECT
        batch_cids = [item["cid"] for item in batch]
        existing_result = await session.execute(
            select(MediaFile).where(MediaFile.cid.in_(batch_cids))
        )
        existing_map: dict[str, MediaFile] = {
            mf.cid: mf for mf in existing_result.scalars().all()
        }

        for item in batch:
            cid = item["cid"]
            if cid in existing_map:
                mf = existing_map[cid]
                mf.file_name = item["file_name"]
                mf.file_path = item["file_path"]
                mf.file_size = item["file_size"]
            else:
                mf = MediaFile(
                    cid=cid,
                    file_name=item["file_name"],
                    file_path=item["file_path"],
                    file_size=item["file_size"],
                    media_type=item["media_type"],
                    recognized=item["recognized"],
                    organized=item["organized"],
                )
                session.add(mf)
        await session.commit()


async def _save_checkpoint(record_id: int, cid: str, scanned: int) -> None:
    """Save a checkpoint for resume on interruption."""
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.sync_record import SyncRecord

    async with async_session_factory() as session:
        result = await session.execute(
            select(SyncRecord).where(SyncRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.status = "interrupted"
            record.checkpoint_cid = cid
            record.scanned_files = scanned
            record.can_resume = True
            record.finished_at = _utcnow()
            await session.commit()


async def _log_sync_error(record_id: int, title: str, detail: str,
                          can_retry: bool = True, checkpoint: str | None = None) -> None:
    """Write an ErrorLog entry for sync interruptions."""
    try:
        from app.models.error_log import ErrorLog
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            err = ErrorLog(
                level="error",
                module="sync",
                title=title,
                detail=detail,
                can_retry=can_retry,
                checkpoint=checkpoint,
            )
            session.add(err)
            await session.commit()
    except Exception as e:
        logger.warning("Failed to write sync error log: %s", e)


@celery_app.task(bind=True, max_retries=3)
def incremental_sync_task(self, record_id: int, checkpoint_cid: str | None = None) -> dict:
    """Incremental sync using cid-based diff against local MediaFile table.

    Uses iter_files with cooldown=0.5 for rate-limited iteration.
    Compares cid+file_name+file_size against DB:
    - New cid → INSERT
    - Same cid, same fields → skip
    - Same cid, changed fields → UPDATE
    - Cid in DB but not in 115 → mark deleted (or soft-delete)
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.sync_record import SyncRecord
    from app.models.media_file import MediaFile
    from app.core.p115_wrapper import get_client
    from p115client.tool import iter_files

    import asyncio

    async def _run():
        logger.info("Incremental sync started: record_id=%s", record_id)

        client = get_client()
        if not client:
            logger.error("Incremental sync: No 115 client available")
            return {"status": "failed", "error": "No client"}

        await _broadcast("sync.start", {"type": "incremental", "record_id": record_id})

        root_cid = checkpoint_cid or "0"

        # Build a set of known cids from DB for diff
        async with async_session_factory() as session:
            db_result = await session.execute(select(MediaFile.cid, MediaFile.file_name, MediaFile.file_size))
            known_files: dict[str, tuple[str, int]] = {
                row.cid: (row.file_name, row.file_size)
                for row in db_result.all()
            }

        try:
            scanned = 0
            added = 0
            updated = 0
            seen_cids: set[str] = set()
            pending_new: list[dict] = []
            pending_update: list[tuple[str, str, int]] = []  # (cid, name, size)

            async for item in iter_files(client, root_cid, cooldown=0.5, async_=True):
                # Unpack item
                if isinstance(item, dict):
                    cid = str(item.get("id") or item.get("cid", ""))
                    name = item.get("name", "")
                    size = int(item.get("size", 0))
                    is_dir = item.get("is_dir", False) or item.get("folder", False)
                elif isinstance(item, (list, tuple)):
                    cid = str(item[0]) if len(item) > 0 else ""
                    name = str(item[1]) if len(item) > 1 else ""
                    size = int(item[4]) if len(item) > 4 else 0
                    is_dir = bool(item[3]) if len(item) > 3 else False
                else:
                    continue

                if not cid:
                    continue

                scanned += 1
                seen_cids.add(cid)

                if cid not in known_files:
                    # New file — batch
                    added += 1
                    pending_new.append({
                        "cid": cid,
                        "file_name": name,
                        "file_path": "",
                        "file_size": size,
                        "media_type": "unknown",
                        "recognized": False,
                        "organized": False,
                    })
                else:
                    # Check if changed
                    old_name, old_size = known_files[cid]
                    if old_name != name or old_size != size:
                        updated += 1
                        pending_update.append((cid, name, size))

                # Broadcast progress every 100 items
                if scanned % 100 == 0:
                    await _broadcast("sync.progress", {
                        "type": "incremental",
                        "record_id": record_id,
                        "scanned": scanned,
                        "added": added,
                        "updated": updated,
                    })

            # Mark files in DB but not in 115 as "removed" (soft-delete)
            removed_cids: list[str] = []
            for cid in known_files:
                if cid not in seen_cids:
                    removed_cids.append(cid)
            removed = len(removed_cids)

            # Flush all pending changes in a single session
            async with async_session_factory() as session:
                # Insert new files
                for item in pending_new:
                    session.add(MediaFile(**item))
                # Update changed files
                for cid, name, size in pending_update:
                    stmt = select(MediaFile).where(MediaFile.cid == cid)
                    result = await session.execute(stmt)
                    mf = result.scalar_one_or_none()
                    if mf:
                        mf.file_name = name
                        mf.file_size = size
                # Mark removed files
                for cid in removed_cids:
                    stmt = select(MediaFile).where(MediaFile.cid == cid)
                    result = await session.execute(stmt)
                    mf = result.scalar_one_or_none()
                    if mf:
                        mf.file_path = "__removed__"

                # Update sync record in same session
                rec_result = await session.execute(
                    select(SyncRecord).where(SyncRecord.id == record_id)
                )
                record = rec_result.scalar_one_or_none()
                if record:
                    record.status = "completed"
                    record.progress = 100
                    record.scanned_files = scanned
                    record.total_files = len(known_files) + added
                    record.finished_at = _utcnow()
                    record.can_resume = False
                    record.checkpoint_cid = None

                await session.commit()

            await _broadcast("sync.done", {
                "type": "incremental",
                "record_id": record_id,
                "scanned": scanned,
                "added": added,
                "updated": updated,
                "removed": removed,
            })
            await _notify_sync_done("incremental", {
                "record_id": record_id, "scanned": scanned,
                "added": added, "updated": updated, "removed": removed,
            })

            logger.info("Incremental sync done: scanned=%d, added=%d, updated=%d, removed=%d",
                       scanned, added, updated, removed)
            return {"status": "completed", "scanned": scanned, "added": added,
                    "updated": updated, "removed": removed}

        except Exception as e:
            logger.error("Incremental sync failed: %s", e)
            await _log_sync_error(record_id, "增量同步失败", f"增量同步错误: {e}", can_retry=True)
            return {"status": "failed", "error": str(e)}

    return asyncio.run(_run())
