#!/usr/bin/env python3
# AI-hint: Fails on an orphaned negative test, and ratchets the drift checks that have no negative test at all.
# AI-related: tests/drift-gate-negatives.sh, automation/98-drift-checks.sh
import os
import re
import sys
import tomllib

HARNESS = "tests/drift-gate-negatives.sh"
GATE = "automation/98-drift-checks.sh"
TOML = "usr/share/mios/mios.toml"

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    try:
        s = open(os.path.join(root, HARNESS), encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print("%s unreadable: %s" % (HARNESS, exc))
        return 1
    s_harness = s
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
    # The index has always described this gate as "every drift check has a
    # corresponding negative test registered". It only ever detected orphans,
    # so that half went unenforced. Ratchet it: shrink-only, seeded at the
    # measured gap.
    try:
        with open(os.path.join(root, GATE), encoding="utf-8", errors="replace") as fh:
            gate = fh.read()
        with open(os.path.join(root, TOML), "rb") as fh:
            ceiling = tomllib.load(fh)["tests"]["max_checks_without_negative"]
    except (OSError, KeyError) as exc:
        print("cannot read the gate or [tests].max_checks_without_negative: %s" % exc)
        return 1

    body = re.search(r"^main\(\) \{(.*?)^\}", gate, re.S | re.M)
    if not body:
        print("could not locate main() in %s -- the dispatch list is the subject" % GATE)
        return 1
    dispatched = re.findall(r"^\s+(check_[a-z0-9_]+)\s*$", body.group(1), re.M)
    if len(dispatched) < 50:
        print("only %d dispatched checks parsed from main() -- the subject list is wrong"
              % len(dispatched))
        return 1
    uncovered = sorted({c for c in dispatched if c not in s_harness})
    if len(uncovered) > int(ceiling):
        print("drift checks with no negative test: %d > ceiling %d "
              "(write one, then lower [tests].max_checks_without_negative)"
              % (len(uncovered), ceiling))
        for u in uncovered[:15]:
            print("  " + u)
        return 1

    print("[check-negatives-registered] %d negative test(s), all invoked; "
          "%d/%d dispatched check(s) have none"
          % (len(defined), len(uncovered), ceiling), file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
