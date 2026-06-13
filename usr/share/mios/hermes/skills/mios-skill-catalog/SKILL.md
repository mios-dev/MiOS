---
name: mios-skill-catalog
description: |
  The MiOS skill catalog -- Phase C.2 cross-agent codified procedures.
  Promoted skills appear in your tool surface as `mios_skill__<name>`
  functions and run through the agent-pipe Semantic Firewall the
  same way native verbs do. Load this skill when the operator says
  "what skills do I have", "run my <name> skill", "automate <chain>",
  or any phrase referencing learned / saved procedures.
metadata:
  hermes:
    requires_tools:
      - mios_skill_run
      - mios_skill_list
---
<!-- AI-hint: Defines the MiOS skill catalog as a repository of codified, multi-agent procedure DAGs; agents use it to discover, list, and execute promoted skill chains via the mios_skill_run and mios_skill_list tools over the :8640 port.
     AI-related: /usr/share/mios/hermes/skills/mios-skill-catalog/SKILL.md._, mios-skill-catalog, mios-skills-miner, mios-skills, mios-skills-miner.timer -->

# MiOS skill catalog

> _MiOS-managed: seeded from
> /usr/share/mios/hermes/skills/mios-skill-catalog/SKILL.md._

The MiOS agent stack mines repeating tool-call sequences out of
SurrealDB and codifies them as `skill` rows. A promoted skill is a
parameterized DAG of MiOS verbs -- the same verbs you already call
directly. Every agent in the stack reads the same catalog so a
skill promoted from MiOS-OpenCode is callable from Hermes and vice
versa.

## Three access surfaces

| Surface | When to use |
| --- | --- |
| Tool: `mios_skill__<name>` | First-class tool call. Available for every promoted skill at startup; auto-refreshes on configurator save. |
| Tool: `mios_skill_run(name, params)` | Catch-all when the dynamic tool isn't registered yet (immediately-post-promote race). Same effect, same audit chain. |
| Tool: `mios_skill_list(status="promoted")` | Discovery. Returns names + descriptions so the agent can choose at run time. |

All three route through agent-pipe :8640 `/skills/*`, so the
Semantic Firewall + taint chain + audit rows apply identically to
direct verb dispatch.

## How a skill becomes runnable

1. Operator runs verb chain N times across sessions.
2. `mios-skills-miner.timer` fires `mios-skills mine`.
3. Miner inserts a `skill` row, `source=mined`, `status=candidate`.
4. Operator promotes via configurator HTML OR
   `mios-skills promote <name>`.
5. Hermes' next `/skills/openai-tools` refresh picks it up.

Operator-authored skills follow the same lifecycle minus step 1-2:
`mios-skills import` from a JSON template; promote.

## Examples (operator phrasing → tool call)

```
# Operator: "run my morning-routine skill"
mios_skill__morning_routine(app="chromedev")

# Operator: "what skills do I have?"
mios_skill_list(status="promoted")

# Operator: "save these steps as a skill called 'save-doc'"
# (no auto-promote -- ask for the parameter names first, then:)
mios_skill_run(name="save-doc", params={"body": "..."})
```

## What NOT to do

- Do NOT hardcode skill names in YOUR reasoning. The catalog is
  the source of truth -- call `mios_skill_list` if uncertain.
- Do NOT bypass `/skills/run` by stitching verbs manually. The
  audit chain stops working and the miner can't dedup -- the
  operator's promoted procedure gets mined AGAIN as a new
  candidate.
- Do NOT ask the operator for params the skill doesn't expose;
  call `mios_skill_list(status="promoted")` to read the `body.params`
  array.
