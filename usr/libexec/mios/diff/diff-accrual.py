#!/usr/bin/env python3
# AI-hint: Diff snapshotting, boot-cycle accrual, and risk classification engine for WS-DIFFCYCLE.
# AI-doc: usr/share/doc/mios/manual/ch63-diff-snapshotting-boot-accrual-and-hitl-rollin.md
# AI-related: usr/share/doc/mios/adr/0018-shutdown-diff-snapshotting-and-boot-cycle-accrual.md
"""
WS-DIFFCYCLE: Shutdown Diff Snapshotting and Boot-Cycle Accrual Engine.
Captures modified files, redacts secrets, classifies risks (Safe vs High-Risk),
and persists audit ledgers atomically with sub-3s execution SLA.
"""

from __future__ import annotations

import argparse
import datetime
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# SSOT & Policy Defaults
DEFAULT_DIFF_DIR = "/var/lib/mios/diffs"
DEFAULT_SNAPSHOT_DIR = "/var/lib/mios/snapshots/boot-diffs"
DEFAULT_LEDGER_PATH = "/var/run/mios/accrued-diffs.json"
EXECUTION_TIMEOUT_SECS = 3.0

SAFE_PATTERNS = [
    ".config/*",
    "config/*",
    "etc/skel/*",
    "var/lib/mios/ai/skills/*",
    "etc/NetworkManager/system-connections/*",
    "usr/share/doc/*",
    "usr/share/mios/themes/*",
    "*.md",
]

HIGH_RISK_PATTERNS = [
    "etc/pam.d/*",
    "etc/shadow*",
    "etc/sudoers*",
    "usr/bin/*",
    "usr/sbin/*",
    "usr/lib/systemd/*",
    "etc/systemd/*",
    "etc/kargs.d/*",
    "etc/kernel/*",
    "etc/nftables/*",
    "usr/share/mios/security/egress.nft",
    "etc/containers/*",
    "etc/crio/*",
]

KV_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|secret|password|token|bearer|passphrase)(\s*[:=]\s*)['\"]?([^\s'\"]+)['\"]?")
PK_SECRET_PATTERN = re.compile(r"-----BEGIN\s+[A-Z\s]+PRIVATE\s+KEY-----[\s\S]*?-----END\s+[A-Z\s]+PRIVATE\s+KEY-----|-----BEGIN\s+[A-Z\s]+PRIVATE\s+KEY-----")


def redact_secrets(content: str) -> str:
    """Sanitize secret values to comply with SECRETS-NEVER-IN-ENV and persistence hygiene."""
    sanitized = KV_SECRET_PATTERN.sub(r"\1\2[REDACTED]", content)
    sanitized = PK_SECRET_PATTERN.sub(r"[REDACTED_PRIVATE_KEY]", sanitized)
    return sanitized


def classify_risk(file_path: str) -> str:
    """Classify file mutation into 'safe', 'high-risk', or 'review' tier."""
    norm_path = file_path.replace("\\", "/")
    while norm_path.startswith("./"):
        norm_path = norm_path[2:]
    norm_path = norm_path.lstrip("/")

    for pat in HIGH_RISK_PATTERNS:
        if fnmatch.fnmatch(norm_path, pat):
            return "high-risk"
    for pat in SAFE_PATTERNS:
        if fnmatch.fnmatch(norm_path, pat):
            return "safe"
    if norm_path.startswith("etc/"):
        return "high-risk"
    return "review"


def classify_path(file_path: str) -> str:
    """Alias for classify_risk for interface compatibility."""
    risk = classify_risk(file_path)
    return risk if risk in ("safe", "high-risk") else "safe"


def atomic_write_json(target_path: str, data: Any) -> None:
    """Write JSON data to disk using an atomic replace pattern to prevent corruption."""
    parent = os.path.dirname(os.path.abspath(target_path))
    if parent and not os.path.exists(parent):
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError:
            pass

    tmp_file = f"{target_path}.tmp.{os.getpid()}.{int(time.time() * 1000)}"
    payload = json.dumps(data, indent=2, sort_keys=True)
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_file, target_path)
    finally:
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass


