<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-facing doc genericity audit. Walks every doc that gets...

AI-facing doc genericity audit.

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

<!-- mios-src:65a0b7c0f706 from automation/support/audit-hermes-skills.py:3-27 -->
