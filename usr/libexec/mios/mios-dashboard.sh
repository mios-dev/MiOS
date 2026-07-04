#!/usr/bin/env bash
# AI-hint: MiOS live system dashboard. Renders to ANY tty -- detects color
# AI-related: /usr/libexec/mios/mios-dashboard.sh, /usr/share/mios/mios.toml, /etc/mios/install.env, /usr/share/mios/VERSION, /etc/mios/VERSION, /usr/share/mios/branding/mios.txt, /etc/mios/mios.toml, /etc/mios/forge/admin-password, /usr/share/mios/fastfetch/config.jsonc, mios-dashboard
# AI-functions: _mios_toml_value, hr_repeat, frame_top, frame_bot, frame_divide, frame_blank, frame_filter, print_ascii_header, print_title, section_header, service_status, endpoint_up
# /usr/libexec/mios/mios-dashboard.sh
#
# MiOS live system dashboard. Renders to ANY tty -- detects color
# capability, degrades to plain ASCII on tty0 / `linux` console.
#
# Everything renders inside a frame whose width comes from
# /usr/share/mios/mios.toml [terminal].cols - [terminal].right_margin
# (default 80, edge-to-edge), so output never bleeds past the tty0 /
# console viewport. Long lines are truncated with an ellipsis (default)
# or marquee-scrolled when --ticker is passed.
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
# Frame dimensions are sourced from /usr/share/mios/mios.toml [terminal]
# (cols, right_margin) -- WIDTH = cols - right_margin, edge-to-edge by
# default (cols=80, right_margin=0 -> WIDTH=80). Set MIOS_TOML to point
# the awk helper at a different TOML file (e.g. for testing). The
# Windows desktop launcher (build-mios.ps1's Install-WindowsBranding)
# reads the same [terminal] keys via its own PowerShell TOML reader,
# so cross-platform values stay aligned.
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
MONITOR=0
for arg in "$@"; do
    case "$arg" in
        --services-only) MODE="services-only"; NO_FRAME=1 ;;
        --table-only)    MODE="table-only"; NO_FRAME=1 ;;
        --endpoints-only) MODE="endpoints-only"; NO_FRAME=1 ;;
        --mini)          MODE="mini" ;;
        --no-color)      NO_COLOR=1 ;;
        --no-frame)      NO_FRAME=1 ;;
        --ticker)        TICKER=1 ;;
        --monitor)       MONITOR=1 ;;
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

