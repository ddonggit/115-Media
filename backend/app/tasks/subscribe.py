"""Celery tasks — subscription checking (BT4G RSS → match → transfer)."""
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from app.core.celery_app import celery_app
from app.core.file_parser import parse_filename

logger = logging.getLogger(__name__)

from app.core.websocket import manager as ws_manager


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _extract_title_from_item(item_title: str) -> str | None:
    """Extract a clean title from an RSS item title (torrent name).

    Strips brackets, year, and common suffixes to get the media name.
    """
    # Strip leading brackets like [www.example.com] or 【www.example.com】
    cleaned = re.sub(r'^[\[【].*?[\]】]\s*', '', item_title)
    # Strip year from the end (e.g. "2024" or "(2024)")
    cleaned = re.sub(r'\s*[\(\[]?(19|20)\d{2}[\)\]]?\s*$', '', cleaned)
    # Strip resolution/source tags at end
    cleaned = re.sub(r'\s*(2160p|1080p|720p|4K|UHD|HD|BluRay|WEB-DL|WEBRip).*$', '', cleaned, flags=re.IGNORECASE)
    # Clean separators
    cleaned = re.sub(r'[._]', ' ', cleaned)
    cleaned = cleaned.strip()
    return cleaned if cleaned else None


def _quality_matches(item_resolution: str | None, subscription_quality: str) -> bool:
    """Check if an item's resolution matches the subscription's quality requirement.

    Sub quality '4k' → item must be 2160p/4K
    Sub quality 'bluray' → item source must be BluRay
    Sub quality 'bluray+4k' → item must be (BluRay source AND 2160p) OR (4K resolution)
    Sub quality '1080p' → item must be 1080p
    If resolution can't be determined from the item, be lenient and accept.
    """
    sub_q = subscription_quality.lower()
    item_res = (item_resolution or "").lower()

    if not item_res:
        return True

    if sub_q == "4k":
        return item_res in ("2160p", "4k", "uhd")
    if sub_q == "1080p":
        return item_res == "1080p"
    if sub_q == "bluray":
        # Need to detect BluRay source from the item title
        # This is handled by checking source field, not resolution
        return True  # Let source matching handle it
    if sub_q == "bluray+4k":
        return item_res in ("2160p", "4k", "uhd")
    return True



async def _broadcast(event: str, data: dict) -> None:
    try:
        await ws_manager.broadcast(event, data)
    except Exception:
        pass


