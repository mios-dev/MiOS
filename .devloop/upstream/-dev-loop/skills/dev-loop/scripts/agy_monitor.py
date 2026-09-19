#!/usr/bin/env python3
"""
agy_monitor.py — turn an AGY session's raw NDJSON event stream into a status a human and a
monitoring agent can both read.

Why
---
An AGY-managed run is one opaque process. `devloop.sh` has had a tmux grid since forever
(devloop.sh:52) so an operator can watch each lane in its own pane, but `agy_host.sh` never
used it: the manager ran headless with nothing to attach to and no way to see, while it ran,
whether a lane had died or a tool was being denied. The only signal was the envelope, at the end.

This reads the stream `agy_session.py --events-out` tees and emits two things from one parse:

  --follow   human lines, for a tmux pane   (and for `tail -f`-style watching)
  --once     a JSON status object, for a monitoring AGENT to report into a conversation

Both come from the same state, so the pane and the report can never disagree — a monitor whose
display and whose report are computed separately is two monitors, and one of them is wrong.

Event shapes are the ones measured from agy 1.2.6 (references/translation-layer.md 5.1a):
  {"event":"init","conversation_id":..,"init":{cwd,tools[],permission_mode}}
  {"event":"step_update","step_update":{step_index,state,step_type,tool_name,tool_info,
                                        subagent_info,duration_seconds,usage}}
  {"event":"result","result":{conversation_id,status,response,num_turns,duration_seconds,
                              usage, error?, denied_actions?}}

Lines that are NOT json (agy's warnings and bare-text errors go to the same stream) are counted
and surfaced rather than dropped — they are exactly the lines a naive json.loads monitor would
silently discard, and "ignoring unsupported stream input message event" is the difference
between a run that is working and one that is doing nothing.

Exit: 0 always for --follow (a monitor that dies takes the operator's only view with it).
      --once exits 0, or 2 when the stream shows a run that reported success while doing
      nothing (SKILL.md 7) so a caller can gate on it.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from pathlib import Path as pathlib_Path

TOOL_STEPS = ("tool", "subagent")

# Worker self-reports of backgrounding. Kept next to the parser that uses them.
STALL_PHRASES = ("wait for the background command", "will wait for the background",
                 "i have launched", "and will wait")


class State:
    """Everything the monitor knows, derived from the stream alone."""

    def __init__(self) -> None:
        self.conversation_id: str | None = None
        self.cwd: str | None = None
        self.tools: int = 0
        self.permission_mode: str | None = None
        self.turns: int = 0            # cumulative, per the measured envelope
        self.duration_s: float = 0.0
        self.usage: dict = {}
        self.tool_calls: list[str] = []
        self.subagents: dict[str, str] = {}   # child conversation_id -> type_name
        self.denials: list = []
        self.error: str | None = None
        self.status: str | None = None
        self.results: int = 0
        self.unparsed: list[str] = []
        self.last_text: str = ""
        self.stalls: list[str] = []

    def feed(self, raw: str) -> str | None:
        """Consume one stream line. Returns a human line to print, or None."""
        raw = raw.strip()
        if not raw:
            return None
        try:
            evt = json.loads(raw)
        except json.JSONDecodeError:
            self.unparsed.append(raw[:300])
            return f"  ! {raw[:160]}"      # a warning IS the signal; never swallow it
        if not isinstance(evt, dict):
            self.unparsed.append(raw[:300])
            return f"  ! non-object event: {raw[:120]}"

        kind = evt.get("event")
        if kind == "init":
            i = evt.get("init", {})
            self.conversation_id = evt.get("conversation_id")
            self.cwd, self.tools = i.get("cwd"), len(i.get("tools", []))
            self.permission_mode = i.get("permission_mode")
            return (f"  session {str(self.conversation_id)[:8]}  cwd={self.cwd}  "
                    f"tools={self.tools}  mode={self.permission_mode}")

        if kind == "step_update":
            u = evt.get("step_update", {})
            # A worker announcing it will wait for a background command is the turn-boundary
            # failure itself. stall_signals() existed and was never called -- detection that is
            # never invoked is not detection (found by audit 2026-09-19).
            if u.get("step_type") == "agent_response":
                txt = str(u.get("text_delta") or "").lower()
                if any(ph in txt for ph in STALL_PHRASES):
                    self.stalls.append(txt.strip()[:160])
                    return f"  ! STALL: {txt.strip()[:120]}"
            if u.get("state") != "DONE" or u.get("step_type") not in TOOL_STEPS:
                return None
            name = u.get("tool_name") or u.get("step_type")
            if u.get("step_type") == "subagent":
                for sa in (u.get("subagent_info") or {}).get("subagents", []):
                    cid = sa.get("conversation_id")
                    if cid:
                        self.subagents[cid] = sa.get("type_name", "?")
                self.tool_calls.append(name)
                return f"  subagent {name}  children={len(self.subagents)}"
            self.tool_calls.append(name)
            return f"  tool {name}"

        if kind == "result":
            r = evt.get("result", {})
            self.results += 1
            self.status = r.get("status")
            self.turns = r.get("num_turns") or self.turns
            self.duration_s = r.get("duration_seconds") or self.duration_s
            self.usage = r.get("usage") or self.usage
            self.last_text = (r.get("response") or "").strip()
            if r.get("error"):
                self.error = r["error"]
            for k in ("denied_actions", "permission_denials"):
                if r.get(k):
                    self.denials = list(r[k])
            return (f"  result #{self.results}  {self.status}  turns={self.turns}  "
                    f"{self.duration_s:.1f}s  denials={len(self.denials)}")
        return None

    _complete: bool = False       # set by the caller when the stream is known to be finished

    def verdict(self) -> str:
        """Derived from evidence, never from the harness's own `status` (SKILL.md 6)."""
        if self.error:
            return "errored"
        if self.denials:
            return "refused"
        if self.stalls:
            return "stalled"    # the agent announced a background wait: work died with the turn
        if self.results == 0:
            # A live run has not failed, it has not finished. Conflating "no result yet" with
            # "produced no result" makes the monitor cry wolf on every healthy run it watches --
            # found by watching a real MiOS run with it. `in_progress` is only claimed when the
            # stream shows actual activity; a stream with neither results nor tool calls really
            # has produced nothing.
            if self.tool_calls and not self._complete:
                return "in_progress"
            return "no_result"          # measured: an all-unknown stream emits none at all
        if not self.last_text and not self.tool_calls:
            return "vacuous"            # claimed a result, said nothing, did nothing
        return "working"

    def report(self, stream_path: str, done: bool) -> dict:
        return {
            "stream": stream_path,
            "conversation_id": self.conversation_id,
            "cwd": self.cwd,
            "permission_mode": self.permission_mode,
            "verdict": self.verdict(),
            "harness_claimed_status": self.status,
            "stream_complete": done,
            "turns": self.turns,
            "duration_s": round(self.duration_s, 2),
            "tool_calls": len(self.tool_calls),
            "distinct_tools": sorted(set(self.tool_calls)),
            "subagents": [{"conversation_id": k, "type": v} for k, v in self.subagents.items()],
            "denials": self.denials,
            "error": self.error,
            "stalls": self.stalls,
            "unparsed_lines": len(self.unparsed),
            "unparsed_sample": self.unparsed[:3],
            "usage": self.usage,
            "last_text": self.last_text[:400],
        }




