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

def _fail(message: str) -> int:
    print(f"[check-ratchet-direction] FAIL: {message}", file=sys.stderr)
    return 1

def _skip(message: str) -> int:
    print(f"[check-ratchet-direction] SKIP: {message}")
    return 0

def _is_checkout(root: str) -> bool:
    """.git is a directory in a clone and a file in a worktree; both count."""
    return os.path.exists(os.path.join(root, ".git"))

def _tracked_in_index(root: str, rel: str) -> bool:
    """True when git's index lists rel, which survives the worktree copy going."""
    proc = subprocess.run(["git", "-C", root, "ls-files", "--", rel],
                          capture_output=True, text=True, check=False)
    return proc.returncode == 0 and bool(proc.stdout.strip())

def read_head_toml(root: str, rel: str) -> tuple[dict | None, int]:
    """(parsed HEAD copy, 0) or (None, status the caller must return).

    A git that REFUSES leaves no ceiling compared, so it fails; a genuinely
    absent git is a missing tool and skips unless CI demands the toolchain.
    """
    require_tools = os.environ.get("MIOS_DRIFT_REQUIRE_TOOLS") == "1"
    if not _is_checkout(root):
        return None, _skip(f"{root} is not a checkout, so there is no HEAD to compare against")
    try:
        proc = subprocess.run(["git", "-C", root, "show", f"HEAD:{rel}"],
                              capture_output=True, check=True)
    except FileNotFoundError:
        if require_tools:
            return None, _fail("git is not installed, so no ceiling was compared against HEAD")
        return None, _skip("git is not installed; set MIOS_DRIFT_REQUIRE_TOOLS=1 to make that a failure")
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or b"").decode("utf-8", "replace").strip() or "no message"
        return None, _fail(f"git could not read HEAD:{rel} (exit {exc.returncode}: {detail}) -- no ceiling was compared")
    except OSError as exc:
        return None, _fail(f"git could not be run in {root} ({exc}) -- no ceiling was compared")
    try:
        return tomllib.loads(proc.stdout.decode("utf-8")), 0
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        return None, _fail(f"the committed HEAD:{rel} does not parse ({exc}) -- the SSOT in HEAD is broken")

def main() -> int:
    toml_path = os.path.join(_ROOT, _TOML_REL)
    if not os.path.isfile(toml_path):
        # Absent though TRACKED is a dropped deliverable; a tree that never had
        # it is not a checkout of this repo and has nothing to ratchet.
        if _is_checkout(_ROOT) and _tracked_in_index(_ROOT, _TOML_REL):
            return _fail(f"{_TOML_REL} is tracked but missing from the worktree -- the ratchet has no ceilings to read")
        return _skip(f"{toml_path} not found and not tracked here")

    with open(toml_path, "rb") as fh:
        work_cfg = tomllib.load(fh)

    head_cfg, status = read_head_toml(_ROOT, _TOML_REL)
    if head_cfg is None:
        return status

    work_ceilings = extract_ratchet_ceilings(work_cfg)
    head_ceilings = extract_ratchet_ceilings(head_cfg)
    # Zero ceilings on either side means nothing was compared, whatever the
    # loop below then reports.
    if not work_ceilings:
        return _fail(f"{_TOML_REL} declares no shrink-only ceiling, so no ratchet direction was checked")
    if not head_ceilings:
        return _fail(f"HEAD:{_TOML_REL} declares no shrink-only ceiling, so no ratchet direction was checked")

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
