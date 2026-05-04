#!/usr/bin/env bash
# /usr/libexec/mios/bootc-switch-from-build.sh
#
# Closes the self-replication loop on the host side. Triggered via
# mios-bootc-switch.path watching /var/lib/mios/forge-runner/last-build.txt:
# the Forgejo Runner workflow writes that file with the image ref of a
# freshly-built local image (typically `localhost/mios:latest`), and this
# script issues `bootc switch --transport containers-storage <ref>` so the
# next reboot lands on the new build via bootc's A/B swap.
#
# Privilege boundary: the runner container is Privileged=true (documented
# exception) for `podman build`, but it does NOT have direct access to the
# host's bootc tooling. By splitting the build (in the runner) from the
# switch (on the host, via this script triggered by a path watch), bootc
# privilege stays on the host where it belongs.
#
# Sentinel file format (written by .forgejo/workflows/build-mios.yml):
#   <ISO-8601 timestamp> <image-ref>
#   2026-05-03T23:42:18Z localhost/mios:latest
#
# Idempotent: re-running with the same ref is a no-op (bootc switch
# deduplicates internally; if the staged deployment already points at
# this ref, bootc returns 0).
set -euo pipefail

SENTINEL=/var/lib/mios/forge-runner/last-build.txt
LOG_TAG=mios-bootc-switch
_log() { logger -t "$LOG_TAG" "$*" 2>/dev/null || true; echo "[${LOG_TAG}] $*" >&2; }

# Refuse to do anything dangerous if the sentinel is missing -- the path
# unit only triggers on file events, but a manual invocation with no file
# present should fail loud rather than silently.
if [[ ! -r "$SENTINEL" ]]; then
    _log "ERROR: sentinel ${SENTINEL} missing or unreadable; nothing to switch to."
    exit 1
fi

# Sentinel format: "<timestamp> <image-ref>". Reject anything that doesn't
# parse cleanly so we never feed garbage to bootc.
read -r ts ref _ < "$SENTINEL" || true
if [[ -z "${ref:-}" ]]; then
    _log "ERROR: sentinel ${SENTINEL} missing image ref. Content was: $(cat "$SENTINEL")"
    exit 1
fi

# Refuse non-localhost refs unless explicitly opted in. The whole point
# of this loop is local self-replication; switching to a remote ref
# from a runner trigger is almost certainly a mistake. Operator can
# bypass with MIOS_BOOTC_ALLOW_REMOTE=1 if they really mean it.
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

# Verify the image actually exists in containers-storage before asking
# bootc to switch to it. A failed switch on a non-existent ref leaves
# the deployment in a half-staged state.
if ! podman image exists "$ref"; then
    _log "ERROR: image '${ref}' not found in containers-storage; refusing to switch."
    _log "       Last build sentinel may be stale. Re-run the workflow or remove ${SENTINEL}."
    exit 1
fi

# Stage the new deployment. `bootc switch` writes the ref into the
# bootc state store and prepares an A/B deployment for the next boot.
# It does NOT reboot.
if ! bootc switch --transport containers-storage "$ref" 2>&1 | tee -a /var/log/mios-bootc-switch.log; then
    _log "ERROR: bootc switch failed; deployment unchanged."
    exit 1
fi

_log "[ok] staged ${ref} for next boot."
_log "Reboot to activate: 'sudo systemctl reboot' (or 'sudo bootc upgrade --apply' if you want bootc to handle it)."

# Drop a marker so operators can see in `mios-status` (if installed) what
# the last successful switch was.
install -d -m 0755 /var/lib/mios
{ printf '%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$ts" "$ref"; } >> /var/lib/mios/bootc-switch-history.tsv
chmod 0644 /var/lib/mios/bootc-switch-history.tsv

exit 0
