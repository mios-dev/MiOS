#!/bin/bash
# AI-hint: Blink Shell snip script for launching and connecting to Google Cloud Shell visual web IDE and container dev environments for MiOS.
# AI-related: /usr/share/doc/mios/guides/blinkshell-codespaces-cloudshell.md, .devcontainer/cloud-shell/bootstrap.sh
# AI-functions: main, connect_web, connect_ssh

set -euo pipefail

readonly CLOUD_SHELL_IDE_URL="https://shell.cloud.google.com/?show=ide&cloudshell_git_repo=https://github.com/mios-dev/MiOS"
readonly CLOUD_SHELL_TERMINAL_URL="https://shell.cloud.google.com/?cloudshell_git_repo=https://github.com/mios-dev/MiOS"

connect_web() {
    local target="${1:-ide}"
    local url="${CLOUD_SHELL_IDE_URL}"
    if [[ "${target}" == "term" || "${target}" == "shell" ]]; then
        url="${CLOUD_SHELL_TERMINAL_URL}"
    fi

    echo "[blink-gcp] Opening Google Cloud Shell visual web environment..."
    if command -v open >/dev/null 2>&1; then
        open "${url}"
    elif command -v code >/dev/null 2>&1; then
        code "${url}"
    else
        printf '%s\n' "${url}"
    fi
}

connect_ssh() {
    if command -v gcloud >/dev/null 2>&1; then
        echo "[blink-gcp] Connecting to Google Cloud Shell via gcloud SSH..."
        gcloud cloud-shell ssh --authorize-session --ssh-flag="-t" --ssh-flag="bash -l -c 'tmux -f /usr/share/mios/tmux/blink-mobile-keys.tmux.conf new-session -A -s mios || bash -l'"
    else
        echo "[blink-gcp] gcloud not available directly in Blink Shell. Opening Cloud Shell Editor..."
        connect_web "ide"
    fi
}

main() {
    local mode="${1:-web}"
    case "${mode}" in
        web|ide)
            connect_web "ide"
            ;;
        term|shell)
            connect_web "term"
            ;;
        ssh)
            connect_ssh
            ;;
        help|--help|-h)
            echo "Usage: snip gcp [web|term|ssh]"
            echo "  web   - Open visual Cloud Shell IDE in Blink (default)"
            echo "  term  - Open Google Cloud Shell in web terminal mode"
            echo "  ssh   - Connect directly to Cloud Shell SSH instance"
            ;;
        *)
            connect_web "${mode}"
            ;;
    esac
}

main "$@"
