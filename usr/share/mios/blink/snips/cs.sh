#!/bin/bash
# AI-hint: Blink Shell snip script for launching and connecting to GitHub Codespaces visual web and terminal dev environments for MiOS.
# AI-related: /usr/share/doc/mios/guides/blinkshell-codespaces-cloudshell.md, /usr/share/mios/tmux/blink-mobile-keys.tmux.conf
# AI-functions: main, connect_web, connect_ssh

set -euo pipefail

readonly REPO_URL="https://github.com/mios-dev/MiOS"
readonly CODESPACES_NEW_URL="https://github.com/codespaces/new?repo=mios-dev/MiOS"
readonly GITHUB_DEV_URL="https://github.dev/mios-dev/MiOS"

connect_web() {
    local target="${1:-new}"
    echo "[blink-cs] Opening visual Codespaces environment..."
    if [[ "${target}" == "dev" ]]; then
        # Opens lightweight in-browser editor
        if command -v open >/dev/null 2>&1; then
            open "${GITHUB_DEV_URL}"
        elif command -v code >/dev/null 2>&1; then
            code "${GITHUB_DEV_URL}"
        else
            printf '%s\n' "${GITHUB_DEV_URL}"
        fi
    else
        # Opens full compute container codespace
        if command -v open >/dev/null 2>&1; then
            open "${CODESPACES_NEW_URL}"
        elif command -v code >/dev/null 2>&1; then
            code "${CODESPACES_NEW_URL}"
        else
            printf '%s\n' "${CODESPACES_NEW_URL}"
        fi
    fi
}

connect_ssh() {
    local name="${1:-}"
    if command -v gh >/dev/null 2>&1; then
        if [[ -n "${name}" ]]; then
            echo "[blink-cs] Connecting to Codespace '${name}' via SSH..."
            gh cs ssh -c "${name}" -- -t "tmux -f /usr/share/mios/tmux/blink-mobile-keys.tmux.conf new-session -A -s mios"
        else
            echo "[blink-cs] Selecting Codespace to attach..."
            gh cs ssh -- -t "tmux -f /usr/share/mios/tmux/blink-mobile-keys.tmux.conf new-session -A -s mios"
        fi
    else
        echo "[blink-cs] gh CLI not found in Blink environment. Opening web IDE..."
        connect_web "new"
    fi
}

main() {
    local mode="${1:-web}"
    case "${mode}" in
        web|ide)
            connect_web "${2:-new}"
            ;;
        ssh|term)
            connect_ssh "${2:-}"
            ;;
        help|--help|-h)
            echo "Usage: snip cs [web|ssh] [target]"
            echo "  web [new|dev]  - Open visual Codespaces editor in Blink (default)"
            echo "  ssh [name]      - Attach to Codespace SSH with Blink mobile keys"
            ;;
        *)
            connect_web "${mode}"
            ;;
    esac
}

main "$@"
