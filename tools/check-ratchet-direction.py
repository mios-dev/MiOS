#!/usr/bin/env python3
# AI-hint: Drift check check_ratchet_direction -- asserts that shrink-only ratchet ceilings in mios.toml never increase over HEAD.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Fail the gate when any shrink-only ceiling in mios.toml increases over HEAD."""

from __future__ import annotations
import os
import subprocess
import sys
import tomllib

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or os.path.abspath(os.path.join(_HERE, ".."))
_TOML_REL = "usr/share/mios/mios.toml"

RATCHET_SECTIONS = {
    "docs", "legibility", "resolver", "tasks", "ci", "tests",
    "ssot_consumers", "unit_projection", "ai_tag", "rust",
    "build.ratchet", "security.privileged_quadlets", "drift",
    "gates", "sandbox"
}


def is_ceiling_key(key_name: str, section_name: str) -> bool:
    if not isinstance(key_name, str):
        return False
    if key_name.startswith("max_") or key_name.startswith("stay_max_") or key_name.endswith("_ceiling"):
        return True
    if section_name in RATCHET_SECTIONS and ("max_" in key_name or "stay_max_" in key_name or "ceiling" in key_name):
        return True
    return False


def extract_ratchet_ceilings(data: dict, prefix: str = "") -> dict[str, int | float]:
    ceilings = {}
    if isinstance(data, dict):
        for k, v in data.items():
            full_key = f"{prefix}.{k}" if prefix else k
            sec = full_key.split(".")[0]
            if isinstance(v, (int, float)) and is_ceiling_key(k, sec):
                ceilings[full_key] = v
            elif isinstance(v, dict):
                ceilings.update(extract_ratchet_ceilings(v, full_key))
    return ceilings


def main() -> int:
    toml_path = os.path.join(_ROOT, _TOML_REL)
    if not os.path.isfile(toml_path):
        print(f"[check-ratchet-direction] SKIP: {toml_path} not found")
        return 0

    with open(toml_path, "rb") as fh:
        work_cfg = tomllib.load(fh)

    try:
        proc = subprocess.run(
            ["git", "-C", _ROOT, "show", f"HEAD:{_TOML_REL}"],
            capture_output=True,
            check=True,
        )
        head_cfg = tomllib.loads(proc.stdout.decode("utf-8"))
    except (subprocess.SubprocessError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"[check-ratchet-direction] WARNING: Could not read HEAD:{_TOML_REL} ({exc}); skipping HEAD comparison.")
        return 0

    work_ceilings = extract_ratchet_ceilings(work_cfg)
    head_ceilings = extract_ratchet_ceilings(head_cfg)

    violations = []
    for key, work_val in sorted(work_ceilings.items()):
        if key in head_ceilings:
            head_val = head_ceilings[key]
            if work_val > head_val:
                violations.append(
                    f"Ratchet ceiling '{key}' INCREASED from {head_val} to {work_val} (shrink-only ceiling violated)"
                )

    if violations:
        print("[check-ratchet-direction] FAIL: Shrink-only ratchet ceiling(s) increased:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1

    print(f"[check-ratchet-direction] OK: All {len(work_ceilings)} shrink-only ratchet ceilings are <= HEAD.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
