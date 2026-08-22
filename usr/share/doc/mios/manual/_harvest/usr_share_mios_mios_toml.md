<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: The primary configuration file defining the MiOS user profile, providing the base defaults for identity, system environment, and service configurations used by tools via the userenv.sh resolver.
AI-related: tools/lib/userenv.sh, userenv.sh, tools/generate-k3s-manifests.sh, automation/01-system-files-overlay.sh, /usr/share/mios/mios.toml, /etc/mios/mios.toml, /etc/mios/hermes/discord.env, /usr/share/mios/configurator/mios.html, /etc/mios/hermes/api.env., /usr/libexec/mios/mios-powershell
mios-bootstrap/mios.toml -- 'MiOS' User Profile (single source of user truth)

THIS IS THE ONE FILE YOU EDIT. Every script in 'mios.git' and
'mios-bootstrap.git' that needs to know your username, hostname,
base image, AI endpoint, flatpaks, profile features, free-form
environment variables, etc. resolves through this file via a
three-layer overlay:

    /usr/share/mios/mios.toml       (vendor defaults, baked into image; lowest)
    /etc/mios/mios.toml             (host-local overlay, written by bootstrap)
    ~/.config/mios/mios.toml        (per-user overlay; highest)

Higher layers shadow lower layers field-by-field. Bootstrap ships THIS
file at the repo root as the canonical user-edit copy and stages it
into /etc/mios/mios.toml at install time. The per-user copy is seeded
from /etc/skel/.config/mios/mios.toml at useradd -m time.

Resolver: tools/lib/userenv.sh (reads all three layers, exports MIOS_*
env vars, merges [env] table verbatim). Sourced by Justfile,
/etc/profile.d, and any tool that needs the resolved values.

Format: TOML 1.0 -- https://toml.io/en/v1.0.0.

Secrets policy. password_hash, luks_passphrase, and github_pat are
NEVER read from a checked-in copy of this file. The bootstrap
installer prompts interactively for them and writes them to
root-owned mode-0600 files outside this profile. Leave the fields
empty here.

<!-- mios-src:7a1be32630db from usr/share/mios/mios.toml:1-30 -->

### [units] -- Systemd unit definitions SSOT (WS-SYSTEMD...

----------------------------------------------------------------------------
[units] -- Systemd unit definitions SSOT (WS-SYSTEMD schema).
----------------------------------------------------------------------------

<!-- mios-src:b04c83d8bc60 from usr/share/mios/mios.toml:116-118 -->

### First retry shortly after boot, then every 10min while the...

First retry shortly after boot, then every 10min while the service sits\n# inactive and the sentinel is still absent. Persistent catches up a missed\n# window across a shutdown. The timer OWNS retry now (the .service no longer\n# carries Restart=on-failure / StartLimitBurst)."

<!-- mios-src:147de097bd67 from usr/share/mios/mios.toml:145-145 -->

### AI-hint

AI-hint: Systemd timer that triggers mios-dashboard-issue.service every 5 minutes to refresh the /etc/issue.d/ banner with real-time Quadlet status updates like service flapping and endpoint reachability.\n# AI-related: /usr/libexec/mios/mios-dashboard-render-issue.sh, mios-dashboard-issue, mios-dashboard-render-issue, mios-dashboard-issue.service, timers.target\n# /usr/lib/systemd/system/mios-dashboard-issue.timer\n# Refresh the /etc/issue.d/ dashboard snippet every 5 minutes so\n# Quadlet state changes (services flapping, endpoint reachability\n# coming and going) reach the pre-login banner without operator\n# intervention."

<!-- mios-src:8bbf62e16190 from usr/share/mios/mios.toml:167-167 -->

### AI-hint

AI-hint: Daily systemd timer that fires mios-pgvector-backup.service to snapshot the unified agent-plane Postgres+pgvector datastore, with Persistent=true so a missed run (machine off) executes at next boot.\n# AI-related: mios-pgvector-backup.service, timers.target\n# /usr/lib/systemd/system/mios-pgvector-backup.timer\n# WS-0 pgvector durability: schedules the daily logical backup of the unified\n# agent-plane datastore. The service itself is degrade-open + gated on\n# MIOS_PG_BACKUP_ENABLE, so the timer can stay enabled unconditionally."

<!-- mios-src:4bbfd680955f from usr/share/mios/mios.toml:195-195 -->

### AI-hint

AI-hint: Defines the systemd timer for the mios-skills-miner.service, controlling the periodic execution interval (default 60m) for background skill mining and pattern discovery.\n# AI-related: /usr/libexec/mios/mios-skills, mios-skills-miner, mios-skills, mios-skills-miner.service, timers.target\n# /usr/lib/systemd/system/mios-skills-miner.timer\n# Phase C.2 of the AgentOS roadmap: cadence for the background\n# skill miner. Interval lifted to mios.toml [skills].\n# mine_interval_minutes (default 60). Operator override:\n#   sudo systemctl edit mios-skills-miner.timer\n#   [Timer]\n#   OnUnitActiveSec=30min\n#\n# Disabled by default; operator opts in (or it inherits enablement\n# from the configurator HTML \"Skills mining\" toggle which maps to\n# [skills].enable). The .service ConditionPathExists guard means a\n# stripped-down deployment with the libexec script absent skips\n# silently."

<!-- mios-src:11e6c50c0ee7 from usr/share/mios/mios.toml:222-222 -->

### AI-hint

AI-hint: Ensures critical MiOS service ports (3000, 3030, 8080, 8642, 8888, 9090, 9119, 11434, 19090, 3053, 53) are opened in firewalld at boot to prevent connectivity loss for Open WebUI, Hermes, Cockpit, and SearXNG.\n# AI-related: mios-open-webui, mios-searxng, mios-crawl4ai, firewalld.service, hermes-agent.service, mios-open-webui.service, mios-searxng.service, mios-crawl4ai.service, network-online.target, multi-user.target\n# Ensure MiOS service ports are open in firewalld at every boot.\n#\n# Why this exists: automation/44-firewall-ports.sh writes the firewalld\n# zone XML at OCI build time via firewall-offline-cmd. On stale OCI\n# images (pre-2026-05) OR when the install-time script didn't run / the\n# XML didn't persist, firewalld comes up with no ports open and ALL\n# Windows->WSL bridging silently times out (operator-confirmed\n# regression 2026-05-15: Open WebUI/Hermes/Cockpit/SearXNG inaccessible\n# post-reinstall; firewall-cmd --list-ports returned empty; adding the\n# ports manually instantly restored all 4 services).\n#\n# This unit runs at every boot and is idempotent: --add-port on a port\n# that's already open is a no-op. No-ops cleanly when firewalld is\n# absent (ConditionPathExists) or inactive."

<!-- mios-src:6af713b7134d from usr/share/mios/mios.toml:389-389 -->

### Ports

Ports: 3000=Forge, 3030=OWUI, 8080=code-server, 8642=Hermes-Agent,\n#        8888=SearXNG, 9090=Cockpit, 9119=Hermes-Dashboard,\n#        11450=LLM-Light, 5432=pgvector, 19090=Cockpit-link, 3053=AdGuard UI, 53=AdGuard DNS.\n# (crawl4ai :11235 removed 2026-05-24: the crawl engine is now a LOOPBACK-only\n#  venv service -- mios-crawl4ai.service binds 127.0.0.1, never LAN-exposed.)\n# AdGuard DNS needs BOTH 53/tcp and 53/udp (UDP is the normal query path).\n# Hardening: only the firewall-cmd binary needs system privileges; lock\n# everything else down."

<!-- mios-src:0a6ce7c37774 from usr/share/mios/mios.toml:397-397 -->

### AI-hint

AI-hint: Path-watcher companion to mios-libexec-perms.service -- re-runs the go+rX chmod whenever /usr/libexec/mios changes (e.g. a git checkout of / restages the scripts without exec bits), so exec perms self-heal within seconds instead of leaving services crash-looping on 203/EXEC.\n# AI-related: mios-libexec-perms.service, mios-additionalimagestores-perms.path, multi-user.target\n# Path-watcher companion to mios-libexec-perms.service. Any way the exec bits\n# get reset on /usr/libexec/mios (most commonly a `git checkout` of the deployed\n# root /), this snaps them back to go+rX within seconds so no service is left\n# crash-looping on 203/\"Permission denied\"."

<!-- mios-src:723b683d0a6f from usr/share/mios/mios.toml:466-466 -->

### AI-hint

AI-hint: Systemd path unit (WS-A4 boot-ordering fix) that watches for the Hermes venv binary and (re)starts hermes-worker.service once it exists, so a worker that failed its ConditionPathExists at first boot (venv not yet built) comes up automatically when the venv lands -- instead of staying inactive until a manual restart.\n# AI-related: hermes-worker.service, hermes-worker-firstboot.service, /usr/lib/mios/agents/.venv/bin/hermes, multi-user.target, 90-mios.preset\n# /usr/lib/systemd/system/hermes-worker.path\n# WS-A4 (operator 2026-06-22): hermes-worker.service carries\n# ConditionPathExists=/usr/lib/mios/agents/.venv/bin/hermes. On a fresh boot the\n# venv is not built yet -> the Condition fails -> the worker is skipped, and once\n# the venv-build/firstboot finishes systemd never retries it (so :8643 stays\n# inactive forever and the orchestrator silently runs single-agent). This .path\n# closes that gap: PathExists is satisfied the moment the venv binary EXISTS\n# (on creation AND if already present at activation), starting the worker. The\n# worker's own Condition still guards against a half-built venv; start is idempotent."

<!-- mios-src:fd205bd91a7b from usr/share/mios/mios.toml:495-495 -->

### The script reads MIOS_LLAMACPP_BAKE_MODELS (the GGUF...

The script reads MIOS_LLAMACPP_BAKE_MODELS (the GGUF download spec) +\n# MIOS_AI_* from the env bridge. Without this, a fresh systemd boot has an\n# EMPTY environment -> bake_models reads empty -> \"GGUFs not baked\" -> the\n# llm-light lane stays inert forever. The leading '-' makes it optional so\n# the unit still starts (and retries) if the bridge isn't generated yet.\n# install-robustness 2026-06-21."

<!-- mios-src:8394b507e0bd from usr/share/mios/mios.toml:762-762 -->

### AI-hint

AI-hint: Initializes the Hermes gateway by generating the api.env file and ensuring the config.yaml matches the current schema, acting as a self-healing pre-boot step to provide required credentials and configuration for hermes-agent.service.\n# AI-related: /etc/mios/hermes/api.env., /usr/libexec/mios/mios-hermes-firstboot, hermes-agent.service, systemd-tmpfiles-setup.service\n# Runs before the DIRECT-install hermes-agent.service so the gateway\n# starts with a valid $HERMES_HOME/config.yaml + api.env already on\n# disk. The pre-2026-05-14 ordering targeted mios-hermes.service /\n# mios-hermes-workspace.service -- both deleted when the Hermes\n# container Quadlets were removed; hermes-agent.service is the runtime\n# now."

<!-- mios-src:c06861d1217a from usr/share/mios/mios.toml:771-771 -->

### NO ConditionPathExists=!/etc/mios/hermes/api.env. The old...

NO ConditionPathExists=!/etc/mios/hermes/api.env. The old gate made\n# this unit a true once-ever oneshot -- but the script does TWO jobs:\n# (1) mint api.env (genuinely once), and (2) seed/heal\n# /var/lib/mios/hermes/config.yaml (must re-run when the Hermes config\n# SCHEMA drifts across upgrades, or when the container->direct-install\n# migration left $HERMES_HOME orphan-owned). The script is fully\n# idempotent -- it skips keygen when API_SERVER_KEY exists and only\n# rewrites config.yaml on detected drift -- so letting it run every\n# boot is cheap and self-healing. Operator-confirmed 2026-05-14: the\n# gate left a stale pre-0.13 config.yaml in place that the firstboot\n# rewrite could never reach."

<!-- mios-src:9d3743c58fba from usr/share/mios/mios.toml:776-776 -->

### Read MIOS_AI_* + model-tier vars from the env bridge so a...

Read MIOS_AI_* + model-tier vars from the env bridge so a fresh systemd\n# boot has the resolved config (model pick, endpoints). Optional ('-') so\n# the unit still self-heals if the bridge isn't generated yet.\n# install-robustness 2026-06-21."

<!-- mios-src:06a733a38460 from usr/share/mios/mios.toml:781-781 -->

### Hardening

Hardening: this service writes to a small set of paths plus calls\n# 'podman exec' against the running mios-forge container. RestrictNamespaces\n# and RestrictAddressFamilies were tried but break Podman's CRIU/conmon\n# attach path on rootful container exec; we drop them and lean on the\n# read-write path scoping + ProtectHome instead, which is sufficient for\n# this script's actual surface area.\n#\n# /run is LOAD-BEARING and must be writable as a whole: rootful\n# `podman exec` -- even a plain exec, no container lifecycle -- grabs\n# coordination locks across multiple /run subtrees: /run/libpod/\n# alive.lck (runtime init lock), /run/lock/netavark.lock (network\n# coordination), /run/containers/ (storage runroot). Listing them\n# individually is whack-a-mole; each missing one surfaces only at\n# runtime as \"open <path>: read-only file system\" (exit 125). /run is\n# tmpfs runtime state, so granting it RW is low-risk and is exactly\n# podman's requirement. That exit-125 failure is silent-deadly here:\n# forge-firstboot.sh's `admin user create` idempotency guard mis-reads\n# 125 as \"user already exists\", so the admin is never created, the\n# repo-create 401s, the runner-token mint fails, and the entire\n# self-replication CI chain (runner-firstboot -> .runner ->\n# mios-forgejo-runner.service) stays dead behind unmet\n# ConditionPathExists guards. Operator-confirmed regression 2026-05-14."

<!-- mios-src:0b31940c3c73 from usr/share/mios/mios.toml:809-809 -->

### AI-hint

AI-hint: FBM first-boot large-model provisioner unit (oneshot, sentinel-guarded, degrade-open).\n# Runs mios-models-firstboot once at first boot to fetch [ai].firstboot_models GGUFs; enabled via 90-mios.preset.\n# AI-related: /usr/libexec/mios/mios-models-firstboot, /usr/share/mios/mios.toml"

<!-- mios-src:a951c63d36ed from usr/share/mios/mios.toml:840-840 -->

### AI-hint

AI-hint: FBM first-boot bound-image provisioner unit (oneshot, sentinel-guarded, degrade-open).\n# Runs mios-bound-images-firstboot once at first boot to pull [ai].firstboot_bound_images; enabled via 90-mios.preset.\n# AI-related: /usr/libexec/mios/mios-bound-images-firstboot, /usr/share/mios/mios.toml"

<!-- mios-src:31f827fa96fe from usr/share/mios/mios.toml:887-887 -->

### AI-hint

AI-hint: Systemd unit that executes mios-swarm-pack-firstboot to arm concurrent small-model worker units if gpu_profile is \"swarm\", enforcing VRAM budgets and provisioning GGUFs during the first boot sequence.\n# AI-related: /usr/libexec/mios/mios-swarm-pack-firstboot, mios-cdi-detect.service, mios-ai-firstboot.service, network-online.target\n# SWARM Phase-2 (operator 2026-06-12): arm the concurrent small-model server pack\n# at boot IF [dispatch].gpu_profile == \"swarm\" (else the script is a no-op). The\n# script self-gates + enforces the VRAM budget, so this unit is safe to enable\n# unconditionally; it only ever starts mios-llm-worker@<name> units when the\n# operator has flipped the profile + provisioned GGUFs."

<!-- mios-src:23e6d8bf056c from usr/share/mios/mios.toml:966-966 -->

### AI-hint

AI-hint: Systemd unit for the SECOND (non-thin) Hermes WORKER gateway on :8643 -- a real agent that runs its OWN native browser/CDP/terminal/skills tool loop with its OWN inference on the heavy lane (:11441 mios-heavy). Coexists with the thin :8642 Discord gateway (hermes-agent.service) via a SEPARATE HERMES_HOME and no Discord token.\n# AI-related: /usr/lib/mios/agents/.venv/bin/hermes, /var/lib/mios/hermes-worker, /var/lib/mios/hermes-worker/config.yaml, /etc/mios/hermes/api.env, hermes-agent.service, mios-hermes-browser-worker.service, mios-llm-heavy.service, mios-llm-light.service\n# /usr/lib/systemd/system/hermes-worker.service\n#\n# The MiOS Hermes WORKER (P1, operator 2026-06-19). A SECOND `hermes gateway\n# run` instance, fully ISOLATED from the live :8642 Discord gateway:\n#   * SEPARATE HERMES_HOME=/var/lib/mios/hermes-worker => its own gateway.pid /\n#     gateway.lock / gateway_state.json / state.db / kanban.db / config.yaml.\n#     No shared-DB WAL contention with the :8642 instance.\n#   * API_SERVER_PORT=8643 (the LOAD-BEARING bind var -- `PORT` is inert; Hermes\n#     reads API_SERVER_PORT and otherwise binds DEFAULT_PORT=8642).\n#   * NO discord.env / NO DISCORD_BOT_TOKEN => the Discord adapter never calls\n#     _acquire_platform_lock('discord-bot-token', ...), so the host-global\n#     gateway-locks/discord-bot-token-*.lock held by the :8642 gateway is never\n#     contended (no SIGTERM flap). Discord stays the EXCLUSIVE job of :8642.\n#   * NO --replace: the worker's HERMES_HOME-scoped pidfile is its own; the\n#     :8642 gateway's eviction scan is profile/HERMES_HOME-scoped (only --all\n#     crosses profiles, which is not used) so neither instance touches the other.\n#\n# This worker is the WORKER-DISPATCH target of [agents.hermes].endpoint in\n# mios.toml (repointed :11441 -> :8643 in P1). It does its OWN heavy-lane\n# inference (:11441 mios-heavy) so it never relays to :8640 -- no recursion."

<!-- mios-src:9b03ffa0f6a3 from usr/share/mios/mios.toml:1003-1003 -->

### AI-hint

AI-hint: Systemd unit file defining the core MiOS daemon; it consolidates log watching, cron gating, and agent nudging into a single process using a local qwen3 model to update the state.json file used by the OWUI sidecar.\n# AI-related: /usr/libexec/mios/mios-daemon, /etc/mios/secrets.env, /etc/mios/daemon/cron.toml, mios-ai, mios-open-webui\n# /usr/lib/systemd/system/mios-daemon.service\n#\n# MiOS consolidated micro-LLM daemon. Replaces three predecessors\n# (mios-log-watcher + mios-cron-director + mios-agent-nudger) with\n# ONE process that subscribes to journald once, holds a single\n# qwen3:0.6b-cpu client (keep_alive=-1 forever, num_gpu=0 CPU-only\n# per Law 7 OFFLINE-FIRST + \"always-on agentic OS\"), and dispatches\n# the three handlers off a single event stream. Writes a unified\n# /var/lib/mios/daemon/state.json the OWUI mios_sidecar Filter polls.\n#\n# Operator directive 2026-05-17: \"ALL to be consolidated to one\n# mios daemon/agent\" + \"keep_alive should be TRUE for a TRULY\n# Agentic OS--MiOS!\""

<!-- mios-src:15a99d3e222d from usr/share/mios/mios.toml:1147-1147 -->

### Operator-tunable knobs (override via drop-in or...

Operator-tunable knobs (override via drop-in or /etc/mios/secrets.env):\n#   Environment=MIOS_DAEMON_MODEL=qwen3:1.7b\n#   Environment=MIOS_DAEMON_ENDPOINT=http://127.0.0.1:11434\n#   Environment=MIOS_DAEMON_STATE_DIR=/var/lib/mios/daemon\n#   Environment=MIOS_DAEMON_CRON_TOML=/etc/mios/daemon/cron.toml\n#   Environment=MIOS_DAEMON_CLASSIFY_S=30\n#   Environment=MIOS_DAEMON_CRON_TICK_S=60\n#   Environment=MIOS_DAEMON_WATCH_UNITS=mios-agent-pipe.service,mios-open-webui.service"

<!-- mios-src:c2c23e30ca21 from usr/share/mios/mios.toml:1162-1162 -->

### var/lib/mios/daemon = the daemon's own state (state.json...

/var/lib/mios/daemon = the daemon's own state (state.json, launch_failures).\n# /var/lib/mios/scratch = the SHARED cross-agent blackboard the task_collector\n# drops agent-nudges into for other agents to read (operator 2026-05-24: under\n# ProtectSystem=strict it was read-only, so task_collector EROFS-failed writing\n# agent-nudges.md -- the nudge feature was silently dead)."

<!-- mios-src:4d36d868f0d3 from usr/share/mios/mios.toml:1166-1166 -->

### AI-hint

AI-hint: Systemd unit to manage the local ChromeDev flatpak instance providing a Chrome DevTools Protocol (CDP) endpoint at 127.0.0.1:9222 for the Hermes-Agent's browser_tool.py to perform navigation and interaction.\n# AI-related: /usr/libexec/mios/mios-hermes-browser, mios-ai, hermes-agent.service\n# /usr/lib/systemd/system/mios-hermes-browser.service\n#\n# Headless ChromeDev (com.google.ChromeDev flatpak) with Chrome\n# DevTools Protocol on 127.0.0.1:9222 -- the CDP endpoint that\n# Hermes-Agent's browser tool attaches to (see browser.cdp_url in\n# /var/lib/mios/hermes/config.yaml). Operator directive 2026-05-15:\n# \"Hermes-Browser isn't enabled!! Should be using the locally\n# installed ChromeDev flatpak install\"."

<!-- mios-src:4859a24cb9f7 from usr/share/mios/mios.toml:1254-1254 -->

### AI-hint

AI-hint: Systemd unit for the WS-9 out-of-process HITL policy arbiter -- runs /usr/libexec/mios/mios-policy-arbiter (a stdlib loopback HTTP service) as the mios-ai user, answering the agent-pipe's HITL arbiter client with allow/deny verdicts decided by mios_arbiter over the operator policy. Idle/no-op until [ai].hitl_arbiter_url points at it; default policy is allow-all so enabling it changes nothing until a deny-list/block-tier is set.\n# AI-related: /usr/libexec/mios/mios-policy-arbiter, /usr/lib/mios/agent-pipe/mios_arbiter.py, mios-agent-pipe.service\n# /usr/lib/systemd/system/mios-policy-arbiter.service\n# 'MiOS' out-of-process HITL policy arbiter (WS-9). A second, operator-ownable\n# opinion ON TOP of the in-process #62 HITL gate + WS-A9 PDP: the agent-pipe POSTs\n# each high-risk (tier >= [ai].hitl_threshold) action here for an allow/deny\n# verdict. Runs as mios-ai (least privilege); binds 127.0.0.1 only."

<!-- mios-src:32481aee40be from usr/share/mios/mios.toml:1325-1325 -->

### AI-hint

AI-hint: Unprivileged daily oneshot that pg_dumps the unified agent-plane Postgres+pgvector database to /var/lib/mios/backups over loopback-trust and prunes to the newest MIOS_PG_BACKUP_KEEP snapshots; degrade-open so a backup failure never blocks the DB.\n# AI-related: mios-pgvector-backup.timer, mios-pgvector.service, /usr/lib/tmpfiles.d/mios-backups.conf, mios-pg-query\n# /usr/lib/systemd/system/mios-pgvector-backup.service\n# WS-0 pgvector durability: periodic logical backup of the unified agent-plane\n# datastore (tiered memory / knowledge / skills / sessions / scratch / sys_env /\n# kanban / ...). Losing pgvector is expensive, so this snapshots it daily.\n#\n# UNPRIVILEGED (Architectural Law 6 spirit): runs as the pgvector sysuser\n# (mios-pgvector, uid 826) -- it owns /var/lib/mios/backups (tmpfiles) and\n# reaches Postgres over the pg_hba loopback-trust line.\n#\n# DEGRADE-OPEN: every failure path (gate off, no pg_dump client, dump error)\n# logs and exits 0. A backup miss must NEVER fault the boot/timer or affect the\n# live DB. backup_enable ships TRUE; flip MIOS_PG_BACKUP_ENABLE=false to disable."

<!-- mios-src:697885bb7559 from usr/share/mios/mios.toml:1372-1372 -->

### Logical dump over loopback-trust, gzip'd + timestamped...

Logical dump over loopback-trust, gzip'd + timestamped, then prune to the\n# newest N. Pure POSIX sh so it runs on the minimal base. Every branch exits 0\n# (degrade-open): gate-off, missing client, or a dump error logs and succeeds."

<!-- mios-src:74bbfd38c7b8 from usr/share/mios/mios.toml:1396-1396 -->

### Home location for "local" / "near me" / weather / news...

Home location for "local" / "near me" / weather / news asks. When the chat
surface forwards no geo (e.g. OWUI on a phone with location-sharing off), the
agent resolves place-dependent queries against THIS instead of the host
timezone's coarse region. Free-form: a city, "City, ST",
or "lat,long". Empty -> fall back to the host system timezone region, then to
an honest "couldn't determine your location" punt (never fabricated cities).

<!-- mios-src:0ba67d1d1e24 from usr/share/mios/mios.toml:1545-1550 -->

### Global MiOS default password. Every service (Hermes...

Global MiOS default password. Every service (Hermes Workspace, Forge
admin, Cockpit, Ceph dashboard, etc.) defaults to this credential
unless the operator overrides per-service. Vendor default is "mios".
Operators rotate by editing /etc/mios/mios.toml or
~/.config/mios/mios.toml [identity].default_password.

<!-- mios-src:2b4f7ce7e23b from usr/share/mios/mios.toml:1553-1557 -->

### [user] -- Human Operator Profile. Injected natively into...

----------------------------------------------------------------------------
[user] -- Human Operator Profile. Injected natively into the AI context so
the agent knows the user's name, pronouns, and bio. Layered from ~/.config/mios.
----------------------------------------------------------------------------

<!-- mios-src:d6ec3d1533b2 from usr/share/mios/mios.toml:1560-1563 -->

### Vendor default is EMPTY -> the operator's display name...

Vendor default is EMPTY -> the operator's display name inherits the SSOT
[identity].username until personalized (via ~/.config/mios or the MiOS App).
Never ship a personal name here: this is the display label, and it must never
be resolved into a login/credential slot (that reads the DB account SSOT).

<!-- mios-src:b80c487f9d2e from usr/share/mios/mios.toml:1565-1568 -->

### [accounts] -- Multi-tenant account / owner model...

----------------------------------------------------------------------------
[accounts] -- Multi-tenant account / owner model (FOUNDATION). MiOS is moving
multi-tenant: a blade is a machine, a node is a compute unit, and every request
is owned by an ACCOUNT (a human user, or a system/service tenant). The agent
datastore backs this with the `account` table (postgres/schema-init.sql); the
owner-scoped tables (knowledge / agent_memory / scratch) carry `owner_user`.

LINKAGE CONVENTION: owner_user == account.name (a soft natural key today). A hard
foreign-key rewrite across the owner-scoped tables is a deliberate follow-up -- the
table + the convention are established first so nothing existing is rewritten.

There is intentionally NO vendor `default_account` key: the account rows are seeded
by postgres/schema-init.sql FROM the identities the DB already holds -- the operator
singleton (`person`, populated from the host [identity]) plus every distinct
owner_user already on an owned row -- so the owner of legacy/unowned (NULL owner_user)
rows is the operator [identity] WITHOUT restating it here (NO-HARDCODE). The
per-request owner is the principal the surface forwards (reconciled against the
token-bound account under [security].principal_bind_mode=enforce). This [accounts]
table is the home for FUTURE account-model knobs; it declares none today.
----------------------------------------------------------------------------

<!-- mios-src:84ae69eeb55c from usr/share/mios/mios.toml:1573-1592 -->

### [agent_passport] -- Open Agent Passport (v0.1.0; the 2026...

----------------------------------------------------------------------------
[agent_passport] -- Open Agent Passport (v0.1.0; the 2026 native standard for
verifiable, issuer-signed AI-agent identity + authority). agent-pipe serves the
signed JSON at GET /.well-known/agent-passport.json from these values, beside
the A2A AgentCard (/.well-known/agent-card.json). EVERY field is optional -- the
builder fills MiOS defaults (issuer from [identity], agent = the "MiOS AI" served
model). To make the passport VERIFIABLE: set signing_key_path to an Ed25519
private key and publish a DNS TXT at signing_key_dns:
    v=ap1; kid=<key_id>; alg=ed25519; pk=<base64url-public-key>
Until then the doc is schema-valid but served UNSIGNED (flagged x-mios-unsigned).
----------------------------------------------------------------------------

<!-- mios-src:3eab27b5c4fb from usr/share/mios/mios.toml:1605-1615 -->

### The keys below were ORPHANED under...

The keys below were ORPHANED under [security.nohc_allowlist]: that header
opened and never closed, so every consumer reading [security].<key> took its
compiled default instead. Gate: check_ssot_consumer_keys. See TASKS.md T-325.
F2 / T-033 -- the CaMeL-class "Rule of Two" architectural prompt-injection defense
(Meta, "Agents Rule of Two"), applied as a DETERMINISTIC (not probabilistic) gate at
the single dispatch chokepoint. A verb dispatch may hold AT MOST TWO of three
dangerous properties without human review:
  A  untrusted-input  -- the session ingested attacker-controllable content (the
                         existing provenance-taint chain above);
  B  sensitive-access -- the verb READS sensitive/private/cross-tenant data (the
                         per-verb `sensitive = true` flag below);
  C  state-change     -- the verb mutates state / has side-effects (the verb's
                         `permission` tier: write/interactive, derived via the same
                         tier->confinement policy the sandbox uses).
When ALL THREE hold, the chain is the classic prompt-injection kill-chain (untrusted
text -> reads secrets -> exfiltrates/acts) and is gated. Composes the EXISTING taint
+ permission signals -- no new keyword classifier. Modes:
  off     (default) -- the gate is NOT consulted (byte-identical behaviour).
  audit             -- on all-three, LOG a structured audit event + proceed
                       (observe before you enforce; non-blocking).
  enforce           -- on all-three, route to HITL review / BLOCK (fail-safe: a
                       3-property chain requires a human; an out-of-band approval
                       lets the exact action through). Composes with the firewall +
                       HITL gates -- the STRICTER outcome wins.
DEFAULT off because a 3-property block reduces autonomous function -- opt in, then
validate the `sensitive = true` classification for the deployment. Env override:
MIOS_SECURITY_RULE_OF_TWO_MODE.

<!-- mios-src:4f24d56b6131 from usr/share/mios/mios.toml:1641-1667 -->

### F2 -- the CaMeL DUAL-CONTEXT QUARANTINE gate (Debenedetti...

F2 -- the CaMeL DUAL-CONTEXT QUARANTINE gate (Debenedetti et al., "Defeating Prompt
Injections by Design"), the deeper half of the prompt-injection defense and a STRICTER
superset of rule_of_two_mode above. The CaMeL principle: untrusted/attacker-
controllable content (web/file/tool output that TAINTS the session, axis A above) must
not be able to make the privileged action-planner take a PRIVILEGED action it would not
otherwise -- where "privileged" means the verb either READS sensitive data (axis B,
`sensitive = true`) OR mutates state / has side-effects (axis C, the write/interactive
permission tier). The boundary BITES when the session is TAINTED *and* the verb is
privileged (B OR C). Where rule_of_two_mode gates only the all-three chain (A AND B AND
C), quarantine-enforce ADDITIONALLY gates the tainted + (B OR C) case -- the posture for
full CaMeL isolation: untrusted-content-derived privileged actions cannot fire
autonomously; a human (or a non-tainted plan) must authorize them. Composes the SAME
EXISTING taint + permission + sensitive signals -- no new keyword classifier. Modes:
  off     (default) -- the gate is NOT consulted (byte-identical behaviour).
  audit             -- on a bite (tainted + privileged), LOG a structured audit event +
                       proceed (observe before you enforce; non-blocking). Use this to
                       measure how often untrusted content drives privileged actions.
  enforce           -- on a bite, route through mios_hitl.decide to HITL review / BLOCK
                       (fail-safe; an out-of-band or same-turn approval lets the exact
                       action through). Sits at the SAME single dispatch chokepoint as
                       the firewall + HITL + Rule-of-Two gates -- the STRICTER outcome
                       wins, so there is no second action path that bypasses it.
DEGRADE-OPEN (not-crash) but FAIL-SAFE (security): an error computing the boundary falls
back to the existing firewall/HITL/Rule-of-Two behaviour (never crash, never newly-open);
a confirmed tainted+privileged under enforce gates (fail toward safety). DEFAULT off
because the stricter block reduces autonomous function -- opt in for full CaMeL
isolation. Env override: MIOS_SECURITY_QUARANTINE_MODE.

<!-- mios-src:d47a202696c7 from usr/share/mios/mios.toml:1670-1696 -->

### FED-G1 INBOUND AUTH GATE. The agent-pipe front door (:8700...

FED-G1 INBOUND AUTH GATE. The agent-pipe front door
(:8700 /v1/* + /a2a) accepts requests with NO credential today. When ON, an ASGI
middleware gates those paths: a request must present the canonical shared key
(API_SERVER_KEY -- what OWUI + the `mios`/`@` CLI already send), the ingress key,
OR a per-caller key from `api_caller_keys_path` -> a scoped principal stashed for
RBAC. Discovery/health (`/v1/models`, agent-card, passport, `/health`,
`/v1/cluster/health`) stay OPEN so an unauth'd peer can still learn how to auth.
DEFAULT FALSE -> the middleware is a pass-through (byte-identical behaviour). Turn
ON only with a loopback or firewall-scoped (172.16/12) bind -- it changes the
front-door auth posture (operator-greenlight). The federation JOIN contract
(FED-G6/G8) enforces per-peer scope once peers are keyed.

<!-- mios-src:044630ac8cbd from usr/share/mios/mios.toml:1699-1709 -->

### VERIFIED PRINCIPAL BINDING (multi-tenant security...

VERIFIED PRINCIPAL BINDING (multi-tenant security FOUNDATION). The owner used for
per-owner memory row-scoping (`owner_user`) is derived in _client_env from the
request-body `user` field + the forwarded x-openwebui-user-* HEADERS -- both
spoofable by a direct :8700 caller (set "user":"victim"). This setting binds that
owner to the AUTHENTICATED caller-key instead. Each entry in `api_caller_keys_path`
MAY carry an `account` field (alias `owner`) naming the account that key speaks for
(an `account` row in postgres/schema-init.sql). The canonical shared / ingress key
has NO bound account (it is the full-trust gateway credential) -> the forwarded
user is used as-is; that is how the OWUI gateway keeps per-user identity (OWUI
authenticates each user and forwards it, so the gateway is trusted to speak for
whichever user it forwards).
  off     (default) -- NO binding: trust the body/header user exactly as today
                       (BYTE-IDENTICAL behaviour). Single-user / trusted callers.
  verify            -- observe mode: resolve the caller-key's bound account; if it
                       MISMATCHES the body/header user, audit-log it (structured,
                       non-blocking) but STILL use the forwarded value (no behaviour
                       change -- visibility before enforcement).
  enforce           -- the token-bound account IS the owner: a spoofable body/header
                       user is overridden by the verified identity for row-scoping.
DEGRADE-OPEN everywhere: no token / an unbound key / a missing mapping / any error
-> off behaviour, so a turn is never broken and OWUI is never locked out. Pair with
api_require_auth = true (which actually REQUIRES a credential) for full multi-tenant
isolation -- binding alone identifies the owner; the gate decides who may connect.
Env override: MIOS_PRINCIPAL_BIND_MODE.

<!-- mios-src:d1484c4a4d08 from usr/share/mios/mios.toml:1713-1736 -->

### Verbs whose dispatch is REFUSED when the session is tainted...

Verbs whose dispatch is REFUSED when the session is tainted
(Phase A.3 / B.3 Semantic Firewall). These cause visible system
effects -- restarting services, injecting input into Win32 GUI
windows, restarting containers -- so the firewall blocks them
when an upstream tool_call in the same session was tainted.
Operator can add custom verbs to this list (e.g. when shipping
a new privileged shim) without touching agent-pipe code.

<!-- mios-src:a8b3ac69d02c from usr/share/mios/mios.toml:1739-1745 -->

### Window-state verbs (D.3 PC-control template) -- tainted...

Window-state verbs (D.3 PC-control template) -- tainted
sessions moving / hiding operator windows is the kind of
thing the firewall should refuse pre-clear.

<!-- mios-src:f30da52a50de from usr/share/mios/mios.toml:1760-1762 -->

### Package management WRITE verbs (D.4). Either platform's...

Package management WRITE verbs (D.4). Either platform's
install path can land arbitrary code on the operator's
machine -- tainted sessions are refused.

<!-- mios-src:093f6e2e3d44 from usr/share/mios/mios.toml:1768-1770 -->

### Path prefixes whose text_view READ taints the session (the...

Path prefixes whose text_view READ taints the session (the agent is reading
content it did not author, so downstream high-privilege verbs in the same
session get firewall-gated). This is the SAME write-protected prefix set the
native text editor refuses writes to, so a tainting read and a denied write
stay in lock-step -- keep it aligned with the editor's denied-write prefixes.

<!-- mios-src:4ebe4f858bab from usr/share/mios/mios.toml:1783-1787 -->

### Host suffixes treated as the operator's OWN (internal)...

Host suffixes treated as the operator's OWN (internal) infrastructure: a URL
whose host ends with one of these is NOT a taint source (the *.local / *.lan
split-horizon + explicit internal zone). Single-label bare hostnames (no dot)
are also treated as internal by the classifier.

<!-- mios-src:b28b659cf762 from usr/share/mios/mios.toml:1799-1802 -->

### WS-9 out-of-process policy arbiter...

WS-9 out-of-process policy arbiter (mios-policy-arbiter.service) policy. The
arbiter is a SECOND opinion the agent-pipe consults for high-risk verbs when
[ai].hitl_arbiter_url points at it. Default policy is allow-all (empty) -> the
arbiter permits everything until the operator sets a deny-list / block-tier.
Bridged to the service as MIOS_ARBITER_DENY / _ALLOW / _BLOCK_TIER.

<!-- mios-src:eb889269f2db from usr/share/mios/mios.toml:1804-1808 -->

### WS-A10 verified-caller principal (edge identity) --...

WS-A10 verified-caller principal (edge identity) -- RESERVED / aspirational.
This scoped-token gate ("verify" = require a valid scoped token, "enforce" =
verify + 401) was never wired into the inbound path; its token mint/verify core
was removed as dead. The IMPLEMENTED inbound-principal handling lives elsewhere:
[security].api_require_auth (bearer gate), [security].principal_bind_mode (owner
binding -> RLS, in mios_grounding), and [agent_passport].principal_mode (A2A
federation, in mios_a2a). Leave "off" unless/until the scoped-token path is
built. token_ttl_s = intended scoped-token lifetime. Env: MIOS_PRINCIPAL_MODE /
MIOS_TOKEN_TTL_S. Revocation: mios_crl (live, used by mios_a2a key-revoke).

<!-- mios-src:41c53cbbc941 from usr/share/mios/mios.toml:1813-1821 -->

### Phase B.3 of the AgentOS roadmap

----------------------------------------------------------------------------
Phase B.3 of the AgentOS roadmap: TOML-driven Semantic Firewall
allowlist. Hosts in this list are TRUSTED -- open_url to one of
these does NOT taint the session. Anything outside this list +
the compiled-in *.local / *.lan / single-label heuristic is
treated as external and contributes session taint, which gates
subsequent high-privilege verbs (in `firewall_high_privilege_verbs`
below). Operator can extend per deployment (LAN hosts, internal
SaaS, etc.) without touching code. CSV-form in the env (the
userenv.sh slot map flattens these lists).

<!-- mios-src:eef25b4aa9a3 from usr/share/mios/mios.toml:1824-1833 -->

### AIOS gap8

AIOS gap8: also taint EXTERNAL web fetches (web_search/web_extract/crawl/
web_scrape) so untrusted web content gates subsequent high-privilege verbs
(research-then-act) via the firewall below. DEFAULT FALSE -- gating reduces
autonomous function, so the operator opts in. LOCAL rag/recall are NOT tainted
(RAG runs every turn -> tainting it would block all OS-control).

<!-- mios-src:4b9b99634c4b from usr/share/mios/mios.toml:1849-1853 -->

### Tracked .exe files that have NO reproducible source in this...

Tracked .exe files that have NO reproducible source in this repo. ADR-0003
says a shipped binary must be buildable from committed source, so every entry
here is a real gap to CLOSE, not a permanent allowance -- this list should
only shrink. MiOS-iGPU-Server.exe is tracked but
automation/build-windows-binaries.sh only defines a source for
MiosServiceTool.cs, so nothing in-repo can rebuild it.

<!-- mios-src:816b0ed36bbb from usr/share/mios/mios.toml:1930-1935 -->

### key_id = "mios-ap-1" signing_key_path =...

key_id          = "mios-ap-1"
signing_key_path = "/etc/mios/agent-passport/ed25519.key"   # PEM or 32-byte raw
signing_key_dns  = "_agent-passport.mios.example.ts.net"
revocation_list_url = "https://mios.example.ts.net/.well-known/revoked.json"
principal_mode (#60 WS-6): inbound A2A delegation signed-principal enforcement.
  off (default) -- attribution only: a delegation's signed principal is verified
                   and audit-logged, but absent/unsigned/forged ones still run
                   (matches today's open behaviour; single-node / trusted peers).
  require       -- reject any inbound delegation whose principal is absent or
                   fails verification (text-bound Ed25519). Turn on once peers
                   are provisioned with passport keys (zero-trust federation).
Env override: MIOS_A2A_PRINCIPAL_MODE. Outbound delegations are ALWAYS signed
when a passport key is present, regardless of this setting.
principal_mode  = "off"

<!-- mios-src:647ed1059306 from usr/share/mios/mios.toml:1982-1995 -->

### [ai_tag] -- AI-hint codebase-tagging COVERAGE gate. Read by...

----------------------------------------------------------------------------
[ai_tag] -- AI-hint codebase-tagging COVERAGE gate. Read by
mios-ai-hint-coverage, wired into automation/98-drift-checks.sh (check 5) so it
runs in build.sh, both CI workflows, and `just drift-gate`. Taggability itself
is defined by mios-ai-tag (the SSOT for WHICH files should carry a header);
this section only sets the pass/fail POLICY.
----------------------------------------------------------------------------

<!-- mios-src:f0b658acd3b3 from usr/share/mios/mios.toml:1997-2003 -->

### max_untagged

max_untagged: ceiling on how many taggable source files may LACK an `AI-hint:`
header before the drift gate fails. It is a RATCHET -- the build fails the
moment a NEW untagged taggable file lands. Drive it toward 0 by tagging real
code/config with `mios-ai-tag`. The non-zero floor exists only for the few
files that MUST stay header-free: agent SOUL/prompt markdown (a comment line
would leak into the model's prompt) and single-value data files (a comment
would corrupt the value). Env override: MIOS_AITAG_MAX_UNTAGGED; CLI:
--max-untagged. Current intentional remainder = soul prompts + data/plan docs.

<!-- mios-src:226c9cf33c8a from usr/share/mios/mios.toml:2005-2012 -->

### [selfimprove] -- #64 self-improvement ANALYSIS (the safe...

----------------------------------------------------------------------------
[selfimprove] -- #64 self-improvement ANALYSIS (the safe observe half). The
read-only GET /v1/self-improve/report surfaces what to improve from local
outcome data (failing/slow tools, unreliable peers) via mios_selfimprove. It
does NOT act -- closing the loop (auto-tuning) is a separate gated step (agent
self-modification needs guardrails). These are the analysis thresholds.
----------------------------------------------------------------------------

<!-- mios-src:0e7e8a654545 from usr/share/mios/mios.toml:2026-2032 -->

### ── ACT half (T-062) + proof-of-utility (T-064) -- the...

── ACT half (T-062) + proof-of-utility (T-064) -- the self-CURATION loop ──
When the loop runs (interval_min > 0) AND act_enabled is on, each pass turns the
OBSERVE findings into bounded change PROPOSALS, scores each against the current
baseline on a discriminative held-out eval, and QUEUES only a non-regressing
proposal for HUMAN approval (GET /v1/self-improve/proposals). It NEVER auto-applies
a self-modification -- a queued proposal is reviewed + approved out of band, then
applied by a separate path. DEFAULT-OFF: act_enabled=false => the loop is a pure
no-op (analyze still surfaces as before). Degrade-open: any loop error drops the
proposal and never affects live serving. The literals below are the documented
degrade-open fallbacks (the daemon reads these keys; missing keys degrade safe).

<!-- mios-src:302e3ee2a4a3 from usr/share/mios/mios.toml:2045-2054 -->

### Anti-reward-hacking isolation (Autodata's lesson: the...

Anti-reward-hacking isolation (Autodata's lesson: the self-rewriting agent edited
the weak solver's prompt to fake a result). A proposal may ONLY target a kind in
improvable_targets; the evaluator / eval-data / lane-config kinds in
protected_targets are STRUCTURALLY off-limits -- a proposal touching them is rejected
before it is ever scored, so the proposer can never edit the thing that judges it.

<!-- mios-src:b6d8ad4cd260 from usr/share/mios/mios.toml:2072-2076 -->

### [portal] -- MiOS Portal web app (served by mios-agent-pipe...

----------------------------------------------------------------------------
[portal] -- MiOS Portal web app (served by mios-agent-pipe at GET / on
MIOS_PORT_AGENT_PIPE). Login gates the portal UI + its /portal/* data
endpoints; the /v1 OpenAI API, /a2a and /health stay open programmatic
surfaces. Maps to MIOS_PORTAL_* (userenv.sh slot map); the portal also reads
these directly from mios.toml so they apply without a userenv re-render.
----------------------------------------------------------------------------

<!-- mios-src:06771605ebf7 from usr/share/mios/mios.toml:2081-2087 -->

### Discord integration -- the channel + guild MiOS-Agent posts...

Discord integration -- the channel + guild MiOS-Agent posts to when
the operator says "send to discord" / "post a status to discord" /
"let me know on discord" without naming a channel. EMPTY by default
in vendor; operator sets per-host in /etc/mios/mios.toml overlay
(or ~/.config/mios/mios.toml). Used in two places:
  1. mios-hermes-firstboot bakes the value into the seeded SOUL.md
     so the chat model has it as authoritative context when calling
     discord_send_message without an explicit channel_id.
  2. mios-hermes-firstboot writes MIOS_DISCORD_DEFAULT_CHANNEL into
     /etc/mios/hermes/discord.env so any future tool can read it
     from os.environ alongside DISCORD_BOT_TOKEN.

<!-- mios-src:b81ee13776e9 from usr/share/mios/mios.toml:2103-2113 -->

### [auth] -- credential and SSH key policy. ssh_key_action...

----------------------------------------------------------------------------
[auth] -- credential and SSH key policy.
  ssh_key_action: generate | existing | skip
  password_policy: interactive | hashed | plain | none
    - interactive : prompt at install (recommended for hardened deploys)
    - hashed      : use the literal hash in password_hash (openssl passwd -y)
    - plain       : use the literal string in password (chpasswd hashes it)
    - none        : no password set; useful for kiosk / CI builds

Dev VM default is "plain" with password="mios" so Cockpit web at
https://localhost:9090/ accepts the operator-typed `mios / mios`
the dashboard advertises. Operator-overridable via mios.html. The
build-mios.ps1 Invoke-MiosQuadletOverlay step reads this section
and runs `chpasswd` accordingly inside the dev VM.

Secret fields (password / password_hash / luks_passphrase / github_pat)
stay empty in any tracked copy of THIS file when password_policy is
'interactive' or 'hashed' (the installer prompts and writes them to
a mode-0600 file outside this profile). For the 'plain' / 'none'
vendor-default cases, leaving 'password' set here is intentional --
the dev VM is single-tenant on Windows and the trust boundary is
the host login, not the VM password.
----------------------------------------------------------------------------

<!-- mios-src:377a3f7a33dc from usr/share/mios/mios.toml:2126-2148 -->

### [ai] -- Local AI surface (Architectural Law 5...

----------------------------------------------------------------------------
[ai] -- Local AI surface (Architectural Law 5: UNIFIED-AI-REDIRECTS).
The VENDOR default stays local and never names a vendor cloud URL. An
operator OVERLAY may point endpoint anywhere -- that is how a seat offloads
(ADR-0016 D1), and local/localhost/remote are three values of one mechanism.
An off-box endpoint leaves the machine, so [security].api_require_auth is a
seat's precondition, not a preference (ADR-0016 D5). The old note here cited
"postcheck #12" as the enforcer; no such check has ever existed.
Maps to MIOS_AI_ENDPOINT, MIOS_AI_MODEL, MIOS_AI_EMBED_MODEL, MIOS_AI_KEY,
MIOS_SYSTEM_PROMPT_FILE, MIOS_MCP_REGISTRY.

Default model selection (researched for the 12 GB system-RAM baseline,
CPU-only inference, ~8 GB available to the model):

  model = "qwen2.5-coder:7b"
      - Best open-source code model in the 7B class as of 2026
        (HumanEval ~88%; multi-language including bash, PowerShell,
        Containerfiles, systemd units, TOML).
      - Q4_K_M quant: ~4.7 GB on disk, ~5-6 GB resident in CPU RAM.
      - 128K-token context window.
      - Strong at navigating Linux + Windows path semantics.
      - Apache 2.0 license.
      - https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct

  embed_model = "nomic-embed-text"
      - 768-dim sentence embeddings (v1.5).
      - 8192-token context (long enough for whole source files).
      - ~270 MB Q4 GGUF; negligible runtime RAM cost.
      - Apache 2.0; OpenAI /v1/embeddings-shaped via the mios-llm-light lane.
      - https://huggingface.co/nomic-ai/nomic-embed-text-v1.5

Build-baked: automation/73-model-prep.sh pulls the 'model' +
'embed_model' set into /usr/share/mios/llamacpp/models on the immutable
composefs surface during 'just build'. mios-llamacpp-firstboot.service
hardlink-copies that seed into /var/lib/mios/llamacpp/models on first deploy.
Operators can swap models post-deploy by editing this file
(/etc/mios/mios.toml or ~/.config/mios/mios.toml -- highest layer
wins) and running 'systemctl restart mios-llm-light'.

Larger / smaller alternates (NOT baked by default; operators opt in
via MIOS_LLAMACPP_BAKE_MODELS at build time, or pull post-deploy):
  "qwen2.5-coder:14b"    24+ GB RAM systems; better multi-step code
  "llama3.2:3b"          low-RAM (8 GB total) / fast-response profile
----------------------------------------------------------------------------

<!-- mios-src:8b49276143c7 from usr/share/mios/mios.toml:2193-2236 -->

### Global version tracking for the unified user-definitions...

Global version tracking for the unified user-definitions dotfile.
All MiOS scripts (build-mios.sh, build-mios.ps1, userenv.sh,
Resolve-MiosTomlAiDefaults) read this header to decide whether the
layered overlay format is one they understand. schema_version uses
semver: MAJOR bumps are breaking, MINOR add backward-compatible
fields, PATCH are doc-only or default-value adjustments.

<!-- mios-src:dbc8bd4eace2 from usr/share/mios/mios.toml:2238-2243 -->

### [verbs] -- canonical list of operator-facing `mios <verb>`...

----------------------------------------------------------------------------
[verbs] -- canonical list of operator-facing `mios <verb>` commands. The
Windows pwsh dispatcher (in M:\MiOS\powershell\profile.ps1), the post-
install hint banner, the Start Menu / Desktop per-verb shortcuts, and
the mios-help.ps1 listing all read from THIS table. Operators can
rename or reorder verbs via mios.html; the dispatcher + shortcuts
regenerate on the next install. Names must be lowercase ASCII a-z.
----------------------------------------------------------------------------

<!-- mios-src:fb0b116d0b5d from usr/share/mios/mios.toml:2254-2261 -->

### [install_phases.<mode>] -- ordered list of phase names...

----------------------------------------------------------------------------
[install_phases.<mode>] -- ordered list of phase names rendered by
build-mios.ps1's dashboard + log lines. Two modes:
  bootstrap -- the Windows-side "ack + dev VM + handoff" path (default).
  full      -- the legacy end-to-end path (deprecated; only kicks in
               when -FullBuild / -BuildOnly are passed, which the
               self-replication architecture forces to BootstrapOnly).
Operators rename phases via mios.html. The order here is structural
(each name is a step in the install state machine); reordering may
break callers that hardcode `Start-Phase 0`. Add/remove with care.
----------------------------------------------------------------------------

<!-- mios-src:6a01606abeaf from usr/share/mios/mios.toml:2292-2302 -->

### [messages.<context>] -- operator-facing prose strings...

----------------------------------------------------------------------------
[messages.<context>] -- operator-facing prose strings rendered by the
install pipeline. Lifted out of build-mios.ps1 so operators can rebrand
the bootstrap banners via mios.html without touching code. Bullets
support a {disk_gb} placeholder which build-mios.ps1 substitutes at
render time. NOTE: the canonical [messages.install_complete] table
lives below at line ~335 (richer schema with installed_lead /
next_steps / hub_hint). The earlier duplicate that previously sat
here was removed -- TOML's "table can't be redeclared" parse rule
was breaking userenv.sh + every other resolver.
----------------------------------------------------------------------------

<!-- mios-src:8922569851aa from usr/share/mios/mios.toml:2331-2341 -->

### Pre-dashboard EULA banner shown on every MiOS terminal open...

Pre-dashboard EULA banner shown on every MiOS terminal open BEFORE
the framed dashboard renders.  The lines scroll out of the visible
viewport when Clear-Host fires after `display_ms`, but stay
scroll-up-readable in the WT scrollback so the operator can review
at any time.  Operators opt out per-session via $env:MIOS_SKIP_EULA=1.
Edit via mios.html [messages.eula] -- changes flow on the next
`mios update` (re-runs Get-MiOS.ps1 which re-bakes the EULA into
M:\MiOS\powershell\profile.ps1).

<!-- mios-src:ecb39d4ab348 from usr/share/mios/mios.toml:2353-2360 -->

### [messages.build_pipeline] -- copy strings emitted by...

----------------------------------------------------------------------------
[messages.build_pipeline] -- copy strings emitted by build-mios.ps1
during the install pipeline.  Phase LABELS live in
[install_phases.bootstrap] / [install_phases.full] above (already
SSOT-driven via Start-Phase / End-Phase); this section captures the
remaining hardcoded prose.  Operators rebrand the installer face
via mios.html without touching any PowerShell.
----------------------------------------------------------------------------

<!-- mios-src:f83823e4bac7 from usr/share/mios/mios.toml:2378-2385 -->

### [messages.elevation] -- Pass-1 -> Pass-2 UAC handoff...

----------------------------------------------------------------------------
[messages.elevation] -- Pass-1 -> Pass-2 UAC handoff prompts.
The operator sees these immediately before the UAC dialog fires.
----------------------------------------------------------------------------

<!-- mios-src:5b72ff574f69 from usr/share/mios/mios.toml:2392-2395 -->

### [messages.pass2_exit] -- Pass-2 failure / completion /...

----------------------------------------------------------------------------
[messages.pass2_exit] -- Pass-2 failure / completion / close-prompt
strings shown in the elevated bootstrap window after the install
returns (success or failure).  Operators rebrand the post-flow
narrative via mios.html.
----------------------------------------------------------------------------

<!-- mios-src:27f346dd0a04 from usr/share/mios/mios.toml:2401-2406 -->

### In-line success transition ("spawn too many powershell...

In-line success transition ("spawn too many
powershell windows ... should be performed in-line in one
promoted Powershell window after bootstrap").  After install
completes, this conhost dot-sources the MiOS profile so the
operator stays in the same window and types `mios <verb>` here.

<!-- mios-src:7444c08045d9 from usr/share/mios/mios.toml:2413-2417 -->

### [messages.steps] -- Set-Step descriptions emitted during...

----------------------------------------------------------------------------
[messages.steps] -- Set-Step descriptions emitted during the install
pipeline.  These are the per-line yellow-bracket prefix strings the
operator sees during Phase 3 (data disk, mios.git overlay,
mios-bootstrap shadow, MiOS-DEV provisioning, etc.).  Operators
rebrand the install narrative via mios.html [messages.steps] without
touching any PowerShell.
----------------------------------------------------------------------------

<!-- mios-src:0ac86015e08e from usr/share/mios/mios.toml:2423-2430 -->

### Smoke-test labels (post-Phase-3 dev VM health check)....

Smoke-test labels (post-Phase-3 dev VM health check).  Operator
sees these whenever Test-MiosDevDistroHealthy runs.  All 4 are
templates with {name} = the resolved distro (podman-MiOS-DEV or
MiOS-DEV depending on whether Rename-PodmanDevDistro fired).

<!-- mios-src:0ee2e73d4594 from usr/share/mios/mios.toml:2442-2445 -->

### [messages.install_complete] -- end-of-bootstrap...

----------------------------------------------------------------------------
[messages.install_complete] -- end-of-bootstrap operator-facing
summary banner.  Title + bullets are operator-tunable; verb hints
render from [verbs] (already SSOT).  Operators rebrand via mios.html.
----------------------------------------------------------------------------

<!-- mios-src:5e2c11baae2f from usr/share/mios/mios.toml:2452-2456 -->

### Local privacy-respecting metasearch (SearXNG). Always-on...

Local privacy-respecting metasearch (SearXNG). Always-on Quadlet at
etc/containers/systemd/mios-searxng.container; the agent surface
(usr/share/mios/ai/v1/tools.json) can plug into this as a localhost
`web_search` tool target without breaking Architectural Law 5 -- a
search proxy is not a model, so no UNIFIED-AI-REDIRECTS exception
is required.

<!-- mios-src:181ce56356c6 from usr/share/mios/mios.toml:2474-2479 -->

### Topical-anchor stopwords for mios-web-search query...

Topical-anchor stopwords for mios-web-search query expansion (the structural
off-topic screen that requires an expanded sub-query to share >=1 CONTENT token
with the original). A classic function-word + generic-qualifier set -- NOT a
topic deny-list -- sourced here so the tokenizer carries NO baked word screen in
code. The matcher itself is unicode-aware (CJK/accented scripts tokenize, never
to zero); this list only removes the low-signal connective words. Extend per
locale. Flattened to MIOS_WEB_ANCHOR_STOPWORDS (CSV) by the userenv slot map.

<!-- mios-src:3551bb6cf1ef from usr/share/mios/mios.toml:2482-2488 -->

### Back-compat default only; the SSOT default is [ai].model....

Back-compat default only; the SSOT default is [ai].model. Repointed to the
4-model-set reasoning base (was granite4.1:3b, dropped from fleet).
realigned to the live [ai].model head (was "qwen3:1.7b", which was
retired from the fleet AND dropped from bake_models -- a stale ref that named an
un-served model). Mirrors [ai].model; vestigial back-compat key (no runtime
consumer reads it -- agents resolve MIOS_AI_MODEL), kept so older callers parse.

<!-- mios-src:e31218f0a35e from usr/share/mios/mios.toml:2507-2512 -->

### [hermes_workspace] -- REMOVED. The hermes-agent's own...

[hermes_workspace] -- REMOVED. The hermes-agent's own
dashboard at port 9119 is the canonical web UI (Sessions, Skills,
MCP, Plugins, Kanban -- the kanban API is /api/plugins/kanban/* on
port 9119 backed by /var/lib/mios/hermes/kanban.db). The separate
outsourc-e/hermes-workspace project at port 3033 was a redundant
chat front-end whose Tasks/Kanban panels haven't completed the
upstream migration to the agent's kanban API (Issue #311). Use
http://localhost:9119/ -- the agent dashboard auto-injects its
session token into its own HTML, so /api/plugins/kanban/* calls
authenticate from the in-page JS without external token wiring.

<!-- mios-src:6af392dde3fc from usr/share/mios/mios.toml:2516-2525 -->

### WS-0B/WS-A3 de-rot

----------------------------------------------------------------------------
WS-0B/WS-A3 de-rot: the legacy DB is RETIRED. Shared cross-cutting agent state
(agent, session, tool_call, event, kanban, scratch, knowledge, agent_memory,
directory_entry, skill, log_digest, peer_reputation, ...) now lives in
Postgres+pgvector -- see the [pgvector] section + usr/share/mios/postgres/
schema-init.sql, accessed via mios-pg-query / mios-db --pg(-json) / the
agent-pipe mios_pg client. OWUI's webui.db remains SOT for OWUI-native
memory/knowledge/files/tools/functions/models. (The former legacy DB config
block + its :8000 service were removed in the WS-A3 cutover; this note is left
as a signpost.)
----------------------------------------------------------------------------
WS-7: GPU device passthrough -- ONE owned key for the CDI device the GPU
Quadlets (mios-llm-light/heavy/heavy-alt/worker@) attach via AddDevice. Was
duplicated as a bare "nvidia.com/gpu=all" literal in all four; now rendered
from here (15-render-quadlets -> ${MIOS_GPU_DEVICE}) so the passthrough target
is tunable in one place (e.g. a specific GPU id on a multi-GPU host). The
Quadlets keep ":-nvidia.com/gpu=all" inline defaults -> byte-identical if unset.

<!-- mios-src:bfc543f1ffdf from usr/share/mios/mios.toml:2527-2543 -->

### WS-A13 risk-tier dispatch sandbox. enable=false ships the...

WS-A13 risk-tier dispatch sandbox. enable=false ships the policy resolver
(mios_sandbox) + the per-dispatch workspace (/var/lib/mios/ai/dispatch) INERT:
the confinement PROFILE is resolved + observable, but the server.py engine-side
confinement (bwrap/seccomp/podman) is not yet applied. The resolver is
FAIL-CLOSED (an unknown tier -> the strictest profile, never 'none'). Flip on
once the confinement executor lands + is VM-verified. Env: MIOS_SANDBOX_ENABLE.

<!-- mios-src:5b0650008826 from usr/share/mios/mios.toml:2547-2552 -->

### Law 14 -- TARGET-LANGUAGES

Law 14 -- TARGET-LANGUAGES: ALL new applicable code, on EVERY platform (bootc, WSL, Windows),
MUST use the roadmap's language-per-domain targets (ADR-0011 §2 / WS-LANG): Rust for native
tooling/orchestration/services/validation; Python for the AI plane; Bun/TS for the web Portal;
bash is thin GLUE ONLY. No NEW C#, Batch, PowerShell-as-program, or Go native code -- those are
grandfathered-for-port, not a licence for more. Minimise languages; convert shell -> machine code.

<!-- mios-src:351a693602eb from usr/share/mios/mios.toml:2584-2588 -->

### Law 15 -- DOUBLE-REPO-TRIPLE-CHECK

Law 15 -- DOUBLE-REPO-TRIPLE-CHECK: before ANY change, (1) DOUBLE-CHECK BOTH repos -- mios.git (the
system/OCI image source; .git IS /) AND mios-bootstrap.git (the installer + user-overlay) -- for
current state, the SHARED cross-repo SSOT (mios.toml, the userenv twins, [ports]/[colors]), any
duplication, and the OTHER agent's in-flight work; and (2) TRIPLE-CHECK everything -- re-read the
target, re-verify the assumption, and render/parse/test the result -- BEFORE acting. Measure thrice,
cut once; THEN code. A surface mirrored across both repos MUST be updated in both (or the divergence
explicitly justified). Discipline law: enforced by the agent contract (CLAUDE.md/AGENTS.md in BOTH
repos); the "both repos agree" half is mechanically gated by cross-repo parity checks 22 + 27.

<!-- mios-src:70179601fd9d from usr/share/mios/mios.toml:2590-2597 -->

### Law 14 (TARGET-LANGUAGES) enforcement data -- the...

Law 14 (TARGET-LANGUAGES) enforcement data -- the non-target-language sources GRANDFATHERED for
port to Rust (ADR-0011 §2 / WS-LANG). check_target_languages fails on any NEW .cs (outside this
list) or ANY .bat / .cmd / .go. This list may only SHRINK as ports land -- it must never grow.

<!-- mios-src:a217a46c1668 from usr/share/mios/mios.toml:2603-2605 -->

### Law 8 (SSOT-PROJECTION) enforcement data -- lists the known...

Law 8 (SSOT-PROJECTION) enforcement data -- lists the known projection surfaces
and their generators, so that check_projection_registry can verify they are backed
by drift checks (e.g. check_dotfiles_projection).

<!-- mios-src:d4342175e052 from usr/share/mios/mios.toml:2612-2614 -->

### Law 6 (UNPRIVILEGED-QUADLETS) documented root exceptions --...

Law 6 (UNPRIVILEGED-QUADLETS) documented root exceptions -- the ONLY place root
is granted. A Quadlet with User=root/User=0 that is NOT listed here fails
check_quadlet_privilege (98-drift-checks.sh) / postcheck item 13. Keep this in
sync with the tree: `grep -rlE '^User=(root|0)$' usr/share/containers/systemd/`.

<!-- mios-src:6bc511062323 from usr/share/mios/mios.toml:2632-2635 -->

### WS-7 (AIOS immutable-host hardening): fapolicyd...

WS-7 (AIOS immutable-host hardening): fapolicyd PERMISSIVE/observe rollout.
DEFAULT-OFF. When true, the gated build step (automation/lib/
ws7-uki-fapolicyd-build.sh) installs the permissive (observe-only) fapolicyd
config + the sandboxed-codegen exec carve-out over the live /etc copy.
fapolicyd then LOGS would-be denials and BLOCKS NOTHING. Enforce-mode is a
separate, documented, rollback-tested operator step (enforce on an
incomplete whitelist BRICKS BOOT) -- see concepts/ws7-uki-fapolicyd.md.

<!-- mios-src:8dfe815191c6 from usr/share/mios/mios.toml:2709-2715 -->

### [security.mcp_sandbox] -- T-032 hermetic MCP sandboxing for...

----------------------------------------------------------------------------
[security.mcp_sandbox] -- T-032 hermetic MCP sandboxing for tool execution.
DEFAULT-OFF. When true, every MCP stdio server spawn is routed through
/usr/libexec/mios/mcp-server-runner which acts as a gatekeeper: it validates
all tool-call arguments (blocking directory traversal, path escape), enforces
MIOS_WRITE_ALLOWED_PATHS for write operations, and runs the actual MCP server
process inside a rootless podman sandbox (--network=none, read-only root,
dropped caps). When false (default), MCP servers execute directly on the host
as today (degrade-open).
----------------------------------------------------------------------------

<!-- mios-src:c4276e63ab97 from usr/share/mios/mios.toml:2721-2730 -->

### [security.egress] -- #54 zero-trust OUTBOUND firewall for...

----------------------------------------------------------------------------
[security.egress] -- #54 zero-trust OUTBOUND firewall for the AGENT process.
Constrains the agent-pipe user's external egress at the OS layer (nftables) so a
compromised/misled agent cannot exfiltrate to arbitrary internet hosts. It is
UID-scoped, so it does NOT touch other users: web_search still works (the agent
reaches searxng over loopback, and searxng -- a different uid -- reaches the
internet). Generated to usr/share/mios/security/egress.nft by
tools/generate-egress-firewall.sh; the OPERATOR applies it (`nft -f ...`), like
the k3s manifests -- nothing here is auto-applied.
  mode: off (default) -- generator emits an informational, NO-OP ruleset.
        audit         -- LOG would-be-blocked agent egress; block nothing.
        enforce       -- LOG + DROP the agent's non-allowed external egress.
allow: extra destination CIDRs/IPs the agent may reach, BEYOND the always-
allowed loopback, tailnet (100.64.0.0/10) and local WSL gateway (172.16.0.0/12).
----------------------------------------------------------------------------

<!-- mios-src:13deda4489f3 from usr/share/mios/mios.toml:2735-2749 -->

### [security.disk_encryption] -- TPM2-backed LUKS disk...

----------------------------------------------------------------------------
[security.disk_encryption] -- TPM2-backed LUKS disk encryption (WS-VECTOR V1 / T-246).
----------------------------------------------------------------------------

<!-- mios-src:607924991759 from usr/share/mios/mios.toml:2754-2756 -->

### [security.mtls] -- #54 zero-trust TRANSPORT (mutual TLS)...

----------------------------------------------------------------------------
[security.mtls] -- #54 zero-trust TRANSPORT (mutual TLS) PKI. Provision with
tools/provision-agent-mtls.py -> a self-signed local CA + an agent cert/key
(clientAuth + serverAuth) so A2A peers can mutually authenticate. The actual
mTLS is terminated at the reverse proxy that fronts the A2A endpoint (MiOS's
TLS-at-the-proxy pattern); `enable` is advisory for that deployment. Override
the *_file paths to use an existing org CA instead of the self-signed default.
Certs are SECRETS (per-host, time-stamped) -> written under `dir`, NOT committed.
----------------------------------------------------------------------------

<!-- mios-src:f26d6d2aa8e3 from usr/share/mios/mios.toml:2763-2771 -->

### [uki] -- WS-7 verity-rooted Unified Kernel Image build...

----------------------------------------------------------------------------
[uki] -- WS-7 verity-rooted Unified Kernel Image build (DEFAULT-OFF).
When verity_uki_build = true the gated build step runs `ukify build`
measuring the composefs fs-verity digest into a UKI ARTIFACT at
/usr/lib/modules/<kver>/mios-verity.efi. The artifact is NOT signed, NOT
installed, and NOT the active boot entry -- signing (enrolled MOK) + install
+ rollback-tested boot are operator promotion steps. A mis-signed/required
UKI BRICKS BOOT; see concepts/ws7-uki-fapolicyd.md. [packages.uki] already
provides systemd-ukify.
----------------------------------------------------------------------------

<!-- mios-src:8dbebeb837f8 from usr/share/mios/mios.toml:2781-2790 -->

### Phase A.2 of the AgentOS roadmap

Phase A.2 of the AgentOS roadmap: directories the mios-daemon
fs-watcher thread tails via inotify, emitting pgvector event
rows (source=fs-watcher, kind=fs_change) on every mutation.
Other agents subscribe via SQL instead of polling these dirs
individually. Operator can add per-deployment watch points
(e.g. /var/lib/mios/<custom-agent>/) without code edits.

<!-- mios-src:fffe883eb32c from usr/share/mios/mios.toml:2795-2800 -->

### Phase C.1 of the AgentOS roadmap

Phase C.1 of the AgentOS roadmap: Personal Knowledge Graph
tunables. `bootstrap_per_source_cap` caps app_install rows per
inventory source so a pathological catalog can't flood the
graph. `lookup_max_alias_results` caps the alias fuzzy-match
step in kg_lookup. Operator can raise both per-deployment.

<!-- mios-src:69e1ea72683a from usr/share/mios/mios.toml:2813-2817 -->

### Phase D.2 of the AgentOS roadmap

Phase D.2 of the AgentOS roadmap: browser-accessible terminals.
ttyd is a C/libuv pty-over-WebSocket bridge -- the operator's
research note flagged it as the lightest option for
accessing local shells from a browser. MiOS ships TWO instances:

  mios-ttyd-bash       :7681  -> ttyd bash       (Linux side)
  mios-ttyd-powershell :7682  -> ttyd <pwsh.exe> (Windows side)

Both bind 127.0.0.1 by default; the operator hits them from a
local browser at http://localhost:7681 / :7682. For LAN access,
flip `bind` to "0.0.0.0" AND set `auth_user`/`auth_pass` (ttyd
refuses to start exposed without auth credentials if `require_auth`
is true). SSL cert + key paths optional for HTTPS termination.

<!-- mios-src:3d9f9829496d from usr/share/mios/mios.toml:2822-2834 -->

### Optional TLS termination -- when both paths exist, ttyd...

Optional TLS termination -- when both paths exist, ttyd serves
https + wss instead of http + ws. /etc/ssl/mios/ is the canonical
MiOS cert dir; operator drops a wildcard cert there or generates
a self-signed pair via mios-doctor.

<!-- mios-src:942105a8111a from usr/share/mios/mios.toml:2852-2855 -->

### Read-write terminal (operator can type). Set to false for a...

Read-write terminal (operator can type). Set to false for a
view-only session shared with a collaborator -- handy for paired
debugging without granting input.

<!-- mios-src:356036f0fcd6 from usr/share/mios/mios.toml:2863-2865 -->

### Phase D.5 of the AgentOS roadmap

Phase D.5 of the AgentOS roadmap: sub-agent registry. Operator
directive "Hermes isn't the only sub-agent on the
system" -- agent-pipe is the always-first orchestrator;
Hermes, OpenCode, future MCP clients are sub-agents it
delegates to based on the refined intent.

Every entry under [agents.<name>] is an addressable sub-agent.
`endpoint` is the OpenAI-compat /v1 URL; `role` informs the
refine pass which one to pick; `model` is the canonical model
id to advertise upstream; `default` (boolean) flags the
fallback when refine can't match a role.

Refine pass picks by role-match first, then default=true,
then the first registered agent.

<!-- mios-src:95856e783ea0 from usr/share/mios/mios.toml:2876-2889 -->

### ── UNIFIED AGENT TEMPLATE / SSOT (roadmap WS-A1)...

── UNIFIED AGENT TEMPLATE / SSOT (roadmap WS-A1) ─────────────────────────────
Every [agents.<name>] inherits these defaults, then overrides ONLY what differs.
The agent-pipe loader (_load_agent_registry) pops this table, merges
{**_defaults, **agent} per agent (agent keys win), and skips any _-prefixed name
as a non-agent. There is exactly ONE merge path, shared with the node loader, so
an agent can never silently miss a safety field. The loader UPGRADES health_gate
to true for any local-but-OPTIONAL endpoint (enabled=false) or kind in
cli/remote/edge/node/a2a -- the root-cause guard for the "dead local endpoint
treated as live -> merged_chars=0" multi-agent failure. An /etc or ~/.config
overlay can override these host-wide. (Absent => byte-identical legacy behaviour.)

<!-- mios-src:390e3657dbb3 from usr/share/mios/mios.toml:2891-2900 -->

### Per-agent CREDENTIAL + zero-trust posture (open-federation...

Per-agent CREDENTIAL + zero-trust posture (open-federation keystone, roadmap
WS-FED / gap G2): an agent presents its OWN credential, so ANY reachable
OpenAI /v1 endpoint -- a remote box, a second MiOS node, a Claude/Gemini proxy,
opencode -- joins the council by network + credential, never bespoke per-agent
code. header_template is env-resolved at load (same render as MCP headers).
A LOCAL endpoint (in _AUTH_HOSTPORTS) keeps using the shared backend key; a
non-local endpoint with no header_template simply gets no header (degrade-open).

<!-- mios-src:26502b1cc881 from usr/share/mios/mios.toml:2922-2928 -->

### WS-10b

WS-10b: the Hermes SERVICE now runs ON llama.cpp (its
config repointed :11434->:11450, model granite4.1:3b aliased to gemma4). Route
BACK to the real Hermes service (:8720) so it keeps its native browser_*/CDP +
terminal + tool loop -- bare gemma4@:11450 had no browser tools, so CDP browse
(operator's "cdp web browse in hermes") needs the real Hermes. Verified: Hermes
answers on the dGPU at 100% util (prompt ~25k tokens -> gemma4 ctx bumped to 32k).
WORKER-DISPATCH endpoint (RUNAWAY FIX): the :8720 gateway is
a THIN :8700 client now (see the unify note below), so dispatching a swarm/DAG/
reroute WORKER facet to :8720 made it RELAY BACK to :8700 -> swarm -> :8720 -> ...
UNBOUNDED RECURSION (the outage-reroute bypassed fanout=false; hermes spawned 30+
conversation loops pegging the dGPU). A worker MUST hit a REAL model lane, never a
thin gateway that loops to the orchestrator. The :11441-bare stopgap fixed the loop
but LOST hermes's native tools (bare model = no browser_*/CDP/terminal/skills loop).
P1 restores hermes as a REAL WORKER: a SECOND non-thin Hermes
gateway on :8730 (hermes-worker.service, HERMES_HOME=/var/lib/mios/hermes-worker)
that runs its OWN native browser/CDP/terminal/skills tool loop AND does its OWN
inference on the SAME heavy lane (:11441 mios-heavy) -- so worker dispatch now hits
:8730 (real tools) instead of :11441 (bare model). LOOP-SAFE: the worker does its
OWN :11441 inference and has the MCP relay (MIOS_AGENT_PIPE_URL=:8700) DISABLED, so
it never relays back to :8700; the P0 hop-budget/Via guard (_HOP_HEADER/_VIA_HEADER)
is the backstop. The :8720 gateway service stays thin for INCOMING Discord/CLI ->
:8700 (unification preserved; :8730 worker is a distinct instance, Discord OFF).
hermes stays a first-class dispatched agent (job/strengths surface via the pipe loop).

<!-- mios-src:ee5b2179ddc6 from usr/share/mios/mios.toml:2941-2963 -->

### health_gate

health_gate: the :8730 hermes-worker is a SEPARATE service bound to the heavy
GPU lane (mios-heavy), which is gated OFF by default (VRAM / operator opt-in).
Marking it health-gated makes the orchestrator liveness-probe it and DROP it
when unreachable (degrade-open) instead of dispatching the FINAL answer to a
dead endpoint -> "All connection attempts failed" / 502. It auto-rejoins once
the operator enables the heavy lane and the worker comes up. Without this the
:8700 front door 502'd on every turn on any host where the worker is down
(e.g. a fresh dev VM with the heavy lane gated). install-robustness.

<!-- mios-src:9908a3bee64a from usr/share/mios/mios.toml:2967-2974 -->

### WS-2 per-agent RBAC (optional; default = NO restriction =...

WS-2 per-agent RBAC (optional; default = NO restriction = unchanged behaviour):
cap THIS agent's tool surface to what its role should touch, enforced by
_agent_rbac_filter at dispatch. denied_verbs drops the named verbs; allowed_verbs
(when set) keeps ONLY those verbs (non-verb tools/recipes/skills always pass).
Examples (left unset for the general orchestrator, which needs the full surface):
  denied_verbs  = ["pkg", "shutdown", "reboot"]
  allowed_verbs = ["web_search", "fetch_url_markdown", "recall", "summarize"]
#55 per-tool capability/risk gate: max_permission caps the RISK TIER this agent
may call, using the same permission vocabulary verbs declare (read < write <
interactive; lattice tunable via [ai].permission_tiers). Verbs whose tier
outranks the ceiling drop from the surface. Unset = no ceiling. A coarse,
one-key complement to allow/deny lists -- e.g. a read-only research worker:
  max_permission = "read"     # only read-tier verbs (web/search/inspect); no writes
  max_permission = "write"    # read + write verbs; blocks interactive-tier
#60 WS-6 per-USER authz (the per-USER axis, complementing the per-AGENT keys
above): a top-level [users.<name>] table caps the tool surface by WHO is asking,
matched to the principal the chat surface forwards (user_name / email). Same
denied_verbs / allowed_verbs / max_permission semantics + risk lattice. Unset /
no matching [users.*] entry => NO restriction (single-user MiOS unaffected).
NOTE: keys on the surface-CLAIMED identity; cryptographic signed-principal
verification is the remaining half of #60. Example:
  [users.guest]
  max_permission = "read"           # a guest principal: read-only surface
  denied_verbs   = ["pkg", "shutdown", "reboot"]
  # email = "guest@example.com"     # optional: also match by forwarded email
  # WS-6 per-user quota / rate-limit (enforced at the dispatch chokepoint via
  # mios_quota; INERT until set -- both default 0 = unlimited, single-user
  # MiOS unaffected). rpm_limit = max verb dispatches per 60s; daily_budget =
  # max cost units per 24h (for paid remote lanes). Over -> exit 429 quota_block.
  # rpm_limit    = 60                # e.g. cap a guest to 60 tool calls/min
  # daily_budget = 5.0               # e.g. cap a guest's remote-lane spend/day
job ("no fixed roles -- MiOS-Agents are modelfiles for
jobs and tools/skills/recipes"): the one-line CAPABILITY the swarm planner
routes a sub-task by. Tools/recipes/skills are GLOBAL to every agent, so this
describes what the agent is BEST at -- not what it can access.

<!-- mios-src:5cd52e32fa59 from usr/share/mios/mios.toml:2976-3010 -->

### (operator "UNIFY THE WHOLE MIOS AI"): the Hermes gateway...

(operator "UNIFY THE WHOLE MIOS AI"): the Hermes gateway (8720) is now
a THIN :8700 client (its model -> MiOS-Agent on the orchestrator) so Discord + every
gateway platform get the orchestrator's polished/grounded output. That makes :8720
point BACK at :8700, so the orchestrator must NOT call :8720 as a council peer or it
recurses (Discord->:8720->:8700->council->:8720->...; the W0-T3 recursion bound is
process-local and does NOT cross the HTTP hop). fanout=false opts it out of the
council/swarm (_opted_out, server.py:3565) and default=false drops it as the refine
fallback pick -- the orchestrator's own primary is :11450 (MIOS_AGENT_PIPE_BACKEND),
so nothing else needs :8720. Block kept for role-matched-only routing + as docs.

<!-- mios-src:7c431f44a758 from usr/share/mios/mios.toml:3012-3020 -->

### CPU-compute twin ("all MiOS AI Agents/Sub-Agents have a...

CPU-compute twin ("all MiOS AI Agents/Sub-Agents
have a relevant MiOS Modelfile(s) for both CPU and GPU compute"). When
Hermes is dispatched as a concurrent fan-out SECONDARY, agent-pipe runs
this twin on the light iGPU/CPU lane (${MIOS_PORT_LLM_LIGHT}) instead of the dGPU
endpoint above -- so the dGPU stays free for whichever agent holds the
primary stream. Backed by mios-hermes-cpu.Modelfile (the CPU half of the
pair; `model` above -> mios-hermes is the GPU half). Omit cpu_* to keep
an agent single-lane.
"ALL AGENTS USE SGLANG": Hermes-as-fan-out-SECONDARY
dispatches to the SGLang heavy lane too (was the mios-llm-light CPU twin). The
Hermes PRIMARY stays on its :8720 gateway (endpoint above) because it needs
its 64k tool-use context + native browser/CDP/terminal loop, which the 16k
SGLang lane can't host; moving the workers OFF mios-llm-light already relieves the
contention that was timing the Hermes primary out.

<!-- mios-src:1061257e7d88 from usr/share/mios/mios.toml:3029-3042 -->

### default=false: opencode's `run` mode HANGS — even with...

default=false: opencode's `run` mode HANGS — even with
mios-opencode:latest resident + a 240s budget, `opencode run` returns ZERO
output and times out (the model answers in <1s directly; the CLI itself is
stuck in non-interactive mode). With default=true opencode was pulled into
EVERY council/swarm turn, so each one waited up to the gateway timeout for its
💤 — the dominant latency in a normal chat. Make it NON-default so it only
engages when a turn is genuinely code-focused (role-matched), not every turn.
Re-enable once `opencode run` headless invocation is fixed (flags/output-mode).

<!-- mios-src:3fc0b030723f from usr/share/mios/mios.toml:3067-3074 -->

### fanout=false (concurrent-swarm fix): opencode was pulled...

fanout=false (concurrent-swarm fix): opencode was pulled
into EVERY swarm/council turn despite default=false, where its `run` HANGS (->
90s timeout + dumps its whole prompt into the stream) AND its qwen2.5-coder:7b
@ num_ctx=32768 holds ~23GB = MONOPOLISES the shared 4090, blocking co-loading
so real work spills to CPU. Exclude it from automatic fan-out; it engages only
when a turn is explicitly code-routed. Re-enable once `opencode run` is fixed.

<!-- mios-src:2c7f62dbd821 from usr/share/mios/mios.toml:3076-3081 -->

### health_gate (- root cause of the "all nodes succeed=false...

health_gate (- root cause of the "all nodes succeed=false,
output=0 / merged_chars=0" multi-agent failure): the opencode gateway (:8780) is
default-OFF (the `run` hang documented above), but WITHOUT this flag the
orchestrator's liveness model (_live_agent_names) treats a non-health-gated
agent as ALWAYS live, so _reroute_dead_nodes sinks every dead-node DAG facet
onto the dead :8780 -> "All connection attempts failed" xN -> ZERO agent output
merged. health_gate makes opencode liveness-probed + DROPPED when unreachable
(identical to the :8730 hermes-worker pattern), so a fan-out DAG degrades to a
reachable agent instead of a dead sink. Auto-rejoins if the gateway is ever up.

<!-- mios-src:878002903cc5 from usr/share/mios/mios.toml:3083-3091 -->

### P3.2 SPOF removal

P3.2 SPOF removal: when opencode's :8780 backend is down, route to hermes
(the orchestrator can still write code well enough as a fallback). Visible
in /v1/cluster/health.chain so an operator/A2A peer knows the fallback exists.

<!-- mios-src:19d6bd26a13a from usr/share/mios/mios.toml:3096-3098 -->

### "mios-daemon also has a mios-daemon-agent that lives on...

"mios-daemon also has a mios-daemon-agent that lives on
cores always running (reads all SYSTEM(S) logs, journal, etc) and keeps them
in the loop for followups/redirections". "mios-daemon-
agent = mios-cpu/reasoner! CONSOLIDATE" -- so this ONE always-on CPU process
on a loopback port is BOTH the global log/journal monitor AND the council's
CPU reasoning lane. It runs LIGHT in the background (~2c/4t) and BURSTS to
8c/16t when it joins a foreground pipeline turn.
WS-10: repoint off the daemon-agent's retired CPU backend (:11435 dead) to
mios-llm-light; model 'mios-daemon-agent' is aliased to gemma4:12b. Was :8740/v1.
"ALL AGENTS USE SGLANG": the council CPU-reasoner now
dispatches to the SGLang heavy lane (:11441, mios-heavy) like every other
agent, instead of the contended mios-llm-light :11450. (The always-on background
log/telemetry loop on :8740 is unchanged; this is only its FAN-OUT dispatch.)

<!-- mios-src:c3a6ea817937 from usr/share/mios/mios.toml:3102-3114 -->

### fanout=true (was false): the OLD telemetry-only DUMP...

fanout=true (was false): the OLD telemetry-only DUMP flooded unrelated answers
with crowdsec/CDP digests ("fail across the board",), so
it was muted. Now it REASONS and folds telemetry in ONLY when the request
concerns the system (see _daemon_agent_reply's system prompt), so it is safe
to fan out CONCURRENTLY on every substantive turn -- exactly the operator's
"daemon-agent runs in the pipeline concurrently during GPU + iGPU compute".
Foreground turns burst to 8c/16t (MIOS_DAEMON_AGENT_THREADS); the always-on
background loop stays light at ~2c/4t.

<!-- mios-src:5a6ac08c08d5 from usr/share/mios/mios.toml:3122-3129 -->

### [agents.mios-reasoner-cpu] was CONSOLIDATED into...

[agents.mios-reasoner-cpu] was CONSOLIDATED into [agents.mios-daemon-agent]
above ("mios-daemon-agent = mios-cpu/reasoner!"). It
pointed at the SAME retired CPU lane (:11435) running the SAME small qwen3:1.7b, so
the always-on daemon-agent simply ABSORBED the reasoning role rather than
running a duplicate light-lane. To run a CPU/iGPU reasoner on OTHER hardware
(e.g. the AMD iGPU served natively on the Windows host via llama.cpp+Vulkan
:11436), add a DISTINCTLY-NAMED node in /etc/mios/mios.toml so the tailnet IP
stays out of the public repo -- e.g. [agents.mios-igpu], already wired in the
host overlay (same auto-join/auto-drop health_gate pattern as ai-local).

<!-- mios-src:b288bc9d49c3 from usr/share/mios/mios.toml:3151-3159 -->

### Operator can add more agents here -- e.g.

Operator can add more agents here -- e.g.:
  [agents.aichat]
  endpoint = "http://localhost:8765/v1"
  role     = "chat"
  ...
No code edits required; refine_intent reads this list at
request time via the userenv.sh slot map.

<!-- mios-src:d954687f97e0 from usr/share/mios/mios.toml:3161-3167 -->

### ANY AGENT ON ANY ENGINE / NODE ("make sure any Agent(s) can...

----------------------------------------------------------------------------
ANY AGENT ON ANY ENGINE / NODE ("make sure any Agent(s)
can be in any AI Engine/Compute Pipeline -- CPU, dGPU, iGPU, Accelerator" +
"any Agent/Sub-Agent can run on any node/endpoint -- iPhone, Android, other
MiOS nodes/clusters"). An agent is a JOB (a Modelfile); a BINDING is an
endpoint+model that serves it. Beyond the single `endpoint`/`model` (the
agent's home lane) + the legacy `cpu_endpoint`/`cpu_model` twin, declare extra
bindings under `engines` (local compute lanes) and/or `nodes` (remote devices/
hosts) -- the label is free-form; the endpoint decides WHERE it runs. agent-
pipe folds them all into one binding map: the fan-out offloads a concurrent
secondary to the first light engine it finds (cpu -> igpu -> accelerator), and
any binding can be a planner agent-task target. Example (put PERSONAL tailnet
endpoints in /etc/mios, NOT this public vendor file):
  [agents.hermes.engines.igpu]
  endpoint = "http://<igpu-host-tailnet>:11436/v1"    # llama.cpp + Vulkan
  model    = "mios-hermes-igpu"
  [agents.hermes.nodes.iphone]
  endpoint = "http://<iphone-tailnet>:8500/v1"        # AI.Local on the phone (OpenAI /v1)
  model    = "qwen2.5-3b-instruct-4bit"
The target engine/node must actually SERVE that model; health_gate=true makes
a come-and-go node (phone/cluster) auto-join when up + drop when gone.
----------------------------------------------------------------------------
CLIENT-HOSTED SWARM NODES ("AI.Local iphone app hosts
its own endpoint on Tailscale ... added to the swarm as a node capable of
local mobile models"). A client device running an OpenAI-compatible local-
model server on the tailnet becomes a swarm agent here. health_gate=true
means it only engages when REACHABLE (phone awake + serving) and drops fast
when asleep/absent -- auto-join-when-up, auto-drop-when-gone.

REACH PATH: Tailscale runs INSIDE the WSL VM (node "mios-dev", installed
), so agent-pipe reaches tailnet peers DIRECTLY by their 100.x
IP -- no reverse portproxy. (mirrored/"host" WSL networking stays OFF -- it
death-spirals the Quadlet stack per .wslconfig; tailscaled in the VM is the
safe alternative. --accept-dns=false so MagicDNS doesn't disturb the VM's
resolver, so peers are addressed by tailnet IP, not name.)

<!-- mios-src:e7043cdededb from usr/share/mios/mios.toml:3169-3203 -->

### A phone / mobile device running AI.Local -- an OpenAI...

A phone / mobile device running AI.Local -- an OpenAI /v1-compatible local-model
server -- reached over Tailscale. Open the AI.Local app to host; closing it
drops the node from the swarm (health_gate). OPERATOR-SPECIFIC + PRIVACY: vendor
ships `endpoint` EMPTY so no personal device name / tailnet IP is baked into the
public repo; set it to your own device's tailnet /v1 endpoint in your /etc/mios
or ~/.config/mios overlay. Empty = inert node.

<!-- mios-src:a363b290fd2d from usr/share/mios/mios.toml:3206-3211 -->

### [blades.*] -- BLADE (machine) topology + per-blade capacity...

----------------------------------------------------------------------------
[blades.*] -- BLADE (machine) topology + per-blade capacity (V4/V5). A BLADE is a
physical MACHINE; a NODE ([nodes.*] below) is a compute unit (CPU/iGPU/dGPU/NPU +
engines) that lives ON a blade. This makes "nodes X, Y, Z are one machine"
EXPRESSIBLE (set each node's `blade =` to the SAME blade name) and gives the
admission gate a per-blade VRAM budget so a REMOTE node's residents are checked
against ITS machine's headroom, NOT the single local 24GB scalar (the "remote
residents vs one local VRAM scalar" bug).

DEFAULT (this empty table + no `blade` on any node): every node belongs to the
LOCAL blade, whose name is the [identity].hostname SSOT and whose capacity defaults
to the code's VRAM_BUDGET_MB scalar + admit load ceiling -- i.e. EXACTLY today's
single-blade behaviour. The per-blade comparison is FLAG-GATED off by
[admission].multiblade_enable (operator-live-validated on a real cluster); until
then this is pure data.

Per-blade fields (declare in your /etc/mios overlay alongside the remote [nodes.*]):
  vram_budget_mb -- total VRAM headroom on that machine (MB). Omit to inherit the
                    local VRAM_BUDGET_MB (degrade-open). A node co-loads only while
                    its blade's measured residents + the new model fit this budget.
  load_ceil      -- optional 1-min loadavg ceiling for the blade (the LOCAL blade
                    honours it; a remote blade has no local loadavg signal so it is
                    degrade-open / not gated until a remote-load probe exists).
Example (put real machine names/capacities in /etc/mios, NOT the public vendor file):
  [blades.workstation]            # the box this MiOS runs on; name == [identity].hostname
  vram_budget_mb = 23000          # OVERRIDE the local default (else inherits VRAM_BUDGET_MB)
  [blades.potato]                 # a second machine on the tailnet
  vram_budget_mb = 8000           # its smaller GPU's headroom
  load_ceil      = 16
  [blades.bigbox]
  vram_budget_mb = 80000          # an 80GB accelerator box
...then point nodes at their blade:  [nodes.potato-dgpu] ... blade = "potato"

<!-- mios-src:0b291c71c5cd from usr/share/mios/mios.toml:3235-3266 -->

### CANONICAL WORKER + NODE POOL ("don't have separate CPU...

----------------------------------------------------------------------------
CANONICAL WORKER + NODE POOL ("don't have separate CPU
1,2,3 / dGPU 1,2,3 replicas -- there should just be a MiOS Modelfile dispatched
as many times as needed to ANY node(s)"). The model is ONE canonical MiOS
worker dispatched across a declared pool of compute nodes -- NOT a set of hand-
partitioned per-endpoint research replicas. Per-endpoint raw-base replicas are
avoided on purpose: they bypass the MiOS Modelfiles and can mis-place an
oversized base on a CPU-only lane (a model far larger than that lane can serve
-> pegged cores -> a load runaway).

THE MODEL: ONE canonical MiOS worker brain -- a MiOS-discipline Modelfile tag
(mios-agent on GPU lanes, its mios-agent-cpu twin on CPU/light lanes), NOT a raw
base; each node serves the canonical tag its lane is sized for.

THE DISPATCH: agent-pipe's _load_node_pool() reads [nodes.*] below and SYNTHE-
SISES one research-worker registry agent PER NODE -- `node:<name>` = {endpoint,
model(the node's CANONICAL Modelfile tag), lane, research_only, fanout,
engines} -- mirroring the a2a:<peer> injection. So the EXISTING capacity-aware
fan-out / swarm-DAG logic (_pick_fanout_agents / _agent_dag_from_tasks, bounded
by the P1 admission controller + per-lane/-endpoint semaphores) dispatches the
ONE worker brain across the node pool BY CAPACITY -- "as many times as needed
to any node(s)" -- instead of bespoke per-endpoint replica entries. A node's
per-node research_only flag selects WHEN it joins: the shipped default
nodes_research_only=false (below) makes every node eligible on EVERY turn, and a
per-node research_only=true holds that one node for research/deep turns only
(the per-node value wins). Safety lives in admission, never in disabling nodes:
the P1 admission controller + COUNCIL_MAX + per-lane/-endpoint semaphores keep
the wide roster from stampeding. The CPU-lane model backstop (_cap_cpu_lane_
model) still force-caps any light-lane dispatch to the micro model -- belt +
suspenders (the cpu node already declares the micro twin). Degrade-open: if
[nodes.*] is ABSENT, behaviour is unchanged.

A `node` declares WHERE compute lives + WHAT canonical Modelfile it serves; the
`model` MUST be a Modelfile tag (mios-agent / mios-agent-cpu / mios-igpu), NOT a
raw base. Vendor ships the LOCAL nodes + the SHAPE; put REMOTE nodes (potato,
phone, cluster) -- with their tailnet endpoints -- in your /etc/mios overlay so
no personal node name / IP is baked into the public repo. `lane` picks the
semaphore/diversity bucket; `health_gate=true` makes a come-and-go remote node
auto-join when reachable + drop when gone (local nodes omit it = always live).
The target endpoint MUST actually serve that Modelfile tag.
ALL LLAMA.CPP (operator binding: "EVERYTHING IS LLAMA.CPP"). The GPU +
light lanes point to mios-llm-light (${MIOS_PORT_LLM_LIGHT}).
api=llamacpp -> KV-paging + no tool_choice=required.
health_gate=true -> a lane is probed + skipped if mios-llm-light is momentarily down
(never a false "All connection attempts failed" fan-out; e2e).
"ALL AGENTS USE SGLANG": every swarm worker dispatches to
the SGLang heavy lane (:11441, mios-heavy = Qwen3-8B-AWQ; see [ai.sglang]) instead of the
mios-llm-light multi-model lane. SGLang does CONTINUOUS BATCHING, so N concurrent
research facets are served in parallel on ONE backend -- whereas mios-llm-light
loads one model at a time and THRASHED when these nodes requested different
models (gemma4:12b + qwen3:1.7b + ...) concurrently, the root cause of the
75s/150s node timeouts on the "global trending tech" research turn. All worker
nodes now share the sglang endpoint+model so the fan-out is real concurrency.
Local CPU lane -- mios-cpu-node, a bare llama.cpp llama-server on granite-4.1-8b
with n-gpu-layers 0. Was pointed at the SGLang GPU endpoint with lane="gpu", so
the name was the only CPU thing about it and the pool had no CPU lane at all
while [dispatch] budgeted one (lane_priority cpu:7, lane_concurrency_cpu 2).

<!-- mios-src:d16665647028 from usr/share/mios/mios.toml:3269-3325 -->

### Declared protocol (operator no-hardcode): llama.cpp -> the...

Declared protocol (operator no-hardcode): llama.cpp -> the pipe
does /slots KV-paging here (_kv_paging) + skips tool_choice=required, driven by
THIS field instead of a port-substring match (so it's correct even if the
operator serves it on a non-11436 port).

<!-- mios-src:4896fe0bd2d6 from usr/share/mios/mios.toml:3339-3342 -->

### Local vLLM HEAVY lane (Phase 2) -- the re-scoped...

Local vLLM HEAVY lane (Phase 2) -- the re-scoped mios-llm-heavy-alt Quadlet on the dGPU
(PagedAttention + APC; see [ai.vllm]). health_gate=true means it AUTO-JOINS the
swarm only when actually reachable: it is DISABLED + VRAM-gated by default, so
it stays inert with ZERO risk until the operator bakes weights + enables the
service on a dGPU with headroom, then it joins research/deep fan-outs. api=openai
(vLLM speaks /v1 natively + honours tool_choice=required, unlike the iGPU).

<!-- mios-src:5be9f05fc093 from usr/share/mios/mios.toml:3344-3349 -->

### Local mios-llm-light lane (WS-10) -- the llama.cpp...

Local mios-llm-light lane (WS-10) -- the llama.cpp multi-model + KV-paging lane
(mios-llm-light.container on :11450; see [llamacpp]). health_gate=true =>
AUTO-JOINS only when reachable, and the quadlet is gated off until GGUFs are
provisioned (models/.ready), so this stays inert with ZERO risk until the
operator bakes GGUFs + enables the lane. api=llamacpp => the pipe does /slots
KV-paging here (_kv_paging) + skips tool_choice=required -> fleet-wide KV-cache.

<!-- mios-src:46950f4086c2 from usr/share/mios/mios.toml:3367-3372 -->

### REMOTE nodes (operator overlay only -- keep tailnet...

REMOTE nodes (operator overlay only -- keep tailnet names/IPs out of the public
repo). Each is the SAME consolidation: one canonical MiOS Modelfile tag served
on that node, dispatched by capacity -- NOT a hand-numbered replica. Every node
MUST expose the OpenAI /v1 surface (MiOS is /v1-only). Example shape (put in
/etc/mios/mios.toml):
  [nodes.potato-dgpu]
  endpoint    = "http://<potato-tailnet>:8500/v1"
  model       = "mios-agent"          # the GPU brain on the potato node
  lane        = "gpu"
  blade       = "potato"              # V4: this node lives on the `potato` MACHINE
  health_gate = true                  # auto-join when reachable, drop when gone
  [nodes.potato-cpu]
  endpoint    = "http://<potato-tailnet>:8451/v1"
  model       = "mios-agent-cpu"      # the CPU twin on the potato node
  lane        = "cpu"
  blade       = "potato"              # SAME machine as potato-dgpu -> one blade budget
  health_gate = true
  [nodes.phone]
  endpoint    = "http://<phone-tailnet>:8500/v1"
  model       = "mios-agent-cpu"      # or the phone's own small local model tag
  lane        = "mobile"
  health_gate = true

A PLAIN remote box that serves its OWN model (not the MiOS Modelfiles) joins the
SAME way -- declare api="openai" (or leave api="" to auto-detect) and the model's
REAL served tag (qwen3.5:4b etc.); the pipe then runs its own grounding tool-loop
(web_search ...) + strips qwen3 <think> tags + posts to the box's
/v1/chat/completions. It MUST expose OpenAI /v1 -- MiOS speaks no other dialect.
A remote CPU node KEEPS its declared tag (the cpu-lane model cap is LOCAL-only --
a remote box serves its own catalog, not the local micro tag). Example (operator's
second machine, CPU+GPU; put the real tailnet IP in /etc/mios/mios.toml, NOT the
public vendor file):
  [nodes.remote-gpu]
  endpoint     = "http://<host-tailnet>:8500/v1"
  model        = "qwen3.5:4b"          # the remote's best tool-capable served tag
  lane         = "gpu"
  api          = "openai"
  health_gate  = true
  tool_capable = true
  [nodes.remote-cpu]
  endpoint     = "http://<host-tailnet>:8451/v1"
  model        = "qwen3:1.7b"          # lighter tag for the slower CPU lane
  lane         = "cpu"
  api          = "openai"
  health_gate  = true
  tool_capable = true

<!-- mios-src:08b49389bb33 from usr/share/mios/mios.toml:3398-3443 -->

### [dispatch] -- multi-agent CONCURRENT fan-out ("the MiOS...

----------------------------------------------------------------------------
[dispatch] -- multi-agent CONCURRENT fan-out ("the
MiOS mechanism should dispatch to multiple agents at a time -- not ALL
agents, but a couple at least"). agent-pipe picks ONE primary agent
(refine target_agent / registry default) AND up to fanout_max-1 relevant
SECONDARY agents -- scored by role/strengths overlap with the refined
intent (NO hardcoded topic map) -- runs them concurrently, surfaces each
in the reasoning dropdown, and merges their answers in the polish step.
Dead endpoints (e.g. opencode :8780 when not served as /v1) drop out.
fanout_max = 1 restores exact single-agent behaviour.
----------------------------------------------------------------------------

<!-- mios-src:f7d070421fac from usr/share/mios/mios.toml:3445-3455 -->

### [cost] -- WS-RES-GOV cost/energy accounting (CLASSic "Cost"...

----------------------------------------------------------------------------
[cost] -- WS-RES-GOV cost/energy accounting (CLASSic "Cost" axis). On a local-
GPU OS the POWER/thermal envelope is the binding constraint, not an API bill;
mios_cost prices each dispatch by ENERGY (gpu_watts x elapsed -> Wh, optionally
$ at usd_per_kwh) for a local lane, or $/Mtok for a remote lane, and accumulates
per-lane totals (observe via /v1/cost + /v1/scheduler.cost). OBSERVE-ONLY +
default-off: recording is pure arithmetic that gates nothing. Env:
MIOS_COST_ACCOUNTING_ENABLE.
----------------------------------------------------------------------------

<!-- mios-src:61e446b34c9f from usr/share/mios/mios.toml:3457-3465 -->

### SEC-03 tamper-evident event-bus hash chain (mios_audit)....

----------------------------------------------------------------------------
SEC-03 tamper-evident event-bus hash chain (mios_audit). Every `event` row is
linked to its predecessor by a SHA-256 chain at the single persist chokepoint, so
any later insert/delete/reorder/content-edit is detectable via
GET /v1/audit/chain/verify or the mios-chain-verify CLI. ON by default: the
per-event cost is a single sha256 over a small JSON string plus an in-memory cache
update (the chain columns ride the existing INSERT -- no extra DB round-trip, no
per-insert SELECT-max), and it is the integrity substrate record-replay /
self-improve-act / DGM build on. Degrade-open: a chaining hiccup never blocks event
logging. Override via MIOS_AUDIT_CHAIN_ENABLE.

<!-- mios-src:2d2f5efc417e from usr/share/mios/mios.toml:3473-3482 -->

### WORKER-TOOLS reranker/priority knobs...

----------------------------------------------------------------------------
WORKER-TOOLS reranker/priority knobs (mios_worker_tools.configure). The BM25
lexical arm's saturation + length-normalisation, the unembedded-verb priority->
score fallback map, and the weak-lane tool-priority ranking flag. Kept here as SSOT
so none of these stay baked into the ranking code (sibling of the [dispatch] rerank_*
knobs). Override via MIOS_BM25_K1 / MIOS_BM25_B / MIOS_TOOL_PRIORITY_CORE_FIRST.

<!-- mios-src:e96e4f8a6244 from usr/share/mios/mios.toml:3486-3491 -->

### true -> a weak lane ranks the curated core-tier READ verbs...

true -> a weak lane ranks the curated core-tier READ verbs first (perm=read AND
tier=core), via the reranker's own core-tier signal -- NOT English name substrings.
false -> degrade to permission order alone (read verbs rank 1); never a keyword gate.

<!-- mios-src:dc259d7e0839 from usr/share/mios/mios.toml:3498-3500 -->

### WS-SCHED-SLO deadline/SLO scheduling policy (the EDF +...

----------------------------------------------------------------------------
WS-SCHED-SLO deadline/SLO scheduling policy (the EDF + fail-closed-shed core).
These tune the pure mios_slo decision module; the shed itself is gated by
[dispatch].slo_shed_enable (default off). A turn carries an SLO class
(interactive | best_effort); the scheduler orders least-deadline-first and a
best_effort dispatch is shed under contention while an interactive (foreground,
human-waiting) turn is never shed.

<!-- mios-src:525d48d643b2 from usr/share/mios/mios.toml:3503-3509 -->

### Agent-pipe turn-priority scorer...

Agent-pipe turn-priority scorer (mios_sched._sched_priority): priority =
f(complexity, urgency). Every key below is ALSO the code's degrade-open fallback
(a named constant), each EQUAL to the long-standing literal -- so an absent or
malformed [sched] reproduces prior scoring byte-for-byte. Operator-tunable here;
the file path itself is env-overridable via MIOS_TOML (vendor < /etc < ~/.config).

priority_mode -- how urgency/complexity are derived (env: MIOS_SCHED_PRIORITY_MODE):
  "ssot"  = parameterized lexical urgency from the term sets below (today's path).
  "model" = PREFER an upstream model-supplied NUMERIC refined.urgency /
            refined.complexity when present, else the lexical/derived path. Consumes
            an already-present signal only -- it never adds an LLM call of its own.

<!-- mios-src:4c1d75128845 from usr/share/mios/mios.toml:3525-3535 -->

### Operator-localizable urgency vocabulary. Matched...

Operator-localizable urgency vocabulary. Matched case-insensitively with Unicode
casefold, so non-English terms work -- the LIST is SSOT (localizable) and the matcher
is plain casefold membership, NOT an English/ASCII keyword gate.

<!-- mios-src:d34addcc6ab5 from usr/share/mios/mios.toml:3543-3545 -->

### Turn-boundary PREEMPTION (T-019 / SCHED-01) + the...

Turn-boundary PREEMPTION (T-019 / SCHED-01) + the token-time-sliced priority QUEUE
(T-020 / SCHED-02) that layers on it. DISTINCT from both [sched] (which only SCORES
a turn's priority) and [dispatch].rr_* (which time-slices the DECODE loop WITHIN one
generation). This governs the agent-pipe's TURN-boundary preemption seam
(mios_preempt.turn_boundary): at each dispatch turn boundary the scheduler may
snapshot + yield a running turn to a higher-priority waiter and resume it; and the
token-time-sliced queue (mios_preempt.TokenSliceQueue + slice_boundary): turns
enqueue with a priority + a per-turn token SLICE budget, the scheduler dispatches the
highest-priority ready turn, and at each token-slice boundary it re-evaluates via the
same turn_boundary mechanism. It is the substrate later scheduler policies build on.
Every key below is ALSO the code's degrade-open fallback
(mios_preempt._SCHEDULER_FALLBACK), each EQUAL to the default here, so an
absent/malformed [scheduler] reproduces the default behaviour byte-for-byte. Env
overrides: MIOS_SCHEDULER_* (highest precedence).

preempt_enable -- MASTER FLAG (T-019). false (DEFAULT) => the turn-boundary hook is a
pass-through no-op and a turn runs byte-identically (today's behaviour). true =>
the hook consults the PreemptScheduler at the boundary. The ON path is operator-
live-validated; leave it off unless load-testing preemption.

<!-- mios-src:24e350608b7e from usr/share/mios/mios.toml:3559-3577 -->

### queue_enable -- MASTER FLAG (T-020) for the...

queue_enable -- MASTER FLAG (T-020) for the token-time-sliced priority queue, SEPARATE
from preempt_enable. false (DEFAULT) => slice_boundary is a pass-through no-op (no
queue interposition; turns admit/run byte-identically). true => turns are ordered by
priority + token-time-sliced, re-evaluating preemption at each slice boundary (which
additionally requires preempt_enable for the actual snapshot/yield). The ON path is
operator-live-validated; leave it off unless load-testing the queue.

<!-- mios-src:47b7e1286bf7 from usr/share/mios/mios.toml:3579-3584 -->

### [admission] -- V5 multi-blade + per-tenant admission knobs....

----------------------------------------------------------------------------
[admission] -- V5 multi-blade + per-tenant admission knobs. Two INDEPENDENT,
DEFAULT-OFF flags; each off-path is a pure no-op so admission + the priority gate
behave byte-identically to today's single-blade / no-quota path. The ON paths are
operator-live-validated (they need a real multi-blade cluster + real tenants).

<!-- mios-src:a2feeac9ae8a from usr/share/mios/mios.toml:3614-3618 -->

### multiblade_enable -- when true, the capacity-aware...

multiblade_enable -- when true, the capacity-aware admission gate (_admit) compares
a node's measured residents against ITS [blades.*] VRAM budget (node -> blade ->
capacity) instead of the single LOCAL VRAM_BUDGET_MB scalar, and SKIPS the local
/proc/loadavg ceiling for a REMOTE blade (the local loadavg says nothing about
another machine). false (DEFAULT) -> the local scalar + local ceiling EXACTLY as
today. DEGRADE-OPEN: an unknown blade/capacity falls back to the local scalar, so
admission is never wedged. Requires [blades.*] + per-node `blade` to do anything
useful; with neither, every node is the local blade and on==off.

<!-- mios-src:4834a914b87d from usr/share/mios/mios.toml:3620-3627 -->

### tenant_quota_enable -- when true, the global priority gate...

tenant_quota_enable -- when true, the global priority gate gains a per-TENANT
(verified owner) concurrent-dispatch FAIR-SHARE so one tenant cannot hold every
global dispatch slot while another waits. false (DEFAULT) -> no per-tenant cap
(today). DISTINCT axis from [users.*] quota (mios_quota = per-user RPM/spend rate
budget); this is concurrent in-flight fair-share, the AIOS scheduler dimension. The
tenant is the V2 principal-bound owner (reused from owner_user row-scoping); a
system/daemon dispatch with no owner is never capped (degrade-open).

<!-- mios-src:7edab0761337 from usr/share/mios/mios.toml:3629-3635 -->

### Selection mode ("weigh every agent equally + dispatch...

Selection mode ("weigh every agent equally + dispatch
multiple concurrently"):
  council   = EQUAL WEIGHT. Every chat-eligible agent (every [agents.*]
              without fanout=false, minus the primary) runs CONCURRENTLY
              each turn, up to fanout_max, regardless of tag relevance --
              no Hermes monopoly. Lane-diverse so CPU + GPU agents run in
              parallel. This is the active policy.
relevance = MODEL-DRIVEN (de-hardcode "the scoring IS a
              hardcode in and of itself"): the micro-model picks the relevant
              specialist agents from each agent's OWN published card -- was a
              hand-coded role/strengths token-overlap scorer + magic CPU-lane
              bonus + ASCII tokenizer (all removed). NO hardcoded heuristic now.
              Mechanism controlled by fanout_select_mode below.

<!-- mios-src:fe3c97468f31 from usr/share/mios/mios.toml:3767-3779 -->

### COUNCIL BY DEFAULT ("force council shouldn't be FORCED but...

COUNCIL BY DEFAULT ("force council shouldn't be FORCED but a
default option ENABLED"): true -> SUBSTANTIVE turns (intent agent/multi_task, or
chat >= decompose_min_words) engage the full multi-agent council BY DEFAULT, no
force toggle -- breadth + live thinking/emitters by default. The OWUI
force_council toggle still overrides (explicit on/off). Trivial chat stays single.
Bounded by council_max + admission + lane/sub-lane semaphores. false -> the old
native-loop-default (council only when force-toggled).

<!-- mios-src:b4f9989a3280 from usr/share/mios/mios.toml:3781-3787 -->

### Relevance-selection mechanism for `mode = "relevance"`...

Relevance-selection mechanism for `mode = "relevance"` : the
legacy hand-coded token-overlap scorer is REPLACED by model-driven selection -- the
micro-model ([ai].micro_model/micro_endpoint) is shown the refined plan + each
eligible agent's published card and returns which specialists to engage. No magic
weights, no lexical/ASCII bias, no topic map. (Ignored under `mode = "council"`,
which engages every eligible agent equally.)
  model = micro-model picks the relevant subset (degrades to council on failure)
  off   = skip the model call -> council-equal-weight over the eligible pool

<!-- mios-src:1bc4ed99f254 from usr/share/mios/mios.toml:3796-3803 -->

### ── REAL SOURCE CITATIONS ("sources... should be A2A or...

── REAL SOURCE CITATIONS ("sources... should be A2A or
metadata"): every web_search this turn (native loop, council/DAG facets, the
parent's harvest of each sub-agent's answer) records its REAL result URLs; the
final answer attaches a numbered **Sources:** list + structured `mios_sources`
metadata. max_sources caps how many appear; registry_cap bounds the per-turn
cross-agent collector (most-recent N turns). agent-pipe reads these via _dispatch_num.

<!-- mios-src:266e97d028d0 from usr/share/mios/mios.toml:3806-3811 -->

### When a swarm/DAG turn grounds NOTHING (research+nodes both...

When a swarm/DAG turn grounds NOTHING (research+nodes both empty) and the answer
is empty/punt OR it was a web/news turn, RE-ANSWER via the always-up light-lane
native loop (real grounding + real citations) instead of shipping blank or
fabricated text -- the failure mode when leaf agents are down.
false = prior behaviour (ship the empty/fabricated synthesis). Degrade-open.

<!-- mios-src:baff7fd0bac4 from usr/share/mios/mios.toml:3814-3818 -->

### Trust the planner's atomic verdict ("research native...

Trust the planner's atomic verdict ("research native patterns"):
when _plan_swarm self-gates to [] (focused/atomic ask) AND no breadth signal fires
(refine deep/deep_research/multi_task/_multi_step or an operator toggle), do NOT
force-seed a synthetic swarm -> answer via the single-agent path (faster, on-topic).
Genuinely broad asks still fan out to ALL live nodes. false = prior always-seed.

<!-- mios-src:034c6e950688 from usr/share/mios/mios.toml:3820-3824 -->

### ── NATIVE-LOOP GROUNDING / HYGIENE ("OWUI LITERALLY CARRIES...

── NATIVE-LOOP GROUNDING / HYGIENE ("OWUI LITERALLY CARRIES
ENVIRONMENT DETAILS EVERY TURN" + fix the "list N recent X" wrong-year fabrication).
agent-pipe reads these from here via _DISPATCH_TOML (runtime override via the matching
MIOS_NATIVE_LOOP_* env). All default-on; each behaviour degrades open on any error.
  query_reformulate: ALWAYS reformulate the web_search query via the generative micro-
    LLM (_formulate_web_query) -- not just hybrid turns -- so a verbose imperative
    ("Give me a briefing on X this week") becomes a clean entity+date query instead of
    the leading word "give" anchoring a dictionary result. (no hardcoded stopword list)
  date_in_query: fold the resolved current date (YYYY-MM) into time-sensitive web_search
    queries at the dispatch choke-point (covers the model's own in-loop calls too).
  date_anchor: emit a HARD CURRENT_DATE line in the native-loop model context right
    before the user question, so "today/this week/recent/latest" resolve to the present
    (the soft env-grounding prose is overridden by an 8B on strong-prior topics).
  math_hint: instruct the native loop to route non-trivial computation to the sandboxed
    Python executor (run_sandboxed_code / run_python_tool_script), not in-head math.

<!-- mios-src:3cdf94de654c from usr/share/mios/mios.toml:3826-3840 -->

### ── SWARM-NODE COMPUTE BUDGET + DEEPEN ("every node computes...

── SWARM-NODE COMPUTE BUDGET + DEEPEN ("every node computes
... loop until satisfied"; SSOT'd after "HARDCODES!!!"). agent-pipe
reads these from here via _dispatch_toml(); runtime override via the matching
MIOS_* env (MIOS_DAG_NODE_MAX_TOKENS / _SLOW_MAX_TOKENS / _RETRY,
MIOS_SWARM_DEEPEN / _ITERS / _DEADLINE_S / _WEB_S).
Per-node answer token budget: fast lanes (dGPU/CPU) full, slow lanes (iGPU/
phone) trimmed so they finish within the read timeout instead of timing out.

<!-- mios-src:375f61294ebe from usr/share/mios/mios.toml:3845-3851 -->

### PER-NODE WALL-CLOCK DEADLINE (runaway/slowness fix): the...

PER-NODE WALL-CLOCK DEADLINE (runaway/slowness fix): the turn used to
wait for the SLOWEST node (potato-cpu ~600s) -> blew every client timeout. Each
agent node's dispatch+retries is bounded here; a node that doesn't answer in time
is abandoned (empty) and the synthesiser proceeds on who DID answer.

<!-- mios-src:b14b1123c7d9 from usr/share/mios/mios.toml:3855-3858 -->

### NODE/ENDPOINT-AWARE deadline ("LOCAL CPU IS NEEDED... ALL...

NODE/ENDPOINT-AWARE deadline ("LOCAL CPU IS NEEDED... ALL NODES PLAY A PART... planning isn't taking into account the nodes and endpoints"): a SLOW lane (CPU/iGPU/phone) gets a longer deadline. It is now SIZED to its hardware -- it REASONS over the grounding the fast lanes fetched this turn (no 16K-ctx own tool-loop) -- so its single pass finishes well inside this and is never abandoned just for being slow. The fast lanes deepen while it finishes (everything concurrent, all sources every turn).

<!-- mios-src:539b97b6a41f from usr/share/mios/mios.toml:3860-3860 -->

### P0 STABLE TOOL PREFIX ("a lot of tools but optimized")...

P0 STABLE TOOL PREFIX ("a lot of tools but optimized"): when true,
the native loop emits a BYTE-IDENTICAL core tool block first (every turn, same order)
so SGLang RadixAttention caches the system+tools prefix across turns instead of re-
prefilling it on every intent change. The per-turn relevance signal moves OFF the
tools[] array (which must stay stable) and onto a short "likely-relevant tools" TEXT
hint placed next to the user's question + a small cosine-ranked TAIL after the core.
false = legacy behaviour (intent-ordered out[:cap], a fresh prefix every turn). Ship
OFF, measure the prefix-hit-rate, then flip ON. Degrade-open: OFF == byte-for-byte
the prior pipeline. See usr/share/mios/doc/concepts/mcp-tools-optimization.md (P0).
ENABLED after verification: core==23 (tier `core` only) -> ~33 tools visible
(near the working legacy 36); 33/33 byte-identical tool prefix across unrelated intents
(RadixAttention-cacheable); zero accuracy regression on the 7 AIOS capabilities (apps
-> mios_apps, recall -> the saved fact); cap-safe for slow-lane nodes (core truncated to
their cap). Exact hit-rate % not metered (SGLang --enable-metrics off) but the prefill
reduction is deterministic given the proven byte-stability. Flip false to revert.

<!-- mios-src:67c51c1e57e3 from usr/share/mios/mios.toml:3866-3880 -->

### P2 TOOL RERANK ("a lot of tools but optimized"): a...

P2 TOOL RERANK ("a lot of tools but optimized"): a pure-compute
stage-2 over the per-turn cosine TAIL selection -- RRF-fuse the cosine rank with an
in-process BM25 lexical arm (over the same name+desc+examples corpus the embeddings use),
then greedy MMR diversify so two confusable near-duplicates don't both crowd the tail.
No model, ~+2-6ms, degrades-open to plain cosine. Default ON (strictly dominates cosine).

<!-- mios-src:cf24c1f710f8 from usr/share/mios/mios.toml:3893-3897 -->

### (P2 follow-up, operator-gated + default OFF: a...

(P2 follow-up, operator-gated + default OFF: a bge-reranker-v2-m3 cross-encoder stage-2c
behind a `rerank_xenc` flag -- needs a downloaded GGUF + a mios-llm-light --reranking lane +
VRAM headroom on the shared 4090. Inert until the operator deploys it; the pure-compute
RRF+MMR above is the shipping default. See the P2 doc for the wiring.)
DEEPEN: after its primary answer a fast swarm node loops extra web-research +
re-answer passes to widen coverage, hard-bounded by the barrier + deepen_iters +
deepen_deadline_s. By default it runs to that bound; set deepen_early_exit below to
ALSO stop once the per-node Definition-of-Done judge marks the answer satisfied.

<!-- mios-src:ae19c5c7cd1d from usr/share/mios/mios.toml:3904-3911 -->

### SATURATION SCHEDULER ("nothing in the pipeline is idle...

SATURATION SCHEDULER ("nothing in the pipeline is idle until
synthesis"). true -> DAG runs as a CONTINUOUS READY-QUEUE (a node dispatches the
moment its deps finish, bounded by the global/endpoint/lane semaphores) instead
of barrier'd topological levels (fast lanes idle waiting for the slowest node in
a level). Deepen still loops finished nodes until the GLOBAL barrier. false ->
the proven level-barrier fallback. Read by SWARM_SATURATE (env MIOS_SWARM_SATURATE).

<!-- mios-src:e912f3d024a0 from usr/share/mios/mios.toml:3913-3918 -->

### EARLY-EXIT ON SATISFIED

EARLY-EXIT ON SATISFIED: when true, each deepen pass first asks the per-node DoD
judge whether the node's current answer already satisfies its sub-query and STOPS
if so -- the heaviest compute isn't spent re-answering an already-good node and the
freed lane lets slower nodes finish sooner. DEFAULT false (opt-in): it changes
behaviour (fewer deepen passes) and the judge degrades to "satisfied" on its OWN
internal error, so it ships operator-gated + degrade-open. When on, the judge is
bounded by deepen_judge_timeout_s and any timeout/error falls through to the
deadline-bound loop (never under-computes). Read by DEEPEN_EARLY_EXIT (env
MIOS_SWARM_DEEPEN_EARLY_EXIT).

<!-- mios-src:58b4b93268e5 from usr/share/mios/mios.toml:3925-3933 -->

### Per-call wall-clock cap (seconds) on the deepen DoD judge...

Per-call wall-clock cap (seconds) on the deepen DoD judge (a yes/no micro-LLM),
kept well under deepen_deadline_s so a slow/hung judge becomes a caught timeout ->
the loop continues instead of stalling a coverage pass. Only used when
deepen_early_exit = true. Env MIOS_SWARM_DEEPEN_JUDGE_S.

<!-- mios-src:6ed81763857d from usr/share/mios/mios.toml:3935-3938 -->

### ── PER-LANE / GLOBAL CONCURRENCY (SSOT'd after...

── PER-LANE / GLOBAL CONCURRENCY (SSOT'd after "HARDCODES!!!").
agent_concurrency = default per-lane cap; lane_concurrency_<lane> overrides ONE
lane. The LOCAL gpu/cpu lanes (the single SHARED 4090 + in-VM CPU) are capped
to 2 so a wide research fan-out can't oversubscribe them (live test: it
thrashed the VM + WSL). REMOTE lanes (potato-gpu/cpu, igpu) keep the default --
separate hardware. Read via _dispatch_toml; override MIOS_AGENT_CONCURRENCY /
MIOS_AGENT_LANE_CONCURRENCY[_<LANE>].

<!-- mios-src:fdcd943fe317 from usr/share/mios/mios.toml:3940-3946 -->

### dGPU lane/endpoint caps RAISED to a BACKSTOP ceiling (...

dGPU lane/endpoint caps RAISED to a BACKSTOP ceiling (
"multiple medium/small models dispatch concurrently to dGPUs ... until
satisfied"). The real governor is now VRAM-AWARE ADMISSION (_admit gates a
cold model on measured free VRAM + VRAM_COLOAD_RESERVE_MB; see [dispatch].
admit_* + the VRAM_COLOAD_* env), so the dGPU packs several small models by
real headroom. These semaphores are the HARD OOM backstop if the VRAM probe
is wrong (the 4090 is shared with Windows). 4 = the big primary + up to 3
small co-loaded workers; lower if the host steals more VRAM.

<!-- mios-src:ffe886ed9d68 from usr/share/mios/mios.toml:3949-3956 -->

### P7 swarm-safety ("finish! I authorize you"): reverted 4->2...

P7 swarm-safety ("finish! I authorize you"): reverted 4->2, the known-safe ceiling. A broad dispatch_to_nodes swarm at 4 piled concurrent 8B generations onto the single SGLang :11441 -> OOM/cycle; 2 makes excess nodes QUEUE (degrade = slower, never crash). No VRAM change. Raise again only after per-engine spreading (route some agents off the gpu lane) frees headroom -- that needs the operator's model-placement decisions.

<!-- mios-src:0a217f778f37 from usr/share/mios/mios.toml:3957-3957 -->

### ── SWARM Phase-0/2/3 ("delegate a swarm to many small...

── SWARM Phase-0/2/3 ("delegate a swarm to many small models
concurrently across CPU+dGPU+nodes"). gpu_profile selects the dGPU topology:
  "orchestrator" (default, safe) = the single SGLang heavy lane (mios-heavy).
  "swarm"        = arm N single-model llama-server workers (mios-llm-worker@)
                   so 3-4 small models generate CONCURRENTLY on the dGPU. Flip to
                   "swarm" + provision GGUFs + define [nodes.*] serve workers, then
                   mios-swarm-pack-firstboot arms them (Phase-3, VRAM-RISKY).

<!-- mios-src:1576e4509de6 from usr/share/mios/mios.toml:3959-3965 -->

### Inert worker example (uncomment + adjust + set...

Inert worker example (uncomment + adjust + set gpu_profile="swarm" to arm). Each
is ONE concurrent llama-server on the dGPU; vram_mb feeds the budget guard +
per-endpoint admission; sub_lane gives it an independent concurrency semaphore.
  [nodes.swarm-dgpu-a]
  endpoint = "http://localhost:11461/v1"   # its own server instance
  model    = "qwen3:1.7b"                  # the alias it serves (= --alias)
  lane = "gpu"; sub_lane = "gpu0"; vram_mb = 2200; api = "llamacpp"; health_gate = true
  serve = true; gguf = "qwen3-1.7b-q4_k_m.gguf"; ngl = 99; ctx = 8192
  [nodes.swarm-dgpu-b]  # ...11462, another small model, sub_lane="gpu0" ...
  [nodes.swarm-cpu-a]   # lane="cpu"; sub_lane="cpu"; ngl=0; ram_mb=2500; ...
GLOBAL host in-flight cap (load-361 fix; research-endorsed).
Per-lane caps bound each lane, but with all-nodes-eligible the SUM of lanes can
swamp the host -> ONE process-wide cap on TOTAL running dispatches. Sized
~cores-reserve so normal multi-lane concurrency is unaffected; only an extreme
wide fan-out is bounded ("saturate to capacity, never over"). 0/unset -> code
default max(8, cpu_count-4). Read by _GLOBAL_DISPATCH_SEM.

<!-- mios-src:7611febb4a4a from usr/share/mios/mios.toml:3969-3984 -->

### ── COUNCIL ROSTER WIDTH + PER-ENDPOINT CAP (runaway fix)....

── COUNCIL ROSTER WIDTH + PER-ENDPOINT CAP (runaway fix). Left
uncapped, the council fans EVERY non-trivial turn out to ALL live agents
(MIOS_COUNCIL_MAX=0); with every node research-eligible by default, a trivial
prompt can cold-load the whole roster at once -> an inference thundering herd
-> load spike -> VM wedge. council_max bounds the SECONDARY roster size
(0 = uncapped, explicit opt-in) so only a slice of the roster joins a turn; a
node's own research_only=true can still hold it for research/news/deep turns
(default nodes_research_only=false = eligible every turn). endpoint_concurrency
caps concurrent calls to ONE inference daemon (host:port) so a wide fan-out
can't cold-load N models on the same backend simultaneously -- distinct from
the per-LANE cap (hardware category). Override via MIOS_COUNCIL_MAX /
MIOS_AGENT_ENDPOINT_CONCURRENCY.

<!-- mios-src:131c095e309d from usr/share/mios/mios.toml:3999-4010 -->

### ── Admission controller (P1,). NOW ON by default: it is the...

── Admission controller (P1,). NOW ON by default: it is the
AIOS-correct SAFETY layer + the PRECONDITION for "all nodes enabled by default"
(research eligibility is universal, safety lives in admission, never
by disabling nodes). Degrade-open + bounded-wait everywhere -> never deadlocks.
_disp_num reads these from here directly.

<!-- mios-src:b0eaf29139dd from usr/share/mios/mios.toml:4033-4037 -->

### ── WS-1 priority scheduler queue (AIOS Agent Scheduler...

── WS-1 priority scheduler queue (AIOS Agent Scheduler reordering,).
When ON, the next freed GLOBAL dispatch slot goes to the HIGHEST-PRIORITY
waiter (turn priority via _sched_priority + lane priority above, FIFO tie-break)
instead of arrival order -- this makes _sched_priority/_dispatch_priority ACTIVE
rather than advisory. Anti-starvation aging serves any waiter older than
priority_starvation_ms ahead of priority so slow lanes never indefinitely
starve. DEFAULT OFF + degrade-open: a pure no-op until enabled; any error falls
back to the proven plain FIFO global cap. Observe /v1/scheduler.priority_gate
first, then flip on via an /etc drop-in. _disp_num reads these directly.

<!-- mios-src:a324711b3b13 from usr/share/mios/mios.toml:4050-4058 -->

### T21 request-cancellation

T21 request-cancellation: cancel a NON-STREAMING turn's swarm the
moment the client disconnects, instead of churning DAG+deepen to turn_deadline_s.
The streaming path already self-bounds on disconnect. Default ON; degrade-open
(request=None / disabled -> deadline-only, unchanged). _disp_num reads these.

<!-- mios-src:70b1b86db2df from usr/share/mios/mios.toml:4061-4064 -->

### ── KV-cache paging (AIOS context-manager prototype, "VRAM...

── KV-cache paging (AIOS context-manager prototype, "VRAM
can compress or write to disk ... clean state when agents/models load/unload").
On a llama.cpp endpoint (launched with --slot-save-path) the agent-pipe
demand-pages each conversation's KV to/from DISK: page OUT the resident conv
(save) + page IN this one (restore) only on a conversation SWITCH (no per-turn
disk thrash). A swap-only backend can't do this; vLLM+LMCache is the Phase-2/3 scale-up.
Read by the agent-pipe (_kv_paging / _endpoint_is_llamacpp); env overrides
MIOS_KV_PAGING / MIOS_KV_PAGING_HINTS / MIOS_KV_PAGING_SLOT / _TIMEOUT.

<!-- mios-src:f3aea1930a15 from usr/share/mios/mios.toml:4086-4093 -->

### ── KV-cache FORK (WS-8) — branch a parent conversation's...

── KV-cache FORK (WS-8) — branch a parent conversation's saved KV into a NEW
child file so a swarm can fan out parallel cognitive paths from a SHARED PREFIX
(RadixAttention-style prefix-sharing on the disk-file prototype). A fork =
restore(parent)->save(child) over the existing /slots primitive, under the per-
slot lock. DEFAULT-OFF + degrade-open: when disabled (or on any slot error) the
child just starts cold. Read by the agent-pipe (kv_fork / mios_kvfork); env
overrides MIOS_KV_FORK / MIOS_KV_FORK_MAX_BRANCHES.

<!-- mios-src:4d9146ad2f01 from usr/share/mios/mios.toml:4098-4104 -->

### ── KV slot-file GC (WS-A4) — bound the on-disk KV...

── KV slot-file GC (WS-A4) — bound the on-disk KV paging/fork files so an
unbounded fork fan-out can't fill the disk. The systemd-tmpfiles age-out
(usr/lib/tmpfiles.d) is the OS-level backstop; this in-process sweep ALSO runs
when kv_slots_dir is LOCAL + accessible (agent-pipe co-located with the light
lane). Default-on but a true no-op without a local slots dir. Env:
MIOS_KV_GC / MIOS_KV_GC_INTERVAL_S / _TTL_S / _MAX_BYTES / MIOS_KV_SLOTS_DIR.

<!-- mios-src:73ec19ec2f3e from usr/share/mios/mios.toml:4107-4112 -->

### ── RR time-slice preemption (WS-A12) — bound how long one...

── RR time-slice preemption (WS-A12) — bound how long one dispatch holds a lane
before its quantum expires + it is snapshotted/requeued so the next waiter
runs. The policy/bookkeeping (mios_preempt) ships + is observable on
/v1/scheduler; the engine-side interruptible decode that ACTS on it is _rr_run()
in server.py -- a CHUNKED fan-out completion that snapshots the KV (/slots save)
+ yields the priority gate at a slice boundary, then re-acquires + restores so
the preempted generation resumes without reprocessing. DEFAULT-OFF (inert, zero
behaviour change until you opt in + load-test). Applies only to a llama.cpp
/slots lane on a no-tools fan-out dispatch (tool-loop preemption needs WS-A11).
Env: MIOS_RR_ENABLE / MIOS_RR_QUANTUM_S / MIOS_RR_MAX_SUSPENDED /
MIOS_RR_SLICE_TOKENS / MIOS_RR_SLICE_TIMEOUT_S.

<!-- mios-src:1a4cf66e5244 from usr/share/mios/mios.toml:4118-4128 -->

### ── WS-A13 risk-tier dispatch sandbox. The agent-pipe...

── WS-A13 risk-tier dispatch sandbox. The agent-pipe RESOLVES each verb's
permission tier -> a confinement profile (mios_sandbox, FAIL-CLOSED: unknown ->
strict) and RECORDS it on every dispatch result (audit; see /v1 result.sandbox).
When sandbox_enforce=true it also WRAPS the broker cmd of a verb that OPTS IN via
[verbs.<v>].sandbox_profile = "workspace"|"strict" through mios-sandbox-exec
(bwrap: ro-root + writable workspace + no-net unless the tier allows). OPT-IN +
DEFAULT-OFF so OS-control/launch verbs (which bwrap would break) are never
wrapped here; code-exec verbs already self-confine at mios-coderun. Env:
MIOS_SANDBOX_ENFORCE.

<!-- mios-src:1154268c57c6 from usr/share/mios/mios.toml:4134-4142 -->

### ── WS-8 computer-use perceive->act->verify loop (POST...

── WS-8 computer-use perceive->act->verify loop (POST /v1/computer-use). The
agent-pipe drives a closed VLM loop -- screenshot -> the VLM plans ONE action ->
dispatch the platform verb (windows_desktop_*/linux_desktop_*, unified by
mios_cua) -> screenshot -> the VLM verifies the goal -> repeat. FAIL-SAFE: an
unparseable verify is NOT-done, so the loop never claims a goal it didn't
verify. DEFAULT-OFF + VLM-gated (no [ai].chat_vision_model loaded -> honest
stop). Env: MIOS_CUA_ENABLE / MIOS_CUA_MAX_STEPS.

<!-- mios-src:847cbfb9555b from usr/share/mios/mios.toml:4144-4150 -->

### ── WS-A11/WS-3 kernel facade (Stage 2a). The decomposed...

── WS-A11/WS-3 kernel facade (Stage 2a). The decomposed Router/Dispatcher/Kernel
are instantiated + LIVE (introspect via /v1/scheduler.kernel + POST /v1/route);
the Dispatcher delegates the DAG mode to the real execute_dag. kernel_route on
=> a SHADOW classification is logged next to the live inline cascade so the
Router's decision can be verified for parity on real traffic BEFORE the Stage-2b
execution-body swap (which migrates the remaining mode bodies out of
chat_completions, VM-verified). Default-off => zero behaviour change (the live
path never calls dispatcher.run). Env: MIOS_KERNEL_ROUTE.

<!-- mios-src:3a51f9f3ae43 from usr/share/mios/mios.toml:4159-4166 -->

### ── WS-SCHED-SLO: give admission the ability to say "no"....

── WS-SCHED-SLO: give admission the ability to say "no". When on, a BEST_EFFORT
(low-priority / autonomous / fan-out) dispatch is SHED under capacity contention
OR when the host probe failed (fail-CLOSED -- inverts _admit's degrade-OPEN
hole); an INTERACTIVE foreground turn is NEVER shed. A shed fan-out node just
drops from the swarm merge (already tolerated). mios_slo owns the EDF
least-deadline-first ordering + the shed decision. Default-off => _admit never
sheds => byte-identical. Env: MIOS_SLO_SHED_ENABLE.

<!-- mios-src:841b78ab6cf8 from usr/share/mios/mios.toml:4168-4174 -->

### ── Batch coalescing (WS-A6). RESEARCHED...

── Batch coalescing (WS-A6). RESEARCHED: vLLM/SGLang/llama.cpp already do
server-side CONTINUOUS BATCHING (a rolling scheduler coalesces concurrent
requests optimally), so client-side coalescing BYPASSES those lanes (double-
batching only adds latency) and applies a short batch_interval window ONLY to
NON-native endpoints (a rate-limited remote core, added via WS-A16). With only
local lanes -- all native -- this is INERT. batch_native_hints = host:port
substrings that self-batch (the local lane ports). Env: MIOS_BATCH_*.
T-226: an httpx request hook on the one shared AsyncClient, registered
only when true. Manual ch59.

<!-- mios-src:b0a3a6e5f953 from usr/share/mios/mios.toml:4176-4184 -->

### ── Per-request trace/span observability (WS-A8). A...

── Per-request trace/span observability (WS-A8). A chat_completions request
mints (or adopts via the X-MiOS-Trace header) a trace_id; each pipeline stage
(route/plan/refine/dispatch) opens a child span, and finished spans land in a
BOUNDED in-memory ring buffer that backs GET /v1/trace/{trace_id} with no DB
hit + mirrors onto event rows (trace_id/span_id/parent_span_id). Cheap +
degrade-open. Read by the agent-pipe; env overrides MIOS_TRACE_ENABLE /
MIOS_TRACE_MAX_TRACES / MIOS_TRACE_MAX_SPANS_PER_TRACE.

<!-- mios-src:cf8fe3965950 from usr/share/mios/mios.toml:4189-4195 -->

### ── Concurrency / timeouts / per-lane trimming (agent-pipe...

── Concurrency / timeouts / per-lane trimming (agent-pipe env knobs; code
defaults shown, same ${MIOS_*:-default} pattern). "iGPU
fires WITH CPU ... any engine/node" + "add per-lane context trimming".
  MIOS_AGENT_LANE_CONCURRENCY        = 3   -- concurrent agents PER LANE. Each
      compute lane/engine/node (dGPU, CPU, iGPU, accelerator, each remote node)
      gets its OWN semaphore, so distinct hardware ALL fires concurrently; only
      agents SHARING one lane queue. Per-lane override
      MIOS_AGENT_LANE_CONCURRENCY_<LANE> (e.g. _GPU=2 to protect 4090 VRAM).
  MIOS_AGENT_HEALTHGATE_CONNECT_S    = 2.5 -- connect timeout for a health-gated
      (remote/slow) node -> an ABSENT node (phone asleep) drops fast.
  MIOS_AGENT_HEALTHGATE_READ_S       = 120 -- read timeout for a health-gated
      node -> a PRESENT-but-SLOW node (the iGPU, ~13 tok/s Vulkan) FINISHES
      instead of being abandoned mid-compute (was a flat 45s).
  MIOS_SLOW_LANES            = igpu,mobile,accelerator -- lanes that get a
      TRIMMED system prefix (slow prefill); gpu + cpu keep the full context.
  MIOS_SLOW_LANE_BLOCK_CHARS = 1500 -- per-block cap for a slow lane, so the
      ~7K web-research context doesn't blow its prefill (the gist survives).
MIOS_NODE_LIVENESS_TTL_S = 45 -- OUTAGE resilience (
      "iGPU is down"): TTL of the cached node-liveness probe. A health_gate
      client/Tailscale node (the iGPU :11436, a phone) that is DOWN is pruned
      from the swarm roster so the planner never assigns it a facet + any DAG
      facet already on a dead node RE-ROUTES to a live engine -- swarm width is
      preserved under an outage instead of a facet vanishing into a dead node.
      Only health_gate nodes are probed (local lanes are always treated live);
      a down node isn't re-probed every turn and rejoins within the TTL once
      back up. 0 effectively disables caching (probe every turn).
  MIOS_NODE_LIVENESS_CONNECT_S = 1.5 -- connect timeout of that liveness probe.

<!-- mios-src:6c33a8fed701 from usr/share/mios/mios.toml:4199-4225 -->

### ── CLOSED-LOOP + ACTION-VERIFY bounds (agent-pipe env...

── CLOSED-LOOP + ACTION-VERIFY bounds (agent-pipe env knobs; code defaults shown,
same ${MIOS_*:-default} pattern). "loop anything not
successful or fully fulfilled". All bounded + verdict-driven + degrade-open so a
robust turn never spins; they only re-engage on a CONFIRMED failure signal.
  MIOS_SECONDARY_REPLAN_MAX  = 1   -- supervisory re-engages in the shared
      tool-loop (_v1_secondary_tool_loop): when the model stops calling
      tools but a verb THIS loop ran reported a genuine FAILURE
      (_tmsgs_indicate_failure), re-engage once with a fix-it nudge.
  MIOS_DAG_REPLAN_MAX        = 1   -- multi-node DAG re-dispatch of UNFULFILLED
      facets in _synthesise; adopt-only-if-strictly-more-facets-satisfied.
  MIOS_TYPE_RETRY_MAX        = 2   -- per-action typing re-focus+re-type when
      pc_type's STRICT read-back reports the text did NOT land (compound chain).
  MIOS_DAEMON_DIAGNOSE       = 1   -- on a re-engage, a FRESH monitor-LLM pass
      (MIOS_DAEMON_DIAGNOSE_MODEL/_ENDPOINT) explains WHY the step failed +
      proposes a DIFFERENT action, injected into the retry nudge (guided retry).
  MIOS_KNOWLEDGE_STORE_GATE_UNSATISFIED = 1 -- skip persisting a turn's Q+A to the
      knowledge table when its satisfaction verdict is False (no recall poison;
      None still stores, degrade-open).
  MIOS_PC_INPUT_SECTION = "PC input" -- catalog section folded into the fire-one-
      verb fast-path set so a standalone "type X" dispatches pc_type (not the
      wrong-platform cu_type) and surfaces in the refine prompt.
  MIOS_LAST_WINDOW_CAP  = 256 -- bound on the per-CONVERSATION last-opened-window
      map that lets a standalone "type X into it" focus the right window first.

<!-- mios-src:3d6d64b4a05c from usr/share/mios/mios.toml:4227-4249 -->

### ── COUNCIL input-diversity gate (T-047 RouteMoA GAP-1) +...

── COUNCIL input-diversity gate (T-047 RouteMoA GAP-1) + confidence-aware
aggregation bypass (T-048 MOSAIC GAP-2). Both ride the council responses'
ALREADY-computed 768-d nomic embeddings (embedded ONCE, reused by both gates --
zero extra model calls, no per-pair calls). agent-pipe reads these via
_toml_section("council"); runtime override via the matching MIOS_COUNCIL_* env.
Both gates DEFAULT-OFF and degrade-open: OFF => the council synthesis path is
byte-identical to today (nothing is embedded, no gate runs).

<!-- mios-src:4f02f41b58d8 from usr/share/mios/mios.toml:4251-4257 -->

### diversity_gate

diversity_gate: before the aggregator, prune near-duplicate council responses to
a semantically diverse subset -- a lowest-mean-similarity seed then minimax-
orthogonal expansion; any input whose cosine similarity to the selected set
exceeds diversity_threshold is redundant and is replaced by the next most-
orthogonal candidate (dropped when even the most-orthogonal one is over threshold).
Kills the echo-chamber failure mode (a correlated ensemble degrades synthesis).

<!-- mios-src:35614d81a3da from usr/share/mios/mios.toml:4259-4264 -->

### ── WEB-RESEARCH loop bounds (SSOT'd). The pipeline's...

── WEB-RESEARCH loop bounds (SSOT'd). The pipeline's per-facet
web-research loop (search -> fetch/extract -> judge -> re-search) is the
dominant research-turn LATENCY driver. MODERATE-cut values (operator
live test: research turns exceeded 5.5min): fewer judge-gated
attempts + drill passes, and a much shorter crawl-fallback timeout (the deep
crawl is a fallback now that the miosfetch extract works). agent-pipe reads
these via _toml_section("web_research"); runtime override MIOS_WEB_RESEARCH_*.
(Only these 3 latency keys are SSOT-wired today; the rest of the web-research
knobs remain env-overridable -- a noted follow-up sweep.)

<!-- mios-src:a5c20bb4057f from usr/share/mios/mios.toml:4275-4283 -->

### SearXNG time_range applied to a model-classified...

SearXNG time_range applied to a model-classified time-sensitive turn (refine.news/needs_recency) when no explicit override; the broad degrade-open default that replaced the deleted English temporal-word gate. day|week|month|year

<!-- mios-src:46b2cf08e066 from usr/share/mios/mios.toml:4288-4288 -->

### ── 2-hop article-link "real-headline" scorer...

── 2-hop article-link "real-headline" scorer (mios_web_research._rank_links). ──
From an INDEX page the drill harvests outbound links + ranks the most ARTICLE-LIKE
by URL STRUCTURE ONLY -- NO hardcoded domain/keyword/topic list. The keys below are
that ranker's weights / length thresholds / drop cutoff / top-N; their values EQUAL
the in-code degrade-open defaults, so deleting this block leaves ranking byte-
identical. Read via _toml_section("web_research"); each key falls back independently.

<!-- mios-src:9a77d07518eb from usr/share/mios/mios.toml:4289-4294 -->

### ── Knowledge / tiered semantic memory (P2,) ──────────────...

── Knowledge / tiered semantic memory (P2,) ──────────────
The agent-pipe persists every finished Q+A to the pgvector `knowledge` table
+ recalls by embedding cosine. P2 added tiering: recall blends cosine with
outcome (was the prior turn satisfied), tier (hot/warm/cold), and access
frequency. Rank weights default near-zero -> recall == pure recency+cosine
until tuned. Read directly via _toml_section("knowledge") / _cfg_num.

<!-- mios-src:af4b587010d3 from usr/share/mios/mios.toml:4305-4310 -->

### ── WS-3 eviction (P2.1,). The knowledge table appends one...

── WS-3 eviction (P2.1,). The knowledge table appends one row per
finished turn -> unbounded. This bounded K-LRU + TTL sweep removes only STALE,
never-recalled, neutral-outcome rows; it NEVER deletes a hot / satisfied /
pinned row (mios-remember facts live in a SEPARATE store and are untouched).
ON by default ('everything on' for live MiOS-DEV). The
sweep DELETES only stale (>ttl) never-recalled neutral rows -- effectively a
no-op on a recent table until rows age past evict_ttl_days. To observe instead
of delete, set evict_enable=false + evict_dryrun=true (log-only). BACK UP the
knowledge table if it holds valuable rows older than evict_ttl_days.

<!-- mios-src:bbd0cff54280 from usr/share/mios/mios.toml:4321-4329 -->

### ── WS-MEM-02 Memory / Context threshold warning and...

── WS-MEM-02 Memory / Context threshold warning and eviction (P2,) ──
n_ctx is the total context window size in tokens.
At 70% of n_ctx, the system warns the agent about context usage.
At 100% of n_ctx, the oldest turns are evicted, summarized, and archived.

<!-- mios-src:2dde83d7ac65 from usr/share/mios/mios.toml:4348-4351 -->

### ── DCI (Deliberative Collective Intelligence) deliberation...

── DCI (Deliberative Collective Intelligence) deliberation flow. The agent-pipe
ALWAYS runs the cheap single-persona B.1 critic (post-dispatch audit trail of
typed epistemic acts). flow_enabled is the OPT-IN gate for the heavy 4-persona
convergent flow (DCI-CF): when on, a high-confidence Challenger objection from
the B.1 critic escalates to the full Framer/Explorer/Challenger/Integrator
deliberation, which can TAINT the session on unresolved dissent. DEFAULT-OFF
(brick-safe): deliberation changes council behaviour, so the operator opts in +
live-validates. Env override: MIOS_AGENT_PIPE_DCI_FLOW_ENABLED. Read by the
agent-pipe (mios_dci).

<!-- mios-src:79c10ec2ad40 from usr/share/mios/mios.toml:4385-4393 -->

### Anti-fabrication output figure-guard...

Anti-fabrication output figure-guard (mios_verity._strip_ungrounded_figures).
The guard splits an answer line into sentences so it can drop ONLY the sentence
that carries an ungrounded $-price / N%-percent figure. The splitter is
script-neutral (it breaks on unicode sentence terminators too -- 。！？ -- so a
CJK answer gets per-sentence granularity instead of all-or-nothing); the one
language-specific input is this list of ABBREVIATIONS whose trailing period must
NOT be read as a sentence end (else the grounded "$X USD)" conversion fragment
after "approx." / "U.S." gets split off and wrongly dropped). Sourced here so the
guard carries NO baked word list in code. Extend per locale. Read by the
agent-pipe via _toml_section("verity").

<!-- mios-src:f0e046fcf4e7 from usr/share/mios/mios.toml:4397-4406 -->

### Anti-fabricated-EXECUTION guard (operator's #1 value: NEVER...

Anti-fabricated-EXECUTION guard (operator's #1 value: NEVER claim a tool ran
when it did not). Master gate for the routing-layer guards that drop a chat/
synthesis reply narrating an unexecuted '🤝 <verb> output' / {"success":true,
"tool":...} block (chat.py short-circuit + native_loop.py unfired-verb strip).
Bridged to MIOS_ANTIFAB_ENABLE (read by mios_pipe.routing). Degrade-OPEN: set
false to restore the pre-guard passthrough behaviour.

<!-- mios-src:117ae8840837 from usr/share/mios/mios.toml:4412-4417 -->

### Anti-fabricated-CITATION (per-section grounding)...

Anti-fabricated-CITATION (per-section grounding) thresholds. A web/news answer
is split into sections; a section is dropped only when it carries at least
antifab_min_entities candidate entity tokens (proper nouns / years / domains --
structural, unicode-aware, no keyword list) AND its grounded fraction (entities
present in the actually-fetched source text) is below antifab_ground_min. Higher
min_entities = less aggressive (needs more signal before judging); higher
ground_min = stricter (demands more of a section be grounded). Bridged to
MIOS_ANTIFAB_MIN_ENTITIES / MIOS_ANTIFAB_GROUND_MIN. Degrade-OPEN on empty corpus
/ caseless script / too-few entities.

<!-- mios-src:48ae0f9c17a9 from usr/share/mios/mios.toml:4419-4427 -->

### ── WS-2 Code Mode. The agent writes CODE that calls a local...

── WS-2 Code Mode. The agent writes CODE that calls a local tool
API inside the rootless podman coderun-sandbox instead of loading ~71 function
schemas into context (the AIOS Tool-Manager token win). DEFAULT-OFF + degrade-
CLOSED: code execution only runs when enable=true AND the sandbox is present.
Read directly by the agent-pipe + mios-coderun-codemode via [code_mode].

<!-- mios-src:fb042013f068 from usr/share/mios/mios.toml:4431-4435 -->

### Phase D.5 quick-refine pass settings. ALWAYS runs before...

Phase D.5 quick-refine pass settings. ALWAYS runs before any
delegation. INPUT prompt-enhancement half of the "polish mechanism".
consolidation: refine + polish + plan all share
the ONE light MiOS brain (mios-agent, FROM qwen3.5:4b) instead of a
bare base model -- so prompt-enhancement carries the MiOS operating
principles + ENGLISH-default language, and the model count stays
minimal. dGPU lane (:11434); shares mios-hermes's base blob (no extra
resident weights).

<!-- mios-src:308689cf216b from usr/share/mios/mios.toml:4446-4453 -->

### Intent-routing length/word cutoffs. These feed BOTH the...

Intent-routing length/word cutoffs. These feed BOTH the post-classification
promotion guards AND the matching char cues embedded in the refine prompt --
the same number renders the cue and gates the decision, so they cannot drift.
  chat_chars      -- prompt cue only: chat is for very short conversational input.
  dispatch_chars  -- prompt cue only: dispatch is for short verb invocations.
  promote_chars   -- a chat/dispatch classification on a longer input is promoted
                     to `agent` (the worker/planner decomposes it); also a prompt cue.
  dispatch_arg_max_words -- a dispatch arg with more whitespace-tokens than this is
                     treated as a semantic phrase (not a concrete target) -> agent.

<!-- mios-src:b9862e04631d from usr/share/mios/mios.toml:4473-4481 -->

### Phase A.1 DAG-decomposition planner. Short-prompt skip: a...

Phase A.1 DAG-decomposition planner. Short-prompt skip: a prompt under BOTH
cutoffs (and not an action-domain command) almost always maps to a SINGLE
dispatch verb, not a multi-step DAG, so the planner is skipped and the chain
falls through to the single-dispatch path. Other planner tunables
(enabled/model/endpoint/timeout/max_tokens/max_nodes) ride the
MIOS_AGENT_PIPE_PLANNER_* env surface.

<!-- mios-src:4811d65b7f74 from usr/share/mios/mios.toml:4488-4493 -->

### Phase D.5 polish pass settings. Runs ONCE on the final...

Phase D.5 polish pass settings. Runs ONCE on the final answer before
returning to the gateway -- OUTPUT-shaping half of the "polish
mechanism": removes leakage, matches intended_outcome format, applies
the operator PERSONA + the ENGLISH-default language anchor (operator's
original message). Skipped for dispatch / chat / DAG fast paths (those
produce final-shape content already). shares the
ONE light MiOS brain (mios-agent, FROM qwen3.5:4b) with refine + plan
on the dGPU lane -- the final answer is shaped by the MiOS brain, not a
bare base model.

<!-- mios-src:658311e63850 from usr/share/mios/mios.toml:4498-4506 -->

### Phase C.3 of the AgentOS roadmap

Phase C.3 of the AgentOS roadmap: Agent Passports (signed
identity tokens). Every agent in the stack gets an Ed25519
keypair at provisioning -- agent-pipe, MiOS-Hermes, MiOS-
OpenCode, future MCP clients. Security-relevant pgvector
writes (tool_call, skill_invocation, firewall_block events)
carry a passport envelope that binds the signature to the
exact data via SHA-256(table || canonical-json(fields-minus-
passport)). Verification is OFFLINE: any agent reads the
public key from /var/lib/mios/agent-passports/<agent>/
public.key (world-readable) and validates without an external
KMS or CA. Private keys are 0600 owned by the agent's sysuser.

Agents the operator can register out-of-the-box (provisioning
is idempotent -- re-running just keeps existing keys). Add to
this list to enroll a new agent without code edits.

<!-- mios-src:4fceffdee83c from usr/share/mios/mios.toml:4515-4529 -->

### How many days before a key is auto-flagged for rotation by...

How many days before a key is auto-flagged for rotation by the
next provisioning run. 0 = never (operator triggers rotation
manually via `mios-passport rotate <agent>`).

<!-- mios-src:ee249918647f from usr/share/mios/mios.toml:4533-4535 -->

### Whether agent-pipe's read paths VERIFY passports when...

Whether agent-pipe's read paths VERIFY passports when surfacing
data to operators (slows reads but catches tamper attempts).
Default false in v1 -- writes are signed but reads are trust-
the-DB. Operator can flip to true for a hardened deployment.

<!-- mios-src:cd0c26f49c98 from usr/share/mios/mios.toml:4537-4540 -->

### [daemon] -- top-level mios-daemon autonomy / back-pressure...

----------------------------------------------------------------------------
[daemon] -- top-level mios-daemon autonomy / back-pressure governor (Wave 0).
Bare keys here MUST precede any [daemon.*] sub-table (TOML ordering). These
are PURE-PYTHON-READ knobs consumed by mios-daemon / mios-daemon-agent /
the cron-director via the agent-pipe _toml_section("daemon") helper -- they
need NO userenv.sh slot or 34-render-quadlets.sh allowlist entry.

Back-pressure GOVERNOR: when the box is hot (load or GPU util above the
ceilings below) the daemon's *autonomous* (self-initiated) work calms down
so it never starves an interactive turn. Degrade-open: pressure_skip=false
ships the governor in OBSERVE/ACTIVE mode but the ceilings are generous; set
pressure_skip=true to bypass the governor entirely (always run autonomous
work, legacy behaviour). A probe error never crashes the hot path -- on any
read/probe failure the daemon treats pressure as ABSENT (proceeds).
----------------------------------------------------------------------------

<!-- mios-src:8c9f9760f712 from usr/share/mios/mios.toml:4553-4567 -->

### De-dup window (seconds) for the daemon's micro-LLM "is this...

De-dup window (seconds) for the daemon's micro-LLM "is this worth acting on?"
classifier: an identical/near-identical trigger seen again within this window
is skipped instead of re-classified + re-acted. 600 = 10 min; stops a noisy
log line from spawning repeated autonomous runs.

<!-- mios-src:99fc8e3e4b59 from usr/share/mios/mios.toml:4583-4586 -->

### Launch-claim detector mode for the launch verifier. The...

Launch-claim detector mode for the launch verifier. The daemon scans recent
assistant messages for a CLAIM that it launched/opened/started an app or
installer (something to then verify on screen). "model" = the micro-LLM
classifies each assistant message and resolves the claimed target generically
(no keyword/app-name list); degrade-open when the lane is unreachable means
that turn's claim check is simply skipped (never fabricate a claim). "off" =
disable launch-claim verification entirely.

<!-- mios-src:eaacbe674d1a from usr/share/mios/mios.toml:4614-4620 -->

### Refusal/fabrication detection mode for the daemon's nudger....

Refusal/fabrication detection mode for the daemon's nudger. The daemon judges
whether a hermes-agent response is a REFUSAL / HEDGE / FABRICATION instead of
doing the user's work. "model" = the micro-LLM judges EVERY response (no
English refusal-phrase pre-filter decides whether to even check -- the judge
is authoritative); degrade-open when the judge lane is unreachable means that
turn's check is simply skipped (never fall back to a keyword list, never
fabricate a refusal verdict). "off" = disable refusal detection entirely.

<!-- mios-src:e67fcf0d898d from usr/share/mios/mios.toml:4622-4628 -->

### [budget] -- token / in-flight budget ceilings (Wave 0)....

----------------------------------------------------------------------------
[budget] -- token / in-flight budget ceilings (Wave 0). PURE-PYTHON-READ by
agent-pipe (_toml_section("budget")). Generous defaults so normal interactive
use is never throttled; these exist to bound RUNAWAY autonomous fan-out, not
to limit a human's conversation. Degrade-open: a turn that would exceed a
ceiling is trimmed/deferred, never hard-errored on the interactive path.
----------------------------------------------------------------------------

<!-- mios-src:4a0fc9375925 from usr/share/mios/mios.toml:4631-4637 -->

### [dispatch.autonomy] -- Wave-0 autonomous-dispatch knobs....

----------------------------------------------------------------------------
[dispatch.autonomy] -- Wave-0 autonomous-dispatch knobs. NOTE: the primary
[dispatch] table (council/fanout/rerank/...) lives earlier in this file; a
bare key cannot be appended after sub-tables, so these autonomy knobs live in
their own [dispatch.autonomy] sub-table. PURE-PYTHON-READ by agent-pipe
(_toml_section("dispatch.autonomy") / the dispatch loader). The task spec
named [dispatch].autonomous_priority + [dispatch].max_dispatch_depth; they
are scoped here as autonomy.* to keep the SSOT TOML-valid.
----------------------------------------------------------------------------

<!-- mios-src:72784a9cf83a from usr/share/mios/mios.toml:4655-4663 -->

### Scheduling priority class for AUTONOMOUS (self-initiated)...

Scheduling priority class for AUTONOMOUS (self-initiated) dispatches: "low"
(default) lets interactive turns jump ahead; "normal"/"high" raise it. Low
keeps unattended work out of the operator's way.

<!-- mios-src:fec08f8dc0fd from usr/share/mios/mios.toml:4665-4667 -->

### [daemon.post_check] -- per-verb visible-outcome...

----------------------------------------------------------------------------
[daemon.post_check] -- per-verb visible-outcome verification map.
The daemon's turn-satisfaction backstop AND-folds tool_call.success with a
per-verb "did the OS-side effect actually land" check (a broker can return
exit 0 after its sandbox died with the window never shown). This table is
SSOT for WHICH check applies to WHICH dispatched tool name; the check
IMPLEMENTATIONS live in mios-daemon, keyed by the signal name declared here.
An unlisted tool falls back to bare tool_call.success (no post-check).
Add a verb here (mapped to one of the implemented signals: window_visible /
file_exists / file_nonempty / flatpak_installed) to extend coverage without
touching code. Alias tool names that should share a verb's check are listed
explicitly (the recorded tool name, not the canonical verb).

<!-- mios-src:663e0d8d8222 from usr/share/mios/mios.toml:4674-4685 -->

### [daemon.index] -- directory-map indexer in mios-daemon....

----------------------------------------------------------------------------
[daemon.index] -- directory-map indexer in mios-daemon.
Walks the configured roots on `interval_min` cadence, upserts entries
into pgvector's directory_entry table. Agents query via the
`directory_lookup` verb (sub-100ms DB hit vs ~60ms+ live mios-find).
Each root has a label + filesystem path + optional include/exclude
globs. Summaries are extracted for text-shaped files (.md/.toml/
.yaml/.json/.txt) up to `summary_max_bytes`.
----------------------------------------------------------------------------

<!-- mios-src:c8f4f627e83e from usr/share/mios/mios.toml:4695-4703 -->

### [verbs.<name>] -- AGENT-PIPE VERB CATALOG (SSOT) Every verb...

============================================================================
[verbs.<name>] -- AGENT-PIPE VERB CATALOG (SSOT)

Every verb the planner can emit lives here. agent-pipe reads this block
at boot + RENDERS the planner's "Available verbs" catalog from it (no
more hand-typed English in _PLANNER_SYSTEM). Each verb declares:

  section     -- group heading in the catalog (string)
  sig         -- arg signature shown in catalog ("name, position?")
  desc        -- one-line description for the catalog
  tier        -- core | common | rare (drives progressive disclosure --
                 only `core` is loaded into the planner prompt by default
                 once tier-based gating ships)
  permission  -- read | write | interactive
  [verbs.<name>.params.<argname>]
    type     -- string | integer | boolean | array | object
    desc     -- argument description
    aliases  -- list of synonyms the planner LLM might emit instead of
                the canonical argname. Dispatcher accepts any.
    enum     -- (optional) closed set of allowed values
    default  -- (optional) default if omitted

Operator binding: "EVERYTHING SOURCED FROM THE MIOS.TOML/HTML" +
"NO HARDCODES ANYWHERE" -- new verb = one TOML block edit, no Python
touched (dispatch wiring in agent-pipe is a separate concern; this
block owns the LLM-facing surface).
============================================================================

<!-- mios-src:7c8f8eceec98 from usr/share/mios/mios.toml:4745-4771 -->

### ─── OS-control window-placement defaults (SSOT)...

─── OS-control window-placement defaults (SSOT) ──────────────────────
Where freshly-launched windows land + how mios-os-control / mios-launch
behave when a verb's `position` arg is "default". Every value is operator-
tunable here (and via the mios.toml -> userenv.sh slot); NOTHING in code
hardcodes a placement. Consumed by `mios-os-control window-defaults`, the
open_app/focus_window position resolver, and the launch preflight.

<!-- mios-src:441d2c8e38fd from usr/share/mios/mios.toml:4773-4778 -->

### Named half-screen snap regions (left-half / right-half /...

Named half-screen snap regions (left-half / right-half / top-half /
bottom-half) for move_window. Their rectangles are derived live from the
monitor work area by mios-window (no pixel constants). Degrade-open: the
actuator treats these names as enabled when this key is absent; set false to
restrict move_window to the historical region vocabulary.

<!-- mios-src:c1b39dfc680b from usr/share/mios/mios.toml:4784-4788 -->

### Resolution priority (best -> worst) when a launch name...

Resolution priority (best -> worst) when a launch name matches apps in MORE than
one category (mios-launch section-7 inventory fallback). SSOT for the launcher's
category ranking (formerly hardcoded in code; now tunable per the code's own TODO).
Default = Linux-native-first (the historical, proven-stable order).
NOTE: a Windows-host operator wants "open notepad" -> Windows
Notepad, which means moving the windows-* entries up. BUT do it carefully + verify
VISUALLY: the "windows-app" (Microsoft Store / AppX) inventory entries can be flaky
AutoGenerated GUIDs whose interop `Start-Process` HANGS. Prefer putting "windows-gui"
(routes via the in-session executor -- the path that launched Windows Notepad cleanly
in testing) AHEAD of "windows-app", e.g.:
  ["windows-gui", "linux-flatpak", "linux-rpm-gui", "linux-cli", "windows-app"]
Unknown categories sort last.

<!-- mios-src:3453e26aaad4 from usr/share/mios/mios.toml:4792-4803 -->

### Interactive-desktop OS-control executor for THIS host's own...

Interactive-desktop OS-control executor for THIS host's own windows
. When set, mios-pc-control routes window enumeration +
ops (list / close / focus / move / resize) to this URL instead of the
WSL-interop PowerShell path -- because PowerShell spawned through WSL interop
from a user-systemd service is NOT on WinSta0\Default, so EnumWindows is BLIND
(returns count:0) and close/focus can't find a real window. The executor
(usr/share/mios/windows/mios-oscontrol-server.ps1, a scheduled task running in
the interactive session on the Windows host) CAN enumerate + act, reached over
the tailnet. EMPTY in vendor (no personal tailnet IP in the public repo + the
blind interop path stays the default); set the real URL in your /etc/mios
overlay. Unreachable when set => honest error, never a blind fall-back.

<!-- mios-src:01aa4bd976cb from usr/share/mios/mios.toml:4806-4816 -->

### ─── OS-control NODES (4B: launch + verify on a SEPARATE...

─── OS-control NODES (4B: launch + verify on a SEPARATE machine's desktop) ──
"iGPU SHOULD FIRE MIOS OS CONTROL COMMANDS... across all
nodes". `launch_verified app=X node=<name>` makes the mios-daemon-agent fire
the launch to that node's mios-oscontrol-server (the Windows HttpListener
executor in usr/share/mios/windows/mios-oscontrol-server.ps1), which launches
on THAT node's OWN desktop + polls its window verifier and returns the verdict.
Default (no node) stays on THIS host via the broker.

PRIVACY / SSOT: the vendor file ships every `endpoint` EMPTY so no personal
device name / tailnet IP is baked into the public repo. Set the real tailnet
endpoint in your /etc/mios (or ~/.config/mios) overlay -- it merges + WINS over
this. An empty endpoint = inert node: launch_verified node=<that> returns an
honest "not configured" error, NEVER a fabricated success.

<!-- mios-src:398d460b67e3 from usr/share/mios/mios.toml:4819-4831 -->

### ─── Computer-use (Linux/Wayland desktop control)...

─── Computer-use (Linux/Wayland desktop control) ─────────────────────
The Linux/Wayland peer of the Windows pc-control lane. Drives THIS host's
graphical session via /usr/libexec/mios/mios-computer-use (RemoteDesktop
portal + Screenshot/ScreenCast portal + AT-SPI; self-written evdev/uinput
fallback -- NO ydotool/AGPL). The cu_* verbs dispatch to it, so they inherit
the three-projection surface automatically: MCP tool (/v1/verbs), OpenAI tool
(the agent loop), and A2A skill (the agent card).

ENVIRONMENT-ADAPTIVE (MiOS is ONE bootc image for any hardware): the executor
routes by environment -- a reachable executor_endpoint (federation: drive
ANOTHER machine's desktop) wins; else the local Wayland session; else WSL2
delegates to mios-pc-control. ONE verb surface for bare-metal GNOME, WSLg, and
remote nodes.

<!-- mios-src:502949e802c0 from usr/share/mios/mios.toml:4836-4848 -->

### ─── Doc-gen (WS-4 P0): FOSS offline document generation...

─── Doc-gen (WS-4 P0): FOSS offline document generation (Pandoc + LibreOffice) ──
Read by mios-docgen (usr/libexec/mios/mios-docgen) via this layered [computer_use]
section, overridable by MIOS_DOCGEN_* env. DEFAULT-OFF master gate: when
docgen_enable=false every mios-docgen subcommand returns {"ok":false,...} and
exits 0 (degrade-open). NO new daemon/quadlet -- the binaries run synchronously
through the operator broker like the other libexec tools. Needs LibreOffice +
Pandoc in the image ([packages.docgen]); a missing binary also degrades-open.

<!-- mios-src:b2687d12cba5 from usr/share/mios/mios.toml:4869-4875 -->

### ─── Computer-use NODES (drive a SEPARATE machine's...

─── Computer-use NODES (drive a SEPARATE machine's Linux/Wayland desktop) ──
Mirror of [os_control.nodes.*]: each entry is a remote desktop running
mios-computer-use-server, reached over the tailnet. ALSO register the node as
an MCP server (/etc/mios/ai/v1/mcp.json) + A2A peer (/etc/mios/ai/v1/
a2a-peers.json) so the agent-pipe CONSUMES it (full MCP + A2A). Vendor ships
every endpoint EMPTY (privacy/SSOT); set real URLs in the operator overlay.

<!-- mios-src:b7efdf2401f4 from usr/share/mios/mios.toml:4883-4888 -->

### Full-visibility debug surface (operator posture): stream...

Full-visibility debug surface (operator posture): stream internal reasoning,
thinking, tool calls + tool output/args, and status emits as VISIBLE content
to EVERY chat surface (OWUI / Discord / CLI). ON by design -- the operator
wants the whole pipeline observable live. Set false for a clean answer-only
reply (reasoning then rides delta.reasoning_content for OWUI's Thinking pane).

<!-- mios-src:677374e2a47e from usr/share/mios/mios.toml:4901-4905 -->

### ─── A2A fleet discovery (cross-node delegation)...

─── A2A fleet discovery (cross-node delegation) ──────────────────────
mios-a2a-discover probes these candidates + the local self for a live MiOS
AgentCard and writes the responders to /etc/mios/ai/v1/a2a-peers.json -- the
runtime peer list the agent-pipe delegates across when an AIOS-native agent
decomposes a multi-faceted request (see agent-contract.md "Decompose + span
the fleet"). Every MiOS node ships the A2A server, so a live card == a
delegable node. NO hardcoded endpoints: declare your fleet here (operator
overlay) or set a CIDR to auto-sweep. Tailscale is OFF by policy -> use
LAN/local IPs (172.x WSL gateway / 192.168.x), NOT tailnet (100.x).

<!-- mios-src:c1aa64101841 from usr/share/mios/mios.toml:4918-4926 -->

### FED-G7

FED-G7: route the concurrent fan-out on a federated peer's FULL published
AgentCard skills[] -- each skill's name/description/tags -- not just the collapsed
strength-token ids the peer registration keeps. When true, a discovered peer's
skills[] are attached to its synthetic registry entry and folded into the
model-driven relevance corpus (mios_fanout), and the routing decision is written
to the event table. Default false = selection is byte-identical to strength-token
routing (the published skill name/description/tags are ignored). env override:
MIOS_A2A_ROUTE_ON_CARD_SKILLS.

<!-- mios-src:612f06388de6 from usr/share/mios/mios.toml:4953-4960 -->

### ── mDNS / Avahi A2A LAN discovery (FED-G5) — find +...

── mDNS / Avahi A2A LAN discovery (FED-G5) — find + announce MiOS A2A peers on a
local segment with zero static config, complementing the explicit nodes /
discover_cidr lists above. Two independent, conservative-default-OFF halves
(usr/libexec/mios/mios-a2a-mdns), both degrade-open (no avahi / daemon down = inert):
  * mdns_discovery — browse mdns_service_type for peers; the resolved IP:port
    candidates are card-probed by mios-a2a-discover before any is trusted/written
    to a2a-peers.json, so a non-MiOS responder on the wire is never added blindly.
  * mdns_advertise — render usr/lib/mios/avahi/mios-a2a.service.in into
    /etc/avahi/services/ so avahi announces THIS node's A2A endpoint; toggling it
    off withdraws the file. The advertised port is the agent-pipe surface
    ([ports].agent_pipe), substituted from SSOT — never a code literal.
mdns_service_type is the ONE service-type SSOT both halves share. mdns_refresh_sec
is a FLOOR on live browses (a browse inside the window reuses the last result, so
discovery never loses peers); the mios-aios-refresh unit drives the actual cadence.

<!-- mios-src:fd07feb3d50c from usr/share/mios/mios.toml:4963-4976 -->

### MCP (Model Context Protocol) revision MiOS DECLARES as the...

MCP (Model Context Protocol) revision MiOS DECLARES as the latest it offers on the
`initialize` handshake. ONE SSOT read by BOTH the CONSUMER (agent-pipe
mios_mcp.MCP_PROTOCOL_VERSION) and the PUBLISH server (usr/libexec/mios/mios-mcp-server
PROTOCOL_VERSION); env MIOS_MCP_PROTOCOL_VERSION overrides. A protocol-revision token,
declared once here, never restated in code. Negotiation is back-compatible: a peer or
client on an older revision is accepted (liberal-in) while MiOS advertises the current
revision out (strict-out). Transport is Streamable HTTP (current) + stdio; the
deprecated HTTP+SSE transport is not used.

<!-- mios-src:603b4f8397eb from usr/share/mios/mios.toml:4983-4990 -->

### ─── Section: Window / app launch...

─── Section: Window / app launch ─────────────────────────────────────
============================================================================
[routing] -- 2-stage domain router (fix 82-tool mis-routing
WITHOUT english prose rules; per OpenAI/llama.cpp research). Stage-1 classifies
the query into ONE domain via a constrained enum (response_format json_schema,
thinking-OFF -- llama.cpp #20345); Stage-2 shows the planner ONLY that domain's
verbs (<20). FAIL-SAFE: unknown/empty/low-confidence -> FULL surface, so NO
capability is ever lost (swarm/council/DAG unchanged). SSOT for the taxonomy +
the per-domain "use-when" descriptions the Stage-1 classifier consumes. Every
verb is mapped exactly once; a verb absent here falls to the full surface.
kind=tool today; recipes/skills fold in as their own rows (research follow-up).

<!-- mios-src:3a65d5c1f950 from usr/share/mios/mios.toml:4993-5003 -->

### Leading determiners/possessives dropped from a...

Leading determiners/possessives dropped from a deterministic launch target so
"open the calculator" -> name="calculator", "open my settings" -> name="settings"
(e2e: "Open the Windows Calculator app on my desktop." fell
to the LLM router, which then chose hermes's built-in `terminal` tool -> exit
126, instead of open_app). SSOT (no hardcoded English in code); single words,
stripped from the START while the leading word matches.

<!-- mios-src:9a69372e04c6 from usr/share/mios/mios.toml:5017-5022 -->

### Deterministic PRE-ROUTE trigger phrases ("NO...

Deterministic PRE-ROUTE trigger phrases ("NO hardcodes!!!"):
these externalise the remember + web_search refine pre-router keywords that were
hardcoded English literals in code (server.py refine post-processing). SSOT data,
same pattern as the launch pre-router above. FAIL-SAFE: empty list -> that
deterministic route is OFF -> the model self-classifies (no capability lost).
remember: "<phrase> [that] <fact>" -> dispatch remember(fact) (catalog-guarded).

<!-- mios-src:07a1dcaa1bdf from usr/share/mios/mios.toml:5031-5036 -->

### location_sensitive

location_sensitive: a web research query carrying one of these phrases needs the
user's REAL resolved location spliced into the SEARCH STRING, else the engine
returns generic/foreign hits the model passes off as local (
Cobourg weather/local-news grounded to New York sources). This is the SSOT FALLBACK
behind the model-classified `needs_location` flag (refine) -- both feed the splice;
edit here, never hardcode in code. Empty = rely on the model flag alone.

<!-- mios-src:44e8dc47867f from usr/share/mios/mios.toml:5042-5047 -->

### browser_action

browser_action: a URL + a READ/browse verb -> force the CDP browse path (real DOM)
over the launch-only open_url fast-path. SSOT ("NOTHING
HARDCODED"): was a hardcoded regex in refine. EMPTY this list -> the force is skipped
and the model's own browser_action decision stands (degrade-open, fully generative).

<!-- mios-src:4dfea27a9c8b from usr/share/mios/mios.toml:5049-5052 -->

### compound-launch fast-lane vocab ("open X and type Y")...

compound-launch fast-lane vocab ("open X and type Y"): conjunctions joining the launch
to a follow-up action, and the action verbs. SSOT ("NOTHING
HARDCODED"). EMPTY either list -> the deterministic compound fast-lane declines and the
LLM planner decomposes the compound (degrade-open; the planner is the authority).

<!-- mios-src:381568402a64 from usr/share/mios/mios.toml:5054-5057 -->

### Conversational-bypass classifier for...

Conversational-bypass classifier for mios-delegation-prefilter: decides which
user turns are PURE chat (greeting / ack / smalltalk, no task surface) and must
SKIP the forced delegate_task tool_choice -- forcing it there yields a zero-token
reply. "model" = the micro-LLM ([ai].micro_model / micro_endpoint) classifies
chat-vs-act each turn (no English greeting list, no length cutoff); any other
value disables the classifier. Degrade-open: when the micro lane is unreachable
the prefilter force-delegates (the safe majority behaviour), never guessing chat
from keywords. prefilter_classify_timeout_s bounds that sub-second micro call.

<!-- mios-src:ccddf833e300 from usr/share/mios/mios.toml:5071-5078 -->

### Launch FOLLOW-UP / RETRY phrases (BUG B/C: the `mios`/`@`...

Launch FOLLOW-UP / RETRY phrases (BUG B/C: the `mios`/`@`
CLI deterministic launch route only matched the INITIAL "open/launch X"; a
follow-up like "epiphany didn't launch for me" or "attempt to launch and
verify" fell through to free-form Hermes which NARRATED advice + asked
permission instead of re-running the launch+verify path). These phrase lists
let the CLI recognise a launch follow-up and re-run the launch (now via the
VERIFY path) against the LAST-launched app it persisted with the session id.
SSOT (no hardcoded English in the .py/.sh); matched case-insensitively as
substrings. FAIL-SAFE: empty list -> that follow-up detection is OFF (no
capability lost; the turn just falls through to chat).

launch_followup_phrases -> a complaint/observation that the prior launch did
not work ("X didn't launch", "it didn't open", "nothing happened", "no
window"). Re-fires the launch+verify against the persisted last-launched app.

<!-- mios-src:49de156d0c04 from usr/share/mios/mios.toml:5082-5095 -->

### REAL file-search verbs lead (everything_search=Windows NTFS...

REAL file-search verbs lead (everything_search=Windows NTFS index, fs_search=Linux
plocate). mios_find was MISCATEGORISED here -- its own desc says it is NOT a file
search (it resolves an app NAME to a launch command), and leading the hint with it
made a live "find the mios.toml file on this system" answer a guessed path from
memory instead of searching; moved to apps_windows where app-resolution belongs.

<!-- mios-src:18d157abdcac from usr/share/mios/mios.toml:5126-5130 -->

### ─── Browser native launch flags (SSOT for mios-open-url...

─── Browser native launch flags (SSOT for mios-open-url tab/window control) ──
open_url opens a URL as a TAB in the ALREADY-RUNNING browser by default: the
browser BINARY invoked with the URL reuses its single instance (Firefox
remoting / Chromium ProcessSingleton / Epiphany GApplication) and opens a tab.
Launching a .lnk shortcut or a fresh sandbox instead spawns a NEW WINDOW
(upstream research). `family` maps the resolved browser app-id (case-insensitive
substring) to a flag family; `flags` maps mode -> the browser's native flag(s).
Unknown family -> no extra flag (degrade-open: most browsers tab-by-default).
NO-HARDCODE: the flags live here, never in the opener script.

<!-- mios-src:118bbc251060 from usr/share/mios/mios.toml:5457-5465 -->

### Recency / category levers ("research trending" gap): the...

Recency / category levers ("research trending" gap): the binary
already supports SearXNG --time-range + --category; exposing them as OPTIONAL nullable
params lets the MODEL request fresh/news results for time-sensitive asks. {arg?FLAG}
emits nothing when null -> default = today's untimed general search (zero regression).

<!-- mios-src:75d1ae32b31a from usr/share/mios/mios.toml:5662-5665 -->

### crawl engine (the unclecode/crawl4ai CONTAINER was SCRAPPED...

crawl engine (the unclecode/crawl4ai CONTAINER was
SCRAPPED -- a ~2GB image bundling its own Chromium. The crawl engine now
runs as a slim venv FastAPI service, mios-crawl4ai.service, exposed to all
agents as the `crawl` broker verb). Flow:
  PRIMARY    crawl4ai ATTACHES to the EXISTING local Chrome over the
             DevTools Protocol (ws://127.0.0.1:9222, the ChromeDev flatpak
             that mios-hermes-browser.service keeps up) via
             BrowserConfig(browser_mode="custom", cdp_url=...). No bundled
             browser, `crawl4ai-setup` is NEVER run.
  FAIL-RETRY when the CDP crawl errors / is blocked / returns near-empty
             markdown, the same url is retried with Camoufox (stealth
             anti-detect Firefox; ships its own ~150MB patched Firefox).
Default markdown generator only -- NO LLM extraction strategy, so no
provider key (Architectural Law 5: a local browser is not a vendor cloud
AI). The `crawl` verb backend (mios-crawl) POSTs to the loopback service so
the slow crawl4ai/camoufox import is paid ONCE at startup, not per call.
mios-crawl + the service read these from env (same ${MIOS_*:-default}
pattern as the rest of the file):
  MIOS_PORT_CRAWL4AI       = 11235                 -- loopback service port
  MIOS_CRAWL_SERVICE_URL   = http://127.0.0.1:11235 -- mios-crawl -> service
  MIOS_CRAWL_CDP_URL       = ws://127.0.0.1:9222   -- Chrome DevTools endpoint
                                                      crawl4ai attaches to
  MIOS_CRAWL_CAMOUFOX      = true   -- enable the Camoufox fail-retry engine
  MIOS_CRAWL_MIN_CHARS     = 200    -- markdown shorter than this from the
                                      CDP path triggers the Camoufox retry
  MIOS_CRAWL_BIND          = 127.0.0.1 -- service bind (LOOPBACK only; the
                                      crawl engine is never LAN-exposed)
Web fan-out + load tunables ("shoot off more web
queries concurrently ... SearXNG setup to handle the load"). web_search
expands one query into `fanout` diverse sub-queries via a WARM expansion
model, queries the LOCAL SearXNG CONCURRENTLY, and merges with Reciprocal Rank
Fusion + URL dedupe. agent-pipe (server.py) + mios-web-search read these from
env (code defaults shown, same ${MIOS_*:-default} pattern as the rest of the
file); the SearXNG granian worker pool in
etc/containers/systemd/mios-searxng.container is sized to absorb
MIOS_WEB_CONCURRENCY * MIOS_WEB_FANOUT concurrent /search requests:
  MIOS_WEB_FANOUT            = 2    -- sub-queries per web_search call (was 3:
                                      a bigger burst rate-limited the free
engines -> junk fallbacks,)
  MIOS_WEB_FANOUT_WORKERS    = 4    -- concurrent sub-queries within one call
  MIOS_WEB_CONCURRENCY       = 3    -- concurrent web_search calls (all agents)
  MIOS_WEB_DISPATCH_JITTER_S = 0.15 -- pre-acquire stagger (s) for simul starts
  MIOS_WEB_RRF_K             = 60   -- Reciprocal Rank Fusion constant
  MIOS_WEB_EXPAND_MODEL      = qwen3:1.7b              -- the query-expansion
  MIOS_WEB_EXPAND_ENDPOINT   = http://localhost:11435    model + endpoint.
the old micro (qwen3:0.6b-cpu @ :11434) was loaded
    NOWHERE -- cold -- so expansion blew its 6 s budget and SILENTLY fell back
    to ONE query (fan-out dead, "no multiple passes/queries"). Default now to
    the model the mios-daemon pins ALWAYS-WARM on the CPU lane (qwen3:1.7b @
    :11435, keep_alive=-1): sub-second, never cold-fails, more capable.
PIPELINE-SIDE WEB-RESEARCH LOOP ("the MiOS pipeline ITSELF
loops for web use and web tools" + "multi loops for all web tools" + "use
searxng too" + "no use from any agent"): for a web-needing turn agent-pipe runs
the chain ITSELF -- SearXNG web_search (fan-out -> multiple queries) THEN
web_extract the top pages for REAL article text -- and grounds EVERY agent
(primary + reasoning-only secondaries) on it, so the swarm answers from actual
stories not homepage snippets. Gated on the refine web-hint (no over-fire):
  MIOS_WEB_RESEARCH_ENABLED     = true
  MIOS_WEB_RESEARCH_PASSES      = 2     -- fetch-drill passes over the results
  MIOS_WEB_RESEARCH_RESULTS     = 6     -- search results considered
  MIOS_WEB_RESEARCH_FETCH_N     = 3     -- pages fetched per pass (web_extract)
  MIOS_WEB_RESEARCH_FETCH_CHARS = 3000  -- chars pulled per page
  MIOS_WEB_RESEARCH_BLOCK_CHARS = 1200  -- chars injected per source
  MIOS_WEB_RESEARCH_CRAWL_FALLBACK = true -- escalate a THIN extract (a JS /
      protected page) to mios-crawl (crawl4ai+CDP / Camoufox, the web-tools
      pod) so the DEEP web tool fires too, not just search+extract.
      MIOS_WEB_RESEARCH_MIN_CHARS (300) = thin threshold; _CRAWL_TIMEOUT_S (25).
Knowledge storage ("...present to user as final answer
and STORE all gained knowledge in all relevant global databases"). agent-pipe
persists each finished Q+A -- with the turn's derived sources (verbs invoked +
URLs touched) -- to pgvector fire-and-forget AFTER polish, so a write never
delays or breaks the streamed answer. Read from env (same ${MIOS_*:-default}):
  MIOS_KNOWLEDGE_STORE       = true      -- set false to disable persistence
  MIOS_KNOWLEDGE_TABLE       = knowledge -- pgvector table for stored answers
  MIOS_KNOWLEDGE_ANSWER_MAX  = 8000      -- max chars of the answer persisted
RECALL (read the store back): the query is embedded at WRITE time (nomic-embed
via the verb tool-search infra), so recall is a cheap cosine over recent rows,
threshold-gated so only relevant prior answers inject into the agent context:
  MIOS_KNOWLEDGE_RECALL            = true -- set false to disable recall
  MIOS_KNOWLEDGE_RECALL_K          = 3    -- max prior answers injected
  MIOS_KNOWLEDGE_RECALL_CANDIDATES = 60   -- recent rows scored per query
  MIOS_KNOWLEDGE_RECALL_MIN_SCORE  = 0.62 -- cosine floor to inject a hit
Dispatch dedup ("dont fire amongst the swarm multiple
times"). agent-pipe collapses CONCURRENT identical (verb, resolved-args)
dispatches within ONE conversation into a single launcher-broker execution
and shares the result -- the agentic-OS single-flight / idempotency pattern,
keyed on the structural _action_hash (no hardcoded English) + the conversation
contextvar. In-flight ONLY, so legitimate sequential repeats still run. Read
from env (same ${MIOS_*:-default} pattern):
  MIOS_DISPATCH_DEDUP        = true -- set false to disable single-flight dedup

<!-- mios-src:d279f4a65b10 from usr/share/mios/mios.toml:5710-5799 -->

### UIA semantic targeting

UIA semantic targeting: find/click a Windows control BY NAME
via UI Automation (mios-oscontrol-server /ui/find + /ui/click) instead of pixels --
the #1 Windows GUI gap (Linux had AT-SPI; Windows was coordinate-only). Routed via
mios-pc-control ui-find/ui-click to the in-session executor (foreground-window-scoped).

<!-- mios-src:1d0040840acb from usr/share/mios/mios.toml:5888-5891 -->

### ─── Section: Computer-use (Linux/Wayland desktop)...

─── Section: Computer-use (Linux/Wayland desktop) ────────────────────
Cross-platform desktop control via mios-computer-use (env-adaptive: bare-metal
GNOME/KDE Wayland, WSLg, or a federated remote desktop). AT-SPI-first grounding
(cu_ground / cu_atspi_query) avoids pixels; cu_screenshot + cu_ground feed the
click loop. Auto-projects to MCP (/v1/verbs) + A2A skills via _VERB_CATALOG.
Read-class (screenshot/window-list/atspi/ground) vs write-class (click/type/key).

<!-- mios-src:5d52b63ddec5 from usr/share/mios/mios.toml:5954-5959 -->

### ─── Section: Package management...

─── Section: Package management ──────────────────────────────────────
Unified verb: dispatcher routes by (action, backend) to the underlying
winget / flatpak shim. Backend "auto" picks winget for Windows-installed
targets, flatpak for Linux GUI apps. Operator binding
"compact, minimal, efficient -- consolidate redundant".

<!-- mios-src:93561025337d from usr/share/mios/mios.toml:6187-6191 -->

### tier=common (P0): a write/install op, less frequent than...

tier=common (P0): a write/install op, less frequent than the
mios_apps read inventory. Kept OUT of the always-visible stable core so it no longer
sits beside mios_apps and makes the 8B flip-flop on "what apps do I have"; it surfaces
via the per-turn cosine TAIL when a query is actually package-y (install/search pkg).

<!-- mios-src:6c0ce72fa993 from usr/share/mios/mios.toml:6198-6201 -->

### Logs are bulky

Logs are bulky: a DEFAULT 50-line slice of a busy unit (e.g. mios-open-webui)
measures ~10 KB, but without an explicit cap this verb inherits the global
READ_TOOL_ENRICH_CHARS default (1500) and gets head-tail-truncated to ~19% of
what the model asked for. 12000 fits the worst-case default-50 slice whole
while still bounding a pathological large-`lines` request. (Siblings
system_status / service_status / process_list set their own caps similarly.)

<!-- mios-src:d11a75bfb700 from usr/share/mios/mios.toml:6431-6436 -->

### disk-usage is NOT a verb -- it's a [recipes.disk-usage]...

disk-usage is NOT a verb -- it's a [recipes.disk-usage] recipe (the
df/du command lives in the recipe SSOT below, not hardcoded in
agent-pipe's dispatch). Run it via os_recipe(name="disk-usage").
Operator binding "NO hardcodes... should all be native
OpenAI tools/skills/recipes ... unless baked in the modelfile or docs".

<!-- mios-src:735d6455edd6 from usr/share/mios/mios.toml:6499-6503 -->

### COMMON tier (REVERTED from a brief 'core' experiment): the...

COMMON tier (REVERTED from a brief 'core' experiment): the math
path does NOT need coderun on the model's surface -- the native-loop COMPUTE PREFETCH
runs it PIPE-SIDE (a generative _needs_compute judge -> dispatch_mios_verb -> inject the
verified result), so the model gets correct math WITHOUT seeing coderun. Making it 'core'
(always-ambient) caused a small 8B to SPURIOUSLY fire run_sandboxed_code on non-compute
turns -- esp. in the client-tools merged surface (Hermes desktop), spinning the loop on
MiOS verbs and returning EMPTY. Keep it 'common' (reaches the model only when the turn is
genuinely code-relevant via the cosine tail / a code domain); the prefetch covers math.

<!-- mios-src:390f3363b613 from usr/share/mios/mios.toml:6648-6655 -->

### ─── Section: Doc-gen (WS-4 P0; FOSS offline Pandoc +...

─── Section: Doc-gen (WS-4 P0; FOSS offline Pandoc + LibreOffice) ─────
Author/convert office artifacts WITHOUT a GUI -- the computer-use "Worker"
that PRODUCES files (the LiteCUA Worker role) vs the cu_* verbs that DRIVE the
desktop. Backed by mios-docgen; gated by [computer_use].docgen_enable (default
off -> verbs visible but inert/degrade-open). permission=write (writes a file).

<!-- mios-src:77ee42d5195e from usr/share/mios/mios.toml:6978-6982 -->

### [owui.system_prompt] -- MiOS-Agent (MiOS AI) system prompt....

----------------------------------------------------------------------------
[owui.system_prompt] -- MiOS-Agent (MiOS AI) system prompt.
Concise SYSTEM MAP + PURPOSE in `template`; operator-overridable
`user_section_path` for personal addenda the installer appends at
the bottom. Operator binding "OWUI'S MiOS-Agent's SYSTEM
PROMPT SHOULD BE A CONCISE SYSTEM MAP/PURPOSE AND A USER DEFINED
SECTION TOO--VERY CONCISE AND EFFICIENT".

SSOT here -- mios-owui-install-pipe reads this block; no English
paragraph is hardcoded in Python anymore.
----------------------------------------------------------------------------

<!-- mios-src:166bac873388 from usr/share/mios/mios.toml:7043-7053 -->

### Path to an operator-editable markdown file the installer...

Path to an operator-editable markdown file the installer reads + appends
under "## OPERATOR PROFILE" if the file exists. Empty / missing file = no
user section.

<!-- mios-src:96ab6e7ae36d from usr/share/mios/mios.toml:7055-7057 -->

### Concise system map. Token-efficient -- the deeper operating...

Concise system map. Token-efficient -- the deeper operating manual lives
in /usr/share/mios/ai/hermes-soul.md inside Hermes; OWUI's MiOS-Agent is
just the front door. Edit this block in mios.toml + re-run
mios-owui-install-pipe to push.
The template may use Open WebUI's system-prompt variables. OWUI
substitutes most of them server-side (apply_system_prompt_to_body ->
prompt_template) BEFORE the pipe runs: {{USER_NAME}} {{USER_EMAIL}}
{{USER_LOCATION}} {{CURRENT_DATE}} {{CURRENT_DATETIME}} {{CURRENT_TIME}}
{{CURRENT_WEEKDAY}} {{USER_GROUPS}}. But {{USER_LANGUAGE}} and
{{CURRENT_TIMEZONE}} are FRONTEND-only variables -- they resolve ONLY
when the browser sends them in form_data['variables'] (verified against
OWUI utils/task.py: prompt_template has no case for either). To stop
either leaking as a literal token, the pipe (_resolve_env_vars) backfills
any unresolved {{...}} from the host clock + __user__ + metadata.variables
and then STRIPS whatever it cannot resolve. {{USER_LOCATION}} needs HTTPS
+ Settings>Interface>"location access"; absent it OWUI renders "None"/
"Unknown" -- the wording above treats those as not-provided. CRITICAL
the browser locale ({{USER_LANGUAGE}}) is NOT the
reply-language directive -- pinning replies to it while the operator wrote
in another language was the dual-language bug. Reply language now mirrors
the operator's own input only; the locale vars drive formatting/units.
The PERSONA line is composed per-user by the pipe from its UserValves
(operator-set fields in the OWUI UI); empty fields drop out cleanly.

<!-- mios-src:72f8f095de26 from usr/share/mios/mios.toml:7060-7082 -->

### [recipes.<name>] -- OS-shell RECIPES. Each recipe is a...

----------------------------------------------------------------------------
[recipes.<name>] -- OS-shell RECIPES. Each recipe is a templated
command sequence the agent can compose with operator-supplied params,
dispatched by `mios-os-recipe <name> key=val key=val...` (or the
`os_recipe` verb). The recipe declares per-OS templates (linux /
windows) so the SAME named recipe works in both shells -- agent picks
OS-aware behaviour without an `if uname...` block in code.

HARDENING:
  * Only recipes declared in this table are runnable -- the dispatcher
    refuses unknown names (no arbitrary shell pass-through).
  * Only `args` keys are accepted from the caller; unknown kwargs are
    dropped before template expansion.
  * Every {placeholder} substitution is shell-quoted (shlex on Linux,
    wsh-quote on Windows) -- no command injection via params.
  * `permission` = "read" (default, runs as agent) | "write" (needs
    MIOS_OS_RECIPE_WRITE=1) | "interactive" (operator confirmation).
  * `wsl_paths` lists arg names whose values get converted via
    wslpath when the chosen template is `windows` (Linux path ->
    Windows path so File Explorer / Notepad / etc. accept them).

Operator binding "mios-os-control should have more OS
Specific Shell controls/Commands for BOTH Linux + Windows + part of
launch params tools/skills" + "RECIPES" + "NO HARDCODES ANYWHERE".
SSOT here; mios-os-recipe is the generic executor.
----------------------------------------------------------------------------
Windows templates use ABSOLUTE PATHS. The MiOS WSL distro sets
`appendWindowsPath=false` in /etc/wsl.conf (operator preference: keep
the Linux PATH clean of Windows-side binaries), so bare `explorer.exe`
/ `powershell.exe` don't resolve via PATH lookup. WSL's binfmt_misc
still handles .exe execution when the FULL PATH is given -- so
templates name the binary explicitly. Operator-confirmed.

<!-- mios-src:46d5c067ed72 from usr/share/mios/mios.toml:7128-7159 -->

### Phase C.2 of the AgentOS roadmap

Phase C.2 of the AgentOS roadmap: Sequential Pattern Mining + the
cross-agent skill catalog. The miner (mios-skills mine) scans
the pgvector tool_call history for repeating (tool, args-shape)
N-grams and emits skill rows tagged status=candidate. Promoted
skills become first-class verbs every agent in the stack (agent-
pipe, MiOS-Hermes, MiOS-OpenCode) can invoke by name via the
shared pgvector row + agent-pipe's /skills/* REST surface.

All knobs SSOT-routed through userenv.sh + the configurator HTML.
Operator can tighten or loosen mining behaviour without touching
Python -- tools/skills are "global templates that can be self-
improved upon".

<!-- mios-src:841bf774481a from usr/share/mios/mios.toml:7289-7300 -->

### Lookback window (hours) for the miner. Skills age out of...

Lookback window (hours) for the miner. Skills age out of the
candidate pool when their last occurrence falls outside this
window. 168h = 1 week of operator behaviour.

<!-- mios-src:34f4961b3b31 from usr/share/mios/mios.toml:7313-7315 -->

### Auto-promote a candidate when confidence (support /...

Auto-promote a candidate when confidence (support / unique-session
count) crosses this threshold. Below the threshold, candidates
wait for explicit `mios-skills promote <name>` from the operator
OR via the configurator HTML. 0.0 = manual-only.

<!-- mios-src:eb7ad0ed0155 from usr/share/mios/mios.toml:7317-7320 -->

### How often the background miner runs (minutes). The...

How often the background miner runs (minutes). The mios-skills-
miner systemd timer reads this. 0 = disabled (operator runs miner
on-demand via `mios-skills mine`).

<!-- mios-src:2caacca7ef7f from usr/share/mios/mios.toml:7322-7324 -->

### Where /usr/share/mios/skills/ template skills live -- the...

Where /usr/share/mios/skills/ template skills live -- the seed
library the configurator HTML lists in the "Import" picker.
These are shipped with the bootc image (read-only); operator-
authored skills land in /var/lib/mios/skills/ (mutable).

<!-- mios-src:fb51891b3152 from usr/share/mios/mios.toml:7326-7329 -->

### T-049 (GAP-3) -- the HARD pass^k skill-promotion gate....

T-049 (GAP-3) -- the HARD pass^k skill-promotion gate. Promoting a skill
MUTATES the runnable surface every agent in the stack shares, so the DGM /
tau-bench lesson applies: a candidate must PROVE reliability, not merely have
passed once. When the gate is ON, `mios-skills promote <name>` REPLAYS the
skill through the same /skills/run firewall+taint+audit chokepoint
pass_and_k_count times (a DGM-class self-rewrite, run with `--dgm`, uses the
stricter pass_and_k_dgm_count) and flips status to promoted ONLY IF EVERY replay
succeeds -- success = the run succeeded AND no firewall_block fired AND no HITL
escalation. ONE failure vetoes ("pass^k gate: FAIL (n/k succeeded, required
k/k)"). pass^k is tau-bench's worst-case reliability metric ("ALL k repeats must
succeed") -- the SAME metric [selfimprove].passhat_k scores proposals against.

gate_enabled defaults OFF so an env without a reachable agent-pipe promotes
exactly as before (degrade-open: without this block the code is byte-identical
to legacy promote). When ON the gate is FAIL-CLOSED -- an unreachable/erroring
replay counts as a failed replay, because a promotion must be PROVEN, not
assumed. mios-bench also reports a suite-wide pass^k_rate column (the fraction of
eval tasks that would clear this all-or-nothing gate). SSOT-routed to
MIOS_RELIABILITY_* via userenv.sh; the code's numeric fallbacks mirror these.

<!-- mios-src:ec7477b0194b from usr/share/mios/mios.toml:7340-7358 -->

### ─── mios-frontier / A2O war-room roles ─── SSOT for the...

─── mios-frontier / A2O war-room roles ─── SSOT for the tmux war-room composition.
Bridged to MIOS_A2O_* env for the mios-agents container via the service ExecStart
passthrough (install.env overrides). Empty/unset -> the mios-a2o harness's
documented baseline, which EQUALS these values -> the war-room works out-of-box;
edit here to retune. NO-HARDCODE: operator-tunable role composition + effort.

<!-- mios-src:787a04a8bf35 from usr/share/mios/mios.toml:7363-7367 -->

### Lane B degrade-open FALLBACK. The real Lane B engine is agy...

Lane B degrade-open FALLBACK. The real Lane B engine is agy (Gemini); when that
account is quota-blocked (429 RESOURCE_EXHAUSTED) agy generation returns empty and
finalize work stalls. These keys let Lane B fall back to a Claude engine so the
last ~20% never dead-ends. prefer_fallback is the switch: ON => Lane B routes to
the fallback engine/model/effort below instead of the agy ones; OFF => Lane B uses
agy as normal. Unknown/empty fallback keys degrade-open to today's agy behaviour.

<!-- mios-src:e8770d852c04 from usr/share/mios/mios.toml:7388-7393 -->

### Per-engine reasoning-effort flag TEMPLATE ({e} -> effort...

Per-engine reasoning-effort flag TEMPLATE ({e} -> effort value). Empty = omit
(degrade-open: never break a CLI whose effort flag is unverified). claude is
CONFIRMED in-container: `--effort {e}`, levels low|medium|high|xhigh|max. agy and
gemini have NO confirmed effort flag -> left empty so their CLIs are never broken.

<!-- mios-src:decf4d668a2d from usr/share/mios/mios.toml:7400-7403 -->

### Stream the war-room's per-task activity to the MiOS...

Stream the war-room's per-task activity to the MiOS reasoning channel so
OWUI/CLI/Discord can watch the frontier without `tmux attach` ("everything
streams"). OFF by default: when on, mios-a2o appends each task's start/finish
transitions to the frontier sibling of the hermes-tail file (stream_path), and
the agent-pipe folds them into the same mios_status reasoning-channel emission
it already publishes. Degrade-open: a target that can't be written never fails a
dispatch; when off, the file is never created and the pipe path is byte-identical.

<!-- mios-src:db2c1dfd9f0c from usr/share/mios/mios.toml:7407-7413 -->

### Frontier activity sink -- JSONL under a dedicated...

Frontier activity sink -- JSONL under a dedicated group-writable child of the
hermes-tail transport dir the front-ends already read. Its own dir (not the
hermes-tail root) because the WRITER is the mios-agents container (host uid 1000)
and the READER is mios-agent-pipe (mios-ai): the dir is owned uid 1000 + group
mios-ai + setgid (see usr/lib/tmpfiles.d/mios.conf) so the container can create
the file AND its trim .tmp sibling while mios-ai still reads every line. The
war-room re-anchors this host-absolute path under MIOS_A2O_WORK when it runs
inside the container (host / mounted there).

<!-- mios-src:50063263f43d from usr/share/mios/mios.toml:7415-7422 -->

### 'MiOS' standalone Agent Pipe -- the router / refine /...

'MiOS' standalone Agent Pipe -- the router / refine / critic chain
extracted out of the OWUI pipe class into a gateway-agnostic FastAPI
service. Every gateway (OWUI, Hermes Discord, future Slack/Telegram/
MCP) points at this service for chat completions; it routes the
request through the full agentic chain and forwards the heavy
inference to Hermes-Agent at [hermes].endpoint.

Architecture per operator directive "mios discord chats
not going through MiOS-Agent(OWUI) paths when contacting through
discord (uses only MiOS-Hermes and doesn't have the same tool
understanding and environments details now!!!!)" -- centralizing the
pipe so all gateways get the same tool surface + critic + pgvector
state writes.

<!-- mios-src:89fc4a503142 from usr/share/mios/mios.toml:7434-7446 -->

### Client-side tool-calling PASSTHROUGH (Zen browser...

Client-side tool-calling PASSTHROUGH (Zen browser smart-window).
When an external OpenAI client supplies its OWN tools[] (browser/IDE assistants that
EXECUTE the tools themselves and expect tool_calls back), agent-pipe bypasses the
server-side orchestrator and relays the request verbatim to a tool-capable backend,
returning tool_calls unmodified -- the structural twin of the vision bypass. A2A and
Agent Passports are the wrong tool for this (researched). DEDICATED backend
knobs (NOT backend/backend_model above) so the relay never inherits model-drift.
Default granite4.1:8b on the keyless mios-llm-light (${MIOS_PORT_LLM_LIGHT}) lane (verified to emit
tool_calls); repoint tool_backend->:11441 + tool_backend_model->mios-heavy for harder
multi-tool routing. ingress_key (optional, empty=off) gates the route with a static
bearer a browser CAN send -- passports can't gate Zen (it's keyless).

<!-- mios-src:bfb71b580b5d from usr/share/mios/mios.toml:7451-7461 -->

### WS-9c cutover backend

WS-9c cutover backend: "dual" (write BOTH, read the legacy DB --
exercises PG live without risking reads) | "postgres" (PG primary
+ native <=> recall). FLIPPED to "postgres" (WS-9c cutover: agent-pipe
+ mios-remember/skills/daemon/kg all read+write pgvector; mechanism verified live,
a chat ran pg-primary). Set back to "dual" to re-enable the dual-write safety net
during a soak. Minor deferred read paths (eviction/hitl-edge/miner-SPM/daemon
batch+async/person-owns) degrade gracefully until finished.

<!-- mios-src:ea5688f5016e from usr/share/mios/mios.toml:7482-7488 -->

### 59 WS-5 row-level security mode for owner-scoped memory...

#59 WS-5 row-level security mode for owner-scoped memory recall.
  off    (default) -- tag-only: rows carry owner_user but recall does NOT filter
                      by owner (single-user behaviour; zero change).
  enforce          -- WIRED: knowledge recall returns only rows owned by the
                      requesting principal, PLUS legacy/shared rows (owner_user
                      IS NULL) so flipping it on never blanks the existing
                      single-user base. Scopes the knowledge (RAG) store today;
                      extending owner-scoping to agent_memory/scratch (both
                      default-off recall paths) is incremental WS-5 hardening.
                      Safe to leave off for single-user; flip on for multi-user.

<!-- mios-src:4bedcd12499e from usr/share/mios/mios.toml:7490-7499 -->

### T-068 DB-side native Postgres Row-Level-Security...

T-068 DB-side native Postgres Row-Level-Security ENFORCEMENT (defense-in-depth,
DISTINCT from rls_mode above). rls_mode is the APP-SIDE recall WHERE-filter;
rls_enable controls whether the agent-pipe (mios_pg) + the confined mios-pg-query
CLI emit a per-request `SET LOCAL mios.owner_user = <verified-principal>` (owner
bound as a PARAMETER, never spliced) so the schema-init.sql RLS policies enforce
owner isolation IN THE DATABASE -- a caller sees only its OWN rows + shared
(owner_user IS NULL) rows even if the app-side filter is bypassed.

REQUIRES [security].principal_bind_mode = "enforce" FOR REAL ISOLATION. The owner
fed to the GUC derives from the forwarded body/header `user`, which a direct caller
can SPOOF; only enforce mode reconciles it against the authenticated caller-key's
bound account. So the agent-pipe emits SET LOCAL ONLY when rls_enable is on AND
principal_bind_mode = enforce -- with rls_enable on but bind-mode off/verify the
owner is UNVERIFIED, so NOTHING is emitted (degrade to permissive = honest, and a
loud one-time WARN fires) rather than DB-scoping rows on a spoofable string. Pair
with [security].api_require_auth = true so a credential is actually required.
  false (default) -- NO SET LOCAL is emitted; the GUC stays unset; the policies
                     stay permissive -> every statement is byte-identical to today
                     (single-operator behaviour; system/daemon/seeding never scoped).
  true            -- emit SET LOCAL ONLY for a request carrying an ENFORCE-VERIFIED
                     owner; owner-less internal/system/daemon connections (and any
                     unverified owner) emit nothing and stay permissive (degrade-open:
                     never locked out). Flip on -- WITH principal_bind_mode=enforce --
                     for a multi-tenant deployment (operator-validated against live PG).
Bridged to MIOS_DB_RLS_ENABLE by userenv.sh (read by mios_pg.rls_enabled).

<!-- mios-src:551706f8bbaf from usr/share/mios/mios.toml:7512-7536 -->

### ── connection pooling (opt-in; swarm/DAG fan-out...

── connection pooling (opt-in; swarm/DAG fan-out connection-storm relief) ────
DEFAULT OFF: the agent-pipe (mios_pg) opens a fresh connection per query and
closes it -- byte-identical to the historic path. ON: a bounded pool of live
connections is REUSED across queries so a swarm/DAG fan-out (N concurrent nodes)
does not open N fresh connects. Degrade-open: pool exhaustion/error falls back to
a direct connect (a query never fails on the pool); a broken/dirty connection is
discarded, never reused, and a transaction-scoped SET LOCAL (the RLS owner GUC) is
rolled back on check-in so no per-request owner scope leaks across checkouts.
  pool_min -- connections pre-opened on first use (0 = grow purely on demand)
  pool_max -- hard ceiling on concurrent live connections (idle + checked-out)
Bridged to MIOS_PG_POOL_* by userenv.sh (read by mios_pg.pool_config).

<!-- mios-src:37912f8c4f1c from usr/share/mios/mios.toml:7538-7548 -->

### ── HNSW iterative scan (pgvector 0.8.0+): correctness for...

── HNSW iterative scan (pgvector 0.8.0+): correctness for FILTERED recall ────
Recall fuses an HNSW cosine scan with metadata filters (the owner_user RLS
scoping above, emb_version hygiene, tier). A plain HNSW search collects its
candidate set FIRST and applies the filter AFTER, so a selective filter can
yield FEWER than the requested LIMIT (silent under-retrieval). iterative_scan
re-enters the graph and keeps searching until LIMIT is satisfied or the tuple
cap is reached -- exactly the RLS-filtered case this complements.
  off           -- legacy single search (under-returns under a selective filter)
  strict_order  -- iterate while preserving EXACT distance ordering (default:
                   recall ranking + the downstream recency re-rank stay correct)
  relaxed_order -- iterate with a discarded-candidate heap; marginally higher
                   recall at the cost of approximate ordering
Rendered into the mios-pgvector Exec -c flags by 34-render-quadlets.sh, so it is
the server-wide default every session inherits (incl. the agent-pipe recall
connection) with no app-side per-session SET. Env: MIOS_PG_HNSW_ITERATIVE_SCAN.

<!-- mios-src:7e5e6a9ba73b from usr/share/mios/mios.toml:7552-7566 -->

### ── WS-MEM-VALIDATE (OWASP ASI08) write-time...

── WS-MEM-VALIDATE (OWASP ASI08) write-time memory-poisoning guard. A durable
knowledge fact is RECALLED later + folded into context, so an embedded
prompt-injection imperative / code-exfil payload persisted today can steer a
future turn. mios_memguard scans each fact before store. Modes: off (no-op;
default, zero behaviour change) | log (emit a memory_poison_flag audit event +
store) | strip (neutralize URLs/code-fences in the stored text) | reject (drop
a HIGH-severity fact). Complements the existing verdict-gate (unsatisfied turns
already skipped). Env: MIOS_MEMORY_GUARD_MODE.
Roadmap B1: default "log" -- audit-only (emits memory_poison_flag + stores, no
behaviour change), so ASI08 poisoning is actually observed instead of inert.
Operator can raise to strip/reject. (off = silent; the prior credibility gap.)

<!-- mios-src:760b202b1ab0 from usr/share/mios/mios.toml:7577-7587 -->

### memguard SEVERITY classifier path. "model" (default) -> a...

memguard SEVERITY classifier path. "model" (default) -> a micro-model
prompt-injection / poisoning judge classifies the write's INTENT (caught in any
language or paraphrase, unlike a fixed keyword list); when the micro lane is
unavailable the verdict DEGRADES to a pure structural scan (an inert URL/code
fence -> low, a tokenizer control-token delimiter -> a high escalation; benign
content still stores -- fail-safe, no keyword gate, no silent drop). Any other
value -> structural-only (the judge is skipped). Env: MIOS_MEMGUARD_JUDGE_MODE.

<!-- mios-src:977f8f88b95d from usr/share/mios/mios.toml:7589-7595 -->

### ── WS-A2 embedding-version hygiene + working-memory...

── WS-A2 embedding-version hygiene + working-memory durability ──────────────
emb_model/emb_version are stamped onto every stored vector (knowledge +
agent_memory) so a model/dimension change is detectable. Bump emb_version when
the embedding model or its dims change -> mios_embed_backfill re-embeds the
stale rows OFF the hot path instead of silently mixing incompatible vector
spaces (which degrades cosine recall to noise). scratch_persist mirrors the
per-chat working scratchpad to the pg `scratch` table so it survives an
agent-pipe restart (rehydrated once on chat entry). Read by the agent-pipe
(EMB_MODEL/EMB_VERSION/SCRATCHPAD_PERSIST) + mios-remember; env overrides
MIOS_PGVECTOR_EMB_MODEL / MIOS_PGVECTOR_EMB_VERSION / MIOS_SCRATCHPAD_PERSIST.

<!-- mios-src:ed5fad0b59d9 from usr/share/mios/mios.toml:7597-7606 -->

### ── WS-0 pgvector durability + bind hardening (Wave 0)...

── WS-0 pgvector durability + bind hardening (Wave 0) ───────────────────────
Periodic pg_dump backups of the unified agent datastore. backup_enable ships
TRUE (the datastore holds tiered memory / knowledge / skills / sessions --
losing it is expensive), but is degrade-open: a backup failure logs and the
DB keeps serving; it never blocks a read/write. The backup runner (a timer +
script outside this owner's files) reads MIOS_PG_BACKUP_KEEP for retention.

<!-- mios-src:cf632a30e2e1 from usr/share/mios/mios.toml:7617-7622 -->

### ── WS-10 mios-llm-light: the llama.cpp multi-model lane...

── WS-10 mios-llm-light: the llama.cpp multi-model lane (upstream llama-swap proxy) ──
Additive engine step toward the llama.cpp fleet-wide
KV-cache (concepts/llamacpp-engine-conversion.md). GATED OFF (enable=false) +
the quadlet's ConditionPathExists(models/.ready) keeps it inert until GGUFs are
provisioned. The agent-pipe is ALREADY ready: point a [nodes.*]/[agents.*]
entry at http://localhost:11450/v1 with api="llamacpp" and _kv_paging fires.

<!-- mios-src:45d0be2bdf36 from usr/share/mios/mios.toml:7639-7644 -->

### GGUF bake (73-model-prep.sh). CSV of...

GGUF bake (73-model-prep.sh). CSV of dest.gguf=hf_repo:filename; EMPTY =
opt-in skip (no image bloat). dest filenames MUST match mios-llm-light.yaml's
/models/*. Pre-quantized FOSS GGUFs, e.g.:
  "granite-4.1-8b.gguf=unsloth/granite-4.1-8b-GGUF:granite-4.1-8b-Q4_K_M.gguf,lfm2-700m.gguf=LiquidAI/LFM2-700M-GGUF:LFM2-700M-Q4_K_M.gguf,embeddinggemma-300m-qat-q8_0.gguf=ggml-org/embeddinggemma-300m-qat-q8_0-GGUF:embeddinggemma-300m-qat-Q8_0.gguf"
fleet modernization: provision the family-diverse light-lane GGUFs so the
/models/* dest names match mios-llm-light.yaml (Granite brain+coder, LFM2 micro,
EmbeddingGemma embeddings). Quant filenames VERIFIED present in each HF repo via the
HF API (granite-4.1-8b-Q4_K_M.gguf, LFM2-700M-Q4_K_M.gguf,
embeddinggemma-300m-qat-Q8_0.gguf). If a name ever drifts the bake just no-ops and the
quadlet's models/.ready gate keeps the lane inert (fails safe, no crash). Vision
(holo1.5-7b.gguf + mmproj) is operator-provisioned (the security classifier blocks the
assistant fetch).

<!-- mios-src:0f2452f21cec from usr/share/mios/mios.toml:7654-7665 -->

### [enhanced_session] -- alternate launch path: full GNOME...

----------------------------------------------------------------------------
[enhanced_session] -- alternate launch path: full GNOME desktop inside
the dev VM, exposed via xrdp on `port`, connected to from Windows via
mstsc.exe (the same Hyper-V Enhanced Session client). Complements the
WSLg per-window launch path (which keeps working). Operator picks per
session: per-window for native-Windows-window feel, Enhanced Session
for libadwaita-consistent theming + rounded corners + Bibata cursor
(because the full session renders inside the VM and only the final
pixmap is RDP'd to Windows -- no WSLg-per-window decoration drift).

Driven by:
  * automation/35-xrdp-enhanced-session.sh installs xrdp + gnome-session
    and binds the port at install time.
  * Update-MiOSStartMenuShortcuts.ps1 writes a `MiOS Full Desktop` .lnk
    pointing at mstsc.exe /v:localhost:<port> /f.
  * RDP creds = [identity].default_password (same source the keyring
    auto-unlock service uses).
----------------------------------------------------------------------------

<!-- mios-src:4c0a9a6cd2d5 from usr/share/mios/mios.toml:7669-7686 -->

### Port 13389 (NOT the standard 3389). Windows blocks RDP via...

Port 13389 (NOT the standard 3389). Windows blocks RDP via loopback
on the canonical 3389 with error 0x708 "console session in progress"
as a security measure -- mstsc /v:localhost:3389 short-circuits to
the local console RDP check and refuses to connect even though the
target is xrdp inside the dev VM. Port 13389 bypasses that check:
loopback detection only triggers on the standard port.
Operator-flagged mstsc 0x708 error.

<!-- mios-src:445fbca0d5e4 from usr/share/mios/mios.toml:7689-7695 -->

### [appearance] -- system-wide visual identity. Applied to: *...

----------------------------------------------------------------------------
[appearance] -- system-wide visual identity. Applied to:
  * Operator's GNOME session (gsettings)
  * Flatpak runtime overrides (via /usr/libexec/mios/mios-flatpak-init)
  * Per-user gtk-3.0 + gtk-4.0 settings.ini (via /etc/skel/.config/...)
  * Bibata cursor + dark Adwaita variants

Lifted out of automation/10-locale-theme.sh + mios-flatpak-init so the
operator can override in /etc/mios/mios.toml [appearance] without
patching scripts. Operator directive theme drift between
bake-time and firstboot was leaving Nautilus + others rendered in
default light Adwaita instead of the operator's preferred dark
variant.
----------------------------------------------------------------------------

<!-- mios-src:e4966568fb67 from usr/share/mios/mios.toml:7700-7713 -->

### [flatpak] -- channel + remote preferences for all flatpak...

----------------------------------------------------------------------------
[flatpak] -- channel + remote preferences for all flatpak operations.
Operator binding "target betas for all flatpaks" -- prefer
the flathub-beta remote where an app publishes there; fall back to
stable flathub otherwise. Picks up fresher upstreams (newer GNOME
runtime / GTK4 versions etc.) without manually tracking each app.
----------------------------------------------------------------------------

<!-- mios-src:c698f1f70300 from usr/share/mios/mios.toml:7715-7721 -->

### [graphics] -- WSLg-aware GTK4 render-path overrides applied...

----------------------------------------------------------------------------
[graphics] -- WSLg-aware GTK4 render-path overrides applied globally
to ALL flatpaks via mios-flatpak-overrides-apply.
Operator binding "ALL Windowed Linux applications have
outdated and broken Windowing... out of date GLOBALLY". Root cause is
WSLg's Weston compositor + dxgkrnl GPU passthrough being mismatched
with modern GTK4 / libadwaita / Vulkan + dmabuf expectations. The
stable render path on WSLg is:
  * GTK4 renderer  -> cairo (CPU compositing; no GL path)
  * Mesa GL        -> llvmpipe (LIBGL_ALWAYS_SOFTWARE=1)
  * Vulkan         -> disabled (no dzn passthrough)
Setting all three forces every flatpak GUI through the path that
actually works on this compositor -- trades render perf for stability
+ correct rendering of headerbars, scrolling, decorations.
----------------------------------------------------------------------------
MODERN GTK4 rendering ("GTK themes regressed / old not
modern / windowing + CSS out of date"). cairo + software-GL was a May WSLg
compatibility hammer, but cairo IS the legacy renderer -> flat/old look, no
modern libadwaita visuals. WSLg + the 4090 (/dev/dri) have matured: use the
modern GTK4 `ngl` (node-GL) renderer + real hardware GL. Vulkan stays OFF
(WSLg Vulkan is still flaky; ngl is GL, not Vulkan). gdk_backend stays x11
(XWayland) for WebKit/GTK4 WSLg stability. If a GTK4 app misrenders, fall
back via /etc/mios overlay [graphics].gsk_renderer="cairo".

<!-- mios-src:c155a30f7438 from usr/share/mios/mios.toml:7734-7756 -->

### WSLg's Weston Wayland trips Gdk Error 71 (Protocol error)...

WSLg's Weston Wayland trips Gdk Error 71
(Protocol error) in WebKit/GTK4 AND lacks
xdg_popup reposition. Flatpaks DON'T inherit
the shell's GDK_BACKEND across the sandbox
boundary, so the override MUST set it here.
Mirrors [wsl2.desktop_compat].gdk_backend="x11".
Search path for cursor + icon themes. ~/.local/share/icons LEADS because
/usr is read-only on bootc (Bibata can't be added there at runtime) and
flatpaks already bind-mount ~/.local/share/icons via xdg-data/icons:ro --
so installing Bibata there reaches BOTH host shells and every sandbox.

<!-- mios-src:eaf0c0459f49 from usr/share/mios/mios.toml:7762-7771 -->

### FBM (first-boot models, T-200/T-201). Entry schema, one...

FBM (first-boot models, T-200/T-201). Entry schema, one array-of-tables row
per model:

    [[ai.firstboot_models]]
    name   = "qwen3-8b-q4.gguf"   # filename under /var/lib/mios/llamacpp/models
    source = "https://..."        # direct GGUF/HF URL; curl -C - resumable
    sha256 = "<hex>"              # OPTIONAL, but see below
    lane   = "llm_light"          # optional [ports] lane hint, reported by `mios models list`

sha256 is ENFORCED when present: the fetcher streams the downloaded part file
through sha256, and on mismatch DELETES it and skips the model rather than
installing an unverified weight under a name the lanes would load (it used to
print "Verifying sha256" and rename without hashing anything). Omitting the
key provisions the model unverified, and `mios models add` says so.

Edit this vendor list for a fleet default; `mios models add|rm` writes the
USER overlay (~/.config/mios/mios.toml) instead, per the vendor<host<user
cascade. `mios models list` prints the RESOLVED set joined against disk, so a
declared-but-missing model is visible.

Also: [[ai.firstboot_bound_images]] { image } for mios-bound-images-firstboot.
None are declared by default -- the provisioners resolve an empty list and
no-op, so the machinery ships dormant until an operator adds entries.
Canonical agent surface = the AGENT-PIPE ORCHESTRATOR on :8700 (served model
"MiOS-Agent"), the UNIFIED entrypoint ("UNIFY THE MiOS AI
PIPELINE"). MIOS_AI_ENDPOINT (the surface every OpenAI-API client + the `@`/
`mios` CLI resolves, via userenv.sh) MUST point here so those clients get the
full pipeline (refine -> route -> deterministic dispatch / native-loop / council
-> SERVER-SIDE broker execution + read-back verification -> polish + grounding),
NOT the bare Hermes leaf. Hermes-Agent (:8720/v1, direct host install,
automation/72-hermes-agent.sh) is now a LEAF the pipe calls (binding in
[agents.hermes].endpoint), never the public entrypoint -- pointing the canonical
surface at :8720 made the interactive `@` bypass the orchestrator + fail. NOTE:
this is the CLIENT surface only; the pipe's OWN inference backend is
MIOS_AGENT_PIPE_BACKEND (separate), so :8700 here does not self-loop.

<!-- mios-src:1fa585fa46da from usr/share/mios/mios.toml:7781-7815 -->

### Served model id the orchestrator advertises on...

Served model id the orchestrator advertises on :8700/v1/models, and the model
every THIN client requests (the @/mios CLI via MIOS_AI_GATEWAY_MODEL, the Hermes
desktop app, and the `hermes` CLI REPL). SSOT for the agent-surface model name so
no front-end hardcodes it (operator "NO HARDCODES"; unify of the REPL).

<!-- mios-src:42d31cab7dcb from usr/share/mios/mios.toml:7817-7820 -->

### 62 WS-9 human-in-the-loop gate-mode (applied at the...

#62 WS-9 human-in-the-loop gate-mode (applied at the dispatch chokepoint).
  off   (default) -- no gating, zero overhead/behaviour change.
  audit -- LOG every action whose risk tier is >= hitl_threshold, then proceed
           (observe what WOULD be gated before enforcing).
  block -- REFUSE such actions (not executed) until a human approves them.
hitl_threshold is a permission tier from the risk lattice (read < write <
interactive); HITL fires for verbs at/above it. Reuses the #55 risk tiers + the
agent-passport humanInLoop thresholds. Ships off (inert) -- opt in deliberately.

<!-- mios-src:f13601e1517b from usr/share/mios/mios.toml:7823-7830 -->

### ASK-TO-RUN ("mios daemon should ask user to run things")...

ASK-TO-RUN ("mios daemon should ask user to run things"): when a
HITL-tier verb is intercepted, the pipe PROPOSES it + asks the user to approve (instead
of silently no-op'ing / fabricating). The user's next reply is MODEL-classified (no
keyword list) as approve/reject; approve re-runs exactly that hashed action. OWUI + the
Hermes desktop app render the proposal as a NATIVE prompt (the mios_proposed_action
block); the text round-trip is the portable fallback. TTL expires an unanswered proposal.

<!-- mios-src:638cbb655849 from usr/share/mios/mios.toml:7833-7838 -->

### WS-A9 dispatch-time PDP (Policy Decision Point) capability...

WS-A9 dispatch-time PDP (Policy Decision Point) capability gate. The per-agent
[agents.<name>] and per-user [users.<name>] denied_verbs / allowed_verbs /
max_permission policies are now enforced at the SINGLE dispatch chokepoint
(mios_pdp, shared with the surface filters), so a verb pruned from a caller's
tool surface can never still dispatch (closes the RBAC bypass). An UNKNOWN
max_permission tier FAILS CLOSED (restricts to the safest tier) -- it used to
fail OPEN (silently grant the full surface). The gate is always on but a no-op
for callers with no policy (single-user MiOS unaffected). This flag only sets
audit verbosity: false (default) emits a pdp_block event on DENY only; true
also emits a pdp_allow event per permitted dispatch.

<!-- mios-src:3df1557a67d1 from usr/share/mios/mios.toml:7860-7869 -->

### WS-A5 tokenizer seam

WS-A5 tokenizer seam: selects the token-COUNTING backend (mios_tokenize), used
by context-fit sizing, the OpenAI usage object, and history/block truncation.
  tiktoken  (default, SHIPPED) -- EXACT OpenAI-BPE counts via the tiktoken dep
            installed into the agent venv; the encoding blob is baked offline at
            build time (tokenizer_cache_dir) so no network is touched at runtime.
  hf        -- a served model's OWN tokenizer.json via the `tokenizers` dep
            (set tokenizer_path to a vendored tokenizer.json -- most accurate
            per-model count).
  heuristic -- the zero-dep ~4-chars/token estimate (the legacy //4); pick this
            to drop the tokenizer dependency entirely.
DEGRADE-OPEN: if the selected backend's dep/asset is absent (CI, a bare/air-gapped
host), the agent-pipe transparently falls back to the heuristic -- the tokenizer is
never a hard import dependency. Env: MIOS_TOKENIZER_BACKEND.

<!-- mios-src:9b320b91e506 from usr/share/mios/mios.toml:7871-7883 -->

### WS-A1 SSOT catalog load posture. "warn" (default): the...

WS-A1 SSOT catalog load posture. "warn" (default): the verb/recipe/agent
catalog loaders log + degrade to empty/partial on a parse error. "fail":
FAIL-LOUD -- a malformed mios.toml RAISES at agent-pipe startup so a broken
SSOT never silently serves an empty tool surface. Flip to "fail" once the
manifest-drift gate (mios-ai-manifest-gen --check) is green in CI. Env:
MIOS_CATALOG_FAIL_MODE.

<!-- mios-src:ec7e40d222cc from usr/share/mios/mios.toml:7895-7900 -->

### WS-A16 cost/quality SmartRouting (RESEARCHED local-first...

WS-A16 cost/quality SmartRouting (RESEARCHED local-first escalation, LiteLLM-
shaped): run the local lane(s) first, escalate to a paid REMOTE core ONLY when
a quality gate fails / locals are exhausted, within a per-day cost budget
(mios_smartroute). DISABLED by default = local-only (today's behaviour). Add a
remote core under a future [ai.remote_cores.<name>] block (url/model/cost_in/
quality_tier/key_ref -- key from the secret store, NOT here) + flip the flag.
Env: MIOS_SMARTROUTE_ENABLE / MIOS_SMARTROUTE_BUDGET.

<!-- mios-src:acf442873187 from usr/share/mios/mios.toml:7906-7912 -->

### WS-A17 local package registry. When true, the build...

WS-A17 local package registry. When true, the build materializes a versioned
package tree (ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml +
registry.json) projected from the live SSOT (verbs/agents/recipes) via the
mios-registry CLI, and the drift gate verifies it stays in sync. DEFAULT FALSE
-> the feature ships DORMANT: nothing is materialized and every gate passes
trivially. Env: MIOS_PACKAGE_REGISTRY.

<!-- mios-src:642a2a3cda3b from usr/share/mios/mios.toml:7915-7920 -->

### WS-1 unified lane resolver

WS-1 unified lane resolver: which heavy engine the agent-pipe
PREFERS when both heavy lanes ([ai.sglang] :11441 + [ai.vllm] :11440 -- BOTH advertise
served_name "mios-heavy") are provisioned. mios_lanes.LaneResolver tries the preferred
heavy lane first, then the OTHER heavy lane, then the always-on light lane (mios-llm-light
:11450); a dead lane fails over (never 404s) with a per-lane cooldown + auto-recovery.
Single engine ("sglang" | "vllm") sets the preference; "light" forces light-only; an
explicit comma-chain ("sglang,vllm,light") is honoured verbatim. Read directly from this
SSOT by the agent-pipe (no quadlet placeholder); env override MIOS_AGENT_PIPE_HEAVY_ENGINE.

<!-- mios-src:29778b3066df from usr/share/mios/mios.toml:7922-7929 -->

### opencode (https://opencode.ai) -- code-specialist agent CLI...

opencode (https://opencode.ai) -- code-specialist agent CLI installed
directly onto the host by automation/72-hermes-agent.sh. CURRENT path =
a first-class OpenAI /v1 council peer via mios-opencode-gateway.service
(:8780); the agent-pipe orchestrator dispatches code-heavy work to it
(see the /v1 gateway block below). LEGACY/retired = Hermes spawning it
per-task via ACP when a delegate_task entry sets acp_command="opencode".
Cascade: Hermes-Agent plans, opencode is the code specialist /v1 peer,
qwen3:1.7b is the general fan-out worker.

To enable opencode as a global delegation target, set in
/etc/mios/hermes/config.yaml:
  delegation:
    acp_command: opencode
    acp_args: ["--acp", "--stdio"]
OR scope per-task by passing acp_command in delegate_task(tasks=[...])
entries that match code-tagged goals (recommended; keeps the default
delegate path on qwen3:1.7b for non-code work).

<!-- mios-src:b32b973b1905 from usr/share/mios/mios.toml:7945-7961 -->

### ── opencode /v1 gateway (front-door commitment,) ────────...

── opencode /v1 gateway (front-door commitment,) ────────
opencode is a first-class OpenAI /v1 COUNCIL PEER via mios-opencode-gateway.
service (:8780), NOT a Hermes ACP subprocess (the ACP framing above is the
RETIRED path). These keys are the SSOT for automation/72-hermes-agent.sh + the
gateway unit + tools/lib/userenv.sh (MIOS_OPENCODE_*). ONE canonical model id
across: [agents.opencode].model, opencode.json's model key, and the
mios-opencode build name:tag.

<!-- mios-src:a4bcf5e5c5eb from usr/share/mios/mios.toml:7964-7970 -->

### Unified agent-plane tree (full-hybrid relocation): all...

Unified agent-plane tree (full-hybrid relocation): all three
agents live under /usr/lib/mios/agents/ — hermes-agent/ (Hermes code + bin),
opencode/bin/opencode (binary), opencode-gateway/ (the /v1 shim) — and share
ONE explicit venv at /usr/lib/mios/agents/.venv (sibling, not nested inside
hermes-agent). agent_venv is the de-facto shared interpreter for hermes-agent
+ agent-pipe + the gateway shim. These two values are the SSOT MIRROR: the
systemd units (hermes-agent / mios-agent-pipe / mios-delegation-prefilter /
mios-opencode-gateway) and the libexec scripts (mios-hermes-firstboot self-
recovery, /usr/bin/hermes, dashboard-auth-stub, discord-reactions-patch) carry
the same LITERAL paths (systemd does not expand env in ExecStart=). Change
these AND every one of those together.

<!-- mios-src:e4f633db8581 from usr/share/mios/mios.toml:7988-7998 -->

### SSOT for the default chat model. The 4-model-set reasoning...

SSOT for the default chat model. The 4-model-set reasoning base
(qwen3.5:4b, ~3.4 GB resident) -- was granite4.1:3b, repointed in the
consolidation (granite was dropped from the fleet). Same value as
small_ram_model below so a host with no auto-pick still lands on a 4-set base
(never re-pulls a dropped model). build-mios.ps1's auto-pick in
[ai.host_thresholds] below promotes this on hosts with enough VRAM by writing
the picked value into the per-host mios.toml overlay at /etc/mios/mios.toml.
mios-hermes-firstboot reads the resolved value through the layered overlay
chain (~/.config -> /etc -> /usr/share). mios.html exposes [[ai.catalog]].

<!-- mios-src:10173a6ccaa5 from usr/share/mios/mios.toml:8004-8012 -->

### Per-role BASE brain the agent-pipe reasoning stages...

Per-role BASE brain the agent-pipe reasoning stages (refine, polish, planner,
DCI, swarm, micro) inherit when their own MIOS_*_MODEL env is unset (server.py
_STACK_MODEL = ${MIOS_STACK_MODEL:-stack_model}). ONE resident served brain =
no llama-swap thrash (operator's "one resident model" choice). Was the GONE
gemma4:12b in the server.py default -> 404; SSOT-pinned to the served brain
. The mios-agent-pipe.service mirrors these; a fresh boot is correct
even without the runtime model-align drop-in (which becomes redundant).

<!-- mios-src:6f153351176a from usr/share/mios/mios.toml:8014-8020 -->

### Bash prompt shortcut

Bash prompt shortcut: type `@how do I X` (no space after the char)
and the shell forwards the rest to /usr/bin/mios (-> Hermes /v1).
Implemented via command_not_found_handle in /etc/profile.d/mios-verbs.sh.
Operator may override the prefix glyph here -- pick any char bash leaves
alone at command-position. Avoid: ~ ! ? : # > < & | ; ' " (all reserved
by the shell parser at command-start). Safe choices: @ , %

<!-- mios-src:1c042e540ace from usr/share/mios/mios.toml:8026-8031 -->

### Build-time model bake list. Comma-separated; consumed by...

Build-time model bake list. Comma-separated; consumed by
automation/73-model-prep.sh as MIOS_LLAMACPP_BAKE_MODELS. Empty disables
baking (image stays small; first-boot pulls instead).

4-MODEL POLICY ("should be 3-4 max including micro-llm;
the 4 newest available that fit the stack"). The fleet is EXACTLY 4 bases --
3 LLMs + 1 embedder -- chosen as the newest that fit a lean shared-4090 stack:
  * qwen3.5:4b         REASONING  (~3.4 GB) -- mios-agent + mios-hermes +
                                   mios-sys-agent all derive FROM this one base
  * qwen3:1.7b         MICRO/CPU  (~1.4 GB) -- the micro-LLM, every CPU/light-
                                   lane worker, and the *-cpu twins
  * qwen2.5-coder:7b   CODING     (~4.7 GB) -- mios-opencode (newest small coder
                                   that fits; qwen3-coder is 30B-only / 7b=404)
  * nomic-embed-text   EMBED      (~0.3 GB) -- knowledge-table + RAG embeddings
                                   (KEEP: live embeddings are wired to nomic)
Everything else (qwen3.5:9b, qwen3.5:2b, qwen3:0.6b, qwen3-coder:30b,
qwen2.5-coder:14b, llama3.2-vision:11b, granite4.1:3b/30b, gpt-oss:20b,
qwen3-vl:4b, gemma4:e4b) was REMOVED from the fleet per the 3-4-model cap.

The list below also names the derived mios-* role tags. Those are derived tags
defined in automation/73-model-prep.sh and REUSE
the 3 LLM base blobs (under /usr/share/mios/llamacpp/models) -- they add ~no disk, so
listing them only guarantees they are present after a build. Total baked: the
3 LLM bases + nomic (~9.8 GB) + the (blob-sharing) mios-* tags.

Consumed by automation/73-model-prep.sh as MIOS_LLAMACPP_BAKE_MODELS. Operators
on bandwidth-constrained networks can shrink this in /etc/mios/mios.toml; empty
disables baking entirely (first-boot pulls instead).

<!-- mios-src:b366be56172c from usr/share/mios/mios.toml:8033-8060 -->

### [ai.kv] -- llama.cpp KV-cache SERVING knobs (init-time...

----------------------------------------------------------------------------
----------------------------------------------------------------------------
[ai.kv] -- llama.cpp KV-cache SERVING knobs (init-time launch flags for the
inference lanes). DISTINCT from [dispatch].kv_* (the agent-pipe's RUNTIME
save/restore/fork/GC behaviour over the /slots API): this table is about HOW a
llama-server lane is LAUNCHED so its KV is pageable + correct.

RESERVED / NOT AUTO-RENDERED (forward-looking): no render path injects these values
into the launch yaml today -- mios-llm-light.yaml carries the --slot-save-path
literal DIRECTLY in each lane `cmd`. This table DOCUMENTS the canonical value so the
yaml + the tmpfiles dir stay in sync BY HAND, and reserves the keys for a future
env-render of the lane cmds; editing a value here does NOT change a running lane
until the yaml literal is updated to match.
  * slot_save_path -- the canonical --slot-save-path every chat lane should launch
    with, so the agent-pipe can checkpoint/restore a conversation's KV to disk (the
    AIOS Context Manager). MUST match the tmpfiles-declared dir (mios-llamacpp.conf)
    and the literal in the chat lanes of mios-llm-light.yaml (kept in sync by hand).
  * swa_full -- when true, append --swa-full to SWA (sliding-window-attention)
    model lanes so the FULL window is retained and KV checkpoint/restore stays
    correct across a save->restore. RESERVED, default OFF: the current chat
    brains (granite4.1:8b, lfm2:700m) are HYBRID/RECURRENT, not SWA, so
    --swa-full is MOOT for them and must NOT be added to their cmd. It is for a
    FUTURE Gemma / Qwen3-SWA lane that pages KV (an init-time flag). The real
    hybrid checkpoint-restore correctness lever is the llama.cpp BUILD VERSION
    (recent builds fix hybrid-recurrent restore), so the llama-swap image pin
    should track a recent VALIDATED build -- verify the pin; do not change it here.
A save->restore round-trip smoke (POST /slots/0?action=save then action=restore,
warn-only / degrade-open) belongs in a future llama.cpp verify script; no such
offline verify/migration script exists yet to extend.
----------------------------------------------------------------------------

<!-- mios-src:6570dc1cedd4 from usr/share/mios/mios.toml:8068-8097 -->

### [[ai.catalog]] -- array of model entries the mios.html...

[[ai.catalog]] -- array of model entries the mios.html dropdown
renders for [ai].model selection. Adding a row here adds an option
in the UI; build-mios.ps1's Read-Model + mios-hermes-firstboot's
custom_providers list both iterate this array. `id` is the model
tag, `label` is the human display text, `ram_gb` is the rule-of-
thumb RAM floor (informational; surfaces under each <option>).
Keep ordered small -> large; first entry is the no-RAM-info fallback.
----------------------------------------------------------------------------
── fleet modernization (family-diverse, mainline-llama.cpp-safe) ──
The active fleet across slots: Granite 4.1 8B (IBM) brain+coder, LFM2-700M (Liquid
AI) micro, EmbeddingGemma-300m QAT (Google) embeddings, Magistral Small 2509
(Mistral) heavy, Holo1.5 (H Company) vision. RETIRED the all-Qwen + unservable
entries: qwen3.5:4b/9b (BLOCKED on mainline llama.cpp -- the qwen35 arch trap),
qwen2.5-coder:7b/14b, qwen3-coder:30b, qwen3:32b, llama3.2-vision:11b,
granite4.1:3b/30b, gpt-oss[-tools]:20b. host_thresholds small/mid -> granite4.1:8b,
big -> mistral-magistral-small-2509; every host_thresholds id MUST appear here.
First entry (granite4.1:8b) is the default / no-RAM-info fallback.

<!-- mios-src:f5eb07717dcd from usr/share/mios/mios.toml:8102-8118 -->

### [ai.host_thresholds] -- auto-pick model based on host RAM...

----------------------------------------------------------------------------
[ai.host_thresholds] -- auto-pick model based on host RAM during the
Get-Hardware phase. Operators tune the cutoffs via mios.html.
Build-mios.ps1 reads these and assigns $aiModel = big/mid/small at
install time. All three entries must be `id` values present in
[[ai.catalog]] above.
----------------------------------------------------------------------------

<!-- mios-src:810fec131dd8 from usr/share/mios/mios.toml:8134-8140 -->

### Operator directive "base default models ALL fit within 12GB...

Operator directive "base default models ALL fit within
12GB systems (8GB of which are available to the Models on CPU --
Medium models are for users with dGPUs or just multiple GPUs. ALL
Global agents are default to the CPU models (even for GPU models
also default to this global defaults). ONLY if there's detected
availability during MiOS build pipelines AND MiOS installation
Pipelines too (their all dictated by the toml files variables).
mios.toml/html is GLOBAL verb/variables library (user modifiable)
-- if detected GPU has more than 8GB of VRAM it deploys with medium
sized models (8GB+). 16GB+ models are purely decided by the users
definition in the mios.html edits. All AGENTS DEFAULTS TO CPU
models -- across all hardware (dGPU also uses this model -- just
on GPU compute instead). 8GB+ models are ONLY for GPU compute
agents if detected system meets criteria!!!"

Resolution rule applied by build-mios.ps1 + install pipeline +
mios-hermes-firstboot, top-down:

  1. If the operator EXPLICITLY chose big_ram_model in mios.html
     (sets [ai].model to a >=16GB id), USE THAT and skip the
     auto-picker. Mios.html surfaces big models behind a clear
     "I have the VRAM headroom" tick.
  2. Else if VRAM >= mid_vram_gb (8GB) detected at build/install,
     promote default to mid_ram_model (medium, 8-16GB class).
  3. Else: default to small_ram_model (CPU-fit, <8GB resident).
     EVERY agent on EVERY host starts here -- dGPU hosts just
     RUN the small model on GPU for speed; the model size stays
     conservative until step 1 or 2 promotes.

VRAM thresholds (NOT system RAM -- the rule is about GPU availability):

<!-- mios-src:5f178f2f1183 from usr/share/mios/mios.toml:8142-8171 -->

### Model picks per tier (research-driven swap...

Model picks per tier (research-driven swap, operator-approved):
Consolidated around the qwen3.5 family for Hermes -- consistent
tokenizer + style across tiers means cleaner fallback escalation +
native OpenAI tool_calls JSON with NO harmony chain-of-thought leak
(the issue that killed gpt-oss-tools:20b). The big-tier qwen-coder
stays because coder models tested cleaner on multi-step tool flows.

  small_ram_model -- DEFAULT for every fresh install + every global
    agent. Fits in 8GB CPU budget; ~3.4GB resident. Native OpenAI
    tool_calls JSON; sub-second first inference on dGPU; reasonable
speed on a 12GB CPU-only host. Operator-flagged
    ("ALL AGENTS DEFAULTS TO CPU models"). Was granite4.1:3b;
swapped to qwen3.5:4b per Hermes-orchestrator
    SOTA survey (better tool-call discipline + family-consistent).

<!-- mios-src:f412987346d1 from usr/share/mios/mios.toml:8184-8197 -->

### mid_ram_model -- 8-16GB class. Auto-deploys ONLY when...

mid_ram_model -- 8-16GB class. Auto-deploys ONLY when build/install
    detects VRAM >= mid_vram_gb (8). A bigger reasoning base for a
mid-tier dGPU box ("a large model for MiOS
    deployments with dGPUs"). The LEAN single-box default stays on
    small_ram_model (qwen3.5:4b); this never deploys on a CPU-only /
    <8GB host, so it does not bloat the 4-set baseline.

<!-- mios-src:94eb3b0f4132 from usr/share/mios/mios.toml:8199-8205 -->

### big_ram_model -- 16GB+ dGPU class. The LARGE model for dGPU...

big_ram_model -- 16GB+ dGPU class. The LARGE model for dGPU deployments.
    Auto-deployed at first boot when detected VRAM >= big_vram_gb (16)
    (operator directive); mios.html can still override to any explicit pick,
    so the single-box 4-set is untouched. The role Modelfiles are base-
    agnostic (the pipe injects the MiOS contract + global tools at runtime,
    agent-contract.md: "Whatever your size, model, or lane..."), so the SAME
    roles run on this large base on a dGPU node with zero code change. Newest
    large coder/reasoner present in the registry that fits a 24GB dGPU.

<!-- mios-src:d89ae54e605c from usr/share/mios/mios.toml:8207-8215 -->

### Vision-grounding model -- read by...

Vision-grounding model -- read by /usr/libexec/mios/mios-pc-vision
for screenshot -> click-coordinate translation. Hermes's main text
model is separate; vision lane runs on its own model tag.
DROPPED FROM THE FLEET the 4-model set (qwen3.5:4b / qwen3:1.7b /
qwen2.5-coder:7b / nomic-embed-text) carries NO vision model. The previous
pick (llama3.2-vision:11b, ~8 GB) is no longer baked/pulled. These slots ship
EMPTY so an image turn does NOT silently re-pull an 11B VLM; the vision lanes
are OPT-IN -- to re-enable, add a vision tag to [[ai.catalog]], pull it, and
set these to that tag in /etc/mios/mios.toml (operator overlay).

<!-- mios-src:2cca1b3f3357 from usr/share/mios/mios.toml:8218-8226 -->

### Chat VLM

Chat VLM: agent-pipe routes any chat turn carrying an image straight to this
model. SSOT for MIOS_AGENT_PIPE_VISION_MODEL (bridged in tools/lib/userenv.sh).
(operator "FIX ALL VISION"): provisioned the Holo1.5-7B GGUFs under
/models (served as "qwen3-vl:4b" in mios-llm-light.yaml) and ENABLED vision. Set
back to "" to disable image chat (the agent-pipe then returns an honest "vision
unavailable" turn instead of a confusing backend 5xx).

<!-- mios-src:4dd941e43c01 from usr/share/mios/mios.toml:8229-8234 -->

### GUI click-grounding VLM lane (Phase-2 desktop control...

GUI click-grounding VLM lane (Phase-2 desktop control: screenshot ->
click coordinates). The llama.cpp light lane CANNOT run the grounding heads (GUI-Actor /
Holo1.5 / UI-TARS / Qwen3-VL) -> they need vLLM. RE-SCOPED the
mios-llm-heavy-alt Quadlet is now the GENERIC gated vLLM lane (see [ai.vllm] below),
serving a HEAVY TEXT reasoner by DEFAULT (operator "vLLM heavy lane"); to serve
a grounding VLM instead, point vllm_bake_model at one + set vllm_served_name =
"mios-grounding". The lane now lives on :vllm (11440), off the iGPU's :11436.

<!-- mios-src:8ab3677fa777 from usr/share/mios/mios.toml:8237-8243 -->

### Always-on micro-LLM. ~600 MB resident; sub-second...

Always-on micro-LLM. ~600 MB resident; sub-second classification.
Used by mios-log-watcher.service (journal triage), the cron-director
(gating scheduled tasks on system state), and any agent / shim
wanting <500 ms classification without round-tripping the big text
model. Loaded continuously (keep_alive = -1).
Operator directive "we could have a micro-LLM be running
in the background on 1 core(2 threads) ... daemon for logs and log
collection and presenting ... could even be a cron director".
Operator directive (clarification): "mios-sys-agent should
use a good 2-6Gb+ modern model for enhancing prompts and leave the
micro-llms to use the small models for its background/daemon tasks".
Two roles, two models:
  * mios-sys-agent   (Modelfile FROM qwen3.5:4b, the 4-set reasoning base) --
                     operator-facing chat refinement layer in the
                     OWUI Pipe + the (currently-disabled) prefilter
                     refinement step. Configured by [ai].sys_agent_*.
  * micro_model      (qwen3:1.7b, ~1.4 GB, CPU lane) -- background daemons
                     (log-watcher, cron-director, agent-nudger, mios-micro-llm
CLI). REPOINTED from qwen3:0.6b-cpu (a dropped
                     5th base) to the 4-set micro/CPU base qwen3:1.7b -- which
                     is already the daemon's background MODEL and the
                     mios-agent-cpu base. Small + fast for classification; no
                     chat-quality needed. Endpoint stays the CPU lane (:11435).

<!-- mios-src:eaa650b493fc from usr/share/mios/mios.toml:8247-8269 -->

### Flatpak refs installed across EVERY MiOS deployment shape...

Flatpak refs installed across EVERY MiOS deployment shape -- the
OCI build pipeline (automation/61-flatpak-bake.sh) and the
dev-VM overlay layer (mios-bootstrap/build-mios.ps1's
Layer-MiOSEssentials) BOTH read this list, so what lands here
lands in podman-MiOS-DEV AND in the deployed bootc image.  Per
feedback_mios_dev_equals_mios memory: "every flatpak (Epiphany /
Nautilus / GNOME runtime)" -- canonical MiOS desktop surface.
Nautilus is the GNOME file manager (`Files`); shipping it here
means `flatpak run org.gnome.Nautilus` works on every host.

<!-- mios-src:17184e8c59bf from usr/share/mios/mios.toml:8282-8290 -->

### VSCodium removed the MiOS dev surface is code-server...

VSCodium removed the MiOS dev surface is code-server
(mios-code-server.container, http://localhost:8220) editing the live
root FHS at /mnt/mios-root -- the self-hosting dev loop. No separate
desktop IDE flatpak.
Google Chrome Dev channel -- closest flathub-available analog to
the Windows "Canary" channel (true Canary doesn't ship for Linux;
Dev releases ~weekly, one channel ahead of Beta). Operator-requested
to provide a Chromium-derived browser the Hermes agent
(and the operator) can drive for web tasks. Hermes's bundled
Playwright Chromium still handles agent browser_use tools; this
flatpak is for operator-facing browsing + manual CDP integration.

<!-- mios-src:c91f60cd63b0 from usr/share/mios/mios.toml:8305-8315 -->

### [[desktop.apps]] -- UNIFIED app metadata. Operator...

----------------------------------------------------------------------------
[[desktop.apps]] -- UNIFIED app metadata.

Operator directive "toml/html packages sections are
BOTH the installation references for MiOS builds and deployments
globally -- AS WELL as AI agents references for defaults...
mios.html; user edits and adds a flatpak like zen browser >> this
is changed in the default browser fields and is picked up by the
code for building MiOS, deploying and running -- AS WELL as being
the reference material for AI agents GLOBALLY".

This array of tables is the SSOT for every desktop app on MiOS.
Each entry carries:
  id          (string, required)  flatpak app-id OR host binary
  remote      (string, optional)  flathub | fedora | gnome-nightly (default: flathub)
  role        (string, optional)  semantic role: browser/file-manager/terminal/...
  default     (bool, optional)    is this the default for its role? (default: false)
  description (string, optional)  one-line operator-visible blurb
  overrides   (table, optional)   per-app env overrides (same shape as
                                  [flatpak.app_overrides.*])

Code that consumes this:
  * mios-flatpak-overrides-apply       -> emits per-app override files from .overrides
  * mios-find (via [mios-find.aliases]) -> alias values reference these ids
  * (future) automation/61-flatpak-bake.sh -> install list from id+remote
  * (future) mios.html configurator UI    -> renders array with role-picker

Operators add an app: append a [[desktop.apps]] entry. To make it
the default for a role, set role + default=true and that role's
aliases route to it. To change render envs, add overrides = {...}.
----------------------------------------------------------------------------

<!-- mios-src:e91caa4bfae9 from usr/share/mios/mios.toml:8319-8349 -->

### Split-renderer strategy for Epiphany under WSLg: * GTK4...

Split-renderer strategy for Epiphany under WSLg:
  * GTK4 chrome stays on the SAME stable cairo + SW-GL combo the
    rest of the WSLg fleet uses (Nautilus, Ptyxis, etc.) -- the
    wslg-gpu.sh empirical comment is that ANY hardware GTK4 path
    crashes the main process within seconds.
  * WebKit (the engine inside Epiphany) gets its OWN GPU compositing
    enabled, decoupled from GTK4's renderer. WEBKIT_DISABLE_
    COMPOSITING_MODE=0 + WEBKIT_USE_DMABUF_RENDERER=1 allow
    WebKit's WebProcess to talk to the GPU directly without
    dragging GTK4 onto the unstable hardware path.
Operator-observed flipping the whole stack to gl+GPU
made Epiphany flash-and-die in ~327ms scopes. Split-renderer
(compositing-on) was attempt #3; it tripped Wayland Protocol error
71 in WebKit's WebProcess on WSLg (operator trace).
Attempt #4 -- the operator's own next-step note in this file --
is "wayland-without-compositing": KEEP wayland for GTK4 chrome,
DISABLE WebKit's GPU compositing entirely so the WebProcess stays
on its software-cairo path with no dmabuf passthrough. This
trades render perf for stability on WSLg's virtual compositor.
Attempt #6 (operator trace): attempts #1-#5 ALL kept GTK4
chrome on Wayland and ALL still hit Gdk Error 71. WSLg's Weston
Wayland is the common factor. Route Epiphany (GTK4 + WebKit) through
XWayland instead -- X11 has no Error-71 path and WSLg implements X11
popup semantics correctly. Inherits the global [graphics] x11 now;
pinned explicitly so a global flip can't silently re-break it.

<!-- mios-src:9af117a6ce16 from usr/share/mios/mios.toml:8358-8382 -->

### Attempt #7 (operator trace): on x11 the WebProcess no...

Attempt #7 (operator trace): on x11 the WebProcess no
longer hits Wayland Error 71, but Epiphany now crashes with
`ephy_embed_get_web_view: assertion failed (EPHY_IS_EMBED)` -- the
WebKitWebView never constructs (NULL embed). Root cause: the prior
override used INVALID env-var names. WEBKIT_USE_DMABUF_RENDERER is
NOT a real WebKitGTK var (so the dmabuf renderer stayed ON, and on
no-GPU WSLg the GL/dmabuf init hard-fails the WebProcess), and
WEBKIT_FORCE_SANDBOX / WEBKIT_DISABLE_HARDWARE_ACCELERATION are not
real vars either. Corrected to the TWO vars WebKitGTK actually
honours (compositing off + the REAL dmabuf-disable). Combined with
moving Epiphany to the flathub remote (coherent org.gnome.Platform
runtime, not the broken fedora f44 refs gnome-software reported).

<!-- mios-src:83cdcc6285c2 from usr/share/mios/mios.toml:8385-8396 -->

### [image] -- image references used at every layer of the...

----------------------------------------------------------------------------
[image] -- image references used at every layer of the pipeline.
  ref / branch  : Day-2 'bootc switch' target on the deployed host.
  base          : OCI base image used by Containerfile FROM.
  bib           : bootc-image-builder image used by 'just iso/qcow2/wsl2/...'
  name / tag    : remote registry path + tag for 'just push'.
  local_tag     : local podman tag for 'just build' output.
Maps to MIOS_IMAGE_REF, MIOS_BRANCH, MIOS_BASE_IMAGE, MIOS_BIB_IMAGE,
MIOS_IMAGE_NAME, MIOS_IMAGE_TAG, MIOS_LOCAL_TAG.
----------------------------------------------------------------------------

<!-- mios-src:9fc9bbdded3a from usr/share/mios/mios.toml:8459-8468 -->

### Machine-os layer (the WSL2 root podman-machine init pulls)....

Machine-os layer (the WSL2 root podman-machine init pulls). The
canonical 6.0 tag is operator-overridable via mios.html so they can
track 6.1/7.0 without bumping code.

<!-- mios-src:915a868087f3 from usr/share/mios/mios.toml:8485-8487 -->

### [deployment] -- bootc-image-builder (BIB) target formats....

----------------------------------------------------------------------------
[deployment] -- bootc-image-builder (BIB) target formats.

After the OCI image is built, mios-build-driver runs BIB once per
enabled target to render the disk image for that platform. Default
= ALL targets ON per operator instruction "deploy all
target images / build target images for ALL deployment types".

Each toggle maps to a `--type` arg passed to bootc-image-builder.
Add new targets here and the build-driver picks them up via
MIOS_DEPLOY_<TARGET> env vars (synthesized by tools/lib/userenv.sh).

Storage cost: each format produces a multi-GB artifact under
/var/lib/mios/build/output/. With all 7 targets enabled and the
image at ~6 GB compressed, expect ~30-40 GB output.
----------------------------------------------------------------------------

<!-- mios-src:de6e993a7de7 from usr/share/mios/mios.toml:8490-8505 -->

### [hwcaps] -- x86-64 microarchitecture level for...

----------------------------------------------------------------------------
[hwcaps] -- x86-64 microarchitecture level for runtime-selected
optimized libraries.

Background: Fedora ships glibc-hwcaps subpackages
(glibc-hwcaps-x86-64-v3, glibc-hwcaps-x86-64-v4) that drop alternative
.so files into /usr/lib64/glibc-hwcaps/x86-64-vN/. The dynamic linker
(ld.so) auto-selects them at process start when the host CPU advertises
the matching capability bits via AT_HWCAP / AT_HWCAP2 in the auxiliary
vector. No application changes; transparent perf uplift.

Hardware floor:
  v1 (baseline)  every x86-64 CPU since 2003 (the original AMD64 ISA)
  v2             SSE3 + SSSE3 + SSE4.1 + SSE4.2 + POPCNT
                 Intel Nehalem 2008+, AMD Barcelona 2007+
  v3             AVX + AVX2 + BMI1 + BMI2 + FMA + F16C + LZCNT + MOVBE
                 Intel Haswell 2013+, AMD Excavator 2015+, AMD Zen 1 2017+
                 AMD Ryzen 9000 series (Zen 5) supports v3 and v4
                 AMD Ryzen 7000 series (Zen 4) supports v3 and v4
                 AMD Ryzen 5000 series (Zen 3) supports v3
  v4             AVX-512 (foundation + DQ + CD + BW + VL)
                 Intel Skylake-X 2017+, Ice Lake 2019+
                 AMD Zen 4 2022+ (Ryzen 7000), Zen 5 2024+ (Ryzen 9000)

Tradeoffs:
  - v3/v4 binaries can be 5-30% faster on numeric / SIMD-heavy workloads
    (BLAS, libvips, ffmpeg, video transcoding, ML inference, blake3
    hashing, json/yaml parsing with -O3 simd codegen).
  - Storage cost: each hwcaps subpackage adds ~5-15 MB per glibc revision.
    The whole hwcaps loader infrastructure is ~30 MB combined for v3+v4.
  - Runtime cost: zero. ld.so picks the right loader at exec time; no
    branching at hot-path level.
  - Binary compat: hwcaps libraries are PURE ADDITIVE -- they never
    replace the baseline v1 .so files. Older / cross-arch binaries
    keep working.

Native rebuild (future track): MiOS may eventually compile select hot-path
packages (kernel, glibc itself, openssl, zstd, ffmpeg, mesa-vulkan-drivers)
with -march=znver4 / -march=x86-64-v4 directly instead of relying on the
hwcaps multi-build trick. That work is documented in
usr/share/doc/mios/reference/hwcaps.md and tracked as a Day-N goal.
----------------------------------------------------------------------------

<!-- mios-src:daa3a1f0a659 from usr/share/mios/mios.toml:8523-8564 -->

### Microarchitecture level. Set to "v3" or "v4" to pull the...

Microarchitecture level. Set to "v3" or "v4" to pull the matching
glibc-hwcaps-* RPMs into the image; the loader auto-selects them on
capable CPUs at boot. Operators on Zen 5 (Ryzen 9000) hosts can safely
enable "v4". Operators on Zen 1-3 hosts cap at "v3". Setting "v1"
(baseline) skips the hwcaps install entirely (smallest image, widest
CPU compat).

<!-- mios-src:116af4d794b2 from usr/share/mios/mios.toml:8566-8571 -->

### Allow ld.so glibc-hwcaps loader autoselect at runtime (the...

Allow ld.so glibc-hwcaps loader autoselect at runtime (the default).
Setting false would force baseline-only paths even when v3/v4 .so files
are present -- exists for benchmarking / regression isolation.

<!-- mios-src:c37e35527ce3 from usr/share/mios/mios.toml:8573-8575 -->

### [security] -- sealed-image and tamper-evident root knobs....

----------------------------------------------------------------------------
[security] -- sealed-image and tamper-evident root knobs.

composefs_mode controls how /usr/lib/ostree/prepare-root.conf is
rendered by automation/77-composefs-verity.sh:

  "verity"   composefs in fs-verity mode (default). Tamper-evident
             root: every ostree object is content-addressed and
             cryptographically chained back to a single trusted root
             digest. Requires the target filesystem to support
             fs-verity natively (ext4, btrfs). XFS does NOT support
             fs-verity and will fail to boot if this mode is selected
             on an XFS root.
  "yes"      composefs enabled without verity. Same content-addressed
             read-only /usr root, but no cryptographic integrity
             chain on individual objects. Works on every filesystem
             composefs supports (including XFS) and is the upstream
             FCOS / bootc default.
  "off"      do not write prepare-root.conf at all. Falls through to
             whatever the base image (ucore-hci / fedora-bootc /
             UBlue) already configured. Use this when running on a
             host that already has a custom prepare-root.conf you
             don't want MiOS to clobber.

Why this is opt-in rather than always-on:
  - On bare-metal hosts with ext4/btrfs, "verity" is the strongest
    anti-tamper posture we can ship without rebuilding userland against
    a signing key (the native-rebuild track in [hwcaps]).
  - Inside WSL2 / podman-machine / cloud images that target XFS,
    "verity" will brick the deploy. "yes" keeps the read-only-/usr
    guarantee without the verity dependency on the underlying FS.
  - Day-N+1: when sealed-image fs-verity userspace + signing-key
    plumbing lands (the "sealed-image-track" referenced in
    usr/share/doc/mios/reference/bootc-comparison.md), this same key
    gates the cryptographic boot path. Operators who already set
    "verity" today inherit it automatically; operators on "off"/"yes"
    keep their existing posture.

Default policy: "verity" matches the existing behavior of the script
before this knob was introduced (no behavior change for existing
deployments).
----------------------------------------------------------------------------
Composefs security settings -- merged into the first [security]
section below (was a duplicate [security] which strict TOML
parsers reject; the awk userenv parser tolerated it, tomllib
does not). Operator note keys preserved under the
canonical [security] section earlier in this file.

<!-- mios-src:bf5de31d31f3 from usr/share/mios/mios.toml:8583-8629 -->

### ── vLLM heavy lane (Phase 2, "both, in order" + "a large...

── vLLM heavy lane (Phase 2, "both, in order" + "a large
model for MiOS deployments with dGPUs"). The re-scoped mios-llm-heavy-alt Quadlet serves
a HEAVY TEXT reasoner over OpenAI /v1 with vLLM's PagedAttention + Automatic
Prefix Caching (APC) -- APC reuses the shared swarm system-prompt prefix across
concurrent fan-out at ~0 cost; PagedAttention is the in-GPU VRAM-compress
primitive. KV disk/CPU TIERING (the operator's "write to disk, clean state when
agents/models load/unload") is Phase 3 = +LMCache (deferred). GATED + DISABLED
BY DEFAULT: a heavy model needs real free VRAM the SHARED 4090 lacks while the
Windows host holds ~20GB (same gate as the gemma4 planner) -> enable only on a
dGPU with headroom:
  1. build with [ai.vllm].bake_model set (bakes weights OFFLINE; empty = no bloat)
  2. systemctl enable --now mios-llm-heavy-alt.service
Then [nodes.local-vllm] (health-gated) auto-joins the swarm. Recommended text
reasoners (set bake_model at build time):
  Qwen/Qwen3-8B          (~16GB fp16 / ~6GB AWQ -- mid dGPU)
  Qwen/Qwen3-30B-A3B     (MoE 30B / 3B-active -- the "large model", big dGPU + quant)
GUI-GROUNDING VLM lane (computer-use desktop click-control -- see [computer_use]):
to serve a grounding head INSTEAD of a text reasoner, set both:
  bake_model  = "ByteDance-Seed/UI-TARS-1.5-7B"   # Apache-2.0; best end-to-end PC GUI policy, absolute coords
  served_name = "mios-grounding"                  # mios-pc-vision's grounding_endpoint (:11440) targets this
Alternative grounding heads (all FOSS): Hcompany/Holo1.5-7B (dense-UI localizer),
microsoft/GUI-Actor-7B-Qwen2-VL (MIT), Qwen/Qwen3-VL-4B-Instruct (lighter).
STAGED, not baked by default: a 14GB head would bloat every bootc image + the
lane is VRAM-gated (the shared 4090 is held ~20GB by the Windows host). Set
bake_model in your /etc overlay + `systemctl enable --now mios-llm-heavy-alt` when VRAM frees.
The mios-llm-heavy-alt Quadlet reads these via MIOS_VLLM_* (rendered from here).

<!-- mios-src:5a6115ced517 from usr/share/mios/mios.toml:8631-8656 -->

### provisioned to /usr/share/mios/vllm/model....

provisioned to /usr/share/mios/vllm/model. Qwen3-30B-A3B-Instruct-2507 (MoE 30.5B-total/3.3B-active, 262144 NATIVE ctx), INT4 AWQ via vllm-project llm-compressor (~16GB). 2026-07 operator pick over Magistral-2509 (family-diverse, MoE-fast, 256k-native). Instruct = NON-thinking; swap to Qwen/Qwen3-30B-A3B-Thinking-2507 for CoT.

<!-- mios-src:6ba3e889cffc from usr/share/mios/mios.toml:8659-8659 -->

### [ai.sglang] -- the SGLang heavy lane ("continue with...

----------------------------------------------------------------------------
[ai.sglang] -- the SGLang heavy lane ("continue with SGLang").
Mirror of [ai.sglang]; the mios-llm-heavy Quadlet reads these via MIOS_SGLANG_*.
SGLang's HiCache spills inactive KV to CPU RAM -> a quantized heavy/VLM reasoner
fits the partial 4090. Gated/disabled by default; enable ONE heavy lane (vLLM OR
SGLang) on a shared GPU.

<!-- mios-src:fb1a6b5476ee from usr/share/mios/mios.toml:8669-8674 -->

### 256k NATIVE (operator-requested). Feasible on the shared...

256k NATIVE (operator-requested). Feasible on the shared 4090 via HiCache CPU KV-offload + fp8 KV (the note above); vLLM alone can't hold 256k KV in ~4GB, SGLang can by spilling to RAM.

<!-- mios-src:2a5624e429f7 from usr/share/mios/mios.toml:8682-8682 -->

### [packages] -- runtime SSOT for every dnf install in MiOS....

----------------------------------------------------------------------------
[packages] -- runtime SSOT for every dnf install in MiOS. Each
[packages.<section>] sub-table below carries a `pkgs = [...]` array;
automation/lib/packages.sh resolves them via the documented overlay
chain (MIOS_TOML override -> ~/.config -> /etc/mios -> /ctx/mios-bootstrap
-> /usr/share/mios -> /ctx/usr/share/mios). The configurator HTML at
/usr/share/mios/configurator/mios.html is the operator-facing WYSIWYG
editor for the same TOML. PACKAGES.md (now under
usr/share/doc/mios/reference/PACKAGES.md) is human-readable
documentation only -- the legacy fenced ```packages-<cat>``` fallback
was removed in v0.3.0.

  sections        sections to install on a deployed MiOS host (image-time).
  dev_overlay     subset to install on the Windows-side MiOS-DEV podman
                  backend. Empty/unset = use a minimal sane default
                  (no GNOME shell, no Phosh, no gaming -- the dev VM is
                  a podman backend, not a desktop session; operators see
                  GUIs via flatpak windows routed through WSLg, e.g.
                  org.gnome.Ptyxis terminal).

Always-skipped (regardless of selection): kernel, boot, moby, bloat,
critical -- these are either WSL-incompatible or anti-pattern fence
sections.
----------------------------------------------------------------------------

<!-- mios-src:bd5566189dd4 from usr/share/mios/mios.toml:8687-8710 -->

### Master inclusion list -- the build pipeline installs every...

Master inclusion list -- the build pipeline installs every section
named here. Each [packages.<section>] table now also has its own
`enable = true|false` field; the build resolver respects BOTH (a
section is installed only if its name appears here AND its enable
flag is true). The configurator HTML toggles enable; the array
stays as the canonical "what groups exist". To add a new section
permanently, add it both here and as [packages.<section>] below.

Default = EVERYTHING ON except bloat (per operator instruction
"MiOS Defaults are all pre-checked on, excluding bloat
and including everything else -- steamos, proton/wine11+, ALL the
self; dev, build, host, hosting, run, deploy"). The configurator
pre-checks every box on first paint.

<!-- mios-src:69c3bdbc057d from usr/share/mios/mios.toml:8712-8724 -->

### Windows-side winget package list installed by...

Windows-side winget package list installed by mios-bootstrap's
Get-MiOS.ps1 Pass-1 (current-user scope). Read by the bootstrap
at install time -- this is the SSOT for "what gets installed on
the operator's Windows host"; the hardcoded list previously in
Get-MiOS.ps1 has been removed in favor of this section per
operator instruction "ALL Global packages SOURCE FROM THE
TOML/HTML FILE!!!".

To override per-operator: drop a [packages.windows] table in
~/.config/mios/mios.toml with your own pkgs = [...] -- replaces
this list field-for-field per the layered TOML resolver.

Default = strictly-needed runtime/toolchain + MiOS terminal CLI
surface only. No browser/editor/utility GUIs (operator brings
their own). Bloat-free per 2026-05 directive.

<!-- mios-src:279249f8b5c0 from usr/share/mios/mios.toml:8737-8751 -->

### ─── Browser AI: Zen Twilight wired to the MiOS OWUI...

─── Browser AI: Zen Twilight wired to the MiOS OWUI pipeline ─────────────────
Installs Zen Browser (Twilight channel, Firefox-based) on the Windows host and
points Firefox/Zen's built-in AI chatbot SIDEBAR at the local OWUI / MiOS-Agent
pipeline -- MiOS AI, natively in the browser. Applied by mios-bootstrap
(install-host-tools.ps1 Configure-MiosBrowserAI): installs `package` via winget,
then writes these as a per-profile user.js (the reliable method) plus a
best-effort distribution/policies.json, so Zen's AI sidebar drives the MiOS
pipeline. All operator-tunable here (SSOT); the installer hardcodes nothing.

<!-- mios-src:b448def3cb2f from usr/share/mios/mios.toml:8794-8801 -->

### The AI Window (Smart Window) CUSTOM model endpoint is...

The AI Window (Smart Window) CUSTOM model endpoint is configured UI-side
(Settings > AI Controls > Smart Window Settings > Assistant model > Custom:
Use your own LLM). Point it at the MiOS agent-pipe -- a clean keyless
OpenAI-compatible /v1 that runs the full refine->Hermes->polish chain:
    Model endpoint : http://localhost:8700/v1
    Model name     : MiOS-Agent
    API key        : (leave blank -- not required)
NB: OWUI's own /api path 500s on plain OpenAI API calls (a known OWUI-core
'NoneType.startswith' bug in process_chat), so the agent-pipe is the correct
BYOM target. provider_url below still wires the older sidebar-chatbot path
(which loads OWUI's web UI in the sidebar, not via the API).
provider_url above is emitted as browser.ml.chat.provider. The bootstrap
applies these as a per-profile user.js (the reliable method -- some
browser.ml.chat.* prefs do not apply via policies.json) plus a best-effort
distribution/policies.json for profiles created on first launch.

<!-- mios-src:1d51042a0eb3 from usr/share/mios/mios.toml:8819-8833 -->

### Minimum DNF package set installed into podman-MiOS-DEV at...

Minimum DNF package set installed into podman-MiOS-DEV at Phase-3
provisioning so the build pipeline can RUN -- mkpasswd / openssl /
passlib for password hashing, bootc for the self-replication
closure, git for the in-distro clone, iptables/nftables for
netavark networking, fastfetch + oh-my-posh + bash-completion for
the MiOS terminal experience pre-bootc-switch.

This is the SEED layer; full feature parity (every package in
every other [packages.<section>] above) lands via bootc switch
at end of mios-build-driver per feedback_mios_dev_equals_mios.md.
To customize, drop a [packages.dev_vm_essentials] table in a
higher-precedence layer with your own pkgs list.

<!-- mios-src:5ab92cbaae59 from usr/share/mios/mios.toml:8836-8847 -->

### MiOS-DEV (podman-WSL2 backend on Windows)...

MiOS-DEV (podman-WSL2 backend on Windows) minimal-but-complete:
every operator/dev/security daemon + the GPU CDI plumbing for /dev/dxg
+ the GNOME Flatpak runtime (portals/audio/theming) so the GNOME
Flatpaks (Ptyxis, Nautilus, Software, Epiphany, Flatseal) routed through
WSLg can render with file dialogs / audio / Adwaita theming intact.
NO full GNOME session (no gnome-shell / GDM / control-center) -- the
dev VM is a podman backend, not a workstation; the Windows compositor
IS the WSLg surface.

<!-- mios-src:5976c86b0af5 from usr/share/mios/mios.toml:8868-8875 -->

### [packages.<section>] -- DEFINITIVE SSOT (v0.3.0+) Every DNF...

----------------------------------------------------------------------------
[packages.<section>] -- DEFINITIVE SSOT (v0.3.0+)

Every DNF package the build pulls is enumerated below. PACKAGES.md is
now a documentation shim that points operators at this file (it stayed
in mios.git for human-readable docs but no longer drives package
selection). The packages.sh resolver (automation/lib/packages.sh)
reads `[packages.<section>].pkgs` from the layered TOML chain:

  ~/.config/mios/mios.toml   per-user override     (highest precedence)
  /etc/mios/mios.toml        host/admin override
  /usr/share/mios/mios.toml  vendor defaults       (THIS file -- lowest)

To override a section, drop a [packages.<section>] table in a higher
layer with your own pkgs = [...] list -- TOML doesn't merge tables, so
the user-level entry replaces the vendor list field-for-field.
----------------------------------------------------------------------------

<!-- mios-src:d7357e19c19e from usr/share/mios/mios.toml:8886-8902 -->

### ────────────────────────────────────────────────────────────...

─────────────────────────────────────────────────────────────────────
[packages.*] -- DEFINITIVE SSOT for the MiOS package surface.
Each section below is a DNF install list. The packages.sh resolver
(automation/lib/packages.sh) consumes these tables; PACKAGES.md is
now a documentation shim that points operators here.
─────────────────────────────────────────────────────────────────────

<!-- mios-src:8143764a0d60 from usr/share/mios/mios.toml:8904-8909 -->

### python3.13

python3.13: hermes-agent requires Python <3.14 but F44's python3 is 3.14;
72-hermes-agent.sh builds the shared agent venv with this when present
(degrade-open to python3). --skip-unavailable keeps it safe if F44 names it
differently (rebuild fix).

<!-- mios-src:e2ff916bf722 from usr/share/mios/mios.toml:8975-8978 -->

### Without dconf + gsettings-desktop-schemas +...

Without dconf + gsettings-desktop-schemas + adwaita-icon-theme +
gnome-themes-extra, GTK apps fall back to a "GTK2-era" Adwaita default
(no icons, light theme only, no color-scheme propagation) -- a full
GNOME session pulls these as gnome-shell deps, but the dev_overlay
explicitly drops gnome-shell, so they have to be listed here. gnome-
keyring provides the Secret Service portal that epiphany / geary /
vscode-flatpak need to store credentials.

<!-- mios-src:51400f8b506b from usr/share/mios/mios.toml:9025-9031 -->

### GNOME Software ships from Fedora repos as an RPM, NOT from...

GNOME Software ships from Fedora repos as an RPM, NOT from Flathub.
The Flathub `org.gnome.Software` ID returns "Nothing matches" as
of 2026-05 -- delisted/renamed. dnf-installed gnome-software still
surfaces Flathub apps (and any other configured remote) via its
PackageKit + flatpak plugins, so the operator-facing UX is the
same; just the install channel is the Fedora vendor.

<!-- mios-src:7d7d8948dfa4 from usr/share/mios/mios.toml:9063-9068 -->

### CUA capture backends for mios-computer-use (cu_screenshot /...

CUA capture backends for mios-computer-use (cu_screenshot / cu_ground).
mios-computer-use probes: Screenshot PORTAL first (xdg-desktop-portal-gnome
ships with GNOME), then these CLI fallbacks -- grim for wlroots sessions
(sway/Hyprland), gnome-screenshot for GNOME. Without one of these the verb
returns "no working capture backend" (verified live). NOTE: the
WSLg dev VM's Weston supports NEITHER wlr-screencopy NOR a Screenshot portal
("compositor doesn't support the screen capture protocol"), so the dev VM
still cannot capture; bare-metal/VM Wayland MiOS (GNOME or wlroots) can.

<!-- mios-src:4f20b780b70e from usr/share/mios/mios.toml:9070-9077 -->

### Full Cockpit suite + PCP stack. cockpit-packagekit is...

Full Cockpit suite + PCP stack. cockpit-packagekit is intentionally
omitted because PackageKit is in [packages.bloat] (bootc + flatpak
handle updates on MiOS). pcp-zeroconf flips the preset on pmlogger/
pmproxy so collection runs out of the box.

Cockpit Metrics HISTORY (cockpit 361, Fedora 44) reads time-series via
pmproxy -> pmseries, which REQUIRES a redis-compatible key-server
`keydb` here. Without a key-server the Metrics tab renders "history
could not be loaded" / "pmlogger.service is failing to collect data"
even though pmlogger IS collecting (the data is fine; the query backend
is missing). keydb 6.3 works with PCP 7.1; valkey 9.x is protocol-
incompatible (closes the pmproxy connection), so pin keydb. (
regression fix: no key-server was in the list, so history broke.)
NOTE: there is NO `cockpit-pcp` package in Fedora 44 (retired/merged
into cockpit-system) -- do not re-add it; install_packages_strict skips
the unknown name but it is dead weight.

<!-- mios-src:7a067a58bd70 from usr/share/mios/mios.toml:9220-9235 -->

### ttyd -- C/libuv pty-over-WebSocket bridge backing the MiOS...

ttyd -- C/libuv pty-over-WebSocket bridge backing the MiOS Portal's
inline browser terminals (mios-ttyd-bash :7681 / -powershell :7682; see
[ttyd] above). Was configured + unit-enabled but NEVER in any package
list, so the binary was absent and both units skipped on
ConditionPathExistsGlob=/usr/?bin/ttyd (portal
"Terminals 0/2 up"). Fedora pkg, installs /usr/bin/ttyd.

<!-- mios-src:e44f5a745bb8 from usr/share/mios/mios.toml:9259-9264 -->

### SteamOS-equivalent gaming surface

SteamOS-equivalent gaming surface: Steam + Proton (via RPM Fusion's
steam package; flatpak Steam at com.valvesoftware.Steam is layered
in [packages].flatpaks for the SteamOS-style sandbox), Wine, Lutris,
gamescope (Valve compositor), mangohud (perf overlay).
Default ON per operator instruction "steamos, proton/wine11+, ALL".
RPM Fusion (in [packages.repos]) is the source for steam/wine RPMs.

<!-- mios-src:0b0e55270bee from usr/share/mios/mios.toml:9312-9317 -->

### fuse-overlayfs

fuse-overlayfs: rootless-podman storage driver for environments
where the kernel overlayfs isn't accessible -- specifically a
MiOS-DEV podman-machine WSL distro running Quadlet containers
against bind-mounted /var. Without it `podman run` against a
rootless image fails with `creating overlay mount: fuse-overlayfs:
cannot mount: No such file or directory` (the literal failure
mode visible in the deployed-host journal for mios-forge).

<!-- mios-src:7b1654f54ed8 from usr/share/mios/mios.toml:9447-9453 -->

### AI assistant CLIs installed globally via npm. ON by default...

AI assistant CLIs installed globally via npm. ON by default --
operator can remove from this list to skip. Each entry is an npm
package id (passed to `npm install -g`). Installed by
/usr/libexec/mios/install-ai-clis.sh which runs during the overlay
phase (build-mios.ps1) and is operator-re-runnable any time.

<!-- mios-src:81c62f52fd52 from usr/share/mios/mios.toml:9568-9572 -->

### [packages.glibc-hwcaps-v3] / [packages.glibc-hwcaps-v4]...

----------------------------------------------------------------------------
[packages.glibc-hwcaps-v3] / [packages.glibc-hwcaps-v4]

Optional sections gated by [hwcaps].level. Pulled into the install set by
automation/lib/packages.sh when [hwcaps].level == "v3" or "v4". Skipped
(or installed best-effort if --skip-unavailable in dnf) for hosts where
the matching glibc-hwcaps subpackage isn't shipped in the active Fedora
release -- Fedora's hwcaps packaging cadence has been uneven, and
secureblue / x86-64-v3 derivative projects sometimes carry COPR rebuilds
instead. dnf's --skip-unavailable + --skip-broken handle the gap.

Hardware floor:
  v3:  Intel Haswell 2013+ / AMD Zen 1+ (most consumer CPUs from the
       last decade). Recommended for the canonical MiOS image.
  v4:  Intel Skylake-X / Ice Lake / AMD Zen 4+. Required: AVX-512.
       Recommended for HCI / compute / inference workloads on Zen 4-5.

Operators enable by editing /etc/mios/mios.toml:
    [hwcaps]
    level = "v3"   # or "v4"
    [packages]
    sections = [..., "glibc-hwcaps-v3"]   # or "glibc-hwcaps-v4"
and re-running `just build`.
----------------------------------------------------------------------------

<!-- mios-src:c56abab10367 from usr/share/mios/mios.toml:9631-9654 -->

### [colors] -- MiOS unified palette applied to every console /...

----------------------------------------------------------------------------
[colors] -- MiOS unified palette applied to every console / terminal /
tty surface (bash, zsh, PowerShell, Windows Terminal, Ptyxis, Cockpit,
the configurator HTML, the oh-my-posh prompt, fastfetch logo color).
Sourced from:
  - Operator neutrals: #1A407F deep-blue, #E0E0E0 silver,
    #B7C9D7 pale blue-grey, #948E8E warm grey, #734F39 brown
  - Hokusai "The Great Wave off Kanagawa": #3E7765 wave-green,
    #E7DFD3 foam-cream, #F35C15 sunset-orange, #DC271B coral-red,
    #282262 deep-indigo
Combined into one coherent palette where every tone has a role.
/etc/profile.d/mios-colors.sh emits OSC-4 / OSC-10 / OSC-11 / OSC-12
escape sequences at every interactive shell start so the operator's
terminal repaints to MiOS palette regardless of which emulator
launched it. Ptyxis / GNOME Terminal also read this same TOML via
the configurator HTML when the operator picks a custom override.
----------------------------------------------------------------------------

<!-- mios-src:ef0602ad15d8 from usr/share/mios/mios.toml:9668-9684 -->

### INFRASTRUCTURE CONSTANTS — migrated from...

============================================================================
INFRASTRUCTURE CONSTANTS — migrated from /usr/share/mios/env.defaults
============================================================================
These sections capture every operator-tunable infrastructure constant
that previously lived in env.defaults. Per the project's TOML-as-
singular-SSOT directive, mios.toml is now the canonical source for
ports / sidecar pins / service identities / runtime paths / build
tunables. tools/lib/userenv.sh emits MIOS_* env vars from these
sections; consumer scripts source userenv.sh and read the env vars.

Hardcoded values that could live in mios.toml are bugs.
============================================================================

<!-- mios-src:1a02cd01bb1b from usr/share/mios/mios.toml:9686-9697 -->

### [ports] -- canonical port allocations. MUST stay in sync...

----------------------------------------------------------------------------
[ports] -- canonical port allocations. MUST stay in sync with
automation/44-firewall-ports.sh (firewall-offline-cmd at build time)
and automation/45-firewall.sh (runtime mios-firewall-init). Both
consume MIOS_PORT_* env vars synthesized from these slots by
tools/lib/userenv.sh, so editing here flows through end-to-end.

Service access surface contract: every service binds 0.0.0.0 inside
its Quadlet and the firewall is what gates LAN reachability. See
usr/share/mios/ai/INDEX.md §5b.
----------------------------------------------------------------------------

<!-- mios-src:ae9f872d5a06 from usr/share/mios/mios.toml:9699-9709 -->

### [ports.categories] -- THE NUMBERING SSOT. Ports are not...

----------------------------------------------------------------------------
[ports.categories] -- THE NUMBERING SSOT.

Ports are not hand-assigned. Each category declares its OWN base and its OWN
stride, and every member's port is DERIVED at resolve time:

    port(member) = base + (index_in_members * stride) + (stack_id * 10000)

`members` is ORDERED -- the order IS the numbering. An operator retargets an
entire category by changing ONE number (its base): set
[ports.categories.agent].base = 9200 and the whole agent plane moves together,
collision-free, with no other edit anywhere in the tree.

`pinned` holds ports fixed by an external protocol contract (DNS/53). Pinned
ports never shift -- not by base, not by stride, not by stack_id.

The flat [ports] table above is the RENDERED PROJECTION of this schema. It is
regenerated (tools/render-ports.py), never hand-edited, and check 129
(check_ports_category_schema) fails the build if the two disagree, if a port
belongs to no category or two, or if two categories' bands overlap.
----------------------------------------------------------------------------

<!-- mios-src:ff1807ac3745 from usr/share/mios/mios.toml:9767-9787 -->

### [units] -- systemd unit names. Previously hand-typed in...

----------------------------------------------------------------------------
[units] -- systemd unit names. Previously hand-typed in BOTH
automation/lib/globals.sh and globals.ps1; SSOT here so both are generated.
----------------------------------------------------------------------------

<!-- mios-src:5db725aedd68 from usr/share/mios/mios.toml:9871-9874 -->

### [versions] -- SSOT version definitions for non-image...

----------------------------------------------------------------------------
[versions] -- SSOT version definitions for non-image software components,
DNF repo targets, tool pins, and system components (WS-FLOAT campaign).
Cascades into MIOS_VERSION_* environment variables via userenv.sh.
----------------------------------------------------------------------------

<!-- mios-src:84b265d1ea0f from usr/share/mios/mios.toml:9931-9935 -->

### rancher/k3s lives ONLY on docker.io (no quay.io/ghcr.io...

rancher/k3s lives ONLY on docker.io (no quay.io/ghcr.io mirror). The
`docker.io/` prefix is mandatory: without it, podman treats the value
as a short name and refuses to silently resolve to docker.io inside
the OCI bake step (no TTY -> "short-name resolution enforced but cannot
prompt without a TTY"), failing the entire `bootc install-to-filesystem`
stage downstream (operator-confirmed every other sidecar
entry in this section was already fully qualified; k3s was the only
regression and broke ALL deployment artifacts). Keep the registry prefix.

<!-- mios-src:22abf1a75511 from usr/share/mios/mios.toml:9951-9958 -->

### web-tools POD ("consolidate containers to share similar...

web-tools POD ("consolidate containers to share similar
services together" + "co-locate the real firecrawl stack" + "make it a pod").
mios-webtools is now a podman POD (usr/share/containers/systemd/
mios-webtools.pod, Network=host) with FOUR member containers instead of one
fat supervisord image:
  * redis            docker.io/redis:7-alpine            (loopback :6379)
  * firecrawl-api    localhost/mios-firecrawl:v1.0.0     (:3002, Hermes's
                     native FIRECRAWL_API_URL backend; cmd start:production)
  * firecrawl-worker SAME firecrawl image                (cmd: pnpm run workers)
  * crawl4ai         localhost/mios-crawl4ai-slim:latest (:11235, the `crawl`
                     verb backend, Chrome-CDP primary + camoufox fail-retry)
It REPLACES the prior single-purpose mios-crawl4ai image AND the abandoned
fat mios-webtools monolith (the supervisord Containerfile + its quadlet were
git-rm'd on the pod cutover). Two LOCALLY-BUILT images, no upstream registry
pin to render here:
  * firecrawl   built from usr/share/mios/webtools/firecrawl.Containerfile,
                which clones + builds firecrawl's OWN apps/api at the PINNED
                tag (ARG FIRECRAWL_REF=v1.0.0); quadlets default to
                localhost/mios-firecrawl:v1.0.0 via ${MIOS_FIRECRAWL_IMAGE}.
  * crawl4ai    built from usr/share/mios/crawl4ai/Containerfile; quadlet
                defaults to localhost/mios-crawl4ai-slim:latest via
                ${MIOS_CRAWL4AI_IMAGE}.
See [verbs.crawl], [ports].crawl4ai + [ports].firecrawl, and
[services.webtools] (uid 824) below.

<!-- mios-src:27c826ca51f0 from usr/share/mios/mios.toml:9963-9986 -->

### WS-9 unified agent-plane DB. pgvector/pgvector bundles the...

WS-9 unified agent-plane DB. pgvector/pgvector bundles the `vector` extension
on upstream postgres (FOSS: PostgreSQL License). FLOATS on the `pgNN` family
tag (ADR-0012): the newest pgvector for that PG major, resolved at build and
digest-recorded in the SBOM -- no hand-pinned version to rot. Newest always
satisfies hnsw.iterative_scan (pgvector 0.8.0+), which the Quadlet Exec= sets
unconditionally.
The `pgNN` suffix names the PostgreSQL MAJOR, which cannot float freely: a
newer-major image refuses to start on an older PGDATA. mios-pgvector-major-
upgrade.service is what makes the major movable -- on a mismatch it dumps the
old cluster with the OLD image into [pgvector].restore_sql and stashes the old
data dir so the new major initdb's and replays the dump. Degrade-open: if it
cannot dump, it touches nothing and the container stops on Postgres's own
major-mismatch error rather than losing data.

<!-- mios-src:bb7ac5852c16 from usr/share/mios/mios.toml:9999-10011 -->

### [services.<svc>] -- per-service identity (UID / GID /...

----------------------------------------------------------------------------
[services.<svc>] -- per-service identity (UID / GID / username) baked
at OVERLAY TIME via /usr/lib/sysusers.d/*.conf + automation/11-user.sh
+ /usr/lib/tmpfiles.d/mios-user.conf. Never propose runtime patches
to /etc/passwd / /etc/subuid / /etc/subgid in firstboot scripts —
the principle is "native Fedora user creation at overlay time".
Numeric UID allocations match /usr/lib/sysusers.d/mios-*.conf.
----------------------------------------------------------------------------

<!-- mios-src:a300624df149 from usr/share/mios/mios.toml:10045-10052 -->

### [services.webtools] -- the consolidated web-tools container...

[services.webtools] -- the consolidated web-tools container (mios-webtools:
firecrawl + crawl4ai + camoufox). Renamed from [services.crawl4ai] on the
consolidation. The user/uid is KEPT as mios-crawl4ai/824 to avoid
churning /usr/lib/sysusers.d/50-mios-services.conf + tmpfiles + the live
passwd db (the container runs root-in-namespace anyway; this uid owns the
host-side cache/state dirs /var/{lib,cache}/mios/crawl4ai). Slot map exports
MIOS_WEBTOOLS_USER/UID/GID (userenv.sh).

<!-- mios-src:2b40bc905d12 from usr/share/mios/mios.toml:10102-10108 -->

### [pods.*] -- co-resident container GROUPS (WS-7 "pods as...

----------------------------------------------------------------------------
[pods.*] -- co-resident container GROUPS (WS-7 "pods as SSOT"). Each entry
declares a set of containers that must be scheduled together in ONE podman pod
(shared network namespace / lifecycle). The .pod Quadlet under
usr/share/containers/systemd/<name>.pod is GENERATED from this section by
tools/generate-pod-quadlets.py (drift-gated in 98-drift-checks.sh) so the pod
definition can't drift from SSOT; each member .container still declares its own
`Pod=<name>.pod` membership. tools/generate-k3s-manifests.sh then projects the
LIVE pods to k3s (the runtime half), so the cluster path is one bridge removed
from the same SSOT. Fields: description, network ("host"|"private"), after[],
wants[], wanted_by[], members[] (documented; the .container files wire it), doc.
----------------------------------------------------------------------------

<!-- mios-src:05f10273b3bb from usr/share/mios/mios.toml:10124-10135 -->

### [adguard] -- AdGuard Home DNS sinkhole config (SSOT)....

----------------------------------------------------------------------------
[adguard] -- AdGuard Home DNS sinkhole config (SSOT). Rendered into
/etc/mios/adguard/AdGuardHome.yaml by usr/libexec/mios/mios-adguard-firstboot,
which ALSO discovers + injects the live Tailscale IP (bind_hosts) and MagicDNS
suffix (split-DNS) at boot -- host-specific values that can't be baked at image
build time. Everything here is open-source. Complements CrowdSec: CrowdSec
firewalls malicious IPs (nftables bouncer), AdGuard sinkholes ad/tracker/
malware DOMAINS at resolve time.
----------------------------------------------------------------------------

<!-- mios-src:5a39fea3f0d5 from usr/share/mios/mios.toml:10193-10201 -->

### ──── FHS roots + the dirs derived from them...

──── FHS roots + the dirs derived from them ─────────────────────────
These were the last block of hand-typed constants living ONLY in
automation/lib/globals.sh and globals.ps1 (two divergent copies). They are
SSOT now so those two files can be fully generated. `${...}` placeholders are
expanded by the renderer into whichever language it is emitting, so a root
moves once here and every derived path follows.

<!-- mios-src:7d308b0d1f65 from usr/share/mios/mios.toml:10255-10260 -->

### ──── Windows-side paths consumed by mios-find /...

──── Windows-side paths consumed by mios-find / mios-windows ────────
Operator directive "I DON'T WANT ANY HARDCODED PATHS OR
WORDS!!! SKILLS AND TOOLS ARE TEMPLATES FOR ANY VARIABLES!!!". Lifted
out of mios-find (es.exe probe list) + mios-windows (powershell.exe
full path). Operators override in /etc/mios/mios.toml [paths] = ...

<!-- mios-src:13a85fd8f729 from usr/share/mios/mios.toml:10295-10299 -->

### Recommended Everything command-line (ES / es.exe) release....

Recommended Everything command-line (ES / es.exe) release. es.exe is a
WINDOWS-HOST tool the operator installs (voidtools.com/downloads#cli) -- it is
NOT built or shipped by this image -- so this pin is the SSOT the runtime hint
surfaces when Everything is unreachable (an es.exe too old for the running
Everything's IPC returns "Error 8: IPC window not found"). Newer ES builds add
Everything 1.5 + Journal support and stay compatible with 1.4.x. Bump here.

<!-- mios-src:46591010d7f2 from usr/share/mios/mios.toml:10310-10315 -->

### Windows PowerShell full path -- systemd user services have...

Windows PowerShell full path -- systemd user services have stripped
PATH that excludes /mnt/c/Windows/System32 (operator-confirmed
regression bash: line 1: powershell.exe: command not
found from broker).

<!-- mios-src:51d695e601ae from usr/share/mios/mios.toml:10318-10321 -->

### [flatpak.app_overrides."<app-id>"] -- per-app flatpak env...

----------------------------------------------------------------------------
[flatpak.app_overrides."<app-id>"] -- per-app flatpak env overrides.

Operator directive "EVERYTHING IS DICTATED AND UNDERSTOOD
FROM THE mios.toml/html file(s)". Per-app render / GPU / WebKit envs
previously lived as standalone files at var/lib/flatpak/overrides/<id>;
now they live HERE in the SSOT, and mios-flatpak-overrides-apply
materializes the per-app override files at boot. Operators add or
tune by editing this section in mios.html or directly in TOML.

Each [flatpak.app_overrides."<app-id>"] sub-table is a flat key=value
map of environment variables. The apply script writes
  /var/lib/flatpak/overrides/<app-id>
with an [Environment] section containing every key in the table.

Add a per-app override ONLY when global flatpak defaults (set by
mios-flatpak-overrides-apply from [appearance] + WSLg defaults)
don't work for a specific app. Most apps need no entry here.
----------------------------------------------------------------------------

<!-- mios-src:c45b6b3ec65e from usr/share/mios/mios.toml:10331-10349 -->

### NOTE

NOTE: per-app overrides for desktop apps now live in [[desktop.apps]]
entries (overrides = {...}). The [flatpak.app_overrides."<id>"]
table below is the legacy / non-desktop-app fallback (services,
infrastructure flatpaks, anything not in [[desktop.apps]]). The
apply script reads BOTH sources; [[desktop.apps]] shadows on
conflict so operator-overlay app entries win cleanly.

(no current entries -- Epiphany overrides moved to [[desktop.apps]])

<!-- mios-src:f0a4050218cf from usr/share/mios/mios.toml:10351-10358 -->

### [mios-find.aliases] -- CANONICAL Linux/freedesktop role ->...

----------------------------------------------------------------------------
[mios-find.aliases] -- CANONICAL Linux/freedesktop role -> app map.

Operator directive "DONT USE HARDCODED KEY WORDS AT
ALL ANYWHERE!!!! Linux natively tags applications to its
environments defaults -- linux defaults things to global verbs
like; web, files, email, documents, etc-etc and are all mapped
to local applications in Linux environments. THAT is what the
toml/html dictates and changes -- AGENTS SEE THAT WEB = EPIPHANY
FLATPAK, FILES = NAUTILUS -- ETC-ETC".

So: ONE entry per Linux global verb (no synonyms, no "a browser"
/ "the browser" / "my browser" bloat). The AGENT is responsible
for mapping natural language ("open my browser", "fire up chrome",
"the web app") to the canonical verb ("web") -- that's freedesktop
/ xdg knowledge every LLM already has.

Future: this table will be AUTO-DERIVED from [[desktop.apps]]
entries where role is set and default = true. For now it's a
small manually-maintained map of the freedesktop standard roles.
Operators add per-host overrides at /etc/mios/mios.toml or
per-user at ~/.config/mios/mios.toml.

Future-future: mios-find itself will query Linux-native default-app
infrastructure (xdg-settings, xdg-mime, gio mime) at lookup time
so the SoT is the actual system state, not a duplicate table.
----------------------------------------------------------------------------
App-TYPE defaults (every application type has a default in
mios.toml, user-switchable by telling the AI; Linux apps first for most, Windows
for games/windows-specific, BOTH for system apps; agents discern intent from
environment context -- NO hardcoded keyword lists). os_pref tells the launcher/
agent which side to prefer: linux-first | windows | both. `default` = the Linux/
primary app id (resolved via [mios-find.aliases]/[[desktop.apps]]); windows_default
= the app when the agent discerns Windows intent ("my browser", a Windows-only app).
A per-user ~/.config/mios/mios.toml override (written by the app_default verb) wins.

<!-- mios-src:fda46806bac5 from usr/share/mios/mios.toml:10360-10394 -->

### MiOS configurator UI (mios.html). The agent's natural...

MiOS configurator UI (mios.html). The agent's natural phrasings
("open mios.html", "open the configurator", "customize MiOS",
"open MiOS settings") all need to reach the same launcher:
/usr/libexec/mios/mios-html -- a shim that resolves the WSL UNC
path and dispatches Start-Process through mios-windows to the
operator's default Windows browser. Operator-flagged
agent claimed mios.html "isn't installed" and suggested a fake
`dnf install MiosGUI` package; the aliases below remove the
lookup ambiguity so mios-find resolves them to a launch line.

<!-- mios-src:fdbac068a8c3 from usr/share/mios/mios.toml:10481-10489 -->

### Cross-platform installer. Single entry point that fronts...

Cross-platform installer. Single entry point that fronts winget
(Windows) + dnf (Fedora RPM) + flatpak (Flathub). Auto-detects the
right backend from the package-id shape: "Microsoft.PowerToys" ->
winget, "org.mozilla.firefox" -> flatpak, "vim" -> dnf. Operator
directive "mios-installer should be able to use windows
CMD and Linux BASH for installing applications on their respective
platforms (using winget install, winget search, etc-etc)".

<!-- mios-src:b1dd82dffae3 from usr/share/mios/mios.toml:10496-10502 -->

### Screenshot — every "take a screenshot" / "snap a window" /...

Screenshot — every "take a screenshot" / "snap a window" / "screen
capture" / "save the screen" intent flows through mios-screenshot.
That shim writes a PNG to the operator's Windows Pictures/Screenshots
folder via mios-pc-control screenshot (System.Drawing.Bitmap +
CopyFromScreen on the Windows side). Operator-flagged
agent burned 6 minutes trying `screencapture.exe`, `Invoke-
Screenshot`, broken PowerShell pipelines and gave up with "Windows
screenshot tools aren't available in this WSL environment". The
tools WERE available; mios-screenshot makes the surface obvious.

<!-- mios-src:fbced53782dd from usr/share/mios/mios.toml:10508-10516 -->

### Window-manipulation verbs. mios-window resolves a...

Window-manipulation verbs. mios-window resolves a title-pattern to a
hwnd via window-list, then dispatches mios-pc-control window-*.
Launches already auto-center via mios-windows launch's URI/.exe
branches; post-launch move/center/focus/resize/min/max/restore flow
through this shim. Operator directive "make sure window
moving is active/functional and can launch things centered by
default and that it can be told to move the windows".

<!-- mios-src:14d130b7c270 from usr/share/mios/mios.toml:10523-10529 -->

### SteamCMD wrapper. ONE verb for any Steam-side operation...

SteamCMD wrapper. ONE verb for any Steam-side operation: install /
uninstall / update / validate / status / info / login / list /
search / path. Two install routes: `uri` (operator-friendly,
steam://install/<appid> -> Steam GUI prompt -- works for any owned
game), and `cmd` (headless SteamCMD, auto-installs Valve.SteamCMD
via winget if missing, works for free + dedicated-server content
under anonymous login). Operator directive "make a
steamCMD a native tool for handling steam CMD commands GLOBALLY".

<!-- mios-src:5131f439c439 from usr/share/mios/mios.toml:10536-10543 -->

### Markdown editor + live preview window. Self-hosted viewer...

Markdown editor + live preview window. Self-hosted viewer at
/usr/share/mios/markdown/index.html (vendored snarkdown, no CDN);
mios-md opens it via Start-Process in the operator's default
browser, optionally pre-loaded with a file or inline text.
Complements OWUI's inline markdown rendering -- this is the
standalone surface for ad-hoc note editing + previewing.
Operator directive "react windows for markdown to
markup text in OWUI also".

<!-- mios-src:f1d23704682f from usr/share/mios/mios.toml:10549-10556 -->

### [mios-find.ranker] -- SSOT for the mios-find...

----------------------------------------------------------------------------
[mios-find.ranker] -- SSOT for the mios-find launch-disambiguation ranker.
mios-find resolves "launch <app>" to ONE launch command by scoring every
inventory entry, then picking the lowest (best) score. The score is
(match-tier, category-priority, length-tiebreak). These tables are the SSOT
for that scorer so the winner-selection weights live in config, not baked in
code (a hand-rolled weight map is a hardcode). Each key documents the default;
the defaults equal the historical in-code values, so behaviour is unchanged
until an operator overrides them.

tiers: the match-type ORDERING. Lower index = stronger match = wins. Each
name maps to a check the ranker performs against the candidate's name/desc:
  name_exact   name == query
  name_prefix  name starts with query
  name_word    query at a word boundary in name
  name_substr  query anywhere in name
  desc_word    query at a word boundary in description
  desc_substr  query anywhere in description
  fuzzy        bounded-Levenshtein token match (typo tolerance)
Reorder/remove entries to re-rank match strength; an omitted tier disables
that match class. Any check whose name is absent from this list is skipped.

<!-- mios-src:63e6b00cfb37 from usr/share/mios/mios.toml:10563-10583 -->

### fuzzy_max_edit_ratio

fuzzy_max_edit_ratio: cap edits as a FRACTION of the query-token length, so a
short query cannot fuzzy-match a semantically different app at the flat cap
(e.g. "forza" vs "forge" is 2 edits = 40% of a 5-char word -> rejected at
0.34, while long-name typos still get up to fuzzy_max_edit_distance edits).

<!-- mios-src:7e7be2b67087 from usr/share/mios/mios.toml:10599-10602 -->

### [compliance] -- OpenSCAP scan-only build gate (BOOT-02)....

----------------------------------------------------------------------------
[compliance] -- OpenSCAP scan-only build gate (BOOT-02). When enabled, the
automation/86-oscap-compliance.sh build step runs `oscap xccdf eval` against an
SSG datastream and FAILS the build if any rule at/above severity_gate FAILS.
Scan-only: openscap-scanner + scap-security-guide are already in
[packages.security] (no new package). DEFAULT OFF + degrade-open: disabled means
the build step exits 0 and is a complete no-op. ARF + HTML reports are baked
under report_path (in the image, NOT /var). Remediation (oscap-im / --remediate)
is intentionally NOT wired: it is operator-opt-in and needs openscap-utils +
CentOS-shaped remediation content; leave it to a future, deliberately-enabled step.
----------------------------------------------------------------------------

<!-- mios-src:0482b13a47b1 from usr/share/mios/mios.toml:10622-10632 -->

### bound-images bake sharding (commit-fit; consumed by...

--- bound-images bake sharding (commit-fit; consumed by
    usr/libexec/mios/mios-bake-group, one Containerfile RUN per group) ---
The bound-images bake is split into per-group RUNs so no single buildah commit
serializes the whole ~40-60GB store at once (that monolithic commit overran
disk-constrained CI runners: exit 125 / "closed pipe" while storing the layer).
Groups commit in `groups` ORDER; the heavy GPU-engine group commits FIRST,
while the store is smallest. Tokens are substring-matched against each rendered
bound-image Image= ref; each image is assigned to the FIRST matching group, and
anything unmatched falls into the LAST group ("extra", the catch-all). Every
image is still baked -- this only moves layer boundaries, not membership.
The two CUDA GPU engines (vLLM ~25GB, SGLang ~22GB) each get their OWN group so
no single commit serializes more than ONE whale (~25GB) -- bundling both would
leave a ~49GB commit, barely better than the monolith. They commit first.
With those engines evicted to the firstboot tier, the residual whales are
open-webui (~9GB) + ceph (~3.5GB): the "heavy" group commits them in their own
RUN so the extra catch-all commit stays ~10GB. buildah needs ~2-3x a layer's
diff in transient scratch during each commit, so halving the biggest layer is
what keeps the bake inside a standard GHA runner's /mnt (operator-confirmed
ENOSPC at 'committing container for step ... mios-bake-group extra' when all
14 residual images landed in ONE commit).

<!-- mios-src:17175093a1a6 from usr/share/mios/mios.toml:10660-10679 -->

### firstboot tier -- bound images whose rendered ref...

firstboot tier -- bound images whose rendered ref substring-matches ANY token
here are NOT baked into the OS image. They are the multi-GB GPU-engine "whales"
(vLLM ~25GB, SGLang ~22GB) that overran disk-constrained CI runners (exit 125 /
"closed pipe"); evicting them drops the bake ~25GB (only vLLM has an active
Quadlet today) so a standard 88GB runner can bake+commit+publish. They stay in
`core` (still first-class MiOS bound images) -- generate-bake-plan.py emits them
to plan.d/firstboot.list, mios-bake-group SKIPS them, and their Quadlet web-pulls
the image on first start (mios-ai-firstboot already seeds the model weights into
/var; MiOS-Cat can pre-stage the image on a 128GB+ USB data partition for an
offline first boot). Empty list = bake everything (previous behavior).
crawl4ai + firecrawl: the two LOCALLY-BUILT webtools images (localhost/
mios-crawl4ai-slim, localhost/mios-firecrawl -- see [image.sidecars] notes).
A localhost/ ref can never be PULLED by mios-bake-group (there is no registry
behind it; leaving them in a bake group fails the whole bake with
"dial tcp [::1]:443: connect: connection refused"). Their firstboot path is
BUILD, not web-pull: mios-webtools-firstboot.service (enabled in
multi-user.target.wants by automation/47-init-service.sh, ordered Before= the
webtools pod) builds them from their in-image contexts
(usr/share/mios/crawl4ai/Containerfile, usr/share/mios/webtools/
firecrawl.Containerfile) if missing -- degrade-open per BAKE-NOT-FETCH.

<!-- mios-src:2fe169d05310 from usr/share/mios/mios.toml:10706-10725 -->

### mios-build-driver fallback

mios-build-driver fallback: when the local `podman build` trigger is
unavailable (podman missing), trigger the Forgejo CI build over HTTP via curl
(workflow_dispatch on build-mios.yml). Endpoints resolve from install.env
(MIOS_HOSTNAME + MIOS_PORT_FORGE_HTTP). Degrade-open: the driver treats the
fallback as enabled when this key is absent; set false to hard-fail instead.

<!-- mios-src:06a7cdc49ee1 from usr/share/mios/mios.toml:10761-10765 -->

### May a seat fail its boot when its blade is unreachable?...

May a seat fail its boot when its blade is unreachable? Default no: Law 12
says degrade open. true makes boot success network-dependent -- opt in only.

<!-- mios-src:592aa84244de from usr/share/mios/mios.toml:10805-10806 -->

### [bootstrap] -- behavior of mios-bootstrap.git/install.sh...

----------------------------------------------------------------------------
[bootstrap] -- behavior of mios-bootstrap.git/install.sh during Phase-0.
  mode: auto | bootc | fhs
    - auto  : detect host kind, prefer 'bootc switch' when available
    - bootc : force 'bootc switch' (fail if not bootc-managed)
    - fhs   : force the Total Root Merge path (clone + overlay)
Maps to MIOS_BOOTSTRAP_MODE, MIOS_REPO_URL, MIOS_BOOTSTRAP_REPO_URL.
----------------------------------------------------------------------------

<!-- mios-src:fc8b6033915b from usr/share/mios/mios.toml:10867-10874 -->

### [bootstrap.host_storage] -- Windows-side dedicated data...

----------------------------------------------------------------------------
[bootstrap.host_storage] -- Windows-side dedicated data partition.
Get-MiOS.ps1's Initialize-MiosDataDisk shrinks C:\ by `shrink_mb` and
creates a partition labeled `volume_label` at drive `drive_letter`.
ALL MiOS install paths redirect onto this disk (M:\MiOS, M:\etc\mios,
M:\podman\machine, M:\MiOS\repo\mios + mios-bootstrap, BIB output).

Why shrink_mb = 262656 (not 262144)?
  262144 MB = 256 GiB exactly, but NTFS reserves ~16 MB at the start
  for boot sector + alignment + initial $MFT extents. The resulting
  "Capacity" in Windows Explorer falls 16-32 MB shy of the boundary,
  rounding DOWN to "255 GB". 262656 MB (= 256 GiB + 512 MB buffer)
  guarantees Explorer shows "256 GB".
----------------------------------------------------------------------------

<!-- mios-src:667ab2acfe04 from usr/share/mios/mios.toml:10883-10896 -->

### rename_distro

rename_distro: false (default) keeps the WSL distro registered as
`podman-MiOS-DEV` (the name `podman machine init` creates) so Podman
Desktop can see and control the machine. true opts back in to the
legacy export/unregister/import-as-MiOS-DEV cycle which broke Podman
Desktop visibility (operator-confirmed regression).
Operator-facing UX continues to read "MiOS-DEV" via the WT profile
name, Start Menu labels, and the `mios-dev` shell helper regardless.

<!-- mios-src:a2752b6eb55e from usr/share/mios/mios.toml:10921-10927 -->

### networking_mode

networking_mode: "NAT" or "mirrored". NAT + localhost_forwarding=true is
the safe default. Mirrored mode TRIAL on build 26300.8376 / WSL 2.7.3.0
reproduced a port-mirror desync (Windows-side svchost relay holds the
Quadlet ports after WSL services crash → EADDRINUSE death-spiral on
auto-restart). Re-attempt mirrored after Quadlet migration: host-network
removal, sshd off the mirrored port range, explicit mirror cleanup on
service stop. Operator-confirmed.

<!-- mios-src:d27e440d3c55 from usr/share/mios/mios.toml:10936-10942 -->

### [wsl2.desktop_compat] -- WSLg-specific GUI app behavior...

----------------------------------------------------------------------------
[wsl2.desktop_compat] -- WSLg-specific GUI app behavior knobs. WSLg's
Wayland compositor lacks xdg_popup reposition support (operator-
confirmed GTK4 popups detach from parent windows, stay
visible after minimize, don't follow window moves). Routing GTK / Qt
/ Mozilla apps through Xwayland (X11 semantics work correctly under
WSLg) is the documented workaround. Switch back to native Wayland via
mios.html when WSLg's compositor implements the missing protocol.

/etc/profile.d/mios-wslg.sh exports these as GDK_BACKEND /
MOZ_ENABLE_WAYLAND / QT_QPA_PLATFORM whenever /mnt/wslg is mounted.
----------------------------------------------------------------------------

<!-- mios-src:340663088daa from usr/share/mios/mios.toml:10950-10961 -->

### [wsl2.dev_vm] -- Quadlet networking knobs specific to the...

----------------------------------------------------------------------------
[wsl2.dev_vm] -- Quadlet networking knobs specific to the dev VM
(podman-MiOS-DEV). The dev VM ships dropins under
/etc/containers/systemd/<unit>.container.d/ that override the parent
unit's Network= directive (Network=mios.network) to Network=host.
This makes container-side `localhost:N` references reach sibling
services directly without relying on the bridge's container-name DNS.

Under WSL2 networking_mode=NAT the dev VM's loopback is isolated from
the Windows host's loopback, so Network=host is safe. Under
networking_mode=mirrored the WSL VM's loopback IS the Windows host's
loopback, and Network=host produces EADDRINUSE death-spirals
(operator-confirmed sshd/hermes etc. all looped
auto-restart with "address already in use"). Switch to "bridge" when
migrating to mirrored mode -- the parent units already declare
mios.network, so the only change is to NOT install the host-network
dropins. automation/01-system-files-overlay.sh honors this key and
removes any *-host-network.conf dropin when bridge is selected.
----------------------------------------------------------------------------

<!-- mios-src:01f13817bcd6 from usr/share/mios/mios.toml:10967-10985 -->

### [desktop.start_menu] -- explicit Windows Start Menu...

----------------------------------------------------------------------------
[desktop.start_menu] -- explicit Windows Start Menu shortcuts for MiOS
web services. WSLg's auto-publish heuristic filters out
Categories=System;Network;Settings; entries and Exec=xdg-open URL
patterns (operator-confirmed in podman-MiOS-DEV: 10
mios-svc-*.desktop files present, 0 surfaced as native Windows
shortcuts). Install-MiOSServiceShortcuts in Get-MiOS.ps1 reads the
`publish` list below + per-entry label/scheme keys, resolves the port
from [ports].<port_key>, and writes one .url Internet shortcut per
entry into %APPDATA%\Microsoft\Windows\Start Menu\Programs\
podman-MiOS-DEV\. Each shortcut opens scheme://localhost:port/ in the
default Windows browser. Idempotent.

Add a new service: append its key to `publish` and add three keys
(<key>_label, <key>_scheme, <key>_port_key). Remove a service by
dropping it from `publish` (existing .lnk persists until the next
Pass-0 reap; safe to delete manually).
----------------------------------------------------------------------------

<!-- mios-src:75a7baffc036 from usr/share/mios/mios.toml:10989-11006 -->

### [bootstrap.dev_vm.host_reserve] -- headroom kept for the...

----------------------------------------------------------------------------
[bootstrap.dev_vm.host_reserve] -- headroom kept for the Windows host
when the values above are "max". The dev VM is the builder, so we err
heavily toward feeding it; reserves are tuned to keep the Windows
host responsive (Explorer, browser, IDE) during long builds, not to
guarantee gaming-class throughput on Windows during a build.
----------------------------------------------------------------------------

<!-- mios-src:998ade4342aa from usr/share/mios/mios.toml:11037-11043 -->

### [bootstrap.prereqs] -- Phase 0 auto-install catalog. The...

----------------------------------------------------------------------------
[bootstrap.prereqs] -- Phase 0 auto-install catalog. The irm|iex web
entry now winget-installs each missing prerequisite instead of
failing. Operators swap implementations (e.g. an alternative WSL
package id, a different Podman distribution channel) via mios.html.
----------------------------------------------------------------------------

<!-- mios-src:b91f8361d753 from usr/share/mios/mios.toml:11052-11057 -->

### Every winget ID + Windows feature the irm|iex bootstrap...

Every winget ID + Windows feature the irm|iex bootstrap installs on a
truly-fresh Win 11 host. Operator-confirmed "MiOS should
automatically install EVERYTHING needed to install MiOS via irm|iex".
Scattered hardcoded IDs in Get-MiOS.ps1's Install-MiOS* functions
should be lifted to these keys (one TOML-first refactor in flight).

winget package IDs (each Install-MiOS* function reads its key here):

<!-- mios-src:4933f3abba55 from usr/share/mios/mios.toml:11059-11065 -->

### reboot_required_features

reboot_required_features: the ordered list above; if any reports
RestartNeeded after Enable-WindowsOptionalFeature, Pass-2 must reboot
and re-enter (operator-flagged: NO mid-install reboots without a
resume-on-next-boot mechanism). Until that resume mechanism is wired,
Get-MiOS.ps1 surfaces a "reboot then re-run irm|iex" hint and exits
Pass-2 cleanly so the operator doesn't watch downstream steps fail.

<!-- mios-src:149c4809a52a from usr/share/mios/mios.toml:11087-11092 -->

### [terminal] -- canonical MiOS terminal dimensions. EVERY...

----------------------------------------------------------------------------
[terminal] -- canonical MiOS terminal dimensions. EVERY spawned shell
(wt.exe new-tab, conhost fallback, wsl.exe into MiOS-DEV, the
auto-elevated bootstrap window, the native-app launcher, Linux tty0
console via /etc/profile.d/mios-tty.sh) opens at exactly cols × rows.

EMPIRICAL REALITY: WT chrome on the operator's hardware (Win11 26H1,
WT Stable, GeistMono Nerd Font Mono 12pt, acrylic 50%, focus mode)
eats 2-3 cells of buffer beyond what `[Console]::WindowWidth` reports.
The chrome budget breaks down approximately as:
  - 1 cell scrollbar gutter (reserved even with scrollbarState=hidden)
  - 1 cell acrylic blur edge (visible bleed at the right border)
  - 0-1 cell sub-pixel rounding (when DPI != 100% the cell grid
    doesn't divide the window pixel width evenly, so the rightmost
    cell renders as a partial column that WT clips)

Both attempts at zero-slack edge-to-edge wrapped:
commit 04c228c (margin=0, frame=80, final_space=false,
    no trailing): doubled-`||` left-border ghost wrap on dashboard
    rows + 4-cell time-segment wrap (operator screenshot at 18:38)
commit 47383f0 (margin=1, frame=79, final_space=true,
    trailing=""): same pattern, slightly less wrap (operator
    screenshot at 18:39)

Last-known-working config: commit 920af40
  (margin=2, frame=78, final_space=true, trailing="  "). Operator's
  17:19 screenshot showed time `17:19 ` ending cleanly with no wrap.
  Reverting to that as the proven floor. Future operators can drop
  margin to 0 ONCE WT exposes a knob to drop ALL chrome reservations
  (no such knob exists in WT 1.x) -- not before.

DEPLOYMENT NOTE: changing these values requires re-running
`irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/Get-MiOS.ps1 | iex`
to re-substitute Show-MiosDashboard (which bakes the values into
`M:\MiOS\powershell\profile.ps1` at install time). Plain install.ps1
in BootstrapOnly mode does NOT re-substitute -- the live dashboard
function will keep rendering at whatever values the LAST full Get-
MiOS.ps1 run baked in.
----------------------------------------------------------------------------

<!-- mios-src:ea75f301c386 from usr/share/mios/mios.toml:11104-11142 -->

### "ALL dashboards render to the edge of the MiOS app window...

"ALL dashboards render to the edge of the
MiOS app window size constraints!!" -- edge-to-edge framing.
frame_width = cols - 1, right_margin = 1: the rightmost frame
`│` lands at col 78, leaving exactly 1 cell of safety against
WT's pseudo-console over-reporting WindowWidth by 1 cell during
the first paint (before scrollbarState='hidden' applies).
Tighter than the prior 5-cell margin -- WT 1.18+ with
launchMode=focus + scrollbarState=hidden + padding=0 reports
the visible-cell count correctly from FIRST paint, so the
legacy 5-cell chrome reservation is overkill.  Bump back to 5
only if powerline wrap returns.

<!-- mios-src:77c05abf4987 from usr/share/mios/mios.toml:11147-11157 -->

### over-report) but on settled WT renders that produced a...

over-report) but on settled WT renders that produced
a visible 1-char gap on the right of the bash dashboard.
Operator-flagged with screenshot. Setting
to 0 matches mios-bootstrap/mios.toml (UNIFIED).

<!-- mios-src:0a86b640cc72 from usr/share/mios/mios.toml:11161-11164 -->

### [terminal.gui_min] -- minimum size for WSLg-hosted GUI app...

----------------------------------------------------------------------------
[terminal.gui_min] -- minimum size for WSLg-hosted GUI app windows.
Read by M:\MiOS\bin\mios-gui-watch.ps1 (Windows side). The daemon
polls msrdc.exe processes and auto-resizes any newly-spawned RDP-RAIL
window smaller than these dims to exactly these dims, centered on
the cursor monitor.

GUI apps on WSLg spawn at native X11/GTK
default sizes (xeyes 129x113, nautilus 942x649, gnome-software
714x486) which look invisible on a 4K display against acrylic
terminals. Vendor default 1600x1000 covers ~55% of a 2926x1646
work area -- comfortable to read + manage without dominating
the desktop.

Once a window is auto-adopted (resized once) the operator can
drag/resize freely; the daemon only touches each window's initial
spawn frame.
----------------------------------------------------------------------------

<!-- mios-src:9878a8695a9f from usr/share/mios/mios.toml:11166-11183 -->

### [terminal.install] -- the BOOTSTRAP window dims (taller so...

----------------------------------------------------------------------------
[terminal.install] -- the BOOTSTRAP window dims (taller so the install
output / readme / acknowledgements / Pass-1 + Pass-2 logs fit without
scrolling). The post-install MiOS app uses [terminal] above (80x20
portal feel). The install conhost uses these dims.
----------------------------------------------------------------------------

<!-- mios-src:c57baa4b1bfb from usr/share/mios/mios.toml:11188-11193 -->

### [terminal.reading] -- larger centered window mode for...

----------------------------------------------------------------------------
[terminal.reading] -- larger centered window mode for outputs that
don't fit the canonical 80x20 portal (btop, long log tails, code
review, multi-pane fastfetch, etc). `mios reading` resizes + re-
centers the CURRENT MiOS window to these dims; `mios portal` flips
back to [terminal].cols/.rows. btop's launcher invokes
`mios reading` automatically because btop's hardcoded minimum is
80x24 -- WSLg's effective viewport at portal-size 80x20 is 75x18,
below the minimum, so btop refuses to render.
----------------------------------------------------------------------------

<!-- mios-src:51a9ac766c22 from usr/share/mios/mios.toml:11198-11207 -->

### [theme] -- visual styling tokens. The [colors] table above...

----------------------------------------------------------------------------
[theme] -- visual styling tokens. The [colors] table above defines
the palette; this section names the typography, opacity, prompt,
and per-host theme switches that consumers (WT settings.json patcher,
oh-my-posh renderer, GTK/Adwaita, KDE Plasma) read.
----------------------------------------------------------------------------

<!-- mios-src:1eca24c98450 from usr/share/mios/mios.toml:11212-11217 -->

### GLOBAL MiOS terminal defaults -- per operator: "the MiOS...

GLOBAL MiOS terminal defaults -- per operator: "the MiOS app/terminal
is acrylic set to on GLOBALLY AND SET TO 50 PERCENT TRANSPARENCY!!!!
FRAME-LESS/BORDER-LESS/SCROLL-BAR-LESS, ETC--ETC!!! GLOBAL DEFAULTS".
Every WT MiOS / MiOS-DEV profile + every mios-launch.ps1 invocation
applies these. Get-MiOS.ps1's Install-MiOSTerminalProfile reads this
section and stamps the values into settings.json.

<!-- mios-src:c1c3c30ae1f3 from usr/share/mios/mios.toml:11219-11224 -->

### animations ON -- per operator "enable animations and all...

animations ON -- per operator "enable animations and all preview features in the MiOS Windows Terminal profile, full aesthetics! ALSO: can it quickly fade on open and close??". The WT window open/close fade is gated on disableAnimations=false + useAcrylic=true; both are on. If the powerline ever wraps with animations on, raise [terminal].right_margin to 1 as a targeted band-aid -- do NOT flip animations off (operator wants the aesthetics).

<!-- mios-src:5ec9caca871a from usr/share/mios/mios.toml:11234-11234 -->

### WT experimental.* knobs bundle (useAtlasEngine GPU...

WT experimental.* knobs bundle (useAtlasEngine GPU renderer, experimental.detectURLs, experimental.input.forceVT, experimental.rendering.forceFullRepaint). DISABLED operator screenshots showed CLI apps (Gemini CLI, Claude Code CLI) rendering TUI frames that extend past the visible cell boundary -- text wrapping that doesn't happen in conhost or non-MiOS WT at the same window size. Strongest hypothesis: experimental.input.forceVT changes how WT's pseudo-console reports buffer dimensions to apps querying [Console]::WindowWidth (which the diagnostic at M:\MiOS\diagnostics\window-width.txt shows reporting 80 even though actual visible cells is ~76). Re-enable once WT exposes a stable knob whose width-reporting is verified correct.

<!-- mios-src:8fe244976380 from usr/share/mios/mios.toml:11235-11235 -->

### Windows-side cursor SSOT. Bibata-Modern-Classic ships a...

Windows-side cursor SSOT. Bibata-Modern-Classic ships a Windows release
whose smallest .cur image variant is 32x32; even that renders visibly
bigger than typical Aero cursors because the bibata glyph fills more
of the canvas. Lowering CursorBaseSize forces Windows to downscale.
Get-MiOS.ps1's Install-MiOSBibataCursor reads this key and writes
HKCU\Control Panel\Cursors\CursorBaseSize accordingly.

Range: 16..256 (Windows clamps below 16 and above 256). 24 matches
the operator's visual benchmark of "normal weight, not too large".

<!-- mios-src:df06af8ddf36 from usr/share/mios/mios.toml:11238-11246 -->

### [theme.cursor_linux] -- Linux-side (dev VM + bare-metal...

----------------------------------------------------------------------------
[theme.cursor_linux] -- Linux-side (dev VM + bare-metal MiOS) cursor SSOT.
Read by:
  * gsettings org.gnome.desktop.interface.cursor-{theme,size} (mios-firstboot)
  * /var/lib/flatpak/overrides/global -> XCURSOR_THEME / XCURSOR_SIZE
    so flatpak sandboxes (Flatseal, Extension Manager, Nautilus,
    Epiphany, Ptyxis, ChromeDev) inherit the same cursor
  * /etc/profile.d/mios-cursor.sh -> XCURSOR_THEME / XCURSOR_SIZE
    for raw X/Wayland clients launched outside flatpak
Bibata-Modern-Classic ships at /usr/share/icons/Bibata-Modern-Classic
(RPM: bibata-cursor-themes). Size is DIFFERENT from Windows's
base_size (24) on purpose: WSLg's Wayland compositor renders Bibata
SVGs at their literal pixel size, while Windows downscales Bibata's
32x32 .cur images via CursorBaseSize. At equal `size` values, the
Linux cursor renders ~2x larger than the Windows cursor; 16 lines
them up visually. Operator-flagged.
----------------------------------------------------------------------------

<!-- mios-src:563b4abb110d from usr/share/mios/mios.toml:11249-11265 -->

### Source URLs for the three font families MiOS deploys...

Source URLs for the three font families MiOS deploys system-wide. All
three are read by build-mios.ps1's font installer; mios.html exposes
them so operators can pin to a specific release tag instead of
"latest". Linux side: automation/56-fonts.sh reads the same keys.

<!-- mios-src:b94f7e421618 from usr/share/mios/mios.toml:11279-11282 -->

### install_scope

install_scope: "system" forces HKLM + C:\Windows\Fonts (requires admin),
"user" forces HKCU + %LOCALAPPDATA%\Microsoft\Windows\Fonts, "auto"
(default) picks system when running elevated, user otherwise. Operator
can pin via mios.html. Geist is the MiOS GLOBAL font per operator
"Linux and Windows Font is Geist font (system-wide --
terminals, apps, UI, etc-etc)" -- system scope is the canonical mode.

<!-- mios-src:3db194248d25 from usr/share/mios/mios.toml:11286-11291 -->

### Windows Terminal "MiOS" scheme name -- the WT settings.json...

Windows Terminal "MiOS" scheme name -- the WT settings.json patcher
stamps a scheme block whose colors come from the [colors] table above.
(re-decision): "MiOS app opens direct to the
local OCI image(s) or podman-MiOS-DEV!!!".  Consolidated: ONE
user-facing app named "MiOS" that opens straight into MiOS-DEV
(the canonical MiOS Linux experience).  The Windows-side pwsh
WT profile keeps the "MiOS-WIN" name (for the post-install
transition surface and operator-typed `mios <verb>` workflow)
but it's NOT a Start Menu app -- only "MiOS.lnk" lives in the
Start Menu, and it launches the MiOS-DEV WT profile directly.

<!-- mios-src:caddc50cc50d from usr/share/mios/mios.toml:11301-11310 -->

### oh-my-posh renderer SSOT. mios.toml IS the canonical source...

oh-my-posh renderer SSOT. mios.toml IS the canonical source for
every powerline glyph + prompt symbol; mios.omp.json on disk uses
placeholder strings that the bootstrap substitutes from this
section at staging time. Operators edit these values via
mios.html to change the prompt look without touching omp JSON.

DEFAULTS = rounded powerline (`` U+E0B4 + `` U+E0B6). Sharp
triangles (`` `` U+E0B0/B2) are an operator override; flat
(` ` `) is another override. The configurator HTML exposes
all three.

<!-- mios-src:26861916e7d0 from usr/share/mios/mios.toml:11322-11331 -->

### Distro tagline -- the one-line elevator pitch under the...

Distro tagline -- the one-line elevator pitch under the MiOS banner.
Used by the agreement-gate banner subtitle, the installer banner
taglines, the .lnk Description fields, the Add/Remove Programs
DisplayName, and the dashboard footer. Operator rebrands via
mios.html for a custom downstream (e.g. "MyCo Dev Workstation").

<!-- mios-src:7f60f5e7ce30 from usr/share/mios/mios.toml:11359-11363 -->

### tagline_app is the one shown in Windows Application...

tagline_app is the one shown in Windows Application registrations
(Add/Remove Programs DisplayName, .lnk Description tooltips,
AppX manifest description, agreement gate banner). Operator
'the Applications tag/description when installed
"MiOS - Immutable Fedora AI Workstation" should be defined as
My Personal Operating System or similar' -- so OS-wide the app
face says "MiOS - My Personal Operating System" while the
technical descriptor "Immutable Fedora AI Workstation" lives
in the dashboard subtitle for context.

<!-- mios-src:7eb38f487bab from usr/share/mios/mios.toml:11366-11374 -->

### [theme.fastfetch] -- ANSI-color tags applied to the four...

----------------------------------------------------------------------------
[theme.fastfetch] -- ANSI-color tags applied to the four fastfetch
surfaces (ASCII logo, key labels, title line, value output).  These
resolve through the terminal palette which is sourced from
mios.toml [colors] -- so the rendered hex always matches MiOS
palette without per-config hardcoding.  Operators tune via
mios.html [theme.fastfetch].  build-mios.ps1's Install-MiOSFastfetch
substitutes these strings into M:\MiOS\fastfetch\config.jsonc at
install time.

ANSI vs MiOS palette mapping (default):
  blue   = ansi_4_blue   = accent  (operator blue   #1A407F)
  yellow = ansi_3_yellow = cursor  (sunset orange   #F35C15)
  white  = ansi_7_white  = fg      (cream           #E7DFD3)
  cyan   = ansi_6_cyan   = subtle  (pale blue-grey  #B7C9D7)
  green  = ansi_2_green  = success (wave green      #3E7765)
  red    = ansi_1_red    = error   (coral red       #DC271B)
----------------------------------------------------------------------------

<!-- mios-src:02849cf3577a from usr/share/mios/mios.toml:11386-11403 -->

### [btop] -- the operator-tunable btop system-monitor settings...

----------------------------------------------------------------------------
[btop] -- the operator-tunable btop system-monitor settings SSOT. Every
key here is PROJECTED into the btop config file by mios-theme-render
(surface "btop-conf" -> etc/btop/btop.conf) exactly the way [colors] is
projected into themes/mios.theme. This is the SINGLE source: the operator
tunes btop HERE (or via the Portal/configurator that writes here), then
`mios-sync-theme` re-renders the conf. The rendered etc/btop/btop.conf is
the FHS/Law-1 canonical artifact on Linux AND the artifact the Windows
bootstrap stages to M:\MiOS\btop (install-host-tools.ps1), so btop is
UNIFIED across Linux+Windows from one source instead of two hand-copies.

Reconciliation note: the previous Linux (etc/btop) and Windows
(mios-bootstrap/src/btop) confs were byte-identical EXCEPT shown_boxes
(Linux "proc" vs Windows "cpu mem"). Because btop on Windows IS the dev
VM's Linux btop (dispatched via WSL) -- same binary, one config -- that
divergence is collapsed to the single canonical value below. The launch
preset stays a launcher concern (mios-btop.sh forces `btop -p 4`).

The palette (theme[*] colors) is NOT here -- it lives in [colors] and is
projected to the sibling themes/mios.theme surface. color_theme="mios" is
a fixed binding held literally in the template.
----------------------------------------------------------------------------

<!-- mios-src:439f2674279c from usr/share/mios/mios.toml:11410-11431 -->

### Boxes shown at launch. UNIFIED value (was proc on Linux /...

Boxes shown at launch. UNIFIED value (was proc on Linux / cpu mem on
Windows). Matches the canonical proc-only preset so a plain `btop`
(invoked without -p, e.g. the Windows WSL dispatch) renders the operator's
canonical view.

<!-- mios-src:c8cfe45896d3 from usr/share/mios/mios.toml:11440-11443 -->

### [dashboard] -- the framed top-of-terminal banner shown by...

----------------------------------------------------------------------------
[dashboard] -- the framed top-of-terminal banner shown by BOTH the
Windows-side Show-MiosDashboard (M:\MiOS\powershell\profile.ps1)
and the Linux-side mios-dashboard (/usr/libexec/mios/mios-dashboard.sh).
Per "the dash is set GLOBALLY to Windows and
Linux dashboards!! same settings!!! ... smaller metric can be
side-by-side in the dash; freeing up more room for the prompt
field." Both renderers read THIS section so a configurator edit
re-skins both terminals on the next render.

Default = compact 80x20-friendly: 1 title + 5 metric rows
(side-by-side) + 1 verb hint + 4 frame rows = 11 rows total,
leaves 9 rows for the prompt and command output.
----------------------------------------------------------------------------

<!-- mios-src:b09279d82690 from usr/share/mios/mios.toml:11524-11537 -->

### Verb-hint refresh surface the current /usr/bin/mios...

Verb-hint refresh surface the current /usr/bin/mios
KNOWN_VERBS surface (was stuck on the 7-verb subset from before
mini / ai / code / summary / user were added). The hint line is
the operator's quick reference at the bottom of `mios dash` --
keep it accurate as new verbs ship.

<!-- mios-src:67772089dfa6 from usr/share/mios/mios.toml:11543-11547 -->

### rows

rows: each entry is a list of field-keys.  Multiple keys per row =
side-by-side rendering with equal column widths within the framed
inner area.  Available field-keys (built into both renderers; un-
known keys are silently skipped):

  host_os         "$user@$host -- $os $arch"
  cpu             "CPU $name $clock GHz ($n c)"
  gpu_discrete    "GPU $name $vram GiB"     (top discrete GPU only)
  gpu_integrated  "GPU $name $vram GiB"     (top integrated GPU)
  ram             "RAM $used / $total GiB ($pct %)"
  swap            "Swap $used / $total GiB ($pct %)"
  disk_c          "C: $used / $total GiB ($pct %)"           [Windows]
  disk_m          "M: $used / $total GiB ($pct %)"
  disk_root       "/ $used / $total GiB ($pct %)"            [Linux]
  disk_home       "/home $used / $total GiB ($pct %)"        [Linux]
  kernel          "Kernel $version"
  shell           "Shell $name $version"
  font            "Font $family $size pt"   (from [theme.font])
  uptime          "Up $days d $hours h $min m"

<!-- mios-src:65d8ad186557 from usr/share/mios/mios.toml:11556-11574 -->

### WT profile directly (operator "MiOS app opens direct to ......

WT profile directly (operator
"MiOS app opens direct
to ... podman-MiOS-DEV").  Per-verb
shortcuts (MiOS Help / MiOS Config /
MiOS-DEV / MiOS-WIN) are intentionally
NOT created -- those are typed verbs
in the terminal (`mios help`,
`mios config`, etc.), not separate
native apps.

<!-- mios-src:01b67ef1739b from usr/share/mios/mios.toml:11594-11602 -->

### Per-verb Start Menu + Desktop shortcuts. The hub "MiOS.lnk"...

Per-verb Start Menu + Desktop shortcuts. The hub "MiOS.lnk" + the
"Uninstall MiOS.lnk" entry are NOT in this table (they're handled
separately by Install-MiOSLauncher's hub block + the legacy
uninstall block). The 3 per-verb apps below are the operator-
customizable surface; mios.html exposes them as editable fields.
Each entry: name=display-label, bin=script-in-MiosBinDir,
icon=ico-name-in-MiosIconsDir, description=tooltip text.

<!-- mios-src:df54656ec174 from usr/share/mios/mios.toml:11605-11611 -->

### [preflight] -- minimum host requirements. Get-MiOS.ps1...

----------------------------------------------------------------------------
[preflight] -- minimum host requirements. Get-MiOS.ps1 checks these
before starting the install; a violation aborts with a clear message
pointing at which knob the operator can lower (e.g. via mios.html).
----------------------------------------------------------------------------

<!-- mios-src:982a7a885d4e from usr/share/mios/mios.toml:11629-11633 -->

### [quadlets.enable] -- per-Quadlet first-boot enablement...

----------------------------------------------------------------------------
[quadlets.enable] -- per-Quadlet first-boot enablement flags.
Defaults are all true; the system never disables a service via static
config. Incompatible deployments are gated via systemd Condition*
directives in the Quadlet itself. Set a flag to false here only to
force-disable a service even when it would otherwise run.
----------------------------------------------------------------------------

<!-- mios-src:8d8da669069e from usr/share/mios/mios.toml:11651-11657 -->

### AI chain (architecture, operator-directed): mios-llm-light...

AI chain (architecture, operator-directed):
  mios-llm-light (container) -- LLM + embeddings inference backend
                                (llama.cpp behind llama-swap; OpenAI /v1).
  hermes-agent (DIRECT)      -- installed natively on the root
                                filesystem (NOT containerized), runs as
                                a host systemd service, uses the
                                mios-llm-light lane (and vllm/sglang when
                                present) as its inference backend.
                                See automation/72-hermes-agent.sh +
                                usr/lib/systemd/system/hermes-agent.service.
  open-webui (container)     -- rich browser LLM UI on :3033, talks to
                                the OpenAI /v1 surface.

mios-hermes + mios-hermes-dashboard CONTAINER Quadlets were REMOVED
(operator directive). Hermes-Agent is a DIRECT host install
(automation/72-hermes-agent.sh + hermes-agent.service) -- there is no
containerized agent path anymore. The agent's dashboard ships inside
that same install; Open WebUI is the browser LLM UI.

<!-- mios-src:c3b32d9adc6e from usr/share/mios/mios.toml:11659-11676 -->

### [env] -- free-form environment-variable additions. Keys...

----------------------------------------------------------------------------
[env] -- free-form environment-variable additions. Keys must match POSIX
env-var rules ([A-Za-z_][A-Za-z0-9_]*). Anything you put here is exported
verbatim to every script that sources tools/lib/userenv.sh, so it
propagates throughout the build / install / runtime chain.
Examples:
  MIOS_BUILDER_DISTRO = "MiOS-DEV"
  MIOS_RECHUNK_MAX_LAYERS = "67"
  MIOS_AI_GRADER = "qwen2.5-coder:7b"
----------------------------------------------------------------------------

<!-- mios-src:d0004f8fa064 from usr/share/mios/mios.toml:11687-11696 -->

### Fine-tune subsystem -- distil a strong LOCAL teacher model...

Fine-tune subsystem -- distil a strong LOCAL teacher model into a small, fast
MiOS role model via LoRA/SFT, then ship the adapter as a GGUF for the llama.cpp
lane (served over OpenAI /v1 by mios-finetune-serve; MiOS is /v1-only). FOSS +
fully OFFLINE + HARDWARE-AGNOSTIC: the trainer auto-detects the device (NVIDIA
CUDA / AMD ROCm / Apple MPS / CPU) and only 4-bit-quantises where the hardware
supports it -- MiOS has the components to train on ANY hardware combination, same
as it runs inference on any lane. This is an OPERATOR-GATED heavy build (it
saturates a GPU for a while + the framework install needs a one-time network
fetch); it is deliberately NOT exposed as an agent verb so no chat turn can kick
off a multi-hour training run. Everything here is overridable via /etc/mios/ +
~/.config/mios/ overlays and the MIOS_FINETUNE_* env (userenv.sh).

<!-- mios-src:f83ee0ec7317 from usr/share/mios/mios.toml:11707-11717 -->

### Dataset (self-distillation; NO hardcoded English) ---...

--- Dataset (self-distillation; NO hardcoded English) ---
Queries are GENERATED by the teacher, seeded by the LIVE capability surface
(verb catalog from the running pipe + real operator Q+A from the knowledge DB);
labels are produced by the teacher against the live refine schema + catalog. So
the corpus tracks the real system, never a hand-written topic list.

<!-- mios-src:cb4757794e91 from usr/share/mios/mios.toml:11746-11750 -->

### the strongest LOCALLY-SERVED model (mios-llm-light) is now...

the strongest LOCALLY-SERVED model (mios-llm-light) is now Granite 4.1 8B (the new brain); gemma4:12b is no longer the served reasoning GGUF after the fleet swap. Teacher MUST be a served model. For a STRONGER teacher than the refiner, enable the heavy lane and point this at the served-name mios-heavy (Magistral Small 2509).

<!-- mios-src:a4ad51f38509 from usr/share/mios/mios.toml:11751-11751 -->

### ─── WS-F Tool Consolidation (Phase 1) Merged Verbs...

─── WS-F Tool Consolidation (Phase 1) Merged Verbs ─────────────────────

<!-- mios-src:7e95cc1bcfcd from usr/share/mios/mios.toml:11765-11765 -->

### ─── WS-F Tool Consolidation (Phase 2) Merged Verbs...

─── WS-F Tool Consolidation (Phase 2) Merged Verbs ─────────────────────

<!-- mios-src:c5db889cb876 from usr/share/mios/mios.toml:11900-11900 -->

### [desktop.app_types] -- WS-D: App-type aliases & default...

----------------------------------------------------------------------------
[desktop.app_types] -- WS-D: App-type aliases & default resolution SSOT.
Maps generic application types (like 'browser', 'editor', 'terminal') to
their specific concrete application defaults on each platform.
----------------------------------------------------------------------------

<!-- mios-src:a43a843037da from usr/share/mios/mios.toml:12004-12008 -->

### Health gate

Health gate: same upstream llama-swap:cuda baked `curl localhost:8220/` port mismatch
as the cpu-node lane -> perpetual Unhealthy while it serves 200 on ${MIOS_PORT_LLM_LIGHT}.
Override against the real port. Probes /v1/models (not /health): llama-swap answers it
from config.yaml WITHOUT forcing a model load, so the proxy reads healthy while idle
instead of flapping on lazy model swap. NO-HARDCODE: port from ${MIOS_PORT_LLM_LIGHT}.

<!-- mios-src:d4541dfe5e17 from usr/share/mios/mios.toml:12609-12613 -->

### After mios-cdi-detect.service

After mios-cdi-detect.service: the PRIMARY always-on lane hardcodes
AddDevice=${MIOS_GPU_DEVICE:-nvidia.com/gpu=all}, but mios-gpu-passthrough
(cdi-detect ExecStartPost) RESETS that list + re-adds only the vendor whose
CDI spec is actually present. Ordering after cdi-detect guarantees the drop-in
+ daemon-reload land BEFORE llm-light starts, so a host with no/undetected
NVIDIA GPU starts CPU-only instead of podman hard-failing on an absent
nvidia.com/gpu device (which was failing the whole install on GPU-less/
undetected-dGPU hosts). Mirrors mios-llm-heavy/worker@. Hardware-agnostic.

<!-- mios-src:3d40adacf8df from usr/share/mios/mios.toml:12645-12652 -->

### [blade] -- node activation capabilities and targets...

----------------------------------------------------------------------------
[blade] -- node activation capabilities and targets (WS-BLADE)
Defines archetype role types and mapping of units to requirements.
----------------------------------------------------------------------------

<!-- mios-src:9e410e44d5f4 from usr/share/mios/mios.toml:13114-13117 -->

### Proposed sections for roadmap index validation...

----------------------------------------------------------------------------
Proposed sections for roadmap index validation compatibility (WS-CAT / WS-DOTFILES)
----------------------------------------------------------------------------

<!-- mios-src:278790245cf8 from usr/share/mios/mios.toml:13260-13262 -->

### AI-hint

AI-hint: MiOS-Cat unified USB installer configuration (ADR-0008 / WS-CAT). All
installer values resolve from this block; MiOS-Cat.bat reads these via an inline
PowerShell SSOT pass so nothing is hardcoded. Keys match the ADR-0008 §6 mandate.

<!-- mios-src:f6323b376957 from usr/share/mios/mios.toml:13264-13266 -->

### Ventoy release to install onto the USB. "latest" ->...

Ventoy release to install onto the USB. "latest" -> MiOS-Cat resolves the newest Ventoy
upstream live from the GitHub API at build/runtime and NEVER hand-pins a stale fallback
(the resolved version is recorded to the SBOM, per ADR-0003 / mios-sbom-not-hardcode).
Keep the Secure Boot shim advisory in foss-upstream-map.md in step with what ships.

<!-- mios-src:65e2aef465bc from usr/share/mios/mios.toml:13277-13280 -->

### Path override for the Xbox builder script. Empty =...

Path override for the Xbox builder script. Empty = auto-resolve from cat/autounattend/.
Set to an absolute path to point MiOS-Cat at a custom builder location.
(Top-level [cat] key -- resolves as cat.xbox_builder, matching the root seed + ADR-0008.)

<!-- mios-src:d07f820c6855 from usr/share/mios/mios.toml:13283-13285 -->

### Model weights to stage into MiOS-Data/models/ (references...

Model weights to stage into MiOS-Data/models/ (references [ai].bake_models SSOT;
MiOS-Cat reads [ai].bake_models directly for the GGUF list and [ai.vllm].bake_model
for the AWQ weights -- this key is a human-readable cross-reference, not parsed).
(Top-level [cat] key -- resolves as cat.models, cited by WS-CATREPO + ADR-0008.)

<!-- mios-src:c8b8d6a585bc from usr/share/mios/mios.toml:13288-13291 -->

### [dotfiles.registry.<surface>] -- the SSOT projection...

----------------------------------------------------------------------------
[dotfiles.registry.<surface>] -- the SSOT projection registry (ADR-0010).
REPLACES the former hardcoded Python SURFACES dict in
usr/libexec/mios/mios-theme-render, so the surface map itself is
operator-editable via the Portal (ADR-0009). Each surface carries:
  template = repo-relative token-substitution template (.tmpl)
  target   = repo-relative committed artifact the render/check gate owns
  section  = (SETTINGS surfaces only) the mios.toml [section] whose scalar
             keys project as @MIOS:<section>_<key>@ tokens (conf-formatted)
The registry REFERENCES the existing content sections ([colors], [btop],
[gitconfig], [identity]); it does NOT re-home them (Law 9).
The optional [.apply.target] sub-table names the LIVE-HOME destination per
platform for the additive `apply`/`diff` verbs (HOME-eligible surfaces only;
the system surfaces app-shell + term-osc have none). Surface names MUST NOT
contain a dot (the surface key is a dotted-walk leaf). Order matches the
former SURFACES literal so render/check/capture log order is unchanged.
----------------------------------------------------------------------------

<!-- mios-src:1cd7f4ef0f8e from usr/share/mios/mios.toml:13307-13323 -->

### JSON-MERGE surface (ADR-0010 `kind` axis, the proof of the...

JSON-MERGE surface (ADR-0010 `kind` axis, the proof of the merge mode). MiOS
owns ONLY the workbench.colorCustomizations subtree of a VS Code settings.json;
kind=json-merge splices that owned subtree onto a foreign settings doc,
preserving every key MiOS does not emit (arrays replaced wholesale, foreign
keys byte-preserved). The drift-gate is OFFLINE: `check` merges the owned
subtree onto the checked-in fixture.base and byte-diffs the committed
fixture.expected -- it NEVER reads the operator's live settings.json. `apply`
merges the owned subtree onto the LIVE settings.json (backing it up first), so
the operator's font/telemetry/other keys survive a theme refresh. `target` is
the committed gated artifact (= fixture.expected); the real per-platform live
destination is [.apply.target].

<!-- mios-src:5795a7c9dea3 from usr/share/mios/mios.toml:13380-13390 -->

### INI-MERGE surface (ADR-0010 `kind` axis, AGY-58) -- the...

INI-MERGE surface (ADR-0010 `kind` axis, AGY-58) -- the SAFE live-apply of the
gitconfig the `gitconfig` (template) surface intentionally withheld. MiOS owns
EXACTLY the ~9 keys its template emits (user.name/email, core.editor,
init.defaultBranch, pull.rebase, alias.{co,br,ci,st}); kind=ini-merge UPSERTS
only those keys into a foreign ~/.gitconfig -- seeding absent keys, and (under
policy=seed-or-enforce) replacing a present one ONLY when the operator has
explicitly set it in the SSOT (host/user overlay), never stomping a foreign
value with a vendor default. Every foreign line (credential.helper,
user.signingkey, commit.gpgsign, [remote ...]) is byte-preserved, so a whole-
file overwrite can no longer clobber the user's identity/credentials/signing/
remotes. `template` REUSES the existing gitconfig.tmpl VERBATIM (its rendered
[section] key=value lines are BOTH the ownership manifest AND the values). The
drift-gate is OFFLINE: `check` upserts the owned keys onto the checked-in
fixture.base and byte-diffs the committed fixture.expected -- it NEVER reads the
operator's live ~/.gitconfig. `target` is the committed gated artifact
(= fixture.expected); the real per-platform live destination is [.apply.target].
The EXISTING `gitconfig` (kind=template, etc/skel/.gitconfig, no apply.target)
surface is UNCHANGED and stays byte-identical.

<!-- mios-src:49fd26075106 from usr/share/mios/mios.toml:13402-13419 -->

### JSON-MERGE surface (ADR-0010 `kind` axis) -- the Windows...

JSON-MERGE surface (ADR-0010 `kind` axis) -- the Windows Terminal color scheme.
MiOS owns ONLY the "MiOS" color scheme + profiles.defaults.colorScheme of a
foreign settings.json. WT keeps its schemes in a TOP-LEVEL `schemes` ARRAY of
`{name, background, foreground, black..white, ...}` objects, so a wholesale
array-replace would DELETE the operator's other schemes; kind=json-merge here
relies on the ARRAY-MERGE-BY-KEY path (mios-theme-render _ARRAY_MERGE_KEYS maps
the "/schemes" pointer to the "name" key) so a foreign scheme (e.g. Campbell)
is PRESERVED, the "MiOS" scheme is added/updated in place, and every foreign
top-level key (copyOnSelect, launchMode, profiles.list, ...) is byte-preserved.
The colors come from the [colors] SSOT via @MIOS:token@ (background=bg,
foreground=fg, cursorColor=cursor, black..brightWhite from the ansi_0..15
slots). The drift-gate is OFFLINE: `check` merges the owned subtree onto the
checked-in fixture.base and byte-diffs the committed fixture.expected -- it
NEVER reads the operator's live settings.json. `apply` merges onto the LIVE
WT LocalState settings.json (backing it up first). WT is Windows-only, so only
[.apply.target].windows is declared (no linux target -> `apply` no-ops on Linux,
exactly like quickshell no-ops on Windows). `target` is the committed gated
artifact (= fixture.expected); the real live destination is [.apply.target].

<!-- mios-src:628a56d4f6e3 from usr/share/mios/mios.toml:13433-13450 -->

### REGISTRY surface (ADR-0010 `kind` axis) -- proof-surface...

REGISTRY surface (ADR-0010 `kind` axis) -- proof-surface for Windows Registry.
MiOS owns HKCU\Console\MiOS color/settings values. It uses Registry apply logic
on Windows and skips on Linux. fixture.base and fixture.expected are used
for offline drift gating.

<!-- mios-src:fa3aae82e81c from usr/share/mios/mios.toml:13461-13464 -->

### [gitconfig] -- the operator-tunable git settings SSOT....

----------------------------------------------------------------------------
[gitconfig] -- the operator-tunable git settings SSOT.
projected to etc/skel/.gitconfig via mios-theme-render.
----------------------------------------------------------------------------

<!-- mios-src:c05e989e4477 from usr/share/mios/mios.toml:13511-13514 -->

### [kargs] -- Immutable kernel boot arguments, rendered into...

----------------------------------------------------------------------------
[kargs] -- Immutable kernel boot arguments, rendered into kargs.d fragments
at image build time. (WS-VECTOR V1 / T-245).
----------------------------------------------------------------------------

<!-- mios-src:d1d8f3c6deeb from usr/share/mios/mios.toml:13830-13833 -->

### WS-RESOLVER checks that cannot be exercised by a negative...

WS-RESOLVER checks that cannot be exercised by a negative test yet: they
no-op unless the mios-resolver binary is installed in the image, so an
injected fault would be skipped rather than caught and the "test" would pass
for the wrong reason. AGY-1572 installs the binary; these come off this list
with real negative tests in the same change. The two cheap deterministic new
checks (check_cargo_deny, check_powershell_parse) have real tests instead.

<!-- mios-src:3bf9b6b89eb6 from usr/share/mios/mios.toml:13858-13863 -->

### The MiOS build/system numbering SSOT (ADR-0012...

The MiOS build/system numbering SSOT (ADR-0012, doc-unified-pipeline.md).
TWO axes, deliberately distinct:
  * stage IDENTITY  NN  -- sparse/banded 0..99; the automation/NN-name.sh prefix
                          AND the [NN-name] log label (same number by construction).
                          Becomes the OCI RUN-step ONLY after one-RUN-per-stage (P3).
  * progress ORDINAL    -- build.sh SCRIPT_COUNT 1..N; the human progress denominator.
                          NOT equal to the prefix; rendered from ONE variable.
The 121 drift-checks are NOT a peer axis: they live inside stage 98 and are
addressed [98-drift-checks:CC], CC = within-stage id from `check_index`.

<!-- mios-src:138a9bab6981 from usr/share/mios/mios.toml:13929-13937 -->

### [docs] -- the generative documentation system...

----------------------------------------------------------------------------
[docs] -- the generative documentation system (docs/agy/doc-generative-documentation.md).
These thresholds ARE the comment classifier: usr/lib/mios/mios_comments.py holds
no constants of its own, so tuning what counts as "narrative worth extracting"
is an operator edit here, never a code edit (Law 7 NO-HARDCODE, Law 8).
----------------------------------------------------------------------------

<!-- mios-src:233a555e4b94 from usr/share/mios/mios.toml:14083-14088 -->

### Anchored regexes in TOML LITERAL strings (single quotes)...

Anchored regexes in TOML LITERAL strings (single quotes): in a basic string a
backslash-b is an invalid escape. Kept in SSOT so a rule change is an operator
edit, never a code edit.

<!-- mios-src:916cf52b7120 from usr/share/mios/mios.toml:14292-14294 -->

### [desktop.launchers] -- SSOT for...

----------------------------------------------------------------------------
[desktop.launchers] -- SSOT for usr/share/applications/*.desktop.
Rendered by tools/render-desktop.py; gated by check_desktop_launchers.
Derived from the 9 shipped launchers, which were previously ungoverned:
the table was ABSENT, so the renderer looped zero times and --check
reported success without comparing anything.
----------------------------------------------------------------------------

<!-- mios-src:08caeaed45cc from usr/share/mios/mios.toml:14300-14306 -->
