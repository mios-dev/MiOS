#!/usr/bin/env python3
"""
goal.py - Dev Loop Goal Engine & Stopping-Condition Evaluator (2026 AI Agent Standards).
Defines, tracks, evaluates, and enforces mathematical stopping conditions for autonomous agentic loops.
Implements loop engineering Level 2-4: Verification, Event-driven evaluation, and Shrink-only ratchets.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


# The closed set evaluate() dispatches on. Anything outside it fails rather than passes:
# an unrecognised type means the criterion was never measured, which is not a pass.
CRITERION_TYPES = ("test", "invariant", "artifact", "git_clean", "non_empty")


@dataclass
class GoalCriterion:
    id: str
    description: str
    criterion_type: str  # one of CRITERION_TYPES
    command: Optional[str] = None
    target_path: Optional[str] = None
    passed: bool = False
    details: Optional[str] = None


@dataclass
class GoalDefinition:
    objective: str
    stopping_condition: str
    status: str = "IN_PROGRESS"  # NOT_STARTED, IN_PROGRESS, VERIFYING, BLOCKED, COMPLETED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    criteria: List[GoalCriterion] = field(default_factory=list)
    non_goals: List[str] = field(default_factory=list)
    ratchet_history: List[Dict[str, int]] = field(default_factory=list)


class GoalEngine:
    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = Path(repo_root or self._find_repo_root()).resolve()
        self.goal_file = self.repo_root / "GOALS.md"
        self.artifacts_dir = self.repo_root / ".devloop"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.artifacts_dir / "goal_state.json"
        self.goal: Optional[GoalDefinition] = None
        self._load()

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

    def _load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    criteria = [GoalCriterion(**c) for c in data.get("criteria", [])]
                    self.goal = GoalDefinition(
                        objective=data.get("objective", ""),
                        stopping_condition=data.get("stopping_condition", ""),
                        status=data.get("status", "IN_PROGRESS"),
                        created_at=data.get("created_at", ""),
                        completed_at=data.get("completed_at"),
                        criteria=criteria,
                        non_goals=data.get("non_goals", []),
                        ratchet_history=data.get("ratchet_history", [])
                    )
            except Exception as e:
                print(f"[WARN] Could not parse goal state: {e}", file=sys.stderr)

    def save(self):
        if not self.goal:
            return
        data = asdict(self.goal)
        temp_file = self.state_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_file.replace(self.state_file)

    def init_goal(self, objective: str, stopping_condition: str, criteria: Optional[List[Dict]] = None, non_goals: Optional[List[str]] = None):
        c_objs = []
        if criteria:
            for idx, c in enumerate(criteria):
                ctype = c.get("type", "invariant")
                if ctype not in CRITERION_TYPES:
                    raise SystemExit(f"[ERROR] criterion {idx+1}: unknown type {ctype!r}; "
                                     f"expected one of {', '.join(CRITERION_TYPES)}")
                if ctype in ("test", "invariant") and not c.get("command"):
                    raise SystemExit(f"[ERROR] criterion {idx+1}: type {ctype!r} needs a command to run")
                if ctype == "non_empty" and not c.get("target_path"):
                    raise SystemExit(f"[ERROR] criterion {idx+1}: type 'non_empty' needs a target_path")
                c_objs.append(GoalCriterion(
                    id=f"C-{idx+1:02d}",
                    description=c.get("description", ""),
                    criterion_type=ctype,
                    command=c.get("command"),
                    target_path=c.get("target_path")
                ))
        else:
            if not stopping_condition:
                raise SystemExit("[ERROR] --stop is required: the stopping condition is the goal's "
                                 "only executable criterion. Give the project's own gate command.")
            # Default minimal robust criteria adhering to 2026 verification standard
            c_objs = [
                GoalCriterion(id="C-01", description=f"Stopping condition: {stopping_condition}", criterion_type="test", command=stopping_condition),
                GoalCriterion(id="C-02", description="Working tree clean of uncommitted residue", criterion_type="git_clean"),
            ]
            # Only mint the artifact criterion where there are task artifacts to validate;
            # a criterion nothing can satisfy is worse than no criterion at all.
            if (self.artifacts_dir / "tasks.jsonl").is_file():
                c_objs.append(GoalCriterion(id="C-03", description="Task artifacts validate (ids, vocabulary, dependency graph, done⇒evidence)", criterion_type="artifact"))

        self.goal = GoalDefinition(
            objective=objective,
            stopping_condition=stopping_condition,
            status="IN_PROGRESS",
            criteria=c_objs,
            non_goals=non_goals or [
                "Do not refactor unassigned modules or out-of-scope files.",
                "Do not introduce regressions to passing baseline tests.",
                "Do not bypass security checks, linters, or suppressions."
            ]
        )
        self.save()
        self._sync_goals_md()
        print(f"[GOAL INITIALIZED] {objective}")
        print(f"  Stopping Condition: {stopping_condition}")

    def _sync_goals_md(self):
        if not self.goal:
            return
        lines = [
            f"# Engineering Goal: {self.goal.objective}",
            "",
            f"**Status:** `{self.goal.status}`  ",
            f"**Stopping Condition:** `{self.goal.stopping_condition}`  ",
            f"**Initialized:** {self.goal.created_at}  ",
            f"**Completed:** `{self.goal.completed_at or 'Pending'}`",
            "",
            "## 1. Core Invariants & Stopping Criteria",
        ]
        for c in self.goal.criteria:
            chk = "[x]" if c.passed else "[ ]"
            cmd_hint = f" (`{c.command}`)" if c.command else ""
            lines.append(f"- {chk} **{c.id}**: {c.description}{cmd_hint}")

        if self.goal.non_goals:
            lines.extend(["", "## 2. Non-Goals (Blast Radius Boundaries)"])
            for ng in self.goal.non_goals:
                lines.append(f"- {ng}")

        with open(self.goal_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def _artifacts_py(self) -> Optional[Path]:
        """artifacts.py ships beside this file; a repo may also vendor its own copy."""
        for cand in (Path(__file__).resolve().parent / "artifacts.py",
                     self.repo_root / "skills" / "dev-loop" / "scripts" / "artifacts.py",
                     self.repo_root / ".devloop" / "artifacts.py"):
            if cand.is_file():
                return cand
        return None

    def evaluate(self) -> bool:
        if not self.goal:
            print("[ERROR] No goal initialized. Run 'goal.py init' first.", file=sys.stderr)
            return False

        print(f"==> Evaluating stopping condition for: {self.goal.objective}")
        all_passed = True

        for c in self.goal.criteria:
            if c.criterion_type in ("test", "invariant") and c.command:
                res = subprocess.run(c.command, shell=True, cwd=self.repo_root, capture_output=True, text=True)
                c.passed = (res.returncode == 0)
                c.details = f"Exit code {res.returncode}"
            elif c.criterion_type == "git_clean":
                # -uall, not the default: porcelain COLLAPSES an untracked directory to a
                # single "?? .devloop/" entry, and a per-file exemption cannot match that. The
                # tempting shortcut is to excuse ".devloop/" wholesale -- which is precisely the
                # blanket-exclusion bug this repo hit in .git/info/exclude, where hiding the
                # directory also hid every lane deliverable inside it. Ask git for per-file
                # granularity instead, so the exemption stays exactly as narrow as it claims.
                res = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=self.repo_root, capture_output=True, text=True)
                # The evaluator WRITES ITS OWN STATE as part of evaluating: save() rewrites
                # GOALS.md and .devloop/goal_state.json with this very verdict. Counting those
                # made the criterion unsatisfiable after the first run -- eval #1 observed a
                # clean tree, recorded "clean", and dirtied the tree doing so; eval #2 then
                # failed on eval #1's writes. The goal could only ever be COMPLETE in a state
                # that no longer existed. Exclude the evaluator's own outputs and the lane
                # worktrees, and SAY SO in the details rather than silently widening the check
                # (SKILL.md 7: narrow the claim, do not widen the check).
                self_written = {"GOALS.md"}
                try:
                    self_written.add(self.state_file.relative_to(self.repo_root).as_posix())
                except ValueError:
                    pass

                def _path(line):  # porcelain: XY <path>, quoted when it contains oddities
                    return line[3:].strip().strip('"') if len(line) > 3 else ""

                dirty_lines, excused = [], []
                for l in res.stdout.splitlines():
                    pth = _path(l)
                    if pth.rstrip("/") == ".worktrees" or pth.startswith(".worktrees/") or pth in self_written:
                        excused.append(pth)
                    else:
                        dirty_lines.append(l)
                clean = len(dirty_lines) == 0
                c.passed = clean
                if clean:
                    c.details = "Working tree clean"
                    if excused:
                        c.details += f" (excluding {len(excused)} evaluator-written/worktree path(s): {', '.join(sorted(excused)[:4])})"
                else:
                    named = ", ".join(_path(l) for l in dirty_lines[:5])
                    c.details = f"Dirty files: {len(dirty_lines)} files — {named}"
            elif c.criterion_type == "artifact":
                art_py = self._artifacts_py()
                tasks = self.artifacts_dir / "tasks.jsonl"
                if art_py is None:
                    c.passed = False
                    c.details = "artifacts.py not found — cannot validate; drop this criterion or install the skill scripts"
                elif not tasks.is_file():
                    # `tasks validate` reports "ok: 0 tasks" on an absent file. Passing on an
                    # empty set would let this criterion be satisfied by having no artifacts.
                    c.passed = False
                    c.details = f"{tasks.relative_to(self.repo_root)} does not exist — nothing to validate"
                else:
                    res = subprocess.run([sys.executable, str(art_py), "tasks", "validate", "--root", str(self.repo_root)],
                                         cwd=self.repo_root, capture_output=True, text=True)
                    c.passed = (res.returncode == 0)
                    why = ((res.stderr or res.stdout).strip().splitlines() or ["validate failed"])[-1]
                    c.details = "Task artifacts validate" if c.passed else why
            elif c.criterion_type == "non_empty":
                if not c.target_path:
                    c.passed = False
                    c.details = "non_empty criterion has no target_path — nothing to measure"
                else:
                    target = self.repo_root / c.target_path
                    c.passed = target.exists() and target.is_file() and target.stat().st_size > 0
                    c.details = f"Size: {target.stat().st_size} bytes" if target.exists() else "File missing"
            elif c.criterion_type in ("test", "invariant"):
                # reached only when the command is missing: the branches above require one
                c.passed = False
                c.details = f"{c.criterion_type} criterion has no command — nothing was run"
            else:
                # Fail closed. A typo'd or unimplemented type must never satisfy a goal:
                # this branch used to report PASSED, which made "invariant" (the default
                # type for every caller-supplied criterion) unfalsifiable.
                c.passed = False
                c.details = f"unknown criterion_type {c.criterion_type!r}; expected one of {', '.join(sorted(CRITERION_TYPES))}"

            status_sym = "\033[92m[PASSED]\033[0m" if c.passed else "\033[91m[FAILED]\033[0m"
            print(f"  {status_sym} {c.id}: {c.description} ({c.details})")
            if not c.passed:
                all_passed = False

        if all_passed:
            self.goal.status = "COMPLETED"
            self.goal.completed_at = datetime.now().isoformat()
            print("\n\033[92m==> STOPPING CONDITION SATISFIED! Goal is COMPLETE.\033[0m")
        else:
            self.goal.status = "IN_PROGRESS"
            print("\n\033[93m==> Stopping condition NOT met. Dev loop iteration must continue.\033[0m")

        self.save()
        self._sync_goals_md()
        return all_passed

    def status(self):
        if not self.goal:
            print("[INFO] No active goal. Initialize with 'goal.py init <objective>'.")
            return
        print(f"Goal Objective: {self.goal.objective}")
        print(f"Status:         {self.goal.status}")
        print(f"Stopping Invariant: {self.goal.stopping_condition}")
        print(f"Criteria Count: {len(self.goal.criteria)}")
        for c in self.goal.criteria:
            sym = "[x]" if c.passed else "[ ]"
            print(f"  {sym} {c.id}: {c.description} ({c.details or 'pending'})")


def main():
    parser = argparse.ArgumentParser(description="Dev Loop Goal Engine")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    init_p = subparsers.add_parser("init", help="Initialize a goal with stopping invariants")
    init_p.add_argument("objective", help="High-level engineering goal")
    init_p.add_argument("--stop", required=True, help="Testable stopping condition command")
    init_p.add_argument("--non-goals", nargs="*", help="Explicit non-goal boundaries")

    eval_p = subparsers.add_parser("eval", help="Evaluate goal stopping criteria")
    status_p = subparsers.add_parser("status", help="Show current goal status")

    args = parser.parse_args()
    engine = GoalEngine()

    if args.cmd == "init":
        engine.init_goal(args.objective, args.stop, non_goals=args.non_goals)
    elif args.cmd == "eval":
        success = engine.evaluate()
        sys.exit(0 if success else 1)
    elif args.cmd == "status":
        engine.status()


if __name__ == "__main__":
    main()
