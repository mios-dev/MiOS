#!/usr/bin/env bash
# AI-hint: layered mios.toml dotfile.
# AI-related: /etc/mios/install.env, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /usr/lib/mios/userenv.sh, /usr/share/mios/configurator/mios.html, /etc/mios/install.env.XXXXXX, mios-sync-env, mios-tools, localhost:8642
# AI-functions: generate_env
# /usr/bin/mios-sync-env -- regenerate /etc/mios/install.env from the
# layered mios.toml dotfile.
#
# Why both files exist:
#   mios.toml    user-edited source of truth (layered overlay:
#                ~/.config/mios/mios.toml > /etc/mios/mios.toml >
#                /usr/share/mios/mios.toml). Owned by the operator.
#   install.env  derived; env-var format consumed by shell scripts,
#                systemd EnvironmentFile= directives, and first-boot
#                services that can't easily parse TOML on their own.
#                Owned by the system; regenerated from mios.toml.
#
# This CLI is the bridge: edit mios.toml (via /usr/share/mios/
# configurator/mios.html or your editor of choice), then run
# 'mios-sync-env' to refresh install.env. Idempotent.
#
# SECRETS ARE NEVER WRITTEN HERE. The operator password hash lives in
# /etc/shadow (baked via `chpasswd -e` in automation/31-user.sh) and in
# /etc/mios/secrets.env (0600); Forge admin password + GitHub token also
# live in secrets.env. install.env carries ONLY non-secret tunables.
# Rationale: install.env is read by THREE parsers with incompatible
# quoting rules -- systemd EnvironmentFile= (no $-expansion, strips outer
# quotes), bash `.`-source (word-splits + set -u expands $6), and podman
# --env-file (does NOT strip quotes). The only serialization safe under
# all three is BARE `KEY=value` with no shell-metachar/whitespace values.
# A `$`-bearing secret (the sha512 hash `$6$salt$digest`) cannot be
# represented safely here at all -- so it is evicted, not quoted.
#
# Output: /etc/mios/install.env, mode 0640, owned root:root. Requires
# sudo because /etc/mios/ is system config (FHS).
#
# Usage:
#   mios-sync-env              # regenerate from current mios.toml
#   mios-sync-env --dry-run    # print to stdout without writing
#   mios-sync-env --show-source # print the resolved layered TOML
#                                source first, then the generated env
set -euo pipefail

DRY_RUN=0
SHOW_SOURCE=0
for arg in "$@"; do
    case "$arg" in
        --dry-run)     DRY_RUN=1 ;;
        --show-source) SHOW_SOURCE=1 ;;
        -h|--help)
            sed -n '2,/^set -euo/p' "$0" | sed -n '/^# /p' | sed 's/^# //'
            exit 0
            ;;
        *) printf 'mios-sync-env: unknown arg %q (try --help)\n' "$arg" >&2; exit 2 ;;
    esac
done

OUT=/etc/mios/install.env

# Source the layered TOML resolver. Lives at /usr/lib/mios/userenv.sh
# (installed by automation/36-tools.sh) and exports MIOS_* vars derived
# from the deep-merged mios.toml overlay.
RESOLVER=/usr/lib/mios/userenv.sh
if [[ ! -r "$RESOLVER" ]]; then
    echo "mios-sync-env: resolver $RESOLVER not found -- is mios-tools installed?" >&2
    exit 1
fi
# shellcheck disable=SC1090
. "$RESOLVER"

# emit KEY VALUE -- write ONE bare `KEY=value` line, the only form safe
# under all three consumers of install.env (see header): systemd
# EnvironmentFile=, bash `.`-source, and podman --env-file. Reject values
# that cannot be represented bare -- whitespace (bash word-splits),
# double/single quote, `$`, backtick, `#` (mis-parse/expand). Such values
# do not belong in a tri-parser flat env file (secrets -> secrets.env;
# free-text/multi-line -> read from mios.toml directly). install-robustness.
_ENV_UNSAFE='[[:space:]"'"'"'$`#]'
emit() {
    local _k="$1" _v="$2"
    if [[ "$_v" =~ $_ENV_UNSAFE ]]; then
        printf 'mios-sync-env: WARN skip %s (value unsafe for a bare env file)\n' "$_k" >&2
        return 0
    fi
    printf '%s=%s\n' "$_k" "$_v"
}

