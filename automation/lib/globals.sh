#!/usr/bin/env bash
# AI-hint: GENERATED IN FULL from usr/share/mios/mios.toml by tools/render-globals.py. Zero hand-written constants; DO NOT EDIT -- re-run the renderer.
# AI-related: usr/share/mios/mios.toml, automation/lib/globals.ps1, tools/render-globals.py
# AI-functions: _mios_resolve_version
#
# Shell sibling of automation/lib/globals.ps1 -- both are rendered from the same
# SSOT by the same generator, so they cannot diverge. Dot-source from any entry
# point; every constant uses `:=` so an environment variable exported BEFORE
# sourcing still wins.

_mios_resolve_version() {
    local v=""
    if   [[ -n "${MIOS_VERSION:-}" ]];        then v="$MIOS_VERSION"
    elif [[ -f /ctx/VERSION ]];               then v="$(cat /ctx/VERSION)"
    elif [[ -f /usr/share/mios/VERSION ]];    then v="$(cat /usr/share/mios/VERSION)"
    else
        local _root
        _root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
        if [[ -n "$_root" && -f "${_root}/VERSION" ]]; then
            v="$(cat "${_root}/VERSION")"
        fi
    fi
    printf '%s' "${v:-0.3.0}" | tr -d '[:space:]'
}
: "${MIOS_VERSION:=$(_mios_resolve_version)}"
export MIOS_VERSION

: "${MIOS_A2A_COUNCIL:=false}"
: "${MIOS_A2A_DISCOVER_PORT:=8700}"
: "${MIOS_A2A_MDNS_ADVERTISE:=false}"
: "${MIOS_A2A_MDNS_DISCOVERY:=false}"
: "${MIOS_A2A_MDNS_REFRESH_SEC:=300}"
: "${MIOS_A2A_MDNS_SERVICE_TYPE:=_mios-a2a._tcp}"
: "${MIOS_A2A_PROTOCOL_VERSION:=1.0}"
: "${MIOS_A2A_ROUTE_ON_CARD_SKILLS:=false}"
: "${MIOS_A2A_SELF_ID:=local-mios}"
[ -n "${MIOS_A2O_CLAUDE_EFFORT_FLAG+x}" ] || MIOS_A2O_CLAUDE_EFFORT_FLAG='--effort {e}'
: "${MIOS_A2O_LANE_A_EFFORT:=xhigh}"
: "${MIOS_A2O_LANE_A_ENGINE:=claude}"
: "${MIOS_A2O_LANE_A_MODEL:=claude-opus-4-8}"
: "${MIOS_A2O_LANE_A_ROLE:=framework + ~80%}"
: "${MIOS_A2O_LANE_B_EFFORT:=high}"
: "${MIOS_A2O_LANE_B_ENGINE:=agy}"
: "${MIOS_A2O_LANE_B_FALLBACK_EFFORT:=high}"
: "${MIOS_A2O_LANE_B_FALLBACK_ENGINE:=claude}"
: "${MIOS_A2O_LANE_B_FALLBACK_MODEL:=claude-sonnet-5}"
: "${MIOS_A2O_LANE_B_MODEL:=Gemini 3.5 Flash (High)}"
: "${MIOS_A2O_LANE_B_PREFER_FALLBACK:=true}"
: "${MIOS_A2O_LANE_B_ROLE:=finalize (last ~20%)}"
: "${MIOS_A2O_ORCH_EFFORT:=high}"
: "${MIOS_A2O_ORCH_ENGINE:=claude}"
: "${MIOS_A2O_ORCH_MODEL:=claude-sonnet-5}"
: "${MIOS_A2O_STREAM_PATH:=/var/lib/mios/hermes-tail/frontier/frontier.jsonl}"
: "${MIOS_A2O_STREAM_REASONING:=false}"
: "${MIOS_ACCOUNTS_DB_BACKED:=true}"
: "${MIOS_ACCOUNTS_DB_RENDER_PREFS:=false}"
: "${MIOS_ACI_HEAD_FRAC:=0.6}"
: "${MIOS_ACI_MAX_LINES:=160}"
: "${MIOS_ADGUARD_ADMIN_USER:=admin}"
: "${MIOS_ADGUARD_BLOCKLISTS:=https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts,https://big.oisd.nl,https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt}"
: "${MIOS_ADGUARD_BOOTSTRAP:=9.9.9.9,1.1.1.1}"
: "${MIOS_ADGUARD_CACHE_MAX_TTL:=86400}"
: "${MIOS_ADGUARD_CACHE_MIN_TTL:=60}"
: "${MIOS_ADGUARD_DNS_PORT:=53}"
: "${MIOS_ADGUARD_GID:=825}"
: "${MIOS_ADGUARD_IMAGE:=docker.io/adguard/adguardhome:latest}"
: "${MIOS_ADGUARD_MAGICDNS_RESOLVER:=100.100.100.100}"
: "${MIOS_ADGUARD_UID:=825}"
: "${MIOS_ADGUARD_UI_PORT:=8050}"
: "${MIOS_ADGUARD_UPSTREAMS:=https://dns.quad9.net/dns-query,https://dns.cloudflare.com/dns-query}"
: "${MIOS_ADGUARD_USER:=mios-adguard}"
: "${MIOS_ADGUARD_VERSION:=docker.io/adguard/adguardhome:latest}"
: "${MIOS_ADMISSION_MULTIBLADE_ENABLE:=false}"
: "${MIOS_ADMISSION_TENANT_MAX_CONCURRENCY:=0}"
: "${MIOS_ADMISSION_TENANT_QUOTA_ENABLE:=false}"
: "${MIOS_AGENTS_AI_LOCAL_DEFAULT:=false}"
: "${MIOS_AGENTS_AI_LOCAL_HEALTH_GATE:=true}"
[ -n "${MIOS_AGENTS_AI_LOCAL_JOB+x}" ] || MIOS_AGENTS_AI_LOCAL_JOB='On-device mobile second opinion -- a lightweight local model on the operator'"'"'s phone (AI.Local over the tailnet) for an extra perspective when it is serving.'
: "${MIOS_AGENTS_AI_LOCAL_LANE:=mobile}"
: "${MIOS_AGENTS_AI_LOCAL_MODEL:=qwen2.5-3b-instruct-4bit}"
: "${MIOS_AGENTS_AI_LOCAL_ROLE:=mobile}"
: "${MIOS_AGENTS_AI_LOCAL_STRENGTHS:=mobile_local_model,on_device,offline_edge}"
: "${MIOS_PORT_SGLANG:=8530}"
[ -n "${MIOS_AGENTS_HERMES_CPU_ENDPOINT+x}" ] || MIOS_AGENTS_HERMES_CPU_ENDPOINT='http://localhost:'"${MIOS_PORT_SGLANG}"'/v1'
: "${MIOS_AGENTS_HERMES_CPU_MODEL:=mios-heavy}"
: "${MIOS_AGENTS_HERMES_DEFAULT:=false}"
: "${MIOS_PORT_HERMES:=8720}"
[ -n "${MIOS_AGENTS_HERMES_ENDPOINT+x}" ] || MIOS_AGENTS_HERMES_ENDPOINT='http://localhost:'"${MIOS_PORT_HERMES}"'/v1'
: "${MIOS_AGENTS_HERMES_FANOUT:=false}"
: "${MIOS_AGENTS_HERMES_HEALTH_GATE:=true}"
: "${MIOS_AGENTS_HERMES_JOB:=General orchestration of multi-step, tool-driven tasks -- decide local-vs-web, search, inspect and operate the system, launch apps, then fan out and synthesise.}"
: "${MIOS_AGENTS_HERMES_LANE:=gpu}"
: "${MIOS_AGENTS_HERMES_MODEL:=mios-heavy}"
: "${MIOS_AGENTS_HERMES_PRIVILEGE_GROUP:=privileged}"
: "${MIOS_AGENTS_HERMES_ROLE:=general}"
: "${MIOS_AGENTS_HERMES_STRENGTHS:=kanban,web_search,skill_invocation,multi_step_reasoning,tool_use}"
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_DEFAULT:=false}"
[ -n "${MIOS_AGENTS_MIOS_DAEMON_AGENT_ENDPOINT+x}" ] || MIOS_AGENTS_MIOS_DAEMON_AGENT_ENDPOINT='http://localhost:'"${MIOS_PORT_SGLANG}"'/v1'
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_FAILOVER_AGENTS:=hermes}"
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_FANOUT:=true}"
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_HEALTH_GATE:=true}"
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_JOB:=CPU reasoning grounded in live system state -- second opinions, summaries, planning, and answers grounded in the global journal/log telemetry it continuously collects.}"
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_LANE:=cpu}"
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_MODEL:=mios-heavy}"
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_ROLE:=reasoning}"
: "${MIOS_AGENTS_MIOS_DAEMON_AGENT_STRENGTHS:=reasoning,second_opinion,summarize,planning,journalctl_tail,log_search,event_query,system_followup,what_just_happened}"
: "${MIOS_AGENTS_OPENCODE_DEFAULT:=false}"
: "${MIOS_AGENTS_OPENCODE_ENABLED:=true}"
: "${MIOS_PORT_OPENCODE_GATEWAY:=8780}"
[ -n "${MIOS_AGENTS_OPENCODE_ENDPOINT+x}" ] || MIOS_AGENTS_OPENCODE_ENDPOINT='http://localhost:'"${MIOS_PORT_OPENCODE_GATEWAY}"'/v1'
: "${MIOS_AGENTS_OPENCODE_FAILOVER_AGENTS:=hermes}"
: "${MIOS_AGENTS_OPENCODE_FANOUT:=true}"
: "${MIOS_AGENTS_OPENCODE_HEALTH_GATE:=true}"
: "${MIOS_AGENTS_OPENCODE_JOB:=Software engineering -- read, edit, review, test and commit code, configs, scripts, systemd units, Containerfiles and TOML in this repo/system.}"
: "${MIOS_AGENTS_OPENCODE_KIND:=cli}"
: "${MIOS_AGENTS_OPENCODE_LANE:=gpu}"
: "${MIOS_AGENTS_OPENCODE_MODEL:=mios-opencode:latest}"
: "${MIOS_AGENTS_OPENCODE_PRIVILEGE_GROUP:=routine}"
: "${MIOS_AGENTS_OPENCODE_ROLE:=coding}"
: "${MIOS_AGENTS_OPENCODE_STRENGTHS:=file_edit,code_review,git,test_running,refactor}"
: "${MIOS_AGENTS_OPENCODE_TIMEOUT_S:=90}"
: "${MIOS_AGENTS_OPENCODE_TRANSPORT:=cli}"
: "${MIOS_AGENTS__DEFAULTS_AUTH_SCHEME:=none}"
: "${MIOS_AGENTS__DEFAULTS_DEFAULT:=false}"
: "${MIOS_AGENTS__DEFAULTS_ENABLED:=true}"
: "${MIOS_AGENTS__DEFAULTS_FANOUT:=true}"
: "${MIOS_AGENTS__DEFAULTS_HEALTH_GATE:=false}"
: "${MIOS_AGENTS__DEFAULTS_KIND:=local-http}"
: "${MIOS_AGENTS__DEFAULTS_LANE:=gpu}"
: "${MIOS_AGENTS__DEFAULTS_RESEARCH_ONLY:=false}"
: "${MIOS_AGENTS__DEFAULTS_ROLE:=general}"
: "${MIOS_AGENTS__DEFAULTS_TIMEOUT_S:=0}"
: "${MIOS_AGENTS__DEFAULTS_TRANSPORT:=http}"
: "${MIOS_AGENTS__DEFAULTS_TRUST_MIN_REPUTATION:=0.0}"
: "${MIOS_AGENTS__DEFAULTS_TRUST_MTLS:=false}"
: "${MIOS_AGENTS__DEFAULTS_TRUST_REQUIRE_SIGNED_PRINCIPAL:=false}"
[ -n "${MIOS_AGENT_PIPE_BACKEND+x}" ] || MIOS_AGENT_PIPE_BACKEND='http://localhost:'"${MIOS_PORT_HERMES}"'/v1'
: "${MIOS_AGENT_PIPE_BACKEND_MODEL:=hermes-agent}"
: "${MIOS_AGENT_PIPE_CLIENT_TOOLS_PASSTHROUGH:=true}"
: "${MIOS_AGENT_PIPE_COUNCIL_AGGREGATOR_BYPASS:=false}"
: "${MIOS_AGENT_PIPE_COUNCIL_AGGREGATOR_BYPASS_THRESHOLD:=0.95}"
: "${MIOS_AGENT_PIPE_COUNCIL_DIVERSITY_GATE:=false}"
: "${MIOS_AGENT_PIPE_COUNCIL_DIVERSITY_THRESHOLD:=0.92}"
: "${MIOS_AGENT_PIPE_ENABLE:=true}"
: "${MIOS_PORT_AGENT_PIPE:=8700}"
[ -n "${MIOS_AGENT_PIPE_ENDPOINT+x}" ] || MIOS_AGENT_PIPE_ENDPOINT='http://localhost:'"${MIOS_PORT_AGENT_PIPE}"'/v1'
: "${MIOS_AGENT_PIPE_GID:=822}"
: "${MIOS_AGENT_PIPE_MAX_CONSECUTIVE_FAILURES:=3}"
: "${MIOS_AGENT_PIPE_NO_PROGRESS_WINDOW:=2}"
: "${MIOS_AGENT_PIPE_PORT:=8700}"
: "${MIOS_AGENT_PIPE_QUALITY_CHECK_EMPTY:=true}"
: "${MIOS_AGENT_PIPE_QUALITY_CHECK_JSON:=true}"
: "${MIOS_AGENT_PIPE_QUALITY_CHECK_PUNT:=true}"
: "${MIOS_AGENT_PIPE_QUALITY_MIN_LENGTH:=5}"
: "${MIOS_AGENT_PIPE_REFLEXION_ENABLE:=true}"
: "${MIOS_AGENT_PIPE_REFLEXION_LIMIT:=2}"
: "${MIOS_AGENT_PIPE_REPLAN_MAX:=5}"
: "${MIOS_PORT_LLM_LIGHT:=8500}"
[ -n "${MIOS_AGENT_PIPE_TOOL_BACKEND+x}" ] || MIOS_AGENT_PIPE_TOOL_BACKEND='http://localhost:'"${MIOS_PORT_LLM_LIGHT}"'/v1'
: "${MIOS_AGENT_PIPE_TOOL_BACKEND_MODEL:=granite4.1:8b}"
: "${MIOS_AGENT_PIPE_TOOL_LOOP_LIMIT:=20}"
: "${MIOS_AGENT_PIPE_TOOL_MAX_ITERS:=15}"
: "${MIOS_AGENT_PIPE_UID:=822}"
: "${MIOS_AGENT_PIPE_USER:=mios-agent-pipe}"
: "${MIOS_AGENT_PIPE_WALL_CLOCK_BUDGET_S:=90}"
: "${MIOS_AI_BAKE_MODELS:=granite4.1:8b,lfm2:700m,nomic-embed-text,mios-agent,mios-agent-cpu,mios-hermes,mios-hermes-cpu,mios-opencode,mios-sys-agent}"
: "${MIOS_AI_DIR:=/usr/share/mios/ai}"
: "${MIOS_AI_EMBED_MODEL:=nomic-embed-text}"
[ -n "${MIOS_AI_ENDPOINT+x}" ] || MIOS_AI_ENDPOINT='http://localhost:'"${MIOS_PORT_AGENT_PIPE}"'/v1'
: "${MIOS_AI_JOURNAL:=/var/lib/mios/ai/journal.md}"
: "${MIOS_AI_MCP_DIR:=/srv/ai/mcp}"
: "${MIOS_AI_MEMORY_DIR:=/var/lib/mios/ai/memory}"
: "${MIOS_AI_MODEL:=granite4.1:8b}"
: "${MIOS_AI_MODELS_DIR:=/srv/ai/models}"
: "${MIOS_AI_RAM_FLOOR_GB:=12}"
: "${MIOS_AI_SCRATCH_DIR:=/var/lib/mios/ai/scratch}"
: "${MIOS_SHARE_DIR:=/usr/share/mios}"
[ -n "${MIOS_SHARE_AI_DIR+x}" ] || MIOS_SHARE_AI_DIR="${MIOS_SHARE_DIR}"'/ai'
[ -n "${MIOS_AI_SYSTEM_PROMPT+x}" ] || MIOS_AI_SYSTEM_PROMPT="${MIOS_SHARE_AI_DIR}"'/system.md'
: "${MIOS_AI_TAG_HINT_MAX_CHARS:=3000}"
: "${MIOS_AI_TAG_MAX_UNCONFORMING:=0}"
: "${MIOS_AI_TAG_MAX_UNTAGGED:=120}"
: "${MIOS_AI_TAG_TEACHER_MODEL:=granite4.1:3b}"
: "${MIOS_AI_TAG_TEACHER_PORT_KEY:=llm_light}"
: "${MIOS_ANSI_0_BLACK:=#282262}"
: "${MIOS_ANSI_10_BRIGHT_GREEN:=#5FAA8E}"
: "${MIOS_ANSI_11_BRIGHT_YELLOW:=#FF8540}"
: "${MIOS_ANSI_12_BRIGHT_BLUE:=#3D6BA8}"
: "${MIOS_ANSI_13_BRIGHT_MAGENTA:=#9D7660}"
: "${MIOS_ANSI_14_BRIGHT_CYAN:=#E0E0E0}"
: "${MIOS_ANSI_15_BRIGHT_WHITE:=#FFFFFF}"
: "${MIOS_ANSI_1_RED:=#DC271B}"
: "${MIOS_ANSI_2_GREEN:=#3E7765}"
: "${MIOS_ANSI_3_YELLOW:=#F35C15}"
: "${MIOS_ANSI_4_BLUE:=#1A407F}"
: "${MIOS_ANSI_5_MAGENTA:=#734F39}"
: "${MIOS_ANSI_6_CYAN:=#B7C9D7}"
: "${MIOS_ANSI_7_WHITE:=#E7DFD3}"
: "${MIOS_ANSI_8_BRIGHT_BLACK:=#948E8E}"
: "${MIOS_ANSI_9_BRIGHT_RED:=#FF6B5C}"
: "${MIOS_ANTIFAB_ENABLE:=true}"
: "${MIOS_ANTIFAB_GROUND_MIN:=0.34}"
: "${MIOS_ANTIFAB_MIN_ENTITIES:=3}"
: "${MIOS_APPEARANCE_ADW_COLOR_SCHEME:=prefer-dark}"
: "${MIOS_APPEARANCE_CURSOR_SIZE:=24}"
: "${MIOS_APPEARANCE_CURSOR_THEME:=Bibata-Modern-Classic}"
: "${MIOS_APPEARANCE_GTK_THEME:=adw-gtk3-dark}"
: "${MIOS_APPS_AUMID:=MiOS.Workstation}"
: "${MIOS_APPS_HUB_SHORTCUT_NAME:=MiOS}"
: "${MIOS_APPS_SHORTCUTS_MIOS_CONFIG_BIN:=mios-config.ps1}"
: "${MIOS_APPS_SHORTCUTS_MIOS_CONFIG_DESCRIPTION:=Open mios.html (the HTML configurator) in your default browser to edit mios.toml}"
: "${MIOS_APPS_SHORTCUTS_MIOS_CONFIG_ICON:=mios-config.ico}"
: "${MIOS_APPS_SHORTCUTS_MIOS_CONFIG_NAME:=MiOS Config}"
: "${MIOS_APPS_SHORTCUTS_MIOS_DEV_BIN:=mios-dev.ps1}"
: "${MIOS_APPS_SHORTCUTS_MIOS_DEV_DESCRIPTION:=Open MiOS-DEV (podman machine) directly to its themed dashboard}"
: "${MIOS_APPS_SHORTCUTS_MIOS_DEV_ICON:=mios-dev.ico}"
: "${MIOS_APPS_SHORTCUTS_MIOS_DEV_NAME:=MiOS-DEV}"
: "${MIOS_APPS_SHORTCUTS_MIOS_HELP_BIN:=mios-help.ps1}"
: "${MIOS_APPS_SHORTCUTS_MIOS_HELP_DESCRIPTION:=Full verb + functionality reference (every MiOS command and where things live)}"
: "${MIOS_APPS_SHORTCUTS_MIOS_HELP_ICON:=mios-help.ico}"
: "${MIOS_APPS_SHORTCUTS_MIOS_HELP_NAME:=MiOS Help}"
: "${MIOS_APPS_START_MENU_FOLDER:=MiOS}"
: "${MIOS_ARBITER_PORT:=8760}"
: "${MIOS_AUDIT_CHAIN_ENABLE:=true}"
: "${MIOS_AUTH_PASSWORD:=mios}"
: "${MIOS_AUTH_PASSWORD_POLICY:=plain}"
: "${MIOS_AUTH_SSH_KEY_ACTION:=generate}"
: "${MIOS_AUTH_SSH_KEY_TYPE:=ed25519}"
: "${MIOS_BASE_IMAGE:=ghcr.io/ublue-os/ucore-hci:stable-nvidia}"
: "${MIOS_BIB_ALPINE_IMAGE:=docker.io/library/alpine:latest}"
: "${MIOS_BIB_ALPINE_VERSION:=docker.io/library/alpine:latest}"
: "${MIOS_BIB_IMAGE:=quay.io/centos-bootc/bootc-image-builder:latest}"
: "${MIOS_BLADES_HAZARDS_ACCEPTED:=k3s-multi-server,pacemaker-unfenced}"
[ -n "${MIOS_BLADES_HAZARDS_DOC+x}" ] || MIOS_BLADES_HAZARDS_DOC='A MiOS-Mini fleet is 2-6 boxes (T-331), so a configuration that only works standalone is a defect waiting for the operator to add a peer. Each entry here is a hazard the tree currently carries, accepted deliberately while the fleet design lands (T-333). k3s-multi-server: four archetypes grant what mios-k3s requires and the unit runs `k3s server` with no K3S_URL, so every controller stands up its OWN control plane instead of joining one -- three default `hybrid` Minis would be three clusters sharing one token. pacemaker-unfenced: mios-ha-bootstrap sets stonith-enabled=false, which is correct for the one-node cluster it creates and is how split-brain corrupts data once a peer exists. Retiring an entry means the detector stops reproducing it, not editing this list.'
: "${MIOS_BLADES_HAZARDS_MAX_ACCEPTED:=2}"
: "${MIOS_BLADES_MAX_NODES:=6}"
: "${MIOS_BLADES_MIN_NODES:=1}"
: "${MIOS_BLADES_TYPICAL_NODES:=3}"
: "${MIOS_BLADE_ARCHETYPES_COMPUTE:=gpu-serving,service-plane}"
: "${MIOS_BLADE_ARCHETYPES_CONTROLLER:=controller,service-plane}"
: "${MIOS_BLADE_ARCHETYPES_DESKTOP:=service-plane}"
: "${MIOS_BLADE_ARCHETYPES_HA_NODE:=controller,service-plane}"
: "${MIOS_BLADE_ARCHETYPES_HEADLESS:=service-plane}"
: "${MIOS_BLADE_ARCHETYPES_HYBRID:=gpu-serving,controller,service-plane}"
: "${MIOS_BLADE_ARCHETYPES_K3S_MASTER:=controller,service-plane}"
: "${MIOS_BLADE_COLLAPSE_DWELL_S:=30}"
: "${MIOS_BLADE_COLLAPSE_FAIL_CHECKS:=3}"
: "${MIOS_BLADE_COLLAPSE_RECOVER_DWELL_S:=120}"
: "${MIOS_BLADE_CPU_FALLBACKS_MIOS_LLM_HEAVY:=mios-llm-light}"
: "${MIOS_BLADE_CPU_FALLBACKS_MIOS_LLM_HEAVY_ALT:=mios-llm-light}"
: "${MIOS_BLADE_CPU_FALLBACKS_MIOS_LLM_WORKER_:=mios-llm-light}"
: "${MIOS_BLADE_DISCOVERY_HEALTH_PATH:=/v1/models}"
: "${MIOS_BLADE_DISCOVERY_HEALTH_TIMEOUT_S:=3}"
: "${MIOS_BLADE_DISCOVERY_ORDER:=localhost,mdns,tailnet,remote}"
: "${MIOS_BLADE_FALLBACK:=headless}"
: "${MIOS_BLADE_HARDWARE_MIN_AP_CAPABLE:=1}"
: "${MIOS_BLADE_HARDWARE_MIN_INTERFACES:=2}"
: "${MIOS_BLADE_PLACEMENT_CONTAINERS:=k3s}"
: "${MIOS_BLADE_PLACEMENT_FAILOVER_ORDER:=local,localhost,cluster}"
: "${MIOS_BLADE_PLACEMENT_VMS:=pacemaker}"
: "${MIOS_BLADE_PLANES_AI_OWNER:=either}"
: "${MIOS_BLADE_PLANES_AI_ROLE:=the OpenAI-compatible front door and the lanes behind it}"
: "${MIOS_BLADE_PLANES_AI_WIRED_BY:=usr/share/containers/systemd/mios-llm-light.container}"
: "${MIOS_BLADE_PLANES_HA_MARKERS:=pacemaker,corosync}"
: "${MIOS_BLADE_PLANES_HA_OWNER:=either}"
: "${MIOS_BLADE_PLANES_HA_ROLE:=Pacemaker/Corosync: places and live-migrates VMs (ADR-0017 D1). A guest may hold a vote (ADR-0016 D11), so fencing one goes via its host}"
: "${MIOS_BLADE_PLANES_HA_WIRED_BY:=usr/lib/greenboot/check/wanted.d/50-mios-ha-cluster.sh}"
: "${MIOS_BLADE_PLANES_HYPERVISOR_MARKERS:=libvirt,qemu-kvm}"
: "${MIOS_BLADE_PLANES_HYPERVISOR_OWNER:=mini}"
: "${MIOS_BLADE_PLANES_HYPERVISOR_ROLE:=runs the VMs and containers every other plane lands in}"
: "${MIOS_BLADE_PLANES_HYPERVISOR_WIRED_BY:=usr/lib/sysctl.d/99-mios-vmhost.conf}"
: "${MIOS_BLADE_PLANES_MESH_MARKERS:=tailscale}"
: "${MIOS_BLADE_PLANES_MESH_OWNER:=mini}"
: "${MIOS_BLADE_PLANES_MESH_ROLE:=joins every node and service into one addressable overlay}"
: "${MIOS_BLADE_PLANES_ORCHESTRATOR_MARKERS:=k3s}"
: "${MIOS_BLADE_PLANES_ORCHESTRATOR_OWNER:=either}"
: "${MIOS_BLADE_PLANES_ORCHESTRATOR_ROLE:=k3s: places containers across the fleet (ADR-0017 D1). Peers JOIN one elected server, never stand up their own (ADR-0016 D11)}"
: "${MIOS_BLADE_PLANES_ORCHESTRATOR_WIRED_BY:=usr/share/containers/systemd/mios-k3s.container}"
: "${MIOS_BLADE_PLANES_RADIO_MARKERS:=hostapd,wpa_supplicant}"
: "${MIOS_BLADE_PLANES_RADIO_OWNER:=mini}"
: "${MIOS_BLADE_PLANES_RADIO_ROLE:=serves WiFi clients as an access point; needs [blade.hardware].min_ap_capable of the min_interfaces}"
: "${MIOS_BLADE_PLANES_ROUTER_MARKERS:=firewalld,dnsmasq}"
: "${MIOS_BLADE_PLANES_ROUTER_OWNER:=mini}"
: "${MIOS_BLADE_PLANES_ROUTER_ROLE:=is the uplink: forwards, NATs and filters for the clients it serves, on a different interface from the one serving them}"
: "${MIOS_BLADE_PLANES_ROUTER_WIRED_BY:=usr/lib/sysctl.d/99-mios-vmhost.conf}"
: "${MIOS_BLADE_PLANES_STORAGE_MARKERS:=ceph-common,cephadm}"
: "${MIOS_BLADE_PLANES_STORAGE_OWNER:=either}"
: "${MIOS_BLADE_PLANES_STORAGE_ROLE:=CephFS, shadow-copied across the mesh (local, localhost, remote) so a shed workload lands on its data rather than cold-starting}"
: "${MIOS_BLADE_PLANES_STORAGE_WIRED_BY:=usr/share/containers/systemd/mios-ceph.container}"
: "${MIOS_BLADE_RECONCILE_AGENT_MEMORY:=append-ordered}"
: "${MIOS_BLADE_RECONCILE_CONFIG_KV:=conflict-is-error}"
: "${MIOS_BLADE_RECONCILE_EMBEDDINGS:=union-by-hash}"
: "${MIOS_BLADE_RECONCILE_ENABLED:=false}"
: "${MIOS_BLADE_RECONCILE_EVENT:=append-ordered}"
: "${MIOS_BLADE_RECONCILE_KNOWLEDGE:=union-by-hash}"
: "${MIOS_BLADE_RECONCILE_SCRATCH:=last-writer-wins}"
: "${MIOS_BLADE_RECONCILE_SESSION:=last-writer-wins}"
: "${MIOS_BLADE_REQUIRES_HERMES_WORKER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_K3S:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_ACCOUNT_SYNC:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_ADGUARD:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_AGENTS:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_CEPH:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_COCKPIT_LINK:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_CODE_SERVER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_CPU_NODE:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_CRON_DIRECTOR:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_DAEMON:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_EMBED_BACKFILL:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_FINETUNE_SERVE:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_FORGE:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_FORGEJO_RUNNER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_FORGEJO_RUNNER_FIRSTBOOT:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_FORGE_FIRSTBOOT:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_GIT_ROOT_INIT:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_GUACAMOLE:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_GUACD:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_HERMES_BROWSER_WORKER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_K3S:=controller,service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_K3S_MASTER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_LLM_HEAVY:=gpu-serving,service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_LLM_HEAVY_ALT:=gpu-serving,service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_LLM_LIGHT:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_LLM_WORKER_:=gpu-serving,service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_MCP:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_OPENCODE_GATEWAY:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_OPEN_WEBUI:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_OTELCOL:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_PASSPORT_PROVISION:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_PGVECTOR:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_PGVECTOR_BACKUP:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_POLICY_ARBITER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_PXE_HUB:=controller,service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_SEARXNG:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_SKILLS_MINER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_SYS_ENV_REFRESH:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_USERDB_RENDER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_WEBTOOLS_CRAWL4AI:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_WEBTOOLS_FIRECRAWL_API:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_WEBTOOLS_FIRECRAWL_WORKER:=service-plane}"
: "${MIOS_BLADE_REQUIRES_MIOS_WEBTOOLS_REDIS:=service-plane}"
: "${MIOS_BLADE_ROLE_ALIASES_HA:=ha-node}"
: "${MIOS_BLADE_ROLE_ALIASES_K3S:=k3s-master}"
: "${MIOS_BLADE_SEAT_SIDE:=mios-agent-pipe,hermes-dashboard,mios-hermes-browser,mios-hermes-tail,mios-ttyd-bash,mios-ttyd-powershell}"
: "${MIOS_BLADE_SOFT_OK:=hermes-worker}"
: "${MIOS_BLADE_TYPE:=hybrid}"
: "${MIOS_BOOLEAN_PARAM_KEYWORDS:=enable,force,success,active,dryrun}"
: "${MIOS_BOOTSTRAP_MODE:=auto}"
: "${MIOS_BOOTSTRAP_REPO_URL:=C:/mios-bootstrap}"
: "${MIOS_BRANCH:=main}"
: "${MIOS_BRANDING_DASHBOARD_FRAME_CHARS:=╭─╮│╰╯}"
: "${MIOS_BRANDING_DASHBOARD_FRAME_COLOR:=blue}"
: "${MIOS_BRANDING_DASHBOARD_FRAME_WIDTH_COLS:=80}"
: "${MIOS_BRANDING_DASHBOARD_SHOW_FASTFETCH:=true}"
: "${MIOS_BRANDING_DASHBOARD_SHOW_LOGO:=true}"
: "${MIOS_BRANDING_FASTFETCH_CONFIG:=fastfetch/config.jsonc}"
: "${MIOS_BRANDING_ICON_ICO:=branding/mios.ico}"
: "${MIOS_BRANDING_LIVING_WALLPAPER:=true}"
: "${MIOS_BRANDING_LIVING_WALLPAPER_MODE:=shader}"
: "${MIOS_BRANDING_LOGO_ASCII:=fastfetch/mios.txt}"
: "${MIOS_BRANDING_LOGO_IMAGE:=branding/mios-logo.png}"
: "${MIOS_BRANDING_TAGLINE:=My Personal Operating System}"
: "${MIOS_BRANDING_TAGLINE_APP:=My Personal Operating System}"
: "${MIOS_BRANDING_TAGLINE_LONG:=My Personal Operating System  --  Immutable Fedora AI Workstation}"
: "${MIOS_BROWSER_ACTION_VERBS:=quote,read,tell,summarise,summarize,what is,what does,what say,what says,first sentence,the content,browse,extract,scrape,headline,article,say}"
: "${MIOS_BROWSER_AI_ENABLE:=true}"
: "${MIOS_BROWSER_AI_PACKAGE:=Zen-Team.Zen-Browser.Twilight}"
: "${MIOS_BROWSER_AI_PREFS:=browser.ml.enable|bool|true,browser.smartwindow.enabled|bool|true,browser.ml.chat.enabled|bool|true,browser.ml.chat.hideLocalhost|bool|false,browser.ml.chat.shortcuts|bool|true,browser.ml.chat.menu|bool|true,browser.ml.pageAssist.enabled|bool|true,browser.ml.linkPreview.enabled|bool|true}"
: "${MIOS_PORT_OPEN_WEBUI:=8200}"
[ -n "${MIOS_BROWSER_AI_PROVIDER_URL+x}" ] || MIOS_BROWSER_AI_PROVIDER_URL='http://localhost:'"${MIOS_PORT_OPEN_WEBUI}"
: "${MIOS_BROWSER_FAMILY_CHROMIUM:=chrome,chromium,brave,edge,vivaldi,opera}"
: "${MIOS_BROWSER_FAMILY_EPIPHANY:=epiphany,gnome.web,gnome.epiphany}"
: "${MIOS_BROWSER_FAMILY_FIREFOX:=firefox,mozilla,librewolf,waterfox,zen,floorp}"
: "${MIOS_BROWSER_FLAGS_CHROMIUM_NEW_WINDOW:=--new-window}"
: "${MIOS_BROWSER_FLAGS_CHROMIUM_PRIVATE:=--incognito}"
: "${MIOS_BROWSER_FLAGS_CHROMIUM_WINDOW:=--new-window}"
: "${MIOS_BROWSER_FLAGS_EPIPHANY_NEW_WINDOW:=--new-window}"
: "${MIOS_BROWSER_FLAGS_EPIPHANY_PRIVATE:=--incognito-mode}"
: "${MIOS_BROWSER_FLAGS_EPIPHANY_TAB:=--new-tab}"
: "${MIOS_BROWSER_FLAGS_EPIPHANY_WINDOW:=--new-window}"
: "${MIOS_BROWSER_FLAGS_FIREFOX_NEW_WINDOW:=--new-window --new-instance}"
: "${MIOS_BROWSER_FLAGS_FIREFOX_PRIVATE:=--private-window}"
: "${MIOS_BROWSER_FLAGS_FIREFOX_TAB:=--new-tab}"
: "${MIOS_BROWSER_FLAGS_FIREFOX_WINDOW:=--new-window}"
: "${MIOS_BUDGET_AUTONOMOUS_MAX_INFLIGHT:=1}"
: "${MIOS_BUDGET_AUTONOMOUS_TOKEN_CEIL:=400000}"
: "${MIOS_BUDGET_CONVERSATION_TOKEN_CEIL:=2000000}"
: "${MIOS_BUDGET_WINDOW_S:=3600}"
: "${MIOS_BUILDER_DISTRO:=MiOS-DEV}"
: "${MIOS_BUILD_AI_RAM_FLOOR_GB:=12}"
: "${MIOS_BUILD_ARTIFACTS_OUTPUT_DIR:=build}"
: "${MIOS_BUILD_BAKE_CORE:=localhost/mios-sys,localhost/mios-cuda,localhost/mios-crawl4ai-slim:latest,localhost/mios-firecrawl:v1.0.0,code.forgejo.org/forgejo/runner:7,codeberg.org/forgejo/forgejo:12,docker.io/adguard/adguardhome:latest,docker.io/guacamole/guacamole:latest,docker.io/guacamole/guacd:latest,docker.io/jaegertracing/all-in-one:1.76.0,docker.io/lmsysorg/sglang:latest,docker.io/pgvector/pgvector:pg18,docker.io/rancher/k3s:v1.36.3-k3s1,docker.io/searxng/searxng:latest,docker.io/valkey/valkey:latest,docker.io/vllm/vllm-openai:latest,ghcr.io/mostlygeek/llama-swap:cuda,ghcr.io/open-webui/open-webui:main,quay.io/centos-bootc/bootc-image-builder:latest,quay.io/ceph/ceph:v19,quay.io/poseidon/matchbox:latest}"
: "${MIOS_BUILD_BAKE_FIRSTBOOT_TOKENS:=vllm,sglang,crawl4ai,firecrawl}"
: "${MIOS_BUILD_BAKE_GROUPS:=sys,cuda,heavy,extra}"
: "${MIOS_BUILD_BAKE_GROUP_MEMBERS_CUDA:=cuda}"
: "${MIOS_BUILD_BAKE_GROUP_MEMBERS_HEAVY:=open-webui,ceph}"
: "${MIOS_BUILD_BAKE_GROUP_MEMBERS_SYS:=sys}"
: "${MIOS_BUILD_BAKE_REFS_HYPRLAND:=main}"
: "${MIOS_BUILD_BAKE_REFS_LOOKINGGLASS:=B7}"
: "${MIOS_BUILD_BAKE_REFS_QUICKSHELL:=v0.3.0}"
: "${MIOS_BUILD_BAKE_REFS_SEARXNG:=master}"
: "${MIOS_BUILD_BAKE_REFS_SURFER:=17d9a1577170880cdac13dca7c3d6871716fc046}"
: "${MIOS_BUILD_BAKE_REFS_SYFT:=v1.19.0}"
: "${MIOS_BUILD_BAKE_RUNNER_DISK_BUDGET_GB:=40}"
: "${MIOS_BUILD_CURL_TRIGGER_FALLBACK:=true}"
[ -n "${MIOS_BUILD_PHASES_LIST+x}" ] || MIOS_BUILD_PHASES_LIST='{'"'"'ordinal'"'"': '"'"'01'"'"', '"'"'name'"'"': '"'"'system-files-overlay'"'"', '"'"'script'"'"': '"'"'01-system-files-overlay.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'containerfile'"'"'},{'"'"'ordinal'"'"': '"'"'02'"'"', '"'"'name'"'"': '"'"'materialize-build-ctx'"'"', '"'"'script'"'"': '"'"'02-materialize-build-ctx.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'04'"'"', '"'"'name'"'"': '"'"'local-rpm-mirror'"'"', '"'"'script'"'"': '"'"'04-local-rpm-mirror.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'05'"'"', '"'"'name'"'"': '"'"'repos'"'"', '"'"'script'"'"': '"'"'05-repos.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'06'"'"', '"'"'name'"'"': '"'"'enable-external-repos'"'"', '"'"'script'"'"': '"'"'06-enable-external-repos.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'07'"'"', '"'"'name'"'"': '"'"'kernel'"'"', '"'"'script'"'"': '"'"'07-kernel.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'10'"'"', '"'"'name'"'"': '"'"'locale-theme'"'"', '"'"'script'"'"': '"'"'10-locale-theme.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'11'"'"', '"'"'name'"'"': '"'"'user'"'"', '"'"'script'"'"': '"'"'11-user.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'12'"'"', '"'"'name'"'"': '"'"'hostname'"'"', '"'"'script'"'"': '"'"'12-hostname.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'13'"'"', '"'"'name'"'"': '"'"'accounts-db'"'"', '"'"'script'"'"': '"'"'13-accounts-db.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'14'"'"', '"'"'name'"'"': '"'"'podman-machine-compat'"'"', '"'"'script'"'"': '"'"'14-podman-machine-compat.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'15'"'"', '"'"'name'"'"': '"'"'freeipa-client'"'"', '"'"'script'"'"': '"'"'15-freeipa-client.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'20'"'"', '"'"'name'"'"': '"'"'hardware'"'"', '"'"'script'"'"': '"'"'20-hardware.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'21'"'"', '"'"'name'"'"': '"'"'virt'"'"', '"'"'script'"'"': '"'"'21-virt.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'22'"'"', '"'"'name'"'"': '"'"'akmod-guards'"'"', '"'"'script'"'"': '"'"'22-akmod-guards.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'23'"'"', '"'"'name'"'"': '"'"'gpu-passthrough'"'"', '"'"'script'"'"': '"'"'23-gpu-passthrough.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'24'"'"', '"'"'name'"'"': '"'"'gpu-pv-shim'"'"', '"'"'script'"'"': '"'"'24-gpu-pv-shim.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'25'"'"', '"'"'name'"'"': '"'"'gpu-cdi-toolkits'"'"', '"'"'script'"'"': '"'"'25-gpu-cdi-toolkits.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'26'"'"', '"'"'name'"'"': '"'"'nvidia-cdi-refresh'"'"', '"'"'script'"'"': '"'"'26-nvidia-cdi-refresh.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'27'"'"', '"'"'name'"'"': '"'"'vm-gating'"'"', '"'"'script'"'"': '"'"'27-vm-gating.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'33'"'"', '"'"'name'"'"': '"'"'generate-quadlets'"'"', '"'"'script'"'"': '"'"'33-generate-quadlets.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'34'"'"', '"'"'name'"'"': '"'"'render-quadlets'"'"', '"'"'script'"'"': '"'"'34-render-quadlets.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'35'"'"', '"'"'name'"'"': '"'"'render-ports'"'"', '"'"'script'"'"': '"'"'35-render-ports.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'36'"'"', '"'"'name'"'"': '"'"'ceph-k3s'"'"', '"'"'script'"'"': '"'"'36-ceph-k3s.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'37'"'"', '"'"'name'"'"': '"'"'k3s-selinux'"'"', '"'"'script'"'"': '"'"'37-k3s-selinux.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'38'"'"', '"'"'name'"'"': '"'"'selinux'"'"', '"'"'script'"'"': '"'"'38-selinux.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'39'"'"', '"'"'name'"'"': '"'"'moby-engine'"'"', '"'"'script'"'"': '"'"'39-moby-engine.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'40'"'"', '"'"'name'"'"': '"'"'fapolicyd-trust'"'"', '"'"'script'"'"': '"'"'40-fapolicyd-trust.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'41'"'"', '"'"'name'"'"': '"'"'services'"'"', '"'"'script'"'"': '"'"'41-services.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'42'"'"', '"'"'name'"'"': '"'"'chrony-render'"'"', '"'"'script'"'"': '"'"'42-chrony-render.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'43'"'"', '"'"'name'"'"': '"'"'nut-render'"'"', '"'"'script'"'"': '"'"'43-nut-render.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'44'"'"', '"'"'name'"'"': '"'"'firewall-ports'"'"', '"'"'script'"'"': '"'"'44-firewall-ports.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'45'"'"', '"'"'name'"'"': '"'"'firewall'"'"', '"'"'script'"'"': '"'"'45-firewall.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'46'"'"', '"'"'name'"'"': '"'"'sshd-port'"'"', '"'"'script'"'"': '"'"'46-sshd-port.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'47'"'"', '"'"'name'"'"': '"'"'init-service'"'"', '"'"'script'"'"': '"'"'47-init-service.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'48'"'"', '"'"'name'"'"': '"'"'mios-dropin-fanout'"'"', '"'"'script'"'"': '"'"'48-mios-dropin-fanout.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'49'"'"', '"'"'name'"'"': '"'"'cosign-policy'"'"', '"'"'script'"'"': '"'"'49-cosign-policy.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'50'"'"', '"'"'name'"'"': '"'"'uupd-installer'"'"', '"'"'script'"'"': '"'"'50-uupd-installer.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'51'"'"', '"'"'name'"'"': '"'"'hardening'"'"', '"'"'script'"'"': '"'"'51-hardening.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'52'"'"', '"'"'name'"'"': '"'"'apply-boot-fixes'"'"', '"'"'script'"'"': '"'"'52-apply-boot-fixes.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'53'"'"', '"'"'name'"'"': '"'"'enable-log-copy-service'"'"', '"'"'script'"'"': '"'"'53-enable-log-copy-service.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'54'"'"', '"'"'name'"'"': '"'"'bake-coderun-sandbox'"'"', '"'"'script'"'"': '"'"'54-bake-coderun-sandbox.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'56'"'"', '"'"'name'"'"': '"'"'fonts'"'"', '"'"'script'"'"': '"'"'56-fonts.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'57'"'"', '"'"'name'"'"': '"'"'gnome'"'"', '"'"'script'"'"': '"'"'57-gnome.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'58'"'"', '"'"'name'"'"': '"'"'gnome-remote-desktop'"'"', '"'"'script'"'"': '"'"'58-gnome-remote-desktop.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'59'"'"', '"'"'name'"'"': '"'"'tools'"'"', '"'"'script'"'"': '"'"'59-tools.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'60'"'"', '"'"'name'"'"': '"'"'flatpak-env'"'"', '"'"'script'"'"': '"'"'60-flatpak-env.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'61'"'"', '"'"'name'"'"': '"'"'flatpak-bake'"'"', '"'"'script'"'"': '"'"'61-flatpak-bake.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'62'"'"', '"'"'name'"'"': '"'"'oh-my-posh'"'"', '"'"'script'"'"': '"'"'62-oh-my-posh.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'65'"'"', '"'"'name'"'"': '"'"'bake-hyprland'"'"', '"'"'script'"'"': '"'"'65-bake-hyprland.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'66'"'"', '"'"'name'"'"': '"'"'bake-quickshell'"'"', '"'"'script'"'"': '"'"'66-bake-quickshell.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'67'"'"', '"'"'name'"'"': '"'"'bake-surfer'"'"', '"'"'script'"'"': '"'"'67-bake-surfer.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'68'"'"', '"'"'name'"'"': '"'"'bake-kvmfr'"'"', '"'"'script'"'"': '"'"'68-bake-kvmfr.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'69'"'"', '"'"'name'"'"': '"'"'bake-lookingglass-client'"'"', '"'"'script'"'"': '"'"'69-bake-lookingglass-client.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'72'"'"', '"'"'name'"'"': '"'"'hermes-agent'"'"', '"'"'script'"'"': '"'"'72-hermes-agent.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'73'"'"', '"'"'name'"'"': '"'"'model-prep'"'"', '"'"'script'"'"': '"'"'73-model-prep.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'75'"'"', '"'"'name'"'"': '"'"'kargs-render'"'"', '"'"'script'"'"': '"'"'75-kargs-render.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'76'"'"', '"'"'name'"'"': '"'"'uki-render'"'"', '"'"'script'"'"': '"'"'76-uki-render.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'77'"'"', '"'"'name'"'"': '"'"'composefs-verity'"'"', '"'"'script'"'"': '"'"'77-composefs-verity.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'78'"'"', '"'"'name'"'"': '"'"'greenboot'"'"', '"'"'script'"'"': '"'"'78-greenboot.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'79'"'"', '"'"'name'"'"': '"'"'boot-config'"'"', '"'"'script'"'"': '"'"'79-boot-config.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'80'"'"', '"'"'name'"'"': '"'"'distribution'"'"', '"'"'script'"'"': '"'"'80-distribution.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'85'"'"', '"'"'name'"'"': '"'"'bake-plan'"'"', '"'"'script'"'"': '"'"'85-bake-plan.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'86'"'"', '"'"'name'"'"': '"'"'oscap-compliance'"'"', '"'"'script'"'"': '"'"'86-oscap-compliance.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'88'"'"', '"'"'name'"'"': '"'"'finalize'"'"', '"'"'script'"'"': '"'"'88-finalize.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'90'"'"', '"'"'name'"'"': '"'"'generate-sbom'"'"', '"'"'script'"'"': '"'"'90-generate-sbom.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'91'"'"', '"'"'name'"'"': '"'"'strip-build-toolchain'"'"', '"'"'script'"'"': '"'"'91-strip-build-toolchain.sh'"'"', '"'"'fatal'"'"': False, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'94'"'"', '"'"'name'"'"': '"'"'cleanup'"'"', '"'"'script'"'"': '"'"'94-cleanup.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'universal'"'"'},{'"'"'ordinal'"'"': '"'"'97'"'"', '"'"'name'"'"': '"'"'ssot-lint'"'"', '"'"'script'"'"': '"'"'97-ssot-lint.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'containerfile'"'"'},{'"'"'ordinal'"'"': '"'"'98'"'"', '"'"'name'"'"': '"'"'drift-checks'"'"', '"'"'script'"'"': '"'"'98-drift-checks.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'containerfile'"'"'},{'"'"'ordinal'"'"': '"'"'99'"'"', '"'"'name'"'"': '"'"'postcheck'"'"', '"'"'script'"'"': '"'"'99-postcheck.sh'"'"', '"'"'fatal'"'"': True, '"'"'apply_class'"'"': '"'"'containerfile'"'"'}'
: "${MIOS_BUILD_RATCHET_MAX_PHASE_SCRIPTS:=72}"
: "${MIOS_BUILD_RECHUNK_MAX_LAYERS:=67}"
[ -n "${MIOS_CAT_CACHE_PATH+x}" ] || MIOS_CAT_CACHE_PATH='M:\MediCat.USB.v21.12.7z'
: "${MIOS_CAT_DATA_PARTITION_LABEL:=MiOS-Data}"
: "${MIOS_CAT_DATA_PARTITION_MIN_DISK_GB:=512}"
: "${MIOS_CAT_DRIVEPATH:=D}"
: "${MIOS_CAT_MEDICATVER:=21.12}"
: "${MIOS_CAT_MODELS:=see [ai].bake_models + [ai.vllm].bake_model}"
: "${MIOS_CAT_REPO_PARTITION_LABEL:=MiOS-Repo}"
: "${MIOS_CAT_VENTOY_VERSION:=latest}"
: "${MIOS_CEPHFS_AUTOMOUNT_ENABLE:=true}"
: "${MIOS_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S:=600}"
: "${MIOS_CEPHFS_CLIENT_CACHE_SIZE:=16384}"
: "${MIOS_CEPHFS_CLIENT_READAHEAD_MAX_BYTES:=33554432}"
: "${MIOS_CEPHFS_CLIENT_RECONNECT_STALE_INTERVAL:=30}"
: "${MIOS_CEPHFS_CLUSTER_NAME:=ceph}"
: "${MIOS_CEPHFS_DATA_POOL_BULK:=cephfs_data_bulk}"
: "${MIOS_CEPHFS_DATA_POOL_HOT:=cephfs_data_hot}"
: "${MIOS_CEPHFS_ENABLE:=false}"
: "${MIOS_CEPHFS_FS_NAME:=cephfs}"
: "${MIOS_CEPHFS_KEYRING_DIR:=/etc/ceph/keyring.d}"
: "${MIOS_CEPHFS_MDS_CACHE_MEMORY_LIMIT_GIB:=4}"
: "${MIOS_CEPHFS_MDS_SESSION_CAP_MAX:=1024}"
: "${MIOS_CEPHFS_METADATA_POOL:=cephfs_metadata}"
: "${MIOS_CEPHFS_MONITORS:=127.0.0.1:6789}"
: "${MIOS_CEPHFS_MOUNT_OPTIONS:=noatime,fsc,_netdev}"
: "${MIOS_CEPHFS_PROVISION_SCRIPT:=/usr/libexec/mios/mios-cephfs-provision}"
: "${MIOS_CEPHFS_SUBVOLUME_MODE:=0700}"
: "${MIOS_CEPHFS_TENANT_ID:=mios}"
: "${MIOS_CEPH_DASHBOARD_PORT:=8460}"
: "${MIOS_CEPH_GID:=819}"
[ -n "${MIOS_CEPH_IMAGE+x}" ] || MIOS_CEPH_IMAGE='quay.io/ceph/ceph:'"${MIOS_VERSION_CEPH}"
: "${MIOS_CEPH_UID:=819}"
: "${MIOS_CEPH_USER:=mios-ceph}"
[ -n "${MIOS_CEPH_VERSION+x}" ] || MIOS_CEPH_VERSION='quay.io/ceph/ceph:'"${MIOS_VERSION_CEPH}"
: "${MIOS_CHROME_CDP_PORT:=9222}"
: "${MIOS_CHROME_CDP_WORKER_PORT:=9223}"
: "${MIOS_CMD_EXE:=/mnt/c/Windows/System32/cmd.exe}"
: "${MIOS_COCKPIT_ALLOW_UNENCRYPTED:=true}"
: "${MIOS_COCKPIT_IDLE_TIMEOUT:=0}"
: "${MIOS_COCKPIT_LINK_PORT:=8120}"
: "${MIOS_COCKPIT_LOGIN_TO:=false}"
: "${MIOS_COCKPIT_PORT:=8110}"
: "${MIOS_PORT_COCKPIT:=8110}"
[ -n "${MIOS_COCKPIT_URL+x}" ] || MIOS_COCKPIT_URL='https://localhost:'"${MIOS_PORT_COCKPIT}"
: "${MIOS_CODEMODE_ALLOW_NET:=false}"
: "${MIOS_CODEMODE_ENABLE:=true}"
: "${MIOS_CODEMODE_GID:=828}"
: "${MIOS_CODEMODE_HEAVY_LANE_ONLY:=true}"
: "${MIOS_CODEMODE_MAX_OUTPUT_CHARS:=8000}"
: "${MIOS_CODEMODE_UID:=828}"
: "${MIOS_CODEMODE_WORKSPACE_ROOT:=/var/lib/mios/codemode}"
: "${MIOS_CODERUN_SNAPSHOTS_ROOT:=/var/home/mios/.coderun-snapshots}"
: "${MIOS_CODERUN_WORKSPACE_ROOT:=/var/home/mios/coderuns}"
: "${MIOS_CODE_MODE_ALLOW_NET:=false}"
: "${MIOS_CODE_MODE_ENABLE:=true}"
: "${MIOS_CODE_MODE_GID:=828}"
: "${MIOS_CODE_MODE_HEAVY_LANE_ONLY:=true}"
: "${MIOS_CODE_MODE_MAX_OUTPUT_CHARS:=8000}"
: "${MIOS_CODE_MODE_UID:=828}"
: "${MIOS_CODE_SERVER_IMAGE:=ghcr.io/coder/code-server:latest}"
: "${MIOS_CODE_SERVER_PORT:=8900}"
: "${MIOS_PORT_CODE_SERVER:=8900}"
[ -n "${MIOS_CODE_SERVER_URL+x}" ] || MIOS_CODE_SERVER_URL='http://localhost:'"${MIOS_PORT_CODE_SERVER}"'/'
: "${MIOS_CODE_SERVER_VERSION:=ghcr.io/coder/code-server:latest}"
: "${MIOS_COLORS_ACCENT:=#1A407F}"
: "${MIOS_COLORS_ANSI_0_BLACK:=#282262}"
: "${MIOS_COLORS_ANSI_10_BRIGHT_GREEN:=#5FAA8E}"
: "${MIOS_COLORS_ANSI_11_BRIGHT_YELLOW:=#FF8540}"
: "${MIOS_COLORS_ANSI_12_BRIGHT_BLUE:=#3D6BA8}"
: "${MIOS_COLORS_ANSI_13_BRIGHT_MAGENTA:=#9D7660}"
: "${MIOS_COLORS_ANSI_14_BRIGHT_CYAN:=#E0E0E0}"
: "${MIOS_COLORS_ANSI_15_BRIGHT_WHITE:=#FFFFFF}"
: "${MIOS_COLORS_ANSI_1_RED:=#DC271B}"
: "${MIOS_COLORS_ANSI_2_GREEN:=#3E7765}"
: "${MIOS_COLORS_ANSI_3_YELLOW:=#F35C15}"
: "${MIOS_COLORS_ANSI_4_BLUE:=#1A407F}"
: "${MIOS_COLORS_ANSI_5_MAGENTA:=#734F39}"
: "${MIOS_COLORS_ANSI_6_CYAN:=#B7C9D7}"
: "${MIOS_COLORS_ANSI_7_WHITE:=#E7DFD3}"
: "${MIOS_COLORS_ANSI_8_BRIGHT_BLACK:=#948E8E}"
: "${MIOS_COLORS_ANSI_9_BRIGHT_RED:=#FF6B5C}"
: "${MIOS_COLORS_BG:=#282262}"
: "${MIOS_COLORS_CURSOR:=#F35C15}"
: "${MIOS_COLORS_EARTH:=#734F39}"
: "${MIOS_COLORS_ERROR:=#DC271B}"
: "${MIOS_COLORS_FG:=#E7DFD3}"
: "${MIOS_COLORS_INFO:=#1A407F}"
: "${MIOS_COLORS_MUTED:=#948E8E}"
: "${MIOS_COLORS_SILVER:=#E0E0E0}"
: "${MIOS_COLORS_SUBTLE:=#B7C9D7}"
: "${MIOS_COLORS_SUCCESS:=#3E7765}"
: "${MIOS_COLORS_WARNING:=#F35C15}"
: "${MIOS_COLOR_ACCENT:=#1A407F}"
: "${MIOS_COLOR_ANSI_0_BLACK:=#282262}"
: "${MIOS_COLOR_ANSI_10_BRIGHT_GREEN:=#5FAA8E}"
: "${MIOS_COLOR_ANSI_11_BRIGHT_YELLOW:=#FF8540}"
: "${MIOS_COLOR_ANSI_12_BRIGHT_BLUE:=#3D6BA8}"
: "${MIOS_COLOR_ANSI_13_BRIGHT_MAGENTA:=#9D7660}"
: "${MIOS_COLOR_ANSI_14_BRIGHT_CYAN:=#E0E0E0}"
: "${MIOS_COLOR_ANSI_15_BRIGHT_WHITE:=#FFFFFF}"
: "${MIOS_COLOR_ANSI_1_RED:=#DC271B}"
: "${MIOS_COLOR_ANSI_2_GREEN:=#3E7765}"
: "${MIOS_COLOR_ANSI_3_YELLOW:=#F35C15}"
: "${MIOS_COLOR_ANSI_4_BLUE:=#1A407F}"
: "${MIOS_COLOR_ANSI_5_MAGENTA:=#734F39}"
: "${MIOS_COLOR_ANSI_6_CYAN:=#B7C9D7}"
: "${MIOS_COLOR_ANSI_7_WHITE:=#E7DFD3}"
: "${MIOS_COLOR_ANSI_8_BRIGHT_BLACK:=#948E8E}"
: "${MIOS_COLOR_ANSI_9_BRIGHT_RED:=#FF6B5C}"
: "${MIOS_COLOR_BG:=#282262}"
: "${MIOS_COLOR_CURSOR:=#F35C15}"
: "${MIOS_COLOR_EARTH:=#734F39}"
: "${MIOS_COLOR_ERROR:=#DC271B}"
: "${MIOS_COLOR_FG:=#E7DFD3}"
: "${MIOS_COLOR_INFO:=#1A407F}"
: "${MIOS_COLOR_MUTED:=#948E8E}"
: "${MIOS_COLOR_SCHEME:=prefer-dark}"
: "${MIOS_COLOR_SILVER:=#E0E0E0}"
: "${MIOS_COLOR_SUBTLE:=#B7C9D7}"
: "${MIOS_COLOR_SUCCESS:=#3E7765}"
: "${MIOS_COLOR_WARNING:=#F35C15}"
: "${MIOS_COMPLIANCE_ENABLED:=false}"
: "${MIOS_COMPLIANCE_FETCH_REMOTE_RESOURCES:=false}"
: "${MIOS_COMPLIANCE_PROFILE:=standard}"
: "${MIOS_COMPLIANCE_REMEDIATE:=false}"
: "${MIOS_COMPLIANCE_REPORT_PATH:=/usr/share/mios/compliance}"
: "${MIOS_COMPLIANCE_SEVERITY_GATE:=high}"
: "${MIOS_COMPOUND_ACTIONS:=type,write,enter,input,paste,put}"
: "${MIOS_COMPOUND_CONJUNCTIONS:=and,then}"
: "${MIOS_COMPOUND_CONNECTIVES:=in,and,then,with,on,to}"
: "${MIOS_COMPUTER_USE_BIND_ADDRESS:=127.0.0.1}"
: "${MIOS_COMPUTER_USE_CAPTURE_BACKEND:=auto}"
: "${MIOS_COMPUTER_USE_DOCGEN_ENABLE:=true}"
: "${MIOS_COMPUTER_USE_DOCGEN_MAX_BYTES:=20000000}"
: "${MIOS_COMPUTER_USE_DOCGEN_PANDOC:=pandoc}"
: "${MIOS_COMPUTER_USE_DOCGEN_SOFFICE:=soffice}"
: "${MIOS_COMPUTER_USE_DOCGEN_TIMEOUT_S:=120}"
: "${MIOS_COMPUTER_USE_ENABLE:=true}"
: "${MIOS_COMPUTER_USE_INPUT_BACKEND:=auto}"
: "${MIOS_COMPUTER_USE_NODES_WORKSTATION_DESC:=A second MiOS/Linux desktop -- screenshot + click + type + verify on its own Wayland session over the tailnet.}"
: "${MIOS_COMPUTER_USE_REQUIRE_APPROVAL:=true}"
: "${MIOS_COMPUTER_USE_SERVER_PORT:=11438}"
: "${MIOS_COMPUTER_USE_VERIFY_AFTER_ACT:=true}"
: "${MIOS_CONSENSUS_ENABLE:=false}"
: "${MIOS_CONSENSUS_MIN_LANES:=2}"
: "${MIOS_CONSENSUS_RRF_K:=60}"
: "${MIOS_CONSENSUS_THRESHOLD:=0.5}"
: "${MIOS_CONSENSUS_TIMEOUT_S:=20.0}"
: "${MIOS_CONSENSUS_WEIGHT_FLOOR:=0.1}"
[ -n "${MIOS_CONVERGE_GATEWAY_FALLBACK_HTTP+x}" ] || MIOS_CONVERGE_GATEWAY_FALLBACK_HTTP='http://localhost:'"${MIOS_PORT_HERMES}"'/v1'
: "${MIOS_CONVERGE_GATEWAY_MODE:=http}"
: "${MIOS_CONVERGE_GATEWAY_QUEUE_MAXSIZE:=64}"
: "${MIOS_CONVERGE_GATEWAY_WORKER_CONCURRENCY:=4}"
: "${MIOS_CONVERGE_IMAGE_DISTROLESS_BASE:=gcr.io/distroless/python3-debian13}"
: "${MIOS_CONVERGE_IMAGE_DISTROLESS_ENABLE:=false}"
: "${MIOS_CONVERGE_IMAGE_MCP_POOL_ENABLE:=false}"
: "${MIOS_CONVERGE_IMAGE_RECHUNK_ENABLE:=false}"
: "${MIOS_CONVERGE_IMAGE_RECHUNK_FORMAT_VERSION:=1}"
: "${MIOS_CONVERGE_INFERENCE_HEAVY_ENGINE_MODE:=single}"
: "${MIOS_CONVERGE_INFERENCE_LLAMA_CACHE_REUSE_TOKENS:=0}"
: "${MIOS_CONVERGE_INFERENCE_LLAMA_PARALLEL_SLOTS:=1}"
: "${MIOS_CONVERGE_INFERENCE_RETIRE_HEAVY_ALT:=true}"
: "${MIOS_CONVERGE_INFERENCE_VLLM_ALLOW_RUNTIME_LORA:=false}"
: "${MIOS_CONVERGE_INFERENCE_VLLM_LORA_ADAPTERS_DIR:=/var/lib/mios/lora-adapters/}"
: "${MIOS_CONVERGE_MEMORY_COLD_EVICT_ENABLE:=false}"
: "${MIOS_CONVERGE_MEMORY_COLD_RETENTION_DAYS:=90}"
: "${MIOS_CONVERGE_MEMORY_COLD_STORAGE_DIR:=/var/lib/mios/history/}"
: "${MIOS_CONVERGE_MEMORY_COLD_ZSTD_LEVEL:=10}"
[ -n "${MIOS_CONVERGE_MEMORY_SCRATCHPAD_DIR+x}" ] || MIOS_CONVERGE_MEMORY_SCRATCHPAD_DIR='/run/user/{uid}'
: "${MIOS_CONVERGE_MEMORY_SQLITE_VEC_ENABLE:=false}"
: "${MIOS_CORE_NET_GATEWAY:=10.89.0.1}"
: "${MIOS_CORE_NET_SUBNET:=10.89.0.0/24}"
: "${MIOS_COST_BUDGET_USD:=0.0}"
: "${MIOS_COST_ENABLE:=true}"
: "${MIOS_COST_GPU_WATTS:=350.0}"
: "${MIOS_COST_REMOTE_USD_PER_MTOK:=0.0}"
: "${MIOS_COST_USD_PER_KWH:=0.0}"
: "${MIOS_COUNCIL_AGGREGATOR_BYPASS:=false}"
: "${MIOS_COUNCIL_AGGREGATOR_BYPASS_THRESHOLD:=0.95}"
: "${MIOS_COUNCIL_DIVERSITY_GATE:=false}"
: "${MIOS_COUNCIL_DIVERSITY_THRESHOLD:=0.92}"
: "${MIOS_CPU_NODE_PORT:=8510}"
: "${MIOS_CPU_NODE_THREADS:=14}"
: "${MIOS_CRAWL4AI_PORT:=8810}"
: "${MIOS_CRAWL_CAMOUFOX:=true}"
: "${MIOS_PORT_CHROME_CDP:=9222}"
[ -n "${MIOS_CRAWL_CDP_URL+x}" ] || MIOS_CRAWL_CDP_URL='http://127.0.0.1:'"${MIOS_PORT_CHROME_CDP}"
: "${MIOS_CRAWL_MIN_CHARS:=200}"
: "${MIOS_CROWDSEC_IMAGE:=docker.io/crowdsecurity/crowdsec:latest}"
: "${MIOS_CROWDSEC_VERSION:=docker.io/crowdsecurity/crowdsec:latest}"
: "${MIOS_CUDA_IMAGE:=ghcr.io/mostlygeek/llama-swap:cuda}"
: "${MIOS_CUDA_VERSION:=ghcr.io/mostlygeek/llama-swap:cuda}"
: "${MIOS_DAEMON_AGENT_PORT:=8740}"
: "${MIOS_DAEMON_CALM_MAX_TICK_S:=300}"
: "${MIOS_DAEMON_CLASSIFY_DEDUP_S:=600}"
: "${MIOS_DAEMON_CLASSIFY_LIMIT_PER_MIN:=10}"
: "${MIOS_DAEMON_CRON_MAX_CONCURRENT:=1}"
: "${MIOS_DAEMON_ESCALATION_COOLDOWN_S:=1800}"
: "${MIOS_DAEMON_ESCALATION_MAX_ATTEMPTS:=3}"
: "${MIOS_DAEMON_INDEX_ENABLE:=true}"
: "${MIOS_DAEMON_INDEX_INTERVAL_MIN:=15}"
: "${MIOS_DAEMON_INDEX_MAX_DEPTH:=6}"
: "${MIOS_DAEMON_INDEX_MAX_ENTRIES:=50000}"
[ -n "${MIOS_DAEMON_INDEX_ROOTS+x}" ] || MIOS_DAEMON_INDEX_ROOTS='{'"'"'label'"'"': '"'"'mios-vendor'"'"', '"'"'path'"'"': '"'"'/usr/share/mios'"'"', '"'"'excludes'"'"': ['"'"'__pycache__'"'"', '"'"'*.pyc'"'"']},{'"'"'label'"'"': '"'"'mios-vendor-bin'"'"', '"'"'path'"'"': '"'"'/usr/libexec/mios'"'"'},{'"'"'label'"'"': '"'"'mios-config'"'"', '"'"'path'"'"': '"'"'/etc/mios'"'"'},{'"'"'label'"'"': '"'"'mios-state'"'"', '"'"'path'"'"': '"'"'/var/lib/mios'"'"', '"'"'excludes'"'"': ['"'"'sessions'"'"', '"'"'vector_db'"'"', '"'"'models'"'"', '"'"'*.db'"'"', '"'"'*.db-*'"'"', '"'"'__pycache__'"'"', '"'"'cache'"'"']},{'"'"'label'"'"': '"'"'operator-home'"'"', '"'"'path'"'"': '"'"'/var/home'"'"', '"'"'excludes'"'"': ['"'"'.cache'"'"', '"'"'.local/share/Trash'"'"', '"'"'node_modules'"'"', '"'"'.git'"'"', '"'"'__pycache__'"'"']},{'"'"'label'"'"': '"'"'windows-home'"'"', '"'"'path'"'"': '"'"'/mnt/c/Users'"'"', '"'"'max_depth'"'"': 4, '"'"'excludes'"'"': ['"'"'AppData'"'"', '"'"'.cache'"'"', '"'"'node_modules'"'"', '"'"'.git'"'"', '"'"'OneDrive*'"'"', '"'"'Cookies'"'"']}'
: "${MIOS_DAEMON_INDEX_SUMMARY_MAX_BYTES:=240}"
: "${MIOS_DAEMON_LAUNCH_CLAIM_DETECT:=model}"
: "${MIOS_DAEMON_POST_CHECK_FLATPAK_INSTALL:=flatpak_installed}"
: "${MIOS_DAEMON_POST_CHECK_FOCUS_WINDOW:=window_visible}"
: "${MIOS_DAEMON_POST_CHECK_LAUNCH_APP:=window_visible}"
: "${MIOS_DAEMON_POST_CHECK_OPEN_APP:=window_visible}"
: "${MIOS_DAEMON_POST_CHECK_OPEN_URL:=window_visible}"
: "${MIOS_DAEMON_POST_CHECK_TEXT_CREATE:=file_exists}"
: "${MIOS_DAEMON_POST_CHECK_TEXT_STR_REPLACE:=file_nonempty}"
: "${MIOS_DAEMON_PRESSURE_GPU_UTIL_CEIL:=90}"
: "${MIOS_DAEMON_PRESSURE_LOAD_CEIL:=8.0}"
: "${MIOS_DAEMON_PRESSURE_SKIP:=false}"
: "${MIOS_DAEMON_QUIESCENCE_WINDOW_MIN:=10}"
: "${MIOS_DAEMON_REFUSAL_DETECT:=model}"
: "${MIOS_DAEMON_REFUSAL_LIMIT_PER_MIN:=20}"
[ -n "${MIOS_DASHBOARD_ROWS+x}" ] || MIOS_DASHBOARD_ROWS='['"'"'version'"'"', '"'"'date'"'"'],['"'"'user'"'"', '"'"'uptime'"'"'],['"'"'cpu'"'"', '"'"'gpu_discrete'"'"'],['"'"'disk_c'"'"', '"'"'disk_m'"'"'],['"'"'ram'"'"', '"'"'swap'"'"'],['"'"'kernel'"'"', '"'"'shell'"'"'],['"'"'host'"'"', '"'"'font'"'"']'
: "${MIOS_DASHBOARD_SHOW_LOGO:=false}"
: "${MIOS_DASHBOARD_SHOW_SERVICES:=true}"
: "${MIOS_DASHBOARD_SHOW_TITLE:=true}"
: "${MIOS_DASHBOARD_SHOW_VERB_HINTS:=true}"
: "${MIOS_DASHBOARD_TITLE:=MiOS  --  My Personal Operating System}"
: "${MIOS_DASHBOARD_VERB_HINT:=build  config  dash  mini  ai  code  dev  summary  user  pull  update  help}"
: "${MIOS_DATA_DISK_LETTER:=M}"
: "${MIOS_DATA_DISK_MB:=262656}"
: "${MIOS_DB_BACKEND:=postgres}"
: "${MIOS_DCI_FLOW_ENABLED:=false}"
: "${MIOS_DEFAULT_GROUPS:=wheel,libvirt,kvm,video,render,input,dialout,docker}"
: "${MIOS_DEFAULT_HOST:=mios}"
: "${MIOS_DEFAULT_KEYBOARD:=us}"
: "${MIOS_DEFAULT_LOCALE:=en_US.UTF-8}"
: "${MIOS_DEFAULT_PASSWORD:=mios}"
: "${MIOS_DEFAULT_SHELL:=/bin/bash}"
: "${MIOS_DEFAULT_TIMEZONE:=UTC}"
: "${MIOS_DEFAULT_USER:=mios}"
: "${MIOS_DEPLOYMENT_TARGET_AMI:=false}"
: "${MIOS_DEPLOYMENT_TARGET_ANACONDA_ISO:=true}"
: "${MIOS_DEPLOYMENT_TARGET_GCE:=false}"
: "${MIOS_DEPLOYMENT_TARGET_ISO:=true}"
: "${MIOS_DEPLOYMENT_TARGET_OVA:=false}"
: "${MIOS_DEPLOYMENT_TARGET_PXE_TAR_XZ:=false}"
: "${MIOS_DEPLOYMENT_TARGET_QCOW2:=true}"
: "${MIOS_DEPLOYMENT_TARGET_RAW:=true}"
: "${MIOS_DEPLOYMENT_TARGET_VHD:=true}"
: "${MIOS_DEPLOYMENT_TARGET_VMDK:=false}"
: "${MIOS_DEPLOY_ARTIFACTS_ISO_MINSIZE:=150 GiB}"
: "${MIOS_DEPLOY_ARTIFACTS_RAW_SIZE:=80 GiB}"
[ -n "${MIOS_DESKTOP_APPS+x}" ] || MIOS_DESKTOP_APPS='{'"'"'id'"'"': '"'"'org.gnome.Epiphany'"'"', '"'"'remote'"'"': '"'"'flathub'"'"', '"'"'role'"'"': '"'"'browser'"'"', '"'"'default'"'"': True, '"'"'description'"'"': '"'"'GNOME Web -- the default MiOS flatpak browser (libadwaita, native dark, WSLg-compatible with the split-renderer override below).'"'"', '"'"'overrides'"'"': {'"'"'GDK_BACKEND'"'"': '"'"'x11'"'"', '"'"'WEBKIT_DISABLE_COMPOSITING_MODE'"'"': 1, '"'"'WEBKIT_DISABLE_DMABUF_RENDERER'"'"': 1}},{'"'"'id'"'"': '"'"'org.gnome.Nautilus.Devel'"'"', '"'"'remote'"'"': '"'"'gnome-nightly'"'"', '"'"'role'"'"': '"'"'file-manager'"'"', '"'"'default'"'"': True, '"'"'description'"'"': '"'"'GNOME Files (Nautilus). Devel build because Flathub stable is EOL on GNOME 3.28 runtime.'"'"'},{'"'"'id'"'"': '"'"'app.devsuite.Ptyxis'"'"', '"'"'remote'"'"': '"'"'flathub'"'"', '"'"'role'"'"': '"'"'terminal'"'"', '"'"'default'"'"': True, '"'"'description'"'"': '"'"'Ptyxis -- GNOME 47-era libadwaita terminal (the rename of org.gnome.Ptyxis).'"'"'},{'"'"'id'"'"': '"'"'com.google.ChromeDev'"'"', '"'"'remote'"'"': '"'"'flathub'"'"', '"'"'role'"'"': '"'"'browser'"'"', '"'"'default'"'"': False, '"'"'launcher'"'"': '"'"'mios-chrome'"'"', '"'"'description'"'"': '"'"'Google Chrome Dev channel. Operator-facing alt browser + Hermes-Agent CDP target. `launcher = mios-chrome` so dispatch sets the CDP port + WSLg env BEFORE flatpak-run.'"'"', '"'"'com'"'"': {'"'"'google'"'"': {'"'"'ChromeDev'"'"': {'"'"'overrides'"'"': {'"'"'GDK_BACKEND'"'"': '"'"'wayland'"'"', '"'"'CHROME_DEFAULT_ARGS'"'"': '"'"'--ozone-platform=wayland --enable-features=UseOzonePlatform,WaylandWindowDecorations --gtk-version=4 --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1'"'"'}}}}},{'"'"'id'"'"': '"'"'com.mattjakeman.ExtensionManager'"'"', '"'"'remote'"'"': '"'"'flathub'"'"', '"'"'role'"'"': '"'"'extensions'"'"', '"'"'default'"'"': True, '"'"'description'"'"': '"'"'GNOME shell extensions manager.'"'"'},{'"'"'id'"'"': '"'"'com.github.tchx84.Flatseal'"'"', '"'"'remote'"'"': '"'"'flathub'"'"', '"'"'role'"'"': '"'"'flatpak-permissions'"'"', '"'"'default'"'"': True, '"'"'description'"'"': '"'"'Flatseal -- per-flatpak permissions UI.'"'"'},{'"'"'id'"'"': '"'"'org.gtk.Gtk3theme.adw-gtk3-dark'"'"', '"'"'remote'"'"': '"'"'flathub'"'"', '"'"'description'"'"': '"'"'adw-gtk3-dark theme extension (consumed by GTK3 apps inside flatpak sandboxes).'"'"'},{'"'"'id'"'"': '"'"'org.gtk.Gtk3theme.adw-gtk3'"'"', '"'"'remote'"'"': '"'"'flathub'"'"', '"'"'description'"'"': '"'"'adw-gtk3 theme extension (light variant, kept for apps that auto-switch).'"'"'}'
[ -n "${MIOS_DESKTOP_APP_TYPES+x}" ] || MIOS_DESKTOP_APP_TYPES='{'"'"'type'"'"': '"'"'browser'"'"', '"'"'os_pref'"'"': '"'"'linux-first'"'"', '"'"'default'"'"': '"'"'epiphany'"'"', '"'"'windows_default'"'"': '"'"'zen'"'"', '"'"'description'"'"': "Web browser -- Linux flatpak by default; Zen (the Windows default browser) on Windows / '"'"'my browser'"'"' intent."},{'"'"'type'"'"': '"'"'files'"'"', '"'"'os_pref'"'"': '"'"'linux-first'"'"', '"'"'default'"'"': '"'"'nautilus'"'"', '"'"'description'"'"': '"'"'File manager.'"'"'},{'"'"'type'"'"': '"'"'editor'"'"', '"'"'os_pref'"'"': '"'"'linux-first'"'"', '"'"'default'"'"': '"'"'gedit'"'"', '"'"'description'"'"': '"'"'Text editor.'"'"'},{'"'"'type'"'"': '"'"'terminal'"'"', '"'"'os_pref'"'"': '"'"'linux-first'"'"', '"'"'default'"'"': '"'"'ptyxis'"'"', '"'"'description'"'"': '"'"'Terminal emulator.'"'"'},{'"'"'type'"'"': '"'"'media'"'"', '"'"'os_pref'"'"': '"'"'linux-first'"'"', '"'"'default'"'"': '"'"'showtime'"'"', '"'"'description'"'"': '"'"'Media / video player.'"'"'},{'"'"'type'"'"': '"'"'games'"'"', '"'"'os_pref'"'"': '"'"'windows'"'"', '"'"'windows_default'"'"': '"'"'steam'"'"', '"'"'description'"'"': '"'"'Games + game launchers -- the Windows side (Steam/Epic/GOG/Xbox).'"'"'},{'"'"'type'"'"': '"'"'settings'"'"', '"'"'os_pref'"'"': '"'"'both'"'"', '"'"'default'"'"': '"'"'gnome-control-center'"'"', '"'"'description'"'"': '"'"'System settings -- both OSes have one; agent picks by which system the ask targets.'"'"'},{'"'"'type'"'"': '"'"'system'"'"', '"'"'os_pref'"'"': '"'"'both'"'"', '"'"'description'"'"': '"'"'System / OS apps -- assume either side; agent discerns from context.'"'"'},{'"'"'type'"'"': '"'"'games'"'"', '"'"'os_priority'"'"': '"'"'windows'"'"'},{'"'"'type'"'"': '"'"'settings'"'"', '"'"'os_priority'"'"': '"'"'both'"'"'},{'"'"'type'"'"': '"'"'system'"'"', '"'"'os_priority'"'"': '"'"'both'"'"'},{'"'"'type'"'"': '"'"'browser'"'"', '"'"'os_priority'"'"': '"'"'linux-first'"'"', '"'"'linux_default'"'"': '"'"'org.gnome.Epiphany'"'"', '"'"'windows_default'"'"': '"'"'zen'"'"'},{'"'"'type'"'"': '"'"'fallback'"'"', '"'"'os_priority'"'"': '"'"'linux-first'"'"'}'
: "${MIOS_DESKTOP_COLOR_SCHEME:=prefer-dark}"
: "${MIOS_DESKTOP_FLATPAKS:=org.gtk.Gtk3theme.adw-gtk3-dark,org.gtk.Gtk3theme.adw-gtk3,app.devsuite.Ptyxis,gnome-nightly:org.gnome.Nautilus.Devel,fedora:org.gnome.Epiphany,com.github.tchx84.Flatseal,com.mattjakeman.ExtensionManager,com.google.ChromeDev}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_AI_HINT:=Desktop entry for MiOS Settings — the one unified configuration surface. Launches mios-configurator-launch, which opens the configurator embedded in the MiOS Portal (http://localhost:8700/configure) and falls back to the standalone HTML editor only when the Portal is unreachable. All settings serialise to the mios.toml SSOT (identity, AI models, packages, flatpaks, desktop).}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_AI_RELATED:=/etc/mios/mios.toml, /usr/libexec/mios/mios-configurator-launch, mios-configurator-launch, http://localhost:8700/configure}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_CATEGORIES:=System;Settings;PackageManager;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_COMMENT:=One unified surface for every MiOS setting — identity, AI, packages, flatpaks, desktop (writes the mios.toml SSOT)}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_EXEC_CMD:=/usr/libexec/mios/mios-configurator-launch}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_GENERIC_NAME:=System Settings}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_ICON:=preferences-system}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_KEYWORDS:=mios;configurator;system;settings;packages;flatpak;ai;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_STARTUP_WM_CLASS:=org.gnome.Epiphany}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_TITLE:=MiOS Settings}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_TRAILING_COMMENTS+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_CONFIGURATOR_TRAILING_COMMENTS='# WSLg auto-publishes this entry to the Windows Start Menu under,# "<Distro> Apps" when MiOS-DEV is the source distro, so the same,# .desktop file gives Linux GNOME Dock + Activities visibility on a,# deployed MiOS host AND a Windows Start Menu entry on the Win-side,# dev VM. One file, two surfaces.'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_AI_HINT:=Desktop entry for the Ceph storage dashboard that provides a GUI interface for managing the Ceph cluster via a web browser at port 8443.}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_CATEGORIES:=System;Network;}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_COMMENT+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_COMMENT='Open the Ceph storage dashboard at https://localhost:{port}/'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_GENERIC_NAME:=Storage Cluster Dashboard}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_ICON:=drive-multidisk-symbolic}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_KEYWORDS:=mios;ceph;storage;cluster;dashboard;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_NO_DISPLAY:=false}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_PORT_KEY:=ceph_dashboard}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_SCHEME:=https}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CEPH_TITLE:=MiOS Ceph Dashboard}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_AI_HINT:=Desktop entry for the MiOS Cockpit web console, providing a shortcut to the system administration interface at port 9090 for remote management and monitoring.}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_CATEGORIES:=System;Network;Settings;}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_COMMENT+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_COMMENT='Open the Cockpit host web console at https://localhost:{port}/'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_GENERIC_NAME:=System Console}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_ICON:=utilities-system-monitor-symbolic}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_KEYWORDS:=mios;cockpit;admin;console;system;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_PORT_KEY:=cockpit}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_SCHEME:=https}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_COCKPIT_TITLE:=MiOS Cockpit}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_AI_HINT+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_AI_HINT='Desktop entry for the code-server web IDE, providing a launcher for agents to identify and open the MiOS development environment at the local port 8080 via the system'"'"'s default browser.'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_CATEGORIES:=Development;IDE;TextEditor;}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_COMMENT+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_COMMENT='Open code-server at http://localhost:{port}/ in the default browser'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_GENERIC_NAME:=VS Code in a Browser}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_ICON:=visual-studio-code}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_KEYWORDS:=mios;code-server;vscode;editor;ide;git;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_PORT_KEY:=code_server}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_CODE_SERVER_TITLE:=MiOS Code (code-server)}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_AI_HINT+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_AI_HINT='Desktop entry for the MiOS Forge (Forgejo) service, providing a launcher to open the local Git repository management web interface at http://localhost:{port}/ via the system'"'"'s default browser.'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_CATEGORIES:=Development;RevisionControl;Network;}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_COMMENT+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_COMMENT='Open the local Forgejo git forge at http://localhost:{port}/'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_GENERIC_NAME:=Self-Hosted Git Forge (Forgejo)}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_ICON:=text-x-generic-symbolic}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_KEYWORDS:=mios;forge;forgejo;git;gitea;repo;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_PORT_KEY:=forge_http}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_FORGE_TITLE:=MiOS Forge}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_AI_HINT:=Desktop entry for the Guacamole remote desktop gateway, providing a launcher to open the local web interface at port 8080 for RDP/VNC access.}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_CATEGORIES:=Network;RemoteAccess;}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_COMMENT+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_COMMENT='Open Apache Guacamole at http://localhost:{port}/guacamole/'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_GENERIC_NAME:=Browser Remote Desktop}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_ICON:=preferences-desktop-remote-desktop-symbolic}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_KEYWORDS:=mios;guacamole;rdp;vnc;remote;desktop;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_PATH:=/guacamole/}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_PORT_KEY:=guacamole_web}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_GUACAMOLE_TITLE:=MiOS Guacamole}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_AI_HINT:=Desktop entry for the Hermes Agent gateway, providing a shortcut to the local /v1 API surface at port 8642 for interacting with the primary MiOS AI agent.}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_CATEGORIES:=Development;Network;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_COMMENT:=Open the Hermes-Agent /v1 surface (the LIVE MiOS agent at root)}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_GENERIC_NAME:=AI Agent Gateway}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_ICON:=applications-science-symbolic}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_KEYWORDS:=mios;hermes;agent;api;openai;v1;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_PATH:=/v1}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_PORT_KEY:=hermes}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_HERMES_TITLE:=MiOS Hermes Agent}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_LLM_LIGHT_AI_HINT:=Desktop entry for the LLM Light service providing the local LLM and embedding backend, used by agents to identify and launch the local inference server at port 11450.}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_LLM_LIGHT_CATEGORIES:=Development;Network;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_LLM_LIGHT_COMMENT:=Open the LLM Light API surface (local model server)}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_LLM_LIGHT_GENERIC_NAME:=Local LLM + Embedding Backend (llama-swap)}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_LLM_LIGHT_ICON:=applications-engineering-symbolic}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_LLM_LIGHT_KEYWORDS:=mios;llm-light;llama-swap;llm;embedding;ai;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_LLM_LIGHT_PORT_KEY:=llm_light}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_LLM_LIGHT_TITLE:=MiOS LLM Light}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_AI_HINT:=Desktop entry for the SearXNG metasearch proxy; used by agents to identify and launch the local search interface at port 8899 via a web browser.}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_CATEGORIES:=Network;WebBrowser;}"
[ -n "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_COMMENT+x}" ] || MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_COMMENT='Open the local SearXNG metasearch proxy at http://localhost:{port}/'
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_GENERIC_NAME:=Privacy Metasearch}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_ICON:=system-search-symbolic}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_KEYWORDS:=mios;searxng;search;metasearch;privacy;}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_PORT_KEY:=searxng}"
: "${MIOS_DESKTOP_LAUNCHERS_MIOS_SVC_SEARXNG_TITLE:=MiOS Search (SearXNG)}"
: "${MIOS_DESKTOP_SESSION:=gnome}"
: "${MIOS_DESKTOP_START_MENU_COCKPIT_LABEL:=Cockpit}"
: "${MIOS_DESKTOP_START_MENU_COCKPIT_PORT_KEY:=cockpit}"
: "${MIOS_DESKTOP_START_MENU_COCKPIT_SCHEME:=https}"
: "${MIOS_DESKTOP_START_MENU_CODE_SERVER_LABEL:=Code}"
: "${MIOS_DESKTOP_START_MENU_CODE_SERVER_PORT_KEY:=code_server}"
: "${MIOS_DESKTOP_START_MENU_CODE_SERVER_SCHEME:=http}"
: "${MIOS_DESKTOP_START_MENU_FORGE_LABEL:=Forge}"
: "${MIOS_DESKTOP_START_MENU_FORGE_PORT_KEY:=forge_http}"
: "${MIOS_DESKTOP_START_MENU_FORGE_SCHEME:=http}"
: "${MIOS_DESKTOP_START_MENU_GUACAMOLE_WEB_LABEL:=Guacamole}"
: "${MIOS_DESKTOP_START_MENU_GUACAMOLE_WEB_PORT_KEY:=guacamole_web}"
: "${MIOS_DESKTOP_START_MENU_GUACAMOLE_WEB_SCHEME:=http}"
: "${MIOS_DESKTOP_START_MENU_HERMES_DASHBOARD_LABEL:=Dashboard}"
: "${MIOS_DESKTOP_START_MENU_HERMES_DASHBOARD_PORT_KEY:=hermes_dashboard}"
: "${MIOS_DESKTOP_START_MENU_HERMES_DASHBOARD_SCHEME:=http}"
: "${MIOS_DESKTOP_START_MENU_PUBLISH:=forge,cockpit,code_server,searxng,hermes_dashboard,guacamole_web}"
: "${MIOS_DESKTOP_START_MENU_SEARXNG_LABEL:=Search}"
: "${MIOS_DESKTOP_START_MENU_SEARXNG_PORT_KEY:=searxng}"
: "${MIOS_DESKTOP_START_MENU_SEARXNG_SCHEME:=http}"
: "${MIOS_DEVELOPER:=MiOS}"
: "${MIOS_DEV_VM_BASE_IMAGE:=quay.io/podman/machine-os:6.0}"
: "${MIOS_DEV_VM_CPUS:=max}"
: "${MIOS_DEV_VM_CPU_RESERVE_MIN:=2}"
: "${MIOS_DEV_VM_CPU_RESERVE_PCT:=15}"
: "${MIOS_DEV_VM_DISK_GB:=max}"
: "${MIOS_DEV_VM_DISK_RESERVE_GB:=32}"
: "${MIOS_DEV_VM_GPU:=max}"
: "${MIOS_DEV_VM_MEMORY_MB:=max}"
: "${MIOS_DEV_VM_MEMORY_RESERVE_GB:=4}"
: "${MIOS_DEV_VM_MEMORY_RESERVE_PCT:=15}"
: "${MIOS_DISPATCH_ADMIT_ENABLE:=true}"
: "${MIOS_DISPATCH_ADMIT_LOAD_CEIL:=56}"
: "${MIOS_DISPATCH_ADMIT_MAX_WAIT:=8.0}"
: "${MIOS_DISPATCH_ADMIT_MEM_PCT:=92}"
: "${MIOS_DISPATCH_AGENT_CONCURRENCY:=3}"
: "${MIOS_DISPATCH_AUTONOMY_AUTONOMOUS_PRIORITY:=low}"
: "${MIOS_DISPATCH_AUTONOMY_MAX_DISPATCH_DEPTH:=2}"
: "${MIOS_DISPATCH_BATCH_ENABLE:=false}"
: "${MIOS_DISPATCH_BATCH_INTERVAL_S:=0.05}"
: "${MIOS_DISPATCH_BATCH_MAX_SIZE:=8}"
: "${MIOS_DISPATCH_BATCH_NATIVE_HINTS:=8530,8520,8500}"
: "${MIOS_DISPATCH_COUNCIL_DEFAULT:=true}"
: "${MIOS_DISPATCH_COUNCIL_MAX:=4}"
: "${MIOS_DISPATCH_CUA_ENABLE:=false}"
: "${MIOS_DISPATCH_CUA_MAX_STEPS:=12}"
: "${MIOS_DISPATCH_DAG_EMPTY_NATIVE_FALLBACK:=true}"
: "${MIOS_DISPATCH_DAG_NODE_DEADLINE_S:=140}"
: "${MIOS_DISPATCH_DAG_NODE_DEADLINE_SLOW_S:=150}"
: "${MIOS_DISPATCH_DAG_NODE_MAX_TOKENS:=800}"
: "${MIOS_DISPATCH_DAG_NODE_RETRY:=1}"
: "${MIOS_DISPATCH_DAG_NODE_SLOW_MAX_TOKENS:=350}"
: "${MIOS_DISPATCH_DEEPEN_DEADLINE_S:=60}"
: "${MIOS_DISPATCH_DEEPEN_EARLY_EXIT:=false}"
: "${MIOS_DISPATCH_DEEPEN_ENABLED:=true}"
: "${MIOS_DISPATCH_DEEPEN_FETCH:=true}"
: "${MIOS_DISPATCH_DEEPEN_ITERS:=12}"
: "${MIOS_DISPATCH_DEEPEN_JUDGE_TIMEOUT_S:=6}"
: "${MIOS_DISPATCH_DEEPEN_LANES:=gpu,accelerator}"
: "${MIOS_DISPATCH_DEEPEN_WEB_TIMEOUT_S:=20}"
: "${MIOS_DISPATCH_DEFAULT_HOP_BUDGET:=2}"
: "${MIOS_DISPATCH_DEFAULT_TOOL_CAP:=16}"
: "${MIOS_DISPATCH_ENABLE:=true}"
: "${MIOS_DISPATCH_ENDPOINT_CONCURRENCY:=4}"
: "${MIOS_DISPATCH_FANOUT_MAX:=3}"
: "${MIOS_DISPATCH_FANOUT_MIN:=1}"
: "${MIOS_DISPATCH_FANOUT_SELECT_MODE:=model}"
: "${MIOS_DISPATCH_FANOUT_SELECT_TIMEOUT_S:=8}"
: "${MIOS_DISPATCH_GLOBAL_CONCURRENCY:=16}"
: "${MIOS_DISPATCH_GPU_PROFILE:=orchestrator}"
: "${MIOS_DISPATCH_KERNEL_ROUTE:=false}"
: "${MIOS_DISPATCH_KV_FORK_ENABLE:=false}"
: "${MIOS_DISPATCH_KV_FORK_MAX_BRANCHES:=4}"
: "${MIOS_DISPATCH_KV_GC_ENABLE:=true}"
: "${MIOS_DISPATCH_KV_GC_INTERVAL_S:=900}"
: "${MIOS_DISPATCH_KV_GC_MAX_BYTES:=2000000000}"
: "${MIOS_DISPATCH_KV_GC_TTL_S:=86400}"
: "${MIOS_DISPATCH_KV_PAGING_ENABLE:=true}"
: "${MIOS_DISPATCH_KV_PAGING_HINTS:=11436}"
: "${MIOS_DISPATCH_KV_PAGING_SLOT:=0}"
: "${MIOS_DISPATCH_KV_PAGING_TIMEOUT:=12.0}"
: "${MIOS_DISPATCH_LANE_CONCURRENCY:=3}"
: "${MIOS_DISPATCH_LANE_CONCURRENCY_CPU:=2}"
: "${MIOS_DISPATCH_LANE_CONCURRENCY_GPU:=2}"
: "${MIOS_DISPATCH_LANE_CONCURRENCY_GPU0:=4}"
: "${MIOS_DISPATCH_LANE_PRIORITY:=gpu:8,cpu:7,accelerator:6,igpu:3,mobile:2,_default:5}"
: "${MIOS_DISPATCH_LANE_TOOL_CAP:=igpu:12,mobile:12}"
: "${MIOS_DISPATCH_LLM_NUM_PREDICT_CAP:=2048}"
: "${MIOS_DISPATCH_LLM_NUM_PREDICT_CAP_CPU:=512}"
: "${MIOS_DISPATCH_MAX_SOURCES:=8}"
: "${MIOS_DISPATCH_MODE:=council}"
: "${MIOS_DISPATCH_NATIVE_LOOP_DATE_ANCHOR:=true}"
: "${MIOS_DISPATCH_NATIVE_LOOP_DATE_IN_QUERY:=true}"
: "${MIOS_DISPATCH_NATIVE_LOOP_MATH_HINT:=true}"
: "${MIOS_DISPATCH_NATIVE_LOOP_QUERY_REFORMULATE:=true}"
: "${MIOS_DISPATCH_NODES_RESEARCH_ONLY:=false}"
: "${MIOS_DISPATCH_NO_TOOL_CHOICE_HINTS:=11436}"
: "${MIOS_DISPATCH_OFFLOAD_CPU:=false}"
: "${MIOS_DISPATCH_PARALLEL_TOOLS_HINTS:=8520,8530}"
: "${MIOS_DISPATCH_PRIORITY_QUEUE_ENABLE:=true}"
: "${MIOS_DISPATCH_PRIORITY_STARVATION_MS:=4000}"
: "${MIOS_DISPATCH_REPUTATION_FLUSH_S:=300.0}"
: "${MIOS_DISPATCH_REQUEST_CANCEL_ENABLE:=1}"
: "${MIOS_DISPATCH_REQUEST_CANCEL_POLL_S:=2.0}"
: "${MIOS_DISPATCH_RERANK_FANOUT:=3}"
: "${MIOS_DISPATCH_RERANK_MIN_K:=24}"
: "${MIOS_DISPATCH_RERANK_MMR_LAMBDA:=0.8}"
: "${MIOS_DISPATCH_RERANK_RRF_K:=60}"
: "${MIOS_DISPATCH_RERANK_SKIP_MARGIN:=0.08}"
: "${MIOS_DISPATCH_RR_ENABLE:=false}"
: "${MIOS_DISPATCH_RR_MAX_SUSPENDED:=4}"
: "${MIOS_DISPATCH_RR_QUANTUM_S:=8.0}"
: "${MIOS_DISPATCH_RR_SLICE_TIMEOUT_S:=120.0}"
: "${MIOS_DISPATCH_RR_SLICE_TOKENS:=512}"
: "${MIOS_DISPATCH_RUNAWAY_REAP:=true}"
: "${MIOS_DISPATCH_SANDBOX_ENFORCE:=false}"
: "${MIOS_DISPATCH_SLOW_LANE_TOOL_CAP:=12}"
: "${MIOS_DISPATCH_SLO_SHED_ENABLE:=false}"
: "${MIOS_DISPATCH_SOURCES_REGISTRY_CAP:=64}"
: "${MIOS_DISPATCH_STABLE_PREFIX_HINT:=false}"
: "${MIOS_DISPATCH_STABLE_PREFIX_TAIL:=4}"
: "${MIOS_DISPATCH_STABLE_TOOL_PREFIX:=true}"
: "${MIOS_DISPATCH_SWARM_MAX_CPU_NODES:=2}"
: "${MIOS_DISPATCH_SWARM_MAX_WIDTH:=3}"
: "${MIOS_DISPATCH_SWARM_SATURATE:=true}"
: "${MIOS_DISPATCH_SWARM_TRUST_ATOMIC:=true}"
: "${MIOS_DISPATCH_TOOL_RERANK:=true}"
: "${MIOS_DISPATCH_TRACE_ENABLE:=true}"
: "${MIOS_DISPATCH_TRACE_MAX_SPANS_PER_TRACE:=128}"
: "${MIOS_DISPATCH_TRACE_MAX_TRACES:=256}"
: "${MIOS_DISPATCH_TURN_DEADLINE_S:=600}"
: "${MIOS_DISPATCH_VRAM_BUDGET_MB:=11000}"
: "${MIOS_DISPATCH_VRAM_COLOAD_EST_MB:=5000}"
: "${MIOS_DISPATCH_VRAM_COLOAD_RESERVE_MB:=3000}"
: "${MIOS_DISPATCH_VRAM_RECLAIM_IDLE:=false}"
: "${MIOS_DISPATCH_WORKER_MCP_TOOLS:=true}"
: "${MIOS_DOCS_BLOCKLIST_GLOBS:=automation/lib/globals.sh,automation/lib/globals.ps1,tools/native/mios-unit-gen/tests/golden/**,**/*.generated.*,usr/share/mios/names.generated.txt}"
[ -n "${MIOS_DOCS_BOILERPLATE_WHAT_MIOS_IS+x}" ] || MIOS_DOCS_BOILERPLATE_WHAT_MIOS_IS='MiOS is one thing built two ways at once: an immutable, `bootc`/OCI-shaped
Fedora workstation -- the whole OS is a single container image, so `bootc
upgrade` behaves like a `git pull` and `bootc rollback` like a Ctrl-Z -- that
is *also* a local, self-hosted, agentic AI operating system.
'
: "${MIOS_DOCS_DISTILL_DEST_DIR:=usr/share/doc/mios/manual}"
: "${MIOS_DOCS_DISTILL_ENABLE:=true}"
: "${MIOS_DOCS_DISTILL_SKIP_GLOBS:=usr/share/mios/mios.toml,tools/native/mios-unit-gen/tests/golden/*,usr/share/doc/*}"
: "${MIOS_DOCS_LANDING_MIN_WORD_RATIO:=0.9}"
: "${MIOS_DOCS_LINK_BASE:=repo}"
: "${MIOS_DOCS_LLM_PAYLOAD_GLOBS:=usr/share/mios/owui/**,usr/share/mios/hermes/**,usr/share/mios/prompts/**,usr/share/mios/ai/**,etc/mios/system-prompts/**,usr/share/mios/agents/**,usr/share/mios/cookbooks/**,etc/skel/.config/mios/**}"
: "${MIOS_DOCS_MAX_OVERLONG_HINTS:=1}"
: "${MIOS_DOCS_MAX_STALE_REFS:=150}"
: "${MIOS_DOCS_MAX_UNMIGRATED_NARRATIVE:=1724}"
: "${MIOS_DOCS_MIGRATE_MIN_LINES:=6}"
: "${MIOS_DOCS_MIGRATE_MIN_WORDS:=60}"
: "${MIOS_DOCS_PORT_CLEAN:=README.md,CLAUDE.md,GEMINI.md,AGENTS.md,MiOS.md,SECURITY.md,.github/ai-instructions.md,llms.txt,llms-full.txt,usr/share/doc/mios/reference/api.md,system-prompt.md,tools/README.md,etc/mios/ai/system-prompt.md,etc/mios/system-prompts/mios-reviewer.md,usr/share/mios/ai/INDEX.md,usr/share/mios/ai/audit-prompt.md,usr/share/mios/security/README.md,usr/share/mios/docs/agents/AI-ARCHITECTURE.md,usr/share/mios/docs/ai-pipeline-map.md,usr/share/mios/cookbooks/ingest-kb.md,usr/share/mios/hermes/skills/mios-skill-catalog/SKILL.md,usr/share/mios/hermes/skills/parallel-fanout/SKILL.md,installation/UNIFY.md,tools/windows/README-WINDOWS.md,etc/mios/system-prompts/mios-engineer.md,etc/mios/system-prompts/mios-troubleshoot.md,usr/share/mios/ai/system.md,usr/share/mios/ai/hermes-soul-full.md,usr/share/mios/cookbooks/finetune-flow.md,usr/share/mios/cookbooks/local-rag-day0.md,usr/share/mios/docs/day-0/FIRST-BOOT.md,usr/share/mios/docs/agents/PC-CONTROL-LOCAL.md,usr/share/mios/docs/terminal/INVOCATIONS.md,usr/share/mios/hermes/skills/mios-environment/SKILL.md,usr/share/mios/hermes/skills/opencode-delegation/SKILL.md,usr/share/mios/open-webui/system-prompts/mios-agent.md,usr/share/doc/mios/manual.md,usr/share/doc/mios/manual/ch04-the-agentic-ai-stack.md,usr/share/doc/mios/manual/ch10-local-inference-lanes-and-llama-cpp.md,usr/share/doc/mios/adr/0005-sovereign-run-off-m-drive.md,usr/share/doc/mios/adr/0006-openai-api-only-ai-contract.md,usr/share/doc/mios/adr/0008-mios-cat-unified-entry-and-minification.md,usr/share/doc/mios/adr/0009-unified-config-surface.md,usr/share/doc/mios/adr/README.md,usr/share/doc/mios/concepts/OFFLINE-FIRST.md,usr/share/doc/mios/concepts/a2a-passport-conformance-2026-06-20.md,usr/share/doc/mios/concepts/agent-pipe-openai-standards-master-plan.md,usr/share/doc/mios/concepts/aios-engineering-blueprint.md,usr/share/doc/mios/concepts/aios-implementation-plan.md,usr/share/doc/mios/concepts/coderun-sandbox.md,usr/share/doc/mios/concepts/container-os-runtime.md,usr/share/doc/mios/concepts/foss-upstream-map.md,usr/share/doc/mios/concepts/mios-app-browser-portal-dashboard-design-2026-07-03.md,usr/share/doc/mios/concepts/multi-agent-buildout-plan.md,usr/share/doc/mios/concepts/naming-refactor-plan.md,usr/share/doc/mios/concepts/postgres-pgvector-unification.md,usr/share/doc/mios/concepts/roadmap-snapshot-decomposition-2026-06-22.md,usr/share/doc/mios/concepts/unified-ai-pipeline-2026-06-16.md,usr/share/doc/mios/concepts/upstream-gap-plan-2026-06.md,usr/share/doc/mios/concepts/ws-0-preflight-findings-2026-06-20.md,usr/share/doc/mios/concepts/ws-a3-central-path-cutover-worklist.md,usr/share/doc/mios/concepts/ws-subsystems-activation-2026-06-20.md,usr/share/doc/mios/concepts/ws7-uki-fapolicyd.md,usr/share/doc/mios/finetune.md,usr/share/doc/mios/guides/agent-windows-ssh.md,usr/share/doc/mios/guides/deploy.md,usr/share/doc/mios/guides/edge-node-join.md,usr/share/doc/mios/guides/engineering.md,usr/share/doc/mios/guides/hummingbird-distroless.md,usr/share/doc/mios/guides/inference-consolidation.md,usr/share/doc/mios/guides/security.md,usr/share/doc/mios/manual/ch05-federation-and-computer-use.md,usr/share/doc/mios/manual/ch11-heavy-gpu-lanes-and-sglang-vllm.md,usr/share/doc/mios/manual/ch14-agent-to-agent-delegation-protocols.md,usr/share/doc/mios/manual/ch25-local-search-engine-and-searxng.md,usr/share/doc/mios/manual/ch48-local-ai-web-consoles.md,usr/share/doc/mios/manual/ch51-distilled-system-knowledge-code-invariants.md,usr/share/doc/mios/manual/federation.md,usr/share/doc/mios/manual/hermes.md,usr/share/doc/mios/manual/llamacpp.md,usr/share/doc/mios/manual/mios.md,usr/share/doc/mios/manual/opencode-gateway.md,usr/share/doc/mios/manual/root.md,usr/share/doc/mios/manual/routing.md,usr/share/doc/mios/manual/scheduler.md,usr/share/doc/mios/manual/system.md,usr/share/doc/mios/manual/tools.md,usr/share/doc/mios/reference/PACKAGES.md,usr/share/doc/mios/reference/audit-security.md,usr/share/doc/mios/reference/build-scripts.md,usr/share/doc/mios/reference/credits.md,usr/share/doc/mios/reference/engineering-reference.md,usr/share/doc/mios/reference/hwcaps.md,usr/share/doc/mios/reference/maturity-and-release-runbook.md,usr/share/doc/mios/reference/sources.md,usr/share/doc/mios/reference/tree.md,usr/share/doc/mios/upstream/cdi.md,usr/share/doc/mios/upstream/deploy-targets.md,usr/share/doc/mios/upstream/fedora-bootc.md,usr/share/doc/mios/upstream/ghcr.md,usr/share/doc/mios/upstream/nvidia.md,usr/share/doc/mios/upstream/podman.md,usr/share/doc/mios/upstream/related-distros.md,usr/share/doc/mios/upstream/selinux.md,usr/share/mios/docs/MIOS-GEMINI-TASKS-2026-06-22.md,usr/share/mios/docs/MIOS-ROADMAP-PROGRESS-2026-06-22.md,usr/share/mios/docs/install-robustness-2026-06-21.md,automation/67-bake-surfer.sh,usr/share/mios/owui/pipes/mios_agent_pipe.py}"
: "${MIOS_DOCS_REF_ALLOWLIST:=/etc/ceph/ceph.conf,/etc/cdi/nvidia.yaml,/var/run/cdi/nvidia.yaml,/etc/containers/policy.json,/etc/mios/manifest.json,/var/,@@MIOS_,ollama,8080}"
: "${MIOS_DOCS_RENDER_EXTRA:=llms.txt,llms-full.txt}"
: "${MIOS_DOCS_RETIRED_PORTS:=11434,11450,11441,3030,8432,8441,8442,8633,8640,8641,8642,8888,8899}"
[ -n "${MIOS_DOCS_SANITIZE_PATH_REWRITES+x}" ] || MIOS_DOCS_SANITIZE_PATH_REWRITES='['"'"'file:///C:/MiOS/'"'"', '"'"''"'"'],['"'"'file:///C:/'"'"', '"'"''"'"'],['"'"'C:\\MiOS\\'"'"', '"'"'/usr/share/mios/'"'"'],['"'"'C:/MiOS/'"'"', '"'"'/usr/share/mios/'"'"'],['"'"'C:\\MiOS'"'"', '"'"'/usr/share/mios'"'"'],['"'"'C:/MiOS'"'"', '"'"'/usr/share/mios'"'"'],['"'"'/mnt/c/MiOS'"'"', '"'"'/usr/share/mios'"'"']'
[ -n "${MIOS_DOCS_SANITIZE_REDACT_PATTERNS+x}" ] || MIOS_DOCS_SANITIZE_REDACT_PATTERNS='(?i)[A-Za-z0-9_]*(?:api[_-]?key|secret|passwd|password|token)[A-Za-z0-9_]*\s*[:=]+\s*(?![>\s])[^\s"'"'"']{4,},\bsha256:[0-9a-f]{64}\b,(?i)\bBearer\s+[A-Za-z0-9._-]{16,}'
: "${MIOS_DOCS_SANITIZE_REDACT_WITH:=[redacted]}"
[ -n "${MIOS_DOCS_SIGNALS_CODE+x}" ] || MIOS_DOCS_SIGNALS_CODE='^\s*(if|for|while|def|class|function|export|set|return|elif|else|fi|done|esac|end)\b|[;{]\s*$|^\s*[\w.]+\s*=[^=]'
[ -n "${MIOS_DOCS_SIGNALS_FACT+x}" ] || MIOS_DOCS_SIGNALS_FACT='\b(broken|deprecated|removed|disabled|not supported|only on|requires|since|as of|WS-[A-Z]+|AGY-[0-9]+|ADR-[0-9]+|Law [0-9]+)\b'
[ -n "${MIOS_DOCS_SIGNALS_NARRATIVE+x}" ] || MIOS_DOCS_SIGNALS_NARRATIVE='\b(operator|used to|no longer|previously|regression|root cause|incident|reverted|scrapped|rejected|instead of|alternative|rationale|invariant|degrade|ADR-[0-9]+|Law [0-9]+|AGY-[0-9]+|WS-[A-Z]+|[0-9]{4}-[0-9]{2}-[0-9]{2})\b'
[ -n "${MIOS_DOCS_SIGNALS_WHY+x}" ] || MIOS_DOCS_SIGNALS_WHY='\b(because|so that|otherwise|avoid|prevents?|must not|never|do not|fail-open|fail-closed|deliberately|intentionally|noqa|workaround|upstream bug|race|deadlock)\b'
: "${MIOS_DOCS_STAY_MAX_LINES:=2}"
: "${MIOS_DOCS_STAY_MAX_WORDS:=25}"
: "${MIOS_DRIFT_DENYLIST:=mios_ctxpack,mios_embed_backfill,mios_provider_translate,mios_smartroute,mios_worker_tools}"
: "${MIOS_DRIFT_MONITOR_AXES:=verdict,intent}"
: "${MIOS_DRIFT_MONITOR_ENABLE:=false}"
: "${MIOS_DRIFT_MONITOR_MIN_SAMPLES:=30}"
: "${MIOS_DRIFT_MONITOR_THRESHOLD:=0.2}"
: "${MIOS_DRIFT_MONITOR_WINDOW:=200}"
: "${MIOS_EDITIONS_MIOS_AUTOUNATTEND_DEBLOAT_PROFILE:=minimal}"
: "${MIOS_EDITIONS_MIOS_AUTOUNATTEND_POSTURE:=B}"
: "${MIOS_EDITIONS_MIOS_AUTOUNATTEND_UUP_ARCH:=amd64}"
: "${MIOS_EDITIONS_MIOS_AUTOUNATTEND_UUP_CHANNEL:=retail}"
: "${MIOS_EDITIONS_MIOS_AUTOUNATTEND_XBOX_ENABLE:=false}"
: "${MIOS_EDITIONS_MIOS_BRANDING_LIVING_WALLPAPER:=false}"
: "${MIOS_EDITIONS_MIOS_COLORS_ACCENT:=#1A407F}"
: "${MIOS_EDITIONS_MIOS_METAL_GPU_ARBITRATION:=static}"
: "${MIOS_EDITIONS_MIOS_METAL_GPU_ASSIGNMENTS_MIOS_GUEST:=0000:01:00.0}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_AUTOUNATTEND_DEBLOAT_PROFILE:=gaming}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_AUTOUNATTEND_POSTURE:=C}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_AUTOUNATTEND_UUP_ARCH:=arm64}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_AUTOUNATTEND_UUP_CHANNEL:=dev}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_AUTOUNATTEND_XBOX_ENABLE:=true}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_BRANDING_LIVING_WALLPAPER:=true}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_COLORS_ACCENT:=#4B105C}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_METAL_GPU_ARBITRATION:=static}"
: "${MIOS_EDITIONS_MIOS_XBOX_ARM_METAL_GPU_ASSIGNMENTS_MIOS_GUEST:=0000:01:00.0}"
: "${MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_DEBLOAT_PROFILE:=gaming}"
: "${MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_POSTURE:=C}"
: "${MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_UUP_ARCH:=amd64}"
: "${MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_UUP_CHANNEL:=dev}"
: "${MIOS_EDITIONS_MIOS_XBOX_AUTOUNATTEND_XBOX_ENABLE:=true}"
: "${MIOS_EDITIONS_MIOS_XBOX_BRANDING_LIVING_WALLPAPER:=true}"
: "${MIOS_EDITIONS_MIOS_XBOX_COLORS_ACCENT:=#282262}"
: "${MIOS_EDITIONS_MIOS_XBOX_METAL_GPU_ARBITRATION:=static}"
: "${MIOS_EDITIONS_MIOS_XBOX_METAL_GPU_ASSIGNMENTS_MIOS_GUEST:=0000:01:00.0}"
[ -n "${MIOS_ENDPOINT+x}" ] || MIOS_ENDPOINT='http://localhost:'"${MIOS_PORT_AGENT_PIPE}"'/v1'
: "${MIOS_ENHANCED_SESSION_ENABLED:=true}"
: "${MIOS_ENHANCED_SESSION_PORT:=13389}"
: "${MIOS_ENHANCED_SESSION_RESOLUTION:=auto}"
: "${MIOS_ENV_MIOS_URL_BIBATA_API:=https://api.github.com/repos/ful1e5/Bibata_Cursor/releases/latest}"
[ -n "${MIOS_ENV_MIOS_URL_BIBATA_DL+x}" ] || MIOS_ENV_MIOS_URL_BIBATA_DL='https://github.com/ful1e5/Bibata_Cursor/releases/download/v{}/Bibata-Modern-Classic.tar.xz'
[ -n "${MIOS_ENV_MIOS_URL_BIBATA_SUM+x}" ] || MIOS_ENV_MIOS_URL_BIBATA_SUM='https://github.com/ful1e5/Bibata_Cursor/releases/download/v{}/sha256-{}.txt'
[ -n "${MIOS_ENV_MIOS_URL_CROWDSEC_REPO+x}" ] || MIOS_ENV_MIOS_URL_CROWDSEC_REPO='https://packagecloud.io/crowdsec/crowdsec/config_file.repo?os=fedora&dist=${FEDORA_VERSION}&source=script'
: "${MIOS_ENV_MIOS_URL_TAILSCALE_REPO:=https://pkgs.tailscale.com/stable/fedora/tailscale.repo}"
: "${MIOS_ENV_MIOS_URL_TERRA_REPO:=https://github.com/terrapkg/subatomic-repos/raw/main/terra.repo}"
[ -n "${MIOS_ENV_MIOS_URL_UBLUE_REPO+x}" ] || MIOS_ENV_MIOS_URL_UBLUE_REPO='https://copr.fedorainfracloud.org/coprs/ublue-os/packages/repo/fedora-${FEDORA_VERSION}/ublue-os-packages-fedora-${FEDORA_VERSION}.repo'
: "${MIOS_ETC_DIR:=/etc/mios}"
[ -n "${MIOS_ETC_AI_DIR+x}" ] || MIOS_ETC_AI_DIR="${MIOS_ETC_DIR}"'/ai'
[ -n "${MIOS_ETC_ENVD_DIR+x}" ] || MIOS_ETC_ENVD_DIR="${MIOS_ETC_DIR}"'/env.d'
[ -n "${MIOS_ETC_FORGE_DIR+x}" ] || MIOS_ETC_FORGE_DIR="${MIOS_ETC_DIR}"'/forge'
: "${MIOS_EVERYTHING_CLI:=/mnt/m/Programs/Everything/es.exe,/mnt/c/Program Files/Everything/es.exe,/mnt/c/Program Files (x86)/Everything/es.exe,/mnt/c/Tools/Everything/es.exe,/mnt/c/Users/mios/AppData/Local/Programs/Everything/es.exe}"
: "${MIOS_EVERYTHING_CLI_VERSION:=1.1.0.37}"
: "${MIOS_FAPOLICYD_OBSERVE_ENABLE:=false}"
: "${MIOS_FIND_ALIASES_CALCULATOR:=gnome-calculator}"
: "${MIOS_FIND_ALIASES_CALCULATOR_WIN:=calc}"
: "${MIOS_FIND_ALIASES_CALENDAR:=gnome-calendar}"
: "${MIOS_FIND_ALIASES_CENTER_WINDOW:=mios-window}"
: "${MIOS_FIND_ALIASES_CLOCK:=gnome-clocks}"
: "${MIOS_FIND_ALIASES_CODE:=codium}"
: "${MIOS_FIND_ALIASES_COMMAND_PROMPT:=cmd}"
: "${MIOS_FIND_ALIASES_CONFIGURATOR:=mios-html}"
: "${MIOS_FIND_ALIASES_CONTROL_PANEL:=control}"
: "${MIOS_FIND_ALIASES_CUSTOMIZE:=mios-html}"
: "${MIOS_FIND_ALIASES_DISKS:=gnome-disks}"
: "${MIOS_FIND_ALIASES_DOCUMENTS:=papers}"
: "${MIOS_FIND_ALIASES_EDITOR:=gedit}"
: "${MIOS_FIND_ALIASES_EXTENSIONS:=extension-manager}"
: "${MIOS_FIND_ALIASES_FILES:=nautilus}"
: "${MIOS_FIND_ALIASES_FILE_EXPLORER:=explorer}"
: "${MIOS_FIND_ALIASES_FOCUS_WINDOW:=mios-window}"
: "${MIOS_FIND_ALIASES_GAMES:=lutris}"
: "${MIOS_FIND_ALIASES_HELP:=yelp}"
: "${MIOS_FIND_ALIASES_INSTALL:=mios-installer}"
: "${MIOS_FIND_ALIASES_INSTALLER:=mios-installer}"
: "${MIOS_FIND_ALIASES_MAIL:=evolution}"
: "${MIOS_FIND_ALIASES_MAPS:=gnome-maps}"
: "${MIOS_FIND_ALIASES_MARKDOWN:=mios-md}"
: "${MIOS_FIND_ALIASES_MD:=mios-md}"
: "${MIOS_FIND_ALIASES_MIOSCONFIG:=mios-html}"
: "${MIOS_FIND_ALIASES_MIOS_HTML:=mios-html}"
: "${MIOS_FIND_ALIASES_MIOS_SETTINGS:=mios-html}"
: "${MIOS_FIND_ALIASES_MOBILE_CONTROL_PANEL:=mobi.phosh.MobileSettings}"
: "${MIOS_FIND_ALIASES_MOBILE_SETTINGS:=mobi.phosh.MobileSettings}"
: "${MIOS_FIND_ALIASES_MOVE_WINDOW:=mios-window}"
: "${MIOS_FIND_ALIASES_MUSIC:=decibels}"
: "${MIOS_FIND_ALIASES_NOTEPAD_APP:=notepad}"
: "${MIOS_FIND_ALIASES_NOTES:=mios-md}"
: "${MIOS_FIND_ALIASES_PACKAGE:=mios-installer}"
: "${MIOS_FIND_ALIASES_PAINT:=mspaint}"
: "${MIOS_FIND_ALIASES_PHOTOS:=loupe}"
: "${MIOS_FIND_ALIASES_POWER_SHELL:=powershell}"
: "${MIOS_FIND_ALIASES_PREVIEW_MD:=mios-md}"
: "${MIOS_FIND_ALIASES_PRTSCR:=mios-screenshot}"
: "${MIOS_FIND_ALIASES_PWSH_SHELL:=pwsh}"
: "${MIOS_FIND_ALIASES_REGISTRY_EDITOR:=regedit}"
: "${MIOS_FIND_ALIASES_RENDER_MD:=mios-md}"
: "${MIOS_FIND_ALIASES_SCREENCAP:=mios-screenshot}"
: "${MIOS_FIND_ALIASES_SCREENSHOT:=mios-screenshot}"
: "${MIOS_FIND_ALIASES_SCREEN_CAPTURE:=mios-screenshot}"
: "${MIOS_FIND_ALIASES_SETTINGS:=gnome-control-center}"
: "${MIOS_FIND_ALIASES_SNAP:=mios-screenshot}"
: "${MIOS_FIND_ALIASES_SNIP:=snipping-tool}"
: "${MIOS_FIND_ALIASES_SOFTWARE:=gnome-software}"
: "${MIOS_FIND_ALIASES_STEAMCMD:=mios-steamcmd}"
: "${MIOS_FIND_ALIASES_STEAM_CMD:=mios-steamcmd}"
: "${MIOS_FIND_ALIASES_STEAM_GAME:=mios-steamcmd}"
: "${MIOS_FIND_ALIASES_STEAM_INSTALL:=mios-steamcmd}"
: "${MIOS_FIND_ALIASES_TASK_MANAGER:=taskmgr}"
: "${MIOS_FIND_ALIASES_TERMINAL:=ptyxis}"
: "${MIOS_FIND_ALIASES_VIDEO:=showtime}"
: "${MIOS_FIND_ALIASES_WEATHER:=gnome-weather}"
: "${MIOS_FIND_ALIASES_WEB:=epiphany}"
: "${MIOS_FIND_ALIASES_WINDOW:=mios-window}"
: "${MIOS_FIND_ALIASES_WINDOWS_EXPLORER:=explorer}"
: "${MIOS_FIND_ALIASES_WINDOWS_MGR:=mios-window}"
: "${MIOS_FIND_ALIASES_WINGET:=mios-installer}"
: "${MIOS_FIND_CATEGORY_PRIORITY_AGENT_CLI:=5}"
: "${MIOS_FIND_CATEGORY_PRIORITY_LINUX_FLATPAK:=3}"
: "${MIOS_FIND_CATEGORY_PRIORITY_LINUX_RPM_GUI:=4}"
: "${MIOS_FIND_CATEGORY_PRIORITY_MIOS_SHIM:=6}"
: "${MIOS_FIND_CATEGORY_PRIORITY_SERVICE_URL:=7}"
: "${MIOS_FIND_CATEGORY_PRIORITY_WINDOWS_APP:=1}"
: "${MIOS_FIND_CATEGORY_PRIORITY_WINDOWS_BROWSER:=1}"
: "${MIOS_FIND_CATEGORY_PRIORITY_WINDOWS_GUI:=2}"
: "${MIOS_FIND_RANKER_FUZZY_MAX_EDIT_DISTANCE:=2}"
: "${MIOS_FIND_RANKER_FUZZY_MAX_EDIT_RATIO:=0.34}"
: "${MIOS_FIND_RANKER_FUZZY_MIN_TOKEN_LEN:=4}"
: "${MIOS_FIND_RANKER_TIERS:=name_exact,name_prefix,name_word,name_substr,desc_word,desc_substr,fuzzy}"
: "${MIOS_FINETUNE_BASE_MODEL:=granite4.1:8b}"
: "${MIOS_FINETUNE_BATCH_SIZE:=2}"
: "${MIOS_FINETUNE_DATASET_PATH:=/var/lib/mios/finetune/refiner-sft.jsonl}"
: "${MIOS_FINETUNE_DEVICE:=auto}"
: "${MIOS_FINETUNE_ENABLE:=true}"
: "${MIOS_FINETUNE_EPOCHS:=2}"
: "${MIOS_FINETUNE_GGUF_CONVERT:=true}"
: "${MIOS_FINETUNE_GGUF_QUANT:=q8_0}"
: "${MIOS_FINETUNE_GRAD_ACCUM:=8}"
: "${MIOS_FINETUNE_GRAD_CHECKPOINTING:=true}"
: "${MIOS_FINETUNE_HF_BASE:=ibm-granite/granite-4.1-8b}"
: "${MIOS_FINETUNE_INCLUDE_KNOWLEDGE:=true}"
: "${MIOS_FINETUNE_LEARNING_RATE:=0.0002}"
: "${MIOS_FINETUNE_LOAD_IN_4BIT:=auto}"
: "${MIOS_FINETUNE_LORA_ALPHA:=32}"
: "${MIOS_FINETUNE_LORA_DROPOUT:=0.05}"
: "${MIOS_FINETUNE_LORA_R:=16}"
: "${MIOS_FINETUNE_MAX_SEQ_LEN:=2048}"
: "${MIOS_FINETUNE_MIN_EXAMPLES:=24}"
: "${MIOS_FINETUNE_OUTPUT_TAG:=mios-sys-agent-ft}"
[ -n "${MIOS_FINETUNE_PIPE_URL+x}" ] || MIOS_FINETUNE_PIPE_URL='http://127.0.0.1:'"${MIOS_PORT_AGENT_PIPE}"
: "${MIOS_FINETUNE_PREFER_UNSLOTH:=true}"
: "${MIOS_FINETUNE_SEEDS_PER_CAPABILITY:=4}"
: "${MIOS_FINETUNE_SERVE_PORT:=11438}"
: "${MIOS_FINETUNE_TARGET_MODULES:=auto}"
: "${MIOS_FINETUNE_TARGET_ROLE:=refiner}"
[ -n "${MIOS_FINETUNE_TEACHER_ENDPOINT+x}" ] || MIOS_FINETUNE_TEACHER_ENDPOINT='http://localhost:'"${MIOS_PORT_LLM_LIGHT}"
: "${MIOS_FINETUNE_TEACHER_MODEL:=granite4.1:8b}"
: "${MIOS_FINETUNE_WARMUP_RATIO:=0.03}"
: "${MIOS_FINETUNE_WORK_DIR:=/var/lib/mios/finetune}"
: "${MIOS_FIRECRAWL_BULL_KEY:=mios}"
: "${MIOS_FIRECRAWL_LOG_LEVEL:=INFO}"
: "${MIOS_FIRECRAWL_PORT:=8820}"
: "${MIOS_FIRECRAWL_WORKERS:=2}"
: "${MIOS_FIREWALLD_ZONE:=drop}"
: "${MIOS_FIREWALL_OPEN_PORTS:=forge_http,open_webui,code_server,hermes,searxng,cockpit,hermes_dashboard,llm_light,pgvector,cockpit_link,adguard_ui,ssh,forge_ssh,vllm,sglang,cpu_node}"
: "${MIOS_VAR_DIR:=/var/lib/mios}"
[ -n "${MIOS_FIRSTBOOT_SENTINEL+x}" ] || MIOS_FIRSTBOOT_SENTINEL="${MIOS_VAR_DIR}"'/.wsl-firstboot-done'
: "${MIOS_FLATPAKS:=org.gtk.Gtk3theme.adw-gtk3-dark,org.gtk.Gtk3theme.adw-gtk3,app.devsuite.Ptyxis,gnome-nightly:org.gnome.Nautilus.Devel,fedora:org.gnome.Epiphany,com.github.tchx84.Flatseal,com.mattjakeman.ExtensionManager,com.google.ChromeDev}"
: "${MIOS_FLATPAK_DEFAULT_REMOTE:=flathub}"
: "${MIOS_FLATPAK_DEFAULT_SCOPE:=system}"
: "${MIOS_FLATPAK_NONINTERACTIVE:=true}"
: "${MIOS_FLATPAK_PREFER_BETA:=true}"
: "${MIOS_FORGE_GID:=816}"
: "${MIOS_FORGE_HTTP_PORT:=8400}"
[ -n "${MIOS_FORGE_IMAGE+x}" ] || MIOS_FORGE_IMAGE='codeberg.org/forgejo/forgejo:'"${MIOS_VERSION_FORGEJO}"
: "${MIOS_FORGE_RUNNER_IMAGE:=code.forgejo.org/forgejo/runner:7}"
: "${MIOS_FORGE_RUNNER_VERSION:=code.forgejo.org/forgejo/runner:7}"
: "${MIOS_FORGE_SSH_PORT:=8410}"
: "${MIOS_FORGE_UID:=816}"
: "${MIOS_PORT_FORGE_HTTP:=8400}"
[ -n "${MIOS_FORGE_URL+x}" ] || MIOS_FORGE_URL='http://localhost:'"${MIOS_PORT_FORGE_HTTP}"
: "${MIOS_FORGE_USER:=mios-forge}"
[ -n "${MIOS_FORGE_VERSION+x}" ] || MIOS_FORGE_VERSION='codeberg.org/forgejo/forgejo:'"${MIOS_VERSION_FORGEJO}"
[ -n "${MIOS_FRONTIER_CLAUDE_EFFORT_FLAG+x}" ] || MIOS_FRONTIER_CLAUDE_EFFORT_FLAG='--effort {e}'
: "${MIOS_FRONTIER_LANE_A_EFFORT:=xhigh}"
: "${MIOS_FRONTIER_LANE_A_ENGINE:=claude}"
: "${MIOS_FRONTIER_LANE_A_MODEL:=claude-opus-4-8}"
: "${MIOS_FRONTIER_LANE_A_ROLE:=framework + ~80%}"
: "${MIOS_FRONTIER_LANE_B_EFFORT:=high}"
: "${MIOS_FRONTIER_LANE_B_ENGINE:=agy}"
: "${MIOS_FRONTIER_LANE_B_FALLBACK_EFFORT:=high}"
: "${MIOS_FRONTIER_LANE_B_FALLBACK_ENGINE:=claude}"
: "${MIOS_FRONTIER_LANE_B_FALLBACK_MODEL:=claude-sonnet-5}"
: "${MIOS_FRONTIER_LANE_B_MODEL:=Gemini 3.5 Flash (High)}"
: "${MIOS_FRONTIER_LANE_B_PREFER_FALLBACK:=true}"
: "${MIOS_FRONTIER_LANE_B_ROLE:=finalize (last ~20%)}"
: "${MIOS_FRONTIER_ORCH_EFFORT:=high}"
: "${MIOS_FRONTIER_ORCH_ENGINE:=claude}"
: "${MIOS_FRONTIER_ORCH_MODEL:=claude-sonnet-5}"
: "${MIOS_FRONTIER_STREAM_PATH:=/var/lib/mios/hermes-tail/frontier/frontier.jsonl}"
: "${MIOS_FRONTIER_STREAM_TO_REASONING:=false}"
: "${MIOS_FS_WATCHER_DIRS:=/var/lib/mios/hermes-tail,/var/lib/mios/delegation-prefilter,/var/lib/mios/log-watcher,/var/lib/mios/daemon,/var/lib/mios/scratch,/var/lib/mios/agent-nudger,/var/lib/mios/cron-director,/var/lib/mios/ai/scratch}"
: "${MIOS_FS_WATCHER_WATCH_DIRS:=/var/lib/mios/hermes-tail,/var/lib/mios/delegation-prefilter,/var/lib/mios/log-watcher,/var/lib/mios/daemon,/var/lib/mios/scratch,/var/lib/mios/agent-nudger,/var/lib/mios/cron-director,/var/lib/mios/ai/scratch}"
: "${MIOS_GATEWAY_CONTEXT_LENGTH:=8192}"
: "${MIOS_GATEWAY_ENABLE:=false}"
: "${MIOS_GATEWAY_MAX_STEPS:=30}"
: "${MIOS_GATEWAY_MAX_TOKENS:=4096}"
: "${MIOS_GATEWAY_MCP_REFRESH_SECONDS:=300}"
: "${MIOS_GATEWAY_MODEL:=granite4.1:8b}"
: "${MIOS_GATEWAY_PORT:=8720}"
: "${MIOS_GATEWAY_SEARXNG_URL:=http://mios-searxng:8080}"
: "${MIOS_GATEWAY_SKILL_CATALOG_STATIC_PATH:=/var/lib/mios/skills/catalog.json}"
: "${MIOS_GATEWAY_SKILL_REFRESH_SECONDS:=300}"
: "${MIOS_GATEWAY_TOOL_LOOP_ENGINE:=smolagents}"
: "${MIOS_GENERATOR_PLACEHOLDERS:=FEDORA_VERSION,MIOS_VERSION}"
: "${MIOS_GITCONFIG_ALIAS_BR:=branch}"
: "${MIOS_GITCONFIG_ALIAS_CI:=commit}"
: "${MIOS_GITCONFIG_ALIAS_CO:=checkout}"
: "${MIOS_GITCONFIG_ALIAS_ST:=status}"
: "${MIOS_GITCONFIG_CORE_EDITOR:=nano}"
: "${MIOS_GITCONFIG_INIT_DEFAULT_BRANCH:=main}"
: "${MIOS_GITCONFIG_PULL_REBASE:=true}"
: "${MIOS_GOSSIP_FANOUT:=3}"
: "${MIOS_GOSSIP_INTERVAL_MIN:=0}"
: "${MIOS_GOSSIP_MIN_TRUST:=0.0}"
: "${MIOS_GPU_DEVICE:=nvidia.com/gpu=all}"
: "${MIOS_GPU_VENDORS_AMD:=true}"
: "${MIOS_GPU_VENDORS_INTEL:=true}"
: "${MIOS_GPU_VENDORS_NVIDIA:=true}"
: "${MIOS_GRAPHICS_DISABLE_VULKAN:=true}"
: "${MIOS_GRAPHICS_FORCE_SOFTWARE_GL:=false}"
: "${MIOS_GRAPHICS_GDK_BACKEND:=x11}"
: "${MIOS_GRAPHICS_GSK_RENDERER:=ngl}"
: "${MIOS_GRAPHICS_XCURSOR_PATH:=~/.local/share/icons:~/.icons:/usr/share/icons:/usr/share/pixmaps}"
: "${MIOS_GREENBOOT_BLADE_REACHABILITY_CRITICAL:=false}"
: "${MIOS_GREENBOOT_CRITICAL_SERVICES:=agent-pipe,llm-light,pgvector,hermes}"
: "${MIOS_GREENBOOT_PROBE_AGENT_PIPE_KIND:=http}"
: "${MIOS_GREENBOOT_PROBE_AGENT_PIPE_PATH:=/v1/models}"
: "${MIOS_GREENBOOT_PROBE_HERMES_UNIT:=hermes-worker.service}"
: "${MIOS_GUACAMOLE_IMAGE:=docker.io/guacamole/guacamole:latest}"
: "${MIOS_GUACAMOLE_VERSION:=docker.io/guacamole/guacamole:latest}"
: "${MIOS_GUACD_IMAGE:=docker.io/guacamole/guacd:latest}"
: "${MIOS_GUACD_PORT:=8560}"
: "${MIOS_GUACD_VERSION:=docker.io/guacamole/guacd:latest}"
: "${MIOS_HERMES_AGENT_REF:=main}"
: "${MIOS_HERMES_AGENT_REPO:=https://github.com/NousResearch/hermes-agent.git}"
[ -n "${MIOS_HERMES_BACKEND+x}" ] || MIOS_HERMES_BACKEND='http://localhost:'"${MIOS_PORT_LLM_LIGHT}"
[ -n "${MIOS_HERMES_BACKEND_URL+x}" ] || MIOS_HERMES_BACKEND_URL='http://localhost:'"${MIOS_PORT_LLM_LIGHT}"'/v1'
: "${MIOS_HERMES_DASHBOARD_PORT:=8210}"
: "${MIOS_HERMES_DIR:=/usr/lib/mios/agents/hermes-agent}"
: "${MIOS_HERMES_ENABLE:=true}"
[ -n "${MIOS_HERMES_ENDPOINT+x}" ] || MIOS_HERMES_ENDPOINT='http://localhost:'"${MIOS_PORT_AGENT_PIPE}"'/v1'
: "${MIOS_HERMES_GID:=820}"
: "${MIOS_HERMES_IMAGE:=docker.io/nousresearch/hermes-agent:latest}"
: "${MIOS_HERMES_MODEL:=granite4.1:8b}"
: "${MIOS_HERMES_PORT:=8720}"
: "${MIOS_HERMES_UID:=820}"
: "${MIOS_HERMES_USER:=mios-hermes}"
: "${MIOS_HERMES_VENV:=/usr/lib/mios/agents/.venv}"
: "${MIOS_HERMES_VERSION:=docker.io/nousresearch/hermes-agent:latest}"
[ -n "${MIOS_HERMES_WORKER_ENDPOINT+x}" ] || MIOS_HERMES_WORKER_ENDPOINT='http://localhost:'"${MIOS_PORT_HERMES}"'/v1'
: "${MIOS_HITL_ENABLE:=true}"
: "${MIOS_HITL_MODE:=log}"
: "${MIOS_HOSTNAME:=mios}"
: "${MIOS_HWCAPS_LD_SO_HWCAPS_AUTOSELECT:=true}"
: "${MIOS_HWCAPS_LEVEL:=v1}"
: "${MIOS_HWCAPS_NATIVE_REBUILD:=false}"
: "${MIOS_IDENTITY_DEFAULT_PASSWORD:=mios}"
: "${MIOS_IDENTITY_EMAIL:=mios@localhost}"
: "${MIOS_IDENTITY_FULLNAME:=MiOS Operator}"
: "${MIOS_IDENTITY_GROUPS:=wheel,libvirt,kvm,video,render,input,dialout,docker}"
: "${MIOS_IDENTITY_HOSTNAME:=mios}"
: "${MIOS_IDENTITY_IPA_DOMAIN:=mios.internal}"
: "${MIOS_IDENTITY_IPA_ENABLED:=false}"
: "${MIOS_IDENTITY_IPA_ENROLL_PRINCIPAL:=admin}"
: "${MIOS_IDENTITY_IPA_OTP:=placeholder-one-time-password}"
: "${MIOS_IDENTITY_IPA_REALM:=MIOS.INTERNAL}"
: "${MIOS_IDENTITY_IPA_SERVER:=ipa.mios.internal}"
: "${MIOS_IDENTITY_NAME:=mios}"
: "${MIOS_IDENTITY_SHELL:=/bin/bash}"
: "${MIOS_IDENTITY_USERNAME:=mios}"
: "${MIOS_IMAGE_NAME:=ghcr.io/mios-dev/mios}"
: "${MIOS_IMAGE_REF:=ghcr.io/mios-dev/mios:latest}"
: "${MIOS_IMAGE_TAG:=latest}"
: "${MIOS_INSTALL_ENV:=/etc/mios/install.env}"
: "${MIOS_INTEGER_PARAM_KEYWORDS:=limit,count,timeout,port,every,concurrency,maxsize}"
: "${MIOS_K3S_API_PORT:=8450}"
[ -n "${MIOS_K3S_IMAGE+x}" ] || MIOS_K3S_IMAGE='docker.io/rancher/k3s:'"${MIOS_VERSION_K3S}"
[ -n "${MIOS_K3S_VERSION+x}" ] || MIOS_K3S_VERSION='docker.io/rancher/k3s:'"${MIOS_VERSION_K3S}"
: "${MIOS_KARGS_IOMMU:=on}"
: "${MIOS_KEYBOARD:=us}"
: "${MIOS_KNOWLEDGE_EVICT_BATCH:=500}"
: "${MIOS_KNOWLEDGE_EVICT_DRYRUN:=false}"
: "${MIOS_KNOWLEDGE_EVICT_ENABLE:=true}"
: "${MIOS_KNOWLEDGE_EVICT_INTERVAL_S:=3600}"
: "${MIOS_KNOWLEDGE_EVICT_MAX_ROWS:=50000}"
: "${MIOS_KNOWLEDGE_EVICT_MIN_ACCESS:=1}"
: "${MIOS_KNOWLEDGE_EVICT_TTL_DAYS:=90}"
: "${MIOS_KNOWLEDGE_HOT_THRESHOLD:=5}"
: "${MIOS_KNOWLEDGE_RANK_ACCESS:=0.02}"
: "${MIOS_KNOWLEDGE_RANK_AGE:=0.3}"
: "${MIOS_KNOWLEDGE_RANK_HOT:=0.03}"
: "${MIOS_KNOWLEDGE_RANK_OUTCOME:=0.05}"
: "${MIOS_KNOWLEDGE_RECALL_HALFLIFE_DAYS:=7.0}"
: "${MIOS_KNOWLEDGE_RECALL_PREF_MIN_SCORE:=0.5}"
: "${MIOS_KNOWLEDGE_RECALL_STRICT_SCORE:=0.82}"
: "${MIOS_KNOWLEDGE_STORE_SKIP_VOLATILE:=true}"
: "${MIOS_LANES_LIGHT_CONSTRAINED_TOOLS:=true}"
: "${MIOS_LANES_LIGHT_REASONING_PARSER:=qwen3}"
: "${MIOS_LANES_LIGHT_STREAM_THINKING:=true}"
: "${MIOS_LANES_LIGHT_TOOL_CALL_PARSER:=hermes}"
: "${MIOS_LANES_SGLANG_CONSTRAINED_TOOLS:=true}"
: "${MIOS_LANES_SGLANG_REASONING_PARSER:=qwen3}"
: "${MIOS_LANES_SGLANG_STREAM_THINKING:=true}"
: "${MIOS_LANES_SGLANG_TOOL_CALL_PARSER:=qwen25}"
: "${MIOS_LANES_VLLM_CONSTRAINED_TOOLS:=true}"
: "${MIOS_LANES_VLLM_REASONING_PARSER:=qwen3}"
: "${MIOS_LANES_VLLM_STREAM_THINKING:=true}"
: "${MIOS_LANES_VLLM_TOOL_CALL_PARSER:=hermes}"
: "${MIOS_LAUNCHER_SOCKET:=/run/mios-launcher/launcher.sock}"
: "${MIOS_LAUNCH_FILLER_PHRASES:=for me please,on my desktop,on the desktop,right now,real quick,thank you,for me,please,thanks,now}"
[ -n "${MIOS_LAUNCH_FOLLOWUP_PHRASES+x}" ] || MIOS_LAUNCH_FOLLOWUP_PHRASES='didn'"'"'t launch,did not launch,didn'"'"'t open,did not open,didn'"'"'t start,did not start,didn'"'"'t come up,did not come up,didn'"'"'t work,did not work,wouldn'"'"'t open,would not open,no window,nothing happened,nothing opened,never opened,never launched,not opening,not launching,isn'"'"'t open,is not open,isn'"'"'t running,is not running,won'"'"'t open,won'"'"'t launch,doesn'"'"'t open,does not open,failed to open,failed to launch'
: "${MIOS_LAUNCH_RETRY_PHRASES:=attempt to launch and verify,launch and verify,launch it and verify,try to launch and verify,open and verify,open it and verify,try launching it again,try launching again,try opening it again,try opening again,launch it again,open it again,start it again,run it again,try again,attempt again,retry,relaunch,re-launch,reopen,re-open,try once more,one more time,attempt to launch,attempt the launch,verify the launch,launch and confirm,open and confirm}"
: "${MIOS_LAUNCH_TARGET_LEAD_PHRASES:=the,a,an,my}"
: "${MIOS_LAUNCH_TARGET_TRAIL_PHRASES:=application,program,app,window}"
[ -n "${MIOS_LAWS_LAWS+x}" ] || MIOS_LAWS_LAWS='{'"'"'id'"'"': 1, '"'"'slug'"'"': '"'"'USR-OVER-ETC'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_usr_over_etc'"'"'},{'"'"'id'"'"': 2, '"'"'slug'"'"': '"'"'NO-MKDIR-IN-VAR'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_no_mkdir_in_var'"'"'},{'"'"'id'"'"': 3, '"'"'slug'"'"': '"'"'BOUND-IMAGES'"'"', '"'"'applies_to'"'"': '"'"'bootc'"'"', '"'"'enforced_by'"'"': '"'"'99-postcheck.sh:item14'"'"'},{'"'"'id'"'"': 4, '"'"'slug'"'"': '"'"'BOOTC-CONTAINER-LINT'"'"', '"'"'applies_to'"'"': '"'"'bootc'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_lint_is_final'"'"'},{'"'"'id'"'"': 5, '"'"'slug'"'"': '"'"'UNIFIED-AI-REDIRECTS'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'99-postcheck.sh:item12'"'"'},{'"'"'id'"'"': 6, '"'"'slug'"'"': '"'"'UNPRIVILEGED-QUADLETS'"'"', '"'"'applies_to'"'"': '"'"'bootc'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_quadlet_privilege'"'"'},{'"'"'id'"'"': 7, '"'"'slug'"'"': '"'"'NO-HARDCODE'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_no_hardcode'"'"'},{'"'"'id'"'"': 8, '"'"'slug'"'"': '"'"'SSOT-PROJECTION'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_projection_registry'"'"'},{'"'"'id'"'"': 9, '"'"'slug'"'"': '"'"'ONE-CANONICAL-NAME'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_var_closure'"'"'},{'"'"'id'"'"': 10, '"'"'slug'"'"': '"'"'BARE-SAFE-ENV'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'99-postcheck.sh:item16'"'"'},{'"'"'id'"'"': 11, '"'"'slug'"'"': '"'"'SECRETS-NEVER-IN-ENV'"'"', '"'"'applies_to'"'"': '"'"'bootc'"'"', '"'"'enforced_by'"'"': '"'"'99-postcheck.sh:item17'"'"'},{'"'"'id'"'"': 12, '"'"'slug'"'"': '"'"'BAKE-NOT-FETCH'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_dag_integrity,check_firstboot_degrade_open'"'"'},{'"'"'id'"'"': 13, '"'"'slug'"'"': '"'"'NATIVE-DROPINS'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_resolver_twin_parity'"'"'},{'"'"'id'"'"': 14, '"'"'slug'"'"': '"'"'TARGET-LANGUAGES'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_target_languages'"'"'},{'"'"'id'"'"': 15, '"'"'slug'"'"': '"'"'DOUBLE-REPO-TRIPLE-CHECK'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'process:CLAUDE.md/AGENTS.md (both repos); parity via 98-drift-checks.sh checks 22+27'"'"'},{'"'"'id'"'"': 16, '"'"'slug'"'"': '"'"'ONE-TEMPLATE-PER-TYPE'"'"', '"'"'applies_to'"'"': '"'"'both'"'"', '"'"'enforced_by'"'"': '"'"'98-drift-checks.sh:check_template_conformance'"'"'}'
[ -n "${MIOS_LAWS_PROJECTION_REGISTRY_SURFACES+x}" ] || MIOS_LAWS_PROJECTION_REGISTRY_SURFACES='{'"'"'generator'"'"': '"'"'usr/libexec/mios/mios-theme-render'"'"', '"'"'check'"'"': '"'"'check_dotfiles_projection'"'"', '"'"'output'"'"': '"'"'etc/ (and various target registries)'"'"'},{'"'"'generator'"'"': '"'"'usr/libexec/mios/mios-sync-toml'"'"', '"'"'check'"'"': '"'"'check_toml_projection'"'"', '"'"'output'"'"': '"'"'usr/share/mios/mios.toml.bak (and metadata)'"'"'},{'"'"'generator'"'"': '"'"'automation/98-drift-checks.sh'"'"', '"'"'check'"'"': '"'"'check_drift_projection'"'"', '"'"'output'"'"': '"'"'stdout (drift assertions)'"'"'},{'"'"'generator'"'"': '"'"'usr/libexec/mios/mios-manual'"'"', '"'"'check'"'"': '"'"'check_manual_ledger'"'"', '"'"'output'"'"': '"'"'usr/share/mios/reference/manual-corpus.tsv'"'"'},{'"'"'generator'"'"': '"'"'usr/libexec/mios/mios-manual'"'"', '"'"'check'"'"': '"'"'check_manual_generated'"'"', '"'"'output'"'"': '"'"'usr/share/doc/mios/ (MIOS-GEN marker interiors)'"'"'},{'"'"'generator'"'"': '"'"'usr/libexec/mios/mios-manual'"'"', '"'"'check'"'"': '"'"'check_comment_landing'"'"', '"'"'output'"'"': '"'"'usr/share/doc/mios/ (harvested passages + mios-src anchors)'"'"'},{'"'"'generator'"'"': '"'"'usr/libexec/mios/mios-manual'"'"', '"'"'check'"'"': '"'"'check_docs_ratchet_monotone'"'"', '"'"'output'"'"': '"'"'usr/share/mios/reference/doc-ratchet-floor.tsv'"'"'}'
: "${MIOS_LAWS_TARGET_LANGUAGES_GRANDFATHERED_CS:=usr/share/mios/windows/MiOS-Launcher.cs,usr/share/mios/windows/MiosServiceTool.cs}"
: "${MIOS_LEGIBILITY_MAX_AUTOMATION_PHASES:=72}"
: "${MIOS_LEGIBILITY_MAX_LIBEXEC_VERBS:=283}"
: "${MIOS_LEGIBILITY_MAX_PS_LINES:=33174}"
: "${MIOS_LEGIBILITY_MAX_SHELL_LINES:=46389}"
: "${MIOS_LEGIBILITY_MAX_TRACKED_FILES:=2389}"
: "${MIOS_LEGIBILITY_MAX_TRACKED_MB:=202}"
: "${MIOS_LIBEXEC_DIR:=/usr/libexec/mios}"
: "${MIOS_LLAMACPP_BAKE_MODELS:=granite-4.1-8b.gguf=unsloth/granite-4.1-8b-GGUF:granite-4.1-8b-Q4_K_M.gguf,lfm2-700m.gguf=LiquidAI/LFM2-700M-GGUF:LFM2-700M-Q4_K_M.gguf,embeddinggemma-300m-qat-q8_0.gguf=ggml-org/embeddinggemma-300m-qat-q8_0-GGUF:embeddinggemma-300m-qat-Q8_0.gguf}"
: "${MIOS_LLAMACPP_CONFIG:=/usr/share/mios/llamacpp/mios-llm-light.yaml}"
: "${MIOS_LLAMACPP_CPU_NODE_THREADS:=14}"
: "${MIOS_LLAMACPP_ENABLE:=true}"
: "${MIOS_LLAMACPP_GID:=827}"
: "${MIOS_LLAMACPP_MODELS_DIR:=/usr/share/mios/llamacpp/models}"
: "${MIOS_LLAMACPP_SLOT_DIR:=/var/lib/mios/llamacpp/slots}"
: "${MIOS_LLAMACPP_UID:=827}"
: "${MIOS_LLAMACPP_USER:=mios-llamacpp}"
: "${MIOS_LLM_LIGHT_IMAGE:=ghcr.io/mostlygeek/llama-swap:cuda}"
: "${MIOS_LLM_LIGHT_PORT:=8500}"
: "${MIOS_LLM_LIGHT_VERSION:=ghcr.io/mostlygeek/llama-swap:cuda}"
: "${MIOS_LOCALE:=en_US.UTF-8}"
: "${MIOS_LOCALE_KEYBOARD_LAYOUT:=us}"
: "${MIOS_LOCALE_LANGUAGE:=en_US.UTF-8}"
: "${MIOS_LOCALE_TIMEZONE:=UTC}"
[ -n "${MIOS_LOCAL_FORGE_REPO+x}" ] || MIOS_LOCAL_FORGE_REPO='http://localhost:'"${MIOS_PORT_FORGE_HTTP}"'/mios/mios.git'
: "${MIOS_LOCAL_TAG:=localhost/mios:latest}"
: "${MIOS_LOCATION_SENSITIVE_PHRASES:=weather,forecast,near me,nearby,near here,around here,local news,local,my area,things to do,restaurants,closest,directions to}"
: "${MIOS_LSFS_EMBED_MODEL:=nomic-embed-text}"
: "${MIOS_LSFS_ENABLE:=true}"
: "${MIOS_LSFS_MAX_VERSIONS:=10}"
: "${MIOS_LSFS_ROOT_DIR:=/var/lib/mios/lsfs}"
: "${MIOS_MCP_PORT:=8770}"
: "${MIOS_MCP_PROTOCOL_VERSION:=2025-11-25}"
[ -n "${MIOS_MCP_REGISTRY+x}" ] || MIOS_MCP_REGISTRY="${MIOS_SHARE_AI_DIR}"'/v1/mcp.json'
: "${MIOS_MEMORY_COMPACTION_INTERVAL:=20}"
: "${MIOS_MEMORY_COMPACTION_THRESHOLD_PCT:=80}"
: "${MIOS_MEMORY_CONSOLIDATE:=true}"
: "${MIOS_MEMORY_CONSOLIDATE_INTERVAL_S:=3600}"
: "${MIOS_MEMORY_CONSOLIDATE_MAX_GROUPS:=200}"
: "${MIOS_MEMORY_KV_SLOT_PERSIST:=true}"
: "${MIOS_MEMORY_N_CTX:=8000}"
: "${MIOS_MEMORY_TOOL_RESULT_TTL_TURNS:=5}"
: "${MIOS_METAL_BIND_DGPU_VFIO:=true}"
: "${MIOS_METAL_DGPUMODE:=vfio-pci}"
: "${MIOS_METAL_ENABLED:=false}"
: "${MIOS_METAL_GPU_ARBITRATION:=static}"
: "${MIOS_METAL_GPU_ASSIGNMENTS_MIOS_GUEST:=0000:01:00.0}"
: "${MIOS_METAL_GUEST_CPU_PERCENT:=85}"
: "${MIOS_METAL_GUEST_RAM_PERCENT:=85}"
: "${MIOS_METAL_MESH_ENABLED:=false}"
: "${MIOS_METAL_MESH_HEADSCALE_DOMAIN:=mesh.mios.local}"
: "${MIOS_METAL_MESH_SWTPM_VTPM:=true}"
: "${MIOS_METAL_MESH_VNET_CIDR:=100.64.0.0/10}"
: "${MIOS_META_EDITOR_URL:=/usr/share/mios/configurator/mios.html}"
: "${MIOS_META_FORMAT:=toml}"
: "${MIOS_META_MIOS_VERSION:=0.3.0}"
: "${MIOS_META_SCHEMA_VERSION:=1.1.0}"
: "${MIOS_META_SPEC_URL:=https://toml.io/en/v1.0.0}"
: "${MIOS_MIGRATION_USE_COMPILED_AINODE:=true}"
: "${MIOS_MIGRATION_USE_COMPILED_OSCONTROL:=true}"
: "${MIOS_MIGRATION_USE_RUST_RESOLVER_INSTALL_ENV:=true}"
: "${MIOS_MIGRATION_USE_RUST_RESOLVER_POWERSHELL:=true}"
: "${MIOS_MIGRATION_USE_RUST_RESOLVER_PYTHON:=true}"
: "${MIOS_MIGRATION_USE_RUST_RESOLVER_SHELL:=true}"
: "${MIOS_MIOS_DEVELOPER:=MiOS}"
: "${MIOS_MIOS_FIND_ALIASES_CALCULATOR:=gnome-calculator}"
: "${MIOS_MIOS_FIND_ALIASES_CALCULATOR_WIN:=calc}"
: "${MIOS_MIOS_FIND_ALIASES_CALENDAR:=gnome-calendar}"
: "${MIOS_MIOS_FIND_ALIASES_CENTER_WINDOW:=mios-window}"
: "${MIOS_MIOS_FIND_ALIASES_CLOCK:=gnome-clocks}"
: "${MIOS_MIOS_FIND_ALIASES_CODE:=codium}"
: "${MIOS_MIOS_FIND_ALIASES_COMMAND_PROMPT:=cmd}"
: "${MIOS_MIOS_FIND_ALIASES_CONFIGURATOR:=mios-html}"
: "${MIOS_MIOS_FIND_ALIASES_CONTROL_PANEL:=control}"
: "${MIOS_MIOS_FIND_ALIASES_CUSTOMIZE:=mios-html}"
: "${MIOS_MIOS_FIND_ALIASES_DISKS:=gnome-disks}"
: "${MIOS_MIOS_FIND_ALIASES_DOCUMENTS:=papers}"
: "${MIOS_MIOS_FIND_ALIASES_EDITOR:=gedit}"
: "${MIOS_MIOS_FIND_ALIASES_EXTENSIONS:=extension-manager}"
: "${MIOS_MIOS_FIND_ALIASES_FILES:=nautilus}"
: "${MIOS_MIOS_FIND_ALIASES_FILE_EXPLORER:=explorer}"
: "${MIOS_MIOS_FIND_ALIASES_FOCUS_WINDOW:=mios-window}"
: "${MIOS_MIOS_FIND_ALIASES_GAMES:=lutris}"
: "${MIOS_MIOS_FIND_ALIASES_HELP:=yelp}"
: "${MIOS_MIOS_FIND_ALIASES_INSTALL:=mios-installer}"
: "${MIOS_MIOS_FIND_ALIASES_INSTALLER:=mios-installer}"
: "${MIOS_MIOS_FIND_ALIASES_MAIL:=evolution}"
: "${MIOS_MIOS_FIND_ALIASES_MAPS:=gnome-maps}"
: "${MIOS_MIOS_FIND_ALIASES_MARKDOWN:=mios-md}"
: "${MIOS_MIOS_FIND_ALIASES_MD:=mios-md}"
: "${MIOS_MIOS_FIND_ALIASES_MIOSCONFIG:=mios-html}"
: "${MIOS_MIOS_FIND_ALIASES_MIOS_HTML:=mios-html}"
: "${MIOS_MIOS_FIND_ALIASES_MIOS_SETTINGS:=mios-html}"
: "${MIOS_MIOS_FIND_ALIASES_MOBILE_CONTROL_PANEL:=mobi.phosh.MobileSettings}"
: "${MIOS_MIOS_FIND_ALIASES_MOBILE_SETTINGS:=mobi.phosh.MobileSettings}"
: "${MIOS_MIOS_FIND_ALIASES_MOVE_WINDOW:=mios-window}"
: "${MIOS_MIOS_FIND_ALIASES_MUSIC:=decibels}"
: "${MIOS_MIOS_FIND_ALIASES_NOTEPAD_APP:=notepad}"
: "${MIOS_MIOS_FIND_ALIASES_NOTES:=mios-md}"
: "${MIOS_MIOS_FIND_ALIASES_PACKAGE:=mios-installer}"
: "${MIOS_MIOS_FIND_ALIASES_PAINT:=mspaint}"
: "${MIOS_MIOS_FIND_ALIASES_PHOTOS:=loupe}"
: "${MIOS_MIOS_FIND_ALIASES_POWER_SHELL:=powershell}"
: "${MIOS_MIOS_FIND_ALIASES_PREVIEW_MD:=mios-md}"
: "${MIOS_MIOS_FIND_ALIASES_PRTSCR:=mios-screenshot}"
: "${MIOS_MIOS_FIND_ALIASES_PWSH_SHELL:=pwsh}"
: "${MIOS_MIOS_FIND_ALIASES_REGISTRY_EDITOR:=regedit}"
: "${MIOS_MIOS_FIND_ALIASES_RENDER_MD:=mios-md}"
: "${MIOS_MIOS_FIND_ALIASES_SCREENCAP:=mios-screenshot}"
: "${MIOS_MIOS_FIND_ALIASES_SCREENSHOT:=mios-screenshot}"
: "${MIOS_MIOS_FIND_ALIASES_SCREEN_CAPTURE:=mios-screenshot}"
: "${MIOS_MIOS_FIND_ALIASES_SETTINGS:=gnome-control-center}"
: "${MIOS_MIOS_FIND_ALIASES_SNAP:=mios-screenshot}"
: "${MIOS_MIOS_FIND_ALIASES_SNIP:=snipping-tool}"
: "${MIOS_MIOS_FIND_ALIASES_SOFTWARE:=gnome-software}"
: "${MIOS_MIOS_FIND_ALIASES_STEAMCMD:=mios-steamcmd}"
: "${MIOS_MIOS_FIND_ALIASES_STEAM_CMD:=mios-steamcmd}"
: "${MIOS_MIOS_FIND_ALIASES_STEAM_GAME:=mios-steamcmd}"
: "${MIOS_MIOS_FIND_ALIASES_STEAM_INSTALL:=mios-steamcmd}"
: "${MIOS_MIOS_FIND_ALIASES_TASK_MANAGER:=taskmgr}"
: "${MIOS_MIOS_FIND_ALIASES_TERMINAL:=ptyxis}"
: "${MIOS_MIOS_FIND_ALIASES_VIDEO:=showtime}"
: "${MIOS_MIOS_FIND_ALIASES_WEATHER:=gnome-weather}"
: "${MIOS_MIOS_FIND_ALIASES_WEB:=epiphany}"
: "${MIOS_MIOS_FIND_ALIASES_WINDOW:=mios-window}"
: "${MIOS_MIOS_FIND_ALIASES_WINDOWS_EXPLORER:=explorer}"
: "${MIOS_MIOS_FIND_ALIASES_WINDOWS_MGR:=mios-window}"
: "${MIOS_MIOS_FIND_ALIASES_WINGET:=mios-installer}"
: "${MIOS_MIOS_FIND_CATEGORY_PRIORITY_AGENT_CLI:=5}"
: "${MIOS_MIOS_FIND_CATEGORY_PRIORITY_LINUX_FLATPAK:=3}"
: "${MIOS_MIOS_FIND_CATEGORY_PRIORITY_LINUX_RPM_GUI:=4}"
: "${MIOS_MIOS_FIND_CATEGORY_PRIORITY_MIOS_SHIM:=6}"
: "${MIOS_MIOS_FIND_CATEGORY_PRIORITY_SERVICE_URL:=7}"
: "${MIOS_MIOS_FIND_CATEGORY_PRIORITY_WINDOWS_APP:=1}"
: "${MIOS_MIOS_FIND_CATEGORY_PRIORITY_WINDOWS_BROWSER:=1}"
: "${MIOS_MIOS_FIND_CATEGORY_PRIORITY_WINDOWS_GUI:=2}"
: "${MIOS_MIOS_FIND_RANKER_FUZZY_MAX_EDIT_DISTANCE:=2}"
: "${MIOS_MIOS_FIND_RANKER_FUZZY_MAX_EDIT_RATIO:=0.34}"
: "${MIOS_MIOS_FIND_RANKER_FUZZY_MIN_TOKEN_LEN:=4}"
: "${MIOS_MIOS_FIND_RANKER_TIERS:=name_exact,name_prefix,name_word,name_substr,desc_word,desc_substr,fuzzy}"
: "${MIOS_MIOS_NAME:=MiOS AI}"
[ -n "${MIOS_MIOS_ROLE+x}" ] || MIOS_MIOS_ROLE='the ONE name you go by on EVERY surface (the `@`/`mios` CLI, OWUI, Discord, the desktop app, the API)'
: "${MIOS_MODEL:=granite4.1:8b}"
: "${MIOS_MODEL_MODALITIES_EMBEDDINGS:=embed,bert,text-embedding,bge}"
: "${MIOS_MODEL_MODALITIES_IMAGE:=diffuse,flux,dall,midjourney,sd}"
: "${MIOS_MODEL_ROUTER_PORT:=8750}"
: "${MIOS_NAME:=MiOS AI}"
[ -n "${MIOS_NETWORKS_MIOS_NETWORK_GATEWAY+x}" ] || MIOS_NETWORKS_MIOS_NETWORK_GATEWAY='${MIOS_CORE_NET_GATEWAY:-10.89.0.1}'
: "${MIOS_NETWORKS_MIOS_NETWORK_LABEL:=io.mios.network=core}"
[ -n "${MIOS_NETWORKS_MIOS_NETWORK_SUBNET+x}" ] || MIOS_NETWORKS_MIOS_NETWORK_SUBNET='${MIOS_CORE_NET_SUBNET:-10.89.0.0/24}'
: "${MIOS_NETWORK_ALLOW_COCKPIT:=true}"
: "${MIOS_NETWORK_ALLOW_LIBVIRT_BRIDGE:=true}"
: "${MIOS_NETWORK_ALLOW_SSH:=true}"
: "${MIOS_NETWORK_FIREWALLD_DEFAULT_ZONE:=drop}"
: "${MIOS_NETWORK_NTP_SERVERS:=0.pool.ntp.org,1.pool.ntp.org,2.pool.ntp.org,3.pool.ntp.org}"
: "${MIOS_NETWORK_QUADLET_CORE_GATEWAY:=10.89.0.1}"
: "${MIOS_NETWORK_QUADLET_CORE_SUBNET:=10.89.0.0/24}"
: "${MIOS_NETWORK_QUADLET_NETWORK:=mios.network}"
: "${MIOS_NETWORK_QUADLET_SUBNET:=10.89.0.0/24}"
: "${MIOS_NETWORK_RETRY_DELAYS_SECONDS:=0,5,15,30}"
: "${MIOS_NETWORK_RETRY_HTTP_STATUS_RETRY:=502,503,504}"
: "${MIOS_NETWORK_RETRY_TOTAL_TIMEOUT_SEC:=120}"
: "${MIOS_NODES_LOCAL_CPU_API:=llamacpp}"
: "${MIOS_PORT_CPU_NODE:=8510}"
[ -n "${MIOS_NODES_LOCAL_CPU_ENDPOINT+x}" ] || MIOS_NODES_LOCAL_CPU_ENDPOINT='http://localhost:'"${MIOS_PORT_CPU_NODE}"'/v1'
: "${MIOS_NODES_LOCAL_CPU_HEALTH_GATE:=true}"
: "${MIOS_NODES_LOCAL_CPU_LANE:=cpu}"
: "${MIOS_NODES_LOCAL_CPU_MODEL:=mios-agent-cpu}"
: "${MIOS_NODES_LOCAL_IGPU_API:=llamacpp}"
: "${MIOS_NODES_LOCAL_IGPU_LANE:=igpu}"
: "${MIOS_NODES_LOCAL_IGPU_MODEL:=mios-igpu}"
: "${MIOS_NODES_LOCAL_LLAMASWAP_API:=llamacpp}"
[ -n "${MIOS_NODES_LOCAL_LLAMASWAP_ENDPOINT+x}" ] || MIOS_NODES_LOCAL_LLAMASWAP_ENDPOINT='http://localhost:'"${MIOS_PORT_LLM_LIGHT}"'/v1'
: "${MIOS_NODES_LOCAL_LLAMASWAP_HEALTH_GATE:=true}"
: "${MIOS_NODES_LOCAL_LLAMASWAP_LANE:=cpu}"
: "${MIOS_NODES_LOCAL_LLAMASWAP_MODEL:=mios-agent-cpu}"
: "${MIOS_NODES_LOCAL_SGLANG_API:=openai}"
[ -n "${MIOS_NODES_LOCAL_SGLANG_ENDPOINT+x}" ] || MIOS_NODES_LOCAL_SGLANG_ENDPOINT='http://localhost:'"${MIOS_PORT_SGLANG}"'/v1'
: "${MIOS_NODES_LOCAL_SGLANG_HEALTH_GATE:=true}"
: "${MIOS_NODES_LOCAL_SGLANG_LANE:=gpu}"
: "${MIOS_NODES_LOCAL_SGLANG_MODEL:=mios-heavy}"
: "${MIOS_NODES_LOCAL_VLLM_API:=openai}"
: "${MIOS_PORT_VLLM:=8520}"
[ -n "${MIOS_NODES_LOCAL_VLLM_ENDPOINT+x}" ] || MIOS_NODES_LOCAL_VLLM_ENDPOINT='http://localhost:'"${MIOS_PORT_VLLM}"'/v1'
: "${MIOS_NODES_LOCAL_VLLM_HEALTH_GATE:=true}"
: "${MIOS_NODES_LOCAL_VLLM_LANE:=gpu}"
: "${MIOS_NODES_LOCAL_VLLM_MODEL:=mios-heavy}"
: "${MIOS_NON_ADDRESSABLE_URL:=adguard_dns,adguard_ui,agent_pipe,arbiter,ceph_dashboard,crawl4ai,hermes,llm_light,pgvector,chrome_cdp,chrome_cdp_worker,cockpit_link,cpu_node,daemon_agent,firecrawl,forge_ssh,guacamole_web,guacd,hermes_dashboard,k3s_api,mcp,model_router,opencode_gateway,oscontrol,otelcol_otlp,prefilter,pxe_hub_api,rdp,redis,sglang,ssh,ttyd_bash,ttyd_powershell,vllm}"
: "${MIOS_OBSERVABILITY_CHANNELS_CONTENT:=content}"
: "${MIOS_OBSERVABILITY_CHANNELS_PLAN:=reasoning}"
: "${MIOS_OBSERVABILITY_CHANNELS_SOURCE:=source}"
: "${MIOS_OBSERVABILITY_CHANNELS_THINKING:=reasoning}"
: "${MIOS_OBSERVABILITY_CHANNELS_TOOL_CALL:=status+reasoning}"
: "${MIOS_OBSERVABILITY_CHANNELS_TOOL_RESULT:=reasoning}"
: "${MIOS_OBSERVABILITY_DEBUG:=true}"
: "${MIOS_OBSERVABILITY_OTEL_ENABLE:=false}"
: "${MIOS_PORT_OTELCOL_OTLP:=8575}"
[ -n "${MIOS_OBSERVABILITY_OTEL_ENDPOINT+x}" ] || MIOS_OBSERVABILITY_OTEL_ENDPOINT='http://localhost:'"${MIOS_PORT_OTELCOL_OTLP}"
: "${MIOS_OBSERVABILITY_RECORD_MODE:=false}"
: "${MIOS_OBSERVABILITY_REPLAY_MODE:=false}"
: "${MIOS_OBSERVABILITY_SURFACE_DEFAULT:=clean}"
: "${MIOS_OFFLINE_BACKFILL_BATCH:=50}"
: "${MIOS_OFFLINE_BACKUP_DIR:=/var/lib/mios/backups}"
: "${MIOS_OFFLINE_BACKUP_ENABLE:=true}"
: "${MIOS_OFFLINE_BACKUP_KEEP:=7}"
: "${MIOS_OFFLINE_EMB_MODEL:=nomic-embed-text}"
: "${MIOS_OFFLINE_EMB_VERSION:=nomic-768-v1}"
: "${MIOS_OFFLINE_ENABLE:=false}"
: "${MIOS_OFFLINE_FALLBACK_TO_ONLINE:=true}"
: "${MIOS_OFFLINE_HNSW_ITERATIVE_SCAN:=strict_order}"
: "${MIOS_OFFLINE_HNSW_MAX_SCAN_TUPLES:=20000}"
: "${MIOS_OFFLINE_HNSW_SCAN_MEM_MULTIPLIER:=1}"
: "${MIOS_OFFLINE_LISTEN_LOOPBACK:=true}"
: "${MIOS_OFFLINE_MEMGUARD_JUDGE_MODE:=model}"
: "${MIOS_OFFLINE_MEMORY_GUARD_MODE:=log}"
: "${MIOS_OFFLINE_MEMORY_PROVIDER:=pgvector}"
: "${MIOS_OFFLINE_POOL_ENABLE:=false}"
: "${MIOS_OFFLINE_POOL_MAX:=8}"
: "${MIOS_OFFLINE_POOL_MIN:=0}"
: "${MIOS_OFFLINE_RLS_ENABLE:=false}"
: "${MIOS_OFFLINE_RPM_MIRROR_DIR:=/usr/share/mios/vendored/rpm-mirror}"
: "${MIOS_OFFLINE_SCRATCH_PERSIST:=true}"
: "${MIOS_OPENCODE_BIN:=/usr/lib/mios/agents/opencode/bin/opencode}"
: "${MIOS_OPENCODE_CONFIG:=/etc/mios/opencode/opencode.json}"
: "${MIOS_OPENCODE_GATEWAY_PORT:=8780}"
: "${MIOS_OPENCODE_INSTALL_URL:=https://opencode.ai/install}"
: "${MIOS_OPENCODE_MODEL:=mios-opencode:latest}"
: "${MIOS_OPENCODE_PROVIDER:=local}"
: "${MIOS_OPENCODE_TIMEOUT_S:=90}"
: "${MIOS_OPENCODE_VERSION:=latest}"
: "${MIOS_OPENCODE_WORKDIR:=/var/lib/mios/opencode-gateway/work}"
: "${MIOS_OPEN_WEBUI_GID:=817}"
: "${MIOS_OPEN_WEBUI_IMAGE:=ghcr.io/open-webui/open-webui:main}"
: "${MIOS_OPEN_WEBUI_PORT:=8200}"
: "${MIOS_OPEN_WEBUI_UID:=817}"
[ -n "${MIOS_OPEN_WEBUI_URL+x}" ] || MIOS_OPEN_WEBUI_URL='http://localhost:'"${MIOS_PORT_OPEN_WEBUI}"'/'
: "${MIOS_OPEN_WEBUI_USER:=mios-open-webui}"
: "${MIOS_OPEN_WEBUI_VERSION:=ghcr.io/open-webui/open-webui:main}"
: "${MIOS_OSCONTROL_PORT:=8950}"
: "${MIOS_OS_CONTROL_DEFAULT_MONITOR:=0}"
: "${MIOS_OS_CONTROL_DEFAULT_POSITION:=center}"
: "${MIOS_OS_CONTROL_EDGE_MARGIN_PX:=0}"
: "${MIOS_OS_CONTROL_FOCUS_AFTER_LAUNCH:=true}"
: "${MIOS_OS_CONTROL_LAUNCH_CATEGORY_PRIORITY:=linux-flatpak,linux-rpm-gui,linux-cli,windows-app,windows-gui}"
: "${MIOS_OS_CONTROL_NODES_IGPU_DESC:=iGPU Windows host -- launch + verify on its own desktop over the tailnet (also runs mios-igpu-server.ps1 for inference).}"
: "${MIOS_OS_CONTROL_REGION_SNAP_HALVES:=true}"
: "${MIOS_OS_CONTROL_RESTORE_IF_RUNNING:=true}"
: "${MIOS_OS_CONTROL_TILE_GAP_PX:=8}"
: "${MIOS_OTELCOL_IMAGE:=docker.io/jaegertracing/all-in-one:1.76.0}"
: "${MIOS_OTELCOL_OTLP_PORT:=8575}"
: "${MIOS_OTELCOL_UI_PORT:=8580}"
: "${MIOS_PORT_OTELCOL_UI:=8580}"
[ -n "${MIOS_OTELCOL_UI_URL+x}" ] || MIOS_OTELCOL_UI_URL='http://localhost:'"${MIOS_PORT_OTELCOL_UI}"'/'
: "${MIOS_OTELCOL_VERSION:=docker.io/jaegertracing/all-in-one:1.76.0}"
[ -n "${MIOS_OWUI_SYSTEM_PROMPT_TEMPLATE+x}" ] || MIOS_OWUI_SYSTEM_PROMPT_TEMPLATE='# MiOS AI
Front door of MiOS, a local-first agentic OS. You refine intent, plan,
delegate to sub-agents, and shape the final answer. Live facts (services,
GPU, models, paths, what'"'"'s installed) come from TOOLS at call-time --
never this prompt.

ENVIRONMENT (authoritative facts -- use them, do not assume; treat
"Unknown", "None", or blank as NOT PROVIDED): operator name is
{{USER_NAME}}; now is {{CURRENT_WEEKDAY}} {{CURRENT_DATE}} {{CURRENT_TIME}}
({{CURRENT_TIMEZONE}}); browser locale is {{USER_LANGUAGE}}; location is
{{USER_LOCATION}}. Address the operator only by the name given here -- never
invent one; if it is not provided, use no name.

RESPONSE LANGUAGE (decisive): reply in ENGLISH by default. Adapt seamlessly to the operator'"'"'s preferred language when they write or request responses in another language, replying naturally in that language without mid-reply language switching or unsolicited translation.

ENVIRONMENT USE (apply EVERY detected fact above, on EVERY turn -- they are
the operator'"'"'s real session, not optional):
- TIMEZONE + DATE/TIME -> resolve all temporal references (today, tonight,
  this weekend, "now") against the current date in the operator'"'"'s timezone,
  and render every date/time in that zone.
- LOCATION -> for ANY place-dependent lookup (weather, places, restaurants,
  events, traffic, "nearby"), localise to it and put it INTO the search query;
  never localise to the server'"'"'s network location or to a default.
- BROWSER LOCALE -> use it for number, date, and unit conventions (metric vs
  imperial, date order, decimal mark); never to choose the reply language (see
  RESPONSE LANGUAGE), and never to silently convert a figure a tool returned.
- NAME -> address the operator by it; use no name if it is not provided.
A fact marked Unknown / None / blank is simply NOT PROVIDED -- never guess it.

LOOP every request: REASON (what'"'"'s asked + is it one ask or several?)
-> PLAN (break into steps; for any open/find/install/use X, FAN OUT in
parallel across the inventory + search verbs first; decide local-file
vs web by intent) -> DELEGATE (fire parallel, merge, act on the
highest-confidence result; answer EACH part of a multi-part ask).

RULES: tool stdout is ground truth -- never invent paths/IDs/statuses/
versions/prices/news/weather. Cite real source links from tool results
verbatim; never invent a URL. Never say "X isn'"'"'t installed" without a
zero-hit fan-out. Native tools are tool_calls, not bash lines. "Process
alive" is not "launched" (check the active window). Greetings: 1-2
sentences, no tools. Never tail with "would you like me to" / "feel free
to" / "let me know".
'
: "${MIOS_OWUI_SYSTEM_PROMPT_USER_SECTION_PATH:=~/.config/mios/system-prompt-user.md}"
: "${MIOS_PASSPORT_AGENTS:=agent-pipe,hermes,mios-daemon,opencode,cron-director}"
: "${MIOS_PASSPORT_ALGO:=ed25519}"
: "${MIOS_PASSPORT_ENABLE:=true}"
: "${MIOS_PASSPORT_KEY_DIR:=/var/lib/mios/agent-passports}"
: "${MIOS_PASSPORT_ROTATE_DAYS:=365}"
: "${MIOS_PASSPORT_VERIFY_ON_READ:=false}"
: "${MIOS_PASSWORD_POLICY:=plain}"
: "${MIOS_PATHS_AI_DIR:=/usr/share/mios/ai}"
: "${MIOS_PATHS_AI_JOURNAL:=/var/lib/mios/ai/journal.md}"
: "${MIOS_PATHS_AI_MCP_DIR:=/srv/ai/mcp}"
: "${MIOS_PATHS_AI_MEMORY_DIR:=/var/lib/mios/ai/memory}"
: "${MIOS_PATHS_AI_MODELS_DIR:=/srv/ai/models}"
: "${MIOS_PATHS_AI_SCRATCH_DIR:=/var/lib/mios/ai/scratch}"
[ -n "${MIOS_PATHS_AI_SYSTEM_PROMPT+x}" ] || MIOS_PATHS_AI_SYSTEM_PROMPT="${MIOS_SHARE_AI_DIR}"'/system.md'
: "${MIOS_PATHS_CMD_EXE:=/mnt/c/Windows/System32/cmd.exe}"
: "${MIOS_PATHS_CODEMODE_WORKSPACE_ROOT:=/var/lib/mios/codemode}"
: "${MIOS_PATHS_CODERUN_SNAPSHOTS_ROOT:=/var/home/mios/.coderun-snapshots}"
: "${MIOS_PATHS_CODERUN_WORKSPACE_ROOT:=/var/home/mios/coderuns}"
[ -n "${MIOS_PATHS_ETC_AI_DIR+x}" ] || MIOS_PATHS_ETC_AI_DIR="${MIOS_ETC_DIR}"'/ai'
: "${MIOS_PATHS_ETC_DIR:=/etc/mios}"
[ -n "${MIOS_PATHS_ETC_ENVD_DIR+x}" ] || MIOS_PATHS_ETC_ENVD_DIR="${MIOS_ETC_DIR}"'/env.d'
[ -n "${MIOS_PATHS_ETC_FORGE_DIR+x}" ] || MIOS_PATHS_ETC_FORGE_DIR="${MIOS_ETC_DIR}"'/forge'
: "${MIOS_PATHS_EVERYTHING_CLI:=/mnt/m/Programs/Everything/es.exe,/mnt/c/Program Files/Everything/es.exe,/mnt/c/Program Files (x86)/Everything/es.exe,/mnt/c/Tools/Everything/es.exe,/mnt/c/Users/mios/AppData/Local/Programs/Everything/es.exe}"
: "${MIOS_PATHS_EVERYTHING_CLI_VERSION:=1.1.0.37}"
[ -n "${MIOS_PATHS_FIRSTBOOT_SENTINEL+x}" ] || MIOS_PATHS_FIRSTBOOT_SENTINEL="${MIOS_VAR_DIR}"'/.wsl-firstboot-done'
: "${MIOS_PATHS_INSTALL_ENV:=/etc/mios/install.env}"
: "${MIOS_PATHS_LAUNCHER_SOCKET:=/run/mios-launcher/launcher.sock}"
: "${MIOS_PATHS_LIBEXEC_DIR:=/usr/libexec/mios}"
[ -n "${MIOS_PATHS_MCP_REGISTRY+x}" ] || MIOS_PATHS_MCP_REGISTRY="${MIOS_SHARE_AI_DIR}"'/v1/mcp.json'
: "${MIOS_PATHS_MIOS_TOML:=/usr/share/mios/mios.toml}"
: "${MIOS_PATHS_POWERSHELL_EXE:=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe}"
: "${MIOS_PATHS_PROFILE_TOML_HOST:=/etc/mios/profile.toml}"
: "${MIOS_PATHS_PROFILE_TOML_VENDOR:=/usr/share/mios/profile.toml}"
[ -n "${MIOS_PATHS_SHARE_AI_DIR+x}" ] || MIOS_PATHS_SHARE_AI_DIR="${MIOS_SHARE_DIR}"'/ai'
[ -n "${MIOS_PATHS_SHARE_BRANDING_DIR+x}" ] || MIOS_PATHS_SHARE_BRANDING_DIR="${MIOS_SHARE_DIR}"'/branding'
[ -n "${MIOS_PATHS_SHARE_CONFIGURATOR_DIR+x}" ] || MIOS_PATHS_SHARE_CONFIGURATOR_DIR="${MIOS_SHARE_DIR}"'/configurator'
: "${MIOS_PATHS_SHARE_DIR:=/usr/share/mios}"
[ -n "${MIOS_PATHS_SHARE_DISTROBOX_DIR+x}" ] || MIOS_PATHS_SHARE_DISTROBOX_DIR="${MIOS_SHARE_DIR}"'/distrobox'
[ -n "${MIOS_PATHS_SHARE_FASTFETCH_DIR+x}" ] || MIOS_PATHS_SHARE_FASTFETCH_DIR="${MIOS_SHARE_DIR}"'/fastfetch'
[ -n "${MIOS_PATHS_SHARE_K3S_MANIFESTS_DIR+x}" ] || MIOS_PATHS_SHARE_K3S_MANIFESTS_DIR="${MIOS_SHARE_DIR}"'/k3s-manifests'
[ -n "${MIOS_PATHS_SHARE_KB_DIR+x}" ] || MIOS_PATHS_SHARE_KB_DIR="${MIOS_SHARE_DIR}"'/kb'
: "${MIOS_SRV_AI_DIR:=/srv/ai}"
[ -n "${MIOS_PATHS_SRV_AI_COLLECTIONS_DIR+x}" ] || MIOS_PATHS_SRV_AI_COLLECTIONS_DIR="${MIOS_SRV_AI_DIR}"'/collections'
: "${MIOS_PATHS_SRV_AI_DIR:=/srv/ai}"
[ -n "${MIOS_PATHS_SRV_AI_MCP_DIR+x}" ] || MIOS_PATHS_SRV_AI_MCP_DIR="${MIOS_SRV_AI_DIR}"'/mcp'
[ -n "${MIOS_PATHS_SRV_AI_MODELS_DIR+x}" ] || MIOS_PATHS_SRV_AI_MODELS_DIR="${MIOS_SRV_AI_DIR}"'/models'
[ -n "${MIOS_PATHS_SRV_AI_OUTPUTS_DIR+x}" ] || MIOS_PATHS_SRV_AI_OUTPUTS_DIR="${MIOS_SRV_AI_DIR}"'/outputs'
[ -n "${MIOS_PATHS_TOML_HOST+x}" ] || MIOS_PATHS_TOML_HOST="${MIOS_ETC_DIR}"'/mios.toml'
[ -n "${MIOS_PATHS_TOML_VENDOR+x}" ] || MIOS_PATHS_TOML_VENDOR="${MIOS_SHARE_DIR}"'/mios.toml'
: "${MIOS_PATHS_USR_DIR:=/usr/lib/mios}"
[ -n "${MIOS_PATHS_VAR_AI_DIR+x}" ] || MIOS_PATHS_VAR_AI_DIR="${MIOS_VAR_DIR}"'/ai'
[ -n "${MIOS_PATHS_VAR_BACKUPS_DIR+x}" ] || MIOS_PATHS_VAR_BACKUPS_DIR="${MIOS_VAR_DIR}"'/backups'
[ -n "${MIOS_PATHS_VAR_CACHE_DIR+x}" ] || MIOS_PATHS_VAR_CACHE_DIR="${MIOS_VAR_DIR}"'/cache'
: "${MIOS_PATHS_VAR_DIR:=/var/lib/mios}"
[ -n "${MIOS_PATHS_VAR_MCP_DIR+x}" ] || MIOS_PATHS_VAR_MCP_DIR="${MIOS_VAR_DIR}"'/mcp'
: "${MIOS_PATHS_WSL_FIRSTBOOT_DONE:=/var/lib/mios/.wsl-firstboot-done}"
: "${MIOS_PGVECTOR_DATA_DIR:=/var/lib/mios/pgvector}"
: "${MIOS_PGVECTOR_DB:=mios}"
: "${MIOS_PGVECTOR_DB_BACKEND:=postgres}"
: "${MIOS_PGVECTOR_EMBED_MODEL:=nomic-embed-text}"
: "${MIOS_PGVECTOR_ENABLE:=true}"
: "${MIOS_PGVECTOR_GID:=826}"
: "${MIOS_PGVECTOR_HOST:=127.0.0.1}"
: "${MIOS_PGVECTOR_IMAGE:=docker.io/pgvector/pgvector:pg18}"
: "${MIOS_PGVECTOR_PASS:=mios}"
: "${MIOS_PGVECTOR_PORT:=8600}"
: "${MIOS_PGVECTOR_RESTORE_SQL:=/var/lib/mios/pgvector-restore.sql}"
: "${MIOS_PGVECTOR_RLS_MODE:=off}"
: "${MIOS_PGVECTOR_SCHEMA_INIT:=/usr/share/mios/postgres/schema-init.sql}"
: "${MIOS_PGVECTOR_UID:=826}"
: "${MIOS_PGVECTOR_USER:=mios-pgvector}"
: "${MIOS_PGVECTOR_VERSION:=docker.io/pgvector/pgvector:pg18}"
: "${MIOS_PG_BACKUP_DIR:=/var/lib/mios/backups}"
: "${MIOS_PG_BACKUP_ENABLE:=true}"
: "${MIOS_PG_BACKUP_KEEP:=7}"
: "${MIOS_PG_DATA_DIR:=/var/lib/mios/pgvector}"
: "${MIOS_PG_DB:=mios}"
: "${MIOS_PG_EMBED_MODEL:=nomic-embed-text}"
: "${MIOS_PG_ENABLE:=true}"
: "${MIOS_PG_HOST:=127.0.0.1}"
: "${MIOS_PG_PASS:=mios}"
: "${MIOS_PG_RESTORE_SQL:=/var/lib/mios/pgvector-restore.sql}"
: "${MIOS_PG_RLS_MODE:=off}"
: "${MIOS_PG_SCHEMA_INIT:=/usr/share/mios/postgres/schema-init.sql}"
: "${MIOS_PG_USER:=mios}"
[ -n "${MIOS_PIPELINE_BANDS+x}" ] || MIOS_PIPELINE_BANDS='{'"'"'range'"'"': [1, 1], '"'"'purpose'"'"': '"'"'git-overlay'"'"'},{'"'"'range'"'"': [2, 2], '"'"'purpose'"'"': '"'"'build-context'"'"'},{'"'"'range'"'"': [5, 7], '"'"'purpose'"'"': '"'"'repos/kernel'"'"'},{'"'"'range'"'"': [10, 15], '"'"'purpose'"'"': '"'"'accounts'"'"'},{'"'"'range'"'"': [20, 27], '"'"'purpose'"'"': '"'"'hardware-universal'"'"'},{'"'"'range'"'"': [33, 54], '"'"'purpose'"'"': '"'"'services'"'"'},{'"'"'range'"'"': [56, 62], '"'"'purpose'"'"': '"'"'themes'"'"'},{'"'"'range'"'"': [65, 80], '"'"'purpose'"'"': '"'"'ai/desktop/boot/distribution'"'"'},{'"'"'range'"'"': [85, 99], '"'"'purpose'"'"': '"'"'finalize/validators'"'"'}'
: "${MIOS_PIPELINE_CHECK_INDEX:=usr/share/mios/reference/drift-gate-index.tsv}"
: "${MIOS_PIPELINE_CHECK_STAGE:=98}"
[ -n "${MIOS_PIPELINE_EXTERNAL_COUNTERS+x}" ] || MIOS_PIPELINE_EXTERNAL_COUNTERS='{'"'"'tool'"'"': '"'"'podman/buildah'"'"', '"'"'pattern'"'"': '"'"'STEP i/N'"'"', '"'"'scope'"'"': '"'"'outer ~25, nested mios-sys ~19, go-builder 2, rust-builder 4'"'"'},{'"'"'tool'"'"': '"'"'dnf5'"'"', '"'"'pattern'"'"': '"'"'[i/N]'"'"', '"'"'scope'"'"': '"'"'download ~55 + transaction ~57'"'"'},{'"'"'tool'"'"': '"'"'cargo'"'"', '"'"'pattern'"'"': '"'"'Compiling c (i/m)'"'"', '"'"'scope'"'"': '"'"'rust-builder crate graph'"'"'}'
: "${MIOS_PIPELINE_EXTERNAL_SUPPRESS_HINT:=quiet flags only (dnf5 -q, buildah --quiet, cargo -q). Never parse or fold into the MiOS scheme.}"
: "${MIOS_PIPELINE_FUTURE_AXES:=oci_run_step}"
: "${MIOS_PIPELINE_GATE:=98-drift-checks.sh:check_pipeline_numbering}"
: "${MIOS_PIPELINE_GENERATOR:=tools/generate-pipeline-index.py}"
: "${MIOS_PIPELINE_IDENTITY_AXES:=script_prefix,log_label}"
: "${MIOS_PIPELINE_INVARIANTS_CHECK_DENSE:=true}"
: "${MIOS_PIPELINE_INVARIANTS_CHECK_DERIVED:=true}"
: "${MIOS_PIPELINE_INVARIANTS_LABEL_NOT_STALE:=true}"
: "${MIOS_PIPELINE_INVARIANTS_MAP_IN_SYNC:=true}"
: "${MIOS_PIPELINE_INVARIANTS_PREFIX_IN_BAND:=true}"
: "${MIOS_PIPELINE_INVARIANTS_PREFIX_UNIQUE:=true}"
: "${MIOS_PIPELINE_INVARIANTS_SINGLE_PROGRESS:=true}"
[ -n "${MIOS_PIPELINE_LABEL_CHECK+x}" ] || MIOS_PIPELINE_LABEL_CHECK='[{nn}-{name}:{cc}]'
[ -n "${MIOS_PIPELINE_LABEL_STAGE+x}" ] || MIOS_PIPELINE_LABEL_STAGE='[{nn}-{name}]'
: "${MIOS_PIPELINE_MAP:=usr/share/mios/reference/pipeline-index.tsv}"
: "${MIOS_PIPELINE_PROGRESS_AXIS:=script_count}"
: "${MIOS_PIPELINE_REPORTER:=usr/lib/mios/log.sh}"
: "${MIOS_PIPELINE_SPACE_MAX:=99}"
: "${MIOS_PIPELINE_SPACE_MIN:=0}"
: "${MIOS_PKG_BOOTSTRAP_PER_SOURCE_CAP:=200}"
: "${MIOS_PKG_LOOKUP_MAX_ALIAS_RESULTS:=3}"
: "${MIOS_PLANNER_SHORT_PROMPT_CHARS:=60}"
: "${MIOS_PLANNER_SHORT_PROMPT_WORDS:=10}"
: "${MIOS_PODS_MIOS_AI_AFTER:=network-online.target}"
[ -n "${MIOS_PODS_MIOS_AI_DESCRIPTION+x}" ] || MIOS_PODS_MIOS_AI_DESCRIPTION=''"'"'MiOS'"'"' AI pod (inference, heavy, data, ui)'
: "${MIOS_PODS_MIOS_AI_DOC:=Consolidated AI pod.}"
: "${MIOS_PODS_MIOS_AI_MEMBERS:=mios-llm-light,mios-cpu-node,mios-llm-worker@,mios-llm-heavy,mios-llm-heavy-alt,mios-pgvector,mios-open-webui}"
: "${MIOS_PODS_MIOS_AI_NETWORK:=host}"
: "${MIOS_PODS_MIOS_AI_WANTED_BY:=multi-user.target,default.target}"
: "${MIOS_PODS_MIOS_AI_WANTS:=network-online.target}"
: "${MIOS_PODS_MIOS_SYSTEM_AFTER:=network-online.target}"
[ -n "${MIOS_PODS_MIOS_SYSTEM_DESCRIPTION+x}" ] || MIOS_PODS_MIOS_SYSTEM_DESCRIPTION=''"'"'MiOS'"'"' System pod (dns, storage, admin, sec, pxe, k3s, remote-desktop)'
: "${MIOS_PODS_MIOS_SYSTEM_DOC:=Consolidated system services pod.}"
: "${MIOS_PODS_MIOS_SYSTEM_MEMBERS:=mios-adguard,mios-ceph,mios-pxe-hub,mios-k3s,mios-guacamole,mios-guacd}"
: "${MIOS_PODS_MIOS_SYSTEM_NETWORK:=host}"
: "${MIOS_PODS_MIOS_SYSTEM_WANTED_BY:=multi-user.target,default.target}"
: "${MIOS_PODS_MIOS_SYSTEM_WANTS:=network-online.target}"
: "${MIOS_PODS_MIOS_WEBTOOLS_AFTER:=network-online.target,mios-hermes-browser.service,mios-webtools-firstboot.service}"
[ -n "${MIOS_PODS_MIOS_WEBTOOLS_DESCRIPTION+x}" ] || MIOS_PODS_MIOS_WEBTOOLS_DESCRIPTION=''"'"'MiOS'"'"' Webtools pod (webtools, search, devforge)'
: "${MIOS_PODS_MIOS_WEBTOOLS_DOC:=Consolidated webtools pod.}"
: "${MIOS_PODS_MIOS_WEBTOOLS_MEMBERS:=mios-webtools-redis,mios-webtools-firecrawl-api,mios-webtools-firecrawl-worker,mios-webtools-crawl4ai,mios-searxng,mios-forge,mios-forgejo-runner,mios-code-server,mios-otelcol}"
: "${MIOS_PODS_MIOS_WEBTOOLS_NETWORK:=host}"
: "${MIOS_PODS_MIOS_WEBTOOLS_WANTED_BY:=multi-user.target,default.target}"
: "${MIOS_PODS_MIOS_WEBTOOLS_WANTS:=network-online.target,mios-hermes-browser.service,mios-webtools-firstboot.service}"
: "${MIOS_POLISH_ENABLE:=true}"
[ -n "${MIOS_POLISH_ENDPOINT+x}" ] || MIOS_POLISH_ENDPOINT='http://localhost:'"${MIOS_PORT_LLM_LIGHT}"
: "${MIOS_POLISH_MAX_TOKENS:=800}"
: "${MIOS_POLISH_MODEL:=mios-agent}"
: "${MIOS_POLISH_TIMEOUT_S:=45}"
: "${MIOS_POLISH_TIMEOUT_SECONDS:=45}"
: "${MIOS_PORTAL_REQUIRE_LOGIN:=true}"
: "${MIOS_PORTAL_SESSION_TTL:=604800}"
: "${MIOS_PORTS_ADGUARD_DNS:=53}"
: "${MIOS_PORTS_ADGUARD_UI:=8050}"
: "${MIOS_PORTS_AGENT_PIPE:=8700}"
: "${MIOS_PORTS_ARBITER:=8760}"
: "${MIOS_PORTS_CATEGORIES_ADMIN_BASE:=8100}"
: "${MIOS_PORTS_CATEGORIES_ADMIN_DOC:=Host administration surfaces (operator SSH, Cockpit console + discovery shim).}"
: "${MIOS_PORTS_CATEGORIES_ADMIN_MEMBERS:=ssh,cockpit,cockpit_link}"
: "${MIOS_PORTS_CATEGORIES_ADMIN_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_AGENT_BASE:=8700}"
: "${MIOS_PORTS_CATEGORIES_AGENT_DOC:=Agent plane. Ordered along the request path: pipe -> prefilter -> hermes -> workers -> router -> arbiter, then the MCP host and the /v1 gateway shims. All LOOPBACK-only except hermes.}"
: "${MIOS_PORTS_CATEGORIES_AGENT_MEMBERS:=agent_pipe,prefilter,hermes,,daemon_agent,model_router,arbiter,mcp,opencode_gateway}"
: "${MIOS_PORTS_CATEGORIES_AGENT_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_BRIDGE_BASE:=8950}"
: "${MIOS_PORTS_CATEGORIES_BRIDGE_DOC:=Cross-OS bridges (Windows-side UI Automation executor). LOOPBACK-only.}"
: "${MIOS_PORTS_CATEGORIES_BRIDGE_MEMBERS:=oscontrol}"
: "${MIOS_PORTS_CATEGORIES_BRIDGE_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_CLUSTER_BASE:=8450}"
: "${MIOS_PORTS_CATEGORIES_CLUSTER_DOC:=Cluster orchestration and storage control planes.}"
: "${MIOS_PORTS_CATEGORIES_CLUSTER_MEMBERS:=k3s_api,ceph_dashboard}"
: "${MIOS_PORTS_CATEGORIES_CLUSTER_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_DATA_BASE:=8600}"
: "${MIOS_PORTS_CATEGORIES_DATA_DOC:=Datastores (the unified agent DB).}"
: "${MIOS_PORTS_CATEGORIES_DATA_MEMBERS:=pgvector}"
: "${MIOS_PORTS_CATEGORIES_DATA_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_DESKTOP_BASE:=8300}"
: "${MIOS_PORTS_CATEGORIES_DESKTOP_DOC:=Remote desktop and browser-pty session surfaces.}"
: "${MIOS_PORTS_CATEGORIES_DESKTOP_MEMBERS:=rdp,ttyd_bash,ttyd_powershell}"
: "${MIOS_PORTS_CATEGORIES_DESKTOP_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_DEVTOOLS_BASE:=8900}"
: "${MIOS_PORTS_CATEGORIES_DEVTOOLS_DOC:=Developer surfaces served to a browser.}"
: "${MIOS_PORTS_CATEGORIES_DEVTOOLS_MEMBERS:=code_server}"
: "${MIOS_PORTS_CATEGORIES_DEVTOOLS_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_EDGE_BASE:=8050}"
: "${MIOS_PORTS_CATEGORIES_EDGE_DOC:=Network edge / resolver. DNS is protocol-pinned at 53 and never floats.}"
: "${MIOS_PORTS_CATEGORIES_EDGE_MEMBERS:=adguard_ui}"
: "${MIOS_PORTS_CATEGORIES_EDGE_PINNED_ADGUARD_DNS:=53}"
: "${MIOS_PORTS_CATEGORIES_EDGE_STRIDE:=1}"
: "${MIOS_PORTS_CATEGORIES_FORGE_BASE:=8400}"
: "${MIOS_PORTS_CATEGORIES_FORGE_DOC:=Source forge and CI (Forgejo web + git-over-ssh).}"
: "${MIOS_PORTS_CATEGORIES_FORGE_MEMBERS:=forge_http,forge_ssh}"
: "${MIOS_PORTS_CATEGORIES_FORGE_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_INFERENCE_BASE:=8500}"
: "${MIOS_PORTS_CATEGORIES_INFERENCE_DOC:=Model-serving lanes. Ordered cheapest-to-heaviest: always-on llama.cpp, CPU lane, then the GATED dGPU lanes.}"
: "${MIOS_PORTS_CATEGORIES_INFERENCE_MEMBERS:=llm_light,cpu_node,vllm,sglang}"
: "${MIOS_PORTS_CATEGORIES_INFERENCE_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_SIDECAR_BASE:=8560}"
: "${MIOS_PORTS_CATEGORIES_SIDECAR_DOC:=Supporting daemons that bind a real port but are not user-facing services. Each was HARDCODED in a Quadlet with no SSOT key (guacd 4822, redis 6380, Chrome CDP 9222, OTLP 4317, Jaeger query 16686, matchbox 8081), so nothing could detect a collision when a container was added. Allocating a key is only half the job: the service must then BIND it, which is why [ports].unbound is a shrink-only register gated by check_ports_bound. Index 6 is a RESERVED slot -- forge_ssh_git named a second Forgejo SSH listener that does not exist, since SSH_PORT and SSH_LISTEN_PORT both resolve MIOS_PORT_FORGE_SSH.}"
: "${MIOS_PORTS_CATEGORIES_SIDECAR_MEMBERS:=guacd,redis,,otelcol_otlp,otelcol_ui,pxe_hub_api,}"
: "${MIOS_PORTS_CATEGORIES_SIDECAR_PINNED_CHROME_CDP:=9222}"
: "${MIOS_PORTS_CATEGORIES_SIDECAR_PINNED_CHROME_CDP_WORKER:=9223}"
: "${MIOS_PORTS_CATEGORIES_SIDECAR_STRIDE:=5}"
: "${MIOS_PORTS_CATEGORIES_WEBTOOLS_BASE:=8800}"
: "${MIOS_PORTS_CATEGORIES_WEBTOOLS_DOC:=Search, crawl and scrape backends (the mios-webtools pod). LOOPBACK-only.}"
: "${MIOS_PORTS_CATEGORIES_WEBTOOLS_MEMBERS:=searxng,crawl4ai,firecrawl}"
: "${MIOS_PORTS_CATEGORIES_WEBTOOLS_STRIDE:=10}"
: "${MIOS_PORTS_CATEGORIES_WEBUI_BASE:=8200}"
: "${MIOS_PORTS_CATEGORIES_WEBUI_DOC:=Browser-facing application UIs a human opens directly.}"
: "${MIOS_PORTS_CATEGORIES_WEBUI_MEMBERS:=open_webui,hermes_dashboard,guacamole_web}"
: "${MIOS_PORTS_CATEGORIES_WEBUI_STRIDE:=10}"
: "${MIOS_PORTS_CEPH_DASHBOARD:=8460}"
: "${MIOS_PORTS_CHROME_CDP:=9222}"
: "${MIOS_PORTS_CHROME_CDP_WORKER:=9223}"
: "${MIOS_PORTS_COCKPIT:=8110}"
: "${MIOS_PORTS_COCKPIT_LINK:=8120}"
: "${MIOS_PORTS_CODE_SERVER:=8900}"
: "${MIOS_PORTS_CPU_NODE:=8510}"
: "${MIOS_PORTS_CRAWL4AI:=8810}"
: "${MIOS_PORTS_DAEMON_AGENT:=8740}"
: "${MIOS_PORTS_FIRECRAWL:=8820}"
: "${MIOS_PORTS_FORGE_HTTP:=8400}"
: "${MIOS_PORTS_FORGE_SSH:=8410}"
: "${MIOS_PORTS_GUACAMOLE_WEB:=8220}"
: "${MIOS_PORTS_GUACD:=8560}"
: "${MIOS_PORTS_HERMES:=8720}"
: "${MIOS_PORTS_HERMES_DASHBOARD:=8210}"
: "${MIOS_PORTS_K3S_API:=8450}"
: "${MIOS_PORTS_LLM_LIGHT:=8500}"
: "${MIOS_PORTS_MCP:=8770}"
: "${MIOS_PORTS_MODEL_ROUTER:=8750}"
: "${MIOS_PORTS_OPENCODE_GATEWAY:=8780}"
: "${MIOS_PORTS_OPEN_WEBUI:=8200}"
: "${MIOS_PORTS_OSCONTROL:=8950}"
: "${MIOS_PORTS_OTELCOL_OTLP:=8575}"
: "${MIOS_PORTS_OTELCOL_UI:=8580}"
: "${MIOS_PORTS_PGVECTOR:=8600}"
: "${MIOS_PORTS_PREFILTER:=8710}"
: "${MIOS_PORTS_PXE_HUB_API:=8585}"
: "${MIOS_PORTS_RDP:=8300}"
: "${MIOS_PORTS_REDIS:=8565}"
: "${MIOS_PORTS_SEARXNG:=8800}"
: "${MIOS_PORTS_SGLANG:=8530}"
: "${MIOS_PORTS_SSH:=8100}"
: "${MIOS_PORTS_STACK_ID:=0}"
: "${MIOS_PORTS_TTYD_BASH:=8310}"
: "${MIOS_PORTS_TTYD_POWERSHELL:=8320}"
: "${MIOS_PORTS_UNBOUND:=chrome_cdp_worker}"
: "${MIOS_PORTS_VLLM:=8520}"
: "${MIOS_PORT_ADGUARD_DNS:=53}"
: "${MIOS_PORT_ADGUARD_UI:=8050}"
: "${MIOS_PORT_ARBITER:=8760}"
: "${MIOS_PORT_CEPH_DASHBOARD:=8460}"
: "${MIOS_PORT_CHROME_CDP_WORKER:=9223}"
: "${MIOS_PORT_COCKPIT_LINK:=8120}"
: "${MIOS_PORT_CRAWL4AI:=8810}"
: "${MIOS_PORT_DAEMON_AGENT:=8740}"
: "${MIOS_PORT_FIRECRAWL:=8820}"
: "${MIOS_PORT_FORGE_SSH:=8410}"
: "${MIOS_PORT_GUACD:=8560}"
: "${MIOS_PORT_HERMES_DASHBOARD:=8210}"
: "${MIOS_PORT_K3S_API:=8450}"
: "${MIOS_PORT_MCP:=8770}"
: "${MIOS_PORT_MODEL_ROUTER:=8750}"
: "${MIOS_PORT_OSCONTROL:=8950}"
: "${MIOS_PORT_PGVECTOR:=8600}"
: "${MIOS_PORT_PREFILTER:=8710}"
: "${MIOS_PORT_PXE_HUB_API:=8585}"
: "${MIOS_PORT_RDP:=8300}"
: "${MIOS_PORT_REDIS:=8565}"
: "${MIOS_PORT_SEARXNG:=8800}"
: "${MIOS_PORT_SSH:=8100}"
: "${MIOS_PORT_STACK_ID:=0}"
: "${MIOS_PORT_TTYD_BASH:=8310}"
: "${MIOS_PORT_TTYD_POWERSHELL:=8320}"
: "${MIOS_PORT_UNBOUND:=chrome_cdp_worker}"
: "${MIOS_POSTGRES_IMAGE:=docker.io/library/postgres:latest}"
: "${MIOS_POSTGRES_VERSION:=docker.io/library/postgres:latest}"
: "${MIOS_POWERSHELL_ENUMERATION_LIMIT:=16}"
: "${MIOS_POWERSHELL_EXE:=/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe}"
: "${MIOS_POWERSHELL_FLATTEN:=true}"
: "${MIOS_POWERSHELL_FLATTEN_WIDTH:=200}"
: "${MIOS_POWERSHELL_MAX_OUTPUT_BYTES:=262144}"
: "${MIOS_POWERSHELL_MAX_SCRIPT_BYTES:=65536}"
: "${MIOS_POWERSHELL_PLAIN_TEXT:=true}"
: "${MIOS_POWERSHELL_STAGE_DIR:=/mnt/c/Users/Public/Documents/mios-ps}"
: "${MIOS_POWERSHELL_TRIM_TRAILING:=true}"
: "${MIOS_POWER_UPS_DESC:=MiOS Uninterruptible Power Supply}"
: "${MIOS_POWER_UPS_DRIVER:=usbhid-ups}"
: "${MIOS_POWER_UPS_PORT:=auto}"
: "${MIOS_PREFILTER_CLASSIFY_TIMEOUT_S:=6}"
: "${MIOS_PREFILTER_CONVERSATIONAL_BYPASS_MODE:=model}"
: "${MIOS_PREFILTER_PORT:=8710}"
: "${MIOS_PREFLIGHT_MIN_DISK_FREE_GB:=280}"
: "${MIOS_PREFLIGHT_MIN_RAM_GB:=8}"
: "${MIOS_PREFLIGHT_MIN_WINDOWS_BUILD:=22000}"
: "${MIOS_PREFLIGHT_REQUIRE_ADMIN:=true}"
: "${MIOS_PREFLIGHT_REQUIRE_VIRT:=true}"
: "${MIOS_PROFILE_TOML_HOST:=/etc/mios/profile.toml}"
: "${MIOS_PROFILE_TOML_VENDOR:=/usr/share/mios/profile.toml}"
: "${MIOS_PXE_HUB_API_PORT:=8585}"
: "${MIOS_PXE_HUB_IMAGE:=quay.io/poseidon/matchbox:latest}"
: "${MIOS_PXE_HUB_VERSION:=quay.io/poseidon/matchbox:latest}"
: "${MIOS_QUADLETS_ENABLE_MIOS_ADGUARD:=true}"
: "${MIOS_QUADLETS_ENABLE_MIOS_CEPH:=true}"
: "${MIOS_QUADLETS_ENABLE_MIOS_CODE_SERVER:=false}"
: "${MIOS_QUADLETS_ENABLE_MIOS_FORGE:=true}"
: "${MIOS_QUADLETS_ENABLE_MIOS_GUACAMOLE:=true}"
: "${MIOS_QUADLETS_ENABLE_MIOS_GUACD:=true}"
: "${MIOS_QUADLETS_ENABLE_MIOS_K3S:=true}"
: "${MIOS_QUADLETS_ENABLE_MIOS_OPEN_WEBUI:=true}"
: "${MIOS_QUADLETS_ENABLE_MIOS_PXE_HUB:=true}"
: "${MIOS_QUADLET_DEV_NETWORK_MODE:=host}"
: "${MIOS_QUADLET_NETWORK:=mios.network}"
: "${MIOS_QUADLET_SUBNET:=10.89.0.0/24}"
: "${MIOS_RDP_PORT:=8300}"
: "${MIOS_RECHUNK_MAX_LAYERS:=67}"
: "${MIOS_REDIS_PORT:=8565}"
: "${MIOS_REFACTOR_MAX_LINES:=800}"
[ -n "${MIOS_REFACTOR_OVERSIZE+x}" ] || MIOS_REFACTOR_OVERSIZE='{'"'"'path'"'"': '"'"'mios_pipe/federation/a2a.py'"'"', '"'"'lines'"'"': 1545},{'"'"'path'"'"': '"'"'mios_pipe/federation/http_caps.py'"'"', '"'"'lines'"'"': 820},{'"'"'path'"'"': '"'"'mios_pipe/memory/knowledge.py'"'"', '"'"'lines'"'"': 961},{'"'"'path'"'"': '"'"'mios_pipe/routing/agent_call.py'"'"', '"'"'lines'"'"': 1153},{'"'"'path'"'"': '"'"'mios_pipe/routing/chat.py'"'"', '"'"'lines'"'"': 1786},{'"'"'path'"'"': '"'"'mios_pipe/routing/dag_exec.py'"'"', '"'"'lines'"'"': 1297},{'"'"'path'"'"': '"'"'mios_pipe/routing/native_loop.py'"'"', '"'"'lines'"'"': 1190},{'"'"'path'"'"': '"'"'mios_pipe/routing/portal.py'"'"', '"'"'lines'"'"': 1675},{'"'"'path'"'"': '"'"'mios_pipe/routing/refine.py'"'"', '"'"'lines'"'"': 1120},{'"'"'path'"'"': '"'"'mios_pipe/routing/swarm.py'"'"', '"'"'lines'"'"': 1062},{'"'"'path'"'"': '"'"'mios_pipe/routing/web_research.py'"'"', '"'"'lines'"'"': 987},{'"'"'path'"'"': '"'"'mios_dispatch.py'"'"', '"'"'lines'"'"': 943},{'"'"'path'"'"': '"'"'server.py'"'"', '"'"'lines'"'"': 4975}'
: "${MIOS_REFINE_BYPASS_CHARS:=24}"
: "${MIOS_REFINE_CHAT_CHARS:=40}"
: "${MIOS_REFINE_DISPATCH_ARG_MAX_WORDS:=3}"
: "${MIOS_REFINE_DISPATCH_CHARS:=60}"
: "${MIOS_REFINE_ENABLE:=true}"
[ -n "${MIOS_REFINE_ENDPOINT+x}" ] || MIOS_REFINE_ENDPOINT='http://localhost:'"${MIOS_PORT_LLM_LIGHT}"
: "${MIOS_REFINE_MAX_TOKENS:=1200}"
: "${MIOS_REFINE_MODEL:=mios-agent}"
: "${MIOS_REFINE_PROMOTE_CHARS:=100}"
: "${MIOS_REFINE_TIMEOUT_S:=45}"
: "${MIOS_REFINE_TIMEOUT_SECONDS:=45}"
[ -n "${MIOS_REFLECT_JUDGE_EXAMPLES+x}" ] || MIOS_REFLECT_JUDGE_EXAMPLES='a punt, refusal, '"'"'I cannot'"'"', or '"'"'where to look'"'"''
: "${MIOS_RELIABILITY_GATE_ENABLED:=false}"
: "${MIOS_RELIABILITY_PASS_AND_K_COUNT:=3}"
: "${MIOS_RELIABILITY_PASS_AND_K_DGM_COUNT:=5}"
[ -n "${MIOS_REMEMBER_TRIGGER_PHRASES+x}" ] || MIOS_REMEMBER_TRIGGER_PHRASES='remember,note,save,keep in mind,don'"'"'t forget,make a note'
: "${MIOS_REPOS_FEDORA_ENABLED:=true}"
: "${MIOS_REPOS_FEDORA_GPGCHECK:=true}"
[ -n "${MIOS_REPOS_FEDORA_GPGKEY+x}" ] || MIOS_REPOS_FEDORA_GPGKEY='file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-{ver}-x86_64'
: "${MIOS_REPOS_FEDORA_IP_RESOLVE:=4}"
: "${MIOS_REPOS_FEDORA_MAX_PARALLEL_DOWNLOADS:=10}"
[ -n "${MIOS_REPOS_FEDORA_METALINK+x}" ] || MIOS_REPOS_FEDORA_METALINK='https://mirrors.fedoraproject.org/metalink?repo=fedora-{ver}&arch=$basearch'
: "${MIOS_REPOS_FEDORA_MINRATE:=1k}"
[ -n "${MIOS_REPOS_FEDORA_NAME+x}" ] || MIOS_REPOS_FEDORA_NAME='Fedora {ver} - $basearch'
: "${MIOS_REPOS_FEDORA_PRIORITY:=95}"
: "${MIOS_REPOS_FEDORA_REPO_GPGCHECK:=false}"
: "${MIOS_REPOS_FEDORA_REPO_TYPE:=rpm}"
: "${MIOS_REPOS_FEDORA_SKIP_IF_UNAVAILABLE:=true}"
: "${MIOS_REPOS_FEDORA_TIMEOUT:=10}"
: "${MIOS_REPOS_FEDORA_UPDATES_ENABLED:=true}"
: "${MIOS_REPOS_FEDORA_UPDATES_GPGCHECK:=true}"
[ -n "${MIOS_REPOS_FEDORA_UPDATES_GPGKEY+x}" ] || MIOS_REPOS_FEDORA_UPDATES_GPGKEY='file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-{ver}-x86_64'
: "${MIOS_REPOS_FEDORA_UPDATES_IP_RESOLVE:=4}"
: "${MIOS_REPOS_FEDORA_UPDATES_MAX_PARALLEL_DOWNLOADS:=10}"
[ -n "${MIOS_REPOS_FEDORA_UPDATES_METALINK+x}" ] || MIOS_REPOS_FEDORA_UPDATES_METALINK='https://mirrors.fedoraproject.org/metalink?repo=updates-released-f{ver}&arch=$basearch'
: "${MIOS_REPOS_FEDORA_UPDATES_MINRATE:=1k}"
[ -n "${MIOS_REPOS_FEDORA_UPDATES_NAME+x}" ] || MIOS_REPOS_FEDORA_UPDATES_NAME='Fedora {ver} Updates - $basearch'
: "${MIOS_REPOS_FEDORA_UPDATES_PRIORITY:=95}"
: "${MIOS_REPOS_FEDORA_UPDATES_REPO_GPGCHECK:=false}"
: "${MIOS_REPOS_FEDORA_UPDATES_REPO_TYPE:=rpm}"
: "${MIOS_REPOS_FEDORA_UPDATES_SKIP_IF_UNAVAILABLE:=true}"
: "${MIOS_REPOS_FEDORA_UPDATES_TIMEOUT:=10}"
: "${MIOS_REPO_URL:=C:/MiOS}"
[ -n "${MIOS_ROLE+x}" ] || MIOS_ROLE='the ONE name you go by on EVERY surface (the `@`/`mios` CLI, OWUI, Discord, the desktop app, the API)'
: "${MIOS_ROUTER_ENABLE:=true}"
: "${MIOS_ROUTING_BOOLEAN_PARAM_KEYWORDS:=enable,force,success,active,dryrun}"
: "${MIOS_ROUTING_BROWSER_ACTION_VERBS:=quote,read,tell,summarise,summarize,what is,what does,what say,what says,first sentence,the content,browse,extract,scrape,headline,article,say}"
: "${MIOS_ROUTING_COMPOUND_ACTIONS:=type,write,enter,input,paste,put}"
: "${MIOS_ROUTING_COMPOUND_CONJUNCTIONS:=and,then}"
: "${MIOS_ROUTING_COMPOUND_CONNECTIVES:=in,and,then,with,on,to}"
: "${MIOS_ROUTING_INTEGER_PARAM_KEYWORDS:=limit,count,timeout,port,every,concurrency,maxsize}"
: "${MIOS_ROUTING_LAUNCH_FILLER_PHRASES:=for me please,on my desktop,on the desktop,right now,real quick,thank you,for me,please,thanks,now}"
[ -n "${MIOS_ROUTING_LAUNCH_FOLLOWUP_PHRASES+x}" ] || MIOS_ROUTING_LAUNCH_FOLLOWUP_PHRASES='didn'"'"'t launch,did not launch,didn'"'"'t open,did not open,didn'"'"'t start,did not start,didn'"'"'t come up,did not come up,didn'"'"'t work,did not work,wouldn'"'"'t open,would not open,no window,nothing happened,nothing opened,never opened,never launched,not opening,not launching,isn'"'"'t open,is not open,isn'"'"'t running,is not running,won'"'"'t open,won'"'"'t launch,doesn'"'"'t open,does not open,failed to open,failed to launch'
: "${MIOS_ROUTING_LAUNCH_RETRY_PHRASES:=attempt to launch and verify,launch and verify,launch it and verify,try to launch and verify,open and verify,open it and verify,try launching it again,try launching again,try opening it again,try opening again,launch it again,open it again,start it again,run it again,try again,attempt again,retry,relaunch,re-launch,reopen,re-open,try once more,one more time,attempt to launch,attempt the launch,verify the launch,launch and confirm,open and confirm}"
: "${MIOS_ROUTING_LAUNCH_TARGET_LEAD_PHRASES:=the,a,an,my}"
: "${MIOS_ROUTING_LAUNCH_TARGET_TRAIL_PHRASES:=application,program,app,window}"
: "${MIOS_ROUTING_LOCATION_SENSITIVE_PHRASES:=weather,forecast,near me,nearby,near here,around here,local news,local,my area,things to do,restaurants,closest,directions to}"
: "${MIOS_ROUTING_MODEL_MODALITIES_EMBEDDINGS:=embed,bert,text-embedding,bge}"
: "${MIOS_ROUTING_MODEL_MODALITIES_IMAGE:=diffuse,flux,dall,midjourney,sd}"
: "${MIOS_ROUTING_PREFILTER_CLASSIFY_TIMEOUT_S:=6}"
: "${MIOS_ROUTING_PREFILTER_CONVERSATIONAL_BYPASS_MODE:=model}"
[ -n "${MIOS_ROUTING_REMEMBER_TRIGGER_PHRASES+x}" ] || MIOS_ROUTING_REMEMBER_TRIGGER_PHRASES='remember,note,save,keep in mind,don'"'"'t forget,make a note'
: "${MIOS_ROUTING_ROUTER_ENABLE:=true}"
: "${MIOS_ROUTING_WEB_SEARCH_TRIGGER_CONTEXTS:=web,internet,online}"
: "${MIOS_ROUTING_WEB_SEARCH_TRIGGER_PHRASES:=search,look up,google,find,search the web,search online}"
: "${MIOS_RUN_TEMPLATE_ENABLE:=true}"
: "${MIOS_RUN_TEMPLATE_REPLAY_CANDIDATES:=50}"
: "${MIOS_RUN_TEMPLATE_REPLAY_ENABLE:=false}"
: "${MIOS_RUN_TEMPLATE_REPLAY_THRESHOLD:=0.85}"
: "${MIOS_SANDBOX_ENABLE:=false}"
: "${MIOS_SCHEDULER_MAX_PREEMPT_DEPTH:=1}"
: "${MIOS_SCHEDULER_MAX_SUSPENDED:=4}"
: "${MIOS_SCHEDULER_PREEMPT_ENABLE:=false}"
: "${MIOS_SCHEDULER_PRIORITY_LEVELS:=0}"
: "${MIOS_SCHEDULER_QUANTUM_S:=8.0}"
: "${MIOS_SCHEDULER_QUEUE_ENABLE:=false}"
: "${MIOS_SCHEDULER_QUEUE_MAX_TURNS:=64}"
: "${MIOS_SCHEDULER_SLICE_TOKENS:=256}"
: "${MIOS_SCHED_COMPLEXITY_BASE:=1}"
: "${MIOS_SCHED_COMPLEXITY_CAP:=10}"
: "${MIOS_SCHED_COMPLEXITY_HINTS_DIVISOR:=2}"
: "${MIOS_SCHED_PRIORITY_MODE:=ssot}"
: "${MIOS_SCHED_SCORE_COMPLEXITY_WEIGHT:=0.4}"
: "${MIOS_SCHED_SCORE_ROUND_NDIGITS:=2}"
: "${MIOS_SCHED_SCORE_URGENCY_WEIGHT:=0.6}"
: "${MIOS_SCHED_URGENCY_DEFAULT:=5}"
: "${MIOS_SCHED_URGENCY_DISPATCH_FLOOR:=8}"
: "${MIOS_SCHED_URGENCY_HIGH:=9}"
: "${MIOS_SCHED_URGENCY_HIGH_TERMS:=high,urgent,now}"
: "${MIOS_SCHED_URGENCY_LOW:=2}"
: "${MIOS_SCHED_URGENCY_LOW_TERMS:=low,background,defer}"
[ -n "${MIOS_SCHEMA_UNCONSUMED+x}" ] || MIOS_SCHEMA_UNCONSUMED='{'"'"'table'"'"': '"'"'mios_security.fido2_keys'"'"', '"'"'reason'"'"': '"'"'T-151 WS-SEC: declared ahead of the FIDO2 enrolment path'"'"'},{'"'"'table'"'"': '"'"'mios_security.usb_rules'"'"', '"'"'reason'"'"': '"'"'T-151 WS-SEC: declared ahead of the USBGuard rule sync'"'"'},{'"'"'table'"'"': '"'"'mios_security.headscale_users'"'"', '"'"'reason'"'"': '"'"'T-151 WS-SEC: declared ahead of the headscale control-plane sync'"'"'},{'"'"'table'"'"': '"'"'mios_security.headscale_preauth_keys'"'"', '"'"'reason'"'"': '"'"'T-151 WS-SEC: declared ahead of the headscale control-plane sync'"'"'},{'"'"'table'"'"': '"'"'mios_security.headscale_acl_rules'"'"', '"'"'reason'"'"': '"'"'T-151 WS-SEC: declared ahead of the headscale control-plane sync'"'"'},{'"'"'table'"'"': '"'"'mios_security.keepass_vaults'"'"', '"'"'reason'"'"': '"'"'T-151 WS-SEC: declared ahead of the vault integration'"'"'},{'"'"'table'"'"': '"'"'mios_identity.account_preferences'"'"', '"'"'reason'"'"': '"'"'T-246: duplicate of the live account_preference; RESOLVE, do not extend'"'"'},{'"'"'table'"'"': '"'"'person_device'"'"', '"'"'reason'"'"': '"'"'person graph: declared ahead of any device-enrolment writer'"'"'},{'"'"'table'"'"': '"'"'person_app_install'"'"', '"'"'reason'"'"': '"'"'person graph: declared ahead of any app-inventory writer'"'"'}'
: "${MIOS_SEARCH_ANCHOR_STOPWORDS:=the,a,an,of,to,from,and,or,for,in,on,at,by,with,as,is,are,was,were,be,this,that,these,those,it,its,me,my,we,our,you,your,they,them,what,which,who,when,where,why,how,do,does,did,can,could,will,would,should,may,might,near,into,about,than,then,there,here,out,not,no,all,any,some,more,most,find,get,make,show,give,tell,list,need,want,like,use,using,best,cheap,cheapest}"
: "${MIOS_SEARCH_ENABLE:=true}"
[ -n "${MIOS_SEARCH_ENDPOINT+x}" ] || MIOS_SEARCH_ENDPOINT='http://localhost:'"${MIOS_PORT_SEARXNG}"'/'
: "${MIOS_SEARXNG_GID:=818}"
: "${MIOS_SEARXNG_IMAGE:=docker.io/searxng/searxng:latest}"
: "${MIOS_SEARXNG_PORT:=8800}"
: "${MIOS_SEARXNG_UID:=818}"
[ -n "${MIOS_SEARXNG_URL+x}" ] || MIOS_SEARXNG_URL='http://localhost:'"${MIOS_PORT_SEARXNG}"
: "${MIOS_SEARXNG_USER:=mios-searxng}"
: "${MIOS_SEARXNG_VERSION:=docker.io/searxng/searxng:latest}"
: "${MIOS_SECURITY_ALLOWLIST_HOSTS:=localhost,127.0.0.1,::1,host.containers.internal,mios-llm-light,mios-open-webui,mios-hermes,mios-pgvector,mios-forge,mios-searxng,mios-crawl4ai,mios-code-server}"
: "${MIOS_SECURITY_PROBE_VERIFY_TLS:=true}"
: "${MIOS_SECURITY_PROVENANCE_TAINT:=false}"
: "${MIOS_SELFIMPROVE_ACCEPT_MARGIN:=0.0}"
: "${MIOS_SELFIMPROVE_ACT_ENABLED:=false}"
: "${MIOS_SELFIMPROVE_FAIL_THRESHOLD:=0.3}"
: "${MIOS_SELFIMPROVE_IMPROVABLE_TARGETS:=prompt,skill,config}"
: "${MIOS_SELFIMPROVE_INTERVAL_MIN:=0}"
: "${MIOS_SELFIMPROVE_MAX_PROPOSALS_PER_PASS:=3}"
: "${MIOS_SELFIMPROVE_MIN_SAMPLES:=5}"
: "${MIOS_SELFIMPROVE_PASSHAT_K:=2}"
: "${MIOS_SELFIMPROVE_PROTECTED_TARGETS:=evaluator,eval_data,lane_config,selfimprove}"
: "${MIOS_SELFIMPROVE_REQUIRE_IMPROVEMENT:=false}"
: "${MIOS_SELFIMPROVE_SAMPLE_SIZE:=500}"
: "${MIOS_SELFIMPROVE_SLOW_MS:=10000}"
: "${MIOS_SELFIMPROVE_SOLVER_GAP_MIN:=0.2}"
: "${MIOS_SELFIMPROVE_STRONG_SOLVER:=heavy}"
: "${MIOS_SELFIMPROVE_WEAK_SOLVER:=light}"
: "${MIOS_SENTENCE_ABBREVIATIONS:=approx.,Approx.,e.g.,i.e.,vs.,etc.,U.S.,U.K.,a.m.,p.m.,No.,Inc.,Co.,Ltd.,St.,Mt.}"
: "${MIOS_SERVICES_ADGUARD_GID:=825}"
: "${MIOS_SERVICES_ADGUARD_UID:=825}"
: "${MIOS_SERVICES_ADGUARD_USER:=mios-adguard}"
: "${MIOS_SERVICES_AGENT_PIPE_GID:=822}"
: "${MIOS_SERVICES_AGENT_PIPE_UID:=822}"
: "${MIOS_SERVICES_AGENT_PIPE_USER:=mios-agent-pipe}"
: "${MIOS_SERVICES_CEPH_GID:=819}"
: "${MIOS_SERVICES_CEPH_UID:=819}"
: "${MIOS_SERVICES_CEPH_USER:=mios-ceph}"
: "${MIOS_SERVICES_FORGE_GID:=816}"
: "${MIOS_SERVICES_FORGE_UID:=816}"
: "${MIOS_SERVICES_FORGE_USER:=mios-forge}"
: "${MIOS_SERVICES_HERMES_GID:=820}"
: "${MIOS_SERVICES_HERMES_UID:=820}"
: "${MIOS_SERVICES_HERMES_USER:=mios-hermes}"
: "${MIOS_SERVICES_LLAMACPP_GID:=827}"
: "${MIOS_SERVICES_LLAMACPP_UID:=827}"
: "${MIOS_SERVICES_LLAMACPP_USER:=mios-llamacpp}"
: "${MIOS_SERVICES_OPEN_WEBUI_GID:=817}"
: "${MIOS_SERVICES_OPEN_WEBUI_UID:=817}"
: "${MIOS_SERVICES_OPEN_WEBUI_USER:=mios-open-webui}"
: "${MIOS_SERVICES_PGVECTOR_GID:=826}"
: "${MIOS_SERVICES_PGVECTOR_UID:=826}"
: "${MIOS_SERVICES_PGVECTOR_USER:=mios-pgvector}"
: "${MIOS_SERVICES_SEARXNG_GID:=818}"
: "${MIOS_SERVICES_SEARXNG_UID:=818}"
: "${MIOS_SERVICES_SEARXNG_USER:=mios-searxng}"
: "${MIOS_SERVICES_WEBTOOLS_CAMOUFOX:=true}"
[ -n "${MIOS_SERVICES_WEBTOOLS_CDP_URL+x}" ] || MIOS_SERVICES_WEBTOOLS_CDP_URL='http://127.0.0.1:'"${MIOS_PORT_CHROME_CDP}"
: "${MIOS_SERVICES_WEBTOOLS_FIRECRAWL_BULL_KEY:=mios}"
: "${MIOS_SERVICES_WEBTOOLS_FIRECRAWL_LOG_LEVEL:=INFO}"
: "${MIOS_SERVICES_WEBTOOLS_FIRECRAWL_WORKERS:=2}"
: "${MIOS_SERVICES_WEBTOOLS_GID:=824}"
: "${MIOS_SERVICES_WEBTOOLS_MIN_CHARS:=200}"
: "${MIOS_SERVICES_WEBTOOLS_UID:=824}"
: "${MIOS_SERVICES_WEBTOOLS_USER:=mios-crawl4ai}"
: "${MIOS_SGLANG_BAKE_MODEL:=stelterlab/Qwen3-30B-A3B-Instruct-2507-AWQ}"
: "${MIOS_SGLANG_ENABLE:=false}"
: "${MIOS_SGLANG_ENABLE_HIERARCHICAL_CACHE:=true}"
: "${MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE:=true}"
: "${MIOS_SGLANG_IMAGE:=docker.io/lmsysorg/sglang:latest}"
: "${MIOS_SGLANG_KV_CACHE_DTYPE:=fp8_e5m2}"
: "${MIOS_SGLANG_MAX_MODEL_LEN:=262144}"
: "${MIOS_SGLANG_MEM_FRACTION:=0.85}"
: "${MIOS_SGLANG_PORT:=8530}"
: "${MIOS_SGLANG_SERVED_NAME:=mios-heavy}"
: "${MIOS_SGLANG_TOOL_PARSER:=qwen25}"
: "${MIOS_SGLANG_VERSION:=docker.io/lmsysorg/sglang:latest}"
[ -n "${MIOS_SHARE_BRANDING_DIR+x}" ] || MIOS_SHARE_BRANDING_DIR="${MIOS_SHARE_DIR}"'/branding'
[ -n "${MIOS_SHARE_CONFIGURATOR_DIR+x}" ] || MIOS_SHARE_CONFIGURATOR_DIR="${MIOS_SHARE_DIR}"'/configurator'
[ -n "${MIOS_SHARE_DISTROBOX_DIR+x}" ] || MIOS_SHARE_DISTROBOX_DIR="${MIOS_SHARE_DIR}"'/distrobox'
[ -n "${MIOS_SHARE_FASTFETCH_DIR+x}" ] || MIOS_SHARE_FASTFETCH_DIR="${MIOS_SHARE_DIR}"'/fastfetch'
[ -n "${MIOS_SHARE_K3S_MANIFESTS_DIR+x}" ] || MIOS_SHARE_K3S_MANIFESTS_DIR="${MIOS_SHARE_DIR}"'/k3s-manifests'
[ -n "${MIOS_SHARE_KB_DIR+x}" ] || MIOS_SHARE_KB_DIR="${MIOS_SHARE_DIR}"'/kb'
: "${MIOS_SHELL_ALIAS_GP:=git push}"
: "${MIOS_SHELL_ALIAS_GS:=git status}"
: "${MIOS_SHELL_ALIAS_LL:=ls -la}"
: "${MIOS_SHELL_SESSION_ENABLE:=false}"
: "${MIOS_SHELL_SESSION_HISTORY_LIMIT:=50000}"
: "${MIOS_SHELL_SESSION_IDLE_S:=1800}"
: "${MIOS_SHELL_SESSION_MAX_OUTPUT_CHARS:=24000}"
: "${MIOS_SHELL_SESSION_MAX_OUTPUT_LINES:=400}"
: "${MIOS_SHELL_SESSION_MAX_SESSIONS:=8}"
: "${MIOS_SHELL_SESSION_SHELL:=/bin/bash}"
: "${MIOS_SHELL_SESSION_SOCKET_NAME:=mios}"
: "${MIOS_SHELL_SESSION_STATE_DIR:=/var/lib/mios/shell-sessions}"
: "${MIOS_SHELL_SESSION_TIMEOUT_S:=120}"
: "${MIOS_SKILLS_AUTO_PROMOTE_THRESHOLD:=0.85}"
: "${MIOS_SKILLS_ENABLE:=true}"
: "${MIOS_SKILLS_LOCAL_CATALOG_DIR:=/var/lib/mios/skills}"
: "${MIOS_SKILLS_MAX_LENGTH:=8}"
: "${MIOS_SKILLS_MINE_INTERVAL_MINUTES:=60}"
: "${MIOS_SKILLS_MIN_LENGTH:=2}"
: "${MIOS_SKILLS_MIN_SUCCESS_RATE:=0.7}"
: "${MIOS_SKILLS_MIN_SUCCESS_SAMPLES:=3}"
: "${MIOS_SKILLS_MIN_SUPPORT:=3}"
: "${MIOS_SKILLS_SEED_CATALOG_DIR:=/usr/share/mios/skills}"
: "${MIOS_SKILLS_WINDOW_HOURS:=168}"
: "${MIOS_SLO_BEST_EFFORT_BUDGET_S:=120.0}"
: "${MIOS_SLO_DEFAULT_PRIORITY:=7.0}"
: "${MIOS_SLO_INTERACTIVE_BUDGET_S:=8.0}"
: "${MIOS_SLO_INTERACTIVE_PRIORITY:=7.0}"
[ -n "${MIOS_SRV_AI_COLLECTIONS_DIR+x}" ] || MIOS_SRV_AI_COLLECTIONS_DIR="${MIOS_SRV_AI_DIR}"'/collections'
[ -n "${MIOS_SRV_AI_MCP_DIR+x}" ] || MIOS_SRV_AI_MCP_DIR="${MIOS_SRV_AI_DIR}"'/mcp'
[ -n "${MIOS_SRV_AI_MODELS_DIR+x}" ] || MIOS_SRV_AI_MODELS_DIR="${MIOS_SRV_AI_DIR}"'/models'
[ -n "${MIOS_SRV_AI_OUTPUTS_DIR+x}" ] || MIOS_SRV_AI_OUTPUTS_DIR="${MIOS_SRV_AI_DIR}"'/outputs'
: "${MIOS_SSH_HOST:=mios-*}"
: "${MIOS_SSH_IDENTITY_FILE:=~/.ssh/agent_ssh_key}"
: "${MIOS_SSH_KEY_ACTION:=generate}"
: "${MIOS_SSH_PORT:=2222}"
: "${MIOS_SSH_USER:=agent}"
[ -n "${MIOS_SSOT_CONSUMERS_DOC+x}" ] || MIOS_SSOT_CONSUMERS_DOC='Shipped Python reads config as _toml_section("<table>").get("<key>"). When <table>.<key> does not exist the consumer silently takes its compiled default -- the SSOT and the code disagree with nobody told, and every test that stubs the value still passes. Nine security controls sat unreachable this way under an unclosed [security.nohc_allowlist] header (T-325). MISPLACED means the key name is declared elsewhere in the SSOT, so one side has the wrong path; UNDECLARED means it exists nowhere, so it is an optional escape hatch or a dead read. Draining an entry: decide which side is right, move the key or fix the consumer, then lower max_unresolved. Gate: check_ssot_consumer_keys.'
: "${MIOS_SSOT_CONSUMERS_MAX_UNRESOLVED:=9}"
: "${MIOS_SSOT_CONSUMERS_UNRESOLVED:=a2a.security,agent_passport.principal_mode,ai.micro_endpoint,ai.micro_model,ai.permission_tiers,computer_use.hidpi_scale_factor,pgvector.memguard_judge_mode,pgvector.memory_guard_mode,pgvector.memory_provider}"
: "${MIOS_STACK_ID_PORT:=0}"
: "${MIOS_STACK_MODEL:=granite4.1:8b}"
: "${MIOS_STORAGE_CEPHFS_AUTOMOUNT_ENABLE:=true}"
: "${MIOS_STORAGE_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S:=600}"
: "${MIOS_STORAGE_CEPHFS_CLIENT_CACHE_SIZE:=16384}"
: "${MIOS_STORAGE_CEPHFS_CLIENT_READAHEAD_MAX_BYTES:=33554432}"
: "${MIOS_STORAGE_CEPHFS_CLIENT_RECONNECT_STALE_INTERVAL:=30}"
: "${MIOS_STORAGE_CEPHFS_CLUSTER_NAME:=ceph}"
: "${MIOS_STORAGE_CEPHFS_DATA_POOL_BULK:=cephfs_data_bulk}"
: "${MIOS_STORAGE_CEPHFS_DATA_POOL_HOT:=cephfs_data_hot}"
: "${MIOS_STORAGE_CEPHFS_ENABLE:=false}"
: "${MIOS_STORAGE_CEPHFS_FS_NAME:=cephfs}"
: "${MIOS_STORAGE_CEPHFS_KEYRING_DIR:=/etc/ceph/keyring.d}"
: "${MIOS_STORAGE_CEPHFS_MDS_CACHE_MEMORY_LIMIT_GIB:=4}"
: "${MIOS_STORAGE_CEPHFS_MDS_SESSION_CAP_MAX:=1024}"
: "${MIOS_STORAGE_CEPHFS_METADATA_POOL:=cephfs_metadata}"
: "${MIOS_STORAGE_CEPHFS_MONITORS:=127.0.0.1:6789}"
: "${MIOS_STORAGE_CEPHFS_MOUNT_OPTIONS:=noatime,fsc,_netdev}"
: "${MIOS_STORAGE_CEPHFS_PROVISION_SCRIPT:=/usr/libexec/mios/mios-cephfs-provision}"
: "${MIOS_STORAGE_CEPHFS_SUBVOLUME_MODE:=0700}"
: "${MIOS_STORAGE_CEPHFS_TENANT_ID:=mios}"
[ -n "${MIOS_STORAGE_CEPHFS_XDG_CACHE_HOME_OVERRIDE+x}" ] || MIOS_STORAGE_CEPHFS_XDG_CACHE_HOME_OVERRIDE='/run/user/{uid}/.cache'
: "${MIOS_SYS_IMAGE:=localhost/mios-sys:latest}"
: "${MIOS_SYS_VERSION:=localhost/mios-sys:latest}"
: "${MIOS_TEMPLATES_ADR_COMMENT:=md}"
: "${MIOS_TEMPLATES_ADR_DEST_DIR:=usr/share/doc/mios/adr}"
: "${MIOS_TEMPLATES_ADR_EMIT:=file}"
: "${MIOS_TEMPLATES_ADR_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_ADR_MATCH+x}" ] || MIOS_TEMPLATES_ADR_MATCH='^usr/share/doc/mios/adr/\d{4}-.*\.md$'
: "${MIOS_TEMPLATES_ADR_NAME_PREFIX:=0012-}"
: "${MIOS_TEMPLATES_ADR_NAME_SUFFIX:=.md}"
: "${MIOS_TEMPLATES_ADR_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_ADR_REQUIRED_MARKERS:=## Status,## Context,## Decision,## Rationale,## Consequences}"
: "${MIOS_TEMPLATES_ADR_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_AUTOMATION_STEP_COMMENT:=hash}"
: "${MIOS_TEMPLATES_AUTOMATION_STEP_DEST_DIR:=automation}"
: "${MIOS_TEMPLATES_AUTOMATION_STEP_EMIT:=file}"
: "${MIOS_TEMPLATES_AUTOMATION_STEP_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_AUTOMATION_STEP_MATCH+x}" ] || MIOS_TEMPLATES_AUTOMATION_STEP_MATCH='^automation/\d{2}-.*\.sh$'
: "${MIOS_TEMPLATES_AUTOMATION_STEP_NAME_PREFIX:=99-}"
: "${MIOS_TEMPLATES_AUTOMATION_STEP_NAME_SUFFIX:=.sh}"
: "${MIOS_TEMPLATES_AUTOMATION_STEP_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_AUTOMATION_STEP_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_BASH_COMMENT:=hash}"
: "${MIOS_TEMPLATES_BASH_DEST_DIR:=usr/libexec/mios}"
: "${MIOS_TEMPLATES_BASH_EMIT:=file}"
: "${MIOS_TEMPLATES_BASH_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_BASH_MATCH+x}" ] || MIOS_TEMPLATES_BASH_MATCH='^(?:tools/|usr/bin/|usr/libexec/mios/|automation/)[\w./-]+\.sh$'
: "${MIOS_TEMPLATES_BASH_NAME_SUFFIX:=.sh}"
: "${MIOS_TEMPLATES_BASH_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_BASH_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_BASH_TOOL_COMMENT:=hash}"
: "${MIOS_TEMPLATES_BASH_TOOL_DEST_DIR:=usr/libexec/mios}"
: "${MIOS_TEMPLATES_BASH_TOOL_EMIT:=file}"
: "${MIOS_TEMPLATES_BASH_TOOL_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_BASH_TOOL_MATCH+x}" ] || MIOS_TEMPLATES_BASH_TOOL_MATCH='^usr/libexec/mios/mios-[\w-]+$|^usr/bin/[\w-]+$'
: "${MIOS_TEMPLATES_BASH_TOOL_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_BASH_TOOL_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_BASH_TOOL_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_BASH_VERB_COMMENT:=hash}"
: "${MIOS_TEMPLATES_BASH_VERB_DEST_DIR:=usr/libexec/mios}"
: "${MIOS_TEMPLATES_BASH_VERB_EMIT:=file}"
: "${MIOS_TEMPLATES_BASH_VERB_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_BASH_VERB_MATCH+x}" ] || MIOS_TEMPLATES_BASH_VERB_MATCH='^usr/libexec/mios/mios-[\w-]+\.sh$'
: "${MIOS_TEMPLATES_BASH_VERB_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_BASH_VERB_NAME_SUFFIX:=.sh}"
: "${MIOS_TEMPLATES_BASH_VERB_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_BASH_VERB_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_CARGO_MANIFEST_COMMENT:=hash}"
: "${MIOS_TEMPLATES_CARGO_MANIFEST_DEST_DIR:=tools/native}"
: "${MIOS_TEMPLATES_CARGO_MANIFEST_EMIT:=file}"
: "${MIOS_TEMPLATES_CARGO_MANIFEST_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_CARGO_MANIFEST_MATCH+x}" ] || MIOS_TEMPLATES_CARGO_MANIFEST_MATCH='^tools/native/[\w-]+/Cargo\.toml$'
: "${MIOS_TEMPLATES_CARGO_MANIFEST_NAME_SUFFIX:=/Cargo.toml}"
: "${MIOS_TEMPLATES_CARGO_MANIFEST_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_CARGO_MANIFEST_REQUIRED_MARKERS:=[package],name =,version.workspace = true}"
: "${MIOS_TEMPLATES_CARGO_MANIFEST_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_DRIFT_CHECK_COMMENT:=hash}"
: "${MIOS_TEMPLATES_DRIFT_CHECK_EMIT:=stdout}"
: "${MIOS_TEMPLATES_DRIFT_CHECK_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_DRIFT_CHECK_MATCH+x}" ] || MIOS_TEMPLATES_DRIFT_CHECK_MATCH='^automation/98-drift-checks\.sh$'
: "${MIOS_TEMPLATES_DRIFT_CHECK_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_DRIFT_CHECK_REQUIRED_MARKERS:=check_}"
: "${MIOS_TEMPLATES_DRIFT_CHECK_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_JSON_SCHEMA_COMMENT:=hash}"
: "${MIOS_TEMPLATES_JSON_SCHEMA_DEST_DIR:=usr/share/mios}"
: "${MIOS_TEMPLATES_JSON_SCHEMA_EMIT:=file}"
: "${MIOS_TEMPLATES_JSON_SCHEMA_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_JSON_SCHEMA_MATCH+x}" ] || MIOS_TEMPLATES_JSON_SCHEMA_MATCH='^[\w./-]+\.json$'
: "${MIOS_TEMPLATES_JSON_SCHEMA_NAME_SUFFIX:=.json}"
: "${MIOS_TEMPLATES_JSON_SCHEMA_REQUIRED_HEADER:=false}"
: "${MIOS_TEMPLATES_JSON_SCHEMA_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_MARKDOWN_DOC_COMMENT:=md}"
: "${MIOS_TEMPLATES_MARKDOWN_DOC_DEST_DIR:=usr/share/doc/mios}"
: "${MIOS_TEMPLATES_MARKDOWN_DOC_EMIT:=file}"
: "${MIOS_TEMPLATES_MARKDOWN_DOC_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_MARKDOWN_DOC_MATCH+x}" ] || MIOS_TEMPLATES_MARKDOWN_DOC_MATCH='^usr/share/doc/mios/[\w./-]+\.md$|^README\.md$'
: "${MIOS_TEMPLATES_MARKDOWN_DOC_NAME_SUFFIX:=.md}"
: "${MIOS_TEMPLATES_MARKDOWN_DOC_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_MARKDOWN_DOC_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_DATE:=2026-07-17}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_DESCRIPTION:=Mock Description}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_FILENAME:=mockname.py}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_GID:=1000}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_ID:=9999}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_IMAGE:=mock-image:latest}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_NAME:=mockname}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_PASCALNAME:=MockName}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_PATH:=usr/lib/mios/agent-pipe/mios_pipe/mockname.py}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_PRIORITY:=P1}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_STATUS:=proposed}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_TASK_ID:=8888}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_TASK_TITLE:=Mock Task Title}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_THEME:=Mock Theme}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_TITLE:=Mock Title}"
: "${MIOS_TEMPLATES_PLACEHOLDERS_UID:=1000}"
: "${MIOS_TEMPLATES_POWERSHELL_COMMENT:=hash}"
: "${MIOS_TEMPLATES_POWERSHELL_DEST_DIR:=tools}"
: "${MIOS_TEMPLATES_POWERSHELL_EMIT:=file}"
: "${MIOS_TEMPLATES_POWERSHELL_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_POWERSHELL_MATCH+x}" ] || MIOS_TEMPLATES_POWERSHELL_MATCH='^[\w./-]+\.ps1$'
: "${MIOS_TEMPLATES_POWERSHELL_NAME_SUFFIX:=.ps1}"
: "${MIOS_TEMPLATES_POWERSHELL_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_POWERSHELL_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_PYTHON_MODULE_COMMENT:=hash}"
: "${MIOS_TEMPLATES_PYTHON_MODULE_DEST_DIR:=usr/lib/mios/agent-pipe/mios_pipe}"
: "${MIOS_TEMPLATES_PYTHON_MODULE_EMIT:=file}"
: "${MIOS_TEMPLATES_PYTHON_MODULE_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_PYTHON_MODULE_MATCH+x}" ] || MIOS_TEMPLATES_PYTHON_MODULE_MATCH='^usr/lib/mios/agent-pipe/mios_pipe/[\w-]+\.py$'
: "${MIOS_TEMPLATES_PYTHON_MODULE_NAME_SUFFIX:=.py}"
: "${MIOS_TEMPLATES_PYTHON_MODULE_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_PYTHON_MODULE_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_PYTHON_TEST_COMMENT:=hash}"
: "${MIOS_TEMPLATES_PYTHON_TEST_DEST_DIR:=usr/lib/mios/agent-pipe}"
: "${MIOS_TEMPLATES_PYTHON_TEST_EMIT:=file}"
: "${MIOS_TEMPLATES_PYTHON_TEST_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_PYTHON_TEST_MATCH+x}" ] || MIOS_TEMPLATES_PYTHON_TEST_MATCH='^usr/lib/mios/agent-pipe/test_mios_[\w-]+\.py$'
: "${MIOS_TEMPLATES_PYTHON_TEST_NAME_PREFIX:=test_mios_}"
: "${MIOS_TEMPLATES_PYTHON_TEST_NAME_SUFFIX:=.py}"
: "${MIOS_TEMPLATES_PYTHON_TEST_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_PYTHON_TEST_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_PYTHON_TOOL_COMMENT:=hash}"
: "${MIOS_TEMPLATES_PYTHON_TOOL_DEST_DIR:=usr/libexec/mios}"
: "${MIOS_TEMPLATES_PYTHON_TOOL_EMIT:=file}"
: "${MIOS_TEMPLATES_PYTHON_TOOL_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_PYTHON_TOOL_MATCH+x}" ] || MIOS_TEMPLATES_PYTHON_TOOL_MATCH='^usr/libexec/mios/mios-[\w-]+\.py$'
: "${MIOS_TEMPLATES_PYTHON_TOOL_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_PYTHON_TOOL_NAME_SUFFIX:=.py}"
: "${MIOS_TEMPLATES_PYTHON_TOOL_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_PYTHON_TOOL_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_QUADLET_COMMENT:=hash}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_COMMENT:=hash}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_DEST_DIR:=usr/share/containers/systemd}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_EMIT:=file}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_GENERATED:=true}"
[ -n "${MIOS_TEMPLATES_QUADLET_CONTAINER_MATCH+x}" ] || MIOS_TEMPLATES_QUADLET_CONTAINER_MATCH='^usr/share/containers/systemd/[\w-]+\.container$'
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_NAME_SUFFIX:=.container}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_REQUIRED_MARKERS:=[Unit],[Container],[Install]}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_REQUIRED_ORDERED:=[Unit],[Container],[Install]}"
: "${MIOS_TEMPLATES_QUADLET_CONTAINER_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_QUADLET_DEST_DIR:=usr/share/containers/systemd}"
: "${MIOS_TEMPLATES_QUADLET_EMIT:=file}"
: "${MIOS_TEMPLATES_QUADLET_GENERATED:=true}"
[ -n "${MIOS_TEMPLATES_QUADLET_MATCH+x}" ] || MIOS_TEMPLATES_QUADLET_MATCH='^usr/share/containers/systemd/[\w-]+\.(?:container|pod|network|volume|image)$'
: "${MIOS_TEMPLATES_QUADLET_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_QUADLET_NAME_SUFFIX:=.container}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_COMMENT:=hash}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_DEST_DIR:=usr/share/containers/systemd}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_EMIT:=file}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_GENERATED:=true}"
[ -n "${MIOS_TEMPLATES_QUADLET_NETWORK_MATCH+x}" ] || MIOS_TEMPLATES_QUADLET_NETWORK_MATCH='^usr/share/containers/systemd/[\w-]+\.network$'
: "${MIOS_TEMPLATES_QUADLET_NETWORK_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_NAME_SUFFIX:=.network}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_REQUIRED_MARKERS:=[Unit],[Network],[Install]}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_REQUIRED_ORDERED:=[Unit],[Network],[Install]}"
: "${MIOS_TEMPLATES_QUADLET_NETWORK_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_QUADLET_POD_COMMENT:=hash}"
: "${MIOS_TEMPLATES_QUADLET_POD_DEST_DIR:=usr/share/containers/systemd}"
: "${MIOS_TEMPLATES_QUADLET_POD_EMIT:=file}"
: "${MIOS_TEMPLATES_QUADLET_POD_GENERATED:=true}"
[ -n "${MIOS_TEMPLATES_QUADLET_POD_MATCH+x}" ] || MIOS_TEMPLATES_QUADLET_POD_MATCH='^usr/share/containers/systemd/[\w-]+\.pod$'
: "${MIOS_TEMPLATES_QUADLET_POD_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_QUADLET_POD_NAME_SUFFIX:=.pod}"
: "${MIOS_TEMPLATES_QUADLET_POD_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_QUADLET_POD_REQUIRED_MARKERS:=[Unit],[Pod],[Install]}"
: "${MIOS_TEMPLATES_QUADLET_POD_REQUIRED_ORDERED:=[Unit],[Pod],[Install]}"
: "${MIOS_TEMPLATES_QUADLET_POD_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_QUADLET_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_QUADLET_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_COMMENT:=hash}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_DEST_DIR:=usr/share/containers/systemd}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_EMIT:=file}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_GENERATED:=true}"
[ -n "${MIOS_TEMPLATES_QUADLET_VOLUME_MATCH+x}" ] || MIOS_TEMPLATES_QUADLET_VOLUME_MATCH='^usr/share/containers/systemd/[\w-]+\.volume$'
: "${MIOS_TEMPLATES_QUADLET_VOLUME_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_NAME_SUFFIX:=.volume}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_REQUIRED_MARKERS:=[Unit],[Volume],[Install]}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_REQUIRED_ORDERED:=[Unit],[Volume],[Install]}"
: "${MIOS_TEMPLATES_QUADLET_VOLUME_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_ROADMAP_COMMENT:=md}"
: "${MIOS_TEMPLATES_ROADMAP_DEST_DIR:=.}"
: "${MIOS_TEMPLATES_ROADMAP_EMIT:=file}"
: "${MIOS_TEMPLATES_ROADMAP_FIXED_NAME:=ROADMAP.md}"
: "${MIOS_TEMPLATES_ROADMAP_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_ROADMAP_MATCH+x}" ] || MIOS_TEMPLATES_ROADMAP_MATCH='^ROADMAP\.md$'
: "${MIOS_TEMPLATES_ROADMAP_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_ROADMAP_REQUIRED_MARKERS:=### Workstream Status Rollup,# Desktop & UX,# Fleet & Federation}"
: "${MIOS_TEMPLATES_ROADMAP_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_ROADMAP_WS_COMMENT:=md}"
: "${MIOS_TEMPLATES_ROADMAP_WS_DEST_DIR:=usr/share/doc/mios/roadmap}"
: "${MIOS_TEMPLATES_ROADMAP_WS_EMIT:=file}"
: "${MIOS_TEMPLATES_ROADMAP_WS_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_ROADMAP_WS_MATCH+x}" ] || MIOS_TEMPLATES_ROADMAP_WS_MATCH='^usr/share/doc/mios/roadmap/[\w-]+\.md$'
: "${MIOS_TEMPLATES_ROADMAP_WS_NAME_SUFFIX:=.md}"
: "${MIOS_TEMPLATES_ROADMAP_WS_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_ROADMAP_WS_REQUIRED_MARKERS:=## WS-,acceptance:}"
: "${MIOS_TEMPLATES_ROADMAP_WS_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_RUST_COMMENT:=slash}"
: "${MIOS_TEMPLATES_RUST_DEST_DIR:=tools/native}"
: "${MIOS_TEMPLATES_RUST_EMIT:=file}"
: "${MIOS_TEMPLATES_RUST_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_RUST_MATCH+x}" ] || MIOS_TEMPLATES_RUST_MATCH='^tools/native/[\w./-]+\.rs$|^src/mios-rs/[\w./-]+\.rs$'
: "${MIOS_TEMPLATES_RUST_NAME_SUFFIX:=.rs}"
: "${MIOS_TEMPLATES_RUST_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_RUST_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_COMMENT:=hash}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_DEST_DIR:=usr/lib/systemd/system}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_EMIT:=file}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_SYSTEMD_TIMER_MATCH+x}" ] || MIOS_TEMPLATES_SYSTEMD_TIMER_MATCH='^usr/lib/systemd/system/[\w-]+\.timer$'
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_NAME_SUFFIX:=.timer}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_REQUIRED_MARKERS:=[Unit],[Timer],[Install]}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_REQUIRED_ORDERED:=[Unit],[Timer],[Install]}"
: "${MIOS_TEMPLATES_SYSTEMD_TIMER_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_COMMENT:=hash}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_DEST_DIR:=usr/lib/systemd/system}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_EMIT:=file}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_SYSTEMD_UNIT_MATCH+x}" ] || MIOS_TEMPLATES_SYSTEMD_UNIT_MATCH='^usr/lib/systemd/system/[\w-]+\.service$'
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_NAME_PREFIX:=mios-}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_NAME_SUFFIX:=.service}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_REQUIRED_MARKERS:=[Unit],[Service],[Install]}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_REQUIRED_ORDERED:=[Unit],[Service],[Install]}"
: "${MIOS_TEMPLATES_SYSTEMD_UNIT_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_TOML_CONFIG_COMMENT:=hash}"
: "${MIOS_TEMPLATES_TOML_CONFIG_DEST_DIR:=usr/share/mios}"
: "${MIOS_TEMPLATES_TOML_CONFIG_EMIT:=file}"
: "${MIOS_TEMPLATES_TOML_CONFIG_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_TOML_CONFIG_MATCH+x}" ] || MIOS_TEMPLATES_TOML_CONFIG_MATCH='^[\w./-]+\.toml$'
: "${MIOS_TEMPLATES_TOML_CONFIG_NAME_SUFFIX:=.toml}"
: "${MIOS_TEMPLATES_TOML_CONFIG_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_TOML_CONFIG_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_TYPESCRIPT_COMMENT:=slash}"
: "${MIOS_TEMPLATES_TYPESCRIPT_DEST_DIR:=tools}"
: "${MIOS_TEMPLATES_TYPESCRIPT_EMIT:=file}"
: "${MIOS_TEMPLATES_TYPESCRIPT_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_TYPESCRIPT_MATCH+x}" ] || MIOS_TEMPLATES_TYPESCRIPT_MATCH='^[\w./-]+\.ts$'
: "${MIOS_TEMPLATES_TYPESCRIPT_NAME_SUFFIX:=.ts}"
: "${MIOS_TEMPLATES_TYPESCRIPT_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_TYPESCRIPT_SCAFFOLD:=true}"
: "${MIOS_TEMPLATES_YAML_COMMENT:=hash}"
: "${MIOS_TEMPLATES_YAML_DEST_DIR:=usr/share/mios}"
: "${MIOS_TEMPLATES_YAML_EMIT:=file}"
: "${MIOS_TEMPLATES_YAML_GENERATED:=false}"
[ -n "${MIOS_TEMPLATES_YAML_MATCH+x}" ] || MIOS_TEMPLATES_YAML_MATCH='^[\w./-]+\.yaml$|^[\w./-]+\.yml$'
: "${MIOS_TEMPLATES_YAML_NAME_SUFFIX:=.yaml}"
: "${MIOS_TEMPLATES_YAML_REQUIRED_HEADER:=true}"
: "${MIOS_TEMPLATES_YAML_SCAFFOLD:=true}"
: "${MIOS_TERMINAL_COLS:=80}"
: "${MIOS_TERMINAL_FRAME_HEIGHT:=19}"
: "${MIOS_TERMINAL_FRAME_WIDTH:=80}"
: "${MIOS_TERMINAL_GUI_MIN_HEIGHT:=1000}"
: "${MIOS_TERMINAL_GUI_MIN_WIDTH:=1600}"
: "${MIOS_TERMINAL_INSTALL_COLS:=80}"
: "${MIOS_TERMINAL_INSTALL_ROWS:=40}"
: "${MIOS_TERMINAL_READING_COLS:=100}"
: "${MIOS_TERMINAL_READING_ROWS:=50}"
: "${MIOS_TERMINAL_RIGHT_MARGIN:=0}"
: "${MIOS_TERMINAL_ROWS:=20}"
: "${MIOS_TERMINAL_SCROLLBACK_ROWS:=9000}"
: "${MIOS_TESTING_NEGATIVE_COVERAGE_EXEMPT_EXEMPT:=check_ps_repo_parity,check_ps_signatures,check_native_lint,check_resolver_ps_equivalence,check_resolver_shell_equivalence,check_template_self_conformance,check_templates_bootstrap_sync,check_agent_schema,check_ai_manifest,check_bib_rootfs_label_policy,check_blade_dropins,check_bootstrap_ports_drift,check_canonical_bools,check_capability_manifest,check_cephfs_ssot,check_cli_sql_safety,check_container_ports,check_converge_ssot,check_coordination_hygiene,check_dag_integrity,check_dotfiles_projection,check_drift_build_catalog,check_drift_projection,check_egress_firewall,check_etc_duplicates,check_fluff_tokens,check_gate_index,check_globals_image_parity,check_globals_ports,check_greenboot,check_greenboot_enablement,check_hint_coverage,check_hummingbird,check_kargs_projection,check_module_boundary,check_negative_test_coverage,check_no_bare_port_literals,check_no_hardcode,check_package_registry,check_pod_quadlets,check_python_lint,check_raw_toml_readers,check_rbac_tiers,check_resolver_twin_parity,check_retired_models,check_structured,check_surface_parity,check_template_conformance,check_unwired_modules,check_userenv_parity,check_unit_security,check_var_closure,check_vendor_urls,check_verb_backends}"
: "${MIOS_TESTING_SMOKE_COMPONENTS_PYTHON_ENTRIES:=usr/lib/mios/agent-pipe/server.py}"
: "${MIOS_TESTING_SMOKE_COMPONENTS_SHIMS:=usr/libexec/mios/flatpak-launch,usr/libexec/mios/mios-pc-control,usr/libexec/mios/mios-launcher-daemon,usr/libexec/mios/mios-flatpak-icon-sanitize}"
: "${MIOS_TESTING_SMOKE_COMPONENTS_UNITS:=usr/lib/systemd/system/mios-wsl-interop-priority.service}"
: "${MIOS_TIMEZONE:=UTC}"
: "${MIOS_TOKENIZER_BACKEND:=tiktoken}"
: "${MIOS_TOKENIZER_CACHE_DIR:=/usr/share/mios/tiktoken}"
: "${MIOS_TOKENIZER_ENCODING:=cl100k_base}"
: "${MIOS_TOML:=/usr/share/mios/mios.toml}"
[ -n "${MIOS_TOML_HOST+x}" ] || MIOS_TOML_HOST="${MIOS_ETC_DIR}"'/mios.toml'
[ -n "${MIOS_TOML_VENDOR+x}" ] || MIOS_TOML_VENDOR="${MIOS_SHARE_DIR}"'/mios.toml'
: "${MIOS_TTYD_BASH_PORT:=8310}"
: "${MIOS_TTYD_BIND:=127.0.0.1}"
: "${MIOS_TTYD_ENABLE:=true}"
: "${MIOS_TTYD_FONT_SIZE:=14}"
: "${MIOS_TTYD_MAX_CLIENTS:=0}"
: "${MIOS_TTYD_POWERSHELL_PORT:=8320}"
: "${MIOS_TTYD_REQUIRE_AUTH:=true}"
: "${MIOS_TTYD_TAILNET_EXPOSE:=false}"
: "${MIOS_TTYD_WRITABLE:=true}"
: "${MIOS_UKI_VERITY_BUILD:=false}"
: "${MIOS_UKI_VERITY_UKI_BUILD:=false}"
: "${MIOS_UNBOUND_PORT:=chrome_cdp_worker}"
: "${MIOS_UNITS_AGENT_PIPE:=mios-agent-pipe.service}"
: "${MIOS_UNITS_CEPH:=mios-ceph.service}"
: "${MIOS_UNITS_COCKPIT_LINK:=mios-cockpit-link.service}"
: "${MIOS_UNITS_CODE_SERVER:=mios-code-server.service}"
: "${MIOS_UNITS_FIRSTBOOT_TARGET:=mios-firstboot.target}"
: "${MIOS_UNITS_FORGE:=mios-forge.service}"
: "${MIOS_UNITS_FORGE_RUNNER:=mios-forgejo-runner.service}"
: "${MIOS_UNITS_HERMES:=mios-hermes.service}"
: "${MIOS_UNITS_HERMES_FIRSTBOOT:=mios-hermes-firstboot.service}"
: "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/hermes-worker-firstboot}"
: "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_AFTER:=local-fs.target systemd-tmpfiles-setup.service}"
: "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_BEFORE:=hermes-worker.service multi-user.target}"
[ -n "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Oneshot that seeds the non-thin Hermes WORKER config (/var/lib/mios/hermes-worker/config.yaml) from the vendor template before hermes-worker.service starts. Distinct from mios-hermes-firstboot (which owns and re-thins the primary :8642 config); this one NEVER touches the primary path.
# AI-related: /usr/libexec/mios/hermes-worker-firstboot, /usr/share/mios/hermes/config-worker.yaml, /var/lib/mios/hermes-worker/config.yaml, hermes-worker.service'
: "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/hermes-worker-firstboot}"
[ -n "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Worker first-boot config seed (:8643 non-thin worker)'
: "${MIOS_UNITS_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS}"
: "${MIOS_UNITS_HERMES_WORKER_PATH_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_HERMES_WORKER_PATH_PATH_PATHEXISTS:=/usr/lib/mios/agents/.venv/bin/hermes}"
: "${MIOS_UNITS_HERMES_WORKER_PATH_PATH_UNIT:=hermes-worker.service}"
: "${MIOS_UNITS_HERMES_WORKER_PATH_UNIT_AFTER:=hermes-worker-firstboot.service}"
[ -n "${MIOS_UNITS_HERMES_WORKER_PATH_UNIT_COMMENT+x}" ] || MIOS_UNITS_HERMES_WORKER_PATH_UNIT_COMMENT='# AI-hint: Systemd path unit (WS-A4 boot-ordering fix) that watches for the Hermes venv binary and (re)starts hermes-worker.service once it exists, so a worker that failed its ConditionPathExists at first boot (venv not yet built) comes up automatically when the venv lands -- instead of staying inactive until a manual restart.
# AI-related: hermes-worker.service, hermes-worker-firstboot.service, /usr/lib/mios/agents/.venv/bin/hermes, multi-user.target, 90-mios.preset
# /usr/lib/systemd/system/hermes-worker.path
# WS-A4 (operator 2026-06-22): hermes-worker.service carries
# ConditionPathExists=/usr/lib/mios/agents/.venv/bin/hermes. On a fresh boot the
# venv is not built yet -> the Condition fails -> the worker is skipped, and once
# the venv-build/firstboot finishes systemd never retries it (so :8643 stays
# inactive forever and the orchestrator silently runs single-agent). This .path
# closes that gap: PathExists is satisfied the moment the venv binary EXISTS
# (on creation AND if already present at activation), starting the worker. The
# worker'"'"'s own Condition still guards against a half-built venv; start is idempotent.'
[ -n "${MIOS_UNITS_HERMES_WORKER_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_HERMES_WORKER_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"' watch for the Hermes venv -> (re)start hermes-worker'
: "${MIOS_UNITS_HERMES_WORKER_PATH_UNIT_DOCUMENTATION:=file:///usr/lib/systemd/system/hermes-worker.service}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_COMMENT='# SEPARATE HERMES_HOME + HOME => fully isolated pid/lock/state/DBs/config AND a
# distinct $HOME/XDG so the discord scope-lock dir (derived from $HOME) can
# never collide with the :8642 gateway'"'"'s. Discord is off here regardless.'
[ -n "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_ENVIRONMENT='HOME=/var/lib/mios/hermes-worker,HERMES_HOME=/var/lib/mios/hermes-worker,SEARXNG_URL=http://localhost:'"${MIOS_PORT_SEARXNG}"',MIOS_CRAWL_SERVICE_URL=http://127.0.0.1:'"${MIOS_PORT_CRAWL4AI}"',FIRECRAWL_API_URL=http://127.0.0.1:'"${MIOS_PORT_FIRECRAWL}"',PORT='"${MIOS_PORT_HERMES}"',API_SERVER_PORT='"${MIOS_PORT_HERMES}"',HERMES_BACKEND_BASE_URL=http://localhost:'"${MIOS_PORT_VLLM}"',HERMES_MAX_TOKENS=8192,BROWSER_CDP_URL=http://localhost:${MIOS_PORT_CHROME_CDP_WORKER:-9223}'
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env,-/etc/mios/hermes/api.env}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_EXECSTART:=/usr/lib/mios/agents/.venv/bin/hermes gateway run}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_EXECSTARTPRE:=+/usr/bin/install -d -o mios-ai -g mios-ai -m 0700 /var/lib/mios/hermes-worker,-/usr/bin/python3 /usr/libexec/mios/mios-hermes-discord-reactions-patch /usr/lib/mios/agents/.venv/lib/python3.14/site-packages/gateway/platforms/discord.py,-+/usr/libexec/mios/mios-hermes-dashboard-auth-stub}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_LIMITNOFILE:=1048576}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_NONEWPRIVILEGES:=false}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_PRIVATETMP:=yes}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_PROTECTHOME:=false}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_READWRITEPATHS:=/etc/mios /var/lib/mios /run/mios-launcher}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_RESTARTSEC:=10s}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_TIMEOUTSTARTSEC:=300s}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_TIMEOUTSTOPSEC:=240s}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_AFTER:=network-online.target mios-llm-heavy.service mios-llm-light.service hermes-worker-firstboot.service}"
[ -n "${MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit for the SECOND (non-thin) Hermes WORKER gateway on :8643 -- a real agent that runs its OWN native browser/CDP/terminal/skills tool loop with its OWN inference on the heavy lane (:11441 mios-heavy). Coexists with the thin :8642 Discord gateway (hermes-agent.service) via a SEPARATE HERMES_HOME and no Discord token.
# AI-related: /usr/lib/mios/agents/.venv/bin/hermes, /var/lib/mios/hermes-worker, /var/lib/mios/hermes-worker/config.yaml, /etc/mios/hermes/api.env, hermes-agent.service, mios-hermes-browser-worker.service, mios-llm-heavy.service, mios-llm-light.service
# /usr/lib/systemd/system/hermes-worker.service
#
# The MiOS Hermes WORKER (P1, operator 2026-06-19). A SECOND `hermes gateway
# run` instance, fully ISOLATED from the live :8642 Discord gateway:
#   * SEPARATE HERMES_HOME=/var/lib/mios/hermes-worker => its own gateway.pid /
#     gateway.lock / gateway_state.json / state.db / kanban.db / config.yaml.
#     No shared-DB WAL contention with the :8642 instance.
#   * API_SERVER_PORT=8643 (the LOAD-BEARING bind var -- `PORT` is inert; Hermes
#     reads API_SERVER_PORT and otherwise binds DEFAULT_PORT=8642).
#   * NO discord.env / NO DISCORD_BOT_TOKEN => the Discord adapter never calls
#     _acquire_platform_lock('"'"'discord-bot-token'"'"', ...), so the host-global
#     gateway-locks/discord-bot-token-*.lock held by the :8642 gateway is never
#     contended (no SIGTERM flap). Discord stays the EXCLUSIVE job of :8642.
#   * NO --replace: the worker'"'"'s HERMES_HOME-scoped pidfile is its own; the
#     :8642 gateway'"'"'s eviction scan is profile/HERMES_HOME-scoped (only --all
#     crosses profiles, which is not used) so neither instance touches the other.
#
# This worker is the WORKER-DISPATCH target of [agents.hermes].endpoint in
# mios.toml (repointed :11441 -> :8643 in P1). It does its OWN heavy-lane
# inference (:11441 mios-heavy) so it never relays to :8640 -- no recursion.'
[ -n "${MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_COMMENT2='# R8: dropped After=mios-ai-firstboot.service -- the worker rides the venv + its own
# provisioner (hermes-worker-firstboot) + the inference lanes, NOT the boot-time
# GGUF/vLLM fetch owned by mios-ai-firstboot.'
[ -n "${MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_COMMENT3+x}" ] || MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_COMMENT3='# Skip cleanly if the direct install didn'"'"'t land.'
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/lib/mios/agents/.venv/bin/hermes}"
[ -n "${MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Worker (non-thin agent, native tool loop, :8643)'
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_DOCUMENTATION:=https://github.com/NousResearch/hermes-agent}"
: "${MIOS_UNITS_HERMES_WORKER_SERVICE_UNIT_WANTS:=network-online.target mios-llm-heavy.service mios-llm-light.service hermes-worker-firstboot.service}"
: "${MIOS_UNITS_K3S:=mios-k3s.service}"
: "${MIOS_UNITS_LLM_LIGHT:=mios-llm-light.service}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_COMMENT:=# Ensure postgres container is ready before launching the daemon}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-account-sync --daemon}"
[ -n "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_EXECSTARTPRE+x}" ] || MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_EXECSTARTPRE='/usr/bin/podman exec mios-pgvector pg_isready -q -h 127.0.0.1 -p ${MIOS_PORT_PGVECTOR:-8600} -U mios -d mios'
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_RESTART:=always}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_RESTARTSEC:=10s}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_AFTER:=mios-pgvector.service}"
[ -n "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/mios-account-sync in daemon mode to keep local Linux accounts synchronized with PostgreSQL accounts and aliases.
# AI-related: /usr/libexec/mios/mios-account-sync, mios-pgvector.service'
[ -n "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' live PostgreSQL-to-OS user account sync daemon'
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-account-sync}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_REQUIRES:=mios-pgvector.service}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_STARTLIMITBURST:=5}"
: "${MIOS_UNITS_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_STARTLIMITINTERVALSEC:=300}"
: "${MIOS_UNITS_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_PATH_PATHCHANGED:=/usr/lib/containers/storage/overlay-images,/usr/lib/containers/storage/overlay-containers,/usr/lib/containers/storage/overlay-layers,/usr/lib/containers/storage/libpod}"
: "${MIOS_UNITS_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_PATH_UNIT:=mios-additionalimagestores-perms.service}"
[ -n "${MIOS_UNITS_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_COMMENT='# AI-hint: Systemd path unit that monitors container storage directories for permission changes and triggers mios-additionalimagestores-perms.service to restore go+rX permissions on image store subdirectories.
# AI-related: mios-additionalimagestores-perms, mios-additionalimagestores-perms.service, multi-user.target
# Path-watcher companion to mios-additionalimagestores-perms.service.
# Re-runs the chmod whenever any of the additional image store'"'"'s per-
# driver subdirs change (e.g. podman extracts new layers and resets
# the perms back to 0700 -- happens on first runtime pull into the
# additional store, though that'"'"'s atypical since this store is built
# at OCI bake time and meant to be read-only at runtime).
#
# Together with the .service unit (runs at boot) this makes the
# go+rX state self-healing: any way the perms get reset, they snap
# back within seconds.'
: "${MIOS_UNITS_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_CONDITIONPATHISDIRECTORY:=/usr/lib/containers/storage}"
[ -n "${MIOS_UNITS_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"': watch additionalimagestores for perm changes; retrigger chmod'
: "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-adguard-firstboot}"
: "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target tailscaled.service}"
: "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_BEFORE:=mios-adguard.service}"
[ -n "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/mios-adguard-firstboot to generate the AdGuardHome.yaml config from mios.toml, injecting Tailscale IPs before the AdGuard container starts.
# AI-related: /usr/libexec/mios/mios-adguard-firstboot, /etc/mios/adguard/AdGuardHome.yaml, tailscaled.service, mios-adguard.service, network-online.target
# /usr/lib/systemd/system/mios-adguard-firstboot.service
# Generates /etc/mios/adguard/AdGuardHome.yaml from mios.toml [adguard]/[ports]
# + the live Tailscale IP/MagicDNS suffix, BEFORE the AdGuard container starts.
# Idempotent + non-destructive (skips if the config already exists), so it is
# safe to leave enabled across boots. mios-adguard.container Requires= + After=
# this unit, so it is pulled in automatically; it is also enabled directly for
# fresh installs.'
: "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/mios-adguard-firstboot}"
[ -n "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' AdGuard Home first-boot config generator'
: "${MIOS_UNITS_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_INSTALL_WANTEDBY:=multi-user.target default.target}"
[ -n "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_COMMENT='# systemd does NOT expand bash ${VAR:-default} in ExecStart -- it resolves to
# empty (code-server then dies "Invalid URL"). Set the defaults here; install.env
# (the mios.toml -> env SSOT bridge) overrides them when present. ExecStart uses
# plain ${VAR}.'
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_COMMENT2:=# Build the local super-container image on first deploy (idempotent no-op after).}"
[ -n "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_ENVIRONMENT='MIOS_PORT_CODE_SERVER=${MIOS_PORT_CODE_SERVER:-8900},MIOS_DEFAULT_PASSWORD=mios'
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
[ -n "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_EXECSTART='/usr/sbin/podman run --replace --name mios-agents --network=host --env PASSWORD='"${MIOS_DEFAULT_PASSWORD}"' --env MIOS_A2O_ENGINE=agy --env MIOS_A2O_WORK=/mnt/mios-root --env MIOS_A2O_ORCH_ENGINE='"${MIOS_A2O_ORCH_ENGINE}"' --env MIOS_A2O_ORCH_MODEL='"${MIOS_A2O_ORCH_MODEL}"' --env MIOS_A2O_ORCH_EFFORT='"${MIOS_A2O_ORCH_EFFORT}"' --env MIOS_A2O_LANE_A_ENGINE='"${MIOS_A2O_LANE_A_ENGINE}"' --env MIOS_A2O_LANE_A_MODEL='"${MIOS_A2O_LANE_A_MODEL}"' --env MIOS_A2O_LANE_A_EFFORT='"${MIOS_A2O_LANE_A_EFFORT}"' --env MIOS_A2O_LANE_B_ENGINE='"${MIOS_A2O_LANE_B_ENGINE}"' --env MIOS_A2O_LANE_B_MODEL='"${MIOS_A2O_LANE_B_MODEL}"' --env MIOS_A2O_LANE_B_EFFORT='"${MIOS_A2O_LANE_B_EFFORT}"' --env MIOS_A2O_CLAUDE_EFFORT_FLAG='"${MIOS_A2O_CLAUDE_EFFORT_FLAG}"' --env MIOS_A2O_AGY_EFFORT_FLAG='"${MIOS_A2O_AGY_EFFORT_FLAG}"' --env MIOS_A2O_GEMINI_EFFORT_FLAG='"${MIOS_A2O_GEMINI_EFFORT_FLAG}"' --volume /:/mnt/mios-root:rw,rslave --volume /var/lib/mios/agents:/home/coder:rw localhost/mios-agents:latest --bind-addr 0.0.0.0:8800 /mnt/mios-root'
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_EXECSTARTPRE:=/usr/libexec/mios/mios-agents-firstboot.sh}"
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_EXECSTOP:=/usr/sbin/podman stop -t 10 mios-agents}"
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_RESTARTSEC:=10s}"
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_TIMEOUTSTARTSEC:=1200s}"
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_UNIT_AFTER:=network-online.target podman.socket}"
[ -n "${MIOS_UNITS_MIOS_AGENTS_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_AGENTS_SERVICE_UNIT_COMMENT='# AI-hint: Runs the mios-agents A2O super-container (code-server IDE + tmux war room + Claude CLI + agy/Gemini + the mios-a2o muxer) as a systemd-managed container. ExecStartPre builds the local image if absent; ExecStart runs it every boot on the code-server port MIOS_PORT_CODE_SERVER (mios-agents REPLACES the retired mios-code-server -- one IDE, no duplicate service).
# AI-related: /usr/share/mios/agents/Containerfile, /usr/share/mios/agents/mios-a2o, /usr/libexec/mios/mios-agents-firstboot.sh, /etc/mios/install.env, /var/lib/mios/agents
# /usr/lib/systemd/system/mios-agents.service'
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/share/mios/agents/Containerfile}"
[ -n "${MIOS_UNITS_MIOS_AGENTS_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_AGENTS_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' A2O agents super-container (Claude + agy/Gemini + tmux war room + code-server)'
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_UNIT_DOCUMENTATION:=https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/agents/ACTIVATION.md}"
: "${MIOS_UNITS_MIOS_AGENTS_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_ENVIRONMENT='MIOS_PORT_AGENT_PIPE=${MIOS_PORT_AGENT_PIPE:-8700},MIOS_AGENT_PIPE_BACKEND_LIGHT=1,MIOS_AI_MODEL=granite4.1:8b,MIOS_NO_TOOL_CHOICE_HINTS=11436,MIOS_KV_PAGING_HINTS=11436,11450,MIOS_LLM_API_HINTS=,MIOS_REFINE_TIMEOUT_S=45,MIOS_POLISH_TIMEOUT_S=45,MIOS_REFINE_MAX_TOKENS=1200,MIOS_AGENT_MEMORY_RECALL=1,MIOS_PASSPORT_AGENT_NAME=agent-pipe'
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/agent-pipe.env,-/etc/mios/install.env}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_EXECSTART:=/usr/lib/mios/agents/.venv/bin/python3 -u /usr/lib/mios/agent-pipe/server.py}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_NONEWPRIVILEGES:=yes}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_PRIVATETMP:=yes}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_PROTECTHOME:=yes}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_READONLYPATHS:=/var/lib/mios/agent-passports}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_READWRITEPATHS:=/var/lib/mios/agent-pipe /var/lib/mios/skills /var/log /var/lib/mios/agent-env /var/lib/mios/ai}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_RESTARTSEC:=5s}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_SUPPLEMENTARYGROUPS:=mios-hermes}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_TIMEOUTSTARTSEC:=60s}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_SERVICE_WORKINGDIRECTORY:=/var/lib/mios/agent-pipe}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_AFTER:=network-online.target mios-pgvector.service mios-passport-provision.service}"
[ -n "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit defining the agent-pipe FastAPI service which acts as a router, refiner, and critic for the Hermes gateway, routing inference requests to the llama.cpp light lane (mios-llm-light); the lane port is the single SSOT key [ports].llm_light (MIOS_PORT_LLM_LIGHT), composed in server.py via _LIGHT_BASE.
# AI-related: /usr/lib/mios/agent-pipe/server.py, /etc/mios/install.env, /etc/mios/agent-pipe.env, mios-pgvector, mios-passport-provision, mios-ai, mios-hermes'
[ -n "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT2='# R8: NOT ordered After=mios-ai-firstboot.service. The plane needs the VENV (baked
# into the image) + pgvector, NOT the boot-time model fetch; ordering behind
# firstboot'"'"'s multi-GB download blocked the router for the whole download. firstboot
# `systemctl restart --no-block`s this unit once models land, so the edge is redundant.'
[ -n "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT3+x}" ] || MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT3='# R6: the pipe touches pgvector on every route, so upgrade the DB edge from After=
# (ordering only) to a hard Requires= -- a missing DB should hold/fail the unit.'
[ -n "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT4+x}" ] || MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT4='# R6: bound the existing Restart=on-failure so a DB-down window (many quick
# restarts) can'"'"'t trip the default 5/10s start limit and land permanently failed.'
[ -n "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT5+x}" ] || MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT5='# The venv python is baked into the FINAL image, but on the podman-MiOS-DEV substrate it is
# built at first boot by mios-ai-firstboot. Skip (rather than 203/EXEC-fail) until it exists.'
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/lib/mios/agents/.venv/bin/python3}"
[ -n "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Agent Pipe (router + refine + critic FastAPI; fronts hermes for every gateway)'
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_DOCUMENTATION:=file:///usr/lib/mios/agent-pipe/server.py}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_REQUIRES:=mios-pgvector.service}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_STARTLIMITBURST:=5}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_STARTLIMITINTERVALSEC:=300}"
: "${MIOS_UNITS_MIOS_AGENT_PIPE_SERVICE_UNIT_WANTS:=network-online.target mios-passport-provision.service}"
: "${MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_INSTALL_WANTEDBY:=timers.target}"
[ -n "${MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_TIMER_COMMENT='# 2 min after boot (agent-pipe up by then), then every 15 min so the role
# SYSTEMs track catalog/SSOT changes and the peer list tracks the live fleet.'
: "${MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_TIMER_ONBOOTSEC:=2min}"
: "${MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_TIMER_ONUNITACTIVESEC:=15min}"
: "${MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_TIMER_PERSISTENT:=true}"
[ -n "${MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers mios-aios-refresh.service every 15 minutes to synchronize the Single Source of Truth (SSOT) and update the A2A fleet discovery peer list.
# AI-related: mios-aios-refresh, mios-aios-refresh.service, timers.target'
: "${MIOS_UNITS_MIOS_AIOS_REFRESH_TIMER_UNIT_DESCRIPTION:=Periodic MiOS AIOS refresh (SSOT role SYSTEMs + A2A fleet discovery)}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_COMMENT='# Cap a hung fetch (multi-GB model download) at 10min so it can'"'"'t wedge the unit
# forever; the timer re-fires the run afterwards. (Was 2400s.)'
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_COMMENT2+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_COMMENT2='# The script reads MIOS_LLAMACPP_BAKE_MODELS (the GGUF download spec) +
# MIOS_AI_* from the env bridge. Without this, a fresh systemd boot has an
# EMPTY environment -> bake_models reads empty -> "GGUFs not baked" -> the
# llm-light lane stays inert forever. The leading '"'"'-'"'"' makes it optional so
# the unit still starts (and retries) if the bridge isn'"'"'t generated yet.
# install-robustness 2026-06-21.'
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-ai-firstboot}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=1800}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target}"
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes the mios-ai-firstboot script to provision the AI agent virtual environment and download llama.cpp GGUF models if the .ai-firstboot-done sentinel is missing.
# AI-related: 72-hermes-agent.sh, /usr/libexec/mios/mios-ai-firstboot, mios-ai-firstboot, mios-dev, mios-llm-light.service, network-online.target
# Completes the build-time AI setup on deployments that didn'"'"'t bake it (the
# overlay-provisioned dev VM, WSL imports, etc.). 72-hermes-agent.sh'"'"'s header
# explicitly anticipates this: "a firstboot retry can complete it later".
# Needs network (pip + model pull); GGUF blobs come from Hugging Face.'
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT2='# The script writes the sentinel ONLY when both the venv and the GGUFs are
# present, so a network-less first boot simply retries on the next one.'
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT3+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT3='# Retry is owned by mios-ai-firstboot.timer (OnBootSec + OnUnitInactiveSec), NOT
# an in-unit Restart=on-failure / StartLimitBurst storm. The script degrades open
# (exit 0) on a partial provision, so the unit shows success and the timer simply
# re-fires it on its cadence until the sentinel above is written.'
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.ai-firstboot-done}"
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' AI first-boot provisioning (agent venv + llama.cpp GGUFs)'
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/mios-dev/mios}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_INSTALL_WANTEDBY:=timers.target}"
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_TIMER_COMMENT='# First retry shortly after boot, then every 10min while the service sits
# inactive and the sentinel is still absent. Persistent catches up a missed
# window across a shutdown. The timer OWNS retry now (the .service no longer
# carries Restart=on-failure / StartLimitBurst).'
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_TIMER_ONBOOTSEC:=2min}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_TIMER_ONUNITINACTIVESEC:=10min}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_TIMER_UNIT:=mios-ai-firstboot.service}"
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_UNIT_COMMENT='# AI-hint: Defines the systemd timer for mios-ai-firstboot.service, controlling post-boot AI provisioning retries until the sentinel file is present.
# AI-related: /var/lib/mios/.ai-firstboot-done, mios-ai-firstboot.service, timers.target
# /usr/lib/systemd/system/mios-ai-firstboot.timer
# Retries the first-boot AI stack deployment if it didn'"'"'t complete on
# initial boot (e.g. machine rebooted mid-pull, or GPU drivers were
# mid-dkms build). The timer is enabled by default so the attempt happens
# automatically, but is gated on the absence of the sentinel file in
# place. The .service degrades open (exit 0) on a partial provision and carries
# ConditionPathExists=!<sentinel>, so once /var/lib/mios/.ai-firstboot-done is
# written the timer-fired run no-ops. The same condition here stops the timer
# itself from firing needlessly once provisioning is complete.'
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.ai-firstboot-done}"
[ -n "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' AI Plane First-Boot Provisioning Retry Schedule'
: "${MIOS_UNITS_MIOS_AI_FIRSTBOOT_TIMER_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-ai-firstboot-provision.sh}"
: "${MIOS_UNITS_MIOS_AI_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_AI_TARGET_UNIT_AFTER:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_AI_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_AI_TARGET_UNIT_COMMENT='# AI-hint: systemd target grouping all MiOS AI plane services (T-076).
# usr/lib/systemd/system/mios-ai.target'
: "${MIOS_UNITS_MIOS_AI_TARGET_UNIT_DESCRIPTION:=MiOS AI Services Target}"
: "${MIOS_UNITS_MIOS_AI_TARGET_UNIT_WANTS:=mios-agent-pipe.service}"
: "${MIOS_UNITS_MIOS_BOOTC_SWITCH_PATH_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_BOOTC_SWITCH_PATH_PATH_PATHCHANGED:=/var/lib/mios/forge-runner/last-build.txt}"
: "${MIOS_UNITS_MIOS_BOOTC_SWITCH_PATH_PATH_UNIT:=mios-bootc-switch.service}"
[ -n "${MIOS_UNITS_MIOS_BOOTC_SWITCH_PATH_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_BOOTC_SWITCH_PATH_UNIT_COMMENT='# AI-hint: Systemd path unit that monitors /var/lib/mios/forge-runner/last-build.txt to trigger mios-bootc-switch.service, automating the bootc kernel/image switch immediately after a Forgejo Runner build completes.
# AI-related: /usr/libexec/mios/bootc-switch-from-build.sh, mios-bootc-switch, mios-bootc-switch.service, multi-user.target
# /usr/lib/systemd/system/mios-bootc-switch.path
# Watches the build-output sentinel that the Forgejo Runner workflow
# writes after a successful `podman build`. PathChanged fires on
# either creation or modification, so re-running the workflow with
# the same image ref still triggers a re-stage (bootc switch is
# idempotent on identical refs -- this is fine).'
[ -n "${MIOS_UNITS_MIOS_BOOTC_SWITCH_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_BOOTC_SWITCH_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"' watch for Forgejo Runner build output -> bootc switch'
: "${MIOS_UNITS_MIOS_BOOTC_SWITCH_PATH_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/bootc-switch-from-build.sh}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-bound-images-firstboot}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_SUCCESSEXITSTATUS:=0 1 2 3}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=10800}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target}"
[ -n "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: FBM first-boot bound-image provisioner unit (oneshot, sentinel-guarded, degrade-open).
# Runs mios-bound-images-firstboot once at first boot to pull [ai].firstboot_bound_images; enabled via 90-mios.preset.
# AI-related: /usr/libexec/mios/mios-bound-images-firstboot, /usr/share/mios/mios.toml'
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.bound-images-firstboot-done}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION:=First-boot Bound Images Provisioner}"
: "${MIOS_UNITS_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/ceph-bootstrap.sh}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_EXECSTARTPOST:=/usr/bin/touch /var/lib/ceph/.bootstrapped,-/bin/chmod 0600 /etc/ceph/ceph.client.admin.keyring}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_STANDARDERROR:=journal+console}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_STANDARDOUTPUT:=journal+console}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_TIMEOUTSTARTSEC:=600}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_AFTER:=network-online.target podman.socket}"
[ -n "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit to execute /usr/libexec/mios/ceph-bootstrap.sh script to initialize the Ceph cluster (first boot only).
# AI-related: /usr/libexec/mios/ceph-bootstrap.sh, podman.socket, network-online.target, multi-user.target'
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/etc/ceph/ceph.conf,!/var/lib/ceph/.bootstrapped}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=no}"
[ -n "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Ceph Cluster Bootstrap'
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_DOCUMENTATION:=https://docs.ceph.com/en/latest/cephadm/}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_STARTLIMITINTERVALSEC:=0}"
: "${MIOS_UNITS_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_WANTS:=network-online.target podman.socket}"
: "${MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_INSTALL_WANTEDBY:=sockets.target}"
: "${MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_SOCKET_BINDIPV6ONLY:=both}"
[ -n "${MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_SOCKET_LISTENSTREAM+x}" ] || MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_SOCKET_LISTENSTREAM='0.0.0.0:'"${MIOS_PORT_COCKPIT_LINK}"
[ -n "${MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_UNIT_COMMENT='# AI-hint: Socket file for mios-cockpit-link proxy. Maps port 8091 on host/WSL to the cockpit service.
# AI-related: usr/lib/systemd/system/mios-cockpit-link.service'
: "${MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_UNIT_CONDITIONVIRTUALIZATION:=!container}"
[ -n "${MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_COCKPIT_LINK_SOCKET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Cockpit Link Proxy Socket'
: "${MIOS_UNITS_MIOS_COMPUTE_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_COMPUTE_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNITS_MIOS_COMPUTE_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_COMPUTE_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_COMPUTE_TARGET_UNIT_COMMENT='# AI-hint: Defines the compute systemd target for MiOS, representing a compute/worker node.
# AI-related: mios-compute, mios-headless.target'
: "${MIOS_UNITS_MIOS_COMPUTE_TARGET_UNIT_CONFLICTS:=mios-controller.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNITS_MIOS_COMPUTE_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_COMPUTE_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Compute Role'
: "${MIOS_UNITS_MIOS_COMPUTE_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNITS_MIOS_CONTROLLER_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_CONTROLLER_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNITS_MIOS_CONTROLLER_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_CONTROLLER_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_CONTROLLER_TARGET_UNIT_COMMENT='# AI-hint: Defines the controller systemd target for MiOS, representing the cluster controller.
# AI-related: mios-controller, mios-headless.target'
: "${MIOS_UNITS_MIOS_CONTROLLER_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNITS_MIOS_CONTROLLER_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_CONTROLLER_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Controller Role'
: "${MIOS_UNITS_MIOS_CONTROLLER_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_COMMENT='# Operator-tunable knobs (override via drop-in or /etc/mios/secrets.env):
#   Environment=MIOS_DAEMON_MODEL=qwen3:1.7b
#   Environment=MIOS_DAEMON_ENDPOINT=http://127.0.0.1:11434
#   Environment=MIOS_DAEMON_STATE_DIR=/var/lib/mios/daemon
#   Environment=MIOS_DAEMON_CRON_TOML=/etc/mios/daemon/cron.toml
#   Environment=MIOS_DAEMON_CLASSIFY_S=30
#   Environment=MIOS_DAEMON_CRON_TICK_S=60
#   Environment=MIOS_DAEMON_WATCH_UNITS=mios-agent-pipe.service,mios-open-webui.service'
[ -n "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_COMMENT2+x}" ] || MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_COMMENT2='# Hardening (kept loose enough to allow journalctl subscription +
# subprocess.Popen for cron actions).'
[ -n "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_COMMENT3+x}" ] || MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_COMMENT3='# /var/lib/mios/daemon = the daemon'"'"'s own state (state.json, launch_failures).
# /var/lib/mios/scratch = the SHARED cross-agent blackboard the task_collector
# drops agent-nudges into for other agents to read (operator 2026-05-24: under
# ProtectSystem=strict it was read-only, so task_collector EROFS-failed writing
# agent-nudges.md -- the nudge feature was silently dead).'
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_ENVIRONMENT:=PYTHONUNBUFFERED=1}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-daemon}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_LOCKPERSONALITY:=true}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_PROTECTCONTROLGROUPS:=true}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_PROTECTKERNELTUNABLES:=true}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_READWRITEPATHS:=/var/lib/mios/daemon /var/lib/mios/scratch}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_RESTARTSEC:=5s}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_RESTRICTADDRESSFAMILIES:=AF_INET AF_INET6 AF_UNIX}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_RESTRICTREALTIME:=true}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_UNIT_AFTER:=mios-llm-light.service network.target}"
[ -n "${MIOS_UNITS_MIOS_DAEMON_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_DAEMON_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit file defining the core MiOS daemon; it consolidates log watching, cron gating, and agent nudging into a single process using a local qwen3 model to update the state.json file used by the OWUI sidecar.
# AI-related: /usr/libexec/mios/mios-daemon, /etc/mios/secrets.env, /etc/mios/daemon/cron.toml, mios-ai, mios-open-webui
# /usr/lib/systemd/system/mios-daemon.service
#
# MiOS consolidated micro-LLM daemon. Replaces three predecessors
# (mios-log-watcher + mios-cron-director + mios-agent-nudger) with
# ONE process that subscribes to journald once, holds a single
# qwen3:0.6b-cpu client (keep_alive=-1 forever, num_gpu=0 CPU-only
# per Law 7 OFFLINE-FIRST + "always-on agentic OS"), and dispatches
# the three handlers off a single event stream. Writes a unified
# /var/lib/mios/daemon/state.json the OWUI mios_sidecar Filter polls.
#
# Operator directive 2026-05-17: "ALL to be consolidated to one
# mios daemon/agent" + "keep_alive should be TRUE for a TRULY
# Agentic OS--MiOS!"'
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/mios-daemon}"
[ -n "${MIOS_UNITS_MIOS_DAEMON_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_DAEMON_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' consolidated micro-LLM daemon (log classify + refusal detect + cron gate)'
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-daemon}"
: "${MIOS_UNITS_MIOS_DAEMON_SERVICE_UNIT_WANTS:=mios-llm-light.service}"
: "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_ACCURACYSEC:=30s}"
: "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_ONBOOTSEC:=2min}"
: "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_ONUNITACTIVESEC:=5min}"
: "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_PERSISTENT:=false}"
: "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_UNIT:=mios-dashboard-issue.service}"
[ -n "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers mios-dashboard-issue.service every 5 minutes to refresh the /etc/issue.d/ banner with real-time Quadlet status updates like service flapping and endpoint reachability.
# AI-related: /usr/libexec/mios/mios-dashboard-render-issue.sh, mios-dashboard-issue, mios-dashboard-render-issue, mios-dashboard-issue.service, timers.target
# /usr/lib/systemd/system/mios-dashboard-issue.timer
# Refresh the /etc/issue.d/ dashboard snippet every 5 minutes so
# Quadlet state changes (services flapping, endpoint reachability
# coming and going) reach the pre-login banner without operator
# intervention.'
[ -n "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' dashboard /etc/issue.d refresh timer'
: "${MIOS_UNITS_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-dashboard-render-issue.sh}"
: "${MIOS_UNITS_MIOS_DESKTOP_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_DESKTOP_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNITS_MIOS_DESKTOP_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_DESKTOP_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_DESKTOP_TARGET_UNIT_COMMENT='# AI-hint: Defines the mios-desktop.target systemd unit to initialize the desktop environment, ensuring required virtualization services (libvirtd, virtnetworkd) are active while preventing concurrent headless or cluster-specific targets.
# AI-related: mios-desktop, mios-headless, mios-k3s-master, mios-ha-node, gdm.service, libvirtd.service, libvirtd.socket, virtnetworkd.service, virtqemud.service, virtstoraged.service'
: "${MIOS_UNITS_MIOS_DESKTOP_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNITS_MIOS_DESKTOP_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_DESKTOP_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Desktop Role'
: "${MIOS_UNITS_MIOS_DESKTOP_TARGET_UNIT_REQUIRES:=multi-user.target gdm.service libvirtd.service libvirtd.socket virtnetworkd.service virtqemud.service virtstoraged.service virtnodedevd.service}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_COMMENT:=# Low-privilege execution}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_ENVIRONMENT:=PYTHONPATH=/usr/lib/mios/agent-pipe}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/userenv.sh,-/etc/mios/install.env}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_EXECSTART:=/usr/lib/mios/agents/.venv/bin/python3 -u -m mios_pipe.memory.embed_backfill}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_AFTER:=mios-pgvector.service mios-llm-light.service mios-agent-pipe.service}"
[ -n "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that runs the mios_pipe.memory.embed_backfill worker to periodically re-embed database rows with stale or missing vector versions.
# AI-related: /usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py, mios-embed-backfill.timer, mios-pgvector.service, mios-llm-light.service
# /usr/lib/systemd/system/mios-embed-backfill.service'
[ -n "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_COMMENT2='# R8: dropped After=mios-ai-firstboot.service -- the backfill worker needs pgvector
# + the embedding lane (mios-llm-light), NOT the boot-time model fetch.'
[ -n "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Embedding Backfill Worker'
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_DOCUMENTATION:=file:///usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_SERVICE_UNIT_REQUIRES:=mios-pgvector.service}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_TIMER_ACCURACYSEC:=1min}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_TIMER_ONBOOTSEC:=5min}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_TIMER_ONUNITACTIVESEC:=15min}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_TIMER_UNIT:=mios-embed-backfill.service}"
[ -n "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_UNIT_COMMENT='# AI-hint: Defines the systemd timer for the mios-embed-backfill.service, controlling the periodic execution interval (default 15m) for background embedding backfilling.
# AI-related: /usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py, mios-embed-backfill.service, timers.target
# /usr/lib/systemd/system/mios-embed-backfill.timer'
[ -n "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Embedding Backfill Timer'
: "${MIOS_UNITS_MIOS_EMBED_BACKFILL_TIMER_UNIT_DOCUMENTATION:=file:///usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py}"
: "${MIOS_UNITS_MIOS_ENDPOINT_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_ENDPOINT_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNITS_MIOS_ENDPOINT_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_ENDPOINT_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_ENDPOINT_TARGET_UNIT_COMMENT='# AI-hint: Defines the endpoint systemd target for MiOS, representing an edge/client node.
# AI-related: mios-endpoint, mios-headless.target'
: "${MIOS_UNITS_MIOS_ENDPOINT_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-ha-node.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNITS_MIOS_ENDPOINT_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_ENDPOINT_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Endpoint Role'
: "${MIOS_UNITS_MIOS_ENDPOINT_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_COMMENT:=# model load + first request can take ~40s on a cold GPU}"
[ -n "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_ENVIRONMENT='HF_HOME=/var/home/mios/.cache/huggingface,MIOS_FINETUNE_SERVE_PORT=${MIOS_PORT_FINETUNE_SERVE:-11438}'
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_EXECSTART:=/var/lib/mios/finetune/venv/bin/python /usr/libexec/mios/mios-finetune-serve}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_GROUP:=mios}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_RESTARTSEC:=5}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_TIMEOUTSTARTSEC:=180}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_USER:=mios}"
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_UNIT_AFTER:=network-online.target}"
[ -n "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit to host the fine-tuned refiner model as an OpenAI /v1-compatible endpoint on port 11438, allowing the agent-pipe to swap between the high-quality transformer-served adapter and the faster llama.cpp path.
# AI-related: /usr/libexec/mios/mios-finetune-serve, network-online.target
# '"'"'MiOS'"'"' fine-tune serve -- serves the trained role adapter (base + LoRA) as an
# OpenAI /v1 endpoint so the fine-tuned refiner can be adopted/A-B'"'"'d
# in the agent-pipe. OPT-IN: NOT enabled by default (the transformers-served 2B is
# correct but slower than the GGUF lane on the hot path; enable to evaluate).'
[ -n "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' fine-tune serve (base+adapter refiner backend)'
: "${MIOS_UNITS_MIOS_FINETUNE_SERVE_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_COMMENT='# Ports: 3000=Forge, 3030=OWUI, 8080=code-server, 8642=Hermes-Agent,
#        8888=SearXNG, 9090=Cockpit, 9119=Hermes-Dashboard,
#        11450=LLM-Light, 5432=pgvector, 19090=Cockpit-link, 3053=AdGuard UI, 53=AdGuard DNS.
# (crawl4ai :11235 removed 2026-05-24: the crawl engine is now a LOOPBACK-only
#  venv service -- mios-crawl4ai.service binds 127.0.0.1, never LAN-exposed.)
# AdGuard DNS needs BOTH 53/tcp and 53/udp (UDP is the normal query path).
# Hardening: only the firewall-cmd binary needs system privileges; lock
# everything else down.'
[ -n "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_EXECSTART='/bin/bash -c '"'"'\
    set +e; \
    if [ -f /etc/mios/install.env ]; then source /etc/mios/install.env; fi; \
    ports=(\
        "${MIOS_PORT_FORGE_HTTP:-8400}" \
        "${MIOS_PORT_OPEN_WEBUI:-8200}" \
        "${MIOS_PORT_CODE_SERVER:-8900}" \
        "${MIOS_PORT_HERMES:-8720}" \
        "${MIOS_PORT_SEARXNG:-8800}" \
        "${MIOS_PORT_COCKPIT:-8110}" \
        "${MIOS_PORT_HERMES_DASHBOARD:-8210}" \
        "${MIOS_PORT_LLM_LIGHT:-8500}" \
        "${MIOS_PORT_PGVECTOR:-8600}" \
        "${MIOS_PORT_COCKPIT_LINK:-8120}" \
        "${MIOS_PORT_ADGUARD_UI:-8050}" \
        "${MIOS_PORT_SSH:-8100}" \
        "${MIOS_PORT_FORGE_SSH:-8410}" \
        "${MIOS_PORT_VLLM:-8520}" \
        "${MIOS_PORT_SGLANG:-8530}" \
        "${MIOS_PORT_CPU_NODE:-8510}" \
        53 \
    ); \
    for p in "${ports[@]}"; do \
        /usr/bin/firewall-cmd --permanent --add-port=${p}/tcp >/dev/null 2>&1; \
    done; \
    /usr/bin/firewall-cmd --permanent --add-port=53/udp >/dev/null 2>&1; \
    /usr/bin/firewall-cmd --reload >/dev/null 2>&1; \
    echo "MiOS firewalld ports: $(/usr/bin/firewall-cmd --list-ports 2>/dev/null)"; \
    exit 0\'"'"''
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_PROTECTCONTROLGROUPS:=yes}"
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_PROTECTKERNELTUNABLES:=yes}"
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_UNIT_AFTER:=firewalld.service network-online.target}"
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_UNIT_BEFORE:=mios-agent-pipe.service mios-open-webui.service mios-searxng.service}"
[ -n "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_UNIT_COMMENT='# AI-hint: Ensures critical MiOS service ports (3000, 3030, 8080, 8642, 8888, 9090, 9119, 11434, 19090, 3053, 53) are opened in firewalld at boot to prevent connectivity loss for Open WebUI, Hermes, Cockpit, and SearXNG.
# AI-related: mios-open-webui, mios-searxng, mios-crawl4ai, firewalld.service, hermes-agent.service, mios-open-webui.service, mios-searxng.service, mios-crawl4ai.service, network-online.target, multi-user.target
# Ensure MiOS service ports are open in firewalld at every boot.
#
# Why this exists: automation/44-firewall-ports.sh writes the firewalld
# zone XML at OCI build time via firewall-offline-cmd. On stale OCI
# images (pre-2026-05) OR when the install-time script didn'"'"'t run / the
# XML didn'"'"'t persist, firewalld comes up with no ports open and ALL
# Windows->WSL bridging silently times out (operator-confirmed
# regression 2026-05-15: Open WebUI/Hermes/Cockpit/SearXNG inaccessible
# post-reinstall; firewall-cmd --list-ports returned empty; adding the
# ports manually instantly restored all 4 services).
#
# This unit runs at every boot and is idempotent: --add-port on a port
# that'"'"'s already open is a no-op. No-ops cleanly when firewalld is
# absent (ConditionPathExists) or inactive.'
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/bin/firewall-cmd}"
[ -n "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"': ensure firewalld has the MiOS service ports open'
: "${MIOS_UNITS_MIOS_FIREWALL_PORTS_SERVICE_UNIT_WANTS:=firewalld.service network-online.target}"
: "${MIOS_UNITS_MIOS_FIRSTBOOT_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_FIRSTBOOT_TARGET_UNIT_AFTER:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_FIRSTBOOT_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_FIRSTBOOT_TARGET_UNIT_COMMENT='# AI-hint: Defines the mios-firstboot.target unit to orchestrate initial provisioning services (CDI, libvirtd, and GRD setup) during the first boot sequence of the MiOS system.
# AI-related: mios-firstboot, mios-cdi-detect, mios-libvirtd-setup, mios-grd-setup, mios-cdi-detect.service, mios-libvirtd-setup.service, mios-grd-setup.service, multi-user.target'
[ -n "${MIOS_UNITS_MIOS_FIRSTBOOT_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_FIRSTBOOT_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' first-boot provisioning'
: "${MIOS_UNITS_MIOS_FIRSTBOOT_TARGET_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS}"
: "${MIOS_UNITS_MIOS_FIRSTBOOT_TARGET_UNIT_WANTS:=mios-cdi-detect.service mios-libvirtd-setup.service mios-grd-setup.service}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-forgejo-runner-firstboot.sh}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_RESTARTSEC:=30}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=180s}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_AFTER:=mios-forge.service mios-forge-firstboot.service}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_BEFORE:=mios-forgejo-runner.service}"
[ -n "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: One-shot systemd service that executes the initial registration of the Forgejo runner using the local token if the runner is not yet configured, ensuring the runner is registered before the main service starts.
# AI-related: /etc/mios/forge/runner-token, /usr/libexec/mios/mios-forgejo-runner-firstboot.sh, mios-forge.service, mios-forge-firstboot.service, mios-forgejo-runner.service'
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=/etc/mios/forge/runner-token,!/srv/mios/forge-runner/.runner}"
[ -n "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Forgejo Runner first-boot registration'
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://forgejo.org/docs/latest/admin/actions/}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_STARTLIMITBURST:=6}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_STARTLIMITINTERVALSEC:=1200}"
: "${MIOS_UNITS_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_WANTS:=mios-forge.service}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_COMMENT='# Hardening: this service writes to a small set of paths plus calls
# '"'"'podman exec'"'"' against the running mios-forge container. RestrictNamespaces
# and RestrictAddressFamilies were tried but break Podman'"'"'s CRIU/conmon
# attach path on rootful container exec; we drop them and lean on the
# read-write path scoping + ProtectHome instead, which is sufficient for
# this script'"'"'s actual surface area.
#
# /run is LOAD-BEARING and must be writable as a whole: rootful
# `podman exec` -- even a plain exec, no container lifecycle -- grabs
# coordination locks across multiple /run subtrees: /run/libpod/
# alive.lck (runtime init lock), /run/lock/netavark.lock (network
# coordination), /run/containers/ (storage runroot). Listing them
# individually is whack-a-mole; each missing one surfaces only at
# runtime as "open <path>: read-only file system" (exit 125). /run is
# tmpfs runtime state, so granting it RW is low-risk and is exactly
# podman'"'"'s requirement. That exit-125 failure is silent-deadly here:
# forge-firstboot.sh'"'"'s `admin user create` idempotency guard mis-reads
# 125 as "user already exists", so the admin is never created, the
# repo-create 401s, the runner-token mint fails, and the entire
# self-replication CI chain (runner-firstboot -> .runner ->
# mios-forgejo-runner.service) stays dead behind unmet
# ConditionPathExists guards. Operator-confirmed regression 2026-05-14.'
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/forge-firstboot.sh}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_LOCKPERSONALITY:=yes}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_NONEWPRIVILEGES:=yes}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_PRIVATETMP:=yes}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_PROTECTHOME:=yes}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_READWRITEPATHS:=/etc/mios/forge /var/lib/mios/forge /var/log/mios/forge /var/lib/containers /run}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_RESTARTSEC:=30}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_RESTRICTREALTIME:=yes}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=600s}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_AFTER:=mios-forge.service network-online.target}"
[ -n "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Executes the forge-firstboot.sh script to bootstrap the Forgejo instance, creating the initial admin user and repository credentials required for the MiOS self-replication and CI runner integration.
# AI-related: /etc/mios/install.env, /usr/libexec/mios/forge-firstboot.sh, mios-forge.service, mios-forgejo-runner.service
# /etc/mios/install.env is the optional layered-TOML resolver output
# from mios-sync-env. The firstboot script tolerates its absence:
# admin user, email, password all resolve from MIOS_DEFAULT_* or
# fall back to "mios" / mios@hostname.local. Keep the unit gated only
# by the firstboot sentinel.'
[ -n "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_COMMENT2='# Forgejo bootstrap MUST run on WSL too (the localhost:3000 git origin
# is the heart of the MiOS self-replication loop on every shape). A
# plain `!container` would skip WSL because systemd reports virtualization
# as `wsl` -- a container variant. Use OR: "not a container OR is WSL".'
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/forge/.firstboot-done}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=|!container,|wsl}"
[ -n "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Forge first-boot admin-bootstrap (Forgejo)'
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/mios-dev/MiOS/blob/main/etc/containers/systemd/mios-forge.container}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_STARTLIMITBURST:=6}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_STARTLIMITINTERVALSEC:=1200}"
: "${MIOS_UNITS_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_WANTS:=mios-forge.service network-online.target}"
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNITS_MIOS_GPU_AMD_SERVICE_SERVICE_EXECSTART='/usr/bin/bash -c '"'"' \
  # If amd-ctk ever lands in Fedora RPM repos, drop a CDI spec automatically. \
  # Until then containers must pass --device /dev/kfd --device /dev/dri \
  # --group-add keep-groups explicitly. \
  if command -v amd-ctk >/dev/null 2>&1; then \
    amd-ctk cdi generate --output=/run/cdi/amd.json || true; \
  fi; \
  # Defensive perms -- Fedora Rawhide already labels /dev/kfd as root:render \
  # 0660 via kernel, but pin it in case of drift. \
  chgrp render /dev/kfd 2>/dev/null || true; \
  chmod 0660   /dev/kfd 2>/dev/null || true; \
  exit 0\'"'"''
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_SERVICE_EXECSTARTPRE:=/usr/sbin/modprobe -a amdgpu}"
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_SERVICE_STANDARDERROR:=journal}"
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_SERVICE_STANDARDOUTPUT:=journal}"
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_UNIT_AFTER:=systemd-modules-load.service systemd-udev-trigger.service}"
[ -n "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_GPU_AMD_SERVICE_UNIT_COMMENT='# AI-hint: Configures AMD GPU hardware acceleration by loading the amdgpu module, generating CDI specifications for containerized ROCm/KFD access, and enforcing 0660 permissions on /dev/kfd for the render group.
# AI-related: mios-gpu, systemd-modules-load.service, systemd-udev-trigger.service, multi-user.target'
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_UNIT_CONDITIONPATHEXISTS:=/dev/kfd}"
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container}"
[ -n "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_GPU_AMD_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' AMD GPU container plumbing (ROCm/KFD + DRI)'
: "${MIOS_UNITS_MIOS_GPU_AMD_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS/blob/main/docs/gpu-passthrough.md}"
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_INSTALL_WANTEDBY:=sysinit.target}"
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/gpu-detect}"
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_AFTER:=systemd-journald.socket}"
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_BEFORE:=gdm.service display-manager.service systemd-modules-load.service systemd-udevd.service}"
[ -n "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/gpu-detect to identify hardware GPU capabilities during boot, setting environment flags for display managers and graphics drivers.
# AI-related: /usr/libexec/mios/gpu-detect, mios-gpu-detected, gdm.service, display-manager.service, systemd-modules-load.service, systemd-udevd.service, systemd-journald.socket, sysinit.target'
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/run/mios-gpu-detected}"
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container}"
: "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_DEFAULTDEPENDENCIES:=no}"
[ -n "${MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_GPU_DETECT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' GPU Environment Detection'
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_SERVICE_EXECSTART='/usr/bin/bash -c '"'"' \
  # Defensive perms on primary render node -- do not touch card* nodes (video group \
  # handled by 99-mios-gpu.rules at udev-add time). \
  if [ -e /dev/dri/renderD128 ]; then \
    chgrp render /dev/dri/renderD128 2>/dev/null || true; \
    chmod 0660   /dev/dri/renderD128 2>/dev/null || true; \
  fi; \
  exit 0\'"'"''
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_SERVICE_EXECSTARTPRE:=-/usr/sbin/modprobe -a i915 xe amdgpu}"
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_SERVICE_STANDARDERROR:=journal}"
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_SERVICE_STANDARDOUTPUT:=journal}"
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_UNIT_AFTER:=systemd-modules-load.service systemd-udev-trigger.service}"
[ -n "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that initializes iGPU drivers (i915/xe/amdgpu) and configures permissions for /dev/dri/renderD128 to enable hardware acceleration and unified render node access for Intel/AMD hardware.
# AI-related: mios-gpu, systemd-modules-load.service, systemd-udev-trigger.service, multi-user.target'
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_UNIT_CONDITIONPATHEXISTS:=/dev/dri/renderD128}"
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container}"
[ -n "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Intel/AMD iGPU Container Plumbing (i915/xe/amdgpu)'
: "${MIOS_UNITS_MIOS_GPU_INTEL_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS/blob/main/docs/gpu-passthrough.md}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_AFTER:=sysinit.target}"
[ -n "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_COMMENT='# AI-hint: Overrides the mios-gpu-nvidia.service unit to ensure it runs during the early sysinit.target phase, bypassing standard dependency delays to ensure GPU drivers are initialized early in the boot sequence.
# AI-related: mios-gpu-nvidia, mios-gpu-nvidia.service, sysinit.target'
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_DEFAULTDEPENDENCIES:=no}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_REQUIRES:=sysinit.target}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_SERVICE_EXECSTART='/usr/bin/bash -c '"'"' \
  if systemctl list-unit-files nvidia-cdi-refresh.service 2>/dev/null \
       | grep -q nvidia-cdi-refresh; then \
    echo "nvidia-cdi-refresh.service present; deferring CDI generation to upstream"; \
    exit 0; \
  fi; \
  if command -v nvidia-ctk >/dev/null 2>&1; then \
    nvidia-ctk cdi generate --output=/run/cdi/nvidia.yaml || true; \
  fi; \
  exit 0\'"'"''
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_SERVICE_EXECSTARTPRE:=/usr/sbin/modprobe -a nvidia nvidia_uvm nvidia_modeset nvidia_drm}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_SERVICE_STANDARDERROR:=journal}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_SERVICE_STANDARDOUTPUT:=journal}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_AFTER:=systemd-modules-load.service systemd-udev-trigger.service akmods.service}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_BEFORE:=nvidia-cdi-refresh.service}"
[ -n "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that ensures NVIDIA GPU modules are loaded and CDI configurations are generated for container passthrough, acting as a fallback or prerequisite for nvidia-cdi-refresh.service.
# AI-related: mios-gpu, nvidia-cdi-refresh.service, systemd-modules-load.service, systemd-udev-trigger.service, akmods.service, multi-user.target'
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_CONDITIONPATHEXISTS:=/dev/nvidia0}"
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container,!wsl}"
[ -n "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' NVIDIA GPU container plumbing'
: "${MIOS_UNITS_MIOS_GPU_NVIDIA_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS/blob/main/docs/gpu-passthrough.md}"
: "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/gpu-pv-detect}"
: "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_UNIT_AFTER:=systemd-modules-load.service}"
: "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_UNIT_BEFORE:=display-manager.service}"
[ -n "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/gpu-pv-detect to detect Hyper-V GPU Partitioning (GPU-PV) capabilities during boot, enabling hardware acceleration for guests on Microsoft Hyper-V hosts.
# AI-related: /usr/libexec/mios/gpu-pv-detect, systemd-modules-load.service, display-manager.service, multi-user.target'
: "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=microsoft}"
: "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_UNIT_DEFAULTDEPENDENCIES:=no}"
[ -n "${MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_GPU_PV_DETECT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hyper-V GPU-PV Guest Detection'
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_SERVICE_EXECSTART='/usr/bin/bash -c '"'"' \
  set +e; \
  HAS_NV=0; HAS_AMD=0; HAS_INTEL=0; \
  [ -e /dev/nvidia0 ]            && HAS_NV=1; \
  [ -e /dev/kfd ]                && HAS_AMD=1; \
  [ -e /dev/dri/renderD128 ]     && HAS_INTEL=1; \
  VIRT=$(systemd-detect-virt || echo none); \
  # /run/mios, /run/cdi, /var/lib/mios/gpu declared in usr/lib/tmpfiles.d/mios-gpu.conf (LAW 2). \
  { \
    echo "timestamp=$(date -Is)"; \
    echo "virtualization=${VIRT}"; \
    echo "nvidia=${HAS_NV}"; \
    echo "amd=${HAS_AMD}"; \
    echo "intel=${HAS_INTEL}"; \
    lspci -nn 2>/dev/null | grep -iE "vga|3d|display" || true; \
  } > /run/mios/gpu-passthrough.status; \
  # Non-persistent (in-memory) SELinux boolean -- build-time semanage handles \
  # persistence; this guarantees the boolean is on even if the policy merge \
  # dropped it. No-op on permissive / disabled / missing boolean. \
  if command -v setsebool >/dev/null 2>&1; then \
    setsebool container_use_devices on 2>/dev/null || true; \
  fi; \
  exit 0\'"'"''
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_SERVICE_RUNTIMEDIRECTORY:=mios}"
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_SERVICE_RUNTIMEDIRECTORYMODE:=0755}"
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_SERVICE_STANDARDERROR:=journal}"
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_SERVICE_STANDARDOUTPUT:=journal}"
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_UNIT_AFTER:=systemd-udev-trigger.service systemd-modules-load.service local-fs.target}"
[ -n "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that detects GPU hardware (NVIDIA, AMD, Intel) and virtualization status, exporting the results to /run/mios/gpu-passthrough.status and enabling the container_use_devices SELinux boolean.
# AI-related: mios-gpu, systemd-udev-trigger.service, systemd-modules-load.service, podman.socket, docker.socket, local-fs.target, basic.target, sockets.target, multi-user.target'
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container}"
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_UNIT_DEFAULTDEPENDENCIES:=yes}"
[ -n "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' GPU passthrough detection and status'
: "${MIOS_UNITS_MIOS_GPU_STATUS_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS/blob/main/docs/gpu-passthrough.md}"
: "${MIOS_UNITS_MIOS_HA_NODE_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_HA_NODE_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNITS_MIOS_HA_NODE_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_HA_NODE_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_HA_NODE_TARGET_UNIT_COMMENT='# AI-hint: Defines the mios-ha-node.target unit to identify and configure a node as a High Availability cluster member, ensuring it conflicts with desktop/headless modes and requires corosync/pacemaker services.
# AI-related: mios-ha-node, mios-desktop, mios-headless, mios-k3s-master, corosync.service, pacemaker.service, multi-user.target, mios-desktop.target, mios-headless.target, mios-k3s-master.target'
: "${MIOS_UNITS_MIOS_HA_NODE_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-endpoint.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNITS_MIOS_HA_NODE_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_HA_NODE_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' HA Cluster Node Role'
: "${MIOS_UNITS_MIOS_HA_NODE_TARGET_UNIT_REQUIRES:=multi-user.target corosync.service pacemaker.service}"
: "${MIOS_UNITS_MIOS_HEADLESS_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_HEADLESS_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNITS_MIOS_HEADLESS_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_HEADLESS_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_HEADLESS_TARGET_UNIT_COMMENT='# AI-hint: Defines the headless systemd target for MiOS, enforcing a non-GUI environment by conflicting with desktop, k3s-master, and ha-node targets to ensure a dedicated server-mode state.
# AI-related: mios-desktop, mios-k3s-master, mios-ha-node, multi-user.target, mios-desktop.target, mios-k3s-master.target, mios-ha-node.target'
: "${MIOS_UNITS_MIOS_HEADLESS_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNITS_MIOS_HEADLESS_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_HEADLESS_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Headless Role'
: "${MIOS_UNITS_MIOS_HEADLESS_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_COMMENT:=# Flatpak needs HOME to bootstrap its per-user state dir.}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_ENVIRONMENT:=HOME=/var/lib/mios/hermes,XDG_RUNTIME_DIR=/run/mios-hermes-browser,HERMES_BROWSER_HEADLESS=1,NO_AT_BRIDGE=1}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-hermes-browser start}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_PRIVATETMP:=false}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_RESTARTSEC:=5s}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_RUNTIMEDIRECTORY:=mios-hermes-browser}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_RUNTIMEDIRECTORYMODE:=0700}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_STATEDIRECTORY:=mios/hermes-browser/profile}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_STATEDIRECTORYMODE:=0700}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_TIMEOUTSTOPSEC:=30s}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_AFTER:=mios-agent-pipe.service}"
[ -n "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit to manage the local ChromeDev flatpak instance providing a Chrome DevTools Protocol (CDP) endpoint at 127.0.0.1:9222 for the Hermes-Agent'"'"'s browser_tool.py to perform navigation and interaction.
# AI-related: /usr/libexec/mios/mios-hermes-browser, mios-ai, hermes-agent.service
# /usr/lib/systemd/system/mios-hermes-browser.service
#
# Headless ChromeDev (com.google.ChromeDev flatpak) with Chrome
# DevTools Protocol on 127.0.0.1:9222 -- the CDP endpoint that
# Hermes-Agent'"'"'s browser tool attaches to (see browser.cdp_url in
# /var/lib/mios/hermes/config.yaml). Operator directive 2026-05-15:
# "Hermes-Browser isn'"'"'t enabled!! Should be using the locally
# installed ChromeDev flatpak install".'
[ -n "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_COMMENT2='# ChromeDev flatpak must be installed (system or user scope). If
# missing, the unit no-ops cleanly instead of crash-looping.'
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_CONDITIONPATHEXISTS:=|/var/lib/flatpak/app/com.google.ChromeDev,|%h/.local/share/flatpak/app/com.google.ChromeDev}"
[ -n "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Browser (ChromeDev w/ CDP for Hermes-Agent)'
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_DOCUMENTATION:=https://chromedevtools.github.io/devtools-protocol/}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_SERVICE_UNIT_WANTS:=mios-agent-pipe.service}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_ENVIRONMENT='HOME=/var/lib/mios/hermes-worker,XDG_RUNTIME_DIR=/run/mios-hermes-browser-worker,HERMES_BROWSER_HEADLESS=1,HERMES_BROWSER_CDP_PORT=${MIOS_PORT_CHROME_CDP_WORKER:-9223},HERMES_BROWSER_PROFILE_DIR=/var/lib/mios/hermes-browser/profile-w2,HERMES_BROWSER_LOG=/var/lib/mios/hermes-browser/launch-w2.log,NO_AT_BRIDGE=1'
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-hermes-browser start}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_PRIVATETMP:=false}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_RESTARTSEC:=5s}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_RUNTIMEDIRECTORY:=mios-hermes-browser-worker}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_RUNTIMEDIRECTORYMODE:=0700}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_STATEDIRECTORY:=mios/hermes-browser/profile-w2}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_STATEDIRECTORYMODE:=0700}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_TIMEOUTSTOPSEC:=30s}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_AFTER:=hermes-worker.service}"
[ -n "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit for a SECOND headless ChromeDev flatpak providing a dedicated CDP endpoint at 127.0.0.1:9223 (own profile dir profile-w2) for the Hermes WORKER (:8643), so the worker'"'"'s browser_* tool loop never stomps the primary :9222 browser'"'"'s first-page target / cookies.
# AI-related: /usr/libexec/mios/mios-hermes-browser, hermes-worker.service, mios-hermes-browser.service, mios-ai, com.google.ChromeDev
# /usr/lib/systemd/system/mios-hermes-browser-worker.service
#
# A SECOND headless ChromeDev (com.google.ChromeDev flatpak) with CDP on
# 127.0.0.1:9223 -- the dedicated browser for the Hermes WORKER (:8643).
# Distinct from the primary :9222 browser (mios-hermes-browser.service): the CDP
# supervisor attaches to the FIRST page target.'
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_CONDITIONPATHEXISTS:=|/var/lib/flatpak/app/com.google.ChromeDev,|%h/.local/share/flatpak/app/com.google.ChromeDev}"
[ -n "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Browser-Worker (ChromeDev CDP :9223 for the worker)'
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_DOCUMENTATION:=https://chromedevtools.github.io/devtools-protocol/}"
: "${MIOS_UNITS_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_WANTS:=hermes-worker.service}"
: "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_COMMENT='# Read MIOS_AI_* + model-tier vars from the env bridge so a fresh systemd
# boot has the resolved config (model pick, endpoints). Optional ('"'"'-'"'"') so
# the unit still self-heals if the bridge isn'"'"'t generated yet.
# install-robustness 2026-06-21.'
: "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-hermes-firstboot}"
: "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_AFTER:=local-fs.target systemd-tmpfiles-setup.service}"
: "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_BEFORE:=mios-agent-pipe.service multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Initializes the Hermes gateway by generating the api.env file and ensuring the config.yaml matches the current schema, acting as a self-healing pre-boot step to provide required credentials and configuration for hermes-agent.service.
# AI-related: /etc/mios/hermes/api.env., /usr/libexec/mios/mios-hermes-firstboot, hermes-agent.service, systemd-tmpfiles-setup.service
# Runs before the DIRECT-install hermes-agent.service so the gateway
# starts with a valid $HERMES_HOME/config.yaml + api.env already on
# disk. The pre-2026-05-14 ordering targeted mios-hermes.service /
# mios-hermes-workspace.service -- both deleted when the Hermes
# container Quadlets were removed; hermes-agent.service is the runtime
# now.'
[ -n "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_COMMENT2='# NO ConditionPathExists=!/etc/mios/hermes/api.env. The old gate made
# this unit a true once-ever oneshot -- but the script does TWO jobs:
# (1) mint api.env (genuinely once), and (2) seed/heal
# /var/lib/mios/hermes/config.yaml (must re-run when the Hermes config
# SCHEMA drifts across upgrades, or when the container->direct-install
# migration left $HERMES_HOME orphan-owned). The script is fully
# idempotent -- it skips keygen when API_SERVER_KEY exists and only
# rewrites config.yaml on detected drift -- so letting it run every
# boot is cheap and self-healing. Operator-confirmed 2026-05-14: the
# gate left a stale pre-0.13 config.yaml in place that the firstboot
# rewrite could never reach.'
[ -n "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Agent first-boot config + key generation'
: "${MIOS_UNITS_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS}"
: "${MIOS_UNITS_MIOS_HYBRID_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_AFTER:=graphical.target}"
: "${MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_COMMENT='# AI-hint: Defines the mios-hybrid.target unit to orchestrate the concurrent execution of desktop environments, k3s worker nodes, and Ceph OSD services as the primary system state for hybrid-role nodes.
# AI-related: mios-hybrid, k3s-agent.service, graphical.target, default.target'
: "${MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-k3s-master.target}"
[ -n "${MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hybrid role (desktop + k3s-worker + ceph-osd)'
: "${MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_REQUIRES:=graphical.target}"
: "${MIOS_UNITS_MIOS_HYBRID_TARGET_UNIT_WANTS:=k3s-agent.service}"
: "${MIOS_UNITS_MIOS_K3S_MASTER_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_K3S_MASTER_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNITS_MIOS_K3S_MASTER_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_K3S_MASTER_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_K3S_MASTER_TARGET_UNIT_COMMENT='# AI-hint: Defines the systemd target for a K3s master node role, ensuring the K3s service is active and mutually exclusive with other MiOS node profiles like desktop or headless.
# AI-related: mios-desktop, mios-headless, mios-ha-node, k3s.service, multi-user.target, mios-desktop.target, mios-headless.target, mios-ha-node.target'
: "${MIOS_UNITS_MIOS_K3S_MASTER_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-hybrid.target}"
[ -n "${MIOS_UNITS_MIOS_K3S_MASTER_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_K3S_MASTER_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' K3s Master Role'
: "${MIOS_UNITS_MIOS_K3S_MASTER_TARGET_UNIT_REQUIRES:=multi-user.target k3s.service}"
: "${MIOS_UNITS_MIOS_K3S_WORKER_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_K3S_WORKER_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNITS_MIOS_K3S_WORKER_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNITS_MIOS_K3S_WORKER_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_K3S_WORKER_TARGET_UNIT_COMMENT='# AI-hint: Defines the systemd target for the MiOS K3s worker node role, ensuring the k3s-agent.service is active and providing a specific target for orchestrating worker-node lifecycle and dependencies.
# AI-related: mios-k3s-worker, k3s-agent.service, multi-user.target, default.target'
[ -n "${MIOS_UNITS_MIOS_K3S_WORKER_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_K3S_WORKER_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' K3s worker role (agent)'
: "${MIOS_UNITS_MIOS_K3S_WORKER_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNITS_MIOS_K3S_WORKER_TARGET_UNIT_WANTS:=k3s-agent.service}"
: "${MIOS_UNITS_MIOS_LIBEXEC_PERMS_PATH_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_LIBEXEC_PERMS_PATH_PATH_PATHCHANGED:=/usr/libexec/mios}"
: "${MIOS_UNITS_MIOS_LIBEXEC_PERMS_PATH_PATH_UNIT:=mios-libexec-perms.service}"
[ -n "${MIOS_UNITS_MIOS_LIBEXEC_PERMS_PATH_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_LIBEXEC_PERMS_PATH_UNIT_COMMENT='# AI-hint: Path-watcher companion to mios-libexec-perms.service -- re-runs the go+rX chmod whenever /usr/libexec/mios changes (e.g. a git checkout of / restages the scripts without exec bits), so exec perms self-heal within seconds instead of leaving services crash-looping on 203/EXEC.
# AI-related: mios-libexec-perms.service, mios-additionalimagestores-perms.path, multi-user.target
# Path-watcher companion to mios-libexec-perms.service. Any way the exec bits
# get reset on /usr/libexec/mios (most commonly a `git checkout` of the deployed
# root /), this snaps them back to go+rX within seconds so no service is left
# crash-looping on 203/"Permission denied".'
: "${MIOS_UNITS_MIOS_LIBEXEC_PERMS_PATH_UNIT_CONDITIONPATHISDIRECTORY:=/usr/libexec/mios}"
[ -n "${MIOS_UNITS_MIOS_LIBEXEC_PERMS_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_LIBEXEC_PERMS_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"': watch /usr/libexec/mios for perm changes; retrigger chmod'
: "${MIOS_UNITS_MIOS_MCP_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_COMMENT:=# Execution wrapper that verifies SQLite vaults exist before starting the MCP listener}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_COMMENT2:=# Security hardening: isolate the MCP server from writing to the core OS}"
[ -n "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_COMMENT3+x}" ] || MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_COMMENT3='# Hardening parity with sibling mios-* daemons (log-watcher, cron-
# director, hermes-browser) -- consolidation pass 2026-05-15.'
[ -n "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_COMMENT4+x}" ] || MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_COMMENT4='# Drain timeout: MCP serves a long-lived TCP socket but in-flight
# context requests are sub-second; 30 s is generous.'
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mcp-server-runner}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_EXECSTARTPRE:=/usr/libexec/mios/mcp-init.sh}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_PROTECTHOME:=read-only}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_READWRITEPATHS:=/var/lib/mios/mcp /var/log/mios/mcp}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_RESTART:=always}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_RESTARTSEC:=5}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_TIMEOUTSTOPSEC:=30s}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_MIOS_MCP_SERVICE_UNIT_AFTER:=network.target redis.service}"
[ -n "${MIOS_UNITS_MIOS_MCP_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_MCP_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit file defining the mios-mcp.service daemon, which provides the Model Context Protocol (MCP) server for autonomous agents to access system context via a hardened, high-availability userspace listener.
# AI-related: /usr/libexec/mios/mcp-init.sh, /usr/libexec/mios/mcp-server-runner, mios-ai, redis.service'
[ -n "${MIOS_UNITS_MIOS_MCP_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_MCP_SERVICE_UNIT_COMMENT2='# High-availability context provider for autonomous agents. Pure
# userspace daemon (no kernel/audit/hardware coupling) so it runs on
# every MiOS shape -- bare-metal, Hyper-V, QEMU, WSL, Podman-WSL.
# The previous `ConditionVirtualization=!container` would silently skip
# WSL, since systemd reports WSL as a `container` virt variant.'
[ -n "${MIOS_UNITS_MIOS_MCP_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_MCP_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Agent Context Service (MCP)'
: "${MIOS_UNITS_MIOS_MCP_SERVICE_UNIT_WANTS:=redis.service}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_COMMENT:=# Degrade-open: never block boot on a failed pull}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-models-firstboot}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_SUCCESSEXITSTATUS:=0 1 2 3}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=10800}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target}"
[ -n "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: FBM first-boot large-model provisioner unit (oneshot, sentinel-guarded, degrade-open).
# Runs mios-models-firstboot once at first boot to fetch [ai].firstboot_models GGUFs; enabled via 90-mios.preset.
# AI-related: /usr/libexec/mios/mios-models-firstboot, /usr/share/mios/mios.toml'
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.models-firstboot-done}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION:=First-boot Large-model Provisioner}"
: "${MIOS_UNITS_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_ENVIRONMENT='HOME=/var/lib/mios/opencode-gateway/work,MIOS_PORT_OPENCODE_GATEWAY=${MIOS_PORT_OPENCODE_GATEWAY:-8780},MIOS_OPENCODE_HOST=127.0.0.1,MIOS_OPENCODE_BIN=/usr/lib/mios/agents/opencode/bin/opencode,MIOS_OPENCODE_MODEL=mios-opencode:latest,MIOS_OPENCODE_PROVIDER=local,MIOS_OPENCODE_CONFIG=/etc/mios/opencode/opencode.json,MIOS_OPENCODE_TIMEOUT_S=90'
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_EXECSTART:=/usr/lib/mios/agents/.venv/bin/python3 -u /usr/lib/mios/agents/opencode-gateway/server.py}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_LOCKPERSONALITY:=true}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTCONTROLGROUPS:=true}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTKERNELMODULES:=true}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTKERNELTUNABLES:=true}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_READWRITEPATHS:=/etc/mios /var/lib/mios}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_RESTARTSEC:=10s}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_RESTRICTSUIDSGID:=true}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_TIMEOUTSTARTSEC:=30s}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_WORKINGDIRECTORY:=/var/lib/mios/opencode-gateway/work}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_AFTER:=network-online.target mios-llm-light.service}"
[ -n "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that hosts the opencode-gateway on port 8633, providing a standard OpenAI-compatible /v1 API shim for the opencode CLI to enable multi-agent fan-out and local inference via mios-llm-light.
# AI-related: /usr/lib/mios/agents/opencode-gateway/server.py, /usr/lib/mios/agents/opencode/bin/opencode, /usr/lib/mios/agents/.venv, mios-llm-light.service
# R8: dropped After=mios-ai-firstboot.service -- the coder gateway rides the venv +
# the light inference lane (mios-llm-light), NOT the boot-time model fetch.'
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_COMMENT2:=# Skip cleanly if the opencode binary never landed (build-time fetch failure)}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/lib/mios/agents/opencode/bin/opencode}"
[ -n "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' OpenCode /v1 gateway (OpenAI adapter fronting the opencode CLI)'
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_DOCUMENTATION:=file:///usr/lib/mios/agents/opencode-gateway/server.py}"
: "${MIOS_UNITS_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_WANTS:=network-online.target mios-llm-light.service}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT='# SSOT env: MIOS_PG_USER / MIOS_PG_DB / MIOS_PORT_PGVECTOR / MIOS_PG_BACKUP_*
# all flow from mios.toml [pgvector] -> userenv.sh. '"'"'-'"'"' = tolerate absence
# (degrade-open to the inline defaults below).'
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT2:=# Inline-default the knobs so the unit is correct even with no env file present.}"
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT3+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT3='# Runs as root to `podman exec` into the mios-ai.pod pgvector container.
# ProtectSystem=strict / ReadWritePaths dropped so podman can reach its runtime.'
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT4+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT4='# Logical dump over loopback-trust, gzip'"'"'d + timestamped, then prune to the
# newest N. Pure POSIX sh so it runs on the minimal base. Every branch exits 0
# (degrade-open): gate-off, missing client, or a dump error logs and succeeds.'
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_ENVIRONMENT='MIOS_PG_BACKUP_ENABLE=true,MIOS_PG_BACKUP_DIR=/var/lib/mios/backups,MIOS_PG_BACKUP_KEEP=7,MIOS_PG_USER=mios,MIOS_PG_DB=mios,MIOS_PORT_PGVECTOR=${MIOS_PORT_PGVECTOR:-8600}'
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/userenv.sh}"
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_EXECSTART='/bin/sh -c '"'"'case "$$MIOS_PG_BACKUP_ENABLE" in 0|false|False|FALSE|no|off) echo "mios-pgvector-backup: disabled (MIOS_PG_BACKUP_ENABLE=$$MIOS_PG_BACKUP_ENABLE)"; exit 0 ;; esac; DIR="$$MIOS_PG_BACKUP_DIR"; [ -z "$$DIR" ] && DIR="/var/lib/mios/backups"; KEEP="$$MIOS_PG_BACKUP_KEEP"; [ -z "$$KEEP" ] && KEEP="7"; case "$$KEEP" in *[!0-9]*|"") KEEP=7 ;; esac; [ "$$KEEP" -lt 1 ] && KEEP=1; PORT="$$MIOS_PORT_PGVECTOR"; [ -z "$$PORT" ] && PORT="8432"; USR="$$MIOS_PG_USER"; [ -z "$$USR" ] && USR="mios"; DB="$$MIOS_PG_DB"; [ -z "$$DB" ] && DB="mios"; if ! command -v podman >/dev/null 2>&1; then echo "mios-pgvector-backup: podman not found on PATH -- skipping (need podman to exec pg_dump inside the pod)"; exit 0; fi; mkdir -p "$$DIR" 2>/dev/null || true; TS=$$(date -u +%%Y%%m%%dT%%H%%M%%SZ); OUT="$$DIR/mios-pgvector-$$TS.sql.gz"; RAW="$$DIR/.mios-pgvector-$$TS.sql.partial"; ERR="$$DIR/.mios-pgbackup.err"; rc=0; podman exec mios-pgvector pg_dump -h 127.0.0.1 -p "$$PORT" -U "$$USR" --no-password "$$DB" >"$$RAW" 2>"$$ERR" || rc=$$?; if [ "$$rc" -ne 0 ] || [ ! -s "$$RAW" ]; then echo "mios-pgvector-backup: pg_dump failed (rc=$$rc, degrade-open): $$(tail -n1 "$$ERR" 2>/dev/null)"; rm -f "$$RAW" "$$ERR" 2>/dev/null || true; exit 0; fi; if gzip -c "$$RAW" >"$$OUT.partial" && mv -f "$$OUT.partial" "$$OUT"; then chmod 0640 "$$OUT" 2>/dev/null || true; echo "mios-pgvector-backup: wrote $$OUT"; else echo "mios-pgvector-backup: gzip failed (degrade-open)"; rm -f "$$OUT.partial" "$$RAW" "$$ERR" 2>/dev/null || true; exit 0; fi; rm -f "$$RAW" "$$ERR" 2>/dev/null || true; N=$$(ls -1 "$$DIR"/mios-pgvector-*.sql.gz 2>/dev/null | wc -l); if [ "$$N" -gt "$$KEEP" ]; then ls -1t "$$DIR"/mios-pgvector-*.sql.gz 2>/dev/null | tail -n +$$((KEEP+1)) | while IFS= read -r f; do rm -f "$$f" && echo "mios-pgvector-backup: pruned $$f"; done; fi; exit 0'"'"''
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_AFTER:=mios-pgvector.service}"
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_COMMENT='# AI-hint: Unprivileged daily oneshot that pg_dumps the unified agent-plane Postgres+pgvector database to /var/lib/mios/backups over loopback-trust and prunes to the newest MIOS_PG_BACKUP_KEEP snapshots; degrade-open so a backup failure never blocks the DB.
# AI-related: mios-pgvector-backup.timer, mios-pgvector.service, /usr/lib/tmpfiles.d/mios-backups.conf, mios-pg-query
# /usr/lib/systemd/system/mios-pgvector-backup.service
# WS-0 pgvector durability: periodic logical backup of the unified agent-plane
# datastore (tiered memory / knowledge / skills / sessions / scratch / sys_env /
# kanban / ...). Losing pgvector is expensive, so this snapshots it daily.
#
# UNPRIVILEGED (Architectural Law 6 spirit): runs as the pgvector sysuser
# (mios-pgvector, uid 826) -- it owns /var/lib/mios/backups (tmpfiles) and
# reaches Postgres over the pg_hba loopback-trust line.
#
# DEGRADE-OPEN: every failure path (gate off, no pg_dump client, dump error)
# logs and exits 0. A backup miss must NEVER fault the boot/timer or affect the
# live DB. backup_enable ships TRUE; flip MIOS_PG_BACKUP_ENABLE=false to disable.'
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_COMMENT2='# Same virtualization guard as the pgvector container: the DB only runs on
# bare-metal/WSL (not a nested container), so there'"'"'s nothing to back up there.'
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=|!container,|wsl}"
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' daily pg_dump backup of the unified agent-plane datastore (pgvector)'
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_DOCUMENTATION:=file:///usr/lib/systemd/system/mios-pgvector-backup.service}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_WANTS:=mios-pgvector.service}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_ACCURACYSEC:=5m}"
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_COMMENT='# Daily, shortly after midnight local time. Persistent=true catches up a missed
# run (machine asleep/off at the scheduled time) on the next boot. Randomized
# delay spreads the dump off the exact minute so it doesn'"'"'t collide with other
# midnight jobs.'
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_ONCALENDAR:=*-*-* 00:30:00}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_RANDOMIZEDDELAYSEC:=15m}"
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_COMMENT='# AI-hint: Daily systemd timer that fires mios-pgvector-backup.service to snapshot the unified agent-plane Postgres+pgvector datastore, with Persistent=true so a missed run (machine off) executes at next boot.
# AI-related: mios-pgvector-backup.service, timers.target
# /usr/lib/systemd/system/mios-pgvector-backup.timer
# WS-0 pgvector durability: schedules the daily logical backup of the unified
# agent-plane datastore. The service itself is degrade-open + gated on
# MIOS_PG_BACKUP_ENABLE, so the timer can stay enabled unconditionally.'
[ -n "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' daily pgvector datastore backup schedule'
: "${MIOS_UNITS_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_DOCUMENTATION:=file:///usr/lib/systemd/system/mios-pgvector-backup.service}"
: "${MIOS_UNITS_MIOS_PODMAN_GC_SERVICE_SERVICE_EXECSTART:=/usr/bin/podman system prune -a -f}"
: "${MIOS_UNITS_MIOS_PODMAN_GC_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_PODMAN_GC_SERVICE_UNIT_COMMENT:=# AI-hint: Systemd unit that executes a forced Podman system prune to reclaim disk space from unused images and containers, specifically targeting WSL and non-containerized environments.}"
: "${MIOS_UNITS_MIOS_PODMAN_GC_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=|!container,|wsl}"
[ -n "${MIOS_UNITS_MIOS_PODMAN_GC_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_PODMAN_GC_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Podman Garbage Collection'
: "${MIOS_UNITS_MIOS_PODMAN_GC_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_PODMAN_GC_TIMER_TIMER_ONCALENDAR:=weekly}"
: "${MIOS_UNITS_MIOS_PODMAN_GC_TIMER_TIMER_PERSISTENT:=true}"
[ -n "${MIOS_UNITS_MIOS_PODMAN_GC_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_PODMAN_GC_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer unit that triggers the mios-podman-gc.service weekly to automate the removal of stale Podman containers, images, and networks to reclaim disk space.
# AI-related: mios-podman-gc, mios-podman-gc.service, timers.target'
: "${MIOS_UNITS_MIOS_PODMAN_GC_TIMER_UNIT_DESCRIPTION:=Weekly Podman Cleanup}"
: "${MIOS_UNITS_MIOS_PODMAN_PS_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_PODMAN_PS_TIMER_TIMER_ACCURACYSEC:=2s}"
: "${MIOS_UNITS_MIOS_PODMAN_PS_TIMER_TIMER_ONBOOTSEC:=10s}"
: "${MIOS_UNITS_MIOS_PODMAN_PS_TIMER_TIMER_ONUNITACTIVESEC:=15s}"
[ -n "${MIOS_UNITS_MIOS_PODMAN_PS_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_PODMAN_PS_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers mios-podman-ps.service every 15 seconds to refresh the podman container snapshot data for the MiOS dashboard display.
# AI-related: mios-podman-ps, mios-podman-ps.service, timers.target'
[ -n "${MIOS_UNITS_MIOS_PODMAN_PS_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_PODMAN_PS_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' refresh the podman container snapshot for the dashboard'
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_COMMENT:=# Hardening: a stateless loopback decision service needs nothing but Python.}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_ENVIRONMENT:=MIOS_AGENT_PIPE_DIR=/usr/lib/mios/agent-pipe}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_EXECSTART:=/usr/bin/python3 /usr/libexec/mios/mios-policy-arbiter}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_RESTARTSEC:=15s}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_UNIT_AFTER:=network-online.target mios-agent-pipe.service}"
[ -n "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit for the WS-9 out-of-process HITL policy arbiter -- runs /usr/libexec/mios/mios-policy-arbiter (a stdlib loopback HTTP service) as the mios-ai user, answering the agent-pipe'"'"'s HITL arbiter client with allow/deny verdicts decided by mios_arbiter over the operator policy. Idle/no-op until [ai].hitl_arbiter_url points at it; default policy is allow-all so enabling it changes nothing until a deny-list/block-tier is set.
# AI-related: /usr/libexec/mios/mios-policy-arbiter, /usr/lib/mios/agent-pipe/mios_arbiter.py, mios-agent-pipe.service
# /usr/lib/systemd/system/mios-policy-arbiter.service
# '"'"'MiOS'"'"' out-of-process HITL policy arbiter (WS-9). A second, operator-ownable
# opinion ON TOP of the in-process #62 HITL gate + WS-A9 PDP: the agent-pipe POSTs
# each high-risk (tier >= [ai].hitl_threshold) action here for an allow/deny
# verdict. Runs as mios-ai (least privilege); binds 127.0.0.1 only.'
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/mios-policy-arbiter}"
[ -n "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' out-of-process HITL policy arbiter (WS-9)'
: "${MIOS_UNITS_MIOS_POLICY_ARBITER_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-shell-session gc}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_SUCCESSEXITSTATUS:=0 1}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_USER:=mios-ai}"
[ -n "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_UNIT_COMMENT='# AI-hint: SHELL-01 idle reaper for the persistent PTY substrate -- kills tmux sessions idle past [shell_session].idle_s so a long-lived shell plane cannot accumulate unbounded state.
# AI-related: /usr/libexec/mios/mios-shell-session, mios-shell-session-gc.timer, /usr/share/mios/mios.toml [shell_session]'
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/mios-shell-session}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_SERVICE_UNIT_DESCRIPTION:=Reap idle MiOS shell sessions}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_TIMER_TIMER_ONBOOTSEC:=10min}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_TIMER_TIMER_ONUNITINACTIVESEC:=10min}"
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_TIMER_TIMER_PERSISTENT:=true}"
[ -n "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_SHELL_SESSION_GC_TIMER_UNIT_COMMENT='# AI-hint: Fires mios-shell-session-gc.service periodically so idle persistent shells are reclaimed without an operator.
# AI-related: mios-shell-session-gc.service'
: "${MIOS_UNITS_MIOS_SHELL_SESSION_GC_TIMER_UNIT_DESCRIPTION:=Periodic reap of idle MiOS shell sessions}"
: "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_TIMER_ACCURACYSEC:=2min}"
: "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_TIMER_ONBOOTSEC:=10min}"
: "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_TIMER_ONUNITACTIVESEC:=60min}"
: "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_TIMER_UNIT:=mios-skills-miner.service}"
[ -n "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_UNIT_COMMENT='# AI-hint: Defines the systemd timer for the mios-skills-miner.service, controlling the periodic execution interval (default 60m) for background skill mining and pattern discovery.
# AI-related: /usr/libexec/mios/mios-skills, mios-skills-miner, mios-skills, mios-skills-miner.service, timers.target
# /usr/lib/systemd/system/mios-skills-miner.timer
# Phase C.2 of the AgentOS roadmap: cadence for the background
# skill miner. Interval lifted to mios.toml [skills].
# mine_interval_minutes (default 60). Operator override:
#   sudo systemctl edit mios-skills-miner.timer
#   [Timer]
#   OnUnitActiveSec=30min
#
# Disabled by default; operator opts in (or it inherits enablement
# from the configurator HTML "Skills mining" toggle which maps to
# [skills].enable). The .service ConditionPathExists guard means a
# stripped-down deployment with the libexec script absent skips
# silently.'
[ -n "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Phase C.2 skill-miner cadence (sequential pattern mining)'
: "${MIOS_UNITS_MIOS_SKILLS_MINER_TIMER_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-skills}"
: "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_ACCURACYSEC:=1min}"
[ -n "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_COMMENT='# First refresh 2 min after boot so the chain has warmed up.
# Then every 10 min while running.'
: "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_ONBOOTSEC:=2min}"
: "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_ONUNITACTIVESEC:=10min}"
: "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_UNIT:=mios-suggestion-refresh.service}"
[ -n "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers mios-suggestion-refresh.service every 10 minutes to update OWUI starter chips based on current system state, kanban data, and recent user intents.
# AI-related: /usr/libexec/mios/mios-suggestion-refresh, mios-suggestion-refresh, mios-suggestion-refresh.service, timers.target
# /usr/lib/systemd/system/mios-suggestion-refresh.timer
# Fires mios-suggestion-refresh.service every 10 minutes so the
# OWUI starter chips revolve based on current MiOS state (recent
# kanban, daemon nudges, recent refine intents). Operators tune
# the cadence with:
#   sudo systemctl edit mios-suggestion-refresh.timer
#   [Timer]
#   OnUnitActiveSec=30min'
[ -n "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' starter-chip refresh cadence'
: "${MIOS_UNITS_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-suggestion-refresh}"
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_COMMENT:=# Never wedge boot on a pack problem.}"
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-swarm-pack-firstboot}"
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_SUCCESSEXITSTATUS:=0}"
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=120}"
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target mios-cdi-detect.service mios-ai-firstboot.service}"
[ -n "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes mios-swarm-pack-firstboot to arm concurrent small-model worker units if gpu_profile is "swarm", enforcing VRAM budgets and provisioning GGUFs during the first boot sequence.
# AI-related: /usr/libexec/mios/mios-swarm-pack-firstboot, mios-cdi-detect.service, mios-ai-firstboot.service, network-online.target
# SWARM Phase-2 (operator 2026-06-12): arm the concurrent small-model server pack
# at boot IF [dispatch].gpu_profile == "swarm" (else the script is a no-op). The
# script self-gates + enforces the VRAM budget, so this unit is safe to enable
# unconditionally; it only ever starts mios-llm-worker@<name> units when the
# operator has flipped the profile + provisioned GGUFs.'
[ -n "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_COMMENT2='# Don'"'"'t even try before the agent stack'"'"'s prerequisites; the script is idempotent.'
[ -n "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' swarm small-model pack arming (gpu_profile=swarm only)'
: "${MIOS_UNITS_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_ACCURACYSEC:=10s}"
[ -n "${MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_COMMENT='# Mirrors the daemon'"'"'s directory_entry refresh cadence (~15 min): installed
# apps / services / loaded models change far slower than container state, so a
# 15-min refresh keeps the shared snapshot current without churn. The manual
# sys_env_refresh verb covers the "I just installed X" case immediately.'
: "${MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_ONBOOTSEC:=45s}"
: "${MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_ONUNITACTIVESEC:=900s}"
: "${MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_PERSISTENT:=true}"
[ -n "${MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers the mios-sys-env-refresh service every 900 seconds to synchronize the sys_env environment cache with current system state, ensuring shared snapshots reflect recent app/service changes.
# AI-related: mios-sys-env-refresh, timers.target'
[ -n "${MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_SYS_ENV_REFRESH_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' refresh cadence for the sys_env environment cache'
: "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-userdb-render}"
[ -n "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_SERVICE_EXECSTARTPRE+x}" ] || MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_SERVICE_EXECSTARTPRE='-/usr/bin/podman exec mios-pgvector pg_isready -q -h 127.0.0.1 -p ${MIOS_PORT_PGVECTOR:-8600} -U mios -d mios'
: "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_UNIT_AFTER:=mios-pgvector.service}"
[ -n "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/mios-userdb-render to project PostgreSQL account records into systemd userdb JSON drop-ins.
# AI-related: /usr/libexec/mios/mios-userdb-render, mios-pgvector.service'
[ -n "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' PostgreSQL account systemd userdb drop-in renderer'
: "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-userdb-render}"
: "${MIOS_UNITS_MIOS_USERDB_RENDER_SERVICE_UNIT_REQUIRES:=mios-pgvector.service}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_COMMENT='# Retry the build if an image is still missing (a transient network/CDN blip
# during first install must not leave webtools permanently down).'
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-webtools-firstboot.sh}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_RESTARTSEC:=30}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_BEFORE:=mios-webtools-pod.service}"
[ -n "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_COMMENT='# WS-DEPLOY: allow the build to retry (script exits non-zero on a missing image)
# without tripping the start-limit too fast under sustained install contention.'
[ -n "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' web-tools images build-on-demand firstboot service'
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_STARTLIMITBURST:=6}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_STARTLIMITINTERVALSEC:=1200}"
: "${MIOS_UNITS_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/wsl-firstboot}"
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_AFTER:=local-fs.target}"
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_BEFORE:=systemd-user-sessions.service multi-user.target}"
[ -n "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/wsl-firstboot to perform one-time initialization tasks specifically for WSL2 instances if the first-boot flag is not yet set.
# AI-related: /usr/libexec/mios/wsl-firstboot, systemd-user-sessions.service, local-fs.target, multi-user.target'
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.wsl-firstboot-done}"
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=wsl}"
[ -n "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' WSL2 First Boot Initialization'
: "${MIOS_UNITS_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS}"
: "${MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_INSTALL_WANTEDBY:=multi-user.target default.target}"
[ -n "${MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_PATH_COMMENT+x}" ] || MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_PATH_COMMENT='# Trigger whenever flatpak adds/removes an exported .desktop (any
# system-wide install / uninstall touches this dir mtime).'
: "${MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_PATH_PATHCHANGED:=/var/lib/flatpak/exports/share/applications,/var/lib/flatpak/exports/share/icons}"
[ -n "${MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_COMMENT+x}" ] || MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_COMMENT='# AI-hint: Systemd path unit that triggers a synchronization script when flatpak application or icon files are modified in the export directory, ensuring .desktop files are updated for WSL integration.
# AI-related: mios-is-wsl, multi-user.target, default.target'
: "${MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_CONDITIONPATHEXISTS:=/run/mios-is-wsl}"
[ -n "${MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNITS_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Re-fire flatpak->WSL .desktop sync when flatpak installs/uninstalls land'
: "${MIOS_UNITS_OPEN_WEBUI:=mios-open-webui.service}"
: "${MIOS_UNITS_PGVECTOR:=mios-pgvector.service}"
: "${MIOS_UNITS_SEARXNG:=mios-searxng.service}"
[ -n "${MIOS_UNITS_USER_SESSION+x}" ] || MIOS_UNITS_USER_SESSION='user@'"${MIOS_UID}"'.service'
: "${MIOS_UNITS_VAR_HOME_MOUNT_INSTALL_WANTEDBY:=remote-fs.target}"
: "${MIOS_UNITS_VAR_HOME_MOUNT_MOUNT_OPTIONS:=secretfile=/etc/ceph/mios.secret,noatime,_netdev,nofail,x-systemd.device-timeout=30,x-systemd.mount-timeout=30}"
: "${MIOS_UNITS_VAR_HOME_MOUNT_MOUNT_TYPE:=ceph}"
: "${MIOS_UNITS_VAR_HOME_MOUNT_MOUNT_WHAT:=mios@.cephfs=/home}"
: "${MIOS_UNITS_VAR_HOME_MOUNT_MOUNT_WHERE:=/var/home}"
: "${MIOS_UNITS_VAR_HOME_MOUNT_UNIT_AFTER:=ceph.target network-online.target}"
[ -n "${MIOS_UNITS_VAR_HOME_MOUNT_UNIT_COMMENT+x}" ] || MIOS_UNITS_VAR_HOME_MOUNT_UNIT_COMMENT='# AI-hint: Systemd mount unit for mapping the CephFS cluster to /var/home, providing persistent storage for user home directories using the mios.secret for authentication.
# AI-related: ceph.target, network-online.target, x-systemd.mount, remote-fs.target'
: "${MIOS_UNITS_VAR_HOME_MOUNT_UNIT_CONDITIONPATHEXISTS:=/etc/ceph/ceph.conf,/etc/ceph/mios.secret}"
: "${MIOS_UNITS_VAR_HOME_MOUNT_UNIT_DESCRIPTION:=CephFS mount for user home directories}"
: "${MIOS_UNITS_VAR_HOME_MOUNT_UNIT_DOCUMENTATION:=man:mount.ceph(8)}"
: "${MIOS_UNITS_VAR_HOME_MOUNT_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_INSTALL_WANTEDBY:=remote-fs.target}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_MOUNT_OPTIONS:=secretfile=/etc/ceph/mios.secret,noatime,_netdev,nofail,x-systemd.device-timeout=30,x-systemd.mount-timeout=30}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_MOUNT_TYPE:=ceph}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_MOUNT_WHAT:=mios@.cephfs=/containers}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_MOUNT_WHERE:=/var/lib/containers}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_UNIT_AFTER:=ceph.target network-online.target}"
[ -n "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_UNIT_COMMENT+x}" ] || MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_UNIT_COMMENT='# AI-hint: Systemd mount unit for the CephFS storage backend at /var/lib/containers, used by the system to provide persistent, shared storage for Podman containers via the mios.secret credential.
# AI-related: ceph.target, network-online.target, x-systemd.mount, remote-fs.target'
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_UNIT_CONDITIONPATHEXISTS:=/etc/ceph/ceph.conf,/etc/ceph/mios.secret}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_UNIT_DESCRIPTION:=CephFS mount for Podman container storage}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_UNIT_REQUIRESMOUNTSFOR:=/var/lib}"
: "${MIOS_UNITS_VAR_LIB_CONTAINERS_MOUNT_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNITS_VAR_LIB_MACHINES_MOUNT_MOUNT_OPTIONS:=loop}"
: "${MIOS_UNITS_VAR_LIB_MACHINES_MOUNT_MOUNT_TYPE:=btrfs}"
: "${MIOS_UNITS_VAR_LIB_MACHINES_MOUNT_MOUNT_WHAT:=/var/lib/machines.raw}"
: "${MIOS_UNITS_VAR_LIB_MACHINES_MOUNT_MOUNT_WHERE:=/var/lib/machines}"
[ -n "${MIOS_UNITS_VAR_LIB_MACHINES_MOUNT_UNIT_COMMENT+x}" ] || MIOS_UNITS_VAR_LIB_MACHINES_MOUNT_UNIT_COMMENT='#  SPDX-License-Identifier: LGPL-2.1-or-later
#
#  This file is part of systemd.
#
#  systemd is free software; you can redistribute it and/or modify it
#  under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 2.1 of the License, or
#  (at your option) any later version.
# This unit is required for pre-240 versions of systemd that automatically set
# up /var/lib/machines.raw as loopback-mounted btrfs file system. Later
# versions don'"'"'t do that anymore, but let'"'"'s keep minimal compatibility by
# mounting the image still, if it exists.'
: "${MIOS_UNITS_VAR_LIB_MACHINES_MOUNT_UNIT_CONDITIONPATHEXISTS:=/var/lib/machines.raw}"
: "${MIOS_UNITS_VAR_LIB_MACHINES_MOUNT_UNIT_DESCRIPTION:=Virtual Machine and Container Storage (Compatibility)}"
: "${MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_MOUNT_TYPE:=rpc_pipefs}"
: "${MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_MOUNT_WHAT:=sunrpc}"
: "${MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_MOUNT_WHERE:=/var/lib/nfs/rpc_pipefs}"
: "${MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_AFTER:=systemd-tmpfiles-setup.service}"
[ -n "${MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_COMMENT+x}" ] || MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_COMMENT='# AI-hint: Mounts the RPC pipe file system at /var/lib/nfs/rpc_pipefs to provide the necessary mount points for NFS RPC services and client operations.
# AI-related: systemd-tmpfiles-setup.service, umount.target'
: "${MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_CONFLICTS:=umount.target}"
: "${MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_DEFAULTDEPENDENCIES:=no}"
: "${MIOS_UNITS_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_DESCRIPTION:=RPC Pipe File System}"
: "${MIOS_UNITS_WSL_FIRSTBOOT:=mios-wsl-firstboot.service}"
: "${MIOS_UNIT_AGENT_PIPE:=mios-agent-pipe.service}"
: "${MIOS_UNIT_CEPH:=mios-ceph.service}"
: "${MIOS_UNIT_COCKPIT_LINK:=mios-cockpit-link.service}"
: "${MIOS_UNIT_CODE_SERVER:=mios-code-server.service}"
: "${MIOS_UNIT_FIRSTBOOT_TARGET:=mios-firstboot.target}"
: "${MIOS_UNIT_FORGE:=mios-forge.service}"
: "${MIOS_UNIT_FORGE_RUNNER:=mios-forgejo-runner.service}"
: "${MIOS_UNIT_HERMES:=mios-hermes.service}"
: "${MIOS_UNIT_HERMES_FIRSTBOOT:=mios-hermes-firstboot.service}"
: "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/hermes-worker-firstboot}"
: "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_AFTER:=local-fs.target systemd-tmpfiles-setup.service}"
: "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_BEFORE:=hermes-worker.service multi-user.target}"
[ -n "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Oneshot that seeds the non-thin Hermes WORKER config (/var/lib/mios/hermes-worker/config.yaml) from the vendor template before hermes-worker.service starts. Distinct from mios-hermes-firstboot (which owns and re-thins the primary :8642 config); this one NEVER touches the primary path.
# AI-related: /usr/libexec/mios/hermes-worker-firstboot, /usr/share/mios/hermes/config-worker.yaml, /var/lib/mios/hermes-worker/config.yaml, hermes-worker.service'
: "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/hermes-worker-firstboot}"
[ -n "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Worker first-boot config seed (:8643 non-thin worker)'
: "${MIOS_UNIT_HERMES_WORKER_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS}"
: "${MIOS_UNIT_HERMES_WORKER_PATH_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_HERMES_WORKER_PATH_PATH_PATHEXISTS:=/usr/lib/mios/agents/.venv/bin/hermes}"
: "${MIOS_UNIT_HERMES_WORKER_PATH_PATH_UNIT:=hermes-worker.service}"
: "${MIOS_UNIT_HERMES_WORKER_PATH_UNIT_AFTER:=hermes-worker-firstboot.service}"
[ -n "${MIOS_UNIT_HERMES_WORKER_PATH_UNIT_COMMENT+x}" ] || MIOS_UNIT_HERMES_WORKER_PATH_UNIT_COMMENT='# AI-hint: Systemd path unit (WS-A4 boot-ordering fix) that watches for the Hermes venv binary and (re)starts hermes-worker.service once it exists, so a worker that failed its ConditionPathExists at first boot (venv not yet built) comes up automatically when the venv lands -- instead of staying inactive until a manual restart.
# AI-related: hermes-worker.service, hermes-worker-firstboot.service, /usr/lib/mios/agents/.venv/bin/hermes, multi-user.target, 90-mios.preset
# /usr/lib/systemd/system/hermes-worker.path
# WS-A4 (operator 2026-06-22): hermes-worker.service carries
# ConditionPathExists=/usr/lib/mios/agents/.venv/bin/hermes. On a fresh boot the
# venv is not built yet -> the Condition fails -> the worker is skipped, and once
# the venv-build/firstboot finishes systemd never retries it (so :8643 stays
# inactive forever and the orchestrator silently runs single-agent). This .path
# closes that gap: PathExists is satisfied the moment the venv binary EXISTS
# (on creation AND if already present at activation), starting the worker. The
# worker'"'"'s own Condition still guards against a half-built venv; start is idempotent.'
[ -n "${MIOS_UNIT_HERMES_WORKER_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_HERMES_WORKER_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"' watch for the Hermes venv -> (re)start hermes-worker'
: "${MIOS_UNIT_HERMES_WORKER_PATH_UNIT_DOCUMENTATION:=file:///usr/lib/systemd/system/hermes-worker.service}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_COMMENT='# SEPARATE HERMES_HOME + HOME => fully isolated pid/lock/state/DBs/config AND a
# distinct $HOME/XDG so the discord scope-lock dir (derived from $HOME) can
# never collide with the :8642 gateway'"'"'s. Discord is off here regardless.'
[ -n "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_ENVIRONMENT='HOME=/var/lib/mios/hermes-worker,HERMES_HOME=/var/lib/mios/hermes-worker,SEARXNG_URL=http://localhost:'"${MIOS_PORT_SEARXNG}"',MIOS_CRAWL_SERVICE_URL=http://127.0.0.1:'"${MIOS_PORT_CRAWL4AI}"',FIRECRAWL_API_URL=http://127.0.0.1:'"${MIOS_PORT_FIRECRAWL}"',PORT='"${MIOS_PORT_HERMES}"',API_SERVER_PORT='"${MIOS_PORT_HERMES}"',HERMES_BACKEND_BASE_URL=http://localhost:'"${MIOS_PORT_VLLM}"',HERMES_MAX_TOKENS=8192,BROWSER_CDP_URL=http://localhost:${MIOS_PORT_CHROME_CDP_WORKER:-9223}'
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env,-/etc/mios/hermes/api.env}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_EXECSTART:=/usr/lib/mios/agents/.venv/bin/hermes gateway run}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_EXECSTARTPRE:=+/usr/bin/install -d -o mios-ai -g mios-ai -m 0700 /var/lib/mios/hermes-worker,-/usr/bin/python3 /usr/libexec/mios/mios-hermes-discord-reactions-patch /usr/lib/mios/agents/.venv/lib/python3.14/site-packages/gateway/platforms/discord.py,-+/usr/libexec/mios/mios-hermes-dashboard-auth-stub}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_LIMITNOFILE:=1048576}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_NONEWPRIVILEGES:=false}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_PRIVATETMP:=yes}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_PROTECTHOME:=false}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_READWRITEPATHS:=/etc/mios /var/lib/mios /run/mios-launcher}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_RESTARTSEC:=10s}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_TIMEOUTSTARTSEC:=300s}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_TIMEOUTSTOPSEC:=240s}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_AFTER:=network-online.target mios-llm-heavy.service mios-llm-light.service hermes-worker-firstboot.service}"
[ -n "${MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit for the SECOND (non-thin) Hermes WORKER gateway on :8643 -- a real agent that runs its OWN native browser/CDP/terminal/skills tool loop with its OWN inference on the heavy lane (:11441 mios-heavy). Coexists with the thin :8642 Discord gateway (hermes-agent.service) via a SEPARATE HERMES_HOME and no Discord token.
# AI-related: /usr/lib/mios/agents/.venv/bin/hermes, /var/lib/mios/hermes-worker, /var/lib/mios/hermes-worker/config.yaml, /etc/mios/hermes/api.env, hermes-agent.service, mios-hermes-browser-worker.service, mios-llm-heavy.service, mios-llm-light.service
# /usr/lib/systemd/system/hermes-worker.service
#
# The MiOS Hermes WORKER (P1, operator 2026-06-19). A SECOND `hermes gateway
# run` instance, fully ISOLATED from the live :8642 Discord gateway:
#   * SEPARATE HERMES_HOME=/var/lib/mios/hermes-worker => its own gateway.pid /
#     gateway.lock / gateway_state.json / state.db / kanban.db / config.yaml.
#     No shared-DB WAL contention with the :8642 instance.
#   * API_SERVER_PORT=8643 (the LOAD-BEARING bind var -- `PORT` is inert; Hermes
#     reads API_SERVER_PORT and otherwise binds DEFAULT_PORT=8642).
#   * NO discord.env / NO DISCORD_BOT_TOKEN => the Discord adapter never calls
#     _acquire_platform_lock('"'"'discord-bot-token'"'"', ...), so the host-global
#     gateway-locks/discord-bot-token-*.lock held by the :8642 gateway is never
#     contended (no SIGTERM flap). Discord stays the EXCLUSIVE job of :8642.
#   * NO --replace: the worker'"'"'s HERMES_HOME-scoped pidfile is its own; the
#     :8642 gateway'"'"'s eviction scan is profile/HERMES_HOME-scoped (only --all
#     crosses profiles, which is not used) so neither instance touches the other.
#
# This worker is the WORKER-DISPATCH target of [agents.hermes].endpoint in
# mios.toml (repointed :11441 -> :8643 in P1). It does its OWN heavy-lane
# inference (:11441 mios-heavy) so it never relays to :8640 -- no recursion.'
[ -n "${MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_COMMENT2='# R8: dropped After=mios-ai-firstboot.service -- the worker rides the venv + its own
# provisioner (hermes-worker-firstboot) + the inference lanes, NOT the boot-time
# GGUF/vLLM fetch owned by mios-ai-firstboot.'
[ -n "${MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_COMMENT3+x}" ] || MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_COMMENT3='# Skip cleanly if the direct install didn'"'"'t land.'
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/lib/mios/agents/.venv/bin/hermes}"
[ -n "${MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Worker (non-thin agent, native tool loop, :8643)'
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_DOCUMENTATION:=https://github.com/NousResearch/hermes-agent}"
: "${MIOS_UNIT_HERMES_WORKER_SERVICE_UNIT_WANTS:=network-online.target mios-llm-heavy.service mios-llm-light.service hermes-worker-firstboot.service}"
: "${MIOS_UNIT_K3S:=mios-k3s.service}"
: "${MIOS_UNIT_LLM_LIGHT:=mios-llm-light.service}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_COMMENT:=# Ensure postgres container is ready before launching the daemon}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-account-sync --daemon}"
[ -n "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_EXECSTARTPRE+x}" ] || MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_EXECSTARTPRE='/usr/bin/podman exec mios-pgvector pg_isready -q -h 127.0.0.1 -p ${MIOS_PORT_PGVECTOR:-8600} -U mios -d mios'
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_RESTART:=always}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_RESTARTSEC:=10s}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_AFTER:=mios-pgvector.service}"
[ -n "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/mios-account-sync in daemon mode to keep local Linux accounts synchronized with PostgreSQL accounts and aliases.
# AI-related: /usr/libexec/mios/mios-account-sync, mios-pgvector.service'
[ -n "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' live PostgreSQL-to-OS user account sync daemon'
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-account-sync}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_REQUIRES:=mios-pgvector.service}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_STARTLIMITBURST:=5}"
: "${MIOS_UNIT_MIOS_ACCOUNT_SYNC_SERVICE_UNIT_STARTLIMITINTERVALSEC:=300}"
: "${MIOS_UNIT_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_PATH_PATHCHANGED:=/usr/lib/containers/storage/overlay-images,/usr/lib/containers/storage/overlay-containers,/usr/lib/containers/storage/overlay-layers,/usr/lib/containers/storage/libpod}"
: "${MIOS_UNIT_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_PATH_UNIT:=mios-additionalimagestores-perms.service}"
[ -n "${MIOS_UNIT_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_COMMENT='# AI-hint: Systemd path unit that monitors container storage directories for permission changes and triggers mios-additionalimagestores-perms.service to restore go+rX permissions on image store subdirectories.
# AI-related: mios-additionalimagestores-perms, mios-additionalimagestores-perms.service, multi-user.target
# Path-watcher companion to mios-additionalimagestores-perms.service.
# Re-runs the chmod whenever any of the additional image store'"'"'s per-
# driver subdirs change (e.g. podman extracts new layers and resets
# the perms back to 0700 -- happens on first runtime pull into the
# additional store, though that'"'"'s atypical since this store is built
# at OCI bake time and meant to be read-only at runtime).
#
# Together with the .service unit (runs at boot) this makes the
# go+rX state self-healing: any way the perms get reset, they snap
# back within seconds.'
: "${MIOS_UNIT_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_CONDITIONPATHISDIRECTORY:=/usr/lib/containers/storage}"
[ -n "${MIOS_UNIT_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_ADDITIONALIMAGESTORES_PERMS_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"': watch additionalimagestores for perm changes; retrigger chmod'
: "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-adguard-firstboot}"
: "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target tailscaled.service}"
: "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_BEFORE:=mios-adguard.service}"
[ -n "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/mios-adguard-firstboot to generate the AdGuardHome.yaml config from mios.toml, injecting Tailscale IPs before the AdGuard container starts.
# AI-related: /usr/libexec/mios/mios-adguard-firstboot, /etc/mios/adguard/AdGuardHome.yaml, tailscaled.service, mios-adguard.service, network-online.target
# /usr/lib/systemd/system/mios-adguard-firstboot.service
# Generates /etc/mios/adguard/AdGuardHome.yaml from mios.toml [adguard]/[ports]
# + the live Tailscale IP/MagicDNS suffix, BEFORE the AdGuard container starts.
# Idempotent + non-destructive (skips if the config already exists), so it is
# safe to leave enabled across boots. mios-adguard.container Requires= + After=
# this unit, so it is pulled in automatically; it is also enabled directly for
# fresh installs.'
: "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/mios-adguard-firstboot}"
[ -n "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' AdGuard Home first-boot config generator'
: "${MIOS_UNIT_MIOS_ADGUARD_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_INSTALL_WANTEDBY:=multi-user.target default.target}"
[ -n "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_COMMENT='# systemd does NOT expand bash ${VAR:-default} in ExecStart -- it resolves to
# empty (code-server then dies "Invalid URL"). Set the defaults here; install.env
# (the mios.toml -> env SSOT bridge) overrides them when present. ExecStart uses
# plain ${VAR}.'
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_COMMENT2:=# Build the local super-container image on first deploy (idempotent no-op after).}"
[ -n "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_ENVIRONMENT='MIOS_PORT_CODE_SERVER=${MIOS_PORT_CODE_SERVER:-8900},MIOS_DEFAULT_PASSWORD=mios'
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
[ -n "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_EXECSTART='/usr/sbin/podman run --replace --name mios-agents --network=host --env PASSWORD='"${MIOS_DEFAULT_PASSWORD}"' --env MIOS_A2O_ENGINE=agy --env MIOS_A2O_WORK=/mnt/mios-root --env MIOS_A2O_ORCH_ENGINE='"${MIOS_A2O_ORCH_ENGINE}"' --env MIOS_A2O_ORCH_MODEL='"${MIOS_A2O_ORCH_MODEL}"' --env MIOS_A2O_ORCH_EFFORT='"${MIOS_A2O_ORCH_EFFORT}"' --env MIOS_A2O_LANE_A_ENGINE='"${MIOS_A2O_LANE_A_ENGINE}"' --env MIOS_A2O_LANE_A_MODEL='"${MIOS_A2O_LANE_A_MODEL}"' --env MIOS_A2O_LANE_A_EFFORT='"${MIOS_A2O_LANE_A_EFFORT}"' --env MIOS_A2O_LANE_B_ENGINE='"${MIOS_A2O_LANE_B_ENGINE}"' --env MIOS_A2O_LANE_B_MODEL='"${MIOS_A2O_LANE_B_MODEL}"' --env MIOS_A2O_LANE_B_EFFORT='"${MIOS_A2O_LANE_B_EFFORT}"' --env MIOS_A2O_CLAUDE_EFFORT_FLAG='"${MIOS_A2O_CLAUDE_EFFORT_FLAG}"' --env MIOS_A2O_AGY_EFFORT_FLAG='"${MIOS_A2O_AGY_EFFORT_FLAG}"' --env MIOS_A2O_GEMINI_EFFORT_FLAG='"${MIOS_A2O_GEMINI_EFFORT_FLAG}"' --volume /:/mnt/mios-root:rw,rslave --volume /var/lib/mios/agents:/home/coder:rw localhost/mios-agents:latest --bind-addr 0.0.0.0:8800 /mnt/mios-root'
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_EXECSTARTPRE:=/usr/libexec/mios/mios-agents-firstboot.sh}"
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_EXECSTOP:=/usr/sbin/podman stop -t 10 mios-agents}"
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_RESTARTSEC:=10s}"
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_TIMEOUTSTARTSEC:=1200s}"
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_UNIT_AFTER:=network-online.target podman.socket}"
[ -n "${MIOS_UNIT_MIOS_AGENTS_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_AGENTS_SERVICE_UNIT_COMMENT='# AI-hint: Runs the mios-agents A2O super-container (code-server IDE + tmux war room + Claude CLI + agy/Gemini + the mios-a2o muxer) as a systemd-managed container. ExecStartPre builds the local image if absent; ExecStart runs it every boot on the code-server port MIOS_PORT_CODE_SERVER (mios-agents REPLACES the retired mios-code-server -- one IDE, no duplicate service).
# AI-related: /usr/share/mios/agents/Containerfile, /usr/share/mios/agents/mios-a2o, /usr/libexec/mios/mios-agents-firstboot.sh, /etc/mios/install.env, /var/lib/mios/agents
# /usr/lib/systemd/system/mios-agents.service'
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/share/mios/agents/Containerfile}"
[ -n "${MIOS_UNIT_MIOS_AGENTS_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_AGENTS_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' A2O agents super-container (Claude + agy/Gemini + tmux war room + code-server)'
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_UNIT_DOCUMENTATION:=https://github.com/mios-dev/MiOS/blob/main/usr/share/mios/agents/ACTIVATION.md}"
: "${MIOS_UNIT_MIOS_AGENTS_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_ENVIRONMENT='MIOS_PORT_AGENT_PIPE=${MIOS_PORT_AGENT_PIPE:-8700},MIOS_AGENT_PIPE_BACKEND_LIGHT=1,MIOS_AI_MODEL=granite4.1:8b,MIOS_NO_TOOL_CHOICE_HINTS=11436,MIOS_KV_PAGING_HINTS=11436,11450,MIOS_LLM_API_HINTS=,MIOS_REFINE_TIMEOUT_S=45,MIOS_POLISH_TIMEOUT_S=45,MIOS_REFINE_MAX_TOKENS=1200,MIOS_AGENT_MEMORY_RECALL=1,MIOS_PASSPORT_AGENT_NAME=agent-pipe'
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/agent-pipe.env,-/etc/mios/install.env}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_EXECSTART:=/usr/lib/mios/agents/.venv/bin/python3 -u /usr/lib/mios/agent-pipe/server.py}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_NONEWPRIVILEGES:=yes}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_PRIVATETMP:=yes}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_PROTECTHOME:=yes}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_READONLYPATHS:=/var/lib/mios/agent-passports}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_READWRITEPATHS:=/var/lib/mios/agent-pipe /var/lib/mios/skills /var/log /var/lib/mios/agent-env /var/lib/mios/ai}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_RESTARTSEC:=5s}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_SUPPLEMENTARYGROUPS:=mios-hermes}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_TIMEOUTSTARTSEC:=60s}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_SERVICE_WORKINGDIRECTORY:=/var/lib/mios/agent-pipe}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_AFTER:=network-online.target mios-pgvector.service mios-passport-provision.service}"
[ -n "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit defining the agent-pipe FastAPI service which acts as a router, refiner, and critic for the Hermes gateway, routing inference requests to the llama.cpp light lane (mios-llm-light); the lane port is the single SSOT key [ports].llm_light (MIOS_PORT_LLM_LIGHT), composed in server.py via _LIGHT_BASE.
# AI-related: /usr/lib/mios/agent-pipe/server.py, /etc/mios/install.env, /etc/mios/agent-pipe.env, mios-pgvector, mios-passport-provision, mios-ai, mios-hermes'
[ -n "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT2='# R8: NOT ordered After=mios-ai-firstboot.service. The plane needs the VENV (baked
# into the image) + pgvector, NOT the boot-time model fetch; ordering behind
# firstboot'"'"'s multi-GB download blocked the router for the whole download. firstboot
# `systemctl restart --no-block`s this unit once models land, so the edge is redundant.'
[ -n "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT3+x}" ] || MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT3='# R6: the pipe touches pgvector on every route, so upgrade the DB edge from After=
# (ordering only) to a hard Requires= -- a missing DB should hold/fail the unit.'
[ -n "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT4+x}" ] || MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT4='# R6: bound the existing Restart=on-failure so a DB-down window (many quick
# restarts) can'"'"'t trip the default 5/10s start limit and land permanently failed.'
[ -n "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT5+x}" ] || MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_COMMENT5='# The venv python is baked into the FINAL image, but on the podman-MiOS-DEV substrate it is
# built at first boot by mios-ai-firstboot. Skip (rather than 203/EXEC-fail) until it exists.'
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/lib/mios/agents/.venv/bin/python3}"
[ -n "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Agent Pipe (router + refine + critic FastAPI; fronts hermes for every gateway)'
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_DOCUMENTATION:=file:///usr/lib/mios/agent-pipe/server.py}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_REQUIRES:=mios-pgvector.service}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_STARTLIMITBURST:=5}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_STARTLIMITINTERVALSEC:=300}"
: "${MIOS_UNIT_MIOS_AGENT_PIPE_SERVICE_UNIT_WANTS:=network-online.target mios-passport-provision.service}"
: "${MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_INSTALL_WANTEDBY:=timers.target}"
[ -n "${MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_TIMER_COMMENT='# 2 min after boot (agent-pipe up by then), then every 15 min so the role
# SYSTEMs track catalog/SSOT changes and the peer list tracks the live fleet.'
: "${MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_TIMER_ONBOOTSEC:=2min}"
: "${MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_TIMER_ONUNITACTIVESEC:=15min}"
: "${MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_TIMER_PERSISTENT:=true}"
[ -n "${MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers mios-aios-refresh.service every 15 minutes to synchronize the Single Source of Truth (SSOT) and update the A2A fleet discovery peer list.
# AI-related: mios-aios-refresh, mios-aios-refresh.service, timers.target'
: "${MIOS_UNIT_MIOS_AIOS_REFRESH_TIMER_UNIT_DESCRIPTION:=Periodic MiOS AIOS refresh (SSOT role SYSTEMs + A2A fleet discovery)}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_COMMENT='# Cap a hung fetch (multi-GB model download) at 10min so it can'"'"'t wedge the unit
# forever; the timer re-fires the run afterwards. (Was 2400s.)'
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_COMMENT2+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_COMMENT2='# The script reads MIOS_LLAMACPP_BAKE_MODELS (the GGUF download spec) +
# MIOS_AI_* from the env bridge. Without this, a fresh systemd boot has an
# EMPTY environment -> bake_models reads empty -> "GGUFs not baked" -> the
# llm-light lane stays inert forever. The leading '"'"'-'"'"' makes it optional so
# the unit still starts (and retries) if the bridge isn'"'"'t generated yet.
# install-robustness 2026-06-21.'
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-ai-firstboot}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=1800}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target}"
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes the mios-ai-firstboot script to provision the AI agent virtual environment and download llama.cpp GGUF models if the .ai-firstboot-done sentinel is missing.
# AI-related: 72-hermes-agent.sh, /usr/libexec/mios/mios-ai-firstboot, mios-ai-firstboot, mios-dev, mios-llm-light.service, network-online.target
# Completes the build-time AI setup on deployments that didn'"'"'t bake it (the
# overlay-provisioned dev VM, WSL imports, etc.). 72-hermes-agent.sh'"'"'s header
# explicitly anticipates this: "a firstboot retry can complete it later".
# Needs network (pip + model pull); GGUF blobs come from Hugging Face.'
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT2='# The script writes the sentinel ONLY when both the venv and the GGUFs are
# present, so a network-less first boot simply retries on the next one.'
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT3+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_COMMENT3='# Retry is owned by mios-ai-firstboot.timer (OnBootSec + OnUnitInactiveSec), NOT
# an in-unit Restart=on-failure / StartLimitBurst storm. The script degrades open
# (exit 0) on a partial provision, so the unit shows success and the timer simply
# re-fires it on its cadence until the sentinel above is written.'
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.ai-firstboot-done}"
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' AI first-boot provisioning (agent venv + llama.cpp GGUFs)'
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/mios-dev/mios}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_INSTALL_WANTEDBY:=timers.target}"
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_TIMER_COMMENT='# First retry shortly after boot, then every 10min while the service sits
# inactive and the sentinel is still absent. Persistent catches up a missed
# window across a shutdown. The timer OWNS retry now (the .service no longer
# carries Restart=on-failure / StartLimitBurst).'
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_TIMER_ONBOOTSEC:=2min}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_TIMER_ONUNITINACTIVESEC:=10min}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_TIMER_UNIT:=mios-ai-firstboot.service}"
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_UNIT_COMMENT='# AI-hint: Defines the systemd timer for mios-ai-firstboot.service, controlling post-boot AI provisioning retries until the sentinel file is present.
# AI-related: /var/lib/mios/.ai-firstboot-done, mios-ai-firstboot.service, timers.target
# /usr/lib/systemd/system/mios-ai-firstboot.timer
# Retries the first-boot AI stack deployment if it didn'"'"'t complete on
# initial boot (e.g. machine rebooted mid-pull, or GPU drivers were
# mid-dkms build). The timer is enabled by default so the attempt happens
# automatically, but is gated on the absence of the sentinel file in
# place. The .service degrades open (exit 0) on a partial provision and carries
# ConditionPathExists=!<sentinel>, so once /var/lib/mios/.ai-firstboot-done is
# written the timer-fired run no-ops. The same condition here stops the timer
# itself from firing needlessly once provisioning is complete.'
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.ai-firstboot-done}"
[ -n "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' AI Plane First-Boot Provisioning Retry Schedule'
: "${MIOS_UNIT_MIOS_AI_FIRSTBOOT_TIMER_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-ai-firstboot-provision.sh}"
: "${MIOS_UNIT_MIOS_AI_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_AI_TARGET_UNIT_AFTER:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_AI_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_AI_TARGET_UNIT_COMMENT='# AI-hint: systemd target grouping all MiOS AI plane services (T-076).
# usr/lib/systemd/system/mios-ai.target'
: "${MIOS_UNIT_MIOS_AI_TARGET_UNIT_DESCRIPTION:=MiOS AI Services Target}"
: "${MIOS_UNIT_MIOS_AI_TARGET_UNIT_WANTS:=mios-agent-pipe.service}"
: "${MIOS_UNIT_MIOS_BOOTC_SWITCH_PATH_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_BOOTC_SWITCH_PATH_PATH_PATHCHANGED:=/var/lib/mios/forge-runner/last-build.txt}"
: "${MIOS_UNIT_MIOS_BOOTC_SWITCH_PATH_PATH_UNIT:=mios-bootc-switch.service}"
[ -n "${MIOS_UNIT_MIOS_BOOTC_SWITCH_PATH_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_BOOTC_SWITCH_PATH_UNIT_COMMENT='# AI-hint: Systemd path unit that monitors /var/lib/mios/forge-runner/last-build.txt to trigger mios-bootc-switch.service, automating the bootc kernel/image switch immediately after a Forgejo Runner build completes.
# AI-related: /usr/libexec/mios/bootc-switch-from-build.sh, mios-bootc-switch, mios-bootc-switch.service, multi-user.target
# /usr/lib/systemd/system/mios-bootc-switch.path
# Watches the build-output sentinel that the Forgejo Runner workflow
# writes after a successful `podman build`. PathChanged fires on
# either creation or modification, so re-running the workflow with
# the same image ref still triggers a re-stage (bootc switch is
# idempotent on identical refs -- this is fine).'
[ -n "${MIOS_UNIT_MIOS_BOOTC_SWITCH_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_BOOTC_SWITCH_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"' watch for Forgejo Runner build output -> bootc switch'
: "${MIOS_UNIT_MIOS_BOOTC_SWITCH_PATH_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/bootc-switch-from-build.sh}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-bound-images-firstboot}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_SUCCESSEXITSTATUS:=0 1 2 3}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=10800}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target}"
[ -n "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: FBM first-boot bound-image provisioner unit (oneshot, sentinel-guarded, degrade-open).
# Runs mios-bound-images-firstboot once at first boot to pull [ai].firstboot_bound_images; enabled via 90-mios.preset.
# AI-related: /usr/libexec/mios/mios-bound-images-firstboot, /usr/share/mios/mios.toml'
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.bound-images-firstboot-done}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION:=First-boot Bound Images Provisioner}"
: "${MIOS_UNIT_MIOS_BOUND_IMAGES_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/ceph-bootstrap.sh}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_EXECSTARTPOST:=/usr/bin/touch /var/lib/ceph/.bootstrapped,-/bin/chmod 0600 /etc/ceph/ceph.client.admin.keyring}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_STANDARDERROR:=journal+console}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_STANDARDOUTPUT:=journal+console}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_TIMEOUTSTARTSEC:=600}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_AFTER:=network-online.target podman.socket}"
[ -n "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit to execute /usr/libexec/mios/ceph-bootstrap.sh script to initialize the Ceph cluster (first boot only).
# AI-related: /usr/libexec/mios/ceph-bootstrap.sh, podman.socket, network-online.target, multi-user.target'
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/etc/ceph/ceph.conf,!/var/lib/ceph/.bootstrapped}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=no}"
[ -n "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Ceph Cluster Bootstrap'
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_DOCUMENTATION:=https://docs.ceph.com/en/latest/cephadm/}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_STARTLIMITINTERVALSEC:=0}"
: "${MIOS_UNIT_MIOS_CEPH_BOOTSTRAP_SERVICE_UNIT_WANTS:=network-online.target podman.socket}"
: "${MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_INSTALL_WANTEDBY:=sockets.target}"
: "${MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_SOCKET_BINDIPV6ONLY:=both}"
[ -n "${MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_SOCKET_LISTENSTREAM+x}" ] || MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_SOCKET_LISTENSTREAM='0.0.0.0:'"${MIOS_PORT_COCKPIT_LINK}"
[ -n "${MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_UNIT_COMMENT='# AI-hint: Socket file for mios-cockpit-link proxy. Maps port 8091 on host/WSL to the cockpit service.
# AI-related: usr/lib/systemd/system/mios-cockpit-link.service'
: "${MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_UNIT_CONDITIONVIRTUALIZATION:=!container}"
[ -n "${MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_COCKPIT_LINK_SOCKET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Cockpit Link Proxy Socket'
: "${MIOS_UNIT_MIOS_COMPUTE_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_COMPUTE_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNIT_MIOS_COMPUTE_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_COMPUTE_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_COMPUTE_TARGET_UNIT_COMMENT='# AI-hint: Defines the compute systemd target for MiOS, representing a compute/worker node.
# AI-related: mios-compute, mios-headless.target'
: "${MIOS_UNIT_MIOS_COMPUTE_TARGET_UNIT_CONFLICTS:=mios-controller.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNIT_MIOS_COMPUTE_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_COMPUTE_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Compute Role'
: "${MIOS_UNIT_MIOS_COMPUTE_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNIT_MIOS_CONTROLLER_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_CONTROLLER_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNIT_MIOS_CONTROLLER_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_CONTROLLER_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_CONTROLLER_TARGET_UNIT_COMMENT='# AI-hint: Defines the controller systemd target for MiOS, representing the cluster controller.
# AI-related: mios-controller, mios-headless.target'
: "${MIOS_UNIT_MIOS_CONTROLLER_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNIT_MIOS_CONTROLLER_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_CONTROLLER_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Controller Role'
: "${MIOS_UNIT_MIOS_CONTROLLER_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_COMMENT='# Operator-tunable knobs (override via drop-in or /etc/mios/secrets.env):
#   Environment=MIOS_DAEMON_MODEL=qwen3:1.7b
#   Environment=MIOS_DAEMON_ENDPOINT=http://127.0.0.1:11434
#   Environment=MIOS_DAEMON_STATE_DIR=/var/lib/mios/daemon
#   Environment=MIOS_DAEMON_CRON_TOML=/etc/mios/daemon/cron.toml
#   Environment=MIOS_DAEMON_CLASSIFY_S=30
#   Environment=MIOS_DAEMON_CRON_TICK_S=60
#   Environment=MIOS_DAEMON_WATCH_UNITS=mios-agent-pipe.service,mios-open-webui.service'
[ -n "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_COMMENT2+x}" ] || MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_COMMENT2='# Hardening (kept loose enough to allow journalctl subscription +
# subprocess.Popen for cron actions).'
[ -n "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_COMMENT3+x}" ] || MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_COMMENT3='# /var/lib/mios/daemon = the daemon'"'"'s own state (state.json, launch_failures).
# /var/lib/mios/scratch = the SHARED cross-agent blackboard the task_collector
# drops agent-nudges into for other agents to read (operator 2026-05-24: under
# ProtectSystem=strict it was read-only, so task_collector EROFS-failed writing
# agent-nudges.md -- the nudge feature was silently dead).'
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_ENVIRONMENT:=PYTHONUNBUFFERED=1}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-daemon}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_LOCKPERSONALITY:=true}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_PROTECTCONTROLGROUPS:=true}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_PROTECTKERNELTUNABLES:=true}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_READWRITEPATHS:=/var/lib/mios/daemon /var/lib/mios/scratch}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_RESTARTSEC:=5s}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_RESTRICTADDRESSFAMILIES:=AF_INET AF_INET6 AF_UNIX}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_RESTRICTREALTIME:=true}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_UNIT_AFTER:=mios-llm-light.service network.target}"
[ -n "${MIOS_UNIT_MIOS_DAEMON_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_DAEMON_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit file defining the core MiOS daemon; it consolidates log watching, cron gating, and agent nudging into a single process using a local qwen3 model to update the state.json file used by the OWUI sidecar.
# AI-related: /usr/libexec/mios/mios-daemon, /etc/mios/secrets.env, /etc/mios/daemon/cron.toml, mios-ai, mios-open-webui
# /usr/lib/systemd/system/mios-daemon.service
#
# MiOS consolidated micro-LLM daemon. Replaces three predecessors
# (mios-log-watcher + mios-cron-director + mios-agent-nudger) with
# ONE process that subscribes to journald once, holds a single
# qwen3:0.6b-cpu client (keep_alive=-1 forever, num_gpu=0 CPU-only
# per Law 7 OFFLINE-FIRST + "always-on agentic OS"), and dispatches
# the three handlers off a single event stream. Writes a unified
# /var/lib/mios/daemon/state.json the OWUI mios_sidecar Filter polls.
#
# Operator directive 2026-05-17: "ALL to be consolidated to one
# mios daemon/agent" + "keep_alive should be TRUE for a TRULY
# Agentic OS--MiOS!"'
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/mios-daemon}"
[ -n "${MIOS_UNIT_MIOS_DAEMON_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_DAEMON_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' consolidated micro-LLM daemon (log classify + refusal detect + cron gate)'
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-daemon}"
: "${MIOS_UNIT_MIOS_DAEMON_SERVICE_UNIT_WANTS:=mios-llm-light.service}"
: "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_ACCURACYSEC:=30s}"
: "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_ONBOOTSEC:=2min}"
: "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_ONUNITACTIVESEC:=5min}"
: "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_PERSISTENT:=false}"
: "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_TIMER_UNIT:=mios-dashboard-issue.service}"
[ -n "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers mios-dashboard-issue.service every 5 minutes to refresh the /etc/issue.d/ banner with real-time Quadlet status updates like service flapping and endpoint reachability.
# AI-related: /usr/libexec/mios/mios-dashboard-render-issue.sh, mios-dashboard-issue, mios-dashboard-render-issue, mios-dashboard-issue.service, timers.target
# /usr/lib/systemd/system/mios-dashboard-issue.timer
# Refresh the /etc/issue.d/ dashboard snippet every 5 minutes so
# Quadlet state changes (services flapping, endpoint reachability
# coming and going) reach the pre-login banner without operator
# intervention.'
[ -n "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' dashboard /etc/issue.d refresh timer'
: "${MIOS_UNIT_MIOS_DASHBOARD_ISSUE_TIMER_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-dashboard-render-issue.sh}"
: "${MIOS_UNIT_MIOS_DESKTOP_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_DESKTOP_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNIT_MIOS_DESKTOP_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_DESKTOP_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_DESKTOP_TARGET_UNIT_COMMENT='# AI-hint: Defines the mios-desktop.target systemd unit to initialize the desktop environment, ensuring required virtualization services (libvirtd, virtnetworkd) are active while preventing concurrent headless or cluster-specific targets.
# AI-related: mios-desktop, mios-headless, mios-k3s-master, mios-ha-node, gdm.service, libvirtd.service, libvirtd.socket, virtnetworkd.service, virtqemud.service, virtstoraged.service'
: "${MIOS_UNIT_MIOS_DESKTOP_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNIT_MIOS_DESKTOP_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_DESKTOP_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Desktop Role'
: "${MIOS_UNIT_MIOS_DESKTOP_TARGET_UNIT_REQUIRES:=multi-user.target gdm.service libvirtd.service libvirtd.socket virtnetworkd.service virtqemud.service virtstoraged.service virtnodedevd.service}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_COMMENT:=# Low-privilege execution}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_ENVIRONMENT:=PYTHONPATH=/usr/lib/mios/agent-pipe}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/userenv.sh,-/etc/mios/install.env}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_EXECSTART:=/usr/lib/mios/agents/.venv/bin/python3 -u -m mios_pipe.memory.embed_backfill}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_AFTER:=mios-pgvector.service mios-llm-light.service mios-agent-pipe.service}"
[ -n "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that runs the mios_pipe.memory.embed_backfill worker to periodically re-embed database rows with stale or missing vector versions.
# AI-related: /usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py, mios-embed-backfill.timer, mios-pgvector.service, mios-llm-light.service
# /usr/lib/systemd/system/mios-embed-backfill.service'
[ -n "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_COMMENT2='# R8: dropped After=mios-ai-firstboot.service -- the backfill worker needs pgvector
# + the embedding lane (mios-llm-light), NOT the boot-time model fetch.'
[ -n "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Embedding Backfill Worker'
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_DOCUMENTATION:=file:///usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_SERVICE_UNIT_REQUIRES:=mios-pgvector.service}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_TIMER_ACCURACYSEC:=1min}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_TIMER_ONBOOTSEC:=5min}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_TIMER_ONUNITACTIVESEC:=15min}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_TIMER_UNIT:=mios-embed-backfill.service}"
[ -n "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_UNIT_COMMENT='# AI-hint: Defines the systemd timer for the mios-embed-backfill.service, controlling the periodic execution interval (default 15m) for background embedding backfilling.
# AI-related: /usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py, mios-embed-backfill.service, timers.target
# /usr/lib/systemd/system/mios-embed-backfill.timer'
[ -n "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Embedding Backfill Timer'
: "${MIOS_UNIT_MIOS_EMBED_BACKFILL_TIMER_UNIT_DOCUMENTATION:=file:///usr/lib/mios/agent-pipe/mios_pipe/memory/embed_backfill.py}"
: "${MIOS_UNIT_MIOS_ENDPOINT_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_ENDPOINT_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNIT_MIOS_ENDPOINT_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_ENDPOINT_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_ENDPOINT_TARGET_UNIT_COMMENT='# AI-hint: Defines the endpoint systemd target for MiOS, representing an edge/client node.
# AI-related: mios-endpoint, mios-headless.target'
: "${MIOS_UNIT_MIOS_ENDPOINT_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-ha-node.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNIT_MIOS_ENDPOINT_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_ENDPOINT_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Endpoint Role'
: "${MIOS_UNIT_MIOS_ENDPOINT_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_COMMENT:=# model load + first request can take ~40s on a cold GPU}"
[ -n "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_ENVIRONMENT='HF_HOME=/var/home/mios/.cache/huggingface,MIOS_FINETUNE_SERVE_PORT=${MIOS_PORT_FINETUNE_SERVE:-11438}'
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_EXECSTART:=/var/lib/mios/finetune/venv/bin/python /usr/libexec/mios/mios-finetune-serve}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_GROUP:=mios}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_RESTARTSEC:=5}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_TIMEOUTSTARTSEC:=180}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_SERVICE_USER:=mios}"
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_UNIT_AFTER:=network-online.target}"
[ -n "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit to host the fine-tuned refiner model as an OpenAI /v1-compatible endpoint on port 11438, allowing the agent-pipe to swap between the high-quality transformer-served adapter and the faster llama.cpp path.
# AI-related: /usr/libexec/mios/mios-finetune-serve, network-online.target
# '"'"'MiOS'"'"' fine-tune serve -- serves the trained role adapter (base + LoRA) as an
# OpenAI /v1 endpoint so the fine-tuned refiner can be adopted/A-B'"'"'d
# in the agent-pipe. OPT-IN: NOT enabled by default (the transformers-served 2B is
# correct but slower than the GGUF lane on the hot path; enable to evaluate).'
[ -n "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' fine-tune serve (base+adapter refiner backend)'
: "${MIOS_UNIT_MIOS_FINETUNE_SERVE_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_COMMENT='# Ports: 3000=Forge, 3030=OWUI, 8080=code-server, 8642=Hermes-Agent,
#        8888=SearXNG, 9090=Cockpit, 9119=Hermes-Dashboard,
#        11450=LLM-Light, 5432=pgvector, 19090=Cockpit-link, 3053=AdGuard UI, 53=AdGuard DNS.
# (crawl4ai :11235 removed 2026-05-24: the crawl engine is now a LOOPBACK-only
#  venv service -- mios-crawl4ai.service binds 127.0.0.1, never LAN-exposed.)
# AdGuard DNS needs BOTH 53/tcp and 53/udp (UDP is the normal query path).
# Hardening: only the firewall-cmd binary needs system privileges; lock
# everything else down.'
[ -n "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_EXECSTART='/bin/bash -c '"'"'\
    set +e; \
    if [ -f /etc/mios/install.env ]; then source /etc/mios/install.env; fi; \
    ports=(\
        "${MIOS_PORT_FORGE_HTTP:-8400}" \
        "${MIOS_PORT_OPEN_WEBUI:-8200}" \
        "${MIOS_PORT_CODE_SERVER:-8900}" \
        "${MIOS_PORT_HERMES:-8720}" \
        "${MIOS_PORT_SEARXNG:-8800}" \
        "${MIOS_PORT_COCKPIT:-8110}" \
        "${MIOS_PORT_HERMES_DASHBOARD:-8210}" \
        "${MIOS_PORT_LLM_LIGHT:-8500}" \
        "${MIOS_PORT_PGVECTOR:-8600}" \
        "${MIOS_PORT_COCKPIT_LINK:-8120}" \
        "${MIOS_PORT_ADGUARD_UI:-8050}" \
        "${MIOS_PORT_SSH:-8100}" \
        "${MIOS_PORT_FORGE_SSH:-8410}" \
        "${MIOS_PORT_VLLM:-8520}" \
        "${MIOS_PORT_SGLANG:-8530}" \
        "${MIOS_PORT_CPU_NODE:-8510}" \
        53 \
    ); \
    for p in "${ports[@]}"; do \
        /usr/bin/firewall-cmd --permanent --add-port=${p}/tcp >/dev/null 2>&1; \
    done; \
    /usr/bin/firewall-cmd --permanent --add-port=53/udp >/dev/null 2>&1; \
    /usr/bin/firewall-cmd --reload >/dev/null 2>&1; \
    echo "MiOS firewalld ports: $(/usr/bin/firewall-cmd --list-ports 2>/dev/null)"; \
    exit 0\'"'"''
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_PROTECTCONTROLGROUPS:=yes}"
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_PROTECTKERNELTUNABLES:=yes}"
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_UNIT_AFTER:=firewalld.service network-online.target}"
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_UNIT_BEFORE:=mios-agent-pipe.service mios-open-webui.service mios-searxng.service}"
[ -n "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_UNIT_COMMENT='# AI-hint: Ensures critical MiOS service ports (3000, 3030, 8080, 8642, 8888, 9090, 9119, 11434, 19090, 3053, 53) are opened in firewalld at boot to prevent connectivity loss for Open WebUI, Hermes, Cockpit, and SearXNG.
# AI-related: mios-open-webui, mios-searxng, mios-crawl4ai, firewalld.service, hermes-agent.service, mios-open-webui.service, mios-searxng.service, mios-crawl4ai.service, network-online.target, multi-user.target
# Ensure MiOS service ports are open in firewalld at every boot.
#
# Why this exists: automation/44-firewall-ports.sh writes the firewalld
# zone XML at OCI build time via firewall-offline-cmd. On stale OCI
# images (pre-2026-05) OR when the install-time script didn'"'"'t run / the
# XML didn'"'"'t persist, firewalld comes up with no ports open and ALL
# Windows->WSL bridging silently times out (operator-confirmed
# regression 2026-05-15: Open WebUI/Hermes/Cockpit/SearXNG inaccessible
# post-reinstall; firewall-cmd --list-ports returned empty; adding the
# ports manually instantly restored all 4 services).
#
# This unit runs at every boot and is idempotent: --add-port on a port
# that'"'"'s already open is a no-op. No-ops cleanly when firewalld is
# absent (ConditionPathExists) or inactive.'
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/bin/firewall-cmd}"
[ -n "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"': ensure firewalld has the MiOS service ports open'
: "${MIOS_UNIT_MIOS_FIREWALL_PORTS_SERVICE_UNIT_WANTS:=firewalld.service network-online.target}"
: "${MIOS_UNIT_MIOS_FIRSTBOOT_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_FIRSTBOOT_TARGET_UNIT_AFTER:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_FIRSTBOOT_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_FIRSTBOOT_TARGET_UNIT_COMMENT='# AI-hint: Defines the mios-firstboot.target unit to orchestrate initial provisioning services (CDI, libvirtd, and GRD setup) during the first boot sequence of the MiOS system.
# AI-related: mios-firstboot, mios-cdi-detect, mios-libvirtd-setup, mios-grd-setup, mios-cdi-detect.service, mios-libvirtd-setup.service, mios-grd-setup.service, multi-user.target'
[ -n "${MIOS_UNIT_MIOS_FIRSTBOOT_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_FIRSTBOOT_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' first-boot provisioning'
: "${MIOS_UNIT_MIOS_FIRSTBOOT_TARGET_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS}"
: "${MIOS_UNIT_MIOS_FIRSTBOOT_TARGET_UNIT_WANTS:=mios-cdi-detect.service mios-libvirtd-setup.service mios-grd-setup.service}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-forgejo-runner-firstboot.sh}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_RESTARTSEC:=30}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=180s}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_AFTER:=mios-forge.service mios-forge-firstboot.service}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_BEFORE:=mios-forgejo-runner.service}"
[ -n "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: One-shot systemd service that executes the initial registration of the Forgejo runner using the local token if the runner is not yet configured, ensuring the runner is registered before the main service starts.
# AI-related: /etc/mios/forge/runner-token, /usr/libexec/mios/mios-forgejo-runner-firstboot.sh, mios-forge.service, mios-forge-firstboot.service, mios-forgejo-runner.service'
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=/etc/mios/forge/runner-token,!/srv/mios/forge-runner/.runner}"
[ -n "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Forgejo Runner first-boot registration'
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://forgejo.org/docs/latest/admin/actions/}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_STARTLIMITBURST:=6}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_STARTLIMITINTERVALSEC:=1200}"
: "${MIOS_UNIT_MIOS_FORGEJO_RUNNER_FIRSTBOOT_SERVICE_UNIT_WANTS:=mios-forge.service}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_COMMENT='# Hardening: this service writes to a small set of paths plus calls
# '"'"'podman exec'"'"' against the running mios-forge container. RestrictNamespaces
# and RestrictAddressFamilies were tried but break Podman'"'"'s CRIU/conmon
# attach path on rootful container exec; we drop them and lean on the
# read-write path scoping + ProtectHome instead, which is sufficient for
# this script'"'"'s actual surface area.
#
# /run is LOAD-BEARING and must be writable as a whole: rootful
# `podman exec` -- even a plain exec, no container lifecycle -- grabs
# coordination locks across multiple /run subtrees: /run/libpod/
# alive.lck (runtime init lock), /run/lock/netavark.lock (network
# coordination), /run/containers/ (storage runroot). Listing them
# individually is whack-a-mole; each missing one surfaces only at
# runtime as "open <path>: read-only file system" (exit 125). /run is
# tmpfs runtime state, so granting it RW is low-risk and is exactly
# podman'"'"'s requirement. That exit-125 failure is silent-deadly here:
# forge-firstboot.sh'"'"'s `admin user create` idempotency guard mis-reads
# 125 as "user already exists", so the admin is never created, the
# repo-create 401s, the runner-token mint fails, and the entire
# self-replication CI chain (runner-firstboot -> .runner ->
# mios-forgejo-runner.service) stays dead behind unmet
# ConditionPathExists guards. Operator-confirmed regression 2026-05-14.'
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/forge-firstboot.sh}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_LOCKPERSONALITY:=yes}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_NONEWPRIVILEGES:=yes}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_PRIVATETMP:=yes}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_PROTECTHOME:=yes}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_READWRITEPATHS:=/etc/mios/forge /var/lib/mios/forge /var/log/mios/forge /var/lib/containers /run}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_RESTARTSEC:=30}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_RESTRICTREALTIME:=yes}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=600s}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_AFTER:=mios-forge.service network-online.target}"
[ -n "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Executes the forge-firstboot.sh script to bootstrap the Forgejo instance, creating the initial admin user and repository credentials required for the MiOS self-replication and CI runner integration.
# AI-related: /etc/mios/install.env, /usr/libexec/mios/forge-firstboot.sh, mios-forge.service, mios-forgejo-runner.service
# /etc/mios/install.env is the optional layered-TOML resolver output
# from mios-sync-env. The firstboot script tolerates its absence:
# admin user, email, password all resolve from MIOS_DEFAULT_* or
# fall back to "mios" / mios@hostname.local. Keep the unit gated only
# by the firstboot sentinel.'
[ -n "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_COMMENT2='# Forgejo bootstrap MUST run on WSL too (the localhost:3000 git origin
# is the heart of the MiOS self-replication loop on every shape). A
# plain `!container` would skip WSL because systemd reports virtualization
# as `wsl` -- a container variant. Use OR: "not a container OR is WSL".'
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/forge/.firstboot-done}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=|!container,|wsl}"
[ -n "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Forge first-boot admin-bootstrap (Forgejo)'
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/mios-dev/MiOS/blob/main/etc/containers/systemd/mios-forge.container}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_STARTLIMITBURST:=6}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_STARTLIMITINTERVALSEC:=1200}"
: "${MIOS_UNIT_MIOS_FORGE_FIRSTBOOT_SERVICE_UNIT_WANTS:=mios-forge.service network-online.target}"
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNIT_MIOS_GPU_AMD_SERVICE_SERVICE_EXECSTART='/usr/bin/bash -c '"'"' \
  # If amd-ctk ever lands in Fedora RPM repos, drop a CDI spec automatically. \
  # Until then containers must pass --device /dev/kfd --device /dev/dri \
  # --group-add keep-groups explicitly. \
  if command -v amd-ctk >/dev/null 2>&1; then \
    amd-ctk cdi generate --output=/run/cdi/amd.json || true; \
  fi; \
  # Defensive perms -- Fedora Rawhide already labels /dev/kfd as root:render \
  # 0660 via kernel, but pin it in case of drift. \
  chgrp render /dev/kfd 2>/dev/null || true; \
  chmod 0660   /dev/kfd 2>/dev/null || true; \
  exit 0\'"'"''
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_SERVICE_EXECSTARTPRE:=/usr/sbin/modprobe -a amdgpu}"
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_SERVICE_STANDARDERROR:=journal}"
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_SERVICE_STANDARDOUTPUT:=journal}"
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_UNIT_AFTER:=systemd-modules-load.service systemd-udev-trigger.service}"
[ -n "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_GPU_AMD_SERVICE_UNIT_COMMENT='# AI-hint: Configures AMD GPU hardware acceleration by loading the amdgpu module, generating CDI specifications for containerized ROCm/KFD access, and enforcing 0660 permissions on /dev/kfd for the render group.
# AI-related: mios-gpu, systemd-modules-load.service, systemd-udev-trigger.service, multi-user.target'
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_UNIT_CONDITIONPATHEXISTS:=/dev/kfd}"
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container}"
[ -n "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_GPU_AMD_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' AMD GPU container plumbing (ROCm/KFD + DRI)'
: "${MIOS_UNIT_MIOS_GPU_AMD_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS/blob/main/docs/gpu-passthrough.md}"
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_INSTALL_WANTEDBY:=sysinit.target}"
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/gpu-detect}"
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_AFTER:=systemd-journald.socket}"
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_BEFORE:=gdm.service display-manager.service systemd-modules-load.service systemd-udevd.service}"
[ -n "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/gpu-detect to identify hardware GPU capabilities during boot, setting environment flags for display managers and graphics drivers.
# AI-related: /usr/libexec/mios/gpu-detect, mios-gpu-detected, gdm.service, display-manager.service, systemd-modules-load.service, systemd-udevd.service, systemd-journald.socket, sysinit.target'
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/run/mios-gpu-detected}"
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container}"
: "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_DEFAULTDEPENDENCIES:=no}"
[ -n "${MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_GPU_DETECT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' GPU Environment Detection'
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_SERVICE_EXECSTART='/usr/bin/bash -c '"'"' \
  # Defensive perms on primary render node -- do not touch card* nodes (video group \
  # handled by 99-mios-gpu.rules at udev-add time). \
  if [ -e /dev/dri/renderD128 ]; then \
    chgrp render /dev/dri/renderD128 2>/dev/null || true; \
    chmod 0660   /dev/dri/renderD128 2>/dev/null || true; \
  fi; \
  exit 0\'"'"''
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_SERVICE_EXECSTARTPRE:=-/usr/sbin/modprobe -a i915 xe amdgpu}"
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_SERVICE_STANDARDERROR:=journal}"
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_SERVICE_STANDARDOUTPUT:=journal}"
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_UNIT_AFTER:=systemd-modules-load.service systemd-udev-trigger.service}"
[ -n "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that initializes iGPU drivers (i915/xe/amdgpu) and configures permissions for /dev/dri/renderD128 to enable hardware acceleration and unified render node access for Intel/AMD hardware.
# AI-related: mios-gpu, systemd-modules-load.service, systemd-udev-trigger.service, multi-user.target'
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_UNIT_CONDITIONPATHEXISTS:=/dev/dri/renderD128}"
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container}"
[ -n "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Intel/AMD iGPU Container Plumbing (i915/xe/amdgpu)'
: "${MIOS_UNIT_MIOS_GPU_INTEL_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS/blob/main/docs/gpu-passthrough.md}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_AFTER:=sysinit.target}"
[ -n "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_COMMENT='# AI-hint: Overrides the mios-gpu-nvidia.service unit to ensure it runs during the early sysinit.target phase, bypassing standard dependency delays to ensure GPU drivers are initialized early in the boot sequence.
# AI-related: mios-gpu-nvidia, mios-gpu-nvidia.service, sysinit.target'
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_DEFAULTDEPENDENCIES:=no}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_D_10_CYCLE_FIX_CONF_UNIT_REQUIRES:=sysinit.target}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_SERVICE_EXECSTART='/usr/bin/bash -c '"'"' \
  if systemctl list-unit-files nvidia-cdi-refresh.service 2>/dev/null \
       | grep -q nvidia-cdi-refresh; then \
    echo "nvidia-cdi-refresh.service present; deferring CDI generation to upstream"; \
    exit 0; \
  fi; \
  if command -v nvidia-ctk >/dev/null 2>&1; then \
    nvidia-ctk cdi generate --output=/run/cdi/nvidia.yaml || true; \
  fi; \
  exit 0\'"'"''
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_SERVICE_EXECSTARTPRE:=/usr/sbin/modprobe -a nvidia nvidia_uvm nvidia_modeset nvidia_drm}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_SERVICE_STANDARDERROR:=journal}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_SERVICE_STANDARDOUTPUT:=journal}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_AFTER:=systemd-modules-load.service systemd-udev-trigger.service akmods.service}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_BEFORE:=nvidia-cdi-refresh.service}"
[ -n "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that ensures NVIDIA GPU modules are loaded and CDI configurations are generated for container passthrough, acting as a fallback or prerequisite for nvidia-cdi-refresh.service.
# AI-related: mios-gpu, nvidia-cdi-refresh.service, systemd-modules-load.service, systemd-udev-trigger.service, akmods.service, multi-user.target'
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_CONDITIONPATHEXISTS:=/dev/nvidia0}"
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container,!wsl}"
[ -n "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' NVIDIA GPU container plumbing'
: "${MIOS_UNIT_MIOS_GPU_NVIDIA_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS/blob/main/docs/gpu-passthrough.md}"
: "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/gpu-pv-detect}"
: "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_UNIT_AFTER:=systemd-modules-load.service}"
: "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_UNIT_BEFORE:=display-manager.service}"
[ -n "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/gpu-pv-detect to detect Hyper-V GPU Partitioning (GPU-PV) capabilities during boot, enabling hardware acceleration for guests on Microsoft Hyper-V hosts.
# AI-related: /usr/libexec/mios/gpu-pv-detect, systemd-modules-load.service, display-manager.service, multi-user.target'
: "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=microsoft}"
: "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_UNIT_DEFAULTDEPENDENCIES:=no}"
[ -n "${MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_GPU_PV_DETECT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hyper-V GPU-PV Guest Detection'
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_SERVICE_EXECSTART='/usr/bin/bash -c '"'"' \
  set +e; \
  HAS_NV=0; HAS_AMD=0; HAS_INTEL=0; \
  [ -e /dev/nvidia0 ]            && HAS_NV=1; \
  [ -e /dev/kfd ]                && HAS_AMD=1; \
  [ -e /dev/dri/renderD128 ]     && HAS_INTEL=1; \
  VIRT=$(systemd-detect-virt || echo none); \
  # /run/mios, /run/cdi, /var/lib/mios/gpu declared in usr/lib/tmpfiles.d/mios-gpu.conf (LAW 2). \
  { \
    echo "timestamp=$(date -Is)"; \
    echo "virtualization=${VIRT}"; \
    echo "nvidia=${HAS_NV}"; \
    echo "amd=${HAS_AMD}"; \
    echo "intel=${HAS_INTEL}"; \
    lspci -nn 2>/dev/null | grep -iE "vga|3d|display" || true; \
  } > /run/mios/gpu-passthrough.status; \
  # Non-persistent (in-memory) SELinux boolean -- build-time semanage handles \
  # persistence; this guarantees the boolean is on even if the policy merge \
  # dropped it. No-op on permissive / disabled / missing boolean. \
  if command -v setsebool >/dev/null 2>&1; then \
    setsebool container_use_devices on 2>/dev/null || true; \
  fi; \
  exit 0\'"'"''
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_SERVICE_RUNTIMEDIRECTORY:=mios}"
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_SERVICE_RUNTIMEDIRECTORYMODE:=0755}"
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_SERVICE_STANDARDERROR:=journal}"
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_SERVICE_STANDARDOUTPUT:=journal}"
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_UNIT_AFTER:=systemd-udev-trigger.service systemd-modules-load.service local-fs.target}"
[ -n "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that detects GPU hardware (NVIDIA, AMD, Intel) and virtualization status, exporting the results to /run/mios/gpu-passthrough.status and enabling the container_use_devices SELinux boolean.
# AI-related: mios-gpu, systemd-udev-trigger.service, systemd-modules-load.service, podman.socket, docker.socket, local-fs.target, basic.target, sockets.target, multi-user.target'
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=!container}"
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_UNIT_DEFAULTDEPENDENCIES:=yes}"
[ -n "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' GPU passthrough detection and status'
: "${MIOS_UNIT_MIOS_GPU_STATUS_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS/blob/main/docs/gpu-passthrough.md}"
: "${MIOS_UNIT_MIOS_HA_NODE_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_HA_NODE_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNIT_MIOS_HA_NODE_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_HA_NODE_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_HA_NODE_TARGET_UNIT_COMMENT='# AI-hint: Defines the mios-ha-node.target unit to identify and configure a node as a High Availability cluster member, ensuring it conflicts with desktop/headless modes and requires corosync/pacemaker services.
# AI-related: mios-ha-node, mios-desktop, mios-headless, mios-k3s-master, corosync.service, pacemaker.service, multi-user.target, mios-desktop.target, mios-headless.target, mios-k3s-master.target'
: "${MIOS_UNIT_MIOS_HA_NODE_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-endpoint.target mios-headless.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNIT_MIOS_HA_NODE_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_HA_NODE_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' HA Cluster Node Role'
: "${MIOS_UNIT_MIOS_HA_NODE_TARGET_UNIT_REQUIRES:=multi-user.target corosync.service pacemaker.service}"
: "${MIOS_UNIT_MIOS_HEADLESS_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_HEADLESS_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNIT_MIOS_HEADLESS_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_HEADLESS_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_HEADLESS_TARGET_UNIT_COMMENT='# AI-hint: Defines the headless systemd target for MiOS, enforcing a non-GUI environment by conflicting with desktop, k3s-master, and ha-node targets to ensure a dedicated server-mode state.
# AI-related: mios-desktop, mios-k3s-master, mios-ha-node, multi-user.target, mios-desktop.target, mios-k3s-master.target, mios-ha-node.target'
: "${MIOS_UNIT_MIOS_HEADLESS_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-hybrid.target mios-k3s-master.target}"
[ -n "${MIOS_UNIT_MIOS_HEADLESS_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_HEADLESS_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Headless Role'
: "${MIOS_UNIT_MIOS_HEADLESS_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_COMMENT:=# Flatpak needs HOME to bootstrap its per-user state dir.}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_ENVIRONMENT:=HOME=/var/lib/mios/hermes,XDG_RUNTIME_DIR=/run/mios-hermes-browser,HERMES_BROWSER_HEADLESS=1,NO_AT_BRIDGE=1}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-hermes-browser start}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_PRIVATETMP:=false}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_RESTARTSEC:=5s}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_RUNTIMEDIRECTORY:=mios-hermes-browser}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_RUNTIMEDIRECTORYMODE:=0700}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_STATEDIRECTORY:=mios/hermes-browser/profile}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_STATEDIRECTORYMODE:=0700}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_TIMEOUTSTOPSEC:=30s}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_AFTER:=mios-agent-pipe.service}"
[ -n "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit to manage the local ChromeDev flatpak instance providing a Chrome DevTools Protocol (CDP) endpoint at 127.0.0.1:9222 for the Hermes-Agent'"'"'s browser_tool.py to perform navigation and interaction.
# AI-related: /usr/libexec/mios/mios-hermes-browser, mios-ai, hermes-agent.service
# /usr/lib/systemd/system/mios-hermes-browser.service
#
# Headless ChromeDev (com.google.ChromeDev flatpak) with Chrome
# DevTools Protocol on 127.0.0.1:9222 -- the CDP endpoint that
# Hermes-Agent'"'"'s browser tool attaches to (see browser.cdp_url in
# /var/lib/mios/hermes/config.yaml). Operator directive 2026-05-15:
# "Hermes-Browser isn'"'"'t enabled!! Should be using the locally
# installed ChromeDev flatpak install".'
[ -n "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_COMMENT2='# ChromeDev flatpak must be installed (system or user scope). If
# missing, the unit no-ops cleanly instead of crash-looping.'
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_CONDITIONPATHEXISTS:=|/var/lib/flatpak/app/com.google.ChromeDev,|%h/.local/share/flatpak/app/com.google.ChromeDev}"
[ -n "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Browser (ChromeDev w/ CDP for Hermes-Agent)'
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_DOCUMENTATION:=https://chromedevtools.github.io/devtools-protocol/}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_SERVICE_UNIT_WANTS:=mios-agent-pipe.service}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_ENVIRONMENT='HOME=/var/lib/mios/hermes-worker,XDG_RUNTIME_DIR=/run/mios-hermes-browser-worker,HERMES_BROWSER_HEADLESS=1,HERMES_BROWSER_CDP_PORT=${MIOS_PORT_CHROME_CDP_WORKER:-9223},HERMES_BROWSER_PROFILE_DIR=/var/lib/mios/hermes-browser/profile-w2,HERMES_BROWSER_LOG=/var/lib/mios/hermes-browser/launch-w2.log,NO_AT_BRIDGE=1'
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-hermes-browser start}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_PRIVATETMP:=false}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_RESTARTSEC:=5s}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_RUNTIMEDIRECTORY:=mios-hermes-browser-worker}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_RUNTIMEDIRECTORYMODE:=0700}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_STATEDIRECTORY:=mios/hermes-browser/profile-w2}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_STATEDIRECTORYMODE:=0700}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_TIMEOUTSTOPSEC:=30s}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_AFTER:=hermes-worker.service}"
[ -n "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit for a SECOND headless ChromeDev flatpak providing a dedicated CDP endpoint at 127.0.0.1:9223 (own profile dir profile-w2) for the Hermes WORKER (:8643), so the worker'"'"'s browser_* tool loop never stomps the primary :9222 browser'"'"'s first-page target / cookies.
# AI-related: /usr/libexec/mios/mios-hermes-browser, hermes-worker.service, mios-hermes-browser.service, mios-ai, com.google.ChromeDev
# /usr/lib/systemd/system/mios-hermes-browser-worker.service
#
# A SECOND headless ChromeDev (com.google.ChromeDev flatpak) with CDP on
# 127.0.0.1:9223 -- the dedicated browser for the Hermes WORKER (:8643).
# Distinct from the primary :9222 browser (mios-hermes-browser.service): the CDP
# supervisor attaches to the FIRST page target.'
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_CONDITIONPATHEXISTS:=|/var/lib/flatpak/app/com.google.ChromeDev,|%h/.local/share/flatpak/app/com.google.ChromeDev}"
[ -n "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Browser-Worker (ChromeDev CDP :9223 for the worker)'
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_DOCUMENTATION:=https://chromedevtools.github.io/devtools-protocol/}"
: "${MIOS_UNIT_MIOS_HERMES_BROWSER_WORKER_SERVICE_UNIT_WANTS:=hermes-worker.service}"
: "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_COMMENT='# Read MIOS_AI_* + model-tier vars from the env bridge so a fresh systemd
# boot has the resolved config (model pick, endpoints). Optional ('"'"'-'"'"') so
# the unit still self-heals if the bridge isn'"'"'t generated yet.
# install-robustness 2026-06-21.'
: "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-hermes-firstboot}"
: "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_AFTER:=local-fs.target systemd-tmpfiles-setup.service}"
: "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_BEFORE:=mios-agent-pipe.service multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Initializes the Hermes gateway by generating the api.env file and ensuring the config.yaml matches the current schema, acting as a self-healing pre-boot step to provide required credentials and configuration for hermes-agent.service.
# AI-related: /etc/mios/hermes/api.env., /usr/libexec/mios/mios-hermes-firstboot, hermes-agent.service, systemd-tmpfiles-setup.service
# Runs before the DIRECT-install hermes-agent.service so the gateway
# starts with a valid $HERMES_HOME/config.yaml + api.env already on
# disk. The pre-2026-05-14 ordering targeted mios-hermes.service /
# mios-hermes-workspace.service -- both deleted when the Hermes
# container Quadlets were removed; hermes-agent.service is the runtime
# now.'
[ -n "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_COMMENT2='# NO ConditionPathExists=!/etc/mios/hermes/api.env. The old gate made
# this unit a true once-ever oneshot -- but the script does TWO jobs:
# (1) mint api.env (genuinely once), and (2) seed/heal
# /var/lib/mios/hermes/config.yaml (must re-run when the Hermes config
# SCHEMA drifts across upgrades, or when the container->direct-install
# migration left $HERMES_HOME orphan-owned). The script is fully
# idempotent -- it skips keygen when API_SERVER_KEY exists and only
# rewrites config.yaml on detected drift -- so letting it run every
# boot is cheap and self-healing. Operator-confirmed 2026-05-14: the
# gate left a stale pre-0.13 config.yaml in place that the firstboot
# rewrite could never reach.'
[ -n "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hermes-Agent first-boot config + key generation'
: "${MIOS_UNIT_MIOS_HERMES_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS}"
: "${MIOS_UNIT_MIOS_HYBRID_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_AFTER:=graphical.target}"
: "${MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_COMMENT='# AI-hint: Defines the mios-hybrid.target unit to orchestrate the concurrent execution of desktop environments, k3s worker nodes, and Ceph OSD services as the primary system state for hybrid-role nodes.
# AI-related: mios-hybrid, k3s-agent.service, graphical.target, default.target'
: "${MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-k3s-master.target}"
[ -n "${MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Hybrid role (desktop + k3s-worker + ceph-osd)'
: "${MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_REQUIRES:=graphical.target}"
: "${MIOS_UNIT_MIOS_HYBRID_TARGET_UNIT_WANTS:=k3s-agent.service}"
: "${MIOS_UNIT_MIOS_K3S_MASTER_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_K3S_MASTER_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNIT_MIOS_K3S_MASTER_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_K3S_MASTER_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_K3S_MASTER_TARGET_UNIT_COMMENT='# AI-hint: Defines the systemd target for a K3s master node role, ensuring the K3s service is active and mutually exclusive with other MiOS node profiles like desktop or headless.
# AI-related: mios-desktop, mios-headless, mios-ha-node, k3s.service, multi-user.target, mios-desktop.target, mios-headless.target, mios-ha-node.target'
: "${MIOS_UNIT_MIOS_K3S_MASTER_TARGET_UNIT_CONFLICTS:=mios-compute.target mios-controller.target mios-desktop.target mios-endpoint.target mios-ha-node.target mios-headless.target mios-hybrid.target}"
[ -n "${MIOS_UNIT_MIOS_K3S_MASTER_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_K3S_MASTER_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' K3s Master Role'
: "${MIOS_UNIT_MIOS_K3S_MASTER_TARGET_UNIT_REQUIRES:=multi-user.target k3s.service}"
: "${MIOS_UNIT_MIOS_K3S_WORKER_TARGET_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_K3S_WORKER_TARGET_UNIT_AFTER:=multi-user.target}"
: "${MIOS_UNIT_MIOS_K3S_WORKER_TARGET_UNIT_ALLOWISOLATE:=yes}"
[ -n "${MIOS_UNIT_MIOS_K3S_WORKER_TARGET_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_K3S_WORKER_TARGET_UNIT_COMMENT='# AI-hint: Defines the systemd target for the MiOS K3s worker node role, ensuring the k3s-agent.service is active and providing a specific target for orchestrating worker-node lifecycle and dependencies.
# AI-related: mios-k3s-worker, k3s-agent.service, multi-user.target, default.target'
[ -n "${MIOS_UNIT_MIOS_K3S_WORKER_TARGET_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_K3S_WORKER_TARGET_UNIT_DESCRIPTION=''"'"'MiOS'"'"' K3s worker role (agent)'
: "${MIOS_UNIT_MIOS_K3S_WORKER_TARGET_UNIT_REQUIRES:=multi-user.target}"
: "${MIOS_UNIT_MIOS_K3S_WORKER_TARGET_UNIT_WANTS:=k3s-agent.service}"
: "${MIOS_UNIT_MIOS_LIBEXEC_PERMS_PATH_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_LIBEXEC_PERMS_PATH_PATH_PATHCHANGED:=/usr/libexec/mios}"
: "${MIOS_UNIT_MIOS_LIBEXEC_PERMS_PATH_PATH_UNIT:=mios-libexec-perms.service}"
[ -n "${MIOS_UNIT_MIOS_LIBEXEC_PERMS_PATH_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_LIBEXEC_PERMS_PATH_UNIT_COMMENT='# AI-hint: Path-watcher companion to mios-libexec-perms.service -- re-runs the go+rX chmod whenever /usr/libexec/mios changes (e.g. a git checkout of / restages the scripts without exec bits), so exec perms self-heal within seconds instead of leaving services crash-looping on 203/EXEC.
# AI-related: mios-libexec-perms.service, mios-additionalimagestores-perms.path, multi-user.target
# Path-watcher companion to mios-libexec-perms.service. Any way the exec bits
# get reset on /usr/libexec/mios (most commonly a `git checkout` of the deployed
# root /), this snaps them back to go+rX within seconds so no service is left
# crash-looping on 203/"Permission denied".'
: "${MIOS_UNIT_MIOS_LIBEXEC_PERMS_PATH_UNIT_CONDITIONPATHISDIRECTORY:=/usr/libexec/mios}"
[ -n "${MIOS_UNIT_MIOS_LIBEXEC_PERMS_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_LIBEXEC_PERMS_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"': watch /usr/libexec/mios for perm changes; retrigger chmod'
: "${MIOS_UNIT_MIOS_MCP_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_COMMENT:=# Execution wrapper that verifies SQLite vaults exist before starting the MCP listener}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_COMMENT2:=# Security hardening: isolate the MCP server from writing to the core OS}"
[ -n "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_COMMENT3+x}" ] || MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_COMMENT3='# Hardening parity with sibling mios-* daemons (log-watcher, cron-
# director, hermes-browser) -- consolidation pass 2026-05-15.'
[ -n "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_COMMENT4+x}" ] || MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_COMMENT4='# Drain timeout: MCP serves a long-lived TCP socket but in-flight
# context requests are sub-second; 30 s is generous.'
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mcp-server-runner}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_EXECSTARTPRE:=/usr/libexec/mios/mcp-init.sh}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_PROTECTHOME:=read-only}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_READWRITEPATHS:=/var/lib/mios/mcp /var/log/mios/mcp}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_RESTART:=always}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_RESTARTSEC:=5}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_TIMEOUTSTOPSEC:=30s}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_MIOS_MCP_SERVICE_UNIT_AFTER:=network.target redis.service}"
[ -n "${MIOS_UNIT_MIOS_MCP_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_MCP_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit file defining the mios-mcp.service daemon, which provides the Model Context Protocol (MCP) server for autonomous agents to access system context via a hardened, high-availability userspace listener.
# AI-related: /usr/libexec/mios/mcp-init.sh, /usr/libexec/mios/mcp-server-runner, mios-ai, redis.service'
[ -n "${MIOS_UNIT_MIOS_MCP_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_MCP_SERVICE_UNIT_COMMENT2='# High-availability context provider for autonomous agents. Pure
# userspace daemon (no kernel/audit/hardware coupling) so it runs on
# every MiOS shape -- bare-metal, Hyper-V, QEMU, WSL, Podman-WSL.
# The previous `ConditionVirtualization=!container` would silently skip
# WSL, since systemd reports WSL as a `container` virt variant.'
[ -n "${MIOS_UNIT_MIOS_MCP_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_MCP_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Agent Context Service (MCP)'
: "${MIOS_UNIT_MIOS_MCP_SERVICE_UNIT_WANTS:=redis.service}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_COMMENT:=# Degrade-open: never block boot on a failed pull}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-models-firstboot}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_SUCCESSEXITSTATUS:=0 1 2 3}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=10800}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target}"
[ -n "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: FBM first-boot large-model provisioner unit (oneshot, sentinel-guarded, degrade-open).
# Runs mios-models-firstboot once at first boot to fetch [ai].firstboot_models GGUFs; enabled via 90-mios.preset.
# AI-related: /usr/libexec/mios/mios-models-firstboot, /usr/share/mios/mios.toml'
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.models-firstboot-done}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION:=First-boot Large-model Provisioner}"
: "${MIOS_UNIT_MIOS_MODELS_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_ENVIRONMENT='HOME=/var/lib/mios/opencode-gateway/work,MIOS_PORT_OPENCODE_GATEWAY=${MIOS_PORT_OPENCODE_GATEWAY:-8780},MIOS_OPENCODE_HOST=127.0.0.1,MIOS_OPENCODE_BIN=/usr/lib/mios/agents/opencode/bin/opencode,MIOS_OPENCODE_MODEL=mios-opencode:latest,MIOS_OPENCODE_PROVIDER=local,MIOS_OPENCODE_CONFIG=/etc/mios/opencode/opencode.json,MIOS_OPENCODE_TIMEOUT_S=90'
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_EXECSTART:=/usr/lib/mios/agents/.venv/bin/python3 -u /usr/lib/mios/agents/opencode-gateway/server.py}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_LOCKPERSONALITY:=true}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTCONTROLGROUPS:=true}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTKERNELMODULES:=true}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTKERNELTUNABLES:=true}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_READWRITEPATHS:=/etc/mios /var/lib/mios}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_RESTARTSEC:=10s}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_RESTRICTSUIDSGID:=true}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_TIMEOUTSTARTSEC:=30s}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_SERVICE_WORKINGDIRECTORY:=/var/lib/mios/opencode-gateway/work}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_AFTER:=network-online.target mios-llm-light.service}"
[ -n "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that hosts the opencode-gateway on port 8633, providing a standard OpenAI-compatible /v1 API shim for the opencode CLI to enable multi-agent fan-out and local inference via mios-llm-light.
# AI-related: /usr/lib/mios/agents/opencode-gateway/server.py, /usr/lib/mios/agents/opencode/bin/opencode, /usr/lib/mios/agents/.venv, mios-llm-light.service
# R8: dropped After=mios-ai-firstboot.service -- the coder gateway rides the venv +
# the light inference lane (mios-llm-light), NOT the boot-time model fetch.'
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_COMMENT2:=# Skip cleanly if the opencode binary never landed (build-time fetch failure)}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/lib/mios/agents/opencode/bin/opencode}"
[ -n "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' OpenCode /v1 gateway (OpenAI adapter fronting the opencode CLI)'
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_DOCUMENTATION:=file:///usr/lib/mios/agents/opencode-gateway/server.py}"
: "${MIOS_UNIT_MIOS_OPENCODE_GATEWAY_SERVICE_UNIT_WANTS:=network-online.target mios-llm-light.service}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT='# SSOT env: MIOS_PG_USER / MIOS_PG_DB / MIOS_PORT_PGVECTOR / MIOS_PG_BACKUP_*
# all flow from mios.toml [pgvector] -> userenv.sh. '"'"'-'"'"' = tolerate absence
# (degrade-open to the inline defaults below).'
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT2:=# Inline-default the knobs so the unit is correct even with no env file present.}"
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT3+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT3='# Runs as root to `podman exec` into the mios-ai.pod pgvector container.
# ProtectSystem=strict / ReadWritePaths dropped so podman can reach its runtime.'
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT4+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_COMMENT4='# Logical dump over loopback-trust, gzip'"'"'d + timestamped, then prune to the
# newest N. Pure POSIX sh so it runs on the minimal base. Every branch exits 0
# (degrade-open): gate-off, missing client, or a dump error logs and succeeds.'
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_ENVIRONMENT+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_ENVIRONMENT='MIOS_PG_BACKUP_ENABLE=true,MIOS_PG_BACKUP_DIR=/var/lib/mios/backups,MIOS_PG_BACKUP_KEEP=7,MIOS_PG_USER=mios,MIOS_PG_DB=mios,MIOS_PORT_PGVECTOR=${MIOS_PORT_PGVECTOR:-8600}'
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/userenv.sh}"
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_EXECSTART+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_EXECSTART='/bin/sh -c '"'"'case "$$MIOS_PG_BACKUP_ENABLE" in 0|false|False|FALSE|no|off) echo "mios-pgvector-backup: disabled (MIOS_PG_BACKUP_ENABLE=$$MIOS_PG_BACKUP_ENABLE)"; exit 0 ;; esac; DIR="$$MIOS_PG_BACKUP_DIR"; [ -z "$$DIR" ] && DIR="/var/lib/mios/backups"; KEEP="$$MIOS_PG_BACKUP_KEEP"; [ -z "$$KEEP" ] && KEEP="7"; case "$$KEEP" in *[!0-9]*|"") KEEP=7 ;; esac; [ "$$KEEP" -lt 1 ] && KEEP=1; PORT="$$MIOS_PORT_PGVECTOR"; [ -z "$$PORT" ] && PORT="8432"; USR="$$MIOS_PG_USER"; [ -z "$$USR" ] && USR="mios"; DB="$$MIOS_PG_DB"; [ -z "$$DB" ] && DB="mios"; if ! command -v podman >/dev/null 2>&1; then echo "mios-pgvector-backup: podman not found on PATH -- skipping (need podman to exec pg_dump inside the pod)"; exit 0; fi; mkdir -p "$$DIR" 2>/dev/null || true; TS=$$(date -u +%%Y%%m%%dT%%H%%M%%SZ); OUT="$$DIR/mios-pgvector-$$TS.sql.gz"; RAW="$$DIR/.mios-pgvector-$$TS.sql.partial"; ERR="$$DIR/.mios-pgbackup.err"; rc=0; podman exec mios-pgvector pg_dump -h 127.0.0.1 -p "$$PORT" -U "$$USR" --no-password "$$DB" >"$$RAW" 2>"$$ERR" || rc=$$?; if [ "$$rc" -ne 0 ] || [ ! -s "$$RAW" ]; then echo "mios-pgvector-backup: pg_dump failed (rc=$$rc, degrade-open): $$(tail -n1 "$$ERR" 2>/dev/null)"; rm -f "$$RAW" "$$ERR" 2>/dev/null || true; exit 0; fi; if gzip -c "$$RAW" >"$$OUT.partial" && mv -f "$$OUT.partial" "$$OUT"; then chmod 0640 "$$OUT" 2>/dev/null || true; echo "mios-pgvector-backup: wrote $$OUT"; else echo "mios-pgvector-backup: gzip failed (degrade-open)"; rm -f "$$OUT.partial" "$$RAW" "$$ERR" 2>/dev/null || true; exit 0; fi; rm -f "$$RAW" "$$ERR" 2>/dev/null || true; N=$$(ls -1 "$$DIR"/mios-pgvector-*.sql.gz 2>/dev/null | wc -l); if [ "$$N" -gt "$$KEEP" ]; then ls -1t "$$DIR"/mios-pgvector-*.sql.gz 2>/dev/null | tail -n +$$((KEEP+1)) | while IFS= read -r f; do rm -f "$$f" && echo "mios-pgvector-backup: pruned $$f"; done; fi; exit 0'"'"''
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_AFTER:=mios-pgvector.service}"
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_COMMENT='# AI-hint: Unprivileged daily oneshot that pg_dumps the unified agent-plane Postgres+pgvector database to /var/lib/mios/backups over loopback-trust and prunes to the newest MIOS_PG_BACKUP_KEEP snapshots; degrade-open so a backup failure never blocks the DB.
# AI-related: mios-pgvector-backup.timer, mios-pgvector.service, /usr/lib/tmpfiles.d/mios-backups.conf, mios-pg-query
# /usr/lib/systemd/system/mios-pgvector-backup.service
# WS-0 pgvector durability: periodic logical backup of the unified agent-plane
# datastore (tiered memory / knowledge / skills / sessions / scratch / sys_env /
# kanban / ...). Losing pgvector is expensive, so this snapshots it daily.
#
# UNPRIVILEGED (Architectural Law 6 spirit): runs as the pgvector sysuser
# (mios-pgvector, uid 826) -- it owns /var/lib/mios/backups (tmpfiles) and
# reaches Postgres over the pg_hba loopback-trust line.
#
# DEGRADE-OPEN: every failure path (gate off, no pg_dump client, dump error)
# logs and exits 0. A backup miss must NEVER fault the boot/timer or affect the
# live DB. backup_enable ships TRUE; flip MIOS_PG_BACKUP_ENABLE=false to disable.'
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_COMMENT2='# Same virtualization guard as the pgvector container: the DB only runs on
# bare-metal/WSL (not a nested container), so there'"'"'s nothing to back up there.'
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=|!container,|wsl}"
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' daily pg_dump backup of the unified agent-plane datastore (pgvector)'
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_DOCUMENTATION:=file:///usr/lib/systemd/system/mios-pgvector-backup.service}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_SERVICE_UNIT_WANTS:=mios-pgvector.service}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_ACCURACYSEC:=5m}"
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_COMMENT='# Daily, shortly after midnight local time. Persistent=true catches up a missed
# run (machine asleep/off at the scheduled time) on the next boot. Randomized
# delay spreads the dump off the exact minute so it doesn'"'"'t collide with other
# midnight jobs.'
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_ONCALENDAR:=*-*-* 00:30:00}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_TIMER_RANDOMIZEDDELAYSEC:=15m}"
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_COMMENT='# AI-hint: Daily systemd timer that fires mios-pgvector-backup.service to snapshot the unified agent-plane Postgres+pgvector datastore, with Persistent=true so a missed run (machine off) executes at next boot.
# AI-related: mios-pgvector-backup.service, timers.target
# /usr/lib/systemd/system/mios-pgvector-backup.timer
# WS-0 pgvector durability: schedules the daily logical backup of the unified
# agent-plane datastore. The service itself is degrade-open + gated on
# MIOS_PG_BACKUP_ENABLE, so the timer can stay enabled unconditionally.'
[ -n "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' daily pgvector datastore backup schedule'
: "${MIOS_UNIT_MIOS_PGVECTOR_BACKUP_TIMER_UNIT_DOCUMENTATION:=file:///usr/lib/systemd/system/mios-pgvector-backup.service}"
: "${MIOS_UNIT_MIOS_PODMAN_GC_SERVICE_SERVICE_EXECSTART:=/usr/bin/podman system prune -a -f}"
: "${MIOS_UNIT_MIOS_PODMAN_GC_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_PODMAN_GC_SERVICE_UNIT_COMMENT:=# AI-hint: Systemd unit that executes a forced Podman system prune to reclaim disk space from unused images and containers, specifically targeting WSL and non-containerized environments.}"
: "${MIOS_UNIT_MIOS_PODMAN_GC_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=|!container,|wsl}"
[ -n "${MIOS_UNIT_MIOS_PODMAN_GC_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_PODMAN_GC_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Podman Garbage Collection'
: "${MIOS_UNIT_MIOS_PODMAN_GC_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_PODMAN_GC_TIMER_TIMER_ONCALENDAR:=weekly}"
: "${MIOS_UNIT_MIOS_PODMAN_GC_TIMER_TIMER_PERSISTENT:=true}"
[ -n "${MIOS_UNIT_MIOS_PODMAN_GC_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_PODMAN_GC_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer unit that triggers the mios-podman-gc.service weekly to automate the removal of stale Podman containers, images, and networks to reclaim disk space.
# AI-related: mios-podman-gc, mios-podman-gc.service, timers.target'
: "${MIOS_UNIT_MIOS_PODMAN_GC_TIMER_UNIT_DESCRIPTION:=Weekly Podman Cleanup}"
: "${MIOS_UNIT_MIOS_PODMAN_PS_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_PODMAN_PS_TIMER_TIMER_ACCURACYSEC:=2s}"
: "${MIOS_UNIT_MIOS_PODMAN_PS_TIMER_TIMER_ONBOOTSEC:=10s}"
: "${MIOS_UNIT_MIOS_PODMAN_PS_TIMER_TIMER_ONUNITACTIVESEC:=15s}"
[ -n "${MIOS_UNIT_MIOS_PODMAN_PS_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_PODMAN_PS_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers mios-podman-ps.service every 15 seconds to refresh the podman container snapshot data for the MiOS dashboard display.
# AI-related: mios-podman-ps, mios-podman-ps.service, timers.target'
[ -n "${MIOS_UNIT_MIOS_PODMAN_PS_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_PODMAN_PS_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' refresh the podman container snapshot for the dashboard'
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_COMMENT:=# Hardening: a stateless loopback decision service needs nothing but Python.}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_ENVIRONMENT:=MIOS_AGENT_PIPE_DIR=/usr/lib/mios/agent-pipe}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_EXECSTART:=/usr/bin/python3 /usr/libexec/mios/mios-policy-arbiter}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_NONEWPRIVILEGES:=true}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_PRIVATETMP:=true}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_PROTECTHOME:=true}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_PROTECTSYSTEM:=strict}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_RESTARTSEC:=15s}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_TYPE:=simple}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_SERVICE_USER:=mios-ai}"
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_UNIT_AFTER:=network-online.target mios-agent-pipe.service}"
[ -n "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit for the WS-9 out-of-process HITL policy arbiter -- runs /usr/libexec/mios/mios-policy-arbiter (a stdlib loopback HTTP service) as the mios-ai user, answering the agent-pipe'"'"'s HITL arbiter client with allow/deny verdicts decided by mios_arbiter over the operator policy. Idle/no-op until [ai].hitl_arbiter_url points at it; default policy is allow-all so enabling it changes nothing until a deny-list/block-tier is set.
# AI-related: /usr/libexec/mios/mios-policy-arbiter, /usr/lib/mios/agent-pipe/mios_arbiter.py, mios-agent-pipe.service
# /usr/lib/systemd/system/mios-policy-arbiter.service
# '"'"'MiOS'"'"' out-of-process HITL policy arbiter (WS-9). A second, operator-ownable
# opinion ON TOP of the in-process #62 HITL gate + WS-A9 PDP: the agent-pipe POSTs
# each high-risk (tier >= [ai].hitl_threshold) action here for an allow/deny
# verdict. Runs as mios-ai (least privilege); binds 127.0.0.1 only.'
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/mios-policy-arbiter}"
[ -n "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' out-of-process HITL policy arbiter (WS-9)'
: "${MIOS_UNIT_MIOS_POLICY_ARBITER_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-shell-session gc}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_GROUP:=mios-ai}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_SUCCESSEXITSTATUS:=0 1}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_SERVICE_USER:=mios-ai}"
[ -n "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_UNIT_COMMENT='# AI-hint: SHELL-01 idle reaper for the persistent PTY substrate -- kills tmux sessions idle past [shell_session].idle_s so a long-lived shell plane cannot accumulate unbounded state.
# AI-related: /usr/libexec/mios/mios-shell-session, mios-shell-session-gc.timer, /usr/share/mios/mios.toml [shell_session]'
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_UNIT_CONDITIONPATHEXISTS:=/usr/libexec/mios/mios-shell-session}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_SERVICE_UNIT_DESCRIPTION:=Reap idle MiOS shell sessions}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_TIMER_TIMER_ONBOOTSEC:=10min}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_TIMER_TIMER_ONUNITINACTIVESEC:=10min}"
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_TIMER_TIMER_PERSISTENT:=true}"
[ -n "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_SHELL_SESSION_GC_TIMER_UNIT_COMMENT='# AI-hint: Fires mios-shell-session-gc.service periodically so idle persistent shells are reclaimed without an operator.
# AI-related: mios-shell-session-gc.service'
: "${MIOS_UNIT_MIOS_SHELL_SESSION_GC_TIMER_UNIT_DESCRIPTION:=Periodic reap of idle MiOS shell sessions}"
: "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_TIMER_ACCURACYSEC:=2min}"
: "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_TIMER_ONBOOTSEC:=10min}"
: "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_TIMER_ONUNITACTIVESEC:=60min}"
: "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_TIMER_UNIT:=mios-skills-miner.service}"
[ -n "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_UNIT_COMMENT='# AI-hint: Defines the systemd timer for the mios-skills-miner.service, controlling the periodic execution interval (default 60m) for background skill mining and pattern discovery.
# AI-related: /usr/libexec/mios/mios-skills, mios-skills-miner, mios-skills, mios-skills-miner.service, timers.target
# /usr/lib/systemd/system/mios-skills-miner.timer
# Phase C.2 of the AgentOS roadmap: cadence for the background
# skill miner. Interval lifted to mios.toml [skills].
# mine_interval_minutes (default 60). Operator override:
#   sudo systemctl edit mios-skills-miner.timer
#   [Timer]
#   OnUnitActiveSec=30min
#
# Disabled by default; operator opts in (or it inherits enablement
# from the configurator HTML "Skills mining" toggle which maps to
# [skills].enable). The .service ConditionPathExists guard means a
# stripped-down deployment with the libexec script absent skips
# silently.'
[ -n "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Phase C.2 skill-miner cadence (sequential pattern mining)'
: "${MIOS_UNIT_MIOS_SKILLS_MINER_TIMER_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-skills}"
: "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_ACCURACYSEC:=1min}"
[ -n "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_COMMENT='# First refresh 2 min after boot so the chain has warmed up.
# Then every 10 min while running.'
: "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_ONBOOTSEC:=2min}"
: "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_ONUNITACTIVESEC:=10min}"
: "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_PERSISTENT:=true}"
: "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_TIMER_UNIT:=mios-suggestion-refresh.service}"
[ -n "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers mios-suggestion-refresh.service every 10 minutes to update OWUI starter chips based on current system state, kanban data, and recent user intents.
# AI-related: /usr/libexec/mios/mios-suggestion-refresh, mios-suggestion-refresh, mios-suggestion-refresh.service, timers.target
# /usr/lib/systemd/system/mios-suggestion-refresh.timer
# Fires mios-suggestion-refresh.service every 10 minutes so the
# OWUI starter chips revolve based on current MiOS state (recent
# kanban, daemon nudges, recent refine intents). Operators tune
# the cadence with:
#   sudo systemctl edit mios-suggestion-refresh.timer
#   [Timer]
#   OnUnitActiveSec=30min'
[ -n "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' starter-chip refresh cadence'
: "${MIOS_UNIT_MIOS_SUGGESTION_REFRESH_TIMER_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-suggestion-refresh}"
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_COMMENT:=# Never wedge boot on a pack problem.}"
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-swarm-pack-firstboot}"
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_SUCCESSEXITSTATUS:=0}"
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_TIMEOUTSTARTSEC:=120}"
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target mios-cdi-detect.service mios-ai-firstboot.service}"
[ -n "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes mios-swarm-pack-firstboot to arm concurrent small-model worker units if gpu_profile is "swarm", enforcing VRAM budgets and provisioning GGUFs during the first boot sequence.
# AI-related: /usr/libexec/mios/mios-swarm-pack-firstboot, mios-cdi-detect.service, mios-ai-firstboot.service, network-online.target
# SWARM Phase-2 (operator 2026-06-12): arm the concurrent small-model server pack
# at boot IF [dispatch].gpu_profile == "swarm" (else the script is a no-op). The
# script self-gates + enforces the VRAM budget, so this unit is safe to enable
# unconditionally; it only ever starts mios-llm-worker@<name> units when the
# operator has flipped the profile + provisioned GGUFs.'
[ -n "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_COMMENT2+x}" ] || MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_COMMENT2='# Don'"'"'t even try before the agent stack'"'"'s prerequisites; the script is idempotent.'
[ -n "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' swarm small-model pack arming (gpu_profile=swarm only)'
: "${MIOS_UNIT_MIOS_SWARM_PACK_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_INSTALL_WANTEDBY:=timers.target}"
: "${MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_ACCURACYSEC:=10s}"
[ -n "${MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_COMMENT+x}" ] || MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_COMMENT='# Mirrors the daemon'"'"'s directory_entry refresh cadence (~15 min): installed
# apps / services / loaded models change far slower than container state, so a
# 15-min refresh keeps the shared snapshot current without churn. The manual
# sys_env_refresh verb covers the "I just installed X" case immediately.'
: "${MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_ONBOOTSEC:=45s}"
: "${MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_ONUNITACTIVESEC:=900s}"
: "${MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_TIMER_PERSISTENT:=true}"
[ -n "${MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_UNIT_COMMENT='# AI-hint: Systemd timer that triggers the mios-sys-env-refresh service every 900 seconds to synchronize the sys_env environment cache with current system state, ensuring shared snapshots reflect recent app/service changes.
# AI-related: mios-sys-env-refresh, timers.target'
[ -n "${MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_SYS_ENV_REFRESH_TIMER_UNIT_DESCRIPTION=''"'"'MiOS'"'"' refresh cadence for the sys_env environment cache'
: "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_SERVICE_ENVIRONMENTFILE:=-/etc/mios/install.env}"
: "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-userdb-render}"
[ -n "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_SERVICE_EXECSTARTPRE+x}" ] || MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_SERVICE_EXECSTARTPRE='-/usr/bin/podman exec mios-pgvector pg_isready -q -h 127.0.0.1 -p ${MIOS_PORT_PGVECTOR:-8600} -U mios -d mios'
: "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_UNIT_AFTER:=mios-pgvector.service}"
[ -n "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/mios-userdb-render to project PostgreSQL account records into systemd userdb JSON drop-ins.
# AI-related: /usr/libexec/mios/mios-userdb-render, mios-pgvector.service'
[ -n "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' PostgreSQL account systemd userdb drop-in renderer'
: "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_UNIT_DOCUMENTATION:=file:///usr/libexec/mios/mios-userdb-render}"
: "${MIOS_UNIT_MIOS_USERDB_RENDER_SERVICE_UNIT_REQUIRES:=mios-pgvector.service}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_COMMENT+x}" ] || MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_COMMENT='# Retry the build if an image is still missing (a transient network/CDN blip
# during first install must not leave webtools permanently down).'
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/mios-webtools-firstboot.sh}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_RESTART:=on-failure}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_RESTARTSEC:=30}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_AFTER:=network-online.target}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_BEFORE:=mios-webtools-pod.service}"
[ -n "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_COMMENT='# WS-DEPLOY: allow the build to retry (script exits non-zero on a missing image)
# without tripping the start-limit too fast under sustained install contention.'
[ -n "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' web-tools images build-on-demand firstboot service'
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_STARTLIMITBURST:=6}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_STARTLIMITINTERVALSEC:=1200}"
: "${MIOS_UNIT_MIOS_WEBTOOLS_FIRSTBOOT_SERVICE_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_INSTALL_WANTEDBY:=multi-user.target}"
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_SERVICE_EXECSTART:=/usr/libexec/mios/wsl-firstboot}"
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_SERVICE_REMAINAFTEREXIT:=yes}"
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_SERVICE_TYPE:=oneshot}"
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_AFTER:=local-fs.target}"
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_BEFORE:=systemd-user-sessions.service multi-user.target}"
[ -n "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_COMMENT='# AI-hint: Systemd unit that executes /usr/libexec/mios/wsl-firstboot to perform one-time initialization tasks specifically for WSL2 instances if the first-boot flag is not yet set.
# AI-related: /usr/libexec/mios/wsl-firstboot, systemd-user-sessions.service, local-fs.target, multi-user.target'
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_CONDITIONPATHEXISTS:=!/var/lib/mios/.wsl-firstboot-done}"
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_CONDITIONVIRTUALIZATION:=wsl}"
[ -n "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_DESCRIPTION=''"'"'MiOS'"'"' WSL2 First Boot Initialization'
: "${MIOS_UNIT_MIOS_WSL_FIRSTBOOT_SERVICE_UNIT_DOCUMENTATION:=https://github.com/MiOS-DEV/MiOS}"
: "${MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_INSTALL_WANTEDBY:=multi-user.target default.target}"
[ -n "${MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_PATH_COMMENT+x}" ] || MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_PATH_COMMENT='# Trigger whenever flatpak adds/removes an exported .desktop (any
# system-wide install / uninstall touches this dir mtime).'
: "${MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_PATH_PATHCHANGED:=/var/lib/flatpak/exports/share/applications,/var/lib/flatpak/exports/share/icons}"
[ -n "${MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_COMMENT+x}" ] || MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_COMMENT='# AI-hint: Systemd path unit that triggers a synchronization script when flatpak application or icon files are modified in the export directory, ensuring .desktop files are updated for WSL integration.
# AI-related: mios-is-wsl, multi-user.target, default.target'
: "${MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_CONDITIONPATHEXISTS:=/run/mios-is-wsl}"
[ -n "${MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_DESCRIPTION+x}" ] || MIOS_UNIT_MIOS_WSL_FLATPAK_EXPORT_SYNC_PATH_UNIT_DESCRIPTION=''"'"'MiOS'"'"' Re-fire flatpak->WSL .desktop sync when flatpak installs/uninstalls land'
: "${MIOS_UNIT_OPEN_WEBUI:=mios-open-webui.service}"
: "${MIOS_UNIT_PGVECTOR:=mios-pgvector.service}"
[ -n "${MIOS_UNIT_PROJECTION_DOC+x}" ] || MIOS_UNIT_PROJECTION_DOC='[units.*] is the SOURCE and usr/lib/systemd/system is the DERIVED artifact (Law 8), but the declarations went stale while nothing compared them: mios-unit-gen --check rendered into memory, printed PASSED and returned, and its golden test diffed the unit tree against tests/golden/, a byte copy of that same tree. This register lists every unit [units.*] declares whose rendering no longer matches the file it ships. It only shrinks -- tools/native/mios-unit-gen/tests/projection.rs fails an entry that has stopped drifting as loudly as one that starts, so the count cannot be padded. Draining an entry: `mios-unit-gen --render <unit> | diff - usr/lib/systemd/system/<unit>`, then correct [units.*] (the file on disk is what boots, so it wins). A unit absent from BOTH this register and [units.*] is not covered at all -- 52 of the tree'"'"'s 120 units are in that state, which is the larger debt behind T-317.'
: "${MIOS_UNIT_PROJECTION_DRIFT:=hermes-worker-firstboot.service,hermes-worker.service,mios-account-sync.service,mios-additionalimagestores-perms.path,mios-adguard-firstboot.service,mios-agent-pipe.service,mios-agents.service,mios-ai-firstboot.service,mios-ai-firstboot.timer,mios-aios-refresh.timer,mios-ceph-bootstrap.service,mios-daemon.service,mios-embed-backfill.service,mios-finetune-serve.service,mios-firewall-ports.service,mios-forge-firstboot.service,mios-forgejo-runner-firstboot.service,mios-gpu-amd.service,mios-gpu-intel.service,mios-gpu-nvidia.service,mios-gpu-status.service,mios-hermes-browser-worker.service,mios-hermes-browser.service,mios-hermes-firstboot.service,mios-libexec-perms.path,mios-mcp.service,mios-models-firstboot.service,mios-opencode-gateway.service,mios-pgvector-backup.service,mios-pgvector-backup.timer,mios-podman-gc.service,mios-policy-arbiter.service,mios-shell-session-gc.service,mios-suggestion-refresh.timer,mios-swarm-pack-firstboot.service,mios-sys-env-refresh.timer,mios-userdb-render.service,mios-webtools-firstboot.service,mios-wsl-flatpak-export-sync.path}"
: "${MIOS_UNIT_PROJECTION_MAX_DRIFT:=39}"
: "${MIOS_UNIT_SEARXNG:=mios-searxng.service}"
[ -n "${MIOS_UNIT_USER_SESSION+x}" ] || MIOS_UNIT_USER_SESSION='user@'"${MIOS_UID}"'.service'
: "${MIOS_UNIT_VAR_HOME_MOUNT_INSTALL_WANTEDBY:=remote-fs.target}"
: "${MIOS_UNIT_VAR_HOME_MOUNT_MOUNT_OPTIONS:=secretfile=/etc/ceph/mios.secret,noatime,_netdev,nofail,x-systemd.device-timeout=30,x-systemd.mount-timeout=30}"
: "${MIOS_UNIT_VAR_HOME_MOUNT_MOUNT_TYPE:=ceph}"
: "${MIOS_UNIT_VAR_HOME_MOUNT_MOUNT_WHAT:=mios@.cephfs=/home}"
: "${MIOS_UNIT_VAR_HOME_MOUNT_MOUNT_WHERE:=/var/home}"
: "${MIOS_UNIT_VAR_HOME_MOUNT_UNIT_AFTER:=ceph.target network-online.target}"
[ -n "${MIOS_UNIT_VAR_HOME_MOUNT_UNIT_COMMENT+x}" ] || MIOS_UNIT_VAR_HOME_MOUNT_UNIT_COMMENT='# AI-hint: Systemd mount unit for mapping the CephFS cluster to /var/home, providing persistent storage for user home directories using the mios.secret for authentication.
# AI-related: ceph.target, network-online.target, x-systemd.mount, remote-fs.target'
: "${MIOS_UNIT_VAR_HOME_MOUNT_UNIT_CONDITIONPATHEXISTS:=/etc/ceph/ceph.conf,/etc/ceph/mios.secret}"
: "${MIOS_UNIT_VAR_HOME_MOUNT_UNIT_DESCRIPTION:=CephFS mount for user home directories}"
: "${MIOS_UNIT_VAR_HOME_MOUNT_UNIT_DOCUMENTATION:=man:mount.ceph(8)}"
: "${MIOS_UNIT_VAR_HOME_MOUNT_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_INSTALL_WANTEDBY:=remote-fs.target}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_MOUNT_OPTIONS:=secretfile=/etc/ceph/mios.secret,noatime,_netdev,nofail,x-systemd.device-timeout=30,x-systemd.mount-timeout=30}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_MOUNT_TYPE:=ceph}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_MOUNT_WHAT:=mios@.cephfs=/containers}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_MOUNT_WHERE:=/var/lib/containers}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_UNIT_AFTER:=ceph.target network-online.target}"
[ -n "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_UNIT_COMMENT+x}" ] || MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_UNIT_COMMENT='# AI-hint: Systemd mount unit for the CephFS storage backend at /var/lib/containers, used by the system to provide persistent, shared storage for Podman containers via the mios.secret credential.
# AI-related: ceph.target, network-online.target, x-systemd.mount, remote-fs.target'
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_UNIT_CONDITIONPATHEXISTS:=/etc/ceph/ceph.conf,/etc/ceph/mios.secret}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_UNIT_DESCRIPTION:=CephFS mount for Podman container storage}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_UNIT_REQUIRESMOUNTSFOR:=/var/lib}"
: "${MIOS_UNIT_VAR_LIB_CONTAINERS_MOUNT_UNIT_WANTS:=network-online.target}"
: "${MIOS_UNIT_VAR_LIB_MACHINES_MOUNT_MOUNT_OPTIONS:=loop}"
: "${MIOS_UNIT_VAR_LIB_MACHINES_MOUNT_MOUNT_TYPE:=btrfs}"
: "${MIOS_UNIT_VAR_LIB_MACHINES_MOUNT_MOUNT_WHAT:=/var/lib/machines.raw}"
: "${MIOS_UNIT_VAR_LIB_MACHINES_MOUNT_MOUNT_WHERE:=/var/lib/machines}"
[ -n "${MIOS_UNIT_VAR_LIB_MACHINES_MOUNT_UNIT_COMMENT+x}" ] || MIOS_UNIT_VAR_LIB_MACHINES_MOUNT_UNIT_COMMENT='#  SPDX-License-Identifier: LGPL-2.1-or-later
#
#  This file is part of systemd.
#
#  systemd is free software; you can redistribute it and/or modify it
#  under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation; either version 2.1 of the License, or
#  (at your option) any later version.
# This unit is required for pre-240 versions of systemd that automatically set
# up /var/lib/machines.raw as loopback-mounted btrfs file system. Later
# versions don'"'"'t do that anymore, but let'"'"'s keep minimal compatibility by
# mounting the image still, if it exists.'
: "${MIOS_UNIT_VAR_LIB_MACHINES_MOUNT_UNIT_CONDITIONPATHEXISTS:=/var/lib/machines.raw}"
: "${MIOS_UNIT_VAR_LIB_MACHINES_MOUNT_UNIT_DESCRIPTION:=Virtual Machine and Container Storage (Compatibility)}"
: "${MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_MOUNT_TYPE:=rpc_pipefs}"
: "${MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_MOUNT_WHAT:=sunrpc}"
: "${MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_MOUNT_WHERE:=/var/lib/nfs/rpc_pipefs}"
: "${MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_AFTER:=systemd-tmpfiles-setup.service}"
[ -n "${MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_COMMENT+x}" ] || MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_COMMENT='# AI-hint: Mounts the RPC pipe file system at /var/lib/nfs/rpc_pipefs to provide the necessary mount points for NFS RPC services and client operations.
# AI-related: systemd-tmpfiles-setup.service, umount.target'
: "${MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_CONFLICTS:=umount.target}"
: "${MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_DEFAULTDEPENDENCIES:=no}"
: "${MIOS_UNIT_VAR_LIB_NFS_RPC_PIPEFS_MOUNT_UNIT_DESCRIPTION:=RPC Pipe File System}"
: "${MIOS_UNIT_WSL_FIRSTBOOT:=mios-wsl-firstboot.service}"
: "${MIOS_URLS_BOOTSTRAP_REPO:=https://github.com/mios-dev/mios-bootstrap.git}"
[ -n "${MIOS_URLS_COCKPIT+x}" ] || MIOS_URLS_COCKPIT='https://localhost:'"${MIOS_PORT_COCKPIT}"
[ -n "${MIOS_URLS_CODE_SERVER+x}" ] || MIOS_URLS_CODE_SERVER='http://localhost:'"${MIOS_PORT_CODE_SERVER}"'/'
[ -n "${MIOS_URLS_FORGE+x}" ] || MIOS_URLS_FORGE='http://localhost:'"${MIOS_PORT_FORGE_HTTP}"
[ -n "${MIOS_URLS_LOCAL_FORGE_REPO+x}" ] || MIOS_URLS_LOCAL_FORGE_REPO='http://localhost:'"${MIOS_PORT_FORGE_HTTP}"'/mios/mios.git'
: "${MIOS_URLS_NON_ADDRESSABLE:=adguard_dns,adguard_ui,agent_pipe,arbiter,ceph_dashboard,crawl4ai,hermes,llm_light,pgvector,chrome_cdp,chrome_cdp_worker,cockpit_link,cpu_node,daemon_agent,firecrawl,forge_ssh,guacamole_web,guacd,hermes_dashboard,k3s_api,mcp,model_router,opencode_gateway,oscontrol,otelcol_otlp,prefilter,pxe_hub_api,rdp,redis,sglang,ssh,ttyd_bash,ttyd_powershell,vllm}"
[ -n "${MIOS_URLS_OPEN_WEBUI+x}" ] || MIOS_URLS_OPEN_WEBUI='http://localhost:'"${MIOS_PORT_OPEN_WEBUI}"'/'
[ -n "${MIOS_URLS_OTELCOL_UI+x}" ] || MIOS_URLS_OTELCOL_UI='http://localhost:'"${MIOS_PORT_OTELCOL_UI}"'/'
: "${MIOS_URLS_REPO:=https://github.com/mios-dev/MiOS.git}"
[ -n "${MIOS_URLS_SEARXNG+x}" ] || MIOS_URLS_SEARXNG='http://localhost:'"${MIOS_PORT_SEARXNG}"
: "${MIOS_USER:=mios}"
: "${MIOS_USER_FULLNAME:=MiOS Operator}"
: "${MIOS_USER_GROUPS:=wheel,libvirt,kvm,video,render,input,dialout,docker}"
: "${MIOS_USER_SHELL:=/bin/bash}"
: "${MIOS_USR_DIR:=/usr/lib/mios}"
: "${MIOS_VALKEY_IMAGE:=docker.io/valkey/valkey:latest}"
: "${MIOS_VALKEY_VERSION:=docker.io/valkey/valkey:latest}"
[ -n "${MIOS_VAR_AI_DIR+x}" ] || MIOS_VAR_AI_DIR="${MIOS_VAR_DIR}"'/ai'
[ -n "${MIOS_VAR_BACKUPS_DIR+x}" ] || MIOS_VAR_BACKUPS_DIR="${MIOS_VAR_DIR}"'/backups'
[ -n "${MIOS_VAR_CACHE_DIR+x}" ] || MIOS_VAR_CACHE_DIR="${MIOS_VAR_DIR}"'/cache'
[ -n "${MIOS_VAR_MCP_DIR+x}" ] || MIOS_VAR_MCP_DIR="${MIOS_VAR_DIR}"'/mcp'
: "${MIOS_VERB_EMBED_MODEL:=nomic-embed-text}"
: "${MIOS_VERITY_ANTIFAB_ENABLE:=true}"
: "${MIOS_VERITY_ANTIFAB_GROUND_MIN:=0.34}"
: "${MIOS_VERITY_ANTIFAB_MIN_ENTITIES:=3}"
: "${MIOS_VERITY_SENTENCE_ABBREVIATIONS:=approx.,Approx.,e.g.,i.e.,vs.,etc.,U.S.,U.K.,a.m.,p.m.,No.,Inc.,Co.,Ltd.,St.,Mt.}"
: "${MIOS_VERSIONS_CEPH:=v19}"
: "${MIOS_VERSIONS_FEDORA:=44}"
: "${MIOS_VERSIONS_FORGEJO:=12}"
: "${MIOS_VERSIONS_K3S:=v1.36.3-k3s1}"
: "${MIOS_VERSIONS_K8S_REPO:=v1.36}"
: "${MIOS_VLLM_BAKE_MODEL:=stelterlab/Qwen3-30B-A3B-Instruct-2507-AWQ}"
: "${MIOS_VLLM_ENABLE:=false}"
: "${MIOS_VLLM_GPU_UTIL:=0.85}"
: "${MIOS_VLLM_IMAGE:=docker.io/vllm/vllm-openai:latest}"
: "${MIOS_VLLM_KV_CACHE_DTYPE:=fp8}"
: "${MIOS_VLLM_MAX_MODEL_LEN:=262144}"
: "${MIOS_VLLM_PORT:=8520}"
: "${MIOS_VLLM_PREFIX_CACHING:=true}"
: "${MIOS_VLLM_SERVED_NAME:=mios-heavy}"
: "${MIOS_VLLM_TOOL_CALL_PARSER:=hermes}"
: "${MIOS_VLLM_USE_V1:=true}"
: "${MIOS_VLLM_VERSION:=docker.io/vllm/vllm-openai:latest}"
: "${MIOS_VM_WIN11_MEMORY_KIB:=25165824}"
: "${MIOS_VM_WIN11_NAME:=win11-guest}"
: "${MIOS_VM_WIN11_VCPUS:=12}"
: "${MIOS_WEBTOOLS_GID:=824}"
: "${MIOS_WEBTOOLS_UID:=824}"
: "${MIOS_WEBTOOLS_USER:=mios-crawl4ai}"
: "${MIOS_WEB_RESEARCH_ANCHOR_MIN_LEN:=25}"
: "${MIOS_WEB_RESEARCH_ANCHOR_WEIGHT:=2}"
: "${MIOS_WEB_RESEARCH_CRAWL_TIMEOUT_S:=18}"
: "${MIOS_WEB_RESEARCH_DIGIT_WEIGHT:=1}"
: "${MIOS_WEB_RESEARCH_LINK_RANK_MODE:=heuristic}"
: "${MIOS_WEB_RESEARCH_MAX_ATTEMPTS:=3}"
: "${MIOS_WEB_RESEARCH_MIN_SCORE:=2}"
: "${MIOS_WEB_RESEARCH_PASSES:=3}"
: "${MIOS_WEB_RESEARCH_RECENCY_RANGE:=month}"
: "${MIOS_WEB_RESEARCH_SEG_BASE:=1}"
: "${MIOS_WEB_RESEARCH_SLUG_MIN_LEN:=12}"
: "${MIOS_WEB_RESEARCH_SLUG_WEIGHT:=2}"
: "${MIOS_WEB_RESEARCH_TOP_N:=6}"
: "${MIOS_WEB_SEARCH_TRIGGER_CONTEXTS:=web,internet,online}"
: "${MIOS_WEB_SEARCH_TRIGGER_PHRASES:=search,look up,google,find,search the web,search online}"
: "${MIOS_WINDOWS_OWNED_ARTIFACTS_FIREWALL_RULES:=MiOS - igpu-llm,MiOS - ai-node,MiOS}"
: "${MIOS_WINDOWS_OWNED_ARTIFACTS_PROCESS_NAMES:=MiOS-Wallpaper,MiOS-Wallpaper-Service,MiOS-Launcher,MiOS-iGPU-Server}"
[ -n "${MIOS_WINDOWS_OWNED_ARTIFACTS_REGISTRY_ROOTS+x}" ] || MIOS_WINDOWS_OWNED_ARTIFACTS_REGISTRY_ROOTS='HKLM:\SOFTWARE\MiOS,HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MiOS,HKCU:\Control Panel\Cursors\Schemes'
: "${MIOS_WINDOWS_OWNED_ARTIFACTS_SERVICE_NAMES:=MiOS-Wallpaper-Service,MiOS-iGPU-Server}"
: "${MIOS_WINDOWS_OWNED_ARTIFACTS_SHORTCUT_DIRS:=MiOS,podman-MiOS-DEV}"
: "${MIOS_WINDOWS_OWNED_ARTIFACTS_TASK_NAMES:=MiOS-Autostart,MiOS-Resume-Bootstrap,MiOS-WSL-KeepAlive,MiOS-WSL-Session,MiOS-iGPU-Server}"
: "${MIOS_WORKER_TOOLS_BM25_B:=0.75}"
: "${MIOS_WORKER_TOOLS_BM25_K1:=1.2}"
: "${MIOS_WORKER_TOOLS_PRIORITY_FALLBACK_SCORES:=0.55,0.45,0.3,0.25,0.15}"
: "${MIOS_WORKER_TOOLS_TOOL_PRIORITY_CORE_FIRST:=true}"
: "${MIOS_WSL2_AUTO_PROXY:=true}"
: "${MIOS_WSL2_DESKTOP_COMPAT_GDK_BACKEND:=x11}"
: "${MIOS_WSL2_DESKTOP_COMPAT_MOZ_WAYLAND:=0}"
: "${MIOS_WSL2_DESKTOP_COMPAT_QT_PLATFORM:=xcb}"
: "${MIOS_WSL2_DEV_VM_QUADLET_NETWORK_MODE:=host}"
: "${MIOS_WSL2_DNS_TUNNELING:=true}"
: "${MIOS_WSL2_FIREWALL:=false}"
: "${MIOS_WSL2_GUI_APPLICATIONS:=true}"
: "${MIOS_WSL2_LOCALHOST_FORWARDING:=true}"
: "${MIOS_WSL2_NETWORKING_MODE:=NAT}"
: "${MIOS_WSLBOOT_DONE:=/var/lib/mios/.wsl-firstboot-done}"
: "${MIOS_WSLG_GDK_BACKEND:=x11}"
: "${MIOS_WSLG_MOZ_WAYLAND:=0}"
: "${MIOS_WSLG_QT_PLATFORM:=xcb}"
: "${MIOS_WSL_DISTRO:=MiOS}"
[ -n "${MIOS_XDG_CACHE_LOCAL_PATH+x}" ] || MIOS_XDG_CACHE_LOCAL_PATH='/run/user/{uid}/.cache'
