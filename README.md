# 📺 YouTube Video Digest

Automated daily digest of video essays matching your interests.
Delivered by email with one-click playlist add (👍) and feedback (👎) buttons.

---

## What It Does

- Polls your known creators daily for new uploads
- Discovers new creators via topic search
- Scores videos with Claude AI (title → transcript two-stage filter)
- Sends an HTML email at 6am PST with your top 10
- Clicking 👍 adds the video straight to your YouTube playlist
- Clicking 👎 teaches the system to show less like it
- Never recommends the same video twice

---

## Setup (~20 minutes total)

### Step 1 — Fork / clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/yt-digest
cd yt-digest
```

### Step 2 — YouTube Data API key + OAuth

**API Key (for reading data):**
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Go to **APIs & Services → Library**
4. Enable **YouTube Data API v3**
5. Go to **APIs & Services → Credentials → Create Credentials → API Key**
6. Copy the key — this is your `YOUTUBE_API_KEY`

**OAuth (for writing to your playlist):**
1. In the same project, go to **Credentials → Create Credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Download the JSON file
4. Run the one-time auth flow:
```bash
pip install -r requirements.txt
python auth_setup.py
```
5. This opens a browser, you log in, and it saves `credentials.json`
6. Run: `python -c "import json; print(json.dumps(json.load(open('credentials.json'))))"` 
7. Copy the output — this is your `GOOGLE_CREDENTIALS_JSON` secret

### Step 3 — Create your YouTube Playlist

1. Go to YouTube → Your channel → Playlists → New Playlist
2. Name it "Digest Inbox" (or anything)
3. Open the playlist, copy the ID from the URL:
   `youtube.com/playlist?list=`**`PLxxxxxxxxxxxxxxxx`** ← this part
4. This is your `YOUTUBE_PLAYLIST_ID`

### Step 4 — SendGrid (free email sending)

1. Go to https://sendgrid.com → sign up (free tier = 100 emails/day)
2. Go to **Settings → API Keys → Create API Key** (Full Access)
3. Copy it — this is your `SENDGRID_API_KEY`
4. Go to **Settings → Sender Authentication** and verify your email address
5. That verified email is your `FROM_EMAIL`

### Step 5 — Deploy the webhook to Railway

The webhook is a tiny Flask server that handles your button clicks.

1. Go to https://railway.app → sign up (free tier is enough)
2. Click **New Project → Deploy from GitHub repo**
3. Select this repo
4. Set the start command: `python webhook.py`
5. Add environment variables (see Step 6 — add the same secrets)
6. Copy your Railway public URL (e.g. `https://yt-digest-production.up.railway.app`)
   — this is your `WEBHOOK_URL`

### Step 6 — Add GitHub Secrets

In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret name | Value |
|---|---|
| `YOUTUBE_API_KEY` | From Step 2 |
| `ANTHROPIC_API_KEY` | From https://console.anthropic.com |
| `SENDGRID_API_KEY` | From Step 4 |
| `FROM_EMAIL` | Your verified SendGrid sender email |
| `TO_EMAIL` | Where you want the digest delivered |
| `WEBHOOK_URL` | Your Railway app URL (no trailing slash) |
| `GOOGLE_CREDENTIALS_JSON` | The JSON string from Step 2 |
| `YOUTUBE_PLAYLIST_ID` | From Step 3 |

### Step 7 — Add your creators

Edit `config.yaml` and add any creator channel IDs:

```yaml
creators:
  - id: UCmGSJVG3mCRXVOP4yZrU1Dw  # Johnny Harris
  - id: UCIjivfwXSRdCO_QzQFUnkBg  # Fall of Civilizations
```

**How to find a channel ID:**
- Go to the channel on YouTube
- View page source (Ctrl+U) and search for `"channelId"`
- Or use: https://commentpicker.com/youtube-channel-id.php

### Step 8 — Test it manually

In GitHub → **Actions → Daily Video Digest → Run workflow**

Check your inbox within ~2 minutes.

---

## Customization

Everything lives in `config.yaml`. Edit and push to change behavior:

- **Add a creator:** add a line under `creators:`
- **Add a topic:** add a line under `topics:`
- **Change number of videos:** edit `max_videos_per_email`
- **Change length filter:** edit `min_duration_minutes` / `max_duration_minutes`
- **Change send time:** edit `cron` in `.github/workflows/digest.yml`

---

## File Overview

| File | Purpose |
|---|---|
| `config.yaml` | Your preferences — edit freely |
| `main.py` | Daily orchestrator |
| `poller.py` | YouTube API fetching |
| `scorer.py` | Claude AI relevance scoring |
| `digest.py` | HTML email builder + sender |
| `webhook.py` | Flask server for button feedback |
| `db.py` | SQLite: seen videos, feedback, scores |
| `requirements.txt` | Python dependencies |

---

## Quota Usage (YouTube API — 10,000 units/day free)

| Operation | Units | Daily estimate |
|---|---|---|
| Channel metadata | ~4 per creator | ~20 |
| Uploads playlist | ~3 per creator | ~15 |
| Video details | 1 per video | ~50 |
| Topic search | 100 per query | ~600 |
| Playlist insert | 50 per add | ~50 |
| **Total** | | **~735 / 10,000** |

You have plenty of headroom to add more creators and topics.
