"""Cache API — clear various caches with confirmation."""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.core.tmdb_client import _search_cache, _genre_cache

router = APIRouter(prefix="/cache", tags=["cache"])


@router.post("/clear/sync")
async def clear_sync_cache(auth=Depends(get_current_user)):
    """Clear sync cache (triggers full sync on next run)."""
    # The sync cache is the MediaFile table — clearing it means
    # the next incremental sync becomes a full sync
    from sqlalchemy import delete
    from app.models.media_file import MediaFile
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        await session.execute(delete(MediaFile))
        await session.commit()
    return {"message": "sync cache cleared"}


@router.post("/clear/tmdb")
async def clear_tmdb_cache(auth=Depends(get_current_user)):
    """Clear TMDB in-memory search cache."""
    _search_cache.clear()
    _genre_cache.clear()
    return {"message": "TMDB cache cleared"}


@router.post("/clear/events")
async def clear_events_cache(auth=Depends(get_current_user)):
    """Reset 115 life event last_event_id."""
    # Clear any in-memory event tracking
    try:
        from app.core.p115_wrapper import reset_event_cursor
        await reset_event_cursor()
    except Exception:
        pass
    return {"message": "events cache cleared"}


@router.post("/clear/all")
async def clear_all_caches(auth=Depends(get_current_user)):
    """Clear all caches (sync + TMDB)."""
    from sqlalchemy import delete
    from app.models.media_file import MediaFile
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        await session.execute(delete(MediaFile))
        await session.commit()
    _search_cache.clear()
    _genre_cache.clear()
    return {"message": "all caches cleared"}
