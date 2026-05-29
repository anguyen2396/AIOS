---
name: morning-brew
description: Use when someone says "morning brew", "run morning brew", "daily brief", "daily sync", "sync my notes", or "what's my day look like". Reads Obsidian action items, syncs them to Google Calendar, outputs a prioritized daily plan, AND pulls AI news/YouTube/Anthropic/tool updates — all in one email.
argument-hint: [optional date, e.g. "tomorrow" or "2026-06-01"]
---

## What This Skill Does

One email. Two halves:
1. **Your Day** — reads Obsidian `[ ]` action items, syncs to Google Calendar, outputs prioritized daily plan
2. **AI World** — pulls AI news headlines, YouTube channel updates, Claude/Anthropic announcements, and new AI tool drops

## Inputs

- **Obsidian vault:** `C:\Users\Administrator\Desktop\austin-brain\Daily Notes\`
- **Google Calendar:** connected via MCP (`claude.ai Google Calendar`)
- **Goals context:** `context/priorities.md`
- **Date:** today unless argument specifies otherwise

---

## PART 1 — YOUR DAY

### Step 1 — Read Obsidian action items

Read all `.md` files in `C:\Users\Administrator\Desktop\austin-brain\Daily Notes\`.

Extract every line matching `- [ ]` (unchecked checkbox). For each item note:
- The text of the action item
- The date header it falls under (e.g. `## May 28, 2026`)
- Any time hint in the text (e.g. "at 3pm", "tomorrow", "by Friday")

Skip items under `## AIOS` or any section that is clearly meta/framework (not personal tasks).

### Step 2 — Check for existing calendar events

Using Google Calendar MCP, fetch events for today (and next 3 days if items reference future dates).

For each Obsidian action item: check if a calendar event with a similar title already exists. Match loosely — if the calendar has "Draft first outreach message" and the note has "Draft first outreach message tailored to warm contact", treat as duplicate. Skip creating if already exists.

### Step 3 — Create calendar events for unscheduled items

For each action item NOT already on the calendar:

- **If a date is specified in the item:** use that date
- **If no date:** use today
- **If a time is specified:** use that time
- **If no time:** create as a 30-minute block at **17:00 (5:00 PM)** local time (Asia/Bangkok)
- **Event title:** the action item text (trimmed)
- **Event description:** "Synced from Obsidian — [source note filename]"

Create the event. Log what was created.

### Step 4 — Fetch today's full calendar

Pull all calendar events for today using Google Calendar MCP. Include event title, start time, and end time.

### Step 5 — Read priorities

Read `context/priorities.md` for the current Q2/Q3 goals.

---

## PART 2 — AI WORLD

### Step 6 — AI News Headlines

Run 2 WebSearch queries:
- `AI news today site:thedecoder.ai OR site:venturebeat.com OR site:techcrunch.com`
- `artificial intelligence news [today's date]`

Extract 5–7 headlines. For each: Title | Source | one-sentence summary. Skip anything older than 48h. Prioritize model releases, funding, policy, major launches. Flag anything relevant to AI consulting, BPO automation, or trading/fintech.

### Step 7 — YouTube Channel Updates

Run one WebSearch per channel:
- `Nate Herk YouTube new video [current month year]`
- `Tina Huang YouTube new video [current month year]`
- `Greg Isenberg YouTube AI ideas [current month year]`
- `Matthew Berman AI YouTube [current month year]`

For each, extract the most recent 1–2 videos: Channel | Title | Date | URL (if available). YouTube lookback window: 14 days. No hallucinated URLs — omit if unsure.

### Step 8 — Claude / Anthropic Updates

Run WebSearch:
- `Anthropic Claude update announcement [current month year]`

Extract: model releases, API changes, pricing, new features. If nothing in last 7 days, write "No major updates this week."

### Step 9 — AI Tool Drops

Run WebSearch:
- `new AI tools launched [today's date] ProductHunt trending`

Extract 3–5 tools: Tool Name | one-line description | URL. Focus on tools relevant to consulting, automation, or trading.

---

## PART 3 — SEND

### Step 10 — Generate the brief data

Compile all data into variables:
- `DATE` — e.g. "Wednesday May 28, 2026"
- `SCHEDULE` — pipe-separated `time | title` lines, or "none"
- `ITEMS` — `\n`-joined action item texts, or "none"
- `P1`, `P2`, `P3` — top 3 priorities from `context/priorities.md`
- `NEEDLE` — single most important action today (specific, not generic)
- `CAL_NOTE` — e.g. "2 new events added. 1 item already scheduled."
- `NEWS` — `Title | Source | Summary\n...`
- `YOUTUBE` — `Channel | Title | Date | URL\n...`
- `ANTHROPIC` — one item per line, or "No major updates this week."
- `TOOLS` — `Tool | Description | URL\n...`

### Step 11 — Send the combined HTML email

Run:

```
python scripts/send_morning_brew.py \
  --date "Wednesday May 28" \
  --schedule "5:00 PM – 5:30 PM | Draft outreach message\n5:30 PM – 6:00 PM | Build Rung 1 audit" \
  --items "Draft first outreach message tailored to a warm contact\nBuild out Rung 1 audit template" \
  --p1 "Draft first outreach message — advances Priority 3" \
  --p2 "Trading session — protect the funded account" \
  --p3 "Build Rung 1 audit template — completes funnel skeleton" \
  --needle "Open rung-0-funnel.md, pick one warm contact, write Stage 1 message, send before 6 PM." \
  --cal-note "0 new events added. 2 items already scheduled." \
  --news "Title 1 | Source | Summary\nTitle 2 | Source | Summary" \
  --youtube "Nate Herk | Video Title | May 28 | https://...\nTina Huang | Video Title | May 27 | https://..." \
  --anthropic "Claude Opus 4.8 released — 4x better code reliability\nNew multiagent orchestration in Managed Agents" \
  --tools "Phasr | Run 100+ parallel workflows without losing context | https://..."
```

Log: `Email sent — Message ID: [id]`

If script fails, print digest in chat as fallback.

---

## Guardrails

- **No duplicate calendar events.** Always check before creating.
- **Don't create events in the past.** Flag those in the brief instead.
- **Top 3 must tie to goals.** Pull from `context/priorities.md`.
- **Needle-mover must be specific.** Not "work on funnel" — name the contact, the file, the step.
- **No hallucinated URLs.** Omit rather than guess.
- **Recency first.** Skip AI news older than 48h. YouTube lookback 14 days. Tools: this week only.
- **If Obsidian vault is empty:** skip sync, proceed with calendar + goals + AI digest only.

## Notes

- Timezone: **Asia/Bangkok (UTC+7)**
- Vault path: `C:\Users\Administrator\Desktop\austin-brain\Daily Notes\`
- Send to: austinngg996@gmail.com
- Script: `scripts/send_morning_brew.py`
- If argument provided (e.g. `/morning-brew tomorrow`), shift target date accordingly
