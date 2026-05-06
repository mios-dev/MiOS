#!/usr/bin/env bash
# /usr/libexec/mios/mios-dashboard.sh
#
# MiOS live system dashboard. Renders to ANY tty -- detects color
# capability, degrades to plain ASCII on tty0 / `linux` console.
#
# Everything renders inside an 80-column frame so output never bleeds
# past a tty0/console viewport. Long lines are truncated with an
# ellipsis (default) or marquee-scrolled when --ticker is passed.
#
# Modes:
#   default          : framed header (ASCII art) + fastfetch + services + loop hint
#   --services-only  : just the services block (used by fastfetch as a
#                      custom command-module; rendered UNFRAMED so it
#                      can sit inside fastfetch's column layout)
#   --no-color       : strip ANSI escape codes
#   --ticker         : continuously scroll long lines (interactive only;
#                      blocks until Ctrl-C, so NOT used in motd path)
#   --no-frame       : disable the outer frame (legacy / debug)
#
# Frame dimensions are FIXED at 80 cols wide. The Windows desktop
# launcher (build-mios.ps1's Install-WindowsBranding) sizes its
# Windows Terminal profile to match exactly.
#
# Entry points:
#   - /etc/profile.d/zz-mios-motd.sh runs the default mode at every
#     interactive shell login (deduped per-session via $MIOS_MOTD_SHOWN).
#   - mios-dash (/usr/bin/mios-dash) wraps this script.
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
NO_FRAME=0
TICKER=0
for arg in "$@"; do
    case "$arg" in
        --services-only) MODE="services-only"; NO_FRAME=1 ;;
        --no-color)      NO_COLOR=1 ;;
        --no-frame)      NO_FRAME=1 ;;
        --ticker)        TICKER=1 ;;
        --help|-h)
            sed -n '/^# /,/^$/{s/^# \?//;p}' "$0" | head -40
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
    HR="─"
    F_TL="╭"; F_TR="╮"; F_BL="╰"; F_BR="╯"
    F_LT="├"; F_RT="┤"; F_V="│"
else
    C_R=""; C_B=""; C_D=""
    C_RED=""; C_GRN=""; C_YLW=""; C_BLU=""; C_MGT=""; C_CYN=""; C_GRY=""
    DOT_UP="*"; DOT_DOWN="-"; DOT_FAIL="x"; DOT_WAIT="."
    HR="-"
    F_TL="+"; F_TR="+"; F_BL="+"; F_BR="+"
    F_LT="+"; F_RT="+"; F_V="|"
fi

# ── Frame dimensions (FIXED 80 cols) ─────────────────────────────────────────
# 80 = tty0 native width and the Windows Terminal MiOS profile size.
# Inner width = 76: "│ " (2) + content + " │" (2) = 80.
WIDTH=80
INNER=$((WIDTH - 4))

# Identity from install.env (written by mios-bootstrap at install time).
# install.env is sourced FIRST so MIOS_USER lands in env, then we fall
# back to $USER only when install.env didn't supply a value. The previous
# order (`MIOS_LINUX_USER="${USER:-mios}"` set BEFORE sourcing) made the
# MOTD render `login: root / mios` because mios-dashboard-issue.service
# runs as root -- $USER == 'root' wins over the unset MIOS_LINUX_USER.
MIOS_VERSION=""
MIOS_AI_MODEL=""
if [[ -r /etc/mios/install.env ]]; then
    # shellcheck disable=SC1091
    set -a; source /etc/mios/install.env 2>/dev/null || true; set +a
fi
# Resolution order: install.env-staged MIOS_USER (canonical) > legacy
# MIOS_LINUX_USER alias > literal 'mios'. Critically NEVER falls back
# to $USER -- the service `mios-dashboard-issue.service` runs as root,
# so $USER == 'root' would render `login: root / mios` in the pre-login
# banner even though the configured login user is 'mios'. The banner
# describes the OPERATOR'S login surface, not the running process.
MIOS_LINUX_USER="${MIOS_USER:-${MIOS_LINUX_USER:-mios}}"
[[ -z "${MIOS_VERSION:-}" ]] && MIOS_VERSION="$(cat /usr/share/mios/VERSION 2>/dev/null || cat /etc/mios/VERSION 2>/dev/null || echo "0.2.4")"
MIOS_AI_MODEL="${MIOS_AI_MODEL:-qwen2.5-coder:7b}"

