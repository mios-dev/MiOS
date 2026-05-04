#!/usr/bin/env bash
# /usr/libexec/mios/mios-dashboard.sh
#
# MiOS live system dashboard. Renders to ANY tty -- detects color
# capability, degrades to plain ASCII on tty0 / `linux` console where
# unicode + 24-bit color may not render cleanly.
#
# Modes:
#   default          : header + fastfetch + services + loop hint
#   --services-only  : just the services + loop block (used by
#                      fastfetch as a custom command-module)
#   --no-color       : strip all ANSI escape codes
#
# Entry points:
#   - /etc/profile.d/zz-mios-motd.sh runs the default mode at every
#     interactive shell login (deduped per-session via $MIOS_MOTD_SHOWN).
#   - fastfetch's /usr/share/mios/fastfetch/config.jsonc invokes
#     `--services-only --no-color` as a custom module so the loop
#     status sits inline with the standard fastfetch system info.
#   - Operators can run /usr/libexec/mios/mios-dashboard.sh manually
#     any time to refresh the view.
#
# Never aborts -- intentionally NOT using `set -e` so a missing
# command (e.g. systemctl when running outside systemd) only skips
# its own line rather than killing the whole login motd.

set -uo pipefail

# ── Mode + color detection ────────────────────────────────────────────────────
MODE="default"
NO_COLOR=0
for arg in "$@"; do
    case "$arg" in
        --services-only) MODE="services-only" ;;
        --no-color)      NO_COLOR=1 ;;
        --help|-h)
            sed -n '/^# /,/^$/{s/^# \?//;p}' "$0" | head -30
            exit 0
            ;;
    esac
done

# tty0 / `linux` console + dumb terminals: no color, ASCII fallback.
if [[ -z "${TERM:-}" ]] || [[ "$TERM" == "linux" ]] || [[ "$TERM" == "dumb" ]]; then
    NO_COLOR=1
fi
[[ ! -t 1 ]] && NO_COLOR=1

if [[ $NO_COLOR -eq 0 ]]; then
    C_R=$'\033[0m'; C_B=$'\033[1m'; C_D=$'\033[2m'
    C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YLW=$'\033[33m'
    C_BLU=$'\033[34m'; C_MGT=$'\033[35m'; C_CYN=$'\033[36m'
    C_GRY=$'\033[90m'
    DOT_UP="●"; DOT_DOWN="○"; DOT_FAIL="✗"; DOT_WAIT="◌"
    HR="═"; VR="║"; CORNER_TL="╔"; CORNER_TR="╗"; CORNER_BL="╚"; CORNER_BR="╝"
else
    C_R=""; C_B=""; C_D=""
    C_RED=""; C_GRN=""; C_YLW=""; C_BLU=""; C_MGT=""; C_CYN=""; C_GRY=""
    DOT_UP="*"; DOT_DOWN="-"; DOT_FAIL="x"; DOT_WAIT="."
    HR="="; VR="|"; CORNER_TL="+"; CORNER_TR="+"; CORNER_BL="+"; CORNER_BR="+"
fi

# Identity from install.env (written by mios-bootstrap at install time).
MIOS_VERSION=""
MIOS_AI_MODEL=""
MIOS_LINUX_USER="${USER:-mios}"
if [[ -r /etc/mios/install.env ]]; then
    # shellcheck disable=SC1091
    set -a; source /etc/mios/install.env 2>/dev/null || true; set +a
fi
[[ -z "${MIOS_VERSION:-}" ]] && MIOS_VERSION="$(cat /usr/share/mios/VERSION 2>/dev/null || cat /etc/mios/VERSION 2>/dev/null || echo "0.2.2")"
MIOS_AI_MODEL="${MIOS_AI_MODEL:-qwen2.5-coder:7b}"