def stall_signals(lines) -> list[str]:
    """Worker self-reports of backgrounding — the failure --session and the lane foreground
    rule both exist to prevent.

    ONLY `agent_response` text counts. A prompt the manager echoed into a subagent is not the
    worker speaking, and matching it is a Self-Certifying Predicate: this detector's first
    version grepped the whole stream for a phrase that the LANE OBJECTIVE itself quoted as a
    warning, and duly fired on its own warning while the run was healthy (2026-09-19). Scope a
    detector to what the agent GENERATED, never to what it was handed.
    """
    out = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        u = (d.get("step_update") or {}) if isinstance(d, dict) else {}
        if u.get("step_type") != "agent_response":
            continue
        text = str(u.get("text_delta") or "").lower()
        for ph in STALL_PHRASES:
            if ph in text:
                out.append(text.strip()[:160])
                break
    return out


# --------------------------------------------------------------------- transcript UI element

VERDICT_TONE = {"working": "ok", "in_progress": "live", "refused": "bad", "vacuous": "bad",
                "no_result": "bad", "no_stream": "bad", "errored": "bad"}


def render_html(state: "State", rep: dict, rows: list[tuple[str, str, str]]) -> str:
    """A self-contained transcript page: no network, no build step, readable on a phone.

    A run's transcript is the thing an operator actually wants to look at, and until now it
    existed only as NDJSON in a scratch directory. Every value here comes from the same State
    the pane and the JSON report use, so the page cannot disagree with them.
    """
    import html as _h

    tone = VERDICT_TONE.get(rep.get("verdict"), "bad")
    subs = "".join(
        f'<li><code>{_h.escape(x["conversation_id"][:12])}</code> {_h.escape(x["type"])}</li>'
        for x in rep.get("subagents", [])) or "<li class=muted>none</li>"
    dens = "".join(f"<li>{_h.escape(json.dumps(d))}</li>" for d in rep.get("denials", [])) \
        or "<li class=muted>none</li>"
    unp = "".join(f"<li>{_h.escape(u)}</li>" for u in rep.get("unparsed_sample", [])) \
        or "<li class=muted>none</li>"
    body = "".join(
        f'<div class="row {k}"><span class=k>{_h.escape(k)}</span>'
        f'<span class=t>{_h.escape(t)}</span><span class=d>{_h.escape(d)}</span></div>'
        for k, t, d in rows)

    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Run transcript</title><style>
