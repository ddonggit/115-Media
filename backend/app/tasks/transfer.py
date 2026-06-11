"""Celery tasks — transfer (submit + 3-layer retry + expiry cleanup)."""
import logging
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from app.core.celery_app import celery_app
from app.core.websocket import manager as ws_manager

logger = logging.getLogger(__name__)

SUBMIT_RETRY_INTERVAL = 600  # 10 minutes
DOWNLOAD_RETRY_INTERVAL = 1800  # 30 minutes
MAX_WAIT_DAYS = 7
MAX_SUBMIT_RETRY = 3
MAX_DOWNLOAD_RETRY = 3


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _extract_match_text(url: str, media_name: str = "") -> str:
    """从 URL 提取可用于匹配115离线任务的文本."""
    # Magnet: 提取 dn= 参数
    m = re.search(r'[?&]dn=([^&]+)', url, re.IGNORECASE)
    if m:
        try: return urllib.parse.unquote(m.group(1))
        except Exception: return m.group(1)
    # ED2K: 提取 |file|...|
    m = re.search(r'ed2k://\|file\|([^|]+)', url, re.IGNORECASE)
    if m: return m.group(1)
    # 115 share
    if '115.com' in url: return media_name
    return media_name or url


async def _path_to_cid(client, path: str) -> str:
    """将路径字符串转为115目录cid."""
    if not path or path == '/':
        return '0'
    # 已经是纯数字cid则直接返回
    if path.strip('/').isdigit():
        return path.strip('/')
    # 查 organize_config 中的已知目录映射
    try:
        from sqlalchemy import select
        from app.core.database import async_session_factory
        from app.models.organize_config import OrganizeConfig
        async with async_session_factory() as session:
            result = await session.execute(select(OrganizeConfig).limit(1))
            cfg = result.scalar_one_or_none()
            known = {}
            if cfg:
                known['云下载'] = cfg.source_cid
                known['重名整理'] = cfg.duplicate_cid
                known['已经整理'] = cfg.processed_cid
    except Exception:
        known = {}
    from p115client import P115FileSystem
    fs = P115FileSystem(client)
    parts = [p for p in path.strip('/').split('/') if p]
    current = '0'
    for part in parts:
        if part in known and current == '0':
            current = known[part]
            continue
        try:
            current = await fs.get_id(f'{current}/{part}', async_=True)
        except Exception:
            try:
                current = await fs.mkdir(part, current, async_=True)
            except Exception:
                pass
    return current


async def _broadcast(event: str, data: dict) -> None:
    """Send a WebSocket event — runs in asyncio context."""
    try:
        await ws_manager.broadcast(event, data)
    except Exception as e:
        logger.warning("WebSocket broadcast failed: %s", e)


async def _notify_transfer(event: str, task_id: int, **kwargs) -> None:
    """Dispatch transfer notification."""
    try:
        from app.services.notify_service import dispatch_notification
        await dispatch_notification(f"transfer_{event}", {"task_id": task_id, **kwargs})
    except Exception as e:
        logger.warning("Failed to dispatch transfer notification: %s", e)


async def _write_error_log(module: str, title: str, detail: str, level: str = "error",
                           can_retry: bool = True, checkpoint: str | None = None) -> None:
    """Write an error log entry for the Dashboard error card."""
    try:
        from app.services.log_service import log_action
        await log_action(action=title, module=module, level=level, detail=detail,
                        status="failed" if level == "error" else "warning")
        from app.models.error_log import ErrorLog
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            err = ErrorLog(
                level=level,
                module=module,
                title=title,
                detail=detail,
                can_retry=can_retry,
                checkpoint=checkpoint,
            )
            session.add(err)
            await session.commit()
    except Exception as e:
        logger.warning("Failed to write error log: %s", e)


