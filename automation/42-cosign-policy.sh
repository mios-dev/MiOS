#!/usr/bin/env bash
# ============================================================================
# automation/42-cosign-policy.sh - MiOS v0.1.4
# ----------------------------------------------------------------------------
# Consolidates cosign binary installation, Sigstore trust roots, and policy.json.
# Supercedes 37-cosign-policy.sh.
#
# Note: we pin to v0.1.4 because v3 breaks rpm-ostree bundle format (OCI 1.1).
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "42-cosign-policy: ensuring cosign + trust roots + policy.json"

# 1. Install cosign binary (pinned to v2.x for rpm-ostree compatibility)
if ! command -v cosign >/dev/null 2>&1; then
    log "  downloading cosign v0.1.4 static binary..."
    scurl "https://github.com/sigstore/cosign/releases/download/v0.1.4/cosign-linux-amd64" -o /usr/local/bin/cosign
    chmod +x /usr/local/bin/cosign
fi

SYSFILES="/ctx/system_files"
# Paths updated to /usr/share/pki and /usr/lib/containers as per USR-OVER-ETC
install -d -m 0755 /usr/share/pki/containers
install -d -m 0755 /usr/lib/containers/registries.d

# 2. Install policy.json
# v0.1.4: Moved from etc/ to usr/lib/ in system_files
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
