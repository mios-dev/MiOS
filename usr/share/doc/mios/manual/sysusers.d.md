<!-- AI-hint: Manual pages distilled from the source comments of sysusers.d, sanitized, each passage anchored to the comment it came from. -->

# sysusers.d

### USER/SYSTEM/AI separation (operator directive 2026-05-18)...

USER/SYSTEM/AI separation (operator directive 2026-05-18): operator
joins BOTH bucket groups so `mios` can read AI shared state (skill
catalog, passport public keys, scratch, kanban shadow) AND infra
state (Guacamole config, Forgejo data, PXE configs) without sudo.
Writes still require the per-service uid or sudo. Groups are declared
in 50-mios-services.conf (`g mios-ai 850` / `g mios-sys 860`).

<!-- mios-src:1bc5b9b20d19 from usr/lib/sysusers.d/10-mios.conf:39-44 -->

### Upstream cockpit.service traditionally uses 'cockpit-ws' as...

Upstream cockpit.service traditionally uses 'cockpit-ws' as the main
socket user; some sub-units still reference that name even when our
drop-ins point cockpit.service itself at cockpit-systemd-service.
The 2026-05-10 journal showed cockpit-wsinstance-socket-user.service
failing with "Failed to determine credentials for user 'cockpit-ws'"
specifically, so the static name must exist regardless of which unit
is the immediate caller.

<!-- mios-src:b5539dcf2e12 from usr/lib/sysusers.d/50-mios-cockpit.conf:58-64 -->

### Group memberships -- cockpit's binaries are run by systemd...

