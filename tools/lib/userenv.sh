#!/usr/bin/env bash
# AI-hint: Parses layered TOML configuration files (vendor, host, and user) to export unified MIOS_ environment variables for identity, locale, network, AI, and image build settings used by all system tools and scripts.
# AI-related: ./tools/lib/userenv.sh, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /usr/share/mios/env.defaults, mios-bootstrap, mios-colors, mios-opencode-gateway, mios-llm-heavy-alt, mios-llm-heavy, mios-webtools
# AI-functions: _mios_load_unified, _mios_legacy_get
# tools/lib/userenv.sh -- read the unified 'MiOS' user config and export
# MIOS_* environment variables. Sourced by Justfile, /etc/profile.d, every
# entry-point script, and any tool that needs the user-overridden values.
#
# THERE IS ONE CANONICAL FILE PATH PER LAYER. Higher layers shadow lower
# layers field-by-field; the user-edit copy lives in mios-bootstrap and is
# staged into /etc/mios/mios.toml at install time.
#
#   1. /usr/share/mios/mios.toml   (vendor defaults; baked into image)        lowest
#   2. /etc/mios/mios.toml         (host-local; bootstrap-staged)
#   3. ~/.config/mios/mios.toml    (per-user; XDG)                            highest
#
# Schema is the same in all three layers (TOML 1.0; section names below).
# Resolution mode: deep merge by section.field. The Python helper below
# reads each layer in order and writes one consolidated set of MIOS_*
# exports back to the calling shell.
#
# Section -> MIOS_* env mapping (typed slots; non-typed fields can still
# be reached via the [env] table for free-form injection):
#
#   [identity]    .username/.fullname/.hostname/.shell/.groups
#                 -> MIOS_USER, MIOS_USER_FULLNAME, MIOS_HOSTNAME,
#                    MIOS_USER_SHELL, MIOS_USER_GROUPS (CSV)
#   [locale]      .timezone/.keyboard_layout/.language
#                 -> MIOS_TIMEZONE, MIOS_KEYBOARD, MIOS_LOCALE
#   [auth]        .ssh_key_action/.password_policy
#                 -> MIOS_SSH_KEY_ACTION, MIOS_PASSWORD_POLICY
#   [network]     .firewalld_default_zone
#                 -> MIOS_FIREWALLD_ZONE
#   [ai]          .endpoint/.model/.embed_model/.api_key/.system_prompt_file/.mcp_registry
#                 -> MIOS_AI_ENDPOINT, MIOS_AI_MODEL, MIOS_AI_EMBED_MODEL,
#                    MIOS_AI_KEY, MIOS_SYSTEM_PROMPT_FILE, MIOS_MCP_REGISTRY
#   [desktop]     .session/.color_scheme/.flatpaks
#                 -> MIOS_DESKTOP_SESSION, MIOS_COLOR_SCHEME,
#                    MIOS_FLATPAKS (CSV; consumed by Containerfile build arg)
#   [image]       .ref/.branch/.base/.bib/.name/.tag/.local_tag
#                 -> MIOS_IMAGE_REF, MIOS_BRANCH, MIOS_BASE_IMAGE,
#                    MIOS_BIB_IMAGE, MIOS_IMAGE_NAME, MIOS_IMAGE_TAG,
#                    MIOS_LOCAL_TAG
#   [bootstrap]   .mode/.mios_repo/.bootstrap_repo
#                 -> MIOS_BOOTSTRAP_MODE, MIOS_REPO_URL, MIOS_BOOTSTRAP_REPO_URL
#   [profile]     .role/.features
#                 -> MIOS_PROFILE_ROLE, MIOS_PROFILE_FEATURES (CSV)
#   [colors]      .bg/.fg/.accent/.cursor/.success/.warning/.error/.info/
#                 .muted/.subtle/.earth/.silver/.ansi_*
#                 -> MIOS_COLOR_BG, MIOS_COLOR_FG, MIOS_COLOR_ACCENT, ...
#                    MIOS_ANSI_0_BLACK, MIOS_ANSI_1_RED, ...
#                 (consumed by /etc/profile.d/mios-colors.sh, the
#                 oh-my-posh theme, the configurator HTML's :root,
#                 and globals.{sh,ps1} as default overrides)
#   [env]         arbitrary KEY = "VALUE" pairs                exported verbatim
#
# Backwards compat:
#   - The legacy lightweight schema ([user]/[build]/[flatpaks].install) is
#     still understood as a fallback when [identity]/[image]/[desktop] are
#     absent. 'just init-user-space' migrates the legacy split files.
#   - The legacy split files (env.toml, images.toml, build.toml,
#     flatpaks.list, the bare 'env' file) are still read when no
#     mios.toml is present in any layer.
#
# Usage: source ./tools/lib/userenv.sh
# Note: must be sourced (not executed) to affect the calling shell.

MIOS_VENDOR_TOML="${MIOS_VENDOR_TOML:-/usr/share/mios/mios.toml}"
MIOS_HOST_TOML="${MIOS_HOST_TOML:-/etc/mios/mios.toml}"
MIOS_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/mios"
MIOS_USER_TOML="${MIOS_CONFIG_DIR}/mios.toml"

# Removed: vendor env.defaults sourcing block. As of v0.2.4 mios.toml is
# THE singular SSOT for every operator-tunable infrastructure constant
# (ports, sidecar pins, service identities, runtime paths, build
# tunables); env.defaults has been deleted. The Python TOML merger
# below is the only source of MIOS_* env-var emission.

