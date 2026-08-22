#!/usr/bin/env python3
# AI-hint: An idempotent patch script that modifies hermes_cli/web_server.py to allow the HERMES_PTY_SHELL environment variable to override the default TUI chat with a plain bash shell in the dashboard's /chat tab.
# AI-functions: main
from __future__ import annotations
import re
import sys
import pathlib

MARKER = "# MiOS-patch: HERMES_PTY_SHELL override"

INJECTION = '''    # MiOS-patch: HERMES_PTY_SHELL override
    import shlex as _shlex
    _override = os.environ.get("HERMES_PTY_SHELL")
    if _override:
        _argv = _shlex.split(_override)
        if _argv and os.path.basename(_argv[0]) in ("bash", "sh", "zsh", "fish"):
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

    anchor_re = re.compile(
        r"^(?P<indent>\s+)from hermes_cli\.main import PROJECT_ROOT,\s*_make_tui_argv\s*$",
        re.M,
    )
    m = anchor_re.search(text)
    if not m:
        print("shell-patch: could not locate `from hermes_cli.main import ...` anchor — upstream layout changed?", file=sys.stderr)
        return 2
    indent = m.group("indent")

    indented_injection = "\n".join(
        (indent + line[4:]) if line.startswith("    ") else line
        for line in INJECTION.splitlines()
    ) + "\n"

    if "\nimport pathlib\n" not in text and not re.search(r"^import pathlib\b", text, re.M):
        text = re.sub(
            r"(^import os\s*$)",
            r"\1\nimport pathlib",
            text,
            count=1,
            flags=re.M,
        )
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
