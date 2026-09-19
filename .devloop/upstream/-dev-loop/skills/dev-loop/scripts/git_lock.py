#!/usr/bin/env python3
"""
scripts/git_lock.py
Concurrency lock protection for git repository operations across lanes.
Supports both primary working trees and linked git worktrees (.git pointer file invariant).
"""
import os
import random
import subprocess
import time
from pathlib import Path
from typing import Optional


def resolve_git_dir(cwd: Optional[Path] = None) -> Path:
    """
    Resolves the actual git directory for the current working tree.
    In standard git repos, this is <repo_root>/.git.
    In linked git worktrees, .git is an ASCII pointer file, and the real git directory
    is located at <main_repo>/.git/worktrees/<worker_id>.
    """
    try:
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"],
            text=True,
            cwd=str(cwd) if cwd else None
        ).strip()
        p = Path(git_dir)
        if not p.is_absolute():
            p = ((cwd or Path.cwd()) / p).resolve()
        return p
    except Exception:
        # Fallback to walk-up
        cur = cwd or Path.cwd()
        for parent in [cur] + list(cur.parents):
            git_target = parent / ".git"
            if git_target.is_dir():
                return git_target.resolve()
            elif git_target.is_file():
                # Parse gitdir: pointer
                try:
                    content = git_target.read_text(encoding="utf-8").strip()
                    if content.startswith("gitdir:"):
                        ptr = content.split(":", 1)[1].strip()
                        ptr_path = Path(ptr)
                        if not ptr_path.is_absolute():
                            ptr_path = (parent / ptr_path).resolve()
                        return ptr_path
                except Exception:
                    pass
        return Path(".git").resolve()


def resolve_main_git_dir(cwd: Optional[Path] = None) -> Path:
    """
    Resolves the main repository's .git directory.
    For standard repos, this is identical to resolve_git_dir.
    For linked worktrees (<main>/.git/worktrees/<id>), this resolves to <main>/.git.
    """
    gd = resolve_git_dir(cwd)
    if gd.parent.name == "worktrees" and gd.parent.parent.name == ".git":
        return gd.parent.parent
    return gd


def run_git_safe(args: list, max_retries: int = 8, base_delay: float = 0.25, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Executes a git command with retry backoff against index.lock contention."""
    git_dir = resolve_git_dir(cwd)
    main_git_dir = resolve_main_git_dir(cwd)
    lock_files = [git_dir / "index.lock"]
    if main_git_dir != git_dir:
        lock_files.append(main_git_dir / "index.lock")

    env = {**os.environ, "CI": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat", "PAGER": "cat", "NO_COLOR": "1"}

    for attempt in range(max_retries):
        for lock_file in lock_files:
            if lock_file.exists():
                try:
                    mtime = lock_file.stat().st_mtime
                    # If lockfile is older than 45 seconds, assume abandoned worker process and clean it
                    if time.time() - mtime > 45:
                        lock_file.unlink(missing_ok=True)
                except OSError:
                    pass

        proc = subprocess.run(
            (["git", "-C", str(cwd)] + args) if cwd else (["git"] + args),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env
        )
        if proc.returncode == 0 or "index.lock" not in proc.stderr or attempt == max_retries - 1:
            return proc

        sleep_time = (base_delay * (2 ** attempt)) + random.uniform(0.05, 0.2)
        time.sleep(sleep_time)

    return proc


if __name__ == "__main__":
    git_dir = resolve_git_dir()
    print(f"[dev-loop] Git safe lock runner ready. Active git-dir: {git_dir}")
