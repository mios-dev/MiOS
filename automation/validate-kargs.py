#!/usr/bin/env python3
# 'MiOS' v0.2.4 -- Bootc kargs.d validator
"""
validate-kargs.py -- 'MiOS' kargs.d schema validator.

Checks every *.toml in:
  kargs.d/                              (repo root drop-ins)
  usr/lib/bootc/kargs.d/  (image-baked drop-ins)

Schema rules (bootc-dev/bootc authoritative):
  - Top-level key `kargs` (required) must be a list of strings.
  - Top-level key `match-architectures` (optional) must be a list of strings.
  - NO other top-level keys.
  - NO [section] table headers anywhere in the file.
  - Each kargs entry must be a single string (not space-joined multi-arg).
  - Keys with "delete" in their name are invalid parameter -- reject.

Exit codes: 0 = pass, 1 = validation failure(s), 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    try:
        import tomli as tomllib  # type: ignore[import]
    except ImportError:
        print("ERROR: Python ≥ 3.11 required (tomllib stdlib) or install tomli.", file=sys.stderr)
        sys.exit(2)
else:
    import tomllib

ALLOWED_TOP_KEYS: frozenset[str] = frozenset({"kargs", "match-architectures"})

KNOWN_ARCHS: frozenset[str] = frozenset({
    "x86_64", "aarch64", "riscv64", "ppc64le", "s390x", "arm",
})

SECTION_HEADER_RE = re.compile(r"^\s*\[")


def _github_error(path: Path, line: int | None, msg: str) -> None:
    loc = f"file={path}" + (f",line={line}" if line is not None else "")
    print(f"::error {loc}::{msg}")


def _github_warning(path: Path, line: int | None, msg: str) -> None:
    loc = f"file={path}" + (f",line={line}" if line is not None else "")
    print(f"::warning {loc}::{msg}")


def validate_file(path: Path, *, github: bool = False, results: list[dict]) -> bool:
    ok = True
    issues: list[dict] = []

    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    for lineno, text in enumerate(lines, start=1):
        if SECTION_HEADER_RE.match(text) and not text.strip().startswith("#"):
            msg = "[section] header found -- bootc forbids table headers in kargs.d"
            issues.append({"line": lineno, "msg": msg, "level": "error"})
            ok = False

    try:
        data = tomllib.loads(raw)
    except Exception as exc:
        msg = f"TOML parse error: {exc}"
        issues.append({"line": None, "msg": msg, "level": "error"})
        results.append({"path": str(path), "ok": False, "issues": issues})
        _emit(path, issues, github=github)
        return False

    for key in data:
        if key not in ALLOWED_TOP_KEYS:
            if "delete" in key.lower():
                msg = (
                    f"'{key}' is an invalid parameter -- bootc has no delete mechanism "
                    "in kargs.d drop-ins. Remove it."
                )
            else:
                msg = f"Unknown top-level key '{key}'. Only 'kargs' and 'match-architectures' are allowed."
            issues.append({"line": None, "msg": msg, "level": "error"})
            ok = False

    if "kargs" not in data:
        issues.append({"line": None, "msg": "Missing required 'kargs' key.", "level": "error"})
        ok = False
    else:
        kargs = data["kargs"]
        if not isinstance(kargs, list):
            issues.append({"line": None, "msg": f"'kargs' must be a list, got {type(kargs).__name__}.", "level": "error"})
            ok = False
        else:
            for i, entry in enumerate(kargs):
                if not isinstance(entry, str):
                    issues.append({
                        "line": None,
                        "msg": f"kargs[{i}] is {type(entry).__name__}, expected string.",
                        "level": "error",
                    })
                    ok = False
                elif " " in entry and not entry.startswith("console="):
                    issues.append({
                        "line": None,
                        "msg": (
                            f"kargs[{i}] '{entry}' contains a space. "
                            "Each kernel argument should be its own list entry."
                        ),
                        "level": "warning",
                    })

    if "match-architectures" in data:
        ma = data["match-architectures"]
        if not isinstance(ma, list):
            issues.append({
                "line": None,
                "msg": f"'match-architectures' must be a list, got {type(ma).__name__}.",
                "level": "error",
            })
            ok = False
        else:
            for arch in ma:
                if not isinstance(arch, str):
                    issues.append({"line": None, "msg": f"match-architectures entry {arch!r} is not a string.", "level": "error"})
                    ok = False
                elif arch not in KNOWN_ARCHS:
                    issues.append({
                        "line": None,
                        "msg": f"match-architectures: '{arch}' is not a known Rust target_arch value ({', '.join(sorted(KNOWN_ARCHS))}).",
                        "level": "warning",
                    })

    _emit(path, issues, github=github)
    results.append({"path": str(path), "ok": ok, "issues": issues})
    return ok


def _emit(path: Path, issues: list[dict], *, github: bool) -> None:
    for issue in issues:
        level = issue["level"]
        lineno = issue.get("line")
        msg = issue["msg"]
        if github:
            if level == "error":
                _github_error(path, lineno, msg)
            else:
                _github_warning(path, lineno, msg)
        else:
            loc = f":{lineno}" if lineno is not None else ""
            prefix = "ERROR" if level == "error" else "WARN "
            print(f"  {prefix}  {path}{loc}: {msg}")


def collect_files(dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for d in dirs:
        if d.is_dir():
            files.extend(sorted(d.glob("*.toml")))
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate 'MiOS' kargs.d TOML files.")
    parser.add_argument("paths", nargs="*", help="Explicit .toml files or directories.")
    parser.add_argument("--github", action="store_true", help="Emit GitHub Actions annotation format.")
    parser.add_argument("--json", dest="json_out", action="store_true", help="Emit JSON report to stdout.")
    args = parser.parse_args(argv)

    if args.paths:
        candidates: list[Path] = []
        for p in args.paths:
            pp = Path(p)
            if pp.is_dir():
                candidates.extend(sorted(pp.glob("*.toml")))
            elif pp.suffix == ".toml":
                candidates.append(pp)
    else:
        repo_root = Path(__file__).parent.parent
        default_dirs = [
            repo_root / "kargs.d",
            repo_root / "system_files" / "usr" / "lib" / "bootc" / "kargs.d",
        ]
        candidates = collect_files(default_dirs)

    if not candidates:
        print("No .toml files found to validate.", file=sys.stderr)
        return 0

    results: list[dict] = []
    all_ok = True

    for f in candidates:
        if not args.github and not args.json_out:
            print(f"Checking {f} ...")
        passed = validate_file(f, github=args.github, results=results)
        if not passed:
            all_ok = False

    if args.json_out:
        print(json.dumps({"files": len(results), "pass": all_ok, "results": results}, indent=2))
    elif not args.github:
        passed_n = sum(1 for r in results if r["ok"])
        failed_n = len(results) - passed_n
        print(f"\n{passed_n}/{len(results)} files passed" + (f", {failed_n} failed" if failed_n else "."))

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
