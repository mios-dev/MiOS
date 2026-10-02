#!/bin/bash
# AI-hint: Claude Code cloud environment Setup script for MiOS: builds the MiOS dev image (the Codespaces .devcontainer) under podman from main, installs mios-dev and the dev-loop plugin, always exits 0.
# AI-related: /usr/share/mios/templates/bash, .devcontainer/Containerfile, .devcontainer/devcontainer.json, .devcontainer/cloud-shell/README.md
# AI-functions: main
#
# The environment's Setup script field fetches this file from MiOS main and
# runs it (see README.md beside it), so a change here reaches the next new
# session without re-pasting anything.
#
# Cloud setup-script contract: runs as root before Claude Code starts, must
# exit 0, and should finish inside about five minutes or the environment
# cache is not saved. No `set -e`: every step is guarded and a failure leaves
# a plain session with a log line, never a failed one.

main() {
    local toolkit=/opt/dev-loop
    local toolkit_repo=https://github.com/mios-dev/-dev-loop

    # The engineering-loop toolkit is generic: it is the plugin
    # (CLAUDE_CODE_PLUGIN_DIRS) and it owns the devcontainer projection. MiOS
    # supplies only the values below.
    # A cache, not a workspace: it always lands on main, shallow or not.
    if [ -d "$toolkit/.git" ]; then
        { git -C "$toolkit" fetch -q --depth 1 origin main && git -C "$toolkit" reset -q --hard FETCH_HEAD; } \
            || echo "[mios-cloud] toolkit update failed; using the cached checkout"
    else
        git clone -q --depth 1 "$toolkit_repo" "$toolkit" || { echo "[mios-cloud] toolkit clone failed; no MiOS dev image this session"; return 0; }
    fi

    # The MiOS dev image is MiOS's own .devcontainer: built from main, never a
    # branch, under podman (MiOS is podman-native; the VM ships Docker only,
    # so the projection installs podman and refuses to fall back to Docker).
    export FEDORA_DEVCONTAINER_REPO="${FEDORA_DEVCONTAINER_REPO:-https://github.com/mios-dev/MiOS}"
    export FEDORA_DEVCONTAINER_REF="${FEDORA_DEVCONTAINER_REF:-main}"
    export FEDORA_DEVCONTAINER_FILE="${FEDORA_DEVCONTAINER_FILE:-.devcontainer/Containerfile}"
    export FEDORA_DEVCONTAINER_NAME="${FEDORA_DEVCONTAINER_NAME:-mios-dev}"
    export FEDORA_IMAGE="${FEDORA_IMAGE:-mios-dev:latest}"
    export FEDORA_CONTAINER="${FEDORA_CONTAINER:-mios-dev}"
    export FEDORA_RUNTIME="${FEDORA_RUNTIME:-podman}"
    # Past this many seconds the devcontainer lifecycle (post-create) is
    # deferred so the setup stays inside the cache budget; `mios-dev` then
    # reports it and `cloud-fedora-setup.sh --lifecycle` applies it.
    export FEDORA_SETUP_BUDGET_S="${FEDORA_SETUP_BUDGET_S:-240}"

    bash "$toolkit/skills/dev-loop/scripts/env/cloud-fedora-setup.sh" || echo "[mios-cloud] projection exited non-zero; see /var/log/dev-loop-fedora-build.log"
}

main "$@"
exit 0