# ── Frame helpers ────────────────────────────────────────────────────────────
# Repeat a single char N times.
hr_repeat() { local ch="$1" n="$2" i; for ((i=0; i<n; i++)); do printf '%s' "$ch"; done; }

frame_top()    { printf '%s%s%s\n' "$F_TL" "$(hr_repeat "$HR" $((WIDTH-2)))" "$F_TR"; }
frame_bot()    { printf '%s%s%s\n' "$F_BL" "$(hr_repeat "$HR" $((WIDTH-2)))" "$F_BR"; }
frame_divide() { printf '%s%s%s\n' "$F_LT" "$(hr_repeat "$HR" $((WIDTH-2)))" "$F_RT"; }
frame_blank()  { printf '%s%s%s\n' "$F_V" "$(hr_repeat ' ' $((WIDTH-2)))" "$F_V"; }

# frame_filter -- read stdin, wrap each line in the frame.
# Strips ANSI codes for visible-length math, preserves them on output.
# Truncates with "..." (or "…" when unicode) when longer than INNER.
# Pads short lines to exactly INNER chars so the right border lines up.
#
# Implemented in python3 (NOT awk) because awk's length() / substr()
# are byte-based on mawk and locale-dependent on gawk; with multi-byte
# UTF-8 box-drawing chars and dots in our output the right border would
# slide left by 2 chars per glyph. Python's str ops are code-point-based
# everywhere, so the frame stays square.
frame_filter() {
    local ell="…"
    [[ $NO_COLOR -eq 1 ]] && ell="..."
    INNER="$INNER" F_V="$F_V" ELL="$ell" python3 -c '
import os, sys, re
# Force utf-8 on stdin/stdout regardless of locale -- the framing chars
# and dot glyphs are 3-byte UTF-8; if the default locale is C/POSIX
# (or cp1252 on Windows for cross-host testing) Python would raise
# UnicodeEncodeError on the box-drawing chars.
sys.stdin.reconfigure(encoding="utf-8", errors="replace")
sys.stdout.reconfigure(encoding="utf-8")
inner = int(os.environ["INNER"])
vr    = os.environ["F_V"]
ell   = os.environ["ELL"]
ansi  = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
for raw in sys.stdin:
    line = raw.rstrip("\n").rstrip("\r")
    visible = ansi.sub("", line)
    vis = len(visible)
    if vis > inner:
        # Truncating mid-ANSI would orphan a color start without its
        # reset; strip ANSI on the truncate path so colors are clean.
        line = visible[:max(0, inner - len(ell))] + ell
        vis = len(line)
    pad = " " * max(0, inner - vis)
    sys.stdout.write(f"{vr} {line}{pad} {vr}\n")
'
}

