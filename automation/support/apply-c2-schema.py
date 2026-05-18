#!/usr/bin/env python3
"""Helper: apply schema-init.surql via direct curl POST and pretty-
print the per-statement results. Used during Phase C.2 testing on
the dev VM; mios-db schema-apply was spawning an interactive SQL
shell instead of streaming the file body."""
import json
import sys


def main() -> int:
    data = json.load(sys.stdin)
    ok = sum(1 for r in data if r.get("status") == "OK")
    total = len(data)
    print(f"applied: {ok}/{total} OK")
    for i, r in enumerate(data):
        if r.get("status") != "OK":
            result = str(r.get("result"))[:160]
            print(f"  [{i}] {r.get('status')}: {result}")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
