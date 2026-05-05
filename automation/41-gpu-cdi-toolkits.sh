#!/bin/bash
# 41-gpu-cdi-toolkits: install vendor CDI generators (AMD + Intel)
#
# NVIDIA's nvidia-ctk ships via the nvidia-container-toolkit RPM
# (handled in 35-* GPU passes / repo enablement). AMD and Intel each
# distribute their CDI tooling outside Fedora's main repos as of
# May 2026, so we fetch them here:
#
#   AMD: amd-ctk           -- AMD Container Toolkit v1.3+ RHEL9 RPM
#                              (Fedora 44 is glibc/systemd-compatible)
#                              upstream: github.com/ROCm/container-toolkit
#                              docs:     instinct.docs.amd.com
#                                        /projects/container-toolkit/
#                                        /en/latest/container-runtime/cdi-guide.html
#
#   Intel: intel-cdi-specs-generator
#                          -- intel/intel-resource-drivers-for-kubernetes
#                              v0.1+ static binary; non-Kubernetes path
#                              for podman/docker hosts. Tooling is v0.x
#                              and trails NVIDIA/AMD in polish; install
#                              best-effort under /usr/libexec/mios so
#                              mios-cdi-detect can use it when present.
#
# Both lookups follow the project policy: hit api.github.com for the
# latest tag, fall back to a pinned _FALLBACK_TAG when rate-limited
# or offline. Skip the install (warn, don't fail) when neither path
# yields a binary -- mios-cdi-detect's branches no-op cleanly if the
# tool is missing.
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

# Pinned fallbacks (bump as upstream releases). Keep these matched
# to the most recent verified-on-MiOS-build version so a network blip
# doesn't ship a mystery binary.
AMD_CTK_FALLBACK_TAG="v1.3.0"
INTEL_SG_FALLBACK_TAG="v0.7.0"

# ── AMD Container Toolkit (amd-ctk) ──────────────────────────────────
echo "[41-gpu-cdi] AMD: resolving latest amd-container-toolkit release..."
AMD_TAG=$( (scurl -s https://api.github.com/repos/ROCm/container-toolkit/releases/latest \
              | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
if [[ -z "$AMD_TAG" ]]; then
    warn "AMD container toolkit: api.github.com lookup empty -- using fallback ${AMD_CTK_FALLBACK_TAG}"
    AMD_TAG="$AMD_CTK_FALLBACK_TAG"
fi
record_version amd-container-toolkit "$AMD_TAG" "https://github.com/ROCm/container-toolkit/releases/tag/${AMD_TAG}"

# AMD ships .rpm (RHEL/CentOS 9) + .deb (Ubuntu) only -- no Fedora
# package as of May 2026. RHEL9 RPM works on Fedora 44 (same glibc /
# systemd ABI). Asset name pattern observed on releases:
#   amd-container-toolkit-<ver>-1.el9.x86_64.rpm
AMD_VER="${AMD_TAG#v}"
AMD_RPM="amd-container-toolkit-${AMD_VER}-1.el9.x86_64.rpm"
AMD_URL="https://github.com/ROCm/container-toolkit/releases/download/${AMD_TAG}/${AMD_RPM}"

mkdir -p /tmp/amd-cdi-dl
if scurl -sfL "$AMD_URL" -o "/tmp/amd-cdi-dl/${AMD_RPM}" 2>/dev/null; then
    if dnf5 install -y "/tmp/amd-cdi-dl/${AMD_RPM}" >/dev/null 2>&1 \
       || dnf  install -y "/tmp/amd-cdi-dl/${AMD_RPM}" >/dev/null 2>&1 \
       || rpm  -ivh --replacepkgs "/tmp/amd-cdi-dl/${AMD_RPM}" >/dev/null 2>&1; then
        echo "[41-gpu-cdi]   [ok] AMD container toolkit ${AMD_TAG} installed"
    else
        warn "AMD RPM downloaded but install failed -- skipping (non-fatal)"
    fi
else
    warn "AMD container toolkit: ${AMD_URL} not reachable -- skipping (non-fatal)"
fi
rm -rf /tmp/amd-cdi-dl

# ── Intel CDI specs generator ────────────────────────────────────────
echo "[41-gpu-cdi] Intel: resolving latest intel-resource-drivers-for-kubernetes release..."
INTEL_TAG=$( (scurl -s https://api.github.com/repos/intel/intel-resource-drivers-for-kubernetes/releases/latest \
                | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
if [[ -z "$INTEL_TAG" ]]; then
    warn "Intel CDI generator: api.github.com lookup empty -- using fallback ${INTEL_SG_FALLBACK_TAG}"
    INTEL_TAG="$INTEL_SG_FALLBACK_TAG"
fi
record_version intel-cdi-specs-generator "$INTEL_TAG" \
    "https://github.com/intel/intel-resource-drivers-for-kubernetes/releases/tag/${INTEL_TAG}"

# Asset shape varies across the project's releases. Try the canonical
# shape first; fall back to a glob-match against the release index.
INTEL_BIN="intel-cdi-specs-generator-linux-amd64"
INTEL_URL="https://github.com/intel/intel-resource-drivers-for-kubernetes/releases/download/${INTEL_TAG}/${INTEL_BIN}"

mkdir -p /tmp/intel-cdi-dl
if scurl -sfL "$INTEL_URL" -o "/tmp/intel-cdi-dl/${INTEL_BIN}" 2>/dev/null \
   && [[ -s "/tmp/intel-cdi-dl/${INTEL_BIN}" ]]; then
    install -d -m 0755 /usr/libexec/mios
    install -m 0755 "/tmp/intel-cdi-dl/${INTEL_BIN}" /usr/libexec/mios/intel-cdi-specs-generator
    echo "[41-gpu-cdi]   [ok] Intel CDI specs-generator ${INTEL_TAG} installed at /usr/libexec/mios/intel-cdi-specs-generator"
else
    # Fallback: query the release JSON for any *specs-generator* asset.
    # Best-effort -- tooling is v0.x and asset naming has shifted.
    asset_url=$( (scurl -s "https://api.github.com/repos/intel/intel-resource-drivers-for-kubernetes/releases/tags/${INTEL_TAG}" \
                    | grep -oP '"browser_download_url": "\K[^"]*' \
                    | grep -E 'specs-generator.*linux' \
                    | grep -E 'amd64|x86_64' \
                    | head -1) 2>/dev/null || true)
    if [[ -n "$asset_url" ]] && scurl -sfL "$asset_url" -o /tmp/intel-cdi-dl/sg.bin 2>/dev/null \
       && [[ -s /tmp/intel-cdi-dl/sg.bin ]]; then
        install -d -m 0755 /usr/libexec/mios
        install -m 0755 /tmp/intel-cdi-dl/sg.bin /usr/libexec/mios/intel-cdi-specs-generator
        echo "[41-gpu-cdi]   [ok] Intel CDI specs-generator ${INTEL_TAG} installed (fallback asset path)"
    else
        warn "Intel CDI specs-generator: no asset matched on ${INTEL_TAG} -- skipping (non-fatal)"
    fi
fi
rm -rf /tmp/intel-cdi-dl

echo "[41-gpu-cdi] done."
