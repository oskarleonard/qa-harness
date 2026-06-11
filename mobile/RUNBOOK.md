# sim-qa RUNBOOK — how the AI runs a QA round

The **AI drives + evaluates + (by default) fixes**; the scripts are just eyes/hands
on the iOS simulator. The human says e.g. *"find and fix bugs in the send flow for
1h"* or *"report only, 30m"*, then reviews the result (a PR + a findings list).
This is the operating procedure. Design: README.md. Pinned sim/port: target.py.
All commands below go through the front door: **`scripts/sim-qa/qa <cmd>`**.

## Two modes (what to do with bugs)
- **find-and-fix (default):** find bugs AND fix the ones with a clear, verifiable root
  cause — on a dedicated branch, one commit per fix, ending in a PR. Escalate (log
  only) the ambiguous / architectural / native ones.
- **report-only:** find + log, no code changes. Triggered by "report only" /
  "just find" / "don't fix".

## Tester modes (what world the app runs in — target.py MODE)
- **mock (V1 default):** the tester's Metro bundles `EXPO_PUBLIC_MOCK_AUTH=true` →
  Clerk/Privy aliased to stubs, biometric gate skipped, app lands on `(tabs)`,
  axios targets `http://localhost:8080`. **Preflight: the local backend must
  answer on :8080** (`qa health` checks) — if DOWN, STOP and tell the human:
  `cd ../lisk-backend && make run`. The BE accepts any Bearer token in dev mode.
  All data is local → exercising send/approve flows is allowed AND wanted.
- **staging (structured, not yet operational):** `LISK_QA_MODE=staging qa serve` —
  no mock env; the app talks to api-staging with REAL Clerk auth. The tester
  CANNOT log in itself (OAuth runs in a system web-auth session). Recipe: a human
  logs in once on the tester sim (session persists via expo-secure-store; keep the
  Face ID app-setting off). Rails flip to **read-mostly**: never tap
  Send / Confirm / Approve / Submit / Delete — observe and screenshot only.
- Limitations under mock (from CLAUDE.md): Privy wallet flows are no-ops;
  **logging out strands the app on `/(auth)`** (mock Clerk can't re-login —
  recovery: `qa reload`, the mock re-authenticates on mount).

## Two loop drivers (pick at invocation time)
- **`/qa-tester-wake`** — `ScheduleWakeup`-driven, one-step invocation. The skill does
  preflight + every iteration + every reschedule itself. Best for interactive dev
  sessions where you start it and walk away.
- **`/qa-tester`** — `/goal`-driven, two-step invocation. The skill does preflight then
  prints a ready-to-paste `/goal …` command; from there `/goal`'s Stop hook drives
  every turn. Adds a live elapsed/turns/tokens overlay. Required for `claude -p` /
  Remote Control / CI pipelines.
