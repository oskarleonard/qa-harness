# Porting sim-qa from THIS repo to another Expo app

This folder is the **canonical source** for new ports (it has evolved well past
the earlier tester it grew from — see "Why port from here"). The porting agent
should read `README.md` + `RUNBOOK.md` + `COMMANDS.md`
first — they carry ~80% of the operating knowledge. This file carries the rest:
the port map, the per-app values, and the empirical gotchas that cost a day
each if rediscovered.

## Port map — what to copy vs rewrite vs skip

| Piece | Action |
|---|---|
| `core/` (5 files) + `qa` wrapper | **Copy as-is.** Generic: Metro lifecycle, deep-link recovery, a11y tap/scroll with guardrails, crash capture, run bookkeeping, doctor. All app specifics live behind `target.py`. |
| `target.py` | **Rewrite the values, keep the structure** (incl. the auto-resolve + `target.local` pin). See "Per-app values". |
| `lisk/` (qa_api.py + INVARIANTS.md) | **Do NOT copy — re-derive.** This asserts THIS app's backend ground truth. Port the *pattern* (see "Invariants layer"), write your own invariants. |
| `README/COMMANDS/RUNBOOK` | Keep the spine (loop body, Fix flow, HARD RULES, recovery hierarchy, bug-hunt checklist); swap scopes, rails, and app specifics. |
| `.claude/commands/qa-tester*.md` | Port directly; the "Rails" sections are the per-app customization point. |
| `.claude/dev-mode.py` + `auto-verify-{on,off}.md` + `settings.json` hook | Port directly. Per-repo decision: default OFF for shared/company repos, ON acceptable for solo repos. statusLine ALWAYS stays personal (`settings.local.json`) — a shared statusLine replaces every teammate's status bar. |

## Why port from here (improvements over the earlier original)

- **Self-contained `qa` wrapper** — zero `package.json` pollution; the consumer
  is the agent, not humans, so npm-script ergonomics were never the point.
- **`qa doctor`** — new-machine onboarding; every FAIL prints its fix.
- **Portable sim pin** — `DEVICE_NAME` auto-resolved on first run, persisted to
  gitignored `target.local` (stable like a hardcoded UDID, but works on every
  teammate's machine). `LISK_QA_UDID`-style env override.
- **Tap guardrails** — `qa tap --label` refuses off-viewport / tab-bar-occluded
  targets (a11y frames include off-screen scroll content; taps there silently
  no-op or hit the bar). `--force` overrides. Plus `qa scroll` (clamped band).
- **Hardened recovery** — iOS "Open in <app>?" dialog auto-approval;
  SpringBoard + dev-client-error-screen detection; `serve` force-reloads so the
  app can't keep another Metro's bundle (matters with mode-flavored bundles);
  127.0.0.1 deep links (sims share host loopback; LAN IPs break on wifi change).
- **Scriptable lifecycle** — serve/recover/health exit non-zero on failure.
- **Fixed /goal exit condition** — the original exited on "findings.md exists",
  which is true from init; the sentinel is the `## Summary` heading, written
  only at Finish.
- **Mode flag** (`mock`/`staging` via `METRO_ENV`) + **tester-only app
  affordances gated on an env var** the tester Metro sets (here
  `EXPO_PUBLIC_AI_TESTER`) so regular dev / E2E / store bundles are untouched.
- **Invariants layer pattern** with a registry file and seeded-vs-live coverage
  reporting.

## Per-app values to derive (target.py — don't copy lisk's)

- `DEVICE_NAME` — pick a sim model **no other project's tester uses** on the
  same machine (lisk = iPhone 17 Pro; another project's tester picks a different
  model → they run in parallel).
- `PORT` — distinct from the app's dev Metro AND every other tester (8081 dev /
  8092 lisk are taken on this machine; any other tester picks its own port).
- `BUNDLE` + `SCHEME` — from `app.config.ts` (dev-flavor bundle id; URL scheme
  for dev-client deep links).
- `TAB_ORDER` — read the live a11y tree (`qa tree`), don't guess.
- `LAUNCHER_LABELS` — strings distinctive of the Expo dev-launcher AND of the
  dev-client error screen ("there was a problem loading the project",
  "failed to load app").
- `LOG_PROCESS_HINT` — substring of the app's process name for the crash-log
  predicate.
- `/tmp/<project>-tester-*` artifact paths — namespace per project.
- `MODE`/`METRO_ENV` — the app's own mock/dev flag (or empty). Gotcha: Expo's
  dev transform spreads `.env*` files OVER inline env — flag vars must have NO
  `.env*` entry to propagate.

