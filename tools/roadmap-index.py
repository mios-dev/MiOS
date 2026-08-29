#!/usr/bin/env python3
# AI-hint: MiOS system and orchestration module providing roadmap-index capabilities.
# AI-functions: flatten_keys, make_anchor, parse_simple_yaml, main, check_adr_exists, generate_metrics_table, replace_section

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

    def check_adr_exists(adr_num):
        prefix = f"{adr_num:04d}"
        search_path = os.path.join(ROOT, "usr/share/doc/mios/adr", f"{prefix}-*.md")
        files = glob.glob(search_path)
        return len(files) > 0

    with open(roadmap_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_part = None
    workstreams = []
    parts_order = []
    part_workstreams = {}

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("# ") and not line.startswith("## "):
            header_name = line[2:].strip()
            if not any(header_name.lower().startswith(x) for x in ["mios -- master roadmap", "mios roadmap", "archived mios roadmap", "appendix"]):
                current_part = header_name
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

    # The law set is the SSOT's, not a literal: this was pinned at 13 and went
    # stale when the registry grew, so no workstream could cite Laws 14-16.
    valid_law_ids = set()
    try:
        with open(os.path.join(ROOT, "usr/share/mios/mios.toml"), "rb") as fh:
            for law in (tomllib.load(fh).get("laws", {}) or {}).get("laws", []) or []:
                if isinstance(law.get("id"), int):
                    valid_law_ids.add(law["id"])
    except (OSError, tomllib.TOMLDecodeError):
        valid_law_ids = set()

    validation_errors = []
    for ws in workstreams:
        for law in ws["laws"]:
            if not isinstance(law, int) or (valid_law_ids and law not in valid_law_ids):
                validation_errors.append(f"Workstream {ws['id']} cites invalid Law: {law}")

        for adr in ws["adr"]:
            if not isinstance(adr, int) or not check_adr_exists(adr):
                validation_errors.append(f"Workstream {ws['id']} cites non-existent ADR: {adr}")

        for key in ws["ssot_keys"]:
            if key not in valid_ssot_keys:
                validation_errors.append(f"Workstream {ws['id']} cites non-existent SSOT key: {key}")

    if validation_errors:
        print("[roadmap-index] Validation failed:", file=sys.stderr)
        for err in validation_errors:
            print(f"  - {err}", file=sys.stderr)
        return 2

    toc_lines = ["## Table of Contents"]
    for part in parts_order:
        anchor = make_anchor(part)
        toc_lines.append(f"- [{part}](#{anchor})")
    toc_content = "\n".join(toc_lines) + "\n"

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

    index_lines = ["### Workstream Index\n"]
    for part in parts_order:
        index_lines.append(f"**{part}**")
        ws_list = part_workstreams[part]
        if not ws_list:
            index_lines.append("(no workstreams)\n")
        else:
            for ws in ws_list:
                status_suffix = " ✅" if ws["status"].lower() == "done" else f" ({ws['status'].lower()})"
                index_lines.append(f"- `{ws['id']}` — {ws['title']}{status_suffix}")
            index_lines.append("")
    index_content = "\n".join(index_lines)

    def generate_metrics_table(root: str) -> str:
        import subprocess
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mios_tracked import tracked as _tracked_files
        # A git that refused used to yield file_count=0 and a metrics table of
        # zeros. --check then reported "ROADMAP.md index is stale", which reads
        # as an ordinary staleness and invites --apply -- and --apply would
        # WRITE the zeros into a tracked artifact and commit them. Refuse.
        tracked = _tracked_files(root)
        file_count = len(tracked)

        # Census size AND line counts from the INDEX blobs, never the checkout.
        # On-disk bytes are not a function of the commit: .gitattributes checks
        # *.ps1 out as CRLF on every platform, so the tree runs ~24 KiB heavier
        # than the blobs, and the total sits ~13 KiB from the 201.5 MiB rounding
        # boundary -- committed and CI-rendered values landed on opposite sides.
        # Reading the checkout also counts a co-worker's UNCOMMITTED edits into
        # a committed table. Blobs are identical in every clean checkout of the
        # same commit, so the gate converges.
        _p = subprocess.run(["git", "-C", root, "ls-files", "-s", "-z"],
                            capture_output=True, text=True, check=False)
        if _p.returncode != 0 or not _p.stdout.strip():
            raise RuntimeError(
                "git ls-files -s failed in %s (exit %d): %s -- refusing to "
                "render a metrics table from an empty census"
                % (root, _p.returncode, (_p.stderr or "").strip() or "no output"))
        ls_s = _p.stdout
        oid_of = {}
        for ent in ls_s.split("\0"):
            if not ent.strip():
                continue
            meta, _, path = ent.partition("\t")
            parts = meta.split()
            if len(parts) >= 2 and path:
                oid_of[path] = parts[1]

        total_bytes = 0
        if oid_of:
            sizes = subprocess.run(
                ["git", "-C", root, "cat-file", "--batch-check=%(objectsize)"],
                input="\n".join(oid_of.values()), capture_output=True, text=True, check=False,
            ).stdout.splitlines()
            total_bytes = sum(int(s) for s in sizes if s.strip().isdigit())

        sh_l = py_l = ps_l = rs_l = 0
        counted = {'.sh': 0, '.py': 0, '.ps1': 0, '.rs': 0}
        code = [(os.path.splitext(f)[1].lower(), oid_of[f]) for f in tracked
                if os.path.splitext(f)[1].lower() in counted and f in oid_of]
        if code:
            blob = subprocess.run(
                ["git", "-C", root, "cat-file", "--batch"],
                input="\n".join(o for _, o in code).encode(),
                capture_output=True, check=False,
            ).stdout
            pos = 0
            for ext, _oid in code:
                nl = blob.find(b"\n", pos)
                if nl == -1:
                    break
                header = blob[pos:nl].split()
                if len(header) < 3 or not header[2].isdigit():
                    break
                size = int(header[2])
                body = blob[nl + 1:nl + 1 + size]
                counted[ext] += body.count(b"\n") + (1 if body and not body.endswith(b"\n") else 0)
                pos = nl + 1 + size + 1
        sh_l, py_l, ps_l, rs_l = counted['.sh'], counted['.py'], counted['.ps1'], counted['.rs']

        size_mb = int(round(total_bytes / (1024 * 1024)))
        sh_k = round(sh_l / 1000)
        py_k = round(py_l / 1000)
        ps_k = round(ps_l / 1000)
        rs_k = round(rs_l / 1000)
        ratio = (ps_l / rs_l) if rs_l > 0 else 0.0

        drift_count = 0
        gate_sh = os.path.join(root, "automation/98-drift-checks.sh")
        if os.path.isfile(gate_sh):
            try:
                with open(gate_sh, "r", encoding="utf-8", errors="replace") as fh:
                    txt = fh.read()
                m_pos = txt.find("main() {")
                if m_pos != -1:
                    checks = re.findall(r"^\s*(check_[a-z0-9_]+)\s*$", txt[m_pos:], re.MULTILINE)
                    drift_count = len(checks)
            except OSError:
                pass

        declared_cnt = 0
        drift_units_cnt = 0
        shipped_cnt = 0
        toml_path = os.path.join(root, "usr/share/mios/mios.toml")
        if os.path.isfile(toml_path):
            try:
                with open(toml_path, "rb") as fh:
                    data = tomllib.load(fh)
                declared = {k for k, v in (data.get("units") or {}).items() if isinstance(v, dict)}
                declared_cnt = len(declared)
                drift_list = (data.get("unit_projection") or {}).get("drift") or []
                drift_units_cnt = len(drift_list)
            except OSError:
                pass

        unit_dir = os.path.join(root, "usr/lib/systemd/system")
        if os.path.isdir(unit_dir):
            for _, _, fns in os.walk(unit_dir):
                shipped_cnt += len(fns)

        faithful_cnt = max(0, declared_cnt - drift_units_cnt)

        table_lines = [
            "| | Measured | Note |",
            "|---|---:|---|",
            f"| Runs on | MiOS-DEV VM / WSL | Bare metal is **untried**; blade/mesh/vfio behaviour is design, not observation. |",
            f"| Tracked files | {file_count:,} | The reading surface. |",
            f"| Tracked size | {size_mb} MB | Two vendored assets are most of it. |",
            f"| Shell / Python / PowerShell / Rust | {sh_k}k / {py_k}k / {ps_k}k / {rs_k}k lines | Law 14 makes Rust the native tier; PowerShell currently outweighs it {ratio:.1f}x. |",
            f"| Drift checks | {drift_count} | Falsifiability audited per check, not assumed. |",
            f"| Units reproducing from SSOT | {faithful_cnt} faithful of {shipped_cnt} | {drift_units_cnt} registered as drifting: the largest hole in part 1 of the thesis. |",
        ]
        return "\n".join(table_lines) + "\n"

    metrics_content = generate_metrics_table(ROOT)

    with open(roadmap_path, "r", encoding="utf-8") as f:
        file_text = f.read()

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
        new_text = replace_section(new_text, "<!-- ROADMAP_METRICS_START -->", "<!-- ROADMAP_METRICS_END -->", metrics_content)
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
    print("[roadmap-index] Successfully regenerated Table of Contents, Index, Metrics, and Rollup in ROADMAP.md")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