:root{{--bg:#fbfaf8;--fg:#1a1917;--mut:#75706a;--line:#e3ded6;--card:#fff;
--ok:#1a7f4b;--live:#8a6a00;--bad:#b0342c;--acc:#3a5ccc}}
@media(prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#16151a;--fg:#ece9e4;
--mut:#9b958d;--line:#2e2b33;--card:#1e1d23;--ok:#4ec07f;--live:#d9ae3c;--bad:#f08579;--acc:#8fa8ff}}}}
:root[data-theme=dark]{{--bg:#16151a;--fg:#ece9e4;--mut:#9b958d;--line:#2e2b33;--card:#1e1d23;
--ok:#4ec07f;--live:#d9ae3c;--bad:#f08579;--acc:#8fa8ff}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 ui-sans-serif,system-ui,-apple-system,sans-serif;
padding:16px;max-width:820px;margin-inline:auto}}
h1{{font-size:1.1rem;margin:0 0 2px}}
.sub{{color:var(--mut);font-size:.82rem;margin-bottom:14px;word-break:break-all}}
.badge{{display:inline-block;padding:4px 11px;border-radius:999px;font-weight:650;font-size:.8rem;
border:1px solid currentColor}}
.ok{{color:var(--ok)}}.live{{color:var(--live)}}.bad{{color:var(--bad)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:8px;margin:14px 0}}
.cell{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}}
.cell b{{display:block;font-size:1.25rem;line-height:1.2}}
.cell span{{color:var(--mut);font-size:.72rem;text-transform:uppercase;letter-spacing:.04em}}
details{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:8px 0}}
summary{{cursor:pointer;font-weight:600;min-height:32px;display:flex;align-items:center}}
ul{{margin:8px 0 0;padding-left:18px}}li{{margin:3px 0;word-break:break-all;font-size:.86rem}}
.muted{{color:var(--mut)}}
.row{{display:flex;gap:9px;align-items:baseline;padding:7px 10px;border-bottom:1px solid var(--line);
font-size:.87rem}}
.row:last-child{{border-bottom:0}}
.k{{flex:0 0 66px;color:var(--mut);font-size:.7rem;text-transform:uppercase;letter-spacing:.04em}}
.t{{flex:1;min-width:0;word-break:break-word}}
.d{{flex:0 0 auto;color:var(--mut);font-size:.76rem}}
.row.result .t{{font-weight:650}}
.row.warn{{color:var(--bad)}}
.log{{background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-top:6px}}
code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.84em}}
@media(max-width:480px){{.row{{flex-wrap:wrap}}.k{{flex-basis:100%}}.d{{margin-left:auto}}}}
</style></head><body>
<h1>Run transcript</h1>
<div class=sub>{_h.escape(str(rep.get('conversation_id') or 'no session'))} &middot;
{_h.escape(str(rep.get('cwd') or ''))}</div>
<span class="badge {tone}">{_h.escape(str(rep.get('verdict')))}</span>
<div class=grid>
<div class=cell><b>{rep.get('turns', 0)}</b><span>turns</span></div>
<div class=cell><b>{rep.get('tool_calls', 0)}</b><span>tool calls</span></div>
<div class=cell><b>{len(rep.get('subagents', []))}</b><span>subagents</span></div>
<div class=cell><b>{len(rep.get('denials', []))}</b><span>denials</span></div>
<div class=cell><b>{rep.get('duration_s', 0)}s</b><span>elapsed</span></div>
<div class=cell><b>{rep.get('unparsed_lines', 0)}</b><span>unparsed</span></div>
</div>
<details><summary>Run facts</summary><ul>
<li>permission mode: <code>{_h.escape(str(rep.get('permission_mode')))}</code></li>
<li>harness claimed: <code>{_h.escape(str(rep.get('harness_claimed_status')))}</code>
 <span class=muted>(kept for audit; the verdict above is derived from the stream)</span></li>
