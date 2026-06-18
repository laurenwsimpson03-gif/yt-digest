"""
db.py — Persistent storage via GitHub Gist.
Seen video IDs, feedback, creator scores, and state
are stored in a private Gist so they survive forever
across GitHub Actions runs — no cache expiry, no repeats.
"""

import os
import json
import sqlite3
import requests
from datetime import datetime

# ── Local SQLite (in-run scratch) ─────────────────────────
DB_PATH = "/tmp/digest.db"

GIST_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GIST_ID    = os.environ.get("GIST_ID", "")
GIST_FILE  = "yt_digest_db.json"


# ── Gist sync helpers ─────────────────────────────────────

def _gist_headers():
    return {
        "Authorization": f"token {GIST_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def _load_gist() -> dict:
    """Pull latest data from Gist into a dict."""
    if not GIST_ID:
        return {}
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            headers=_gist_headers(), timeout=10
        )
        r.raise_for_status()
        content = r.json()["files"][GIST_FILE]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"  ⚠ Could not load Gist: {e}")
        return {}


def _save_gist(data: dict):
    """Push updated data dict back to Gist."""
    if not GIST_ID:
        return
    try:
        r = requests.patch(
            f"https://api.github.com/gists/{GIST_ID}",
            headers=_gist_headers(),
            json={"files": {GIST_FILE: {"content": json.dumps(data, indent=2)}}},
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        print(f"  ⚠ Could not save Gist: {e}")


# ── In-memory state (loaded once per run) ─────────────────

_store = None

def _get_store() -> dict:
    global _store
    if _store is None:
        _store = _load_gist()
        if not _store:
            _store = {
                "seen_videos": {},      # video_id → {title, channel, seen_at, score}
                "feedback": [],         # [{video_id, action, created_at}]
                "creator_scores": {},   # channel_id → {up, down}
                "state": {},            # key → value
            }
    return _store


def _flush():
    """Write in-memory state back to Gist."""
    _save_gist(_get_store())


# ── Public API (same interface as before) ─────────────────

def init_db():
    """No-op — Gist is initialized on first access."""
    _get_store()


# ── Seen videos ───────────────────────────────────────────

def is_seen(video_id: str) -> bool:
    return video_id in _get_store()["seen_videos"]


def mark_seen(video_id: str, title: str, channel: str, score: float):
    _get_store()["seen_videos"][video_id] = {
        "title": title,
        "channel": channel,
        "seen_at": datetime.utcnow().isoformat(),
        "score": score,
    }
    _flush()


# ── Feedback ──────────────────────────────────────────────

def record_feedback(video_id: str, action: str, channel_id: str = None, channel_name: str = None):
    store = _get_store()
    store["feedback"].append({
        "video_id": video_id,
        "action": action,
        "created_at": datetime.utcnow().isoformat(),
    })
    if channel_id:
        scores = store["creator_scores"].setdefault(channel_id, {"up": 0, "down": 0, "name": channel_name or ""})
        if action == "up":
            scores["up"] += 1
        else:
            scores["down"] += 1
    _flush()


def get_creator_boost(channel_id: str) -> float:
    scores = _get_store()["creator_scores"].get(channel_id)
    if not scores:
        return 1.0
    net = scores.get("up", 0) - scores.get("down", 0)
    return max(0.5, min(1.5, 1.0 + net * 0.1))


# ── State flags ───────────────────────────────────────────

def get_state(key: str):
    return _get_store()["state"].get(key)


def set_state(key: str, value: str):
    _get_store()["state"][key] = value
    _flush()
