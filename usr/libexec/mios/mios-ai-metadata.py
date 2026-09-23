#!/usr/bin/env python3
# AI-hint: Extracts, aggregates, and validates native MiOS AI header metadata (hint, related, functions, doc) across all tracked source files and units into strict OpenAI-compatible schemas.
# AI-related: usr/lib/mios/schemas/ai_metadata.schema.json, usr/share/mios/ai/v1/metadata.json, usr/libexec/mios/mios-ai-tag
# AI-functions: extract_ai_header_metadata, build_metadata_catalog, validate_schema_compliance, main

"""
MiOS Native AI Metadata Engine.

Parses AI comment headers across all source files, modules, units, and documentation
to produce first-class, machine-readable metadata. Guarantees that AI-hint, AI-related,
AI-functions, and AI-doc headers are recognized as native OS metadata for local agent
discovery, tool routing, and automated pipeline validation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))

AI_HINT_RE = re.compile(r"^[#/<!;\-*\s]*AI-hint:\s*(.+?)(?:\s*-->)?\s*$", re.I)
AI_RELATED_RE = re.compile(r"^[#/<!;\-*\s]*AI-related:\s*(.+?)(?:\s*-->)?\s*$", re.I)
AI_FUNCS_RE = re.compile(r"^[#/<!;\-*\s]*AI-functions:\s*(.+?)(?:\s*-->)?\s*$", re.I)
AI_DOC_RE = re.compile(r"^[#/<!;\-*\s]*AI-doc:\s*(.+?)(?:\s*-->)?\s*$", re.I)


def detect_comment_style(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".md", ".html"):
        return "xml"
    if ext in (".js", ".ts", ".rs", ".qml"):
        return "slash"
    if ext == ".sql":
        return "dash"
    if ext in (".ini", ".cfg"):
        return "semi"
    return "hash"


def extract_ai_header_metadata(content: str, rel_path: str) -> Optional[Dict[str, Any]]:
    lines = content.splitlines()[:60]
    hint: Optional[str] = None
    related: List[str] = []
    functions: List[str] = []
    doc: Optional[str] = None

    for line in lines:
        if not hint:
            m = AI_HINT_RE.match(line)
            if m:
                hint = m.group(1).strip()
                continue
        if not related:
            m = AI_RELATED_RE.match(line)
            if m:
                raw = m.group(1).strip()
                related = [x.strip() for x in raw.split(",") if x.strip()]
                continue
        if not functions:
            m = AI_FUNCS_RE.match(line)
            if m:
                raw = m.group(1).strip()
                functions = [x.strip() for x in raw.split(",") if x.strip()]
                continue
        if not doc:
            m = AI_DOC_RE.match(line)
            if m:
                doc = m.group(1).strip()
                continue

    if not hint and not related and not functions and not doc:
        return None

    has_shebang = content.startswith("#!")
    comment_style = detect_comment_style(rel_path)

    return {
        "path": rel_path.replace("\\", "/"),
        "hint": hint,
        "related": related,
        "functions": functions,
        "doc": doc,
        "comment_style": comment_style,
        "has_shebang": has_shebang,
    }


def get_tracked_files(root: str) -> List[str]:
    try:
        out = subprocess.run(
            ["git", "-c", "core.ignorecase=false", "ls-files", "-z"],
            cwd=root,
            capture_output=True,
            check=True,
        )
        return [p for p in out.stdout.decode("utf-8", errors="replace").split("\0") if p]
    except Exception:
        files: List[str] = []
        for dp, _, fns in os.walk(root):
            for fn in fns:
                files.append(os.path.relpath(os.path.join(dp, fn), root))
        return files


def build_metadata_catalog(root: str) -> Dict[str, Any]:
    tracked = get_tracked_files(root)
    entries: List[Dict[str, Any]] = []
    total_hints = 0
    total_funcs = 0
    total_related = 0

    for rel in sorted(tracked):
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read(8192)
        except OSError:
            continue

        meta = extract_ai_header_metadata(content, rel)
        if meta:
            entries.append(meta)
            if meta["hint"]:
                total_hints += 1
            total_funcs += len(meta["functions"])
            total_related += len(meta["related"])

    return {
        "format": "openai_strict_schema_v1",
        "total_files_scanned": len(tracked),
        "total_metadata_entries": len(entries),
        "total_hints": total_hints,
        "total_functions_indexed": total_funcs,
        "total_related_links": total_related,
        "entries": entries,
    }


def validate_schema_compliance(catalog: Dict[str, Any]) -> bool:
    schema_path = os.path.join(
        _REPO_ROOT, "usr/lib/mios/schemas/ai_metadata.schema.json"
    )
    if not os.path.isfile(schema_path):
        return False
    with open(schema_path, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    req = schema.get("schema", {}).get("required", [])
    for entry in catalog.get("entries", []):
        for field in req:
            if field not in entry:
                return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="MiOS Native AI Metadata Engine & Validator"
    )
    parser.add_argument("--root", default=_REPO_ROOT, help="Root repository path")
    parser.add_argument(
        "--export",
        nargs="?",
        const=os.path.join(_REPO_ROOT, "usr/share/mios/ai/v1/metadata.json"),
        help="Export catalog to specified JSON file",
    )
    parser.add_argument("--summary", action="store_true", help="Print summary statistics")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate schema compliance and metadata integrity",
    )
    args = parser.parse_args()

    catalog = build_metadata_catalog(args.root)

    if args.check:
        compliant = validate_schema_compliance(catalog)
        if not compliant:
            print("[ai-metadata] FAIL: Catalog contains non-compliant entries.", file=sys.stderr)
            return 1
        print(f"[ai-metadata] PASS: {catalog['total_metadata_entries']} entries verified against strict schema.")
        return 0

    if args.summary or not args.export:
        print("[ai-metadata] Native MiOS AI Metadata Summary:")
        print(f"  Files scanned:            {catalog['total_files_scanned']}")
        print(f"  Entries with AI metadata: {catalog['total_metadata_entries']}")
        print(f"  AI-hints indexed:         {catalog['total_hints']}")
        print(f"  Exported functions:       {catalog['total_functions_indexed']}")
        print(f"  Related references:       {catalog['total_related_links']}")

    if args.export:
        os.makedirs(os.path.dirname(os.path.abspath(args.export)), exist_ok=True)
        with open(args.export, "w", encoding="utf-8") as fh:
            json.dump(catalog, fh, indent=2)
        print(f"[ai-metadata] Exported metadata catalog to {args.export}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
