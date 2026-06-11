"""API v1 routes — register all routers."""
from fastapi import APIRouter
from .auth import router as auth_router
from .config import router as config_router
from .notify import router as notify_router
from .hot import router as hot_router, tmdb_router

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth_router)
api_v1.include_router(config_router)
api_v1.include_router(notify_router)
api_v1.include_router(hot_router)
api_v1.include_router(tmdb_router)

# Lazy imports for remaining routers (added in later phases)
_subscriptions_router = None
_sources_router = None
_transfers_router = None
_sync_router = None
_organize_router = None
_files_router = None
_dashboard_router = None
_logs_router = None
_cache_router = None


def _lazy_routers():
    global _subscriptions_router, _sources_router, _transfers_router
    global _sync_router, _organize_router, _files_router
    global _dashboard_router, _logs_router, _cache_router
    if _subscriptions_router is None:
        from .subscriptions import router as sr
        _subscriptions_router = sr
        api_v1.include_router(sr)
    if _sources_router is None:
        from .sources import router as sr2
        _sources_router = sr2
        api_v1.include_router(sr2, prefix="/sources")
        api_v1.include_router(sr2, prefix="/rss-sources")
    if _transfers_router is None:
        from .transfers import router as tr
        _transfers_router = tr
        api_v1.include_router(tr)
    if _sync_router is None:
        from .sync import router as sr3
        _sync_router = sr3
        api_v1.include_router(sr3)
    if _organize_router is None:
        from .organize import router as or_
        _organize_router = or_
        api_v1.include_router(or_)
    if _files_router is None:
        from .files import router as fr
        _files_router = fr
        api_v1.include_router(fr)
    if _dashboard_router is None:
        from .dashboard import router as dr
        _dashboard_router = dr
        api_v1.include_router(dr)
    if _logs_router is None:
        from .logs import router as lr
        _logs_router = lr
        api_v1.include_router(lr)
    if _cache_router is None:
        from .cache import router as cr
        _cache_router = cr
        api_v1.include_router(cr)


def get_router() -> APIRouter:
    """Return the fully loaded v1 router (lazily includes all modules)."""
    _lazy_routers()
    return api_v1
