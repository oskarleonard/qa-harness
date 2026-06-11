"""Target config for the web QA tester — the project's pin.

Copy into YOUR project as scripts/qa/target.py (with templates/_harness.py
next to it) and edit the CONFIG section — every line in it is a knob. This is
a real working pin (lisk-web's), kept as the living example; PORTING.md
"Per-app values" explains how to derive each value.
"""
from _harness import targetkit

# ───────────── CONFIG — everything in this section is yours to edit ─────────────

TESTER_PORT = 3002  # never your dev port (web dev = 3000, admin = 3001, storybook = 6006)
APP_URL = f"http://localhost:{TESTER_PORT}"

# Ground truth (omit or None = no backend; health skips the ping).
BACKEND_URL = "http://localhost:8080"
BACKEND_HINT = "cd ../lisk-backend && make run  (Docker deps up first)"

# Tester mode + the env the tester's dev server runs with, per mode.
MODE = targetkit.mode_from_env("LISK_QA_MODE", default="local", allowed=("local", "msw", "staging"))
MODE_ENV = {
    "local": {
        "NEXT_PUBLIC_API_URL": f"{BACKEND_URL}/api/v1",
        "NEXT_PUBLIC_MSW_MODE": "none",
        "NEXT_PUBLIC_MOCK_AUTH": "true",
    },
    "msw": {"NEXT_PUBLIC_MSW_MODE": "full"},
    "staging": {},
}[MODE]

# Dev-server launch: argv + repo subdir. The engine sets PORT in the env (Next
# honors it); if your dev script pins `-p`, launch the binary directly with
# your tester port instead (and add e.g. NEXT_DIST_DIR to MODE_ENV — see
# PORTING.md "Next 16" gotcha).
SERVER_CMD = ["bun", "run", "dev"]
SERVER_CWD = "apps/web"  # monorepo subdir; "" = repo root

# Process-hygiene artifacts — namespace per project!
SERVER_LOG = "/tmp/lisk-web-tester-next.log"
PIDFILE = "/tmp/lisk-web-tester-next.pid"

# ───────────────────── machinery — don't edit below this line ─────────────────────

if __name__ == "__main__":
    targetkit.cli(globals())
