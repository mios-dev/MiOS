#!/usr/bin/env python3
# tools/lib/generate-build-scripts.py -- emit MiOS-Build-Scripts.md, a single
# markdown bundle containing the full source of every script that
# participates in building 'MiOS', in execution order.

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "MiOS-Build-Scripts.md"

# Layered ordering per delivery contract. Each (label, [paths]) -- paths are
# relative to ROOT. Glob-expand patterns inside each layer.
LAYERS = [
    ("Layer 1 -- User entry points (mios-bootstrap repo)",
     # mios-bootstrap repo lives at ../mios-bootstrap; check both possible
     # checkouts.
     []),  # populated dynamically below if sibling repo exists

    ("Layer 2 -- System-side installers",
     [
         "automation/install.sh",
         "automation/install-bootstrap.sh",
         "automation/build-mios.sh",
     ]),

    ("Layer 3 -- Build orchestrators",
     [
         "Containerfile",
         "Justfile",
         "mios-build-local.ps1",
         "automation/mios-build-builder.ps1",
         "preflight.ps1",
         "preflight.sh",
         "push-to-github.ps1",
         "Get-MiOS.ps1",
         "install.ps1",
     ]),

    ("Layer 4a -- Library (sourced helpers)",
     [
         "automation/lib/common.sh",
         "automation/lib/packages.sh",
         "automation/lib/masking.sh",
         "automation/lib/paths.sh",
     ]),

    ("Layer 4b -- Master orchestrator",
     [
         "automation/build.sh",
     ]),

    # Layer 4c-j: every NN-*.sh in automation/, expanded below.
    ("Layer 4c-j -- Numbered phase scripts (lex order)",
     []),  # populated below

    ("Layer 4k -- Helpers",
     [
         "automation/ai-bootstrap.sh",
         "automation/bcvk-wrapper.sh",
         "automation/bootstrap.sh",
         "automation/enroll-mok.sh",
         "automation/generate-mok-key.sh",
         "automation/overlay-builder.sh",
     ]),

    ("Layer 5 -- Postcheck + system-files overlay",
     [
         # 99-postcheck.sh is in the NN scripts; called out here for emphasis
     ]),
]

# Populate Layer 1 from sibling mios-bootstrap repo if present
BOOTSTRAP_ROOT = ROOT.parent / "mios-bootstrap"
if BOOTSTRAP_ROOT.is_dir():
    for f in ["bootstrap.sh", "bootstrap.ps1", "install.sh", "install.ps1"]:
        p = BOOTSTRAP_ROOT / f
        if p.is_file():
            LAYERS[0][1].append(str(p))

# Populate Layer 4c-j: every NN-*.sh in automation/
nn_scripts = sorted((ROOT / "automation").glob("[0-9][0-9]-*.sh"))
LAYERS[5] = (LAYERS[5][0], [str(p.relative_to(ROOT)) for p in nn_scripts])

def fence_for(path: Path) -> str:
    """Return the appropriate ``` fence language tag for a file."""
    s = path.suffix.lower()
    name = path.name
    if name == "Containerfile":
        return "dockerfile"
    if name == "Justfile":
        return "makefile"  # closest fit; just-flavored Makefile syntax
    return {
        ".sh":   "bash",
        ".ps1":  "powershell",
        ".py":   "python",
        ".toml": "toml",
        ".md":   "markdown",
    }.get(s, "")

def section(path_str: str, content: str, fence: str) -> str:
    return f"\n### `{path_str}`\n\n```{fence}\n{content}\n```\n"

def main():
    lines = []
    lines.append("# 'MiOS' Build Scripts -- Full Source Bundle\n")
    lines.append("Every script that participates in building the 'MiOS' OCI image, in")
    lines.append("execution order, with complete source and no truncation. Each section")
    lines.append("header carries the file path; each fenced block carries the verbatim")
    lines.append("file contents. Use `Ctrl-F` against a path to find a script.\n")
    lines.append("---\n")

    total_files = 0
    total_lines = 0
    skipped = []

    for label, paths in LAYERS:
        if not paths:
            continue
        lines.append(f"\n## {label}\n")
        for path_str in paths:
            p = Path(path_str)
            if not p.is_absolute():
                p = ROOT / path_str
            if not p.is_file():
                skipped.append(path_str)
                continue
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                skipped.append(f"{path_str} (read error: {e})")
                continue
            # Display path: prefer relative-to-ROOT; fall back to a stable
            # sibling-form (e.g. 'mios-bootstrap/bootstrap.sh') so the bundle
            # never embeds the build host's absolute path. Absolute paths
            # leak the developer's machine setup; bare basenames lose
            # repo context. The sibling form is the one users see in
            # 'git status' and matches the tracked layout on GHCR.
            try:
                display = str(p.relative_to(ROOT)).replace("\\", "/")
            except ValueError:
                # Outside ROOT -- expected for the mios-bootstrap sibling.
                # Walk parents until we find a *.git directory; emit the
                # path relative to that repo's parent so the output reads
                # 'mios-bootstrap/<file>' regardless of the absolute checkout
                # location on the host. Fall back to bare basename if no
                # repo root is detectable (e.g. file outside any git tree).
                anchor = None
                for ancestor in p.parents:
                    if (ancestor / ".git").exists():
                        anchor = ancestor.parent
                        break
                if anchor is not None:
                    display = str(p.relative_to(anchor)).replace("\\", "/")
                else:
                    display = p.name
            lines.append(section(display, content.rstrip("\n"), fence_for(p)))
            total_files += 1
            total_lines += content.count("\n") + 1

    if skipped:
        lines.append(f"\n## Skipped (not found at expected paths)\n")
        for s in skipped:
            lines.append(f"- `{s}`")

    lines.append(f"\n---\n")
    lines.append(f"\n**Bundle stats:** {total_files} files, "
                 f"{total_lines} source lines aggregated.\n")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"  files: {total_files}")
    print(f"  source lines aggregated: {total_lines}")
    if skipped:
        print(f"  skipped (missing): {len(skipped)}")

if __name__ == "__main__":
    main()