- **Watchdog variant of the wake driver:** `/loop 3m /qa-tester-wake <args>
  --driven` makes the HARNESS the pacemaker — it re-fires the skill on a fixed
  timer even if an iteration crashed before self-scheduling (the self-paced
  loop's one silent-death mode). The skill then never schedules its own wakes;
  post-finish firings are journal-guarded no-ops until the loop is cancelled.
  Ask for "watchdog mode" and the agent composes the /loop line.
- Both follow the SAME iteration body (§6) and the same Fix flow / HARD RULES.

## Run a QA loop
1. **Own Metro:** `qa serve` (starts Metro AND force-reloads the app from it — a
   foregrounded app may be running another Metro's bundle) → `qa health` (metro UP
   + backend UP (mock) + app state `app` + idb companion UP — all four green
   before iter 1; anything off → `qa recover`).
2. **(fix mode) Clean tree + branch:** require a clean `git status` — if dirty, STOP
   and have the human commit/stash first (never entangle their work). Then create +
   checkout `qa-auto/<scope>-<STAMP>` off the current branch; remember the base
   branch for the PR.
3. **Start a run:** `qa init --scope <scope> --driver <wake|goal> --label <STAMP>`
   → run dir `runs/<auto-ts>__<scope>__<driver>-<STAMP>/`.
4. **Seed `runs/<id>/journal.md`** with: mode (find-and-fix/report-only), tester mode,
   bound (deadline + screenshot cap), base branch, the HARD RULES, a nav-map, a plan,
   next-steps. The journal IS the loop's state — re-read it every iteration; it
   survives compaction.
5. **Self-pace** per the invoked skill (`ScheduleWakeup` ≈90s, or `/goal`'s Stop hook).
6. **Each iteration:** Re-read `runs/<id>/journal.md` FIRST (durable state). Then:
   - STEP0 stop-check (`date` + screenshot count; at bound → §7 Finish)
   - STEP1 `qa health` (anything down → `qa recover`)
   - STEP2 `qa logs` + `qa crashes` (note real warns/errors + crash-pattern hits)
   - STEP3 Read latest screenshot → assess → `qa note` any bug
   - STEP4 (fix mode) if fixable → run the **Fix flow**
   - STEP5 navigate (rules below) → `qa shot <label>`
   - STEP6 update journal (Tested / Nav map / Next steps).
   - **After dismissing a sheet**, verify via `qa tree`: the sheet's own labels
     (heading / its buttons / `Bottom sheet handle`) must be GONE. Background
     content being present does NOT prove the sheet closed — gorhom keeps the
     background reachable in the a11y tree.
7. **Finish (bound reached):** append the final **`## Summary`** section to
   `findings.md` — that exact heading is the run's completion sentinel (the
   file itself exists from init; the `/goal` driver greps for the heading);
   (fix mode) if
   `git log <base>..qa-auto/<scope>-<STAMP> --oneline` shows commits, push the branch
   and open a PR into the base (`gh pr create --base <base> --fill`) — if no
   remote/auth, leave the branch local and report its name. Report and stop.

## PR evidence for visual fixes (MANDATORY when a fix changes the screen)
A find-and-fix run that changed anything ON-SCREEN must SHOW the change in the PR
body, not just describe it:
- **Before/after montage per visual fix** — same screen, pre- vs post-fix, side by
  side. `before` = the failing state you logged; `after` = the verified fix captured
  on a **cold reload** (`qa reload`), NOT a Fast-Refresh frame — Fast-Refresh
  screenshots can show transient clipping that isn't in shipped code, so verify the
  real result first.
- **High-res source, width-constrained display.** Render the montage at full res
  (~600px/frame); **never downscale the source** to shrink it (bakes in blur).
  Constrain only the DISPLAY in the PR body: `<img src="…?raw=true" width="580" />`
  — **580px is the standard.**
- **One-line "what changed" caption above each image** (e.g. *"account names now
  capitalized (main account → Main Account)"*) so the diff reads at a glance.
- **Host images on the `qa-assets` orphan branch — NOT the PR/run branch.** Run
  `scripts/sim-qa/qa publish <montage.png> --feature <flow>-<topic> [--caption "…"]`:
  it appends the PNG to the append-only, never-merged `qa-assets` branch and prints
  the `<img src="…/blob/qa-assets/<feature>/<file>?raw=true" width="580">` tag to paste
  into the PR body. This keeps montages out of `main` AND out of the PR's Files-changed.
  **Never `git add` a PNG on the run branch** — on squash-merge that lands it in `main`
  (had to be manually stripped from PRs #193/#194 before this command existed).

Logic-only fixes (no on-screen change) need no montage — the `## Summary` + repro suffice.

## Scopes (which surfaces to visit)
`all | home | send | transactions | contacts | notifications | settings | workspace`

| scope | surfaces |
|---|---|
| home | accounts overview, balances, recent transactions, account detail |
| send | payment flow: recipient → amount → method → review → confirm (mock only) |
| transactions | list, filters, detail, annotate/categorize, attachments, export |
| contacts | list, create (payment methods), detail |
| notifications | list, read/unread, badge sync |
| settings | profile, workspace settings, members, security |
| workspace | switcher, register-workspace, join-organization |

Derive the live nav-map from `qa tree` on the first iteration — don't guess labels.

## Fix flow (find-and-fix mode, per bug)
1. **Triage — classify first:**
   - **CODE_BUG** — clear, localized root cause (dead handler, backwards label,
     missing null-guard, crash with a stack) → **fix it.**
   - **PLATFORM_LIMITATION** — native/needs-rebuild, push notifications, Privy
     wallet, performance, anything not verifiable on-screen, or needs a new
     dependency → **log + skip.**
   - **TEST_ARTIFACT** — the "bug" is in your own repro/expectation (e.g. BE down,
     mock-auth limitation), not the app → discard, don't log it as a product bug.
2. **Fix — strict scope guard:** change ONLY the failing behaviour's code. No new
   files, no refactors/extractions, no routing changes; if it's visual, touch only
   className. Smallest change, in the codebase's style — BUT fix the buggy *pattern*
   in all its instances, not just the one screen. (JS/TSX hot-reloads via Fast Refresh.)
   Priority when several: P0 render/crash → P1 logic/nav → P2 a11y → P3 visual polish.
3. **Verify — replay + regression check:** edits Fast-Refresh in ~1-2s; if a change
   doesn't apply (red box, or a non-component edit), `qa reload` (cold restart).
   Replay the repro (logged tap sequence); confirm the bug is gone, the screen is
   sane, Metro/crash logs clean, and `npm run check` passes.
   THEN re-check screens you already passed this run — if the fix broke a
   previously-PASS screen, that's a **regression** (treat as a failed verify).
4. **Commit or revert:** verified + no regression → commit just that fix (message =
   bug + repro + why), one commit per fix. Not verified / regressed → revert, then
   retry or escalate per the cap below.
5. **Stuck-loop cap:** max **2 fix attempts per bug**. If the 2nd still fails to
   verify, STOP fixing it — log an escalated finding noting "tried A, then B —
   neither verified" — and move on. Record each attempt in the journal so a
   post-compaction resume never re-tries a fix already known to fail.

## HARD RULES (non-negotiable)
- **Branch isolation:** fixes land on `qa-auto/<stamp>` ONLY. NEVER commit to or push
  the human's branch or `main`; never force-push. The PR is the review gate.
- **Verify-or-revert:** never keep an unverified fix.
- **Bounded fixing:** ≤ 2 fix attempts per bug, then escalate — never spiral.
- **Tap by accessibility label (idb):** `qa tree` lists every labelled element +
  frame; tap with `qa tap --label "AXLabel"` (content) or `qa tap --tab
  home|notifications` (the iOS 26 floating pill is probed via describe-point —
  naive segment math taps empty glass). `--frac fx,fy` is a last-resort fallback
  for unlabelled targets. Always `tree` first so you tap a real element, not a
  pixel guess. An element the tester can't find = a missing `accessibilityLabel`
  = **itself a finding** (this repo's a11y convention requires labels on all
  interactive elements).
- **Frames are viewport-relative — check before tapping.** `qa tree` reports
  a11y frames for OFF-SCREEN scrollable content too: `y < 0` = scrolled past,
  `y > ~874` = below the fold, and anything overlapping the Tab Bar group's
  frame (`y ≳ 790`) is occluded by the floating pill. Taps at those coords hit
  nothing or the tab bar (verified live: two Retry taps silently hit the tab
  bar / dead space). **`qa tap --label` refuses such targets itself** and tells
  you to scroll first (`--force` overrides, e.g. for system-dialog buttons).
  `qa scroll down|up [--amount 0.4]`, re-`tree`, then tap. Scrolling works on
  native RN ScrollView/FlatList; RNGH-handled gestures (gorhom drag,
  swipeables) still ignore synthesized touches.
- **Money-flow audit (mock mode):** exercising send/approve IS in scope — the data
  is local. But EVERY tap on a Confirm / Send / Approve / Submit-style button must
  be preceded by `qa shot` and logged via `qa act CONFIRM <what>` so the human can
  audit the run afterwards. In **staging** mode these taps are FORBIDDEN.
- **Never tap Sign Out / Log Out in mock mode** — the mock Clerk cannot log back
  in; you'll strand the run on `/(auth)`. If it happens: `qa reload` (mock
  re-authenticates on mount). Treat any flow that *requires* logout as
  PLATFORM_LIMITATION (log + skip).
- **Recovery hierarchy — prefer in-app navigation; `qa reload` is the LAST resort.**
  1. **Stuck on a gorhom sheet?** → tap its own labelled Close/Cancel button if it
     has one; else `qa tap --label "ModalCloseButtonForAITester"` (the invisible
     tester-escape in the shared BottomSheet wrapper — only present in
     tester-driven bundles).
  2. **Stuck mid-flow?** → labelled Back / Cancel buttons, or `qa tap --tab home`.
  3. **`qa tree` returns EMPTY / taps silently no-op (but the screenshot shows a
     populated screen)?** → the **idb companion died**. `qa recover` self-heals
     (probes + respawns). `qa health` reports `idb companion: UP/DOWN`. Don't
     mistake an empty tree for "nothing on screen" — cross-check a screenshot.
  4. **Genuinely stuck** (red box, hung JS, unresponsive after companion respawn,
     lost track of the nav stack) → `qa reload`.
- **Gorhom bottom-sheets — backdrop tap and drag-down DON'T work** (RNGH ignores
  idb-synthesized touches). Dismiss via the sheet's own labelled buttons, or the
  tester-escape label above. If a sheet that should have closed didn't, dismiss and
  re-check `qa tree` before declaring downstream state a bug.
- **Native `UISwitch` (raw RN `<Switch>`) — taps DON'T flip it** (verified in the sim
  Settings app: idb taps no-op even dead-center on the control; a short horizontal
  swipe across its frame DOES toggle it). lisk is currently immune: our switches are
  `@rn-primitives/switch` (Pressable-based, `component-lib/switch.tsx`), so plain
  `tap --label` works. Only relevant if a raw RN `<Switch>` ever sneaks in — prefer
  a whole-row `Pressable` toggle pattern over a tester workaround.
