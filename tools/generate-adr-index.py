#!/usr/bin/env python3
# AI-hint: Generates the repo-root ADR.md breadcrumb from the front-matter of usr/share/doc/mios/adr/NNNN-*.md (T-265).
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_generate_adr_index_py.md
"""Generate the repo-root ADR.md breadcrumb from the baked ADR front-matter."""

import os
import re
import sys

ADR_DIR = os.path.join("usr", "share", "doc", "mios", "adr")
OUT = "ADR.md"
_SCALAR = re.compile(r"^([a-z_]+):\s*(.*)$")


def parse_front_matter(path: str) -> dict:
    """The `---`-delimited YAML head of an ADR, as a flat dict. Scalars stay
    strings; `[a, b]` lists become lists. Deliberately minimal -- the ADR head
    is a fixed shape, and depending on a YAML parser here would make the
    breadcrumb un-generatable on a host without one."""
    out: dict = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    try:
        start = lines.index("---")
    except ValueError:
        return out
    for line in lines[start + 1:]:
        if line.strip() == "---":
            break
        m = _SCALAR.match(line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            out[key] = [p.strip() for p in inner.split(",") if p.strip()]
        else:
            out[key] = val
    return out


def collect(root: str) -> list:
    d = os.path.join(root, ADR_DIR)
    if not os.path.isdir(d):
        return []
    rows = []
    for fn in sorted(os.listdir(d)):
        if not (fn.endswith(".md") and fn[:1].isdigit()):
            continue
        fm = parse_front_matter(os.path.join(d, fn))
        if not fm.get("adr"):
            continue
        rows.append({
            "file": fn,
            "num": str(fm.get("adr")).strip(),
            "title": str(fm.get("title") or "").strip(),
            "status": str(fm.get("status") or "").strip(),
            "date": str(fm.get("date") or "").strip(),
            "laws": fm.get("laws") or [],
            "ssot": fm.get("ssot_keys") or [],
        })
    return rows


def render(rows: list) -> str:
    n = len(rows)
    accepted = sum(1 for r in rows if r["status"] == "accepted")
    out = [
        "<!-- AI-hint: Repo-root breadcrumb to the MiOS Architecture Decision "
        "Records. GENERATED from the ADR front-matter by "
        "tools/generate-adr-index.py; do not hand-edit -- run the generator. "
        "The ADRs themselves stay baked at usr/share/doc/mios/adr/ (Law 1: a "
        "running MiOS carries its own why), so this file is a pointer, not a "
        "copy. -->",
        "<!-- AI-related: usr/share/doc/mios/adr/, "
        "usr/share/doc/mios/adr/README.md, usr/share/mios/mios.toml [laws], "
        "tools/generate-adr-index.py -->",
        "",
        "# MiOS Architecture Decision Records",
        "",
        f"**{n} ADRs** ({accepted} accepted). The records live at "
        "[`usr/share/doc/mios/adr/`](usr/share/doc/mios/adr/) and are **baked "
        "into the image** -- a running MiOS carries its own *why*. This file is "
        "the root breadcrumb so an agent starting at either repo root reaches "
        "any decision in two hops; the format and status lifecycle are "
        "described in [the ADR README](usr/share/doc/mios/adr/README.md).",
        "",
        "| # | Decision | Status | Date | Laws | SSOT keys |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        laws = ", ".join(str(x) for x in r["laws"]) or "--"
        ssot = ", ".join(f"`{x}`" for x in r["ssot"][:4]) or "--"
        if len(r["ssot"]) > 4:
            ssot += f", +{len(r['ssot']) - 4}"
        out.append(
            f"| {r['num']} | [{r['title']}]({ADR_DIR.replace(os.sep, '/')}/"
            f"{r['file']}) | {r['status']} | {r['date']} | {laws} | {ssot} |")
    out.append("")
    out.append("<!-- derived from the front-matter of "
               f"{n} file(s) under {ADR_DIR.replace(os.sep, '/')}/ -->")
    return "\n".join(out) + "\n"


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    check = "--check" in sys.argv
    rows = collect(root)
    if not rows:
        print(f"no ADRs found under {ADR_DIR}/", file=sys.stderr)
        return 0 if check else 1
    body = render(rows)
    path = os.path.join(root, OUT)
    if check:
        try:
            with open(path, encoding="utf-8") as fh:
                current = fh.read()
        except OSError:
            print(f"{OUT} is missing -- run tools/generate-adr-index.py")
            return 1
        if current != body:
            print(f"{OUT} is stale -- run tools/generate-adr-index.py")
            return 1
        print(f"{OUT} matches the {len(rows)} baked ADR(s)")
        return 0
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    print(f"wrote {OUT} from {len(rows)} ADR(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
