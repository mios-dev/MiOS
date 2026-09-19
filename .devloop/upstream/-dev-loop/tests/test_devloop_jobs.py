#!/usr/bin/env python3
"""
Controls for devloop.sh's job-backed lane dispatch.

What changed and why
--------------------
Lanes used to be launched three ways, each broken differently:

  headless   `sh -c "$CMD"`                 SEQUENTIAL — one lane at a time
  detached   `( cd "$WTA" && sh -c "$CMD" ) &`  concurrent, but a plain `&` child is still a
                                            CHILD: it dies when the shell's session ends,
                                            which is the turn boundary that has killed lane
                                            trees here before
  tmux_grid  a pane per lane                concurrent, but tied to tmux

and every one of them was waited on by:

  while [ ! -f "$RUN/worker-$ID.exit" ]; do sleep 20; done

which has no budget and no liveness check. A lane that died hard hung the orchestrator forever
waiting for a receipt that would never be written — silence that looks exactly like work.

Detached lanes are now spawned through job.py: setsid, stdin closed, an orphan by construction,
and completion is a receipt the SHELL writes. wait_lane blocks on that receipt with a budget,
and distinguishes `lost` from `running` so a dead lane fails instead of hanging.

These controls run devloop.sh's real functions against trivial commands — no agent, no network.

Run: python3 tests/test_devloop_jobs.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "dev-loop" / "scripts"
DEVLOOP = SCRIPTS / "devloop.sh"
JOB = SCRIPTS / "job.py"
sys.path.insert(0, str(SCRIPTS))

import job  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def test_detached_lanes_are_jobs_not_background_children() -> None:
    """The source-level claim: the detached branch must not use a bare `&`."""
    print("dispatch shape:")
    src = DEVLOOP.read_text()
    check("detached branch spawns through job.py", "$JOB_PY\" spawn --root \"$JOBS\"" in src)
    check("the old bare-& detached launch is gone",
          '( cd "$WTA" && sh -c "$CMD" ) >/dev/null 2>&1 &' not in src,
          "a plain background child still dies with the shell's session")
    check("wait_lane has a budget", "LANE_WAIT_BUDGET" in src,
          "the old loop waited forever for a receipt that might never come")
    check("wait_lane treats lost/forged as failure", "lost|forged" in src)
    check("headless stays sequential on purpose", "SEQUENTIAL by design" in src)
    check("the concurrency cap is stated as provisional", "provisional" in src,
          "no measurement here establishes a number; saying so is the honest form")


def test_jobs_run_concurrently() -> None:
    """POSITIVE CONTROL for the fan-out: three one-second jobs must overlap, not queue.

    If they ran sequentially the wall clock would be ~3s; concurrent it is ~1s. The assertion
    is deliberately loose (< 2.5s) so it measures overlap, not machine speed."""
    print("fan-out is concurrent:")
    root = Path(tempfile.mkdtemp(prefix="jobs-conc-"))
    t0 = time.time()
    for i in range(3):
        job.spawn(root, f"lane{i}", ["sh", "-c", "sleep 1"], Path("."), budget_s=30)
    spawn_elapsed = time.time() - t0
    check("spawning 3 jobs returns immediately", spawn_elapsed < 1.0,
          f"took {spawn_elapsed:.2f}s — spawn must not block")

    res = job.wait(root, [f"lane{i}" for i in range(3)], budget_s=30, interval_s=1)
    total = time.time() - t0
    check("all three completed", all(r["state"] == "done" and r["rc"] == 0 for r in res.values()),
          str({k: (v["state"], v["rc"]) for k, v in res.items()}))
    check("they overlapped rather than queued", total < 2.5,
          f"{total:.2f}s for 3x1s jobs — sequential would be ~3s")


def test_a_dead_lane_fails_instead_of_hanging() -> None:
    """THE control that matters. Kill a lane's wrapper so no receipt is ever written, then
    require the wait to TERMINATE with a failure rather than block forever.

    The old `while [ ! -f .exit ]; do sleep 20; done` would still be looping."""
    print("a lane that dies hard:")
    root = Path(tempfile.mkdtemp(prefix="jobs-dead-"))
    job.spawn(root, "doomed", ["sh", "-c", "sleep 300"], Path("."), budget_s=600)

    end = time.time() + 15
    s = job.status(root, "doomed")
    while s["pid"] is None and time.time() < end:
        time.sleep(0.2)
        s = job.status(root, "doomed")
    if not s["pid"]:
        check("lane started", False, "never got a pid")
        return
    os.kill(s["pid"], 9)

    t0 = time.time()
    res = job.wait(root, ["doomed"], budget_s=30, interval_s=1)
    elapsed = time.time() - t0
    check("wait TERMINATED instead of hanging", elapsed < 25, f"{elapsed:.1f}s")
    check("state is lost, not running", res["doomed"]["state"] == "lost", str(res["doomed"]))
    check("no exit code is invented", res["doomed"]["rc"] is None)

    cp = subprocess.run([sys.executable, str(JOB), "wait", "--root", str(root),
                         "--id", "doomed", "--budget", "5", "--interval", "1"],
                        capture_output=True, text=True, timeout=60)
    check("CLI exits 3 so the orchestrator can act", cp.returncode == 3, f"rc={cp.returncode}")
    job.kill(root, "doomed", "KILL")


def test_partial_completion_is_visible() -> None:
    """A wave where one lane succeeds and one fails must report BOTH, not collapse to a single
    verdict — partial completion is the normal case and hiding it is how a half-done run reads
    as done."""
    print("partial completion:")
    root = Path(tempfile.mkdtemp(prefix="jobs-partial-"))
    job.spawn(root, "good", ["sh", "-c", "exit 0"], Path("."), budget_s=30)
    job.spawn(root, "bad", ["sh", "-c", "exit 9"], Path("."), budget_s=30)
    res = job.wait(root, ["good", "bad"], budget_s=30, interval_s=1)
    check("the good lane is done rc=0", res["good"]["state"] == "done" and res["good"]["rc"] == 0)
    check("the bad lane is done rc=9", res["bad"]["state"] == "done" and res["bad"]["rc"] == 9,
          "a failing lane must report its real code, not be flattened")

    cp = subprocess.run([sys.executable, str(JOB), "wait", "--root", str(root),
                         "--id", "good", "--id", "bad", "--budget", "5", "--interval", "1"],
                        capture_output=True, text=True, timeout=60)
    check("CLI exits 2 when any lane failed", cp.returncode == 2, f"rc={cp.returncode}")


def test_budget_expiry_does_not_read_as_success() -> None:
    """Timeout-as-Pass, at the wave level: a wait whose budget expires while a lane is still
    running must NOT report success."""
    print("wait budget expiring mid-flight:")
    root = Path(tempfile.mkdtemp(prefix="jobs-budget-"))
    job.spawn(root, "slow", ["sh", "-c", "sleep 20"], Path("."), budget_s=60)
    res = job.wait(root, ["slow"], budget_s=2, interval_s=1)
    check("returns while the lane is still running", res["slow"]["state"] == "running",
          str(res["slow"]))
    check("no rc is invented for an unfinished lane", res["slow"]["rc"] is None)

    cp = subprocess.run([sys.executable, str(JOB), "wait", "--root", str(root),
                         "--id", "slow", "--budget", "2", "--interval", "1"],
                        capture_output=True, text=True, timeout=60)
    check("CLI exits non-zero on an unfinished lane", cp.returncode != 0, f"rc={cp.returncode}")
    job.kill(root, "slow", "KILL")


# ---------------------------------------------------------------------------------------------
# End-to-end controls for devloop.sh itself. Fault is injected at the PROCESS boundary via the
# PYTHON env var (devloop.sh runs every helper as `$PY <script> …`), the same technique the poll
# tests use for a fake `agy`: it exercises the real shell script rather than a re-implementation.
# ---------------------------------------------------------------------------------------------

LANES_JSON = """{"base_ref":"HEAD","lanes":[{"id":"l1",
"objective":"a minimal lane used only to drive devloop.sh's dispatch and wait paths",
"owned_paths":["a.txt"],"worker":{"harness":"claude-code"},
"positive_cmd":"true","negative_control_cmd":"false","negative_expect":"boom",
"full_gate_cmd":"true"}]}"""


def _repo(lanes_json: str = "") -> Path:
    """A clean one-commit git repo — devloop.sh refuses to run on a dirty tree, so lanes.json
    and the shim live in the parent directory, OUTSIDE the worktree. (Keeping them inside made
    every run refuse on a dirty tree, which still satisfied a bare `rc != 0` assertion: the
    reason the message checks below assert WHICH failure happened.)"""
    d = Path(tempfile.mkdtemp(prefix="devloop-repo-"))
    repo = d / "repo"
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    (repo / "a.txt").write_text("seed\n")
    subprocess.run(["git", "-C", str(repo), "add", "a.txt"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "seed"], check=True, env=env)
    (d / "lanes.json").write_text(lanes_json or LANES_JSON)
    return repo


def _shim(repo: Path, body: str) -> str:
    """A `python3` stand-in that fails one helper subcommand and passes everything else."""
    sh = repo.parent / "pyshim.sh"
    sh.write_text("#!/bin/sh\n" + body + '\nexec python3 "$@"\n')
    sh.chmod(0o755)
    return str(sh)


def _run_devloop(repo: Path, pyshim: str, timeout: int = 180):
    lanes = repo.parent / "lanes.json"
    env = {**os.environ, "PYTHON": pyshim, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "LANE_WAIT_BUDGET": "40"}
    return subprocess.run(["sh", str(DEVLOOP), str(lanes), "--layout", "detached"],
                          cwd=repo, capture_output=True, text=True, timeout=timeout, env=env)


def test_zero_waves_is_not_success() -> None:
    """EMPTY-SET PASS. The wave loop used to be `waves | while read`, so the body ran in a
    subshell and zero iterations left `$RUN/status` unwritten — which the parent then read as
    STATUS=0. A run in which NO LANE RAN AT ALL exited 0 and reported success.

    Fault injection: make `adapters.py waves` print nothing and exit 0."""
    print("a run that dispatches nothing:")
    repo = _repo()
    shim = _shim(repo, 'case "$1" in */adapters.py) case "$2" in waves) exit 0;; esac;; esac')
    cp = _run_devloop(repo, shim)
    check("exit is NOT 0", cp.returncode != 0,
          f"rc={cp.returncode} — zero lanes dispatched must never read as a successful run")
    check("and not for an unrelated reason", "base tree is dirty" not in (cp.stdout + cp.stderr))
    check("it says no waves", "no waves" in (cp.stdout + cp.stderr).lower(),
          (cp.stdout + cp.stderr)[-300:])
    check("no lane job directory was created",
          not list(repo.glob(".devloop/run-*/jobs/*")),
          "a run that reported success would also have had to start something")


def test_waves_crashing_is_not_success() -> None:
    """The same pipeline also swallowed a NON-ZERO producer: a pipeline's status is its last
    command's, so `waves` crashing left `set -e` unmoved and the run exited 0."""
    print("the wave planner crashing:")
    repo = _repo()
    shim = _shim(repo, 'case "$1" in */adapters.py) case "$2" in waves) exit 9;; esac;; esac')
    cp = _run_devloop(repo, shim)
    check("exit is NOT 0", cp.returncode != 0, f"rc={cp.returncode}")
    check("the failure is named", "waves failed" in (cp.stdout + cp.stderr),
          (cp.stdout + cp.stderr)[-300:])