# ── Helpers ───────────────────────────────────────────────────────────────────
hr_line() {
    local width="${1:-79}"
    local i
    for ((i = 0; i < width; i++)); do printf '%s' "$HR"; done
    printf '\n'
}

# service_status <unit>
# Echoes "<state>|<dot>|<color>" so callers don't shell out twice.
# state: active / failed / inactive / skipped / missing / unknown
service_status() {
    local svc="$1"
    if ! command -v systemctl >/dev/null 2>&1; then
        printf 'no-systemd|%s|%s' "$DOT_DOWN" "$C_GRY"; return
    fi
    if ! systemctl list-unit-files "$svc" --no-legend 2>/dev/null | grep -q .; then
        printf 'missing|%s|%s' "$DOT_DOWN" "$C_GRY"; return
    fi
    local state
    state="$(systemctl is-active "$svc" 2>/dev/null || true)"
    case "$state" in
        active)
            printf 'active|%s|%s' "$DOT_UP" "$C_GRN" ;;
        activating|reloading)
            printf 'starting|%s|%s' "$DOT_WAIT" "$C_YLW" ;;
        failed)
            printf 'failed|%s|%s' "$DOT_FAIL" "$C_RED" ;;
        inactive|deactivating)
            # Distinguish "Condition*= gate skipped" from a hard "down".
            if systemctl status "$svc" 2>/dev/null \
                    | grep -qE '(was not met|Condition.*not met|skipped)'; then
                printf 'skipped|%s|%s' "$DOT_DOWN" "$C_YLW"
            else
                printf 'inactive|%s|%s' "$DOT_DOWN" "$C_GRY"
            fi
            ;;
        *)
            printf 'unknown|%s|%s' "$DOT_DOWN" "$C_GRY" ;;
    esac
}

# endpoint_up <url>: returns 0 if reachable within 2s.
endpoint_up() {
    command -v curl >/dev/null 2>&1 || return 1
    curl -fsS --max-time 2 -o /dev/null -k "$1" 2>/dev/null
}

ep_dot() {
    if endpoint_up "$1"; then printf '%s%s%s' "$C_GRN" "$DOT_UP" "$C_R"
    else                       printf '%s%s%s' "$C_GRY" "$DOT_DOWN" "$C_R"; fi
}

# ── Sections ──────────────────────────────────────────────────────────────────
section_header() {
    printf '\n  %s%s%s%s\n' "$C_B" "$C_CYN" "$1" "$C_R"
}

print_endpoints() {
    section_header "Self-replication loop"
    printf '    %s  Forge       %shttp://localhost:3000/%s\n' \
        "$(ep_dot http://localhost:3000/api/v1/version)" "$C_D" "$C_R"
    printf '    %s  AI          %shttp://localhost:8080/v1%s   %s%s%s\n' \
        "$(ep_dot http://localhost:8080/v1/models)" "$C_D" "$C_R" "$C_GRY" "$MIOS_AI_MODEL" "$C_R"
    printf '    %s  Cockpit     %shttps://localhost:9090/%s\n' \
        "$(ep_dot https://localhost:9090/)" "$C_D" "$C_R"
    printf '    %s  Ollama      %shttp://localhost:11434%s\n' \
        "$(ep_dot http://localhost:11434/)" "$C_D" "$C_R"
}

print_quadlets() {
    section_header "Quadlet services"
    local svc info name dot color
    for svc in mios-ai mios-forge mios-forgejo-runner mios-cockpit-link \
               mios-ceph mios-k3s ollama crowdsec-dashboard \
               mios-guacamole guacd guacamole-postgres; do
        info="$(service_status "${svc}.service")"
        IFS='|' read -r name dot color <<< "$info"
        printf '    %s%s%s  %s%-22s%s  %s%s%s\n' \
            "$color" "$dot" "$C_R" \
            "$C_D" "$svc" "$C_R" \
            "$C_GRY" "$name" "$C_R"
    done
}

