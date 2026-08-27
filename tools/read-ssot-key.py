#!/usr/bin/env python3
# AI-hint: Prints one dotted SSOT key, exiting non-zero when it is absent so a shell caller cannot silently default it.
# AI-related: usr/share/mios/mios.toml, automation/98-drift-checks.sh
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

def main(argv) -> int:
    if not argv:
        print("usage: read-ssot-key.py <dotted.key>", file=sys.stderr)
        return 2
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or os.getcwd()
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        node = tomllib.load(fh)
    for part in argv[0].split("."):
        if not isinstance(node, dict) or part not in node:
            print("SSOT key absent: %s" % argv[0], file=sys.stderr)
            return 9
        node = node[part]
    if isinstance(node, (dict, list)):
        print("SSOT key %s is a %s, not a scalar" % (argv[0], type(node).__name__),
              file=sys.stderr)
        return 9
    print(node)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
