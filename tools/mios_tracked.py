#!/usr/bin/env python3
# AI-hint: Lists tracked files for a gate, raising when git could not answer -- an empty listing is never reported as a clean corpus.
# AI-related: tools/check-leaked-fixtures.py, tools/check-header-comment-syntax.py, tools/check-temp-fixture-cleanup.py, tools/sync-bootstrap.py
# AI-functions: tracked
"""One way to ask git what is tracked, so a refusal cannot read as "nothing".

Several checks built their corpus with

    subprocess.run(["git", "-C", root, "ls-files"],
                   capture_output=True, text=True, check=False).stdout

and then iterated it. `check=False` with only `.stdout` consumed means a git
that REFUSED -- "fatal: detected dubious ownership in repository", exit 128,
message on stderr, stdout empty -- yields an empty list. The loop body never
runs, no violation is appended, and the check prints its success line having
examined nothing. That is indistinguishable from a clean tree.

`tracked()` raises instead, on a non-zero exit AND on an empty listing, which
no real MiOS checkout produces.
"""
from __future__ import annotations

import os
import subprocess


class GitUnavailable(RuntimeError):
    """git could not enumerate the tree, so no scan of it means anything."""


def tracked(root: str, *pathspec: str) -> list:
    """Tracked paths under root, slash-separated. Raises GitUnavailable."""
    cmd = ["git", "-C", root, "ls-files", *pathspec]
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise GitUnavailable(
            "git ls-files failed in %s (exit %d): %s"
            % (root, p.returncode, (p.stderr or "").strip() or "no message"))
    paths = [l.strip().replace(os.sep, "/") for l in p.stdout.splitlines() if l.strip()]
    if not paths:
        raise GitUnavailable(
            "git ls-files listed no tracked file in %s%s, so nothing would be "
            "scanned and the result would be clean for the wrong reason"
            % (root, (" for " + " ".join(pathspec)) if pathspec else ""))
    return paths
