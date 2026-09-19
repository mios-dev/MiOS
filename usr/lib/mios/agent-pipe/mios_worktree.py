#!/usr/bin/env python3
# AI-hint: Ephemeral subagent git worktree lifecycle manager and branch pruner for MiOS agent-pipe.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Dict, List, Optional, Any

SUBAGENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")

class AgentWorktreeManager:
    """Manages ephemeral git worktree environments and scratch spaces for concurrent subagents."""

    SUBAGENT_ID_RE = SUBAGENT_ID_RE

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
        if not subagent_id or subagent_id in (".", "..") or not self.SUBAGENT_ID_RE.match(subagent_id) or ".." in subagent_id:
            return {
                "status": "error",
                "action": "create",
                "subagent_id": subagent_id,
                "error": "Invalid subagent_id: cannot contain path traversal characters",
                "message": f"Invalid subagent_id: {subagent_id!r}",
            }

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
        if not subagent_id or subagent_id in (".", "..") or not self.SUBAGENT_ID_RE.match(subagent_id) or ".." in subagent_id:
            return {
                "status": "error",
                "action": "cleanup",
                "subagent_id": subagent_id,
                "error": "Invalid subagent_id: cannot contain path traversal characters",
                "message": f"Invalid subagent_id: {subagent_id!r}",
            }

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

        # 1. Merge changes if requested using merge-tree without checking out base
        merge_success = False
        merge_error: Optional[str] = None
        if merge:
            try:
                res = subprocess.run(
                    ["git", "-C", self.repo_root, "merge-tree", "--write-tree", target_branch, branch_name],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode != 0:
                    err_detail = res.stdout.strip() or res.stderr.strip()
                    merge_error = f"merge-tree failed (exit {res.returncode}): {err_detail}"
                else:
                    tree_sha = res.stdout.strip().splitlines()[0].strip()
                    commit_msg = f"Merge {branch_name} into {target_branch}"
                    c_res = subprocess.run(
                        ["git", "-C", self.repo_root, "commit-tree", tree_sha, "-p", target_branch, "-p", branch_name, "-m", commit_msg],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    commit_sha = c_res.stdout.strip()
                    subprocess.run(
                        ["git", "-C", self.repo_root, "update-ref", f"refs/heads/{target_branch}", commit_sha],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    # If target_branch is currently checked out in repo_root, update index and worktree
                    head_res = subprocess.run(
                        ["git", "-C", self.repo_root, "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True,
                        text=True,
                    )
                    if head_res.returncode == 0 and head_res.stdout.strip() == target_branch:
                        subprocess.run(
                            ["git", "-C", self.repo_root, "read-tree", "-u", "-m", "HEAD"],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                    merge_success = True
            except Exception as exc:
                merge_error = str(exc)

        # 2. Remove worktree
        worktree_removed = False
        remove_error: Optional[str] = None
        try:
            rm_res = subprocess.run(
                ["git", "-C", self.repo_root, "worktree", "remove", "--force", worktree_path],
                capture_output=True,
                text=True,
                check=False,
            )
            if rm_res.returncode == 0:
                worktree_removed = True
            else:
                shutil.rmtree(worktree_path, ignore_errors=True)
                worktree_removed = not os.path.exists(worktree_path)
                if not worktree_removed and rm_res.stderr:
                    remove_error = rm_res.stderr.strip()
        except Exception as exc:
            shutil.rmtree(worktree_path, ignore_errors=True)
            worktree_removed = not os.path.exists(worktree_path)
            if not worktree_removed:
                remove_error = str(exc)

        # 3. Delete branch
        branch_deleted = False
        branch_error: Optional[str] = None
        try:
            br_res = subprocess.run(
                ["git", "-C", self.repo_root, "branch", "-D", branch_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if br_res.returncode == 0:
                branch_deleted = True
            elif br_res.stderr:
                branch_error = br_res.stderr.strip()
        except Exception as exc:
            branch_error = str(exc)

        # 4. Scrub scratch files
        shutil.rmtree(scratch_path, ignore_errors=True)
        scratch_scrubbed = not os.path.exists(scratch_path)

        errors: List[str] = []
        if merge and not merge_success:
            errors.append(f"Merge error: {merge_error}")
        if remove_error:
            errors.append(f"Worktree remove error: {remove_error}")
        if branch_error:
            errors.append(f"Branch delete error: {branch_error}")

        status = "error" if errors else "success"
        res: Dict[str, Any] = {
            "status": status,
            "action": "cleanup",
            "subagent_id": subagent_id,
            "merged": merge_success if merge else False,
            "worktree_removed": worktree_removed,
            "scratch_scrubbed": scratch_scrubbed,
            "branch_deleted": branch_deleted,
        }
        if errors:
            res["errors"] = errors
            res["message"] = "; ".join(errors)
        return res

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
