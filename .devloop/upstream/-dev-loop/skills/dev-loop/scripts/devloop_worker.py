#!/usr/bin/env python3
"""
Dev Loop lane worker — drives ONE lane over any OpenAI-compatible /v1/chat/completions endpoint.

Zero third-party dependencies (stdlib only). Works with OpenAI, Azure OpenAI (via base_url), Ollama,
vLLM, LM Studio, llama.cpp server, OpenRouter, LiteLLM, Open WebUI — anything that speaks the
Chat Completions API with `tools` / `tool_calls`.

Usage:
  devloop_worker.py --lane lane.json --skill ../SKILL.md --report report.json [--cwd <worktree>]

Env:
  OPENAI_BASE_URL   (default https://api.openai.com/v1; lane.worker.base_url overrides)
  <api_key_env>     (default OPENAI_API_KEY; name taken from lane.worker.api_key_env). Never printed.
  DEVLOOP_MODEL     (fallback if lane.worker.model unset)

Contract enforced here, not left to the model:
  * writes/edits only inside lane.owned_paths; reads only inside the worktree
  * no git add/commit/push, no generator runs (blocked command patterns)
  * hard timeouts; timeout == failure
  * the lane ends only via the `report` tool; max_turns / timeout_s produce a synthetic
    status=budget report so the orchestrator never sees silence
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_OUT = 12_000  # chars of stdout/stderr returned to the model per call
BLOCKED_CMD = re.compile(
    r"(^|[;&|]\s*)git\s+(add|commit|push|rebase|reset\s+--hard|checkout\s+--|clean|worktree)\b"
    r"|(^|[;&|]\s*)(sudo|rm\s+-rf\s+/|curl[^|]*\|\s*(sh|bash)|wget[^|]*\|\s*(sh|bash))\b",
    re.IGNORECASE,
)
SECRET_LEAK = re.compile(r"\b(printenv|env)\s*$|\bcat\s+[^\s]*\.env\b|\becho\s+\$\{?[A-Z_]*(KEY|TOKEN|SECRET|PASSWORD)", re.I)


def log(msg: str) -> None:
    print(f"[devloop-worker] {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- API client
class Client:
    def __init__(self, base_url: str, api_key: str | None, model: str, temperature: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature

    def chat(self, messages: list[dict], tools: list[dict], tool_choice: str | dict = "auto") -> dict:
        body = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
            "temperature": self.temperature,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {})},
            method="POST",
        )
        backoff = 2.0
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=600) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                text = e.read().decode("utf-8", "replace")[:2000]
                if e.code in (408, 409, 425, 429, 500, 502, 503, 504) and attempt < 5:
                    log(f"HTTP {e.code}; retry in {backoff:.0f}s: {text[:200]}")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise RuntimeError(f"HTTP {e.code} from {self.base_url}: {text}") from None
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < 5:
                    log(f"network error; retry in {backoff:.0f}s: {e}")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise
        raise RuntimeError("unreachable")


# --------------------------------------------------------------------------- tool implementations
class Tools:
    def __init__(self, root: Path, owned: list[str]):
        self.root = root.resolve()
        self.owned = owned

    def _resolve(self, rel: str) -> Path:
        p = (self.root / rel).resolve()
        if self.root != p and self.root not in p.parents:
            raise PermissionError(f"path escapes worktree: {rel}")
        return p

    def _assert_owned(self, rel: str) -> None:
        norm = rel.replace("\\", "/").lstrip("./")
        for pat in self.owned:
            pat = pat.replace("\\", "/")
            if fnmatch.fnmatch(norm, pat) or norm.startswith(pat.rstrip("/*") + "/") or norm == pat:
                return
        raise PermissionError(f"path not in owned_paths: {rel} (owned: {self.owned})")

    def run_command(self, command: str, timeout_s: int, reason: str) -> dict:
        if BLOCKED_CMD.search(command):
            return {"exit": 126, "timed_out": False, "stdout": "", "stderr": "BLOCKED: git state changes / privileged ops are orchestrator-only (SKILL.md §11)."}
        if SECRET_LEAK.search(command):
            return {"exit": 126, "timed_out": False, "stdout": "", "stderr": "BLOCKED: would print secrets into the transcript (SKILL.md §10)."}
        timeout_s = max(1, min(int(timeout_s), 3600))
        env = {**os.environ, "CI": "1", "GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat", "PAGER": "cat", "DEBIAN_FRONTEND": "noninteractive"}
        shell = ["pwsh", "-NoProfile", "-NonInteractive", "-Command"] if os.name == "nt" else ["sh", "-c"]
        try:
            cp = subprocess.run(shell + [command], cwd=self.root, env=env, capture_output=True, text=True, timeout=timeout_s, stdin=subprocess.DEVNULL)
            return {"exit": cp.returncode, "timed_out": False, "stdout": cp.stdout[-MAX_OUT:], "stderr": cp.stderr[-MAX_OUT:]}
        except subprocess.TimeoutExpired as e:
            return {"exit": 124, "timed_out": True, "stdout": (e.stdout or "")[-MAX_OUT:] if isinstance(e.stdout, str) else "", "stderr": f"TIMEOUT after {timeout_s}s — treat as failure."}

    def read_file(self, path: str, start_line: int, end_line: int) -> dict:
        p = self._resolve(path)
        if not p.is_file():
            return {"error": f"not a file: {path}"}
        lines = p.read_text("utf-8", errors="replace").splitlines()
        s = max(1, start_line)
        e = len(lines) if end_line == -1 else min(end_line, len(lines))
        body = "\n".join(f"{i}\t{lines[i - 1]}" for i in range(s, e + 1))
        return {"path": path, "total_lines": len(lines), "content": body[:MAX_OUT * 4]}

    def write_file(self, path: str, content: str) -> dict:
        self._assert_owned(path)
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, "utf-8")
        return {"ok": True, "path": path, "bytes": len(content.encode("utf-8"))}

    def edit_file(self, path: str, old_str: str, new_str: str) -> dict:
        self._assert_owned(path)
        p = self._resolve(path)
        if not p.is_file():
            return {"error": f"not a file: {path}"}
        text = p.read_text("utf-8")
        n = text.count(old_str)
        if n != 1:
            return {"error": f"old_str matched {n} times; must match exactly once"}
        p.write_text(text.replace(old_str, new_str, 1), "utf-8")
        return {"ok": True, "path": path}

    def list_files(self, path: str) -> dict:
        self._resolve(path)
        cp = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", path], cwd=self.root, capture_output=True, text=True)
        return {"files": cp.stdout.splitlines()[:2000], "exit": cp.returncode, "stderr": cp.stderr[-1000:]}


# --------------------------------------------------------------------------- prompt
def build_system(skill_md: str, lane: dict, root: Path) -> str:
    body = skill_md.split("---", 2)[2] if skill_md.startswith("---") else skill_md
    return (
        f"{body}\n\n---\n\n# LANE CONTRACT (binding)\n"
        f"- lane id: {lane['id']}\n- worktree: {root}\n- role: {lane.get('role', 'worker')}\n"
        f"- owned_paths (you may modify ONLY these): {json.dumps(lane['owned_paths'])}\n"
        f"- read_paths: {json.dumps(lane.get('read_paths', []))}\n"
        f"- positive_cmd: {lane['positive_cmd']}\n- negative_control_cmd: {lane['negative_control_cmd']}\n"
        f"- negative_expect (regex): {lane['negative_expect']}\n"
        f"- full_gate_cmd: {lane.get('full_gate_cmd', '') or '(none)'}\n"
        f"- max_turns: {lane['worker']['max_turns']}; timeout_s: {lane['worker']['timeout_s']}\n"
        "- You MUST NOT run git add/commit/push, generators, or edit contract files; the orchestrator does that.\n"
        "- You MUST run both controls yourself and report their real exit codes before status=done.\n"
        "- You MUST end by calling the `report` tool. Every response should be a tool call until then.\n"
        f"\n# OBJECTIVE\n{lane['objective']}\n\n{lane.get('extra_context', '')}"
    )


# --------------------------------------------------------------------------- main loop
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True)
    ap.add_argument("--skill", default=str(HERE.parent / "SKILL.md"))
    ap.add_argument("--tools", default=str(HERE.parent / "assets" / "openai-tools.json"))
    ap.add_argument("--report", required=True)
    ap.add_argument("--cwd", default=os.getcwd())
    a = ap.parse_args()

    lane = json.loads(Path(a.lane).read_text("utf-8"))
    w = lane.setdefault("worker", {})
    w.setdefault("max_turns", 40)
    w.setdefault("timeout_s", 1800)
    w.setdefault("temperature", 0)
    w.setdefault("api_key_env", "OPENAI_API_KEY")
    model = w.get("model") or os.environ.get("DEVLOOP_MODEL")
    if not model:
        log("no model: set lane.worker.model or DEVLOOP_MODEL")
        return 64
    base_url = w.get("base_url") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.environ.get(w["api_key_env"])
    if not api_key:
        log(f"warning: ${w['api_key_env']} is unset (fine for local endpoints)")

    root = Path(a.cwd).resolve()
    tools_def = json.loads(Path(a.tools).read_text("utf-8"))
    tools = Tools(root, lane["owned_paths"])
    client = Client(base_url, api_key, model, float(w["temperature"]))
    messages = [
        {"role": "system", "content": build_system(Path(a.skill).read_text("utf-8"), lane, root)},
        {"role": "user", "content": "Begin. Orient (git status, git log --oneline -15, discover gates), then execute the loop. Finish with `report`."},
    ]

    deadline = time.time() + int(w["timeout_s"])
    report: dict | None = None
    turns = 0
    while turns < int(w["max_turns"]) and time.time() < deadline:
        turns += 1
        resp = client.chat(messages, tools_def)
        choice = resp["choices"][0]
        msg = choice["message"]
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        calls = msg.get("tool_calls") or []
        if not calls:
            messages.append({"role": "user", "content": "No tool call received. Continue with a tool call; end with `report`."})
            continue
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError as e:
                result = {"error": f"malformed arguments: {e}"}
            else:
                if name == "report":
                    report = args
                    result = {"ok": True}
                elif hasattr(tools, name):
                    try:
                        result = getattr(tools, name)(**args)
                    except (PermissionError, TypeError, OSError) as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"unknown tool {name}"}
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
            log(f"turn {turns}: {name} -> {str(result)[:160]}")
        if report is not None:
            break

    if report is None:
        report = {
            "status": "budget",
            "objective": lane["objective"],
            "summary": f"Worker exhausted max_turns={w['max_turns']} or timeout_s={w['timeout_s']} without calling report.",
            "changed_paths": [], "positive_controls": [], "negative_controls": [],
            "full_gate": {"cmd": "", "exit": -1}, "phantoms_dismissed": [],
            "unverified": ["everything — no report emitted"], "contract_updates": [], "questions": [],
            "next": "Orchestrator: park the diff (git diff > lane.patch), restore, and re-plan with a narrower objective.",
        }
    report["_meta"] = {"lane": lane["id"], "turns": turns, "model": model, "base_url": base_url, "worktree": str(root)}
    Path(a.report).write_text(json.dumps(report, indent=2), "utf-8")
    log(f"report written: {a.report} status={report['status']}")
    return 0 if report["status"] == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
