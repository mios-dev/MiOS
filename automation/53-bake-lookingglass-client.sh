#!/usr/bin/env bash
# AI-hint: Automates the compilation and installation of the Looking Glass client binary to /usr/bin/ if not already present, handling version detection and toolchain checks during the MiOS build process.
# 53-bake-lookingglass-client.sh - git clone Looking Glass B7, cmake/make,
# install looking-glass-client binary to /usr/bin/. BAKED IN - WHEN POSSIBLE.
#
# fix:
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

# Resolve latest Looking Glass release branch from upstream. Project policy:
# every dependency tracks :latest from its source. LG uses letter-numbered
# release branches (B6, B7, ...); pick the highest by version sort.
LG_BRANCH="${MIOS_BUILD_BAKE_REFS_LOOKINGGLASS:-B7}"
if [[ -z "$LG_BRANCH" ]]; then
    LG_BRANCH=$(git ls-remote --heads https://github.com/gnif/LookingGlass.git 'B*' 2>/dev/null \
        | awk -F/ '{print $NF}' \
        | sort -V \
        | tail -n1 || true)
    [[ -n "$LG_BRANCH" ]] || die "Looking Glass: git ls-remote returned no B* release branch"
fi
record_version looking-glass "$LG_BRANCH" "https://github.com/gnif/LookingGlass/tree/${LG_BRANCH}"
BUILD_DIR="/tmp/LookingGlass-build"

# --- Ensure the LG client build deps (12-virt.sh usually provides these; if the *-devel packages
# were stripped, the fallback cmake dies on a missing pkg-config module -- e.g. fontconfig). Install
# the documented Fedora LG-client set so the build can actually configure. -------------------------
if command -v dnf5 >/dev/null 2>&1; then _DNF=dnf5; elif command -v dnf >/dev/null 2>&1; then _DNF=dnf; else _DNF=""; fi
if [[ -n "$_DNF" ]]; then
    log "ensuring Looking Glass client build deps (fontconfig-devel, etc.)"
    "$_DNF" install -y --setopt=install_weak_deps=False \
        fontconfig-devel spice-protocol nettle-devel libglvnd-devel libdecor-devel \
        pipewire-devel wayland-devel wayland-protocols-devel libxkbcommon-x11-devel \
        libXi-devel libXinerama-devel libXcursor-devel libXpresent-devel \
        libXScrnSaver-devel libXrandr-devel binutils-devel dejavu-sans-mono-fonts \
        >/dev/null 2>&1 || warn "some LG client build deps could not be installed (cmake will report specifics)"
fi

# --- Clone + Build ----------------------------------------------------------
LG_OK=""
for attempt in 1 2 3; do
    log "Compilation attempt $attempt/3..."
    cd /                 # leave any prior attempt's build dir BEFORE removing it -- otherwise the
    rm -rf "$BUILD_DIR"  # next git clone runs from a deleted CWD ("Unable to read current working directory").

    if ! git clone --depth 1 --branch "$LG_BRANCH" --recurse-submodules \
            https://github.com/gnif/LookingGlass.git "$BUILD_DIR"; then
        warn "git clone failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
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
        warn "cmake configure failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    log "building looking-glass-client (jobs=$(nproc))"
    if ! make -j"$(nproc)"; then
        warn "make failed on attempt $attempt"
        sleep $((attempt * 8))
        continue
    fi
    
    log "installing binary to /usr/bin/looking-glass-client"
    install -Dm0755 looking-glass-client /usr/bin/looking-glass-client
    
    if [[ -x /usr/bin/looking-glass-client ]]; then
        LG_OK=1
        break
    fi
done

if [[ -z "$LG_OK" ]]; then
    warn "looking-glass-client build failed after 3 attempts."
    exit 1
fi

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

log "looking-glass-client installed at /usr/bin/looking-glass-client"
