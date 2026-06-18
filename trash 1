"""
db.py — SQLite database layer.
Handles: seen videos, feedback signals, creator scores.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "digest.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS seen_videos (
                video_id    TEXT PRIMARY KEY,
                title       TEXT,
                channel     TEXT,
                seen_at     TEXT DEFAULT (datetime('now')),
                score       REAL
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id    TEXT NOT NULL,
                action      TEXT NOT NULL,  -- 'up' or 'down'
                created_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS creator_scores (
                channel_id  TEXT PRIMARY KEY,
                channel_name TEXT,
                up_count    INTEGER DEFAULT 0,
                down_count  INTEGER DEFAULT 0,
                last_seen   TEXT
            );

            CREATE TABLE IF NOT EXISTS state (
                key         TEXT PRIMARY KEY,
                value       TEXT
            );
        """)


# ── Seen videos ──────────────────────────────────────────

def is_seen(video_id: str) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_videos WHERE video_id = ?", (video_id,)
        ).fetchone()
    return row is not None


def mark_seen(video_id: str, title: str, channel: str, score: float):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO seen_videos (video_id, title, channel, score)
               VALUES (?, ?, ?, ?)""",
            (video_id, title, channel, score),
        )


# ── Feedback ─────────────────────────────────────────────

def record_feedback(video_id: str, action: str, channel_id: str = None, channel_name: str = None):
    """Record thumbs up/down and update creator score."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO feedback (video_id, action) VALUES (?, ?)",
            (video_id, action),
        )
        if channel_id:
            col = "up_count" if action == "up" else "down_count"
            conn.execute(
                f"""INSERT INTO creator_scores (channel_id, channel_name, {col}, last_seen)
                    VALUES (?, ?, 1, datetime('now'))
                    ON CONFLICT(channel_id) DO UPDATE SET
                        {col} = {col} + 1,
                        last_seen = datetime('now')""",
                (channel_id, channel_name or ""),
            )


def get_creator_boost(channel_id: str) -> float:
    """
    Returns a score multiplier based on feedback history.
    Channels you thumbs-up get boosted; thumbs-down get penalized.
    Range: 0.5 (avoid) → 1.5 (prefer)
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT up_count, down_count FROM creator_scores WHERE channel_id = ?",
            (channel_id,),
        ).fetchone()
    if not row:
        return 1.0
    net = row["up_count"] - row["down_count"]
    return max(0.5, min(1.5, 1.0 + net * 0.1))


# ── State flags ───────────────────────────────────────────

def get_state(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM state WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else None


def set_state(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
            (key, value),
        )