# 1. TOML overlay (vendor -> host -> per-user). Use python tomllib (3.11+
# stdlib; tomli fallback for older). The Python block prints shell-safe
# 'export' lines that the surrounding shell evals.
_mios_load_unified() {
    local layers=("$MIOS_VENDOR_TOML" "$MIOS_HOST_TOML" "$MIOS_USER_TOML")
    command -v python3 >/dev/null 2>&1 || return 0
    local exports
    exports=$(MIOS_LAYERS="${layers[*]}" python3 - <<'PY'
import os, sys, shlex, re
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.exit(0)

layers = os.environ["MIOS_LAYERS"].split()

def deep_merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = v

merged = {}
for path in layers:
    if not path or not os.path.isfile(path):
        continue
    try:
        with open(path, "rb") as f:
            deep_merge(merged, tomllib.load(f))
    except Exception as e:
        sys.stderr.write(f"userenv: failed to parse {path}: {e}\n")

def get(d, dotted):
    for p in dotted.split("."):
        if not isinstance(d, dict) or p not in d:
            return None
        d = d[p]
    return d

# Typed slot map. Pairs of "section.field=ENV_VAR".
slots = [
    # identity
    ("identity.username",       "MIOS_USER"),
    ("identity.fullname",       "MIOS_USER_FULLNAME"),
    ("identity.hostname",       "MIOS_HOSTNAME"),
    ("identity.shell",          "MIOS_USER_SHELL"),
    ("identity.groups",         "MIOS_USER_GROUPS"),
    # locale
    ("locale.timezone",         "MIOS_TIMEZONE"),
    ("locale.keyboard_layout",  "MIOS_KEYBOARD"),
    ("locale.language",         "MIOS_LOCALE"),
    # auth
    ("auth.ssh_key_action",     "MIOS_SSH_KEY_ACTION"),
    ("auth.password_policy",    "MIOS_PASSWORD_POLICY"),
    # network
    ("network.firewalld_default_zone", "MIOS_FIREWALLD_ZONE"),
    # ai
    ("ai.endpoint",             "MIOS_AI_ENDPOINT"),
    ("ai.model",                "MIOS_AI_MODEL"),
    ("ai.embed_model",          "MIOS_AI_EMBED_MODEL"),
    ("ai.api_key",              "MIOS_AI_KEY"),
    ("ai.system_prompt_file",   "MIOS_SYSTEM_PROMPT_FILE"),
    # Hermes-Agent direct host install (automation/38-hermes-agent.sh).
    ("ai.hermes_agent_repo",    "MIOS_HERMES_AGENT_REPO"),
    ("ai.hermes_agent_ref",     "MIOS_HERMES_AGENT_REF"),
    ("ai.hermes_backend_url",   "MIOS_HERMES_BACKEND_URL"),
    ("ai.mcp_registry",         "MIOS_MCP_REGISTRY"),
    # desktop
    ("desktop.session",         "MIOS_DESKTOP_SESSION"),
    ("desktop.color_scheme",    "MIOS_COLOR_SCHEME"),
    ("desktop.flatpaks",        "MIOS_FLATPAKS"),
    # image
    ("image.ref",               "MIOS_IMAGE_REF"),
    ("image.branch",            "MIOS_BRANCH"),
    ("image.base",              "MIOS_BASE_IMAGE"),
    ("image.bib",               "MIOS_BIB_IMAGE"),
    ("image.name",              "MIOS_IMAGE_NAME"),
    ("image.tag",               "MIOS_IMAGE_TAG"),
    ("image.local_tag",         "MIOS_LOCAL_TAG"),
    # bootstrap
    ("bootstrap.mode",          "MIOS_BOOTSTRAP_MODE"),
    ("bootstrap.mios_repo",     "MIOS_REPO_URL"),
    ("bootstrap.bootstrap_repo","MIOS_BOOTSTRAP_REPO_URL"),
    # profile
    ("profile.role",            "MIOS_PROFILE_ROLE"),
    ("profile.features",        "MIOS_PROFILE_FEATURES"),
    # colors -- Hokusai + operator-neutrals palette, applied across every
    # console / terminal / oh-my-posh / Cockpit / configurator HTML.
    # /etc/profile.d/mios-colors.sh emits OSC-4 / OSC-10 / OSC-11 / OSC-12
    # at every interactive shell start using these MIOS_COLOR_* values.
    # The configurator HTML's :root CSS variables also bind to these
    # tokens via applyColorsToRoot(), so an edit there re-skins every
    # surface that resolves through this slot map.
    ("colors.bg",               "MIOS_COLOR_BG"),
    ("colors.fg",               "MIOS_COLOR_FG"),
    ("colors.accent",           "MIOS_COLOR_ACCENT"),
    ("colors.cursor",           "MIOS_COLOR_CURSOR"),
    ("colors.success",          "MIOS_COLOR_SUCCESS"),
    ("colors.warning",          "MIOS_COLOR_WARNING"),
    ("colors.error",            "MIOS_COLOR_ERROR"),
    ("colors.info",             "MIOS_COLOR_INFO"),
    ("colors.muted",            "MIOS_COLOR_MUTED"),
    ("colors.subtle",           "MIOS_COLOR_SUBTLE"),
    ("colors.earth",            "MIOS_COLOR_EARTH"),
    ("colors.silver",           "MIOS_COLOR_SILVER"),
    ("colors.ansi_0_black",            "MIOS_ANSI_0_BLACK"),
    ("colors.ansi_1_red",              "MIOS_ANSI_1_RED"),
    ("colors.ansi_2_green",            "MIOS_ANSI_2_GREEN"),
    ("colors.ansi_3_yellow",           "MIOS_ANSI_3_YELLOW"),
    ("colors.ansi_4_blue",             "MIOS_ANSI_4_BLUE"),
    ("colors.ansi_5_magenta",          "MIOS_ANSI_5_MAGENTA"),
    ("colors.ansi_6_cyan",             "MIOS_ANSI_6_CYAN"),
    ("colors.ansi_7_white",            "MIOS_ANSI_7_WHITE"),
    ("colors.ansi_8_bright_black",     "MIOS_ANSI_8_BRIGHT_BLACK"),
    ("colors.ansi_9_bright_red",       "MIOS_ANSI_9_BRIGHT_RED"),
    ("colors.ansi_10_bright_green",    "MIOS_ANSI_10_BRIGHT_GREEN"),
    ("colors.ansi_11_bright_yellow",   "MIOS_ANSI_11_BRIGHT_YELLOW"),
    ("colors.ansi_12_bright_blue",     "MIOS_ANSI_12_BRIGHT_BLUE"),
    ("colors.ansi_13_bright_magenta",  "MIOS_ANSI_13_BRIGHT_MAGENTA"),
    ("colors.ansi_14_bright_cyan",     "MIOS_ANSI_14_BRIGHT_CYAN"),
    ("colors.ansi_15_bright_white",    "MIOS_ANSI_15_BRIGHT_WHITE"),
    # ── ports (migrated from /usr/share/mios/env.defaults) ───────────────
    ("ports.ssh",                      "MIOS_PORT_SSH"),
    # ── WS-2 Code Mode sandbox uid/gid (SSOT [code_mode].uid/gid) ──
    ("code_mode.uid",                  "MIOS_CODEMODE_UID"),
    ("code_mode.gid",                  "MIOS_CODEMODE_GID"),
    ("ports.forge_http",               "MIOS_PORT_FORGE_HTTP"),
    ("ports.forge_ssh",                "MIOS_PORT_FORGE_SSH"),
    ("ports.cockpit",                  "MIOS_PORT_COCKPIT"),
    ("ports.cockpit_link",             "MIOS_PORT_COCKPIT_LINK"),
    ("ports.ollama",                   "MIOS_PORT_OLLAMA"),
    ("ports.searxng",                  "MIOS_PORT_SEARXNG"),
    ("ports.crawl4ai",                 "MIOS_PORT_CRAWL4AI"),
    ("ports.firecrawl",                "MIOS_PORT_FIRECRAWL"),
    ("ports.hermes",                   "MIOS_PORT_HERMES"),
    ("ports.hermes_workspace",         "MIOS_PORT_HERMES_WORKSPACE"),
    ("ports.open_webui",               "MIOS_PORT_OPEN_WEBUI"),
    ("ports.code_server",              "MIOS_PORT_CODE_SERVER"),
    ("ports.k3s_api",                  "MIOS_K3S_API_PORT"),
    ("ports.guacamole_web",            "MIOS_GUACAMOLE_PORT"),
    ("ports.ceph_dashboard",           "MIOS_CEPH_DASHBOARD_PORT"),
    ("ports.rdp",                      "MIOS_RDP_PORT"),
    ("ports.pgvector",                 "MIOS_PORT_PGVECTOR"),
    ("ports.llama_swap",               "MIOS_PORT_LLAMA_SWAP"),
    ("ports.agent_pipe",               "MIOS_PORT_AGENT_PIPE"),
    ("ports.ollama_cpu",               "MIOS_PORT_OLLAMA_CPU"),
    ("ports.adguard_dns",              "MIOS_PORT_ADGUARD_DNS"),
    ("ports.adguard_ui",               "MIOS_PORT_ADGUARD_UI"),
    # opencode -> OpenAI /v1 gateway shim port ([ports].opencode_gateway).
    ("ports.opencode_gateway",         "MIOS_PORT_OPENCODE_GATEWAY"),
    # vLLM heavy dGPU lane port ([ports].vllm; Phase 2 2026-06-01).
    ("ports.vllm",                     "MIOS_PORT_VLLM"),
    ("ports.sglang",                   "MIOS_PORT_SGLANG"),
    # ── opencode + shared agent-plane (HYBRID; keys live under [ai]) ──────
    # opencode is a first-class /v1 council peer via mios-opencode-gateway.
    # service. install_url/version pre-existed; the rest are the front-door
    # SSOT added 2026-05-31. agent_venv/agent_install_dir are the de-facto
    # shared interpreter for hermes-agent + agent-pipe + the gateway shim
    # (mapped onto MIOS_HERMES_VENV/_DIR — the names those consumers expect).
    ("ai.opencode_install_url",        "MIOS_OPENCODE_INSTALL_URL"),
    ("ai.opencode_version",            "MIOS_OPENCODE_VERSION"),
    ("ai.opencode_model",              "MIOS_OPENCODE_MODEL"),
    ("ai.opencode_provider",           "MIOS_OPENCODE_PROVIDER"),
    ("ai.opencode_bin",                "MIOS_OPENCODE_BIN"),
    ("ai.opencode_config",             "MIOS_OPENCODE_CONFIG"),
    ("ai.opencode_gateway_workdir",    "MIOS_OPENCODE_WORKDIR"),
    ("ai.opencode_gateway_timeout_s",  "MIOS_OPENCODE_TIMEOUT_S"),
    ("ai.agent_venv",                  "MIOS_HERMES_VENV"),
    ("ai.agent_install_dir",           "MIOS_HERMES_DIR"),
    # ── vLLM heavy lane ([ai.vllm]; re-scoped mios-llm-heavy-alt Quadlet, Phase 2) ──
    # Rendered into mios-llm-heavy-alt.container's Exec= by 15-render-quadlets.sh;
    # bake_model is read by automation/38-vllm-prep.sh at build time.
    ("ai.vllm.served_name",            "MIOS_VLLM_SERVED_NAME"),
    ("ai.vllm.gpu_util",               "MIOS_VLLM_GPU_UTIL"),
    ("ai.vllm.max_model_len",          "MIOS_VLLM_MAX_MODEL_LEN"),
    ("ai.vllm.bake_model",             "MIOS_VLLM_BAKE_MODEL"),
    # ── SGLang heavy lane ([ai.sglang]; mios-llm-heavy Quadlet, operator 2026-06-07) ──
    # Rendered into mios-llm-heavy.container's Exec= by 15-render-quadlets.sh;
    # bake_model is read by automation/38-sglang-prep.sh at build time.
    ("ai.sglang.served_name",          "MIOS_SGLANG_SERVED_NAME"),
    ("ai.sglang.mem_fraction",         "MIOS_SGLANG_MEM_FRACTION"),
    ("ai.sglang.max_model_len",        "MIOS_SGLANG_MAX_MODEL_LEN"),
    ("ai.sglang.bake_model",           "MIOS_SGLANG_BAKE_MODEL"),
    # legacy aliases for ports
    ("ports.forge_http",               "MIOS_FORGE_HTTP_PORT"),
    ("ports.forge_ssh",                "MIOS_FORGE_SSH_PORT"),
    ("ports.searxng",                  "MIOS_SEARXNG_PORT"),
    ("ports.hermes",                   "MIOS_HERMES_PORT"),
    ("ports.cockpit",                  "MIOS_COCKPIT_PORT"),
    ("ports.ssh",                      "MIOS_SSH_PORT"),
    # ── MIOS_DEFAULT_* aliases (env.defaults compat — TOML wins) ─────────
    ("identity.username",              "MIOS_DEFAULT_USER"),
    ("identity.hostname",              "MIOS_DEFAULT_HOST"),
    ("identity.shell",                 "MIOS_DEFAULT_SHELL"),
    ("identity.groups",                "MIOS_DEFAULT_GROUPS"),
    ("identity.default_password",      "MIOS_DEFAULT_PASSWORD"),
    ("portal.require_login",           "MIOS_PORTAL_REQUIRE_LOGIN"),
    ("portal.user",                    "MIOS_PORTAL_USER"),
    ("portal.password",                "MIOS_PORTAL_PASSWORD"),
    ("portal.session_ttl",             "MIOS_PORTAL_SESSION_TTL"),
    ("portal.secret",                  "MIOS_PORTAL_SECRET"),
    ("locale.timezone",                "MIOS_DEFAULT_TIMEZONE"),
    ("locale.language",                "MIOS_DEFAULT_LOCALE"),
    ("locale.keyboard_layout",         "MIOS_DEFAULT_KEYBOARD"),
    # ── meta / version ──────────────────────────────────────────────────
    ("meta.mios_version",              "MIOS_VERSION"),
    # ── ai bake list ────────────────────────────────────────────────────
    ("ai.bake_models",                 "MIOS_AI_BAKE_MODELS"),
    ("ai.bake_models",                 "MIOS_OLLAMA_BAKE_MODELS"),
    # ── bootstrap dev VM + host storage ─────────────────────────────────
    ("bootstrap.dev_vm.machine_name",  "MIOS_BUILDER_DISTRO"),
    ("bootstrap.dev_vm.wsl_distro",    "MIOS_WSL_DISTRO"),
    ("bootstrap.dev_vm.base_image",    "MIOS_DEV_VM_BASE_IMAGE"),
    ("bootstrap.dev_vm.cpus",          "MIOS_DEV_VM_CPUS"),
    ("bootstrap.dev_vm.memory_mb",     "MIOS_DEV_VM_MEMORY_MB"),
    ("bootstrap.dev_vm.disk_size_gb",  "MIOS_DEV_VM_DISK_GB"),
    ("bootstrap.dev_vm.gpu_passthrough","MIOS_DEV_VM_GPU"),
    ("bootstrap.dev_vm.host_reserve.cpu_pct",    "MIOS_DEV_VM_CPU_RESERVE_PCT"),
    ("bootstrap.dev_vm.host_reserve.cpu_min",    "MIOS_DEV_VM_CPU_RESERVE_MIN"),
    ("bootstrap.dev_vm.host_reserve.memory_pct", "MIOS_DEV_VM_MEMORY_RESERVE_PCT"),
    ("bootstrap.dev_vm.host_reserve.memory_gb",  "MIOS_DEV_VM_MEMORY_RESERVE_GB"),
    ("bootstrap.dev_vm.host_reserve.disk_gb",    "MIOS_DEV_VM_DISK_RESERVE_GB"),
    ("bootstrap.host_storage.shrink_mb",   "MIOS_DATA_DISK_MB"),
    ("bootstrap.host_storage.drive_letter","MIOS_DATA_DISK_LETTER"),
    # ── wsl2 (utility VM networking + dev VM Quadlet network mode) ────────
    ("wsl2.networking_mode",                  "MIOS_WSL2_NETWORKING_MODE"),
    ("wsl2.localhost_forwarding",             "MIOS_WSL2_LOCALHOST_FORWARDING"),
    ("wsl2.firewall",                         "MIOS_WSL2_FIREWALL"),
    ("wsl2.gui_applications",                 "MIOS_WSL2_GUI_APPLICATIONS"),
    ("wsl2.desktop_compat.gdk_backend",       "MIOS_WSLG_GDK_BACKEND"),
    ("wsl2.desktop_compat.moz_wayland",       "MIOS_WSLG_MOZ_WAYLAND"),
    ("wsl2.desktop_compat.qt_platform",       "MIOS_WSLG_QT_PLATFORM"),
    ("wsl2.dev_vm.quadlet_network_mode",      "MIOS_QUADLET_DEV_NETWORK_MODE"),
    # ── image.sidecars (sidecar container pins) ───────────────────────────
    ("image.sidecars.k3s_version",     "MIOS_K3S_VERSION"),
    ("image.sidecars.k3s",             "MIOS_K3S_IMAGE"),
    ("image.sidecars.ceph_version",    "MIOS_CEPH_VERSION"),
    ("image.sidecars.ceph",            "MIOS_CEPH_IMAGE"),
    ("image.sidecars.forge_version",   "MIOS_FORGE_VERSION"),
    ("image.sidecars.forge",           "MIOS_FORGE_IMAGE"),
    ("image.sidecars.searxng_version", "MIOS_SEARXNG_VERSION"),
    ("image.sidecars.searxng",         "MIOS_SEARXNG_IMAGE"),
    # web-tools POD (2026-05-24 "make it a pod"): the crawl engine is now a
    # podman POD (mios-webtools.pod, Network=host) with FOUR members --
    # redis:7-alpine, firecrawl-api + firecrawl-worker (localhost/
    # mios-firecrawl:v1.0.0, built from usr/share/mios/webtools/
    # firecrawl.Containerfile), and crawl4ai (localhost/mios-crawl4ai-slim:latest,
    # built from usr/share/mios/crawl4ai/Containerfile). Both are LOCALLY built,
    # so there is no upstream image/version pin to render; the firecrawl quadlets
    # default to localhost/mios-firecrawl:v1.0.0 via ${MIOS_FIRECRAWL_IMAGE} and
    # the crawl4ai quadlet to localhost/mios-crawl4ai-slim:latest via
    # ${MIOS_CRAWL4AI_IMAGE}. The port + service uid mappings ([ports].crawl4ai,
    # [ports].firecrawl, [services.webtools].*) are RETAINED below.
    ("image.sidecars.hermes_version",  "MIOS_HERMES_VERSION"),
    ("image.sidecars.hermes",          "MIOS_HERMES_IMAGE"),
    ("image.sidecars.hermes_workspace_version", "MIOS_HERMES_WORKSPACE_VERSION"),
    ("image.sidecars.hermes_workspace","MIOS_HERMES_WORKSPACE_IMAGE"),
    ("image.sidecars.open_webui_version", "MIOS_OPEN_WEBUI_VERSION"),
    ("image.sidecars.open_webui",      "MIOS_OPEN_WEBUI_IMAGE"),
    ("image.sidecars.code_server_version", "MIOS_CODE_SERVER_VERSION"),
    ("image.sidecars.code_server",     "MIOS_CODE_SERVER_IMAGE"),
    ("image.sidecars.ollama_version",  "MIOS_OLLAMA_VERSION"),
    ("image.sidecars.ollama",          "MIOS_OLLAMA_IMAGE"),
    ("image.sidecars.guacamole_version","MIOS_GUACAMOLE_VERSION"),
    ("image.sidecars.guacamole",       "MIOS_GUACAMOLE_IMAGE"),
    ("image.sidecars.forge_runner_version","MIOS_FORGE_RUNNER_VERSION"),
    ("image.sidecars.forge_runner",    "MIOS_FORGE_RUNNER_IMAGE"),
    ("image.sidecars.crowdsec_version","MIOS_CROWDSEC_VERSION"),
    ("image.sidecars.crowdsec",        "MIOS_CROWDSEC_IMAGE"),
    ("image.sidecars.postgres_version","MIOS_POSTGRES_VERSION"),
    ("image.sidecars.postgres",        "MIOS_POSTGRES_IMAGE"),
    ("image.sidecars.guacd_version",   "MIOS_GUACD_VERSION"),
    ("image.sidecars.guacd",           "MIOS_GUACD_IMAGE"),
    ("image.sidecars.pxe_hub_version", "MIOS_PXE_HUB_VERSION"),
    ("image.sidecars.pxe_hub",         "MIOS_PXE_HUB_IMAGE"),
    ("image.sidecars.bib_alpine",      "MIOS_BIB_ALPINE_IMAGE"),
    ("image.sidecars.pgvector_version","MIOS_PGVECTOR_VERSION"),
    ("image.sidecars.pgvector",        "MIOS_PGVECTOR_IMAGE"),
    ("image.sidecars.llama_swap_version","MIOS_LLAMA_SWAP_VERSION"),
    ("image.sidecars.llama_swap",      "MIOS_LLAMA_SWAP_IMAGE"),
    ("image.sidecars.adguard_version", "MIOS_ADGUARD_VERSION"),
    ("image.sidecars.adguard",         "MIOS_ADGUARD_IMAGE"),
    # ── services (per-service identity: user / uid / gid) ─────────────────
    ("services.forge.user",            "MIOS_FORGE_USER"),
    ("services.forge.uid",             "MIOS_FORGE_UID"),
    ("services.forge.gid",             "MIOS_FORGE_GID"),
    ("services.searxng.user",          "MIOS_SEARXNG_USER"),
    ("services.searxng.uid",           "MIOS_SEARXNG_UID"),
    ("services.searxng.gid",           "MIOS_SEARXNG_GID"),
    ("services.ceph.user",             "MIOS_CEPH_USER"),
    ("services.ceph.uid",              "MIOS_CEPH_UID"),
    ("services.ceph.gid",              "MIOS_CEPH_GID"),
    ("services.hermes.user",           "MIOS_HERMES_USER"),
    ("services.hermes.uid",            "MIOS_HERMES_UID"),
    ("services.hermes.gid",            "MIOS_HERMES_GID"),
    ("services.open_webui.user",       "MIOS_OPEN_WEBUI_USER"),
    ("services.open_webui.uid",        "MIOS_OPEN_WEBUI_UID"),
    ("services.open_webui.gid",        "MIOS_OPEN_WEBUI_GID"),
    ("services.pgvector.user",         "MIOS_PGVECTOR_USER"),
    ("services.pgvector.uid",          "MIOS_PGVECTOR_UID"),
    ("services.pgvector.gid",          "MIOS_PGVECTOR_GID"),
    ("services.llamacpp.user",         "MIOS_LLAMACPP_USER"),
    ("services.llamacpp.uid",          "MIOS_LLAMACPP_UID"),
    ("services.llamacpp.gid",          "MIOS_LLAMACPP_GID"),
    ("services.agent_pipe.user",       "MIOS_AGENT_PIPE_USER"),
    ("services.agent_pipe.uid",        "MIOS_AGENT_PIPE_UID"),
    ("services.agent_pipe.gid",        "MIOS_AGENT_PIPE_GID"),
    ("services.ollama_cpu.user",       "MIOS_OLLAMA_CPU_USER"),
    ("services.ollama_cpu.uid",        "MIOS_OLLAMA_CPU_UID"),
    ("services.ollama_cpu.gid",        "MIOS_OLLAMA_CPU_GID"),
    # OOM/parallelism guard (operator 2026-06-01) -> mios-ollama-cpu.container
    ("services.ollama_cpu.num_parallel", "MIOS_OLLAMA_CPU_NUM_PARALLEL"),
    ("services.ollama_cpu.max_loaded", "MIOS_OLLAMA_CPU_MAX_LOADED"),
    ("services.ollama_cpu.mem_high",   "MIOS_OLLAMA_CPU_MEM_HIGH"),
    ("services.ollama_cpu.mem_max",    "MIOS_OLLAMA_CPU_MEM_MAX"),
    # [services.webtools] -- consolidated web-tools container (firecrawl +
    # crawl4ai + camoufox). Renamed from [services.crawl4ai] 2026-05-24; the
    # canonical env is now MIOS_WEBTOOLS_* + legacy MIOS_CRAWL4AI_* aliases are
    # kept (sysusers/tmpfiles still name the user mios-crawl4ai @ uid 824).
    ("services.webtools.user",         "MIOS_WEBTOOLS_USER"),
    ("services.webtools.uid",          "MIOS_WEBTOOLS_UID"),
    ("services.webtools.gid",          "MIOS_WEBTOOLS_GID"),
    ("services.webtools.user",         "MIOS_CRAWL4AI_USER"),
    ("services.webtools.uid",          "MIOS_CRAWL4AI_UID"),
    ("services.webtools.gid",          "MIOS_CRAWL4AI_GID"),
    ("services.adguard.user",          "MIOS_ADGUARD_USER"),
    ("services.adguard.uid",           "MIOS_ADGUARD_UID"),
    ("services.adguard.gid",           "MIOS_ADGUARD_GID"),
    ("image.sidecars.ollama_cpu_version", "MIOS_OLLAMA_CPU_VERSION"),
    ("image.sidecars.ollama_cpu",      "MIOS_OLLAMA_CPU_IMAGE"),
    # ── security (Phase B.3 -- Semantic Firewall allowlist) ──────────────
    ("security.allowlist_hosts",       "MIOS_SECURITY_ALLOWLIST_HOSTS"),
    ("security.firewall_high_privilege_verbs",
                                       "MIOS_SECURITY_FIREWALL_HIGH_PRIVILEGE_VERBS"),
    # ── WS-7 immutable-host hardening (UKI + fapolicyd, DEFAULT-OFF) ─────
    ("security.fapolicyd_observe.enable", "MIOS_FAPOLICYD_OBSERVE_ENABLE"),
    ("uki.verity_uki_build",             "MIOS_UKI_VERITY_BUILD"),
    # ── fs_watcher (Phase A.2 -- inotify event bus) ──────────────────────
    ("fs_watcher.watch_dirs",          "MIOS_FS_WATCHER_DIRS"),
    # ── pkg (Phase C.1 -- Personal Knowledge Graph) ──────────────────────
    ("pkg.bootstrap_per_source_cap",   "MIOS_PKG_BOOTSTRAP_PER_SOURCE_CAP"),
    ("pkg.lookup_max_alias_results",   "MIOS_PKG_LOOKUP_MAX_ALIAS_RESULTS"),
    # ── refine + polish (Phase D.5 -- agent-pipe orchestration) ─────────
    ("refine.enable",                  "MIOS_REFINE_ENABLE"),
    ("refine.model",                   "MIOS_REFINE_MODEL"),
    ("refine.endpoint",                "MIOS_REFINE_ENDPOINT"),
    ("refine.timeout_seconds",         "MIOS_REFINE_TIMEOUT_S"),
    ("refine.max_tokens",              "MIOS_REFINE_MAX_TOKENS"),
    ("refine.bypass_chars",            "MIOS_REFINE_BYPASS_CHARS"),
    ("polish.enable",                  "MIOS_POLISH_ENABLE"),
    ("polish.model",                   "MIOS_POLISH_MODEL"),
    ("polish.endpoint",                "MIOS_POLISH_ENDPOINT"),
    ("polish.timeout_seconds",         "MIOS_POLISH_TIMEOUT_S"),
    ("polish.max_tokens",              "MIOS_POLISH_MAX_TOKENS"),
    # ── ttyd (Phase D.2 -- browser pty bridge for bash + powershell) ─────
    ("ttyd.enable",                    "MIOS_TTYD_ENABLE"),
    ("ttyd.bind",                      "MIOS_TTYD_BIND"),
    ("ttyd.require_auth",              "MIOS_TTYD_REQUIRE_AUTH"),
    ("ttyd.auth_user",                 "MIOS_TTYD_AUTH_USER"),
    ("ttyd.auth_pass",                 "MIOS_TTYD_AUTH_PASS"),
    ("ttyd.ssl_cert",                  "MIOS_TTYD_SSL_CERT"),
    ("ttyd.ssl_key",                   "MIOS_TTYD_SSL_KEY"),
    ("ttyd.bash_shell",                "MIOS_TTYD_BASH_SHELL"),
    ("ttyd.powershell_shell",          "MIOS_TTYD_POWERSHELL_SHELL"),
    ("ttyd.writable",                  "MIOS_TTYD_WRITABLE"),
    ("ttyd.max_clients",               "MIOS_TTYD_MAX_CLIENTS"),
    ("ttyd.font_size",                 "MIOS_TTYD_FONT_SIZE"),
    ("ports.ttyd_bash",                "MIOS_PORT_TTYD_BASH"),
    ("ports.ttyd_powershell",          "MIOS_PORT_TTYD_POWERSHELL"),
    # ── passport (Phase C.3 -- Ed25519 agent identity tokens) ────────────
    ("passport.enable",                "MIOS_PASSPORT_ENABLE"),
    ("passport.algo",                  "MIOS_PASSPORT_ALGO"),
    ("passport.key_dir",               "MIOS_PASSPORT_KEY_DIR"),
    ("passport.rotate_days",           "MIOS_PASSPORT_ROTATE_DAYS"),
    ("passport.verify_on_read",        "MIOS_PASSPORT_VERIFY_ON_READ"),
    ("passport.agents",                "MIOS_PASSPORT_AGENTS"),
    # ── skills (Phase C.2 -- Sequential Pattern Mining + catalog) ────────
    ("skills.enable",                  "MIOS_SKILLS_ENABLE"),
    ("skills.min_length",              "MIOS_SKILLS_MIN_LENGTH"),
    ("skills.max_length",              "MIOS_SKILLS_MAX_LENGTH"),
    ("skills.min_support",             "MIOS_SKILLS_MIN_SUPPORT"),
    ("skills.window_hours",            "MIOS_SKILLS_WINDOW_HOURS"),
    ("skills.auto_promote_threshold",  "MIOS_SKILLS_AUTO_PROMOTE_THRESHOLD"),
    ("skills.mine_interval_minutes",   "MIOS_SKILLS_MINE_INTERVAL_MINUTES"),
    ("skills.seed_catalog_dir",        "MIOS_SKILLS_SEED_CATALOG_DIR"),
    ("skills.local_catalog_dir",       "MIOS_SKILLS_LOCAL_CATALOG_DIR"),
    ("skills.min_success_rate",        "MIOS_SKILLS_MIN_SUCCESS_RATE"),
    ("skills.min_success_samples",     "MIOS_SKILLS_MIN_SUCCESS_SAMPLES"),
    # ── agent_pipe (standalone router + refine + critic FastAPI) ─────────
    ("agent_pipe.endpoint",            "MIOS_AGENT_PIPE_ENDPOINT"),
    ("agent_pipe.backend",             "MIOS_AGENT_PIPE_BACKEND"),
    ("agent_pipe.backend_model",       "MIOS_AGENT_PIPE_BACKEND_MODEL"),
    ("agent_pipe.enable",              "MIOS_AGENT_PIPE_ENABLE"),
    # ── surrealdb (shared cross-cutting agent state) ──────────────────────
    ("pgvector.db_backend",              "MIOS_DB_BACKEND"),
    # ── pgvector (WS-9 unified agent-plane datastore, FOSS) ───────────────
    ("pgvector.host",                  "MIOS_PG_HOST"),
    ("pgvector.user",                  "MIOS_PG_USER"),
    ("pgvector.pass",                  "MIOS_PG_PASS"),
    ("pgvector.db",                    "MIOS_PG_DB"),
    ("pgvector.data_dir",              "MIOS_PG_DATA_DIR"),
    ("pgvector.schema_init",           "MIOS_PG_SCHEMA_INIT"),
    ("pgvector.embed_model",           "MIOS_PG_EMBED_MODEL"),
    ("pgvector.enable",                "MIOS_PG_ENABLE"),
    # ── llamacpp / llama-swap lane (WS-10 ollama -> llama.cpp conversion) ──
    ("llamacpp.enable",                "MIOS_LLAMACPP_ENABLE"),
    ("llamacpp.slot_dir",              "MIOS_LLAMACPP_SLOT_DIR"),
    ("llamacpp.models_dir",            "MIOS_LLAMACPP_MODELS_DIR"),
    ("llamacpp.config",                "MIOS_LLAMACPP_CONFIG"),
    ("llamacpp.bake_models",           "MIOS_LLAMACPP_BAKE_MODELS"),
    # ── paths (FHS canonical runtime artifacts) ────────────────────────────
    ("paths.ai_dir",                   "MIOS_AI_DIR"),
    ("paths.ai_models_dir",            "MIOS_AI_MODELS_DIR"),
    ("paths.ai_mcp_dir",               "MIOS_AI_MCP_DIR"),
    ("paths.ai_scratch_dir",           "MIOS_AI_SCRATCH_DIR"),
    ("paths.ai_memory_dir",            "MIOS_AI_MEMORY_DIR"),
    ("paths.ai_journal",               "MIOS_AI_JOURNAL"),
    ("paths.install_env",              "MIOS_INSTALL_ENV"),
    ("paths.profile_toml_vendor",      "MIOS_PROFILE_TOML_VENDOR"),
    ("paths.profile_toml_host",        "MIOS_PROFILE_TOML_HOST"),
    ("paths.wsl_firstboot_done",       "MIOS_WSLBOOT_DONE"),
    ("paths.ollama_firstboot_done",    "MIOS_OLLAMA_FIRSTBOOT_DONE"),
    ("paths.ollama_seed_dir",          "MIOS_AI_SEED_DIR"),
    ("paths.ollama_runtime_dir",       "MIOS_AI_RUNTIME_DIR"),
    ("paths.mios_toml",                "MIOS_TOML"),
    # ── build (build-time tunables) ────────────────────────────────────────
    ("build.rechunk_max_layers",       "MIOS_RECHUNK_MAX_LAYERS"),
    ("build.ai_ram_floor_gb",          "MIOS_AI_RAM_FLOOR_GB"),
    # ── network.quadlet (internal podman bridge) ───────────────────────────
    ("network.quadlet.network",        "MIOS_QUADLET_NETWORK"),
    ("network.quadlet.subnet",         "MIOS_QUADLET_SUBNET"),
    ("network.quadlet.core_subnet",    "MIOS_CORE_NET_SUBNET"),
    ("network.quadlet.core_gateway",   "MIOS_CORE_NET_GATEWAY"),
    # legacy/lightweight aliases (keep older mios.toml drafts working)
    ("user.name",               "MIOS_USER"),
    ("user.hostname",           "MIOS_HOSTNAME"),
    ("build.local_tag",         "MIOS_LOCAL_TAG"),
    ("ai.key",                  "MIOS_AI_KEY"),
    ("flatpaks.install",        "MIOS_FLATPAKS"),
]

for dotted, env in slots:
    v = get(merged, dotted)
    if v is None or v == "":
        continue
    if isinstance(v, list):
        v = ",".join(str(x) for x in v)
    print(f"export {env}={shlex.quote(str(v))}")

# Free-form [env] table: arbitrary KEY=VALUE exports. POSIX-compliant
# names only; silently skip otherwise so 'eval' below doesn't choke.
ev = merged.get("env") if isinstance(merged.get("env"), dict) else {}
for k, v in ev.items():
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', k):
        sys.stderr.write(f"userenv: skipping invalid [env] key: {k!r}\n")
        continue
    if v is None:
        continue
    if isinstance(v, list):
        v = ",".join(str(x) for x in v)
    print(f"export {k}={shlex.quote(str(v))}")
PY
    )
    # `[[ ... ]] && cmd` returns 1 when the test is false. Under `set -e`
    # in the caller (mios-build-driver: `set -euo pipefail`), that
    # propagates as a fatal exit even though "no exports to apply" is the
    # expected state for a fresh install with no toml content yet. Use
    # `if`-form so set -e treats the test as a conditional, not a fatal.
    if [[ -n "$exports" ]]; then
        eval "$exports"
    fi
}
_mios_load_unified

