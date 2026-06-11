#!/usr/bin/env python3
"""Publish a QA image to the `qa-assets` orphan branch; print a PR-ready <img>.

WHY: QA before/after montages must NOT be committed to the feature/PR branch —
on squash-merge that lands them in `main`. Instead they live on a dedicated
ORPHAN branch `qa-assets` (no code history, never merged, append-only) and are
referenced from the PR body by a stable raw URL:

    https://github.com/<owner>/<repo>/blob/qa-assets/<feature>/<file>?raw=true

The branch name has no slash, so the plain branch-name URL is stable and needs
no commit-SHA pinning. This command fetches qa-assets (creating it as an orphan
if absent), appends the image at <feature>/<file> via an ISOLATED temp index
(never touches your working tree, current branch, or HEAD), pushes, and prints
the <img> tag to paste into the PR body.

Portable: `<owner>/<repo>` is derived from the `origin` remote, so the same
command works in any repo with an `origin` remote.

Usage:
  qa publish <image> --feature <slug> [--name <file>] [--caption <text>] [--width N]
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

BRANCH = "qa-assets"

_README = """\
# qa-assets — image host for QA artifacts

Orphan branch that ONLY hosts images referenced from PR descriptions
(automated iOS-sim QA before/after montages, etc.).

- No shared history with `main`; carries no code.
- Never merged, no PR — `main` never sees it.
- Append-only, so `?raw=true` links never rot.
- One folder per feature / PR. Referenced via
  https://github.com/<owner>/<repo>/blob/qa-assets/<path>?raw=true

Managed by the QA tester's `qa publish` command. Do not delete (PR bodies link here).
"""


def git(*args, env=None, check=True):
    r = subprocess.run(["git", *args], text=True, capture_output=True, env=env)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{r.stderr.strip()}")
    return r.stdout.strip()


def owner_repo():
    """Parse 'owner/repo' from the origin remote (https or ssh form)."""
    url = git("remote", "get-url", "origin")
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", url)
    if not m:
        sys.exit(f"cannot parse owner/repo from origin remote: {url!r}")
    return m.group(1)


def remote_commit():
    """Commit SHA of origin/qa-assets after a fetch, or None if the branch is absent."""
    git("fetch", "origin", BRANCH, check=False)  # fine if it doesn't exist yet
    return git("rev-parse", "--verify", "--quiet",
               f"refs/remotes/origin/{BRANCH}", check=False) or None


def hash_blob(path):
    return git("hash-object", "-w", path)


def build_tree(base, env, dest, image):
    """Tree = base tree (if any) + image at <dest> (+ a README when bootstrapping)."""
    if base:
        git("read-tree", base, env=env)
    else:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
        tmp.write(_README)
        tmp.close()
        git("update-index", "--add", "--cacheinfo",
            f"100644,{hash_blob(tmp.name)},README.md", env=env)
        os.unlink(tmp.name)
    git("update-index", "--add", "--cacheinfo",
        f"100644,{hash_blob(image)},{dest}", env=env)
    return git("write-tree", env=env)


def emit_snippet(url, caption, width):
    print("\n--- paste into the PR body ---")
    if caption:
        print(f"**{caption}**")
    print(f'<img src="{url}" width="{width}" alt="{caption or "QA before/after"}" />')


def main():
    ap = argparse.ArgumentParser(
        prog="qa publish",
        description="Host a QA image on the qa-assets orphan branch (keeps it out of main).",
    )
    ap.add_argument("image", help="path to the image (montage/screenshot) to host")
    ap.add_argument("--feature", required=True,
                    help="folder slug on qa-assets, e.g. transfer-account-name-capitalize")
    ap.add_argument("--name", help="filename on qa-assets (default: image basename)")
    ap.add_argument("--caption", default="", help="caption / alt text for the <img>")
    ap.add_argument("--width", type=int, default=580,
                    help="display width in the PR body (default 580 — the standard)")
    a = ap.parse_args()

    if not os.path.isfile(a.image):
        sys.exit(f"image not found: {a.image}")
    os.chdir(git("rev-parse", "--show-toplevel"))

    dest = f"{a.feature.strip('/')}/{a.name or os.path.basename(a.image)}"
    url = f"https://github.com/{owner_repo()}/blob/{BRANCH}/{dest}?raw=true"
    base = remote_commit()

    idx = tempfile.mktemp(suffix=".idx")  # isolated index → never touches the real one
    env = {**os.environ, "GIT_INDEX_FILE": idx}
    tree = build_tree(base, env, dest, a.image)
    if os.path.exists(idx):
        os.unlink(idx)

    if base and tree == git("rev-parse", f"{base}^{{tree}}"):
        print(f"already published (identical content) — {url}")
        emit_snippet(url, a.caption, a.width)
        return

    msg = f"qa-assets: {dest}"
    commit = git("commit-tree", tree, "-p", base, "-m", msg) if base \
        else git("commit-tree", tree, "-m", msg)

    push = subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/{BRANCH}"],
                          text=True, capture_output=True)
    if push.returncode != 0:
        sys.exit("push to qa-assets failed (someone else may have published — "
                 f"re-run to retry):\n{push.stderr.strip()}")
    git("update-ref", f"refs/heads/{BRANCH}", commit)  # keep local branch in sync

    print(f"published -> {url}")
    emit_snippet(url, a.caption, a.width)


if __name__ == "__main__":
    main()
