
"""
poller.py — Fetches videos from known creators + topic searches.
Returns a list of candidate video dicts for scoring.
"""

import os
import re
import isodate
import requests
from datetime import datetime, timedelta, timezone

YT_KEY = os.environ["YOUTUBE_API_KEY"]
BASE = "https://www.googleapis.com/youtube/v3"


# ── Helpers ───────────────────────────────────────────────

def _get(endpoint: str, **params) -> dict:
    params["key"] = YT_KEY
    r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def _parse_duration_minutes(iso: str) -> float:
    try:
        return isodate.parse_duration(iso).total_seconds() / 60
    except Exception:
        return 0.0


def _published_since(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_uploads_playlist(channel_id: str) -> str | None:
    data = _get("channels", part="contentDetails", id=channel_id)
    items = data.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _enrich_videos(video_ids: list[str]) -> list[dict]:
    """Fetch duration, view count, description for a list of video IDs."""
    if not video_ids:
        return []
    data = _get(
        "videos",
        part="snippet,contentDetails,statistics",
        id=",".join(video_ids),
    )
    results = []
    for item in data.get("items", []):
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        duration_min = _parse_duration_minutes(
            item["contentDetails"].get("duration", "PT0S")
        )
        results.append({
            "video_id": item["id"],
            "title": snippet["title"],
            "channel_id": snippet["channelId"],
            "channel_name": snippet["channelTitle"],
            "description": snippet.get("description", "")[:500],
            "published_at": snippet["publishedAt"],
            "duration_minutes": duration_min,
            "view_count": int(stats.get("viewCount", 0)),
            "url": f"https://www.youtube.com/watch?v={item['id']}",
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
            "source": "known_creator",
        })
    return results


# ── Known creator polling ─────────────────────────────────

def poll_known_creators(creator_ids: list[str], days_back: int = 7) -> list[dict]:
    """Pull recent uploads from known channels."""
    since = _published_since(days_back)
    all_videos = []

    for channel_id in creator_ids:
        playlist_id = _get_uploads_playlist(channel_id)
        if not playlist_id:
            print(f"  ⚠ Could not find uploads playlist for {channel_id} — skipping")
            continue

        data = _get(
            "playlistItems",
            part="snippet",
            playlistId=playlist_id,
            maxResults=10,
        )

        recent_ids = []
        for item in data.get("items", []):
            pub = item["snippet"]["publishedAt"]
            if pub >= since:
                vid_id = item["snippet"]["resourceId"]["videoId"]
                recent_ids.append(vid_id)

        if recent_ids:
            videos = _enrich_videos(recent_ids)
            all_videos.extend(videos)

    return all_videos


# ── Topic-based discovery ─────────────────────────────────

def search_topics(topics: list[str], max_per_topic: int = 5) -> list[dict]:
    """Search YouTube for new creators by topic keyword."""
    since = _published_since(30)
    seen_ids = set()
    all_videos = []

    for topic in topics:
        data = _get(
            "search",
            part="snippet",
            q=topic,
            type="video",
            videoDuration="long",
            order="relevance",
            publishedAfter=since,
            maxResults=max_per_topic,
        )

        video_ids = []
        for item in data.get("items", []):
            vid_id = item["id"]["videoId"]
            if vid_id not in seen_ids:
                seen_ids.add(vid_id)
                video_ids.append(vid_id)

        if video_ids:
            videos = _enrich_videos(video_ids)
            for v in videos:
                v["source"] = "topic_discovery"
            all_videos.extend(videos)

    return all_videos


# ── Transcript fetching ───────────────────────────────────

def get_transcript_snippet(video_id: str, max_chars: int = 800) -> str:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(entry["text"] for entry in transcript)
        return text[:max_chars]
    except Exception:
        return ""


# ── Filters ───────────────────────────────────────────────

def apply_filters(videos: list[dict], cfg: dict) -> list[dict]:
    """Apply duration, view count, and keyword exclusion filters."""
    f = cfg["filters"]
    min_dur = f.get("min_duration_minutes") or 0
    max_dur = f.get("max_duration_minutes") or 9999
    min_views = f.get("min_view_count") or 0
    exclude = [kw.lower() for kw in f.get("exclude_keywords", [])]

    filtered = []
    for v in videos:
        dur = v.get("duration_minutes") or 0
        if dur < min_dur:
            continue
        if dur > max_dur:
            continue
        if v.get("view_count", 0) < min_views:
            continue
        title_lower = v.get("title", "").lower()
        if any(kw in title_lower for kw in exclude):
            continue
        filtered.append(v)

    return filtered
