"""Config API — CRUD for 115, TMDB, STRM, transfer, subscription settings."""
import asyncio
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.core.p115_wrapper import encrypt_cookie, decrypt_cookie, create_client_from_cookie, get_user_info, set_client
from app.models.account import Account115
from app.models.tmdb_config import TmdbConfig
from app.models.strm_config import StrmConfig
from app.models.transfer_config import TransferConfig
from app.models.subscription_config import SubscriptionConfig
from app.schemas.account import Account115Create, Account115Response
from app.schemas.tmdb_config import TmdbConfigCreate, TmdbConfigUpdate, TmdbConfigResponse
from app.schemas.strm_config import StrmConfigCreate, StrmConfigResponse
from app.schemas.transfer_config import TransferConfigUpdate, TransferConfigResponse
from app.schemas.subscription_config import SubscriptionConfigUpdate, SubscriptionConfigResponse

router = APIRouter(prefix="/config", tags=["config"])


# ── 115 Account ────────────────────────────────────────────────────


@router.get("/115", response_model=Account115Response | None)
async def get_115_config(auth=Depends(get_current_user)):
    """Get the 115 account config (cookie hidden)."""
    async with async_session_factory() as session:
        result = await session.execute(select(Account115).limit(1))
        account = result.scalar_one_or_none()
        return account


