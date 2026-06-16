"""
main.py — Daily orchestrator. Run by GitHub Actions.
"""

import yaml
import db
from poller import poll_known_creators, search_topics, apply_filters
from scorer import score_videos
from digest import build_email, send_email


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def main():
    print("── YouTube Digest ─────────────────────────────")
    cfg = load_config()
    db.init_db()

    # ── 1. Collect videos ────────────────────────────────
    creator_ids = [c["id"] for c in cfg.get("creators", [])]
    topics = cfg.get("topics", [])

    print(f"Polling {len(creator_ids)} known creators...")
    known_videos = poll_known_creators(creator_ids, days_back=7)
    print(f"  → {len(known_videos)} videos found")

    print(f"Searching {len(topics)} topics for discovery...")
    discovered_videos = search_topics(topics, max_per_topic=5)
    print(f"  → {len(discovered_videos)} videos found")

    all_videos = known_videos + discovered_videos

    # ── 2. Dedup against seen history ────────────────────
    fresh = [v for v in all_videos if not db.is_seen(v["video_id"])]
    print(f"After dedup: {len(fresh)} fresh videos")

    # ── 3. Apply config filters ──────────────────────────
    filtered = apply_filters(fresh, cfg)
    print(f"After filters: {len(filtered)} videos")

    # ── 4. Score ─────────────────────────────────────────
    if filtered:
        print("Scoring...")
        scored = score_videos(filtered, cfg)
    else:
        scored = []

    # ── 5. Select top N ──────────────────────────────────
    max_n = cfg["digest"].get("max_videos_per_email", 10)
    top = scored[:max_n]

    # ── 6. Mark as seen ──────────────────────────────────
    for v in top:
        db.mark_seen(v["video_id"], v["title"], v["channel_name"], v["relevance_score"])

    # ── 7. First-run Palestine card ───────────────────────
    include_palestine = False
    if cfg.get("first_run_palestine_card"):
        already_sent = db.get_state("palestine_card_sent")
        if not already_sent:
            include_palestine = True
            db.set_state("palestine_card_sent", "true")
            print("Including Palestine recommendation card (first run)")

    # ── 8. Build + send email ────────────────────────────
    if top or include_palestine:
        print(f"Sending digest with {len(top)} videos...")
        html = build_email(top, include_palestine_card=include_palestine)
        send_email(html)
    else:
        print("No videos to send today.")

    print("── Done ────────────────────────────────────────")


if __name__ == "__main__":
    main()
