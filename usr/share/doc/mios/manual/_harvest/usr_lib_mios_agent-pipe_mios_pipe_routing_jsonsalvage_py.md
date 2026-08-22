<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Generic JSON-grammar salvage for small-model output....

Generic JSON-grammar salvage for small-model output.

Extracted from server.py (modularization). Pure stdlib (re + json) --
NO coupling to the agent-pipe globals, NO schema/field/topic/English knowledge.
This is the FIRST module split out of the 19k-line monolith; keep it dependency-free
so it stays trivially testable and importable.

<!-- mios-src:2350aa2f9f89 from usr/lib/mios/agent-pipe/mios_pipe/routing/jsonsalvage.py:3-9 -->

### Best-effort recovery of a JSON OBJECT from a small model's...

Best-effort recovery of a JSON OBJECT from a small model's NEAR-json output.
    operator binding NO-HARDCODES: this is generic STRUCTURAL repair of the JSON
    grammar -- it knows nothing about the schema, fields, topics, or any English.

    A tiny refine/planner model (qwen3:1.7b) intermittently emits ONE malformed
    token -- an empty value after a colon (`"k":` then `,`/`}`), a trailing comma,
    a // or /* */ comment, a Python True/False/None literal, or a truncated tail --
    and strict json.loads then DISCARDS THE ENTIRE otherwise-perfect object. That
 is the failure: refine produced a flawless trending plan
    (intent=agent, news=true, a clean refined_text) but one empty `inventory_filter`
    field at line 11 made json.loads raise -> the whole plan was dropped -> the
    degraded fallback web-searched "worldwide trends today" (dictionary/shipping
    junk) and punted. Recover the object instead of throwing it away.

    Returns the parsed dict, or None if it genuinely can't be salvaged.

<!-- mios-src:177a458ee298 from usr/lib/mios/agent-pipe/mios_pipe/routing/jsonsalvage.py:19-33 -->
