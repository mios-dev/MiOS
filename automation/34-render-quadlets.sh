#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Processes Quadlet container files by replacing ${MIOS_*} placeholders with values from mios.toml using envsubst, ensuring systemd-compatible container definitions are baked with correct host-specific UIDs, GIDs, and network configs.
# AI-related: /usr/share/mios/kb
# AI-functions: _render_with_envsubst, _render_with_bash
set -euo pipefail

# shellcheck disable=SC1090  # log.sh resolves at runtime: build ctx or installed
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

# shellcheck source=/dev/null
source "$(dirname "$0")/lib/common.sh"

if id -u mios >/dev/null 2>&1; then
    # Declared then assigned: `export X="$(cmd)"` masks the command's exit status.
    MIOS_CODE_SERVER_UID="$(id -u mios)"
    MIOS_CODE_SERVER_GID="$(id -g mios)"
    export MIOS_CODE_SERVER_UID MIOS_CODE_SERVER_GID
fi

mios_log "Render Quadlet placeholders from mios.toml"

if command -v miosd >/dev/null 2>&1; then
    miosd render-quadlets
    mios_ok "Rendered Quadlet placeholders via miosd"
    exit 0
fi

QUADLET_DIRS=(
    /etc/containers/systemd
    /etc/containers/systemd/users
    /usr/share/containers/systemd
    /usr/share/containers/systemd/users
    /etc/mios
    /usr/share/mios/kb
    /usr/lib/systemd/system/cockpit.socket.d
    /usr/lib/systemd/system
)