- **Image-processing error = stop the loop (cost hazard, never self-heals in-session).**
  If the console shows `API Error: an image in the conversation could not be processed
  and was removed`, or a screenshot read comes back with no image, an oversized image
  (>2000px on a side — the model API's cap once a conversation carries many images) is
  in the history. ONE such image poisons every later image read in the session,
  including already-sent ones (verified live in the reflex-hz sibling rig, its commit
  `c109a97`), and every strip-and-retry invalidates the prompt cache, so all remaining
  turns bill at near-full price. Do NOT keep QA-ing through it and do NOT retry the
  read — write current state to `findings.md`, end the session, resume fresh.
  `qa shot` downscales to ≤1800px precisely to prevent this; if the banner appears
  anyway, some other path shipped a full-res image — likely a PR-evidence **montage**
  (side-by-side panels add up past 2000px wide — read back a `sips -Z 1800` copy,
  keep the full-res file for the PR) or a raw `simctl io screenshot`.
- **No new dependencies / installs / native rebuilds** in the loop — log those instead.
- **Self-recover, don't ask** (scoped to target.py's sim/port): `qa health` / `qa recover`.

## Active bug-hunt checklist (do these, don't just happy-path-navigate)

Visiting each screen and seeing it looks "fine" is coverage breadth without depth.
The patterns below only show up when you actively probe — sprinkle 1-2 per QA
round, not every item every iter. **Do not end the loop early** — STEP0 exits ONLY
on deadline or shot-cap; "the happy path looks done" is the signal to go *deeper*.

