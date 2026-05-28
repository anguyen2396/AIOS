"""
AIOS Pitch Deck Builder
Calls Google Slides API directly using OAuth refresh token.
Usage: python scripts/build_pitch_deck.py
"""

import json
import sys
import urllib.request
import urllib.parse

# ── OAuth ─────────────────────────────────────────────────────────────────────
import os
from pathlib import Path

def _load_env():
    env_path = Path(__file__).parent.parent / ".env"
    env = {}
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env

_env = _load_env()
CLIENT_ID     = _env["GOOGLE_WORKSPACE_CLI_CLIENT_ID"]
CLIENT_SECRET = _env["GOOGLE_WORKSPACE_CLI_CLIENT_SECRET"]
REFRESH_TOKEN = _env["GOOGLE_WORKSPACE_CLI_REFRESH_TOKEN"]
PRESENTATION_ID = "1whd2y7jI158J2e97tNw1X9GACP4wpXaOq8MBP7A5LEA"

PT = 12700   # 1pt in EMU
W  = 9144000
H  = 5143500


def get_access_token():
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["access_token"]


def api(method, url, token, body=None):
    data = json.dumps(body).encode() if body else None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"API ERROR {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def batch_update(token, requests):
    url = f"https://slides.googleapis.com/v1/presentations/{PRESENTATION_ID}:batchUpdate"
    return api("POST", url, token, {"requests": requests})


# ── Slide content builders ────────────────────────────────────────────────────
DARK   = {"red": 0.12, "green": 0.12, "blue": 0.12}
GRAY   = {"red": 0.45, "green": 0.45, "blue": 0.45}
ACCENT = {"red": 0.10, "green": 0.30, "blue": 0.60}


def text_box(slide_id, obj_id, text, x, y, w, h, font_size=14, bold=False, color=None):
    reqs = [
        {"createShape": {
            "objectId": obj_id,
            "shapeType": "TEXT_BOX",
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": {"width": {"magnitude": w, "unit": "EMU"}, "height": {"magnitude": h, "unit": "EMU"}},
                "transform": {"scaleX": 1, "scaleY": 1, "translateX": x, "translateY": y, "unit": "EMU"},
            },
        }},
        {"insertText": {"objectId": obj_id, "text": text, "insertionIndex": 0}},
        {"updateTextStyle": {
            "objectId": obj_id,
            "textRange": {"type": "ALL"},
            "style": {
                "bold": bold,
                "fontSize": {"magnitude": font_size, "unit": "PT"},
                **({"foregroundColor": {"opaqueColor": {"rgbColor": color}}} if color else {}),
            },
            "fields": "bold,fontSize" + (",foregroundColor" if color else ""),
        }},
    ]
    return reqs


