#!/bin/bash
# 'MiOS' v0.2.4 -- 11-hardware: GPU drivers (Mesa + AMD ROCm + Intel + NVIDIA)
#
# NVIDIA strategy (v0.2.0):
#   Primary:  ucore-hci:stable-nvidia ships pre-signed kmods for the base
#             kernel. If modinfo finds them for `uname -r`, we keep them.
#   Fallback: akmod rebuild from RPMFusion (requires matching kernel-devel).
#             If that fails or kernel-devel is unavailable, we accept no
#             NVIDIA acceleration - image still works for everything else.
#
# Mesa (AMD/Intel/software fallback) and ROCm + intel-compute-runtime are
# installed from PACKAGES.md. They have no kernel-version coupling.
#
# CHANGELOG:
#   v0.2.0: Dropped COPY-layer fallback. ucore-hci IS already built from
#           ublue's akmods-nvidia pipeline - copying those same RPMs on top
#           would create RPM conflicts, not redundancy. Kernel-mismatch
#           recovery falls to akmod rebuild + graceful skip.
#   v0.2.0: (attempted COPY-layer, reverted)
#   v2.0:   NVIDIA akmod baseline removed (ucore base provides pre-signed)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

KVER=$(cat /tmp/mios-kver 2>/dev/null || find /lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1)

# ── Mesa (AMD / Intel / software fallback) ──────────────────────────────────
echo "[11-hardware] Installing Mesa GPU stack..."
install_packages_strict "gpu-mesa"

# ── AMD ROCm (fault-tolerant) ───────────────────────────────────────────────
echo "[11-hardware] Installing ROCm (optional)..."
install_packages "gpu-amd-compute"

# ── Intel GPU Compute (fault-tolerant -- may not be on all architectures) ──
echo "[11-hardware] Installing Intel compute runtime (fault-tolerant)..."
install_packages "gpu-intel-compute" || true

# ── NVIDIA: Verify ucore's pre-signed modules match the kernel ──────────────
echo "[11-hardware] Checking NVIDIA modules from ucore base (kernel=$KVER)..."

NVIDIA_PRESENT=0
if [[ -d "/lib/modules/$KVER/extra/nvidia" ]] || \
   [[ -d "/lib/modules/$KVER/extra/nvidia-open" ]] || \
   modinfo nvidia -k "$KVER" &>/dev/null; then
    echo "[11-hardware] [ok] NVIDIA kmod present for kernel $KVER (ucore pre-signed)"
    NVIDIA_PRESENT=1
fi

# ── NVIDIA fallback: akmod rebuild via RPMFusion ────────────────────────────
# Only if ucore base missed (rare - the ucore:stable-nvidia tag guarantees
# its own kernel matches). This path requires kernel-devel-$KVER which is the
# exact failure mode that broke v2.2.x when ucore kernel (v0.2.0) didn't
# match F44's kernel-devel (v0.2.0). If kernel-devel is unavailable, we log
# and accept NVIDIA-less - the image still works for everything else, and
# 34-gpu-detect.sh handles runtime blacklisting/unblacklisting.
if [[ $NVIDIA_PRESENT -eq 0 ]]; then
    echo "[11-hardware] Fallback: akmod-nvidia build against $KVER..."
    if install_packages "gpu-nvidia"; then
        if command -v akmods &>/dev/null; then
            akmods --force --kernels "$KVER" 2>&1 | tail -10 || true
            if modinfo nvidia -k "$KVER" &>/dev/null; then
                echo "[11-hardware] [ok] NVIDIA kmod rebuilt via akmods for $KVER"
                NVIDIA_PRESENT=1
            fi
        fi
    fi
fi

if [[ $NVIDIA_PRESENT -eq 0 ]]; then
    echo "[11-hardware] [!] No NVIDIA kmod for $KVER after all fallback attempts."
    echo "[11-hardware]    Image will ship without NVIDIA acceleration. Users with"
    echo "[11-hardware]    NVIDIA hardware can rebuild the kmod at runtime:"
    echo "[11-hardware]       sudo dnf install kernel-devel-\$(uname -r) akmod-nvidia"
    echo "[11-hardware]       sudo akmods --force --kernels \$(uname -r)"
fi

# Regenerate CDI spec if nvidia-ctk is available (fails gracefully in no-GPU builds)
if command -v nvidia-ctk &>/dev/null; then
    nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml 2>/dev/null || true
    echo "[11-hardware] NVIDIA CDI spec generated (build-time; runtime refresh handled by nvidia-cdi-refresh.path)"
fi

# ── NVIDIA Open Kernel Module Configuration ─────────────────────────────────
# Turing+ (RTX 20xx and newer) supports open modules; RTX 50 Blackwell requires
# them. NVreg_OpenRmEnableUnsupportedGpus=1 lets open modules attempt older
# cards too (Pascal, Maxwell) where supported.
# ARCHITECTURAL FIX: Managed via usr/lib/modprobe.d/nvidia-open.conf
# to prevent /etc state drift.

echo "[11-hardware] GPU stack complete. Mesa + AMD ROCm + Intel + NVIDIA (ucore / akmod rebuild)."