### Modal & overlay residue
- After every sheet dismissal: `qa tree` → the sheet's labels must be gone.
- Modal-from-modal (e.g. selector sheet inside send flow): close the inner one,
  verify the outer one is still in the expected state.

### Forms & validation (banking's bread and butter)
- Amount inputs: `0`, negative, absurdly large, `1,23` vs `1.23`, letters, empty.
  Expected: clean validation errors, never NaN/crash/silent-accept.
- Rapid double-tap on Send/Confirm — double-submit guard (duplicate transaction?).
- Required-field-empty submits; whitespace-only text fields.

### Cross-path consistency
- Same entity via two paths: transaction detail via Home recent-list vs
  Transactions tab — identical data? Account balance on Home vs account detail?
- Open a sheet, switch tab, come back — note which behaviour you observe
  (still open vs dismissed); surface to product if unclear which is intended.

### Empty vs populated states
- Fresh local BE = mostly empty states; after exercising flows, revisit the same
  screens populated. Both must render cleanly (no clipped empty-state art, no
  spinner-forever).
- Mutate something (annotate a transaction, rename) → do OTHER screens showing
  that entity update (React Query invalidation bugs hide here)?

### Settings → runtime effect
- Change one setting per round (e.g. workspace name, a toggle), verify it's
  reflected everywhere it appears, then tab away/back (persisted?), then
  `qa reload` (still persisted? — MMKV/Zustand vs server state confusion).