# Render the new install.env. Order matches what wsl-firstboot,
# forge-firstboot, and the llm-light prep step expect.
generate_env() {
    local _ai_backend=""
    cat <<EOF
# /etc/mios/install.env -- DERIVED from mios.toml by mios-sync-env.
# Edit mios.toml (or use /usr/share/mios/configurator/mios.html), then
# run 'sudo mios-sync-env' to refresh this file. Manual edits here are
# overwritten on the next sync. This file holds ONLY non-secret tunables
# as bare KEY=value lines. Secrets (MIOS_USER_PASSWORD_HASH,
# MIOS_FORGE_ADMIN_PASSWORD, MIOS_GITHUB_TOKEN) are NOT here -- they live
# in /etc/shadow and /etc/mios/secrets.env (0600).
#
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
# Source layers (highest precedence first):
EOF
    for layer in \
        "${HOME}/.config/mios/mios.toml" \
        "/etc/mios/mios.toml" \
        "/usr/share/mios/mios.toml"
    do
        if [[ -r "$layer" ]]; then
            echo "#   * $layer"
        fi
    done
    echo ""

    # Identity
    emit MIOS_USER "${MIOS_USER:-mios}"
    emit MIOS_HOSTNAME "${MIOS_HOSTNAME:-mios}"
    [[ -n "${MIOS_USER_FULLNAME:-}" ]] && emit MIOS_USER_FULLNAME "${MIOS_USER_FULLNAME}"
    [[ -n "${MIOS_USER_GROUPS:-}" ]]   && emit MIOS_USER_GROUPS "${MIOS_USER_GROUPS}"
    # Global default password. Every MiOS service (Hermes Workspace,
    # Forge admin, etc.) reads this as its default login credential
    # unless the operator overrides per-service. Vendor default is
    # "mios"; override in /etc/mios/mios.toml [identity].default_password.
    emit MIOS_DEFAULT_PASSWORD "${MIOS_DEFAULT_PASSWORD:-mios}"

    # AI surface (Architectural Law 5: UNIFIED-AI-REDIRECTS). The resolver
    # (userenv.sh) populates these from the layered mios.toml; prefer the
    # resolved value, emit a fallback ONLY for the few keys shell/systemd
    # consumers always expect. Fallback defaults track the live SSOT:
    #   endpoint -> [ai].endpoint  = http://localhost:8640/v1 (AGENT-PIPE ORCHESTRATOR
    # - the UNIFIED entrypoint, model "MiOS-Agent";.
    #               Hermes :8642 is now a LEAF the pipe calls, NOT the client surface.)
    # model -> [ai].model = granite4.1:8b (fleet; the earlier
    #               qwen3.5:2b was a dropped model -> a stale/unservable default)
    emit MIOS_AI_ENDPOINT "${MIOS_AI_ENDPOINT:-http://localhost:8640/v1}"
    emit MIOS_AI_MODEL "${MIOS_AI_MODEL:-granite4.1:8b}"
    emit MIOS_AI_EMBED_MODEL "${MIOS_AI_EMBED_MODEL:-nomic-embed-text}"
    # Inference backend the agents forward to (mios-llm-light front; the
    # :11434 lane retired G5). Derived from the resolver's MIOS_HERMES_BACKEND_URL
    # ([ai].hermes_backend_url, e.g. http://localhost:11450/v1) so MIOS_AI_BACKEND
    # follows the SSOT instead of a hardcoded port. Strip a trailing /v1 so
    # consumers that append their own path get a clean host:port base.
    _ai_backend="${MIOS_AI_BACKEND:-${MIOS_HERMES_BACKEND_URL:-}}"
    _ai_backend="${_ai_backend%/v1}"
    [[ -n "$_ai_backend" ]] && emit MIOS_AI_BACKEND "${_ai_backend}"

    # llama.cpp light lane ([llamacpp] -> MIOS_LLAMACPP_*). All resolver-
    # populated; emit only the values the resolver actually produced (no
    # hardcoded literals). BAKE_MODELS feeds 38-llamacpp-prep.sh + the
    # mios-ai-firstboot online GGUF retry.
    [[ -n "${MIOS_LLAMACPP_ENABLE:-}" ]]      && emit MIOS_LLAMACPP_ENABLE "${MIOS_LLAMACPP_ENABLE}"
    [[ -n "${MIOS_LLAMACPP_SLOT_DIR:-}" ]]    && emit MIOS_LLAMACPP_SLOT_DIR "${MIOS_LLAMACPP_SLOT_DIR}"
    [[ -n "${MIOS_LLAMACPP_MODELS_DIR:-}" ]]  && emit MIOS_LLAMACPP_MODELS_DIR "${MIOS_LLAMACPP_MODELS_DIR}"
    [[ -n "${MIOS_LLAMACPP_CONFIG:-}" ]]      && emit MIOS_LLAMACPP_CONFIG "${MIOS_LLAMACPP_CONFIG}"
    [[ -n "${MIOS_LLAMACPP_BAKE_MODELS:-}" ]] && emit MIOS_LLAMACPP_BAKE_MODELS "${MIOS_LLAMACPP_BAKE_MODELS}"
    [[ -n "${MIOS_VLLM_BAKE_MODEL:-}" ]]      && emit MIOS_VLLM_BAKE_MODEL "${MIOS_VLLM_BAKE_MODEL}"

    # Part 10: Converged-Resource Architecture (MIOS_CONV_*)
    [[ -n "${MIOS_CONV_GATEWAY_MODE:-}" ]]                  && emit MIOS_CONV_GATEWAY_MODE "${MIOS_CONV_GATEWAY_MODE}"
    [[ -n "${MIOS_CONV_GATEWAY_QUEUE_MAXSIZE:-}" ]]         && emit MIOS_CONV_GATEWAY_QUEUE_MAXSIZE "${MIOS_CONV_GATEWAY_QUEUE_MAXSIZE}"
    [[ -n "${MIOS_CONV_GATEWAY_WORKER_CONCURRENCY:-}" ]]    && emit MIOS_CONV_GATEWAY_WORKER_CONCURRENCY "${MIOS_CONV_GATEWAY_WORKER_CONCURRENCY}"
    [[ -n "${MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE:-}" ]]   && emit MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE "${MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE}"
    [[ -n "${MIOS_CONV_INFERENCE_VLLM_LORA_ADAPTERS_DIR:-}" ]] && emit MIOS_CONV_INFERENCE_VLLM_LORA_ADAPTERS_DIR "${MIOS_CONV_INFERENCE_VLLM_LORA_ADAPTERS_DIR}"
    [[ -n "${MIOS_CONV_INFERENCE_VLLM_ALLOW_RUNTIME_LORA:-}" ]] && emit MIOS_CONV_INFERENCE_VLLM_ALLOW_RUNTIME_LORA "${MIOS_CONV_INFERENCE_VLLM_ALLOW_RUNTIME_LORA}"
    [[ -n "${MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS:-}" ]] && emit MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS "${MIOS_CONV_INFERENCE_LLAMA_CACHE_REUSE_TOKENS}"
    [[ -n "${MIOS_CONV_INFERENCE_LLAMA_PARALLEL_SLOTS:-}" ]] && emit MIOS_CONV_INFERENCE_LLAMA_PARALLEL_SLOTS "${MIOS_CONV_INFERENCE_LLAMA_PARALLEL_SLOTS}"
    [[ -n "${MIOS_CONV_INFERENCE_RETIRE_HEAVY_ALT:-}" ]]    && emit MIOS_CONV_INFERENCE_RETIRE_HEAVY_ALT "${MIOS_CONV_INFERENCE_RETIRE_HEAVY_ALT}"
    [[ -n "${MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE:-}" ]]      && emit MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE "${MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE}"
    [[ -n "${MIOS_CONV_MEMORY_SCRATCHPAD_DIR:-}" ]]         && emit MIOS_CONV_MEMORY_SCRATCHPAD_DIR "${MIOS_CONV_MEMORY_SCRATCHPAD_DIR}"
    [[ -n "${MIOS_CONV_MEMORY_COLD_EVICT_ENABLE:-}" ]]      && emit MIOS_CONV_MEMORY_COLD_EVICT_ENABLE "${MIOS_CONV_MEMORY_COLD_EVICT_ENABLE}"
    [[ -n "${MIOS_CONV_MEMORY_COLD_STORAGE_DIR:-}" ]]       && emit MIOS_CONV_MEMORY_COLD_STORAGE_DIR "${MIOS_CONV_MEMORY_COLD_STORAGE_DIR}"
    [[ -n "${MIOS_CONV_MEMORY_COLD_RETENTION_DAYS:-}" ]]    && emit MIOS_CONV_MEMORY_COLD_RETENTION_DAYS "${MIOS_CONV_MEMORY_COLD_RETENTION_DAYS}"
    [[ -n "${MIOS_CONV_MEMORY_COLD_ZSTD_LEVEL:-}" ]]        && emit MIOS_CONV_MEMORY_COLD_ZSTD_LEVEL "${MIOS_CONV_MEMORY_COLD_ZSTD_LEVEL}"
    [[ -n "${MIOS_CONV_IMAGE_DISTROLESS_ENABLE:-}" ]]       && emit MIOS_CONV_IMAGE_DISTROLESS_ENABLE "${MIOS_CONV_IMAGE_DISTROLESS_ENABLE}"
    [[ -n "${MIOS_CONV_IMAGE_RECHUNK_ENABLE:-}" ]]          && emit MIOS_CONV_IMAGE_RECHUNK_ENABLE "${MIOS_CONV_IMAGE_RECHUNK_ENABLE}"
    [[ -n "${MIOS_CONV_IMAGE_MCP_POOL_ENABLE:-}" ]]         && emit MIOS_CONV_IMAGE_MCP_POOL_ENABLE "${MIOS_CONV_IMAGE_MCP_POOL_ENABLE}"

    # Anti-fabricated-execution guard ([verity].antifab_enable -> the agent-pipe
    # routing layer, which reads MIOS_ANTIFAB_ENABLE from this EnvironmentFile).
    # Resolver-populated; emit only what resolved so an unset SSOT key leaves the
    # Python default (guard ON) intact -- degrade-open.
    [[ -n "${MIOS_ANTIFAB_ENABLE:-}" ]] && emit MIOS_ANTIFAB_ENABLE "${MIOS_ANTIFAB_ENABLE}"
    # Per-section grounding thresholds ([verity].antifab_min_entities / .ground_min
    # -> the FAB-02 citation guard). Resolver-populated; emit only what resolved so
    # an unset key leaves the Python degrade-open default intact.
    [[ -n "${MIOS_ANTIFAB_MIN_ENTITIES:-}" ]] && emit MIOS_ANTIFAB_MIN_ENTITIES "${MIOS_ANTIFAB_MIN_ENTITIES}"
    [[ -n "${MIOS_ANTIFAB_GROUND_MIN:-}" ]] && emit MIOS_ANTIFAB_GROUND_MIN "${MIOS_ANTIFAB_GROUND_MIN}"


    # Frontier / A2O war-room roles (mios.toml [frontier] -> MIOS_A2O_* that the
    # mios-agents container's mios-a2o harness reads). Resolver-populated; emit only
    # what resolved (empty effort-flag templates stay unset = degrade-open).
    for _fk in MIOS_A2O_ORCH_ENGINE MIOS_A2O_ORCH_MODEL MIOS_A2O_ORCH_EFFORT \
               MIOS_A2O_LANE_A_ENGINE MIOS_A2O_LANE_A_MODEL MIOS_A2O_LANE_A_EFFORT MIOS_A2O_LANE_A_ROLE \
               MIOS_A2O_LANE_B_ENGINE MIOS_A2O_LANE_B_MODEL MIOS_A2O_LANE_B_EFFORT MIOS_A2O_LANE_B_ROLE \
               MIOS_A2O_LANE_B_FALLBACK_ENGINE MIOS_A2O_LANE_B_FALLBACK_MODEL MIOS_A2O_LANE_B_FALLBACK_EFFORT MIOS_A2O_LANE_B_PREFER_FALLBACK \
               MIOS_A2O_CLAUDE_EFFORT_FLAG MIOS_A2O_AGY_EFFORT_FLAG MIOS_A2O_GEMINI_EFFORT_FLAG \
               MIOS_A2O_STREAM_REASONING MIOS_A2O_STREAM_PATH; do
        _fv="${!_fk:-}"
        if [[ -n "$_fv" ]]; then emit ${_fk} "${_fv}"; fi
    done


    # Heavy GPU lanes (gated/off-by-default; resolver-populated served names +
    # ports). Endpoints assembled from the lane ports so the value tracks the
    # SSOT rather than a hardcoded literal; emit only when the port resolved.
    [[ -n "${MIOS_SGLANG_SERVED_NAME:-}" ]] && emit MIOS_SGLANG_SERVED_NAME "${MIOS_SGLANG_SERVED_NAME}"
    [[ -n "${MIOS_VLLM_SERVED_NAME:-}" ]]   && emit MIOS_VLLM_SERVED_NAME "${MIOS_VLLM_SERVED_NAME}"
    [[ -n "${MIOS_PORT_SGLANG:-}" ]] && emit MIOS_AI_HEAVY_ENDPOINT "http://localhost:${MIOS_PORT_SGLANG}/v1"
    [[ -n "${MIOS_PORT_VLLM:-}" ]]   && emit MIOS_AI_HEAVY_ALT_ENDPOINT "http://localhost:${MIOS_PORT_VLLM}/v1"

    # Resolved service ports (SSOT [ports].*). Emitted as NUMERIC vars so
    # EnvironmentFile= consumers (agent-pipe, hermes) AND ${MIOS_PORT_*}
    # templates in mios.toml endpoint URLs can resolve -- systemd and Python
    # do NOT expand ${...} from sibling env lines, so the ports must exist as
    # their own vars. Without this the agent-pipe read a LITERAL
    # "${MIOS_PORT_HERMES_WORKER}" worker port -> httpx InvalidURL -> :8640 500.
    # MIOS_PORT_PGVECTOR is bridged too so shell consumers that can't parse TOML
    # (the greenboot AI-plane health check, datastore probes) read the datastore
    # port from the SSOT instead of a hardcoded :5432 literal.
    # install-robustness.
    for _pk in MIOS_PORT_LLM_LIGHT MIOS_PORT_HERMES MIOS_PORT_HERMES_WORKER MIOS_PORT_AGENT_PIPE MIOS_PORT_PREFILTER MIOS_PORT_OPENCODE MIOS_PORT_PGVECTOR MIOS_PORT_SGLANG MIOS_PORT_VLLM MIOS_PORT_FORGE_HTTP MIOS_FORGE_HTTP_PORT MIOS_PORT_FORGE_SSH MIOS_FORGE_SSH_PORT MIOS_PORT_OPEN_WEBUI MIOS_PORT_CODE_SERVER MIOS_PORT_SEARXNG MIOS_SEARXNG_PORT MIOS_PORT_TTYD_BASH MIOS_PORT_TTYD_POWERSHELL MIOS_PORT_CRAWL4AI MIOS_PORT_FIRECRAWL MIOS_PORT_CPU_NODE MIOS_PORT_OSCONTROL MIOS_PORT_COCKPIT MIOS_PORT_COCKPIT_LINK; do
        _pv="${!_pk:-}"
        if [[ -n "$_pv" ]]; then emit ${_pk} "${_pv}"; fi
    done

    # ttyd parameters
    for _tk in MIOS_TTYD_BASH_SHELL MIOS_TTYD_POWERSHELL_SHELL MIOS_TTYD_BIND MIOS_TTYD_REQUIRE_AUTH MIOS_TTYD_AUTH_USER MIOS_TTYD_AUTH_PASS MIOS_TTYD_SSL_CERT MIOS_TTYD_SSL_KEY MIOS_TTYD_WRITABLE MIOS_TTYD_MAX_CLIENTS MIOS_TTYD_FONT_SIZE; do
        _tv="${!_tk:-}"
        if [[ -n "$_tv" ]]; then emit ${_tk} "${_tv}"; fi
    done


    # Image
    [[ -n "${MIOS_IMAGE_NAME:-}" ]]   && emit MIOS_IMAGE_NAME "${MIOS_IMAGE_NAME}"
    [[ -n "${MIOS_IMAGE_REF:-}" ]]    && emit MIOS_IMAGE_REF "${MIOS_IMAGE_REF}"
    [[ -n "${MIOS_BRANCH:-}" ]]       && emit MIOS_BRANCH "${MIOS_BRANCH}"
    [[ -n "${MIOS_BASE_IMAGE:-}" ]]   && emit MIOS_BASE_IMAGE "${MIOS_BASE_IMAGE}"

    # Forge admin (non-secret half)
    [[ -n "${MIOS_FORGE_ADMIN_USER:-}" ]]  && emit MIOS_FORGE_ADMIN_USER "${MIOS_FORGE_ADMIN_USER}"
    [[ -n "${MIOS_FORGE_ADMIN_EMAIL:-}" ]] && emit MIOS_FORGE_ADMIN_EMAIL "${MIOS_FORGE_ADMIN_EMAIL}"

    # Secrets are intentionally ABSENT here (R2). MIOS_USER_PASSWORD_HASH,
    # MIOS_FORGE_ADMIN_PASSWORD and MIOS_GITHUB_TOKEN live only in
    # /etc/shadow (baked) and /etc/mios/secrets.env (0600). The password
    # hash is a `$6$salt$digest` string -- unrepresentable in a bare
    # tri-parser env file -- so it was the root of the `$6: unbound
    # variable` service cascade; evicting it (not quoting it) is the fix.
    # Force a clean 0 return so a trailing false `&& emit` never makes
    # `generate_env > "$TMP"` fail under set -e and brick the env bridge.
    return 0
}

