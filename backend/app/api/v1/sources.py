"""RSS Sources API — CRUD with import/export."""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.models.rss_source import RSSSource
from app.schemas.rss_source import RSSSourceCreate, RSSSourceUpdate, RSSSourceResponse

router = APIRouter(tags=["sources"])


@router.get("/", response_model=list[RSSSourceResponse])
async def list_sources(enabled: bool | None = Query(None), auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        stmt = select(RSSSource)
        if enabled is not None:
            stmt = stmt.where(RSSSource.enabled == enabled)
        stmt = stmt.order_by(RSSSource.created_at.desc())
        result = await session.execute(stmt)
        return result.scalars().all()


@router.post("/", response_model=RSSSourceResponse, status_code=201)
async def create_source(data: RSSSourceCreate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        source = RSSSource(**data.model_dump())
        session.add(source)
        await session.commit()
        return source


@router.put("/{source_id}", response_model=RSSSourceResponse)
async def update_source(source_id: int, data: RSSSourceUpdate, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(RSSSource).where(RSSSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(source, key, val)
        await session.commit()
        return source


@router.delete("/{source_id}")
async def delete_source(source_id: int, auth=Depends(get_current_user)):
    async with async_session_factory() as session:
        result = await session.execute(select(RSSSource).where(RSSSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        await session.delete(source)
        await session.commit()
        return {"message": "deleted"}


@router.get("/export")
async def export_sources(auth=Depends(get_current_user)):
    """Export all sources as JSON."""
    async with async_session_factory() as session:
        result = await session.execute(select(RSSSource))
        sources = result.scalars().all()
        data = [
            {
                "name": s.name,
                "url": s.url,
                "category": s.category,
                "provider": s.provider,
                "enabled": s.enabled,
                "season": s.season,
                "include_keywords": s.include_keywords,
                "exclude_keywords": s.exclude_keywords,
            }
            for s in sources
        ]
        return Response(
            content=json.dumps(data, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=sources.json"},
        )


@router.post("/import")
async def import_sources(data: list[RSSSourceCreate], auth=Depends(get_current_user)):
    """Import sources from JSON array."""
    async with async_session_factory() as session:
        count = 0
        for item in data:
            source = RSSSource(**item.model_dump())
            session.add(source)
            count += 1
        await session.commit()
        return {"message": f"imported {count} sources"}


@router.post("/{source_id}/scan")
async def scan_source(source_id: int, auth=Depends(get_current_user)):
    """Manually trigger a scan on a specific RSS source."""
    async with async_session_factory() as session:
        result = await session.execute(select(RSSSource).where(RSSSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        source.sync_status = "syncing"
        source.error_message = None
        await session.commit()
    # Queue Celery task for this specific source
    try:
        from app.core.celery_app import celery_app
        celery_app.send_task("app.tasks.subscribe.scan_single_source", args=[source_id])
    except Exception:
        pass
    from app.services.log_service import log_action
    await log_action(action="scan_source", module="sources", detail=f"扫描 RSS 源: id={source_id}, {source.name}")
    return {"message": "scan queued", "source_id": source_id}


@router.get("/{source_id}/status")
async def get_source_status(source_id: int, auth=Depends(get_current_user)):
    """Get the sync status of a specific RSS source."""
    async with async_session_factory() as session:
        result = await session.execute(select(RSSSource).where(RSSSource.id == source_id))
        source = result.scalar_one_or_none()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        return {
            "data": {
                "id": source.id,
                "name": source.name,
                "sync_status": source.sync_status,
                "last_sync_at": source.last_sync_at.isoformat() if source.last_sync_at else None,
                "error_message": source.error_message,
                "item_count": source.item_count,
            }
        }