@celery_app.task(bind=True, max_retries=3)
def transfer_task(self, task_id: int) -> dict:
    """Submit a transfer to 115 offline download.

    Layer 1: Try offline_add_url, retry on HTTP failure (10 min × 3).
    Handles both magnet: and share_link URLs.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.transfer_task import TransferTask, TransferStatus
    from app.core.p115_wrapper import get_client

    import asyncio

    async def _run():
        logger.info("Transfer task %d: starting submission", task_id)
        await _broadcast("transfer.progress", {"task_id": task_id, "status": "starting"})

        async with async_session_factory() as session:
            result = await session.execute(
                select(TransferTask).where(TransferTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                logger.warning("Transfer task %d not found", task_id)
                return {"status": "failed", "error": "not_found"}

            client = get_client()
            if not client:
                logger.warning("No 115 client available, will retry later")
                task.submit_retry_count = (task.submit_retry_count or 0) + 1
                if task.submit_retry_count >= MAX_SUBMIT_RETRY:
                    task.status = TransferStatus.submit_failed
                    task.error_message = "submit retry exhausted: no 115 client"
                    await _write_error_log("transfer", "转存提交失败", f"Task#{task_id}: {task.error_message}")
                    await _broadcast("transfer.failed", {
                        "task_id": task_id, "reason": "no_client",
                    })
                else:
                    task.next_submit_retry_at = _utcnow() + timedelta(seconds=SUBMIT_RETRY_INTERVAL)
                    await _broadcast("transfer.retry", {
                        "task_id": task_id, "retry_count": task.submit_retry_count,
                        "next_retry_at": task.next_submit_retry_at.isoformat(),
                    })
                await session.commit()
                return {"status": "retry_later"}

            # ── Layer 1: Try submitting to 115 ──────────────────────
            try:
                # Build payload based on transfer type
                payload = {"url": task.url}
                if task.target_dir:
                    payload["wp_path_id"] = await _path_to_cid(client, task.target_dir)

                if task.transfer_type.value == "magnet":
                    response = await client.offline_add_url(payload, async_=True)
                elif task.transfer_type.value == "share_link":
                    from p115client.fs import P115ShareFileSystem
                    fs = P115ShareFileSystem.from_url(client, task.url)
                    target_pid = int(task.target_dir or "0")
                    # Receive the entire shared item (file or folder)
                    await fs.receive(fs.id, target_pid, async_=True)
                    response = {"status": "shared", "ids": [fs.id]}
                else:
                    response = await client.offline_add_url(payload, async_=True)

                # Check response for success
                # Typical success: response has state=2 (completed) or status=200
                resp_state = None
                if isinstance(response, dict):
                    resp_state = response.get("state")
                    if resp_state is None:
                        resp_state = response.get("status")

                if resp_state is not None and resp_state in (-1, 0):
                    # 115 returned failure
                    err_msg = response.get("error", "unknown error")
                    logger.warning("Transfer %d: 115 returned failure state=%s: %s",
                                 task_id, resp_state, err_msg)
                    task.download_retry_count = (task.download_retry_count or 0) + 1
                    if task.download_retry_count >= MAX_DOWNLOAD_RETRY:
                        task.status = TransferStatus.download_failed
                        task.error_message = f"download retry exhausted: {err_msg}"
                        await _write_error_log("transfer", "转存下载失败", f"Task#{task_id}: {task.error_message}")
                        await _broadcast("transfer.failed", {
                            "task_id": task_id, "reason": "download_failed",
                            "error": err_msg,
                        })
                    else:
                        task.next_download_retry_at = _utcnow() + timedelta(seconds=DOWNLOAD_RETRY_INTERVAL)
                        await _broadcast("transfer.retry", {
                            "task_id": task_id, "retry_count": task.download_retry_count,
                            "next_retry_at": task.next_download_retry_at.isoformat(),
                            "layer": 2,
                        })
                    await session.commit()
                    return {"status": "retry_later"}

                # Success
                task.status = TransferStatus.submitted
                task.submitted_at = _utcnow()
                task.expires_at = _utcnow() + timedelta(days=MAX_WAIT_DAYS)
                task.submit_retry_count = 0
                task.download_retry_count = 0
                task.error_message = None

                # Extract size if available
                if isinstance(response, dict):
                    task.size = str(response.get("size", task.size or ""))

                await session.commit()
                await _broadcast("transfer.done", {
                    "task_id": task_id, "status": "submitted",
                    "submitted_at": task.submitted_at.isoformat(),
                })
                await _notify_transfer("done", task_id, status="submitted",
                                      media_name=task.media_name or "")
                logger.info("Transfer task %d: submitted successfully", task_id)
                return {"status": "submitted", "task_id": task_id}

            except Exception as e:
                logger.warning("Transfer %d: submission failed with exception: %s", task_id, e)
                task.submit_retry_count = (task.submit_retry_count or 0) + 1
                if task.submit_retry_count >= MAX_SUBMIT_RETRY:
                    task.status = TransferStatus.submit_failed
                    task.error_message = f"submit retry exhausted: {e}"
                    await _write_error_log("transfer", "转存提交失败", f"Task#{task_id}: {task.error_message}")
                    await _broadcast("transfer.failed", {
                        "task_id": task_id, "reason": "submit_failed",
                        "error": str(e),
                    })
                    await _notify_transfer("failed", task_id, reason="submit_failed",
                                          error=str(e))
                else:
                    task.next_submit_retry_at = _utcnow() + timedelta(seconds=SUBMIT_RETRY_INTERVAL)
                    await _broadcast("transfer.retry", {
                        "task_id": task_id, "retry_count": task.submit_retry_count,
                        "next_retry_at": task.next_submit_retry_at.isoformat(),
                        "layer": 1,
                    })
                await session.commit()
                return {"status": "retry_later"}

    return asyncio.run(_run())


@celery_app.task(bind=True, max_retries=3)
def check_transfer_status(self, task_id: int) -> dict:
    """Layer 2: Check status of submitted transfers and retry if failed.

    Called when next_download_retry_at has passed.
    Queries the 115 offline task list for the current status.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.transfer_task import TransferTask, TransferStatus
    from app.core.p115_wrapper import get_client

    import asyncio

    async def _run():
        async with async_session_factory() as session:
            result = await session.execute(
                select(TransferTask).where(TransferTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task or task.status != TransferStatus.submitted:
                return {"status": "skipped"}

            client = get_client()
            if not client:
                return {"status": "no_client"}

            try:
                # Query 115 offline list for this task
                # offline_iter yields dicts with keys: info_hash, name, status, size, fc_id
                from p115client.tool import offline_iter
                async for t in offline_iter(client, async_=True):
                    name = t.get('name', '')
                    status_val = t.get('status', 0)
                    match_text = _extract_match_text(task.url, task.media_name or "")
                    if match_text in name or (task.media_name and task.media_name in name):
                        if status_val == 2:
                            # Download completed
                            task.status = TransferStatus.done
                            task.progress = 100
                            await session.commit()
                            await _broadcast("transfer.done", {
                                "task_id": task_id, "status": "done",
                            })
                            await _notify_transfer("done", task_id, status="downloaded",
                                                  media_name=task.media_name or "")
                            return {"status": "done"}
                        elif status_val in (-1, 0):
                            # Failed or stopped — Layer 2 retry
                            task.download_retry_count = (task.download_retry_count or 0) + 1
                            if task.download_retry_count >= MAX_DOWNLOAD_RETRY:
                                task.status = TransferStatus.download_failed
                                task.error_message = "download retry exhausted"
                                await _write_error_log("transfer", "转存下载失败", f"Task#{task_id}: {task.error_message}")
                                await session.commit()
                                await _broadcast("transfer.failed", {
                                    "task_id": task_id, "reason": "download_failed",
                                })
                                await _notify_transfer("failed", task_id, reason="download_failed",
                                                      media_name=task.media_name or "")
                                return {"status": "download_failed"}
                            else:
                                # Re-submit the URL
                                try:
                                    payload = {"url": task.url}
                                    if task.target_dir:
                                        payload["wp_path_id"] = await _path_to_cid(client, task.target_dir)
                                    await client.offline_add_url(payload, async_=True)
                                    task.next_download_retry_at = _utcnow() + timedelta(seconds=DOWNLOAD_RETRY_INTERVAL)
                                    await session.commit()
                                    await _broadcast("transfer.retry", {
                                        "task_id": task_id,
                                        "retry_count": task.download_retry_count,
                                        "next_retry_at": task.next_download_retry_at.isoformat(),
                                        "layer": 2,
                                    })
                                    return {"status": "retried"}
                                except Exception:
                                    pass
                        elif isinstance(status_val, int) and 0 < status_val < 100:
                            # Still downloading
                            task.progress = status_val
                            await session.commit()
                            await _broadcast("transfer.progress", {
                                "task_id": task_id, "progress": status_val,
                            })
                            return {"status": "downloading", "progress": status_val}
                        break  # found the task, stop iterating
            except Exception as e:
                logger.warning("check_transfer_status %d: %s", task_id, e)

            return {"status": "not_found"}

    return asyncio.run(_run())


@celery_app.task(bind=True, max_retries=3)
def check_all_transfers(self) -> dict:
    """Batch check all submitted transfers whose retry time has passed.

    Scheduled by Celery beat every 5 minutes. Queries all transfer tasks
    with status=submitted and next_download_retry_at <= now, then delegates
    to check_transfer_status for each.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.transfer_task import TransferTask, TransferStatus

    import asyncio

    async def _run():
        from sqlalchemy import or_

        logger.info("Checking all submitted transfers...")
        async with async_session_factory() as session:
            now = _utcnow()
            stmt = select(TransferTask).where(
                TransferTask.status == TransferStatus.submitted,
                or_(
                    TransferTask.next_download_retry_at <= now,
                    TransferTask.next_download_retry_at.is_(None),
                ),
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()

        if not tasks:
            return {"status": "completed", "checked": 0}

        logger.info("Found %d transfers to check", len(tasks))
        for task in tasks:
            try:
                # Delegate to the existing single-task check
                check_transfer_status.delay(task.id)
            except Exception as e:
                logger.warning("Failed to queue check for transfer %d: %s", task.id, e)

        return {"status": "completed", "checked": len(tasks)}

    return asyncio.run(_run())


@celery_app.task
def cleanup_expired() -> dict:
    """Layer 3: Clean up expired transfer tasks.

    Daily job: finds submitted tasks where expires_at < now,
    flips them to download_failed, and calls offline_clear.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.transfer_task import TransferTask, TransferStatus
    from app.core.p115_wrapper import get_client

    import asyncio

    async def _run():
        logger.info("Checking for expired transfers...")
        async with async_session_factory() as session:
            now = _utcnow()
            stmt = select(TransferTask).where(
                TransferTask.status == TransferStatus.submitted,
                TransferTask.expires_at < now,
            )
            result = await session.execute(stmt)
            count = 0

            client = get_client()

            for task in result.scalars().all():
                logger.info("Cleaning up expired transfer %d (expired at %s)",
                          task.id, task.expires_at)
                task.status = TransferStatus.download_failed
                task.error_message = f"Expired (max_wait_days={MAX_WAIT_DAYS})"
                await _write_error_log("transfer", "转存超时清理", f"Task#{task.id} expired, status→download_failed")
                count += 1

            await session.commit()

            # One-time cleanup of all failed offline tasks in 115 (flag=2)
            # Runs once per cleanup cycle, only if expired tasks were found.
            # NOTE: 115 API offline_clear is a bulk operation — it clears ALL
            # failed tasks, not individual ones. This is acceptable for a daily
            # cleanup job that runs after marking our own tasks as expired.
            if client and count > 0:
                try:
                    await client.offline_clear({"flag": 2}, async_=True)
                except Exception:
                    pass

            logger.info("Cleaned up %d expired transfers", count)
            if count > 0:
                await _broadcast("transfer.cleanup", {"cleaned": count})
            return {"cleaned": count}

    return asyncio.run(_run())