async def _run_subscription_check(source_id: int | None = None) -> dict:
    """Core logic: fetch RSS, match items against subscriptions, create transfers.

    If source_id is provided, only scan that specific RSS source.
    """
    from sqlalchemy import select
    from app.core.database import async_session_factory
    from app.models.subscription import Subscription, SubStatus, MediaType, Quality
    from app.models.rss_source import RSSSource
    from app.models.transfer_task import TransferTask, TransferType, TransferStatus

    logger.info("Checking subscriptions..." + (f" (source_id={source_id})" if source_id else ""))
    async with async_session_factory() as session:
        sub_result = await session.execute(
            select(Subscription).where(Subscription.status == SubStatus.active)
        )
        subscriptions = sub_result.scalars().all()

        src_query = select(RSSSource).where(RSSSource.enabled == True)
        if source_id is not None:
            src_query = src_query.where(RSSSource.id == source_id)
        src_result = await session.execute(src_query)
        sources = src_result.scalars().all()

        logger.info("Found %d active subscriptions, %d RSS sources",
                   len(subscriptions), len(sources))

        if not subscriptions or not sources:
            return {"status": "skipped", "reason": "no subscriptions or sources",
                    "subscriptions_checked": len(subscriptions)}

        sub_dicts = []
        for s in subscriptions:
            sub_dicts.append({
                "id": s.id,
                "tmdb_id": s.tmdb_id,
                "media_name": s.media_name,
                "media_type": s.media_type.value if hasattr(s.media_type, 'value') else s.media_type,
                "year": s.year,
                "quality": s.quality.value if hasattr(s.quality, 'value') else s.quality,
                "season": s.season,
                "episode_start": s.episode_start,
                "episode_end": s.episode_end,
                "episode_current": s.episode_current,
                "include_hd_keyword": s.include_hd_keyword if hasattr(s, 'include_hd_keyword') else True,
                "matched_count": s.matched_count or 0,
                "status": s.status,
            })

        sub_map: dict[str, list[dict]] = {}
        for sd in sub_dicts:
            key = sd["media_name"].lower().strip()
            if key not in sub_map:
                sub_map[key] = []
            sub_map[key].append(sd)

        total_matches = 0

        for source in sources:
            if not source.enabled:
                continue

            items = _fetch_rss(source.url)
            if not items:
                source.sync_status = "error"
                source.error_message = "No items fetched"
                continue

            source.sync_status = "syncing"
            source.item_count = len(items)
            source.last_sync_at = _utcnow()

            for item in items:
                item_title = item.get("title", "")
                item_link = item.get("link", "") or item.get("guid", "")

                if not item_title or not item_link:
                    continue

                parsed = parse_filename(item_title)
                if not parsed:
                    parsed = {}
                    # 降级提取：RSS标题无视频扩展名时，从文本提取年份/画质/来源
                    clean = re.sub(r'^[【\[]..*?[\]】]\s*', '', item_title)
                    m = re.search(r'(?:[.\s\-/\[\]])' + r'((?:19|20)\d{2})' + r'(?:[.\s\-/\[\]]|$)', clean)
                    if m: parsed['year'] = int(m.group(1))
                    m = re.search(r'(?:^|[.\s\-/\[\]])(2160p|1080p|720p)(?:[.\s\-/\[\]]|$)', clean, re.I)
                    if m: parsed['resolution'] = m.group(1)
                    m = re.search(r'(?:^|[.\s\-/\[\]])(BluRay|Blu-ray|WEB-DL|WEBRip|HDTV|DVD|REMUX|BDRip)(?:[.\s\-/\[\]]|$)', clean, re.I)
                    if m: parsed['source'] = m.group(1)
                item_media = (parsed.get("title") or _extract_title_from_item(item_title) or "").lower().strip()
                item_year = parsed.get("year")
                item_season = parsed.get("season")
                item_episode = parsed.get("episode")
                item_resolution = parsed.get("resolution")
                item_source_type = parsed.get("source")
                item_ep_start = parsed.get("episode_start")
                item_ep_end = parsed.get("episode_end")
                item_is_pack = parsed.get("is_pack", False)

                if item_is_pack:
                    logger.debug("Skipping pack item: %s", item_title[:60])
                    continue

                matched_subs = []
                for media_key, subs_list in sub_map.items():
                    if item_media and media_key in item_media:
                        matched_subs.extend(subs_list)
                    elif item_media:
                        for sub in subs_list:
                            sub_name_lower = sub["media_name"].lower().strip()
                            if sub_name_lower in item_media or item_media in sub_name_lower:
                                matched_subs.append(sub)

                seen_ids: set[int] = set()
                unique_matches = []
                for sub in matched_subs:
                    sid = sub["id"]
                    if sid not in seen_ids:
                        seen_ids.add(sid)
                        unique_matches.append(sub)

                for sub in unique_matches:
                    if sub["year"] and item_year and sub["year"] != item_year:
                        continue

                    if sub["media_type"] == "tv" and sub["season"] is not None and item_season is not None:
                        if item_season != sub["season"]:
                            continue

                    if sub["media_type"] == "tv":
                        ep_cur = sub["episode_current"] or 0
                        eps_start = sub["episode_start"] or 1
                        eps_end = sub["episode_end"]

                        ep_match_start = item_ep_start or item_episode
                        ep_match_end = item_ep_end or item_episode

                        if ep_match_start is not None and ep_match_end is not None:
                            match_low = max(ep_match_start, ep_cur + 1)
                            match_high = ep_match_end
                            if eps_end is not None:
                                match_high = min(match_high, eps_end)
                            if match_low > match_high:
                                continue
                            effective_episode = match_high
                        else:
                            if eps_start not in (None, 1):
                                continue
                            effective_episode = None

                    if not _quality_matches(item_resolution, sub["quality"]):
                        continue

                    if sub["quality"] == "bluray":
                        src_lower = (item_source_type or "").lower()
                        if "bluray" not in src_lower and "blu-ray" not in src_lower:
                            continue

                    dup_check = await session.execute(
                        select(TransferTask.id).where(
                            TransferTask.url == item_link,
                            TransferTask.status.in_([
                                TransferStatus.submitted,
                                TransferStatus.done,
                            ])
                        ).limit(1)
                    )
                    if dup_check.scalar_one_or_none() is not None:
                        logger.debug("Skipping duplicate transfer for URL: %s", item_link[:60])
                        continue

                    target_dir = f"/云下载/{sub['media_name']}"
                    if sub["media_type"] == "tv" and sub["season"]:
                        target_dir = f"{target_dir}/Season {sub['season']:02d}"

                    transfer = TransferTask(
                        transfer_type=TransferType.magnet,
                        url=item_link,
                        target_dir=target_dir,
                        auto_organize=True,
                        media_name=sub["media_name"],
                        tmdb_id=sub["tmdb_id"],
                        status=TransferStatus.submitted,
                    )
                    session.add(transfer)

                sub_orm = await session.get(Subscription, sub["id"])
                if sub_orm:
                    sub_orm.matched_count = (sub_orm.matched_count or 0) + 1
                    sub_orm.last_match_at = _utcnow()

                    if sub["media_type"] == "tv" and effective_episode is not None:
                        current = sub_orm.episode_current or 0
                        if effective_episode > current:
                            sub_orm.episode_current = effective_episode
                        if sub["episode_end"] is not None and sub_orm.episode_current is not None:
                            if sub_orm.episode_current >= sub["episode_end"]:
                                sub_orm.status = SubStatus.completed

                total_matches += 1
                logger.info("Matched subscription %d (%s) → item: %s",
                          sub["id"], sub["media_name"], item_title[:50])

            source.sync_status = "ok" if total_matches > 0 or len(items) > 0 else "idle"
            source.error_message = None

        await session.commit()

    if total_matches > 0:
        await _broadcast("subscription.matched", {"matches": total_matches})
        # ── Trigger transfer_task for newly created transfers ──
        from app.core.celery_app import celery_app
        async with async_session_factory() as session:
            result = await session.execute(
                select(TransferTask).where(
                    TransferTask.status == TransferStatus.submitted,
                    TransferTask.next_download_retry_at.is_(None),
                )
            )
            for t in result.scalars().all():
                try:
                    celery_app.send_task("app.tasks.transfer.transfer_task", args=[t.id])
                except Exception:
                    pass
    logger.info("Subscription check done: %d matched", total_matches)
    return {"status": "completed", "subscriptions_checked": len(subscriptions), "matches": total_matches}


