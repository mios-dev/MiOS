#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-firstboot-degrade-open.py.
# AI-doc: usr/share/doc/mios/manual/tools.md

import importlib.util
import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "check_firstboot_degrade_open",
    os.path.join(_HERE, "check-firstboot-degrade-open.py"))
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if cond:
        print("ok   - %s" % name)
    else:
        _fails += 1
        print("FAIL - %s%s" % (name, " -- %s" % detail if detail else ""))


def scan_text(body):
    """Run the real scanner over a throwaway firstboot script."""
    root = tempfile.mkdtemp(prefix="mios-degrade-")
    try:
        d = os.path.join(root, "usr", "libexec", "mios")
        os.makedirs(d)
        path = os.path.join(d, "demo-firstboot.sh")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        return M.scan(path)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_main(body=None):
    """Run main() against a temp root; None means an empty scan set."""
    root = tempfile.mkdtemp(prefix="mios-degrade-main-")
    prev = os.environ.get("MIOS_DRIFT_ROOT")
    try:
        d = os.path.join(root, "usr", "libexec", "mios")
        os.makedirs(d)
        if body is not None:
            with open(os.path.join(d, "demo-firstboot.sh"), "w",
                      encoding="utf-8") as fh:
                fh.write(body)
        os.environ["MIOS_DRIFT_ROOT"] = root
        return M.main()
    finally:
        if prev is None:
            os.environ.pop("MIOS_DRIFT_ROOT", None)
        else:
            os.environ["MIOS_DRIFT_ROOT"] = prev
        shutil.rmtree(root, ignore_errors=True)


def t_unguarded_egress_is_caught():
    bad = scan_text("set -euo pipefail\ncurl -sfL http://x/y -o /tmp/y\n")
    check("unguarded curl under set -e is a finding", len(bad) == 1, repr(bad))


def t_guarded_egress_passes():
    bad = scan_text("set -euo pipefail\ncurl -sfL http://x/y -o /tmp/y || true\n")
    check("|| true guards the call", bad == [], repr(bad))


def t_unrelated_guard_does_not_certify_file():
    # The defect this gate replaced: any '|| true' anywhere passed the file.
    bad = scan_text("set -euo pipefail\nrm -f /tmp/s || true\n"
                    "curl -sfL http://x/y -o /tmp/y\n")
    check("an unrelated '|| true' elsewhere does not certify the script",
          len(bad) == 1, repr(bad))


def t_no_errexit_is_not_a_finding():
    bad = scan_text("curl -sfL http://x/y -o /tmp/y\n")
    check("without set -e an unguarded fetch cannot abort boot", bad == [],
          repr(bad))


def t_indented_set_plus_e_does_not_leak():
    # An indented 'set +e' is inside a function or subshell and must not exempt
    # later top-level lines.
    bad = scan_text("set -euo pipefail\nf() {\n    set +e\n}\n"
                    "curl -sfL http://x/y -o /tmp/y\n")
    check("indented 'set +e' does not disable errexit for later lines",
          len(bad) == 1, repr(bad))


def t_toplevel_set_plus_e_does_exempt():
    bad = scan_text("set -euo pipefail\nset +e\ncurl -sfL http://x/y -o /tmp/y\n")
    check("column-0 'set +e' does exempt what follows", bad == [], repr(bad))


def t_continuation_guard_is_credited():
    bad = scan_text("set -euo pipefail\n(curl -sf \\n    http://x/y) || true\n")
    check("a guard after a continuation is seen", bad == [], repr(bad))


def t_narration_is_not_a_call():
    bad = scan_text('set -euo pipefail\necho "run: curl -sfL http://x/y"\n')
    check("a fetch named inside an echo string is not a call", bad == [],
          repr(bad))


def t_case_pattern_does_not_desync_join():
    # An unmatched ")" in a case pattern must not drive paren depth negative.
    bad = scan_text("set -euo pipefail\ncase $x in\n  *.pyc) ;;\nesac\n"
                    "curl -sfL http://x/y -o /tmp/y\n")
    check("a case pattern does not desynchronise the line join", len(bad) == 1,
          repr(bad))


def t_errexit_variants_register():
    for form in ("set -e", "set -euo pipefail", "set -o errexit"):
        bad = scan_text("%s\ncurl -sfL http://x/y -o /tmp/y\n" % form)
        check("errexit form %r is recognised" % form, len(bad) == 1, repr(bad))


def t_empty_scan_set_fails():
    check("an empty scan set is a failure, not a pass", run_main(None) == 1)


def t_main_returns_zero_when_clean():
    check("main() returns 0 on a clean tree",
          run_main("set -euo pipefail\ncurl -sf http://x/y || true\n") == 0)


def main():
    t_unguarded_egress_is_caught()
    t_guarded_egress_passes()
    t_unrelated_guard_does_not_certify_file()
    t_no_errexit_is_not_a_finding()
    t_indented_set_plus_e_does_not_leak()
    t_toplevel_set_plus_e_does_exempt()
    t_continuation_guard_is_credited()
    t_narration_is_not_a_call()
    t_case_pattern_does_not_desync_join()
    t_errexit_variants_register()
    t_empty_scan_set_fails()
    t_main_returns_zero_when_clean()
    print("\n%d FAILED" % _fails if _fails else "\nok")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())
