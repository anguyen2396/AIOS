"""
Generates and sends the AI Daily Digest HTML email.
Usage:
  python scripts/send_ai_digest.py \
    --date "Friday May 30, 2026" \
    --news "Title | Source | Summary\nTitle 2 | Source | Summary" \
    --youtube "Nate Herk | Video Title | May 29 | https://...\nTina Huang | Title | May 28 | https://..." \
    --anthropic "Claude update item 1\nClaude update item 2" \
    --tools "Tool Name | What it does | https://..."
"""

import argparse
import base64
import json
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


def parse_lines(raw: str) -> list[str]:
    return [l.strip() for l in raw.replace("\\n", "\n").split("\n") if l.strip()]


def build_news_html(news_str: str) -> str:
    lines = parse_lines(news_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No news items found.</p>'
    html = ""
    for line in lines:
        parts = line.split("|", 2)
        title = parts[0].strip() if len(parts) > 0 else line
        source = parts[1].strip() if len(parts) > 1 else ""
        summary = parts[2].strip() if len(parts) > 2 else ""
        html += f"""
        <div style="margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #f0f0f0;">
          <p style="margin:0 0 4px;font-size:15px;font-weight:700;color:#1a1a1a;">{title}</p>
          {f'<p style="margin:0 0 4px;font-size:11px;color:#e05c2d;font-weight:700;text-transform:uppercase;letter-spacing:1px;">{source}</p>' if source else ""}
          {f'<p style="margin:0;font-size:14px;color:#555;line-height:1.5;">{summary}</p>' if summary else ""}
        </div>"""
    return html


def build_youtube_html(yt_str: str) -> str:
    lines = parse_lines(yt_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No new videos found.</p>'
    html = ""
    for line in lines:
        parts = line.split("|", 3)
        channel = parts[0].strip() if len(parts) > 0 else line
        title = parts[1].strip() if len(parts) > 1 else ""
        date = parts[2].strip() if len(parts) > 2 else ""
        url = parts[3].strip() if len(parts) > 3 else ""
        title_html = f'<a href="{url}" style="color:#4a90d9;text-decoration:none;">{title}</a>' if url and title else title
        html += f"""
        <div style="display:flex;align-items:flex-start;margin-bottom:12px;">
          <span style="min-width:24px;margin-right:8px;color:#ff0000;font-size:16px;">▶</span>
          <div>
            <p style="margin:0 0 2px;font-size:11px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:1px;">{channel} {f"· {date}" if date else ""}</p>
            <p style="margin:0;font-size:14px;color:#1a1a1a;">{title_html if title else line}</p>
          </div>
        </div>"""
    return html


def build_anthropic_html(items_str: str) -> str:
    lines = parse_lines(items_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No major updates this week.</p>'
    html = ""
    for item in lines:
        html += f"""
        <div style="display:flex;align-items:flex-start;margin-bottom:10px;">
          <span style="min-width:20px;margin-right:8px;color:#cc785c;font-size:14px;font-weight:700;">◆</span>
          <p style="margin:0;font-size:14px;color:#1a1a1a;line-height:1.5;">{item}</p>
        </div>"""
    return html


def build_tools_html(tools_str: str) -> str:
    lines = parse_lines(tools_str)
    if not lines:
        return '<p style="color:#888;font-style:italic;">No notable drops today.</p>'
    html = ""
    for line in lines:
        parts = line.split("|", 2)
        name = parts[0].strip() if len(parts) > 0 else line
        desc = parts[1].strip() if len(parts) > 1 else ""
        url = parts[2].strip() if len(parts) > 2 else ""
        name_html = f'<a href="{url}" style="color:#2d9e5c;font-weight:700;text-decoration:none;">{name}</a>' if url else f'<strong>{name}</strong>'
        html += f"""
        <div style="display:flex;align-items:flex-start;margin-bottom:12px;">
          <span style="min-width:20px;margin-right:8px;color:#2d9e5c;font-size:14px;">⚙</span>
          <p style="margin:0;font-size:14px;color:#1a1a1a;line-height:1.5;">{name_html}{f" — {desc}" if desc else ""}</p>
        </div>"""
    return html


def section_block(label: str, color: str, icon: str, content_html: str) -> str:
    return f"""
    <tr>
      <td style="background:#ffffff;padding:24px 32px 20px;">
        <p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:{color};border-bottom:2px solid {color};padding-bottom:10px;display:inline-block;">{icon} &nbsp;{label}</p>
        {content_html}
      </td>
    </tr>
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>"""


def build_html(date, news_str, yt_str, anthropic_str, tools_str):
    news_html = build_news_html(news_str)
    yt_html = build_youtube_html(yt_str)
    anthropic_html = build_anthropic_html(anthropic_str)
    tools_html = build_tools_html(tools_str)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Daily Digest — {date}</title>
</head>
<body style="margin:0;padding:0;background:#f0efe9;font-family:Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0efe9;">
<tr><td align="center" style="padding:24px 10px;">

  <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

    <!-- HEADER -->
    <tr>
      <td style="background:#1a1a1a;border-radius:16px 16px 0 0;padding:28px 32px 24px;text-align:center;">
        <p style="margin:0 0 6px;color:#f5c518;font-size:11px;letter-spacing:3px;text-transform:uppercase;font-weight:700;">Your AI Operating System</p>
        <h1 style="margin:0 0 8px;color:#ffffff;font-size:32px;font-weight:800;letter-spacing:-0.5px;">🤖 AI Daily Digest</h1>
        <p style="margin:0;color:#999999;font-size:14px;">{date}</p>
      </td>
    </tr>

    {section_block("AI News Headlines", "#e05c2d", "📰", news_html)}
    {section_block("YouTube Updates", "#4a90d9", "▶", yt_html)}
    {section_block("Claude / Anthropic", "#cc785c", "◆", anthropic_html)}
    {section_block("AI Tool Drops", "#2d9e5c", "⚙", tools_html)}

    <!-- FOOTER -->
    <tr>
      <td style="background:#1a1a1a;border-radius:0 0 16px 16px;padding:20px 32px;text-align:center;">
        <p style="margin:0 0 4px;color:#777777;font-size:12px;">Delivered by AIOS — Austin's AI Operating System</p>
        <p style="margin:0;color:#444444;font-size:11px;letter-spacing:1px;">Austin Nguyen &nbsp;·&nbsp; austinngg996@gmail.com</p>
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
    parser.add_argument("--news", default="")
    parser.add_argument("--youtube", default="")
    parser.add_argument("--anthropic", default="")
    parser.add_argument("--tools", default="")
    args = parser.parse_args()

    html = build_html(
        date=args.date,
        news_str=args.news,
        yt_str=args.youtube,
        anthropic_str=args.anthropic,
        tools_str=args.tools,
    )

    def to_plain(section_str, label):
        lines = parse_lines(section_str)
        return f"\n{label}\n" + "\n".join(f"- {l}" for l in lines) if lines else f"\n{label}\nNo items."

    plain = f"""AI Daily Digest — {args.date}
{to_plain(args.news, "AI NEWS")}
{to_plain(args.youtube, "YOUTUBE UPDATES")}
{to_plain(args.anthropic, "CLAUDE / ANTHROPIC")}
{to_plain(args.tools, "AI TOOL DROPS")}
---
Delivered by AIOS"""

    env = load_env()
    token = get_access_token(
        env["GOOGLE_WORKSPACE_CLI_CLIENT_ID"],
        env["GOOGLE_WORKSPACE_CLI_CLIENT_SECRET"],
        env["GOOGLE_WORKSPACE_CLI_REFRESH_TOKEN"],
    )
    result = send_email(token, "austinngg996@gmail.com", f"🤖 AI Daily Digest — {args.date}", html, plain)
    print(f"Sent. Message ID: {result['id']}")
