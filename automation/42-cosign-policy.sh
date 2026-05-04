#!/usr/bin/env bash
# ============================================================================
# automation/42-cosign-policy.sh - 'MiOS' v0.2.0
# ----------------------------------------------------------------------------
# Consolidates cosign binary installation, Sigstore trust roots, and policy.json.
# Supercedes 37-cosign-policy.sh.
#
# Note: cosign must stay on v2.x -- v3+ breaks rpm-ostree OCI 1.1 bundle format.
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "42-cosign-policy: ensuring cosign + trust roots + policy.json"

# 1. Install cosign binary
# Project policy: every dependency tracks :latest from its source. Cosign is
# constrained to the v2.x series here because v3+ breaks rpm-ostree OCI 1.1
# bundle format (see header). Lift the v2 filter when v3 compat is confirmed.
if ! command -v cosign >/dev/null 2>&1; then
    # Pinned-fallback pattern (matches 37-aichat.sh): bump COSIGN_FALLBACK_VERSION
    # whenever a newer v2.x ships, so a rate-limited api.github.com (HTTP 403 on
    # the 61st unauthenticated call per hour from the runner IP) doesn't kill the
    # whole image build. scurl auto-attaches GH_TOKEN/GITHUB_TOKEN/GHCR_TOKEN
    # when those are in the build env -- the fallback is the safety net.
    COSIGN_FALLBACK_VERSION="v2.6.4"
    COSIGN_VERSION=$( (scurl -s https://api.github.com/repos/sigstore/cosign/releases?per_page=30 \
        | grep -Po '"tag_name": "\Kv2\.[^"]+' \
        | head -n1) 2>/dev/null || true)
    if [[ -z "$COSIGN_VERSION" ]]; then
        [[ -n "$COSIGN_FALLBACK_VERSION" ]] || die "cosign: api.github.com lookup empty AND no fallback pin"
        warn "cosign: api.github.com lookup empty -- falling back to pinned ${COSIGN_FALLBACK_VERSION}"
        COSIGN_VERSION="$COSIGN_FALLBACK_VERSION"
    fi
    COSIGN_BASE_URL="https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}"
    record_version cosign "$COSIGN_VERSION" "https://github.com/sigstore/cosign/releases/tag/${COSIGN_VERSION}"
    log "  resolved cosign latest v2.x: ${COSIGN_VERSION}"
    log "  downloading cosign ${COSIGN_VERSION} static binary..."
    mkdir -p /tmp/cosign-dl
    scurl -sfL "${COSIGN_BASE_URL}/cosign-linux-amd64" -o /tmp/cosign-dl/cosign-linux-amd64
    scurl -sfL "${COSIGN_BASE_URL}/cosign_checksums.txt" -o /tmp/cosign-dl/cosign_checksums.txt
    (cd /tmp/cosign-dl && grep "cosign-linux-amd64$" cosign_checksums.txt | sha256sum -c -) \
        || die "cosign ${COSIGN_VERSION} SHA256 mismatch -- aborting"
    # Install into /usr/bin (immutable image surface). /usr/local is a
    # symlink to /var/usrlocal on bootc/FCOS layouts and /var/usrlocal/bin/
    # does not exist at OCI build time.
    install -m 0755 /tmp/cosign-dl/cosign-linux-amd64 /usr/bin/cosign
    rm -rf /tmp/cosign-dl
fi

SYSFILES="/ctx/system_files"
# Paths updated to /usr/share/pki and /usr/lib/containers as per USR-OVER-ETC
install -d -m 0755 /usr/share/pki/containers
install -d -m 0755 /usr/lib/containers/registries.d

# 2. Install policy.json
# v0.2.0: Moved from etc/ to usr/lib/ in system_files
if [[ -f "${SYSFILES}/usr/lib/containers/policy.json" ]]; then
    install -m 0644 "${SYSFILES}/usr/lib/containers/policy.json" /usr/lib/containers/policy.json
    log "  installed /usr/lib/containers/policy.json"
else
    # Fallback to in-image path if ctx is missing (unlikely in build)
    [[ -f /usr/lib/containers/policy.json ]] || warn "missing policy.json"
fi

# 3. Install Sigstore TUF roots and public keys
# These ship via the usr/share/pki/containers/ overlay
for f in fulcio_v1.crt.pem rekor.pub ublue-os.pub ublue-cosign.pub mios-cosign.pub; do
    src="${SYSFILES}/usr/share/pki/containers/${f}"
    dst="/usr/share/pki/containers/${f}"
    if [[ -f "${src}" ]]; then
        install -m 0644 "${src}" "${dst}"
        log "  installed ${dst}"
    fi
done

# 4. JSON Sanity Check
if command -v jq >/dev/null 2>&1 && [[ -f /usr/lib/containers/policy.json ]]; then
    jq -e . /usr/lib/containers/policy.json >/dev/null || die "policy.json failed jq parse"
    log "  policy.json parses cleanly"
fi

log "42-cosign-policy: validation complete"
