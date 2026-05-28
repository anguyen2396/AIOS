# Decisions Log

Append-only record of meaningful decisions and why they were made. `/level-up` Phase 2 (Method interview) writes scoped automation specs here. You can also append manually whenever you decide something worth remembering.

**Format per entry:**

```
## YYYY-MM-DD — Short title

**Decision:** what was decided.

**Why:** the reasoning, constraints, and what would change your mind.

**Alternatives considered:** what else was on the table.

**Owner:** who's accountable.
```

Keep it terse. Future-you will thank present-you for capturing the *why*, not just the *what*.

---

## 2026-05-28 — Demo/MVP scoped: AI lead conversion and management system

**Decision:** build a working lead conversion tool (cold → warm → booked) by 2026-06-06. Tool doubles as a live Stage 3 demo and as Austin's real sales pipeline.

**Why:** Stage 3 of the funnel requires a live demo. Using your own AIOS as the demo subject is the strongest possible proof of concept — "I built this for myself, here's what I'd build for you." A spreadsheet CRM with AI drafting and calendar follow-ups is achievable in one week with the tools already connected.

**Scope:** Google Sheet as CRM, `draft-outreach` skill, follow-up calendar automation, `pipeline-report` skill. No web UI. No auto-send.

**Roadmap:** `references/demo-mvp-roadmap.md` — 6 phases, Thu May 29 through Fri Jun 6.

**Owner:** Austin

---

## 2026-05-28 — /level-up paused mid-Phase 1

**Decision:** paused `/level-up` during Phase 1 Mindset interview. Resume next session — Austin to answer the weekly review questions before candidates are surfaced.

**Why:** ran out of time / context mid-session. Candidates seeded from vault: (1) Obsidian→Calendar action-item sync, (2) prospect follow-up management. Need Austin's own words to confirm which itches most.

**Next steps:**
- Resume `/level-up` next session — answer Phase 1 questions first
- Strongest candidate based on vault signals: Obsidian→Calendar sync

**Owner:** Austin

---

## 2026-05-27 — Rung 0 funnel and demo/MVP need validation before use

**Decision:** treat the current `references/rung-0-funnel.md` as a first draft only. Do not run it with a real prospect until the demo flow and setup session steps are verified against actual usage.

**Why:** funnel was drafted without running a live session. The demo (Stage 3) and setup session (Stage 4) are untested — what looks clean on paper may break in front of a prospect. One bad first session is harder to recover from than delaying by a week.

**Alternatives considered:** use it as-is and iterate after first session. Rejected — first impressions with warm-network prospects matter; LSV referrals especially.

**Next steps:**
- Run the full demo flow solo at least once (Austin's own AIOS as the demo subject)
- Identify gaps or awkward moments in the setup session steps
- Update the funnel doc after dry run before pitching to any real contact

**Owner:** Austin