def _fetch_rss(url: str) -> list[dict]:
    """Fetch and parse a BT4G RSS feed.

    Returns a list of items, each with keys: title, link, guid.
    """
    import httpx

    try:
        resp = httpx.get(url, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Failed to fetch RSS %s: %s", url, e)
        return []

    items = []
    try:
        root = ET.fromstring(resp.text)
        # RSS 2.0 namespace: items are under channel/item
        for item in root.iter("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            guid_el = item.find("guid")
            title_text = title_el.text.strip() if title_el is not None and title_el.text else ""
            if title_text:
                items.append({
                    "title": title_text,
                    "link": link_el.text.strip() if link_el is not None and link_el.text else "",
                    "guid": guid_el.text.strip() if guid_el is not None and guid_el.text else "",
                })
    except ET.ParseError as e:
        logger.warning("Failed to parse RSS XML from %s: %s", url, e)

    logger.info("Fetched %d items from %s", len(items), url)
    return items


@celery_app.task(bind=True, max_retries=3)
def check_subscriptions(self) -> dict:
    """Check all active subscriptions against BT4G RSS feeds."""
    import asyncio
    return asyncio.run(_run_subscription_check())


@celery_app.task(bind=True, max_retries=3)
def scan_single_source(self, source_id: int) -> dict:
    """Scan a single RSS source and match against all active subscriptions."""
    logger.info("Scanning single RSS source: id=%d", source_id)
    import asyncio
    return asyncio.run(_run_subscription_check(source_id=source_id))
