<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_blades -- blade (machine) topology + per-blade...

mios_blades -- blade (machine) topology + per-blade capacity model.

V4 makes "nodes X, Y, Z are one machine" EXPRESSIBLE: each [nodes.*] may carry an
optional `blade` (which physical machine it lives on), and [blades.<name>] declares
that machine's capacity. V5 gives the model a real consumer: the admission gate
compares a node's residents against ITS blade's VRAM budget instead of the single
LOCAL scalar (the "remote residents vs one local VRAM scalar" bug).

DEFAULT-PRESERVING by construction: a node with no `blade` belongs to the LOCAL blade
(name from the [identity] hostname SSOT), whose capacity defaults to the caller's
existing VRAM_BUDGET_MB. So a config with no [blades.*] and no blade fields resolves
every endpoint to one local blade at the local budget -- i.e. exactly today. Every
lookup degrades OPEN (unknown blade/capacity -> the local scalar) so admission can
never wedge on a missing blade.

<!-- mios-src:2d964abe9c10 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/blades.py:3-17 -->

### Resolve THIS machine's blade name from SSOT, NOT a baked...

Resolve THIS machine's blade name from SSOT, NOT a baked literal.

    Precedence: env ``MIOS_HOSTNAME`` (the install.env bridge derived from
    [identity].hostname) -> [identity].hostname -> the OS hostname
    (``socket.gethostname()``) as the degrade-open fallback. Always returns a
    non-empty name when the OS can report one; only a total failure yields ''.

<!-- mios-src:be081ba9cb54 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/blades.py:43-49 -->

### Build ``{blade_name: {"vram_budget_mb": int, "load_ceil"...

Build ``{blade_name: {"vram_budget_mb": int, "load_ceil": float|None}}``.

    The LOCAL blade is ALWAYS present and defaults to the caller's existing
    VRAM_BUDGET_MB scalar (and optional local load ceiling), so a config with NO
    [blades.*] section reproduces today's single-blade capacity byte-for-byte. A
    declared [blades.<local>] may OVERRIDE the local capacity; remote blades carry
    their own. A declared blade that omits ``vram_budget_mb`` degrades OPEN to the
    local scalar (unknown capacity is never a wedge). Degrade-open: a malformed or
    absent section -> just the local blade at the local scalar.

<!-- mios-src:364670302905 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/blades.py:66-75 -->

### Map each registry endpoint (``host:port`` via...

Map each registry endpoint (``host:port`` via ``endpoint_key``) to its blade.

    A [nodes.*]/[agents.*] entry with an explicit ``blade`` carries it; one WITHOUT a
    blade belongs to the LOCAL blade -- so a config with no blade fields makes every
    endpoint local (today). Returns ``{endpoint_key: blade_name}``. Endpoints absent
    from this map resolve to the local blade at lookup time (see blade_for_endpoint).

<!-- mios-src:182df9a6bf99 from usr/lib/mios/agent-pipe/mios_pipe/scheduler/blades.py:112-118 -->
