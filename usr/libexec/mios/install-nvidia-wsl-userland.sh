#!/bin/bash
# AI-hint: Install NVIDIA's Vulkan ICD + GLX/EGL userspace libs for WSLg
# AI-related: /usr/libexec/mios/install-nvidia-wsl-userland.sh
set -euo pipefail


if [ "${MIOS_SKIP_NVIDIA_INSTALL:-0}" = "1" ]; then
    echo "  [skip] MIOS_SKIP_NVIDIA_INSTALL=1; not installing NVIDIA userland"
    exit 0
fi

if [ ! -d /mnt/wslg ] && [ ! -c /dev/dxg ]; then
    echo "  [skip] not WSLg; NVIDIA WSL userland not applicable"
    exit 0
fi

fedver=$(. /etc/os-release; echo "$PLATFORM_ID" | sed -E 's/^.*:f([0-9]+)$/\1/')
[ -z "$fedver" ] && fedver=$(. /etc/os-release; echo "${VERSION_ID:-44}")
echo "  Fedora upstream: $fedver"

repo_url=""
for v in "$fedver" 44 43 42 41 40; do
    [ -z "$v" ] && continue
    cand="https://developer.download.nvidia.com/compute/cuda/repos/fedora${v}/x86_64/cuda-fedora${v}.repo"
    code=$(curl -fsI -o /dev/null -w "%{http_code}" "$cand" 2>/dev/null || true)
    if [ "$code" = "200" ]; then
        echo "  NVIDIA CUDA repo: fedora${v}"
        repo_url="$cand"
        break
    fi
done
if [ -z "$repo_url" ]; then
    echo "  [warn] no NVIDIA CUDA repo reachable for Fedora ${fedver} or fallbacks; skipping"
    exit 0
fi

dnf config-manager addrepo --from-repofile="$repo_url" --overwrite >/dev/null 2>&1 || true

dnf install -y --setopt=install_weak_deps=False \
    -x 'kmod-nvidia*' \
    -x 'akmod-nvidia*' \
    -x 'nvidia-driver-cuda' \
    -x 'nvidia-driver-NvFBCOpenGL' \
    nvidia-driver-libs 2>&1 | tail -5

if [ -e /usr/share/vulkan/icd.d/nvidia_icd.x86_64.json ] \
    && [ -e /usr/lib64/libGLX_nvidia.so.0 ]; then
    echo "  [ok] NVIDIA WSL userland installed:"
    echo "         vulkan ICD: /usr/share/vulkan/icd.d/nvidia_icd.x86_64.json"
    echo "         GLX/EGL:    /usr/lib64/libGLX_nvidia.so.0 + libEGL_nvidia.so.0"
else
    echo "  [warn] install completed but expected files missing"
    exit 1
fi
