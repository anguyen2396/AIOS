"""
Morning Brew Cloud — combined daily brief + AI digest for GitHub Actions.
Part 1 (Your Day): reads context/action-items.md, syncs to Google Calendar, builds brief.
Part 2 (AI World): uses OpenAI web search to pull AI news, YouTube, Anthropic, tool drops.
Sends one combined HTML email via Gmail API.

Usage: python scripts/morning_brew_cloud.py
Env vars: OPENAI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
Falls back to .env file if env vars not set.
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

BANGKOK = timezone(timedelta(hours=7))
REPO_ROOT = Path(__file__).parent.parent
TARGET_EMAIL = "austinngg996@gmail.com"

YOUTUBE_CHANNELS = [
    "Nate Herk",
    "Tina Huang",
    "Greg Isenberg",
    "Matthew Berman",
]


# ── Credentials ───────────────────────────────────────────────────────────────

def _load_env():
    env_path = REPO_ROOT / ".env"
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def _get_creds():
    openai_key    = os.environ.get("OPENAI_API_KEY")
    client_id     = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        env = _load_env()
        openai_key    = openai_key    or env.get("OPENAI_API_KEY")
        client_id     = client_id     or env.get("GOOGLE_CLIENT_ID")
        client_secret = client_secret or env.get("GOOGLE_CLIENT_SECRET")
        refresh_token = refresh_token or env.get("GOOGLE_REFRESH_TOKEN")

    missing = [k for k, v in {
        "OPENAI_API_KEY": openai_key,
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_CLIENT_SECRET": client_secret,
        "GOOGLE_REFRESH_TOKEN": refresh_token,
    }.items() if not v]

    if missing:
        print(f"ERROR: Missing credentials: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    return openai_key, client_id, client_secret, refresh_token


# ── OAuth ─────────────────────────────────────────────────────────────────────

def get_access_token(client_id, client_secret, refresh_token):
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["access_token"]


# ── Generic HTTP helper ───────────────────────────────────────────────────────

def api(method, url, token, body=None, params=None):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body else None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"API ERROR {e.code}: {e.read().decode()}", file=sys.stderr)
        raise


# ── OpenAI web search ─────────────────────────────────────────────────────────

def openai_search(api_key: str, prompt: str) -> str:
    payload = json.dumps({
        "model": "gpt-4o",
        "tools": [{"type": "web_search_preview"}],
        "input": prompt,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read())
        for item in data.get("output", []):
            if item.get("type") == "message":
                for block in item.get("content", []):
                    if block.get("type") == "output_text":
                        return block.get("text", "")
    except Exception as e:
        print(f"OpenAI search error: {e}", file=sys.stderr)
    return ""


# ── Date helpers ──────────────────────────────────────────────────────────────

def today_bangkok():
    return datetime.now(BANGKOK).date()


def day_window_iso(date):
    start = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=BANGKOK)
    end   = datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=BANGKOK)
    fmt = "%Y-%m-%dT%H:%M:%S+07:00"
    return start.strftime(fmt), end.strftime(fmt)


def event_start_iso(date, hour=17, minute=0):
    dt = datetime(date.year, date.month, date.day, hour, minute, 0, tzinfo=BANGKOK)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")


# ── Action items + priorities ─────────────────────────────────────────────────

def load_action_items():
    path = REPO_ROOT / "context" / "action-items.md"
    if not path.exists():
        print("WARNING: context/action-items.md not found.", file=sys.stderr)
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*-\s+\[\s\]\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
    return items


def load_priorities():
    path = REPO_ROOT / "context" / "priorities.md"
    if not path.exists():
        return []
    priorities = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if m:
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", m.group(1).strip())
            priorities.append(text)
    return priorities


# ── Google Calendar helpers ───────────────────────────────────────────────────

CALENDAR_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def list_todays_events(token, date):
    time_min, time_max = day_window_iso(date)
    result = api("GET", CALENDAR_BASE, token, params={
        "timeMin": time_min, "timeMax": time_max,
        "singleEvents": "true", "orderBy": "startTime",
    })
    return result.get("items", [])


def title_already_on_calendar(title, events):
    title_lower = title.lower()
    for ev in events:
        summary = ev.get("summary", "").lower()
        if title_lower in summary or summary in title_lower:
            return True
    return False


def create_event(token, date, title, start_hour=17, duration_minutes=30):
    start = event_start_iso(date, start_hour, 0)
    end_dt = datetime(date.year, date.month, date.day, start_hour, duration_minutes, 0, tzinfo=BANGKOK)
    end = end_dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")
    body = {
        "summary": title,
        "start": {"dateTime": start, "timeZone": "Asia/Bangkok"},
        "end":   {"dateTime": end,   "timeZone": "Asia/Bangkok"},
        "description": "Auto-added by AIOS Morning Brew",
    }
    return api("POST", CALENDAR_BASE, token, body=body)


def format_event_time(event):
    start = event.get("start", {})
    dt_str = start.get("dateTime") or start.get("date", "")
    if not dt_str:
        return "All day"
    try:
        dt_str_clean = re.sub(r"([+-]\d{2}):(\d{2})$", lambda m: m.group(1) + m.group(2), dt_str)
        dt = datetime.strptime(dt_str_clean, "%Y-%m-%dT%H:%M:%S%z")
        dt_bkk = dt.astimezone(BANGKOK)
        return dt_bkk.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return dt_str[:16]


def build_schedule_str(events):
    if not events:
        return "none"
    lines = []
    for ev in events:
        time_str = format_event_time(ev)
        summary  = ev.get("summary", "(no title)")
        end_dt_str = ev.get("end", {}).get("dateTime", "")
        end_time = ""
        if end_dt_str:
            try:
                dt_str_clean = re.sub(r"([+-]\d{2}):(\d{2})$", lambda m: m.group(1) + m.group(2), end_dt_str)
                dt = datetime.strptime(dt_str_clean, "%Y-%m-%dT%H:%M:%S%z")
                end_time = " – " + dt.astimezone(BANGKOK).strftime("%I:%M %p").lstrip("0")
            except Exception:
                pass
        lines.append(f"{time_str}{end_time} | {summary}")
    return "\\n".join(lines)


# ── AI World section gatherers ────────────────────────────────────────────────

def gather_ai_sections(openai_key: str, today_str: str) -> dict:
    print("  Fetching AI news...")
    news = openai_search(openai_key, (
        f"Search for the top 5-7 AI news stories from today or yesterday ({today_str}). "
        "For each: headline, source publication, one-sentence summary of what happened and why it matters. "
        "Format: TITLE | SOURCE | SUMMARY. One per line. No markdown."
    ))

    print("  Fetching YouTube updates...")
    channels = ", ".join(YOUTUBE_CHANNELS)
    youtube = openai_search(openai_key, (
        f"Find the most recent YouTube videos (last 14 days) from: {channels}. "
        "For each video: channel name, title, upload date, URL, and a one-sentence description of what the video covers. "
        "Format: CHANNEL | TITLE | DATE | URL | DESCRIPTION. One per line. Skip channels with no recent videos."
    ))

    print("  Fetching Anthropic/Claude updates...")
    anthropic = openai_search(openai_key, (
        f"Find Anthropic or Claude AI announcements from the last 7 days (as of {today_str}). "
        "Include model releases, API changes, new features. One plain sentence per item. "
        "If nothing in last 7 days, respond exactly: No major updates this week."
    ))

    print("  Fetching AI tool drops...")
    tools = openai_search(openai_key, (
        f"Find 3-5 new AI tools or product launches from this week ({today_str}). "
        "Focus on tools for productivity, business automation, consulting, or trading. "
        "Format: TOOL NAME | one-line description | URL. One per line."
    ))

    return {
        "news": news.strip(),
        "youtube": youtube.strip(),
        "anthropic": anthropic.strip(),
        "tools": tools.strip(),
    }


# ── HTML email builder ────────────────────────────────────────────────────────

def parse_lines(raw: str) -> list:
    return [l.strip() for l in raw.splitlines() if l.strip()]


def build_schedule_html(schedule_str):
    if not schedule_str.strip() or schedule_str.strip().lower() == "none":
        return '<p style="margin:0 0 8px;color:#888;font-style:italic;">Nothing scheduled — clear day.</p>'
    lines = [l.strip() for l in schedule_str.replace("\\n", "\n").split("\n") if l.strip()]
    rows = ""
    for line in lines:
        time, title = line.split("|", 1) if "|" in line else ("", line)
        rows += f'<tr><td style="padding:6px 12px 6px 0;color:#888;font-size:13px;white-space:nowrap;vertical-align:top;">{time.strip()}</td><td style="padding:6px 0;color:#1a1a1a;font-size:15px;vertical-align:top;">{title.strip()}</td></tr>'
    return f'<table cellpadding="0" cellspacing="0" style="width:100%">{rows}</table>'


def build_items_html(items):
    if not items:
        return '<p style="margin:0;color:#888;font-style:italic;">No open items.</p>'
    html = ""
    for item in items:
        html += f'<div style="display:flex;align-items:flex-start;margin-bottom:10px;"><span style="min-width:20px;margin-right:10px;color:#4a90d9;font-size:16px;line-height:1.4;">□</span><span style="color:#1a1a1a;font-size:15px;line-height:1.4;">{item}</span></div>'
    return html


def build_priorities_html(p1, p2, p3):
    html = ""
    for n, text in [(1, p1), (2, p2), (3, p3)]:
        if text:
            html += f'<div style="display:flex;align-items:flex-start;margin-bottom:12px;"><span style="color:#e05c2d;font-size:15px;font-weight:800;margin-right:10px;">{n}.</span><span style="color:#1a1a1a;font-size:15px;line-height:1.4;padding-top:4px;">{text}</span></div>'
    return html


def build_news_html(news_str):
    lines = parse_lines(news_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No news items found.</p>'
    html = ""
    for line in lines:
        parts = line.split("|", 2)
        title = parts[0].strip() if parts else line
        source = parts[1].strip() if len(parts) > 1 else ""
        summary = parts[2].strip() if len(parts) > 2 else ""
        html += (
            f'<div style="margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #f0f0f0;">'
            f'<p style="margin:0 0 3px;font-size:14px;font-weight:700;color:#1a1a1a;">{title}</p>'
            + (f'<p style="margin:0 0 3px;font-size:10px;color:#e05c2d;font-weight:700;text-transform:uppercase;letter-spacing:1px;">{source}</p>' if source else "")
            + (f'<p style="margin:0;font-size:13px;color:#555;line-height:1.5;">{summary}</p>' if summary else "")
            + "</div>"
        )
    return html


def build_youtube_html(yt_str):
    lines = parse_lines(yt_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No new videos found this week.</p>'
    html = ""
    for line in lines:
        parts = line.split("|", 4)
        channel = parts[0].strip() if parts else line
        title = parts[1].strip() if len(parts) > 1 else ""
        date = parts[2].strip() if len(parts) > 2 else ""
        url = parts[3].strip() if len(parts) > 3 else ""
        desc = parts[4].strip() if len(parts) > 4 else ""
        title_html = f'<a href="{url}" style="color:#4a90d9;font-weight:700;text-decoration:none;">{title}</a>' if url and title else f'<strong>{title}</strong>'
        meta = f'{channel}{" · " + date if date else ""}'
        html += (
            f'<div style="margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #f0f0f0;">'
            f'<p style="margin:0 0 3px;font-size:14px;line-height:1.4;">{title_html or line}</p>'
            f'<p style="margin:0 0 3px;font-size:10px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:1px;">{meta}</p>'
            + (f'<p style="margin:0;font-size:13px;color:#555;line-height:1.5;">{desc}</p>' if desc else "")
            + '</div>'
        )
    return html


def build_simple_list_html(items_str, icon="◆", color="#555"):
    lines = parse_lines(items_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No updates.</p>'
    html = ""
    for item in lines:
        html += (
            f'<div style="display:flex;align-items:flex-start;margin-bottom:8px;">'
            f'<span style="min-width:18px;margin-right:8px;color:{color};font-size:12px;padding-top:2px;">{icon}</span>'
            f'<p style="margin:0;font-size:13px;color:#1a1a1a;line-height:1.5;">{item}</p></div>'
        )
    return html


def build_tools_html(tools_str):
    lines = parse_lines(tools_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No notable drops today.</p>'
    html = ""
    for line in lines:
        parts = line.split("|", 2)
        name = parts[0].strip() if parts else line
        desc = parts[1].strip() if len(parts) > 1 else ""
        url = parts[2].strip() if len(parts) > 2 else ""
        name_html = f'<a href="{url}" style="color:#2d9e5c;font-weight:700;text-decoration:none;">{name}</a>' if url else f'<strong>{name}</strong>'
        html += (
            f'<div style="display:flex;align-items:flex-start;margin-bottom:8px;">'
            f'<span style="min-width:18px;margin-right:8px;color:#2d9e5c;font-size:12px;padding-top:2px;">⚙</span>'
            f'<p style="margin:0;font-size:13px;color:#1a1a1a;line-height:1.5;">{name_html}{f" — {desc}" if desc else ""}</p></div>'
        )
    return html


def section_row(label, color, icon, content_html):
    return (
        f'<tr><td style="background:#ffffff;padding:20px 32px 16px;">'
        f'<p style="margin:0 0 12px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;'
        f'color:{color};border-bottom:2px solid {color};padding-bottom:8px;display:inline-block;">{icon} &nbsp;{label}</p>'
        f'{content_html}</td></tr>'
        f'<tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>'
    )


def build_html(date_str, schedule_str, action_items, p1, p2, p3, needle, cal_note, ai):
    schedule_html   = build_schedule_html(schedule_str)
    items_html      = build_items_html(action_items)
    priorities_html = build_priorities_html(p1, p2, p3)
    news_html       = build_news_html(ai["news"])
    yt_html         = build_youtube_html(ai["youtube"])
    anthropic_html  = build_simple_list_html(ai["anthropic"], icon="◆", color="#cc785c")
    tools_html      = build_tools_html(ai["tools"])

    # Pre-compute section rows — Python 3.11 forbids backslash escapes inside f-string {}
    row_schedule   = section_row("Today's Schedule", "#f5c518", "📅", schedule_html)
    row_items      = section_row("Open Action Items", "#4a90d9", "📋", items_html)
    row_priorities = section_row("Top 3 Priorities", "#e05c2d", "🎯", priorities_html)
    row_news       = section_row("AI News Headlines", "#e05c2d", "📰", news_html)
    row_yt         = section_row("YouTube Updates", "#4a90d9", "▶", yt_html)
    row_anthropic  = section_row("Claude / Anthropic", "#cc785c", "◆", anthropic_html)
    row_tools      = section_row("AI Tool Drops", "#2d9e5c", "⚙", tools_html)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Brew — {date_str}</title></head>
<body style="margin:0;padding:0;background:#f0efe9;font-family:Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0efe9;">
<tr><td align="center" style="padding:24px 10px;">
  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

    <tr><td style="background:#1a1a1a;border-radius:16px 16px 0 0;padding:28px 32px 24px;text-align:center;">
      <p style="margin:0 0 6px;color:#f5c518;font-size:11px;letter-spacing:3px;text-transform:uppercase;font-weight:700;">Your AI Operating System</p>
      <h1 style="margin:0 0 8px;color:#ffffff;font-size:32px;font-weight:800;letter-spacing:-0.5px;">☕ Morning Brew</h1>
      <p style="margin:0;color:#999999;font-size:14px;">{date_str}</p>
    </td></tr>

    {row_schedule}
    {row_items}
    {row_priorities}

    <tr><td style="background:#ffffff;padding:20px 32px 24px;">
      <p style="margin:0 0 12px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#2d9e5c;border-bottom:2px solid #2d9e5c;padding-bottom:8px;display:inline-block;">⚡ &nbsp;One Thing to Move the Needle</p>
      <div style="background:#f0faf5;border-left:4px solid #2d9e5c;border-radius:0 10px 10px 0;padding:16px 20px;">
        <p style="margin:0;font-size:16px;color:#1a1a1a;font-weight:600;line-height:1.6;">→ &nbsp;{needle}</p>
      </div>
    </td></tr>
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    <tr><td style="background:#f0efe9;padding:16px 32px;text-align:center;">
      <p style="margin:0;font-size:10px;font-weight:800;letter-spacing:4px;text-transform:uppercase;color:#888;">— AI World —</p>
    </td></tr>
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    {row_news}
    {row_yt}
    {row_anthropic}
    {row_tools}

    <tr><td style="background:#1a1a1a;border-radius:0 0 16px 16px;padding:20px 32px;text-align:center;">
      <p style="margin:0 0 6px;color:#777777;font-size:12px;">{cal_note}</p>
      <p style="margin:0;color:#444444;font-size:11px;letter-spacing:1px;">AIOS · Austin Nguyen · {TARGET_EMAIL}</p>
    </td></tr>

  </table>
</td></tr>
</table>
</body></html>"""


