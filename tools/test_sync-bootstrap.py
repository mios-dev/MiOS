#!/usr/bin/env python3
# AI-hint: Fixtures for sync-bootstrap.py -- the Law 15 mirror. Proves it reports drift without --apply, that a table mirror rewrites values rather than appending duplicates, and that it never touches a surface the manifest does not declare.
# AI-related: tools/sync-bootstrap.py, usr/share/mios/mios.toml, automation/98-drift-checks.sh
# AI-functions: main
"""What the mirror must not get wrong.

Two failure modes are specific and expensive: silently WRITING when only asked
to report, and appending a duplicate table instead of rewriting one -- the
duplicate-table bug that has made mios.toml unparseable twice in this repo.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

_spec = importlib.util.spec_from_file_location("sb", os.path.join(HERE, "sync-bootstrap.py"))
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)

FAILED: list[str] = []
PASSED = 0

def check(name, got, want):
    global PASSED
    if got == want:
        PASSED += 1
    else:
        FAILED.append(f"{name}: got {got!r}, want {want!r}")

def test_manifest_is_declared_in_ssot():
    sync, data = sb.load_manifest(ROOT)   # (the [bootstrap.sync] table, whole SSOT)
    check("manifest-is-mapping", isinstance(sync, dict), True)
    # A mirror with nothing declared would sync nothing and still report success.
    declared = bool(sync.get("mirror_files") or sync.get("mirror_toml_tables"))
    check("manifest-declares-something", declared, True)
    check("ssot-loaded", "ports" in data, True)
    # [colors] is shared too; the retired ports-drift check was its only parsed compare.
    check("colors-is-mirrored", "colors" in (sync.get("mirror_toml_tables") or ()), True)
    check("ssot-manifest-consistent", sb.validate_manifest(sync), [])

def test_dry_run_does_not_write():
    """Without --apply the mirror must report and change nothing."""
    with tempfile.TemporaryDirectory() as d:
        boot = os.path.join(d, "boot")
        os.makedirs(boot)
        target = os.path.join(boot, "VERSION")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("ORIGINAL\n")
        before = open(target, encoding="utf-8").read()
        try:
            sb.mirror_files(ROOT, boot, ["VERSION"], apply=False)
        except Exception:
            pass
        check("dry-run-leaves-file", open(target, encoding="utf-8").read(), before)

def test_table_rewrite_does_not_duplicate():
    """A mirrored table must be REWRITTEN, never appended a second time."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "mios.toml")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write('[ports]\nalpha = 1\nbeta = 2\n\n[other]\nx = 1\n')
        sb._rewrite_table(p, "ports", {"alpha": 9, "beta": 2, "gamma": 3})
        text = open(p, encoding="utf-8").read()
        check("one-ports-table", text.count("[ports]"), 1)
        check("value-rewritten", "alpha = 9" in text, True)
        check("new-key-added", "gamma = 3" in text, True)
        check("other-table-intact", "[other]" in text and "x = 1" in text, True)
        # It must still parse -- a duplicate table would make this raise.
        try:
            import tomllib
            with open(p, "rb") as fh:
                data = tomllib.load(fh)
            check("still-parses", data["ports"]["alpha"], 9)
        except ImportError:
            pass

def test_unlistable_repo_is_not_silent_agreement():
    """A git that cannot list files must not read as "nothing undeclared"."""
    with tempfile.TemporaryDirectory() as tmp:
        # not a git repository, so `git -C tmp ls-files` exits 128
        man = {"mirror_files": ["a"], "not_mirrored": []}
        drift = sb.unclassified_shared(tmp, tmp, man)
        check("unlistable-repo-reports-drift", bool(drift), True)
        joined = " ".join(drift)
        check("names-the-cause", "did not run" in joined, True)


_MAIN_SYNC = {"mirror_files": '["shared.txt"]',
              "mirror_toml_tables": '["ports", "colors"]',
              "not_mirrored": '["README.md"]'}
_TABLES = '[ports]\nagent_pipe = 1\n\n[colors]\nbg = "#000000"\n'

def _repo(path: str, files: dict) -> str:
    for rel, body in files.items():
        full = os.path.join(path, rel)
        os.makedirs(os.path.dirname(full) or path, exist_ok=True)
        with open(full, "wb") as fh:
            fh.write(body.encode("utf-8") if isinstance(body, str) else body)
    subprocess.run(["git", "-C", path, "init", "-q"], check=True)
    subprocess.run(["git", "-C", path, "add", "-A"], check=True)
    return path

