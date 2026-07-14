#!/usr/bin/env python3
# tools/roadmap-index.py
import os
import sys
import re
import glob

ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

def flatten_keys(d, prefix=""):
    keys = set()
    for k, v in d.items():
        full_key = f"{prefix}.{k}" if prefix else k
        keys.add(full_key)
        if isinstance(v, dict):
            keys.update(flatten_keys(v, full_key))
    return keys

def make_anchor(title):
    # Remove markdown link markup if any, e.g. [foo](#bar) -> foo
    title = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', title)
    title = title.replace("`", "")
    out = []
    for char in title.lower():
        if char.isalnum() or char in (" ", "-", "_"):
            out.append(char)
    res = "".join(out).strip()
    res = re.sub(r'\s+', '-', res)
    res = re.sub(r'-+', '-', res)
    return res

def parse_simple_yaml(text):
    metadata = {}
    lines = text.strip().split("\n")
    in_multiline = None
    multiline_key = None
    multiline_val = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if in_multiline:
            multiline_val.append(line)
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip()
        if v == "|":
            in_multiline = True
            multiline_key = k
            multiline_val = []
            continue
        
        # Parse array
        if v.startswith("[") and v.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            coerced = []
            for x in items:
                try:
                    coerced.append(int(x))
                except ValueError:
                    coerced.append(x)
            v = coerced
        metadata[k] = v
        
    if in_multiline and multiline_key:
        metadata[multiline_key] = "\n".join(multiline_val)
    return metadata

