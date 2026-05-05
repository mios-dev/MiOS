#!/bin/bash
# automation/41-mios-dropin-fanout.sh
#
# Fans canonical drop-in content from /usr/share/mios/dropins/ into the
# per-unit *.d/ directories at image build time.
#
# Why a script instead of committing 60+ identical files (or symlinks):
#   systemd's drop-in mechanism is per-unit -- there is no top-level
#   "apply this drop-in to many services" facility. The MiOS image
#   historically shipped 60+ byte-identical .conf files spread across
#   *.service.d/ / *.socket.d/ / *.mount.d/ / *.target.d/ for the four
#   common condition gates (virt-gate, bare-metal-only, mios-virt-gate,
#   mios-wsl2). Editing one gate meant editing 14+ files.
#
#   Symlinks would deduplicate at the filesystem layer, but creating
#   them on Windows authoring hosts requires SeCreateSymbolicLink-
#   Privilege or Developer Mode (Git Bash falls back to file-copy
#   without them); neither is reliable in a typical author setup.
#
#   So: store one canonical .conf per gate under usr/share/mios/dropins/
#   (committed, edited as a single source of truth), and fan it out at
#   image build time via this script. The deployed image carries the
#   fanned-out files exactly as before -- systemd reads them through its
#   normal *.d/ scanner -- but the source tree stays small and edits
#   propagate cleanly without filesystem-symlink dependencies.
#
# How to add a new gate:
#   1. Drop the canonical content at usr/share/mios/dropins/NAME.conf.
#   2. Add an entry to GATES below mapping NAME to the units it gates.
#   3. The next image build picks it up automatically.
#
# How to extend an existing gate to a new unit:
#   1. Append the unit name (with explicit suffix: foo.service,
#      bar.socket, baz.mount, ...) to that gate's UNITS list.
#   2. The next image build creates the drop-in.
#
# Idempotent: running this script repeatedly produces the same result,
# overwriting any prior copy (so an edit to the canonical propagates
# even on incremental rebuilds).

set -euo pipefail

# Build context root: in the Containerfile RUN that calls this script,
# /tmp/build is the writable copy of the repo and the image's /usr/lib/
# already exists. Read canonicals from the former, write drop-ins into
# the latter (the image hasn't yet absorbed usr/share/mios/dropins/
# at this point in the build).
DROPIN_SRC="${CTX:-/tmp/build}/usr/share/mios/dropins"
SYSTEMD_SYSTEM_DIR="/usr/lib/systemd/system"

# Each line: GATE_NAME:UNIT1,UNIT2,...
# GATE_NAME maps to ${DROPIN_SRC}/${GATE_NAME}.conf
# UNITs include the explicit suffix (.service, .socket, .mount, .target).
# The drop-in lands at ${SYSTEMD_SYSTEM_DIR}/${UNIT}.d/10-${GATE_NAME}.conf
GATES=(
    "virt-gate:mios-cdi-detect.service,mios-ceph-bootstrap.service,mios-flatpak-install.service,mios-gpu-amd.service,mios-gpu-intel.service,mios-gpu-nvidia.service,mios-gpu-status.service,mios-grd-setup.service,mios-k3s-init.service,mios-libvirtd-setup.service,mios-nvidia-cdi.service,mios-role.service,mios-selinux-init.service,mios-waydroid-init.service"

    "bare-metal-only:corosync.service,crowdsec.service,crowdsec-firewall-bouncer.service,mios-ha-bootstrap.service,multipathd.service,nfs-server.service,nmb.service,nvidia-powerd.service,osbuild-composer.service,osbuild-worker@1.service,pacemaker.service,pcsd.service,smb.service"

    "mios-virt-gate:audit-rules.service,auditd.service,bootloader-update.service,ceph-bootstrap.service,chronyd.service,coreos-populate-lvmdevices.service,coreos-printk-quiet.service,dev-binderfs.mount,fapolicyd.service,firewalld.service,gdm.service,nvidia-powerd.service,tuned.service,usbguard.service,waydroid-container.service"

    "mios-wsl2:avahi-daemon.service,avahi-daemon.socket,boot.mount,boot-complete.target,cloud-config.service,cloud-init-local.service,cloud-init-network.service,greenboot-healthcheck.service,qemu-guest-agent.service,rpm-ostree-fix-shadow-mode.service,stratisd.service,systemd-homed.service,systemd-logind.service,var-lib-nfs-rpc_pipefs.mount,virtlxcd.service,virtlxcd-admin.socket,virtlxcd-ro.socket,zincati.service"
)

count=0
for entry in "${GATES[@]}"; do
    gate_name="${entry%%:*}"
    units_csv="${entry#*:}"
    src="${DROPIN_SRC}/${gate_name}.conf"

    if [[ ! -f "$src" ]]; then
        echo "[mios-dropin-fanout] FATAL: canonical missing at $src" >&2
        exit 1
    fi

    IFS=',' read -ra units <<< "$units_csv"
    for unit in "${units[@]}"; do
        dropin_dir="${SYSTEMD_SYSTEM_DIR}/${unit}.d"
        dropin_file="${dropin_dir}/10-${gate_name}.conf"
        install -d -m 0755 "$dropin_dir"
        install -m 0644 "$src" "$dropin_file"
        count=$((count + 1))
    done
done

echo "[mios-dropin-fanout] fanned out $count drop-ins from ${#GATES[@]} canonical gates"
