---
name: research
description: Upstream research before deciding - vendor docs, changelogs, release diffs (`base_ref..upstream_ref`), breaking-change audits, and technology evaluations, written into SPIKE / UPSTREAM_AUDIT / TECH_EVAL documents. Use before an architectural decision, a dependency bump, a migration, or when a deprecation warning appears.
argument-hint: "TOPIC | diff BASE_REF UPSTREAM_REF | template spike|upstream-audit|tech-eval"
context: fork
agent: dev-loop:researcher
allowed-tools: WebSearch, WebFetch, Read, Write, Grep, Glob, Bash
---
# /research — upstream truth before decisions (SKILL §4)

_Paths: `${CLAUDE_SKILL_DIR}/../dev-loop/scripts/` resolves in Claude Code; in other harnesses use `<skills dir>/dev-loop/scripts/` (the shims in `shims/<harness>/` already do)._

Input: `$ARGUMENTS`.

1. **Scope**: state the exact question (error signature, API, version). Read the lockfile first — research the *installed* version, not the latest.
2. **Primary sources first**: vendor docs, changelog, release notes, the installed package source. Aggregator blogs are corroboration only. Cite URLs and versions.
3. **Two-way deprecation check**: was it really removed/replaced, or is it an unmerged proposal? Is the recommended replacement still current?
4. **Release diffing**: `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/research.py diff <base_ref> <upstream_ref>` (tags/SHAs) → breaking-change list.
5. **Write it down**: `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/research.py template spike|upstream-audit|tech-eval` then fill the document under `docs/`; link it from the task (`links`) or an ADR (`artifacts.py adr new`).
6. Return: findings, versions, sources, recommendation with trade-offs, and what remains unverified. No code changes in this skill.
