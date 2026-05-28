"""
Generates and sends the Morning Brew HTML email.
Usage:
  python scripts/send_morning_brew.py \
    --date "Wednesday May 28" \
    --schedule "5:00 PM – 5:30 PM | Draft outreach message\n5:30 PM – 6:00 PM | Build Rung 1 audit" \
    --items "Draft first outreach message tailored to a warm contact\nBuild out Rung 1 audit template" \
    --p1 "Draft first outreach message — advances Priority 3" \
    --p2 "Trading session — protect the funded account" \
    --p3 "Build Rung 1 audit template — completes funnel skeleton" \
    --needle "Open rung-0-funnel.md, pick one warm contact, write Stage 1 message, send before 6 PM." \
    --cal-note "0 new events added to calendar. 2 items already scheduled."
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


def build_schedule_html(schedule_str: str) -> str:
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


def build_items_html(items_str: str) -> str:
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


def build_html(date, schedule_str, items_str, p1, p2, p3, needle, cal_note):
    schedule_html = build_schedule_html(schedule_str)
    items_html = build_items_html(items_str)
    priorities_html = build_priorities_html(p1, p2, p3)

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

    <!-- SCHEDULE -->
    <tr>
      <td style="background:#ffffff;padding:28px 32px 20px;">
        <p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#f5c518;border-bottom:2px solid #f5c518;padding-bottom:10px;display:inline-block;">📅 &nbsp;Today's Schedule</p>
        {schedule_html}
      </td>
    </tr>

    <!-- DIVIDER -->
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    <!-- OPEN ACTION ITEMS -->
    <tr>
      <td style="background:#ffffff;padding:24px 32px 20px;">
        <p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#4a90d9;border-bottom:2px solid #4a90d9;padding-bottom:10px;display:inline-block;">📋 &nbsp;Open Action Items</p>
        {items_html}
      </td>
    </tr>

    <!-- DIVIDER -->
    <tr><td style="background:#ffffff;padding:0 32px;"><div style="height:1px;background:#eeeeee;"></div></td></tr>

    <!-- TOP 3 PRIORITIES -->
    <tr>
      <td style="background:#ffffff;padding:24px 32px 20px;">
        <p style="margin:0 0 14px;font-size:10px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#e05c2d;border-bottom:2px solid #e05c2d;padding-bottom:10px;display:inline-block;">🎯 &nbsp;Top 3 Priorities</p>
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
    )

    plain = f"""Morning Brew — {args.date}

TODAY'S SCHEDULE
{args.schedule.replace(chr(92)+'n', chr(10))}

OPEN ACTION ITEMS
{args.items.replace(chr(92)+'n', chr(10))}

TOP 3 PRIORITIES
1. {args.p1}
2. {args.p2}
3. {args.p3}

ONE THING TO MOVE THE NEEDLE
→ {args.needle}

---
{args.cal_note}"""

    env = load_env()
    token = get_access_token(
        env["GOOGLE_WORKSPACE_CLI_CLIENT_ID"],
        env["GOOGLE_WORKSPACE_CLI_CLIENT_SECRET"],
        env["GOOGLE_WORKSPACE_CLI_REFRESH_TOKEN"],
    )
    result = send_email(token, "austinngg996@gmail.com", f"☕ Morning Brew — {args.date}", html, plain)
    print(f"Sent. Message ID: {result['id']}")