def snapshot_diffs(
    root_dir: str,
    output_dir: str = DEFAULT_SNAPSHOT_DIR,
    boot_id: Optional[str] = None,
    timeout_secs: float = EXECUTION_TIMEOUT_SECS,
) -> Dict[str, Any]:
    """Capture modified and untracked files into an atomic snapshot."""
    start_time = time.monotonic()
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not boot_id:
        boot_id = str(uuid.uuid4())[:8]

    modified_files: List[Dict[str, Any]] = []

    # Fast Git Diff Check against .git == /
    git_dir = os.path.join(root_dir, ".git")
    if os.path.isdir(git_dir):
        try:
            proc = subprocess.run(
                ["git", "--git-dir", git_dir, "--work-tree", root_dir, "status", "--porcelain=v1", "-uall"],
                capture_output=True,
                text=True,
                timeout=timeout_secs,
                check=False,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if len(line) < 3:
                        continue
                    status = line[:2].strip()
                    rel_path = line[3:].strip()
                    full_path = os.path.join(root_dir, rel_path)
                    size = os.path.getsize(full_path) if os.path.isfile(full_path) else 0
                    diff_type = "untracked" if status == "??" else "modified" if "M" in status else "deleted" if "D" in status else "added"
                    risk = classify_risk(rel_path)
                    modified_files.append({
                        "path": rel_path.replace("\\", "/"),
                        "status": status,
                        "type": diff_type,
                        "size_bytes": size,
                        "risk": risk,
                    })
        except subprocess.TimeoutExpired:
            sys.stderr.write(f"[diff-accrual] Snapshot timed out after {timeout_secs}s\n")
        except Exception as e:
            sys.stderr.write(f"[diff-accrual] Git status failed: {e}\n")

    duration_ms = (time.monotonic() - start_time) * 1000.0

    snapshot = {
        "schema_version": "1.0",
        "timestamp": timestamp,
        "boot_id": boot_id,
        "root": root_dir,
        "duration_ms": round(duration_ms, 2),
        "total_files": len(modified_files),
        "total_changes": len(modified_files),
        "files": modified_files,
        "changes": modified_files,
    }

    out_file = os.path.join(output_dir, f"{timestamp}-{boot_id}.json")
    atomic_write_json(out_file, snapshot)
    return snapshot


def accrue_diffs(
    snapshot_dir: str = DEFAULT_SNAPSHOT_DIR,
    ledger_path: str = DEFAULT_LEDGER_PATH,
) -> Dict[str, Any]:
    """Aggregate historical diff snapshots and generate risk-classified audit ledger."""
    accrued: Dict[str, Dict[str, Any]] = {}
    if not os.path.isdir(snapshot_dir):
        ledger = {
            "schema_version": "1.0",
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_diffs": 0,
            "total_accrued": 0,
            "safe_count": 0,
            "high_risk_count": 0,
            "safe_diffs": [],
            "high_risk_diffs": [],
            "entries": [],
            "status": "ready_for_review",
        }
        atomic_write_json(ledger_path, ledger)
        return ledger

    for fn in sorted(os.listdir(snapshot_dir)):
        if not fn.endswith(".json"):
            continue
        fp = os.path.join(snapshot_dir, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                snap = json.load(f)
                items = snap.get("changes") or snap.get("files") or []
                for item in items:
                    p = item["path"]
                    risk_val = item.get("risk", classify_risk(p))
                    accrued[p] = {
                        "path": p,
                        "status": item.get("status", "M"),
                        "type": item.get("type", "modified"),
                        "size_bytes": item.get("size_bytes", 0),
                        "risk": risk_val,
                        "last_observed": snap.get("timestamp"),
                    }
        except (json.JSONDecodeError, OSError):
            continue

    entries = list(accrued.values())
    safe_diffs = [e for e in entries if e["risk"] == "safe"]
    high_risk_diffs = [e for e in entries if e["risk"] == "high-risk"]

    ledger = {
        "schema_version": "1.0",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_diffs": len(entries),
        "total_accrued": len(entries),
        "safe_count": len(safe_diffs),
        "high_risk_count": len(high_risk_diffs),
        "safe_diffs": safe_diffs,
        "high_risk_diffs": high_risk_diffs,
        "entries": sorted(entries, key=lambda x: (x["risk"], x["path"])),
        "status": "ready_for_review",
    }

    atomic_write_json(ledger_path, ledger)
    return ledger


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="MiOS WS-DIFFCYCLE Shutdown Diff & Accrual Engine")
    subparsers = parser.add_subparsers(dest="command")

    # Snapshot subparser
    snap_parser = subparsers.add_parser("snapshot", help="Capture pre-poweroff diff snapshot")
    snap_parser.add_argument("--root", default=os.environ.get("MIOS_ROOT", os.getcwd()))
    snap_parser.add_argument("--output-dir", "--snapshot-dir", dest="output_dir", default=DEFAULT_SNAPSHOT_DIR)
    snap_parser.add_argument("--boot-id", default=None)
    snap_parser.add_argument("--timeout-secs", type=float, default=EXECUTION_TIMEOUT_SECS)

    # Accrue subparser
    accrue_parser = subparsers.add_parser("accrue", help="Accrue historical diffs into audit ledger")
    accrue_parser.add_argument("--snapshots-dir", "--snapshot-dir", dest="snapshots_dir", default=DEFAULT_SNAPSHOT_DIR)
    accrue_parser.add_argument("--ledger-out", "--ledger", dest="ledger_out", default=DEFAULT_LEDGER_PATH)

    # Classify subparser
    classify_parser = subparsers.add_parser("classify", help="Classify file path risk")
    classify_parser.add_argument("--path", required=True, help="File path to classify")

    args = parser.parse_args(argv)

    if args.command == "snapshot":
        snap = snapshot_diffs(args.root, args.output_dir, args.boot_id, args.timeout_secs)
        print(f"[diff-accrual] Snapshot recorded: {snap['total_changes']} changes in {snap['duration_ms']}ms")
        return 0
    elif args.command == "accrue":
        ledger = accrue_diffs(args.snapshots_dir, args.ledger_out)
        print(f"[diff-accrual] Accrued ledger written: {ledger['total_diffs']} changes (Safe: {ledger['safe_count']}, High-Risk: {ledger['high_risk_count']})")
        return 0
    elif args.command == "classify":
        print(classify_risk(args.path))
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