def test_a_failed_spawn_is_not_swallowed() -> None:
    """`job.py spawn … || true` hid a spawn that never started. With no job directory,
    wait_lane fell through to the pre-job `while [ ! -f .exit ]; do sleep 20; done` — the
    unbounded hang job.py exists to remove. The lane must fail loudly and promptly instead."""
    print("a spawn that fails:")
    repo = _repo()
    shim = _shim(repo, 'case "$1" in */job.py) case "$2" in spawn) exit 1;; esac;; esac')
    t0 = time.time()
    cp = _run_devloop(repo, shim)
    elapsed = time.time() - t0
    out = cp.stdout + cp.stderr
    check("SPAWN FAILED is reported", "SPAWN FAILED" in out, out[-400:])
    check("exit is NOT 0", cp.returncode != 0, f"rc={cp.returncode}")
    check("it did not fall into the unbounded wait", elapsed < 40,
          f"{elapsed:.0f}s — the old path slept in 20s steps until LANE_WAIT_BUDGET")


def test_budget_guard_fires_on_a_missing_timeout() -> None:
    """The guard `$(field … || echo 1800)` could never fire: field() prints "" and exits 0 for a
    missing key, so `--budget ""` would reach job.py, which rejects it — turning a missing field
    into the swallowed spawn failure above. The guard must test the VALUE."""
    print("budget guard:")
    src = DEVLOOP.read_text()
    check("the dead `|| echo 1800` guard is gone",
          'field "$LJ" worker.timeout_s || echo 1800' not in src)
    check("the budget is validated as a value", 'case "$BUDGET" in' in src)
    cp = subprocess.run([sys.executable, str(JOB), "spawn", "--root", "/tmp", "--id", "x",
                         "--budget", "", "--", "true"], capture_output=True, text=True)
    check("an empty budget really is rejected by job.py", cp.returncode != 0,
          "if job.py accepted it, the guard above would be theatre")


