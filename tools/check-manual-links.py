#!/usr/bin/env python3
# AI-hint: Link-integrity gate for the shipped docs. (1) Every ToC link in usr/share/doc/mios/manual.md resolves to an existing chapter file and, where a fragment is given, a real anchor, and no chapter is unreachable from the ToC. (2) Every EXPLICITLY relative link (./x, ../x) anywhere under usr/share/doc/mios resolves -- that class has exactly one meaning, unlike a repo-root-relative path, and it is how audit-INDEX.md kept pointing at audit-mios-mini.md for the whole time after that name was reassigned to MiOS-Metal.
# AI-related: usr/share/doc/mios/manual.md, usr/share/doc/mios/manual, usr/libexec/mios/mios-manual, automation/98-drift-checks.sh
"""Fail if the manual's ToC points at a chapter file or anchor that is not there."""
import os
import re
import sys

ROOT = os.environ.get("MIOS_ROOT", ".")
DOCS = os.path.join(ROOT, "usr/share/doc/mios")
MANUAL = os.path.join(DOCS, "manual.md")
LINK_RE = re.compile(r"\[([^\]]*)\]\((manual/ch[^)]+)\)")
# Only ./x and ../x: a bare `usr/share/...` is repo-root-relative by convention
# and resolving it as file-relative would invent 190 false findings.
REL_RE = re.compile(r"\[[^\]]*\]\((\.{1,2}/[^)#\s]+)(?:#[^)\s]*)?\)")
ANCHOR_RE = re.compile(r'<a\s+name="([^"]+)"', re.I)


def relative_link_violations() -> list:
    """Every ./x or ../x link under the docs tree must resolve."""
    viol = []
    for dirpath, _dirnames, filenames in os.walk(DOCS):
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            src = os.path.join(dirpath, fn)
            try:
                with open(src, encoding="utf-8", errors="replace") as fh:
                    body = fh.read()
            except OSError:
                continue
            for m in REL_RE.finditer(body):
                target = m.group(1)
                if not os.path.exists(os.path.normpath(
                        os.path.join(dirpath, target))):
                    viol.append("%s links to %s, which does not exist"
                                % (os.path.relpath(src, ROOT).replace(os.sep, "/"),
                                   target))
    return viol


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
    rel = relative_link_violations()
    bad += rel
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    print(f"manual links resolve ({len(links)} ToC links, {len(chapters)} chapters); "
          f"every explicitly-relative doc link resolves")
    return 0


sys.exit(main())
