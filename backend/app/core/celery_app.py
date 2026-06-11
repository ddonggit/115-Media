"""Celery application configuration."""
import os
import asyncio
from celery import Celery
from celery.signals import worker_ready

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "115-media",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.sync",
        "app.tasks.organize",
        "app.tasks.subscribe",
        "app.tasks.transfer",
        "app.tasks.strm",
        "app.tasks.notify",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "check-subscriptions": {
            "task": "app.tasks.subscribe.check_subscriptions",
            "schedule": 600.0,
        },
        "check-all-transfers": {
            "task": "app.tasks.transfer.check_all_transfers",
            "schedule": 300.0,
        },
        "cleanup-expired-transfers": {
            "task": "app.tasks.transfer.cleanup_expired",
            "schedule": 86400.0,
        },
        "incremental-sync": {
            "task": "app.tasks.sync.incremental_sync_task",
            "schedule": 1800.0,
        },
        "auto-organize": {
            "task": "app.tasks.organize.organize_task",
            "schedule": 1800.0,
        },
    },
)


@worker_ready.connect
def on_worker_ready(**kwargs):
    """Initialize 115 client from DB when worker starts."""
    from app.core.p115_wrapper import init_client_from_db
    try:
        asyncio.run(init_client_from_db())
    except Exception as e:
        print(f"Worker init: Failed to init 115 client: {e}")
