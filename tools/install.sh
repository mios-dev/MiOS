#!/usr/bin/env bash
# MIOS_INSTALLER_ROLE=bootc-baremetal-disk-installer
# AI-hint: Offline bare-metal installer for MiOS: installs the staged oci-archive on MiOS-Repo through mios-install, tracking [image].ref for upgrades.
set -euo pipefail

DRY_RUN=0
TARGET_DISK=""
REPO_DEV="$(blkid -L "MiOS-Repo" 2>/dev/null || true)"
if [[ -n "$REPO_DEV" ]]; then
    mkdir -p /mnt/mios-repo
    mount "$REPO_DEV" /mnt/mios-repo 2>/dev/null || true
fi
OCI_ARCHIVE="${MIOS_OCI_ARCHIVE:-/mnt/mios-repo/mios-latest.tar}"

usage() {
    cat <<EOF
Usage: $0 [options]
Options:
  --target-disk DISK   Target disk (e.g. /dev/sda, /dev/nvme0n1)
  --oci-archive PATH   Path to staged oci-archive (default: $OCI_ARCHIVE)
  --dry-run            Print execution plan without making changes
  --help               Show this help message
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-disk) TARGET_DISK="$2"; shift 2 ;;
        --oci-archive) OCI_ARCHIVE="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --help) usage ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# The installed host tracks [image].ref, not this archive (ADR-0014).
MIOS_INSTALL="${MIOS_INSTALL_BIN:-$(command -v mios-install || true)}"
if [[ -z "$MIOS_INSTALL" ]]; then
    echo "[!] mios-install is not installed on this live system" >&2
    exit 1
fi

if [[ -z "$TARGET_DISK" ]]; then
    echo "[install.sh] Available disks:"
    lsblk -d -n -o NAME,SIZE,MODEL 2>/dev/null || true
    echo "[!] Target disk is required. Specify via --target-disk" >&2
    exit 1
fi

args=(disk --target-disk "$TARGET_DISK" --source "oci-archive:$OCI_ARCHIVE")

if (( DRY_RUN )); then
    exec "$MIOS_INSTALL" "${args[@]}" --dry-run
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "[!] Must run as root to perform bare-metal installation" >&2
    exit 1
fi

if [[ ! -f "$OCI_ARCHIVE" ]]; then
    echo "[!] Staged OCI archive not found at $OCI_ARCHIVE" >&2
    exit 1
fi

echo "WARNING: All data on $TARGET_DISK will be destroyed"
read -rp "Type 'YES' to proceed: " CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
    echo "Installation cancelled"
    exit 0
fi

"$MIOS_INSTALL" "${args[@]}" --yes
echo "[install.sh] Offline installation complete"
