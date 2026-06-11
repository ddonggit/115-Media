"""Hot / TMDB API — discovery, search, detail, genres."""
import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from app.core.security import get_current_user
from app.core.tmdb_client import (
    discover_movie,
    discover_tv,
    search_multi,
    get_detail,
    get_genres,
)
import httpx

router = APIRouter(prefix="/hot", tags=["hot"])
tmdb_router = APIRouter(prefix="/tmdb", tags=["tmdb"])


# ── Discover ───────────────────────────────────────────────────────


@router.get("/movie")
async def hot_movie(
    genre: str | None = Query(None, description="TMDB genre ID(s)"),
    year: str | None = Query(None),
    country: str | None = Query(None, description="ISO 3166-1 code"),
    rating: float | None = Query(None, ge=0, le=10, alias="vote_average.gte"),
    language: str | None = Query(None, description="ISO 639-1"),
    sort: str = Query("popularity.desc"),
    page: int = Query(1, ge=1),
    auth=Depends(get_current_user),
):
    """Discover hot movies with 6-dimension filters."""
    data = await discover_movie(genre, year, country, rating, language, sort, page)
    return {"data": data.get("results", []), "page": data.get("page"), "total_pages": data.get("total_pages")}


@router.get("/tv")
async def hot_tv(
    genre: str | None = Query(None),
    year: str | None = Query(None),
    country: str | None = Query(None),
    rating: float | None = Query(None, ge=0, le=10, alias="vote_average.gte"),
    language: str | None = Query(None),
    sort: str = Query("popularity.desc"),
    page: int = Query(1, ge=1),
    auth=Depends(get_current_user),
):
    """Discover hot TV shows with 6-dimension filters."""
    data = await discover_tv(genre, year, country, rating, language, sort, page)
    return {"data": data.get("results", []), "page": data.get("page"), "total_pages": data.get("total_pages")}


@router.get("/genres")
async def list_genres(auth=Depends(get_current_user)):
    """Get all TMDB genres (cached 24h)."""
    movie_genres = await get_genres("movie")
    tv_genres = await get_genres("tv")
    return {"data": {"movie": movie_genres, "tv": tv_genres}}


@router.get("/search")
async def hot_search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    auth=Depends(get_current_user),
):
    """Multi-search TMDB (movie + tv) — hot search endpoint."""
    data = await search_multi(query, page)
    return {"data": data.get("results", []), "page": data.get("page")}


# ── TMDB Search & Detail ──────────────────────────────────────────


@tmdb_router.get("/search")
async def tmdb_search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    auth=Depends(get_current_user),
):
    """Multi-search TMDB (movie + tv)."""
    data = await search_multi(query, page)
    return {"data": data.get("results", []), "page": data.get("page")}


@tmdb_router.get("/{media_type}/{tmdb_id}")
async def tmdb_detail(
    media_type: str,
    tmdb_id: int,
    auth=Depends(get_current_user),
):
    """Get TMDB detail by type and ID."""
    data = await get_detail(media_type, tmdb_id)
    return {"data": data}


# ── TMDB Image Proxy ──────────────────────────────────────────────

_img_logger = logging.getLogger("hot.img")


@router.get("/img")
async def tmdb_image_proxy(
    path: str = Query(..., description="TMDB image path, e.g. /xxx.jpg"),
    size: str = Query("w500", description="Image size: w92, w154, w185, w342, w500, w780, original"),
):
    """Proxy TMDB image requests to bypass GFW blocking of image.tmdb.org.

    No auth required — images are public TMDB content.
    """
    if not path or not path.startswith("/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid image path")
    url = f"https://image.tmdb.org/t/p/{size}{path}"
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                _img_logger.warning("TMDB image fetch failed (%d): %s", resp.status_code, url)
                from fastapi import HTTPException
                raise HTTPException(status_code=resp.status_code, detail="TMDB image fetch failed")
            content = await resp.aread()
            content_type = resp.headers.get("content-type", "image/jpeg")
            return Response(
                content=content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except Exception:
        _img_logger.warning("TMDB image proxy error for: %s", url, exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail="Image proxy error")
