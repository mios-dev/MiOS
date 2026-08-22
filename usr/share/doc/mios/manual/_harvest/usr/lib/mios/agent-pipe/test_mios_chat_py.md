<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### The micro-LLM early-reply helpers (intent=chat reply...

The micro-LLM early-reply helpers (intent=chat reply, memory-hit judge,
    location-ask), now owned by mios_chat (the injection was reversed). Asserts
    (1) the no-network GUARDS short-circuit and (2) the degrade-open except path.
    Inputs are SYNTHETIC opaque tokens (no English example words); the REFINE lane
    is never actually called -- httpx is swapped for a client that raises and
    _env_grounding is stubbed so the system-prompt assembly stays local.

<!-- mios-src:c27eef8e3ea2 from usr/lib/mios/agent-pipe/test_mios_chat.py:386-391 -->

### The refine-driven orchestration helpers, now owned by...

The refine-driven orchestration helpers, now owned by mios_chat (the
    injection was reversed): the action-hint gate (_hints_write_action), the
    micro-LLM knowledge-gap judge (_needs_external_knowledge) and the multi-task
    queue writer (_shadow_queue_tasks). SYNTHETIC opaque verb tokens + permissions
    (no English example words); no network (the judge degrades open via the
    raising httpx stub) and no DB (the queue writer's guard paths return early).

<!-- mios-src:183e1948a3f8 from usr/lib/mios/agent-pipe/test_mios_chat.py:417-422 -->
