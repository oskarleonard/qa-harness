# web-qa — agent-driven QA for lisk-web (DEV TOOL)

Lets the AI **see and drive the web app in a real browser**, verify its own
changes, run autonomous QA rounds, assert backend invariants the UI can't
show, and compare screens against Figma. Ported from
`lisk-app-mobile/scripts/sim-qa` (its `PORTING_NOTES.md` is the canonical
porting guide) — the process layer is shared; the simulator-specific
eyes/hands were replaced by the **Playwright MCP**, which is strictly better
on web: real ARIA tree, native console + network introspection, no
gesture-system workarounds.

## One-time setup (per developer)

The Playwright MCP server is a pinned devDependency (`@playwright/mcp`), but
`.mcp.json` is gitignored in this repo (per-person by team convention), so add
it yourself — create or merge `.mcp.json` at the repo root:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "node_modules/.bin/playwright-mcp",
      "args": ["--browser", "chromium", "--viewport-size", "1440,900"]
    }
  }
}
```

Restart your Claude session afterwards; the `browser_*` tools appear. Browsers
come from the existing Playwright e2e setup (`bunx playwright install chromium`
if missing — `qa shot` will tell you).

## Layout

```
scripts/qa/
├── qa                   # the front door — `scripts/qa/qa help`
├── target.py            # the pin: tester port 3002, mode (local|msw|staging)
├── core/
│   ├── devserver.py     # tester's OWN Next dev server lifecycle (your :3000
│   │                    # is never touched), mode env injection, logs
│   └── qa.py            # run journal/findings/audit + `qa shot` (archival
│                        # full-page screenshots — app states are
│                        # URL-addressable in mock modes)
├── lisk/
│   ├── INVARIANTS.md    # backend-invariant registry (MIRRORS the mobile copy)
│   ├── qa_api.py        # `qa check` / `qa snapshot` / `qa diff`
│   └── FIGMA_MAP.md     # design-verification registry (/check-figma)
├── RUNBOOK.md           # how the AI runs a QA round (operating procedure)
├── COMMANDS.md          # cheatsheet (wrapper + the MCP browser_* tools)
└── runs/                # per-run output (gitignored)
```

## Tester modes (target.py MODE — `LISK_QA_MODE` env)

- **local (default):** local backend + MSW off + mock auth — mirrors
  `bun dev:local-backend`. Requires `cd ../lisk-backend && make run`.
  Full write freedom (local data); backend invariants apply.
- **msw:** MSW full mode — pure-frontend determinism, no backend. Invariants
  don't apply; ideal for UI-only checks and design verification.
- **staging:** real auth; the tester can't log in itself (a human signs in
  once in the tester's browser session); rails are read-mostly.

## The division of labor

- **Playwright MCP** = live eyes/hands: navigate, click by role/name, type,
  read the ARIA snapshot, read console messages + network requests,
  screenshot the live session.
- **`scripts/qa/qa`** = everything around it: the pinned tester server, the
  compaction-proof run journal + audit log, archival screenshots, and the
  backend-invariant sweep.

## Guardrails (non-negotiable)

- The tester owns ONLY :3002 — never kills your dev server.
- Money flows: allowed in local mode (local data) but every confirm is
  logged (`qa act`) + screenshotted. Forbidden in staging.
- Console-error and failed-request sweeps are part of every QA iteration —
  see RUNBOOK.
