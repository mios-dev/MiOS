#!/usr/bin/env bash
# MiOS Bootstrap -- Total Root Merge Mode
set -euo pipefail

DEFAULT_USER="mios"
DEFAULT_HOST="mios"
DEFAULT_USER_FULLNAME="MiOS User"
DEFAULT_USER_GROUPS="wheel,libvirt,kvm,video,render,input,dialout"
MIOS_REPO="https://github.com/mios-dev/MiOS.git"

log_info()  { printf '\033[36m[INFO]\033[0m %s\n' "$*"; }
log_ok()    { printf '\033[32m[ OK ]\033[0m %s\n' "$*"; }
log_err()   { printf '\033[31m[ERR ]\033[0m %s\n' "$*" >&2; }

require_root() { [[ $EUID -eq 0 ]] || { log_err "Must run as root"; exit 1; }; }

main() {
    require_root
    log_info "Starting MiOS Bootstrap..."

    # 1. User/Group handling (GRACEFUL)
    local existing_groups=""
    IFS=',' read -ra ADDR <<< "$DEFAULT_USER_GROUPS"
    for g in "${ADDR[@]}"; do
        getent group "$g" >/dev/null && { [[ -n "$existing_groups" ]] && existing_groups+=","; existing_groups+="$g"; }
    done

    if id -u "$DEFAULT_USER" >/dev/null 2>&1; then
        usermod -aG "$existing_groups" "$DEFAULT_USER"
    else
        useradd -m -G "$existing_groups" -s /bin/bash -c "$DEFAULT_USER_FULLNAME" "$DEFAULT_USER"
    fi
    log_ok "User configured with available groups: $existing_groups"

    # 2. Total Root Merge
    log_info "Merging MiOS repository onto / ..."
    [[ -d "/.git" ]] || git init /
    git -C / remote add origin "$MIOS_REPO" 2>/dev/null || git -C / remote set-url origin "$MIOS_REPO"
    git -C / fetch --depth=1 origin main
    git -C / checkout -f main
    log_ok "Root merge complete."

    # 3. System installer
    if [[ -x "/install.sh" ]]; then
        log_info "Running /install.sh ..."
        /install.sh
    fi
    log_ok "MiOS Installation Finished."
}

main "$@"