@router.post("/115", response_model=Account115Response)
@router.put("/115", response_model=Account115Response)
async def save_115_config(data: Account115Create, auth=Depends(get_current_user)):
    """Save/update 115 account with encrypted cookie."""
    encrypted_cookie = encrypt_cookie(data.cookie)
    async with async_session_factory() as session:
        result = await session.execute(select(Account115).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            existing.cookie = encrypted_cookie
            existing.uid = data.uid
            existing.username = data.username
        else:
            account = Account115(
                cookie=encrypted_cookie,
                uid=data.uid,
                username=data.username,
            )
            session.add(account)
        await session.commit()
        saved = existing or account
    # Fire-and-forget: try to init the 115 client in background
    from app.services.log_service import log_action
    asyncio.create_task(_try_init_115_client(data.cookie, data.uid))
    await log_action(action="save_115_config", module="config", detail=f"保存 115 配置: uid={data.uid}")
    return saved


async def _try_init_115_client(cookie: str, uid: str | None) -> None:
    """Background task: validate cookie and init global client. Does not raise."""
    try:
        client = await asyncio.wait_for(
            create_client_from_cookie(cookie), timeout=10.0
        )
        info = await get_user_info(client)
        set_client(client, uid or info.get("uid"))
    except Exception:
        pass


# ── 115 Verify ──────────────────────────────────────────────────────


class VerifyCookieRequest(BaseModel):
    cookie: str = Field(..., min_length=1, description="115 cookie to verify")


@router.post("/115/verify")
async def verify_115_cookie(body: VerifyCookieRequest, auth=Depends(get_current_user)):
    """Verify a 115 cookie by testing it against the API. Returns account info on success."""
    try:
        client = await asyncio.wait_for(
            create_client_from_cookie(body.cookie), timeout=10.0
        )
        info = await get_user_info(client)
        return {
            "valid": True,
            "uid": str(info.get("uid", "")),
            "username": info.get("user_name", ""),
            "total_space": info.get("total_space", 0),
            "used_space": info.get("used_space", 0),
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="115 服务超时，请检查网络后重试")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── TMDB Config ────────────────────────────────────────────────────


@router.get("/tmdb", response_model=TmdbConfigResponse | None)
async def get_tmdb_config(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(TmdbConfig).limit(1))
        return result.scalar_one_or_none()


@router.post("/tmdb", response_model=TmdbConfigResponse)
@router.put("/tmdb", response_model=TmdbConfigResponse)
async def save_tmdb_config(data: TmdbConfigCreate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(TmdbConfig).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            for field in ("api_key", "language", "base_url", "image_base_url"):
                val = getattr(data, field, None)
                if val is not None:
                    setattr(existing, field, val)
        else:
            config = TmdbConfig(**data.model_dump())
            session.add(config)
        await session.commit()
    # Reset the in-memory TMDB API key cache so new key takes effect
    from app.core.tmdb_client import reset_api_key_cache
    reset_api_key_cache()
    return existing or config


# ── TMDB Config (partial update) ────────────────────────────────────


@router.patch("/tmdb", response_model=TmdbConfigResponse)
async def patch_tmdb_config(data: TmdbConfigUpdate, auth=Depends(get_current_user)):
    """Partial update: only update provided fields. Creates config if not exists (upsert)."""
    async with async_session_factory() as session:
        try:
            result = await session.execute(select(TmdbConfig).limit(1))
            existing = result.scalar_one_or_none()
            if not existing:
                # Upsert: create with defaults, then apply provided fields
                existing = TmdbConfig(api_key="", language="zh-CN")
                session.add(existing)
            for field in ("api_key", "language", "base_url", "image_base_url"):
                val = getattr(data, field, None)
                if val is not None:
                    setattr(existing, field, val)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    if data.api_key is not None:
        from app.core.tmdb_client import reset_api_key_cache
        reset_api_key_cache()
    return existing


# ── STRM Config ────────────────────────────────────────────────────


@router.get("/strm", response_model=StrmConfigResponse | None)
async def get_strm_config(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(StrmConfig).limit(1))
        return result.scalar_one_or_none()


@router.post("/strm", response_model=StrmConfigResponse)
@router.put("/strm", response_model=StrmConfigResponse)
async def save_strm_config(data: StrmConfigCreate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(StrmConfig).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            for field in ("strm_base_url", "media_library_path", "auto_generate"):
                val = getattr(data, field, None)
                if val is not None:
                    setattr(existing, field, val)
        else:
            config = StrmConfig(**data.model_dump())
            session.add(config)
        await session.commit()
        return existing or config


# ── Transfer Config ─────────────────────────────────────────────────


async def _get_or_create_transfer_config(session):
    """Helper: get first TransferConfig row or create with defaults."""
    result = await session.execute(select(TransferConfig).limit(1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = TransferConfig()
        session.add(cfg)
        await session.commit()
    return cfg


@router.get("/transfer", response_model=TransferConfigResponse)
async def get_transfer_config(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        cfg = await _get_or_create_transfer_config(session)
        return cfg


@router.put("/transfer", response_model=TransferConfigResponse)
async def update_transfer_config(data: TransferConfigUpdate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        cfg = await _get_or_create_transfer_config(session)
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(cfg, key, val)
        await session.commit()
        return cfg


# ── Subscription Config ──────────────────────────────────────────────


async def _apply_subscription_beat_interval(minutes: int) -> None:
    """Update the Celery beat schedule for subscription checking."""
    try:
        from app.core.celery_app import celery_app
        celery_app.conf.beat_schedule["check-subscriptions"]["schedule"] = minutes * 60.0
    except Exception:
        pass


async def _get_or_create_subscription_config(session):
    result = await session.execute(select(SubscriptionConfig).limit(1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = SubscriptionConfig()
        session.add(cfg)
        await session.commit()
    return cfg


@router.get("/subscription", response_model=SubscriptionConfigResponse)
async def get_subscription_config(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        cfg = await _get_or_create_subscription_config(session)
        return cfg


@router.put("/subscription", response_model=SubscriptionConfigResponse)
async def update_subscription_config(data: SubscriptionConfigUpdate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        cfg = await _get_or_create_subscription_config(session)
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(cfg, key, val)
        await session.commit()
    # Apply to Celery beat schedule dynamically
    if cfg.rss_check_interval_minutes:
        await _apply_subscription_beat_interval(cfg.rss_check_interval_minutes)
    return cfg


# ── 115 Renew ────────────────────────────────────────────────────────


@router.post("/115/renew")
async def renew_115_cookie(auth=Depends(get_current_user)):
    """Attempt to renew/refresh the 115 cookie."""
    async with async_session_factory() as session:
        result = await session.execute(select(Account115).limit(1))
        account = result.scalar_one_or_none()
        if not account or not account.cookie:
            raise HTTPException(status_code=400, detail="No 115 account configured")
        try:
            from app.core.p115_wrapper import get_client
            client = get_client()
            if not client:
                # Try re-initializing from stored encrypted cookie
                raw = decrypt_cookie(account.cookie)
                client = await create_client_from_cookie(raw)
                set_client(client, account.uid)
            # Force cookie refresh by calling a read-only API
            info = await get_user_info(client)
            return {"message": "Cookie renewed", "uid": info.get("uid")}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to renew: {e}")


# ── STRM Generate ────────────────────────────────────────────────────


@router.post("/strm/generate")
async def trigger_strm_generate(auth=Depends(get_current_user)):
    """Manually trigger STRM file generation."""
    try:
        from app.core.celery_app import celery_app
        celery_app.send_task("app.tasks.strm.generate_strm_task")
    except Exception:
        pass
    from app.services.log_service import log_action
    await log_action(action="strm_generate", module="config", detail="STRM 生成已加入队列")
    return {"message": "STRM generation task queued"}
