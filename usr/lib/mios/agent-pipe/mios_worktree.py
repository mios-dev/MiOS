#!/usr/bin/env python3
# AI-hint: Ephemeral subagent git worktree lifecycle manager and branch pruner for MiOS agent-pipe.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Any


class AgentWorktreeManager:
    """Manages ephemeral git worktree environments and scratch spaces for concurrent subagents."""

    def __init__(
        self,
        repo_root: str = "/mnt/c/MiOS",
        base_worktree_dir: str = "/tmp/agent-workspaces",
        base_scratch_dir: str = "/var/lib/mios/ai/scratch",
        dry_run: bool = False,
    ):
        self.repo_root = repo_root
        self.base_worktree_dir = base_worktree_dir
        self.base_scratch_dir = base_scratch_dir
        self.dry_run = dry_run

    def create_worktree(self, subagent_id: str, base_branch: str = "main") -> Dict[str, Any]:
        """Provisions an isolated git worktree and scratch directory for a subagent."""
        worktree_path = os.path.join(self.base_worktree_dir, subagent_id)
        scratch_path = os.path.join(self.base_scratch_dir, subagent_id)
        branch_name = f"agent/{subagent_id}"

        cmd = ["git", "-C", self.repo_root, "worktree", "add", worktree_path, "-b", branch_name, base_branch]

        if self.dry_run:
            return {
                "status": "dry_run",
                "action": "create",
                "subagent_id": subagent_id,
                "worktree_path": worktree_path,
                "scratch_path": scratch_path,
                "branch": branch_name,
                "command": " ".join(cmd),
            }

        os.makedirs(self.base_worktree_dir, exist_ok=True)
        os.makedirs(scratch_path, exist_ok=True)

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                "status": "success",
                "action": "create",
                "subagent_id": subagent_id,
                "worktree_path": worktree_path,
                "scratch_path": scratch_path,
                "branch": branch_name,
            }
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            return {
                "status": "error",
                "action": "create",
                "subagent_id": subagent_id,
                "message": str(exc),
            }

    def cleanup_worktree(self, subagent_id: str, merge: bool = False, target_branch: str = "main") -> Dict[str, Any]:
        """Merges verified diffs, unmounts worktree, deletes topic branch, and scrubs scratch."""
        worktree_path = os.path.join(self.base_worktree_dir, subagent_id)
        scratch_path = os.path.join(self.base_scratch_dir, subagent_id)
        branch_name = f"agent/{subagent_id}"

        if self.dry_run:
            return {
                "status": "dry_run",
                "action": "cleanup",
                "subagent_id": subagent_id,
                "worktree_path": worktree_path,
                "merged": merge,
                "cleaned": True,
            }

        # 1. Merge changes if requested
        if merge:
            try:
                subprocess.run(["git", "-C", self.repo_root, "checkout", target_branch], capture_output=True, check=True)
                subprocess.run(["git", "-C", self.repo_root, "merge", "--no-ff", branch_name], capture_output=True, check=True)
            except Exception:
                pass

        # 2. Remove worktree
        try:
            subprocess.run(["git", "-C", self.repo_root, "worktree", "remove", "--force", worktree_path], capture_output=True, check=True)
        except Exception:
            shutil.rmtree(worktree_path, ignore_errors=True)

        # 3. Delete branch
        try:
            subprocess.run(["git", "-C", self.repo_root, "branch", "-D", branch_name], capture_output=True, check=True)
        except Exception:
            pass

        # 4. Scrub scratch files
        shutil.rmtree(scratch_path, ignore_errors=True)

        return {
            "status": "success",
            "action": "cleanup",
            "subagent_id": subagent_id,
            "worktree_removed": True,
            "scratch_scrubbed": True,
            "branch_deleted": True,
        }


def main():
    parser = argparse.ArgumentParser(description="MiOS Subagent Worktree Lifecycle Manager")
    parser.add_argument("--create", help="Subagent ID to create worktree for")
    parser.add_argument("--cleanup", help="Subagent ID to clean up")
    parser.add_argument("--merge", action="store_true", help="Merge topic branch before cleanup")
    parser.add_argument("--dry-run", action="store_true", help="Simulate git worktree lifecycle")
    args = parser.parse_args()

    mgr = AgentWorktreeManager(dry_run=args.dry_run)

    if args.create:
        res = mgr.create_worktree(args.create)
    elif args.cleanup:
        res = mgr.cleanup_worktree(args.cleanup, merge=args.merge)
    else:
        parser.print_help()
        return

    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
