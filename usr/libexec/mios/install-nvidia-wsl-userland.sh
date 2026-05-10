#!/bin/bash
# /usr/libexec/mios/install-nvidia-wsl-userland.sh
#
# Install NVIDIA's Vulkan ICD + GLX/EGL userspace libs for WSLg
# dev-VM hosts. Called by build-mios.ps1's Quadlet/overlay phase
# AND idempotent-callable from `mios install-gpu` for live re-runs.
#
# What this gets you:
#   * /usr/share/vulkan/icd.d/nvidia_icd.x86_64.json
#   * /usr/lib64/libGLX_nvidia.so + libEGL_nvidia.so + libGLESv2_nvidia
#   * libnvidia-ml + libnvidia-gpucomp (already provided by WSL drop,
#     installing the RPM versions is harmless and adds versioned symlinks)
#   * egl-wayland + egl-gbm + egl-x11 (EGL platform implementations)
#
# What this does NOT do:
#   * NO kernel-module install (kmod-nvidia / akmod-nvidia) -- the
#     kernel module isn't applicable on WSL2; /dev/dxg is the kernel-
#     mode bridge and it's already there.
#   * NOT a full CUDA toolkit install -- libnvidia-ml is enough for
#     `nvidia-smi` and PyTorch's CUDA detection. Operators wanting
#     the full toolchain run `dnf install cuda-toolkit-X-Y` separately.
#
# Caveat: this installs NVIDIA's NATIVE Vulkan ICD which expects
# /dev/nvidia* device nodes. WSL2 doesn't have those -- it has
# /dev/dxg (WDDM) instead. So the NVIDIA Vulkan ICD doesn't enumerate
# any GPU under WSL; Vulkan workloads still go through Microsoft's
# `dzn` ICD (Direct3D12 translation). Why install NVIDIA libs anyway?
#
#   1. Compute / CUDA workloads work via libcuda + libnvidia-ml
#      (Microsoft's WSL drop) regardless of NVIDIA Vulkan availability.
#   2. nvidia-smi becomes available so the operator can verify GPU
#      health from inside the dev VM.
#   3. Flatpak apps that bundle libGLX_nvidia detection get a real
#      (if non-functional under WSL) vendor lib to point at, avoiding
#      "no NVIDIA driver detected" warnings on launch.
#   4. Forward-compatible: when WSL2 eventually exposes /dev/nvidia*
#      (or NVIDIA ships a WSL-aware Vulkan ICD that targets /dev/dxg),
#      this stack is already in place.
#
# Idempotent + safe to re-run: dnf install of already-present pkgs
# is a no-op; repo add with --overwrite refreshes the .repo file.
#
# Operator override: set MIOS_SKIP_NVIDIA_INSTALL=1 to skip entirely.

set -e

if [ "${MIOS_SKIP_NVIDIA_INSTALL:-0}" = "1" ]; then
    echo "  [skip] MIOS_SKIP_NVIDIA_INSTALL=1; not installing NVIDIA userland."
    exit 0
fi

# Gate on WSLg presence -- this script is for WSLg dev VMs only.
if [ ! -d /mnt/wslg ] && [ ! -c /dev/dxg ]; then
    echo "  [skip] not WSLg (no /mnt/wslg + no /dev/dxg); NVIDIA WSL userland not applicable."
    exit 0
fi

# Detect upstream Fedora version. MiOS-branded os-release sets
# VERSION_ID to the MiOS version; PLATFORM_ID preserves the Fedora
# upstream as "platform:fXX".
fedver=$(. /etc/os-release; echo "$PLATFORM_ID" | sed -E 's/^.*:f([0-9]+)$/\1/')
[ -z "$fedver" ] && fedver=$(. /etc/os-release; echo "${VERSION_ID:-44}")
echo "  Fedora upstream: $fedver"

# Probe NVIDIA CUDA repo URLs. Try the detected fedora version first,
# fall back to nearby versions if 404 (NVIDIA publishes per-Fedora-
# version repos on a release-by-release basis).
repo_url=""
for v in "$fedver" 44 43 42 41 40; do
    [ -z "$v" ] && continue
    cand="https://developer.download.nvidia.com/compute/cuda/repos/fedora${v}/x86_64/cuda-fedora${v}.repo"
    code=$(curl -fsI -o /dev/null -w "%{http_code}" "$cand" 2>/dev/null || true)
    if [ "$code" = "200" ]; then
        echo "  NVIDIA CUDA repo: fedora${v} ($cand)"
        repo_url="$cand"
        break
    fi
done
if [ -z "$repo_url" ]; then
    echo "  [warn] no NVIDIA CUDA repo reachable for Fedora ${fedver} or fallbacks; skipping."
    exit 0
fi

dnf config-manager addrepo --from-repofile="$repo_url" --overwrite >/dev/null 2>&1 || true

# Install userland-only. Excludes are defensive against weak-deps
# pulling in a kernel-module package; --setopt=install_weak_deps=False
# is also belt-and-suspenders.
dnf install -y --setopt=install_weak_deps=False \
    -x 'kmod-nvidia*' \
    -x 'akmod-nvidia*' \
    -x 'nvidia-driver-cuda' \
    -x 'nvidia-driver-NvFBCOpenGL' \
    nvidia-driver-libs 2>&1 | tail -5

# Verify install landed.
if [ -e /usr/share/vulkan/icd.d/nvidia_icd.x86_64.json ] \
    && [ -e /usr/lib64/libGLX_nvidia.so.0 ]; then
    echo "  [ok] NVIDIA WSL userland installed:"
    echo "         vulkan ICD: /usr/share/vulkan/icd.d/nvidia_icd.x86_64.json"
    echo "         GLX/EGL:    /usr/lib64/libGLX_nvidia.so.0 + libEGL_nvidia.so.0"
else
    echo "  [warn] install completed but expected files missing -- inspect dnf output above."
    exit 1
fi
