# target.example.py — copy into YOUR project as scripts/qa/target.py and adapt.
# This is a real working pin (lisk-web's), kept as the living example.
# Per-app values: TESTER_PORT (never your dev port), MODE/MODE_ENV (your app's
# mock/msw envs), SERVER_LOG/PIDFILE (namespace per project!).
# Dev-server launch (engine defaults: `bun run dev` at the repo root):
#   SERVER_CMD = ["npm", "run", "dev"]      # any argv; PORT env is set for you
#   SERVER_CWD = "apps/web"                 # monorepo subdir, default repo root
# Optional ground truth: BACKEND_URL (omit/None = no backend) + BACKEND_HINT.
# Headless note: `qa shot` is always headless; the agent's live eyes are the
# Playwright MCP — toggle ITS headless mode in the project's .mcp.json args.
"""Target config for the web QA tester — lisk-web's pin.

The tester owns its OWN Next dev server on a pinned port, so your dev server
(:3000), admin (:3001), and Storybook (:6006) are never touched. The agent's
eyes and hands are the Playwright MCP (browser_* tools); these scripts only
manage the tester's server, the run bookkeeping, and the backend invariants.

Ported from lisk-app-mobile/scripts/sim-qa (see its PORTING_NOTES.md) — the
process layer is shared; the simulator-specific eyes/hands were replaced by
the Playwright MCP.
"""

import os
import sys

TESTER_PORT = 3002  # web dev = 3000, admin = 3001, storybook = 6006
APP_URL = f"http://localhost:{TESTER_PORT}"
BACKEND_URL = "http://localhost:8080"

# Tester mode — which world the tester's Next server runs in:
#   local (default): local backend + MSW off + mock auth — mirrors the repo's
#                    `bun dev:local-backend`. Requires lisk-backend running
#                    (`cd ../lisk-backend && make run`). Full write freedom;
#                    backend invariants (qa check) apply.
#   msw:             MSW full mode — pure-frontend determinism, no backend at
#                    all. Invariants do NOT apply (there is no BE to query).
#   staging:         real auth against staging. The tester cannot log in
#                    itself; a human signs in once in the tester's browser
#                    profile. Rails are read-mostly.
MODE = os.environ.get("LISK_QA_MODE", "local")
if MODE not in ("local", "msw", "staging"):
    sys.exit(f"web-qa: invalid LISK_QA_MODE={MODE!r} — expected local | msw | staging")

MODE_ENV = {
    "local": {
        "NEXT_PUBLIC_API_URL": f"{BACKEND_URL}/api/v1",
        "NEXT_PUBLIC_MSW_MODE": "none",
        "NEXT_PUBLIC_MOCK_AUTH": "true",
    },
    "msw": {"NEXT_PUBLIC_MSW_MODE": "full"},
    "staging": {},
}[MODE]

SERVER_LOG = "/tmp/lisk-web-tester-next.log"
PIDFILE = "/tmp/lisk-web-tester-next.pid"


if __name__ == "__main__":
    fields = {"--port": str(TESTER_PORT), "--url": APP_URL, "--mode": MODE}
    key = sys.argv[1] if len(sys.argv) > 1 else "--url"
    if key not in fields:
        sys.exit(f"target.py: unknown field {key!r}; pick from {list(fields)}")
    print(fields[key])
