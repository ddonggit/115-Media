"""Celery tasks — notification dispatch.

Triggers: after sync / organize / transfer events.
"""
import logging
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2)
def send_notification_task(self, event: str, data: dict) -> dict:
    """Dispatch a notification event to all enabled channels."""
    import asyncio

    async def _run():
        from app.services.notify_service import dispatch_notification
        await dispatch_notification(event, data)
        return {"event": event, "dispatched": True}

    return asyncio.run(_run())
