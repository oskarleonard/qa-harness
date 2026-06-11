# sim-qa — command cheatsheet

Eyes & hands for the AI on the iOS simulator. One front door:
**`scripts/sim-qa/qa <command>`** (self-contained — no npm scripts).
Layers: **`devserver.py`** (Metro / app lifecycle + crash capture),
**`qa.py`** (run journal + screenshot + log), **`idb_ui.py`** (tap by
accessibility label). Design: `README.md`. Operating procedure: `RUNBOOK.md`.

## Lifecycle — the commands you run by hand

| Command | Does |
|---------|------|
| `qa doctor`  | First-time machine check (sim, idb, app build, BE) — every FAIL prints its fix |
| `qa serve`   | Take over Metro on :8092 (owned + logged), start crash stream, force-reload the app from THIS Metro |
| `qa health`  | Metro up? local BE up (mock mode)? app vs launcher? idb companion? |
| `qa status`  | What holds the port, the tester's pid, log sizes |
| `qa recover` | Reconnect the app; restart Metro if down; **respawn the idb companion if dead** (e.g. a terminal force-quit left a stale socket) |
| `qa reload`  | Fallback reload (terminate + relaunch) when Fast Refresh doesn't apply a change — LAST resort |
| `qa logs [N]`    | Last N lines of the owned Metro log (JS warns/console/bundling) |
| `qa crashes [N]` | Crash-pattern hits from the OS log stream (native/red-box/fatal) |
| `qa stop`    | Kill the tester's Metro + crash stream (scoped to :8092) and free it |

> After `qa stop`, run `npm start` to bring back your own Metro and reopen the
> app from it.

## Eyes & hands — the QA loop runs these

```bash
scripts/sim-qa/qa init --scope <all|home|send|transactions|contacts|notifications|settings|workspace> \
                       [--driver wake|goal] [--label L]      # → run dir
scripts/sim-qa/qa shot <label>                               # screenshot + center RGB log
scripts/sim-qa/qa tree                                       # labelled a11y elements (what's tappable)
scripts/sim-qa/qa tap --label "AXLabel" [--force]            # tap by a11y label (refuses off-viewport/occluded targets; --force overrides)
scripts/sim-qa/qa tap --tab home|notifications               # tap a bottom tab (NativeTabs segment)
scripts/sim-qa/qa tap --frac 0.5,0.85                        # fraction fallback for unlabelled targets
scripts/sim-qa/qa scroll [down|up] [--amount 0.35]           # scroll native lists (frames y<0 / y>874 are off-viewport)
scripts/sim-qa/qa note <finding text>                        # append to findings.md
scripts/sim-qa/qa act <audit text>                           # append to actions.log
scripts/sim-qa/qa find <label>                               # locate without tapping
scripts/sim-qa/qa companion [ensure]                         # idb companion check / respawn
```

## API invariants — logic bugs the screen can't show

```bash
scripts/sim-qa/qa check                          # assert INV-1..7 vs local-BE ground truth (exit 1 on fail)
scripts/sim-qa/qa snapshot --out /tmp/b.json     # snapshot transaction states before an action
scripts/sim-qa/qa diff /tmp/b.json --expect-new 1  # delta probes D-1..D-3 (double-submit detector)
```

Registry + rules for adding new invariants: **`lisk/INVARIANTS.md`**.
Run `check` at the end of every QA loop (RUNBOOK has the full procedure).

## Design verification — screen vs Figma (on demand)

```text
/check-figma <screen> [state] [--strict] [--version 0.X]
   e.g.  /check-figma notifications
         /check-figma notifications empty --strict
         /check-figma home --version 0.4
```

Natural language works too ("check home against figma"). Registry + full
procedure: **`lisk/FIGMA_MAP.md`** (screen→node mapping, `current`-version
pointers, accepted deviations). Default mode judges structure + tokens — live
data is never a finding; `--strict` additionally flags px-level nits (spacing,
radii, alignment, one-step weight shifts) at a higher false-positive rate.

## Modes

```bash
scripts/sim-qa/qa serve                  # mock mode (default): MOCK_AUTH bundle, BE = localhost:8080
LISK_QA_MODE=staging scripts/sim-qa/qa serve   # staging mode (structured; see RUNBOOK "Tester modes")
```

Mock mode preflight: the local backend must answer on :8080 —
`cd ../lisk-backend && make run` (`qa health` checks it).

## Target & process hygiene

- The tester is **pinned** in `scripts/sim-qa/target.py` (sim UDID, Metro port,
  bundle, tab order). Change there to retarget; it only ever touches that
  sim/port. Parallel testers coexist by living on distinct sims/ports: lisk =
  iPhone 17 Pro / :8092, your dev Metro = :8081, and any other project's tester
  on its own sim / port.
- Owned Metro: pid `/tmp/lisk-tester-metro.pid`, log `/tmp/lisk-tester-metro.log`.
- Crash stream: `/tmp/lisk-tester-crash.log` (+ `.pid`).
- See/kill lingering manually: `lsof -ti tcp:8092` · `scripts/sim-qa/qa stop`.
- Run outputs (screenshots/findings/journal) live under
  `scripts/sim-qa/runs/<timestamp>__<scope>/` (gitignored).
