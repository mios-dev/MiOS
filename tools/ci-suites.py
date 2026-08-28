#!/usr/bin/env python3
# AI-hint: Resolves the [ci] suite registry for the runners and fails when a tracked suite is neither registered in a tier nor exempted.
# AI-related: usr/share/mios/mios.toml, tests/run-suites.sh, automation/98-drift-checks.sh
import fnmatch
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# Scanned for coverage. Anything a runner could reasonably be expected to
# execute, so a dead suite has to be declared dead rather than merely ignored.
#
# The two fitness-function stages are named because leaving them out was not a
# gap, it was a hole: deleting "automation/98-drift-checks.sh" from
# [ci.tiers].gate raised no violation here, the gate tier stayed non-empty so
# run-suites.sh's zero-suite guard never fired either, and the entire drift gate
# stopped running while both reported green.
TRACKED = ("tests/test-*.sh", "tests/test-*.py", "tests/*.sh", "tests/**/*.sh",
           "automation/lint-*.sh", "automation/97-*.sh", "automation/98-*.sh")
# Known still outside TRACKED, so still able to fall out of CI unnoticed:
# automation/test_*.sh, automation/tests/*.sh, automation/lib/test_*.sh,
# usr/lib/mios/**, usr/libexec/mios/test_*.py and usr/share/mios/tests/*.sh --
# 19 tracked suites at last count. Widening to them is a registry change, not a
# reader change: each has to land in a tier or in [ci.exempt] first.

def _root() -> str:
    return os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or os.getcwd()

def _load(root: str) -> dict:
    with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
        return tomllib.load(fh).get("ci") or {}

def _tracked(root: str) -> list:
    """git-tracked, not os.walk: a runner executes what the repository ships."""
    import subprocess
    out = subprocess.run(["git", "-C", root, "ls-files"] + list(TRACKED),
                         capture_output=True, text=True, check=False).stdout
    # fnmatchcase, never fnmatch: on Windows the case-insensitive form makes the
    # registry resolve differently than it does on the runner.
    return sorted({p.strip().replace(os.sep, "/") for p in out.splitlines() if p.strip()})

def _glob_members(root: str, spec: dict) -> list:
    d = spec.get("dir", "")
    pat = spec.get("glob", "*")
    skip = set(spec.get("skip") or ())
    full = os.path.join(root, d)
    if not os.path.isdir(full):
        return []
    return [f"{d}/{fn}" for fn in sorted(os.listdir(full))
            if fnmatch.fnmatchcase(fn, pat) and fn not in skip]

def _registered(root: str, ci: dict) -> dict:
    """path -> tier, for every listed suite and every glob member."""
    reg = {}
    for tier, paths in (ci.get("tiers") or {}).items():
        for p in paths:
            reg[p] = tier
    for spec in (ci.get("globs") or {}).values():
        for p in _glob_members(root, spec):
            reg[p] = spec.get("tier", "unit")
    return reg

# `if:` values that switch a step off outright. An arbitrary expression is left
# alone -- guessing at one would be a worse lie than reading none.
_DISABLED = {"false", "'false'", '"false"', "${{ false }}", "${{false}}"}
_INVOKE = re.compile(r"run-suites\.sh\s+(\S+)")

def _live_run_commands(body: str) -> list:
    """The shell commands a workflow actually executes.

    Parity used to be `f"run-suites.sh {tier}" in body`: a raw substring over the
    whole file, comments and disabled steps included. A step commented out, or
    guarded `if: false`, kept satisfying the one check whose entire job is to
    notice that a publisher has quietly stopped running a tier. Only the value of
    a live `run:` key counts now.
    """
    steps, cur = [], None
    for raw in body.splitlines():
        if not raw.strip():
            continue
        ind = len(raw) - len(raw.lstrip())
        if raw.lstrip().startswith("-"):
            if cur:
                steps.append(cur)
            cur = [ind, [raw]]
        elif cur and ind > cur[0]:
            cur[1].append(raw)
        elif cur:
            steps.append(cur)
            cur = None
    if cur:
        steps.append(cur)

    cmds = []
    for _, chunk in steps:
        keys = [ln.strip()[2:].lstrip() if ln.strip().startswith("- ")
                else ln.strip() for ln in chunk]
        if any(k.startswith("if:") and k[3:].strip() in _DISABLED for k in keys):
            continue
        block = 0
        for raw, key in zip(chunk, keys):
            ind = len(raw) - len(raw.lstrip())
            if block:
                if ind >= block:
                    line = raw.strip()
                    if not line.startswith("#"):
                        cmds.append(line.split(" #", 1)[0].strip())
                    continue
                block = 0
            if key.startswith("#"):
                continue
            if key.startswith("run:"):
                val = key[4:].strip()
                if val.startswith(("|", ">")):
                    block = ind + 1
                else:
                    cmds.append(val.split(" #", 1)[0].strip())
    return cmds

