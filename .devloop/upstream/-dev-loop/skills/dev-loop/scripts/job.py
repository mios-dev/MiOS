#!/usr/bin/env python3
"""
job.py — work that survives a turn boundary.

The problem, stated once
------------------------
Every agent harness is TURN-BASED. A turn ends and unfinished work dies with it, and the agent
inside the turn cannot observe its own death — so it reports having started work and treats that
as completion. This repo has hit that four times at three altitudes: a manager that dispatched
lanes and ended its turn "waiting"; a manager that backgrounded devloop.sh and killed the whole
lane tree with itself; a lane worker that announced three times it would wait for a background
command and measured nothing; and a report claiming success for a lane the orchestrator had
recorded as partial.

Measured on the installed harnesses: on the graceful path both reap their children (`agy -p`
prints "terminating N background task(s) on exit"; `claude -p` stops background shells ~5s after
its final result). On the hard-kill path both LEAK — the child reparents to PID 1 and keeps
running. Neither is recoverable from inside the turn.

The fix already existed here on exactly one path: devloop.sh:49 appends `; echo $? > worker.exit`
and devloop.sh:58 blocks on that file. The receipt is written by the SHELL, not spoken by the
model. This generalises that to every unit of work.

The idea
--------
**The work is never a child of the turn, and completion is an artefact the shell writes, never a
sentence the model says.**

`spawn` writes a job directory, launches a `setsid` wrapper with stdin closed, and returns in
milliseconds. Because the spawner exits immediately the harness never registers a background
task at all — there is nothing for agy's reaper or claude's background-shell stop to find. The
work is an orphan by construction. The wrapper's EXIT trap writes the receipt.

Measured facts this design rests on (this box, 2026-09-19):
  * a setsid child runs with PPID 1 and outlives the shell that spawned it;
  * `timeout` inside the wrapper still yields a receipt (rc 124) for a runaway job;
  * SIGKILL of the wrapper leaves NO receipt and live grandchildren — the `lost` state, which
    is why liveness is checked and not assumed;
  * **kill by session id, never by process group**: after a wrapper died, `kill -- -<pid>`
    reported "No such process" while three descendants were alive, because `timeout` had put
    them in a NEW process group that still shared the session id.

Ordering is the whole contract: `done.json` is renamed into place BEFORE `exit` is, so the
existence of `exit` implies every other artefact is complete. Both are tmp+rename on one
filesystem, so a reader never sees a partial receipt.

States: absent | running | done | lost | forged
  lost   — no receipt and the pid is gone (hard-killed, or the box rebooted)
  forged — a receipt exists that the wrapper did not write, or pid reuse was detected

Exit codes: 0 ok · 1 usage/spawn error · 2 job failed or is not done · 3 lost/forged
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = 1

_DETACHED_PROCS: list[subprocess.Popen] = []


def poll_detached() -> None:
    """Poll detached process handles to release zombie resources and silence ResourceWarnings."""
    for p in _DETACHED_PROCS:
        try:
            p.poll()
        except Exception:
            pass


atexit.register(poll_detached)

# The wrapper is deliberately /bin/sh and deliberately tiny: it must not be able to fail in
# interesting ways. It records its own pid and start-tick (for a pid-reuse guard), runs the
# command under a budget, then writes done.json and the receipt IN THAT ORDER.
WRAPPER = r"""#!/bin/sh
d=$1
echo $$ > "$d/pid"
awk '{print $22}' /proc/$$/stat 2>/dev/null > "$d/pidstart" || :
cmd=$(cat "$d/cmd"); cwd=$(cat "$d/cwd"); budget=$(cat "$d/budget")
finish() {
  rc=$1
  printf '{"rc":%s,"finished_at":%s,"pid":%s}\n' "$rc" "$(date +%s)" "$$" > "$d/done.json.tmp"
  mv "$d/done.json.tmp" "$d/done.json"
  printf '%s\n' "$rc" > "$d/exit.tmp"
  mv "$d/exit.tmp" "$d/exit"
}
trap 'finish 143' TERM
trap 'finish 130' INT
cd "$cwd" 2>/dev/null || { finish 125; exit 125; }
timeout -k 10 "$budget" sh -c "$cmd" > "$d/out" 2> "$d/err"
finish $?
"""


def _now() -> int:
    return int(time.time())


def _read(p: Path, default: str = "") -> str:
    try:
        return p.read_text().strip()
    except OSError:
        return default


def _alive(pid: int, pidstart: str) -> bool:
    """Is this exact process still running? The start-tick guard stops a recycled pid from
    reading as our job — a stale pid file plus pid reuse would otherwise report `running`
    forever."""
    if pid <= 0:
        return False
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    try:
        fields = stat.rsplit(")", 1)[1].split()
    except IndexError:
        return True
    # A ZOMBIE IS NOT RUNNING. /proc/<pid> survives a SIGKILL until the parent reaps, measured
    # here at ~1.2s with init as the parent -- and longer on a loaded box. Without this a
    # hard-killed job reads `running` for that whole window, which is the exact confusion this
    # primitive exists to remove: a dead thing that looks busy.
    if fields and fields[0] == "Z":
        return False
    if not pidstart:
        return True
    try:
        return fields[19] == pidstart
    except (IndexError, ValueError):
        return True


def _session_pids(sid: int) -> list[int]:
    """Every pid in this session. Kill by SID, never by PGID: `timeout` moves its child into a
    new process group that still shares the session, so a pgid kill misses it (measured)."""
    out = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            fields = (d / "stat").read_text().rsplit(")", 1)[1].split()
            if int(fields[3]) == sid:
                out.append(int(d.name))
        except (OSError, IndexError, ValueError):
            continue
    return sorted(out)


def spawn(root: Path, jid: str, argv: list[str], cwd: Path, budget_s: int = 3600,
          label: str = "", replay: str = "skip") -> str:
    """Detach `argv` from this turn. Returns spawned | running | done."""
    d = root / jid
    if d.exists():
        st = status(root, jid)["state"]
        if st in ("running", "done"):
            if replay == "fail":
                raise SystemExit(f"job {jid} already exists ({st})")
            if replay == "skip":
                return st
        # replay == "rerun", or the job was lost/forged: start over from a clean directory
        for f in ("exit", "done.json", "pid", "pidstart", "out", "err"):
            (d / f).unlink(missing_ok=True)
    d.mkdir(parents=True, exist_ok=True)

    cmd = " ".join(shlex.quote(a) for a in argv)
    (d / "cmd").write_text(cmd + "\n")
    (d / "cwd").write_text(str(Path(cwd).resolve()) + "\n")
    (d / "budget").write_text(f"{int(budget_s)}\n")
    (d / "meta.json").write_text(json.dumps({
        "id": jid, "label": label, "argv": argv, "cmd": cmd, "cwd": str(Path(cwd).resolve()),
        "budget_s": int(budget_s), "spawner_pid": os.getpid(), "spawned_at": _now(),
        "host": os.uname().nodename, "schema": SCHEMA}, indent=2) + "\n")
    w = d / "wrapper.sh"
    w.write_text(WRAPPER)
    w.chmod(0o755)

    # setsid + closed stdin: the child leads a new session, so nothing the harness reaps on
    # turn end can see it. Returning immediately is the point — this call must not be the
    # long-running thing.
    with open(os.devnull, "rb") as devnull:
        proc = subprocess.Popen(["setsid", "/bin/sh", str(w), str(d.resolve())],
                                stdin=devnull, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=True)
        try:
            proc.wait(timeout=0.2)
        except subprocess.TimeoutExpired:
            proc.poll()
        _DETACHED_PROCS.append(proc)
    return "spawned"


def status(root: Path, jid: str, grace_s: int = 2) -> dict:
    """Derive state from the FILESYSTEM and /proc, never from anything an agent wrote."""
    poll_detached()
    d = root / jid
    meta = {}
    try:
        meta = json.loads((d / "meta.json").read_text())
    except (OSError, json.JSONDecodeError):
        pass
    out = {"id": jid, "state": "absent", "rc": None, "pid": None,
           "started_at": meta.get("spawned_at"), "finished_at": None,
           "label": meta.get("label", ""), "cmd": meta.get("cmd", "")}
    if not d.is_dir():
        return out

    pid = int(_read(d / "pid", "0") or 0)
    out["pid"] = pid or None
    receipt = d / "exit"

    if receipt.is_file():
        # A RECEIPT DOES NOT OUTRANK LIVENESS. status() used to trust `exit` before looking at
        # the process, so a lane that wrote a consistent exit + done.json pair while STILL
        # RUNNING read as `done` -- it could end its own wait and have its worktree gated and
        # merged underneath it, which is precisely the self-certification this primitive exists
        # to remove. The wrapper writes its receipt and exits within milliseconds, so a live
        # process holding a receipt is premature, not finished: report it as running and keep
        # waiting. This costs a poll interval in the honest case and forges nothing.
        if _alive(pid, _read(d / "pidstart")):
            out["state"] = "running"
            return out
        rc_text = _read(receipt)
        done = {}
        try:
            done = json.loads((d / "done.json").read_text())
        except (OSError, json.JSONDecodeError):
            # `exit` exists but done.json does not: the ordering contract was violated, so
            # something other than the wrapper wrote the receipt.
            out["state"] = "forged"
            return out
        try:
            out["rc"] = int(rc_text)
        except ValueError:
            out["state"] = "forged"
            return out
        if done.get("rc") != out["rc"]:
            out["state"] = "forged"
            return out
        # The wrapper stamps its own pid into done.json. A receipt whose pid disagrees with the
        # pid file was not written by the process that ran the work. (Jobs spawned before this
        # field existed have no pid key; those are not judged on it.)
        if done.get("pid") is not None and pid and int(done["pid"]) != pid:
            out["state"] = "forged"
            return out
        out["state"] = "done"
        out["finished_at"] = done.get("finished_at")
        return out

    if _alive(pid, _read(d / "pidstart")):
        out["state"] = "running"
        return out

    # No receipt and no process. Give a just-spawned job a moment to write its pid file before
    # calling it lost — otherwise a healthy spawn races into `lost` on a slow box.
    if not pid and meta.get("spawned_at") and _now() - meta["spawned_at"] <= grace_s:
        out["state"] = "running"
        return out
    out["state"] = "lost"
    return out


def wait(root: Path, jids: list[str], budget_s: int, interval_s: int = 5) -> dict[str, dict]:
    """Block until every job reaches a terminal state or the budget expires.

    This is the call that replaces "I will wait for the background command to finish" — it is a
    real wait, in a process the model does not control, over a receipt the model did not write.
    """
    deadline = time.time() + budget_s
    seen: dict[str, dict] = {}
    while True:
        seen = {j: status(root, j) for j in jids}
        if all(s["state"] in ("done", "lost", "forged") for s in seen.values()):
            return seen
        if time.time() >= deadline:
            return seen
        time.sleep(interval_s)


def require(root: Path, jid: str, expect_rc: int = 0) -> None:
    s = status(root, jid)
    if s["state"] != "done":
        raise SystemExit(f"job {jid}: {s['state']} (expected done)")
    if s["rc"] != expect_rc:
        raise SystemExit(f"job {jid}: rc={s['rc']} (expected {expect_rc})")


def kill(root: Path, jid: str, sig: str = "TERM") -> int:
    """Kill the job's whole session. By SID, never PGID — measured: timeout's child lands in a
    new process group that still shares the session, so a pgid kill silently misses it."""
    d = root / jid
    pid = int(_read(d / "pid", "0") or 0)
    if not pid:
        return 0
    signo = getattr(signal, f"SIG{sig}", signal.SIGTERM)
    n = 0
    for p in _session_pids(pid):
        try:
            os.kill(p, signo)
            n += 1
        except OSError:
            pass
    return n


def gc(root: Path, older_than_s: int) -> list[str]:
    removed = []
    if not root.is_dir():
        return removed
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        s = status(root, d.name)
        if s["state"] == "done" and s.get("finished_at") and _now() - s["finished_at"] > older_than_s:
            for f in d.iterdir():
                f.unlink(missing_ok=True)
            d.rmdir()
            removed.append(d.name)
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("spawn"); sp.add_argument("--root", required=True)
    sp.add_argument("--id", required=True); sp.add_argument("--cwd", default=".")
    sp.add_argument("--budget", type=int, default=3600); sp.add_argument("--label", default="")
    sp.add_argument("--replay", choices=["skip", "rerun", "fail"], default="skip")
    sp.add_argument("argv", nargs=argparse.REMAINDER)

    st = sub.add_parser("status"); st.add_argument("--root", required=True)
    st.add_argument("--id"); st.add_argument("--json", action="store_true")
    st.add_argument("--grace", type=int, default=2)

    wa = sub.add_parser("wait"); wa.add_argument("--root", required=True)
    wa.add_argument("--id", action="append", required=True)
    wa.add_argument("--budget", type=int, default=3600); wa.add_argument("--interval", type=int, default=5)

    rq = sub.add_parser("require"); rq.add_argument("--root", required=True)
    rq.add_argument("--id", required=True); rq.add_argument("--expect-rc", type=int, default=0)

    kl = sub.add_parser("kill"); kl.add_argument("--root", required=True)
    kl.add_argument("--id", required=True); kl.add_argument("--signal", default="TERM")

    gcp = sub.add_parser("gc"); gcp.add_argument("--root", required=True)
    gcp.add_argument("--older-than", type=int, default=86400)

    a = ap.parse_args()
    root = Path(a.root)

    if a.cmd == "spawn":
        argv = [x for x in a.argv if x != "--"]
        if not argv:
            print("job.py spawn: no command given after --", file=sys.stderr)
            return 1
        r = spawn(root, a.id, argv, Path(a.cwd), a.budget, a.label, a.replay)
        print(r)
        return 0

    if a.cmd == "status":
        ids = [a.id] if a.id else sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
        rows = [status(root, j, a.grace) for j in ids]
        if a.json:
            print(json.dumps(rows if not a.id else rows[0] if rows else {}, indent=2))
        else:
            for r in rows:
                print(f"{r['id']:<28} {r['state']:<8} rc={r['rc']} {r['label']}")
        bad = [r for r in rows if r["state"] in ("lost", "forged")]
        if bad:
            return 3
        return 0 if all(r["state"] == "done" for r in rows) else 2

    if a.cmd == "wait":
        res = wait(root, a.id, a.budget, a.interval)
        for r in res.values():
            print(f"{r['id']:<28} {r['state']:<8} rc={r['rc']}")
        if any(r["state"] in ("lost", "forged") for r in res.values()):
            return 3
        return 0 if all(r["state"] == "done" and r["rc"] == 0 for r in res.values()) else 2

    if a.cmd == "require":
        require(root, a.id, a.expect_rc)
        print(f"{a.id}: done rc={a.expect_rc}")
        return 0

    if a.cmd == "kill":
        print(f"signalled {kill(root, a.id, a.signal)} pid(s) in the job's session")
        return 0

    if a.cmd == "gc":
        for j in gc(root, a.older_than):
            print(f"removed {j}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
