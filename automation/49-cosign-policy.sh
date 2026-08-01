#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs the cosign binary (v2.x), configures Sigstore trust roots, and sets up policy.json to ensure OCI 1.1 bundle compatibility during image builds.
# AI-related: mios-cosign
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

source "$(dirname "$0")/lib/common.sh"

mios_log "Ensuring cosign + trust roots + policy.json"

if ! command -v cosign >/dev/null 2>&1; then
    COSIGN_FALLBACK_VERSION="v2.6.4"
    COSIGN_VERSION=$( (scurl -s https://api.github.com/repos/sigstore/cosign/releases?per_page=30 \
        | grep -Po '"tag_name": "\Kv2\.[^"]+' \
        | head -n1) 2>/dev/null || true)
    if [[ -z "$COSIGN_VERSION" ]]; then
        [[ -n "$COSIGN_FALLBACK_VERSION" ]] || die "cosign: api.github.com lookup empty AND no fallback pin"
        mios_warn "cosign: api.github.com lookup empty -- falling back to pinned ${COSIGN_FALLBACK_VERSION}"
        COSIGN_VERSION="$COSIGN_FALLBACK_VERSION"
    fi
    COSIGN_BASE_URL="https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}"
    record_version cosign "$COSIGN_VERSION" "https://github.com/sigstore/cosign/releases/tag/${COSIGN_VERSION}"
    mios_log "Resolved cosign latest v2.x: ${COSIGN_VERSION}"
    mios_log "Downloading cosign ${COSIGN_VERSION} static binary"
    mkdir -p /tmp/cosign-dl
    scurl -sfL "${COSIGN_BASE_URL}/cosign-linux-amd64" -o /tmp/cosign-dl/cosign-linux-amd64
    scurl -sfL "${COSIGN_BASE_URL}/cosign_checksums.txt" -o /tmp/cosign-dl/cosign_checksums.txt
    (cd /tmp/cosign-dl && grep "cosign-linux-amd64$" cosign_checksums.txt | sha256sum -c -) \
        || die "cosign ${COSIGN_VERSION} SHA256 mismatch -- aborting"
    install -m 0755 /tmp/cosign-dl/cosign-linux-amd64 /usr/bin/cosign

    sbom_dir="/usr/share/mios/artifacts/sbom"
    mkdir -p "$sbom_dir"
    sha=""
    if command -v sha256sum >/dev/null 2>&1; then
        sha="$(sha256sum /usr/bin/cosign | awk '{print $1}')"
    fi
    printf '%s\t%s\t%s\n' "cosign" "${COSIGN_VERSION}" "${sha:-unknown}" >> "${sbom_dir}/binaries.tsv"

    rm -rf /tmp/cosign-dl
fi

SYSFILES="/ctx/system_files"
install -d -m 0755 /usr/share/pki/containers
install -d -m 0755 /usr/lib/containers/registries.d

if command -v miosd >/dev/null 2>&1; then
    miosd cosign-policy
    mios_ok "policy.json generated via miosd"
elif [[ -f "${SYSFILES}/usr/lib/containers/policy.json" ]]; then
    install -m 0644 "${SYSFILES}/usr/lib/containers/policy.json" /usr/lib/containers/policy.json
    mios_ok "installed /usr/lib/containers/policy.json"
else
    [[ -f /usr/lib/containers/policy.json ]] || mios_warn "missing policy.json"
fi

for f in fulcio_v1.crt.pem rekor.pub ublue-os.pub ublue-cosign.pub mios-cosign.pub; do
    src="${SYSFILES}/usr/share/pki/containers/${f}"
    dst="/usr/share/pki/containers/${f}"
    if [[ -f "${src}" ]]; then
        install -m 0644 "${src}" "${dst}"
        mios_ok "installed ${dst}"
    fi
done

if command -v jq >/dev/null 2>&1 && [[ -f /usr/lib/containers/policy.json ]]; then
    jq -e . /usr/lib/containers/policy.json >/dev/null || die "policy.json failed jq parse"
    mios_ok "policy.json parses cleanly"
fi

mios_ok "validation complete"
