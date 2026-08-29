#!/usr/bin/env python3
# AI-hint: Drift gate for Law 12 BAKE-NOT-FETCH -- firstboot scripts must degrade open on egress failure.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: no firstboot script aborts on an egress failure.

The predicate this replaces asked whether the FILE contained "|| true" (or
set +e / trap / exit 0) anywhere. That is file-global: one unrelated cleanup
guard certified the whole script, so every one of the thirteen scripts under
usr/libexec/mios passed and the gate could not fail. It also missed a real
violation -- forge-firstboot.sh fetched a Forgejo runner token into an
assignment under `set -euo pipefail` with no guard, so an admin API that was
not up yet aborted firstboot.

What is checked instead: each EGRESS call reached while errexit is active must
have a fallback. Approximations, stated rather than hidden:

  * Only a column-0 `set +e` changes the file-level errexit state. An indented
    one is inside a function or subshell and does not exempt later top-level
    lines (mios-hermes-firstboot has exactly that).
  * `trap ... EXIT` is not an escape. It runs a handler on exit; it does not
    stop errexit aborting an unguarded fetch.
  * Physical lines are joined into logical ones, because the guard usually
    lands after a backslash continuation or a closing paren. Paren depth is
    clamped at zero so `case` patterns, which carry an unmatched ")", cannot
    desynchronise the join.
  * A fetch named inside a log/echo/printf string is documentation, not a call.
  * `&& return` / `|| exit` count as guards: the author expressed the control
    flow, and errexit does not fire on the left operand of a && list.

Interprocedural analysis is out of scope: a helper whose body ends in
`return 1` and that is only ever called from an `if` is safe, and is credited
here only because its egress lines carry explicit control flow.
"""

import glob
import os
import re
import sys

EGRESS = re.compile(
    r"\b(curl|wget|podman\s+pull|skopeo\s+copy|dnf\s+(install|upgrade)|"
    r"git\s+clone|bootc\s+(switch|upgrade)|pip\s+install|hf\s+download|"
    r"huggingface-cli\s+download|rpm-ostree|flatpak\s+install)\b")
GUARD = re.compile(
    r"\|\||^\s*(if|while|until|elif)\s|&&\s*(true|:|return|exit)|\|\|\s*(return|exit)")
SETE = re.compile(r"^set\s+-[a-zA-Z]*e|^set\s+-o\s+errexit")
SETPE = re.compile(r"^set\s+\+[a-zA-Z]*e|^set\s+\+o\s+errexit")
NARRATION = re.compile(r"^\s*(_?log\w*|echo|printf|cat|#)\b")

SCAN_GLOBS = ("usr/libexec/mios/*firstboot*", "automation/firstboot/*.sh")
SKIP_SUFFIXES = (".pyc", ".bak", ".keep", ".orig", ".rej")


def logical_lines(lines):
    """Join continuations and parenthesised runs into one logical line each."""
    out, buf, start, depth = [], "", None, 0
    for num, line in enumerate(lines, 1):
        if start is None:
            start = num
        stripped = line.rstrip()
        buf += stripped[:-1] if stripped.endswith("\\") else line
        depth = max(0, depth + line.count("(") - line.count(")"))
        if stripped.endswith("\\") or depth > 0:
            buf += " "
            continue
        out.append((start, buf))
        buf, start = "", None
    if buf:
        out.append((start or len(lines), buf))
    return out


def scan(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().split("\n")
    except OSError as exc:
        return [(0, "unreadable: %s" % exc)]
    errexit, bad = False, []
    for num, line in logical_lines(lines):
        if line.lstrip().startswith("#") or NARRATION.search(line):
            continue
        if SETE.search(line):
            errexit = True
        if SETPE.search(line):
            errexit = False
        if errexit and EGRESS.search(line) and not GUARD.search(line):
            bad.append((num, " ".join(line.split())[:100]))
    return bad


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    files = []
    for pattern in SCAN_GLOBS:
        files.extend(glob.glob(os.path.join(root, pattern)))
    files = sorted(f for f in files
                   if os.path.isfile(f) and not f.endswith(SKIP_SUFFIXES))

    if not files:
        # An empty scan set is never a pass: the globs are the gate's subject.
        print("no firstboot scripts matched %s -- the gate has no subject"
              % ", ".join(SCAN_GLOBS))
        return 1

    findings = []
    for path in files:
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        for num, text in scan(path):
            findings.append(
                "%s:%d does not degrade open (Law 12): egress call runs under "
                "active set -e with no fallback -- %s" % (rel, num, text))

    if findings:
        for line in findings:
            print(line)
        return 1

    print("%d firstboot script(s) scanned; every egress call degrades open"
          % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
