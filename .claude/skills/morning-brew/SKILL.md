---
name: morning-brew
description: Use when someone says "morning brew", "run morning brew", "daily brief", "daily sync", "sync my notes", or "what's my day look like". Reads Obsidian action items, syncs them to Google Calendar, then outputs a prioritized daily plan.
argument-hint: [optional date, e.g. "tomorrow" or "2026-06-01"]
---

## What This Skill Does

Two things in one run:
1. **Sync** — reads unchecked `[ ]` action items from Obsidian Daily Notes, creates Google Calendar events for any not yet scheduled
2. **Brief** — pulls today's calendar + open action items + Q2/Q3 goals and outputs a prioritized daily plan

## Inputs

- **Obsidian vault:** `C:\Users\Administrator\Desktop\austin-brain\Daily Notes\`
- **Google Calendar:** connected via MCP (`claude.ai Google Calendar`)
- **Goals context:** `context/priorities.md`
- **Date:** today unless argument specifies otherwise

## Step-by-Step

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

Pull all calendar events for today using Google Calendar MCP. Include the event title, start time, and end time.

### Step 5 — Read priorities

Read `context/priorities.md` for the current Q2/Q3 goals.

### Step 6 — Generate the daily brief

Output the brief in this exact format:

---

```
# ☕ Morning Brew — [Today's Date, e.g. Wednesday May 28]

## Today's Schedule
[list events with times, or "Nothing scheduled — clear day."]

## Open Action Items
[list all unchecked Obsidian items, grouped by note date]

## Top 3 Priorities
1. [highest leverage item tied to Q2/Q3 goals]
2. [second priority]
3. [third priority]

## One Thing to Move the Needle
→ [single most important action today — be specific, not generic]

---
🗓 [N] new events added to calendar. [M] items already scheduled.
```

---

### Step 7 — Send the HTML brief email

After outputting the brief in chat, run `scripts/send_morning_brew.py` with the brief data:

```
python scripts/send_morning_brew.py \
  --date "[e.g. Wednesday May 28]" \
  --schedule "[time | title lines joined by \n, or 'none']" \
  --items "[action item lines joined by \n, or 'none']" \
  --p1 "[priority 1 text]" \
  --p2 "[priority 2 text]" \
  --p3 "[priority 3 text]" \
  --needle "[the one needle-mover sentence]" \
  --cal-note "[N new events added. M items already scheduled.]"
```

The script generates a styled HTML email (dark header, colored section labels, green needle-mover callout) and sends directly to austinngg996@gmail.com via Gmail API.

Log one line after sending: `Email sent — Message ID: [id]`

If the script fails, note the error but do not block the rest of the skill — chat output is the fallback.

---

## Guardrails

- **No duplicate events.** Always check calendar before creating. If unsure, skip and mention it.
- **Don't create events in the past.** If an item's inferred date is already past, flag it in the brief instead.
- **Top 3 must tie to goals.** Never pick "busywork" as a top priority. Pull from `context/priorities.md` to anchor choices.
- **One needle-mover must be specific.** Not "work on the funnel" — "draft the Stage 1 outreach message for [specific contact]".
- **If Obsidian vault is empty or unreadable:** skip sync, proceed to brief with calendar + goals only. Note the skip.

## Notes

- Timezone for all calendar operations: **Asia/Bangkok (UTC+7)**
- Vault path: `C:\Users\Administrator\Desktop\austin-brain\Daily Notes\`
- If argument is provided (e.g. `/morning-brew tomorrow`), shift the target date accordingly
- After running, suggest appending a `## [Date]` section to Daily Notes if today's section is missing
