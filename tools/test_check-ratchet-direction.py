#!/usr/bin/env python3
# AI-hint: Unit test verifying that check-ratchet-direction detects raised ratchet ceilings and refuses to pass when it read no ceiling.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Unit test for tools/check-ratchet-direction.py."""

from __future__ import annotations
import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_CHECK_SCRIPT = os.path.join(_ROOT, "tools", "check-ratchet-direction.py")
_TOML_REL = "usr/share/mios/mios.toml"

_SEED = '[ci]\nmax_exempt_suites = 6\n[docs]\nmax_stale_refs = 20\n'

def _seed_repo(root: str, body: str) -> None:
    """A real checkout, so the absent-though-tracked predicate is exercised."""
    os.makedirs(os.path.join(root, "usr", "share", "mios"), exist_ok=True)
    with open(os.path.join(root, _TOML_REL), "w", encoding="utf-8") as fh:
        fh.write(body)
    subprocess.run(["git", "-C", root, "init", "-q"], check=True)
    subprocess.run(["git", "-C", root, "config", "user.email", "t@example.invalid"], check=True)
    subprocess.run(["git", "-C", root, "config", "user.name", "t"], check=True)
    subprocess.run(["git", "-C", root, "add", "-f", _TOML_REL], check=True)
    subprocess.run(["git", "-C", root, "commit", "-q", "-m", "seed"], check=True)

def _run(root: str, path: str | None = None, **extra) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["MIOS_DRIFT_ROOT"] = root
    env.pop("MIOS_ROOT", None)
    env.pop("MIOS_DRIFT_REQUIRE_TOOLS", None)
    if path is not None:
        env["PATH"] = path
    env.update(extra)
    return subprocess.run([sys.executable, _CHECK_SCRIPT], capture_output=True, text=True, env=env)

def test_ratchet_direction_logic():
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_ratchet_direction", _CHECK_SCRIPT)
    crd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(crd)

    head_toml = {"ci": {"max_exempt_suites": 6}, "docs": {"max_stale_refs": 20}}
    work_toml_ok = {"ci": {"max_exempt_suites": 6}, "docs": {"max_stale_refs": 19}}
    work_toml_raised = {"ci": {"max_exempt_suites": 7}, "docs": {"max_stale_refs": 20}}

    head_ceilings = crd.extract_ratchet_ceilings(head_toml)
    ok_ceilings = crd.extract_ratchet_ceilings(work_toml_ok)
    raised_ceilings = crd.extract_ratchet_ceilings(work_toml_raised)

    violations_ok = [k for k, w in ok_ceilings.items() if k in head_ceilings and w > head_ceilings[k]]
    assert not violations_ok, f"Expected no violations for ok_ceilings, got {violations_ok}"

    violations_raised = [(k, head_ceilings[k], w) for k, w in raised_ceilings.items()
                         if k in head_ceilings and w > head_ceilings[k]]
    assert violations_raised == [("ci.max_exempt_suites", 6, 7)], f"Expected raised violation, got {violations_raised}"

def test_raised_ceiling_fails_end_to_end(tmp: str):
    root = os.path.join(tmp, "raised")
    _seed_repo(root, _SEED)
    with open(os.path.join(root, _TOML_REL), "w", encoding="utf-8") as fh:
        fh.write(_SEED.replace("max_exempt_suites = 6", "max_exempt_suites = 99"))
    proc = _run(root)
    assert proc.returncode == 1, f"a raised ceiling must fail, got {proc.returncode}: {proc.stdout}{proc.stderr}"
    assert "ci.max_exempt_suites" in proc.stderr, f"the failure must name the ceiling: {proc.stderr}"

def test_tracked_but_deleted_toml_fails(tmp: str):
    root = os.path.join(tmp, "deleted")
    _seed_repo(root, _SEED)
    os.remove(os.path.join(root, _TOML_REL))
    proc = _run(root)
    assert proc.returncode == 1, f"a tracked-but-deleted SSOT must fail, got {proc.returncode}: {proc.stdout}"
    assert "tracked but missing" in proc.stderr, f"the failure must say why: {proc.stderr}"

def test_refusing_git_fails(tmp: str):
    root = os.path.join(tmp, "deadgit")
    _seed_repo(root, _SEED)
    shim = os.path.join(tmp, "shim")
    os.makedirs(shim, exist_ok=True)
    shim_git = os.path.join(shim, "git")
    with open(shim_git, "w", encoding="utf-8") as fh:
        fh.write('#!/bin/sh\necho "fatal: refusing" >&2\nexit 128\n')
    os.chmod(shim_git, 0o755)
    proc = _run(root, path=shim + os.pathsep + os.environ.get("PATH", ""))
    assert proc.returncode == 1, f"a git that refuses must fail, got {proc.returncode}: {proc.stdout}"
    assert "no ceiling was compared" in proc.stderr, f"the failure must say why: {proc.stderr}"

def test_absent_git_skips_unless_ci_demands_it(tmp: str):
    root = os.path.join(tmp, "nogit")
    _seed_repo(root, _SEED)
    empty = os.path.join(tmp, "emptybin")
    os.makedirs(empty, exist_ok=True)
    assert shutil.which("git", path=empty) is None, "the no-git PATH must not resolve git"
    lenient = _run(root, path=empty)
    assert lenient.returncode == 0, f"a missing tool alone must not fail: {lenient.stderr}"
    assert "SKIP" in lenient.stdout, f"the skip must be visible: {lenient.stdout}"
    strict = _run(root, path=empty, MIOS_DRIFT_REQUIRE_TOOLS="1")
    assert strict.returncode == 1, f"MIOS_DRIFT_REQUIRE_TOOLS=1 must make it fail: {strict.stdout}"

def test_toml_without_any_ceiling_fails(tmp: str):
    root = os.path.join(tmp, "noceiling")
    _seed_repo(root, '[ci]\nname = "mios"\n')
    proc = _run(root)
    assert proc.returncode == 1, f"reading zero ceilings must fail, got {proc.returncode}: {proc.stdout}"
    assert "no shrink-only ceiling" in proc.stderr, f"the failure must say why: {proc.stderr}"

def main() -> int:
    print("[test-check-ratchet-direction] Running unit test...")
    test_ratchet_direction_logic()

    with tempfile.TemporaryDirectory(prefix="mios-crd-") as tmp:
        test_raised_ceiling_fails_end_to_end(tmp)
        test_tracked_but_deleted_toml_fails(tmp)
        test_refusing_git_fails(tmp)
        test_absent_git_skips_unless_ci_demands_it(tmp)
        test_toml_without_any_ceiling_fails(tmp)

    proc = subprocess.run([sys.executable, _CHECK_SCRIPT], capture_output=True, text=True)
    assert proc.returncode == 0, f"check-ratchet-direction.py failed on current tree: {proc.stderr}"
    assert "OK:" in proc.stdout, f"Expected OK in output, got {proc.stdout}"

    print("[test-check-ratchet-direction] PASS: raise detection, a dropped SSOT, a refusing git, "
          "a missing git and a ceiling-free SSOT all behave, and the current tree is clean.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
