"""Subscriptions API — CRUD with episode auto-follow logic."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.models.subscription import Subscription
from app.schemas.subscription import (
    MediaType,
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubStatus,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/", response_model=list[SubscriptionResponse])
async def list_subscriptions(
    status: str | None = Query(None),
    media_type: str | None = Query(None),
    auth=Depends(get_current_user),
):
    async with async_session_factory() as session:
        stmt = select(Subscription)
        if status:
            stmt = stmt.where(Subscription.status == status)
        if media_type:
            stmt = stmt.where(Subscription.media_type == media_type)
        stmt = stmt.order_by(Subscription.created_at.desc())
        result = await session.execute(stmt)
        return result.scalars().all()


@router.get("/{sub_id}", response_model=SubscriptionResponse)
async def get_subscription(sub_id: int, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == sub_id))
        sub = result.scalar_one_or_none()
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        return sub


@router.post("/", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(data: SubscriptionCreate, auth=Depends(get_current_user)):
    """Create a subscription with episode auto-follow.
    
    Side-effect: Auto-creates a BT4G RSS source entry for the subscribed media.
    """
    sub_data = data.model_dump()
    # Auto-generate episode_current for tv subscriptions
    if data.media_type == MediaType.tv and data.episode_start is not None:
        sub_data["episode_current"] = data.episode_start - 1
    async with async_session_factory() as session:
        sub = Subscription(**sub_data)
        session.add(sub)
        await session.commit()
        
        # ── Auto-create BT4G RSS source ──────────────────────────────
        import urllib.parse
        from app.models.rss_source import RSSSource
        
        hd_suffix = "%20%E9%AB%98%E6%B8%85" if getattr(data, 'include_hd_keyword', True) else ""
        rss_url = f"https://bt4gprx.com/search?q={urllib.parse.quote(data.media_name)}{hd_suffix}&page=rss"
        
        # Check if source already exists for this name
        existing = await session.execute(
            select(RSSSource).where(RSSSource.name == data.media_name).limit(1)
        )
        if not existing.scalar_one_or_none():
            source = RSSSource(
                name=data.media_name,
                url=rss_url,
                category="tv" if data.media_type == MediaType.tv else "movie",
                provider="bt4g",
                enabled=True,
            )
            session.add(source)
            await session.commit()
        
        # Log
        from app.services.log_service import log_action
        await log_action(
            action="create_subscription",
            module="subscription",
            detail=f"创建订阅: tmdb_id={data.tmdb_id}, {data.media_name}({data.media_type})",
        )
        return sub


@router.put("/{sub_id}", response_model=SubscriptionResponse)
async def update_subscription(sub_id: int, data: SubscriptionUpdate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == sub_id))
        sub = result.scalar_one_or_none()
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(sub, key, val)
        await session.commit()
        return sub


@router.delete("/{sub_id}")
async def delete_subscription(sub_id: int, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(Subscription).where(Subscription.id == sub_id))
        sub = result.scalar_one_or_none()
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found")
        await session.delete(sub)
        await session.commit()
        from app.services.log_service import log_action
        await log_action(
            action="delete_subscription",
            module="subscription",
            detail=f"删除订阅: id={sub_id}, {sub.media_name}",
        )
        return {"message": "deleted"}


@router.get("/stats/count")
async def subscription_count(auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        total = await session.scalar(select(func.count(Subscription.id)))
        active = await session.scalar(
            select(func.count(Subscription.id)).where(Subscription.status == SubStatus.active)
        )
        return {"data": {"total": total, "active": active}}


@router.get("/tmdb/search")
async def tmdb_search_for_subscription(
    q: str = Query(..., min_length=1, description="Search keyword"),
    auth=Depends(get_current_user),
):
    """Search TMDB for media to subscribe to. Returns [{tmdb_id, title, year, media_type, rating}]."""
    from app.core.tmdb_client import search_multi
    data = await search_multi(q, page=1)
    results = data.get("results", [])[:10]
    items = [
        {
            "tmdb_id": r.get("id"),
            "title": r.get("title") or r.get("name", ""),
            "year": (r.get("release_date") or r.get("first_air_date") or "")[:4],
            "media_type": r.get("media_type", ""),
            "rating": r.get("vote_average", 0),
        }
        for r in results
    ]
    return {"data": items}
