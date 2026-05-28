"""
Morning Brew Cloud — standalone script for GitHub Actions.
Reads context/action-items.md, syncs unchecked items to Google Calendar,
then sends the Morning Brew HTML email.

Usage: python scripts/morning_brew_cloud.py
Env vars: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
Falls back to .env file in repo root if env vars not set.
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# ── Timezone ──────────────────────────────────────────────────────────────────
BANGKOK = timezone(timedelta(hours=7))

# ── Repo root (two levels up from this script) ────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent

TARGET_EMAIL = "austinngg996@gmail.com"


# ── Credential loading ────────────────────────────────────────────────────────

def _load_env():
    """Load .env file from repo root. Returns empty dict if file absent."""
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
    """
    Load Google OAuth credentials.
    Prefers environment variables; falls back to .env file.
    """
    client_id     = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        env = _load_env()
        client_id     = client_id     or env.get("GOOGLE_CLIENT_ID")
        client_secret = client_secret or env.get("GOOGLE_CLIENT_SECRET")
        refresh_token = refresh_token or env.get("GOOGLE_REFRESH_TOKEN")

    missing = [k for k, v in {
        "GOOGLE_CLIENT_ID": client_id,
        "GOOGLE_CLIENT_SECRET": client_secret,
        "GOOGLE_REFRESH_TOKEN": refresh_token,
    }.items() if not v]

    if missing:
        print(f"ERROR: Missing credentials: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    return client_id, client_secret, refresh_token


def _get_openai_key():
    """Return OPENAI_API_KEY from env or .env file. Returns None if not set."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        key = _load_env().get("OPENAI_API_KEY")
    return key


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
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"API ERROR {e.code}: {e.read().decode()}", file=sys.stderr)
        raise


# ── Date helpers ──────────────────────────────────────────────────────────────

def today_bangkok():
    """Return a date object for today in Bangkok time."""
    return datetime.now(BANGKOK).date()


def day_window_iso(date):
    """
    Return (time_min, time_max) as ISO 8601 strings with +07:00 offset
    covering the full calendar day in Bangkok time.
    """
    start = datetime(date.year, date.month, date.day, 0, 0, 0, tzinfo=BANGKOK)
    end   = datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=BANGKOK)
    fmt = "%Y-%m-%dT%H:%M:%S+07:00"
    return start.strftime(fmt), end.strftime(fmt)


def event_start_iso(date, hour=17, minute=0):
    """Return ISO 8601 datetime string for a given hour:minute in Bangkok."""
    dt = datetime(date.year, date.month, date.day, hour, minute, 0, tzinfo=BANGKOK)
    return dt.strftime("%Y-%m-%dT%H:%M:%S+07:00")


# ── Action-items parser ───────────────────────────────────────────────────────

def load_action_items():
    """
    Read context/action-items.md and return list of unchecked item strings.
    Returns empty list if file does not exist.
    """
    path = REPO_ROOT / "context" / "action-items.md"
    if not path.exists():
        print("WARNING: context/action-items.md not found — no action items to sync.", file=sys.stderr)
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*-\s+\[\s\]\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
    return items


# ── Priorities parser ─────────────────────────────────────────────────────────

def load_priorities():
    """
    Read context/priorities.md and return list of priority strings (stripped of markdown).
    Returns empty list if file does not exist.
    """
    path = REPO_ROOT / "context" / "priorities.md"
    if not path.exists():
        return []
    priorities = []
    for line in path.read_text(encoding="utf-8").splitlines():
        # Match numbered list items: "1. **text** — detail" or "1. text"
        m = re.match(r"^\s*\d+\.\s+(.+)$", line)
        if m:
            text = m.group(1).strip()
            # Strip bold markers
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            priorities.append(text)
    return priorities


# ── Google Calendar helpers ───────────────────────────────────────────────────

CALENDAR_BASE = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def list_todays_events(token, date):
    """Return list of event dicts for today in Bangkok."""
    time_min, time_max = day_window_iso(date)
    result = api("GET", CALENDAR_BASE, token, params={
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
    })
    return result.get("items", [])