print_git_state() {
    section_header "Working tree (/=git)"
    if [[ ! -d /.git ]]; then
        printf '    %s(no .git at /; live root is not yet a git working tree)%s\n' "$C_GRY" "$C_R"
        printf '    %srun forge-firstboot to initialize, then:%s\n' "$C_D" "$C_R"
        printf '    %sgit -C / init && git -C / remote add origin http://%s@localhost:3000/%s/mios.git%s\n' \
            "$C_D" "$MIOS_LINUX_USER" "$MIOS_LINUX_USER" "$C_R"
        return
    fi
    local branch ahead behind modified untracked staged
    branch="$(git -C / symbolic-ref --short HEAD 2>/dev/null || echo "(detached)")"
    ahead="$(git -C / rev-list --count '@{upstream}..HEAD' 2>/dev/null || echo "?")"
    behind="$(git -C / rev-list --count 'HEAD..@{upstream}' 2>/dev/null || echo "?")"
    modified="$(git -C / status --porcelain=v1 2>/dev/null | grep -cE '^.M' || echo 0)"
    staged="$(git -C / status --porcelain=v1 2>/dev/null | grep -cE '^M.|^A.' || echo 0)"
    untracked="$(git -C / status --porcelain=v1 2>/dev/null | grep -cE '^\?\?' || echo 0)"
    printf '    %sbranch%s     %s%s%s\n' "$C_D" "$C_R" "$C_B" "$branch" "$C_R"
    printf '    %sahead%s      %s%s%s\n' "$C_D" "$C_R" "$C_GRN" "$ahead" "$C_R"
    printf '    %sbehind%s     %s%s%s\n' "$C_D" "$C_R" "$C_YLW" "$behind" "$C_R"
    printf '    %sstaged%s     %s\n' "$C_D" "$C_R" "$staged"
    printf '    %smodified%s   %s\n' "$C_D" "$C_R" "$modified"
    printf '    %suntracked%s  %s\n' "$C_D" "$C_R" "$untracked"
}

print_loop_hint() {
    printf '\n  %sEdit /  ->  git -C / commit  ->  git -C / push  ->  Forgejo Runner builds  ->  bootc switch%s\n' "$C_D" "$C_R"
    printf '  %sRebuild now: git -C / push http://%s@localhost:3000/%s/mios.git%s\n\n' \
        "$C_GRY" "$MIOS_LINUX_USER" "$MIOS_LINUX_USER" "$C_R"
}

print_services_block() {
    print_endpoints
    print_quadlets
    print_git_state
}

# ── Main ──────────────────────────────────────────────────────────────────────
case "$MODE" in
    services-only)
        # Used by fastfetch as a custom command-module embedded inside its
        # column layout, AND by mios-dashboard-render-issue.sh writing to
        # /etc/issue.d. Both contexts want the services block ALONE, no
        # loop hint -- the wrapper that called us prints the hint itself.
        print_services_block
        ;;
    *)
        # Default: header -> fastfetch (system info ONLY, no MiOS module
        # because side-by-side multi-line text bleeds into the ASCII logo
        # column) -> services block -> loop hint.
        printf '\n  %s%sMiOS%s %sv%s%s  %s%s%s\n' \
            "$C_B" "$C_CYN" "$C_R" "$C_D" "$MIOS_VERSION" "$C_R" \
            "$C_GRY" "$(uname -srm)" "$C_R"
        hr_line 79

        if command -v fastfetch >/dev/null 2>&1; then
            local_cfg=/usr/share/mios/fastfetch/config.jsonc
            if [[ -r "$local_cfg" ]]; then
                fastfetch -c "$local_cfg" 2>/dev/null || fastfetch 2>/dev/null || true
            else
                fastfetch 2>/dev/null || true
            fi
        fi
        # Services block always renders below fastfetch (or alone if
        # fastfetch is absent). Full-width, no column collision.
        print_services_block
        print_loop_hint
        ;;
esac

exit 0
