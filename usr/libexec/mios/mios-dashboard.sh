#!/usr/bin/env bash
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
for arg in "$@"; do
    case "$arg" in
        --services-only) MODE="services-only"; NO_FRAME=1 ;;
        --mini)          MODE="mini" ;;
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
# Operator 2026-05-09: dashboard inside MiOS-DEV (WSL bash) was rendering
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
# Resolution order: install.env-staged MIOS_USER (canonical) > legacy
# MIOS_LINUX_USER alias > literal 'mios'. Critically NEVER falls back
# to $USER -- the service `mios-dashboard-issue.service` runs as root,
# so $USER == 'root' would render `login: root / mios` in the pre-login
# banner even though the configured login user is 'mios'. The banner
# describes the OPERATOR'S login surface, not the running process.
MIOS_LINUX_USER="${MIOS_USER:-${MIOS_LINUX_USER:-mios}}"
[[ -z "${MIOS_VERSION:-}" ]] && MIOS_VERSION="$(cat /usr/share/mios/VERSION 2>/dev/null || cat /etc/mios/VERSION 2>/dev/null || echo "0.2.4")"
MIOS_AI_MODEL="${MIOS_AI_MODEL:-qwen3.5:2b}"

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
# Inline (no leading blank) to keep the dashboard inside an 18-row
# budget on an 80x20 terminal -- each section header now costs 1 row
# instead of 2.
section_header() {
    printf '  %s%s%s%s\n' "$C_B" "$C_CYN" "$1" "$C_R"
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

# Resolve a [ports].<key> value from the layered mios.toml SSOT.
# Honors ~/.config/mios > /etc/mios > /usr/share/mios precedence so an
# operator port-edit in mios.toml flows through to every URL on this
# dashboard without re-baking. Falls back to $2 if no layer matches.
_mios_port() {
    local key=$1 default=$2 t v
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

# ── Sections (each printed UNFRAMED; frame_filter wraps after capture) ───────
print_endpoints() {
    local _user _pw _fpw
    _user="${MIOS_LINUX_USER:-${MIOS_USER:-mios}}"
    _pw="${MIOS_DEFAULT_PASSWORD:-mios}"
    _fpw="$(cat /etc/mios/forge/admin-password 2>/dev/null)"
    [[ -z "$_fpw" ]]    && _fpw="$_pw"

    local _p_forge _p_cockpit _p_ollama _p_searxng _p_hermes _p_dash _p_code
    _p_forge=$(_mios_port forge_http 3000)
    _p_cockpit=$(_mios_port cockpit 9090)
    _p_ollama=$(_mios_port ollama 11434)
    _p_searxng=$(_mios_port searxng 8888)
    _p_hermes=$(_mios_port hermes 8642)
    _p_dash=$(_mios_port hermes_dashboard 9119)
    _p_code=$(_mios_port code_server 8080)

    local d_forge d_ollama d_cockpit d_searxng d_hermes d_dash d_code
    d_forge=$(ep_dot     "http://localhost:${_p_forge}/api/v1/version")
    d_ollama=$(ep_dot    "http://localhost:${_p_ollama}/")
    d_cockpit=$(ep_dot   "https://localhost:${_p_cockpit}/")
    d_searxng=$(ep_dot   "http://localhost:${_p_searxng}/")
    d_hermes=$(ep_dot    "http://localhost:${_p_hermes}/health")
    d_dash=$(ep_dot      "http://localhost:${_p_dash}/")
    d_code=$(ep_dot      "http://localhost:${_p_code}/")

    # Mini: count recap + 4 clickable hyperlink rows (Cockpit, Code,
    # Workspace, Search) per operator spec 2026-05-11 ("you STILL have
    # 4 rows available... can include some links to Cockpit, Code,
    # hermes workspace, search"). Modern terminals (WT, Ptyxis, Konsole)
    # auto-detect bare http(s):// URLs as OSC 8 hyperlinks even without
    # explicit escape sequences, so each row's URL is click-to-launch.
    if [[ "$MODE" == "mini" ]]; then
        local n_up=0 n_down=0
        for _d in "$d_forge" "$d_ollama" "$d_cockpit" "$d_searxng" \
                  "$d_hermes" "$d_workspace" "$d_code"; do
            case "$_d" in
                *"$DOT_UP"*) n_up=$((n_up + 1)) ;;
                *)           n_down=$((n_down + 1)) ;;
            esac
        done
        printf '  %s%s%s %s%d up%s    %s%s%s %s%d down%s    %sforge:%s  hermes:%s  ollama:%s%s\n' \
            "$C_GRN" "$DOT_UP" "$C_R"   "$C_B"   "$n_up"   "$C_R" \
            "$C_GRY" "$DOT_DOWN" "$C_R" "$C_GRY" "$n_down" "$C_R" \
            "$C_GRY" "$_p_forge" "$_p_hermes" "$_p_ollama" "$C_R"
        local link_fmt='  %s %-10s %s%s%s\n'
        printf "$link_fmt" "$d_cockpit"   "Cockpit"   "$C_D" "https://localhost:${_p_cockpit}/"  "$C_R"
        printf "$link_fmt" "$d_code"      "Code"      "$C_D" "http://localhost:${_p_code}/"      "$C_R"
        printf "$link_fmt" "$d_workspace" "Workspace" "$C_D" "http://localhost:${_p_workspace}/" "$C_R"
        printf "$link_fmt" "$d_searxng"   "Search"    "$C_D" "http://localhost:${_p_searxng}/"   "$C_R"
        return
    fi

    # Full dash: every service as "<dot> <Name> <full URL>" in a
    # 2-column grid -- the operator's "hyperlinks" requirement.
    # Modern terminals (WT, Ptyxis, Konsole) auto-detect bare URLs as
    # OSC 8 hyperlinks even without explicit escape sequences, so a
    # plain `http://localhost:PORT/` is clickable.
    section_header "Services"
    # Compact "name :port" cell -- name is an OSC 8 hyperlink, click
    # opens the service URL in the operator's default browser. The
    # frame_filter at the top of this script strips OSC 8 sequences
    # before counting visible width, so the multi-row 2-column layout
    # survives the framing pass cleanly (operator-confirmed 2026-05-13:
    # without OSC stripping in the framer, the ESC bytes inflated cell
    # widths past the row budget and the wrapper collapsed everything
    # to one line).
    #
    # Cell budget: dot(1)+sp(1)+name(9)+sp(1)+:port(6) = 18 cols
    # visible. Two cells + 2-space indent + 2-space row sep = 40 cols,
    # ~36 cols of slack inside the canonical 80-col frame.
    #
    # OSC 8 escape: \e]8;;URL\e\\TEXT\e]8;;\e\\ -- bash $'...' ANSI-C
    # quoting on $_esc converts \e to literal ESC at parse time, so
    # printf %s passes it through unchanged. Modern terminals (WT,
    # Ptyxis, Konsole, kitty, WezTerm, Alacritty, GNOME Terminal)
    # render the anchor text as a clickable link.
    local _esc=$'\e'
    local osc_lnk="${_esc}]8;;%s${_esc}\\%-9s${_esc}]8;;${_esc}\\"
    local cell_fmt="%s ${osc_lnk} %s:%-5s%s"
    local row_fmt='  %b  %b\n'
    local c_forge c_ollama c_cock c_srch c_herm c_dash c_code
    c_forge=$( printf  "$cell_fmt" "$d_forge"     "http://localhost:${_p_forge}/"     "Forge"     "$C_D" "$_p_forge"     "$C_R")
    c_ollama=$(printf  "$cell_fmt" "$d_ollama"    "http://localhost:${_p_ollama}/"    "Ollama"    "$C_D" "$_p_ollama"    "$C_R")
    c_cock=$(  printf  "$cell_fmt" "$d_cockpit"   "https://localhost:${_p_cockpit}/"  "Cockpit"   "$C_D" "$_p_cockpit"   "$C_R")
    c_srch=$(  printf  "$cell_fmt" "$d_searxng"   "http://localhost:${_p_searxng}/"   "Search"    "$C_D" "$_p_searxng"   "$C_R")
    c_herm=$(  printf  "$cell_fmt" "$d_hermes"    "http://localhost:${_p_hermes}/v1"  "Hermes"    "$C_D" "$_p_hermes"    "$C_R")
    c_dash=$(  printf  "$cell_fmt" "$d_dash"      "http://localhost:${_p_dash}/"      "Dashboard" "$C_D" "$_p_dash"      "$C_R")
    c_code=$(  printf  "$cell_fmt" "$d_code"      "http://localhost:${_p_code}/"      "Code"      "$C_D" "$_p_code"      "$C_R")
    printf "$row_fmt" "$c_forge" "$c_ollama"
    printf "$row_fmt" "$c_cock"  "$c_srch"
    printf "$row_fmt" "$c_herm"  "$c_dash"
    printf '  %b\n' "$c_code"
    # Backing services -- no exposed URL but stack-critical (CI runner,
    # network bridge, cluster). Dot-only indicators so the operator sees
    # the full stack at a glance in `mios dash`. Operator 2026-05-11:
    # "mios dash(FULL) should show ALL services!!"
    local d_runner d_ceph d_k3s
    local s_runner s_ceph s_k3s
    s_runner=$(service_status mios-forgejo-runner.service); IFS='|' read -r _ d_runner _ <<< "$s_runner"
    s_ceph=$(  service_status mios-ceph.service);            IFS='|' read -r _ d_ceph   _ <<< "$s_ceph"
    s_k3s=$(   service_status mios-k3s.service);             IFS='|' read -r _ d_k3s    _ <<< "$s_k3s"
    [[ -z "$d_runner" ]] && d_runner="$DOT_DOWN"
    [[ -z "$d_ceph"   ]] && d_ceph="$DOT_DOWN"
    [[ -z "$d_k3s"    ]] && d_k3s="$DOT_DOWN"
    printf '  %s%s %s Runner%s    %s%s %s Ceph%s    %s%s %s K3s%s\n' \
        "$C_R" "$d_runner" "$C_D" "$C_R" \
        "$C_R" "$d_ceph"   "$C_D" "$C_R" \
        "$C_R" "$d_k3s"    "$C_D" "$C_R"
    # Credentials row (global MiOS password unless per-service override).
    printf '  %slogin %s/%s   forge %s/%s%s\n' \
        "$C_GRY" "$_user" "$_pw" "$_user" "$_fpw" "$C_R"
}

