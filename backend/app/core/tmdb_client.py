"""TMDB API client — discovery, search, detail, genre list with cache."""
import os
import time
import logging
from typing import Any
import httpx

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/"

# In-memory cache: {key: (timestamp, data)}
_search_cache: dict[str, tuple[float, Any]] = {}
_genre_cache: dict[str, tuple[float, Any]] = {}
_discover_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 86400  # 24 hours
DISCOVER_CACHE_TTL = 3600  # 60 minutes


def _get_api_key() -> str:
    """Get TMDB API key from env var."""
    return os.getenv("TMDB_API_KEY", "")


async def _get_language_async() -> str:
    """Get TMDB display language from DB config (cached)."""
    global _db_lang_cached, _db_lang_checked
    if not _db_lang_checked:
        _db_lang_checked = True
        try:
            from sqlalchemy import select
            from app.core.database import async_session_factory
            from app.models.tmdb_config import TmdbConfig
            async with async_session_factory() as sess:
                result = await sess.execute(select(TmdbConfig).limit(1))
                cfg = result.scalar_one_or_none()
                if cfg and cfg.language:
                    _db_lang_cached = cfg.language
        except Exception:
            pass
    return _db_lang_cached or "zh-CN"


_db_lang_cached: str | None = None
_db_lang_checked = False


def reset_api_key_cache() -> None:
    """Reset the DB API key and language cache so saved config takes effect without restart."""
    global _db_key_cached, _db_key_checked, _db_lang_cached, _db_lang_checked
    _db_key_cached = None
    _db_key_checked = False
    _db_lang_cached = None
    _db_lang_checked = False


_db_key_cached: str | None = None
_db_key_checked = False


async def _get_api_key_async() -> str:
    """Get TMDB API key: env var first, then DB config (cached)."""
    global _db_key_cached, _db_key_checked
    api_key = os.getenv("TMDB_API_KEY", "")
    if api_key and api_key != "your_tmdb_api_key_here":
        return api_key
    # Try DB config table (once, cached)
    if not _db_key_checked:
        _db_key_checked = True
        try:
            from sqlalchemy import select
            from app.core.database import async_session_factory
            from app.models.tmdb_config import TmdbConfig
            async with async_session_factory() as sess:
                result = await sess.execute(select(TmdbConfig).limit(1))
                cfg = result.scalar_one_or_none()
                if cfg and cfg.api_key:
                    _db_key_cached = cfg.api_key
        except Exception:
            pass
    return _db_key_cached or ""


def _cache_get(cache: dict, key: str) -> Any | None:
    entry = cache.get(key)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts > CACHE_TTL:
        del cache[key]
        return None
    return data


def _cache_set(cache: dict, key: str, data: Any) -> None:
    cache[key] = (time.time(), data)


def _discover_cache_get(key: str) -> Any | None:
    entry = _discover_cache.get(key)
    if not entry:
        return None
    ts, data = entry
    if time.time() - ts > DISCOVER_CACHE_TTL:
        del _discover_cache[key]
        return None
    return data


async def tmdb_get(endpoint: str, params: dict | None = None) -> dict | list:
    """Make a GET request to TMDB API."""
    api_key = await _get_api_key_async()
    if not api_key:
        logger.warning("TMDB_API_KEY not set")
        return {"results": []}
    lang = await _get_language_async()
    merged_params = {"api_key": api_key, "language": lang, **(params or {})}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{TMDB_BASE_URL}/{endpoint}", params=merged_params)
        resp.raise_for_status()
        return resp.json()


async def discover_movie(
    genre: str | None = None,
    year: str | None = None,
    country: str | None = None,
    rating: float | None = None,
    language: str | None = None,
    sort: str = "popularity.desc",
    page: int = 1,
) -> dict:
    """Discover movies via TMDB /discover/movie (cached 60 min)."""
    params: dict = {
        "sort_by": sort,
        "page": page,
        "vote_count.gte": 50,
    }
    if genre:
        params["with_genres"] = genre
    if year:
        params["primary_release_year"] = year
    if country:
        params["with_origin_country"] = country
    if rating:
        params["vote_average.gte"] = rating
    if language:
        params["with_original_language"] = language

    cache_key = f"discover_movie:{sort}:{page}:{genre}:{year}:{country}:{rating}:{language}"
    cached = _discover_cache_get(cache_key)
    if cached:
        return cached
    data = await tmdb_get("discover/movie", params)
    _cache_set(_discover_cache, cache_key, data)
    return data


async def discover_tv(
    genre: str | None = None,
    year: str | None = None,
    country: str | None = None,
    rating: float | None = None,
    language: str | None = None,
    sort: str = "popularity.desc",
    page: int = 1,
) -> dict:
    """Discover TV shows via TMDB /discover/tv (cached 60 min)."""
    params: dict = {
        "sort_by": sort,
        "page": page,
        "vote_count.gte": 10,
    }
    if genre:
        params["with_genres"] = genre
    if year:
        params["first_air_date_year"] = year
    if country:
        params["with_origin_country"] = country
    if rating:
        params["vote_average.gte"] = rating
    if language:
        params["with_original_language"] = language

    cache_key = f"discover_tv:{sort}:{page}:{genre}:{year}:{country}:{rating}:{language}"
    cached = _discover_cache_get(cache_key)
    if cached:
        return cached
    data = await tmdb_get("discover/tv", params)
    _cache_set(_discover_cache, cache_key, data)
    return data


async def search_multi(query: str, page: int = 1) -> dict:
    """Search TMDB (movie + tv)."""
    lang = await _get_language_async()
    cache_key = f"search:{query}:{page}:{lang}"
    cached = _cache_get(_search_cache, cache_key)
    if cached:
        return cached
    data = await tmdb_get("search/multi", {"query": query, "page": page})
    _cache_set(_search_cache, cache_key, data)
    return data


async def get_detail(media_type: str, tmdb_id: int) -> dict:
    """Get TMDB detail for a movie or tv show."""
    return await tmdb_get(f"{media_type}/{tmdb_id}")


async def get_genres(media_type: str = "movie") -> list:
    """Get genre list (cached 24h)."""
    lang = await _get_language_async()
    cache_key = f"genres:{media_type}:{lang}"
    cached = _cache_get(_genre_cache, cache_key)
    if cached:
        return cached
    data = await tmdb_get(f"genre/{media_type}/list")
    genres = data.get("genres", [])
    _cache_set(_genre_cache, cache_key, genres)
    return genres
