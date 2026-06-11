"""Celery tasks — organize (file recognition + TMDB + classification + move).

Pipeline:
1. Fetch all unorganized files from MediaFile
2. Fast path: files with pre-existing tmdb_id → classify → move
3. Slow path: parse filename → TMDB search (score >= 0.5) → classify → move
4. Apply OrganizeRules top-down by priority (genre_ids / language / country)
5. Resolve conflicts using upgrade_strategy
6. Move to processed_cid + apply rename_pattern
7. Auto-trigger STRM generation if StrmConfig.auto_generate=true
"""
import logging
import re
from app.core.celery_app import celery_app
from app.core.websocket import manager as ws_manager

logger = logging.getLogger(__name__)

TMDB_SEARCH_CACHE: dict[str, dict] = {}


async def _broadcast(event: str, data: dict) -> None:
    try:
        await ws_manager.broadcast(event, data)
    except Exception:
        pass


def _extract_year(item: dict) -> int | None:
    release = item.get("release_date") or item.get("first_air_date")
    if release and len(release) >= 4:
        try:
            return int(release[:4])
        except ValueError:
            pass
    return None


def _apply_rename_pattern(pattern: str, meta: dict, parsed: dict, ext: str) -> str:
    """Apply a rename template to produce the final file name.

    Template variables: {title}, {year}, {resolution}, {source},
    {version}, {effect}, {video_codec}, {audio_codec}, {fps}, {country}, {group}
    """
    vars_map = {
        "title": meta.get("title", ""),
        "year": str(meta.get("year") or ""),
        "resolution": parsed.get("resolution") or "",
        "source": parsed.get("source") or "",
        "version": parsed.get("version") or "",
        "effect": parsed.get("effect") or "",
        "video_codec": parsed.get("video_codec") or "",
        "audio_codec": parsed.get("audio_codec") or "",
        "fps": parsed.get("fps") or "",
        "country": parsed.get("country") or "",
        "group": parsed.get("group") or "",
    }
    result = pattern
    for key, val in vars_map.items():
        result = result.replace("{" + key + "}", str(val))
    # Clean up empty segments like ".." and ". ."
    result = re.sub(r"\.{2,}", ".", result)
    result = re.sub(r"\s*\.\s*\.\s*", ".", result)
    result = result.strip(" .")
    # Append original extension
    if not result.lower().endswith(ext.lower()):
        result = f"{result}{ext}"
    return result


async def _search_tmdb(title: str, year: int | None) -> dict | None:
    """Search TMDB for a media title. Returns best match with score >= 0.5."""
    from app.core.tmdb_client import search_multi

    cache_key = f"tmdb:{title.lower().strip()}:{year}"
    if cache_key in TMDB_SEARCH_CACHE:
        return TMDB_SEARCH_CACHE[cache_key]

    try:
        response = await search_multi(title)
        results = response.get("results", []) if isinstance(response, dict) else (response or [])
        if not results:
            return None

        best = None
        best_score = 0.0
        title_lower = title.lower().strip()

        for item in results:
            item_title = (item.get("title") or item.get("name") or "").lower()
            score = 0.0

            if title_lower in item_title or item_title in title_lower:
                score += 0.5
                if title_lower == item_title:
                    score += 0.3

            item_year = _extract_year(item)
            if year and item_year and item_year == year:
                score += 0.3

            vote_avg = item.get("vote_average", 0)
            if vote_avg:
                score += min(0.1, vote_avg / 100)

            popularity = item.get("popularity", 0)
            if popularity > 0:
                score += min(0.1, 1.0 / (1.0 + 1000.0 / popularity))

            if score > best_score:
                best_score = score
                best = item

        if best and best_score >= 0.5:
            result = {
                "tmdb_id": best.get("id"),
                "media_type": best.get("media_type", "movie"),
                "title": best.get("title") or best.get("name", ""),
                "year": _extract_year(best),
                "genre_ids": best.get("genre_ids", []),
                "original_language": best.get("original_language", ""),
                "origin_country": (best.get("origin_country") or [""])[0],
                "score": best_score,
            }
            TMDB_SEARCH_CACHE[cache_key] = result
            return result

        return None
    except Exception as e:
        logger.warning("TMDB search failed for '%s': %s", title, e)
        return None


