# web-qa — command cheatsheet

One front door: **`scripts/qa/qa <command>`** (self-contained — no
package.json changes). The agent's live eyes/hands are the **Playwright MCP**
(`browser_*` tools — setup in README.md). Operating procedure: RUNBOOK.md.

## Tester server (pinned :3002 — your dev :3000 is never touched)

| Command | Does |
|---------|------|
| `qa serve`  | Start the tester's Next dev server in the active mode (exit 1 if it never comes up) |
| `qa health` | Server up? Backend up (local mode)? Exit 1 when anything is down |
| `qa status` | Pid, port holders, log size |
| `qa logs [N]` | Last N lines of the tester server log (compile errors live here) |
| `qa stop`   | Kill the tester's server (this port only) |

Modes: `qa serve` (local, default) · `LISK_QA_MODE=msw qa serve` ·
`LISK_QA_MODE=staging qa serve`. Local mode needs
`cd ../lisk-backend && make run` first.

## Run bookkeeping + archival evidence

```text
scripts/qa/qa init --scope <all|home|send|transactions|contacts|notifications|settings|workspace> \
                   [--driver wake|goal] [--label L]
scripts/qa/qa shot <label> [path]     # full-page screenshot of APP_URL+path into the run
                                      # (routes are workspace-slug-scoped, e.g. /devcorp/transactions)
                                      # (fresh context — local/msw modes; staging uses the
                                      # MCP's in-session browser_take_screenshot)
scripts/qa/qa note <finding text>
scripts/qa/qa act <audit text>
```

## Backend invariants — logic bugs the screen can't show (local mode only)

```text
scripts/qa/qa check                          # assert INV-1..7 vs backend ground truth
scripts/qa/qa snapshot --out /tmp/b.json     # snapshot transaction states before an action
scripts/qa/qa diff /tmp/b.json --expect-new 1  # delta probes (double-submit detector)
```

Registry: **`lisk/INVARIANTS.md`** (mirrors the mobile copy — same backend).

## Design verification — screen vs Figma (on demand)

```text
/check-figma <screen> [--strict] [--version 0.X]
```

Registry + procedure: **`lisk/FIGMA_MAP.md`** (web Figma file; no screens
mapped yet — the file documents how to add the first).

## Playwright MCP quick reference (the agent's hands)

| Tool | Use |
|---|---|
| `browser_navigate` | open `qa target --url` + path |
| `browser_snapshot` | ARIA tree — roles/names/states; prefer over pixels |
| `browser_click` / `browser_type` | act on snapshot element refs |
| `browser_console_messages` | EVERY iteration — errors/warnings are findings |
| `browser_network_requests` | EVERY iteration — swallowed 4xx/5xx are findings |
| `browser_take_screenshot` | in-session eyes (archival → `qa shot`) |
| `browser_resize` | responsive probes (375 / 768 / 1440) |

## Process hygiene

- Tester server: pid `/tmp/lisk-web-tester-next.pid`, log `/tmp/lisk-web-tester-next.log`.
- See/kill manually: `lsof -ti tcp:3002` · `scripts/qa/qa stop`.
- Run outputs live under `scripts/qa/runs/<timestamp>__<scope>/` (gitignored).
