#!/usr/bin/env bash
# 'MiOS' MiOS-DEV overlay -- makes the build-host podman machine look and
# feel like a Live 'MiOS' environment so it can host the same Quadlets the
# deployed image runs (manifesto: "MiOS-DEV is the source upon what MiOS
# itself is based upon ... mios user appended for hosting the layered
# containers; guacamole, ollama, forgejo, cockpit etc-etc").
#
# Run inside MiOS-DEV, from the MiOS repo working tree:
#   sudo bash automation/overlay-builder.sh /path/to/MiOS-repo
#
# What it does (idempotent throughout):
#   * rsync usr/share/mios/, usr/lib/mios/, usr/libexec/mios/, usr/bin/mios
#     onto / so the canonical 'MiOS' CLI / docs / paths.sh / motd binary all
#     exist at the expected paths
#   * rsync usr/lib/profile.d/mios-*.sh + etc/profile.d/mios-*.sh so login
#     shells get the 'MiOS' MOTD + WSLg env exports
#   * rsync /etc/skel skeleton from the repo if present
#   * rsync etc/mios/ (vendor host config templates)
#   * COPY MiOS sysusers.d into /etc/sysusers.d/ + run systemd-sysusers,
#     creating the 'mios' login user (uid 1000) and the service accounts
#     (mios-ollama, mios-forge, mios-guacamole, mios-pxe-hub,
#     mios-crowdsec, mios-guacd, mios-postgres -- 810-829 range; mios-virt
#     800; cockpit). Drops into /etc (host-layer override) instead of
#     /usr/lib (vendor layer) to avoid colliding with podman-machine-os's
#     own /usr/lib/sysusers.d/20-podman-machine.conf.
#   * COPY MiOS tmpfiles.d into /etc/tmpfiles.d/ + run systemd-tmpfiles
#     --create so /var/lib/<service>/ dirs the Quadlets bind-mount exist
#     with the right ownership.
#   * Establish /var/home/mios (FCOS atomic-desktops home convention)
#     seeded from /etc/skel.
#   * Append /etc/subuid + /etc/subgid entries so the mios user can run
#     rootless podman containers (which is how MiOS-DEV mirrors a deployed
#     MiOS host's Quadlet hosting).
#
# What it explicitly does NOT do (would conflict with podman-machine init):
#   * Install systemd unit files (the podman-machine OS owns /usr/lib/
#     systemd/system; Quadlets land in /etc/containers/systemd/ which is
#     separate)
#   * Install kargs.d (kernel command line is the podman-machine kernel,
#     not bootc; MiOS kargs only matter on a deployed bootc host)
#   * Install SELinux policy modules (MiOS-DEV runs in WSL where SELinux
#     is permissive at best)
#
# After running, opening any new shell in MiOS-DEV shows the 'MiOS' MOTD,
# `mios` is on PATH, and `id mios` returns uid 1000. `loginctl enable-linger
# mios` then enables rootless container hosting so the operator can
# `systemctl --user start mios-forge.service` or any other MiOS Quadlet.

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

# /usr/share/mios -- vendor docs, profile.toml, mios.toml (canonical SSOT),
# mios.toml.example, ai/, configurator/
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
# back to the layered mios.toml overlay -- the canonical SSOT)
_rsync_in "etc/mios/"          "/etc/mios/"

# Mark the executable bits on the canonical libexec scripts
find /usr/libexec/mios -type f -exec chmod +x {} + 2>/dev/null || true
chmod +x /usr/bin/mios 2>/dev/null || true

# ── sysusers: create the mios login user + service accounts so MiOS-DEV
# can host the same Quadlets as a deployed MiOS host. Drop into
# /etc/sysusers.d/ (host-layer override) instead of /usr/lib/sysusers.d/
# (vendor layer) so we coexist with podman-machine-os's vendor file
# /usr/lib/sysusers.d/20-podman-machine.conf without overwriting it.
echo "[overlay-builder] Setting up MiOS sysusers (etc-layer override)..."
install -d -m 0755 /etc/sysusers.d
_sysusers_added=0
for sf in usr/lib/sysusers.d/10-mios.conf \
          usr/lib/sysusers.d/30-mios-tmpfiles-prereq.conf \
          usr/lib/sysusers.d/50-mios.conf \
          usr/lib/sysusers.d/50-mios-ai.conf \
          usr/lib/sysusers.d/50-mios-gpu.conf \
          usr/lib/sysusers.d/50-mios-services.conf \
; do
    [[ -f "$sf" ]] || continue
    install -m 0644 "$sf" "/etc/sysusers.d/$(basename "$sf")"
    echo "[overlay-builder]  /etc/sysusers.d/$(basename "$sf")"
    _sysusers_added=$((_sysusers_added + 1))
