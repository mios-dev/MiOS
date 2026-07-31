#!/usr/bin/env python3
"""
tools/generate-pipeline-index.py
Generates usr/share/mios/reference/pipeline-index.tsv from automation/[0-9][0-9]-*.sh scripts.
Enforces 1:1 mapping for stage identity coordinates (ADR-0012, WS-NUMBER AGY-644).
"""

import os
import sys
import glob
import re

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    automation_dir = os.path.join(root, "automation")
    output_path = os.path.join(root, "usr/share/mios/reference/pipeline-index.tsv")

    if not os.path.isdir(automation_dir):
        sys.stderr.write(f"ERROR: {automation_dir} not found\n")
        sys.exit(1)

    script_paths = sorted(glob.glob(os.path.join(automation_dir, "[0-9][0-9]-*.sh")))

    rows = []
    seen_nns = set()

    for script_path in script_paths:
        basename = os.path.basename(script_path)
        match = re.match(r"^([0-9]{2})-(.+)\.sh$", basename)
        if not match:
            continue
        nn, name = match.group(1), match.group(2)

        if nn in seen_nns:
            sys.stderr.write(f"ERROR: Duplicate NN prefix found: {nn} in {basename}\n")
            sys.exit(1)
        seen_nns.add(nn)

        oneline = ""
        with open(script_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if line_str.startswith("# AI-hint:") or line_str.startswith("# AI-related:"):
                    continue
                if line_str.startswith("#") and not line_str.startswith("#!"):
                    text = line_str.lstrip("#").strip()
                    if text and not text.startswith("---") and not text.startswith("Usage:"):
                        oneline = text
                        break

        if not oneline:
            oneline = name.replace("-", " ")

        rel_path = os.path.relpath(script_path, root).replace("\\", "/")
        rows.append(f"{nn}\tscript\t{name}\t{rel_path}\t{oneline}")

    tsv_content = "# NN\tkind\tname\tfile\toneline\n" + "\n".join(rows) + "\n"

    check_mode = "--check" in sys.argv
    if check_mode:
        if not os.path.isfile(output_path):
            sys.stderr.write(f"ERROR: {output_path} does not exist\n")
            sys.exit(1)
        with open(output_path, "r", encoding="utf-8") as f:
            existing = f.read()
        if existing.replace("\r\n", "\n") != tsv_content.replace("\r\n", "\n"):
            sys.stderr.write("ERROR: pipeline-index.tsv is out of sync with automation scripts. Run tools/generate-pipeline-index.py to regenerate.\n")
            sys.exit(1)
        print("PASS: pipeline-index.tsv is in sync.")
        sys.exit(0)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(tsv_content)

    print(f"Generated {output_path} with {len(rows)} pipeline stages.")

if __name__ == "__main__":
    main()
