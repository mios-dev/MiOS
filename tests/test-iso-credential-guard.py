#!/usr/bin/env python3
# AI-hint: Unit test verifying ISO credential guard in Justfile.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Unit test for ISO credential guard in Justfile."""

from __future__ import annotations
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_JUSTFILE = os.path.join(_ROOT, "Justfile")


def test_iso_credential_guard():
    with open(_JUSTFILE, "r", encoding="utf-8") as f:
        content = f.read()

    iso_idx = content.find("iso: build")
    assert iso_idx != -1, "iso recipe missing in Justfile"
    next_recipe_idx = content.find("\nqcow2: build", iso_idx)
    iso_block = content[iso_idx:next_recipe_idx] if next_recipe_idx != -1 else content[iso_idx:]

    assert '${MIOS_USER_PASSWORD_HASH:-}|g' not in iso_block, "iso recipe uses empty fallback in sed replacement string"
    assert '[ -z "${MIOS_USER_PASSWORD_HASH:-}" ]' in iso_block, "iso recipe lacks non-empty guard for MIOS_USER_PASSWORD_HASH"


def main() -> int:
    print("[test-iso-credential-guard] Running ISO credential guard verification...")
    test_iso_credential_guard()
    print("[test-iso-credential-guard] PASS: Verified ISO credential guard in Justfile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
