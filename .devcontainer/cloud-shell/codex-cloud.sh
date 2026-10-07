#!/bin/bash
# AI-hint: Codex Cloud installation and startup using the canonical Fedora MiOS devcontainer, its lifecycle, SSOT dependencies and an unprivileged mios-dev command wrapper. Incomplete provisioning fails closed.
# AI-related: README.md, .devcontainer/devcontainer.json, .devcontainer/Containerfile, usr/share/mios/mios.toml
# AI-functions: main, install_host, find_source, write_wrapper, start, check

set -euo pipefail

readonly CACHE=/opt/mios-codex-cloud
readonly CLI="$CACHE/cli/node_modules/.bin/devcontainer"

install_host() {
    [[ $EUID == 0 ]] || { echo 'Run the install script as root (or with sudo).' >&2; return 1; }
    if ! command -v podman >/dev/null || ! command -v npm >/dev/null || ! command -v git >/dev/null || ! command -v python3 >/dev/null; then
        . /etc/os-release
        case "$ID" in
            fedora) dnf install -y podman git curl nodejs npm python3 ;;
            ubuntu|debian) apt-get update && apt-get install -y podman git curl nodejs npm python3 ;;
            *) echo "Unsupported cloud control host: $ID; supply Podman, Git, curl, Node/npm and Python." >&2; return 1 ;;
        esac
    fi
    podman info >/dev/null
    install -d -m 0755 "$CACHE/cli" /usr/local/libexec
    npm install --prefix "$CACHE/cli" @devcontainers/cli
    local copy="$CACHE/codex-cloud.sh.new"
    install -m 0755 "${BASH_SOURCE[0]}" "$copy"
    mv -f "$copy" /usr/local/libexec/mios-codex-cloud
}

find_source() {
    local candidate root cloud_uid="${MIOS_UID:-1000}" cloud_gid="${MIOS_GID:-1000}"
    candidate="${MIOS_ROOT:-}"
    if [[ -z "$candidate" ]]; then
        local detected probe
        detected="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
        for probe in "$detected" "$detected/MiOS" "$(dirname "$detected")/MiOS"; do
            if [[ -f "$probe/usr/share/mios/mios.toml" ]]; then candidate="$probe"; break; fi
        done
    fi
    if [[ -z "$candidate" && -r "$CACHE/source-root" ]]; then candidate="$(cat "$CACHE/source-root")"; fi
    if [[ -z "$candidate" ]]; then
        candidate="$CACHE/source/MiOS"
        if [[ ! -e "$candidate" ]]; then
            git clone --depth 1 --branch main https://github.com/mios-dev/MiOS.git "$candidate"
            chown -R "$cloud_uid:$cloud_gid" "$candidate"
        fi
    fi
    root="$(cd "$candidate" && pwd -P)"
    [[ -f "$root/usr/share/mios/mios.toml" && -f "$root/.devcontainer/devcontainer.json" ]] \
        || { echo "MIOS_ROOT must identify the MiOS system checkout: $root" >&2; return 1; }
    printf '%s\n' "$root" > "$CACHE/source-root.new"
    mv -f "$CACHE/source-root.new" "$CACHE/source-root"
}

