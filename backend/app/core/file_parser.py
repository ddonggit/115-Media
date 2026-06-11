"""Regex-based file name parser — Chinese & Western formats."""
import re
from typing import Any

# ── Pre-clean ──────────────────────────────────────────────────────

CLEAN_PATTERNS = [
    (r"^【.*?】\s*", ""),                         # strip 【...】 prefix
    (r"第\s*(\d+)\s*[-–—~至]\s*(\d+)\s*集", r"E\1-E\2"),  # 第N-M集 → EN-EM
    (r"第\s*(\d+)\s*集", r"E\1"),                 # 第N集 → EN
    (r"第\s*(\d+)\s*季", r"S\1"),                 # 第N季 → SN
    (r"[【】\[\]《》（）]", " "),                  # normalize brackets to space
    (r"\s+", " "),                                # collapse whitespace
]

# ── Comprehensive filename regex ───────────────────────────────────
# Supports both: Title.2024.S01E05.1080p.mkv and Title.S01E05.2024.1080p.mkv

RE_FULL = re.compile(
    r"""
    ^
    (?P<title>.*?)
    [.\s\-_]+
    # Year or season/episode (either order)
    (?:
        (?P<year>(?:19|20)\d{2})
        .*?
        (?:S(?P<season>\d{1,2}))?
        (?:E(?P<episode>\d{1,4}))?
        |
        (?:S(?P<season2>\d{1,2}))?
        (?:E(?P<episode2>\d{1,4}))?
        .*?
        (?P<year2>(?:19|20)\d{2})
    )
    .*?
    (?P<resolution>2160p|1080p|720p|4K|UHD|HD)?
    .*?
    (?P<source>
        BluRay|Blu-ray|WEB-DL|WEBRip|HDRip|DVDRip|BDRip|
        WEB\.DL|WEB\.Rip|HDTV|DVD|REMUX
    )?
    .*?
    (?P<version>IMAX|3D|CC|Director.?s.Cut|Extended|Criterion)?
    .*?
    (?P<effect>DV\.?HDR|HDR\d*|SDR|DolbyVision)?
    .*?
    (?P<video_codec>
        x264|x265|H\.264|H\.265|HEVC|AVC|AV1|REMUX|10bit|8bit
    )?
    .*?
    (?P<audio_codec>
        TrueHD|DTS-HD|DTS\.?HD|DTS|AC3|AAC|FLAC|EAC3|Atmos|LPCM|PCM
    )?
    .*?
    (?P<fps>\d{2,3}FPS)?
    .*?
    (?P<country>
        USA|UK|FR|DE|JP|CN|KR|TW|HK|IT|ES|AU|CA|NF|AMZN|HMAX
    )?
    .*?
    (?P<group>-[\w.]+)?
    \.(?:mkv|mp4|avi|ts|m2ts|iso|bdmv|m4v|mov|wmv|flv|webm)$
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Simpler fallback for edge cases
RE_SIMPLE = re.compile(
    r"""
    ^(?P<title>.+?)
    [.\s\-_]+(?P<year>(?:19|20)\d{2}).*
    \.(?:mkv|mp4|avi|ts|m2ts|iso|bdmv|m4v|mov|wmv|flv|webm)$
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Multi-episode range regex (applied after pre-clean) — matches E05-E08, E05-08
RE_EPISODE_RANGE = re.compile(r"E(\d{1,4})\s*[-–]\s*E?(\d{1,4})", re.IGNORECASE)

# Pack/complete collection detection
RE_PACK = re.compile(
    r"(?:全集|合集|全一季|Complete|Pack|全\d+集|全\d+话)",
    re.IGNORECASE,
)


def pre_clean(filename: str) -> str:
    """Apply pre-cleaning transformations to normalize a filename."""
    name = filename.strip()
    for pattern, replacement in CLEAN_PATTERNS:
        name = re.sub(pattern, replacement, name)
    return name.strip()


def parse_filename(filename: str) -> dict[str, Any] | None:
    """Parse a media filename into its components.

    Returns a dict with keys: title, year, season, episode, episode_start,
    episode_end, is_pack, resolution, source, version, effect, video_codec,
    audio_codec, fps, country, group
    or None if it can't be parsed at all.

    For single-episode files: episode == episode_start == episode_end.
    For multi-episode files (S01E05-E08): episode_start=5, episode_end=8,
    episode=episode_start.
    For pack/complete collections: is_pack=True.
    """
    cleaned = pre_clean(filename)

    # Quick pre-check: if no known extension, don't attempt the expensive regex
    # (avoids catastrophic backtracking on RSS titles without extensions)
    has_ext = bool(re.search(r'\.(?:mkv|mp4|avi|ts|m2ts|iso|bdmv|m4v|mov|wmv|flv|webm)\b', cleaned, re.IGNORECASE))

    m = None
    if has_ext:
        m = RE_FULL.match(cleaned)
        if not m:
            m = RE_SIMPLE.match(cleaned)

    if not m:
        return None

    result: dict[str, Any] = {}
    for key in (
        "title", "year", "season", "episode",
        "resolution", "source", "version", "effect",
        "video_codec", "audio_codec", "fps", "country", "group",
    ):
        val = m.group(key)
        if val is not None:
            result[key] = val.strip().rstrip(".")
        else:
            result[key] = None

    # Unify alternation groups (season2/episode2 from year-second order)
    if result["season"] is None:
        result["season"] = m.group("season2")
    if result["episode"] is None:
        result["episode"] = m.group("episode2")
    if result["year"] is None:
        result["year"] = m.group("year2")

    # Normalize
    if result["year"]:
        result["year"] = int(result["year"])
    if result["season"]:
        result["season"] = int(result["season"])
    if result["episode"]:
        result["episode"] = int(result["episode"])
    if result["resolution"]:
        raw = result["resolution"].upper()
        if raw == "4K" or raw == "UHD":
            result["resolution"] = "2160p"
        elif raw == "HD":
            result["resolution"] = "720p"
        else:
            result["resolution"] = raw  # 1080p, 720p preserved
    if result["title"]:
        result["title"] = result["title"].replace(".", " ").replace("_", " ").strip()
    if result.get("group"):
        result["group"] = result["group"].lstrip("-")

    # ── Multi-episode range detection ──────────────────────────
    # Check cleaned text for E05-E08 patterns
    range_match = RE_EPISODE_RANGE.search(cleaned)
    if range_match:
        result["episode_start"] = int(range_match.group(1))
        result["episode_end"] = int(range_match.group(2))
    else:
        result["episode_start"] = result.get("episode")
        result["episode_end"] = result.get("episode")

    # ── Pack / complete collection detection ───────────────────
    # Check the original filename (before clean) for Chinese pack keywords,
    # and the cleaned name for English pack keywords
    result["is_pack"] = bool(RE_PACK.search(filename) or RE_PACK.search(cleaned))

    return result
