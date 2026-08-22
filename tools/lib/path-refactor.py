# AI-hint: !/usr/bin/env python3 Refactors hardcoded MiOS system paths into environment variable constants (e.g., ${MIOS_LOG_DIR}) in configuration files while preserving comm...
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_lib_path_refactor_py.md

import re, sys
from pathlib import Path

SUBS = [
    ("/usr/lib/mios/logs",   "${MIOS_LOG_DIR}"),
    ("/usr/libexec/mios",    "${MIOS_LIBEXEC_DIR}"),
    ("/usr/share/mios",      "${MIOS_SHARE_DIR}"),
    ("/usr/lib/mios",        "${MIOS_USR_DIR}"),
    ("/var/lib/mios",        "${MIOS_VAR_DIR}"),
    ("/etc/mios",            "${MIOS_ETC_DIR}"),
]

_DEFAULT_PATTERN = re.compile(r"\$\{MIOS_[A-Z_]+_DIR:=")
_BOOTSTRAP_PATTERN = re.compile(r"\bsource\b.*\bpaths\.sh\b")

def substitute_line(line: str) -> str:
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return line
    if _DEFAULT_PATTERN.search(line):
        return line
    if _BOOTSTRAP_PATTERN.search(line):
        return line
    out = line
    for old, new in SUBS:
        out = re.sub(re.escape(old) + r"(?![-*\w])", new, out)
    return out

def process(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    new_lines = [substitute_line(ln) for ln in text.splitlines(keepends=True)]
    new = "".join(new_lines)
    if new == text:
        return False
    path.write_text(new, encoding="utf-8", errors="surrogateescape")
    return True

if __name__ == "__main__":
    changed = 0
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.is_file():
            print(f"SKIP {arg} (not a file)", file=sys.stderr); continue
        if process(p):
            print(f"changed: {arg}")
            changed += 1
    print(f"\n{changed} file(s) changed")
