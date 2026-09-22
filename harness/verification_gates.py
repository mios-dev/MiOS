#!/usr/bin/env python3
"""MiOS embedded harness verification gate evaluator.

Discovers `invariants/test_*.sh` scripts and executes each one, instead of
merely counting how many exist. Exit-code contract for invariant scripts:

    0   PASS  - invariant verified on this host/container.
    2   SKIP  - invariant is not applicable here (declared optional hardware
                or capability is absent); NOT counted as a pass.
    any other non-zero - FAIL.

The gate fails closed: zero discovered scripts, zero executed scripts, or an
all-SKIP run (nothing actually verified) all exit non-zero. This avoids the
"no tests found -> declared success" and "skip-as-pass" failure modes.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

SKIP_EXIT_CODE = 2
DEFAULT_TIMEOUT_SECONDS = 60
QUICK_TIMEOUT_SECONDS = 15

# Redact secret-shaped substrings before any captured output is printed or
# persisted, per the MiOS persistence-sanitization contract.
_REDACTION_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
)


def redact(text: str) -> str:
    for pattern in _REDACTION_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def discover_scripts(inv_dir: Path) -> list[Path]:
    return sorted(inv_dir.glob("test_*.sh"))


def run_script(script: Path, timeout: int) -> dict:
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        code = proc.returncode
        stdout, stderr = proc.stdout, proc.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        code = 124
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + "\n[gate] script exceeded timeout"
        timed_out = True

    if timed_out:
        status = "FAIL"
    elif code == 0:
        status = "PASS"
    elif code == SKIP_EXIT_CODE:
        status = "SKIP"
    else:
        status = "FAIL"

    return {
        "name": script.name,
        "status": status,
        "exit_code": code,
        "stdout": redact(stdout).strip(),
        "stderr": redact(stderr).strip(),
    }


def run_checks(quick: bool, as_json: bool) -> int:
    inv_dir = Path(__file__).resolve().parent.parent / "invariants"
    scripts = discover_scripts(inv_dir)
    timeout = QUICK_TIMEOUT_SECONDS if quick else DEFAULT_TIMEOUT_SECONDS

    if not scripts:
        _emit(
            {"results": [], "summary": {"pass": 0, "fail": 0, "skip": 0, "total": 0}},
            as_json,
            error="No invariant scripts found under invariants/test_*.sh",
        )
        return 1

    results = [run_script(script, timeout) for script in scripts]
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    summary = {"pass": passed, "fail": failed, "skip": skipped, "total": len(results)}
    _emit({"results": results, "summary": summary}, as_json)

    if failed > 0:
        return 1
    if passed == 0:
        # All invariants were skipped (or none executed): nothing was
        # actually verified, so this must not report success.
        print(
            "[FAIL] All invariants were SKIPPED; nothing was verified.",
            file=sys.stderr,
        )
        return 1
    return 0


def _emit(payload: dict, as_json: bool, error: str | None = None) -> None:
    if as_json:
        if error:
            payload["error"] = error
        print(json.dumps(payload, indent=2))
        return

    print("==> Evaluating MiOS Embedded Harness Verification Gates...")
    if error:
        print(f"[FAIL] {error}", file=sys.stderr)
    for result in payload["results"]:
        marker = {"PASS": "OK", "FAIL": "FAIL", "SKIP": "SKIP"}[result["status"]]
        print(f"[{marker}] {result['name']} (exit={result['exit_code']})")
        if result["status"] == "FAIL" and result["stderr"]:
            print(f"       {result['stderr'].splitlines()[-1]}")
    summary = payload["summary"]
    print(
        f"==> {summary['pass']} passed, {summary['fail']} failed, "
        f"{summary['skip']} skipped, {summary['total']} total."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Use a shorter per-script timeout for lifecycle-hook use.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a structured, redacted JSON result instead of text.",
    )
    args = parser.parse_args()
    return run_checks(quick=args.quick, as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
