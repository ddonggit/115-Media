"""Notify API — CRUD for notification channels (feishu/telegram)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.models.notify_config import NotifyConfig
from app.schemas.notify_config import NotifyConfigCreate, NotifyConfigUpdate, NotifyConfigResponse

router = APIRouter(prefix="/notify", tags=["notify"])


@router.get("/", response_model=list[NotifyConfigResponse])
async def list_notify(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(NotifyConfig))
        return result.scalars().all()


@router.post("/", response_model=NotifyConfigResponse)
async def create_notify(data: NotifyConfigCreate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        config = NotifyConfig(**data.model_dump())
        session.add(config)
        await session.commit()
        return config


@router.put("/{config_id}", response_model=NotifyConfigResponse)
async def update_notify(config_id: int, data: NotifyConfigUpdate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(NotifyConfig).where(NotifyConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Notify config not found")
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(config, key, val)
        await session.commit()
        return config


@router.post("/test")
async def test_notification(auth=Depends(get_current_user)):
    """Send a test notification to verify configuration."""
    from app.services.notify_service import send_feishu, send_telegram
    from app.models.notify_config import NotifyConfig
    
    async with async_session_factory() as session:
        result = await session.execute(
            select(NotifyConfig).where(NotifyConfig.enabled == True)
        )
        configs = result.scalars().all()
    
    if not configs:
        raise HTTPException(status_code=400, detail="No enabled notify config found")
    
    sent = 0
    for cfg in configs:
        try:
            if cfg.channel.value == "feishu":
                ok = await send_feishu(cfg.webhook_url, "115-Media: 测试", "这是一条测试消息 ✅")
            elif cfg.channel.value == "telegram" and cfg.bot_token and cfg.chat_id:
                ok = await send_telegram(cfg.bot_token, cfg.chat_id, "*115-Media: 测试*\n这是一条测试消息 ✅")
            else:
                continue
            if ok:
                sent += 1
        except Exception:
            continue
    
    if sent == 0:
        raise HTTPException(status_code=500, detail="All notification attempts failed")
    return {"message": f"Test notification sent to {sent} channel(s)"}


@router.delete("/{config_id}")
async def delete_notify(config_id: int, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(NotifyConfig).where(NotifyConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise HTTPException(status_code=404, detail="Notify config not found")
        await session.delete(config)
        await session.commit()
        return {"message": "deleted"}
