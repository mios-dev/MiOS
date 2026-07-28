#!/usr/bin/env python3
"""
tools/generate-gate-index.py
Generates usr/share/mios/reference/drift-gate-index.tsv from automation/98-drift-checks.sh.
Enforces 1:1 ordinal numbering for every registered drift-check in main() order.
"""

import os
import sys
import re

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script_path = os.path.join(root, "automation/98-drift-checks.sh")
    output_path = os.path.join(root, "usr/share/mios/reference/drift-gate-index.tsv")

    if not os.path.isfile(script_path):
        sys.stderr.write(f"ERROR: {script_path} not found\n")
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Extract main() function block (from `main() {` to the end of the file or `main "$@"`)
    main_start = content.find("main() {")
    if main_start == -1:
        sys.stderr.write("ERROR: main() function not found in 98-drift-checks.sh\n")
        sys.exit(1)

    main_body = content[main_start:]
    check_names = re.findall(r"^\s*(check_[a-z0-9_]+)\s*$", main_body, re.MULTILINE)

    if not check_names:
        sys.stderr.write("ERROR: No check_* functions found in main()\n")
        sys.exit(1)

    # Parse function definitions and descriptions
    rows = []
    for idx, name in enumerate(check_names, 1):
        # Look for comment right before or at top of function definition
        pattern = r"(?:#\s*---\s*(?:\(\d+,\s*)?([^\n#]+?)\s*---\s*\n)?\s*" + re.escape(name) + r"\(\)\s*\{"
        comment_match = re.search(pattern, content)
        desc = ""
        if comment_match and comment_match.group(1):
            desc = comment_match.group(1).strip()
        else:
            fn_match = re.search(r"^\s*" + re.escape(name) + r"\(\)\s*\{(.*?)\n\}", content, re.MULTILINE | re.DOTALL)
            if fn_match:
                fn_body = fn_match.group(1)
                echo_matches = re.findall(r'echo\s+"\[38-drift-checks\]\s+(?:\(\d+\)\s+)?([^"]+)"', fn_body)
                for em in echo_matches:
                    if not em.startswith("WARNING") and not em.startswith("VIOLATION") and not em.startswith("---"):
                        desc = em.strip()
                        break
                if not desc:
                    desc = name.replace("check_", "").replace("_", " ")

        rows.append(f"{idx}\t{name}\t{desc}")

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
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(tsv_content)

    print(f"Generated {output_path} with {len(check_names)} gate entries.")

if __name__ == "__main__":
    main()
