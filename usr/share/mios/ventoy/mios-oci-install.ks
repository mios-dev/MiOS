# AI-hint: Path-B OFFLINE immutable-bootc Anaconda kickstart -- its %post mounts the MiOS-Repo brain partition and finally calls the real tools/install.sh (role bootc-baremetal-disk-installer), which runs `bootc install to-disk --transport oci-archive` from the staged /mnt/mios-repo/mios-latest.tar (zero-network). This deploys the REAL immutable ghcr.io/mios-dev/mios image, unlike the sibling mutable-Fedora mios-kickstart.cfg (that stays a separate deploy MODE). No clearpart/%packages here on purpose: the OS is laid down by bootc, not by an Anaconda package transaction.
# AI-related: tools/install.sh, usr/libexec/mios/mios-stage-oci-archive, cat/loopback.cfg, usr/share/mios/ventoy/mios-kickstart.cfg, usr/share/mios/ventoy/ventoy.json, usr/share/mios/mios.toml [cat.repo_partition], automation/98-drift-checks.sh (checks 81/85/88)

# Non-interactive text install. Booted by cat/loopback.cfg's "Install MiOS from OCI
# archive" entry via `rd.live.image inst.ks=hd:LABEL=MiOS-Repo:/ventoy/mios-oci-install.ks`,
# so this %post runs in the live/installer environment as root; the actual disk
# deployment is performed by tools/install.sh (bootc), not by Anaconda.
text --non-interactive

# Best-effort networking only (--device=link never hangs without a carrier). The
# install itself is zero-network: the immutable image comes from the staged
# oci-archive on the USB, never from a registry pull.
network --bootproto=dhcp --device=link --activate --onboot=on

# Reboot into the freshly bootc-installed MiOS once %post succeeds.
reboot

%post --nochroot --log=/var/log/mios-oci-install.log --erroronfail
set -euo pipefail

# SSOT: mios.toml [cat.repo_partition].label / the tools/install.sh default archive.
REPO_LABEL="MiOS-Repo"
OCI_ARCHIVE="/mnt/mios-repo/mios-latest.tar"

echo "[mios-oci-install] Path-B offline immutable install starting..."

# 1. Mount the MiOS-Repo brain partition (read-only) to reach the staged oci-archive
#    tar and the shipped tools/install.sh. install.sh re-resolves + re-mounts the same
#    label itself; a pre-mount here just makes the installer discoverable.
repo_dev="$(blkid -L "$REPO_LABEL" 2>/dev/null || true)"
if [ -n "$repo_dev" ]; then
    mkdir -p /mnt/mios-repo
    grep -q " /mnt/mios-repo " /proc/mounts 2>/dev/null || mount -o ro "$repo_dev" /mnt/mios-repo || true
fi

# 2. Locate the REAL bare-metal installer -- tools/install.sh, uniquely marked
#    MIOS_INSTALLER_ROLE=bootc-baremetal-disk-installer (drift-check 86). Candidate
#    layouts depend on how the USB stager laid out the brain repo (git archive ->
#    repos/, or a named MiOS/ tree). The role-marker grep guards against grabbing the
#    unrelated installation/mios-install.sh guided installer.
installer=""
for cand in \
    /mnt/mios-repo/repos/tools/install.sh \
    /mnt/mios-repo/repos/MiOS/tools/install.sh \
    /mnt/mios-repo/repos/mios/tools/install.sh \
    /mnt/mios-repo/MiOS/tools/install.sh \
    /mnt/mios-repo/mios/tools/install.sh \
    /mnt/mios-repo/tools/install.sh ; do
    if [ -f "$cand" ] && grep -q "MIOS_INSTALLER_ROLE=bootc-baremetal-disk-installer" "$cand"; then
        installer="$cand"
        break
    fi
done
if [ -z "$installer" ]; then
    echo "[mios-oci-install] FATAL: tools/install.sh (bootc-baremetal-disk-installer) not found on $REPO_LABEL." >&2
    exit 1
fi

# 3. Confirm the zero-network source of the immutable image is present.
if [ ! -f "$OCI_ARCHIVE" ]; then
    echo "[mios-oci-install] FATAL: staged oci-archive $OCI_ARCHIVE missing (produce it with 'just oci-archive' + the USB stager)." >&2
    exit 1
fi

# 4. Auto-select the first FIXED (non-removable, RM=0) disk as the install target;
#    the boot USB is removable (RM=1) and loop devices are TYPE=loop, so both are
#    skipped. Operators can override by editing this menu entry's target.
target="$(lsblk -dnro NAME,TYPE,RM | awk '$2=="disk" && $3==0 {print "/dev/"$1; exit}')"
if [ -z "$target" ]; then
    echo "[mios-oci-install] FATAL: no fixed target disk found." >&2
    exit 1
fi

echo "[mios-oci-install] installer=$installer target=$target archive=$OCI_ARCHIVE"

# 5. Hand off to the genuine offline installer. tools/install.sh runs:
#      bootc install to-disk --target-no-signature-verification \
#        --source-imgref "oci-archive:$OCI_ARCHIVE" "$target"
#    i.e. the immutable --transport oci-archive path, fully offline. Its interactive
#    'Type YES to proceed' confirm gate is satisfied by the piped 'YES'.
echo "YES" | bash "$installer" --target-disk "$target" --oci-archive "$OCI_ARCHIVE"

echo "[mios-oci-install] Immutable bootc install complete; rebooting into MiOS."
%end
