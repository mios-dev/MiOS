#!/usr/bin/env python3
# AI-hint: Resolves the [ci] suite registry for the runners and fails when a tracked suite is neither registered in a tier nor exempted.
# AI-related: usr/share/mios/mios.toml, tests/run-suites.sh, automation/98-drift-checks.sh
import fnmatch
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# Scanned for coverage. Anything a runner could reasonably be expected to
# execute, so a dead suite has to be declared dead rather than merely ignored.
TRACKED = ("tests/test-*.sh", "tests/test-*.py", "tests/*.sh", "tests/**/*.sh",
           "automation/lint-*.sh")


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

    runners = set(ci.get("runners") or ())
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
        for tier in tiers:
            if f"run-suites.sh {tier}" not in body:
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
