<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### Web portal helpers + PWA asset builders + the swarm-roster...

Web portal helpers + PWA asset builders + the swarm-roster probe (refactor R10).

Extracted VERBATIM from ``server.py`` -- the portal config/auth SSOT, the Quadlet
service auto-discovery + host/container telemetry, the dashboard/login/PWA asset
strings, and the per-agent reachability probe. Every name is moved byte-identically
and re-imported by ``server.py``; the @app portal routes stay there as thin
wrappers, so the module's public + HTTP surface is unchanged.

``loads_lenient`` is imported directly; the two server helpers the swarm probe
calls (``_probe_auth_headers``, ``_agent_lane``) are injected via :func:`configure`
(one-way boundary -- this module never imports ``server``).

<!-- mios-src:6d49b54bdcf1 from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:3-14 -->

### Inject server.py's runtime deps under their original...

Inject server.py's runtime deps under their original module-level names.
    _probe_auth_headers + _agent_lane back the swarm probe; _AGENT_REGISTRY backs
    the swarm-roster route (injected by reference -> server must re-configure on a
    membership reload); _sanitize_tool_text scrubs the service-detail logs; the
    ``websockets`` client module backs the terminal WS bridge. A None arg is
    skipped so server may call with a partial set (e.g. only the registry on a
    reload).

<!-- mios-src:e509cff5fb0b from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:52-58 -->

### True when login is disabled or the request carries a valid...

True when login is disabled or the request carries a valid session --
    either the browser's httponly cookie, OR an 'Authorization: Bearer
    <token>' header. Same signed token either way (_portal_token_ok); the
    header form exists for NATIVE (non-browser) local clients -- e.g. the
    Quickshell PortalData.qml widget (design spec: mios-app-browser-portal-
    dashboard-design-*.md, native-unification roadmap addendum) --
    that call portal_login_logic once and reuse a Bearer token instead of
    implementing cookie-jar + redirect handling for a login flow that was
    designed for browsers.

<!-- mios-src:9b9da7620fc4 from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:141-149 -->

### True if a Quadlet's generated unit is MASKED or was skipped...

True if a Quadlet's generated unit is MASKED or was skipped by a FAILED
    start condition (ConditionResult=no) -- i.e. retired (a legacy lane -> mios-llm-light)
    or gated OFF (vllm/guacamole: model not provisioned / wrong virtualization).
    Such a unit can only ever show as a phantom 'down' in the portal, so drop it.
    A unit that is MEANT to run but crashed keeps ConditionResult=yes and stays
    visible -> genuine outages are still surfaced. The unit's own systemd state
 is the SSOT -- no service-name list. Fail-OPEN: any
    query error returns False (visible), so a probe glitch never hides a real
    service.

<!-- mios-src:372d409b7c57 from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:161-169 -->

### Best-effort host-port -> {container,state,image} map from...

Best-effort host-port -> {container,state,image} map from podman.
    Returns {} on any failure (podman absent / no perms) so the portal
    degrades to health-only without erroring.

    PREFERS the root-written snapshot at MIOS_PODMAN_PS_SNAPSHOT: this service
    runs hardened + non-root and CANNOT reach the rootful /run/podman socket
    (/run/podman is 0700 root:root), so a direct `podman ps` here sees an empty
 rootless context -> "podman present but no containers".
    mios-podman-ps.timer refreshes the snapshot every ~15s. Falls back to a
    direct `podman ps` for unrestricted/rootless-visible deployments.

<!-- mios-src:7f309ad4c2f5 from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:284-293 -->

### Build a :root override from mios.toml [colors] (SSOT) so...

Build a :root override from mios.toml [colors] (SSOT) so the portal
    tracks the operator's palette. Maps the MiOS color ROLES to the portal's
    CSS vars; derived surfaces (--card/--line) recompute via color-mix in the
    page CSS. Returns '' on any failure -> the static MiOS-default :root
    stands. Per the no-hardcode rule: the toml is the source, the static
    block is just the documented fallback.

<!-- mios-src:9968379ebdfc from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:906-911 -->

### Same-origin WebSocket bridge to a loopback ttyd. The...

Same-origin WebSocket bridge to a loopback ttyd. The operator's device
    reaches the portal but NOT ttyd's 127.0.0.1:<port> directly (loopback-only,
    not tailscale-served), so the native xterm embed connects here and we proxy
    to ttyd inside the VM -- works from any device with no per-port serve.

<!-- mios-src:4317314e084c from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:1228-1231 -->

### Serve the MiOS Configurator as a unified portal sub-page...

Serve the MiOS Configurator as a unified portal sub-page (auth-gated).
    Reads mios.html from disk at request time so live edits are reflected
    immediately without a process restart. Injects the SSOT palette so the
    configurator tracks the operator's theme just like the dashboard does.

<!-- mios-src:0699d7f0e816 from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:1339-1342 -->

### Run ``mios-theme-render check`` and report the projection...

Run ``mios-theme-render check`` and report the projection state WITHOUT
    ever writing. Returns {state, exit, summary}: state is 'PASS' (exit 0),
    'FAIL' (non-zero exit), or 'unknown' (the check could not be run at all --
    degrade-open, never raises). summary is the first PASS/FAIL line emitted.

<!-- mios-src:e69a61268947 from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:1591-1594 -->

### READ-ONLY summary for the dashboard's System Config card...

READ-ONLY summary for the dashboard's System Config card: the resolved
    identity user + deploy version, the top-level section count, whether a
    user-layer override is present, and the theme-projection state. Reuses the
    Portal's layered tomllib load (the mios_toml vendor<host<user overlay,
    falling back to the single-file read) -- no new deps, NO writes anywhere.
    Degrade-open throughout: any probe failure yields a safe placeholder.

<!-- mios-src:53a594cd7b7b from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:1612-1617 -->

### GET /portal/config/status -> small READ-ONLY JSON summary...

GET /portal/config/status -> small READ-ONLY JSON summary of live config
    health (resolved user/version, top-level section count, user-override
    presence, theme-projection PASS/FAIL) for the dashboard's System Config
    card. Auth-gated; NEVER writes; degrade-open (a probe failure yields a
    placeholder, not an error). The blocking reads + subprocess run off the
    event loop via asyncio.to_thread.

<!-- mios-src:d645e54114f6 from usr/lib/mios/agent-pipe/mios_pipe/routing/portal.py:1648-1653 -->