Group memberships -- cockpit's binaries are run by systemd as
`cockpit-systemd-service` (set by cockpit.service's User=) and as
`cockpit-ws` (set by some helper units). Both need access to the
Unix sockets cockpit-ws creates at runtime under /run/cockpit/:

  /run/cockpit/session                            group cockpit-session-socket
  /run/cockpit/wsinstance/http.sock               group cockpit-wsinstance-socket
  /run/cockpit/wsinstance/https-factory.sock      group cockpit-wsinstance-socket

Without these supplementary group memberships, cockpit-tls fails with
  cockpit-tls: connect(...): Permission denied
the browser receives HTTP 401 "Authentication not available", and
the login form shows "Authentication failed" even when the operator
entered the correct credentials. Operator-flagged 2026-05-10.

<!-- mios-src:e6a8d9319d52 from usr/lib/sysusers.d/50-mios-cockpit.conf:68-81 -->

### cockpit-wsinstance-https.service spawns...

cockpit-wsinstance-https.service spawns /usr/libexec/cockpit-ws with
DynamicUser=yes + User=cockpit-wsinstance-https + Group=cockpit-session-socket.
When DynamicUser is in effect systemd uses the unit's Group= for the
transient primary GID; when our overlay drop-ins disable it, the static
user's own primary group sticks (cockpit-wsinstance-https=953) and the
cockpit-session.sock connect fails. Explicit membership keeps both
paths working. Same applies to the http instance.

<!-- mios-src:8a8bbac22260 from usr/lib/sysusers.d/50-mios-cockpit.conf:86-92 -->

### CORE AI-AGENT USER (operator 2026-05-23: "consolidate MiOS...

---- CORE AI-AGENT USER (operator 2026-05-23: "consolidate MiOS system users
to fewer combined/core users"). The agent/code PLANE now RUNS as this single
user instead of 4 (mios-hermes, mios-agent-pipe, root, mios): agent-pipe,
hermes-agent, delegation-prefilter, hermes-browser, mios-daemon, mios-mcp,
skills-miner. One owner for /var/lib/mios state -> no cross-user perms walls
(the class behind the container/snapshot visibility bugs). Per-container
DATA-plane users (llamacpp, open-webui, searxng, pgvector, forge, ...) stay
ISOLATED. uid 850 == the mios-ai bucket gid; HOME=/var/lib/mios/hermes keeps
opencode's ~/.local + $HERMES_HOME working. journal+adm groups give the
consolidated daemon RO log/journal access (it previously ran as root).
Legacy mios-hermes (820) + mios-agent-pipe (822) accounts are RETAINED inert
for `sudo -u`/chown reference-compat; nothing runs as them now.

<!-- mios-src:27259b586c6b from usr/lib/sysusers.d/50-mios-services.conf:40-51 -->

### Container-only service (Quadlet at /etc/containers/systemd/...

Container-only service (Quadlet at /etc/containers/systemd/
mios-forge.container). The sysuser exists for /var/lib/mios/forge
ownership stability across rebuilds; HOME=/var/empty is correct
because the container has its own internal HOME -- this UID/GID
is never logged into directly. Consolidation note 2026-05-15.

<!-- mios-src:495e4ffddb81 from usr/lib/sysusers.d/50-mios-services.conf:67-71 -->

### Home is /var/lib/mios/hermes -- the Hermes service unit's...

Home is /var/lib/mios/hermes -- the Hermes service unit's
$HERMES_HOME and the writable area sub-tools (opencode, the
self-improvement skill clones, browser profile, kanban.db, etc.)
need a real writable home for. Setting this in passwd lets
`sudo -u mios-hermes -H ...`, opencode's ~/.local/<name>
bootstrap, and any other "use $HOME" pattern Just Work.
Operator-confirmed regression 2026-05-15: opencode failed with
"EACCES: permission denied, mkdir '/var/empty/.local'" when
invoked as mios-hermes because the prior /var/empty home left
~/.local unwritable.

<!-- mios-src:95700909e9e0 from usr/lib/sysusers.d/50-mios-services.conf:79-88 -->

### Supplementary groups so the gateway can read journals +...

Supplementary groups so the gateway can read journals + system logs
without a sudo escalation: systemd-journal grants RO journal access;
adm grants RO /var/log/* access. Both are read-only -- the gateway
can SEE everything but only WRITES go through the existing capability
surface (Bash tool + sudo policy). Lets the log-watcher daemon's
state ALSO be visible to the agent's "what happened recently?" path
even if it ever moves off world-readable 0644 mode.

<!-- mios-src:b51935d3f2a4 from usr/lib/sysusers.d/50-mios-services.conf:90-96 -->

### 'MiOS' standalone Agent Pipe (router + refine + critic...

'MiOS' standalone Agent Pipe (router + refine + critic FastAPI;
fronts hermes-agent for every gateway: OWUI, Discord, future
Slack/Telegram/MCP). Operator directive 2026-05-18: centralize the
pipe so all gateways get the same tool surface + critic + agent-DB
state writes. HOME=/var/lib/mios/agent-pipe is the data + state dir
(chown via /usr/lib/tmpfiles.d/mios-agent-pipe.conf at boot).

<!-- mios-src:5afdcc4027d9 from usr/lib/sysusers.d/50-mios-services.conf:100-105 -->

### 'MiOS' in-VM CPU light-lane (router/classifier + verb...

'MiOS' in-VM CPU light-lane (router/classifier + verb embeddings +
micro-LLMs) -- a retired sidecar UID from the 810-829 range, along
with its retired dGPU big-model sibling (uid 815). The AMD iGPU now
runs natively on the Windows host (mios-igpu-server.ps1, served to
the swarm as mios-reasoner-cpu).
'MiOS' crawl engine user (operator 2026-05-24: the unclecode/crawl4ai
CONTAINER was scrapped). Now owns the venv FastAPI service
(mios-crawl4ai.service): the venv at /usr/lib/mios/crawl4ai/.venv and the
cache at /var/cache/mios/crawl4ai (camoufox's patched Firefox + crawl4ai
cache), chowned via /usr/lib/tmpfiles.d/mios-crawl4ai.conf + the
mios-crawl4ai-setup script. HOME=/var/empty (the service points
XDG_CACHE_HOME at the cache dir). Next free UID after the retired CPU light-lane (823)
in the 810-829 sidecar range.

<!-- mios-src:dabb7198c478 from usr/lib/sysusers.d/50-mios-services.conf:108-120 -->

### Phase D.5

Phase D.5: agent-pipe forwards to Hermes-Agent and other sub-
agents. /etc/mios/hermes/api.env (0640 mios-hermes:mios-hermes)
carries the API_SERVER_KEY agent-pipe injects as Bearer when
the upstream caller didn't supply one (curl, MCP clients,
Discord). Adding agent-pipe to the hermes group is narrower
than world-readable + cleaner than copying the key.

<!-- mios-src:5642bd93c268 from usr/lib/sysusers.d/50-mios-services.conf:158-163 -->
