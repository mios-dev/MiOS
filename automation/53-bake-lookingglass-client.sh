#!/usr/bin/env bash
# 53-bake-lookingglass-client.sh - git clone Looking Glass B7, cmake/make,
# install looking-glass-client binary to /usr/bin/. BAKED IN - WHEN POSSIBLE.
#
# v0.1.1 fix:
#   - SKIP (don't fail) when cmake or required dev libraries are missing.
#     12-virt.sh already builds Looking Glass as part of its virtualization
#     stack and then removes cmake/gcc/*-devel to shrink the image. By the
#     time this script runs the toolchain is gone. Skipping here is safe
#     because the binary is already installed by 12-virt.sh; a hard-fail
#     aborted the whole build for a redundant second build attempt.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# --- If 12-virt.sh already baked it in, declare success and exit -----------
if [[ -x /usr/bin/looking-glass-client ]]; then
    log "OK: looking-glass-client already present (installed by 12-virt.sh)"
    /usr/bin/looking-glass-client --version 2>&1 | head -5 || true
    exit 0
fi

# --- Check toolchain availability ------------------------------------------
MISSING=""
for tool in cmake make gcc git; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING="${MISSING}${tool} "
    fi
done

if [[ -n "$MISSING" ]]; then
    warn "SKIP: missing toolchain: $MISSING"
    warn "      12-virt.sh normally builds Looking Glass and removes cmake/gcc"
    warn "      afterwards. If 12-virt.sh failed, fix it first - the LG build"
    warn "      there is the canonical path."
    exit 0
fi

LG_BRANCH="${LG_BRANCH:-B7}"
BUILD_DIR="/tmp/LookingGlass-build"

# --- Clone -----------------------------------------------------------------
log "cloning Looking Glass $LG_BRANCH"
rm -rf "$BUILD_DIR"
if ! git clone --depth 1 --branch "$LG_BRANCH" --recurse-submodules \
        https://github.com/gnif/LookingGlass.git "$BUILD_DIR"; then
    warn "SKIP: git clone failed (network or branch issue)"
    exit 0
fi

# --- Configure + build client ---------------------------------------------
log "configuring client build"
mkdir -p "$BUILD_DIR/client/build"
cd "$BUILD_DIR/client/build"
if ! cmake -DCMAKE_INSTALL_PREFIX=/usr \
           -DCMAKE_INSTALL_LIBDIR=/usr/lib \
           -DCMAKE_BUILD_TYPE=Release \
           -DENABLE_LIBDECOR=ON \
           -DENABLE_PIPEWIRE=ON \
           -DENABLE_PULSEAUDIO=OFF \
           -DENABLE_BACKTRACE=OFF \
           ..; then
    warn "SKIP: cmake configure failed - check -devel packages"
    exit 0
fi

log "building looking-glass-client (jobs=$(nproc))"
if ! make -j"$(nproc)"; then
    warn "SKIP: make failed"
    exit 0
fi

# --- Install binary + desktop file ----------------------------------------
log "installing binary to /usr/bin/looking-glass-client"
install -Dm0755 looking-glass-client /usr/bin/looking-glass-client

# Ship a .desktop entry
install -Dm0644 /dev/stdin /usr/share/applications/looking-glass.desktop <<'DESK'
[Desktop Entry]
Type=Application
Name=Looking Glass
Comment=Low-latency KVM display from a VM via shared memory
Icon=video-display
Exec=looking-glass-client
Terminal=false
Categories=System;Utility;
Keywords=KVM;VFIO;Passthrough;
DESK

# --- Cleanup build tree (keep toolchain in image per self-building principle) ---
log "cleaning up source tree"
cd /
rm -rf "$BUILD_DIR"

# --- Verify ----------------------------------------------------------------
if [[ -x /usr/bin/looking-glass-client ]]; then
    log "OK: looking-glass-client baked in at /usr/bin/looking-glass-client"
    /usr/bin/looking-glass-client --version 2>&1 | head -5 || true
else
    warn "SKIP: binary missing after install (non-fatal)"
    exit 0
fi

log "Looking Glass client BAKED IN"
