"""
Generates and sends the combined Morning Brew + AI Daily Digest HTML email.
Usage:
  python scripts/send_morning_brew.py \
    --date "Wednesday May 28" \
    --schedule "5:00 PM – 5:30 PM | Draft outreach\n5:30 PM – 6:00 PM | Build audit" \
    --items "Draft first outreach message\nBuild Rung 1 audit template" \
    --p1 "Draft first outreach message — advances Priority 3" \
    --p2 "Trading session — protect the funded account" \
    --p3 "Build Rung 1 audit template" \
    --needle "Open rung-0-funnel.md, pick one warm contact, write Stage 1 message." \
    --cal-note "0 new events added. 2 items already scheduled." \
    --news "Title | Source | Summary\nTitle 2 | Source | Summary" \
    --youtube "Nate Herk | Video Title | May 28 | https://...\nTina Huang | Title | May 27 | https://..." \
    --anthropic "Claude Opus 4.8 released\nNew multiagent orchestration" \
    --tools "Phasr | Run 100+ parallel workflows | https://..."
"""

import argparse
import base64
import json
import sys
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    env = {}
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


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


def parse_lines(raw: str) -> list:
    return [l.strip() for l in raw.replace("\\n", "\n").split("\n") if l.strip()]


# ── Your Day section builders ─────────────────────────────────────────────────

def build_schedule_html(schedule_str: str) -> str:
    if not schedule_str.strip() or schedule_str.strip().lower() == "none":
        return '<p style="margin:0 0 8px;color:#888;font-style:italic;">Nothing scheduled — clear day.</p>'
    lines = parse_lines(schedule_str)
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


def build_items_html(items_str: str) -> str:
    if not items_str.strip() or items_str.strip().lower() == "none":
        return '<p style="margin:0;color:#888;font-style:italic;">No open items.</p>'
    lines = parse_lines(items_str)
    html = ""
    for item in lines:
        html += f"""
        <div style="display:flex;align-items:flex-start;margin-bottom:10px;">
          <span style="min-width:20px;margin-right:10px;color:#4a90d9;font-size:16px;line-height:1.4;">□</span>
          <span style="color:#1a1a1a;font-size:15px;line-height:1.4;">{item}</span>
        </div>"""
    return html


def build_priorities_html(p1: str, p2: str, p3: str) -> str:
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


# ── AI World section builders ─────────────────────────────────────────────────

def build_news_html(news_str: str) -> str:
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


