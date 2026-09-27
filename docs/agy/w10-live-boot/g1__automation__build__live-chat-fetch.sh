#!/usr/bin/env bash
# AI-hint: Build-time staging for the W10 live-boot AI chat lane -- fetches the
# AI-related: mios.toml [cat.live_chat], [llamacpp].bake_models, mios-cpu-node,
set -euo pipefail

ROOTFS="${1:?usage: live-chat-fetch.sh <exported-rootfs-dir>}"
[[ -d "$ROOTFS" ]] || { echo "[live-chat-fetch] ROOTFS '$ROOTFS' does not exist" >&2; exit 1; }

source "$(dirname "$0")/../lib/common.sh" 2>/dev/null || {
    log() { printf '[live-chat-fetch] %s\n' "$*"; }
    printf '[live-chat-fetch] WARN: lib/common.sh unavailable -- continuing with bare logging\n' >&2
}

BAKE_SPEC="${MIOS_LLAMACPP_BAKE_MODELS:-}"
MODEL_KEY="${MIOS_CAT_LIVE_CHAT_MODEL:-lfm2-700m}"
FALLBACK_KEY="${MIOS_CAT_LIVE_CHAT_MODEL_FALLBACK:-granite-4.1-8b}"
INCLUDE_FALLBACK="${MIOS_CAT_LIVE_CHAT_INCLUDE_FALLBACK:-false}"
PORT="${MIOS_CAT_LIVE_CHAT_PORT:-8642}"
LLAMA_SWAP_IMAGE="${MIOS_CAT_LIVE_CHAT_LLAMA_SWAP_IMAGE:-ghcr.io/mostlygeek/llama-swap:cuda}"

MODELS_DIR="${ROOTFS}/usr/share/mios/live-chat/models"
BIN_PATH="${ROOTFS}/usr/libexec/mios/llama-server"
SBOM_DIR="${ROOTFS}/usr/share/mios/artifacts/sbom"
install -d -m 0755 "$MODELS_DIR" "$(dirname "$BIN_PATH")" "$SBOM_DIR"

if [[ ! -s "$BIN_PATH" ]]; then
    _cid="$(podman create "$LLAMA_SWAP_IMAGE" true)"
    if podman cp "${_cid}:/usr/bin/llama-server" "$BIN_PATH"; then
        chmod 0755 "$BIN_PATH"
        log "[live-chat-fetch] staged llama-server binary from ${LLAMA_SWAP_IMAGE}"
    else
        podman rm -f "$_cid" >/dev/null 2>&1 || true
        echo "[live-chat-fetch] FATAL: could not extract llama-server from ${LLAMA_SWAP_IMAGE}" >&2
        exit 1
    fi
    podman rm -f "$_cid" >/dev/null 2>&1 || true
fi

_lookup() { # _lookup <key> -> prints "repo:file" on stdout, empty if absent
    local want="${1}.gguf" entry dest rest
    IFS=',' read -ra _entries <<< "$BAKE_SPEC"
    for entry in "${_entries[@]}"; do
        entry="$(printf '%s' "$entry" | tr -d '[:space:]')"
        [[ -z "$entry" ]] && continue
        dest="${entry%%=*}"
        rest="${entry#*=}"
        if [[ "$dest" == "$want" ]]; then
            printf '%s' "$rest"
            return 0
        fi
    done
    return 1
}

_fetch_one() { # _fetch_one <key> <required:true|false>
    local key="$1" required="$2" dest="${1}.gguf" spec repo file url sha
    spec="$(_lookup "$key")" || spec=""
    if [[ -z "$spec" ]]; then
        log "[live-chat-fetch] no [llamacpp].bake_models entry for '${dest}'"
        if [[ "$required" == "true" ]]; then
            echo "[live-chat-fetch] FATAL: default model key '${key}' has no [llamacpp].bake_models entry" >&2
            exit 1
        fi
        return 0
    fi
    repo="${spec%%:*}"
    file="${spec#*:}"
    if [[ -s "${MODELS_DIR}/${dest}" ]]; then
        log "[live-chat-fetch] ${dest} already staged"
        return 0
    fi
    url="https://huggingface.co/${repo}/resolve/main/${file}"
    if curl -fL -C - --retry 3 --max-time 1800 -o "${MODELS_DIR}/${dest}.part" "$url" \
       && [[ -s "${MODELS_DIR}/${dest}.part" ]]; then
        mv -f "${MODELS_DIR}/${dest}.part" "${MODELS_DIR}/${dest}"
        log "[live-chat-fetch] staged ${repo}:${file} -> ${dest}"
        sha=""
        command -v sha256sum >/dev/null 2>&1 && sha="$(sha256sum "${MODELS_DIR}/${dest}" | awk '{print $1}')"
        printf '%s\t%s\t%s\t%s\t%s\n' "$dest" "gguf-live-chat" "$repo" "$file" "${sha:-unknown}" >> "${SBOM_DIR}/models.tsv"
        return 0
    fi
    rm -f "${MODELS_DIR}/${dest}.part" 2>/dev/null || true
    if [[ "$required" == "true" ]]; then
        echo "[live-chat-fetch] FATAL: default model '${dest}' failed to download" >&2
        exit 1
    fi
    log "[live-chat-fetch] optional step-up model '${dest}' failed to download"
}

_fetch_one "$MODEL_KEY" "true"
if [[ "$INCLUDE_FALLBACK" == "true" ]]; then
    _fetch_one "$FALLBACK_KEY" "false"
fi

printf '%s.gguf\n' "$MODEL_KEY" > "${MODELS_DIR}/.selected"

_toml_host="${ROOTFS}/etc/mios/mios.toml"
if [[ -f "$_toml_host" ]]; then
    python3 - "$_toml_host" "$PORT" <<'PY'
import re, sys
path, port = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
m = re.search(r'^\[ai\]\s*$', text, re.MULTILINE)
if not m:
    sys.exit(0)  # no [ai] table to patch -- leave file untouched
start = m.end()
nxt = re.search(r'^\[', text[start:], re.MULTILINE)
end = start + nxt.start() if nxt else len(text)
block = text[start:end]
block = re.sub(r'^endpoint\s*=.*$', f'endpoint            = "http://127.0.0.1:{port}/v1"', block, flags=re.MULTILINE)
block = re.sub(r'^model\s*=.*$', 'model               = "mios-live-chat"', block, flags=re.MULTILINE)
block = re.sub(r'^api_key\s*=.*$', 'api_key             = ""', block, flags=re.MULTILINE)
text = text[:start] + block + text[end:]
open(path, "w", encoding="utf-8").write(text)
PY
    log "[live-chat-fetch] patched ${_toml_host} [ai] -> http://127.0.0.1:${PORT}/v1"
else
    echo "[live-chat-fetch] WARN: ${_toml_host} not found in rootfs" >&2
fi

log "[live-chat-fetch] done"$MODELS_DIR" 2>/dev/null | awk '{print $1}') staged in ${MODELS_DIR}"
exit 0
