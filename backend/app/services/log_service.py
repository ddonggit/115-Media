"""Log service — write operation logs asynchronously."""
import logging

logger = logging.getLogger(__name__)


async def log_action(
    action: str,
    module: str,
    level: str = "info",
    detail: str = "",
    status: str = "success",
    error_message: str | None = None,
) -> None:
    """Write an entry to the operation_log table.

    Args:
        action: Short action name, e.g. "create_subscription", "trigger_sync"
        module: Module name, e.g. "subscription", "sync", "organize"
        level: "debug" | "info" | "warning" | "error"
        detail: Human-readable description
        status: "success" | "failed" | "warning"
        error_message: Optional error details
    """
    from app.core.database import async_session_factory
    from app.models.operation_log import OperationLog

    try:
        async with async_session_factory() as session:
            log = OperationLog(
                action=action,
                module=module,
                level=level,
                detail=detail,
                status=status,
                error_message=error_message,
            )
            session.add(log)
            await session.commit()
        # Broadcast new log entry via WebSocket for real-time log display
        from app.core.websocket import manager as ws_manager
        try:
            await ws_manager.broadcast("log.new", {
                "id": log.id,
                "action": log.action,
                "module": log.module,
                "level": log.level if isinstance(log.level, str) else log.level.value,
                "detail": log.detail,
                "status": log.status if isinstance(log.status, str) else log.status.value,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })
        except Exception:
            pass
    except Exception as e:
        logger.warning("Failed to write operation log: %s", e)
