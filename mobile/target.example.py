"""Target config for the auto-QA tester — lisk-app-mobile's pin.

The tester is PINNED to exactly one simulator + Metro port, so any other
project's tester on this machine (a different sim / port) can run at the same
time without collision. It never kills Metro on a different port or drives a
different sim.

The UDID is per-machine, so it is NOT hardcoded here. Resolution order:
  1. LISK_QA_UDID env var (explicit override)
  2. scripts/sim-qa/target.local — the per-machine pin (gitignored, one line)
  3. auto-discover a simulator named DEVICE_NAME (prefer booted, then newest
     iOS runtime) and WRITE the pin, so the choice sticks forever after.
The persisted pin is what keeps this as stable as a hardcoded UDID — discovery
runs at most once per machine. `qa doctor` shows what resolved and why.
"""

import json
import os
import re
import subprocess
import sys

DEVICE_NAME = "iPhone 17 Pro"  # a distinct sim so any other tester here coexists
PORT = 8092  # lisk dev Metro = 8081; a distinct port so any other tester on this machine can coexist
BUNDLE = "com.lisk.app.development"  # ENVIRONMENT=development build
SCHEME = "liskmobile"  # app.config.ts `scheme` — used for dev-client deep links
WINDOW = f'window "{DEVICE_NAME}"'  # legacy osascript reference only (unused)

_LOCAL_PIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "target.local")


def _runtime_version(runtime_key):
    m = re.search(r"iOS-(\d+)-(\d+)", runtime_key)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _discover_udid():
    """Best available sim named DEVICE_NAME: booted first, then newest iOS."""
    try:
        out = subprocess.run(
            ["xcrun", "simctl", "list", "-j", "devices", "available"],
            capture_output=True, text=True, timeout=15,
        )
        runtimes = json.loads(out.stdout)["devices"]
    except Exception:
        return None
    candidates = [
        (d.get("state") == "Booted", _runtime_version(runtime), d["udid"])
        for runtime, devices in runtimes.items()
        for d in devices
        if d.get("name") == DEVICE_NAME
    ]
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def _resolve_udid():
    env = os.environ.get("LISK_QA_UDID")
    if env:
        return env
    try:
        pin = open(_LOCAL_PIN).read().strip()
        if pin:
            return pin
    except OSError:
        pass
    udid = _discover_udid()
    if not udid:
        sys.exit(
            f"sim-qa: no simulator named {DEVICE_NAME!r} found.\n"
            f"Create one (Xcode > Devices & Simulators), or pin one explicitly:\n"
            f"  echo <UDID> > {_LOCAL_PIN}   (or export LISK_QA_UDID=<UDID>)\n"
            f"Run `scripts/sim-qa/qa doctor` to check the full setup."
        )
    try:
        open(_LOCAL_PIN, "w").write(udid + "\n")
    except OSError:
        pass  # read-only checkout — resolution still works, just re-runs next time
    return udid


UDID = _resolve_udid()

# Tester mode — 'mock' (V1 default) or 'staging' (structured, not yet operational):
#   mock:    Metro is spawned with EXPO_PUBLIC_MOCK_AUTH=true -> Clerk/Privy are
#            aliased to stubs (metro.config.js), the biometric gate is skipped,
#            and the axios client targets http://localhost:8080. The local
#            lisk-backend MUST be running: `cd ../lisk-backend && make run`.
#   staging: no env override -> the app talks to api-staging with REAL Clerk
#            auth. Requires a human to have logged in once on this sim (the
#            session persists via expo-secure-store); rails become read-mostly.
#            See RUNBOOK.md "Tester modes".
MODE = os.environ.get("LISK_QA_MODE", "mock")
if MODE not in ("mock", "staging"):
    # A typo must not silently select non-mock behavior against the wrong backend.
    sys.exit(f"sim-qa: invalid LISK_QA_MODE={MODE!r} — expected 'mock' or 'staging'")
# EXPO_PUBLIC_AI_TESTER marks the bundle as tester-driven in BOTH modes — it
# gates tester-only affordances in app code (the BottomSheet escape hatch) so
# regular dev / Detox / EAS bundles are unaffected.
METRO_ENV = {
    "EXPO_PUBLIC_AI_TESTER": "true",
    **({"EXPO_PUBLIC_MOCK_AUTH": "true"} if MODE == "mock" else {}),
}

# idb — accessibility-tree element finding/tapping (preferred over pixel taps).
# One-time machine setup: `brew install idb-companion` +
# `python3 -m venv ~/.idb-venv && ~/.idb-venv/bin/pip install fb-idb`.
IDB = os.path.expanduser("~/.idb-venv/bin/idb")

# Bottom-tab order (left->right). iOS 26 NativeTabs collapse their items into a
# single 'Tab Bar' a11y group, so idb_ui taps the n-th segment by this index.
# (A 'cards' tab exists behind TODO(cards) — add it here when unhidden.)
TAB_ORDER = ["home", "notifications"]

# app_state() detection (core/devserver.py): lisk is light-themed, so the
# dark-pixel heuristic from an earlier version of this tester can't tell the app
# from the Expo dev-launcher. We grep the a11y tree for launcher-distinctive labels.
# The last two match the dev-client ERROR screen (e.g. after it tried a dead
# Metro URL) — also a "needs deep link" state.
LAUNCHER_LABELS = [
    "development servers",
    "enter url manually",
    "there was a problem loading the project",
    "failed to load app",
]

# OS crash-log stream predicate hint (core/crashlog.py): matches the app's
# process image path case-insensitively.
LOG_PROCESS_HINT = "lisk"

# Process-hygiene artifacts (so nothing lingers unnoticed):
METRO_LOG = "/tmp/lisk-tester-metro.log"  # owned-Metro stdout/stderr
PIDFILE = "/tmp/lisk-tester-metro.pid"  # owned-Metro pid
CRASHLOG = "/tmp/lisk-tester-crash.log"  # `simctl log stream` capture
CRASHLOG_PID = "/tmp/lisk-tester-crash.pid"  # the log-stream pid


# Single source of truth: scripts can read pinned values from here, e.g.
# `python3 scripts/sim-qa/target.py --udid`.
if __name__ == "__main__":
    import sys

    fields = {
        "--udid": UDID,
        "--port": str(PORT),
        "--window": WINDOW,
        "--bundle": BUNDLE,
        "--mode": MODE,
    }
    key = sys.argv[1] if len(sys.argv) > 1 else "--udid"
    if key not in fields:
        sys.exit(f"target.py: unknown field {key!r}; pick from {list(fields)}")
    print(fields[key])