print_quadlets() {
    # Count-only summary instead of a 14-row listing. Full state:
    # `systemctl --no-pager list-units 'mios-*' ollama.service`.
    local svc info name dot color
    local n_active=0 n_starting=0 n_inactive=0 n_failed=0
    for svc in mios-forge mios-forgejo-runner mios-cockpit-link \
               mios-ceph mios-k3s ollama mios-searxng \
               mios-hermes mios-hermes-dashboard mios-hermes-workspace mios-code-server crowdsec-dashboard \
               mios-guacamole guacd guacamole-postgres; do
        info="$(service_status "${svc}.service")"
        IFS='|' read -r name dot color <<< "$info"
        case "$name" in
            active|running)      n_active=$((n_active + 1)) ;;
            activating|starting) n_starting=$((n_starting + 1)) ;;
            failed)              n_failed=$((n_failed + 1)) ;;
            *)                   n_inactive=$((n_inactive + 1)) ;;
        esac
    done
    section_header "Stack"
    printf '    %s  %s%d active%s   %s%d starting%s   %s%d inactive%s   %s%d failed%s\n' \
        "$GLYPH_QUADLETS" \
        "$C_GRN" "$n_active"   "$C_R" \
        "$C_YLW" "$n_starting" "$C_R" \
        "$C_GRY" "$n_inactive" "$C_R" \
        "$C_RED" "$n_failed"   "$C_R"
}