_render_with_envsubst() {
    local f="$1"
    local content
    content="$(cat "$f")"
    while [[ "$content" =~ \$\{([A-Z_][A-Z0-9_]*):-([^}]*)\} ]]; do
        local _v="${BASH_REMATCH[1]}"
        local _d="${BASH_REMATCH[2]}"
        local _val="${!_v:-}"
        local _rep="${_val:-$_d}"
        content="${content//${BASH_REMATCH[0]}/${_rep}}"
    done
    printf '%s' "$content" | envsubst '${MIOS_SYS_IMAGE} ${MIOS_CUDA_IMAGE} ${MIOS_K3S_IMAGE} ${MIOS_CEPH_IMAGE} ${MIOS_FORGE_IMAGE} ${MIOS_SEARXNG_IMAGE} ${MIOS_HERMES_IMAGE} ${MIOS_OPEN_WEBUI_IMAGE} ${MIOS_CODE_SERVER_IMAGE} ${MIOS_GUACAMOLE_IMAGE} ${MIOS_FORGE_RUNNER_IMAGE} ${MIOS_CROWDSEC_IMAGE} ${MIOS_POSTGRES_IMAGE} ${MIOS_GUACD_IMAGE} ${MIOS_PXE_HUB_IMAGE} ${MIOS_BIB_ALPINE_IMAGE} ${MIOS_PORT_SSH} ${MIOS_PORT_FORGE_HTTP} ${MIOS_PORT_FORGE_SSH} ${MIOS_PORT_GUACD} ${MIOS_PORT_REDIS} ${MIOS_PORT_PXE_HUB_API} ${MIOS_PORT_COCKPIT} ${MIOS_PORT_COCKPIT_LINK} ${MIOS_PORT_SEARXNG} ${MIOS_PORT_CRAWL4AI} ${MIOS_PORT_FIRECRAWL} ${MIOS_PORT_HERMES} ${MIOS_PORT_HERMES_DASHBOARD} ${MIOS_PORT_AGENT_PIPE} ${MIOS_PORT_OPEN_WEBUI} ${MIOS_PORT_CODE_SERVER} ${MIOS_K3S_API_PORT} ${MIOS_GUACAMOLE_PORT} ${MIOS_CEPH_DASHBOARD_PORT} ${MIOS_RDP_PORT} ${MIOS_FORGE_USER} ${MIOS_FORGE_UID} ${MIOS_FORGE_GID} ${MIOS_SEARXNG_USER} ${MIOS_SEARXNG_UID} ${MIOS_SEARXNG_GID} ${MIOS_CEPH_USER} ${MIOS_CEPH_UID} ${MIOS_CEPH_GID} ${MIOS_HERMES_USER} ${MIOS_HERMES_UID} ${MIOS_HERMES_GID} ${MIOS_OPEN_WEBUI_USER} ${MIOS_OPEN_WEBUI_UID} ${MIOS_OPEN_WEBUI_GID} ${MIOS_CODE_SERVER_UID} ${MIOS_CODE_SERVER_GID} ${MIOS_QUADLET_NETWORK} ${MIOS_QUADLET_SUBNET} ${MIOS_CORE_NET_SUBNET} ${MIOS_CORE_NET_GATEWAY} ${MIOS_AI_DIR} ${MIOS_AI_MODELS_DIR} ${MIOS_AI_MCP_DIR} ${MIOS_DB_USER} ${MIOS_DB_PASS} ${MIOS_DB_BACKEND} ${MIOS_DB_DATA_DIR} ${MIOS_ADGUARD_IMAGE} ${MIOS_PORT_ADGUARD_DNS} ${MIOS_PORT_ADGUARD_UI} ${MIOS_ADGUARD_USER} ${MIOS_ADGUARD_UID} ${MIOS_ADGUARD_GID} ${MIOS_PORT_VLLM} ${MIOS_VLLM_IMAGE} ${MIOS_VLLM_SERVED_NAME} ${MIOS_VLLM_GPU_UTIL} ${MIOS_VLLM_MAX_MODEL_LEN} ${MIOS_VLLM_USE_V1} ${MIOS_CODEMODE_UID} ${MIOS_CODEMODE_GID} ${MIOS_PGVECTOR_IMAGE} ${MIOS_PORT_PGVECTOR} ${MIOS_PGVECTOR_USER} ${MIOS_PGVECTOR_UID} ${MIOS_PGVECTOR_GID} ${MIOS_PG_USER} ${MIOS_PG_PASS} ${MIOS_PG_DB} ${MIOS_PG_DATA_DIR} ${MIOS_PG_BIND_ADDR} ${MIOS_PG_BACKUP_DIR} ${MIOS_PG_BACKUP_KEEP} ${MIOS_PG_BACKUP_ENABLE} ${MIOS_PG_HNSW_ITERATIVE_SCAN} ${MIOS_PG_HNSW_MAX_SCAN_TUPLES} ${MIOS_PG_HNSW_SCAN_MEM_MULTIPLIER} ${MIOS_LLM_LIGHT_IMAGE} ${MIOS_PORT_LLM_LIGHT} ${MIOS_PORT_CPU_NODE} ${MIOS_CPU_NODE_THREADS} ${MIOS_LLAMACPP_UID} ${MIOS_LLAMACPP_GID} ${MIOS_LLAMACPP_SLOT_DIR} ${MIOS_CRAWL4AI_IMAGE} ${MIOS_CRAWL_CDP_URL} ${MIOS_CRAWL_CAMOUFOX} ${MIOS_CRAWL_MIN_CHARS} ${MIOS_FIRECRAWL_IMAGE} ${MIOS_FIRECRAWL_WORKERS} ${MIOS_FIRECRAWL_BULL_KEY} ${MIOS_FIRECRAWL_LOG_LEVEL} ${MIOS_SGLANG_IMAGE} ${MIOS_SGLANG_SERVED_NAME} ${MIOS_PORT_SGLANG} ${MIOS_SGLANG_MEM_FRACTION} ${MIOS_SGLANG_MAX_MODEL_LEN} ${MIOS_SGLANG_TOOL_PARSER} ${MIOS_SGLANG_REASONING_PARSER} ${MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE} ${MIOS_SGLANG_KV_CACHE_DTYPE} ${MIOS_GPU_DEVICE}'
}

