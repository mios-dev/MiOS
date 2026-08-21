#!/usr/bin/env python3
# AI-hint: Link-integrity gate for the shipped MiOS manual: asserts every ToC link in usr/share/doc/mios/manual.md resolves to an existing chapter file and, where a fragment is given, to a real anchor inside it, and that no chapter file is unreachable from the ToC.
# AI-related: usr/share/doc/mios/manual.md, usr/share/doc/mios/manual, usr/libexec/mios/mios-manual, automation/98-drift-checks.sh
"""Fail if the manual's ToC points at a chapter file or anchor that is not there."""
import os
import re
import sys

ROOT = os.environ.get("MIOS_ROOT", ".")
DOCS = os.path.join(ROOT, "usr/share/doc/mios")
MANUAL = os.path.join(DOCS, "manual.md")
LINK_RE = re.compile(r"\[([^\]]*)\]\((manual/ch[^)]+)\)")
ANCHOR_RE = re.compile(r'<a\s+name="([^"]+)"', re.I)


def main() -> int:
    if not os.path.isfile(MANUAL):
        print(f"manual entry point missing: {MANUAL}", file=sys.stderr)
        return 1
    text = open(MANUAL, encoding="utf-8").read()
    links = LINK_RE.findall(text)
    bad = []
    for _, target in links:
        path, _, frag = target.partition("#")
        full = os.path.join(DOCS, path)
        if not os.path.isfile(full):
            bad.append(f"manual.md -> missing chapter file: {target}")
            continue
        if frag:
            anchors = set(ANCHOR_RE.findall(open(full, encoding="utf-8").read()))
            if frag not in anchors:
                bad.append(f"manual.md -> missing anchor: {target}")
    referenced = {t.partition("#")[0] for _, t in links}
    chapters = sorted(
        "manual/" + f
        for f in os.listdir(os.path.join(DOCS, "manual"))
        if f.startswith("ch") and f.endswith(".md")
    )
    bad += [f"chapter unreachable from the ToC: {c}" for c in chapters if c not in referenced]
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    print(f"manual links resolve ({len(links)} ToC links, {len(chapters)} chapters)")
    return 0


sys.exit(main())