if [[ "$SHOW_SOURCE" -eq 1 ]]; then
    echo "# ===== layered TOML source ====="
    for layer in \
        "${HOME}/.config/mios/mios.toml" \
        "/etc/mios/mios.toml" \
        "/usr/share/mios/mios.toml"
    do
        if [[ -r "$layer" ]]; then
            echo "# --- $layer ---"
            cat "$layer"
            echo ""
        fi
    done
    echo "# ===== generated install.env ====="
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    generate_env
    exit 0
fi

# Write atomically (mktemp + rename) so a concurrent reader never
# sees a half-written file.
TMP="$(mktemp /etc/mios/install.env.XXXXXX)"
trap 'rm -f "$TMP"' EXIT
generate_env > "$TMP"
chown root:root "$TMP" 2>/dev/null || true
chmod 0640 "$TMP"

# R4 self-test: assert the serialization can never crash a consumer.
# Runs on the TMP before the atomic swap. Non-fatal (a warned imperfect
# file beats no env at all -- see the generate_env brick history), but
# loud; the hard gate is drift-check "install-env-safe" in automation/38.
_st=0
if grep -qE '="' "$TMP"; then
    echo "mios-sync-env: SELFTEST double-quoted value(s) present (breaks podman --env-file):" >&2
    grep -nE '="' "$TMP" >&2; _st=1
fi
if grep -qE '^MIOS_(USER_PASSWORD_HASH|FORGE_ADMIN_PASSWORD|GITHUB_TOKEN)=' "$TMP"; then
    echo "mios-sync-env: SELFTEST secret present in install.env (must live only in secrets.env):" >&2
    grep -nE '^MIOS_(USER_PASSWORD_HASH|FORGE_ADMIN_PASSWORD|GITHUB_TOKEN)=' "$TMP" >&2; _st=1
fi
if ! bash -u -c ". '$TMP'" >/dev/null 2>&1; then
    echo "mios-sync-env: SELFTEST $OUT does not source clean under 'set -u'" >&2; _st=1
fi
[[ "$_st" -ne 0 ]] && echo "mios-sync-env: WARN self-test failed -- writing anyway (drift-gate is the hard gate)" >&2

mv -f "$TMP" "$OUT"
trap - EXIT

echo "mios-sync-env: regenerated $OUT from layered mios.toml"