# ── ASCII art header (centered inside frame) ─────────────────────────────────
ART_FILE=/usr/share/mios/branding/mios.txt
print_ascii_header() {
    if [[ ! -r "$ART_FILE" ]]; then return; fi
    # Find max width of art lines to center it as a block.
    local maxw=0 line
    while IFS= read -r line; do
        local stripped="$line"
        # No ANSI in the art file, so length is direct.
        (( ${#stripped} > maxw )) && maxw=${#stripped}
    done < "$ART_FILE"
    local pad=$(( (INNER - maxw) / 2 ))
    (( pad < 0 )) && pad=0
    local pad_str
    pad_str="$(hr_repeat ' ' "$pad")"
    while IFS= read -r line; do
        printf '%s%s%s%s\n' "$C_CYN" "$pad_str" "$line" "$C_R"
    done < "$ART_FILE"
}

# ── Title row + version ──────────────────────────────────────────────────────
print_title() {
    local left=" MiOS v${MIOS_VERSION}"
    local right="$(uname -srm) "
    local gap=$(( INNER - ${#left} - ${#right} ))
    (( gap < 1 )) && gap=1
    printf '%s%s%s%s%s%s\n' "$C_B$C_CYN" "$left" "$C_R" \
        "$(hr_repeat ' ' "$gap")" "$C_GRY$right" "$C_R"
}

# ── Section header ───────────────────────────────────────────────────────────
section_header() {
    printf '\n  %s%s%s%s\n' "$C_B" "$C_CYN" "$1" "$C_R"
}

# ── Service status helpers ───────────────────────────────────────────────────
service_status() {
    local svc="$1"
    if ! command -v systemctl >/dev/null 2>&1; then
        printf 'no-systemd|%s|%s' "$DOT_DOWN" "$C_GRY"; return
    fi
    local out load active
    out="$(systemctl show "$svc" --property=LoadState --property=ActiveState 2>/dev/null || true)"
    load="$(printf '%s' "$out"   | sed -nE 's/^LoadState=(.*)$/\1/p')"
    active="$(printf '%s' "$out" | sed -nE 's/^ActiveState=(.*)$/\1/p')"
    if [[ -z "$load" ]] || [[ "$load" == "not-found" ]] || [[ "$load" == "masked" ]]; then
        printf 'missing|%s|%s' "$DOT_DOWN" "$C_GRY"; return
    fi
    case "$active" in
        active)
            printf 'active|%s|%s' "$DOT_UP" "$C_GRN" ;;
        activating|reloading)
            printf 'starting|%s|%s' "$DOT_WAIT" "$C_YLW" ;;
        failed)
            printf 'failed|%s|%s' "$DOT_FAIL" "$C_RED" ;;
        inactive|deactivating)
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

endpoint_up() {
    command -v curl >/dev/null 2>&1 || return 1
    curl -fsS --max-time 2 -o /dev/null -k "$1" 2>/dev/null
}
ep_dot() {
    if endpoint_up "$1"; then printf '%s%s%s' "$C_GRN" "$DOT_UP" "$C_R"
    else                       printf '%s%s%s' "$C_GRY" "$DOT_DOWN" "$C_R"; fi
}

# ── Sections (each printed UNFRAMED; frame_filter wraps after capture) ───────
print_endpoints() {
    section_header "Self-replication loop"
    printf '    %s  Forge       %shttp://localhost:3000/%s\n' \
        "$(ep_dot http://localhost:3000/api/v1/version)" "$C_D" "$C_R"
    printf '    %s  AI          %shttp://localhost:8080/v1%s   %s%s%s\n' \
        "$(ep_dot http://localhost:8080/v1/models)" "$C_D" "$C_R" "$C_GRY" "$MIOS_AI_MODEL" "$C_R"
    printf '    %s  Cockpit     %shttps://localhost:9090/%s   %slogin: %s / %s%s\n' \
        "$(ep_dot https://localhost:9090/)" "$C_D" "$C_R" \
        "$C_GRY" "${MIOS_LINUX_USER:-mios}" "${MIOS_DEV_DEFAULT_PASSWORD:-mios}" "$C_R"
    printf '    %s  Ollama      %shttp://localhost:11434%s\n' \
        "$(ep_dot http://localhost:11434/)" "$C_D" "$C_R"
    printf '    %s  Search      %shttp://localhost:8888/%s\n' \
        "$(ep_dot http://localhost:8888/)" "$C_D" "$C_R"
    printf '    %s  Hermes      %shttp://localhost:8642/v1%s\n' \
        "$(ep_dot http://localhost:8642/v1/models)" "$C_D" "$C_R"
    printf '    %s  WebUI       %shttp://localhost:3030/%s\n' \
        "$(ep_dot http://localhost:3030/)" "$C_D" "$C_R"
}

print_quadlets() {
    section_header "Quadlet services"
    local svc info name dot color
    for svc in mios-ai mios-forge mios-forgejo-runner mios-cockpit-link \
               mios-ceph mios-k3s ollama mios-searxng \
               mios-hermes mios-webui crowdsec-dashboard \
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
        printf '    %sgit -C / init && remote add origin localhost:3000/%s/mios.git%s\n' \
            "$C_D" "$MIOS_LINUX_USER" "$C_R"
        return
    fi
    local branch ahead behind modified untracked staged porcelain
    branch="$(git -C / symbolic-ref --short HEAD 2>/dev/null || echo "(detached)")"
    if git -C / show-ref --verify --quiet "refs/remotes/origin/$branch" 2>/dev/null; then
        ahead="$(git -C / rev-list --count "origin/${branch}..HEAD" 2>/dev/null || echo "?")"
        behind="$(git -C / rev-list --count "HEAD..origin/${branch}" 2>/dev/null || echo "?")"
    else
        ahead="?"; behind="?"
    fi
    porcelain="$(git -C / status --porcelain=v1 2>/dev/null)"
    modified="$(printf '%s\n' "$porcelain"  | grep -cE '^.M'   2>/dev/null; true)"
    staged="$(printf '%s\n'   "$porcelain"  | grep -cE '^[MA]' 2>/dev/null; true)"
    untracked="$(printf '%s\n' "$porcelain" | grep -cE '^\?\?' 2>/dev/null; true)"
    modified="${modified%%[!0-9]*}";   modified="${modified:-0}"
    staged="${staged%%[!0-9]*}";       staged="${staged:-0}"
    untracked="${untracked%%[!0-9]*}"; untracked="${untracked:-0}"
    printf '    %sbranch%s     %s%s%s\n' "$C_D" "$C_R" "$C_B" "$branch" "$C_R"
    printf '    %sahead%s      %s%s%s\n' "$C_D" "$C_R" "$C_GRN" "$ahead" "$C_R"
    printf '    %sbehind%s     %s%s%s\n' "$C_D" "$C_R" "$C_YLW" "$behind" "$C_R"
    printf '    %sstaged%s     %s\n' "$C_D" "$C_R" "$staged"
    printf '    %smodified%s   %s\n' "$C_D" "$C_R" "$modified"
    printf '    %suntracked%s  %s\n' "$C_D" "$C_R" "$untracked"
}

print_loop_hint() {
    printf '\n  %sEdit /  ->  git commit  ->  git push  ->  Forgejo Runner  ->  bootc switch%s\n' "$C_D" "$C_R"
    printf '  %sRebuild now: git -C / push http://%s@localhost:3000/%s/mios.git%s\n' \
        "$C_GRY" "$MIOS_LINUX_USER" "$MIOS_LINUX_USER" "$C_R"
}

print_services_block() {
    print_endpoints
    print_quadlets
    print_git_state
}

# ── Fastfetch capture (logo suppressed; we render our own header) ────────────
print_fastfetch() {
    if ! command -v fastfetch >/dev/null 2>&1; then return; fi
    local local_cfg=/usr/share/mios/fastfetch/config.jsonc
    if [[ -r "$local_cfg" ]]; then
        # --logo none kills fastfetch's logo so our centered MiOS art at
        # the top of the frame is the only logo. Width forced narrow so
        # the info column doesn't push past INNER.
        fastfetch -c "$local_cfg" --logo none 2>/dev/null || fastfetch --logo none 2>/dev/null || true
    else
        fastfetch --logo none 2>/dev/null || true
    fi
}

# ── Main ─────────────────────────────────────────────────────────────────────
case "$MODE" in
    services-only)
        # Used by fastfetch as a custom command-module embedded inside its
        # column layout. Frame would collide with fastfetch's borders, so
        # we render UNFRAMED here regardless of --no-frame.
        print_services_block
        ;;
    *)
        if [[ $NO_FRAME -eq 1 ]]; then
            print_ascii_header
            print_title
            print_fastfetch
            print_services_block
            print_loop_hint
        else
            # Capture each section, pipe through frame_filter so each
            # line is wrapped and truncated to fit INNER chars exactly.
            frame_top
            print_ascii_header | frame_filter
            frame_divide
            { print_title; } | frame_filter
            frame_divide
            print_fastfetch | frame_filter
            frame_divide
            print_services_block | frame_filter
            frame_divide
            print_loop_hint | frame_filter
            frame_bot
        fi
        ;;
esac

exit 0
