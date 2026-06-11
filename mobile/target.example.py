"""Target config for the auto-QA tester (MOBILE) — the project's pin.

Copy into YOUR project as scripts/sim-qa/target.py (with templates/_harness.py
next to it) and edit the CONFIG section — every line in it is a knob; the
machinery (per-machine sim resolution, the --field CLI) comes from the
harness. This is a real working pin (lisk-mobile's), kept as the living
example; PORTING.md "Per-app values" explains how to derive each value.
"""
import os

from _harness import targetkit

# ───────────── CONFIG — everything in this section is yours to edit ─────────────

DEVICE_NAME = "iPhone 17 Pro"  # a sim model NO other project's tester uses on this machine
PORT = 8092  # tester Metro port — distinct from dev Metro (8081) + every other tester
BUNDLE = "com.lisk.app.development"  # dev-flavor bundle id (app.config.ts)
SCHEME = "liskmobile"  # app.config.ts `scheme` — dev-client deep links
UDID_ENV = "LISK_QA_UDID"  # env override for the per-machine sim pin (target.local)

# Tester mode + the env vars the tester's Metro bundles with (your app's mock flags).
MODE = targetkit.mode_from_env("LISK_QA_MODE", default="mock", allowed=("mock", "staging"))
METRO_ENV = {
    "EXPO_PUBLIC_AI_TESTER": "true",
    **({"EXPO_PUBLIC_MOCK_AUTH": "true"} if MODE == "mock" else {}),
}

# Ground truth (omit or None = no backend; health/doctor skip the ping).
BACKEND_URL = "http://localhost:8080"
BACKEND_HINT = "cd ../lisk-backend && make run  (Docker deps up first)"

# idb CLI location (machine setup: see the engine README).
IDB = os.path.expanduser("~/.idb-venv/bin/idb")

# Bottom-tab order (left->right) — read the live a11y tree (`qa tree`), don't guess.
TAB_ORDER = ["home", "notifications"]

# app_state() launcher detection — generic Expo dev-client labels usually suffice.
LAUNCHER_LABELS = [
    "development servers",
    "enter url manually",
    "there was a problem loading the project",
    "failed to load app",
]

# OS crash-log stream predicate (substring of the app's process image path).
LOG_PROCESS_HINT = "lisk"

# Process-hygiene artifacts — namespace per project!
METRO_LOG = "/tmp/lisk-tester-metro.log"
PIDFILE = "/tmp/lisk-tester-metro.pid"
CRASHLOG = "/tmp/lisk-tester-crash.log"
CRASHLOG_PID = "/tmp/lisk-tester-crash.pid"

WINDOW = f'window "{DEVICE_NAME}"'  # legacy osascript reference only

# ───────────────────── machinery — don't edit below this line ─────────────────────

UDID = targetkit.resolve_udid(DEVICE_NAME, env_var=UDID_ENV, near=__file__)

if __name__ == "__main__":
    targetkit.cli(globals())
