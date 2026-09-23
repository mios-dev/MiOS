#!/bin/bash
# AI-hint: Blink Shell snip script for launching MiOS visual web environments including Open WebUI, Code-Server, Cockpit, and Guacamole.
# AI-related: /usr/share/doc/mios/guides/blinkshell-codespaces-cloudshell.md, usr/share/containers/systemd/mios-open-webui.container
# AI-functions: main, open_target

set -euo pipefail

readonly OWUI_PORT=8080
readonly CODE_SERVER_PORT=8443
readonly COCKPIT_PORT=9090
readonly GUACAMOLE_PORT=8088

open_target() {
    local target="${1:-owui}"
    local host="${2:-localhost}"
    local url=""

    case "${target}" in
        owui|ai)
            url="http://${host}:${OWUI_PORT}"
            ;;
        code|vscode)
            url="http://${host}:${CODE_SERVER_PORT}"
            ;;
        cockpit|admin)
            url="https://${host}:${COCKPIT_PORT}"
            ;;
        desktop|guacamole)
            url="http://${host}:${GUACAMOLE_PORT}"
            ;;
        *)
            url="http://${host}:${target}"
            ;;
    esac

    echo "[blink-mios-web] Opening visual surface: ${url}"
    if command -v open >/dev/null 2>&1; then
        open "${url}"
    elif command -v code >/dev/null 2>&1; then
        code "${url}"
    else
        printf '%s\n' "${url}"
    fi
}

main() {
    local surface="${1:-owui}"
    local host="${2:-localhost}"

    case "${surface}" in
        help|--help|-h)
            echo "Usage: snip mios-web [owui|code|cockpit|desktop] [host]"
            echo "  owui     - Open WebUI AI interface (:8080)"
            echo "  code     - Visual Code-Server web IDE (:8443)"
            echo "  cockpit  - System Cockpit administrator (:9090)"
            echo "  desktop  - Guacamole web desktop (:8088)"
            ;;
        *)
            open_target "${surface}" "${host}"
            ;;
    esac
}

main "$@"
