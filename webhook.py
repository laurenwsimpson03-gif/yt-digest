"""
webhook.py — Flask webhook server (deploy to Railway).
Handles thumbs up (→ add to playlist) and thumbs down (→ log signal).
"""

import os
import json
from flask import Flask, request, jsonify, redirect
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import db

app = Flask(__name__)

PLAYLIST_ID = os.environ.get("YOUTUBE_PLAYLIST_ID", "")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS_JSON", "{}")


def _get_youtube_client():
    creds_data = json.loads(GOOGLE_CREDENTIALS)
    creds = Credentials(
        token=creds_data.get("token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret"),
    )
    return build("youtube", "v3", credentials=creds)


def _add_to_playlist(video_id: str) -> bool:
    try:
        yt = _get_youtube_client()
        yt.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": PLAYLIST_ID,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            },
        ).execute()
        return True
    except Exception as e:
        print(f"  ⚠ Playlist insert failed: {e}")
        return False


@app.route("/feedback")
def feedback():
    action = request.args.get("action")          # 'up' or 'down'
    video_id = request.args.get("video_id")
    channel_id = request.args.get("channel_id", "")
    channel_name = request.args.get("channel_name", "")

    if not action or not video_id:
        return jsonify({"error": "Missing action or video_id"}), 400

    db.init_db()
    db.record_feedback(video_id, action, channel_id, channel_name)

    if action == "up":
        added = _add_to_playlist(video_id)
        msg = "Added to playlist! ✅" if added else "Logged — playlist add failed ⚠"
    else:
        msg = "Got it — we'll show less like this. 👎"

    # Return a simple confirmation page
    return f"""
    <html><body style="font-family:sans-serif;max-width:480px;margin:80px auto;text-align:center;">
      <div style="font-size:48px;margin-bottom:16px;">{'✅' if action == 'up' else '👎'}</div>
      <div style="font-size:20px;font-weight:600;">{msg}</div>
      <div style="margin-top:24px;">
        <a href="https://www.youtube.com/watch?v={video_id}" target="_blank"
           style="color:#1d4ed8;">Watch on YouTube →</a>
      </div>
      <div style="margin-top:40px;font-size:13px;color:#9ca3af;">You can close this tab.</div>
    </body></html>
    """


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    db.init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