def build_youtube_html(yt_str: str) -> str:
    lines = parse_lines(yt_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No new videos found this week.</p>'
    html = ""
    for line in lines:
        parts = line.split("|", 3)
        channel = parts[0].strip() if parts else line
        title = parts[1].strip() if len(parts) > 1 else ""
        date = parts[2].strip() if len(parts) > 2 else ""
        url = parts[3].strip() if len(parts) > 3 else ""
        title_html = f'<a href="{url}" style="color:#4a90d9;text-decoration:none;">{title}</a>' if url and title else title
        html += (
            f'<div style="display:flex;align-items:flex-start;margin-bottom:10px;">'
            f'<span style="min-width:22px;margin-right:8px;color:#ff0000;font-size:14px;">▶</span>'
            f'<div>'
            f'<p style="margin:0 0 1px;font-size:10px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:1px;">{channel}{f" · {date}" if date else ""}</p>'
            f'<p style="margin:0;font-size:13px;color:#1a1a1a;">{title_html or line}</p>'
            f'</div></div>'
        )
    return html


def build_anthropic_html(items_str: str) -> str:
    lines = parse_lines(items_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No major updates this week.</p>'
    html = ""
    for item in lines:
        html += (
            f'<div style="display:flex;align-items:flex-start;margin-bottom:8px;">'
            f'<span style="min-width:18px;margin-right:8px;color:#cc785c;font-size:12px;font-weight:700;padding-top:2px;">◆</span>'
            f'<p style="margin:0;font-size:13px;color:#1a1a1a;line-height:1.5;">{item}</p>'
            f'</div>'
        )
    return html


def build_tools_html(tools_str: str) -> str:
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
            f'<p style="margin:0;font-size:13px;color:#1a1a1a;line-height:1.5;">{name_html}{f" — {desc}" if desc else ""}</p>'
            f'</div>'
        )
    return html


def section_row(label: str, color: str, icon: str, content_html: str) -> str:
    return (
        f'<tr><td style="background:#ffffff;padding:20px 32px 16px;">'
        f'<p style="margin:0 0 12px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;'
        f'color:{color};border-bottom:2px solid {color};padding-bottom:8px;display:inline-block;">{icon} &nbsp;{label}</p>'
        f'{content_html}</td></tr>'
        f'<tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>'
    )


def build_html(date, schedule_str, items_str, p1, p2, p3, needle, cal_note,
               news_str="", yt_str="", anthropic_str="", tools_str=""):

    schedule_html = build_schedule_html(schedule_str)
    items_html = build_items_html(items_str)
    priorities_html = build_priorities_html(p1, p2, p3)
    news_html = build_news_html(news_str) if news_str else ""
    yt_html = build_youtube_html(yt_str) if yt_str else ""
    anthropic_html = build_anthropic_html(anthropic_str) if anthropic_str else ""
    tools_html = build_tools_html(tools_str) if tools_str else ""

    ai_sections = ""
    if any([news_str, yt_str, anthropic_str, tools_str]):
        ai_sections = f"""
    <!-- AI WORLD DIVIDER -->
    <tr>
      <td style="background:#f0efe9;padding:16px 32px;text-align:center;">
        <p style="margin:0;font-size:10px;font-weight:800;letter-spacing:4px;text-transform:uppercase;color:#888;">— AI World —</p>
      </td>
    </tr>
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    {section_row("AI News Headlines", "#e05c2d", "📰", news_html) if news_str else ""}
    {section_row("YouTube Updates", "#4a90d9", "▶", yt_html) if yt_str else ""}
    {section_row("Claude / Anthropic", "#cc785c", "◆", anthropic_html) if anthropic_str else ""}
    {section_row("AI Tool Drops", "#2d9e5c", "⚙", tools_html) if tools_str else ""}"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Morning Brew — {date}</title>
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
        <p style="margin:0;color:#999999;font-size:14px;">{date}</p>
      </td>
    </tr>

    {section_row("Today's Schedule", "#f5c518", "📅", schedule_html)}
    {section_row("Open Action Items", "#4a90d9", "📋", items_html)}
    {section_row("Top 3 Priorities", "#e05c2d", "🎯", priorities_html)}

    <!-- NEEDLE MOVER -->
    <tr>
      <td style="background:#ffffff;padding:20px 32px 24px;">
        <p style="margin:0 0 12px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#2d9e5c;border-bottom:2px solid #2d9e5c;padding-bottom:8px;display:inline-block;">⚡ &nbsp;One Thing to Move the Needle</p>
        <div style="background:#f0faf5;border-left:4px solid #2d9e5c;border-radius:0 10px 10px 0;padding:16px 20px;">
          <p style="margin:0;font-size:16px;color:#1a1a1a;font-weight:600;line-height:1.6;">→ &nbsp;{needle}</p>
        </div>
      </td>
    </tr>
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    {ai_sections}

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
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = json.dumps({"raw": raw}).encode()
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--schedule", default="none")
    parser.add_argument("--items", default="none")
    parser.add_argument("--p1", default="")
    parser.add_argument("--p2", default="")
    parser.add_argument("--p3", default="")
    parser.add_argument("--needle", required=True)
    parser.add_argument("--cal-note", default="")
    parser.add_argument("--news", default="")
    parser.add_argument("--youtube", default="")
    parser.add_argument("--anthropic", default="")
    parser.add_argument("--tools", default="")
    args = parser.parse_args()

    html = build_html(
        date=args.date,
        schedule_str=args.schedule,
        items_str=args.items,
        p1=args.p1,
        p2=args.p2,
        p3=args.p3,
        needle=args.needle,
        cal_note=args.cal_note,
        news_str=args.news,
        yt_str=args.youtube,
        anthropic_str=args.anthropic,
        tools_str=args.tools,
    )

    nl = chr(10)
    plain = f"""Morning Brew — {args.date}

TODAY'S SCHEDULE
{args.schedule.replace(chr(92)+'n', nl)}

OPEN ACTION ITEMS
{args.items.replace(chr(92)+'n', nl)}

TOP 3 PRIORITIES
1. {args.p1}
2. {args.p2}
3. {args.p3}

ONE THING TO MOVE THE NEEDLE
→ {args.needle}

---
{args.cal_note}

AI NEWS
{args.news.replace(chr(92)+'n', nl)}

YOUTUBE UPDATES
{args.youtube.replace(chr(92)+'n', nl)}

CLAUDE / ANTHROPIC
{args.anthropic.replace(chr(92)+'n', nl)}

AI TOOL DROPS
{args.tools.replace(chr(92)+'n', nl)}"""

    env = load_env()
    token = get_access_token(
        env["GOOGLE_WORKSPACE_CLI_CLIENT_ID"],
        env["GOOGLE_WORKSPACE_CLI_CLIENT_SECRET"],
        env["GOOGLE_WORKSPACE_CLI_REFRESH_TOKEN"],
    )
    result = send_email(token, "austinngg996@gmail.com", f"☕ Morning Brew — {args.date}", html, plain)
    print(f"Sent. Message ID: {result['id']}")
