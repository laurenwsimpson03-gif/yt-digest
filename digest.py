"""
digest.py — Builds and sends the HTML digest email.
Includes thumbs up/down buttons that hit the webhook.
First-run includes the hardcoded Palestine recommendation card.
"""

import os
import sendgrid
from sendgrid.helpers.mail import Mail, To
from datetime import datetime

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-railway-app.up.railway.app")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "digest@yourdomain.com")
TO_EMAIL = os.environ.get("TO_EMAIL", "")

# ── Palestine hardcoded recommendation ───────────────────
PALESTINE_CARD = {
    "title": "1948: Creation & Catastrophe",
    "channel": "Documentary — Dir. Ahlam Muhtaseb & Andy Trimlett",
    "url": "https://www.youtube.com/watch?v=adsW1qdk-X8",
    "thumbnail": "https://img.youtube.com/vi/adsW1qdk-X8/hqdefault.jpg",
    "duration": "1h 25m",
    "why": (
        "The definitive oral-history documentary on 1948 — the year Israel was founded "
        "and 750,000 Palestinians were displaced. Built from first-hand testimonies of "
        "both Israelis and Palestinians who lived through it, it gives you the human-level "
        "foundation you need before diving into anything else on this topic. "
        "Reviewed and screened at MIT, UCI, and CSUSB. 7.8/10 on IMDb. Free on YouTube."
    ),
}


# ── HTML helpers ─────────────────────────────────────────

def _video_card(v: dict, index: int) -> str:
    thumb = v.get("thumbnail", "")
    feedback_up = f"{WEBHOOK_URL}/feedback?action=up&video_id={v['video_id']}&channel_id={v['channel_id']}&channel_name={v['channel_name'].replace(' ', '+')}"
    feedback_down = f"{WEBHOOK_URL}/feedback?action=down&video_id={v['video_id']}&channel_id={v['channel_id']}&channel_name={v['channel_name'].replace(' ', '+')}"
    duration = f"{int(v['duration_minutes'])}m"
    score = v.get("relevance_score", "—")
    source_badge = "📡 Known creator" if v.get("source") == "known_creator" else "🔍 Discovery"

    return f"""
    <div style="display:flex;gap:16px;margin-bottom:28px;padding-bottom:28px;border-bottom:1px solid #e5e7eb;">
      <a href="{v['url']}" target="_blank" style="flex-shrink:0;">
        <img src="{thumb}" width="180" height="100"
             style="object-fit:cover;border-radius:8px;display:block;" />
      </a>
      <div style="flex:1;">
        <div style="font-size:11px;color:#6b7280;margin-bottom:4px;">
          {source_badge} &nbsp;·&nbsp; {duration} &nbsp;·&nbsp; Score: {score}/10
        </div>
        <a href="{v['url']}" target="_blank"
           style="font-size:16px;font-weight:600;color:#111827;text-decoration:none;line-height:1.3;">
          {v['title']}
        </a>
        <div style="font-size:13px;color:#6b7280;margin-top:4px;">{v['channel_name']}</div>
        <div style="margin-top:10px;display:flex;gap:8px;">
          <a href="{feedback_up}"
             style="display:inline-block;padding:6px 14px;background:#16a34a;color:#fff;
                    border-radius:6px;font-size:13px;text-decoration:none;">
            👍 Add to Playlist
          </a>
          <a href="{feedback_down}"
             style="display:inline-block;padding:6px 14px;background:#f3f4f6;color:#374151;
                    border-radius:6px;font-size:13px;text-decoration:none;">
            👎 Not for me
          </a>
        </div>
      </div>
    </div>"""


def _palestine_card() -> str:
    c = PALESTINE_CARD
    return f"""
    <div style="background:#fef9c3;border:2px solid #fbbf24;border-radius:12px;
                padding:20px;margin-bottom:32px;">
      <div style="font-size:12px;font-weight:700;color:#92400e;letter-spacing:.05em;
                  text-transform:uppercase;margin-bottom:8px;">
        🎬 Recommended Starting Point — Palestine History
      </div>
      <div style="display:flex;gap:16px;align-items:flex-start;">
        <a href="{c['url']}" target="_blank" style="flex-shrink:0;">
          <img src="{c['thumbnail']}" width="160" height="90"
               style="object-fit:cover;border-radius:8px;" />
        </a>
        <div>
          <a href="{c['url']}" target="_blank"
             style="font-size:17px;font-weight:700;color:#111827;text-decoration:none;">
            {c['title']}
          </a>
          <div style="font-size:12px;color:#6b7280;margin:3px 0 8px;">{c['channel']} · {c['duration']}</div>
          <div style="font-size:13px;color:#374151;line-height:1.5;">{c['why']}</div>
          <a href="{c['url']}" target="_blank"
             style="display:inline-block;margin-top:12px;padding:7px 16px;
                    background:#1d4ed8;color:#fff;border-radius:6px;
                    font-size:13px;text-decoration:none;">
            Watch on YouTube →
          </a>
        </div>
      </div>
    </div>"""


def build_email(videos: list[dict], include_palestine_card: bool = False) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    cards = "".join(_video_card(v, i) for i, v in enumerate(videos))
    palestine_section = _palestine_card() if include_palestine_card else ""

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:640px;margin:32px auto;background:#fff;border-radius:12px;
              box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden;">

    <!-- Header -->
    <div style="background:#111827;padding:24px 32px;">
      <div style="font-size:20px;font-weight:700;color:#fff;">🎬 Video Essay Recs</div>
      <div style="font-size:13px;color:#9ca3af;margin-top:4px;">{today}</div>
    </div>

    <!-- Body -->
    <div style="padding:28px 32px;">
      {palestine_section}
      {cards}
    </div>

    <!-- Footer -->
    <div style="background:#f3f4f6;padding:16px 32px;font-size:12px;color:#9ca3af;text-align:center;">
      👍 adds video to your YouTube playlist &nbsp;·&nbsp; 👎 helps filter future results<br>
      <a href="{WEBHOOK_URL}/unsubscribe" style="color:#9ca3af;">Unsubscribe</a>
    </div>
  </div>
</body>
</html>"""


def send_email(html: str, subject: str = None):
    if not TO_EMAIL:
        raise ValueError("TO_EMAIL env var not set")
    if not subject:
        subject = f"🎬 Video Essay Recs — {datetime.now().strftime('%b %d')}"

    sg = sendgrid.SendGridAPIClient(api_key=os.environ["SENDGRID_API_KEY"])
    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=To(TO_EMAIL),
        subject=subject,
        html_content=html,
    )
    response = sg.send(message)
    print(f"  ✉ Email sent — status {response.status_code}")
