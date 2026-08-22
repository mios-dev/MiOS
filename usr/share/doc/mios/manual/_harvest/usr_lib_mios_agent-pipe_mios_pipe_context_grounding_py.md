<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Per-turn environment-grounding block builders (native <env>...

Per-turn environment-grounding block builders (native <env> system block).

Extracted verbatim from ``server.py``. Assembles the system-role grounding block
from host facts + config + the forwarded client/invocation environment. Every
function is moved byte-for-byte; ``server.py`` re-imports each under its original
``_``-prefixed name so the module's importable surface is unchanged.

Config constants come from ``mios_config``; the per-request ``_client_env_var``
ContextVar and the ``_current_date_str`` helper (both stay in ``server.py``) are
injected via :func:`configure` (one-way module boundary -- this module never
imports ``server``).

<!-- mios-src:371cad9fae1a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:3-14 -->

### A COMPACT live capability summary for identity grounding...

A COMPACT live capability summary for identity grounding: one line per
    catalog section listing the real verb names (from _VERB_CATALOG, i.e. the
    mios.toml [verbs.*] SSOT). The model then answers "what can you do?" from its
    ACTUAL tool surface instead of inventing capabilities. Names only + capped
    per section to keep the system block (and the RadixAttention stable prefix)
    short. Rare-tier verbs are omitted -- still dispatchable, just not advertised.
    No hardcoded English: re-derived from the catalog on every load.

<!-- mios-src:37a34aa81f04 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:63-69 -->

### One system-message block giving the agents the current...

One system-message block giving the agents the current date/time.

    The micros have no clock. Without this, relative dates ("tomorrow",
    "this weekend") were resolved by guessing off whatever dates appeared
    in retrieved text -- operator-flagged: "what's tomorrow at Tech Con"
    came back as TODAY's date and three other dates across one answer.
    This grounds the orchestrator's OWN system prompts (refine / polish /
    dispatch); it is NOT a pre_llm_call env-inject into the user message.

    Timezone/date/time come from the USER's Open WebUI client context when
    the pipe forwarded it (metadata.variables: CURRENT_TIMEZONE / CURRENT_DATE
    / CURRENT_TIME / CURRENT_WEEKDAY), so "today"/"tomorrow" match the
    OPERATOR's wall clock, not the server's (the VM is often UTC). Falls back
    to the process-local clock when no client context is present (Discord, raw
 API). "use detected environment details -- locations,
    timezones, locale, time".

<!-- mios-src:83b29bd77a9a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:103-118 -->

### The host's IANA timezone (e.g. 'America/New_York') -- a...

The host's IANA timezone (e.g. 'America/New_York') -- a REAL, always-
    available env detail (read once from /etc/localtime). Used as the coarse
    locale-of-last-resort for 'local' / 'near me' asks when no precise user
    location was forwarded or configured, so the agent grounds to the right
 REGION instead of fabricating unrelated cities (OWUI on
    phone answered 'local weather' for five random US cities, observing no env).

<!-- mios-src:1c1f53773b50 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:233-238 -->

### Client/session grounding -- the user's REAL location +...

Client/session grounding -- the user's REAL location + locale forwarded
    by the OWUI pipe (metadata.variables: USER_LOCATION / USER_LANGUAGE /
    USER_NAME). Like _temporal_grounding it grounds the orchestrator's OWN
    system prompts (refine / swarm / council / polish); NOT a pre_llm_call
    user-message inject. Returns '' when the client sent nothing (Discord, raw
 API, location-sharing off) so nothing is fabricated.
    "OWUI provides entire environment details ... USE them in the pipeline";
    the location is what lets 'near me' resolve instead of a placeholder.

<!-- mios-src:24eeb4ebff7a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:256-263 -->

### Non-negotiable identity grounding injected into EVERY...

Non-negotiable identity grounding injected into EVERY orchestrator prompt
    (refine / synthesis / polish / council / native-loop) via _env_grounding.

    The local backend models (granite/qwen) confabulate a cloud identity when
    asked "who are you / what model are you" -- a small model fills the gap with
    its training prior and claimed to "provide access to Claude (Fable 5 / Mythos
 5) with Constitutional AI" (operator-caught fabrication). MiOS is
    local-only; the /MiOS.md guard only reaches the native-loop path, so the
    verb-DAG synthesis/polish path needed its own copy. Kept terse + forceful;
    leads with the prohibition so it survives a long prompt.

<!-- mios-src:f835ba87f897 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:351-360 -->

### A fixed-shape, parseable <env> block of the LIVE per-turn...

A fixed-shape, parseable <env> block of the LIVE per-turn environment
 (research a small ~8B model reads structured key:value far more
    reliably than the prose helpers, which it routinely overrides). This is the
    CANONICAL 'every prompt env-grounded natively' mechanism -- a SYSTEM-role block
    refreshed each turn, NOT a pre_llm_call user-message inject (that is the banned
    hack). Values are LIVE this turn from the forwarded invocation env + host facts;
    an undetermined key is OMITTED (never fabricated). cwd/surface/location come
    ONLY from this turn's context, never recall. Reuses the SAME getters +
    location-chain as _client_grounding so the structured + prose views agree.

<!-- mios-src:ecf18a54098a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:432-440 -->

### Identity guard + self-architecture + temporal +...

Identity guard + self-architecture + temporal + client-environment grounding
    for the orchestrator's OWN system prompts (refine / synthesis / polish / swarm /
    council / native-loop). Single helper so every grounded prompt site threads the
    identity + arch + forwarded OWUI environment (time, timezone, location, locale,
    name) in one place. Leads with a STRUCTURED <env> block (research
    parseable key:value for small models) followed by the detailed prose guidance +
    anti-fabrication rules -- the prose is kept so nothing regresses.

<!-- mios-src:16c83df3c8e3 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:522-528 -->

### Resolve THIS request's bearer token to the account/owner...

Resolve THIS request's bearer token to the account/owner identity BOUND to its
    caller-key, or None when there is no token / no mapping / the resolver was not
    injected (degrade-open). The canonical shared + ingress keys resolve to the
    full-trust operator principal, which carries NO bound account -> None here, so a
    trusted gateway (OWUI) keeps speaking for its forwarded per-user identity. The
    per-key binding is the optional `account` (alias `owner`) field on the caller-key
    entry (see mios.toml [security].principal_bind_mode).

<!-- mios-src:dce689bf9d35 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:558-564 -->

### Normalise the per-request client/session context the OWUI...

Normalise the per-request client/session context the OWUI pipe forwards.

    Primary source is metadata.variables (OWUI's own convention; keys carry
    the {{ }} braces, e.g. "{{USER_LOCATION}}"). We also accept a top-level
    `variables` dict and directly-placed known keys (non-OWUI callers), plus
    the standard OpenAI `user` field as a last-resort display name. Returns a
    flat dict {location, timezone, date, time, datetime, weekday, language,
    user_name, user_email} with empty strings for anything not provided.

<!-- mios-src:fbeef67db77a from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:582-589 -->

### Current 4-digit year. Prefers the USER's client date (the...

Current 4-digit year. Prefers the USER's client date (the env-detected
    value the OWUI pipe forwarded) so a query anchors to the OPERATOR's NOW,
    falling back to the live system clock. NEVER hardcode the year (operator
 "use env detect for current values for all AI functions / fall
    back to embedding the current year").

<!-- mios-src:462d85580302 from usr/lib/mios/agent-pipe/mios_pipe/context/grounding.py:736-740 -->
