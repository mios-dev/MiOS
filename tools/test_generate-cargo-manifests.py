#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/generate-cargo-manifests.py -- members come from the crate dirs, --check diffs without writing.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Unit test for tools/generate-cargo-manifests.py."""

from __future__ import annotations
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_GEN = os.path.join(_ROOT, "tools", "generate-cargo-manifests.py")
_CARGO = os.path.join(_ROOT, "tools", "native", "Cargo.toml")

def _load():
    spec = importlib.util.spec_from_file_location("generate_cargo_manifests", _GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _md5(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()

def test_members_come_from_the_crate_directories(mod):
    with tempfile.TemporaryDirectory(prefix="mios-cargo-") as tmp:
        for name in ("zeta-crate", "alpha-crate"):
            os.makedirs(os.path.join(tmp, name))
            with open(os.path.join(tmp, name, "Cargo.toml"), "w", encoding="utf-8") as fh:
                fh.write('[package]\nname = "x"\n')
        os.makedirs(os.path.join(tmp, "target"))          # no Cargo.toml, not a member
        os.makedirs(os.path.join(tmp, "notacrate"))
        found = mod.enumerate_members(tmp)
        assert found == ["alpha-crate", "zeta-crate"], f"expected the two crate dirs sorted, got {found}"

def test_missing_native_dir_yields_no_members(mod):
    assert mod.enumerate_members(os.path.join(_ROOT, "no", "such", "dir")) == []

def test_render_is_deterministic(mod):
    a = mod.render(["b-crate", "a-crate"], "9.9.9")
    b = mod.render(["b-crate", "a-crate"], "9.9.9")
    assert a == b, "render must be deterministic for the same inputs"
    assert '"a-crate",' in a and 'version = "9.9.9"' in a, a

def test_every_crate_on_disk_is_a_member(mod):
    on_disk = set(mod.enumerate_members(os.path.join(_ROOT, "tools", "native")))
    assert on_disk, "tools/native must hold crate directories"
    with open(_CARGO, "r", encoding="utf-8") as fh:
        committed = fh.read()
    missing = sorted(c for c in on_disk if f'"{c}",' not in committed)
    assert not missing, f"crate dir(s) absent from the workspace members: {missing}"

def test_check_mode_reports_clean_and_writes_nothing():
    before = _md5(_CARGO)
    proc = subprocess.run([sys.executable, _GEN, "--check"], capture_output=True, text=True)
    assert proc.returncode == 0, f"--check must be clean on HEAD: {proc.stdout}{proc.stderr}"
    assert _md5(_CARGO) == before, "--check must not rewrite tools/native/Cargo.toml"

def test_hand_edited_manifest_is_reported():
    with open(_CARGO, "r", encoding="utf-8") as fh:
        original = fh.read()
    planted = original.replace('    "xtask",\n', "", 1)
    assert planted != original, "the plant must actually change the manifest"
    try:
        with open(_CARGO, "w", encoding="utf-8") as fh:
            fh.write(planted)
        proc = subprocess.run([sys.executable, _GEN, "--check"], capture_output=True, text=True)
        assert proc.returncode == 1, f"a hand-edited manifest must fail --check, got {proc.returncode}"
        assert "xtask" in proc.stderr, f"the diff must name the dropped member: {proc.stderr}"
    finally:
        with open(_CARGO, "w", encoding="utf-8") as fh:
            fh.write(original)

def main() -> int:
    print("[test-generate-cargo-manifests] Running unit test...")
    mod = _load()
    test_members_come_from_the_crate_directories(mod)
    test_missing_native_dir_yields_no_members(mod)
    test_render_is_deterministic(mod)
    test_every_crate_on_disk_is_a_member(mod)
    test_check_mode_reports_clean_and_writes_nothing()
    test_hand_edited_manifest_is_reported()
    print("[test-generate-cargo-manifests] PASS: members are enumerated from disk, every crate is "
          "a member, --check is read-only and a hand-edit is reported.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
