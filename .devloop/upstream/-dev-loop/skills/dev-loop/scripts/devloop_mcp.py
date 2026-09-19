#!/usr/bin/env python3
"""
devloop_mcp.py — the Dev Loop orchestrator as an MCP server (stdio, JSON-RPC 2.0, stdlib only).

Any MCP-capable host (Claude Code/Desktop, Codex, Gemini/Antigravity, Copilot, Cursor, OpenCode, Open WebUI, a custom
OpenAI-compatible runtime) can host the loop by registering:
    {"mcpServers": {"dev-loop": {"command": "python3", "args": ["<skill>/scripts/devloop_mcp.py"]}}}

Stateless by design (MCP 2026-07-28 model): every tool call carries its own inputs and returns explicit handles
(run directories, report paths). Supports both the pre-2026 `initialize` handshake and the 2026-07-28 `server/discover`
RPC, and both `Content-Length` framing and newline-delimited JSON, so old and new hosts connect.

Tools
  validate_lanes  {lanes_path}                         schema + v1→v2 normalisation + DAG check
  run_lanes       {lanes_path, layout?, dry_run?}      run scripts/devloop.sh (POSIX) / DevLoop.ps1 (Windows); returns run dir + per-lane reports
  gate            {lane_path, worktree, run_dir?}      positive / negative(+expect, tree-restore) / mutation / full gate; exit 0 pass, 1 fail, 2 vacuous
  probe           {harness?[]}                         verify installed harness CLIs and the flags the adapters rely on
  tasks_next      {root?}                              unblocked tasks from .devloop/tasks.jsonl
  task_set        {root?, id, status, evidence?}       flip a task (done requires evidence)
  ledger          {root?, status, objective, done?, next?, blockers?, unverified?}
  report          {run_dir}                            collect .devloop/run-*/report-*.json into one object
  scaffold        {root?, dry_run?}                    create missing canonical artifacts
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
PROTOCOL_VERSIONS = ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
SERVER_INFO = {"name": "dev-loop", "version": "7.0.0"}
CAPS = {"tools": {"listChanged": False}}


def S(**props):  # strict object schema helper
    req = [k for k, v in props.items() if not v.get("_opt")]
    for v in props.values(): v.pop("_opt", None)
    return {"type": "object", "additionalProperties": False, "required": req, "properties": props}


def opt(t, **kw): return {"type": t, "_opt": True, **kw}


TOOLS = [
    {"name": "validate_lanes", "description": "Validate a lanes.json against assets/lane-schema.json (accepts v1 files, normalises to v2, rejects lanes without a real negative control, checks the depends_on DAG).",
     "inputSchema": S(lanes_path={"type": "string"})},
    {"name": "run_lanes", "description": "Run the Dev Loop orchestrator on a lanes.json: one git worktree per lane, each lane in its own harness, two-sided merge gates, --no-ff merges, task ledger + handoff note. Returns the run directory, exit status (0 ok, 1 lane failed/partial, 2 vacuous lane) and every lane report. Long-running: prefer headless layout from MCP.",
     "inputSchema": S(lanes_path={"type": "string"}, layout=opt("string", enum=["auto", "tmux_grid", "wt_grid", "detached", "headless"]), dry_run=opt("boolean"), timeout_s=opt("integer"))},
    {"name": "gate", "description": "Run a single lane's merge gate in a worktree: positive control (exit 0), negative control (must fail, must match negative_expect, must restore the tree), optional mutation and full gates. exit 2 = vacuous control.",
     "inputSchema": S(lane_path={"type": "string"}, worktree={"type": "string"}, run_dir=opt("string"))},
    {"name": "probe", "description": "Check which harness CLIs (claude, codex, gemini, agy, copilot, opencode, agent) are installed and whether the flags the adapters rely on still appear in --help.",
     "inputSchema": S(harness=opt("array", items={"type": "string"}))},
    {"name": "tasks_next", "description": "List tasks in .devloop/tasks.jsonl that are open with all dependencies done.", "inputSchema": S(root=opt("string"))},
    {"name": "task_set", "description": "Set a task's status (open|in_progress|blocked|done|cancelled); done requires evidence citing both controls. Re-renders TASKS.md.",
     "inputSchema": S(id={"type": "string"}, status={"type": "string"}, evidence=opt("string"), root=opt("string"))},
    {"name": "ledger", "description": "Append a handoff note to .devloop/LEDGER.md (status, objective, done, next, blockers, unverified).",
     "inputSchema": S(status={"type": "string"}, objective={"type": "string"}, done=opt("string"), next=opt("string"), blockers=opt("string"), unverified=opt("string"), root=opt("string"))},
    {"name": "report", "description": "Collect every lane report under a run directory into one object.", "inputSchema": S(run_dir={"type": "string"})},
    {"name": "scaffold", "description": "Create any missing canonical project artifacts (AGENTS.md, docs/GOALS.md, ROADMAP, DOD, CHECKLISTS, CHANGELOG, .devloop/tasks.jsonl, LEDGER) and the per-harness pointer files. Never overwrites.",
     "inputSchema": S(root=opt("string"), dry_run=opt("boolean"))},
]


def sh(argv, cwd=None, timeout=1800):
    cp = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout, env={**os.environ, "CI": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat", "PAGER": "cat"})
    return cp.returncode, (cp.stdout + cp.stderr)[-20000:]


def call(name: str, a: dict) -> tuple[str, bool]:
    ad = str(HERE / "adapters.py"); art = str(HERE / "artifacts.py"); root = a.get("root") or os.getcwd()
    if name == "validate_lanes":
        code, out = sh([PY, ad, "validate", a["lanes_path"]]); return out, code != 0
    if name == "run_lanes":
        if a.get("dry_run") is None and a.get("layout") is None: a["layout"] = "headless"
        if os.name == "nt":
            argv = ["pwsh", "-NoProfile", "-NonInteractive", "-File", str(HERE / "DevLoop.ps1"), "-Lanes", a["lanes_path"], "-Layout", a.get("layout", "headless")] + (["-DryRun"] if a.get("dry_run") else [])
        else:
            argv = ["sh", str(HERE / "devloop.sh"), a["lanes_path"], "--layout", a.get("layout", "headless")] + (["--dry-run"] if a.get("dry_run") else [])
        code, out = sh(argv, timeout=int(a.get("timeout_s") or 7200))
        run_dir = next((ln.split("run artefacts: ", 1)[1].split(" ;")[0] for ln in out.splitlines() if "run artefacts:" in ln), None)
        res = {"exit": code, "run_dir": run_dir, "log_tail": out[-4000:], "reports": _reports(run_dir) if run_dir else {}}
        return json.dumps(res, indent=2), code == 2
    if name == "gate":
        run_dir = a.get("run_dir") or str(Path(a["worktree"]).resolve().parent / ".devloop" / "gate"); Path(run_dir).mkdir(parents=True, exist_ok=True)
        code, out = sh([PY, ad, "gate", "--lane", a["lane_path"], "--wt", a["worktree"], "--run", run_dir]); return json.dumps({"exit": code, "verdict": {0: "pass", 1: "fail", 2: "VACUOUS"}.get(code, "error"), "output": out}), code != 0
    if name == "probe":
        code, out = sh([PY, ad, "probe"] + (["--harness", *a["harness"]] if a.get("harness") else [])); return out, False
    if name == "tasks_next":
        code, out = sh([PY, art, "tasks", "next", "--root", root]); return out, code != 0
    if name == "task_set":
        argv = [PY, art, "tasks", "set", a["id"], a["status"], "--root", root] + (["--evidence", a["evidence"]] if a.get("evidence") else [])
        code, out = sh(argv)
        if code == 0: sh([PY, art, "tasks", "render", "--root", root])
        return out, code != 0
    if name == "ledger":
        argv = [PY, ad, "ledger", "--root", root, "--status", a["status"], "--objective", a["objective"]]
        for k in ("done", "next", "blockers", "unverified"):
            if a.get(k): argv += [f"--{k}", a[k]]
        code, out = sh(argv); return out, code != 0
    if name == "report":
        return json.dumps(_reports(a["run_dir"]), indent=2), False
    if name == "scaffold":
        code, out = sh([PY, art, "scaffold", "--root", root] + (["--dry-run"] if a.get("dry_run") else []))
        if code == 0 and not a.get("dry_run"): code2, out2 = sh([PY, art, "bridges", "--root", root]); out += "\n" + out2
        return out, code != 0
    return f"unknown tool {name}", True


def _reports(run_dir):
    out = {}
    for p in sorted(Path(run_dir).glob("report-*.json")):
        try: out[p.stem[7:]] = json.loads(p.read_text("utf-8"))
        except (OSError, json.JSONDecodeError) as e: out[p.stem[7:]] = {"error": str(e)}
    return out


# ---------------------------------------------------------------- JSON-RPC plumbing (both framings)
def read_message():
    line = sys.stdin.buffer.readline()
    if not line: return None
    if line.lower().startswith(b"content-length:"):
        n = int(line.split(b":")[1].strip())
        while True:
            h = sys.stdin.buffer.readline()
            if h in (b"\r\n", b"\n", b""): break
        return json.loads(sys.stdin.buffer.read(n).decode("utf-8")), "lsp"
    line = line.strip()
    return (json.loads(line.decode("utf-8")) if line else {}), "ndjson"


def write_message(obj, framing):
    data = json.dumps(obj).encode("utf-8")
    if framing == "lsp": sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(data) + data)
    else: sys.stdout.buffer.write(data + b"\n")
    sys.stdout.buffer.flush()


def handle(msg):
    m, p, i = msg.get("method"), msg.get("params") or {}, msg.get("id")
    if m == "initialize":  # ≤ 2025-11-25 hosts
        v = p.get("protocolVersion"); v = v if v in PROTOCOL_VERSIONS else "2025-06-18"
        return {"protocolVersion": v, "capabilities": CAPS, "serverInfo": SERVER_INFO, "instructions": "Dev Loop orchestrator. Start with validate_lanes, then run_lanes (headless) or gate a single lane; read tasks_next / report; write ledger before you stop."}
    if m == "server/discover":  # 2026-07-28 stateless negotiation
        return {"protocolVersions": PROTOCOL_VERSIONS, "capabilities": CAPS, "serverInfo": SERVER_INFO}
    if m in ("notifications/initialized", "initialized"): return None
    if m == "ping": return {}
    if m == "tools/list": return {"tools": TOOLS}
    if m == "tools/call":
        name = p.get("name"); args = p.get("arguments") or {}
        try:
            text, is_err = call(name, args)
        except subprocess.TimeoutExpired:
            text, is_err = "timeout — treat as failure (SKILL §6)", True
        except Exception as e:  # noqa: BLE001 — surface every failure to the host, never silence
            text, is_err = f"{type(e).__name__}: {e}", True
        return {"content": [{"type": "text", "text": text}], "isError": is_err}
    if m in ("resources/list", "prompts/list"): return {m.split("/")[0]: []}
    raise KeyError(m)


def main():
    while True:
        try:
            got = read_message()
        except (json.JSONDecodeError, ValueError) as e:
            write_message({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"parse error: {e}"}}, "ndjson"); continue
        if got is None: return
        msg, framing = got
        if not msg: continue
        if "id" not in msg:  # notification
            try: handle(msg)
            except KeyError: pass
            continue
        try:
            result = handle(msg)
            write_message({"jsonrpc": "2.0", "id": msg["id"], "result": result if result is not None else {}}, framing)
        except KeyError as e:
            write_message({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32601, "message": f"method not found: {e.args[0]}"}}, framing)
        except Exception as e:  # noqa: BLE001
            write_message({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32603, "message": f"{type(e).__name__}: {e}"}}, framing)


if __name__ == "__main__":
    main()
