#!/usr/bin/env python3
# AI-hint: Structural governor-coverage gate for mios-daemon: asserts every autonomous *_loop consults the host-pressure gate, that the SSOT [daemon]...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Fail if the daemon governor has a hole: an ungated loop, a dead knob, or a drifted fallback."""
import os
import re
import subprocess
import sys
import tomllib

ROOT = os.environ.get("MIOS_ROOT", ".")
DAEMON = os.path.join(ROOT, "usr/libexec/mios/mios-daemon")
SSOT = os.path.join(ROOT, "usr/share/mios/mios.toml")
CHAT = os.path.join(ROOT, "usr/lib/mios/agent-pipe/mios_pipe/routing/chat.py")

# Loops that serve interactive requests rather than initiating autonomous work;
# gating these would throttle a human, which is the opposite of the intent.
EXEMPT_LOOPS = {"daemon_agent_server_loop"}
# Knobs consumed outside the daemon (agent-pipe owns the budget plane).
ELSEWHERE = {"conversation_token_ceil", "autonomous_token_ceil",
             "autonomous_max_inflight", "window_s"}

def loops_missing_pressure_gate(src: str) -> list:
    lines = src.split("\n")
    starts = [(i, m.group(1)) for i, l in enumerate(lines)
              if (m := re.match(r"^def (\w+_loop)\(", l))]
    missing = []
    for idx, (i, name) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        if name in EXEMPT_LOOPS:
            continue
        if "_pressure_should_skip" not in "\n".join(lines[i:end]):
            missing.append(name)
    return missing

def _consumer_sources(root: str) -> list:
    """Code that may consume a knob: no test_* files, no comment lines -- a knob
    merely NAMED in a docstring or an AI-hint is not a consumer."""
    out = []
    for base in ("usr/libexec/mios", "usr/lib/mios"):
        for dirpath, _, names in os.walk(os.path.join(root, base)):
            if "__pycache__" in dirpath:
                continue
            for n in names:
                if n.startswith("test_") or not (n.endswith(".py") or n.startswith("mios-")):
                    continue
                try:
                    text = open(os.path.join(dirpath, n), encoding="utf-8",
                                errors="replace").read()
                except OSError:
                    continue
                code = "\n".join(l for l in text.split("\n")
                                 if not l.lstrip().startswith("#"))
                out.append(code)
    return out

def dead_knobs(root: str, keys: list) -> list:
    sources = _consumer_sources(root)
    dead = []
    for key in keys:
        if key in ELSEWHERE:
            continue
        if not any(f'"{key}"' in s or f"'{key}'" in s for s in sources):
            dead.append(key)
    return dead

def drifted_fallbacks(ssot: dict) -> list:
    if not os.path.isfile(CHAT):
        return []
    text = open(CHAT, encoding="utf-8").read()
    out = []
    for key, want in ssot.get("budget", {}).items():
        m = re.search(rf'"{key}",\s*([0-9_]+)', text)
        if m and int(m.group(1).replace("_", "")) != int(want):
            out.append(f"{key}: fallback {m.group(1)} != SSOT {want}")
    return out

def main() -> int:
    src = open(DAEMON, encoding="utf-8").read()
    data = tomllib.load(open(SSOT, "rb"))
    daemon_keys = [k for k, v in data.get("daemon", {}).items() if not isinstance(v, dict)]
    budget_keys = [k for k, v in data.get("budget", {}).items() if not isinstance(v, dict)]
    bad = []
    bad += [f"autonomous loop without the host-pressure gate: {n}"
            for n in loops_missing_pressure_gate(src)]
    bad += [f"SSOT knob declared but never consumed: [daemon].{k}"
            for k in dead_knobs(ROOT, daemon_keys)]
    bad += [f"agent-pipe budget fallback drifted from the SSOT -- {d}"
            for d in drifted_fallbacks(data)]
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    total = len(re.findall(r"^def \w+_loop\(", src, re.M))
    print(f"daemon governor complete ({total - len(EXEMPT_LOOPS)} autonomous loops gated, "
          f"{len(daemon_keys)} [daemon] + {len(budget_keys)} [budget] knobs consumed)")
    return 0

sys.exit(main())
