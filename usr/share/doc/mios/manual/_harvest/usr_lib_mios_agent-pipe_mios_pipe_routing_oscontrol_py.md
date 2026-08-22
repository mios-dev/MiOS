<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### OS-control fast-path responder + window enum/verify helpers...

OS-control fast-path responder + window enum/verify helpers (refactor R9).

Extracted VERBATIM from ``server.py`` -- the deterministic one-verb OS-control
action path (``_respond_os_control``) and the window-enumeration / before-after
diff / launch-verification / anti-fabrication-verdict helpers it owns. Every
function is moved byte-identically (LIVE hot path: computer-use / launch /
window-op); their consolidation is NOT in scope. ``server.py`` re-imports every
name under its original alias so the module's public surface is byte-identical.

Sibling functions (the ``_sse_*`` emitters, the broker ``dispatch_mios_verb``,
``polish_response``, ``_store_knowledge``, ``loads_lenient``, the DCI critic) are
imported directly; every server-side symbol the path touches (the ``OS_CONTROL_*``
config scalars, the ``_OS_CONTROL_ACTION_VERBS`` / ``_LAUNCH_VERBS`` verb sets, the
conv-key ContextVar, ``_get_client``, ``_scratchpad_note``, the ``_db_*`` helpers,
``_inline_satisfaction_check``, ``_strip_think_tags``) is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).

<!-- mios-src:01f018fae7b9 from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:3-19 -->

### Inject server.py's OS-control config scalars, the verb...

Inject server.py's OS-control config scalars, the verb sets, the conv-key
    ContextVar and the runtime helpers the fast-path calls back into.

    Callable more than once with a partial set (mios_sched-style): server.py
    injects ``fastpath_verbs`` / ``verb_catalog`` EARLY (the import-time stage --
    ``_render_os_control_verbs`` is called at server import) and the remaining
    runtime deps LATE, once they are all defined.

<!-- mios-src:f85144cbbb20 from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:77-83 -->

### Resolve the cross-desktop window-probe endpoints from the...

Resolve the cross-desktop window-probe endpoints from the SSOT
    (vendor /usr/share + /etc/mios + ~/.config). Returns a list of
    {"label","url"} dicts -- the local-host executor (when set) plus every
    [os_control.nodes.<name>].endpoint declared with a non-empty URL.
    Cached once per process; the lazy-load means a build without ANY
    overlay incurs zero work (returns []).

<!-- mios-src:167eb97bc5ed from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:131-136 -->

### Snapshot all open top-level windows. Calls the WSL-side...

Snapshot all open top-level windows. Calls the WSL-side list_windows verb
    AND every configured cross-desktop executor in parallel ([os_control].
    executor_endpoint + every [os_control.nodes.*].endpoint), merging the
    results. Without remote endpoints this collapses to the original WSL-only
    behavior (vendor empty = no overhead). Returns {"ok", "count", "windows":[...]}
    with each window carrying a `_source` tag so the diff can attribute opens to
    a specific desktop. Never raises.

<!-- mios-src:559eb6deb1db from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:205-211 -->

### RECORD + INDEX the before/after window snapshots + delta so...

RECORD + INDEX the before/after window snapshots + delta so FUTURE
    queries recall them (RAG: embedded knowledge row via _store_knowledge) and
    same-conversation agents see them (scratchpad). Fire-and-forget; the
 "check before, diff after" grounding the operator asked for.

<!-- mios-src:3c984772596b from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:305-308 -->

### Center the given window(s) on their desktop (operator...

Center the given window(s) on their desktop (operator binding
    'launches are ALWAYS centered -- that should be the default MiOS AI opening
    pattern'). WSLg / flatpak windows IGNORE Win32 launch-time placement, so we
    center AFTER the window maps. Picks the LARGEST window per owning executor
    (the MAIN app window -- a launch also spawns ~11 tiny PopupHost/tooltip
    windows) and POSTs /window/center to the Windows-native executor that owns
    it (only executor-sourced windows have movable Win32 hwnds; the WSL
    list_windows hwnds are a different namespace). The executor's center is a
    non-blocking async SetWindowPos, so this never stalls the turn. Best-effort;
    returns the list of centered window titles. Never raises.

<!-- mios-src:f1621ac9483a from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:344-353 -->

### Process-name patterns to pgrep for to confirm a launch...

Process-name patterns to pgrep for to confirm a launch ACTUALLY started
 ('should JUST search for PIDs globally for
    verifications'). The robust signal is the PROCESS existing -- WSLg windows
    carry content titles + proc=msrdc, never the app name, so title/count are
    unreliable. The launcher echoes the resolved ref ('launching <id>' /
    'fired <id>' / 'run <id>'); take both the reverse-DNS id AND its lowercased
    leaf (the bwrap binary, e.g. org.gnome.Epiphany -> 'epiphany'), plus the
    bare target name as a last-resort weak pattern.

<!-- mios-src:f2f48c60b206 from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:391-398 -->

### True if ANY pattern matches a running process command line...

True if ANY pattern matches a running process command line (global
    `pgrep -if` or Windows host `tasklist.exe`). /proc is world-readable, so the
    agent uid sees EVERY user's process cmdlines -- including the operator's flatpak
    GUIs running under bwrap. On WSL2, also queries tasklist.exe for host processes.

<!-- mios-src:289a93dc2018 from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:418-421 -->

### OS-control action fast-path. A single concrete...

OS-control action fast-path. A single concrete
    app/window/URL action is a DETERMINISTIC one-verb action: fire that ONE
    verb through the broker, report the REAL verdict, and STOP. NO council
    fan-out, NO web_search, NO synthesis of fabricated detail -- the failure
    mode that ran a 4-agent web-search swarm for "Launch Forza" (inventing
    window coordinates, never stopping after the launch had already
    succeeded) and narrated a fake tool call for "Close Forza".

    The polish prompt forbids claiming a success the verb's own output does
    not show (anti-fabrication; mirrors the launch_verified / verify_launch
    'presented, not merely process-alive' Definition-of-Done rule in SOUL).

<!-- mios-src:1753313590fd from usr/lib/mios/agent-pipe/mios_pipe/routing/oscontrol.py:513-523 -->
