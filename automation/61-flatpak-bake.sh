#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs operator-selected Flatpaks into the system image during the build process to ensure the final deployment (ISO, VHD...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_61_flatpak_bake_sh.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"

FLATPAK_LIST="${MIOS_FLATPAKS:-}"
if [[ -z "$FLATPAK_LIST" ]] && [[ -r /tmp/build/usr/share/mios/flatpak-list ]]; then
    FLATPAK_LIST="$(tr '\n' ',' < /tmp/build/usr/share/mios/flatpak-list | sed 's/,*$//')"
fi
if [[ -z "$FLATPAK_LIST" ]] && [[ -r /tmp/build/mios.toml ]]; then
    FLATPAK_LIST="$(awk '/^\[desktop\]/,/^\[/{ if ($0 ~ /^\[desktop\]/) next; if ($0 ~ /^\[/) exit; print }' \
                   /tmp/build/mios.toml \
        | grep -oE '"[^"]+"' \
        | tr -d '"' \
        | grep -E '^[A-Za-z][A-Za-z0-9_-]*(\.[A-Za-z][A-Za-z0-9_-]*){2,}$' \
        | tr '\n' ',' \
        | sed 's/,*$//')"
fi

if [[ -z "${FLATPAK_LIST// /}" ]]; then
    mios_skip "no Flatpaks selected (mios.toml [desktop].flatpaks empty)"
    exit 0
fi

if ! command -v flatpak >/dev/null 2>&1; then
    mios_warn "Flatpak binary missing"
    exit 0
fi

flatpak remote-add --system --if-not-exists flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true

mios_log "Selected refs: ${FLATPAK_LIST}"
mios_log "System-wide install"

INSTALLED=0
FAILED=0
IFS=',' read -ra REFS <<< "$FLATPAK_LIST"
for raw in "${REFS[@]}"; do
    ref="$(echo "$raw" | xargs)"
    [[ -z "$ref" ]] && continue

    case "$ref" in
        \#*) continue ;;
    esac

    case "$ref" in
        *:*)
            remote="${ref%%:*}"
            app="${ref#*:}"
            ;;
        *)
            remote="flathub"
            app="$ref"
            ;;
    esac

    if ! flatpak remote-list --system --columns=name 2>/dev/null | grep -qw "$remote"; then
        case "$remote" in
            flathub)
                flatpak remote-add --system --if-not-exists flathub \
                    https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true ;;
            flathub-beta)
                flatpak remote-add --system --if-not-exists flathub-beta \
                    https://flathub.org/beta-repo/flathub-beta.flatpakrepo 2>/dev/null || true ;;
            gnome-nightly)
                flatpak remote-add --system --if-not-exists gnome-nightly \
                    https://nightly.gnome.org/gnome-nightly.flatpakrepo 2>/dev/null || true ;;
            fedora)
                flatpak remote-add --system --if-not-exists fedora \
                    oci+https://registry.fedoraproject.org 2>/dev/null || true ;;
            *)
                mios_warn "Unknown remote '$remote' for $ref" ;;
        esac
    fi

    local_flatpak=""
    if [ -f "/usr/share/mios/vendored/${app}.flatpak" ]; then
        local_flatpak="/usr/share/mios/vendored/${app}.flatpak"
    fi

    mios_log "Installing ${app}"
    if [ -n "$local_flatpak" ]; then
        mios_log "Offline vendored flatpak file: ${local_flatpak}"
        install_cmd="flatpak install --system --noninteractive --assumeyes --or-update ${local_flatpak}"
    else
        install_cmd="flatpak install --system --noninteractive --assumeyes --or-update ${remote} ${app}"
    fi

    set +e
    install_out=$($install_cmd 2>&1)
    install_status=$?
    set -e

    if [[ -n "$install_out" ]]; then
        echo "$install_out" | grep -E '^(Installing|Updating|Already installed|Skipping|Error|Warning)' || echo "$install_out"
    fi

    if [[ $install_status -eq 0 ]]; then
        INSTALLED=$((INSTALLED + 1))
    else
        FAILED=$((FAILED + 1))
        mios_warn "${remote}:${app} install returned non-zero"
    fi
done

mios_ok "${INSTALLED} refs attempted, ${FAILED} reported non-zero"

install -d -m 0755 /usr/lib/mios/state
{
    printf 'MIOS_FLATPAK_BAKE_DATE=%s\n' "$(date -u +%FT%TZ)"
    printf 'MIOS_FLATPAK_BAKE_INSTALLED=%d\n' "$INSTALLED"
    printf 'MIOS_FLATPAK_BAKE_FAILED=%d\n'    "$FAILED"
    printf 'MIOS_FLATPAK_BAKE_LIST=%q\n'      "$FLATPAK_LIST"
} > /usr/lib/mios/state/flatpak-bake.env
chmod 0644 /usr/lib/mios/state/flatpak-bake.env

exit 0