def _run(d: str, sync=None, main_files=None, boot_files=None, boot_arg=None,
         extra=()) -> tuple[int, str]:
    """Build a two-repo pair under d, run sync-bootstrap on it, return (rc, output)."""
    sync = {**_MAIN_SYNC, **(sync or {})}
    toml = "[bootstrap.sync]\n" + "".join(f"{k} = {v}\n" for k, v in sync.items())
    mfiles = {"usr/share/mios/mios.toml": toml + "\n" + _TABLES,
              "shared.txt": "same\n", "README.md": "main\n", **(main_files or {})}
    bfiles = {"mios.toml": _TABLES, "shared.txt": "same\n", "README.md": "boot\n",
              **(boot_files or {})}
    m = _repo(os.path.join(d, "main"), {k: v for k, v in mfiles.items() if v is not None})
    b = _repo(os.path.join(d, "boot"), {k: v for k, v in bfiles.items() if v is not None})
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = sb.main(["--root", m, "--bootstrap", boot_arg or b, *extra])
    return rc, out.getvalue()

def _case(name, want_rc, want_text, **kw):
    with tempfile.TemporaryDirectory() as d:
        rc, out = _run(d, **kw)
    check(f"{name}-rc", rc, want_rc)
    check(f"{name}-names-it", want_text in out, True)
    if want_text not in out:
        FAILED.append(f"{name}: output was {out!r}")

def test_two_repo_mirror():
    """Each leg of the Law 15 check, on a throwaway pair: pass clean, fail by name."""
    _case("pos", 0, "1 mirrored file(s) and 2 table(s) match")
    _case("file", 1, "shared.txt: differs", boot_files={"shared.txt": "drifted\n"})
    _case("crlf", 0, "match", boot_files={"shared.txt": b"same\r\n"})
    _case("missing", 1, "shared.txt: missing in mios-bootstrap",
          boot_files={"shared.txt": None})
    _case("table-value", 1, "[colors].bg: main='#000000' bootstrap='#ffffff'",
          boot_files={"mios.toml": _TABLES.replace("#000000", "#ffffff")})
    _case("table-header", 1, "[colors].bg: main='#000000' bootstrap=None",
          boot_files={"mios.toml": _TABLES.split("[colors]")[0]})
    _case("undeclared", 1, "extra.txt: tracked in both repos but declared in neither",
          main_files={"extra.txt": "x\n"}, boot_files={"extra.txt": "x\n"})
    _case("contradiction", 1, "shared.txt: declared in both",
          sync={"not_mirrored": '["README.md", "shared.txt"]'})
    _case("malformed", 1, "' shared.txt': malformed",
          sync={"mirror_files": '["shared.txt", " shared.txt"]'})
    _case("empty", 1, "mirror_files is empty or absent", sync={"mirror_files": "[]"})

def test_absent_bootstrap_always_fails():
    """No switch turns a missing sibling into a pass."""
    saved = os.environ.get("MIOS_DRIFT_REQUIRE_TOOLS")
    try:
        for val in (None, "0"):
            if val is None:
                os.environ.pop("MIOS_DRIFT_REQUIRE_TOOLS", None)
            else:
                os.environ["MIOS_DRIFT_REQUIRE_TOOLS"] = val
            with tempfile.TemporaryDirectory() as d:
                _case(f"absent-require-{val}", 1, "Law 15 NOT checked",
                      boot_arg=os.path.join(d, "no-such-bootstrap"))
    finally:
        if saved is None:
            os.environ.pop("MIOS_DRIFT_REQUIRE_TOOLS", None)
        else:
            os.environ["MIOS_DRIFT_REQUIRE_TOOLS"] = saved

def test_apply_then_check_is_clean():
    """--apply writes mios.git's copy, after which --check agrees."""
    with tempfile.TemporaryDirectory() as d:
        rc, _ = _run(d, boot_files={"shared.txt": "drifted\n"}, extra=("--apply",))
        check("apply-rc", rc, 0)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            rc = sb.main(["--root", os.path.join(d, "main"),
                          "--bootstrap", os.path.join(d, "boot"), "--check"])
        check("apply-then-check-rc", rc, 0)


def main() -> int:
    test_manifest_is_declared_in_ssot()
    test_dry_run_does_not_write()
    test_table_rewrite_does_not_duplicate()
    test_unlistable_repo_is_not_silent_agreement()
    test_two_repo_mirror()
    test_absent_bootstrap_always_fails()
    test_apply_then_check_is_clean()
    print(f"[test_sync-bootstrap] {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"  FAIL {f}")
    return 1 if FAILED else 0

if __name__ == "__main__":
    sys.exit(main())
