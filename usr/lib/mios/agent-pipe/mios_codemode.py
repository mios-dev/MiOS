# AI-hint: Provides pure, side-effect-free logic for WS-2 Code Mode, including session ID derivation, podman exec argument construction, and tool-call normalizat...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_lib_mios_agent_pipe_mios_codemode_py.md

from __future__ import annotations

import hashlib
import json
from mios_jsonsalvage import loads_lenient as _loads_lenient
import re
import shlex
from typing import Optional

SUPPORTED_LANGS = ("python", "bash", "sh")
DEFAULT_LANG = "python"

MAX_CODE_CHARS = 64_000
MIN_TIMEOUT_S = 1
MAX_TIMEOUT_S = 600


def normalize_lang(lang: Optional[str]) -> str:
    """Fold a requested language to a supported one; unknown -> DEFAULT_LANG.
    `sh` is kept distinct from `bash` (some sandboxes only ship one)."""
    l = (lang or "").strip().lower()
    if l in SUPPORTED_LANGS:
        return l
    if l in ("py", "python3"):
        return "python"
    if l in ("shell", "/bin/bash"):
        return "bash"
    return DEFAULT_LANG


def clamp_timeout(value, default: int = 60) -> int:
    """Coerce + clamp a timeout into [MIN_TIMEOUT_S, MAX_TIMEOUT_S]. Preserves a
    legit small value; junk -> default. Never returns 0 (an unbounded run)."""
    try:
        t = int(value)
    except (TypeError, ValueError):
        t = int(default)
    if t < MIN_TIMEOUT_S:
        return MIN_TIMEOUT_S
    if t > MAX_TIMEOUT_S:
        return MAX_TIMEOUT_S
    return t


def session_id(conversation_id: Optional[str], fallback: str = "default") -> str:
    """Derive a STABLE, filesystem + Quadlet-instance-safe sandbox id from the
    conversation id, so every Code Mode call in one chat reuses ONE warm sandbox
    (the coderun-sandbox@.container is templated by %i, and %i must be a clean
    token). Empty -> `fallback`. Deterministic: same conversation -> same id."""
    raw = (conversation_id or "").strip() or fallback
    return "cm-" + hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:16]


def extract_code(args: dict) -> str:
    """Pull the snippet from an agent tool-call's args, tolerating the synonym
    keys the planner uses (code / source / script / snippet / program). Returns
    the stripped source ('' if none)."""
    if not isinstance(args, dict):
        return ""
    for k in ("code", "source", "script", "snippet", "program", "command"):
        v = args.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def validate_request(args: dict) -> tuple:
    code = extract_code(args)
    if not code:
        return False, {"error": "no code provided (expected `code`/`source`)"}
    if len(code) > MAX_CODE_CHARS:
        return False, {"error": f"code too large ({len(code)} > {MAX_CODE_CHARS} chars)"}
    a = args if isinstance(args, dict) else {}
    return True, {
        "code": code,
        "lang": normalize_lang(a.get("lang") or a.get("language")),
        "timeout": clamp_timeout(a.get("timeout", a.get("timeout_s", 60))),
        "net": _truthy(a.get("net") if a.get("net") is not None else a.get("network")),
    }


def _truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def is_enabled(cfg: dict) -> bool:
    if not isinstance(cfg, dict):
        return False
    return _truthy(cfg.get("enable", False))


def net_allowed(cfg: dict, requested: bool) -> bool:
    """The effective network decision: the agent may REQUEST net, but the deploy
    must also ALLOW it ([code_mode].allow_net, default off). AND of the two ->
    offline-by-default jail unless BOTH say yes."""
    deploy_ok = _truthy((cfg or {}).get("allow_net", False))
    return bool(requested) and deploy_ok


def podman_exec_argv(container: str, lang: str, src_path: str,
                     podman: str = "podman", init: str = "") -> list:
    interp = "python3" if normalize_lang(lang) == "python" else (
        "bash" if normalize_lang(lang) == "bash" else "sh")
    inner = ([init] if init else []) + [interp, src_path]
    return [podman, "exec", "-i", container, *inner]


def parse_result(stdout: str, stderr: str, returncode: int,
                 max_chars: int = 8000) -> dict:
    """Normalise a sandbox run into the verb's structured envelope. If the
    snippet itself printed a JSON object on stdout (the Code Mode convention --
    the model's code prints its FILTERED result as JSON), surface it under
    `result`; otherwise return raw stdout. Always bounded by `max_chars` so a
    runaway print can't blow the model's context."""
    out = (stdout or "")[:max_chars]
    err = (stderr or "")[:max_chars]
    env: dict = {
        "ok": returncode == 0,
        "exit_code": returncode,
        "stdout": out,
        "stderr": err,
        "sandboxed": True,
    }
    parsed = _try_json_tail(stdout or "")
    if parsed is not None:
        env["result"] = parsed
    return env


def _try_json_tail(text: str):
    """Best-effort: if the LAST non-empty stdout line is a JSON object/array,
    return it (the model's code is asked to print its result as a final JSON
    line). None when there is no parseable trailing JSON."""
    for line in reversed([ln for ln in text.splitlines() if ln.strip()]):
        s = line.strip()
        if (s.startswith("{") and s.endswith("}")) or (
                s.startswith("[") and s.endswith("]")):
            try:
                return _loads_lenient(s)
            except (ValueError, TypeError):
                return None
        break  # only consider the final non-empty line
    return None


def safe_session_token(s: str) -> str:
    """Quadlet %i / dir-name safety net: keep only [a-z0-9-]. Used as a final
    guard if a caller hands a non-session_id() string straight through."""
    return re.sub(r"[^a-z0-9-]", "", (s or "").lower()) or "default"


def build_cli_argv(cli: str, payload: dict, conversation_id: Optional[str],
                   cfg: Optional[dict] = None) -> list:
    """Assemble the argv for the host-side Code Mode CLI (mios-coderun-codemode)
    from a validated payload. The CLI reads the snippet from stdin (avoids any
    shell-quoting hazard with the model's code); flags carry the rest. Pure --
    the caller pipes payload['code'] to the process stdin."""
    cfg = cfg or {}
    argv = [cli, "--lang", normalize_lang(payload.get("lang")),
            "--timeout", str(clamp_timeout(payload.get("timeout", 60))),
            "--session", session_id(conversation_id)]
    if net_allowed(cfg, payload.get("net", False)):
        argv.append("--net")
    return argv


def quote_inline_code(code: str) -> str:
    """Shell-safe single-arg quoting of a snippet, for the rare path that passes
    code as an argument rather than stdin. Prefer stdin; this exists for the
    template/SSOT cmd form."""
    return shlex.quote(code or "")
