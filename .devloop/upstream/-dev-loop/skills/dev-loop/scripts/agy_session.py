#!/usr/bin/env python3
"""
agy_session.py — drive `agy` as a HELD, multi-turn stream-json session.

Why this exists
---------------
`agy -p "<prompt>"` is single-turn print mode: the turn ends when the model stops
speaking and the PROCESS EXITS. Anything the manager started that had not finished --
a native `invoke_subagent` lane, a backgrounded command -- dies with it, and the
manager cannot detect that, because from inside the turn the dispatch succeeded.
That is why `agy_host.sh --headless` forbids native subagents.

Measured on agy 1.2.6: `--input-format stream-json` reads one NDJSON message per line
from stdin and runs a turn for each, requiring `--output-format stream-json`. While the
caller holds stdin open the process stays alive ACROSS turns. So the constraint above is
a property of SINGLE-SHOT print mode, not of headless operation: a held session can
dispatch native lanes and then poll for them over further turns.

Wire protocol (all measured, see references/translation-layer.md 5.1a)
----------------------------------------------------------------------
  invoke : agy --input-format stream-json --output-format stream-json \
               --print-timeout 0 [--model M] [--effort E] -p=''
           Flag order is load-bearing: a BARE `-p` swallows the next token as its
           prompt, so the empty-valued `-p=''` form is required here.
  stdin  : {"event":"user","message":{"role":"user","content":"..."}}   one per line
  stdout : {"event":"init","conversation_id":...,"init":{cwd,tools[],permission_mode}}
           {"event":"step_update","step_update":{step_index,state,step_type,...}}
           {"event":"result","result":{...}}        ONE PER TURN, not only at the end

  `num_turns` and `duration_seconds` in a result are CUMULATIVE across the session,
  not per-turn. Do not sum them.

  An UNKNOWN input event only warns and is ignored -- a stream of them yields no result
  event at all, so "no terminal envelope" is its own outcome and is reported here as an
  error rather than as success. A MALFORMED KNOWN event is fatal instead.

Exit codes: 0 ok · 3 no terminal envelope / session produced nothing · 4 agy missing
            5 lane reports still missing when the poll budget ran out
            6 the manager left the base tree dirty outside every lane worktree

STATUS OF THE POLL LOOP: UNEXERCISED as of the first end-to-end run (2026-09-19). The manager
dispatched both native lanes, gated them and merged them inside a SINGLE turn, so `missing_reports`
was already empty at the first result event and no follow-up turn was ever sent. The loop's unit
behaviour is covered by tests/test_agy_dispatch_rule.py, but its reason for existing -- keeping the
process alive for a subagent that has NOT finished when the turn ends -- has not yet been observed.
Do not describe it as proven.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # for job.py

USER_EVENT = "user"


def ndjson_user(text: str) -> str:
    """One stdin line. `message` is TOP-LEVEL, not nested under `user` (measured:
    omitting it fails with 'stream input "user" message is missing the "message" field')."""
    return json.dumps({"event": USER_EVENT, "message": {"role": "user", "content": text}}) + "\n"


def missing_reports(native_dir: Path, lane_ids: list[str], jobs_dir: Path | None = None) -> list[str]:
    """Lane ids that have not finished. Empty lane_ids means nothing to wait for.

    THE PREDICATE MATTERS MORE THAN THE LOOP. This was `is_file()` over
    report-<id>.json -- a file the poll prompt explicitly asks the polled agent to create
    (see the prompt below). The thing being measured wrote the measurement, so an agent that
    wrote the file and did nothing else ended the wait. That is a self-certifying predicate
    (SKILL.md 7) sitting inside the one mitigation that was actually enforced in code.

    When a jobs directory is present the SHELL's receipt decides: a lane is finished only when
    job.py reports it terminal (done/lost/forged), which the agent cannot fabricate because the
    wrapper writes done.json before the receipt and status() cross-checks the pair. The report
    file remains the FALLBACK for native subagent lanes, which have no job of their own -- and
    that fallback is still agent-writable, which is stated here rather than hidden.
    """
    out = []
    for lid in lane_ids:
        if jobs_dir is not None and (jobs_dir / lid).is_dir():
            try:
                import job as _job
                if _job.status(jobs_dir, lid)["state"] in ("done", "lost", "forged"):
                    continue
                out.append(lid)
                continue
            except Exception:
                pass  # fall through to the report-file fallback
        if not (native_dir / f"report-{lid}.json").is_file():
            out.append(lid)
    return out


# The manager is not a lane, so nothing else in this file watches what IT writes.
# Measured 2026-09-19: a manager run with worktree_root set never created a worktree and
# edited the base tree directly, planting a negatives-suite fixture -- `echo
# "Root:<literal>" | chpasswd` -- into a shipped boot script and a 99999 ratchet into the
# SSOT. Every lane gate passed, because lane gates read WORKTREES. The dispatch prompt
# already said to use isolated workspaces; a rule with no measurement behind it is a check
# that cannot fail (SKILL.md 7), so this measures it.
BASE_TREE_ALWAYS_ALLOWED = (".devloop/", ".git/", "AGENTS.md", "TASKS.md")


def base_tree_state(root: Path) -> dict[str, str] | None:
    """`git status --porcelain` as {path: XY}, or None when git cannot answer.

    None is NOT "clean". A control that reports nothing to report when its instrument is
    missing is the Skip-as-Pass this whole guard exists to catch, so the caller says so out
    loud and turns the guard OFF rather than letting it pass vacuously.
    """
    try:
        p = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                           capture_output=True, text=True)
    except OSError:
        return None
    if p.returncode != 0:
        return None
    out: dict[str, str] = {}
    for ln in p.stdout.splitlines():
        if len(ln) < 4:
            continue
        path = ln[3:]
        # `R  old -> new` names two paths; the destination is the one that appeared.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        out[path.strip().strip('"')] = ln[:2]
    return out


def stray_base_edits(before: dict[str, str], now: dict[str, str] | None,
                     allowed: tuple[str, ...]) -> list[str]:
    """Paths whose base-tree status CHANGED since `before` and that no lane may own.

    Compared against a baseline rather than against clean, because a run that starts on a
    dirty tree would otherwise blame the manager for every path it inherited.
    """
    if now is None:
        return []
    return sorted(path for path, st in now.items()
                  if before.get(path) != st
                  and not any(path == a or (a.endswith("/") and path.startswith(a)) for a in allowed))


def worktree_root_of(lanes_path: Path) -> str:
    """The lane plan's worktree_root, normalised to a directory prefix."""
    try:
        doc = json.loads(lanes_path.read_text())
    except Exception:
        return ".worktrees/"
    root = str(doc.get("worktree_root") or ".worktrees").strip().lstrip("./")
    return (root.rstrip("/") or ".worktrees") + "/"


