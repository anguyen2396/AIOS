# Connections

Registry of every system Austin's AIOS can reach. `/audit` checks this file for domain coverage and freshness.

| # | Domain | Tool | Mechanism | Auth | Last checked |
|---|---|---|---|---|---|
| 1 | Revenue / Financials | Bank transfer (Vietnam) + TopStep (trading) | not yet connected | — | — |
| 2 | Customer interactions | Facebook Messenger, Instagram DMs | not yet connected | — | — |
| 3 | Calendar | Google Calendar | mcp (`claude.ai Google Calendar`) | OAuth | 2026-05-28 |
| 4 | Communication | Gmail | mcp (`claude.ai Gmail`) | OAuth | 2026-05-28 |
| 4b | Communication | Google Chat, Facebook Messenger, Instagram | not yet connected | — | — |
| 5 | Project / task tracking | None yet (building system) | not yet connected | — | — |
| 6 | Meeting intelligence | None yet (no recording tool) | not yet connected | — | — |
| 7 | Knowledge / files | Obsidian (notes) | direct file read (`C:\Users\Administrator\Desktop\austin-brain`) | none needed | 2026-05-28 |
| 8 | Knowledge / files | Google Drive (docs) | mcp (`claude.ai Google Drive`) | OAuth | 2026-05-28 |

**Mechanism options:** `mcp` (MCP server), `script` (Python/Bash hitting an API, in `scripts/`), `export` (CSV/JSON dump pipeline), `key+ref` (`.env` key + `references/{tool}-api.md` guide), `not yet connected`.

When you wire a new tool, also save `references/{tool}-api.md` capturing endpoints, auth flow, and common queries — researched-once-saved-forever.

**Day 2 recommendation:** highest-leverage first connection is Google Calendar via MCP — directly attacks Austin's top pain (Obsidian → calendar bridging).
