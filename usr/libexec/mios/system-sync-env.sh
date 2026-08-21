#!/usr/bin/env bash
# AI-hint: layered mios.toml dotfile.
# AI-related: /etc/mios/install.env, /etc/mios/mios.toml, /usr/share/mios/mios.toml, /usr/lib/mios/userenv.sh, /usr/share/mios/configurator/mios.html, /etc/mios/install.env.XXXXXX, mios-sync-env, mios-tools, mios-hermes (port key `hermes`)
# AI-functions: generate_env
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

RESOLVER=/usr/lib/mios/userenv.sh
if [[ ! -r "$RESOLVER" ]]; then
    echo "Mios-sync-env: resolver $RESOLVER not found" >&2
    exit 1
fi
# shellcheck disable=SC1090  # resolver path is a variable by design (vendor/host/user cascade)
. "$RESOLVER"

_ENV_UNSAFE='[[:space:]"'"'"'$`#]'
emit() {
    local _k="$1" _v="$2"
    if [[ "$_v" =~ $_ENV_UNSAFE ]]; then
        printf 'mios-sync-env: WARN skip %s (value unsafe for a bare env file)\n' "$_k" >&2
        return 0
    fi
    printf '%s=%s\n' "$_k" "$_v"
}

generate_env() {
    local _ai_backend=""
    cat <<EOF
# MIOS_FORGE_ADMIN_PASSWORD, MIOS_GITHUB_TOKEN) are NOT here -- they live
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

    emit MIOS_USER "${MIOS_USER:-mios}"
    emit MIOS_HOSTNAME "${MIOS_HOSTNAME:-mios}"
    [[ -n "${MIOS_USER_FULLNAME:-}" ]] && emit MIOS_USER_FULLNAME "${MIOS_USER_FULLNAME}"
    [[ -n "${MIOS_USER_GROUPS:-}" ]]   && emit MIOS_USER_GROUPS "${MIOS_USER_GROUPS}"
    emit MIOS_DEFAULT_PASSWORD "${MIOS_DEFAULT_PASSWORD:-mios}"

    emit MIOS_AI_ENDPOINT "${MIOS_AI_ENDPOINT:-http://localhost:8640/v1}"
    emit MIOS_AI_MODEL "${MIOS_AI_MODEL:-granite4.1:8b}"
    emit MIOS_AI_EMBED_MODEL "${MIOS_AI_EMBED_MODEL:-nomic-embed-text}"
    _ai_backend="${MIOS_AI_BACKEND:-${MIOS_HERMES_BACKEND_URL:-}}"
    _ai_backend="${_ai_backend%/v1}"
    [[ -n "$_ai_backend" ]] && emit MIOS_AI_BACKEND "${_ai_backend}"

    [[ -n "${MIOS_LLAMACPP_ENABLE:-}" ]]      && emit MIOS_LLAMACPP_ENABLE "${MIOS_LLAMACPP_ENABLE}"
    [[ -n "${MIOS_LLAMACPP_SLOT_DIR:-}" ]]    && emit MIOS_LLAMACPP_SLOT_DIR "${MIOS_LLAMACPP_SLOT_DIR}"
    [[ -n "${MIOS_LLAMACPP_MODELS_DIR:-}" ]]  && emit MIOS_LLAMACPP_MODELS_DIR "${MIOS_LLAMACPP_MODELS_DIR}"
    [[ -n "${MIOS_LLAMACPP_CONFIG:-}" ]]      && emit MIOS_LLAMACPP_CONFIG "${MIOS_LLAMACPP_CONFIG}"
    [[ -n "${MIOS_LLAMACPP_BAKE_MODELS:-}" ]] && emit MIOS_LLAMACPP_BAKE_MODELS "${MIOS_LLAMACPP_BAKE_MODELS}"
    [[ -n "${MIOS_VLLM_BAKE_MODEL:-}" ]]      && emit MIOS_VLLM_BAKE_MODEL "${MIOS_VLLM_BAKE_MODEL}"

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

    [[ -n "${MIOS_ANTIFAB_ENABLE:-}" ]] && emit MIOS_ANTIFAB_ENABLE "${MIOS_ANTIFAB_ENABLE}"
    [[ -n "${MIOS_ANTIFAB_MIN_ENTITIES:-}" ]] && emit MIOS_ANTIFAB_MIN_ENTITIES "${MIOS_ANTIFAB_MIN_ENTITIES}"
    [[ -n "${MIOS_ANTIFAB_GROUND_MIN:-}" ]] && emit MIOS_ANTIFAB_GROUND_MIN "${MIOS_ANTIFAB_GROUND_MIN}"


    for _fk in MIOS_A2O_ORCH_ENGINE MIOS_A2O_ORCH_MODEL MIOS_A2O_ORCH_EFFORT \
               MIOS_A2O_LANE_A_ENGINE MIOS_A2O_LANE_A_MODEL MIOS_A2O_LANE_A_EFFORT MIOS_A2O_LANE_A_ROLE \
               MIOS_A2O_LANE_B_ENGINE MIOS_A2O_LANE_B_MODEL MIOS_A2O_LANE_B_EFFORT MIOS_A2O_LANE_B_ROLE \
               MIOS_A2O_LANE_B_FALLBACK_ENGINE MIOS_A2O_LANE_B_FALLBACK_MODEL MIOS_A2O_LANE_B_FALLBACK_EFFORT MIOS_A2O_LANE_B_PREFER_FALLBACK \
               MIOS_A2O_CLAUDE_EFFORT_FLAG MIOS_A2O_AGY_EFFORT_FLAG MIOS_A2O_GEMINI_EFFORT_FLAG \
               MIOS_A2O_STREAM_REASONING MIOS_A2O_STREAM_PATH; do
        _fv="${!_fk:-}"
        if [[ -n "$_fv" ]]; then emit ${_fk} "${_fv}"; fi
    done


    [[ -n "${MIOS_SGLANG_SERVED_NAME:-}" ]] && emit MIOS_SGLANG_SERVED_NAME "${MIOS_SGLANG_SERVED_NAME}"
    [[ -n "${MIOS_VLLM_SERVED_NAME:-}" ]]   && emit MIOS_VLLM_SERVED_NAME "${MIOS_VLLM_SERVED_NAME}"
    [[ -n "${MIOS_PORT_SGLANG:-}" ]] && emit MIOS_AI_HEAVY_ENDPOINT "http://localhost:${MIOS_PORT_SGLANG}/v1"
    [[ -n "${MIOS_PORT_VLLM:-}" ]]   && emit MIOS_AI_HEAVY_ALT_ENDPOINT "http://localhost:${MIOS_PORT_VLLM}/v1"

    # MIOS_PORT_PGVECTOR is bridged too so shell consumers that can't parse TOML
    for _pk in MIOS_PORT_LLM_LIGHT MIOS_PORT_HERMES MIOS_PORT_HERMES_WORKER MIOS_PORT_AGENT_PIPE MIOS_PORT_PREFILTER MIOS_PORT_OPENCODE MIOS_PORT_PGVECTOR MIOS_PORT_SGLANG MIOS_PORT_VLLM MIOS_PORT_FORGE_HTTP MIOS_FORGE_HTTP_PORT MIOS_PORT_FORGE_SSH MIOS_FORGE_SSH_PORT MIOS_PORT_OPEN_WEBUI MIOS_PORT_CODE_SERVER MIOS_PORT_SEARXNG MIOS_SEARXNG_PORT MIOS_PORT_TTYD_BASH MIOS_PORT_TTYD_POWERSHELL MIOS_PORT_CRAWL4AI MIOS_PORT_FIRECRAWL MIOS_PORT_CPU_NODE MIOS_PORT_OSCONTROL MIOS_PORT_COCKPIT MIOS_PORT_COCKPIT_LINK; do
        _pv="${!_pk:-}"
        if [[ -n "$_pv" ]]; then emit ${_pk} "${_pv}"; fi
    done

    for _tk in MIOS_TTYD_BASH_SHELL MIOS_TTYD_POWERSHELL_SHELL MIOS_TTYD_BIND MIOS_TTYD_REQUIRE_AUTH MIOS_TTYD_AUTH_USER MIOS_TTYD_AUTH_PASS MIOS_TTYD_SSL_CERT MIOS_TTYD_SSL_KEY MIOS_TTYD_WRITABLE MIOS_TTYD_MAX_CLIENTS MIOS_TTYD_FONT_SIZE; do
        _tv="${!_tk:-}"
        if [[ -n "$_tv" ]]; then emit ${_tk} "${_tv}"; fi
    done


    [[ -n "${MIOS_IMAGE_NAME:-}" ]]   && emit MIOS_IMAGE_NAME "${MIOS_IMAGE_NAME}"
    [[ -n "${MIOS_IMAGE_REF:-}" ]]    && emit MIOS_IMAGE_REF "${MIOS_IMAGE_REF}"
    [[ -n "${MIOS_BRANCH:-}" ]]       && emit MIOS_BRANCH "${MIOS_BRANCH}"
    [[ -n "${MIOS_BASE_IMAGE:-}" ]]   && emit MIOS_BASE_IMAGE "${MIOS_BASE_IMAGE}"

    [[ -n "${MIOS_FORGE_ADMIN_USER:-}" ]]  && emit MIOS_FORGE_ADMIN_USER "${MIOS_FORGE_ADMIN_USER}"
    [[ -n "${MIOS_FORGE_ADMIN_EMAIL:-}" ]] && emit MIOS_FORGE_ADMIN_EMAIL "${MIOS_FORGE_ADMIN_EMAIL}"

    # MIOS_FORGE_ADMIN_PASSWORD and MIOS_GITHUB_TOKEN live only in
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
            echo "#"
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

TMP="$(mktemp /etc/mios/install.env.XXXXXX)"
trap 'rm -f "$TMP"' EXIT
generate_env > "$TMP"
chown root:root "$TMP" 2>/dev/null || true
chmod 0640 "$TMP"

_st=0
if grep -qE '="' "$TMP"; then
    echo "Mios-sync-env: SELFTEST double-quoted value present:" >&2
    grep -nE '="' "$TMP" >&2; _st=1
fi
if grep -qE '^MIOS_(USER_PASSWORD_HASH|FORGE_ADMIN_PASSWORD|GITHUB_TOKEN)=' "$TMP"; then
    echo "Mios-sync-env: SELFTEST secret present in install.env:" >&2
    grep -nE '^MIOS_(USER_PASSWORD_HASH|FORGE_ADMIN_PASSWORD|GITHUB_TOKEN)=' "$TMP" >&2; _st=1
fi
if ! bash -u -c ". '$TMP'" >/dev/null 2>&1; then
    echo "Mios-sync-env: SELFTEST $OUT does not source clean under 'set -u'" >&2; _st=1
fi
[[ "$_st" -ne 0 ]] && echo "Mios-sync-env: WARN self-test failed" >&2

mv -f "$TMP" "$OUT"
trap - EXIT

echo "Mios-sync-env: regenerated $OUT from layered mios.toml"
