#!/usr/bin/env python3
# AI-hint: Extracts, aggregates, and validates native MiOS AI header metadata (hint, related, functions, doc) across all tracked source files and units into strict OpenAI-compatible schemas.
# AI-related: usr/lib/mios/schemas/ai_metadata.schema.json, usr/share/mios/ai/v1/metadata.json, usr/libexec/mios/mios-ai-tag
# AI-functions: extract_ai_header_metadata, build_metadata_catalog, render_catalog_json, diff_catalog_entries, check_export_fresh, validate_schema_compliance, main

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
import sys
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(_REPO_ROOT, "usr", "lib", "mios"))
from mios_comments import tracked_file_modes

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


def build_metadata_catalog(root: str) -> Dict[str, Any]:
    tracked = tracked_file_modes(root)
    entries: List[Dict[str, Any]] = []
    total_hints = 0
    total_funcs = 0
    total_related = 0

    for rel in sorted(tracked):
        if tracked[rel] not in ("100644", "100755"):
            continue
        full = os.path.join(root, rel)
        if os.path.islink(full):
            continue
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


def render_catalog_json(catalog: Dict[str, Any]) -> str:
    """The exact bytes --export writes; --check-fresh compares against the same."""
    return json.dumps(catalog, indent=2)


def diff_catalog_entries(tracked: Dict[str, Any], fresh: Dict[str, Any]) -> List[str]:
    """Name what differs, entry by entry, so a stale file says which header moved."""
    lines: List[str] = []
    for key in sorted(set(tracked) | set(fresh)):
        if key == "entries":
            continue
        if tracked.get(key) != fresh.get(key):
            lines.append(f"field {key}: tracked={tracked.get(key)!r} fresh={fresh.get(key)!r}")
    old = {e.get("path"): e for e in tracked.get("entries", []) if isinstance(e, dict)}
    new = {e.get("path"): e for e in fresh.get("entries", []) if isinstance(e, dict)}
    for path in sorted(set(old) | set(new), key=str):
        if path not in new:
            lines.append(f"entry {path}: in the tracked file but no longer has an AI header (or is untracked)")
        elif path not in old:
            lines.append(f"entry {path}: has an AI header but is missing from the tracked file")
        elif old[path] != new[path]:
            keys = sorted(k for k in set(old[path]) | set(new[path]) if old[path].get(k) != new[path].get(k))
            lines.append(f"entry {path}: differs in {', '.join(keys)}")
    return lines


def check_export_fresh(catalog: Dict[str, Any], path: str) -> int:
    """Regenerate-and-diff (Law 8): 0 when the tracked export is byte-identical."""
    rel = os.path.relpath(path)
    try:
        with open(path, "r", encoding="utf-8", newline="") as fh:
            on_disk = fh.read()
    except OSError as exc:
        print(f"[ai-metadata] FAIL: {rel} is unreadable ({exc}); nothing was compared.", file=sys.stderr)
        return 1
    expected = render_catalog_json(catalog)
    if on_disk == expected:
        print(f"[ai-metadata] PASS: {rel} is byte-identical to a fresh export "
              f"({catalog['total_metadata_entries']} entries).")
        return 0
    print(f"[ai-metadata] FAIL: {rel} is stale -- it differs from a fresh export.", file=sys.stderr)
    try:
        details = diff_catalog_entries(json.loads(on_disk), catalog)
    except ValueError as exc:
        details = [f"tracked file is not valid JSON: {exc}"]
    if not details:
        details = ["same parsed content, different bytes (formatting drift)"]
    cap = 40
    for line in details[:cap]:
        print(f"    {line}", file=sys.stderr)
    if len(details) > cap:
        print(f"    ... and {len(details) - cap} more", file=sys.stderr)
    print("  Regenerate with: bash tools/sync-generated.sh "
          "(or python3 usr/libexec/mios/mios-ai-metadata.py --export)", file=sys.stderr)
    return 1


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
    parser.add_argument(
        "--check-fresh",
        nargs="?",
        const="",
        default=None,
        metavar="PATH",
        help="Fail unless PATH (default: <root>/usr/share/mios/ai/v1/metadata.json) "
        "is byte-identical to a fresh export, naming each differing entry",
    )
    args = parser.parse_args()

    catalog = build_metadata_catalog(args.root)

    if args.check_fresh is not None:
        target = args.check_fresh or os.path.join(args.root, "usr/share/mios/ai/v1/metadata.json")
        return check_export_fresh(catalog, target)

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
        with open(args.export, "w", encoding="utf-8", newline="") as fh:
            fh.write(render_catalog_json(catalog))
        print(f"[ai-metadata] Exported metadata catalog to {args.export}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
