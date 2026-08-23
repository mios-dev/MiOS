#!/usr/bin/env bash
# AI-hint: Shared container-runtime, registry and image helpers for the workflows, so both publishers execute one implementation.
# AI-related: .github/workflows/mios-ci.yml, .forgejo/workflows/build-mios.yml, tools/lib/userenv.sh
#
# Every function here replaced a block that had been pasted into two or more
# workflow steps. The registry-name validation existed four times, the storage
# configuration twice, the label verification twice, and the version parse three
# times; the copies had already diverged. Source this instead.
#
# shellcheck shell=bash

mios_ci_prepare_storage() {
    sudo mkdir -p /etc/containers /mnt/tmp
    printf '%s\n' \
        '[storage]' \
        'driver = "overlay"' \
        'graphroot = "/mnt/containers-storage"' \
        'runroot = "/run/containers/storage"' \
        '[storage.options.overlay]' \
        'mountopt = "nodev"' | sudo tee /etc/containers/storage.conf >/dev/null
    sudo rm -rf /var/lib/containers/storage /run/containers/storage /mnt/containers-storage
    rm -rf "${HOME}/.local/share/containers/storage" 2>/dev/null || true
    sudo podman system reset -f || true
}

# Print the registry host the SSOT publishes to, or fail with the reason.
#
# MIOS_IMAGE_NAME is resolved from mios.toml, so an empty or host-less value is
# a broken SSOT rather than a workflow typo, and saying which of the two it is
# saves the reader a round trip.
mios_ci_registry_host() {
    local root="${1:-.}"
    # shellcheck source=/dev/null
    source "${root}/tools/lib/userenv.sh"
    if [[ -z "${MIOS_IMAGE_NAME:-}" ]]; then
        echo "MIOS_IMAGE_NAME resolved empty from the SSOT" >&2
        return 1
    fi
    if [[ "$MIOS_IMAGE_NAME" != */* ]]; then
        echo "MIOS_IMAGE_NAME must carry a registry host, got '${MIOS_IMAGE_NAME}'" >&2
        return 1
    fi
    printf '%s\n' "${MIOS_IMAGE_NAME%%/*}"
}

# Print the image tag: VERSION, a UTC timestamp and the short commit.
#
# VERSION must reduce to one token. Comment lines and whitespace are stripped
# because a multi-line value writes a bare line to the step output file, which
# the runner rejects as an invalid format rather than as a bad version.
mios_ci_version() {
    local root="${1:-.}" ver
    ver="$(grep -vE '^[[:space:]]*#' "${root}/VERSION" 2>/dev/null | tr -d '[:space:]')"
    printf '%s\n' "${ver:-0.0.0}"
}

mios_ci_image_tag() {
    local root="${1:-.}" ver sha ts
    ver="$(mios_ci_version "$root")"
    sha="$(git -C "$root" rev-parse --short=12 HEAD)"
    ts="$(date -u +%Y%m%d-%H%M%S)"
    printf '%s\n' "${ver#v}-${ts}-${sha}"
}

mios_ci_verify_bootc_labels() {
    local image="${1:-localhost/mios:latest}" label value
    for label in containers.bootc ostree.bootable; do
        value="$(sudo podman image inspect "$image" \
                 --format "{{ index .Config.Labels \"${label}\" }}" 2>/dev/null)"
        if [[ "$value" != "1" ]]; then
            echo "${image} carries ${label}='${value:-<unset>}', expected 1" >&2
            return 1
        fi
    done
    echo "${image}: containers.bootc=1 ostree.bootable=1"
}