_render_with_bash() {
    local f="$1"
    local content
    content="$(cat "$f")"
    for var in MIOS_SYS_IMAGE MIOS_CUDA_IMAGE MIOS_K3S_IMAGE MIOS_CEPH_IMAGE MIOS_FORGE_IMAGE \
               MIOS_SEARXNG_IMAGE MIOS_HERMES_IMAGE MIOS_OPEN_WEBUI_IMAGE MIOS_CODE_SERVER_IMAGE \
               MIOS_GUACAMOLE_IMAGE \
               MIOS_FORGE_RUNNER_IMAGE MIOS_CROWDSEC_IMAGE MIOS_POSTGRES_IMAGE \
               MIOS_GUACD_IMAGE MIOS_PXE_HUB_IMAGE MIOS_BIB_ALPINE_IMAGE \
               \
               MIOS_PORT_SSH MIOS_PORT_FORGE_HTTP MIOS_PORT_FORGE_SSH \
               MIOS_PORT_GUACD MIOS_PORT_REDIS MIOS_PORT_PXE_HUB_API \
               MIOS_PORT_OTELCOL_OTLP MIOS_PORT_OTELCOL_UI MIOS_PORT_CHROME_CDP \
               MIOS_PORT_COCKPIT MIOS_PORT_COCKPIT_LINK MIOS_PORT_SEARXNG MIOS_PORT_CRAWL4AI \
               MIOS_PORT_FIRECRAWL \
               MIOS_PORT_HERMES MIOS_PORT_HERMES_DASHBOARD MIOS_PORT_AGENT_PIPE MIOS_PORT_OPENCODE_GATEWAY MIOS_PORT_OPEN_WEBUI MIOS_PORT_CODE_SERVER MIOS_PORT_K3S_API MIOS_PORT_GUACAMOLE_WEB \
               MIOS_PORT_CEPH_DASHBOARD MIOS_PORT_RDP \
               MIOS_FORGE_USER MIOS_FORGE_UID MIOS_FORGE_GID \
               MIOS_SEARXNG_USER MIOS_SEARXNG_UID MIOS_SEARXNG_GID \
               MIOS_CEPH_USER MIOS_CEPH_UID MIOS_CEPH_GID \
               MIOS_HERMES_USER MIOS_HERMES_UID MIOS_HERMES_GID \
               MIOS_OPEN_WEBUI_USER MIOS_OPEN_WEBUI_UID MIOS_OPEN_WEBUI_GID \
               \
               \
               \
               \
               MIOS_QUADLET_NETWORK MIOS_QUADLET_SUBNET \
               MIOS_CORE_NET_SUBNET MIOS_CORE_NET_GATEWAY \
               MIOS_AI_DIR MIOS_AI_MODELS_DIR MIOS_AI_MCP_DIR \
               MIOS_DB_USER MIOS_DB_PASS MIOS_DB_BACKEND MIOS_DB_DATA_DIR \
               MIOS_PGVECTOR_IMAGE MIOS_PORT_PGVECTOR \
               MIOS_PGVECTOR_USER MIOS_PGVECTOR_UID MIOS_PGVECTOR_GID \
               MIOS_PG_USER MIOS_PG_PASS MIOS_PG_DB MIOS_PG_DATA_DIR \
               MIOS_PG_BIND_ADDR MIOS_PG_BACKUP_DIR MIOS_PG_BACKUP_KEEP MIOS_PG_BACKUP_ENABLE \
               MIOS_PG_HNSW_ITERATIVE_SCAN MIOS_PG_HNSW_MAX_SCAN_TUPLES MIOS_PG_HNSW_SCAN_MEM_MULTIPLIER \
               MIOS_LLM_LIGHT_IMAGE MIOS_PORT_LLM_LIGHT MIOS_PORT_CPU_NODE MIOS_CPU_NODE_THREADS \
               MIOS_LLAMACPP_UID MIOS_LLAMACPP_GID MIOS_LLAMACPP_SLOT_DIR \
               MIOS_CODEMODE_UID MIOS_CODEMODE_GID \
               MIOS_ADGUARD_IMAGE MIOS_PORT_ADGUARD_DNS MIOS_PORT_ADGUARD_UI \
               MIOS_ADGUARD_USER MIOS_ADGUARD_UID MIOS_ADGUARD_GID \
               MIOS_PORT_VLLM MIOS_VLLM_IMAGE MIOS_VLLM_SERVED_NAME \
               MIOS_VLLM_GPU_UTIL MIOS_VLLM_MAX_MODEL_LEN MIOS_VLLM_USE_V1 \
               MIOS_CRAWL4AI_IMAGE MIOS_CRAWL_CDP_URL MIOS_CRAWL_CAMOUFOX MIOS_CRAWL_MIN_CHARS \
               MIOS_FIRECRAWL_IMAGE MIOS_FIRECRAWL_WORKERS MIOS_FIRECRAWL_BULL_KEY MIOS_FIRECRAWL_LOG_LEVEL \
               MIOS_SGLANG_IMAGE MIOS_SGLANG_SERVED_NAME MIOS_PORT_SGLANG \
               MIOS_SGLANG_MEM_FRACTION MIOS_SGLANG_MAX_MODEL_LEN MIOS_SGLANG_TOOL_PARSER \
               MIOS_SGLANG_REASONING_PARSER MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE MIOS_SGLANG_KV_CACHE_DTYPE MIOS_GPU_DEVICE; do
        local val="${!var:-}"
        content="${content//\$\{${var}\}/${val}}"
        while [[ "$content" =~ \$\{${var}:-([^}]*)\} ]]; do
            local default="${BASH_REMATCH[1]}"
            local replacement="${val:-$default}"
            content="${content//${BASH_REMATCH[0]}/${replacement}}"
        done
    done
    printf '%s' "$content"
}