print_git_state() {
    section_header "Tree"
    if [[ ! -d /.git ]]; then
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
    printf '    %s  %s%s%s  +%s/-%s   %s%d staged  %d modified  %d untracked%s\n' \
        "$GLYPH_GIT" "$C_B" "$branch" "$C_R" "$ahead" "$behind" \
        "$C_GRY" "$staged" "$modified" "$untracked" "$C_R"
}

print_loop_hint() {
    printf '\n  %sEdit /  ->  git commit  ->  git push  ->  Forgejo Runner  ->  bootc switch%s\n' "$C_D" "$C_R"
    printf '  %sRebuild now: git -C / push http://%s@localhost:3000/%s/mios.git%s\n' \
        "$C_GRY" "$MIOS_LINUX_USER" "$MIOS_LINUX_USER" "$C_R"
}

print_services_block() {
    print_endpoints
    # Mini mode: only the endpoints (dots + names + ports). Skip the
    # credential row + Stack count + Tree git-state to leave shell-
    # rows free for the prompt. Default mode shows everything.
    if [[ "$MODE" != "mini" ]]; then
        print_quadlets
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
# Per operator 2026-05-09: "the dash is set GLOBALLY to Windows and
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
        # Vendor default (matches mios.toml [dashboard].rows default)
        rows='"host_os"
"cpu", "gpu_discrete"
"ram", "swap"
"disk_root", "disk_home"
"kernel", "shell", "font"'
    fi

    local row n colW cells field val
    while IFS= read -r row; do
        [[ -z "$row" ]] && continue
        # Strip surrounding "..." per token, comma-split.
        IFS=',' read -ra fields <<< "$row"
        # Trim + dequote each token.
        local trimmed=()
        for field in "${fields[@]}"; do
            field="${field#"${field%%[![:space:]]*}"}"
            field="${field%"${field##*[![:space:]]}"}"
            field="${field#\"}"; field="${field%\"}"
            [[ -n "$field" ]] && trimmed+=("$field")
        done
        n=${#trimmed[@]}
        (( n == 0 )) && continue
        colW=$(( (INNER - (n - 1) * 2) / n ))
        (( colW < 8 )) && colW=8

        local line="" pad
        local i=0
        for field in "${trimmed[@]}"; do
            val="$(_dash_field "$field")"
            # Truncate -- code-point safe via awk (mawk uses bytes; gawk does code points).
            if (( ${#val} > colW )); then
                val="${val:0:$((colW - 1))}…"
            fi
            # Pad to exact colW.
            pad=$((colW - ${#val}))
            (( pad < 0 )) && pad=0
            local padstr; padstr="$(hr_repeat ' ' "$pad")"
            if (( i == 0 )); then line="${val}${padstr}"
            else                  line="${line}  ${val}${padstr}"; fi
            i=$((i + 1))
        done
        # Trim trailing whitespace -- frame_filter will pad to INNER.
        line="${line%"${line##*[![:space:]]}"}"
        printf '%s\n' "$line"
    done <<< "$rows"
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
            _dashboard_rows_render
            print_services_block
            print_loop_hint
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
            # The MiOS banner is part of the ASCII header. In mini mode
            # (no ASCII header) the host/version/date row at the top of
            # [dashboard].rows carries the identity, so we skip the
            # standalone print_title banner -- otherwise mini would
            # show "MiOS v0.2.4" twice (banner + version row).
            if [[ "$MODE" != "mini" ]]; then
                { print_title; } | frame_filter
                frame_divide
            fi
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
                # a plain assignment instead (operator 2026-05-09 hit
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
                    _verb_hint="$(_mios_toml_value 'dashboard' 'verb_hint' 'build  config  dash  dev  pull  update  help')"
                    if [[ -n "$_verb_hint" ]]; then
                        frame_divide
                        printf '  %s mios %s%s\n' "$C_GRY" "$_verb_hint" "$C_R" | frame_filter
                    fi
                fi
            fi
            frame_bot
        fi
        ;;
esac

exit 0
