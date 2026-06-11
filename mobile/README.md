# sim-qa — simulator eyes & hands for the AI (DEV TOOL)

One self-contained folder that lets the AI **see and drive the iOS simulator**:
screenshot → read the a11y tree → tap by accessibility label → drive flows. The
human says *"QA the send flow for 1h, find and fix bugs"*; the AI drives +
evaluates + fixes on a branch → PR.

The **AI drives + evaluates** (decides what to test, judges screenshots, writes
findings); the scripts are **dumb mechanics** (screenshot / tap / log / Metro
lifecycle). Tooling: `xcrun simctl` + `idb`.

## First-time setup (new developers)

```bash
brew tap facebook/fb && brew install idb-companion        # native daemon
python3 -m venv ~/.idb-venv && ~/.idb-venv/bin/pip install fb-idb   # idb CLI
scripts/sim-qa/qa doctor                                  # checks everything;
                                                          # every FAIL prints its fix
```

> Note: `idb` will NOT be on your PATH (`zsh: command not found: idb` is
> expected) — the venv keeps it isolated and the tooling calls it by absolute
> path (`~/.idb-venv/bin/idb`, pinned in `target.py`). `qa doctor` verifies the
> right location.

`doctor` also resolves your simulator: the target device (`DEVICE_NAME` in
`target.py`, currently iPhone 17 Pro) is discovered on first run — preferring a
booted one, then the newest iOS — and pinned to the gitignored
`scripts/sim-qa/target.local`, so the choice is stable per machine forever
after. To retarget: delete `target.local` (re-discovers) or write a UDID into
it (or `export LISK_QA_UDID=<udid>`). If the app isn't installed on that sim
yet, `doctor` prints the exact build command.

## Layout

```
scripts/sim-qa/
├── qa                   # the front door — `scripts/sim-qa/qa help`
├── target.py            # THIS project's pin (sim UDID / port / bundle / mode)
├── core/                # portable engine (any Expo dev-build project)
│   ├── common.py        # primitives: screenshot, PNG decode, idb tap
│   ├── idb_ui.py        # a11y-tree access + tap by label/tab/fraction
│   ├── devserver.py     # Metro lifecycle pinned to target.PORT + backend check
│   ├── crashlog.py      # OS-level crash-pattern capture via simctl log stream
│   └── qa.py            # per-run journal + screenshot bookkeeping
├── RUNBOOK.md           # how the AI runs a QA round (operating procedure)
├── COMMANDS.md          # command cheatsheet
├── PORTING_NOTES.md     # porting this to another Expo app (this repo is the
│                        # canonical source — it has evolved past its ancestor)
├── lisk/                # app-specific layer
│   ├── INVARIANTS.md    # living registry of asserted API invariants
│   ├── qa_api.py        # `qa check` / `qa snapshot` / `qa diff`
│   └── FIGMA_MAP.md     # design-verification registry (/check-figma)
└── runs/                # per-run output (gitignored)
```

## Pinning — runs in parallel with other projects

`target.py` pins the tester to **one iPhone 17 Pro (per-machine pin in
`target.local`) + Metro :8092**. Any other project's tester on this machine
runs on a different sim + port, and your own dev Metro owns :8081 — they all
coexist. The tester never kills Metro on another port or drives another sim.

The tester **repoints the installed dev app** (`com.lisk.app.development`) to
its own Metro via a dev-client deep link. To get your own dev session back
afterwards: `scripts/sim-qa/qa stop`, then `npm start` and reopen the app from
your Metro (press `i`) or the dev launcher.

## Tester modes (target.py MODE)

- **mock (V1 default):** tester Metro sets `EXPO_PUBLIC_MOCK_AUTH=true` →
  Clerk/Privy stubbed, biometric gate skipped, app lands on tabs, API =
  `localhost:8080`. **The local backend must be running:**
  `cd ../lisk-backend && make run`.
- **staging (structured, not yet operational):** real Clerk against
  api-staging. Needs a one-time human login on the tester sim; rails become
  read-mostly. Recipe in RUNBOOK.md.

Both modes set `EXPO_PUBLIC_AI_TESTER=true`, which gates tester-only app
affordances (the BottomSheet escape hatch) — regular dev / Detox / EAS bundles
are unaffected.

## QA loop — model-driven, compaction-proof

- `qa.py` = deterministic mechanics + logging (cheap, no model).
- The model decides what to test, VIEWS select screenshots, writes findings,
  updates the journal — paced by `/qa-tester-wake` (ScheduleWakeup) or
  `/qa-tester` (/goal). See `.claude/commands/`.
- **State lives on disk** (`runs/<id>/journal.md`), re-read each iteration, so
  a mid-run context compaction is survivable. See RUNBOOK.md.

## Guardrails (non-negotiable)

- **Verify-before-act**: screenshot + confirm the screen before tapping.
- **Money flows**: allowed in mock mode (local data) but every Confirm/Send/
  Approve is logged + screenshotted for post-run audit.
- **Never tap Sign Out in mock mode** — the mock Clerk can't log back in
  (recovery: `qa reload`).
- **Full audit**: every action lands in `actions.log` + a screenshot.

## Cost

Saving screenshots is free (local I/O); the model *viewing* them costs tokens.
The loop stays cheap by using the logged `center_rgb` signal for routine steps
and only viewing screens that look off or are key.