async def _get_tmdb_by_id(tmdb_id: int) -> dict | None:
    """Get TMDB metadata directly by tmdb_id (fast path from subscription)."""
    from app.core.tmdb_client import get_detail

    try:
        item = await get_detail("movie", tmdb_id)
        if not item or item.get("success") is False:
            item = await get_detail("tv", tmdb_id)
        if not item or item.get("success") is False:
            return None

        return {
            "tmdb_id": tmdb_id,
            "media_type": "tv" if item.get("seasons") else "movie",
            "title": item.get("title") or item.get("name", ""),
            "year": _extract_year(item),
            "genre_ids": [g["id"] for g in item.get("genres", [])],
            "original_language": item.get("original_language", ""),
            "origin_country": (item.get("origin_country") or [""])[0],
            "score": 1.0,
        }
    except Exception as e:
        logger.warning("TMDB detail fetch failed for id %d: %s", tmdb_id, e)
        return None


async def _classify(metadata: dict) -> dict | None:
    """Apply OrganizeRules top-down by priority.

    Returns dict with target_cid, folder_name, rename_pattern, or None if no rule matched.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.organize_rule import OrganizeRule

    async with async_session_factory() as session:
        result = await session.execute(
            select(OrganizeRule).order_by(OrganizeRule.priority)
        )
        rules = result.scalars().all()

    for rule in rules:
        if not rule.enabled:
            continue
        if rule.media_type and rule.media_type != metadata.get("media_type"):
            continue
        if rule.genre_ids:
            required = set(g.strip() for g in rule.genre_ids.split(",") if g.strip())
            item = set(str(g) for g in metadata.get("genre_ids", []))
            if not required.intersection(item):
                continue
        if rule.original_language:
            allowed = set(l.strip() for l in rule.original_language.split(",") if l.strip())
            if metadata.get("original_language", "") not in allowed:
                continue
        if rule.origin_country:
            allowed = set(c.strip() for c in rule.origin_country.split(",") if c.strip())
            if metadata.get("origin_country", "") not in allowed:
                continue

        media_name = metadata.get("title", "Unknown")
        year = metadata.get("year", "")
        tmdb_id = metadata.get("tmdb_id", "")
        media_type = metadata.get("media_type", "movie")
        folder_name = f"{media_name}({year})[tmdb={tmdb_id}]"
        if media_type == "tv":
            folder_name = f"{media_name}({year})[tmdb={tmdb_id}]/Season {metadata.get('season', 1):02d}"

        return {
            "target_cid": rule.target_cid,
            "folder_name": folder_name,
            "rename_pattern": rule.rename_pattern or "{title}.{year}",
        }
    return None


async def _move_file(client, source_cid: str, target_cid: str, sub_path: str) -> bool:
    """Move a file within 115 to target_cid/sub_path.

    Creates intermediate directories if they don't exist.
    """
    try:
        from p115client import P115FileSystem
        fs = P115FileSystem(client)
        parts = [p for p in sub_path.strip("/").split("/") if p]
        current_cid = target_cid
        for part in parts:
            try:
                current_cid = await fs.get_id(f"{current_cid}/{part}", async_=True)
            except Exception:
                current_cid = await fs.mkdir(part, current_cid, async_=True)
        await fs.move(source_cid, current_cid, async_=True)
        return True
    except Exception as e:
        logger.warning("File move failed: %s", e)
        return False


async def _get_organize_config():
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.organize_config import OrganizeConfig
    async with async_session_factory() as session:
        result = await session.execute(select(OrganizeConfig).limit(1))
        return result.scalar_one_or_none()


async def _get_strm_config():
    """Get StrmConfig from DB."""
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.strm_config import StrmConfig
    async with async_session_factory() as session:
        result = await session.execute(select(StrmConfig).limit(1))
        return result.scalar_one_or_none()


async def _maybe_trigger_strm() -> None:
    """Trigger STRM generation if StrmConfig.auto_generate is enabled."""
    try:
        config = await _get_strm_config()
        if config and config.auto_generate:
            celery_app.send_task("app.tasks.strm.generate_strm_task")
            logger.info("Auto-triggered STRM generation after organize")
    except Exception as e:
        logger.warning("Failed to auto-trigger STRM: %s", e)


@celery_app.task(bind=True, max_retries=3)
def organize_task(self) -> dict:
    """Execute organize pipeline: regex → TMDB → classification → move."""
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.media_file import MediaFile
    from app.models.subscription import Subscription, UpgradeStrategy
    from app.core.p115_wrapper import get_client
    from app.core.file_parser import parse_filename

    import asyncio

    async def _run():
        logger.info("Organize task started")
        client = get_client()
        if not client:
            return {"status": "skipped", "reason": "No client"}

        config = await _get_organize_config()
        if not config or not config.source_cid:
            return {"status": "skipped", "reason": "No config"}

        await _broadcast("organize.start", {})

        # ── Fetch ALL unorganized files (no limit) ──
        async with async_session_factory() as session:
            # Files with tmdb_id already set (fast path from subscription)
            fast_files = (await session.execute(
                select(MediaFile).where(
                    MediaFile.organized == False,
                    MediaFile.tmdb_id.isnot(None),
                )
            )).scalars().all()

            # Files that need recognition (no tmdb_id yet)
            pending_files = (await session.execute(
                select(MediaFile).where(
                    MediaFile.organized == False,
                    MediaFile.tmdb_id.is_(None),
                )
            )).scalars().all()

        total = len(fast_files) + len(pending_files)
        logger.info("Organize: %d fast-path, %d pending recognition", len(fast_files), len(pending_files))

        org, fail, skip = 0, 0, 0
        processed = 0

        # ── Phase 1: Fast path (tmdb_id already known) ──
        for mf in fast_files:
            meta = await _get_tmdb_by_id(mf.tmdb_id)
            if not meta:
                async with async_session_factory() as s:
                    db = (await s.execute(select(MediaFile).where(MediaFile.id == mf.id))).scalar_one_or_none()
                    if db:
                        db.retry_count = (db.retry_count or 0) + 1
                        await s.commit()
                fail += 1
                processed += 1
                continue

            async with async_session_factory() as s:
                db = (await s.execute(select(MediaFile).where(MediaFile.id == mf.id))).scalar_one_or_none()
                if db:
                    db.recognized = True
                    db.year = meta.get("year")
                    await s.commit()

            r = await _process_file(mf, meta, client, config)
            if r == "organized":
                org += 1
            elif r == "skipped":
                skip += 1
            else:
                fail += 1
            processed += 1

            if processed % 10 == 0:
                await _broadcast("organize.progress", {
                    "processed": processed, "total": total,
                    "organized": org, "failed": fail, "skipped": skip,
                })

        # ── Phase 2: Recognition (parse filename → search TMDB) ──
        for mf in pending_files:
            parsed = parse_filename(mf.file_name)
            if not parsed or not parsed.get("title"):
                # Mark failed attempt, increment retry count
                async with async_session_factory() as s:
                    db = (await s.execute(select(MediaFile).where(MediaFile.id == mf.id))).scalar_one_or_none()
                    if db:
                        db.retry_count = (db.retry_count or 0) + 1
                        await s.commit()
                fail += 1
                processed += 1
                continue

            meta = await _search_tmdb(parsed["title"], parsed.get("year"))
            if not meta:
                # TMDB search failed — mark as unrecognized, don't increment retry
                # (retry_count only increments on parse failure; TMDB failure may
                #  succeed later when the movie becomes available in the database)
                fail += 1
                processed += 1
                continue

            # Save recognition results to MediaFile
            async with async_session_factory() as s:
                db = (await s.execute(select(MediaFile).where(MediaFile.id == mf.id))).scalar_one_or_none()
                if db:
                    db.tmdb_id = meta["tmdb_id"]
                    db.media_type = meta["media_type"]
                    db.year = meta.get("year")
                    db.resolution = parsed.get("resolution")
                    db.source = parsed.get("source")
                    db.video_codec = parsed.get("video_codec")
                    db.audio_codec = parsed.get("audio_codec")
                    db.effect = parsed.get("effect")
                    db.version = parsed.get("version")
                    db.fps = parsed.get("fps")
                    db.country = parsed.get("country")
                    db.recognized = True
                    await s.commit()

            r = await _process_file(mf, meta, client, config)
            if r == "organized":
                org += 1
            elif r == "skipped":
                skip += 1
            else:
                fail += 1
            processed += 1

            if processed % 10 == 0:
                await _broadcast("organize.progress", {
                    "processed": processed, "total": total,
                    "organized": org, "failed": fail, "skipped": skip,
                })

        await _broadcast("organize.done", {"organized": org, "failed": fail, "skipped": skip})

        # Auto-trigger STRM if enabled
        if org > 0:
            await _maybe_trigger_strm()

        try:
            from app.services.notify_service import dispatch_notification
            await dispatch_notification("organize_done", {
                "organized": org, "failed": fail, "skipped": skip,
            })
        except Exception:
            pass

        logger.info("Organize done: %d org, %d fail, %d skip", org, fail, skip)
        return {"status": "completed", "organized": org, "failed": fail, "skipped": skip}

    return asyncio.run(_run())


async def _process_file(mf, meta, client, config) -> str:
    """Process a single file: classify → resolve conflicts → rename → move.

    Returns "organized", "skipped", or "failed".
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.media_file import MediaFile
    from app.models.subscription import Subscription, UpgradeStrategy
    from app.core.file_parser import parse_filename

    classification = await _classify(meta)
    if not classification:
        return "failed"

    target_cid = config.processed_cid
    folder_name = classification["folder_name"]

    # ── Determine new file name via rename_pattern ──
    parsed = parse_filename(mf.file_name) or {}
    ext = ""
    if "." in mf.file_name:
        ext = "." + mf.file_name.rsplit(".", 1)[-1]
    new_name = _apply_rename_pattern(classification["rename_pattern"], meta, parsed, ext)

    # ── Resolve conflicts ──
    async with async_session_factory() as session:
        ex = (await session.execute(
            select(MediaFile).where(
                MediaFile.tmdb_id == meta["tmdb_id"],
                MediaFile.organized == True,
            )
        )).scalars().first()

        if ex:
            sub = (await session.execute(
                select(Subscription).where(Subscription.tmdb_id == meta["tmdb_id"]).limit(1)
            )).scalar_one_or_none()
            # Default to coexist when no subscription
            strategy = sub.upgrade_strategy if sub else UpgradeStrategy.coexist

            if strategy == UpgradeStrategy.skip:
                await _move_file(client, mf.cid, config.duplicate_cid, "")
                db = (await session.execute(select(MediaFile).where(MediaFile.id == mf.id))).scalar_one_or_none()
                if db:
                    db.organized = True
                    await session.commit()
                return "skipped"
            elif strategy in (UpgradeStrategy.max_size, UpgradeStrategy.min_size):
                keep_larger = strategy == UpgradeStrategy.max_size
                if (keep_larger and mf.file_size > ex.file_size) or \
                   (not keep_larger and mf.file_size < ex.file_size):
                    # New file wins — move old to duplicate_cid
                    await _move_file(client, ex.cid, config.duplicate_cid, "")
                    db_ex = (await session.execute(select(MediaFile).where(MediaFile.id == ex.id))).scalar_one_or_none()
                    if db_ex:
                        db_ex.organized = False
                        await session.commit()
                else:
                    # Old file wins — move new to duplicate_cid
                    await _move_file(client, mf.cid, config.duplicate_cid, "")
                    return "skipped"
            # coexist: keep both, fall through to normal move

    # ── Move file to processed_cid ──
    success = await _move_file(client, mf.cid, target_cid, folder_name)
    if not success:
        return "failed"

    # ── Update DB ──
    async with async_session_factory() as s:
        db = (await s.execute(select(MediaFile).where(MediaFile.id == mf.id))).scalar_one_or_none()
        if db:
            db.organized = True
            db.file_path = f"{target_cid}/{folder_name}/{new_name}"
            await s.commit()

    return "organized"
