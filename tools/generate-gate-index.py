#!/usr/bin/env python3
# AI-hint: MiOS system and orchestration module providing generate-gate-index capabilities.
# AI-functions: main

"""
tools/generate-gate-index.py
Generates usr/share/mios/reference/drift-gate-index.tsv from automation/98-drift-checks.sh.
Enforces 1:1 ordinal numbering for every registered drift-check in main() order.
"""

import os
import sys
import re

_ECHO = re.compile(r'echo\s+"\[98-drift-checks\]\s+(?:\(\d+\)\s+)?([^"]+)"')
_RUN_PY = re.compile(r'_run_py_check\s+\S+\s+(?:"([^"]+)"|(\S+))')
_HINT = re.compile(r"#\s*AI-hint:\s*(.+)")

def _body(lines, name):
    """The function's OWN lines; a one-liner's brace never starts a line."""
    opener = re.compile(r"^\s*" + re.escape(name) + r"\(\)\s*\{")
    for i, ln in enumerate(lines):
        if not opener.match(ln):
            continue
        if ln.rstrip().endswith("}"):
            return [ln[ln.index("{") + 1:ln.rstrip().rindex("}")]]
        out = []
        for nxt in lines[i + 1:]:
            if nxt.startswith("}"):
                return out
            out.append(nxt)
        return out
    return []

def _hint_of(root, command):
    """First sentence of the delegated tool's AI-hint header.

    A command carrying a bare sub-command word runs one check out of a
    multi-check module, so the module's hint describes the module, not this row.
    """
    parts = command.strip().rstrip(";").strip().split()
    if not parts:
        return ""
    if any(not p.startswith("-") for p in parts[1:]):
        return ""
    path = os.path.join(root, parts[0])
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, ln in enumerate(fh):
            if i > 8:
                break
            m = _HINT.match(ln.strip())
            if m:
                text = m.group(1).strip()
                first = re.split(r"(?<=[a-z0-9)])\.\s+", text, maxsplit=1)[0]
                if first.endswith("..."):
                    return ""       # elided at source; do not re-publish a stub
                return first.rstrip(".").replace("\t", " ").strip()
    return ""

def _describe(root, lines, content, name):
    m = re.search(r"#\s*---\s*(?:\(\d+,\s*)?([^\n#]+?)\s*---\s*\n\s*"
                  + re.escape(name) + r"\(\)\s*\{", content)
    if m:
        return m.group(1).strip()
    body = _body(lines, name)
    for em in _ECHO.findall("\n".join(body)):
        if not em.startswith(("WARNING", "VIOLATION", "---")):
            return em.strip()
    for line in body:
        d = _RUN_PY.search(line)
        if d:
            hint = _hint_of(root, d.group(1) or d.group(2))
            if hint:
                return hint
    return name.replace("check_", "").replace("_", " ")

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script_path = os.path.join(root, "automation/98-drift-checks.sh")
    output_path = os.path.join(root, "usr/share/mios/reference/drift-gate-index.tsv")

    if not os.path.isfile(script_path):
        sys.stderr.write(f"ERROR: {script_path} not found\n")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    main_start = content.find("main() {")
    if main_start == -1:
        sys.stderr.write("ERROR: main() function not found in 98-drift-checks.sh\n")
        sys.exit(1)

    main_body = content[main_start:]
    check_names = re.findall(r"^\s*(check_[a-z0-9_]+)\s*$", main_body, re.MULTILINE)

    if not check_names:
        sys.stderr.write("ERROR: No check_* functions found in main()\n")
        sys.exit(1)

    if len(check_names) != len(set(check_names)):
        dups = [name for name in check_names if check_names.count(name) > 1]
        sys.stderr.write(f"ERROR: Duplicate check_* functions found in main(): {set(dups)}\n")
        sys.exit(1)

    lines = content.splitlines()
    rows = []
    for idx, name in enumerate(check_names, 1):
        rows.append(f"{idx}\t{name}\t{_describe(root, lines, content, name)}")

    tsv_content = "# Ordinal\tCheck Function\tDescription\n" + "\n".join(rows) + "\n"

    check_mode = "--check" in sys.argv
    if check_mode:
        if not os.path.isfile(output_path):
            sys.stderr.write(f"ERROR: {output_path} does not exist\n")
            sys.exit(1)
        with open(output_path, "r", encoding="utf-8") as f:
            existing = f.read()
        if existing != tsv_content:
            sys.stderr.write("ERROR: drift-gate-index.tsv is out of sync with 98-drift-checks.sh. Run tools/generate-gate-index.py to regenerate.\n")
            sys.exit(1)
        print("PASS: drift-gate-index.tsv is in sync.")
        sys.exit(0)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # newline="\n": Python text mode translates \n to the host
    # separator, so regenerating on Windows produced a CRLF file differing
    # from the committed LF one in every row. The gate diffs generated
    # against committed, so that fired on who ran it, not on real drift.
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(tsv_content)
    os.replace(tmp_path, output_path)

    print(f"Generated {output_path} with {len(check_names)} gate entries.")

if __name__ == "__main__":
    main()
