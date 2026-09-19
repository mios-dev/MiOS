#!/usr/bin/env python3
"""
ship.py - Safe Trunk-Based Shipping & Worktree Reconciliation Engine (/ship, /sh).
Verifies pre-flight gates, reconciles branches, merges changes with conflict abort,
prunes worktrees, cleans ephemeral branches, and records changelog entries.
Complies with Stage 6 of the 2026 Dev Loop Engineering Lifecycle.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ShipResult:
    source_branch: str
    target_branch: str
    merge_commit: Optional[str]
    success: bool
    changelog_updated: bool
    worktree_pruned: bool
    branch_cleaned: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    message: str = ""


class ShipEngine:
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
        src_path = self.script_dir.parent / "assets" / "templates" / "RELEASE_CHECKLIST.md"
        if not src_path.exists():
            src_path = self.repo_root / "reference" / "templates" / "RELEASE_CHECKLIST.md"
        dest_path = self.repo_root / "RELEASE_CHECKLIST.md"
        if src_path.exists():
            shutil.copy2(src_path, dest_path)
            print(f"[SCAFFOLDED] Created {dest_path.name} at {dest_path}")
        return dest_path

    def ship(self, source_branch: str, target_branch: str = "main", tag: Optional[str] = None, delete_branch: bool = False, **kwargs) -> ShipResult:
        print(f"==> Shipping branch '{source_branch}' into '{target_branch}'...")
        result = ShipResult(
            source_branch=source_branch,
            target_branch=target_branch,
            merge_commit=None,
            success=False,
            changelog_updated=False,
            worktree_pruned=False,
            branch_cleaned=False
        )

        # 1. Pre-flight dirty check
        st_res = subprocess.run(["git", "status", "--porcelain"], cwd=self.repo_root, capture_output=True, text=True)
        # Exclude .worktrees from dirty status
        dirty = [l for l in st_res.stdout.splitlines() if not l.endswith(".worktrees/")]
        if dirty:
            result.message = f"Pre-flight gate failed: Working tree has {len(dirty)} uncommitted modifications."
            print(f"[ERROR] {result.message}", file=sys.stderr)
            self._save_report(result)
            return result

        # 1.5. SCOPE Staged Code Review Gate
        rev_py = self.script_dir / "review.py"
        if rev_py.exists() and not kwargs.get('skip_scope_gate', False):
            print(f"==> Running SCOPE Staged Oversight Gate on '{source_branch}'...")
            rev_res = subprocess.run([sys.executable, str(rev_py), source_branch], cwd=self.repo_root, capture_output=True, text=True)
            if rev_res.returncode != 0:
                result.message = f"SCOPE Assurance Gate failed for '{source_branch}'. Unresolved findings or Escalate Down tier active."
                print(f"[ERROR] {result.message}", file=sys.stderr)
                self._save_report(result)
                return result

        # 2. Verify target branch exists
        br_check = subprocess.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{target_branch}"], cwd=self.repo_root)
        if br_check.returncode != 0:
            # Maybe master is default
            if target_branch == "main":
                m_check = subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/master"], cwd=self.repo_root)
                if m_check.returncode == 0:
                    target_branch = "master"
                    result.target_branch = "master"

        # 3. Checkout target branch
        p = subprocess.run(["git", "checkout", target_branch], cwd=self.repo_root, capture_output=True, text=True)
        if p.returncode != 0:
            result.message = f"Failed to checkout {target_branch}: {p.stderr.strip()}"
            self._save_report(result)
            return result

        # 4. Atomic merge with automatic abort on conflict
        p_merge = subprocess.run(
            ["git", "merge", "--no-ff", "-m", f"Merge lane {source_branch} via DevLoop /ship", source_branch],
            cwd=self.repo_root, capture_output=True, text=True
        )
        if p_merge.returncode != 0:
            result.message = f"Merge conflict or failure: {p_merge.stderr.strip()}"
            print(f"[WARN] Conflict detected. Aborting merge cleanly...", file=sys.stderr)
            subprocess.run(["git", "merge", "--abort"], cwd=self.repo_root, capture_output=True)
            self._save_report(result)
            return result

        sha_res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo_root, capture_output=True, text=True)
        result.merge_commit = sha_res.stdout.strip()
        result.success = True

        # 5. Update changelog
        result.changelog_updated = self._update_changelog(source_branch, result.merge_commit)

        # 6. Prune worktrees
        subprocess.run(["git", "worktree", "prune"], cwd=self.repo_root, capture_output=True)
        result.worktree_pruned = True

        # 7. Optional clean feature branch
        if delete_branch and source_branch != target_branch:
            del_res = subprocess.run(["git", "branch", "-d", source_branch], cwd=self.repo_root, capture_output=True)
            result.branch_cleaned = (del_res.returncode == 0)

        # 8. Release Tagging
        if tag:
            subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag} via DevLoop /ship"], cwd=self.repo_root)

        result.message = f"Successfully shipped {source_branch} into {target_branch} at commit {result.merge_commit[:8]}."
        self._save_report(result)
        self._export_markdown(result)
        return result

    def _update_changelog(self, lane_name: str, commit_sha: str) -> bool:
        cl_path = self.repo_root / "CHANGELOG.md"
        if not cl_path.exists():
            # Create a standard Keep-a-Changelog template
            cl_path.write_text(
                "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n## [Unreleased]\n",
                encoding="utf-8"
            )

        content = cl_path.read_text(encoding="utf-8")
        date_str = datetime.now().strftime("%Y-%m-%d")
        entry = f"- [{date_str}] Merged `{lane_name}` ({commit_sha[:8]})\n"

        if "## [Unreleased]" in content:
            new_content = content.replace("## [Unreleased]", f"## [Unreleased]\n{entry}")
        else:
            new_content = f"# Changelog\n\n## [Unreleased]\n{entry}\n" + content

        cl_path.write_text(new_content, encoding="utf-8")
        return True

    def _save_report(self, result: ShipResult):
        path = self.artifacts_dir / f"ship_{int(time.time())}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, indent=2)
        print(f"[SAVED] Ship telemetry: {path}")

    def _export_markdown(self, result: ShipResult):
        out_path = self.repo_root / "SHIP_REPORT.md"
        lines = [
            "# Dev Loop Ship Report (`/ship`, `/sh`)",
            "",
            f"**Source Branch:** `{result.source_branch}`  ",
            f"**Target Branch:** `{result.target_branch}`  ",
            f"**Timestamp:** {result.timestamp}  ",
            f"**Success:** `{'YES' if result.success else 'NO'}`  ",
            f"**Merge Commit:** `{result.merge_commit or 'N/A'}`  ",
            f"**Changelog Updated:** `{'YES' if result.changelog_updated else 'NO'}`  ",
            f"**Worktree Pruned:** `{'YES' if result.worktree_pruned else 'NO'}`  ",
            f"**Branch Cleaned:** `{'YES' if result.branch_cleaned else 'NO'}`  ",
            "",
            "## Delivery Summary",
            f"{result.message}",
            ""
        ]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"[EXPORTED] Markdown ship report: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Dev Loop Safe Shipping & Worktree Reconciliation Engine")
    parser.add_argument("source", nargs="?", help="Source feature or lane branch to merge")
    parser.add_argument("--target", default="main", help="Target trunk branch (default: main)")
    parser.add_argument("--tag", help="Optional release tag to apply upon successful merge")
    parser.add_argument("--delete-branch", action="store_true", help="Delete source branch after successful merge")
    parser.add_argument("--init", action="store_true", help="Scaffold RELEASE_CHECKLIST.md template")
    parser.add_argument("--skip-scope-gate", action="store_true", help="Bypass automated SCOPE staged review gate")

    args = parser.parse_args()
    engine = ShipEngine()

    if args.init:
        engine.scaffold_template()
    elif args.source:
        res = engine.ship(args.source, target_branch=args.target, tag=args.tag, delete_branch=args.delete_branch, skip_scope_gate=args.skip_scope_gate)
        sys.exit(0 if res.success else 1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
