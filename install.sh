#!/usr/bin/env bash
#
# CANONICAL ENTRY POINT NOTICE (v0.2.4+):
# The user-facing end-to-end pipeline now lives at `./mios-pipeline.sh`
# (11 phases: Questions -> Stage -> MiOS-DEV -> Overlay -> Account ->
# Install -> Smoketest -> Build -> Deploy -> Boot -> Repeat). This
# script is invoked BY mios-pipeline.sh as the worker for Phase 9
# (Deploy) and remains fully functional standalone. Operator
# automation should call mios-pipeline.sh instead of install.sh
# directly; calling install.sh still works but skips Phases 1-8.
#
# 'MiOS' system-side installer -- runs as the system-init half of Phase-3
# (Apply). Invoked by mios-bootstrap.git/install.sh after Phase-1 (overlay)
# and Phase-2 (package install) have already completed.
#
# Refuses to run on bootc-managed hosts (their /usr is read-only composefs);
# on bootc, Phase-2/3 are handled by `bootc switch`.
#
# What this script does (Phase-3 system-init responsibilities):
#   1. Lay down any remaining FHS overlay rsyncs from this repository's
#      working tree to / (idempotent if bootstrap already merged via git).
#   2. systemd-sysusers (creates mios + sidecar service accounts).
#   3. systemd-tmpfiles --create (declares /var/, /run/, /etc/cdi paths).
#   4. systemctl daemon-reload + enable 'MiOS' services.

set -euo pipefail

# Acknowledgment banner (sourced; informational; respects
# MIOS_AGREEMENT_BANNER=quiet and MIOS_REQUIRE_AGREEMENT_ACK=1).
_repo_root_for_banner="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=automation/lib/agreements-banner.sh
[[ -r "${_repo_root_for_banner}/automation/lib/agreements-banner.sh" ]] && \
    . "${_repo_root_for_banner}/automation/lib/agreements-banner.sh" && \
    mios_print_agreement_banner "install.sh"
unset _repo_root_for_banner

# Refuse to run on bootc-managed hosts.
if command -v bootc >/dev/null 2>&1 && bootc status --format=json 2>/dev/null | grep -q '"booted"'; then
    echo "[FAIL] This host is bootc-managed. install.sh is for non-bootc Fedora hosts." >&2
    echo "       Use 'sudo bootc switch ghcr.io/MiOS-DEV/mios:latest' instead." >&2
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "[FAIL] install.sh must run as root: sudo $0" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[INFO] Phase-3 -- 'MiOS' system installer running from ${REPO_ROOT}"

if [[ "${REPO_ROOT}" != "/" ]]; then
    # Apply FHS overlay. We rsync each top-level overlay dir if it exists.
    for d in usr etc var srv; do
        if [[ -d "${REPO_ROOT}/${d}" ]]; then
            echo "[INFO] Applying overlay: ${d}/"
            rsync -aH --info=stats1 "${REPO_ROOT}/${d}/" "/${d}/"
        fi
    done

    # v1/ holds discovery symlinks; we materialize them at /v1.
    if [[ -d "${REPO_ROOT}/v1" ]]; then
        echo "[INFO] Materializing /v1 discovery surface"
        install -d /v1
        rsync -aH "${REPO_ROOT}/v1/" "/v1/"
    fi
else
    echo "[INFO] Running directly from root (/), skipping overlay sync."
fi
echo "[INFO] Running systemd-sysusers"
systemd-sysusers

echo "[INFO] Running systemd-tmpfiles"
systemd-tmpfiles --create

echo "[INFO] Reloading systemd"
systemctl daemon-reload

echo "[INFO] Enabling 'MiOS' services"
if [[ -f /etc/containers/systemd/mios-ai.container ]]; then
    systemctl enable --now mios-ai.service || echo "[WARN] mios-ai.service not yet active; will retry on boot"
fi

echo "[ OK ] Phase-3 -- 'MiOS' system installer complete."
echo "       Control returns to mios-bootstrap install.sh for Phase-3 user"
echo "       staging and Phase-4 reboot prompt."