def create_slide(slide_id):
    return [{"createSlide": {"objectId": slide_id, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}]


# ── Fetch first slide ID ──────────────────────────────────────────────────────
print("Getting access token...")
token = get_access_token()

print("Fetching presentation...")
pres = api("GET", f"https://slides.googleapis.com/v1/presentations/{PRESENTATION_ID}", token)
first_slide = pres["slides"][0]["objectId"]

slide_ids = [first_slide, "slide_2", "slide_3", "slide_4", "slide_5"]

# ── Build requests per slide, send each separately ───────────────────────────

# --- CREATE slides 2-5 ---
print("Creating slides 2-5...")
batch_update(token, [
    {"createSlide": {"objectId": sid, "slideLayoutReference": {"predefinedLayout": "BLANK"}}}
    for sid in slide_ids[1:]
])

# --- SLIDE 1: Title ---
print("Building slide 1 — Title...")
s = first_slide
batch_update(token,
    text_box(s, "s1_tag",      "AI CONSULTING",                                                   60*PT,  55*PT, 300*PT,  30*PT, font_size=10, bold=True, color=ACCENT) +
    text_box(s, "s1_title",    "Your AI Operating System",                                        60*PT,  90*PT, 620*PT,  80*PT, font_size=36, bold=True, color=DARK) +
    text_box(s, "s1_sub",      "How we build AI that knows your business — and runs without you.", 60*PT, 180*PT, 620*PT,  45*PT, font_size=16, color=GRAY) +
    text_box(s, "s1_prospect", "Prepared for: [Prospect Name / Company]",                         60*PT, 360*PT, 420*PT,  30*PT, font_size=12, color=GRAY) +
    text_box(s, "s1_by",       "Austin Nguyen  |  AI OS Consultant",                              60*PT, 395*PT, 420*PT,  28*PT, font_size=11, color=GRAY)
)

# --- SLIDE 2: The Problem ---
print("Building slide 2 — The Problem...")
s = "slide_2"
body = (
    "→  [Pain point 1 — e.g., Spending hours on tasks you've done 100 times]\n"
    "→  [Pain point 2 — e.g., Knowledge locked in your head, not in your systems]\n"
    "→  [Pain point 3 — e.g., Growth bottlenecked by manual processes]\n\n"
    "Replace [ ] with what you learn in discovery."
)
batch_update(token,
    text_box(s, "s2_label",  "THE PROBLEM",                                       60*PT,  40*PT, 250*PT,  25*PT, font_size=10, bold=True, color=ACCENT) +
    text_box(s, "s2_title",  "You're the bottleneck in your own business.",        60*PT,  72*PT, 650*PT,  60*PT, font_size=26, bold=True, color=DARK) +
    text_box(s, "s2_body",   body,                                                 60*PT, 155*PT, 680*PT, 195*PT, font_size=16, color=DARK) +
    text_box(s, "s2_note",   "\U0001F4DD PREP: Fill in the 3 pains before presenting.", 60*PT, 395*PT, 500*PT, 28*PT, font_size=11, color=GRAY)
)

# --- SLIDE 3: The Solution ---
print("Building slide 3 — The Solution...")
s = "slide_3"
c1 = "EXPERTISE EXTRACTION\n\nTurn your knowledge into AI workflows. The business runs the way you would — even when you're not there."
c2 = "CONNECTED WORKFLOWS\n\nYour email, calendar, docs, and tools move data automatically. No more copy-paste."
c3 = "BOTTLENECK REMOVAL\n\nIdentify the 3–5 tasks only you handle today. Build systems that run them on autopilot."
outcome = "WHAT SUCCESS LOOKS LIKE:  6+ hrs/week returned  •  Customer response: hours → minutes  •  New-hire ramp time cut 30–50%"
batch_update(token,
    text_box(s, "s3_label",   "THE SOLUTION",                                          60*PT,  40*PT, 250*PT,  25*PT, font_size=10, bold=True, color=ACCENT) +
    text_box(s, "s3_title",   "AI that knows your business and works while you don't.", 60*PT,  72*PT, 650*PT,  55*PT, font_size=26, bold=True, color=DARK) +
    text_box(s, "s3_col1",    c1,  60*PT, 155*PT, 210*PT, 230*PT, font_size=13, color=DARK) +
    text_box(s, "s3_col2",    c2, 290*PT, 155*PT, 210*PT, 230*PT, font_size=13, color=DARK) +
    text_box(s, "s3_col3",    c3, 520*PT, 155*PT, 200*PT, 230*PT, font_size=13, color=DARK) +
    text_box(s, "s3_outcome", outcome, 60*PT, 405*PT, 680*PT, 28*PT, font_size=11, color=ACCENT)
)

# --- SLIDE 4: Roadmap ---
print("Building slide 4 — Roadmap...")
s = "slide_4"
rungs = [
    ("RUNG 0", "Discovery Hour",  "$50–$500",  "60-min paid session. We stand up your AIOS together. You leave with a working system that knows your business."),
    ("RUNG 1", "Deep Audit",      "Quoted",         "We map every workflow. Find the top automation opportunities. You get a written build plan with ROI estimates."),
    ("RUNG 2", "Build Project",   "Quoted",         "We ship one end-to-end workflow with measurable ROI. Audit fee credited against project cost."),
    ("RUNG 3", "Ongoing Support", "Retainer",       "Continuous optimization, new workflow expansion, and team training on your AIOS."),
]
reqs = (
    text_box(s, "s4_label", "THE ROADMAP",                              60*PT,  40*PT, 250*PT,  25*PT, font_size=10, bold=True, color=ACCENT) +
    text_box(s, "s4_title", "Four rungs. Start small. Scale what works.", 60*PT,  72*PT, 650*PT,  55*PT, font_size=26, bold=True, color=DARK) +
    text_box(s, "s4_note",  "\U0001F4DD PREP: Circle the rung you're pitching today.", 60*PT, 405*PT, 450*PT, 28*PT, font_size=11, color=GRAY)
)
for i, (rung, name, price, desc) in enumerate(rungs):
    x = (60 + i * 170) * PT
    reqs += (
        text_box(s, f"s4_r{i}_rung",  rung,  x, 155*PT, 155*PT, 22*PT, font_size=9, bold=True, color=ACCENT) +
        text_box(s, f"s4_r{i}_name",  name,  x, 182*PT, 155*PT, 25*PT, font_size=14, bold=True, color=DARK) +
        text_box(s, f"s4_r{i}_price", price, x, 212*PT, 155*PT, 20*PT, font_size=11, color=GRAY) +
        text_box(s, f"s4_r{i}_desc",  desc,  x, 237*PT, 155*PT, 140*PT, font_size=11, color=DARK)
    )
batch_update(token, reqs)

# --- SLIDE 5: Next Step ---
print("Building slide 5 — Next Step...")
s = "slide_5"
body5 = (
    "Book a free 20-minute call. I'll show you the system live on my own business.\n"
    "If it fits — we do your setup session the same week.\n\n"
    "What you get from the discovery call:\n"
    "  ✓  Your current workflows mapped\n"
    "  ✓  3 quick wins identified\n"
    "  ✓  A clear build plan if we proceed\n\n"
    "[Your booking link or contact here]"
)
aside = "\U0001F4DD CUSTOMIZE:\n\n• Add your booking link\n• Add WhatsApp / Zalo\n• Swap in their pain from slide 2"
batch_update(token,
    text_box(s, "s5_label", "NEXT STEP",         60*PT,  40*PT, 250*PT,  25*PT, font_size=10, bold=True, color=ACCENT) +
    text_box(s, "s5_title", "Start with one hour.", 60*PT, 72*PT, 600*PT,  55*PT, font_size=32, bold=True, color=DARK) +
    text_box(s, "s5_body",  body5,               60*PT, 145*PT, 490*PT, 260*PT, font_size=16, color=DARK) +
    text_box(s, "s5_aside", aside,              590*PT, 145*PT, 160*PT, 260*PT, font_size=11, color=GRAY)
)

print("\n✓ Done.")
print(f"Open: https://docs.google.com/presentation/d/{PRESENTATION_ID}/edit")
