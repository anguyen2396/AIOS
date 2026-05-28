# Demo MVP — AI Lead Conversion & Management System
**Target:** rough version done by 2026-06-06
**Purpose:** live proof of concept for Stage 3 demos. You run this on your own sales pipeline. Prospect sees it live. "This is what I'd build for you."

---

## System overview

```
CAPTURE                ENRICH              DRAFT            MANAGE            DASHBOARD
──────────             ──────────          ──────           ──────────        ──────────
Facebook Ads  ─┐                           Channel-aware    Status            Pipeline funnel
Website Form  ─┼─► Google Sheet ─► AI  ─► message draft ─► tracking    ─►   By channel
In-person QR  ─┘    (CRM)        research  (human review)  + follow-up       By location
                                            + send          cadence           By rep / week
```

---

## Pipeline stages

```
New → Contacted → Responded → Qualified → Demo Scheduled → Won
                                                         ↘ Lost
                                                         ↘ Nurture (not ready, stay warm)
```

---

## Stack

| Layer | Tool | Mechanism |
|---|---|---|
| CRM / data | Google Sheets | gws CLI + Python scripts |
| Web capture | Google Form | native Form → Sheet link |
| In-person capture | Google Form (QR code) | same form, Source=In-Person |
| Facebook capture | Facebook Lead Ads CSV export | `import_facebook_leads.py` |
| Research | Python + Claude prompt | `research_lead.py` |
| Outreach drafting | Claude skill | `draft-outreach` |
| Status management | Python + Claude skill | `update_status.py` + `stale-leads` skill |
| Follow-up calendar | Google Calendar MCP | auto-created on message approve |
| Dashboard | Google Sheets (native charts) | Dashboard tab |

---

## Google Sheet architecture

**File name:** `AIOS Lead Pipeline`
**Location:** Ideas folder (`1-di3hj-MvK_9y9kl50Sk_PQRQClL1Bsw`)

### Tab 1: Leads (main data)

| Column | Values / Notes |
|---|---|
| Lead_ID | Auto (YYYYMMDD-NNN) |
| Name | |
| Company | |
| Role | |
| Email | |
| Phone | |
| Location | City / Country |
| Channel | Facebook / Website / In-Person |
| Campaign | Ad name, form name, or event/meeting name |
| Assigned_Rep | Austin (default) — field exists for scaling |
| Status | New / Contacted / Responded / Qualified / Demo_Scheduled / Won / Lost / Nurture |
| Date_Created | |
| Date_Last_Contact | |
| Date_Next_Followup | |
| Followup_Count | Number |
| Research_Notes | AI-generated: what they do, likely pain, personalization hook |
| Last_Message_Preview | First 100 chars of last outbound message |
| Days_In_Stage | Formula: TODAY() - Date_Last_Contact |
| Tags | e.g. LSV-referral, luxury-retail, warm-network |
| Notes | Manual free text |

### Tab 2: Dashboard
Google Sheets native charts — pipeline funnel, channel split, conversion rates, weekly activity.

### Tab 3: Templates
Channel-specific message scaffolds for reference (not used directly by scripts, but visible in demo).

---

## Follow-up cadence by status

| Status | Trigger | Action |
|---|---|---|
| New | Lead added | +1 day: "Contact [Name] — new lead from [Channel]" |
| Contacted | Message sent, no reply | +3 days, +7 days, +14 days → auto-move to Nurture |
| Responded | They replied | +1 day: follow up while hot |
| Qualified | 2/3 qual questions yes | +2 days: book demo |
| Demo_Scheduled | Demo on calendar | +1 day before: prep reminder. +1 day after: follow-up |
| Nurture | No response after 14 days | +30 days: re-engagement check |

---

## Channel-aware draft tone

| Channel | Register | Notes |
|---|---|---|
| Facebook | Casual, short, emoji ok | They saw an ad — don't be formal |
| Website | Semi-formal, slightly longer | They came to you — show you read their context |
| In-Person | Warm, reference the meeting | They already know you — skip the intro |

---

## Phase 1 — Sheet architecture + Google Form setup (Thu May 29)

- [ ] Create Google Sheet "AIOS Lead Pipeline" in Ideas folder with all columns above
- [ ] Set up Dashboard tab with placeholder charts (populate after data exists)
- [ ] Create Google Form: Name, Company, Role, Email, Phone, Location, Source (Website / In-Person), Notes
  - Link form responses directly to Leads tab
  - Set Source field to pre-fill "In-Person" for QR code version
- [ ] Generate QR code linking to the In-Person pre-filled form URL (use qr-code generator, no signup needed)
- [ ] Add 2–3 dummy leads to test dashboard charts
- [ ] Add Sheet ID + Form URL to `connections.md`

---

## Phase 2 — Multi-channel intake scripts (Fri May 30)

- [ ] Write `scripts/add_lead.py` — manual CLI intake (Name, Company, Role, Channel, etc.) → appends row to sheet with auto Lead_ID
- [ ] Write `scripts/import_facebook_leads.py` — reads Facebook Lead Ads CSV export → deduplicates by email → appends new rows to sheet
  - Facebook Lead Ads exports from Ads Manager: Ads Manager → Lead Center → Download
  - Column mapping: Full Name → Name, Company Name → Company, Email → Email, etc.