def cmd_list(root: str, ci: dict, tier: str) -> int:
    reg = _registered(root, ci)
    if tier not in (ci.get("tiers") or {}) and tier not in {
            s.get("tier") for s in (ci.get("globs") or {}).values()}:
        print(f"unknown tier: {tier}", file=sys.stderr)
        return 2
    for path in sorted(p for p, t in reg.items() if t == tier):
        runner = "python3" if path.endswith(".py") else "bash"
        print(f"{runner}\t{path}")
    return 0

def cmd_check(root: str, ci: dict) -> int:
    viol = []
    reg = _registered(root, ci)
    exempt = ci.get("exempt") or {}

    for path, tier in sorted(reg.items()):
        if not os.path.isfile(os.path.join(root, path)):
            viol.append(f"[ci.tiers].{tier} lists {path}, which does not exist")

    listed = {}
    for tier, paths in (ci.get("tiers") or {}).items():
        for p in paths:
            if p in listed:
                viol.append(f"{p} is registered in both {listed[p]} and {tier}")
            listed[p] = tier

    for name, spec in sorted((ci.get("globs") or {}).items()):
        d, pat = spec.get("dir", ""), spec.get("glob", "*")
        if not os.path.isdir(os.path.join(root, d)):
            viol.append(f"[ci.globs.{name}] dir '{d}' is not a directory -- a"
                        " renamed dir registers zero suites and says nothing")
        elif not _glob_members(root, spec):
            viol.append(f"[ci.globs.{name}] '{d}/{pat}' matches no file -- an"
                        " empty glob removes every suite it used to supply"
                        " without moving a count anything watches")
        if spec.get("skip") and not str(spec.get("skip_reason") or "").strip():
            viol.append(f"[ci.globs.{name}] skips {len(spec['skip'])} suite(s)"
                        " with no skip_reason -- a skip is an exemption")

    # A runner is exempt from the tiers because it EXECUTES them. One that never
    # reads the registry is not a harness, it is a suite parked out of reach of
    # both the tiers and the exemption ratchet.
    runners = set(ci.get("runners") or ())
    for path in sorted(runners):
        full = os.path.join(root, path)
        if not os.path.isfile(full):
            viol.append(f"[ci].runners lists {path}, which does not exist")
        elif "ci-suites.py" not in open(
                full, encoding="utf-8", errors="replace").read():
            viol.append(f"[ci].runners {path} never reads the suite registry, so"
                        " it is not a harness -- a suite listed here runs nowhere"
                        " and never touches [ci].max_exempt_suites")

    for path in _tracked(root):
        if path in reg or path in exempt or path in runners:
            continue
        viol.append(f"{path} is tracked but runs in no tier and is not exempt")

    for path, reason in sorted(exempt.items()):
        if not str(reason).strip():
            viol.append(f"[ci.exempt] {path} carries no reason")
        if path in reg:
            viol.append(f"{path} is both exempt and registered in {reg[path]}")

    tiers = sorted(ci.get("tiers") or {})
    for wf in (".github/workflows/mios-ci.yml", ".forgejo/workflows/build-mios.yml"):
        full = os.path.join(root, wf)
        if not os.path.isfile(full):
            viol.append(f"{wf} is missing -- both publishers must run the tiers")
            continue
        body = open(full, encoding="utf-8", errors="replace").read()
        cmds = _live_run_commands(body)
        if not cmds:
            viol.append(f"{wf} has no live 'run:' step at all -- parity is read"
                        " off executed commands, not off the file's text")
        ran = {m.group(1).strip("'\"") for c in cmds for m in _INVOKE.finditer(c)}
        for tier in tiers:
            if tier not in ran:
                viol.append(f"{wf} never runs the '{tier}' tier")

    ceiling = ci.get("max_exempt_suites")
    if ceiling is None:
        viol.append("[ci] has no max_exempt_suites -- an absent ceiling is a broken"
                    " ratchet, not an open one")
    elif len(exempt) > int(ceiling):
        viol.append(f"exempt suites {len(exempt)} > ceiling {ceiling}")

    print("\n".join(viol))
    if not viol:
        print(f"[ci-suites] {len(reg)} suite(s) registered across "
              f"{len(set(reg.values()))} tier(s); {len(exempt)}/{ceiling} exempt",
              file=sys.stderr)
    return 1 if viol else 0

def main(argv: list) -> int:
    root = _root()
    try:
        ci = _load(root)
    except OSError as exc:
        print(f"mios.toml unreadable: {exc}")
        return 1
    if not ci:
        print("mios.toml has no [ci] table -- the suite registry is the only"
              " thing that keeps the publishers running the same set")
        return 1
    if "--check" in argv:
        return cmd_check(root, ci)
    if "--python-packages" in argv:
        py = ci.get("python") or {}
        args = []
        for req in (py.get("requirements") or ()):
            args += ["-r", req]
        args += list(py.get("packages") or ())
        print(" ".join(args))
        return 0
    for i, a in enumerate(argv):
        if a == "--tier" and i + 1 < len(argv):
            return cmd_list(root, ci, argv[i + 1])
        if a.startswith("--tier="):
            return cmd_list(root, ci, a.split("=", 1)[1])
    print("usage: ci-suites.py --tier <name> | --check | --python-packages",
          file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
