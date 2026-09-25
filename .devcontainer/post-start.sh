#!/bin/bash
set -euo pipefail
echo "[devcontainer:post-start] Checking agentic environment and AI endpoint..."

# postCreateCommand only ever runs once per container lifetime, so a
# transient network failure there (e.g. agy's release-manifest endpoint
# unreachable at creation time) would otherwise never be retried. Re-check
# and self-heal on every start instead; best-effort, never fails the gate.
if ! command -v agy >/dev/null 2>&1; then
    echo "[devcontainer:post-start] agy missing; retrying install..."
    tmp="$(mktemp -d)"
    if bash /workspaces/MiOS/.devcontainer/fetch-installer.sh \
         https://antigravity.google/cli/install.sh "${tmp}/install.sh" \
       && bash "${tmp}/install.sh" >/dev/null 2>&1; then
        echo "[devcontainer:post-start] agy installed: $(agy --version 2>/dev/null || echo unknown)"
    else
        echo "[devcontainer:post-start] agy still unreachable; will retry next start"
    fi
    rm -rf "${tmp}"
fi

# The credential keyring is a process, so it is gone after every restart and
# agy re-asks for authentication without it. Best-effort, like the install above.
DEVLOOP_ENV=/workspaces/-dev-loop/skills/dev-loop/scripts/env
if [ -r "${DEVLOOP_ENV}/agy-keyring.sh" ]; then
    # shellcheck source=/dev/null
    . "${DEVLOOP_ENV}/agy-keyring.sh" || echo "[devcontainer:post-start] keyring not started; agy will ask to authenticate"
fi

# The verification gate must fail closed: a non-zero exit here fails
# postStartCommand and surfaces in the devcontainer UI/CLI. Do not mask this
# with `|| true` -- that turned every failing invariant into a silent pass.
python3 harness/verification_gates.py --quick

echo "[devcontainer:post-start] Ready for agent dispatch."
