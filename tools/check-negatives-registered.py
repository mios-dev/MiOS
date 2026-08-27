#!/usr/bin/env python3
# AI-hint: Fails when a negative test is defined in the harness but never invoked by it.
# AI-related: tests/drift-gate-negatives.sh, automation/98-drift-checks.sh
import os
import re
import sys

HARNESS = "tests/drift-gate-negatives.sh"

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    try:
        s = open(os.path.join(root, HARNESS), encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print("%s unreadable: %s" % (HARNESS, exc))
        return 1
    defined = set(re.findall(r"^(test_[a-z0-9_]+)\(\)", s, re.M))
    invoked = set(re.findall(r"^\s*_run_test\s+(test_[a-z0-9_]+)\s*$", s, re.M))
    invoked |= set(re.findall(r"^\s*(test_[a-z0-9_]+)\s*$", s, re.M))
    orphans = sorted(defined - invoked)
    if orphans:
        print("negative test(s) defined but never invoked -- coverage that is not:")
        for o in orphans[:15]:
            print("  " + o)
        if len(orphans) > 15:
            print("  ... and %d more" % (len(orphans) - 15))
        return 1
    print("[check-negatives-registered] %d negative test(s), all invoked"
          % len(defined), file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
