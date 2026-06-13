#!/usr/bin/env python3
# AI-hint: Audit script to identify and flag non-portable, environment-specific data (hardcoded paths, hostnames, or project-specific jargon) in LLM-facing documentation within the hermes/skills and ai directories.
# AI-related: /usr/share/mios/hermes/skills/, /usr/share/mios/ai/, /usr/share/mios/hermes/skills, /usr/share/mios/ai, mios-ec377
# AI-functions: split_frontmatter, audit_one, audit_ai_doc, main
"""AI-facing doc genericity audit.

Walks every doc that gets loaded into an LLM's context window and
flags content bound to a single deployment / operator / project
state. Covers:

  * /usr/share/mios/hermes/skills/*/SKILL.md   (per-skill guidance)
  * /usr/share/mios/ai/*.md                    (system + SOUL docs)

Findings:
  * conversational tone in body prose ("operator-flagged YYYY-MM-DD")
  * hardcoded paths bound to a single user (/mnt/c/Users/<name>,
    /var/home/<name>); operator name is an SSOT variable
    ([identity].username -> MIOS_USER)
  * hardcoded hostnames (MiOS-955, mios-ec377, ...)
  * project-internal phase jargon in YAML frontmatter description
    (descriptions get surfaced to LLM context; jargon noise wastes
    tokens + leaks implementation detail)

These are LLM-guidance docs, so prose in the body is EXPECTED.
The check is for guidance bound to a specific operator / machine
/ project state vs. guidance portable to any MiOS deployment.

Exits 0 (clean) / 1 (findings).
"""
from __future__ import annotations

import glob
import os
import re
import sys

SKILLS_DIR = "/usr/share/mios/hermes/skills"
AI_DOCS_DIR = "/usr/share/mios/ai"
# AI docs to skip: by design these reference scrub-targets or use
# canonical "user:user" build-recipe placeholders that look like
# leaks but aren't.
AI_DOC_SKIP = {"audit-prompt.md", "INDEX.md"}
# Also skip Claude-side meta files in the AI dir that document our
# OWN agent behavior rather than getting loaded into MiOS-Agent.
AI_DOC_PATTERN = "*.md"
# Allow temporal framing in lines that ARE temporal events the model
# legitimately needs to anchor (release-date facts, version pins).
TEMPORAL_FACT_RE = re.compile(
    r"(Fedora \d+ released|released \d{4}-\d{2}-\d{2}|"
    r"build-time|since \d{4}-\d{2})", re.I)

# Operator account name is a variable: SSOT is
# [identity].username in mios.toml (-> MIOS_USER env), and
# the Windows-side username is discovered by tools at runtime
# (not bound in config). Examples in SKILL.md MUST use $MIOS_USER
# / $env:USERPROFILE / $env:TEMP -- never a literal account.
#
# Exempt: the conventional placeholder identifiers "user" and
# "claude" -- these are widely-recognized stand-ins, not real
# account leaks. Real account names get flagged.
HARDCODED_PATH_RE = re.compile(
    r"/(?:mnt/c/Users|var/home|home)/"
    r"(?!(?:user|claude)\b)[a-zA-Z0-9_-]+(?!\b)", re.I)
HARDCODED_HOSTNAME_RE = re.compile(
    r"\b(?:MiOS-955|mios-ec377|podman-MiOS-DEV)\b")
# These project-jargon tokens belong in commit messages, not in
# the LLM-facing description field.
DESC_JARGON_RE = re.compile(
    r"\b(?:Phase [A-Z]\.?\d?|Operator-flagged|operator-confirmed|"
    r"operator directive|operator 2026-\d{2}-\d{2}|"
    r"GLOBAL SWEEP|SOUL\.md|webui\.db|kanban\.db)\b", re.I)
# Same shape as DESC_JARGON_RE but applied to AI prose-doc bodies
# (system.md, SOUL.md, etc). These docs DO carry per-turn weight
# in every LLM session -- temporal/personal framing is pure noise.
BODY_JARGON_RE = re.compile(
    r"\b(?:Operator-flagged \d{4}-\d{2}-\d{2}|"
    r"operator-confirmed \d{4}-\d{2}-\d{2}|"
    r"operator directive \d{4}-\d{2}-\d{2}|"
    r"operator 2026-\d{2}-\d{2})\b", re.I)


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


def audit_ai_doc(path: str) -> list[str]:
    findings: list[str] = []
    rel = os.path.basename(path)
    with open(path, "r", encoding="utf-8") as f:
        body = f.read()
    for m in HARDCODED_PATH_RE.finditer(body):
        findings.append(
            f"[ai/{rel}] hardcoded user path: {m.group()!r}")
    for m in HARDCODED_HOSTNAME_RE.finditer(body):
        findings.append(
            f"[ai/{rel}] hardcoded hostname: {m.group()!r}")
    for m in BODY_JARGON_RE.finditer(body):
        # Skip if the line is a legitimate temporal fact
        line = body.rfind("\n", 0, m.start())
        line_end = body.find("\n", m.end())
        line_text = body[line + 1:line_end if line_end >= 0 else None]
        if TEMPORAL_FACT_RE.search(line_text):
            continue
        findings.append(
            f"[ai/{rel}] temporal/operator framing: {m.group()!r}")
    return findings


def main() -> int:
    skill_paths = sorted(
        glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md")))
    ai_paths = sorted(
        p for p in glob.glob(os.path.join(AI_DOCS_DIR, AI_DOC_PATTERN))
        if os.path.basename(p) not in AI_DOC_SKIP)
    if not skill_paths and not ai_paths:
        print("  (no AI-facing docs found)")
        return 0
    print(f"=== {len(skill_paths)} SKILL.md + {len(ai_paths)} "
          f"AI-doc files ===")
    for p in skill_paths:
        rel = os.path.basename(os.path.dirname(p))
        size = os.path.getsize(p)
        print(f"  skill/{rel:<24} {size:>6} bytes")
    for p in ai_paths:
        rel = os.path.basename(p)
        size = os.path.getsize(p)
        print(f"  ai/{rel:<27} {size:>6} bytes")
    print()
    all_findings: list[str] = []
    for p in skill_paths:
        all_findings.extend(audit_one(p))
    for p in ai_paths:
        all_findings.extend(audit_ai_doc(p))
    print("=== findings ===")
    if not all_findings:
        print("  (none -- all AI-facing docs clean)")
        return 0
    for f in all_findings:
        print(f"  * {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