def antigravity_lane_ids(lanes_path: Path) -> list[str]:
    try:
        doc = json.loads(lanes_path.read_text())
    except Exception:
        return []
    out = []
    for lane in doc.get("lanes", []):
        if (lane.get("worker") or {}).get("harness") == "antigravity" and lane.get("id"):
            out.append(lane["id"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompt-file", required=True, help="file holding the manager prompt (turn 1)")
    ap.add_argument("--lanes", help="lanes.json; its antigravity lane ids are what we poll for")
    ap.add_argument("--run-root", default=".", help="repo root holding .devloop/native/")
    ap.add_argument("--jobs-root", help="job.py root; when set, a lane is finished when its "
                                        "SHELL-written receipt says so, not when a report file appears")
    ap.add_argument("--model")
    ap.add_argument("--effort")
    ap.add_argument("--poll-max", type=int, default=8, help="follow-up turns allowed after turn 1")
    ap.add_argument("--envelope-out", help="write the final result object here")
    ap.add_argument("--events-out", help="tee every raw NDJSON event here for monitors "
                                        "(agy_monitor.py tails this; a tmux pane watches it)")
    ap.add_argument("--yolo", action="store_true")
    a = ap.parse_args()

    argv = ["agy", "--input-format", "stream-json", "--output-format", "stream-json",
            "--print-timeout", "0"]
    if a.model:
        argv += ["--model", a.model]
    if a.effort:
        argv += ["--effort", a.effort]
    if a.yolo:
        argv.append("--dangerously-skip-permissions")
    argv.append("-p=")  # MUST be the attached-empty form; a bare -p eats the next flag

    native_dir = Path(a.run_root) / ".devloop" / "native"
    jobs_dir = Path(a.jobs_root) if a.jobs_root else None
    lane_ids = antigravity_lane_ids(Path(a.lanes)) if a.lanes else []

    # Baseline BEFORE turn 1, so inherited dirt is never attributed to the manager.
    allowed = BASE_TREE_ALWAYS_ALLOWED + (
        (worktree_root_of(Path(a.lanes)),) if a.lanes else (".worktrees/",))
    # No off switch: a guard that can be turned off is turned off by whatever is failing it.
    base_before = base_tree_state(Path(a.run_root))
    if base_before is None:
        print("agy_session: base-tree guard OFF -- git could not read %s, so a manager editing "
              "the base tree instead of a lane worktree will NOT be detected" % a.run_root,
              file=sys.stderr)
    strays: list[str] = []
    stray_warned: set[str] = set()

    events = None
    if a.events_out:
        Path(a.events_out).parent.mkdir(parents=True, exist_ok=True)
        # line-buffered: a monitor tailing this must see each event as it happens, not at exit
        events = open(a.events_out, "w", buffering=1)

    try:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, bufsize=1,
                                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except FileNotFoundError:
        print("agy_session: agy not installed", file=sys.stderr)
        return 4

    last_result: dict | None = None
    turns_sent = 1
    try:
        proc.stdin.write(ndjson_user(Path(a.prompt_file).read_text()))
        proc.stdin.flush()

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            if events:
                # tee BEFORE parsing: a monitor must see the warnings and bare-text errors
                # too, which are exactly the lines json.loads throws away
                events.write(line + "\n")
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                print(line, file=sys.stderr)  # warnings/errors arrive as bare text
                continue

            kind = evt.get("event")
            if kind == "init":
                init = evt.get("init", {})
                print(f"agy_session: init cwd={init.get('cwd')} "
                      f"tools={len(init.get('tools', []))} mode={init.get('permission_mode')}",
                      file=sys.stderr)
                continue
            if kind == "step_update":
                u = evt.get("step_update", {})
                if u.get("state") == "DONE" and u.get("step_type") in ("tool", "subagent"):
                    print(f"agy_session: {u.get('step_type')} {u.get('tool_name')}", file=sys.stderr)
                continue
            if kind != "result":
                continue

            last_result = evt.get("result", {})
            if base_before is not None:
                strays = stray_base_edits(base_before, base_tree_state(Path(a.run_root)), allowed)
            fresh = [x for x in strays if x not in stray_warned]
            outstanding = missing_reports(native_dir, lane_ids, jobs_dir)
            if fresh:
                stray_warned.update(fresh)
                print("agy_session: BASE TREE EDITED outside any lane worktree: %s -- failing closed"
                      % ", ".join(fresh), file=sys.stderr)
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
                return 6
            if not outstanding or turns_sent > a.poll_max:
                break
            # The manager's turn ended but native lanes have not reported. In a held
            # session the process is still alive, so ask it to wait rather than
            # accepting a turn-end as the run's end.
            print(f"agy_session: turn {turns_sent} ended, {len(outstanding)} lane(s) "
                  f"unreported {outstanding} — polling", file=sys.stderr)
            proc.stdin.write(ndjson_user(
                "Your dispatched native lanes have not all written "
                f"{native_dir}/report-<LANE_ID>.json yet. Still missing: {', '.join(outstanding)}. "
                "Do NOT start new work and do NOT re-dispatch a lane that is already running. "
                "Wait for the outstanding subagents, collect each one's devloop_report into its "
                "report file with write_file, then reply DONE when every listed lane has a file."))
            proc.stdin.flush()
            turns_sent += 1
    finally:
        if events:
            try:
                events.close()
            except Exception:
                pass
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=60)
        except Exception:
            proc.kill()

    if last_result is None:
        # No terminal envelope at all. Measured: a stream whose events are all unknown
        # produces exactly this. Never report it as success.
        print("agy_session: the session produced NO result event — nothing ran", file=sys.stderr)
        return 3

    text = json.dumps(last_result)
    if a.envelope_out:
        Path(a.envelope_out).write_text(text + "\n")
    print(text)

    if base_before is not None:
        strays = stray_base_edits(base_before, base_tree_state(Path(a.run_root)), allowed)
        if strays:
            print("agy_session: run ended with the BASE TREE dirty outside every lane "
                  "worktree: %s -- these were never gated, because lane gates read "
                  "worktrees. Review and revert them before trusting this run."
                  % ", ".join(strays), file=sys.stderr)
            return 6

    still = missing_reports(native_dir, lane_ids, jobs_dir)
    if still:
        print(f"agy_session: poll budget spent; still unreported: {', '.join(still)}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    rc = main()
    # Record the real exit status beside the stream. Under --tmux this process is a pane and
    # its exit code is not observable by the launching shell, which previously fabricated one.
    try:
        import argparse as _a
        _p = _a.ArgumentParser(add_help=False)
        _p.add_argument("--events-out")
        _known, _ = _p.parse_known_args()
        if _known.events_out:
            Path(_known.events_out).parent.joinpath("session.rc").write_text(f"{rc}\n")
    except Exception:
        pass
    sys.exit(rc)