# A lane whose own job budget (worker.timeout_s, floor 30) is far shorter than its worker.
SLOW_LANE_JSON = """{"base_ref":"HEAD","lanes":[{"id":"l1",
"objective":"a lane whose worker outruns its own job budget, reaching job.py wait's exit 2",
"owned_paths":["a.txt"],"worker":{"harness":"claude-code","timeout_s":30},
"positive_cmd":"true","negative_control_cmd":"false","negative_expect":"boom",
"full_gate_cmd":"true"}]}"""


def test_a_lane_that_outruns_its_budget_does_not_kill_the_orchestrator() -> None:
    """THE fatal one. `job.py wait` was called unguarded under `set -eu`, and wait exits 2 when
    a lane is not done-rc-0 (3 when lost). A lane that hit its own job timeout therefore killed
    devloop.sh AT THE WAIT: no gate ran, no $RUN/status was written, no ledger entry, and the
    process exited 2 -- which in this script's contract means 'VACUOUS lane', so the one run
    that most needed an honest report produced a misleading one.

    Measured against the pre-fix file: output stopped after the job status line and rc was 2.

    The lane here sleeps 300s with a 30s job budget, so the wrapper's `timeout` fires and the
    receipt is rc=124 -- a real receipt, not an invented code."""
    print("a lane that outruns its job budget:")
    repo = _repo(SLOW_LANE_JSON)
    shim = _shim(repo, 'case "$1" in */adapters.py) case "$2" in run) sleep 300; exit 0;; esac;; esac')
    cp = _run_devloop(repo, shim, timeout=300)
    out = cp.stdout + cp.stderr
    check("the wait did not abort the run", "== gate l1" in out,
          "the orchestrator never reached the gate — set -e killed it at the wait")
    check("the lane's real receipt is reported", "worker exit=124" in out, out[-400:])
    check("run artefacts were still written", "run artefacts:" in out)
    check("exit is 1 (lane failed), not 2 (vacuous)", cp.returncode == 1,
          f"rc={cp.returncode} — exit 2 here would misreport an orchestrator abort as a vacuous lane")
    check("the status file exists", list(repo.glob(".devloop/run-*/status")),
          "written only if the wave loop completed")


