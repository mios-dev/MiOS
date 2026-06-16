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
# 'mios-sync-env' to refresh install.env. Idempotent; preserves
# secret fields the user can't put in mios.toml (e.g.
# MIOS_USER_PASSWORD_HASH, MIOS_FORGE_ADMIN_PASSWORD) by reading the
# previous install.env and re-emitting them verbatim.
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

# Preserve secret fields from the previous install.env if it exists
# (mios.toml does NOT contain secrets; those flow in via the bootstrap
# Phase-7 prompt and never round-trip through the dotfile).
PREV_PWHASH=""
PREV_FORGE_PW=""
PREV_GHCR_TOKEN=""
if [[ -r "$OUT" ]]; then
    # shellcheck disable=SC1091
    set +u; . <(grep -E '^MIOS_(USER_PASSWORD_HASH|FORGE_ADMIN_PASSWORD|GITHUB_TOKEN)=' "$OUT" || true); set -u
    PREV_PWHASH="${MIOS_USER_PASSWORD_HASH:-}"
    PREV_FORGE_PW="${MIOS_FORGE_ADMIN_PASSWORD:-}"
    PREV_GHCR_TOKEN="${MIOS_GITHUB_TOKEN:-}"
fi

# Render the new install.env. Order matches what wsl-firstboot,
# forge-firstboot, and 37-ollama-prep.sh expect.
generate_env() {
    local _ai_backend=""
    cat <<EOF
# /etc/mios/install.env -- DERIVED from mios.toml by mios-sync-env.
# Edit mios.toml (or use /usr/share/mios/configurator/mios.html), then
# run 'sudo mios-sync-env' to refresh this file. Manual edits here are
# overwritten on the next sync. Secrets (MIOS_USER_PASSWORD_HASH,
# MIOS_FORGE_ADMIN_PASSWORD, MIOS_GITHUB_TOKEN) are preserved verbatim
# from the previous install.env -- they are never round-tripped
# through mios.toml.
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
    echo "MIOS_USER=\"${MIOS_USER:-mios}\""
    echo "MIOS_HOSTNAME=\"${MIOS_HOSTNAME:-mios}\""
    [[ -n "${MIOS_USER_FULLNAME:-}" ]] && echo "MIOS_USER_FULLNAME=\"${MIOS_USER_FULLNAME}\""
    [[ -n "${MIOS_USER_GROUPS:-}" ]]   && echo "MIOS_USER_GROUPS=\"${MIOS_USER_GROUPS}\""
    # Global default password. Every MiOS service (Hermes Workspace,
    # Forge admin, etc.) reads this as its default login credential
    # unless the operator overrides per-service. Vendor default is
    # "mios"; override in /etc/mios/mios.toml [identity].default_password.
    echo "MIOS_DEFAULT_PASSWORD=\"${MIOS_DEFAULT_PASSWORD:-mios}\""

    # AI surface (Architectural Law 5: UNIFIED-AI-REDIRECTS). The resolver
    # (userenv.sh) populates these from the layered mios.toml; prefer the
    # resolved value, emit a fallback ONLY for the few keys shell/systemd
    # consumers always expect. Fallback defaults track the live SSOT:
    #   endpoint -> [ai].endpoint  = http://localhost:8640/v1 (AGENT-PIPE ORCHESTRATOR
    #               -- the UNIFIED entrypoint, model "MiOS-Agent"; operator 2026-06-16.
    #               Hermes :8642 is now a LEAF the pipe calls, NOT the client surface.)
    #   model    -> [ai].model     = granite4.1:8b (2026-06-13 fleet; ollama-era
    #               qwen3.5:2b was a dropped model -> a stale/unservable default)
    echo "MIOS_AI_ENDPOINT=\"${MIOS_AI_ENDPOINT:-http://localhost:8640/v1}\""
    echo "MIOS_AI_MODEL=\"${MIOS_AI_MODEL:-granite4.1:8b}\""
    echo "MIOS_AI_EMBED_MODEL=\"${MIOS_AI_EMBED_MODEL:-nomic-embed-text}\""
    # Inference backend the agents forward to (mios-llm-light front; ollama
    # :11434 retired G5). Derived from the resolver's MIOS_HERMES_BACKEND_URL
    # ([ai].hermes_backend_url, e.g. http://localhost:11450/v1) so MIOS_AI_BACKEND
    # follows the SSOT instead of a hardcoded port. Strip a trailing /v1 so
    # consumers that append their own path get a clean host:port base.
    _ai_backend="${MIOS_AI_BACKEND:-${MIOS_HERMES_BACKEND_URL:-}}"
    _ai_backend="${_ai_backend%/v1}"
    [[ -n "$_ai_backend" ]] && echo "MIOS_AI_BACKEND=\"${_ai_backend}\""
    # Build-time ollama bake list (resolver-populated; emit only if set).
    [[ -n "${MIOS_OLLAMA_BAKE_MODELS:-}" ]] && echo "MIOS_OLLAMA_BAKE_MODELS=\"${MIOS_OLLAMA_BAKE_MODELS}\""

    # llama.cpp light lane ([llamacpp] -> MIOS_LLAMACPP_*). All resolver-
    # populated; emit only the values the resolver actually produced (no
    # hardcoded literals). BAKE_MODELS feeds 38-llamacpp-prep.sh + the
    # mios-ai-firstboot online GGUF retry.
    [[ -n "${MIOS_LLAMACPP_ENABLE:-}" ]]      && echo "MIOS_LLAMACPP_ENABLE=\"${MIOS_LLAMACPP_ENABLE}\""
    [[ -n "${MIOS_LLAMACPP_SLOT_DIR:-}" ]]    && echo "MIOS_LLAMACPP_SLOT_DIR=\"${MIOS_LLAMACPP_SLOT_DIR}\""
    [[ -n "${MIOS_LLAMACPP_MODELS_DIR:-}" ]]  && echo "MIOS_LLAMACPP_MODELS_DIR=\"${MIOS_LLAMACPP_MODELS_DIR}\""
    [[ -n "${MIOS_LLAMACPP_CONFIG:-}" ]]      && echo "MIOS_LLAMACPP_CONFIG=\"${MIOS_LLAMACPP_CONFIG}\""
    [[ -n "${MIOS_LLAMACPP_BAKE_MODELS:-}" ]] && echo "MIOS_LLAMACPP_BAKE_MODELS=\"${MIOS_LLAMACPP_BAKE_MODELS}\""

    # Heavy GPU lanes (gated/off-by-default; resolver-populated served names +
    # ports). Endpoints assembled from the lane ports so the value tracks the
    # SSOT rather than a hardcoded literal; emit only when the port resolved.
    [[ -n "${MIOS_SGLANG_SERVED_NAME:-}" ]] && echo "MIOS_SGLANG_SERVED_NAME=\"${MIOS_SGLANG_SERVED_NAME}\""
    [[ -n "${MIOS_VLLM_SERVED_NAME:-}" ]]   && echo "MIOS_VLLM_SERVED_NAME=\"${MIOS_VLLM_SERVED_NAME}\""
    [[ -n "${MIOS_PORT_SGLANG:-}" ]] && echo "MIOS_AI_HEAVY_ENDPOINT=\"http://localhost:${MIOS_PORT_SGLANG}/v1\""
    [[ -n "${MIOS_PORT_VLLM:-}" ]]   && echo "MIOS_AI_HEAVY_ALT_ENDPOINT=\"http://localhost:${MIOS_PORT_VLLM}/v1\""

    # Image
    [[ -n "${MIOS_IMAGE_REF:-}" ]]    && echo "MIOS_IMAGE_REF=\"${MIOS_IMAGE_REF}\""
    [[ -n "${MIOS_BRANCH:-}" ]]       && echo "MIOS_BRANCH=\"${MIOS_BRANCH}\""
    [[ -n "${MIOS_BASE_IMAGE:-}" ]]   && echo "MIOS_BASE_IMAGE=\"${MIOS_BASE_IMAGE}\""

    # Forge admin (non-secret half)
    [[ -n "${MIOS_FORGE_ADMIN_USER:-}" ]]  && echo "MIOS_FORGE_ADMIN_USER=\"${MIOS_FORGE_ADMIN_USER}\""
    [[ -n "${MIOS_FORGE_ADMIN_EMAIL:-}" ]] && echo "MIOS_FORGE_ADMIN_EMAIL=\"${MIOS_FORGE_ADMIN_EMAIL}\""

    # Preserved secrets (NEVER originate from mios.toml)
    [[ -n "$PREV_PWHASH" ]]     && echo "MIOS_USER_PASSWORD_HASH=\"$PREV_PWHASH\""
    [[ -n "$PREV_FORGE_PW" ]]   && echo "MIOS_FORGE_ADMIN_PASSWORD=\"$PREV_FORGE_PW\""
    [[ -n "$PREV_GHCR_TOKEN" ]] && echo "MIOS_GITHUB_TOKEN=\"$PREV_GHCR_TOKEN\""
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
mv -f "$TMP" "$OUT"
trap - EXIT

echo "mios-sync-env: regenerated $OUT from layered mios.toml"