- [ ] Test: add 1 manual lead, import 1 Facebook CSV row, submit 1 Google Form — all land in correct columns

---

## Phase 3 — Research + enrichment (Mon Jun 2)

- [ ] Write `scripts/research_lead.py`
  - Input: Lead_ID (reads row from sheet)
  - Outputs structured research block saved to Research_Notes column:
    1. What the company does (1 line)
    2. Likely pain point — mapped to AIOS offer (bottleneck, manual process, knowledge locked in one person)
    3. Personalization hook (something specific: industry context, channel context, any detail from notes)
    4. Suggested approach angle (based on channel: casual / semi-formal / warm)
  - Source: notes already in sheet + any manual context Austin adds before running
  - No external API required for v1 — prompt-based synthesis of what's already known
- [ ] Test: run research on 3 dummy leads, verify Notes column updates

---

## Phase 4 — Draft-outreach skill v2 (Tue Jun 3)

- [ ] Create `.claude/skills/draft-outreach/SKILL.md`
  - Input: Lead_ID
  - Reads: lead row + Research_Notes + channel + `references/rung-0-funnel.md` Stage 1 template + `references/voice.md`
  - Adjusts tone for channel (see channel table above)
  - Output: draft message shown to Austin for review — never auto-sends
  - On Austin approval:
    - Saves first 100 chars to Last_Message_Preview column
    - Sets Status → Contacted, Date_Last_Contact → today, Followup_Count +1
    - Creates Google Calendar follow-up event per cadence table
- [ ] Test: run `/draft-outreach [Lead_ID]` for one Facebook lead and one in-person lead — verify tone difference

---

## Phase 5 — Status management + stale lead alerts (Wed Jun 4)

- [ ] Write `scripts/update_status.py` — change Status for a lead + log Date_Last_Contact + trigger next follow-up calendar event per cadence table
- [ ] Create `.claude/skills/stale-leads/SKILL.md`
  - Reads sheet
  - Surfaces leads where Days_In_Stage exceeds cadence threshold (e.g. Contacted with no update in 7+ days)
  - Outputs: list of overdue leads + suggested next action per lead
  - Run manually or as part of `/morning-brew`
- [ ] Test: mark a lead Contacted, advance clock 8 days, run `/stale-leads` — verify it surfaces

---

## Phase 6 — Dashboard (Thu Jun 5)

Build Dashboard tab in Google Sheets using native chart tools. No external BI tool needed for v1.

- [ ] Pipeline funnel: bar chart showing lead count at each stage (New / Contacted / Responded / Qualified / Demo / Won / Lost)
- [ ] By channel: pie or bar chart — Facebook vs Website vs In-Person lead count
- [ ] By location: if Location column has data, group by city/country
- [ ] By rep: column chart (Austin only for now, field ready for scaling)
- [ ] Weekly activity summary (formula-driven):
  - Messages sent this week
  - Responses received
  - Demos scheduled
  - New leads added
- [ ] Conversion rates (formula column on Dashboard tab):
  - Contacted / New (outreach rate)
  - Responded / Contacted (response rate) → target 40%+
  - Qualified / Responded (qualification rate)
  - Demo / Qualified (demo booking rate)
  - Won / Demo (close rate)
- [ ] Test: populate with 5–10 dummy leads across channels — verify charts update

---

## Phase 7 — Demo dry run + polish (Fri Jun 6)

- [ ] Write `references/demo-script.md` — step-by-step what Austin says and shows during Stage 3 demo
- [ ] Run full end-to-end: Facebook import → research → draft → approve → calendar follow-up → status update → stale-leads check → dashboard refresh
- [ ] Fix any rough edges
- [ ] Take screenshots of each step for async demo (send via Messenger/Zalo before call)

---

## Definition of "rough version done" (June 6)

- All 3 channels feed into one sheet cleanly
- New lead → research → draft runs in under 5 minutes total
- Draft is channel-aware (tone differs between Facebook / Website / In-Person)
- Follow-up auto-created on message approval, follows cadence table
- Dashboard shows pipeline funnel + channel breakdown + conversion rates
- Stale-leads surfaces overdue follow-ups on demand

**Out of scope for v1:**
- Automated Facebook webhook (manual CSV export is fine for demo)
- Auto-monitoring email/DM for replies
- Lead scoring algorithm
- Multi-rep assignment logic
- Export to external CRM (HubSpot, Salesforce)

---

## V2 features (after first paying client)

- Facebook webhook → real-time capture without CSV export
- Gmail monitoring: flag when a lead replies → auto-update status
- Lead scoring: rank leads by engagement + fit signals
- Multi-rep: assign leads, track by rep in dashboard
- Testimonial capture: prompt Austin after Won stage to log case study to `references/case-studies.md`

---

## Demo story (Stage 3 script seed)

> "Every lead — Facebook ad, website form, or someone I met in person — lands here automatically. I run one command, it researches them, drafts a message in my voice with the right tone for where they came from, and the moment I approve it, it books the follow-up in my calendar. If I go 7 days without touching a lead, it flags me. This dashboard shows me exactly where my pipeline is leaking. I built this in a week. That's what I'd build for your sales process — except tuned to your business, your words, and the channels your customers actually use."