if command -v envsubst >/dev/null 2>&1; then
    _renderer=_render_with_envsubst
else
    mios_log "Envsubst not found, bash fallback"
    _renderer=_render_with_bash
fi

rendered_count=0
skipped_count=0
for dir in "${QUADLET_DIRS[@]}"; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r -d '' f; do
        if ! grep -q '\${MIOS_' "$f" 2>/dev/null; then
            skipped_count=$((skipped_count + 1))
            continue
        fi
        local_tmp="$(mktemp)"
        $_renderer "$f" > "$local_tmp"
        if [[ "$(basename "$f")" == "mios-llm-heavy.container" ]]; then
            heavy_mode="${MIOS_CONV_INFERENCE_HEAVY_ENGINE_MODE:-dual}"
            if [[ "$heavy_mode" == "single" ]]; then
                mios_log "Apply multi-LoRA config to mios-llm-heavy.container"
                sed -i 's|--enable-prefix-caching|--enable-prefix-caching --enable-lora --max-loras 4 --max-cpu-loras 8 --max-lora-rank 64 --lora-modules coding=/var/lib/mios/lora-adapters/coding reasoning=/var/lib/mios/lora-adapters/reasoning|g' "$local_tmp"
                sed -i '/ContainerName=mios-llm-heavy/a Environment=VLLM_ALLOW_RUNTIME_LORA_UPDATING=true\nEnvironment=VLLM_PLUGINS=lora_filesystem_resolver\nEnvironment=VLLM_LORA_RESOLVER_CACHE_DIR=/var/lib/mios/lora-adapters/\nVolume=/var/lib/mios/lora-adapters:/var/lib/mios/lora-adapters:Z' "$local_tmp"
            fi
        fi
        if ! cmp -s "$f" "$local_tmp"; then
            mv "$local_tmp" "$f"
            chmod 0644 "$f"
            mios_ok "Rendered: $f"
            rendered_count=$((rendered_count + 1))
        else
            rm -f "$local_tmp"
        fi
    done < <(find "$dir" -maxdepth 2 -type f \( -name '*.container' -o -name '*.network' -o -name '*.volume' -o -name '*.pod' -o -name '*.image' -o -name '*.build' -o -name '*.toml' -o -name '*.json' -o -name '*.conf' -o -name '*.service' \) -print0 2>/dev/null)
done

mios_ok "Rendered $rendered_count, skipped $skipped_count"
