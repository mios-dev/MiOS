# AI-hint: Pure PTY-session protocol for the persistent shell substrate (SHELL-01).
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_pipe_routing_pty_py.md
"""Pure protocol for the persistent shell substrate (SHELL-01)."""

from __future__ import annotations

import re
import secrets
import time
from typing import Optional

__all__ = ["session_key", "session_path", "tmux_argv", "tmux_conf", "new_nonce",
           "session_init_cmd",
           "wrap_command", "parse_result", "is_idle",
           "MARKER_PREFIX", "SESSION_PREFIX"]

# The sentinel a wrapped command prints when it finishes. It carries a nonce
# minted per command, so output that echoes an OLD marker (or guesses at the
# shape) does not read as this command completing.
MARKER_PREFIX = "__MIOS_PTY__"
SESSION_PREFIX = "mios-"

_SAFE = re.compile(r"[^A-Za-z0-9_-]+")
_NONCE_RE = re.compile(r"^[0-9a-f]{16,}$")


def session_key(session_id, *, max_len: int = 48) -> str:
    """A tmux-safe session name: unsafe chars collapse, namespaced, length-capped
    with a digest tail so two long ids never collide. See ch56."""
    raw = "" if session_id is None else str(session_id)
    cleaned = _SAFE.sub("-", raw).strip("-")
    if not cleaned:
        import hashlib
        cleaned = hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:16]
    elif len(cleaned) > max_len:
        # Truncating alone would let two long ids collide; keep a digest tail.
        import hashlib
        digest = hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:8]
        cleaned = cleaned[: max_len - 9] + "-" + digest
    return SESSION_PREFIX + cleaned


def session_path(session_id, root: str) -> str:
    """The per-session state dir under `root`. Uses session_key, so it inherits
    the same escape-proofing -- a `../` in the id cannot walk out."""
    return f"{root.rstrip('/')}/{session_key(session_id)}"


def new_nonce() -> str:
    """A fresh per-command nonce. 128 bits: an attacker who controls command
    output cannot guess the marker for the command currently in flight."""
    return secrets.token_hex(16)


def tmux_conf(history_limit: int = 50000) -> str:
    """The tmux.conf every invocation is started with. history-limit has to
    arrive this way, not via set-option -- why: ch56."""
    return f"set -g history-limit {int(history_limit)}\n"


def tmux_argv(action: str, session_id, *, command: str = "",
              socket_name: str = "mios", shell: str = "/bin/bash",
              conf_path: str = "") -> list:
    """argv for one tmux action against this session. Returns [] for an unknown
    action rather than guessing -- a mistyped action must not run something."""
    key = session_key(session_id)
    base = ["tmux"]
    if conf_path:
        base += ["-f", conf_path]
    base += ["-L", socket_name]
    if action == "new":
        return base + ["new-session", "-d", "-s", key, shell]
    if action == "send":
        return base + ["send-keys", "-t", key, command, "Enter"]
    if action == "capture":
        return base + ["capture-pane", "-p", "-J", "-S", "-", "-t", key]
    if action == "kill":
        return base + ["kill-session", "-t", key]
    if action == "has":
        return base + ["has-session", "-t", key]
    if action == "list":
        return base + ["list-sessions", "-F", "#{session_name} #{session_activity}"]
    return []


def session_init_cmd() -> str:
    """First line into a new session: silence the PTY echo and the prompt, so a
    capture is output rather than a terminal transcript. See ch56."""
    return "stty -echo 2>/dev/null; PS1=''; PS2=''; clear 2>/dev/null || true\n"


def wrap_command(command: str, nonce: str) -> str:
    """Frame `command` between BEGIN/END sentinels carrying a per-command nonce.
    Printed in two pieces so the PTY echo cannot parse as the result; see ch56."""
    if not nonce or not _NONCE_RE.match(str(nonce)):
        raise ValueError("wrap_command requires a hex nonce from new_nonce()")
    n = str(nonce)
    # printf, not echo: no backslash-escape interpretation of $PWD.
    return (f"printf '%s%s\\n' \"{MARKER_PREFIX}\" \"{n}-BEGIN\"\n"
            f"{command}\n"
            f"printf '%s%s\\n' \"{MARKER_PREFIX}\" \"{n} $? $PWD\"\n")


def parse_result(raw: str, nonce: str) -> Optional[dict]:
    """-> {output, exit_code, cwd}, or None while unfinished. Output is exactly
    the BEGIN..END span; only this nonce counts, last END wins. See ch56."""
    if not raw or not nonce:
        return None
    n = str(nonce)
    end_needle = MARKER_PREFIX + n + " "
    end_idx = raw.rfind("\n" + end_needle)
    if end_idx < 0 and raw.startswith(end_needle):
        end_idx = -1  # marker is the very first line
    elif end_idx < 0:
        return None
    marker_start = 0 if end_idx < 0 else end_idx + 1
    line_end = raw.find("\n", marker_start)
    marker_line = raw[marker_start:line_end if line_end != -1 else len(raw)]
    parts = marker_line.split(" ", 2)
    exit_code, cwd = None, ""
    if len(parts) >= 2:
        try:
            exit_code = int(parts[1])
        except ValueError:
            exit_code = None
    if len(parts) >= 3:
        cwd = parts[2].strip()

    body = raw[:marker_start]
    begin_needle = MARKER_PREFIX + n + "-BEGIN"
    b_idx = body.rfind(begin_needle)
    if b_idx >= 0:
        nl = body.find("\n", b_idx)
        body = body[nl + 1:] if nl != -1 else ""
    return {"output": body.strip("\n"), "exit_code": exit_code, "cwd": cwd}


def is_idle(last_activity, now=None, *, idle_s: float = 1800.0) -> bool:
    """True when a session has been idle longer than `idle_s` -- the reaper's
    only decision. A missing or unparseable timestamp reads as NOT idle, so a
    session is never killed on bad bookkeeping."""
    try:
        last = float(last_activity)
    except (TypeError, ValueError):
        return False
    if last <= 0:
        return False
    current = float(now) if now is not None else time.time()
    return (current - last) > float(idle_s)
