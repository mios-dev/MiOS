#!/usr/bin/env bash
# 'MiOS' BUILDER overlay -- makes the build-host WSL2 podman machine
# look and feel like a Live 'MiOS' environment without breaking the
# podman-machine OS plumbing underneath.
#
# Run inside the BUILDER, from the MiOS repo working tree:
#   sudo bash automation/overlay-builder.sh /path/to/MiOS-repo
#
# What it does (idempotent, --ignore-existing throughout):
#   * rsync usr/share/mios/, usr/lib/mios/, usr/libexec/mios/, usr/bin/mios
#     onto / so the canonical 'MiOS' CLI / docs / paths.sh / motd binary all
#     exist at the expected paths
#   * rsync usr/lib/profile.d/mios-*.sh + etc/profile.d/mios-*.sh so login
#     shells get the 'MiOS' MOTD + WSLg env exports
#   * rsync /etc/skel skeleton from the repo if present
#   * rsync etc/mios/ (vendor host config templates)
#   * NOT touched: systemd units, drop-ins, tmpfiles.d, sysusers.d, kargs.d,
#     SELinux modules -- these would conflict with the podman-machine init
#     and must only land in the bootc image proper.
#
# After running, opening any new shell in BUILDER shows the 'MiOS' MOTD and
# `mios` is on PATH.

set -euo pipefail

REPO="${1:-${PWD}}"
if [[ ! -d "$REPO/usr/share/mios" ]]; then
    echo "[overlay-builder] FAIL: '$REPO' does not look like a 'MiOS' repo (no usr/share/mios)" >&2
    exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "[overlay-builder] FAIL: must run as root (sudo bash $0 $REPO)" >&2
    exit 1
fi

cd "$REPO"
echo "[overlay-builder] Source repo: $REPO"

# rsync helper: keep ownership simple (root:root), don't clobber existing
# files (so podman-machine internals stay intact), preserve perms/symlinks.
_rsync_in() {
    local src="$1" dst="$2"
    [[ -e "$src" ]] || { echo "[overlay-builder] skip $src (missing)"; return 0; }
    install -d "$dst"
    rsync -aH --ignore-existing --info=stats0 "$src" "$dst"
    echo "[overlay-builder]  $src -> $dst"
}

# /usr/share/mios -- vendor docs, profile.toml, env.defaults, mios.toml.example
_rsync_in "usr/share/mios/"    "/usr/share/mios/"

# /usr/lib/mios -- runtime paths.sh + any future shared lib
_rsync_in "usr/lib/mios/"      "/usr/lib/mios/"

# /usr/libexec/mios -- motd, role-apply, gpu-detect, etc.
_rsync_in "usr/libexec/mios/"  "/usr/libexec/mios/"

# /usr/bin/mios -- CLI entrypoint (Python)
if [[ -f "usr/bin/mios" ]]; then
    install -m 0755 "usr/bin/mios" "/usr/bin/mios"
    echo "[overlay-builder]  /usr/bin/mios"
fi

# Profile.d -- MOTD + WSLg env exports
for src in usr/lib/profile.d/mios-*.sh etc/profile.d/mios-*.sh; do
    [[ -f "$src" ]] || continue
    install -d "/etc/profile.d"
    install -m 0644 "$src" "/etc/profile.d/$(basename "$src")"
    echo "[overlay-builder]  /etc/profile.d/$(basename "$src")"
done

# /etc/skel -- shell dotfiles, only seed if directory exists in the repo
_rsync_in "etc/skel/"          "/etc/skel/"

# /etc/mios -- vendor host config templates (install.env will be missing on
# BUILDER because no Windows installer ran here; that's fine, agents fall
# back to /usr/share/mios/env.defaults)
_rsync_in "etc/mios/"          "/etc/mios/"

# Mark the executable bits on the canonical libexec scripts
find /usr/libexec/mios -type f -exec chmod +x {} + 2>/dev/null || true
chmod +x /usr/bin/mios 2>/dev/null || true

# Re-run tmpfiles for /usr/lib/mios subdirs (logs, scratch). These are
# declared in usr/lib/tmpfiles.d/mios.conf in the bootc image; on BUILDER
# we just create them imperatively because the tmpfiles.d file isn't
# overlaid (would clash with podman-machine).
install -d -m 0755 /usr/lib/mios/logs
install -d -m 0755 /var/lib/mios

echo "[overlay-builder] Overlay complete."
echo "[overlay-builder] Open a fresh shell to see the 'MiOS' MOTD."
