#!/usr/bin/env python3
"""
triage.py - Automated Phantom-Failure Triage & Flakiness Isolation Engine (/triage, /tr).
Distinguishes deterministic code bugs, flaky tests, and phantom environment failures.
Generates minimal standalone reproduction scripts and exports actionable findings.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TriageClassification:
    failure_type: str  # DETERMINISTIC_BUG, FLAKY_TEST, PHANTOM_ENVIRONMENT, INDEX_LOCK, RESOURCE_STARVATION, WORKTREE_POINTER_BUG, STALE_CACHE_DRIFT
    confidence: float
    root_cause_summary: str
    reproduction_steps: List[str] = field(default_factory=list)
    remediation_recommendation: str = ""
    repro_script_path: Optional[str] = None


@dataclass
class TriageReport:
    command_executed: str
    exit_code: int
    classification: Optional[TriageClassification] = None
    stdout_sample: str = ""
    stderr_sample: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class FailureTriager:
    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = Path(repo_root or self._find_repo_root()).resolve()
        self.artifacts_dir = self.repo_root / ".devloop"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.script_dir = Path(__file__).resolve().parent

    def _find_repo_root(self) -> Path:
        try:
            out = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
            return Path(out).resolve()
        except Exception:
            cur = Path.cwd()
            for parent in [cur] + list(cur.parents):
                if (parent / ".git").exists():
                    return parent
            return cur

    def scaffold_template(self) -> Path:
        src_path = self.script_dir.parent / "assets" / "templates" / "TRIAGE_INCIDENT.md"
        if not src_path.exists():
            src_path = self.repo_root / "reference" / "templates" / "TRIAGE_INCIDENT.md"
        dest_path = self.repo_root / "INCIDENT_TRIAGE.md"
        if src_path.exists():
            shutil.copy2(src_path, dest_path)
            print(f"[SCAFFOLDED] Created {dest_path.name} at {dest_path}")
        return dest_path

    def triage_command(self, test_cmd: str, iterations: int = 3) -> TriageReport:
        print(f"==> Triaging command across {iterations} iteration(s): '{test_cmd}'...")
        results = []
        for i in range(iterations):
            p = subprocess.run(test_cmd, shell=True, cwd=self.repo_root, capture_output=True, text=True)
            results.append((p.returncode, p.stdout, p.stderr))
            if p.returncode == 0 and iterations > 1:
                time.sleep(0.5)

        first_rc, first_out, first_err = results[0]
        report = TriageReport(
            command_executed=test_cmd,
            exit_code=first_rc,
            stdout_sample=first_out[-1000:] if first_out else "",
            stderr_sample=first_err[-1000:] if first_err else ""
        )

        return_codes = [r[0] for r in results]
        stderr_combined = " ".join([r[2] for r in results])
        stdout_combined = " ".join([r[1] for r in results])
        full_output = (stderr_combined + " " + stdout_combined).lower()

        if "index.lock" in full_output:
            clf = TriageClassification(
                failure_type="INDEX_LOCK",
                confidence=0.98,
                root_cause_summary="Git index lock contention detected (active index.lock prevents git operations).",
                remediation_recommendation="Use scripts/git_lock.py safe runner with exponential backoff or prune stale lockfiles."
            )
        elif "not a directory" in full_output and (".git" in full_output or "gitdir" in full_output):
            clf = TriageClassification(
                failure_type="WORKTREE_POINTER_BUG",
                confidence=0.96,
                root_cause_summary="Code assumes .git is a directory, violating the linked git worktree pointer file invariant.",
                remediation_recommendation="Resolve git paths via 'git rev-parse --git-dir' instead of static '.git' directory checks."
            )
        elif any(term in full_output for term in ["enospc", "out of memory", "oom", "resource temporarily unavailable"]):
            clf = TriageClassification(
                failure_type="RESOURCE_STARVATION",
                confidence=0.95,
                root_cause_summary="System resource exhaustion (memory, disk space, or process limits).",
                remediation_recommendation="Prune temporary worktrees, clear disk caches, and reduce parallel lane concurrency."
            )
        elif any(term in full_output for term in ["stale file handle", "cache mismatch", "pycache", ".pytest_cache"]):
            clf = TriageClassification(
                failure_type="STALE_CACHE_DRIFT",
                confidence=0.90,
                root_cause_summary="Stale build or test cache drift detected.",
                remediation_recommendation="Execute clean cache wipe: find . -name '__pycache__' -exec rm -rf {} +; rm -rf .pytest_cache."
            )
        elif 0 in return_codes and any(rc != 0 for rc in return_codes):
            clf = TriageClassification(
                failure_type="FLAKY_TEST",
                confidence=0.90,
                root_cause_summary=f"Non-deterministic test outcome across {iterations} runs (Exit codes: {return_codes}).",
                remediation_recommendation="Isolate race condition, async timeout, unseeded random generator, or unmocked network call."
            )
        elif all(rc != 0 for rc in return_codes):
            repro_path = self._generate_repro_script(test_cmd)
            clf = TriageClassification(
                failure_type="DETERMINISTIC_BUG",
                confidence=0.92,
                root_cause_summary="Persistent deterministic failure reproducible across all test runs.",
                remediation_recommendation="Inspect failure stack trace, verify assertion invariants, and patch root cause logic.",
                repro_script_path=str(repro_path.relative_to(self.repo_root)) if repro_path else None
            )
        else:
            clf = TriageClassification(
                failure_type="CLEAN_PASS",
                confidence=1.0,
                root_cause_summary="Command completed with exit code 0 on all executions.",
                remediation_recommendation="No action needed."
            )

        report.classification = clf
        self._save_report(report)
        self._export_markdown(report)
        return report

    def _generate_repro_script(self, test_cmd: str) -> Path:
        repro_path = self.repo_root / "repro.sh"
        content = f"""#!/usr/bin/env bash
