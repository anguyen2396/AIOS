"""
Send a message to Discord via webhook.
Usage: python scripts/send_discord.py "message text"
       echo "message" | python scripts/send_discord.py
Splits messages exceeding Discord's 2000-char limit into chunks.
"""

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_env():
    env_path = Path(__file__).parent.parent / ".env"
    env = {}
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def send_chunk(webhook_url: str, text: str):
    payload = json.dumps({"content": text}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return r.status


def send(webhook_url: str, message: str, chunk_size: int = 1990):
    # Split on newlines to avoid cutting mid-word
    chunks = []
    current = ""
    for line in message.splitlines(keepends=True):
        if len(current) + len(line) > chunk_size:
            if current:
                chunks.append(current.rstrip())
            current = line
        else:
            current += line
    if current.strip():
        chunks.append(current.rstrip())

    for i, chunk in enumerate(chunks):
        status = send_chunk(webhook_url, chunk)
        if status not in (200, 204):
            print(f"ERROR: chunk {i+1} returned HTTP {status}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    env = load_env()
    webhook_url = env.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL not set in .env", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = sys.stdin.read()

    if not message.strip():
        print("ERROR: no message provided", file=sys.stderr)
        sys.exit(1)

    send(webhook_url, message)
    print("Sent to Discord.")