def title_already_on_calendar(title, events):
    """
    Loose title match: return True if any calendar event summary contains
    the action item text (case-insensitive substring match).
    """
    title_lower = title.lower()
    for ev in events:
        summary = ev.get("summary", "").lower()
        if title_lower in summary or summary in title_lower:
            return True
    return False


def create_event(token, date, title, start_hour=17, duration_minutes=30):
    """Create a 30-min calendar event on the given date at start_hour Bangkok time."""
    start = event_start_iso(date, start_hour, 0)
    # Compute end time
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
    """Return a readable time string like '5:00 PM' from a calendar event."""
    start = event.get("start", {})
    dt_str = start.get("dateTime") or start.get("date", "")
    if not dt_str:
        return "All day"
    try:
        # Parse ISO datetime — handle offset manually for stdlib compat
        # Format: 2026-05-28T17:00:00+07:00
        dt_str_clean = re.sub(r"([+-]\d{2}):(\d{2})$", lambda m: m.group(1) + m.group(2), dt_str)
        dt = datetime.strptime(dt_str_clean, "%Y-%m-%dT%H:%M:%S%z")
        dt_bkk = dt.astimezone(BANGKOK)
        return dt_bkk.strftime("%-I:%M %p") if sys.platform != "win32" else dt_bkk.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return dt_str[:16]


def build_schedule_str(events):
    """Build the schedule string for the email (pipe-separated time|title lines)."""
    if not events:
        return "none"
    lines = []
    for ev in events:
        time_str = format_event_time(ev)
        summary  = ev.get("summary", "(no title)")
        end_start = ev.get("end", {})
        end_dt_str = end_start.get("dateTime", "")
        end_time = ""
        if end_dt_str:
            try:
                dt_str_clean = re.sub(r"([+-]\d{2}):(\d{2})$", lambda m: m.group(1) + m.group(2), end_dt_str)
                dt = datetime.strptime(dt_str_clean, "%Y-%m-%dT%H:%M:%S%z")
                dt_bkk = dt.astimezone(BANGKOK)
                end_time = " – " + (dt_bkk.strftime("%-I:%M %p") if sys.platform != "win32" else dt_bkk.strftime("%I:%M %p").lstrip("0"))
            except Exception:
                pass
        lines.append(f"{time_str}{end_time} | {summary}")
    return "\\n".join(lines)


# ── Email (HTML + send) ───────────────────────────────────────────────────────
# Functions copied inline from send_morning_brew.py to avoid import issues.

def build_schedule_html(schedule_str):
    if not schedule_str.strip() or schedule_str.strip().lower() == "none":
        return '<p style="margin:0 0 8px;color:#888;font-style:italic;">Nothing scheduled — clear day.</p>'
    lines = [l.strip() for l in schedule_str.split("\\n") if l.strip()]
    rows = ""
    for line in lines:
        if "|" in line:
            time, title = line.split("|", 1)
        else:
            time, title = "", line
        rows += f"""
        <tr>
          <td style="padding:6px 12px 6px 0;color:#888;font-size:13px;white-space:nowrap;vertical-align:top;">{time.strip()}</td>
          <td style="padding:6px 0;color:#1a1a1a;font-size:15px;vertical-align:top;">{title.strip()}</td>
        </tr>"""
    return f'<table cellpadding="0" cellspacing="0" style="width:100%">{rows}</table>'


def build_items_html(items_str):
    if not items_str.strip() or items_str.strip().lower() == "none":
        return '<p style="margin:0;color:#888;font-style:italic;">No open items.</p>'
    lines = [l.strip() for l in items_str.split("\\n") if l.strip()]
    html = ""
    for item in lines:
        html += f"""
        <div style="display:flex;align-items:flex-start;margin-bottom:10px;">
          <span style="min-width:20px;margin-right:10px;color:#4a90d9;font-size:16px;line-height:1.4;">□</span>
          <span style="color:#1a1a1a;font-size:15px;line-height:1.4;">{item}</span>
        </div>"""
    return html


def build_priorities_html(p1, p2, p3):
    items = [(1, p1), (2, p2), (3, p3)]
    html = ""
    for n, text in items:
        if not text:
            continue
        html += f"""
        <div style="display:flex;align-items:flex-start;margin-bottom:12px;">
          <span style="color:#e05c2d;font-size:15px;font-weight:800;margin-right:10px;vertical-align:top;">{n}.</span>
          <span style="color:#1a1a1a;font-size:15px;line-height:1.4;padding-top:4px;">{text}</span>
        </div>"""
    return html