<li>stream complete: <code>{rep.get('stream_complete')}</code> via
 <code>{_h.escape(str(rep.get('completeness_from', 'n/a')))}</code></li>
<li>distinct tools: {_h.escape(', '.join(rep.get('distinct_tools', [])) or '-')}</li>
</ul></details>
<details><summary>Subagents ({len(rep.get('subagents', []))})</summary><ul>{subs}</ul></details>
<details><summary>Denials ({len(rep.get('denials', []))})</summary><ul>{dens}</ul></details>
<details><summary>Unparsed lines ({rep.get('unparsed_lines', 0)})</summary>
<p class=muted>agy writes warnings and bare-text errors into the same stream. These are the
lines a json.loads monitor drops silently.</p><ul>{unp}</ul></details>
<h2 style="font-size:.95rem;margin:18px 0 4px">Transcript ({len(rows)} events)</h2>
<div class=log>{body or '<div class="row"><span class=t muted>no events</span></div>'}</div>
</body></html>"""


def task_records(rep: dict, lanes_path: Path | None, stream: Path) -> list[dict]:
    """One task record per lane, shaped for a host to mirror into its NATIVE task list.

    The point is not another bespoke UI. A run already has a native place to live in whatever
    client is driving it -- Claude Code's task list, an issue tracker, a board -- and what was
    missing was the transcript travelling WITH the task instead of sitting in a scratch
    directory nothing opens. Each record therefore carries the stream path, the rendered page,
    the tmux session, and the monitor's derived verdict, so the task itself is openable.

    Status maps from the RUN's evidence, never from the harness's claim:
      in_progress -> in_progress ; working -> completed ; anything else -> in_progress with
      the verdict named, because refused/vacuous/no_result are states a human must look at and
      silently completing them is the failure this whole skill is about.
    """
    verdict = rep.get("verdict")
    marker = stream.parent / "session.status"
    run_started = 0.0
    try:
        run_started = float(json.loads(marker.read_text()).get("started_at") or 0)
    except Exception:
        run_started = 0.0
    if not run_started and stream.is_file():
        run_started = stream.stat().st_mtime - 6 * 3600   # unknown start: accept a wide window
    lanes = []
    if lanes_path and lanes_path.is_file():
        try:
            lanes = json.loads(lanes_path.read_text()).get("lanes", [])
        except Exception:
            lanes = []
    if not lanes:
        lanes = [{"id": "run", "objective": "AGY-managed run (no lane plan supplied)"}]

    out = []
    for l in lanes:
        lid = l.get("id")
        # A lane's status comes from ITS OWN evidence, never from the run-level verdict. The
        # first version mapped verdict "working" -> every lane completed, and a real run proved
        # it wrong within minutes: one lane had delivered and merged while the other had not
        # started, and both were reported completed. That is the over-claim this whole skill
        # exists to catch, committed by the monitor meant to catch it.
        # Scoped to THIS run: a report file left by a PREVIOUS run makes a lane that has not
        # started look delivered. Caught by comparing the records against a real re-run where
        # one lane's report was 11 minutes stale. started_at comes from the run marker; with no
        # marker we fall back to the stream's own mtime, which is never older than the run.
        # A REPORT IS A CLAIM, NOT AN ARTIFACT. Measured on a real re-run: the manager wrote
        # report-t1001-gate05.json at 03:11 for a lane whose owned deliverable was last touched
        # at 02:59, before this run even started. Trusting the report marked a lane that did
        # nothing as completed -- SKILL.md 11, never trust a lane's own claim over the tree.
        # Delivery requires the lane's OWNED PATH to have changed during THIS run.
        # READ the report, do not merely count it. adapters.py synthesises an HONEST fallback
        # for a lane that emitted no devloop_report: status partial, changed_paths empty,
        # full_gate exit -1. Treating that as a delivery claim was my error, not the
        # orchestrator's -- it had already said the lane produced nothing. Measured on
        # t1001-gate05, whose worker looped on "I will wait for the background command" and
        # exited after one turn.
        report = stream.parent / f"report-{lid}.json"
        has_report = report.is_file() and report.stat().st_mtime >= run_started
        claimed_done = False
        if has_report:
            try:
                rj = json.loads(report.read_text())
                rj = rj.get("devloop_report", rj)
                claimed_done = rj.get("status") == "done" and bool(rj.get("changed_paths"))
            except Exception:
                claimed_done = False
        owned = [pathlib_Path(stream.parent.parent.parent / o) for o in (l.get("owned_paths") or [])]
        touched = [o for o in owned if o.is_file() and o.stat().st_mtime >= run_started]
        delivered = bool(has_report and claimed_done and touched)
        out.append({
            "lane": lid,
            "subject": f"{lid}: {(l.get('objective') or '')[:80]}",
            "status": "completed" if delivered else "in_progress",
            "evidence": ("report says done + owned path changed this run" if delivered
                         else "lane reported PARTIAL/empty — the orchestrator recorded that it "
                              "produced nothing" if has_report and not claimed_done
                         else "report claims done but the owned path is unchanged since this "
                              "run started" if has_report and not touched
                         else "no per-lane report from this run yet"),
            "owned_paths_touched": [str(o) for o in touched],
            "lane_report": str(report) if delivered else None,
            "verdict": verdict,
            "harness_claimed_status": rep.get("harness_claimed_status"),
            "transcript_stream": str(stream),
            "transcript_html": str(stream.parent / "transcript.html"),
            "monitor_report": str(stream.parent / "monitor-report.json"),
            "tool_calls": rep.get("tool_calls"),
            "subagents": rep.get("subagents"),
            "denials": rep.get("denials"),
            "needs_attention": verdict not in ("working", "in_progress") or not delivered,
        })
    return out


def read_all(path: Path, state: State, echo: bool, rows: list | None = None) -> None:
    for line in path.read_text(errors="ignore").splitlines():
        before = len(state.tool_calls), state.results, len(state.unparsed)
        out = state.feed(line)
        if echo and out:
            print(out, flush=True)
        if rows is not None and out:
            after = len(state.tool_calls), state.results, len(state.unparsed)
            kind = ("warn" if after[2] > before[2] else
                    "result" if after[1] > before[1] else
                    "tool" if after[0] > before[0] else "init")
            rows.append((kind, out.strip(), f"{state.duration_s:.1f}s" if kind == "result" else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stream", help="NDJSON file written by agy_session.py --events-out")
    ap.add_argument("--follow", action="store_true", help="human lines, for a tmux pane")
    ap.add_argument("--once", action="store_true", help="print a JSON status object and exit")
    ap.add_argument("--report-out", help="also write the JSON status here (for a monitor agent)")
    ap.add_argument("--html", help="also render a self-contained transcript page here "
                                   "(the UI element a client shows for the task)")
    ap.add_argument("--tasks-out", help="emit per-lane task records for a host to mirror "
                                        "into its NATIVE task list, transcript paths included")
    ap.add_argument("--lanes", help="lane plan, so task records carry one entry per lane")
    ap.add_argument("--poll-s", type=float, default=1.0)
    ap.add_argument("--stale-after-s", type=float, default=90.0,
                    help="--once treats a stream untouched for this long as finished")
    ap.add_argument("--max-idle-s", type=float, default=0,
                    help="stop following after this long with no new bytes (0 = never)")
    a = ap.parse_args()

    path = Path(a.stream)
    state = State()

    if not a.follow:
        if not path.is_file():
            # An absent stream is NOT an empty run: say so rather than reporting a clean nothing.
            rep = {"stream": str(path), "verdict": "no_stream",
                   "error": "event stream does not exist — the session may not have started"}
            print(json.dumps(rep, indent=2))
            if a.report_out:
                Path(a.report_out).write_text(json.dumps(rep, indent=2) + "\n")
            return 2
        # --once cannot see the future: a growing stream is in progress, a stale one is done.
        # The threshold is stated in the report so a reader can judge it rather than trust it.
        import time as _t
        idle_for = _t.time() - path.stat().st_mtime
        # Staleness is a POOR proxy for completion: a manager inside a long run_command emits
        # no events for minutes and a purely time-based rule calls that a dead run. Measured on
        # a real MiOS run -- 128s of silence while a gate executed, flipping the verdict to
        # no_result on a perfectly healthy manager. Prefer the run marker agy_host.sh writes;
        # fall back to staleness only when there is no marker to read.
        marker = path.parent / "session.status"
        marker_state = None
        if marker.is_file():
            try:
                marker_state = json.loads(marker.read_text()).get("state")
            except Exception:
                marker_state = marker.read_text().strip() or None
        if marker_state == "running":
            state._complete = False
        elif marker_state in ("finished", "failed"):
            state._complete = True
        else:
            state._complete = idle_for >= a.stale_after_s
        rows: list = []
        read_all(path, state, echo=False, rows=rows)
        rep = state.report(str(path), done=state._complete)
        rep["stream_idle_s"] = round(idle_for, 1)
        rep["completeness_from"] = f"marker:{marker_state}" if marker_state else f"staleness>={a.stale_after_s}s"
        rep["assumed_complete_after_s"] = a.stale_after_s
        print(json.dumps(rep, indent=2))
        if a.report_out:
            Path(a.report_out).write_text(json.dumps(rep, indent=2) + "\n")
        if a.html:
            Path(a.html).parent.mkdir(parents=True, exist_ok=True)
            Path(a.html).write_text(render_html(state, rep, rows))
        if a.tasks_out:
            recs = task_records(rep, Path(a.lanes) if a.lanes else None, path)
            Path(a.tasks_out).write_text(json.dumps(recs, indent=2) + "\n")
        return 2 if rep["verdict"] in ("vacuous", "no_result", "stalled") else 0   # in_progress is NOT a failure

    # --follow: a pane view. Tolerate the file not existing yet; the session may still be starting.
    print(f"agy_monitor: following {path}", flush=True)
    pos, idle = 0, 0.0
    while True:
        if path.is_file():
            with path.open("r", errors="ignore") as fh:
                fh.seek(pos)
                chunk = fh.read()
                pos = fh.tell()
            if chunk:
                idle = 0.0
                for line in chunk.splitlines():
                    out = state.feed(line)
                    if out:
                        print(out, flush=True)
            else:
                idle += a.poll_s
        else:
            idle += a.poll_s
        if a.max_idle_s and idle >= a.max_idle_s:
            print(f"  -- idle {idle:.0f}s; verdict={state.verdict()}", flush=True)
            if a.report_out:
                Path(a.report_out).write_text(json.dumps(state.report(str(path), done=False), indent=2) + "\n")
            return 0
        time.sleep(a.poll_s)


if __name__ == "__main__":
    sys.exit(main())
