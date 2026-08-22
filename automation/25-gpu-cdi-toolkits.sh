#!/bin/bash
# AI-hint: MIOS_APPLY_CLASS=universal Installs AMD and Intel vendor-specific CDI (Container Device Interface) generator tools (amd-ctk and intel-cdi-specs-ge...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_25_gpu_cdi_toolkits_sh.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

AMD_CTK_FALLBACK_TAG="v1.3.0"
INTEL_SG_FALLBACK_TAG="v0.7.0"

mios_log "AMD: resolving latest amd-container-toolkit release"
AMD_TAG=$( (scurl -s https://api.github.com/repos/ROCm/container-toolkit/releases/latest \
              | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
if [[ -z "$AMD_TAG" ]]; then
    warn "AMD container toolkit: api.github.com lookup empty"
    AMD_TAG="$AMD_CTK_FALLBACK_TAG"
fi
record_version amd-container-toolkit "$AMD_TAG" "https://github.com/ROCm/container-toolkit/releases/tag/${AMD_TAG}"

AMD_VER="${AMD_TAG#v}"
AMD_RPM="amd-container-toolkit-${AMD_VER}-1.el9.x86_64.rpm"
AMD_URL="https://github.com/ROCm/container-toolkit/releases/download/${AMD_TAG}/${AMD_RPM}"

mkdir -p /tmp/amd-cdi-dl
if scurl -sfL "$AMD_URL" -o "/tmp/amd-cdi-dl/${AMD_RPM}" 2>/dev/null; then
    if dnf5 install -y "/tmp/amd-cdi-dl/${AMD_RPM}" >/dev/null 2>&1 \
       || dnf  install -y "/tmp/amd-cdi-dl/${AMD_RPM}" >/dev/null 2>&1 \
       || rpm  -ivh --replacepkgs "/tmp/amd-cdi-dl/${AMD_RPM}" >/dev/null 2>&1; then
        mios_ok "AMD container toolkit ${AMD_TAG} installed via RPM"
    else
        warn "AMD RPM downloaded but install failed"
    fi
elif command -v go >/dev/null 2>&1 && GOBIN=/usr/bin go install github.com/ROCm/container-toolkit/cmd/amd-ctk@latest >/dev/null 2>&1; then
    mios_ok "AMD container toolkit installed via go build"
else
    warn "AMD container toolkit: ${AMD_URL} not reachable"
fi
rm -rf /tmp/amd-cdi-dl

mios_log "Intel: resolving latest intel-resource-drivers-for-kubernetes release"
INTEL_TAG=$( (scurl -s https://api.github.com/repos/intel/intel-resource-drivers-for-kubernetes/releases \
                | grep -Po '"tag_name": "\Kspecs-generator-[^"]*' | head -1) 2>/dev/null || true)
if [[ -z "$INTEL_TAG" ]]; then
    INTEL_TAG=$( (scurl -s https://api.github.com/repos/intel/intel-resource-drivers-for-kubernetes/releases/latest \
                    | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
fi
if [[ -z "$INTEL_TAG" ]]; then
    warn "Intel CDI generator: api.github.com lookup empty"
    INTEL_TAG="$INTEL_SG_FALLBACK_TAG"
fi
record_version intel-cdi-specs-generator "$INTEL_TAG" \
    "https://github.com/intel/intel-resource-drivers-for-kubernetes/releases/tag/${INTEL_TAG}"

INTEL_BIN="intel-cdi-specs-generator-linux-amd64"
INTEL_URL="https://github.com/intel/intel-resource-drivers-for-kubernetes/releases/download/${INTEL_TAG}/${INTEL_BIN}"

mkdir -p /tmp/intel-cdi-dl
installed_intel=0
if scurl -sfL "$INTEL_URL" -o "/tmp/intel-cdi-dl/${INTEL_BIN}" 2>/dev/null \
   && [[ -s "/tmp/intel-cdi-dl/${INTEL_BIN}" ]]; then
    install -d -m 0755 /usr/libexec/mios
    install -m 0755 "/tmp/intel-cdi-dl/${INTEL_BIN}" /usr/libexec/mios/intel-cdi-specs-generator
    mios_ok "Intel CDI specs-generator ${INTEL_TAG} installed at /usr/libexec/mios/intel-cdi-specs-generator"
    installed_intel=1
else
    asset_url=$( (scurl -s "https://api.github.com/repos/intel/intel-resource-drivers-for-kubernetes/releases" \
                    | grep -oP '"browser_download_url": "\K[^"]*' \
                    | grep -E 'specs-generator' \
                    | head -1) 2>/dev/null || true)
    if [[ -n "$asset_url" ]] && scurl -sfL "$asset_url" -o /tmp/intel-cdi-dl/sg.asset 2>/dev/null \
       && [[ -s /tmp/intel-cdi-dl/sg.asset ]]; then
        install -d -m 0755 /usr/libexec/mios
        if [[ "$asset_url" == *.zip ]] && command -v unzip >/dev/null 2>&1; then
            unzip -q /tmp/intel-cdi-dl/sg.asset -d /tmp/intel-cdi-dl/extracted
            bin_path=$(find /tmp/intel-cdi-dl/extracted -type f -name "intel-cdi-specs-generator" | head -1)
            if [[ -n "$bin_path" ]]; then
                install -m 0755 "$bin_path" /usr/libexec/mios/intel-cdi-specs-generator
                mios_ok "Intel CDI specs-generator installed from zip asset"
                installed_intel=1
            fi
        else
            install -m 0755 /tmp/intel-cdi-dl/sg.asset /usr/libexec/mios/intel-cdi-specs-generator
            mios_ok "Intel CDI specs-generator installed"
            installed_intel=1
        fi
    fi
fi

if [[ $installed_intel -eq 0 ]]; then
    if command -v go >/dev/null 2>&1 && GOBIN=/usr/libexec/mios go install github.com/intel/intel-resource-drivers-for-kubernetes/cmd/intel-cdi-specs-generator@latest >/dev/null 2>&1; then
        mios_ok "Intel CDI specs-generator installed via go build"
    else
        warn "Intel CDI specs-generator: no asset matched on ${INTEL_TAG}"
    fi
fi
rm -rf /tmp/intel-cdi-dl

mios_ok "Done"
