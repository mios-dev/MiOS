#!/usr/bin/env python3
# AI-hint: Drift gate for the [units] projection debt register. The authoritative rendering comparison lives in the Rust test tools/native/mios-unit-gen/tests/projection.rs, which CI always runs; this gate enforces the half that needs no toolchain -- the register names real, declared, sorted, unique units and never grows past [unit_projection].max_drift. It runs mios-unit-gen --check too when a built binary is there, and SAYS SO when there is not, because a gate that skips quietly is how the golden test stayed green over a copy of itself for months.
# AI-related: usr/share/mios/mios.toml, tools/test_check-unit-projection.py, tools/native/mios-unit-gen/src/lib.rs, tools/native/mios-unit-gen/tests/projection.rs, automation/98-drift-checks.sh
# AI-functions: declared_units, unit_aliases, _built, register, max_drift, shipped, hygiene, binary_path, run_binary, main
"""Gate: the [units] projection's debt register is real, sorted and shrinking."""

import os
import shutil
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"
UNIT_DIR = "usr/lib/systemd/system"


def declared_units(data: dict) -> set:
    """Unit filenames [units.*] projects. Table-valued keys only -- the
    string-valued half is name aliases, not units. See TASKS.md T-317."""
    return {k for k, v in (data.get("units") or {}).items() if isinstance(v, dict)}


def unit_aliases(data: dict) -> set:
    """The string-valued half of [units]: name -> unit-file aliases."""
    return {k for k, v in (data.get("units") or {}).items() if isinstance(v, str)}


def register(data: dict) -> list:
    """[unit_projection].drift, in declaration order."""
    reg = (data.get("unit_projection") or {}).get("drift")
    if reg is None:
        return []
    return [str(x).strip() for x in reg if str(x).strip()]


def max_drift(data: dict):
    """The ratchet ceiling, or None when the table declares none."""
    val = (data.get("unit_projection") or {}).get("max_drift")
    return val if isinstance(val, int) else None


def shipped(root: str) -> set:
    """Unit files actually on disk."""
    d = os.path.join(root, UNIT_DIR)
    if not os.path.isdir(d):
        return set()
    return {n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n))}


def hygiene(data: dict, root: str) -> list:
    """Everything about the register that can be checked without rendering."""
    viol = []
    units = declared_units(data)
    if not units:
        return ["[units.*] declares no units at all -- the projection gate would "
                "pass vacuously over an empty set"]

    table = data.get("unit_projection")
    if table is None:
        return ["[unit_projection] is absent -- the [units] projection has no debt "
                "register, so nothing bounds how far the declarations may drift"]
    if "drift" not in table:
        viol.append("[unit_projection] declares no `drift` key -- an implied empty "
                    "register is indistinguishable from a forgotten one")

    reg = register(data)
    if len(reg) != len(set(reg)):
        dupes = sorted({x for x in reg if reg.count(x) > 1})
        viol.append("[unit_projection].drift lists a unit twice: %s" % ", ".join(dupes))
    if reg != sorted(reg):
        viol.append("[unit_projection].drift is not sorted -- an unsorted register "
                    "hides an addition inside a reordering")

    on_disk = shipped(root)
    for name in sorted(set(reg)):
        if name not in units:
            viol.append("[unit_projection].drift names '%s', which [units.*] does "
                        "not declare -- a unit outside the projection cannot drift "
                        "from it" % name)
        elif name not in on_disk:
            viol.append("[unit_projection].drift names '%s', which the tree does "
                        "not ship" % name)

    ceiling = max_drift(data)
    if ceiling is None:
        viol.append("[unit_projection].max_drift is unset -- without a ceiling the "
                    "register can absorb new drift as fast as it is created")
    elif len(reg) > ceiling:
        viol.append("[unit_projection].drift holds %d entries, over the ratchet "
                    "ceiling max_drift = %d. The ceiling only comes DOWN: fix the "
                    "declaration instead of raising it" % (len(reg), ceiling))
    elif len(reg) < ceiling:
        viol.append("[unit_projection].drift holds %d entries but max_drift is "
                    "still %d -- lower the ceiling to %d so the ground gained is "
                    "held" % (len(reg), ceiling, len(reg)))
    return viol


def _built(root: str):
    for rel in ("target/release/mios-unit-gen", "target/debug/mios-unit-gen",
                "target/release/mios-unit-gen.exe", "target/debug/mios-unit-gen.exe"):
        p = os.path.join(root, "tools/native", rel)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def binary_path(root: str, build: bool = True):
    """A built mios-unit-gen, building it once if cargo is available.

    Without this the gate SKIPS its rendering comparison wherever nobody has run
    cargo -- which is every CI checkout, the one place it matters. See T-317.
    """
    found = _built(root)
    if found or not build:
        return found
    if not shutil.which("cargo"):
        return None
    try:
        subprocess.run(["cargo", "build", "--manifest-path",
                        os.path.join(root, "tools/native/Cargo.toml"),
                        "-p", "mios-unit-gen"],
                       capture_output=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        return None
    return _built(root)


def run_binary(path: str, root: str):
    """(ok, output). The binary owns the rendering comparison; we only relay it."""
    env = dict(os.environ, MIOS_ROOT=os.path.abspath(root))
    try:
        proc = subprocess.run([path, "--check"], env=env, capture_output=True,
                              text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "mios-unit-gen --check could not run: %s" % exc
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, out


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-unit-projection: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 1

    viol = hygiene(data, root)

    binary = binary_path(root)
    if binary:
        ok, out = run_binary(binary, root)
        if not ok:
            for line in out.splitlines():
                if line.strip():
                    viol.append(line.strip())
    elif os.environ.get("MIOS_DRIFT_REQUIRE_TOOLS", "0") == "1":
        viol.append("no built mios-unit-gen, so the rendering half did not run "
                    "and a drifting unit dropped from the register would pass "
                    "(MIOS_DRIFT_REQUIRE_TOOLS=1). Build it: "
                    "cd tools/native && cargo build -p mios-unit-gen")
    if viol:
        for v in viol:
            print("check_unit_projection: %s" % v, file=sys.stderr)
        return 1

    reg, units = register(data), declared_units(data)
    note = ("mios-unit-gen --check agrees" if binary else
            "NOT rendering-checked here: no mios-unit-gen and no cargo to build one. "
            "tools/native/mios-unit-gen/tests/projection.rs is the authority and CI runs it")
    print("[check-unit-projection] %d unit(s) declared in [units.*] (plus %d name "
          "aliases sharing the table), %d registered as drifted (ceiling %s). %s."
          % (len(units), len(unit_aliases(data)), len(reg), max_drift(data), note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