# ── Gmail send ────────────────────────────────────────────────────────────────

def send_email(token, to, subject, html_body, plain_body):
    msg = MIMEMultipart("alternative")
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body,  "html",  "utf-8"))
    raw     = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = json.dumps({"raw": raw}).encode()
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    openai_key, client_id, client_secret, refresh_token = _get_creds()

    now = datetime.now(BANGKOK)
    today = now.date()
    date_str = now.strftime("%A %B %d, %Y").replace(" 0", " ")
    today_short = now.strftime("%B %d, %Y")

    print(f"Morning Brew — {date_str}")

    # ── Part 1: Your Day ──────────────────────────────────────────────────────
    print("Getting OAuth token...")
    token = get_access_token(client_id, client_secret, refresh_token)

    print("Loading action items...")
    action_items = load_action_items()
    print(f"  {len(action_items)} item(s).")

    priorities = load_priorities()

    print("Fetching calendar...")
    existing_events = list_todays_events(token, today)
    print(f"  {len(existing_events)} existing event(s).")

    created_count = skipped_count = 0
    for item in action_items:
        if title_already_on_calendar(item, existing_events):
            skipped_count += 1
        else:
            try:
                create_event(token, today, item, start_hour=17)
                created_count += 1
                print(f"  CREATE: {item}")
            except Exception as e:
                print(f"  WARNING: Could not create event: {e}", file=sys.stderr)

    cal_note = f"{created_count} new event(s) added. {skipped_count} item(s) already scheduled."
    print(cal_note)

    final_events = list_todays_events(token, today)
    schedule_str = build_schedule_str(final_events)
    items_str    = "\\n".join(action_items) if action_items else "none"

    p1 = priorities[0] if len(priorities) > 0 else ""
    p2 = priorities[1] if len(priorities) > 1 else ""
    p3 = priorities[2] if len(priorities) > 2 else ""

    client_keywords = ["outreach", "client", "prospect", "funnel", "stage", "warm contact", "rung 0"]
    needle = next((i for i in action_items if any(kw in i.lower() for kw in client_keywords)), None)
    if needle is None and action_items:
        needle = action_items[0]
    if needle is None:
        needle = "Review priorities and pick one action to advance Priority 3 today."

    # ── Part 2: AI World ──────────────────────────────────────────────────────
    print("Gathering AI World sections...")
    ai = gather_ai_sections(openai_key, today_short)

    # ── Build + send ──────────────────────────────────────────────────────────
    print("Building email...")
    html = build_html(date_str, schedule_str, action_items, p1, p2, p3, needle, cal_note, ai)

    plain = f"""Morning Brew — {date_str}

YOUR DAY
Schedule: {schedule_str.replace(chr(92)+'n', chr(10))}
Action items: {chr(10).join(action_items) or 'none'}
Top 3: {p1} / {p2} / {p3}
Needle: {needle}
{cal_note}

AI WORLD
News: {ai['news']}
YouTube: {ai['youtube']}
Anthropic: {ai['anthropic']}
Tools: {ai['tools']}"""

    print(f"Sending to {TARGET_EMAIL}...")
    result = send_email(token, TARGET_EMAIL, f"☕ Morning Brew — {date_str}", html, plain)
    print(f"Sent. Message ID: {result['id']}")


if __name__ == "__main__":
    main()