### Permission/role gating
- Note which actions render for the current role; permission-gated UI that's
  *visible but dead* (tap does nothing) is a finding. Testing OTHER roles needs
  different accounts — observe + log, don't try to mutate roles.

## Design verification (on demand — `lisk/FIGMA_MAP.md`)
When asked to check a screen against design ("check X against Figma",
`/check-figma X`): resolve the node in **FIGMA_MAP.md** (it decodes the
version-sectioned Figma jungle and carries the `current` pointer per screen),
fetch the Figma render via MCP `get_screenshot` (curl the PNG into
`runs/<id>/figma/`), capture the sim in the SAME screen+state, view both, and
judge in **structure+tokens** mode by default (`--strict` only on request).
Data differences are never findings; missing/extra elements, layout order,
token/typography drift are. Log each as a `[design]` finding; record
team-blessed divergences in the screen's accepted-deviations list. Screens not
in the map yet: follow FIGMA_MAP's "Adding a screen" recipe first.

## Limits
- Both drivers are session-scoped — they fire only while this terminal/session
  stays alive and the Mac stays awake. Not a background daemon.
- Visual / crash / flow / on-screen-logic bugs + JS-TSX fixes only. Can't judge
  push notifications, Privy wallet flows (mock no-ops), real OAuth, performance,
  or anything not visible on screen.
- RNGH-gesture surfaces (swipe-to-X, drag) can't be exercised via idb — log as
  not-automatable rather than reporting "broken".

## API-invariant sweep (`scripts/sim-qa/lisk/` — MANDATORY at end of loop)
Screenshots verify rendering; they cannot verify arithmetic. Before §7 Finish,
run **`qa check`** — it reads ground truth from the LOCAL BE's REST API (any
Bearer in dev mode) and asserts the registry in **`lisk/INVARIANTS.md`**
(INV-1..7: decision-counter drift, status↔threshold coherence, soft-FK orphans,
pagination merge gaps, filter partition, balance-history contract). Exit 1 =
one logged finding PER failed invariant — paste the full output into
`findings.md`.

Additionally, bracket risky actions with the delta probes:
`qa snapshot --out /tmp/before.json` → do the action in the app →
`qa diff /tmp/before.json --expect-new 1` (D-1 exactly-one-created /
D-2 status transitions / D-3 nothing-ever-disappears). The double-submit probe
(rapid double-tap on Send) is `--expect-new 1` — two new rows = a real bug.

**Seeded data is static — write paths are only under test when the round
CREATES something.** A sweep over purely seeded rows verifies the fixture and
the read-path computation (pagination/filter/history code), but not the write
paths (create/reject/cancel/annotate → counters). `qa check` prints a coverage
line (`N seeded, M live-created`) and warns when M = 0 — every find-and-fix
round should drive at least one create or cancel through the app so INV-1..4
also run against rows the production write path just produced.

When a triaged failure turns out to be the CHECKER's fault (over-strict rule,
wrong field), fix `qa_api.py` AND its row in `INVARIANTS.md` together — the
registry must always match the implementation.

## Cleanup
`qa stop` (kill the tester's Metro + crash stream) · `qa status` · then
`npm start` for your own Metro. Run output: `runs/<timestamp>__<scope>/` (gitignored).
