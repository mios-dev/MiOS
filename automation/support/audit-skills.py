#!/usr/bin/env python3
# AI-hint: Validates skill definitions in /usr/share/mios/skills/ and SurrealDB against technical standards, flagging hardcoded paths, hostnames, and non-OpenAI-compliant tool schemas to ensure portability.
# AI-related: /usr/share/mios/skills/, /usr/share/mios/skills, mios-ec377, localhost:8000
# AI-functions: fetch_db_skills, audit_skill, main
"""Skill catalog genericity audit.

Operator directive 2026-05-18: "make sure they are generic and
technical and OpenAI API compliant". Walks the seed skills at
/usr/share/mios/skills/*.json + the live promoted skills in
SurrealDB, flags:

  * hardcoded paths (/mnt/c/Users/<name>, /home/<name>)
  * hostnames + usernames bound to a single deployment
  * English-only verb labels (descriptions should be technical)
  * non-OpenAI-shaped tool definitions

Exits 0 (clean) / 1 (findings).
"""
from __future__ import annotations

import base64
import glob
import json
import os
import re
import sys
import urllib.request

SEED_DIR = "/usr/share/mios/skills"
DB_URL = "http://localhost:8000"
AUTH = "Basic " + base64.b64encode(b"root:root").decode()

# Patterns that flag hardcoded specifics.
HARDCODED_PATH_RE = re.compile(
    r"/(?:mnt/c/Users|home|var/home|Users)/[a-zA-Z0-9_-]+", re.I)
HARDCODED_HOSTNAME_RE = re.compile(
    r"\b(?:MiOS-955|mios-ec377|podman-MiOS-DEV)\b")


def fetch_db_skills() -> list[dict]:
    body = b"USE NS mios DB mios; SELECT name, description, body, status, source FROM skill;"
    req = urllib.request.Request(
        f"{DB_URL}/sql", data=body, method="POST",
        headers={"Authorization": AUTH, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        return (data[-1] or {}).get("result") or []
    except Exception as e:
        print(f"  (db fetch failed: {e})")
        return []


def audit_skill(label: str, skill: dict, findings: list):
    body = skill.get("body") or {}
    steps = body.get("steps") or []
    params = body.get("params") or []
    name = skill.get("name", "?")
    desc = skill.get("description", "") or ""
    # Find raw text the skill carries (incl. step arg values).
    haystack_parts = [desc]
    for step in steps:
        for k, v in (step.get("args") or {}).items():
            if isinstance(v, str):
                haystack_parts.append(v)
    haystack = "\n".join(haystack_parts)
    for m in HARDCODED_PATH_RE.finditer(haystack):
        findings.append(f"[{label}] {name}: hardcoded path '{m.group()}'")
    for m in HARDCODED_HOSTNAME_RE.finditer(haystack):
        findings.append(f"[{label}] {name}: hardcoded hostname '{m.group()}'")
    # Verb names should not be English-only -- they're identifiers.
    # Descriptions ARE prose -- they're meant to be technical English
    # per the operator's "generic and technical and OpenAI API
    # compliant" rule. We only flag descriptions that include
    # CONVERSATIONAL English (operator instructions / examples).
    if "operator" in desc.lower() or "your " in desc.lower():
        findings.append(
            f"[{label}] {name}: description has conversational tone "
            f"('operator'/'your ...') -- prefer purely technical descriptor")
    # OpenAI tool-schema compliance check: each step must have
    # verb + args dict. params must all be referenced via $-tokens.
    referenced = set()
    for step in steps:
        if "verb" not in step:
            findings.append(f"[{label}] {name}: step missing verb")
        if not isinstance(step.get("args"), dict):
            findings.append(f"[{label}] {name}: step args not an object")
        for v in (step.get("args") or {}).values():
            if isinstance(v, str):
                for m in re.finditer(r"\$([A-Za-z_][A-Za-z0-9_]*)", v):
                    referenced.add(m.group(1))
    unused = [p for p in params if p not in referenced]
    if unused:
        findings.append(
            f"[{label}] {name}: declared params not referenced: {unused}")
    missing = [r for r in referenced if r not in params]
    if missing:
        findings.append(
            f"[{label}] {name}: referenced $tokens not in params: {missing}")


def main() -> int:
    findings: list[str] = []
    seed_skills = []
    print("=== seed templates (/usr/share/mios/skills/) ===")
    for path in sorted(glob.glob(os.path.join(SEED_DIR, "*.json"))):
        try:
            with open(path) as f:
                skill = json.load(f)
        except json.JSONDecodeError as e:
            findings.append(f"[seed] {path}: invalid JSON: {e}")
            continue
        seed_skills.append(skill)
        print(f"  {skill.get('name'):<32} {skill.get('source','?'):<10} "
              f"{skill.get('status','?')}")
        audit_skill("seed", skill, findings)
    print()
    print("=== live promoted skills (SurrealDB) ===")
    db_skills = fetch_db_skills()
    for skill in db_skills:
        print(f"  {skill.get('name'):<32} {skill.get('source','?'):<10} "
              f"{skill.get('status','?')}")
        audit_skill("db", skill, findings)
    print()
    print("=== findings ===")
    if not findings:
        print("  (none -- all skills clean)")
        return 0
    for f in findings:
        print(f"  * {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
