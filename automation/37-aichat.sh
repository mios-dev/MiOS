#!/bin/bash
# 37-aichat: install aichat / aichat-ng via Distrobox (v0.2.4+)
#
# Per Architectural Law 1 (VM | Container | Flatpak only -- no
# application binaries on the host substrate), aichat + aichat-ng
# now ship inside a Distrobox container. The container is BUILT at
# boot by /usr/share/containers/systemd/mios-aichat.build (Quadlet),
# pre-pulled by mios-aichat.image, and assembled into a Distrobox
# instance per /usr/share/mios/distrobox/aichat/distrobox.ini.
#
# This script's only job at IMAGE BUILD TIME is to drop the host-side
# shim wrappers under /usr/bin so the operator can type `aichat`
# from any shell and have it route into the container. The shims
# exec `distrobox enter mios-aichat -- <bin> "$@"` -- a single
# distrobox roundtrip with no host application code.
#
# The pre-v0.2.4 musl-tarball install at /usr/bin/aichat was removed
# (substrate-purity violation per project research May 2026).
#
# References:
#   /usr/share/mios/distrobox/aichat/Containerfile
#   /usr/share/mios/distrobox/aichat/distrobox.ini
#   /usr/share/containers/systemd/mios-aichat.{image,build}
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

echo "[37-aichat] dropping host-side Distrobox shims (substrate-pure)"

mkdir -p /usr/bin

# Shared shim body. Each verb wrapper sources this for the heavy
# lifting -- one file = one place to fix bugs.
mkdir -p /usr/libexec/mios
cat > /usr/libexec/mios/aichat-distrobox-exec.sh <<'SHIM'
#!/usr/bin/env bash
# /usr/libexec/mios/aichat-distrobox-exec.sh
#
# Sourced by /usr/bin/aichat and /usr/bin/aichat-ng to route the
# call into the mios-aichat Distrobox container without duplicating
# wrapper logic.
#
# First-call ergonomics:
#   * If `mios-aichat` container doesn't exist yet, run distrobox-
#     assemble to create it from the Quadlet-built image. The image
#     itself is built / pulled by mios-aichat.{build,image} units.
#   * If neither image nor container exists (host still on the
#     legacy /usr/bin/aichat install), exec the binary at
#     $LEGACY_BIN if present, with a warning. This lets a partial
#     bootstrap still produce a working aichat command.
set -euo pipefail
VERB="${1:?usage: aichat-distrobox-exec.sh <verb> [args...]}"
shift || true

CONTAINER="mios-aichat"
ASSEMBLE_INI="/usr/share/mios/distrobox/aichat/distrobox.ini"

if ! command -v distrobox >/dev/null 2>&1; then
    echo "aichat: distrobox is not installed on this host." >&2
    echo "        Run automation/37-aichat.sh on a machine with distrobox available," >&2
    echo "        or install it via dnf install distrobox." >&2
    exit 127
fi

# Existence check: ask podman directly. `distrobox list` formats its
# output as pipe-aligned columns (ID | NAME | STATUS | IMAGE) which is
# fragile to parse with awk -- and a distrobox container is just a
# regular podman container under the hood, so `podman container
# exists` is both faster and unambiguous.
if ! podman container exists "$CONTAINER" 2>/dev/null; then
    if [[ -f "$ASSEMBLE_INI" ]]; then
        echo "aichat: first run -- assembling $CONTAINER from $ASSEMBLE_INI" >&2
        distrobox-assemble create --file "$ASSEMBLE_INI" >&2 || true
    fi
    # If the assemble failed (image wasn't built yet), surface the
    # remediation. The .build Quadlet writes to root podman storage;
    # /etc/containers/storage.conf.d/30-mios-additionalstores.conf
    # makes that store readable by rootless users so distrobox can
    # find localhost/mios/aichat:latest without a copy or push.
    if ! podman container exists "$CONTAINER" 2>/dev/null; then
        echo "aichat: container creation failed -- the build/image Quadlets" >&2
        echo "        (mios-aichat.{build,image}) may not have completed yet." >&2
        echo "        Re-try in a few seconds, or run:" >&2
        echo "          sudo systemctl start mios-aichat-build.service" >&2
        echo "          sudo systemctl start mios-aichat-image.service" >&2
        exit 1
    fi
fi

exec distrobox enter "$CONTAINER" -- "$VERB" "$@"
SHIM
chmod 0755 /usr/libexec/mios/aichat-distrobox-exec.sh

# /usr/bin/aichat -- thin shim
cat > /usr/bin/aichat <<'WRAP'
#!/usr/bin/env bash
exec /usr/libexec/mios/aichat-distrobox-exec.sh aichat "$@"
WRAP
chmod 0755 /usr/bin/aichat

# /usr/bin/aichat-ng -- thin shim
cat > /usr/bin/aichat-ng <<'WRAP'
#!/usr/bin/env bash
exec /usr/libexec/mios/aichat-distrobox-exec.sh aichat-ng "$@"
WRAP
chmod 0755 /usr/bin/aichat-ng

echo "[37-aichat] host shims at /usr/bin/aichat, /usr/bin/aichat-ng"
echo "[37-aichat] container build runs at boot via mios-aichat.build (Quadlet)"