# Standalone reproduction script generated by Dev Loop /triage
# Run directly in terminal to isolate from AI harness environment
set -euo pipefail
echo "==> Dev Loop Standalone Reproduction: {test_cmd}"
export PYTHONDONTWRITEBYTECODE=1
{test_cmd}
"""
        repro_path.write_text(content, encoding="utf-8")
        try:
            repro_path.chmod(0o755)
        except OSError:
            pass
        return repro_path

    def _save_report(self, report: TriageReport):
        path = self.artifacts_dir / f"triage_{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)
        print(f"[SAVED] Triage telemetry: {path}")

    def _export_markdown(self, report: TriageReport):
        out_path = self.repo_root / "TRIAGE.md"
        clf = report.classification or TriageClassification(
            failure_type="UNKNOWN", confidence=0.0, root_cause_summary="No classification"
        )
        lines = [
            "# Dev Loop Incident Triage Report (`/triage`, `/tr`)",
            "",
            f"**Timestamp:** {report.timestamp}  ",
            f"**Command:** `{report.command_executed}`  ",
            f"**Initial Exit Code:** `{report.exit_code}`  ",
            f"**Classification:** `{clf.failure_type}` (Confidence: {int(clf.confidence * 100)}%)  ",
            "",
            "## Root Cause Summary",
            f"{clf.root_cause_summary}",
            "",
            "## Remediation Recommendation",
            f"{clf.remediation_recommendation}",
            ""
        ]
        if clf.repro_script_path:
            lines.extend([
                "## Reproduction Script",
                f"Run standalone: `./{clf.repro_script_path}`",
                ""
            ])
        if report.stderr_sample:
            lines.extend([
                "## Stderr Sample",
                "```",
                report.stderr_sample.strip(),
                "```",
                ""
            ])
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[EXPORTED] Markdown triage report: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Dev Loop Phantom-Failure Triage Engine")
    parser.add_argument("command", nargs="?", default="", help="Failing command or test to triage")
    parser.add_argument("--runs", type=int, default=3, help="Number of repetitions for flakiness check")
    parser.add_argument("--init", action="store_true", help="Scaffold TRIAGE_INCIDENT.md template")

    args = parser.parse_args()
    triager = FailureTriager()

    if args.init:
        triager.scaffold_template()
    elif args.command:
        report = triager.triage_command(args.command, iterations=args.runs)
        if report.classification and report.classification.failure_type in ("DETERMINISTIC_BUG", "FLAKY_TEST"):
            sys.exit(1)
        sys.exit(0)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
