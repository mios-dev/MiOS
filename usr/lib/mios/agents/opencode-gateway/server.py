#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MiOS opencode → OpenAI /v1 gateway shim.

opencode (the SST/charm CLI coding agent) speaks its own CLI protocol, not the
OpenAI /v1 chat-completions contract that the MiOS agent-pipe council expects.
This shim wraps `opencode run` behind a minimal OpenAI-compatible HTTP server so
opencode can be dispatched as a first-class /v1 council peer (like Hermes at
:8642), without teaching agent-pipe a bespoke protocol.

Endpoints:
  GET  /v1/models            → advertise the single opencode model id
  POST /v1/chat/completions  → run opencode, return an OpenAI chat.completion
                               (or an SSE delta stream when stream=true)

Config (all via env, SSOT-rendered by the unit / userenv.sh):
  MIOS_PORT_OPENCODE_GATEWAY   listen port (default 8633)
  MIOS_OPENCODE_BIN            path to the opencode binary
  MIOS_OPENCODE_MODEL          model id to advertise/forward (ONE canonical id;
                               must match [agents.opencode].model + the key in
                               opencode.json)
  MIOS_OPENCODE_PROVIDER       opencode provider name from opencode.json
                               (default "ollama"); used to build the `-m
                               provider/model` selector
  MIOS_OPENCODE_CONFIG         explicit path to opencode.json; exported to the
                               child as OPENCODE_CONFIG so opencode does NOT
                               depend on a hardcoded /root/.config location
  MIOS_OPENCODE_HOST           bind host (default 127.0.0.1)
  MIOS_OPENCODE_TIMEOUT_S      per-run timeout seconds (default 90; SSOT key
                               [ai].opencode_gateway_timeout_s). Legacy
                               MIOS_OPENCODE_TIMEOUT is still honoured as a
                               fallback for older overlays.