# 2. Backwards-compat: legacy split files (per-user only). Read only when
# none of the three TOML layers contain a [identity] or [user] section --
# i.e., the user is on a pre-unified-schema deployment. Each is shallow
# KEY="VALUE", grep-friendly.
_mios_legacy_get() {
    local file="$1" key="$2"
    grep -E "^${key}\s*=" "$file" 2>/dev/null \
        | head -1 \
        | sed 's/.*=\s*"\?\([^"]*\)"\?.*/\1/' \
        | tr -d '"' || true
}

if [[ -z "${MIOS_USER:-}" && ! -f "$MIOS_USER_TOML" && ! -f "$MIOS_HOST_TOML" ]]; then
    # `[[ ... ]] && cmd` returns 1 when the test is false; under set -e
    # in callers like mios-build-driver, that's fatal even though
    # "key not present in legacy file" is the expected case for fresh
    # installs. Use `[[ -z ... ]] || cmd` form so set -e treats the
    # whole expression as a guard, not a hard fail.
    if [[ -f "${MIOS_CONFIG_DIR}/env.toml" ]]; then
        f="${MIOS_CONFIG_DIR}/env.toml"
        for key in MIOS_USER MIOS_HOSTNAME MIOS_FLATPAKS MIOS_BASE_IMAGE MIOS_LOCAL_TAG; do
            val="$(_mios_legacy_get "$f" "$key")"
            [[ -z "$val" ]] || export "$key=$val"
        done
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/images.toml" ]]; then
        f="${MIOS_CONFIG_DIR}/images.toml"
        for key in MIOS_BASE_IMAGE MIOS_BIB_IMAGE MIOS_IMAGE_NAME; do
            val="$(_mios_legacy_get "$f" "$key")"
            [[ -z "$val" ]] || export "$key=$val"
        done
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/build.toml" ]]; then
        val="$(_mios_legacy_get "${MIOS_CONFIG_DIR}/build.toml" MIOS_LOCAL_TAG)"
        [[ -z "$val" ]] || export "MIOS_LOCAL_TAG=$val"
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/flatpaks.list" ]]; then
        flat=$(grep -vE '^\s*(#|$)' "${MIOS_CONFIG_DIR}/flatpaks.list" 2>/dev/null | paste -sd,)
        [[ -z "$flat" ]] || export "MIOS_FLATPAKS=$flat"
    fi
    if [[ -f "${MIOS_CONFIG_DIR}/env" ]]; then
        set -a
        # shellcheck disable=SC1091
        source "${MIOS_CONFIG_DIR}/env"
        set +a
    fi
fi
