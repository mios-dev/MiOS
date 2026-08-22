<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### P2.1 ("council not fan-out"): per-secondary role lens...

P2.1 ("council not fan-out"): per-secondary role
    lens prompt so a council DOES NOT send the same prompt to N models. Each
    secondary gets a small system message identifying its angle (its role +
    declared strengths from mios.toml [agents.*]) so the council answers from
    DIVERSE perspectives instead of duplicating one answer N times. SSOT-
    derived (no hardcoded per-agent text); empty when the agent has neither
    a role nor strengths -- harmless fall-back to identical-prompt mode.

<!-- mios-src:17120f99c511 from usr/lib/mios/agent-pipe/mios_pipe/context/promptfmt.py:11-17 -->

### Render a compact system-message prefix from a refined plan....

Render a compact system-message prefix from a refined plan.
    Injected at the head of `messages` when proxying to a sub-
    agent so the agent receives MiOS-Agent's intent + suggested
    tools/skills/outcome -- NOT as free-form prose, but as a
    structured marker block the agent's own system prompt can
    parse.

    Format kept tight (~150-250 tokens) so even a 4K-context
    micro-model has plenty of room for the conversation itself.

<!-- mios-src:61db4666603a from usr/lib/mios/agent-pipe/mios_pipe/context/promptfmt.py:95-104 -->

### Render a short user-facing preamble surfacing what's in the...

Render a short user-facing preamble surfacing what's in the
    queue. Goes at the TOP of the polished reply so the operator
    sees the queue state up front (and the polished response for
    the active task comes immediately below).

<!-- mios-src:5012dd72a750 from usr/lib/mios/agent-pipe/mios_pipe/context/promptfmt.py:156-159 -->
