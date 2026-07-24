#!/usr/bin/env bash
# AI-hint: Offline bare-metal installer for MiOS (CATREPO-01 kickstart integration). Performs bootc install to-disk --transport oci-archive from staged oci-archive on MiOS-Repo/MiOS-Data.
set -euo pipefail

DRY_RUN=0
TARGET_DISK=""
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

if [[ -z "$TARGET_DISK" ]]; then
    echo "[install.sh] Available disks:"
    lsblk -d -n -o NAME,SIZE,MODEL 2>/dev/null || true
    if (( DRY_RUN )); then
        TARGET_DISK="/dev/sda"
    fi
fi

if [[ -z "$TARGET_DISK" ]] && (( ! DRY_RUN )); then
    echo "[!] Target disk is required. Specify via --target-disk." >&2
    exit 1
fi

echo "[install.sh] Offline Bare-Metal Installer Plan (CATREPO-01):"
echo "  Target Disk: ${TARGET_DISK:-<none>}"
echo "  OCI Archive: $OCI_ARCHIVE"
echo "  Transport:   oci-archive"

if (( DRY_RUN )); then
    echo "[install.sh] DRY-RUN: Would execute -> bootc install to-disk --target-no-signature-verification --source-imgref \"oci-archive:$OCI_ARCHIVE\" \"${TARGET_DISK:-/dev/sda}\""
    exit 0
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "[!] Must run as root to perform bare-metal installation." >&2
    exit 1
fi

if [[ ! -f "$OCI_ARCHIVE" ]]; then
    echo "[!] Staged OCI archive not found at $OCI_ARCHIVE." >&2
    exit 1
fi

echo "WARNING: All data on $TARGET_DISK will be destroyed!"
read -rp "Type 'YES' to proceed: " CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
    echo "Installation cancelled."
    exit 0
fi

bootc install to-disk --target-no-signature-verification --source-imgref "oci-archive:$OCI_ARCHIVE" "$TARGET_DISK"
echo "[install.sh] Offline installation complete."
