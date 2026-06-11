# web-qa RUNBOOK — how the AI runs a QA round

The **AI drives + evaluates + (by default) fixes**; the Playwright MCP is its
eyes/hands and `scripts/qa/qa` is the bookkeeping. The human says e.g. *"find
and fix bugs in the send flow for 1h"* or *"report only, 30m"*, then reviews
the result. Ported from `lisk-app-mobile/scripts/sim-qa/RUNBOOK.md` — the
discipline is identical; the mechanics are web-native.

## Two modes (what to do with bugs)
- **find-and-fix (default):** find bugs AND fix the ones with a clear,
  verifiable root cause — on a dedicated branch, one commit per fix, ending in
  a PR. Escalate (log only) the ambiguous / architectural ones.
- **report-only:** find + log, no code changes. Triggered by "report only" /
  "just find" / "don't fix".

## Tester modes (which world — target.py MODE)
- **local (default):** tester server runs with local backend + mock auth
  (mirrors `bun dev:local-backend`). Preflight: backend must answer on :8080
  (`qa health` checks; if DOWN, STOP: `cd ../lisk-backend && make run`).
  Writes are local → exercising send/approve flows is allowed AND wanted.
- **msw:** MSW full mode — deterministic frontend, no backend. UI/flow/design
  checks only; `qa check` does not apply.
- **staging:** real auth. The tester cannot log in (OAuth); a human signs in
  once in the MCP browser session. Rails flip to **read-mostly**: never
  click Send / Confirm / Approve / Submit / Delete.

## Eyes and hands — the Playwright MCP
- `browser_navigate(url)` — go to `qa target --url` + path
- `browser_snapshot()` — the ARIA tree: roles, names, states. Prefer it over
  screenshots for finding things; it's the web's `qa tree`, but better
- `browser_click` / `browser_type` / `browser_select_option` — by element ref
  from the snapshot (no pixel guessing, no occlusion problem)
- `browser_take_screenshot()` — in-session eyes (use `qa shot <label> <path>`
  instead when you want the image ARCHIVED in the run folder)
- `browser_console_messages()` — **check every iteration**: errors and
  warnings are findings (hydration mismatches especially)
- `browser_network_requests()` — **check every iteration**: 4xx/5xx responses
  the UI swallowed are findings
- `browser_resize(w, h)` — responsive probes

## Run a QA loop
1. **Own the tester server:** `qa serve` → `qa health` (exit 0 = server +
   backend green). Your dev server on :3000 is untouched.
2. **(fix mode) Clean tree + branch:** require clean `git status` — if dirty,
   STOP and have the human commit/stash. Then create `qa-auto/<scope>-<STAMP>`
   off the current branch; note the base branch for the PR.
3. **Start a run:** `qa init --scope <scope> --driver <wake|goal> --label <STAMP>`.
4. **Seed `runs/<id>/journal.md`**: mode, tester mode, bound (deadline + a
   step cap), base branch, HARD RULES, nav map, plan. The journal IS the
   loop's state — re-read it every iteration; it survives compaction.
5. **Self-pace** per the invoked skill (`ScheduleWakeup` ≈90s) — or in
   watchdog mode (`/loop 3m /qa-tester-wake <args> --driven`) the harness
   re-fires on a fixed timer even if an iteration crashed; the skill then
   never self-schedules, and post-finish firings are journal-guarded no-ops
   until the loop is cancelled.
6. **Each iteration:** re-read journal FIRST. Then: STEP0 stop-check →
   STEP1 `qa health` → STEP2 `browser_console_messages` +
   `browser_network_requests` (new errors/failed requests = findings) →
   STEP3 snapshot/screenshot → assess → `qa note` bugs → STEP4 (fix mode)
   Fix flow → STEP5 navigate deeper → STEP6 update journal.
7. **Finish (bound reached):** append the final **`## Summary`** section to
   `findings.md` (that exact heading is the completion sentinel). Run the
   **invariants sweep** first in local mode: `qa check` — each failure is a
   finding. (fix mode) commits exist → push `qa-auto/<...>` + open a PR
   (title only, no body — repo convention); else report the branch name.

## Scopes
`all | home | send | transactions | contacts | notifications | settings | workspace`
(same product surfaces as mobile). Routes are WORKSPACE-SLUG-SCOPED:
`/<workspaceSlug>/transactions` etc. (seeded slug: `devcorp`); a bare
`/transactions` silently lands on Home. Derive routes from the sidebar nav in
the first ARIA snapshot — don't guess.

## Fix flow (find-and-fix mode, per bug)
1. **Triage:** CODE_BUG (clear, localized → fix) · PLATFORM_LIMITATION
   (needs new dependency, infra, design decision → log + skip) ·
   TEST_ARTIFACT (your own setup/expectation — e.g. backend down, MSW
   handler missing → discard, fix the setup).
2. **Fix — strict scope guard:** smallest change, repo style (no comments,
   named exports, cn(), kebab-case). Fix the buggy *pattern* everywhere it
   repeats, not just one screen.