done
if (( _sysusers_added > 0 )); then
    # systemd-sysusers materializes the entries into /etc/passwd + /etc/group.
    # Idempotent: existing users with matching UID/GID are left alone.
    systemd-sysusers 2>&1 | sed 's/^/[overlay-builder] sysusers: /' || true
fi

# ── tmpfiles: create /var/lib/<service>/ dirs the Quadlets bind-mount.
# Same /etc-layer override pattern. mios-services.conf, mios-ollama.conf,
# mios-forge.conf etc. declare per-service writable state directories that
# the matching Quadlets expect to find pre-created with the right owner.
echo "[overlay-builder] Setting up MiOS tmpfiles.d (etc-layer override)..."
install -d -m 0755 /etc/tmpfiles.d
_tmpfiles_added=0
for tf in usr/lib/tmpfiles.d/mios.conf \
          usr/lib/tmpfiles.d/mios-services.conf \
          usr/lib/tmpfiles.d/mios-ollama.conf \
          usr/lib/tmpfiles.d/mios-forge.conf \
          usr/lib/tmpfiles.d/mios-forge-runner.conf \
          usr/lib/tmpfiles.d/mios-ai.conf \
          usr/lib/tmpfiles.d/mios-pxe-hub.conf \
          usr/lib/tmpfiles.d/mios-guacamole.conf \
          usr/lib/tmpfiles.d/mios-infra.conf \
          usr/lib/tmpfiles.d/mios-user.conf \
; do
    [[ -f "$tf" ]] || continue
    install -m 0644 "$tf" "/etc/tmpfiles.d/$(basename "$tf")"
    echo "[overlay-builder]  /etc/tmpfiles.d/$(basename "$tf")"
    _tmpfiles_added=$((_tmpfiles_added + 1))
done
install -d -m 0755 /usr/lib/mios/logs
install -d -m 0755 /var/lib/mios
if (( _tmpfiles_added > 0 )); then
    # --create materializes declared paths; --remove would clean up paths
    # marked for removal (we skip that to be conservative -- the Quadlet
    # mounts that touch /var should never see "missing" as their state).
    systemd-tmpfiles --create 2>&1 | sed 's/^/[overlay-builder] tmpfiles: /' || true
fi

# ── /var/home/mios -- FCOS / atomic-desktops home convention
# (the deployed MiOS image uses /var/home/mios as the operator's $HOME so
# /etc 3-way merge doesn't have to deal with home-dir state). Establish
# the same on MiOS-DEV so configs match across substrates.
install -d -m 0755 /var/home
if id mios >/dev/null 2>&1; then
    install -d -m 0755 -o mios -g mios /var/home/mios 2>/dev/null || \
        install -d -m 0755 /var/home/mios
    if [[ -d /etc/skel ]] && [[ ! -e /var/home/mios/.bashrc ]]; then
        rsync -aH --ignore-existing /etc/skel/ /var/home/mios/ 2>/dev/null || true
        chown -R mios:mios /var/home/mios 2>/dev/null || true
        echo "[overlay-builder]  /var/home/mios seeded from /etc/skel"
    fi
fi

# ── subuid / subgid for rootless podman as the mios user.
# Rootless containers need an unprivileged uid/gid range available for
# user-namespace mapping. Standard convention: 524288 + 65536 (one
# 64K-uid range, starting outside the host's regular uid space). The
# mios-services accounts (810-829) don't need their own subuid ranges
# because they're nologin shell-less daemons that do not run rootless
# containers themselves.
if ! grep -q '^mios:' /etc/subuid 2>/dev/null; then
    echo 'mios:524288:65536' >> /etc/subuid
    echo "[overlay-builder]  /etc/subuid: mios:524288:65536 added"
fi
if ! grep -q '^mios:' /etc/subgid 2>/dev/null; then
    echo 'mios:524288:65536' >> /etc/subgid
    echo "[overlay-builder]  /etc/subgid: mios:524288:65536 added"
fi

# ── Linger so the mios user can run systemd --user services (the
# Quadlets) without a logged-in session. Required for `systemctl --user
# enable mios-forge.service` etc. to actually start at boot.
if command -v loginctl >/dev/null 2>&1 && id mios >/dev/null 2>&1; then
    loginctl enable-linger mios 2>/dev/null || true
    echo "[overlay-builder]  loginctl enable-linger mios"
fi

echo "[overlay-builder] Overlay complete."
echo "[overlay-builder] Open a fresh shell to see the 'MiOS' MOTD."
echo "[overlay-builder] Verify mios user: id mios; subuid grep mios /etc/subuid"
echo "[overlay-builder] Container-host probe: sudo -u mios podman info"
