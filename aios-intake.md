# AIS-OS Intake

This is the source-of-truth file for your AIOS. Fill it in by typing, voice-pasting (Wispr Flow / OS dictation), or running `/onboard` for a guided conversation. Whichever mode, this file is what `/onboard` reads to scaffold your Day-1 setup.

**Hard cap: 7 questions.** Each answerable in under 60 seconds. Don't overthink — you can edit and re-run `/onboard` any time.

---

## Q1 — Who are you, what do you sell, who do you sell it to?

Identity, offer, ICP. One paragraph each is fine.

```
Austin is an AI Operating System consultant helping medium-size businesses integrate AI into their existing workflows.

Offer: A 4-rung ladder model.
- Rung 0: Consulting hour / AIOS setup — $100–$500 (start $50–$99 for reps). Goal: help owner stand up their own AIOS. Pitch at first touch with any new lead.
- Rung 1: Paid Audit — $500–$2,500. Goal: map workflows, document automation opportunities, write proposal. Pitch after 1–2 successful Rung 0 sessions when owner asks "what else?"
- Rung 2: Focused Build Project — $2,500–$10,000. Goal: ship one end-to-end workflow with measurable ROI. Pitch after audit identifies a clear, painful problem.
- Rung 3: Retainer — $3,000–$10,000+/month. Goal: ongoing optimization, expansion, training. Pitch after Rung 2 ships ROI and they ask "what's next?"

ICP: Medium-size business owners looking to integrate AI into existing workflows.

Background: Austin (Huy Anh Nguyen), born Oct 25 1996, Hanoi Vietnam. 9 years in Nebraska USA — BS Supply Chain Management, MS Information Management Systems. Current role at GearInc (BPO company) as process improvement and innovation lead. Also a certified Anaplan Level 3 Model Builder. Active futures trader — passed TopStep funded account challenge (Express Funded Account). Partnering with Let's Speak Vietnamese (letsspeakvietnamese.com) on the AI consulting startup; their owner brings marketing domain expertise.
```

---

## Q2 — Paste 1-2 things you've written recently. Don't edit them.

An email, a LinkedIn post, a DM, a doc — anything that sounds like you when you're not trying. **Paste verbatim.** Do not type these mid-conversation with Claude — chat-shaped samples are worse than no samples (voice contamination).

```
Sample 1 — work email:

Hello team,

I hope everyone is having a great start of the week.

For today's video queue, we are experiencing issues with videos failing to download into the tool. The download process is being halted, resulting in failed video loads

Sharing this id for a spot check: db5b7b471dcd4e22a663cd0c415feb08
```

```
Sample 2 — casual DM:

morning Mabell

VTC is the name of a company

not sure what its stand for though

9:01 AM

oh it's vietnam multimedia corporation
```

---

## Q3 — What are your 2-3 biggest priorities for the next 90 days?

Quarterly priorities. Not yearly aspirations. Things that, if not done by July, would make you say "I wasted Q2."

```
1. Trading: stay consistent — follow rules and setup now that TopStep funded account is live. No blowups.
2. Build the sales funnel/framework for the AI OS consulting business pitch (the 4-rung ladder).
3. Land first client, or at minimum get a real prospect through the full sales funnel end-to-end.
```

---

## Q4 — Where does revenue actually land, and where is it tracked?

Multiple answers OK. Stripe? Skool? GoHighLevel? QuickBooks? A spreadsheet?

```
- GearInc salary: bank transfer (Vietnam bank)
- Trading payouts (TopStep): not yet active / no tracking system set up
- Consulting income: not yet / no clients yet
- No formal tracking system in place currently
```

---

## Q5 — Where do you talk to customers, your team, and the outside world day-to-day?

Email (which one — Gmail / Outlook)? Slack? Teams? DMs (Skool / Discord / iMessage)? Phone?

```
- Email (Gmail)
- Google Chat (internal at GearInc)
- Facebook Messenger (clients / external)
- Instagram DMs (external / prospecting)
```

---

## Q6 — Where do meeting recordings, notes, and important docs live?

Granola? Otter? Fireflies? Google Drive? Notion? Dropbox? A folder on your desktop you keep meaning to organize?

```
- Obsidian (personal notes, knowledge base)
- Google Drive (docs, shared files)
- No meeting recording tool yet
```

---

## Q7 — What's the one task that eats your week, and where do you currently track work?

The single biggest time-suck or recurring drudgery. Plus where tasks/projects live (ClickUp / Asana / Linear / Notion / a notebook).

```
Top pain: manually updating schedule/calendar based on action items sitting in Obsidian. No automated bridge between notes and calendar.
Second pain: ideating and building the sales funnel + MVP for the AI OS consulting business — no structured system yet.
Task tracking: nothing formal in place yet; working to set one up.
```

---

When this file is filled, run `/onboard` (or re-run it) and the wizard will scaffold your Day-1 file set: `context/`, `references/voice.md`, populated `connections.md`, and a filled `CLAUDE.md`.
