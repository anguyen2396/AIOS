"""
Send an email via Gmail API using OAuth refresh token.
Usage: python scripts/send_gmail.py --to "email" --subject "subject" --body "body"
       echo "body" | python scripts/send_gmail.py --to "email" --subject "subject"
"""

import argparse
import base64
import json
import sys
import urllib.parse
import urllib.request
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


def send_email(token, to, subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = to
    msg["Subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", default=None)
    args = parser.parse_args()

    body = args.body if args.body else sys.stdin.read()
    if not body.strip():
        print("ERROR: no body provided", file=sys.stderr)
        sys.exit(1)

    env = load_env()
    token = get_access_token(
        env["GOOGLE_WORKSPACE_CLI_CLIENT_ID"],
        env["GOOGLE_WORKSPACE_CLI_CLIENT_SECRET"],
        env["GOOGLE_WORKSPACE_CLI_REFRESH_TOKEN"],
    )
    result = send_email(token, args.to, args.subject, body)
    print(f"Sent. Message ID: {result['id']}")
