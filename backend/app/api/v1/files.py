"""File Browser API — browse 115 directory tree and search files."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.security import get_current_user
from app.core.p115_wrapper import get_client, validate_client
from app.models.media_file import MediaFile
from app.schemas.media_file import MediaFileResponse

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/browse", response_model=dict)
async def browse_directory(
    cid: str = Query("0", description="115 directory cid, 0=root"),
    auth=Depends(get_current_user),
):
    """Browse files in a 115 directory by cid — fetches live from 115 API."""
    client = get_client()
    if not client or not await validate_client(client):
        raise HTTPException(status_code=400, detail="115 账号未登录或 Cookie 已失效，请先在设置页重新登录")

    try:
        data = await client.fs_files(cid, async_=True, timeout=15.0)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"115 API 请求失败: {e}")

    if not isinstance(data, dict) or not data.get("state"):
        raise HTTPException(status_code=502, detail="115 API 返回异常")

    # Build path from 115 response
    path_parts = data.get("path", [])
    path_str = "/".join(p.get("name", "") for p in path_parts) if path_parts else f"/{cid}"

    # Parse items from 115 response
    items = []
    for item in data.get("data", []):
        is_dir = "fid" not in item  # directories don't have fid in web API
        items.append({
            "cid": str(item.get("cid", "")),
            "file_name": item.get("n", ""),
            "file_size": item.get("s", 0) if not is_dir else 0,
            "media_type": "unknown" if is_dir else _guess_media_type(item.get("n", "")),
            "is_dir": is_dir,
            "fid": item.get("fid", ""),
            "pickcode": item.get("pc", ""),
            "sha1": item.get("sha", ""),
        })

    return {
        "data": {
            "files": items,
            "path": path_str,
            "path_parts": [{"name": p.get("name", ""), "cid": str(p.get("cid", ""))} for p in path_parts],
            "cid": cid,
            "count": data.get("count", 0),
        }
    }


def _guess_media_type(name: str) -> str:
    """Guess media type from file extension."""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    video_exts = {"mp4", "mkv", "avi", "wmv", "flv", "mov", "rmvb", "ts", "m2ts", "webm"}
    audio_exts = {"mp3", "flac", "wav", "aac", "ogg", "m4a", "wma"}
    if ext in video_exts:
        return "video"
    if ext in audio_exts:
        return "audio"
    return "other"


@router.get("/search", response_model=list[MediaFileResponse])
async def search_files(
    q: str = Query(..., min_length=1, description="Filename to search for"),
    limit: int = Query(50, ge=1, le=200),
    auth=Depends(get_current_user),
):
    """Search files by name (single-level)."""
    async with async_session_factory() as session:
        stmt = (
            select(MediaFile)
            .where(MediaFile.file_name.contains(q))
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()


@router.get("/resolve")
async def resolve_cid(
    cid: str = Query(..., description="115 directory cid"),
    auth=Depends(get_current_user),
):
    """Resolve a CID to its real folder name from 115 API."""
    client = get_client()
    if not client or not await validate_client(client):
        raise HTTPException(status_code=400, detail="115 账号未登录或 Cookie 已失效，请先在设置页重新登录")

    try:
        data = await client.fs_files(cid, async_=True, timeout=15.0)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"115 API 请求失败: {e}")

    if not isinstance(data, dict) or not data.get("state"):
        raise HTTPException(status_code=502, detail="115 API 返回异常或目录不存在")

    path_parts = data.get("path", [])
    if not path_parts:
        raise HTTPException(status_code=404, detail="目录不存在或路径为空")
    name = path_parts[-1].get("name", "未知目录")
    return {"cid": cid, "name": name}


@router.get("/{cid}")
async def get_file_info(cid: str, auth=Depends(get_current_user)):
    """Get file info by cid."""
    async with async_session_factory() as session:
        result = await session.execute(select(MediaFile).where(MediaFile.cid == cid))
        file_ = result.scalar_one_or_none()
        if not file_:
            raise HTTPException(status_code=404, detail="File not found")
        return {"data": MediaFileResponse.model_validate(file_).model_dump()}