# ── News digest ───────────────────────────────────────────────────────────────

NEWS_SOURCES = {
    "AI & Tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    ],
    "Markets & Trading": [
        "https://feeds.reuters.com/reuters/businessNews",
    ],
    "Vietnam Business": [
        "https://e.vnexpress.net/rss/business.rss",
    ],
}


def fetch_rss(url, max_items=5):
    """Fetch and parse an RSS 2.0 feed. Returns [] silently on any error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AIOS-MorningBrew/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml_data = r.read()
        root = ET.fromstring(xml_data)
        items = []
        for item in root.findall(".//item")[:max_items]:
            title = (item.findtext("title") or "").strip()
            link  = (item.findtext("link")  or "").strip()
            desc  = re.sub(r"<[^>]+>", "", (item.findtext("description") or ""))[:200].strip()
            if title:
                items.append({"title": title, "link": link, "description": desc})
        return items
    except Exception as e:
        print(f"  WARNING: RSS fetch failed for {url}: {e}", file=sys.stderr)
        return []


def fetch_all_news(max_per_category=5):
    results = {}
    for category, urls in NEWS_SOURCES.items():
        items = []
        for url in urls:
            items.extend(fetch_rss(url, max_items=max_per_category))
            if len(items) >= max_per_category:
                break
        results[category] = items[:max_per_category]
    return results


def summarize_with_openai(headlines, category, api_key):
    """Call OpenAI gpt-4o-mini to produce 2-3 bullet points. Returns None on failure."""
    if not api_key or not headlines:
        return None
    headlines_text = "\n".join(f"- {h['title']}" for h in headlines)
    prompt = (
        f"You are Austin's briefing assistant. Here are today's {category} headlines:\n\n"
        f"{headlines_text}\n\n"
        "Write 2-3 tight bullet points — one sentence each — on what matters most for "
        "an AI OS consultant and futures trader in Hanoi. No fluff. Start each bullet with •"
    )
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.3,
    }
    try:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            result = json.loads(r.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  WARNING: OpenAI summarization failed for {category}: {e}", file=sys.stderr)
        return None


def build_news_digest(openai_key):
    print("Fetching news digest...")
    news = fetch_all_news()
    digest = {}
    for category, items in news.items():
        print(f"  {category}: {len(items)} headline(s)")
        summary = summarize_with_openai(items, category, openai_key)
        digest[category] = {"items": items, "summary": summary}
    return digest


def build_news_html(digest):
    """Render the news digest as an HTML email section. Returns '' if no items."""
    if not digest or all(not v["items"] for v in digest.values()):
        return ""

    category_blocks = ""
    for category, data in digest.items():
        items   = data["items"]
        summary = data.get("summary")
        if not items:
            continue

        if summary:
            bullets_html = ""
            for line in summary.splitlines():
                line = re.sub(r"^[•\-\*]\s*", "", line.strip())
                if line:
                    bullets_html += (
                        f'<div style="display:flex;align-items:flex-start;margin-bottom:8px;">'
                        f'<span style="color:#8b5cf6;margin-right:8px;font-size:14px;flex-shrink:0;">•</span>'
                        f'<span style="color:#1a1a1a;font-size:14px;line-height:1.5;">{line}</span></div>'
                    )
        else:
            bullets_html = ""
            for item in items[:3]:
                bullets_html += (
                    f'<div style="display:flex;align-items:flex-start;margin-bottom:8px;">'
                    f'<span style="color:#8b5cf6;margin-right:8px;font-size:14px;flex-shrink:0;">•</span>'
                    f'<span style="color:#1a1a1a;font-size:14px;line-height:1.5;">{item["title"]}</span></div>'
                )

        category_blocks += (
            f'<div style="margin-bottom:20px;">'
            f'<p style="margin:0 0 10px;font-size:11px;font-weight:800;letter-spacing:2px;'
            f'text-transform:uppercase;color:#666666;">{category}</p>'
            f'{bullets_html}</div>'
        )

    return (
        f'<tr><td style="background:#ffffff;padding:24px 32px 20px;">'
        f'<p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;'
        f'text-transform:uppercase;color:#8b5cf6;border-bottom:2px solid #8b5cf6;'
        f'padding-bottom:10px;display:inline-block;">\U0001f4f0 &nbsp;AI Daily Digest</p>'
        f'{category_blocks}</td></tr>'
        f'<tr><td style="background:#ffffff;padding:0 32px;">'
        f'<div style="height:1px;background:#eeeeee;"></div></td></tr>'
    )


def build_news_plain(digest):
    """Render news digest as plain text. Returns '' if no items."""
    if not digest or all(not v["items"] for v in digest.values()):
        return ""
    lines = ["\n\nAI DAILY DIGEST", "-" * 40]
    for category, data in digest.items():
        items   = data["items"]
        summary = data.get("summary")
        if not items:
            continue
        lines.append(f"\n{category.upper()}")
        if summary:
            lines.append(summary)
        else:
            for item in items[:3]:
                lines.append(f"• {item['title']}")
    return "\n".join(lines)


def build_html(date_str, schedule_str, items_str, p1, p2, p3, needle, cal_note, news_html=""):
    schedule_html   = build_schedule_html(schedule_str)
    items_html      = build_items_html(items_str)
    priorities_html = build_priorities_html(p1, p2, p3)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Brew — {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#f0efe9;font-family:Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0efe9;">
<tr><td align="center" style="padding:24px 10px;">

  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

    <!-- HEADER -->
    <tr>
      <td style="background:#1a1a1a;border-radius:16px 16px 0 0;padding:28px 32px 24px;text-align:center;">
        <p style="margin:0 0 6px;color:#f5c518;font-size:11px;letter-spacing:3px;text-transform:uppercase;font-weight:700;">Your AI Operating System</p>
        <h1 style="margin:0 0 8px;color:#ffffff;font-size:32px;font-weight:800;letter-spacing:-0.5px;">☕ Morning Brew</h1>
        <p style="margin:0;color:#999999;font-size:14px;">{date_str}</p>
      </td>
    </tr>

    <!-- SCHEDULE -->
    <tr>
      <td style="background:#ffffff;padding:28px 32px 20px;">
        <p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#f5c518;border-bottom:2px solid #f5c518;padding-bottom:10px;display:inline-block;">\U0001f4c5 &nbsp;Today's Schedule</p>
        {schedule_html}
      </td>
    </tr>

    <!-- DIVIDER -->
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    <!-- OPEN ACTION ITEMS -->
    <tr>
      <td style="background:#ffffff;padding:24px 32px 20px;">
        <p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#4a90d9;border-bottom:2px solid #4a90d9;padding-bottom:10px;display:inline-block;">\U0001f4cb &nbsp;Open Action Items</p>
        {items_html}
      </td>
    </tr>

    <!-- DIVIDER -->
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    <!-- TOP 3 PRIORITIES -->
    <tr>
      <td style="background:#ffffff;padding:24px 32px 20px;">
        <p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#e05c2d;border-bottom:2px solid #e05c2d;padding-bottom:10px;display:inline-block;">\U0001f3af &nbsp;Top 3 Priorities</p>
        {priorities_html}
      </td>
    </tr>

    <!-- DIVIDER -->
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    <!-- NEEDLE MOVER -->
    <tr>
      <td style="background:#ffffff;padding:24px 32px 28px;">
        <p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#2d9e5c;border-bottom:2px solid #2d9e5c;padding-bottom:10px;display:inline-block;">⚡ &nbsp;One Thing to Move the Needle</p>
        <div style="background:#f0faf5;border-left:4px solid #2d9e5c;border-radius:0 10px 10px 0;padding:16px 20px;">
          <p style="margin:0;font-size:16px;color:#1a1a1a;font-weight:600;line-height:1.6;">→ &nbsp;{needle}</p>
        </div>
      </td>
    </tr>

    <!-- AI DAILY DIGEST -->
    {news_html}

    <!-- FOOTER -->
    <tr>
      <td style="background:#1a1a1a;border-radius:0 0 16px 16px;padding:20px 32px;text-align:center;">
        <p style="margin:0 0 6px;color:#777777;font-size:12px;">{cal_note}</p>
        <p style="margin:0;color:#444444;font-size:11px;letter-spacing:1px;">AIOS &nbsp;·&nbsp; Austin Nguyen &nbsp;·&nbsp; austinngg996@gmail.com</p>
      </td>
    </tr>

  </table>

</td></tr>
</table>
</body>
</html>"""


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
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # 1. Load credentials
    client_id, client_secret, refresh_token = _get_creds()

    # 2. Get OAuth token
    print("Getting access token...")
    token = get_access_token(client_id, client_secret, refresh_token)

    # 3. Load action items
    print("Loading action items...")
    action_items = load_action_items()
    print(f"  Found {len(action_items)} unchecked item(s).")

    # 4. Load priorities
    priorities = load_priorities()

    # 4b. Build news digest
    openai_key = _get_openai_key()
    digest = build_news_digest(openai_key)

    # 5. Fetch today's calendar events
    today = today_bangkok()
    date_str = datetime.now(BANGKOK).strftime("%A %B %-d") if sys.platform != "win32" \
               else datetime.now(BANGKOK).strftime("%A %B %d").replace(" 0", " ")
    print(f"Fetching calendar for {date_str} (Bangkok)...")
    existing_events = list_todays_events(token, today)
    print(f"  {len(existing_events)} existing event(s) on calendar.")

    # 6. Sync action items to calendar (skip items already present)
    created_count = 0
    skipped_count = 0
    for item in action_items:
        if title_already_on_calendar(item, existing_events):
            print(f"  SKIP (already on cal): {item}")
            skipped_count += 1
        else:
            print(f"  CREATE event: {item}")
            try:
                create_event(token, today, item, start_hour=17)
                created_count += 1
            except Exception as e:
                print(f"  WARNING: Could not create event for '{item}': {e}", file=sys.stderr)

    cal_note = f"{created_count} new event(s) added to calendar. {skipped_count} item(s) already scheduled."
    print(cal_note)

    # 7. Re-fetch full calendar after creation
    print("Re-fetching calendar after sync...")
    final_events = list_todays_events(token, today)

    # 8. Build brief data
    schedule_str = build_schedule_str(final_events)
    items_str    = "\\n".join(action_items) if action_items else "none"

    # Top 3 priorities from priorities.md (first 3)
    p1 = priorities[0] if len(priorities) > 0 else ""
    p2 = priorities[1] if len(priorities) > 1 else ""
    p3 = priorities[2] if len(priorities) > 2 else ""

    # Needle-mover: first unchecked action item tied to Priority 3 (land first client)
    # Heuristic: prefer items that mention outreach, client, prospect, funnel; else first item
    client_keywords = ["outreach", "client", "prospect", "funnel", "stage", "warm contact", "rung 0"]
    needle_item = None
    for item in action_items:
        if any(kw in item.lower() for kw in client_keywords):
            needle_item = item
            break
    if needle_item is None and action_items:
        needle_item = action_items[0]
    if needle_item is None:
        needle_item = "Review priorities and pick one action to advance Priority 3 today."

    needle = needle_item

    # 9. Build HTML
    html = build_html(
        date_str     = date_str,
        schedule_str = schedule_str,
        items_str    = items_str,
        p1           = p1,
        p2           = p2,
        p3           = p3,
        needle       = needle,
        cal_note     = cal_note,
        news_html    = build_news_html(digest),
    )

    plain = f"""Morning Brew — {date_str}

TODAY'S SCHEDULE
{schedule_str.replace(chr(92) + 'n', chr(10))}

OPEN ACTION ITEMS
{items_str.replace(chr(92) + 'n', chr(10))}

TOP 3 PRIORITIES
1. {p1}
2. {p2}
3. {p3}

ONE THING TO MOVE THE NEEDLE
→ {needle}
{build_news_plain(digest)}

---
{cal_note}"""

    # 10. Send email
    print(f"Sending Morning Brew to {TARGET_EMAIL}...")
    result = send_email(token, TARGET_EMAIL, f"☕ Morning Brew — {date_str}", html, plain)
    print(f"Sent. Message ID: {result['id']}")


if __name__ == "__main__":
    main()
