#!/bin/bash
# 40-flatpak-bake: install operator-selected Flatpaks AT BUILD TIME so
# every deploy shape (raw, vhdx, qcow2, ISO, WSL2 distro, Podman-WSL OCI
# host) carries them baked into the image. Replaces the first-boot
# install model -- the deployed system no longer needs network on first
# boot to render the user's selected Flatpak surface.
#
# The Flatpak set comes from the operator's configurator-saved mios.toml
# `[desktop].flatpaks` array, which build-mios.{sh,ps1} threads through
# the pipeline as:
#
#   mios.toml [desktop].flatpaks
#     -> --build-arg MIOS_FLATPAKS=<csv>
#     -> /tmp/build/usr/share/mios/flatpak-list (newline-separated)
#     -> THIS script reads either source and runs `flatpak install --system`
#
# Ordering: runs after 10-gnome.sh which adds the flathub remote, and
# before 99-cleanup.sh which strips dnf/build caches. NON_FATAL_SCRIPTS
# in build.sh marks this non-fatal so a transient network blip during
# bake doesn't tank the whole build -- the first-boot mios-flatpak-install
# service still picks up any uninstalled refs as a fallback.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# Resolve the selection list. Explicit env wins; build-arg-staged file
# is the fallback. Both encode the same comma- (env) or newline-
# (file) separated set of Flatpak refs.
FLATPAK_LIST="${MIOS_FLATPAKS:-}"
if [[ -z "$FLATPAK_LIST" ]] && [[ -r /tmp/build/usr/share/mios/flatpak-list ]]; then
    FLATPAK_LIST="$(tr '\n' ',' < /tmp/build/usr/share/mios/flatpak-list | sed 's/,*$//')"
fi
# Fall back to the canonical mios.toml in the build context if neither
# env nor flatpak-list provided refs (e.g., when build was kicked off
# without the wrapper that propagates the build-arg).
if [[ -z "$FLATPAK_LIST" ]] && [[ -r /tmp/build/mios.toml ]]; then
    # Scrape [desktop].flatpaks array out of mios.toml. The configurator
    # (usr/share/mios/configurator/index.html) emits multi-line arrays
    # for >4 entries so awk's section bracket includes the
    # multi-line continuation; grep -oE pulls every quoted string and
    # the trailing flatpak-id regex filters out any non-ref strings
    # (e.g. session/color_scheme values).
    #
    # The leading-char class is [A-Za-z] (case-insensitive) so extras
    # entered through the configurator's "extra flatpaks" textarea --
    # which validates against /^[A-Za-z][A-Za-z0-9_-]*(\.[A-Za-z][A-Za-z0-9_-]*){2,}$/
    # -- are accepted by this scrape too. Previous [a-z]-only anchor
    # silently dropped capital-leading IDs, breaking parity between
    # configurator validation and bake-time scraping.
    FLATPAK_LIST="$(awk '/^\[desktop\]/,/^\[/{ if ($0 ~ /^\[desktop\]/) next; if ($0 ~ /^\[/) exit; print }' \
                   /tmp/build/mios.toml \
        | grep -oE '"[^"]+"' \
        | tr -d '"' \
        | grep -E '^[A-Za-z][A-Za-z0-9_-]*(\.[A-Za-z][A-Za-z0-9_-]*){2,}$' \
        | tr '\n' ',' \
        | sed 's/,*$//')"
fi

if [[ -z "${FLATPAK_LIST// /}" ]]; then
    log "[40-flatpak-bake] no Flatpaks selected (mios.toml [desktop].flatpaks empty) -- skipping bake"
    exit 0
fi

if ! command -v flatpak >/dev/null 2>&1; then
    warn "[40-flatpak-bake] flatpak binary missing -- skipping bake (mios-flatpak-install will retry on first boot)"
    exit 0
fi

# Ensure flathub remote is present at the system installation. 10-gnome.sh
# adds it earlier; idempotent here for cases where 10-gnome was skipped
# (e.g., headless variant, or a re-run from this phase forward).
flatpak remote-add --system --if-not-exists flathub \
    https://dl.flathub.org/repo/flathub.flatpakrepo 2>/dev/null || true

log "[40-flatpak-bake] selected refs: ${FLATPAK_LIST}"
log "[40-flatpak-bake] beginning system-wide install (this may take several minutes)"

INSTALLED=0
FAILED=0
IFS=',' read -ra REFS <<< "$FLATPAK_LIST"
for raw in "${REFS[@]}"; do
    ref="$(echo "$raw" | xargs)"
    [[ -z "$ref" ]] && continue

    # Skip empty / comment-shaped entries (a stray `# ...` slipped through
    # the configurator save would otherwise trip the install).
    case "$ref" in
        \#*) continue ;;
    esac

    log "[40-flatpak-bake]   installing ${ref}"
    if flatpak install --system --noninteractive --assumeyes --or-update \
            flathub "${ref}" 2>&1 \
            | grep -E '^(Installing|Updating|Already installed|Skipping|Error|Warning)' \
            || true; then
        INSTALLED=$((INSTALLED + 1))
    else
        FAILED=$((FAILED + 1))
        warn "[40-flatpak-bake]   ${ref} install returned non-zero -- will retry at first boot"
    fi
done

log "[40-flatpak-bake] bake complete: ${INSTALLED} installed, ${FAILED} deferred to first boot"

# Mark the bake state so the first-boot service can short-circuit when
# everything's already present, and the postcheck can verify that the
# image actually carries the installed refs.
install -d -m 0755 /usr/lib/mios/state
{
    printf 'MIOS_FLATPAK_BAKE_DATE=%s\n' "$(date -u +%FT%TZ)"
    printf 'MIOS_FLATPAK_BAKE_INSTALLED=%d\n' "$INSTALLED"
    printf 'MIOS_FLATPAK_BAKE_FAILED=%d\n'    "$FAILED"
    printf 'MIOS_FLATPAK_BAKE_LIST=%q\n'      "$FLATPAK_LIST"
} > /usr/lib/mios/state/flatpak-bake.env
chmod 0644 /usr/lib/mios/state/flatpak-bake.env

exit 0
