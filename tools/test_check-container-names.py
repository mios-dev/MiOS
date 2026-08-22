#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-container-names.py. Builds throwaway trees and asserts every direction the real audit produced: a matching pair passes, a MISSING ContainerName fails (Quadlet would name it systemd-<unit>, which no systemctl name matches), a mismatched one fails on either surface independently so SSOT and rendered file cannot drift apart alone, a TEMPLATE unit must name the instantiated `<base>-%i` form rather than its own key, a container gated off in [quadlets.enable] may render nothing but must still name itself correctly for the day it is switched on, an ENABLED container with no rendered file fails, and an empty tree fails rather than passing vacuously over nothing.
# AI-related: ./check-container-names.py, usr/share/mios/mios.toml, usr/share/containers/systemd/
# AI-functions: check, mkrepo, run, main

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "check_container_names", os.path.join(_HERE, "check-container-names.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))


def mkrepo(ssot, rendered, enable=None):
    """ssot: {unit: ContainerName|None}. rendered: {unit: ContainerName|None}."""
    root = tempfile.mkdtemp(prefix="cname-")
    os.makedirs(os.path.join(root, "usr/share/mios"), exist_ok=True)
    os.makedirs(os.path.join(root, "usr/share/containers/systemd"), exist_ok=True)
    lines = []
    for unit, cname in ssot.items():
        lines.append(f'[containers."{unit}".Container]')
        if cname is not None:
            lines.append(f'ContainerName = "{cname}"')
        lines.append("")
    if enable:
        lines.append("[quadlets.enable]")
        for unit, on in enable.items():
            lines.append(f'"{unit}" = {"true" if on else "false"}')
    open(os.path.join(root, M.TOML), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    for unit, cname in rendered.items():
        body = "[Container]\n" + (f"ContainerName={cname}\n" if cname is not None else "")
        open(os.path.join(root, "usr/share/containers/systemd", f"{unit}.container"),
             "w", encoding="utf-8").write(body)
    return root


def run(root):
    p = subprocess.run([sys.executable, os.path.join(_HERE, "check-container-names.py")],
                       env={**os.environ, "MIOS_DRIFT_ROOT": root},
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def main():
    roots = []

    r = mkrepo({"mios-a": "mios-a"}, {"mios-a": "mios-a"}); roots.append(r)
    rc, out = run(r)
    check("a matching pair passes", rc == 0, out)

    r = mkrepo({"mios-a": None}, {"mios-a": "mios-a"}); roots.append(r)
    rc, out = run(r)
    check("a MISSING ContainerName in the SSOT fails",
          rc == 1 and "systemd-mios-a" in out, out)

    r = mkrepo({"mios-a": "mios-a"}, {"mios-a": None}); roots.append(r)
    rc, out = run(r)
    check("a rendered unit with no ContainerName fails", rc == 1, out)

    r = mkrepo({"mios-a": "something-else"}, {"mios-a": "mios-a"}); roots.append(r)
    rc, out = run(r)
    check("an SSOT name that is not the unit name fails", rc == 1, out)

    r = mkrepo({"mios-a": "mios-a"}, {"mios-a": "something-else"}); roots.append(r)
    rc, out = run(r)
    check("a RENDERED name that is not the unit name fails independently", rc == 1, out)

    r = mkrepo({"mios-w@": "mios-w-%i"}, {"mios-w@": "mios-w-%i"}); roots.append(r)
    rc, out = run(r)
    check("a template unit naming <base>-%i passes", rc == 0, out)

    r = mkrepo({"mios-w@": "mios-w@"}, {"mios-w@": "mios-w@"}); roots.append(r)
    rc, out = run(r)
    check("a template unit naming its own key fails", rc == 1, out)

    r = mkrepo({"mios-a": "mios-a", "mios-off": "mios-off"}, {"mios-a": "mios-a"},
               enable={"mios-off": False}); roots.append(r)
    rc, out = run(r)
    check("a gated-off container may render nothing", rc == 0, out)
    check("the pass line counts the gated-off container", "gated-off=1" in out, out)

    r = mkrepo({"mios-a": "mios-a", "mios-off": None}, {"mios-a": "mios-a"},
               enable={"mios-off": False}); roots.append(r)
    rc, out = run(r)
    check("a gated-off container must STILL name itself correctly", rc == 1, out)

    r = mkrepo({"mios-a": "mios-a", "mios-b": "mios-b"}, {"mios-a": "mios-a"}); roots.append(r)
    rc, out = run(r)
    check("an ENABLED container with no rendered unit fails",
          rc == 1 and "regenerate" in out, out)

    r = mkrepo({}, {}); roots.append(r)
    rc, out = run(r)
    check("an empty tree fails rather than passing over nothing", rc == 1, out)

    check("expected_name: a plain unit names itself",
          M.expected_name("mios-a") == "mios-a")
    check("expected_name: a template names the instantiated form",
          M.expected_name("mios-w@") == "mios-w-%i")

    for r in roots:
        shutil.rmtree(r, ignore_errors=True)
    print(f"\n{'FAIL' if _fails else 'PASS'}: {_fails} failure(s)")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
