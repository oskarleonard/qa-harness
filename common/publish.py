#!/usr/bin/env python3
"""Publish a QA image to the hidden qa-assets store; print a PR-ready <img>.

WHY: QA before/after montages must NOT be committed to the feature/PR branch —
on squash-merge that lands them in `main`. They also shouldn't live on a
regular branch: GitHub shows a "had recent pushes — Compare & pull request"
banner for any freshly-pushed branch, every single run. So images live on a
**custom ref** outside the branch namespace:

    refs/qa-assets/store

No branch → no banner, no branch-list entry, nothing to merge or PR. The ref's
history is append-only and shares no ancestry with `main`. PR bodies reference
images by COMMIT-PINNED raw URL, which never rots:

    https://github.com/<owner>/<repo>/blob/<commit-sha>/<path>?raw=true

Migration: repos that previously used the `qa-assets` BRANCH get seamless
continuity — the first publish seeds the store ref from the legacy branch tip,
so the old branch can stay frozen (its embedded URLs keep working) while all
new publishes go to the hidden ref.

Everything happens via an ISOLATED temp index (never touches your working
tree, current branch, or HEAD). Idempotent: re-publishing identical content
reuses the existing commit. `<owner>/<repo>` derives from `origin`, so the
same command works in any repo.

Usage:
  qa publish <image> --feature <slug> [--name <file>] [--caption <text>] [--width N]
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

REF = "refs/qa-assets/store"
LEGACY_BRANCH = "qa-assets"  # frozen after migration; never pushed again

_README = """\
# qa-assets — image store for QA artifacts

Machine-managed, append-only store of images referenced from PR descriptions
(automated QA before/after montages, etc.).

- Lives on the hidden ref `refs/qa-assets/store` — NOT a branch: no UI
  banners, no branch-list entry, nothing to merge or PR.
- Shares no history with `main`; never reachable from any branch.
- PR bodies link images by commit-pinned raw URL, so links never rot.

Managed by the QA tester's `qa publish` command. Do not delete the ref
(PR bodies link into its history).
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


def remote_base():
    """Tip of the remote store ref after a fetch; on first use, seed from the
    legacy qa-assets BRANCH tip (continuous history → old branch-URL images
    stay reachable). None when neither exists (fresh bootstrap)."""
    git("fetch", "origin", f"+{REF}:{REF}", check=False)  # fine if absent
    tip = git("rev-parse", "--verify", "--quiet", REF, check=False)
    if tip:
        return tip
    git("fetch", "origin", LEGACY_BRANCH, check=False)
    return git("rev-parse", "--verify", "--quiet",
               f"refs/remotes/origin/{LEGACY_BRANCH}", check=False) or None


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
        description="Host a QA image on the hidden qa-assets store ref (keeps it out of main, branches, and banners).",
    )
    ap.add_argument("image", help="path to the image (montage/screenshot) to host")
    ap.add_argument("--feature", required=True,
                    help="folder slug in the store, e.g. transfer-account-name-capitalize")
    ap.add_argument("--name", help="filename in the store (default: image basename)")
    ap.add_argument("--caption", default="", help="caption / alt text for the <img>")
    ap.add_argument("--width", type=int, default=580,
                    help="display width in the PR body (default 580 — the standard)")
    a = ap.parse_args()

    if not os.path.isfile(a.image):
        sys.exit(f"image not found: {a.image}")
    os.chdir(git("rev-parse", "--show-toplevel"))

    dest = f"{a.feature.strip('/')}/{a.name or os.path.basename(a.image)}"
    base = remote_base()

    idx = tempfile.mktemp(suffix=".idx")  # isolated index → never touches the real one
    env = {**os.environ, "GIT_INDEX_FILE": idx}
    tree = build_tree(base, env, dest, a.image)
    if os.path.exists(idx):
        os.unlink(idx)

    if base and tree == git("rev-parse", f"{base}^{{tree}}"):
        commit = base
        print(f"already published (identical content) — commit {commit[:9]}")
    else:
        msg = f"qa-assets: {dest}"
        commit = git("commit-tree", tree, "-p", base, "-m", msg) if base \
            else git("commit-tree", tree, "-m", msg)
        push = subprocess.run(["git", "push", "origin", f"{commit}:{REF}"],
                              text=True, capture_output=True)
        if push.returncode != 0:
            sys.exit("push to the qa-assets store failed (someone else may have "
                     f"published — re-run to retry):\n{push.stderr.strip()}")
        git("update-ref", REF, commit)  # keep the local store ref in sync
        print(f"published -> commit {commit[:9]} on {REF}")

    url = f"https://github.com/{owner_repo()}/blob/{commit}/{dest}?raw=true"
    emit_snippet(url, a.caption, a.width)


if __name__ == "__main__":
    main()