def main(argv):
    check = "--check" in argv
    roadmap_path = os.path.join(ROOT, "ROADMAP.md")
    
    if not os.path.exists(roadmap_path):
        print(f"ERROR: ROADMAP.md not found at {roadmap_path}", file=sys.stderr)
        return 1

    # Load valid SSOT keys
    valid_ssot_keys = set()
    userenv_path = os.path.join(ROOT, "tools/lib/userenv.sh")
    if os.path.exists(userenv_path):
        with open(userenv_path, "r", encoding="utf-8") as f:
            userenv_content = f.read()
        for m in re.finditer(r'\("([a-zA-Z0-9_.-]+)"\s*,\s*"[A-Z0-9_]+"\)', userenv_content):
            valid_ssot_keys.add(m.group(1))
            
    toml_path = os.path.join(ROOT, "usr/share/mios/mios.toml")
    if os.path.exists(toml_path):
        with open(toml_path, "rb") as f:
            toml_data = tomllib.load(f)
        valid_ssot_keys.update(flatten_keys(toml_data))

    # Helper to check ADR file
    def check_adr_exists(adr_num):
        prefix = f"{adr_num:04d}"
        search_path = os.path.join(ROOT, "usr/share/doc/mios/adr", f"{prefix}-*.md")
        files = glob.glob(search_path)
        return len(files) > 0

    # Parse ROADMAP.md
    with open(roadmap_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_part = None
    workstreams = []
    parts_order = []
    part_workstreams = {}
    
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("# Part ") or line.startswith("## Part "):
            # We only count # Part (top-level) for Table of Contents and grouping
            if line.startswith("# Part "):
                current_part = line[2:].strip()
                if current_part not in parts_order:
                    parts_order.append(current_part)
                    part_workstreams[current_part] = []
            idx += 1
            continue
            
        if line.startswith("## WS-"):
            header_text = line[2:].strip()
            parts = re.split(r'\s+[-—–]+\s+', header_text, maxsplit=1)
            ws_id = parts[0].strip()
            ws_title = parts[1].strip() if len(parts) > 1 else header_text
            
            frontmatter_text = ""
            fm_idx = idx + 1
            while fm_idx < len(lines) and not lines[fm_idx].strip():
                fm_idx += 1
                
            if fm_idx < len(lines) and lines[fm_idx].strip().startswith("<!--"):
                block_lines = []
                first_line = lines[fm_idx].strip()
                if first_line.endswith("-->"):
                    block_lines.append(first_line[4:-3])
                    fm_idx += 1
                else:
                    block_lines.append(first_line[4:])
                    fm_idx += 1
                    while fm_idx < len(lines):
                        cur_line = lines[fm_idx]
                        if "-->" in cur_line:
                            block_lines.append(cur_line.split("-->", 1)[0])
                            fm_idx += 1
                            break
                        else:
                            block_lines.append(cur_line)
                            fm_idx += 1
                block_text = "\n".join(block_lines)
                if "id:" in block_text or "status:" in block_text:
                    frontmatter_text = block_text
                    
            meta = {}
            if frontmatter_text:
                meta = parse_simple_yaml(frontmatter_text)
                
            meta["id"] = meta.get("id") or ws_id
            meta["title"] = meta.get("title") or ws_title
            
            if "status" not in meta:
                rest_of_text = ""
                for j in range(idx, min(idx + 15, len(lines))):
                    rest_of_text += lines[j]
                if "✅" in rest_of_text or "DONE" in rest_of_text:
                    meta["status"] = "done"
                elif "active" in rest_of_text.lower():
                    meta["status"] = "active"
                else:
                    meta["status"] = "proposed"
                    
            meta["priority"] = meta.get("priority") or "P2"
            meta["laws"] = meta.get("laws") or []
            meta["ssot_keys"] = meta.get("ssot_keys") or []
            meta["adr"] = meta.get("adr") or []
            meta["deps"] = meta.get("deps") or []
            meta["acceptance"] = meta.get("acceptance") or ""
            meta["theme"] = meta.get("theme") or "General"
            meta["part"] = current_part
            
            workstreams.append(meta)
            if current_part:
                part_workstreams[current_part].append(meta)
                
        idx += 1

    # Validation Checks
    validation_errors = []
    for ws in workstreams:
        # 1. Laws verification (1-13)
        for law in ws["laws"]:
            if not isinstance(law, int) or law < 1 or law > 13:
                validation_errors.append(f"Workstream {ws['id']} cites invalid Law: {law}")
                
        # 2. ADR verification
        for adr in ws["adr"]:
            if not isinstance(adr, int) or not check_adr_exists(adr):
                validation_errors.append(f"Workstream {ws['id']} cites non-existent ADR: {adr}")
                
        # 3. SSOT keys verification
        for key in ws["ssot_keys"]:
            if key not in valid_ssot_keys:
                validation_errors.append(f"Workstream {ws['id']} cites non-existent SSOT key: {key}")

    if validation_errors:
        print("[roadmap-index] Validation failed:", file=sys.stderr)
        for err in validation_errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    # Generate Tables
    # Table of Contents
    toc_lines = ["## Table of Contents"]
    for part in parts_order:
        anchor = make_anchor(part)
        toc_lines.append(f"- [{part}](#{anchor})")
    toc_content = "\n".join(toc_lines) + "\n"

    # Status Rollup
    rollup_counts = {"done": 0, "active": 0, "proposed": 0, "blocked": 0}
    for ws in workstreams:
        status = ws["status"].lower()
        if status in rollup_counts:
            rollup_counts[status] += 1
        else:
            rollup_counts["proposed"] += 1
            
    rollup_lines = [
        "### Workstream Status Rollup",
        f"- **Done**: {rollup_counts['done']}",
        f"- **Active**: {rollup_counts['active']}",
        f"- **Proposed**: {rollup_counts['proposed']}",
        f"- **Blocked**: {rollup_counts['blocked']}"
    ]
    rollup_content = "\n".join(rollup_lines) + "\n"

    # Index
    index_lines = ["### Workstream Index\n"]
    for part in parts_order:
        index_lines.append(f"**{part}**")
        ws_list = part_workstreams[part]
        if not ws_list:
            index_lines.append("(no workstreams)\n")
        else:
            for ws in ws_list:
                # Add checkmark emoji if done
                status_suffix = " ✅" if ws["status"].lower() == "done" else f" ({ws['status'].lower()})"
                index_lines.append(f"- `{ws['id']}` — {ws['title']}{status_suffix}")
            index_lines.append("")
    index_content = "\n".join(index_lines)

    # Read current file to check drift or replace
    with open(roadmap_path, "r", encoding="utf-8") as f:
        file_text = f.read()

    # Regex search and replace
    def replace_section(text, start_marker, end_marker, replacement):
        pattern = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            re.DOTALL
        )
        if not pattern.search(text):
            raise ValueError(f"Markers {start_marker} and {end_marker} not found")
        return pattern.sub(start_marker + "\n" + replacement + end_marker, text)

    try:
        new_text = file_text
        new_text = replace_section(new_text, "<!-- ROADMAP_ROLLUP_START -->", "<!-- ROADMAP_ROLLUP_END -->", rollup_content)
        new_text = replace_section(new_text, "<!-- ROADMAP_INDEX_START -->", "<!-- ROADMAP_INDEX_END -->", index_content)
        new_text = replace_section(new_text, "<!-- ROADMAP_TOC_START -->", "<!-- ROADMAP_TOC_END -->", toc_content)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if check:
        if file_text != new_text:
            print("[roadmap-index] DRIFT detected: ROADMAP.md index is stale", file=sys.stderr)
            return 1
        print("[roadmap-index] ROADMAP.md index is in sync")
        return 0

    with open(roadmap_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_text)
    print("[roadmap-index] Successfully regenerated Table of Contents, Index, and Rollup in ROADMAP.md")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
