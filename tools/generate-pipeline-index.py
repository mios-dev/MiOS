#!/usr/bin/env python3
# AI-hint: MiOS system and orchestration module providing generate-pipeline-index capabilities.
# AI-functions: _ssot, main

import os
import sys
import glob
import re

def _ssot(root):
    """The layered SSOT; {} when unreadable (degrade-open)."""
    for lib in (os.path.join(root, "usr/lib/mios"), "/usr/lib/mios"):
        if os.path.isdir(lib) and lib not in sys.path:
            sys.path.insert(0, lib)
    try:
        import mios_toml
        return mios_toml.load_merged() or {}
    except Exception:
        try:
            import tomllib
        except ImportError:
            return {}
        try:
            with open(os.environ.get("MIOS_TOML") or os.path.join(
                    root, "usr/share/mios/mios.toml"), "rb") as fh:
                return tomllib.load(fh) or {}
        except OSError:
            return {}

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    automation_dir = os.path.join(root, "automation")

    # The scheme this generator projects is declared, not restated: the map it
    # writes, the numbering space it accepts, and whether prefixes must be
    # unique all come from the SSOT that documents them.
    cfg = _ssot(root).get("pipeline") or {}
    space = cfg.get("space") or {}
    invariants = cfg.get("invariants") or {}
    nn_min = int(space.get("min", 0))
    nn_max = int(space.get("max", 99))
    prefix_unique = bool(invariants.get("prefix_unique", True))
    output_path = os.path.join(root, str(
        cfg.get("map") or "usr/share/mios/reference/pipeline-index.tsv"))

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

        if not (nn_min <= int(nn) <= nn_max):
            sys.stderr.write(
                f"ERROR: {basename} prefix {nn} is outside the declared "
                f"[pipeline].space {nn_min}..{nn_max}\n")
            sys.exit(1)
        if prefix_unique and nn in seen_nns:
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
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(tsv_content)
    os.replace(tmp_path, output_path)

    print(f"Generated {output_path} with {len(rows)} pipeline stages.")

if __name__ == "__main__":
    main()
