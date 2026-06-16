"""
scorer.py — Two-stage LLM relevance scoring via Claude API.
Stage 1: score title + description (cheap).
Stage 2: fetch transcript and re-score if stage 1 >= threshold.
All videos scored in one batched API call per stage.
"""

import os
import json
import anthropic
from poller import get_transcript_snippet
from db import get_creator_boost

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

INTERESTS = """
The user's interests:
1. Science discoveries told in an engaging, colloquial style (not dry academic)
2. Geopolitical and historical storytelling — think Johnny Harris, Fall of Civilizations,
   Kings and Generals, CaspianReport. Narrative-driven, well-produced, long-form.
3. Palestine / Middle East history from multiple perspectives.

High score (8–10): Clearly matches one of the above, long-form, narrative storytelling style.
Mid score (5–7): Loosely related, or topic match but unclear production quality.
Low score (1–4): Off-topic, clickbait, reaction video, or too surface-level.
"""


def _batch_score(videos: list[dict], use_transcript: bool = False) -> dict[str, float]:
    """
    Score a batch of videos in one Claude API call.
    Returns {video_id: score} dict.
    """
    if not videos:
        return {}

    items = []
    for v in videos:
        text = f"Title: {v['title']}\nChannel: {v['channel_name']}\n"
        text += f"Description: {v['description']}"
        if use_transcript and v.get("transcript"):
            text += f"\nTranscript excerpt: {v['transcript']}"
        items.append({"video_id": v["video_id"], "text": text})

    prompt = f"""{INTERESTS}

Score each video 1–10 for relevance to the user's interests.
Return ONLY a JSON object mapping video_id to score. Example:
{{"abc123": 8, "xyz789": 3}}

Videos to score:
{json.dumps(items, indent=2)}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Strip markdown fences if present
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def score_videos(videos: list[dict], cfg: dict) -> list[dict]:
    """
    Two-stage scoring:
    1. Score all videos on title + description.
    2. For videos >= transcript_min_score, fetch transcript and re-score.
    Returns videos with 'relevance_score' field, sorted descending.
    """
    scoring_cfg = cfg.get("scoring", {})
    threshold = scoring_cfg.get("transcript_min_score", 6)

    # Stage 1
    print(f"  → Stage 1: scoring {len(videos)} videos on title/description...")
    stage1_scores = _batch_score(videos, use_transcript=False)

    for v in videos:
        v["relevance_score"] = stage1_scores.get(v["video_id"], 0)

    # Stage 2: fetch transcripts for promising videos
    candidates = [v for v in videos if v["relevance_score"] >= threshold]
    print(f"  → Stage 2: fetching transcripts for {len(candidates)} candidates...")

    for v in candidates:
        v["transcript"] = get_transcript_snippet(v["video_id"])

    if candidates:
        stage2_scores = _batch_score(candidates, use_transcript=True)
        for v in candidates:
            if v["video_id"] in stage2_scores:
                v["relevance_score"] = stage2_scores[v["video_id"]]

    # Apply creator feedback boost
    for v in videos:
        boost = get_creator_boost(v["channel_id"])
        v["relevance_score"] = round(v["relevance_score"] * boost, 2)

    # Sort by score
    videos.sort(key=lambda x: x["relevance_score"], reverse=True)
    return videos
