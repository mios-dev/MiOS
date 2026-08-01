#!/usr/bin/bash
# AI-hint: Enrolls the MiOS Secure Boot MOK certificate using mokutil, handling variant-specific keys and idempotency checks to ensure the system's boot chain is signed and trusted.
# AI-functions: log, status_probe, pick_key
set -euo pipefail

STATUS_ONLY=0
KEY_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --status)  STATUS_ONLY=1; shift ;;
        --key)     KEY_OVERRIDE="$2"; shift 2 ;;
        -*)        echo "Unknown option: $1" >&2; exit 1 ;;
        *)         break ;;
    esac
done

LOG_DIR=/var/log/mios
LOG_FILE="${LOG_DIR}/mok-enroll-$(date -u +%Y%m%dT%H%M%SZ).log"
install -d -m 0750 "$LOG_DIR"

log() {
    local msg="[mok-enroll] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

status_probe() {
    if ! command -v mokutil >/dev/null 2>&1; then
        echo "No-secureboot"
        return
    fi
    local sb_state
    sb_state=$(mokutil --sb-state 2>/dev/null || true)
    if echo "$sb_state" | grep -qi "SecureBoot disabled"; then
        echo "No-secureboot"
        return
    fi

    local key_path
    key_path=$(pick_key)
    if [[ -z "$key_path" ]]; then
        echo "Not-enrolled"
        return
    fi

    local fingerprint
    fingerprint=$(openssl x509 -inform DER -in "$key_path" -fingerprint -sha256 -noout 2>/dev/null | sed 's/.*=//') || {
        echo "Error"
        return
    }

    local enrolled_fps
    enrolled_fps=$(mokutil --list-enrolled 2>/dev/null | grep -i "SHA256 Fingerprint" | sed 's/.*: //' | tr -d ':' | tr '[:upper:]' '[:lower:]' || true)
    local pending_fps
    pending_fps=$(mokutil --list-new 2>/dev/null | grep -i "SHA256 Fingerprint" | sed 's/.*: //' | tr -d ':' | tr '[:upper:]' '[:lower:]' || true)
    local target_fp
    target_fp=$(echo "$fingerprint" | tr -d ':' | tr '[:upper:]' '[:lower:]')

    if echo "$enrolled_fps" | grep -qF "$target_fp"; then
        echo "Enrolled"
    elif echo "$pending_fps" | grep -qF "$target_fp"; then
        echo "Pending"
    else
        local key_cn
        key_cn=$(openssl x509 -inform DER -in "$key_path" -subject -noout 2>/dev/null | sed 's/.*CN\s*=\s*//' | cut -d'/' -f1 || true)
        if [[ -n "$key_cn" ]]; then
            local enrolled_subjects
            enrolled_subjects=$(mokutil --list-enrolled 2>/dev/null || true)
            if echo "$enrolled_subjects" | grep -qF "$key_cn"; then
                echo "Conflict"
                return
            fi
        fi
        echo "Not-enrolled"
    fi
}

pick_key() {
    if [[ -n "$KEY_OVERRIDE" ]]; then
        echo "$KEY_OVERRIDE"
        return
    fi
    [[ -f /etc/pki/mios/mok.der ]] && { echo /etc/pki/mios/mok.der; return; }
    [[ -f /etc/pki/akmods/certs/akmods-ublue.der ]] && { echo /etc/pki/akmods/certs/akmods-ublue.der; return; }
    echo ""
}


if (( STATUS_ONLY == 1 )); then
    status_probe
    exit 0
fi


log "=== 'MiOS' MOK Enrollment ==="

if ! command -v mokutil >/dev/null 2>&1; then
    log "Mokutil not found"
    exit 1
fi

sb_state=$(mokutil --sb-state 2>/dev/null || true)
if echo "$sb_state" | grep -qi "SecureBoot disabled"; then
    log "Secure Boot is disabled"
    exit 0
fi
log "Secure Boot state: $sb_state"

KEY=$(pick_key)
if [[ -z "$KEY" ]]; then
    log "No MOK key found. Generate one with:"
    log "  sudo automation/generate-mok-key.sh"
    exit 2
fi
log "Using key: $KEY"

FINGERPRINT=$(openssl x509 -inform DER -in "$KEY" -fingerprint -sha256 -noout | sed 's/.*=//') || {
    log "Cannot read key fingerprint from $KEY"
    exit 1
}
log "Key fingerprint: $FINGERPRINT"

CURRENT_STATUS=$(status_probe)
log "Current status: $CURRENT_STATUS"

case "$CURRENT_STATUS" in
    enrolled)
        log "Key already enrolled"
        exit 0
        ;;
    pending)
        log "Key already queued for enrollment"
        exit 0
        ;;
    conflict)
        log "ERROR: A key with the same CN is already enrolled but with a different fingerprint"
        log "This indicates a key rotation. Manual steps required:"
        log "  1. mokutil"
        log "  2. Reboot and complete deletion in MokManager"
        log "  3. Re-run this script"
        exit 3
        ;;
    no-secureboot)
        log "Secure Boot appears disabled"
        exit 0
        ;;
esac


log "Queuing $KEY for MOK enrollment"
log ""
log "You will be prompted to confirm using the system root password"
log "On next reboot, MokManager will ask for this same password"
log ""

if ! mokutil --import "$KEY" --root-pw; then
    log "Mokutil"
    log "Attempting to revoke pending import"
    mokutil --revoke-import "$KEY" 2>/dev/null || log "Revoke-import also failed"
    exit 1
fi

mokutil --timeout 10 2>/dev/null || log "Note:"

log ""
log "[ok] Key queued for enrollment"
log ""
log "NEXT STEPS:"
log "  1. Reboot the system"
log "  2. In MokManager, choose 'Enroll MOK' and enter the root password"
log "  3. Reboot again. The key will be active"
log ""
log "── TPM2 WARNING ────────────────────────────────────────────────────────────"
log "If you have LUKS volumes sealed to TPM2 PCR 7,"
log "Every MOK mutation changes PCR 7 and WILL break automatic unlock"
log "After this reboot completes enrollment, re-seal with:"
log "  systemd-cryptenroll"
log "  systemd-cryptenroll"
log "────────────────────────────────────────────────────────────────────────────"
log ""
log "Full log: $LOG_FILE"
