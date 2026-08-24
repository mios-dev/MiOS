#!/usr/bin/env python3
# AI-hint: Fails when a Rust crate ships with no test at all, because cargo test reports ok for a crate that asserts nothing.
# AI-related: src/mios-rs, tools/native, usr/share/mios/mios.toml
"""A crate with no tests passes `cargo test` every time.

The workspace run prints `test result: ok. 0 passed` for each such crate, which
reads exactly like a crate whose tests all passed. Ten crates and roughly 5,600
lines are in that state, miosd alone being 3,550 of them, so the suite's green
says far less than it appears to.

The ceiling is shrink-only: a crate may be registered as untested with a reason,
and the count may only fall.
"""
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

WORKSPACES = ("src/mios-rs", "tools/native")
TEST_MARKERS = ("#[test]", "#[tokio::test]", "#[rstest]")


def crate_tests(root: str, ws: str, crate: str) -> int:
    n = 0
    for sub in ("src", "tests", "benches"):
        base = os.path.join(root, ws, crate, sub)
        for dirpath, _dirs, files in os.walk(base):
            for f in files:
                if not f.endswith(".rs"):
                    continue
                try:
                    body = open(os.path.join(dirpath, f), encoding="utf-8",
                                errors="replace").read()
                except OSError:
                    continue
                n += sum(body.count(m) for m in TEST_MARKERS)
    return n


def crate_lines(root: str, ws: str, crate: str) -> int:
    n = 0
    base = os.path.join(root, ws, crate, "src")
    for dirpath, _dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".rs"):
                try:
                    with open(os.path.join(dirpath, f), encoding="utf-8",
                              errors="replace") as fh:
                        n += sum(1 for _ in fh)
                except OSError:
                    pass
    return n


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or os.getcwd()
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        rust = (tomllib.load(fh).get("rust") or {})

    registered = rust.get("untested_crates") or {}
    ceiling = rust.get("max_untested_crates")
    viol, untested, seen = [], [], 0

    for ws in WORKSPACES:
        wsdir = os.path.join(root, ws)
        if not os.path.isdir(wsdir):
            viol.append("workspace %s is missing -- the gate has nothing to inspect" % ws)
            continue
        for crate in sorted(os.listdir(wsdir)):
            if not os.path.isfile(os.path.join(wsdir, crate, "Cargo.toml")):
                continue
            seen += 1
            if crate_tests(root, ws, crate) == 0:
                untested.append("%s/%s" % (ws, crate))

    if not seen:
        print("no crate was inspected -- an empty scan reports the same green as a"
              " clean one")
        return 1

    for name in untested:
        if name not in registered:
            viol.append("%s ships %d source line(s) and not one test; cargo test"
                        " reports ok for it regardless"
                        % (name, crate_lines(root, *name.split("/", 1))))
        elif not str(registered[name]).strip():
            viol.append("%s is registered as untested with no reason" % name)

    for name in sorted(registered):
        if name not in untested:
            viol.append("%s is registered as untested but now has tests -- remove"
                        " the entry and lower the ceiling" % name)

    if ceiling is None:
        viol.append("[rust] has no max_untested_crates -- an absent ceiling is a"
                    " broken ratchet, not an open one")
    elif len(untested) > int(ceiling):
        viol.append("untested crates %d > ceiling %d" % (len(untested), ceiling))

    print("\n".join(viol))
    if viol:
        return 1
    print("[check-rust-test-coverage] %d crate(s); %d untested and registered"
          " (ceiling %s)" % (seen, len(untested), ceiling), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
