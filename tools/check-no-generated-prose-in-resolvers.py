#!/usr/bin/env python3
# AI-hint: Drift check 157 check_no_generated_prose_in_resolvers -- asserts zero AI-hint: and zero MIOS_UNITS_*_COMMENT= in globals.sh/ps1.
# AI-doc: usr/share/doc/mios/manual/tools.md

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# Honour the root the caller names, as every sibling checker does. Hardcoding it
# to this file's location made the tool impossible to aim at a fixture or at the
# bootstrap repo, so it could only ever be exercised against the live tree.
ROOT = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT")     or os.path.abspath(os.path.join(_HERE, ".."))

TARGETS = [
    os.path.join(ROOT, "automation", "lib", "globals.sh"),
    os.path.join(ROOT, "automation", "lib", "globals.ps1"),
]

COMMENT_RE = re.compile(r"MIOS_UNITS_[A-Z0-9_]*_COMMENT=")


def main() -> int:
    violations = []
    for path in TARGETS:
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/").replace("\\", "/")
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line_no, line in enumerate(fh, 1):
                if "AI-hint:" in line:
                    violations.append(f"{rel}:{line_no} contains prose header 'AI-hint:'")
                if COMMENT_RE.search(line):
                    violations.append(f"{rel}:{line_no} contains unit comment assignment 'MIOS_UNITS_*_COMMENT='")

    if violations:
        for v in violations:
            print(f"check_no_generated_prose_in_resolvers: {v}", file=sys.stderr)
        return 1

    print("check_no_generated_prose_in_resolvers OK: zero AI-hint prose or unit comment values in resolvers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
