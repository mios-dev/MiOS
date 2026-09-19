---
name: websearch
description: Targeted web discovery for canonical vendor documentation, API specifications, changelogs, and exact error signatures. Use for a quick fact check during work; use /research for a full upstream audit.
argument-hint: "QUERY-or-error-signature"
allowed-tools: WebSearch, WebFetch
---
# /websearch — quick, cited fact check

_Paths: `${CLAUDE_SKILL_DIR}/../dev-loop/scripts/` resolves in Claude Code; in other harnesses use `<skills dir>/dev-loop/scripts/` (the shims in `shims/<harness>/` already do)._

Query: `$ARGUMENTS`. Search the exact signature; prefer vendor docs/changelogs/GitHub issues over aggregators; open the primary page; answer with version numbers and URLs; say what remains unverified. Log durable findings with `python3 ${CLAUDE_SKILL_DIR}/../dev-loop/scripts/research.py search "<query>"` only if they belong in the project record.
