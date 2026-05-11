#!/usr/bin/env bash
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

    # AI surface (Architectural Law 5)
    echo "MIOS_AI_ENDPOINT=\"${MIOS_AI_ENDPOINT:-http://localhost:8642/v1}\""
    echo "MIOS_AI_MODEL=\"${MIOS_AI_MODEL:-qwen3.5:2b}\""
    echo "MIOS_AI_EMBED_MODEL=\"${MIOS_AI_EMBED_MODEL:-nomic-embed-text}\""
    [[ -n "${MIOS_OLLAMA_BAKE_MODELS:-}" ]] && echo "MIOS_OLLAMA_BAKE_MODELS=\"${MIOS_OLLAMA_BAKE_MODELS}\""

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
