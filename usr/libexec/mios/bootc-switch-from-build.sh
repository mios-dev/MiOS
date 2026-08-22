# AI-hint: !/usr/bin/env bash Executes `bootc switch` to update the active system partition to a local image (e.g., `localhost/mios:latest`) by parsing the `l...
# AI-doc: usr/share/doc/mios/manual/_harvest/usr_libexec_mios_bootc_switch_from_build_sh.md
set -euo pipefail

SENTINEL=/var/lib/mios/forge-runner/last-build.txt
LOG_TAG=mios-bootc-switch
_log() { logger -t "$LOG_TAG" "$*" 2>/dev/null || true; echo "[${LOG_TAG}] $*" >&2; }

if command -v miosd >/dev/null 2>&1; then
    miosd bootc-apply --sentinel "$SENTINEL"
    exit 0
fi

if [[ ! -r "$SENTINEL" ]]; then
    _log "ERROR: sentinel ${SENTINEL} missing or unreadable; nothing to switch to."
    exit 1
fi

read -r ts ref _ < "$SENTINEL" || true
if [[ -z "${ref:-}" ]]; then
    _log "ERROR: sentinel ${SENTINEL} missing image ref. Content was: $(cat "$SENTINEL")"
    exit 1
fi

case "$ref" in
    localhost/*) ;;
    *)
        if [[ "${MIOS_BOOTC_ALLOW_REMOTE:-0}" != "1" ]]; then
            _log "ERROR: refusing non-localhost ref '${ref}' (set MIOS_BOOTC_ALLOW_REMOTE=1 to bypass)"
            exit 1
        fi
        ;;
esac

_log "build sentinel: ts=${ts} ref=${ref}"

if ! podman image exists "$ref"; then
    _log "ERROR: image '${ref}' not found in containers-storage; refusing to switch."
    _log "       Last build sentinel may be stale. Re-run the workflow or remove ${SENTINEL}."
    exit 1
fi

if ! bootc switch --transport containers-storage "$ref" 2>&1 | tee -a /var/log/mios-bootc-switch.log; then
    _log "ERROR: bootc switch failed; deployment unchanged."
    exit 1
fi

_log "[ok] staged ${ref} for next boot."
_log "Reboot to activate: 'sudo systemctl reboot' (or 'sudo bootc upgrade --apply' if you want bootc to handle it)."

install -d -m 0755 /var/lib/mios
{ printf '%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$ts" "$ref"; } >> /var/lib/mios/bootc-switch-history.tsv
chmod 0644 /var/lib/mios/bootc-switch-history.tsv

exit 0
