"""Notification service — send messages via Feishu / Telegram.

Functions are async, callable from both API routes and Celery tasks.
"""
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


async def send_feishu(webhook_url: str, title: str, content: str) -> bool:
    """Send a message card to a Feishu webhook.

    Returns True on success, False on failure.
    """
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": title}},
            "elements": [
                {"tag": "markdown", "content": content},
            ],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") != 0:
                logger.warning("Feishu responded with error code: %s", result.get("msg"))
                return False
            return True
    except Exception as e:
        logger.warning("Failed to send Feishu notification: %s", e)
        return False


async def send_telegram(bot_token: str, chat_id: str, text: str) -> bool:
    """Send a text message via Telegram Bot API.

    Returns True on success, False on failure.
    """
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            if not result.get("ok"):
                logger.warning("Telegram responded with error: %s", result.get("description"))
                return False
            return True
    except Exception as e:
        logger.warning("Failed to send Telegram notification: %s", e)
        return False


async def dispatch_notification(event: str, data: dict[str, Any]) -> None:
    """Dispatch a notification event to all enabled notify configs.

    Reads NotifyConfig from DB, filters by notify_on list, and sends
    via the appropriate channel.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.notify_config import NotifyConfig

    async with async_session_factory() as session:
        result = await session.execute(
            select(NotifyConfig).where(NotifyConfig.enabled == True)
        )
        configs = result.scalars().all()

    for cfg in configs:
        if cfg.notify_on and event not in cfg.notify_on:
            continue

        # Build a readable message from the event data
        title = f"115-Media: {event}"
        text_lines = [f"*{title}*"]
        for key, val in data.items():
            text_lines.append(f"• {key}: {val}")
        text = "\n".join(text_lines)
        content = "  \n".join(f"**{k}**: {v}" for k, v in data.items())

        try:
            if cfg.channel.value == "feishu":
                await send_feishu(cfg.webhook_url, title, content)
            elif cfg.channel.value == "telegram":
                if cfg.bot_token and cfg.chat_id:
                    await send_telegram(cfg.bot_token, cfg.chat_id, text)
        except Exception as e:
            logger.warning("Notification dispatch failed for config %d: %s", cfg.id, e)