3. **Verify:** Next dev hot-reloads; re-drive the repro via the MCP; confirm
   gone, console clean, no new failed requests, then `bun run typecheck` +
   `bun run lint` pass. Re-check screens already PASSed this run —
   regressions = failed verify.
4. **Commit or revert:** one atomic commit per verified fix
   (`fix(web): <subject>` style). Unverified → revert.
5. **Stuck-loop cap:** max 2 attempts per bug, then escalate as a finding.

## PR evidence for visual fixes (host via `qa publish` — NEVER the PR branch)
A find-and-fix run that changed anything ON-SCREEN should SHOW it in the PR body,
not just describe it:
- **Before/after montage per visual fix** — same screen, pre- vs post-fix, side by
  side. `before` = the failing state you logged; `after` = the verified fix after the
  Next hot-reload. Build it with ImageMagick (`magick montage …`) at full res;
  **never downscale the source** (bakes in blur).
- **Host it OFF the PR branch:** `scripts/qa/qa publish <montage.png> --feature <flow>-<topic> [--caption "…"]`.
  It appends the PNG to the append-only, never-merged `qa-assets` orphan branch and prints
  the `<img src="…/blob/qa-assets/<feature>/<file>?raw=true" width="580">` tag for the PR body —
  keeping montages out of `main` AND the PR's Files-changed. **Never `git add` a PNG on the run
  branch** (on squash-merge it lands in `main`).
- **One-line "what changed" caption above each image** so the diff reads at a glance.

Logic-only fixes (no on-screen change) need no montage — `## Summary` + repro suffice.

## HARD RULES (non-negotiable)
- **Branch isolation:** fixes land on `qa-auto/<stamp>` only; never commit to
  the human's branch. **Verify-or-revert.** **≤2 attempts per bug.**
- **Console + network sweep every iteration** — a clean-looking screen with a
  500 in the network log is a finding, not a pass.
- **Navigate via the ARIA snapshot** (roles/names), not coordinates. An
  element you can't address by role/name is itself an accessibility finding.
- **Money-flow audit (local mode):** before EVERY click on a Confirm/Send/
  Approve/Submit-style control: `qa shot` + `qa act CONFIRM <what>`. In
  staging those clicks are FORBIDDEN.
- **Invariants sweep before Finish (local mode):** `qa check`
  (registry: `lisk/INVARIANTS.md`). Bracket risky actions with
  `qa snapshot` / `qa diff --expect-new N` (double-submit probe).
- **Recovery hierarchy:** in-app navigation → `browser_navigate` back to a
  known route → page reload → `qa serve` (server restart) last.
- **Image-processing error = stop the loop (cost hazard, never self-heals in-session).**
  If the console shows `API Error: an image in the conversation could not be processed
  and was removed`, or a screenshot read comes back with no image, an oversized
  image (>2000px on a side — the model API's cap once a conversation carries
  many images) is in the history. ONE such image poisons every later image
  read in the session, including already-sent ones (verified live in the
  reflex-hz sibling sim-qa rig), and every strip-and-retry invalidates the
  prompt cache, so all remaining turns bill at near-full price. Do NOT keep
  QA-ing through it and do NOT retry the read — write current state to
  `findings.md`, end the session, resume fresh. Web-specific prevention:
  archival `qa shot` images are FULL-PAGE (long routes blow past 2000px tall)
  and belong in the run folder, NOT in the conversation — use the MCP's
  viewport-sized `browser_take_screenshot()` for in-session eyes, and read
  archived shots / montages / Figma exports only via a `sips -Z 1800` copy.
- **No new dependencies / installs** in the loop — log instead.
- Self-recover (`qa health` / `qa serve`), don't ask.

## Active bug-hunt checklist (probe, don't just happy-path)
At least 1-2 per round: console-error sweep on every route visited ·
failed/4xx/5xx network responses the UI swallowed · hydration-mismatch
warnings · forms: invalid amounts (0, negative, huge, `1,23`), required-empty,
rapid double-submit · cross-path consistency (same entity via two routes) ·
empty vs populated states (fresh BE vs after creating data) · responsive
breakpoints (`browser_resize` 375/768/1440) on key screens · keyboard nav +
focus visibility on one flow per round · React Query staleness (mutate, check
other screens reflect).

## Design verification (on demand — `lisk/FIGMA_MAP.md`)
`/check-figma <screen> [--strict]`: resolve the node in FIGMA_MAP.md, fetch
the Figma render (MCP `get_screenshot` → curl into `runs/<id>/figma/`),
capture the app at the same route + viewport (`qa shot`), judge
structure+tokens by default. Strict mode may MEASURE (computed styles vs
Figma variables) — see FIGMA_MAP.

## Limits
- The wake loop is session-scoped (terminal open, Mac awake).
- MSW mode: no backend behavior under test; staging: read-only.
- A fresh `qa shot` context sees mock-auth states only — staging screenshots
  must come from the MCP's logged-in session.

## Cleanup
`qa stop` · run output in `scripts/qa/runs/<timestamp>__<scope>/` (gitignored).