# ── Frame dimensions (sourced from mios.toml [terminal]) ─────────────────────
# WIDTH = cols - right_margin. EDGE-TO-EDGE by default
# (right_margin=0, frame_width=cols=80). The TOML is the SSOT --
# mios.html edits flow here on next render. Vendor fallback is
# 80 cols / margin 0 if the TOML is missing (cold first-boot before
# /usr/share/mios is staged). Inner width = WIDTH - 4 because the
# frame chars consume "│ " + content + " │" = 4 cells.
#
# All MiOS consoles (Linux tty0, GNOME terminal, Ptyxis, WT MiOS
# profile, conhost fallback, WSL pwsh dispatcher) honor the same
# [terminal].cols / right_margin via their respective TOML readers
# (Get-MiOS.ps1's Get-MiosTomlValue / mios-dash.ps1's regex / this
# awk helper). No hardcoded 80 anywhere -- if you find one, lift it.
_mios_toml_value() {
    local section="$1" key="$2" def_val="$3"
    local toml="${MIOS_TOML:-/usr/share/mios/mios.toml}"
    [[ -r "$toml" ]] || { printf '%s' "$def_val"; return; }
    # gawk reserves `default` as a keyword (used in switch/case).  Passing
    # `-v default=...` raises `cannot use gawk builtin 'default' as variable
    # name` on Fedora's gawk.  Renamed to `def_val` everywhere -- mawk and
    # gawk both accept it.
    awk -v want_section="$section" -v want_key="$key" -v def_val="$def_val" '
        BEGIN { in_section = 0; found = 0 }
        /^\[/ {
            line = $0
            sub(/[[:space:]]*#.*$/, "", line)
            in_section = (line == "[" want_section "]") ? 1 : 0
            next
        }
        in_section && /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*=/ {
            line = $0
            sub(/[[:space:]]*#.*$/, "", line)
            eq = index(line, "=")
            if (eq == 0) next
            k = substr(line, 1, eq - 1)
            v = substr(line, eq + 1)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", v)
            gsub(/^"|"$/, "", v)
            if (k == want_key) { print v; found = 1; exit }
        }
        END { if (!found) print def_val }
    ' "$toml"
}
_mios_cols=$(_mios_toml_value "terminal" "cols" "80")
_mios_rmgn=$(_mios_toml_value "terminal" "right_margin" "0")
_mios_rows=$(_mios_toml_value "terminal" "rows" "20")
# dashboard inside MiOS-DEV (WSL bash) was rendering
# 80-wide but visible window only ~75 cells -> right edge cut off. Plus
# image #22: full ASCII logo overflows window vertically. Operator's
# benchmark: "full framed dash and 1 line of the prompt visible".
# Strategy: read LIVE tput cols/lines (actual paintable cells) over TOML
# values. TOML acts as fallback when tput fails. WIDTH = tput_cols -
# right_margin. AVAIL_ROWS = tput_lines - 1 (reserve 1 row for the
# prompt line). Logo render decision and content budget below honor
# AVAIL_ROWS so the dashboard always fits.
_term_cols=$(tput cols 2>/dev/null || true)
_term_rows=$(tput lines 2>/dev/null || true)
if [[ -n "$_term_cols" ]] && (( _term_cols > 0 )); then
    WIDTH=$(( _term_cols - _mios_rmgn ))
else
    WIDTH=$(( _mios_cols - _mios_rmgn ))
fi
(( WIDTH < 20 )) && WIDTH=80     # safety floor
INNER=$((WIDTH - 4))
if [[ -n "$_term_rows" ]] && (( _term_rows > 0 )); then
    AVAIL_ROWS=$(( _term_rows - 1 ))    # reserve 1 row for prompt
else
    AVAIL_ROWS=$(( _mios_rows - 1 ))
fi
(( AVAIL_ROWS < 6 )) && AVAIL_ROWS=18    # safety floor: too small to render
# Compact mode = drop the multi-row ASCII logo when window can't fit it
# AND the framed banner + system info + prompt. Logo is ~12 rows;
# system info is 5 rows; framing + dividers add ~5; total ~22.
# AVAIL_ROWS < 22 triggers compact mode (no logo).
MIOS_COMPACT=1
if (( AVAIL_ROWS >= 22 )); then
    MIOS_COMPACT=0
fi

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
# LOGIN account = the DB-driven account SSOT (pgvector), resolved via the
# shared mios-login-account helper (DB person/account -> live primary human
# account -> vendor default 'user'). Deliberately NOT MIOS_USER / [user].name:
# that is the operator's DISPLAY name (e.g. "Kabu") and must never land in a
# login/credential slot. Interim consumer ahead of the WS-ACCT DB<->OS control
# plane (T-150..T-153). Degrade-open so the banner always renders; NEVER falls
# back to $USER (the dashboard-issue service runs as root).
_mios_login_helper="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/mios-login-account"
[[ -r "$_mios_login_helper" ]] || _mios_login_helper="/usr/libexec/mios/mios-login-account"
MIOS_LINUX_USER="$(bash "$_mios_login_helper" 2>/dev/null)"
[[ -z "$MIOS_LINUX_USER" ]] && MIOS_LINUX_USER="user"
MIOS_LOGIN_PASSWORD="$(bash "$_mios_login_helper" password 2>/dev/null)"
[[ -z "$MIOS_LOGIN_PASSWORD" ]] && MIOS_LOGIN_PASSWORD="user"
[[ -z "${MIOS_VERSION:-}" ]] && MIOS_VERSION="$(cat /usr/share/mios/VERSION 2>/dev/null || cat /etc/mios/VERSION 2>/dev/null || echo "0.2.4")"
MIOS_AI_MODEL="${MIOS_AI_MODEL:-granite4.1:8b}"

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
# CSI escape (color codes etc.): \e[...letter
csi   = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# OSC escape (hyperlinks, title sets): \e]...ST  where ST = BEL or ESC\
# OSC 8 hyperlinks for clickable service names produce
# `\e]8;;URL\e\\NAME\e]8;;\e\\` -- visually 0 + len(NAME) + 0 chars,
# but raw byte length is 30+. Without OSC stripping, the framer would
# count the ESC sequence bytes as visible width and wrap the row.
osc   = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
def strip_invisible(s):
    return osc.sub("", csi.sub("", s))
for raw in sys.stdin:
    line = raw.rstrip("\n").rstrip("\r")
    visible = strip_invisible(line)
    vis = len(visible)
    if vis > inner:
        # Truncating mid-ANSI would orphan a color start without its
        # reset; strip ANSI+OSC on the truncate path so colors and
        # hyperlinks are clean. Drop hyperlink wrappers but keep the
        # visible anchor text.
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
        [[ "$line" =~ ^# ]] && continue
        local stripped="$line"
        stripped="${stripped%"${stripped##*[![:space:]]}"}"
        # No ANSI in the art file, so length is direct.
        (( ${#stripped} > maxw )) && maxw=${#stripped}
    done < "$ART_FILE"
    local pad=$(( (INNER - maxw) / 2 ))
    (( pad < 0 )) && pad=0
    local pad_str="$(hr_repeat ' ' "$pad")"
    while IFS= read -r line; do
        [[ "$line" =~ ^# ]] && continue
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
# Inline (no leading blank) to keep the dashboard inside an 18-row
# budget on an 80x20 terminal -- each section header now costs 1 row
# instead of 2.
section_header() {
    local pad="${2:-  }"
    printf '%s%s%s%s%s\n' "$pad" "$C_B" "$C_CYN" "$1" "$C_R"
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
            local status_out
            status_out=$(systemctl status "$svc" 2>/dev/null || true)
            if printf '%s' "$status_out" | grep -qE '(was not met|Condition.*not met|skipped)'; then
                printf 'skipped|%s|%s' "$DOT_WAIT" "$C_YLW"
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
    curl -fsSL --max-time 2 -o /dev/null -k "$1" 2>/dev/null
}
ep_dot() {
    if endpoint_up "$1"; then printf '%s%s%s' "$C_GRN" "$DOT_UP" "$C_R"
    else                       printf '%s%s%s' "$C_GRY" "$DOT_DOWN" "$C_R"; fi
}

# TCP-open dot for non-HTTP services (pgvector/PostgreSQL): an HTTP probe always
# reads DOWN on a raw TCP port. $1=host $2=port.
tcp_dot() {
    if timeout 2 bash -c "exec 3<>/dev/tcp/$1/$2" 2>/dev/null; then
        printf '%s%s%s' "$C_GRN" "$DOT_UP" "$C_R"
    else printf '%s%s%s' "$C_GRY" "$DOT_DOWN" "$C_R"; fi
}

# Resolve a [ports].<key> value from the layered mios.toml SSOT.
# Honors ~/.config/mios > /etc/mios > /usr/share/mios precedence so an
# operator port-edit in mios.toml flows through to every URL on this
# dashboard without re-baking. Falls back to $2 if no layer matches.
_mios_port() {
    local key=$1 default=$2 t v var_name
    var_name="MIOS_PORT_$(echo "$key" | tr 'a-z' 'A-Z')"
    v=$(printenv "$var_name" 2>/dev/null || true)
    if [[ -n "$v" ]]; then
        printf '%s' "$v"
        return
    fi
    for t in "${HOME:-/root}/.config/mios/mios.toml" /etc/mios/mios.toml /usr/share/mios/mios.toml; do
        [ -r "$t" ] || continue
        v=$(awk -v k="$key" '
            /^\[ports\]/{in_ports=1; next}
            /^\[/{in_ports=0}
            in_ports && $0 ~ "^[[:space:]]*"k"[[:space:]]*=" {
                sub(/^[^=]*=[[:space:]]*/, "")
                sub(/[[:space:]]*#.*$/, "")
                gsub(/[[:space:]"]/, "")
                print; exit
            }
        ' "$t" 2>/dev/null)
        [ -n "$v" ] && { printf '%s' "$v"; return; }
    done
    printf '%s' "$default"
}

GLYPH_QUADLETS=$''   #  cubes
GLYPH_GIT=$''        #  code-branch

# ── Live "SSH into the code-server dev container" command ────────────────────
# The command (and its sshd port) come from the shared SSOT helper
# mios-ssh-dev-cmd, which BOTH this dashboard and the Windows dashboard call so
# the two never drift. We prefer the copy shipped next to this script (so a
# repo checkout tests against its own helper) and fall back to the deployed
# path. Run via `bash` so it works even when the exec bit is missing (e.g. a
# /mnt/c Windows-filesystem checkout).
_ssh_dev_helper() {
    local self_dir c
    self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
    for c in "$self_dir/mios-ssh-dev-cmd" /usr/libexec/mios/mios-ssh-dev-cmd; do
        [[ -r "$c" ]] && { printf '%s' "$c"; return; }
    done
    printf '%s' "/usr/libexec/mios/mios-ssh-dev-cmd"
}
_ssh_live_port() { bash "$(_ssh_dev_helper)" port 2>/dev/null || _mios_port ssh 22; }
_ssh_dev_cmd()   { bash "$(_ssh_dev_helper)" 2>/dev/null; }

# ── Sections (each printed UNFRAMED; frame_filter wraps after capture) ───────
print_endpoints() {
    local _user _pw _fpw
    _user="${MIOS_LINUX_USER:-${MIOS_USER:-mios}}"
    _pw="${MIOS_DEFAULT_PASSWORD:-mios}"
    _fpw="$(cat /etc/mios/forge/admin-password 2>/dev/null)"
    [[ -z "$_fpw" ]]    && _fpw="$_pw"

    local _p_forge _p_cockpit _p_ollama _p_ollama_cpu _p_searxng
    local _p_hermes _p_dash _p_code _p_webui _p_agent_pipe _p_pgvector _p_guacamole
    local _p_ttyd_bash _p_ttyd_ps _p_ssh
    _p_forge=$(_mios_port forge_http 3000)
    _p_cockpit=$(_mios_port cockpit 9090)
    _p_ollama=$(_mios_port ollama 11434)
    _p_ollama_cpu=$(_mios_port ollama_cpu 11435)
    _p_llamaswap=$(_mios_port llm_light 11450)
    _p_searxng=$(_mios_port searxng 8899)
    _p_hermes=$(_mios_port hermes 8642)
    _p_dash=$(_mios_port hermes_dashboard 9119)
    _p_code=$(_mios_port code_server 8800)
    _p_webui=$(_mios_port open_webui 3033)
    _p_agent_pipe=$(_mios_port agent_pipe 8640)
    _p_pgvector=$(_mios_port pgvector 5432)
    _p_guacamole=$(_mios_port guacamole_web 8080)
    _p_ttyd_bash=$(_mios_port ttyd_bash 7681)
    _p_ttyd_ps=$(_mios_port ttyd_powershell 7682)
    _p_ssh=$(_mios_port ssh 22)
    local _ssh_check_port="$_p_ssh"
    if command -v systemctl >/dev/null 2>&1; then
        local _actual_ssh_port
        _actual_ssh_port=$(systemctl status sshd 2>/dev/null | grep -m 1 -oP 'port \K[0-9]+' || true)
        if [[ -n "$_actual_ssh_port" ]]; then
            _ssh_check_port="$_actual_ssh_port"
        fi
    fi

    local d_forge d_ollama d_ollama_cpu d_cockpit d_searxng
    local d_hermes d_dash d_code d_webui d_agent_pipe d_pgvector
    local d_ttyd_bash d_ttyd_ps d_guacamole d_ssh
    d_forge=$(ep_dot      "http://localhost:${_p_forge}/api/v1/version")
    d_ollama=$(ep_dot     "http://localhost:${_p_ollama}/")
    d_ollama_cpu=$(ep_dot "http://localhost:${_p_ollama_cpu}/")
    d_llamaswap=$(ep_dot  "http://localhost:${_p_llamaswap}/v1/models")
    d_cockpit=$(ep_dot    "https://localhost:${_p_cockpit}/")
    d_searxng=$(ep_dot    "http://localhost:${_p_searxng}/")
    d_hermes=$(ep_dot     "http://localhost:${_p_hermes}/health")
    d_dash=$(ep_dot       "http://localhost:${_p_dash}/")
    d_code=$(ep_dot       "http://localhost:${_p_code}/")
    d_webui=$(ep_dot      "http://localhost:${_p_webui}/")
    d_agent_pipe=$(ep_dot "http://localhost:${_p_agent_pipe}/health")
    d_pgvector=$(tcp_dot  localhost "$_p_pgvector")
    d_ttyd_bash=$(tcp_dot "127.0.0.1" "$_p_ttyd_bash")
    d_ttyd_ps=$(tcp_dot "127.0.0.1" "$_p_ttyd_ps")
    d_ssh=$(tcp_dot       localhost "$_ssh_check_port")
    s_guac=$( service_status mios-guacamole.service); IFS='|' read -r _ d_guacamole _ <<< "$s_guac"
    s_crowdsec=$( service_status mios-crowdsec-dashboard.service); IFS='|' read -r _ d_crowdsec _ <<< "$s_crowdsec"

    local n_up=0 n_down=0
    for _d in "$d_agent_pipe" "$d_hermes" "$d_pgvector" \
              "$d_llamaswap" "$d_webui" \
              "$d_cockpit" "$d_forge" "$d_searxng" \
              "$d_code" "$d_ttyd_bash" "$d_ttyd_ps" "$d_ssh"; do
        case "$_d" in
            *"$DOT_UP"*) n_up=$((n_up + 1)) ;;
            *)           n_down=$((n_down + 1)) ;;
        esac
    done
    local up_str="${n_up} up    " down_str="${n_down} down    "
    local ep_str="agent:${_p_agent_pipe}  hermes:${_p_hermes}  llama:${_p_llamaswap}"
    local total_len=$(( 6 + ${#up_str} + ${#down_str} + ${#ep_str} ))
    local pad=$(( (INNER - total_len) / 2 ))
    (( pad < 0 )) && pad=0
    local padstr="$(hr_repeat ' ' "$pad")"
    
    printf '%s%s%s%s %s%s%s%s%s %s%s%s%s\n' \
        "$padstr" \
        "$C_GRN" "$DOT_UP" "$C_R" "$C_B" "$up_str" \
        "$C_GRY" "$DOT_DOWN" "$C_R" "$C_GRY" "$down_str" \
        "$C_GRY" "$ep_str" "$C_R"
        
    local l_name1="Agent-Pipe" l_link1="http://localhost:${_p_agent_pipe}/v1"
    local r_name1="WebUI"      r_link1="http://localhost:${_p_webui}/"
    local l_name2="Cockpit"    l_link2="https://localhost:${_p_cockpit}/"
    local r_name2="PS-Term"    r_link2="http://localhost:${_p_ttyd_ps}/"
    local l_name3="IDE / Code"  l_link3="http://localhost:${_p_code}/"
    local r_name3="SSH"
    local r_link3 _ssh_live
    _ssh_live="$(_ssh_live_port)"
    r_link3="port ${_ssh_live}"

    local col_sep=" │ "
    [[ "$NO_COLOR" -eq 1 ]] && col_sep=" | "

    # Left cell width: 1 (dot) + 1 (sp) + 10 (name) + 1 (sp) + 24 (link) = 37 chars.
    # Separator: 3 chars.
    # Right cell width: 1 (dot) + 1 (sp) + 7 (name) + 1 (sp) + 22 (link) = 32 chars.
    # Total width = 37 + 3 + 32 = 72 chars.
    local table_w=72
    local t_pad=$(( (INNER - table_w) / 2 ))
    (( t_pad < 0 )) && t_pad=0
    local t_padstr="$(hr_repeat ' ' "$t_pad")"

    # Row 1
    printf "${t_padstr}%s %-10s %s%-24s%s${col_sep}%s %-7s %s%s%s\n" \
        "$d_agent_pipe" "$l_name1" "$C_D" "$l_link1" "$C_R" \
        "$d_webui" "$r_name1" "$C_D" "$r_link1" "$C_R"

    # Row 2
    printf "${t_padstr}%s %-10s %s%-24s%s${col_sep}%s %-7s %s%s%s\n" \
        "$d_cockpit" "$l_name2" "$C_D" "$l_link2" "$C_R" \
        "$d_ttyd_ps" "$r_name2" "$C_D" "$r_link2" "$C_R"

    # Row 3
    printf "${t_padstr}%s %-10s %s%-24s%s${col_sep}%s %-7s %s%s%s\n" \
        "$d_code" "$l_name3" "$C_D" "$l_link3" "$C_R" \
        "$d_ssh" "$r_name3" "$C_D" "$r_link3" "$C_R"
}

print_unified_table() {
    INNER="${INNER:-76}" NO_COLOR="${NO_COLOR:-0}" MONITOR="${MONITOR:-0}" MIOS_LINUX_USER="${MIOS_LINUX_USER:-}" MIOS_DEFAULT_PASSWORD="${MIOS_DEFAULT_PASSWORD:-}" MIOS_LOGIN_PASSWORD="${MIOS_LOGIN_PASSWORD:-}" python3 -c '
import os, glob, subprocess, math, time, shutil

no_color = int(os.environ.get("NO_COLOR", "0"))
inner = int(os.environ.get("INNER", "76"))
monitor = int(os.environ.get("MONITOR", "0"))

if no_color == 0:
    C_GRN = "\033[32m"
    C_RED = "\033[31m"
    C_YLW = "\033[33m"
    C_GRY = "\033[90m"
    C_R = "\033[0m"
    C_CYN = "\033[36m"
    C_B = "\033[1m"
    DOT_UP = "●"
    DOT_DOWN = "○"
    DOT_FAIL = "✗"
    DOT_WAIT = "◌"
else:
    C_GRN = C_RED = C_YLW = C_GRY = C_R = C_CYN = C_B = ""
    DOT_UP = "*"
    DOT_DOWN = "-"
    DOT_FAIL = "x"
    DOT_WAIT = "."

# 1. Resource Monitor Header
if monitor == 1:
    def get_cpu_usage():
        try:
            with open("/proc/stat") as f:
                fields = [float(column) for column in f.readline().strip().split()[1:]]
            return fields[3], sum(fields)
        except Exception:
            return 0, 0

    def get_mem_usage():
        try:
            mem = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem[parts[0].rstrip(":")] = int(parts[1])
            total = mem.get("MemTotal", 0) / 1024 / 1024
            free = mem.get("MemFree", 0) / 1024 / 1024
            buffers = mem.get("Buffers", 0) / 1024 / 1024
            cached = mem.get("Cached", 0) / 1024 / 1024
            used = total - free - buffers - cached
            pct = (used / total) * 100 if total > 0 else 0
            return used, total, pct
        except Exception:
            return 0, 0, 0

    def get_disk_usage():
        try:
            total, used, free = shutil.disk_usage("/")
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            pct = (used / total) * 100 if total > 0 else 0
            return used_gb, total_gb, pct
        except Exception:
            return 0, 0, 0

    def draw_bar(pct, width=10):
        filled = int(round(pct / 100 * width))
        return "█" * filled + "░" * (width - filled)

    id1, tot1 = get_cpu_usage()
    time.sleep(0.1)
    id2, tot2 = get_cpu_usage()
    diff_tot = tot2 - tot1
    cpu_pct = (1.0 - (id2 - id1) / diff_tot) * 100.0 if diff_tot > 0 else 0.0

    mem_used, mem_tot, mem_pct = get_mem_usage()
    disk_used, disk_tot, disk_pct = get_disk_usage()
    
    try:
        load1, load5, load15 = os.getloadavg()
    except Exception:
        load1 = load5 = load15 = 0.0

    cpu_bar = draw_bar(cpu_pct)
    mem_bar = draw_bar(mem_pct)
    disk_bar = draw_bar(disk_pct)

    r1 = f"CPU  [{C_CYN}{cpu_bar}{C_R}] {cpu_pct:>5.1f}%  │  Mem  [{C_CYN}{mem_bar}{C_R}] {mem_pct:>5.1f}% ({mem_used:.1f}/{mem_tot:.1f} GB)"
    r2 = f"Disk [{C_CYN}{disk_bar}{C_R}] {disk_pct:>5.1f}%  │  Load [{C_CYN}{load1:.2f} {load5:.2f} {load15:.2f}{C_R}]"

    visible_r1 = 66
    visible_r2 = 54
    pad_r1 = max(0, (inner - visible_r1) // 2)
    pad_r2 = max(0, (inner - visible_r2) // 2)
    pad_r1_str = " " * pad_r1
    pad_r2_str = " " * pad_r2
    print(f"{pad_r1_str}{r1}")
    print(f"{pad_r2_str}{r2}")
    print()

# 2. Unified Status Table
ports = {}
for path in ["/root/.config/mios/mios.toml", "/etc/mios/mios.toml", "/usr/share/mios/mios.toml"]:
    if os.path.isfile(path):
        try:
            with open(path, "rb") as f:
                import tomllib
                data = tomllib.load(f)
                if "ports" in data:
                    ports = data["ports"]
                    break
        except Exception:
            pass

import re

# LIVE enumeration -- NO hardcoded name/port lists. Pods + containers come from
# `podman (pod) ps` (real running state + real published port); host services
# from `systemctl list-units` (minus container-backed units). Ports for host-net
# containers and for services resolve from the mios.toml [ports] SSOT by name.
def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=6).stdout
    except Exception:
        return ""

have_podman = shutil.which("podman") is not None

def short_name(n):
    return n[5:] if n.startswith("mios-") else n

def svc_port(short):
    if short == "agents":
        return str(ports.get("code_server", "8800"))
    key = short.replace("-", "_")
    if key in ports:
        return str(ports[key])
    for suf in ("_http", "_ui", "_web"):
        if key + suf in ports:
            return str(ports[key + suf])
    return ""

def live_port(ports_field):
    m = re.search(r":(\d+)->", ports_field or "")
    return m.group(1) if m else ""

def up_dot():   return f"{C_GRN}{DOT_UP}{C_R}"
def wait_dot(): return f"{C_YLW}{DOT_WAIT}{C_R}"
def fail_dot(): return f"{C_RED}{DOT_FAIL}{C_R}"
def down_dot(): return f"{C_GRY}{DOT_DOWN}{C_R}"

rendered_items = []
container_units = set()

# Pods (live)
if have_podman:
    for line in _run(["podman", "pod", "ps", "--format", "{{.Name}}|{{.Status}}"]).splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        name = parts[0]
        status = (parts[1] if len(parts) > 1 else "").lower()
        dot = up_dot() if "running" in status else (wait_dot() if "degraded" in status else down_dot())
        rendered_items.append(("Pod", short_name(name), "", dot))

# Containers (live: real state + real published port)
if have_podman:
    for line in _run(["podman", "ps", "-a", "--format", "{{.Names}}|{{.State}}|{{.Ports}}"]).splitlines():
        if not line.strip():
            continue
        parts = line.split("|")
        name = parts[0]
        state = (parts[1] if len(parts) > 1 else "").lower()
        pf = parts[2] if len(parts) > 2 else ""
        container_units.add(name)
        short = short_name(name)
        # Skip podman pod-infra (pause) containers -- the pod itself is shown above.
        if short.endswith("-infra"):
            continue
        if state == "running":
            dot = up_dot()
        elif state in ("created", "restarting", "paused"):
            dot = wait_dot()
        else:
            dot = down_dot()
        pv = live_port(pf) or svc_port(short)
        rendered_items.append(("Cont", short, f":{pv}" if pv else "", dot))

# MiOS host services (live), excluding container-backed units (already shown above)
svc_state = {}
for line in _run(["systemctl", "list-units", "--type=service", "--all", "--no-legend",
                  "--plain", "mios-*.service", "hermes*.service"]).splitlines():
    cols = line.split()
    if len(cols) < 4 or not cols[0].endswith(".service"):
        continue
    base = cols[0][:-len(".service")]
    # Skip container-backed units (shown as Cont) and pod units (shown as Pod).
    if base in container_units or base.endswith("-pod"):
        continue
    svc_state[base] = (cols[2], cols[3])   # (ActiveState, SubState)

# Show only genuinely-live and genuinely-broken services: real running daemons
# (ACTIVE=active + SUB=running) and hard failures (ACTIVE=failed). Everything
# else is hidden -- RemainAfterExit boot one-shots (active/exited), dormant units,
# and ConditionResult=no services gated off on this host (no Chrome flatpak,
# unbuilt optional images, etc.) which flap through "activating" and would
# otherwise read as false outages. State-driven, no name list.
for base in sorted(svc_state):
    active, sub = svc_state[base]
    if active == "active" and sub == "running":
        dot = up_dot()
    elif active == "failed":
        dot = fail_dot()
    else:
        continue
    short = short_name(base)
    pv = svc_port(short)
    rendered_items.append(("Svc", short, f":{pv}" if pv else "", dot))

num_items = len(rendered_items)
num_rows = math.ceil(num_items / 2)
left_col = rendered_items[:num_rows]
right_col = rendered_items[num_rows:]

max_l_name = max(len(x[1]) for x in left_col) if left_col else 0
max_l_port = max(len(x[2]) for x in left_col) if left_col else 0
max_r_name = max(len(x[1]) for x in right_col) if right_col else 0
max_r_port = max(len(x[2]) for x in right_col) if right_col else 0

sep = " │ " if no_color == 0 else " | "

table_rows = []
for i in range(num_rows):
    l_type, l_name, l_port, l_dot = left_col[i]
    l_cell = f"{C_GRY}{l_type:<4}{C_R} {C_B}{l_name:<{max_l_name}}{C_R} {C_CYN}{l_port:<{max_l_port}}{C_R} {l_dot}"
    
    if i < len(right_col):
        r_type, r_name, r_port, r_dot = right_col[i]
        r_cell = f"{C_GRY}{r_type:<4}{C_R} {C_B}{r_name:<{max_r_name}}{C_R} {C_CYN}{r_port:<{max_r_port}}{C_R} {r_dot}"
        row_str = f"{l_cell}{sep}{r_cell}"
    else:
        row_str = l_cell
    table_rows.append(row_str)

visible_width = 19 + max_l_name + max_l_port + max_r_name + max_r_port

if visible_width > inner or inner < 70:
    num_rows = num_items
    left_col = rendered_items
    max_l_name = max(len(x[1]) for x in left_col) if left_col else 0
    max_l_port = max(len(x[2]) for x in left_col) if left_col else 0
    visible_width = 8 + max_l_name + max_l_port
    table_rows = []
    for i in range(num_rows):
        l_type, l_name, l_port, l_dot = left_col[i]
        l_cell = f"{C_GRY}{l_type:<4}{C_R} {C_B}{l_name:<{max_l_name}}{C_R} {C_CYN}{l_port:<{max_l_port}}{C_R} {l_dot}"
        table_rows.append(l_cell)

pad_len = max(0, (inner - visible_width) // 2)
padding = " " * pad_len

header_title = "UNIFIED SYSTEM STACK & SERVICES"
header_pad = max(0, (inner - len(header_title)) // 2)
head_pad_str = " " * header_pad
print(f"{head_pad_str}{C_B}{C_CYN}{header_title}{C_R}")

border_char = "─" if no_color == 0 else "-"
border_line = padding + border_char * visible_width

print(border_line)
for row in table_rows:
    print(f"{padding}{row}")
print(border_line)

# 3. Credentials Row
# LOGIN user + password come from the DB-driven account SSOT (via
# mios-login-account, passed in as MIOS_LINUX_USER / MIOS_LOGIN_PASSWORD) --
# never the operator DISPLAY name. `pw` (service default) is only a fallback
# for the Forge admin password.
user = os.environ.get("MIOS_LINUX_USER") or "user"
login_pw = os.environ.get("MIOS_LOGIN_PASSWORD") or "user"
pw = os.environ.get("MIOS_DEFAULT_PASSWORD", "mios")
fpw = ""
if os.path.isfile("/etc/mios/forge/admin-password"):
    try:
        with open("/etc/mios/forge/admin-password") as f:
            fpw = f.read().strip()
    except Exception:
        pass
if not fpw:
    fpw = pw

cred_str = f"login {user}/{login_pw}   forge {user}/{fpw}"
cred_pad_str = " " * max(0, (inner - len(cred_str)) // 2)
print(f"{cred_pad_str}{C_GRY}{cred_str}{C_R}")
'
}

print_git_state() {
    if [[ ! -d /.git ]]; then
        section_header "Tree"
        printf '    %s  %s(/ is not yet a git working tree)%s\n' "$GLYPH_GIT" "$C_GRY" "$C_R"
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
    local str="    ${GLYPH_GIT}  ${branch}  +${ahead}/-${behind}   ${staged} staged  ${modified} modified  ${untracked} untracked"
    local pad=$(( (INNER - ${#str}) / 2 )); (( pad < 0 )) && pad=0; local padstr="$(hr_repeat ' ' "$pad")"
    section_header "Tree" "$padstr"
    printf '%s%s  %s%s%s  +%s/-%s   %s%d staged  %d modified  %d untracked%s\n' \
        "$padstr" "$GLYPH_GIT" "$C_B" "$branch" "$C_R" "$ahead" "$behind" \
        "$C_GRY" "$staged" "$modified" "$untracked" "$C_R"
}

print_loop_hint() {
    local pad=$(( (INNER - 74) / 2 )); (( pad < 0 )) && pad=0; local padstr="$(hr_repeat ' ' "$pad")"
    printf '\n%s%sEdit /  ->  git commit  ->  git push  ->  Forgejo Runner  ->  bootc switch%s\n' "$padstr" "$C_D" "$C_R"
    local rh_len=$(( 56 + ${#MIOS_LINUX_USER} * 2 ))
    local rh_pad=$(( (INNER - rh_len) / 2 )); (( rh_pad < 0 )) && rh_pad=0; local rh_padstr="$(hr_repeat ' ' "$rh_pad")"
    printf '%s%sRebuild now: git -C / push http://%s@localhost:3000/%s/mios.git%s\n' \
        "$rh_padstr" "$C_GRY" "$MIOS_LINUX_USER" "$MIOS_LINUX_USER" "$C_R"
}

print_services_block() {
    if [[ "$MODE" == "mini" ]]; then
        print_endpoints
    else
        print_unified_table
        print_git_state
    fi
}

# ── Fastfetch capture (logo suppressed; we render our own header) ────────────
# Kept for the legacy `--ticker` / `--no-frame` paths and as a fallback
# when [dashboard].rows is missing/unparseable.  The default render path
# now uses _dashboard_rows_render below for parity with the Windows-side
# Show-MiosDashboard.
print_fastfetch() {
    if ! command -v fastfetch >/dev/null 2>&1; then return; fi
    local local_cfg=/usr/share/mios/fastfetch/config.jsonc
    if [[ -r "$local_cfg" ]]; then
        fastfetch -c "$local_cfg" --logo none 2>/dev/null || fastfetch --logo none 2>/dev/null || true
    else
        fastfetch --logo none 2>/dev/null || true
    fi
}

# ── [dashboard] row-driven renderer (parity with Windows Show-MiosDashboard) ─
# Per "the dash is set GLOBALLY to Windows and
# Linux dashboards!! same settings!!!".  Reads mios.toml [dashboard].rows
# (a list of lists of field-keys) and emits one framed line per row,
# laying out fields side-by-side with equal column width.  Same field-
# key library as the Windows side -- host_os / cpu / gpu_* / ram / swap /
# disk_root / disk_home / kernel / shell / font / uptime.  disk_c /
# disk_m are accepted on Linux too (they fall back to disk_root).

# _df_human BYTES -- format as "<n.n>GiB" / "<n.n>TiB".
_df_human() {
    local b=$1
    if [[ -z "$b" ]] || [[ "$b" == "0" ]]; then printf '0GiB'; return; fi
    awk -v b="$b" 'BEGIN {
        gib = b / (1024*1024*1024)
        if (gib < 1024) { printf "%.1fGiB", gib }
        else            { printf "%.2fTiB", gib / 1024 }
    }'
}

# _dash_field KEY -- emit the rendered string for one field-key.
# Echoes empty string for unknown keys so unknown -> silently skipped.
_dash_field() {
    local k="$1"
    case "$k" in
        host_os)
            local user host os arch
            user="${MIOS_LINUX_USER:-${USER:-mios}}"
            host="$(hostname -s 2>/dev/null || echo localhost)"
            if [[ -r /etc/os-release ]]; then
                # shellcheck disable=SC1091
                os="$(. /etc/os-release; echo "${PRETTY_NAME:-$NAME}")"
            else
                os="$(uname -o 2>/dev/null || uname -s)"
            fi
            arch="$(uname -m)"
            printf '%s@%s -- %s %s' "$user" "$host" "$os" "$arch"
            ;;
        host)
            #  nf-fa-server U+F233 -- hostname only
            local h
            h="$(hostname -s 2>/dev/null || echo localhost)"
            printf $'\xef\x88\xb3'" %s" "$h"
            ;;
        version)
            #  nf-fa-tag U+F02B -- MiOS version + arch. VERSION ships
            # at the repo root (/VERSION on deployed hosts; mios.git's
            # working tree is overlaid AT /). Fall back to mios.toml
            # [meta].mios_version then "?" if neither is readable.
            local v
            for _vf in /VERSION /usr/share/mios/VERSION; do
                if [[ -r "$_vf" ]]; then v="$(cat "$_vf")"; break; fi
            done
            [[ -z "${v:-}" ]] && v="$(_mios_toml_value 'meta' 'mios_version' '?')"
            printf $'\xef\x80\xab'" MiOS v%s %s" "$v" "$(uname -m)"
            ;;
        date)
            # 󰃭 nf-md-calendar U+F00ED -- today's date, no time
            # (powerline already shows time).
            printf $'\xf3\xb0\x83\xad'" %s" "$(date '+%Y-%m-%d')"
            ;;
        user)
            #  nf-fa-user U+F007 -- username only
            local u
            u="${MIOS_LINUX_USER:-${USER:-mios}}"
            printf $'\xef\x80\x87'" %s" "$u"
            ;;
        cpu)
            local model cores clk
            model="$(awk -F: '/^model name/ { sub(/^[[:space:]]+/, "", $2); print $2; exit }' /proc/cpuinfo 2>/dev/null)"
            cores="$(grep -cE '^processor[[:space:]]*:' /proc/cpuinfo 2>/dev/null || echo 0)"
            # Max clock from /sys if available, else cpufreq scaling_max_freq, else /proc.
            if [[ -r /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq ]]; then
                clk=$(awk '{ printf "%.2f", $1 / 1000000 }' /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq)
            else
                clk=$(awk -F: '/^cpu MHz/ { printf "%.2f", $2/1000; exit }' /proc/cpuinfo 2>/dev/null)
            fi
            model="${model//(R)/}"; model="${model//(TM)/}"
            model="$(echo "$model" | sed -E 's/[[:space:]]*@.*$//; s/[[:space:]]*Processor[[:space:]]*//; s/[[:space:]]+/ /g')"
            if [[ -n "$clk" ]]; then printf ' %s %sGHz (%sc)' "$model" "$clk" "$cores"
            else                     printf ' %s (%sc)' "$model" "$cores"; fi
            ;;
        gpu_discrete|gpu_integrated)
            local pat
            if [[ "$k" == "gpu_discrete" ]]; then pat='NVIDIA|GeForce|Radeon RX|Radeon Pro|Quadro|RTX|GTX'
            else                                  pat='Intel.*Graphics|UHD Graphics|Iris|Radeon\(TM\) Graphics|integrated'; fi
            local line=""
            if command -v lspci >/dev/null 2>&1; then
                line="$(lspci -mm 2>/dev/null | grep -iE 'VGA|3D|Display' | grep -iE "$pat" | head -1)"
                # Strip class label, keep vendor + device.
                line="$(echo "$line" | awk -F'"' '{ printf "%s %s", $4, $6 }')"
            fi
            if [[ -z "$line" ]]; then printf ' --'
            else                       printf ' %s' "$line"; fi
            ;;
        ram)
            local total used free pct
            total=$(awk '/^MemTotal:/  { print $2 }' /proc/meminfo)
            free=$( awk '/^MemAvailable:/{ print $2 }' /proc/meminfo)
            [[ -z "$free" ]] && free=$(awk '/^MemFree:/{ print $2 }' /proc/meminfo)
            used=$((total - free))
            pct=$(( total > 0 ? (used * 100 / total) : 0 ))
            printf ' %.1f / %.1fGiB (%d%%)' \
                "$(awk -v u="$used" 'BEGIN{print u/1024/1024}')" \
                "$(awk -v t="$total" 'BEGIN{print t/1024/1024}')" \
                "$pct"
            ;;
        swap)
            local total used pct
            total=$(awk '/^SwapTotal:/{ print $2 }' /proc/meminfo)
            local sfree
            sfree=$(awk '/^SwapFree:/ { print $2 }' /proc/meminfo)
            used=$((total - sfree))
            if [[ -z "$total" ]] || [[ "$total" == "0" ]]; then printf ' --'; return; fi
            pct=$(( total > 0 ? (used * 100 / total) : 0 ))
            printf ' %.1f / %.1fGiB (%d%%)' \
                "$(awk -v u="$used" 'BEGIN{print u/1024/1024}')" \
                "$(awk -v t="$total" 'BEGIN{print t/1024/1024}')" \
                "$pct"
            ;;
        disk_root|disk_c)
            _dash_disk / "/"
            ;;
        disk_home|disk_m)
            if mountpoint -q /home 2>/dev/null; then _dash_disk /home "/home"
            elif [[ "$k" == "disk_m" ]] && mountpoint -q /mnt/m 2>/dev/null; then _dash_disk /mnt/m "M:"
            else _dash_disk / "/"; fi
            ;;
        disk_var)
            if mountpoint -q /var 2>/dev/null; then _dash_disk /var "/var"
            else _dash_disk / "/"; fi
            ;;
        kernel)
            printf ' %s' "$(uname -r)"
            ;;
        shell)
            local sh ver
            sh="$(basename "${SHELL:-bash}")"
            case "$sh" in
                bash) ver="$(bash --version 2>/dev/null | head -1 | sed -E 's/.*version ([0-9.]+).*/\1/')" ;;
                zsh)  ver="$(zsh --version 2>/dev/null  | awk '{print $2}')" ;;
                fish) ver="$(fish --version 2>/dev/null | awk '{print $3}')" ;;
                pwsh|pwsh.exe) ver="$(pwsh --version 2>/dev/null | awk '{print $2}')" ;;
                *)    ver=""
            esac
            if [[ -n "$ver" ]]; then printf ' %s %s' "$sh" "$ver"
            else                     printf ' %s' "$sh"; fi
            ;;
        font)
            # Resolves through mios.toml [theme.font].family / .size --
            # Linux terminals usually inherit the user's terminal font
            # config, but the SSOT-correct value lives in mios.toml.
            local family size
            family="$(_mios_toml_value "theme.font" "family" "GeistMono Nerd Font Mono")"
            size="$(_mios_toml_value "theme.font" "size" "12")"
            printf ' %s %spt' "$family" "$size"
            ;;
        uptime)
            local up_s d h m
            up_s=$(awk '{print int($1)}' /proc/uptime 2>/dev/null)
            [[ -z "$up_s" ]] && { printf ' --'; return; }
            d=$((up_s / 86400)); h=$(((up_s % 86400) / 3600)); m=$(((up_s % 3600) / 60))
            printf ' %dd %dh %dm' "$d" "$h" "$m"
            ;;
        *)
            # Unknown field-key -- emit empty string; renderer skips it.
            printf ''
            ;;
    esac
}

# _dash_disk MOUNT LABEL -- emit "<label>: <used> / <total>GiB (<pct>%)"
_dash_disk() {
    local mp="$1" lbl="$2"
    # Operator directive: drives and disks use their drive letter
    # (or mountpoint) directly -- no icon prefix. Frees horizontal
    # room and matches the at-a-glance "M:" / "/" identity the
    # operator already uses on the host filesystem.
    if ! command -v df >/dev/null 2>&1; then printf '%s --' "$lbl"; return; fi
    local out total used pct
    out="$(df -B1 --output=size,used,pcent "$mp" 2>/dev/null | tail -n +2 | awk '{ print $1, $2, $3 }')"
    if [[ -z "$out" ]]; then printf '%s --' "$lbl"; return; fi
    read -r total used pct <<< "$out"
    pct="${pct%%%}"
    printf '%s %.1f / %.1fGiB (%s%%)' "$lbl" \
        "$(awk -v u="$used"  'BEGIN{print u/1024/1024/1024}')" \
        "$(awk -v t="$total" 'BEGIN{print t/1024/1024/1024}')" \
        "$pct"
}

# _dashboard_rows_render -- read [dashboard].rows and emit one line per
# row with fields padded to equal column width.  Pipes through
# frame_filter for the framed render.  Awk-driven extraction of the
# nested-array TOML (rows = [["a"],["b","c"]]) since /usr/bin/awk and
# bash regex both struggle with that shape; we tokenize char-by-char.
_dashboard_rows_parse() {
    local toml="${MIOS_TOML:-/usr/share/mios/mios.toml}"
    [[ -r "$toml" ]] || return 1
    awk '
        # Find [dashboard] section
        /^\[/ {
            line = $0; sub(/[[:space:]]*#.*$/, "", line)
            in_dash = (line == "[dashboard]") ? 1 : 0
            next
        }
        in_dash && /^[[:space:]]*rows[[:space:]]*=[[:space:]]*\[/ { capturing = 1 }
        capturing { buf = buf $0 "\n" }
        capturing && /^\][[:space:]]*$/ { capturing = 0; in_dash = 0 }
        END {
            if (buf == "") exit 1
            # Strip everything before the first [[ and after the last ]]
            n = split(buf, lines, "\n")
            # Walk char by char, find each [...] inner row
            text = buf
            depth = 0
            row = ""
            current = ""
            in_str = 0
            for (i = 1; i <= length(text); i++) {
                c = substr(text, i, 1)
                if (c == "\"") { in_str = !in_str; current = current c; continue }
                if (in_str)    { current = current c; continue }
                if (c == "[")  { depth++; if (depth == 2) current = ""; continue }
                if (c == "]")  {
                    depth--
                    if (depth == 1 && current != "") {
                        # Emit one row -- normalize whitespace + commas
                        gsub(/[[:space:]]+/, " ", current)
                        gsub(/^[[:space:]]+|[[:space:]]+$/, "", current)
                        print current
                        current = ""
                    }
                    continue
                }
                if (depth >= 2) current = current c
            }
        }
    ' "$toml"
}

_dashboard_rows_render() {
    local rows
    rows="$(_dashboard_rows_parse 2>/dev/null)"
    if [[ -z "$rows" ]]; then
        rows='"cpu", "gpu_discrete"
"ram", "swap"
"disk_root", "disk_home"'
    fi

    local parsed_rows=()
    local max_c1=0 max_c2=0
    local row n field val v1 v2
    
    while IFS= read -r row; do
        [[ -z "$row" ]] && continue
        IFS=',' read -ra fields <<< "$row"
        local trimmed=()
        for field in "${fields[@]}"; do
            field="${field#"${field%%[![:space:]]*}"}"
            field="${field%"${field##*[![:space:]]}"}"
            field="${field#\"}"; field="${field%\"}"
            [[ -n "$field" ]] && trimmed+=("$field")
        done
        n=${#trimmed[@]}
        (( n == 0 )) && continue
        
        v1="$(_dash_field "${trimmed[0]}")"
        v2=""
        if (( n > 1 )); then
            v2="$(_dash_field "${trimmed[1]}")"
        fi
        
        (( ${#v1} > max_c1 )) && max_c1=${#v1}
        (( ${#v2} > max_c2 )) && max_c2=${#v2}
        
        parsed_rows+=("${v1}|${v2}")
    done <<< "$rows"
    
    local total_w=$(( max_c1 + 4 + max_c2 ))
    if (( total_w > INNER )); then
        if (( max_c1 + 4 + max_c2 > INNER )); then
            max_c1=$(( INNER - 4 - max_c2 ))
            if (( max_c1 < 15 )); then
                max_c1=$(( (INNER - 4) / 2 ))
                max_c2=$(( INNER - 4 - max_c1 ))
            fi
        fi
        total_w=$(( max_c1 + 4 + max_c2 ))
    fi

    local row_pad=$(( (INNER - total_w) / 2 ))
    (( row_pad < 0 )) && row_pad=0
    local row_padstr="$(hr_repeat ' ' "$row_pad")"
    
    for r in "${parsed_rows[@]}"; do
        IFS='|' read -r v1 v2 <<< "$r"
        if (( ${#v1} > max_c1 )); then
            v1="${v1:0:$((max_c1 - 1))}…"
        fi
        if (( ${#v2} > max_c2 )); then
            v2="${v2:0:$((max_c2 - 1))}…"
        fi
        
        local pad1=$(( max_c1 - ${#v1} ))
        (( pad1 < 0 )) && pad1=0
        local pad1str="$(hr_repeat ' ' "$pad1")"
        
        if [[ -n "$v2" ]]; then
            printf '%s%s%s    %s\n' "$row_padstr" "$v1" "$pad1str" "$v2"
        else
            printf '%s%s\n' "$row_padstr" "$v1"
        fi
    done
}

render_dashboard() {
    case "$MODE" in
        services-only)
            # Used by fastfetch as a custom command-module embedded inside its
            # column layout. Frame would collide with fastfetch's borders, so
            # we render UNFRAMED here regardless of --no-frame.
            print_services_block
            ;;
        table-only)
            # Just the live UNIFIED service table (+ credentials line), UNFRAMED.
            # The Windows dashboard bridges to this via wsl and embeds it in its
            # own frame, so BOTH dashboards render the SAME live service list
            # from ONE source (no drift).
            print_unified_table
            ;;
        endpoints-only)
            # The COMPACT endpoint table (fits 80x20), UNFRAMED. The Windows
            # `mios mini` bridges to this so its compact view matches the Linux
            # `mios mini` (which renders print_endpoints), while `mios dash`
            # uses the fuller --table-only. One source, no drift.
            print_endpoints
            ;;
        *)
            if [[ $NO_FRAME -eq 1 ]]; then
                print_ascii_header
                print_title
                _dashboard_rows_render
                print_services_block
                print_loop_hint
                _dev_cmd="$(_ssh_dev_cmd)"
                [[ -n "$_dev_cmd" ]] && printf 'dev shell: %s\n' "$_dev_cmd"
            else
                # Capture each section, pipe through frame_filter so each
                # line is wrapped and truncated to fit INNER chars exactly.
                # The metric block uses [dashboard].rows from mios.toml --
                # matches the Windows-side Show-MiosDashboard exactly so
                # the operator sees the same compact side-by-side layout
                # on both hosts.  Set MIOS_DASH_LEGACY=1 to fall back to
                # the verbose fastfetch + services + loop-hint render
                # (one metric per row, no [dashboard].rows).
                frame_top
                # Full `mios dash` (MODE=default) shows the ASCII banner +
                # every section + verb hints regardless of terminal height
                # -- operator may scroll. `mios mini` (MODE=mini) drops the
                # logo to fit in 18 rows on an 80x20 terminal.
                if [[ "$MODE" != "mini" ]]; then
                    print_ascii_header | frame_filter
                    frame_divide
                fi
                { print_title; } | frame_filter
                frame_divide
                if [[ "${MIOS_DASH_LEGACY:-0}" == "1" ]]; then
                    print_fastfetch     | frame_filter
                    frame_divide
                    print_services_block | frame_filter
                    frame_divide
                    print_loop_hint     | frame_filter
                else
                    _dashboard_rows_render | frame_filter
                    # Keep the Linux-only services block when explicitly
                    # requested via MIOS_DASH_SERVICES=1 OR when the
                    # configurator toggled [dashboard].show_services=true.
                    # Bash's `local` only works inside a function -- this
                    # branch is at script scope (case/esac body), so use
                    # a plain assignment instead (hit
                    # `local: can only be used in a function` here).
                    _show_services="$(_mios_toml_value 'dashboard' 'show_services' 'false')"
                    # mini ALWAYS shows the abbreviated services block --
                    # that's the whole point of mini (hardware + a few
                    # services, no Stack/Tree/credentials).
                    if [[ "$MODE" == "mini" ]] || [[ "${MIOS_DASH_SERVICES:-0}" == "1" ]] || [[ "$_show_services" == "true" ]]; then
                        frame_divide
                        print_services_block | frame_filter
                    fi
                    # Verb hints -- full dash only. Mini drops them to
                    # leave room for the prompt. Reads [dashboard].verb_hint
                    # from mios.toml so operators rebrand the hint line.
                    if [[ "$MODE" != "mini" ]]; then
                        # Default verb list refreshed to match the
                        # current /usr/bin/mios KNOWN_VERBS surface. Operator
                        # override via mios.toml [dashboard].verb_hint.
                        _verb_hint="$(_mios_toml_value 'dashboard' 'verb_hint' 'build  config  dash  mini  ai  code  dev  summary  user  pull  update  help')"
                        if [[ -n "$_verb_hint" ]]; then
                            frame_divide
                            hint_str=" mios ${_verb_hint} "
                            hint_pad=$(( (INNER - ${#hint_str}) / 2 ))
                            (( hint_pad < 0 )) && hint_pad=0
                            hint_padstr="$(hr_repeat ' ' "$hint_pad")"
                            printf '%s%s%s%s\n' "$hint_padstr" "$C_GRY" "$hint_str" "$C_R" | frame_filter
                        fi
                    fi
                fi
                frame_bot
                # LIVE, copy-pasteable "SSH from your host into the code-server
                # container at the MiOS tree" command. Printed UNFRAMED below
                # the box so it is never truncated -- it must stay usable in
                # full. Every field (port / container / workdir / user)
                # resolves from the running system via _ssh_dev_cmd; shown on
                # both `mios dash` and `mios mini`.
                _dev_cmd="$(_ssh_dev_cmd)"
                if [[ -n "$_dev_cmd" ]]; then
                    _dev_line="dev shell: ${_dev_cmd}"
                    _dev_pad=$(( (WIDTH - ${#_dev_line}) / 2 ))
                    (( _dev_pad < 0 )) && _dev_pad=0
                    printf '%s%sdev shell:%s %s\n' \
                        "$(hr_repeat ' ' "$_dev_pad")" "$C_B$C_CYN" "$C_R" "$_dev_cmd"
                fi
            fi
            ;;
    esac
}

# ── Main ─────────────────────────────────────────────────────────────────────
if [[ $MONITOR -eq 1 ]]; then
    trap "clear; exit 0" INT TERM
    while true; do
        printf '\033[H\033[J'
        render_dashboard
        [[ "${MIOS_MONITOR_ONCE:-0}" == "1" ]] && exit 0
        sleep 5
    done
else
    render_dashboard
fi

exit 0
