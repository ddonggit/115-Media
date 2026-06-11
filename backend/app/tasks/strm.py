"""Celery tasks — STRM file generation for organized media.

Uses p115client.tool.download.make_strm to generate .strm files
pointing to the 115 download URL via p115tiny302 on port 8095.
"""
import logging
import os
from app.core.celery_app import celery_app
from app.core.websocket import manager as ws_manager

logger = logging.getLogger(__name__)


async def _broadcast(event: str, data: dict) -> None:
    try:
        await ws_manager.broadcast(event, data)
    except Exception:
        pass


async def _get_strm_config():
    """Get StrmConfig from DB."""
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.strm_config import StrmConfig

    async with async_session_factory() as session:
        result = await session.execute(select(StrmConfig).limit(1))
        return result.scalar_one_or_none()


async def _build_strm_path(file_path: str, media_library_path: str) -> str:
    """Build the local .strm file path from the organized file_path on 115.

    file_path format: {processed_cid}/{Movie(2024)[tmdb=123]}/file.mkv
    Strips the leading cid segment, replaces extension with .strm.
    """
    # Strip leading cid (the first path segment is a numeric 115 directory ID)
    parts = file_path.strip("/").split("/")
    if len(parts) >= 2:
        # Remove the cid segment, keep the rest as the media-relative path
        relative = "/".join(parts[1:])
    else:
        relative = parts[0] if parts else file_path

    # Change extension to .strm
    if "." in relative:
        name = relative.rsplit(".", 1)[0]
    else:
        name = relative
    strm_rel = f"{name}.strm"

    media_lib = media_library_path.rstrip("/")
    return os.path.join(media_lib, strm_rel)


@celery_app.task(bind=True, max_retries=3)
def generate_strm_task(self) -> dict:
    """Generate STRM files for organized media.

    Scans MediaFile records where organized=True and strm_generated=False,
    then uses make_strm to generate .strm files in the configured
    media library path.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.media_file import MediaFile
    from app.core.p115_wrapper import get_client

    import asyncio

    async def _run():
        logger.info("STRM generation task started")

        client = get_client()
        if not client:
            logger.warning("STRM: No 115 client available")
            return {"status": "skipped", "reason": "No client"}

        config = await _get_strm_config()
        if not config or not config.media_library_path:
            logger.warning("STRM: StrmConfig not fully configured")
            return {"status": "skipped", "reason": "No config"}

        # Only process organized files that haven't had STRM generated yet
        async with async_session_factory() as session:
            result = await session.execute(
                select(MediaFile).where(
                    MediaFile.organized == True,
                    MediaFile.strm_generated == False,
                    MediaFile.media_type != "unknown",
                ).limit(200)
            )
            files = result.scalars().all()

        if not files:
            logger.info("STRM: No files need STRM generation")
            return {"status": "completed", "generated": 0, "message": "All up-to-date"}

        await _broadcast("strm.start", {"total": len(files)})

        generated = 0
        failed = 0

        for mf in files:
            try:
                from p115client.tool.download import make_strm

                # Build STRM path from the organized directory structure
                if mf.file_path:
                    full_strm_path = await _build_strm_path(mf.file_path, config.media_library_path)
                else:
                    # Fallback: use file name in the media library root
                    name = mf.file_name.rsplit(".", 1)[0] if "." in mf.file_name else mf.file_name
                    full_strm_path = os.path.join(config.media_library_path.rstrip("/"), f"{name}.strm")

                # Ensure parent directory exists
                parent_dir = os.path.dirname(full_strm_path)
                os.makedirs(parent_dir, exist_ok=True)

                # Generate the .strm file via p115client SDK
                await make_strm(client, mf.cid, strm_path=full_strm_path, async_=True)

                # Mark as generated in DB
                async with async_session_factory() as s:
                    db = (await s.execute(select(MediaFile).where(MediaFile.id == mf.id))).scalar_one_or_none()
                    if db:
                        db.strm_generated = True
                        await s.commit()

                generated += 1
                logger.debug("STRM generated: %s", full_strm_path)

                if generated % 10 == 0:
                    await _broadcast("strm.progress", {
                        "generated": generated, "total": len(files),
                    })

            except Exception as e:
                logger.warning("STRM generation failed for file %s (cid=%s): %s",
                              mf.file_name, mf.cid, e)
                failed += 1

        await _broadcast("strm.done", {"generated": generated, "failed": failed})
        logger.info("STRM generation done: %d generated, %d failed", generated, failed)

        return {"status": "completed", "generated": generated, "failed": failed}

    return asyncio.run(_run())