write_wrapper() {
    local temporary="$CACHE/mios-dev.new"
    cat > "$temporary" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
cache=/opt/mios-codex-cloud
root="$(cat "$cache/source-root")"
args=(exec --docker-path podman --workspace-folder "$root" --config "$root/.devcontainer/devcontainer.json")
# Translate checkout paths; otherwise use the canonical primary repository.
workdir="$(awk -F '\t' '$1 == "MiOS" {print $2}' "$cache/workspace-mounts")"
[[ -n "$workdir" ]] || { echo 'MiOS workspace mapping is missing.' >&2; exit 1; }
primary="$workdir"
if [[ "$PWD" == "$root" || "$PWD" == "$root/"* ]]; then
    workdir="$primary${PWD#"$root"}"
else
    parent="$(dirname "$root")"
    while IFS=$'\t' read -r name target; do
        source="$parent/$name"
        if [[ "$PWD" == "$source" || "$PWD" == "$source/"* ]]; then workdir="$target${PWD#"$source"}"; break; fi
    done < "$cache/workspace-mounts"
fi
[[ $# -gt 0 ]] || set -- /bin/bash --login
exec "$cache/cli/node_modules/.bin/devcontainer" "${args[@]}" -- bash -c 'cd "$1" || exit; shift; exec "$@"' mios-dev "$workdir" "$@"
WRAPPER
    chmod 0755 "$temporary"
    mv -f "$temporary" /usr/local/bin/mios-dev
}

start() {
    [[ -x "$CLI" ]] || { echo 'MiOS cloud install has not completed.' >&2; return 1; }
    podman info >/dev/null
    find_source
    local root repo source target
    root="$(cat "$CACHE/source-root")"
    local args=(up --docker-path podman --workspace-folder "$root" --config "$root/.devcontainer/devcontainer.json" --update-remote-user-uid-default off)
    # Preserve selected sibling checkouts rather than replacing them with clones.
    local mounts="$CACHE/workspace-mounts"
    python3 - "$root" > "$mounts.new" <<'PY'
import json, os, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1])
get = [sys.executable, str(root/'usr/libexec/mios/mios-toml-get'), '--vendor', 'workspace']
env = {**os.environ, 'MIOS_TOML_ROOT':str(root)}
base = subprocess.check_output([*get, 'root'], env=env, text=True).strip()
repos = json.loads(subprocess.check_output([*get, 'repos'], env=env, text=True))
for repo in repos:
    print(repo['name'] + '\t' + str(pathlib.Path(base)/repo['name']))
PY
    mv -f "$mounts.new" "$mounts"
    while IFS=$'\t' read -r repo target; do
        [[ "$repo" != MiOS ]] || continue
        source="$(dirname "$root")/$repo"
        [[ -d "$source" ]] || continue
        [[ "$source" != *,* && "$target" != *,* ]] || { echo 'Mount paths must not contain commas.' >&2; return 1; }
        args+=(--mount "type=bind,source=$source,target=$target")
    done < "$mounts"
    "$CLI" "${args[@]}"
    write_wrapper
    mios-dev bash -lc 'mios-agent-pipe-dev start && /usr/lib/mios/mcp/.venv/bin/python3 /usr/libexec/mios/mios-mcp-server --project-agent-clients'
    check
}

check() {
    mios-dev bash -lc '
set -euo pipefail
. /etc/os-release
[[ "$ID" == fedora ]] || { echo "MiOS requires Fedora userspace, got $ID" >&2; exit 1; }
[[ "$(id -u)" != 0 ]] || { echo "MiOS tasks must run unprivileged" >&2; exit 1; }
test -r /usr/share/mios/mios.toml
test -x /usr/libexec/mios/mios-agent-relay
tmux -V
oh-my-posh --version
/usr/libexec/mios/mios-gen render-tmux-theme --runtime "${XDG_CACHE_HOME:-$HOME/.cache}/mios-cloud-theme"
mios agents
python3 - <<"PY"
import json, subprocess
catalog = json.loads(subprocess.check_output(["mios", "agents"], text=True))
for row in catalog["agents"]:
    subprocess.run([row["executable"], "--version"], check=True, timeout=30)
PY
mios-agent-pipe-dev check
echo "MiOS Fedora userspace, SSOT theme, agent catalog and gateway checks passed."
'
}

main() {
    case "${1:-install}" in
        install) install_host; find_source; start ;;
        start) start ;;
        check) check ;;
        --help|-h) echo 'Usage: codex-cloud.sh [install|start|check]' ;;
        *) echo 'Usage: codex-cloud.sh [install|start|check]' >&2; return 2 ;;
    esac
}

main "$@"
