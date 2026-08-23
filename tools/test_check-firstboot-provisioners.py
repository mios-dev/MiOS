#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-firstboot-provisioners.py.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_test_check_firstboot_provisioners_py.md

import importlib.util
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "check_firstboot_provisioners",
    os.path.join(_HERE, "check-firstboot-provisioners.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

_fails = 0
SENTINEL = "/var/lib/mios/.demo-done"
VARDIR = "/var/lib/mios/demo"


def check(name, cond, detail=""):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))


def mkroot(*, fetcher=True, sentinel_in_fetcher=True, execstart=None,
           condition=True, condition_path=None, preset=True, tmpfiles=True):
    root = tempfile.mkdtemp(prefix="fbprov-")
    os.makedirs(os.path.join(root, "usr/libexec/mios"), exist_ok=True)
    os.makedirs(os.path.join(root, M.UNIT_DIR), exist_ok=True)
    os.makedirs(os.path.join(root, "usr/lib/systemd/system-preset"), exist_ok=True)
    os.makedirs(os.path.join(root, M.TMPFILES_DIR), exist_ok=True)

    if fetcher:
        body = "#!/usr/bin/env python3\n"
        if sentinel_in_fetcher:
            body += f'SENTINEL = "{SENTINEL}"\n'
        open(os.path.join(root, "usr/libexec/mios/demo-firstboot"), "w").write(body)

    lines = ["[Unit]", "Description=Demo"]
    if condition:
        lines.append("ConditionPathExists=!" + (condition_path or SENTINEL))
    lines += ["", "[Service]", "Type=oneshot",
              "ExecStart=" + (execstart or "/usr/libexec/mios/demo-firstboot")]
    open(os.path.join(root, M.UNIT_DIR, "demo-firstboot.service"), "w").write(
        "\n".join(lines) + "\n")

    open(os.path.join(root, M.PRESET), "w").write(
        "enable demo-firstboot.service\n" if preset else "enable something-else.service\n")

    open(os.path.join(root, M.TMPFILES_DIR, "demo.conf"), "w").write(
        f"d {VARDIR} 0750 827 827 -\n" if tmpfiles else "# nothing declared\n")
    return root


def run(root):
    declared = M.tmpfiles_dirs(root)
    return M.check_one(root, "demo-firstboot.service",
                       "usr/libexec/mios/demo-firstboot", (VARDIR,), declared)


def t_whole_triple_passes():
    r = mkroot()
    try:
        check("a whole triple passes", run(r) == [], str(run(r)))
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_missing_fetcher():
    r = mkroot(fetcher=False)
    try:
        bad = run(r)
        check("a missing fetcher fails", len(bad) == 1 and "does not exist" in bad[0], str(bad))
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_wrong_execstart():
    r = mkroot(execstart="/usr/bin/true")
    try:
        bad = run(r)
        check("an ExecStart pointing elsewhere fails",
              any("ExecStart does not run" in b for b in bad), str(bad))
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_no_condition_gate():
    r = mkroot(condition=False)
    try:
        bad = run(r)
        check("no ConditionPathExists gate fails (would re-run every boot)",
              any("no ConditionPathExists" in b for b in bad), str(bad))
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_sentinel_never_written():
    r = mkroot(sentinel_in_fetcher=False)
    try:
        bad = run(r)
        check("a gate on a sentinel the fetcher never writes fails",
              any("never names that path" in b for b in bad), str(bad))
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_gate_on_a_different_path():
    r = mkroot(condition_path="/var/lib/mios/.some-other-sentinel")
    try:
        bad = run(r)
        check("a gate on the WRONG sentinel path fails",
              any("never names that path" in b for b in bad), str(bad))
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_not_in_preset():
    r = mkroot(preset=False)
    try:
        bad = run(r)
        check("a unit absent from the preset fails",
              any("not enabled in" in b for b in bad), str(bad))
    finally:
        shutil.rmtree(r, ignore_errors=True)


def t_undeclared_var_dir():
    r = mkroot(tmpfiles=False)
    try:
        bad = run(r)
        check("an undeclared /var dir fails (Law 2)",
              any("Architectural Law 2" in b for b in bad), str(bad))
    finally:
        shutil.rmtree(r, ignore_errors=True)


def main():
    t_whole_triple_passes()
    t_missing_fetcher()
    t_wrong_execstart()
    t_no_condition_gate()
    t_sentinel_never_written()
    t_gate_on_a_different_path()
    t_not_in_preset()
    t_undeclared_var_dir()
    print(f"\n{_fails} FAILED" if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