def test_the_wave_waits_on_one_deadline_not_n() -> None:
    """Waiting lane-by-lane started each wait only after the previous returned, so N lanes could
    consume N x LANE_WAIT_BUDGET. job.py wait already takes repeated --id under one deadline."""
    print("wave budget:")
    src = DEVLOOP.read_text()
    check("the per-lane wait loop is gone", "for id in $WAVE; do wait_lane" not in src)
    check("the wave is waited on as a set", "wait_wave $WAVE" in src)
    check("the wait's non-zero exit is swallowed deliberately",
          '--interval 20 || :' in src,
          "a non-zero wait is this code's normal reporting channel, not an error")
    root = Path(tempfile.mkdtemp(prefix="jobs-deadline-"))
    for i in range(3):
        job.spawn(root, f"w{i}", ["sh", "-c", "sleep 30"], Path("."), budget_s=60)
    t0 = time.time()
    job.wait(root, [f"w{i}" for i in range(3)], budget_s=4, interval_s=1)
    elapsed = time.time() - t0
    check("one budget covers the whole set", elapsed < 8,
          f"{elapsed:.1f}s for a 4s budget over 3 lanes — per-lane budgets would take ~12s")
    for i in range(3):
        job.kill(root, f"w{i}", "KILL")


def main() -> int:
    for t in (test_detached_lanes_are_jobs_not_background_children,
              test_jobs_run_concurrently,
              test_a_dead_lane_fails_instead_of_hanging,
              test_partial_completion_is_visible,
              test_budget_expiry_does_not_read_as_success,
              test_zero_waves_is_not_success,
              test_waves_crashing_is_not_success,
              test_a_failed_spawn_is_not_swallowed,
              test_budget_guard_fires_on_a_missing_timeout,
              test_a_lane_that_outruns_its_budget_does_not_kill_the_orchestrator,
              test_the_wave_waits_on_one_deadline_not_n):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all devloop-job controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
