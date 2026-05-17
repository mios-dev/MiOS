#!/usr/bin/env python3
"""In-place patch of hermes_cli/web_server.py so the /api/pty endpoint
honors HERMES_PTY_SHELL env var.

Upstream hermes-agent hardcodes `_resolve_chat_argv` to spawn
`hermes --tui` (the Node-built TUI chat). MiOS-DEV wants a plain bash
shell in the dashboard's /chat tab (operator directive 2026-05-17:
"do we have a react window for terminal(s)?" -> chose "plain bash").
Setting `HERMES_PTY_SHELL=/bin/bash` (or any shell binary) replaces
the hardcoded TUI spawn with the requested shell.

Idempotent: rerunning is a no-op once the marker comment is present.
Safe: leaves the upstream fallback when HERMES_PTY_SHELL is unset.

Usage:
    hermes-dashboard-shell-patch.py /path/to/hermes_cli/web_server.py
"""
from __future__ import annotations
import re
import sys
import pathlib

MARKER = "# MiOS-patch: HERMES_PTY_SHELL override"

INJECTION = '''    # MiOS-patch: HERMES_PTY_SHELL override
    # When set (e.g. HERMES_PTY_SHELL=/bin/bash), the /api/pty endpoint
    # spawns the requested shell instead of `hermes --tui`. Lets the
    # dashboard's /chat tab serve a plain bash prompt with xterm.js
    # rendering it in the browser. Loopback + session-token already
    # protect the endpoint. Operator directive 2026-05-17.
    import shlex as _shlex
    _override = os.environ.get("HERMES_PTY_SHELL")
    if _override:
        _argv = _shlex.split(_override)
        if _argv and os.path.basename(_argv[0]) in ("bash", "sh", "zsh", "fish"):
            # Login + interactive so .bashrc/.profile load (PATH, aliases, history)
            if "-l" not in _argv and "--login" not in _argv:
                _argv.insert(1, "-l")
            if "-i" not in _argv:
                _argv.insert(1 if "-l" in _argv else 0, "-i")
        _env = os.environ.copy()
        _env.setdefault("TERM", "xterm-256color")
        _env.setdefault("LANG", "C.UTF-8")
        return _argv, str(pathlib.Path.home()), _env

'''


def main(path: str) -> int:
    p = pathlib.Path(path)
    if not p.is_file():
        print(f"shell-patch: file not found: {p}", file=sys.stderr)
        return 1

    text = p.read_text(encoding="utf-8")
    if MARKER in text:
        print("shell-patch: already patched (idempotent no-op)")
        return 0

    # Inject ABOVE the first statement of `_resolve_chat_argv`, which
    # is the line `    from hermes_cli.main import PROJECT_ROOT, _make_tui_argv`.
    # Earlier versions of this script tried to anchor on (signature +
    # optional docstring) via a single multi-line regex; that matched
    # the closing `"""` greedily and ended up splicing the injection
    # INSIDE the docstring -- function compiled but the override was
    # part of the doc-string literal and never executed. The line-based
    # approach below operates on a single anchor line and inserts a
    # block right above it with matching indentation; impossible to
    # corrupt the docstring this way.
    anchor_re = re.compile(
        r"^(?P<indent>\s+)from hermes_cli\.main import PROJECT_ROOT,\s*_make_tui_argv\s*$",
        re.M,
    )
    m = anchor_re.search(text)
    if not m:
        print("shell-patch: could not locate `from hermes_cli.main import ...` anchor — upstream layout changed?", file=sys.stderr)
        return 2
    indent = m.group("indent")

    # Re-indent the INJECTION block (currently 4-space) to match
    indented_injection = "\n".join(
        (indent + line[4:]) if line.startswith("    ") else line
        for line in INJECTION.splitlines()
    ) + "\n"

    # Ensure `import pathlib` exists at module top (used by the patch
    # to resolve home dir). Idempotent.
    if "\nimport pathlib\n" not in text and not re.search(r"^import pathlib\b", text, re.M):
        text = re.sub(
            r"(^import os\s*$)",
            r"\1\nimport pathlib",
            text,
            count=1,
            flags=re.M,
        )
        # Re-locate the anchor (offsets shifted)
        m = anchor_re.search(text)
        if not m:
            print("shell-patch: anchor lost after pathlib import injection", file=sys.stderr)
            return 3

    insert_at = m.start()
    new_text = text[:insert_at] + indented_injection + text[insert_at:]
    p.write_text(new_text, encoding="utf-8")
    print(f"shell-patch: injected HERMES_PTY_SHELL override into {p}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <web_server.py>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
