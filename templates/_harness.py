"""Locate the shared qa-harness and expose its helper lib (targetkit).

Installed per project next to target.py — copy from qa-harness/templates/,
never edit. Resolution mirrors the qa shim: $QA_HARNESS_DIR -> ~/.qa-harness
(one-line path file) -> ~/programming/projects/qa-harness.
"""
import os
import sys


def root():
    env = os.environ.get("QA_HARNESS_DIR")
    if env:
        return env
    pin = os.path.expanduser("~/.qa-harness")
    if os.path.exists(pin):
        v = open(pin).read().strip()
        if v:
            return v
    return os.path.expanduser("~/programming/projects/qa-harness")


def _checked_root():
    r = root()
    if not os.path.isdir(os.path.join(r, "common")):
        sys.exit(
            f"qa: harness not found at '{r}'. Fix one of:\n"
            f"  git clone https://github.com/oskarleonard/qa-harness \"$HOME/programming/projects/qa-harness\"\n"
            f"  echo /path/to/qa-harness > ~/.qa-harness\n"
            f"  export QA_HARNESS_DIR=/path/to/qa-harness"
        )
    return r


def core_dir():
    """Mobile engine core — for project scripts that import common/idb_ui."""
    return os.path.join(_checked_root(), "mobile", "core")


sys.path.insert(0, os.path.join(_checked_root(), "common"))
import targetkit  # noqa: E402,F401  (usage: `from _harness import targetkit`)