"""
import os
import sys
import json
import time
import uuid
import subprocess

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# ---------------------------------------------------------------------------
# SSOT-rendered config (env-first; defaults match mios.toml slots)
# ---------------------------------------------------------------------------
HOST = os.environ.get("MIOS_OPENCODE_HOST", "127.0.0.1")
PORT = int(os.environ.get("MIOS_PORT_OPENCODE_GATEWAY", "8633"))
OPENCODE_BIN = os.environ.get(
    "MIOS_OPENCODE_BIN", "/usr/lib/mios/agents/opencode/bin/opencode"
)
# ONE canonical model id, shared with [agents.opencode].model + opencode.json.
OPENCODE_MODEL = os.environ.get("MIOS_OPENCODE_MODEL", "mios-opencode:latest")
# opencode provider name as declared in opencode.json (e.g. "ollama").
OPENCODE_PROVIDER = os.environ.get("MIOS_OPENCODE_PROVIDER", "ollama")
# Explicit config location (no hardcoded /root/.config/opencode). Exported to
# the child process as OPENCODE_CONFIG.
OPENCODE_CONFIG = os.environ.get(
    "MIOS_OPENCODE_CONFIG", "/etc/mios/opencode/opencode.json"
)
# Per-run timeout. Canonical SSOT key is MIOS_OPENCODE_TIMEOUT_S (mios.toml
# [ai].opencode_gateway_timeout_s, mirrored by the unit). Fall back to the
# legacy MIOS_OPENCODE_TIMEOUT for older overlays, then a 90s default that
# matches the SSOT vendor value (so the swarm fan-out drops opencode harmlessly
# under VRAM pressure rather than hanging on the old 600s).
TIMEOUT = int(
    os.environ.get("MIOS_OPENCODE_TIMEOUT_S")
    or os.environ.get("MIOS_OPENCODE_TIMEOUT")
    or "90"
)


def _selector(model: str) -> str:
    """Build opencode's `provider/model` selector.

    opencode's `-m` flag wants `<provider>/<model>`; if the caller already
    passed a qualified id (contains a slash) honour it verbatim.
    """
    if "/" in model:
        return model
    return f"{OPENCODE_PROVIDER}/{model}"


def _flatten_messages(messages):
    """Collapse an OpenAI messages array into a single opencode `run` prompt.

    opencode's non-interactive `run` takes one prompt string, so we serialise
    the whole conversation (system + history + latest user turn) into a clearly
    delimited transcript instead of dropping everything but the last user line.
    Returns (system_prompt, prompt_text).
    """
    system_parts = []
    convo = []
    for m in messages or []:
        role = (m.get("role") or "user").lower()
        content = m.get("content", "")
        # OpenAI content can be a list of parts; flatten to text.
        if isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )
        else:
            text = str(content)
        if not text.strip():
            continue
        if role == "system":
            system_parts.append(text)
        elif role == "assistant":
            convo.append(f"Assistant:\n{text}")
        elif role == "tool":
            convo.append(f"Tool result:\n{text}")
        else:  # user (and any unknown role)
            convo.append(f"User:\n{text}")

    system_prompt = "\n\n".join(system_parts).strip()
    transcript = "\n\n".join(convo).strip()

    if system_prompt:
        prompt = (
            f"# System instructions\n{system_prompt}\n\n"
            f"# Conversation\n{transcript}\n\n"
            f"# Task\nRespond as the assistant to the latest user turn above."
        )
    else:
        prompt = transcript
    return system_prompt, prompt


def _run_opencode(prompt: str, model: str):
    """Invoke `opencode run` with the unified config + model selector.

    Returns the assistant text. Raises on failure.
    """
    env = dict(os.environ)
    # Point opencode at the unified config explicitly (no /root/.config dep).
    env["OPENCODE_CONFIG"] = OPENCODE_CONFIG
    # XDG fallback so any opencode build that ignores OPENCODE_CONFIG still
    # finds the file under <dir>/opencode/opencode.json.
    cfg_dir = os.path.dirname(os.path.dirname(OPENCODE_CONFIG))
    if cfg_dir:
        env.setdefault("XDG_CONFIG_HOME", cfg_dir)

    cmd = [OPENCODE_BIN, "run", "-m", _selector(model), prompt]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=TIMEOUT, env=env
    )
    out = (proc.stdout or "").strip()
    if not out:
        out = (proc.stderr or "").strip()
    if proc.returncode != 0 and not out:
        raise RuntimeError(
            f"opencode exited {proc.returncode} with no output"
        )
    return out


class Handler(BaseHTTPRequestHandler):
    # Quieten the default stderr access-log spam (journald captures stdout).
    def log_message(self, fmt, *args):
        return

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

    def _sse_write(self, obj):
        self.wfile.write(b"data: " + json.dumps(obj).encode("utf-8") + b"\n\n")
        self.wfile.flush()

    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models":
            self._send(200, {
                "object": "list",
                "data": [
                    {"id": OPENCODE_MODEL, "object": "model", "owned_by": "mios"}
                ],
            })
        elif self.path.rstrip("/") in ("/health", "/healthz"):
            self._send(200, {"status": "ok", "model": OPENCODE_MODEL})
        else:
            self._send(404, {"error": {"message": "not found"}})

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._send(404, {"error": {"message": "not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            req = json.loads(raw or b"{}")
        except Exception as e:
            self._send(400, {"error": {"message": f"bad request: {e}"}})
            return

        messages = req.get("messages", [])
        # This gateway serves exactly ONE model (opencode itself). The caller's
        # `model` is just a routing label -- the agent-pipe sends the AGENT NAME
        # ("opencode"), which _selector would turn into the bogus "ollama/opencode"
        # -> "Model not found" (operator 2026-06-01 live error). ALWAYS use our
        # own configured OPENCODE_MODEL (mios-opencode:latest) regardless of what
        # the caller asked for; only honour a caller id that is already a real,
        # provider-qualified opencode model (contains '/').
        _req_model = str(req.get("model") or "")
        model = _req_model if "/" in _req_model else OPENCODE_MODEL
        stream = bool(req.get("stream", False))

        # Pass the FULL conversation (system + history) to opencode, not just
        # the last user message.
        _system, prompt = _flatten_messages(messages)

        cmpl_id = "chatcmpl-" + uuid.uuid4().hex[:24]
        created = int(time.time())

        if stream:
            self._stream(cmpl_id, created, model, prompt)
            return

        try:
            out = _run_opencode(prompt, model)
        except Exception as e:
            self._send(500, {"error": {"message": f"opencode failed: {e}"}})
            return

        self._send(200, {
            "id": cmpl_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": out},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        })

    def _stream(self, cmpl_id, created, model, prompt):
        """Emit a well-formed OpenAI SSE delta stream.

        opencode's `run` is not token-incremental over a stable public API, so
        we run it to completion then chunk the result into SSE deltas. This
        keeps stream=true callers (agent-pipe council) happy with a valid
        chat.completion.chunk stream terminated by [DONE].
        """
        try:
            out = _run_opencode(prompt, model)
            err = None
        except Exception as e:
            out, err = "", str(e)

        self._sse_headers()

        # role delta first
        self._sse_write({
            "id": cmpl_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None,
            }],
        })

        if err:
            self._sse_write({
                "id": cmpl_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"opencode failed: {err}"},
                    "finish_reason": None,
                }],
            })
        else:
            # Chunk into reasonably sized content deltas.
            step = 512
            for i in range(0, len(out), step):
                self._sse_write({
                    "id": cmpl_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": out[i:i + step]},
                        "finish_reason": None,
                    }],
                })

        # terminal chunk
        self._sse_write({
            "id": cmpl_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }],
        })
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def main():
    addr = (HOST, PORT)
    httpd = ThreadingHTTPServer(addr, Handler)
    sys.stderr.write(
        f"[opencode-gateway] listening on http://{HOST}:{PORT}/v1 "
        f"(model={OPENCODE_MODEL}, bin={OPENCODE_BIN})\n"
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
