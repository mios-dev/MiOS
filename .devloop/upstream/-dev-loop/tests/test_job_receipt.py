#!/usr/bin/env python3
"""
Controls for job.py — work that survives a turn boundary.

What this primitive claims, and therefore what must be falsifiable
------------------------------------------------------------------
1. A job outlives the shell that spawned it. (If not, it is just a background command and the
   turn boundary still kills it.)
2. Completion is an artefact the SHELL wrote, never a sentence a model said. The existing poll
   loop fails this: its predicate is `is_file()` over a report the polled AGENT is asked to
   create, so the thing being measured is written by the thing being measured.
3. Absence of a receipt is NOT success. A hard-killed job must read `lost`, never `done` —
   silence looking like success is the whole defect family this skill exists for.
4. A receipt the wrapper did not write must be detected as `forged`.

Every case below is either a claim or its refutation. The negatives are the point: a job system
that cannot report `lost` and `forged` is a progress bar, not a verification mechanism.

Run: python3 tests/test_job_receipt.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOB = ROOT / "skills" / "dev-loop" / "scripts" / "job.py"
sys.path.insert(0, str(JOB.parent))

import job  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}{': ' + detail if detail else ''}")
        FAILURES.append(name)


def newroot() -> Path:
    return Path(tempfile.mkdtemp(prefix="jobs-"))


def wait_state(root: Path, jid: str, want: set[str], timeout_s: float = 30) -> dict:
    end = time.time() + timeout_s
    s = job.status(root, jid)
    while s["state"] not in want and time.time() < end:
        time.sleep(0.3)
        s = job.status(root, jid)
    return s


def test_outlives_its_spawner() -> None:
    """THE central claim. Spawn from a subprocess that exits immediately — the same shape as a
    turn ending — and require the work to keep running and finish."""
    print("a job outlives the shell that spawned it:")
    root = newroot()
    marker = root / "proof.txt"
    # spawn via a short-lived child python, which then exits, mimicking a turn boundary
    cp = subprocess.run(
        [sys.executable, str(JOB), "spawn", "--root", str(root), "--id", "outlive",
         "--budget", "60", "--", "sh", "-c", f"sleep 4; echo LIVED > {marker}"],
        capture_output=True, text=True, timeout=30)
    check("spawn returns immediately", cp.returncode == 0 and "spawned" in cp.stdout, cp.stderr[-200:])

    s = job.status(root, "outlive")
    check("job is running after its spawner exited", s["state"] == "running", str(s))

    pid = s["pid"]
    ppid = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1] if pid else "?"
    check("reparented to init (PPID 1) — an orphan by construction", ppid == "1", f"ppid={ppid}")

    s = wait_state(root, "outlive", {"done", "lost", "forged"})
    check("reaches done", s["state"] == "done", str(s))
    check("receipt rc is 0", s["rc"] == 0, str(s["rc"]))
    check("the side effect actually happened", marker.is_file() and "LIVED" in marker.read_text(),
          "a receipt without the work is worse than no receipt")


def test_absence_of_receipt_is_lost_not_done() -> None:
    """NEGATIVE CONTROL, and the one that matters most. Hard-kill the wrapper so no receipt is
    written. The job must read `lost`. If a missing receipt read as done — or as running
    forever — this primitive would reproduce the exact failure it exists to prevent."""
    print("a hard-killed job is lost, never done:")
    root = newroot()
    job.spawn(root, "killed", ["sh", "-c", "sleep 30"], Path("."), budget_s=60)
    # status() reports `running` during its grace window BEFORE the wrapper has written its pid
    # file, so polling on state alone races the spawn. Wait for a real pid.
    end = time.time() + 15
    s = job.status(root, "killed")
    while s["pid"] is None and time.time() < end:
        time.sleep(0.2)
        s = job.status(root, "killed")
    check("running with a real pid before the kill",
          s["state"] == "running" and s["pid"], str(s))
    if not s["pid"]:
        return

    pid = s["pid"]
    os.kill(pid, 9)                       # SIGKILL: no trap, therefore no receipt
    # Poll rather than sleep a fixed amount: /proc/<pid> lingers as a zombie until init reaps,
    # so a fixed sleep races that window. job.py treats a zombie as not-running, so this should
    # settle almost immediately -- but the test must not depend on how fast init is.
    s = wait_state(root, "killed", {"lost", "done", "forged"}, 15)
    check("state is lost", s["state"] == "lost", f"got {s['state']} — silence must not read as success")
    check("no rc is invented", s["rc"] is None, str(s["rc"]))
    check("no receipt file exists", not (root / "killed" / "exit").is_file())

    cp = subprocess.run([sys.executable, str(JOB), "status", "--root", str(root), "--id", "killed"],
                        capture_output=True, text=True)
    check("CLI exits 3 on lost", cp.returncode == 3, f"rc={cp.returncode}")
    job.kill(root, "killed", "KILL")      # reap any survivors


def test_forged_receipt_is_detected() -> None:
    """NEGATIVE CONTROL for claim 2. Write a receipt by hand, as an agent could. The ordering
    contract — done.json renamed before exit — is what makes this detectable."""
    print("a receipt the wrapper did not write is forged:")
    root = newroot()
    d = root / "forged"
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"id": "forged", "spawned_at": job._now()}))
    (d / "exit").write_text("0\n")        # the claim, with no done.json behind it
    s = job.status(root, "forged")
    check("receipt without done.json is forged", s["state"] == "forged", str(s))

    # a receipt that disagrees with done.json is also forged
    (d / "done.json").write_text(json.dumps({"rc": 1, "finished_at": job._now()}))
    s = job.status(root, "forged")
    check("receipt disagreeing with done.json is forged", s["state"] == "forged", str(s))

    # and the honest pair is accepted, or the check above proves nothing
    (d / "done.json").write_text(json.dumps({"rc": 0, "finished_at": job._now()}))
    s = job.status(root, "forged")
    check("a consistent pair IS accepted", s["state"] == "done" and s["rc"] == 0, str(s))


def test_runaway_still_yields_a_receipt() -> None:
    """A job that exceeds its budget must still produce a receipt — Timeout-as-Pass inverted:
    the timeout must be visible, not silent."""
    print("a runaway job is killed and still reports:")
    root = newroot()
    job.spawn(root, "runaway", ["sh", "-c", "sleep 60"], Path("."), budget_s=2)
    s = wait_state(root, "runaway", {"done", "lost", "forged"}, 40)
    check("reaches done (not lost)", s["state"] == "done", str(s))
    check("rc is the timeout code 124", s["rc"] == 124, f"rc={s['rc']}")


def test_failure_is_reported_as_failure() -> None:
    print("a failing job reports its real exit code:")
    root = newroot()
    job.spawn(root, "fails", ["sh", "-c", "exit 7"], Path("."), budget_s=30)
    s = wait_state(root, "fails", {"done", "lost", "forged"})
    check("done with rc=7", s["state"] == "done" and s["rc"] == 7, str(s))

    cp = subprocess.run([sys.executable, str(JOB), "wait", "--root", str(root), "--id", "fails",
                         "--budget", "10", "--interval", "1"], capture_output=True, text=True)
    check("wait exits 2 for a failed job", cp.returncode == 2, f"rc={cp.returncode}")

    try:
        job.require(root, "fails")
        check("require raises on a non-zero rc", False, "it returned instead")
    except SystemExit as e:
        check("require raises on a non-zero rc", "rc=7" in str(e), str(e))


def test_wait_blocks_until_terminal() -> None:
    """`wait` is what replaces 'I will wait for the background command to finish' — a real
    wait, in a process the model does not control, over a receipt it did not write."""
    print("wait blocks until the job is terminal:")
    root = newroot()
    t0 = time.time()
    job.spawn(root, "slow", ["sh", "-c", "sleep 4"], Path("."), budget_s=30)
    res = job.wait(root, ["slow"], budget_s=30, interval_s=1)
    elapsed = time.time() - t0
    check("returned only after the job finished", elapsed >= 3.5, f"returned after {elapsed:.1f}s")
    check("reports done rc=0", res["slow"]["state"] == "done" and res["slow"]["rc"] == 0, str(res))


def test_absent_job_is_absent() -> None:
    """Empty-Set Pass guard: asking about a job that was never spawned must not read as done."""
    print("a job that never existed:")
    root = newroot()
    s = job.status(root, "nope")
    check("state is absent", s["state"] == "absent", str(s))
    check("no rc", s["rc"] is None)


def test_a_receipt_does_not_outrank_liveness() -> None:
    """THE self-certification hole, closed. status() checked `exit` BEFORE the process, so a
    lane that wrote a consistent exit + done.json pair while still running read as `done` —
    it could end its own wait, and devloop.sh would then audit, stage and merge a worktree the
    agent was still writing to. Two files were all it took.

    A live process holding a receipt is premature, not finished."""
    print("a receipt planted while the job is still running:")
    root = newroot()
    job.spawn(root, "premature", ["sh", "-c", "sleep 60"], Path("."), budget_s=120)
    end = time.time() + 15
    s = job.status(root, "premature")
    while s["pid"] is None and time.time() < end:
        time.sleep(0.2)
        s = job.status(root, "premature")
    if not s["pid"]:
        check("job started", False, "never got a pid")
        return

    d = root / "premature"
    (d / "done.json").write_text(json.dumps({"rc": 0, "finished_at": job._now()}))
    (d / "exit").write_text("0\n")
    s = job.status(root, "premature")
    check("still running, not done", s["state"] == "running",
          f"got {s['state']} — a running lane must not be able to declare itself finished")
    check("no rc is taken from the planted receipt", s["rc"] is None, str(s["rc"]))

    # And the honest case must still resolve, or the check above is just a broken reader.
    # Signal the SESSION, the way kill()/reap_lane do -- TERM to the wrapper alone fires its
    # trap (which writes a receipt) but leaves `timeout` still waiting on the real command, so
    # the wrapper stays alive holding a receipt. Under the new rule that reads `running`, which
    # is the correct answer: the work has not stopped.
    job.kill(root, "premature", "TERM")
    s = wait_state(root, "premature", {"done", "lost", "forged"}, 30)
    check("once the process is gone the receipt is read", s["state"] in ("done", "lost"),
          str(s))
    job.kill(root, "premature", "KILL")


def test_the_wrapper_stamps_its_own_pid() -> None:
    """Second term: the wrapper writes its pid into done.json, so a receipt left behind by
    something other than the process that ran the work is detectable even after it exits."""
    print("receipt provenance:")
    root = newroot()
    job.spawn(root, "stamped", ["sh", "-c", "exit 0"], Path("."), budget_s=30)
    s = wait_state(root, "stamped", {"done", "lost", "forged"})
    check("an honest job is done", s["state"] == "done", str(s))
    d = root / "stamped"
    done = json.loads((d / "done.json").read_text())
    check("done.json carries a pid", isinstance(done.get("pid"), int), str(done))
    check("it matches the pid file", str(done.get("pid")) == (d / "pid").read_text().strip(),
          f"done.json pid={done.get('pid')} pid file={(d / 'pid').read_text().strip()}")

    done["pid"] = done["pid"] + 1
    (d / "done.json").write_text(json.dumps(done))
    check("a mismatched pid is forged", job.status(root, "stamped")["state"] == "forged",
          "a receipt from another process must not be accepted")


def main() -> int:
    for t in (test_outlives_its_spawner, test_absence_of_receipt_is_lost_not_done,
              test_forged_receipt_is_detected, test_runaway_still_yields_a_receipt,
              test_failure_is_reported_as_failure, test_wait_blocks_until_terminal,
              test_absent_job_is_absent,
              test_a_receipt_does_not_outrank_liveness,
              test_the_wrapper_stamps_its_own_pid):
        t()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all job-receipt controls passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
