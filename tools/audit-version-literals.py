# AI-hint: !/usr/bin/env python3 Inventories every version token in the repo and classifies it as SSOT-definition, SSOT-derived placeholder, or hardcoded literal, emittin...
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_audit_version_literals_py.md

import os
import re
import sys
from pathlib import Path

VERSION_REGEX = re.compile(
    r'(:v?\d+\.\d+(?:\.\d+)?|stable:/v\d+\.\d+|fedora-\d+|@sha256:[a-f0-9]{64}|==\d+\.\d+(?:\.\d+)?|rancher/k3s:v\d+\.\d+\.\d+(?:-[a-z0-9]+)?)'
)

SKIP_DIRS = {
    ".git", ".cargo", ".rustup", "__pycache__", "node_modules", "vendor",
    "target", ".tmp.drivedownload", ".tmp.driveupload", "artifacts", "root",
    "usr/share/doc", "tmp"
}

EXEMPT_EXTENSIONS = {
    ".lock", ".csv", ".tsv", ".sum", ".log", ".diff", ".png", ".jpg", ".gz", ".md"
}

def classify_line(file_path: str, line: str, token: str) -> str:
    norm_path = file_path.replace('\\', '/')

    # (a) SSOT-definition
    if "usr/share/mios/mios.toml" in norm_path or norm_path == "mios.toml":
        return "SSOT-definition"

    # (b) SSOT-derived / placeholder
    if "${" in line or "$MIOS_" in line or "$FEDORA_VERSION" in line or "env_var" in line:
        return "SSOT-derived/placeholder"

    # (c) HARDCODED-literal
    return "HARDCODED-literal"

def suggest_ssot_key(token: str) -> str:
    if "k3s" in token or "k8s" in token or "stable:/v" in token:
        return "MIOS_K3S_VERSION"
    if "fedora-" in token:
        return "FEDORA_VERSION"
    if "==" in token:
        return "PYTHON_DEP_VERSION"
    return "MIOS_VERSION_SSOT"

def scan_repo(repo_root):
    records = []
    class_counts = {"SSOT-definition": 0, "SSOT-derived/placeholder": 0, "HARDCODED-literal": 0}

    for root, dirs, files in os.walk(repo_root):
        # Prune skipped directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]

        rel_root = os.path.relpath(root, repo_root).replace('\\', '/')
        if rel_root == ".":
            rel_root = ""

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXEMPT_EXTENSIONS or f == "version-literals-audit.tsv":
                continue

            rel_path = f"{rel_root}/{f}" if rel_root else f
            abs_path = os.path.join(root, f)

            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as fh:
                    for line_idx, line in enumerate(fh, 1):
                        matches = VERSION_REGEX.findall(line)
                        for match in matches:
                            cls = classify_line(rel_path, line, match)
                            class_counts[cls] = class_counts.get(cls, 0) + 1
                            sugg = suggest_ssot_key(match)
                            records.append((rel_path, str(line_idx), match, cls, sugg))
            except Exception:
                continue

    # Sort deterministically
    records.sort(key=lambda r: (r[0], int(r[1]), r[2]))
    return records, class_counts

def main():
    repo_root = Path(__file__).resolve().parent.parent
    output_tsv = repo_root / "usr/share/mios/reference/version-literals-audit.tsv"
    output_tsv.parent.mkdir(parents=True, exist_ok=True)

    records, class_counts = scan_repo(repo_root)

    lines = ["path\tline\ttoken\tclass\tsuggested_ssot_key\n"]
    for rec in records:
        lines.append("\t".join(rec) + "\n")

    output_tsv.write_text("".join(lines), encoding="utf-8")

    print(f"[audit-version-literals] Audit complete ({len(records)} findings). Output written to {output_tsv}")
    print(f"[audit-version-literals] Summary of classes:")
    for cls, count in sorted(class_counts.items()):
        print(f"  {cls}: {count}")

if __name__ == "__main__":
    main()
