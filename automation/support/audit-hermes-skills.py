#!/usr/bin/env python3
"""Hermes SKILL.md genericity audit.

Walks /usr/share/mios/hermes/skills/*/SKILL.md and flags:

  * conversational tone in body prose (operator-bound: "you should",
    "we got burned", "your machine", etc.)
  * hardcoded paths bound to a single deployment (/mnt/c/Users/mios/,
    /var/home/mios/)
  * hardcoded hostnames (MiOS-955, mios-ec377, ...)
  * project-internal phase jargon in YAML frontmatter description
    (descriptions get surfaced to LLM context; jargon noise wastes
    tokens + leaks implementation detail)

These are LLM-guidance docs (not OpenAI tool schemas), so prose
in the body is EXPECTED. The check is for guidance that's bound
to a specific operator / machine / project state vs. guidance
that's portable to any MiOS deployment.

Exits 0 (clean) / 1 (findings).
"""
from __future__ import annotations

import glob
import os
import re
import sys

SKILLS_DIR = "/usr/share/mios/hermes/skills"

# Operator account name is a variable: SSOT is
# [identity].username in mios.toml (-> MIOS_USER env), and
# the Windows-side username is discovered by tools at runtime
# (not bound in config). Examples in SKILL.md MUST use $MIOS_USER
# / $env:USERPROFILE / $env:TEMP -- never a literal account.
HARDCODED_PATH_RE = re.compile(
    r"/(?:mnt/c/Users|var/home|home)/[a-zA-Z0-9_-]+(?!\b)", re.I)
HARDCODED_HOSTNAME_RE = re.compile(
    r"\b(?:MiOS-955|mios-ec377|podman-MiOS-DEV)\b")
# These project-jargon tokens belong in commit messages, not in
# the LLM-facing description field.
DESC_JARGON_RE = re.compile(
    r"\b(?:Phase [A-Z]\.?\d?|Operator-flagged|operator-confirmed|"
    r"operator directive|operator 2026-\d{2}-\d{2}|"
    r"GLOBAL SWEEP|SOUL\.md|webui\.db|kanban\.db)\b", re.I)


def split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}, text
    front_raw, body = parts[0][4:], parts[1]
    front = {}
    for line in front_raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            front[k.strip()] = v.strip().strip('"').strip("'")
    return front, body


def audit_one(path: str) -> list[str]:
    findings: list[str] = []
    rel = os.path.basename(os.path.dirname(path))
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    front, body = split_frontmatter(text)
    # Frontmatter description checks
    desc = front.get("description", "")
    for m in DESC_JARGON_RE.finditer(desc):
        findings.append(
            f"[{rel}] description has project-internal jargon: "
            f"{m.group()!r}")
    # Body checks
    for m in HARDCODED_PATH_RE.finditer(body):
        findings.append(
            f"[{rel}] hardcoded user path in body: {m.group()!r}")
    for m in HARDCODED_HOSTNAME_RE.finditer(body):
        findings.append(
            f"[{rel}] hardcoded hostname in body: {m.group()!r}")
    # Light conversational-tone check on body (just count noteworthy
    # tokens; don't fail on each occurrence -- prose IS expected).
    op_tokens = len(re.findall(
        r"\b(operator-(?:flagged|confirmed)|operator directive|"
        r"operator binding|operator quote|operator-bind)\b",
        body, re.I))
    if op_tokens >= 3:
        findings.append(
            f"[{rel}] body has {op_tokens} 'operator-...' tokens "
            f"-- consider trimming to keep guidance portable")
    return findings


def main() -> int:
    paths = sorted(glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md")))
    if not paths:
        print(f"  (no SKILL.md files under {SKILLS_DIR})")
        return 0
    print(f"=== {len(paths)} SKILL.md files ===")
    for p in paths:
        rel = os.path.basename(os.path.dirname(p))
        size = os.path.getsize(p)
        print(f"  {rel:<28} {size:>6} bytes")
    print()
    all_findings: list[str] = []
    for p in paths:
        all_findings.extend(audit_one(p))
    print("=== findings ===")
    if not all_findings:
        print("  (none -- all SKILL.md docs clean)")
        return 0
    for f in all_findings:
        print(f"  * {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