## Empirical gotchas (each cost real debugging time — don't relearn)

1. **idb rejects `"booted"` as a UDID** — pass the real UDID (`simctl` accepts
   the alias; `idb` errors "Cannot spawn companion for booted").
2. **Synthesized taps lose to react-native-gesture-handler** — gorhom
   backdrop-tap/drag-down never fire. Sheets need a labelled escape: an
   in-flow gorhom `TouchableOpacity` (NOT RN Pressable — a11y sees it but
   onPress never fires inside the sheet's gesture context; NOT
   position:absolute — same failure; NOT opacity:0 — iOS drops alpha=0 from
   the a11y tree). Gate it on the tester env var.
3. **Gorhom's container is accessible-by-default** (role 'adjustable') — it
   collapses ALL sheet content out of the a11y tree (VoiceOver, Detox, and the
   tester are all blind). `accessible={false}` on the container un-collapses.
4. **iOS 26 NativeTabs**: items don't appear in `describe-all` (only a 'Tab
   Bar' group), and the group frame is FULL-WIDTH while the visual pill is
   centered/narrower — naive segment math taps empty glass. `core/idb_ui.py`
   probes via `describe-point` (already handled; keep it).
5. **a11y frames are viewport-relative** — `y<0` scrolled past, `y>screen`
   below the fold, tab-bar band occluded. Core's tap guardrail enforces this.
6. **Light-themed apps break pixel-based app detection** — `app_state()` greps
   the a11y tree against `LAUNCHER_LABELS` instead (the earlier pixel heuristic
   only worked because that app is dark).
7. **The Simulator can be headless** — `simctl`/`idb` work with the window
   hidden/unfocused/on another Space.
8. **First boot after adding a JS dep may crash native** — transitive NATIVE
   modules are NOT autolinked (direct package.json deps only). A
   `NativeModule: X is null` red box right after porting is the app's
   dependency gap, not the tester's fault.
9. **Stale ESLint cache after npm install** — import/no-unresolved ghosts for
   freshly installed packages; clear `.expo/cache/eslint`.
10. **`simctl openurl` pops an "Open in <app>?" confirm** when invoked from
    outside the app — core auto-approves it; budget polls for slow dialogs.

## Invariants layer — port the pattern, not the file

1. Find the app's ground truth (local BE REST, SQLite, …). If only a remote
   prod API exists, this layer may not apply.
2. Read the schema/serving code FIRST and classify: **real invariants** =
   denormalized state that can drift (counters incremented in place, soft
   references with no FK, pagination merges); **tautological** = computed on
   read (asserting those is worthless — document them so nobody re-adds them).
3. One registry file (`INVARIANTS.md`) = IDs + rules + evidence; the checker
   implements exactly the registry; fix both together or neither.
4. Make checks **mode-aware** (states unreachable in dev mode must not fail)
   and report **seeded-vs-live coverage** (a sweep over fixtures only exercises
   read paths — warn when the round created nothing).
5. `snapshot`/`diff` delta probes around risky actions (exactly-one-created,
   nothing-ever-disappears, double-submit).

## Not portable from here, fundamentally

- The invariant rules themselves (per-backend), scope keywords, rails, and the
  TAB/launcher label sets.
- The app's a11y-label conventions — the tester is only as good as the app's
  `accessibilityLabel` coverage (an unfindable element is itself a finding).
- If the target app has **timed gameplay** (sub-3s response windows an LLM
  can't keep up with), it would need a dedicated autoplay layer — deliberately
  not built here (lisk has no timed inner loop; live mode covers everything).

## Smoke test for a fresh port

```bash
scripts/sim-qa/qa doctor      # every FAIL prints its fix; resolves + pins the sim
scripts/sim-qa/qa serve       # owns Metro, force-reloads the app from it
scripts/sim-qa/qa health      # exit 0 = metro + (backend) + app + idb all green
scripts/sim-qa/qa tree        # labelled elements visible?
scripts/sim-qa/qa init --scope all --label porting-smoke
scripts/sim-qa/qa shot home && scripts/sim-qa/qa tap --tab <first-tab>
scripts/sim-qa/qa stop
```

All green → core is wired; everything after is per-app work (scopes, rails,
escape hatch, invariants). Expect the smoke test itself to surface real app
bugs — both prior ports did (lisk's found three shipping issues on day one).
