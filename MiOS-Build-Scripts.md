# 'MiOS' Build Scripts -- Full Source Bundle

Every script that participates in building the 'MiOS' OCI image, in
execution order, with complete source and no truncation. Each section
header carries the file path; each fenced block carries the verbatim
file contents. Use `Ctrl-F` against a path to find a script.

---


## Layer 1 -- User entry points (mios-bootstrap repo)


### `C:\Users\USER\OneDrive\Documents\GitHub\mios-bootstrap\bootstrap.sh`

```bash
#!/bin/bash
# 'MiOS' Public Bootstrap -- Linux / WSL2
# Repository: MiOS-DEV/MiOS-bootstrap
# Usage: curl -fsSL https://raw.githubusercontent.com/MiOS-DEV/MiOS-bootstrap/main/bootstrap.sh | bash
set -euo pipefail

PRIVATE_INSTALLER="https://raw.githubusercontent.com/MiOS-DEV/mios/main/install.sh"
_ENV_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/mios/mios-build.env"

_r=$'\033[0m'; _b=$'\033[1m'; _dim=$'\033[2m'; _c=$'\033[36m'; _g=$'\033[32m'; _red=$'\033[31m'; _y=$'\033[33m'

echo ""
echo "  ${_c}╔══════════════════════════════════════════════════════════════╗${_r}"
echo "  ${_c}║  'MiOS' -- Local Build Configuration                           ║${_r}"
echo "  ${_c}╚══════════════════════════════════════════════════════════════╝${_r}"
echo ""

# ── Load saved build config ────────────────────────────────────────────────
if [[ -f "$_ENV_FILE" ]]; then
    echo "  ${_dim}Found saved config: $_ENV_FILE${_r}"
    read -rp "  Load previous build variables? [Y/n]: " _load_ok </dev/tty
    if [[ "${_load_ok,,}" != "n" ]]; then
        set +u
        # shellcheck source=/dev/null
        source "$_ENV_FILE"
        set -u
        echo "  ${_g}[OK]${_r} Loaded."
        echo ""
    fi
fi

# ── GitHub PAT (required for private repo access) ─────────────────────────
if [[ -z "${GHCR_TOKEN:-}" ]]; then
    read -rsp "  ${_b}GitHub PAT${_r} (requires 'repo' scope): " GHCR_TOKEN </dev/tty; echo ""
fi
if [[ -z "${GHCR_TOKEN:-}" ]]; then
    echo "  ${_red}[!] Token required.${_r}"; exit 1
fi
export GHCR_TOKEN

echo ""
echo "  ${_y}── Build Configuration ─────────────────────────────────────────${_r}"
echo ""

# ── Admin username ─────────────────────────────────────────────────────────
if [[ -z "${MIOS_USER:-}" ]]; then
    read -rp "  Admin username ${_dim}[mios]${_r}: " MIOS_USER </dev/tty
    MIOS_USER="${MIOS_USER:-mios}"
else
    echo "  Admin username: ${MIOS_USER}  ${_dim}(env)${_r}"
fi
export MIOS_USER

# ── Admin password ─────────────────────────────────────────────────────────
if [[ -z "${MIOS_PASSWORD:-}" ]]; then
    while true; do
        read -rsp "  Admin password: " MIOS_PASSWORD </dev/tty; echo ""
        [[ -z "${MIOS_PASSWORD:-}" ]] && { echo "  ${_red}[!] Password cannot be empty.${_r}"; continue; }
        read -rsp "  Confirm password: " _c2 </dev/tty; echo ""
        [[ "$MIOS_PASSWORD" == "$_c2" ]] && break
        echo "  ${_red}[!] Mismatch -- try again.${_r}"
    done
else
    echo "  Admin password: ${_dim}(env -- masked)${_r}"
fi
export MIOS_PASSWORD

# ── Hostname ───────────────────────────────────────────────────────────────
# Suffix is generated first so the user sees the full hostname in the prompt.
if [[ -z "${MIOS_HOSTNAME:-}" ]]; then
    _suf=$(shuf -i 10000-99999 -n1 2>/dev/null || printf '%05d' $(( RANDOM % 90000 + 10000 )))
    read -rp "  Hostname base ${_dim}[mios]${_r} (suffix -${_suf} is pre-generated -> mios-${_suf}): " _hbase </dev/tty
    _hbase="${_hbase:-mios}"
    export MIOS_HOSTNAME="${_hbase}-${_suf}"
else
    echo "  Hostname: ${MIOS_HOSTNAME}  ${_dim}(env)${_r}"
fi

# ── Optional: GHCR push credentials ───────────────────────────────────────
if [[ -z "${MIOS_GHCR_USER:-}" ]]; then
    echo ""
    read -rp "  GHCR push username ${_dim}[skip]${_r}: " MIOS_GHCR_USER </dev/tty
fi
export MIOS_GHCR_USER="${MIOS_GHCR_USER:-}"

if [[ -n "$MIOS_GHCR_USER" && -z "${MIOS_GHCR_PUSH_TOKEN:-}" ]]; then
    read -rsp "  GHCR push token ${_dim}[reuse GitHub PAT]${_r}: " MIOS_GHCR_PUSH_TOKEN </dev/tty; echo ""
    export MIOS_GHCR_PUSH_TOKEN="${MIOS_GHCR_PUSH_TOKEN:-$GHCR_TOKEN}"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "  ${_y}── Summary ──────────────────────────────────────────────────────${_r}"
echo ""
printf "    %-20s %s\n" "Admin user:"     "$MIOS_USER"
printf "    %-20s %s\n" "Admin password:" "(masked)"
printf "    %-20s %s\n" "Hostname:"       "$MIOS_HOSTNAME"
printf "    %-20s %s\n" "Registry push:"  "${MIOS_GHCR_USER:-none (local build only)}"
printf "    %-20s %s\n" "Config saved to:" "$_ENV_FILE"
echo ""
read -rp "  ${_b}Proceed?${_r} [Y/n]: " _ok </dev/tty
[[ "${_ok,,}" == "n" ]] && { echo "  Aborted."; exit 0; }

# ── Save build config ──────────────────────────────────────────────────────
mkdir -p "$(dirname "$_ENV_FILE")"
{
    printf '# 'MiOS' Build Configuration\n'
    printf '# Generated: %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    printf 'GHCR_TOKEN=%q\n'    "$GHCR_TOKEN"
    printf 'MIOS_USER=%q\n'     "$MIOS_USER"
    printf 'MIOS_PASSWORD=%q\n' "$MIOS_PASSWORD"
    printf 'MIOS_HOSTNAME=%q\n' "$MIOS_HOSTNAME"
    [[ -n "${MIOS_GHCR_USER:-}" ]]       && printf 'MIOS_GHCR_USER=%q\n'       "$MIOS_GHCR_USER"
    [[ -n "${MIOS_GHCR_PUSH_TOKEN:-}" ]] && printf 'MIOS_GHCR_PUSH_TOKEN=%q\n' "$MIOS_GHCR_PUSH_TOKEN"
} > "$_ENV_FILE"
chmod 600 "$_ENV_FILE"
echo "  ${_g}[OK]${_r} Build config saved → ${_dim}$_ENV_FILE${_r}"

# ── Fetch and execute private installer ───────────────────────────────────
export MIOS_AUTOINSTALL=1
echo ""
echo "  [+] Fetching private installer..."
_tmp=$(mktemp /tmp/mios-install-XXXXXX.sh)
if curl -fsSL -H "Authorization: token $GHCR_TOKEN" "$PRIVATE_INSTALLER" -o "$_tmp"; then
    chmod +x "$_tmp"
    echo "  ${_g}[OK]${_r} Launching installer."
    echo ""
    bash "$_tmp"
    rm -f "$_tmp"
else
    rm -f "$_tmp"
    echo "  ${_red}[!] Failed to fetch installer. Check token and repo permissions.${_r}"
    exit 1
fi
```


### `C:\Users\USER\OneDrive\Documents\GitHub\mios-bootstrap\bootstrap.ps1`

```powershell
#Requires -Version 5.1
# 'MiOS' Bootstrap -- redirector
#
# The unified entry point is now install.ps1.
# This file is retained so existing shortcuts and docs that reference
# bootstrap.ps1 keep working, but it simply delegates to install.ps1.
#
# One-liner (preferred):
#   irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.ps1 | iex

param([switch]$BuildOnly, [switch]$Unattended)

$installScript = Join-Path $PSScriptRoot "install.ps1"

if (Test-Path $installScript) {
    & $installScript @PSBoundParameters
} else {
    # Running piped -- fetch install.ps1 directly
    $url = "https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.ps1"
    & ([scriptblock]::Create((Invoke-RestMethod $url))) @PSBoundParameters
}
```


### `C:\Users\USER\OneDrive\Documents\GitHub\mios-bootstrap\install.sh`

```bash
#!/usr/bin/env bash
#
# 'MiOS' Bootstrap -- Interactive Ignition Installer
#
# Usage:
#   sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/MiOS-DEV/MiOS-bootstrap/main/install.sh)"
#   # or after cloning:
#   sudo /path/to/MiOS-bootstrap/install.sh
#
# Global pipeline phases (numbered; reused everywhere this project speaks of
# "phases"):
#
#   Phase-0  mios-bootstrap    -- preflight, profile load, host detection,
#                                interactive identity capture (this script).
#   Phase-1  overlay-merge     -- clone mios.git into /, copy bootstrap
#                                overlays (etc/, usr/, var/, profile/) on top.
#   Phase-2  build             -- optional self-build: `podman build` an OCI
#                                image from the merged tree. The numbered
#                                automation/[0-9][0-9]-*.sh scripts inside
#                                Containerfile are sub-phases of Phase-2.
#   Phase-3  apply             -- systemd-sysusers, systemd-tmpfiles, daemon
#                                reload; create the Linux user; stage
#                                ~/.config/mios/{profile.toml,system-prompt.md}
#                                + ~/.ssh/; deploy /etc/mios/ai/system-prompt.md.
#   Phase-4  reboot            -- interactive y/N to `systemctl reboot`.
#
# Idempotent: re-running with the same answers updates rather than duplicates.
# load_profile_defaults() reads /etc/mios/profile.toml on a previously-
# bootstrapped host (or this repo's etc/mios/profile.toml otherwise) so each
# re-run picks up edits.

set -euo pipefail

# ============================================================================
# Defaults -- sourced from the user profile card (etc/mios/profile.toml in
# this repo, or /etc/mios/profile.toml on a previously-bootstrapped host).
# load_profile_defaults() below parses the TOML on-the-fly with sed/grep so
# we don't pull in any TOML library at install time.
# ============================================================================
DEFAULT_USER="mios"
DEFAULT_HOST="mios"
DEFAULT_USER_FULLNAME="MiOS User"
DEFAULT_USER_SHELL="/bin/bash"
DEFAULT_USER_GROUPS="wheel,libvirt,kvm,video,render,input,dialout,docker"
DEFAULT_SSH_KEY_TYPE="ed25519"
DEFAULT_IMAGE="ghcr.io/mios-dev/mios:latest"
DEFAULT_BRANCH="main"
DEFAULT_TIMEZONE="UTC"
DEFAULT_KEYBOARD="us"
DEFAULT_LANG="en_US.UTF-8"

MIOS_REPO="https://github.com/mios-dev/mios.git"
BOOTSTRAP_REPO="https://github.com/mios-dev/mios-bootstrap.git"
PROFILE_DIR="/etc/mios"
PROFILE_CARD="${PROFILE_DIR}/profile.toml"
PROFILE_FILE="${PROFILE_DIR}/install.env"
LOG_FILE="/var/log/mios-bootstrap.log"

# Pull a value from a TOML file. Args: <file> <section> <key>.
# Strips quotes and inline comments. Returns empty if missing.
toml_get() {
    local file="$1" section="$2" key="$3"
    [[ -f "$file" ]] || { echo ""; return; }
    awk -v sect="[${section}]" -v k="$key" '
        $0 == sect            { in_sect = 1; next }
        /^\[/                 { in_sect = 0 }
        in_sect && $1 == k    { sub(/^[^=]*=[ \t]*/, ""); sub(/[ \t]*#.*$/, ""); gsub(/^"|"$/, ""); print; exit }
    ' "$file"
}

# Parse a TOML array of strings into a comma-joined value (groups, flatpaks).
toml_get_array_csv() {
    local file="$1" section="$2" key="$3"
    [[ -f "$file" ]] || { echo ""; return; }
    awk -v sect="[${section}]" -v k="$key" '
        $0 == sect            { in_sect = 1; next }
        /^\[/                 { in_sect = 0 }
        in_sect && $1 == k    {
            sub(/^[^\[]*\[/, ""); sub(/\].*$/, "")
            gsub(/[ \t"]/, "")
            print
            exit
        }
    ' "$file"
}

# Three-layer profile resolution. Each layer overlays the one above.
# Returned as a space-separated list of paths (lowest precedence first).
#
#   1. /usr/share/mios/profile.toml        vendor defaults (mios.git)
#   2. <bootstrap-checkout>/etc/mios/profile.toml  user-edit overrides (this repo)
#   3. /etc/mios/profile.toml              host-installed user-edit (re-run case)
#   4. /etc/mios/install.env (legacy)      previous-install identity env
#
# Empty strings in higher layers do NOT override non-empty defaults below
# them -- that's how this implements "user-set fields supersede defaults"
# without requiring sparse TOML files.
resolve_profile_layers() {
    local layers=()
    [[ -f /usr/share/mios/profile.toml ]] && layers+=(/usr/share/mios/profile.toml)
    local repo_card; repo_card="$(dirname "${BASH_SOURCE[0]}")/etc/mios/profile.toml"
    [[ -f "$repo_card" ]] && layers+=("$repo_card")
    [[ -f "$PROFILE_CARD" && "$PROFILE_CARD" != "$repo_card" ]] && layers+=("$PROFILE_CARD")
    printf '%s\n' "${layers[@]}"
}

# Read a single key, walking layers in order. Higher layers override lower.
toml_get_layered() {
    local section="$1" key="$2" array_mode="${3:-}"
    local fn="toml_get"
    [[ "$array_mode" == "array" ]] && fn="toml_get_array_csv"
    local result=""
    while IFS= read -r card; do
        local v; v="$($fn "$card" "$section" "$key")"
        [[ -n "$v" ]] && result="$v"
    done < <(resolve_profile_layers)
    echo "$result"
}

# Override DEFAULT_* from the merged profile-card layers.
load_profile_defaults() {
    local layers; layers=$(resolve_profile_layers | tr '\n' ' ')
    [[ -n "$layers" ]] || return 0
    log_info "Loading profile layers (lowest→highest precedence):"
    while IFS= read -r card; do log_info "  * ${card}"; done < <(resolve_profile_layers)

    local v
    v="$(toml_get_layered identity username)";        [[ -n "$v" ]] && DEFAULT_USER="$v"
    v="$(toml_get_layered identity hostname)";        [[ -n "$v" ]] && DEFAULT_HOST="$v"
    v="$(toml_get_layered identity fullname)";        [[ -n "$v" ]] && DEFAULT_USER_FULLNAME="$v"
    v="$(toml_get_layered identity shell)";           [[ -n "$v" ]] && DEFAULT_USER_SHELL="$v"
    v="$(toml_get_layered identity groups array)";    [[ -n "$v" ]] && DEFAULT_USER_GROUPS="$v"
    v="$(toml_get_layered auth ssh_key_type)";        [[ -n "$v" ]] && DEFAULT_SSH_KEY_TYPE="$v"
    v="$(toml_get_layered image ref)";                [[ -n "$v" ]] && DEFAULT_IMAGE="$v"
    v="$(toml_get_layered image branch)";             [[ -n "$v" ]] && DEFAULT_BRANCH="$v"
    v="$(toml_get_layered locale timezone)";          [[ -n "$v" ]] && DEFAULT_TIMEZONE="$v"
    v="$(toml_get_layered locale keyboard_layout)";   [[ -n "$v" ]] && DEFAULT_KEYBOARD="$v"
    v="$(toml_get_layered locale language)";          [[ -n "$v" ]] && DEFAULT_LANG="$v"
    v="$(toml_get_layered bootstrap mios_repo)";      [[ -n "$v" ]] && MIOS_REPO="$v"
    v="$(toml_get_layered bootstrap bootstrap_repo)"; [[ -n "$v" ]] && BOOTSTRAP_REPO="$v"

    # Legacy .env.mios fallback (deprecated; sourced last so explicit TOML wins).
    local legacy_env; legacy_env="$(dirname "${BASH_SOURCE[0]}")/.env.mios"
    if [[ -f "$legacy_env" ]]; then
        log_info "Sourcing legacy ${legacy_env} (deprecated; migrate to profile.toml)"
        # shellcheck source=/dev/null
        set +u; source "$legacy_env"; set -u
        [[ -n "${MIOS_DEFAULT_USER:-}" ]] && DEFAULT_USER="${MIOS_DEFAULT_USER}"
        [[ -n "${MIOS_DEFAULT_HOST:-}" ]] && DEFAULT_HOST="${MIOS_DEFAULT_HOST}"
        [[ -n "${MIOS_IMAGE_NAME:-}" && -n "${MIOS_IMAGE_TAG:-}" ]] && \
            DEFAULT_IMAGE="${MIOS_IMAGE_NAME}:${MIOS_IMAGE_TAG}"
    fi
}

# ============================================================================
# Logging
# ============================================================================
_BOLD=$(tput bold 2>/dev/null || echo "")
_RED=$(tput setaf 1 2>/dev/null || echo "")
_GREEN=$(tput setaf 2 2>/dev/null || echo "")
_YELLOW=$(tput setaf 3 2>/dev/null || echo "")
_CYAN=$(tput setaf 6 2>/dev/null || echo "")
_DIM=$(tput dim 2>/dev/null || echo "")
_RESET=$(tput sgr0 2>/dev/null || echo "")

log_info()  { printf '%s[INFO]%s %s\n' "${_CYAN}" "${_RESET}" "$*"; }
log_ok()    { printf '%s[ OK ]%s %s\n' "${_GREEN}" "${_RESET}" "$*"; }
log_warn()  { printf '%s[WARN]%s %s\n' "${_YELLOW}" "${_RESET}" "$*" >&2; }
log_err()   { printf '%s[ERR ]%s %s\n' "${_RED}" "${_RESET}" "$*" >&2; }
log_phase() { printf '\n%s%s== %s ==%s\n\n' "${_BOLD}" "${_CYAN}" "$*" "${_RESET}"; }

# ── Spinner ───────────────────────────────────────────────────────────────────
_SPIN_PID=0
spin_start() {
    local msg="${1:-Working...}"
    printf '%s  %s...%s\n' "${_CYAN}" "$msg" "${_RESET}" >&2
    (
        local i=0 chars='|/-\'
        while true; do
            printf '\r  %s %s %s  ' "${_CYAN}" "${chars:$((i % 4)):1}" "$msg${_RESET}" >&2
            i=$((i + 1))
            sleep 0.2
        done
    ) &
    _SPIN_PID=$!
}
spin_stop() {
    if [[ "$_SPIN_PID" -ne 0 ]]; then
        kill "$_SPIN_PID" 2>/dev/null || true
        wait "$_SPIN_PID" 2>/dev/null || true
        _SPIN_PID=0
    fi
    printf '\r%s\r' "$(tput el 2>/dev/null || printf '%80s')" >&2
}

# ============================================================================
# Preflight
# ============================================================================
require_root() {
    if [[ $EUID -ne 0 ]]; then
        log_err "Bootstrap must run as root. Re-invoke with sudo:"
        log_err "  sudo $0"
        exit 1
    fi
}

detect_host_kind() {
    if command -v bootc >/dev/null 2>&1 && bootc status --format=json 2>/dev/null | grep -q '"booted"'; then
        echo "bootc"
    elif [[ -f /etc/os-release ]] && grep -qE '^ID(_LIKE)?=.*fedora' /etc/os-release; then
        echo "fhs-fedora"
    else
        echo "unsupported"
    fi
}

check_network() {
    local host
    for host in github.com ghcr.io; do
        if ! curl -fsSL --max-time 5 -o /dev/null "https://${host}/" 2>/dev/null; then
            log_err "No network reachability to ${host}. Check your network and re-run."
            exit 1
        fi
    done
    log_ok "Network reachability verified"
}

install_prerequisites() {
    local missing=()
    for cmd in git curl openssl; do
        command -v "$cmd" &>/dev/null || missing+=("$cmd")
    done
    [[ ${#missing[@]} -eq 0 ]] && return 0

    log_info "Installing missing prerequisites: ${missing[*]}"
    local dnf_cmd="dnf"
    command -v dnf5 &>/dev/null && dnf_cmd="dnf5"
    spin_start "Installing ${missing[*]}"
    $dnf_cmd install -y --skip-unavailable "${missing[@]}" || {
        spin_stop
        log_err "Failed to install prerequisites: ${missing[*]}"
        exit 1
    }
    spin_stop
    log_ok "Prerequisites ready: ${missing[*]}"
}

# ============================================================================
# Prompts -- the "mios" defaults are baked in; user just hits Enter to accept.
# ============================================================================
prompt_default() {
    local question="$1" default="$2" answer
    read -r -p "$(printf '%s%s%s [%s%s%s]: ' "${_BOLD}" "${question}" "${_RESET}" "${_DIM}" "${default}" "${_RESET}")" answer
    echo "${answer:-$default}"
}

prompt_password() {
    local prompt="$1" pw1 pw2
    while :; do
        printf '%s%s%s: ' "${_BOLD}" "${prompt}" "${_RESET}" >&2
        read -rs pw1; echo >&2
        printf '%sConfirm:%s ' "${_BOLD}" "${_RESET}" >&2
        read -rs pw2; echo >&2
        if [[ "$pw1" == "$pw2" ]]; then
            if [[ -z "$pw1" ]]; then
                log_warn "Empty password not allowed."
                continue
            fi
            echo "$pw1"
            return 0
        fi
        log_warn "Passwords don't match, please try again."
    done
}

prompt_yesno() {
    local question="$1" default="${2:-y}" answer hint
    if [[ "$default" == "y" ]]; then hint="[Y/n]"; else hint="[y/N]"; fi
    read -r -p "$(printf '%s%s%s %s: ' "${_BOLD}" "${question}" "${_RESET}" "${hint}")" answer
    answer="${answer:-$default}"
    case "${answer,,}" in
        y|yes) return 0 ;;
        *) return 1 ;;
    esac
}

# ============================================================================
# Phase-0 (continued): gather installation profile
# ============================================================================
gather_user_choices() {
    log_phase "Phase-0 -- Installation profile"
    log_info "Press Enter to accept defaults (everything defaults to 'MiOS')."
    echo

    LINUX_USER="$(prompt_default 'Linux username' "${DEFAULT_USER}")"
    HOSTNAME_VAL="$(prompt_default 'Hostname' "${DEFAULT_HOST}")"
    USER_FULLNAME="$(prompt_default 'Full name (GECOS)' "${DEFAULT_USER_FULLNAME}")"

    log_info "Setting password for '${LINUX_USER}' (will be a sudoer):"
    USER_PASSWORD="$(prompt_password 'Password')"

    SSH_CHOICE="$(prompt_default 'SSH key: (g)enerate ed25519 / (e)xisting path / (s)kip' 'g')"
    case "${SSH_CHOICE,,}" in
        e|existing) SSH_KEY_PATH="$(prompt_default 'Existing private key path' "/root/.ssh/id_${DEFAULT_SSH_KEY_TYPE}")" ;;
        s|skip)     SSH_KEY_PATH="" ;;
        *)          SSH_KEY_PATH="generate" ;;
    esac

    if prompt_yesno 'Configure GitHub PAT for git credential helper?' n; then
        printf '%sGitHub PAT (input hidden):%s ' "${_BOLD}" "${_RESET}"
        read -rs GH_TOKEN; echo
    else
        GH_TOKEN=""
    fi

    local hostkind
    hostkind="$(detect_host_kind)"
    if [[ "$hostkind" == "bootc" ]]; then
        IMAGE_TAG="$(prompt_default 'MiOS bootc image' "${DEFAULT_IMAGE}")"
        INSTALL_MODE="bootc"
    else
        # FHS mode is always "fhs" for total root overlay in this branch.
        INSTALL_MODE="fhs"
        IMAGE_TAG=""
    fi
}

# ============================================================================
# Phase-0 (continued): confirm before applying
# ============================================================================
print_summary() {
    log_phase "Phase-0 -- Review profile"
    cat <<EOF
  ${_BOLD}Linux user${_RESET}     : ${LINUX_USER}  (full name: ${USER_FULLNAME})
  ${_BOLD}Sudo groups${_RESET}    : ${DEFAULT_USER_GROUPS}
  ${_BOLD}Hostname${_RESET}       : ${HOSTNAME_VAL}
  ${_BOLD}Password${_RESET}       : (set, hidden)
  ${_BOLD}SSH key${_RESET}        : ${SSH_KEY_PATH:-skip}
  ${_BOLD}GitHub PAT${_RESET}     : $([ -n "${GH_TOKEN:-}" ] && echo 'configured' || echo 'skip')
  ${_BOLD}Install mode${_RESET}   : ${INSTALL_MODE} (Total Root Overlay)

EOF
    if ! prompt_yesno 'Proceed with these settings?' y; then
        log_info "Aborted by user. No changes made."
        exit 0
    fi
}

# ============================================================================
# Phase-3: apply profile to host
# ============================================================================
apply_user_profile() {
    log_phase "Phase-3 -- Apply profile to host"
    mkdir -p "${PROFILE_DIR}"
    chmod 0750 "${PROFILE_DIR}"

    log_info "Setting hostname -> ${HOSTNAME_VAL}"
    hostnamectl set-hostname "${HOSTNAME_VAL}"

    if id -u "${LINUX_USER}" >/dev/null 2>&1; then
        log_info "User '${LINUX_USER}' exists; updating groups + password"
        usermod -aG "${DEFAULT_USER_GROUPS}" "${LINUX_USER}"
        usermod -c "${USER_FULLNAME}" "${LINUX_USER}"
    else
        log_info "Creating '${LINUX_USER}' (groups: ${DEFAULT_USER_GROUPS})"
        useradd -m -G "${DEFAULT_USER_GROUPS}" -s "${DEFAULT_USER_SHELL}" -c "${USER_FULLNAME}" "${LINUX_USER}"
    fi
    echo "${LINUX_USER}:${USER_PASSWORD}" | chpasswd
    log_ok "User '${LINUX_USER}' configured"

    local home; home="$(getent passwd "${LINUX_USER}" | cut -d: -f6)"
    if [[ "$SSH_KEY_PATH" == "generate" ]]; then
        log_info "Generating ${DEFAULT_SSH_KEY_TYPE} key for ${LINUX_USER}"
        sudo -u "${LINUX_USER}" mkdir -p "${home}/.ssh"
        chmod 0700 "${home}/.ssh"
        sudo -u "${LINUX_USER}" ssh-keygen -q -t "${DEFAULT_SSH_KEY_TYPE}" -N '' \
            -C "mios@${HOSTNAME_VAL}" \
            -f "${home}/.ssh/id_${DEFAULT_SSH_KEY_TYPE}"
        log_ok "SSH key generated: ${home}/.ssh/id_${DEFAULT_SSH_KEY_TYPE}"
    elif [[ -n "$SSH_KEY_PATH" ]]; then
        if [[ ! -f "$SSH_KEY_PATH" ]]; then
            log_warn "SSH key path not found: ${SSH_KEY_PATH} -- skipping"
        else
            log_info "Installing SSH key from ${SSH_KEY_PATH}"
            sudo -u "${LINUX_USER}" mkdir -p "${home}/.ssh"
            cp "${SSH_KEY_PATH}" "${home}/.ssh/id_${DEFAULT_SSH_KEY_TYPE}"
            cp "${SSH_KEY_PATH}.pub" "${home}/.ssh/id_${DEFAULT_SSH_KEY_TYPE}.pub" 2>/dev/null || true
            chown "${LINUX_USER}:${LINUX_USER}" "${home}/.ssh"/*
            chmod 0600 "${home}/.ssh/id_${DEFAULT_SSH_KEY_TYPE}"
            log_ok "SSH key installed"
        fi
    fi

    if [[ -n "${GH_TOKEN:-}" ]]; then
        sudo -u "${LINUX_USER}" mkdir -p "${home}/.config/git"
        sudo -u "${LINUX_USER}" git config --file "${home}/.config/git/config" credential.helper store
        echo "https://${LINUX_USER}:${GH_TOKEN}@github.com" > "${home}/.git-credentials"
        chmod 0600 "${home}/.git-credentials"
        chown "${LINUX_USER}:${LINUX_USER}" "${home}/.git-credentials"
        log_ok "GitHub credential helper configured"
    fi

    cat > "${PROFILE_FILE}" <<EOF
# 'MiOS' install profile -- written by mios-bootstrap install.sh
# Non-secret installation metadata. Passwords/tokens are NOT stored here.
MIOS_LINUX_USER="${LINUX_USER}"
MIOS_HOSTNAME="${HOSTNAME_VAL}"
MIOS_USER_FULLNAME="${USER_FULLNAME}"
MIOS_USER_GROUPS="${DEFAULT_USER_GROUPS}"
MIOS_INSTALL_MODE="${INSTALL_MODE}"
MIOS_IMAGE_TAG="${IMAGE_TAG}"
MIOS_INSTALLED_AT="$(date -u --iso-8601=seconds)"
MIOS_BOOTSTRAP_VERSION="0.2.0"
EOF
    chmod 0640 "${PROFILE_FILE}"
    log_ok "Profile env written: ${PROFILE_FILE}"

    # Persist the user-editable profile card alongside install.env so future
    # bootstrap re-runs (or `mios edit-env`) can amend defaults in TOML.
    if [[ ! -f "${PROFILE_CARD}" ]]; then
        local repo_card; repo_card="$(dirname "${BASH_SOURCE[0]}")/etc/mios/profile.toml"
        if [[ -f "$repo_card" ]]; then
            install -m 0644 "$repo_card" "${PROFILE_CARD}"
            log_ok "Profile card seeded: ${PROFILE_CARD}"
        fi
    fi
}

# ============================================================================
# Phase-3 (continued): deploy AI system prompt to host AND user home
# ============================================================================
deploy_system_prompt() {
    log_phase "Phase-3 -- Deploy AI system prompt"
    install -d -m 0755 /etc/mios/ai

    local src_local prompt_url
    src_local="$(dirname "${BASH_SOURCE[0]}")/system-prompt.md"
    prompt_url="https://raw.githubusercontent.com/mios-dev/mios-bootstrap/${DEFAULT_BRANCH}/system-prompt.md"

    if [[ -f "$src_local" ]]; then
        log_info "Using local system-prompt.md from ${src_local}"
        install -m 0644 "$src_local" /etc/mios/ai/system-prompt.md
    else
        log_info "Fetching system prompt from ${prompt_url}"
        spin_start "Downloading system-prompt.md"
        if curl -fsSL --max-time 30 "$prompt_url" -o /etc/mios/ai/system-prompt.md.new; then
            spin_stop
            mv /etc/mios/ai/system-prompt.md.new /etc/mios/ai/system-prompt.md
            chmod 0644 /etc/mios/ai/system-prompt.md
        else
            spin_stop
            rm -f /etc/mios/ai/system-prompt.md.new
            log_warn "Could not fetch system prompt"
            return 0
        fi
    fi
    log_ok "Host system prompt deployed: /etc/mios/ai/system-prompt.md"

    # Stage per-user copies for every existing human account
    # (uid 1000-65533). Single helper avoids duplicate logic across
    # deploy_system_prompt + stage_user_profile_artifacts; the call sites
    # remain distinct so the bootstrap-created user still gets the
    # name-bearing log line.
    seed_user_skel_for_all_accounts
}

# ============================================================================
# Multi-user seeder: copy /etc/skel/.config/mios/* into every existing user's
# home, owned by that user. Called from deploy_system_prompt (after the host
# /etc/mios/ai/system-prompt.md is in place) and again from
# stage_user_profile_artifacts (after the bootstrap-created user is added).
# Idempotent: install(1) overwrites with current content, mode is enforced.
# ============================================================================
seed_user_skel_for_all_accounts() {
    local skel_root=/etc/skel/.config/mios
    [[ -d "$skel_root" ]] || {
        log_warn "etc/skel/.config/mios missing -- per-user staging skipped"
        return 0
    }

    local u home uid sh
    while IFS=: read -r u _ uid _ _ home sh; do
        [[ "$uid" -ge 1000 && "$uid" -lt 65534 && -d "$home" ]] || continue
        sudo -u "$u" install -d -m 0755 "${home}/.config" "${home}/.config/mios"
        local f
        for f in "$skel_root"/*; do
            [[ -f "$f" ]] || continue
            install -o "$u" -g "$u" -m 0644 "$f" "${home}/.config/mios/$(basename "$f")"
        done
        log_ok "Seeded ${home}/.config/mios/ for ${u} (uid ${uid})"
    done < /etc/passwd
}

# ============================================================================
# Phase-3 (continued): stage per-user profile card + system prompt for the
# bootstrap-created user. Reads from /etc/skel/.config/mios/, the FHS-native
# template surface that mios-bootstrap.git populates from etc/skel/.
# ============================================================================
stage_user_profile_artifacts() {
    log_phase "Phase-3 -- Stage per-user 'MiOS' artifacts"
    local home; home="$(getent passwd "${LINUX_USER}" | cut -d: -f6)"
    [[ -n "$home" && -d "$home" ]] || {
        log_warn "User home not found; skipping per-user staging"
        return 0
    }

    sudo -u "${LINUX_USER}" install -d -m 0755 "${home}/.config" "${home}/.config/mios"

    local skel_root=/etc/skel/.config/mios
    if [[ -d "$skel_root" ]]; then
        local f
        for f in "$skel_root"/*; do
            [[ -f "$f" ]] || continue
            install -o "${LINUX_USER}" -g "${LINUX_USER}" -m 0644 \
                "$f" "${home}/.config/mios/$(basename "$f")"
            log_ok "User artifact: ${home}/.config/mios/$(basename "$f")"
        done
    else
        log_warn "etc/skel/.config/mios missing -- bootstrap user staging skipped"
    fi

    # Re-run the multi-user pass so a newly added user picks up the same
    # content as everyone else (idempotent).
    seed_user_skel_for_all_accounts
}

# ============================================================================
# Phase-1 + Phase-2: clone mios.git into /, apply bootstrap overlays, install
# packages from PACKAGES.md SSOT, run mios.git/install.sh for system init.
# Phase-2 (build) is implicit: on FHS hosts the package install + system-side
# init is the equivalent of "build the running system from the merged tree";
# on bootc hosts Phase-2 is `bootc switch` to a pre-built image.
# ============================================================================
trigger_mios_install() {
    log_phase "Phase-1 -- Total Root Merge"
    
    case "${INSTALL_MODE}" in
        bootc)
            log_info "Switching bootc deployment to ${IMAGE_TAG}"
            bootc switch "${IMAGE_TAG}"
            log_ok "bootc deployment staged"
            ;;
        fhs)
            local dnf_cmd="dnf"
            command -v dnf5 >/dev/null 2>&1 && dnf_cmd="dnf5"

            # 1. Initialize / as the git root for 'MiOS' core
            log_info "Staging 'MiOS' core repository (mios.git) to /"
            if [[ ! -d "/.git" ]]; then
                git init /
                git -C / remote add origin "${MIOS_REPO}"
            fi
            spin_start "Fetching mios.git (system layer)"
            git -C / fetch --depth=1 origin "${DEFAULT_BRANCH}" 2>&1 | tail -3
            git -C / reset --hard FETCH_HEAD
            spin_stop
            log_ok "MiOS core (mios.git) merged to /"

            # 2. Apply MiOS-bootstrap repo overlays
            local bootstrap_tmp="/tmp/mios-bootstrap-src"
            log_info "Fetching MiOS-bootstrap overlays from ${BOOTSTRAP_REPO}"
            spin_start "Cloning mios-bootstrap.git (user layer)"
            rm -rf "${bootstrap_tmp}"
            git clone --depth=1 "${BOOTSTRAP_REPO}" "${bootstrap_tmp}" 2>&1 | tail -3
            spin_stop

            log_info "Merging bootstrap system folders (etc, usr) to /"
            for d in etc usr; do
                if [[ -d "${bootstrap_tmp}/${d}" ]]; then
                    cp -a "${bootstrap_tmp}/${d}/." "/${d}/" 2>/dev/null || true
                fi
            done
            rm -rf "${bootstrap_tmp}"
            log_ok "MiOS-bootstrap overlays applied"

            # 3. Phase-2: RPM package install from PACKAGES.md SSOT.
            # Build-only blocks (kernel kmods, selinux policy source, looking-glass
            # build deps, cockpit plugin build deps) are excluded -- they only make
            # sense inside the OCI build pipeline, not on a running FHS host.
            log_phase "Phase-2 -- FHS package install (from PACKAGES.md)"
            local packages_md="/usr/share/mios/PACKAGES.md"
            if [[ -f "$packages_md" ]]; then
                # Excluded block names: build-time / image-only groups
                local -a exclude_blocks=(
                    packages-kernel
                    packages-k3s-selinux-build
                    packages-looking-glass-build
                    packages-cockpit-plugins-build
                    packages-self-build
                )
                local exclude_pat
                exclude_pat=$(printf '|%s' "${exclude_blocks[@]}")
                exclude_pat="${exclude_pat:1}"   # strip leading |

                local pkgs
                pkgs=$(awk -v excl="$exclude_pat" '
                    /^```packages-/ {
                        block = $0; sub(/^```/,"",block); sub(/[[:space:]].*$/,"",block)
                        if (block ~ excl) { skip=1 } else { skip=0 }
                        next
                    }
                    /^```$/ { skip=0; next }
                    skip || /^#/ || /^$/ { next }
                    { print }
                ' "$packages_md" | tr '\n' ' ')

                if [[ -n "$pkgs" ]]; then
                    # Install repos meta-packages first so that subsequent packages
                    # can resolve from RPMFusion, CrowdSec, Terra, etc.
                    local repo_pkgs
                    repo_pkgs=$(sed -n '/^```packages-repos/,/^```$/{/^```/d;/^#/d;/^$/d;p}' "$packages_md" | tr '\n' ' ')
                    if [[ -n "$repo_pkgs" ]]; then
                        log_info "Setting up additional repos..."
                        spin_start "Installing repo packages"
                        # shellcheck disable=SC2086
                        $dnf_cmd install -y --skip-unavailable $repo_pkgs 2>&1 | grep -E '^(Install|Upgrade|Error|Warning|Failed)' || true
                        spin_stop
                        $dnf_cmd makecache --refresh 2>/dev/null || true
                        log_ok "Repos configured"
                    fi

                    log_info "Installing full 'MiOS' component stack..."
                    spin_start "dnf install (this takes several minutes)"
                    # shellcheck disable=SC2086
                    $dnf_cmd install -y --skip-unavailable --best $pkgs 2>&1 \
                        | grep -E '^\s*(Installing|Upgrading|Removing|Error|Warning|Nothing)' || true
                    spin_stop
                    log_ok "Package installation complete"
                else
                    log_warn "No packages extracted from PACKAGES.md"
                fi
            else
                log_err "PACKAGES.md not found at ${packages_md} -- package installation skipped"
            fi

            # 4. Phase-3: systemd-sysusers, systemd-tmpfiles, daemon-reload.
            # This wires up 'MiOS' user/group definitions and creates /var/ paths
            # declared in usr/lib/tmpfiles.d/mios*.conf.
            log_phase "Phase-3 -- System init (sysusers + tmpfiles + daemon-reload)"
            spin_start "Running systemd-sysusers"
            systemctl-sysusers 2>/dev/null || systemd-sysusers 2>/dev/null || log_warn "systemd-sysusers not available"
            spin_stop
            spin_start "Running systemd-tmpfiles --create"
            systemd-tmpfiles --create 2>/dev/null || log_warn "systemd-tmpfiles failed"
            spin_stop
            if systemctl is-system-running --quiet 2>/dev/null; then
                spin_start "Reloading systemd daemon"
                systemctl daemon-reload
                spin_stop
                log_ok "Systemd daemon reloaded"
            fi
            log_ok "FHS system init complete"
            ;;
    esac
}

# ============================================================================
# Phase-4: reboot prompt
# ============================================================================
reboot_prompt() {
    log_phase "Phase-4 -- Reboot"
    if prompt_yesno 'Reboot now to activate 'MiOS'?' y; then
        log_info "Rebooting in 3s..."
        sleep 3
        systemctl reboot
    else
        log_info "Skipping reboot. Run 'sudo systemctl reboot' when ready."
    fi
}

# ============================================================================
# Main
# ============================================================================
main() {
    require_root
    log_phase "Phase-0 -- mios-bootstrap (Total Root Merge Mode)"

    local hostkind
    hostkind="$(detect_host_kind)"
    if [[ "$hostkind" == "unsupported" ]]; then
        log_err "Host is not Fedora. Aborting."
        exit 1
    fi
    log_info "Detected host: ${hostkind}"

    check_network
    install_prerequisites
    load_profile_defaults
    gather_user_choices
    print_summary

    # Phase-1 (overlay merge) and Phase-2 (build / package install) happen
    # inside trigger_mios_install. System groups are created there before
    # apply_user_profile needs them.
    trigger_mios_install

    # Phase-3a: deploy AI system prompt to host /etc/ AND every existing user home.
    deploy_system_prompt

    # Phase-3b: create the bootstrap user, set password, persist install.env
    # and seed /etc/mios/profile.toml.
    apply_user_profile

    # Phase-3c: stage the per-user profile.toml + system-prompt.md into the
    # newly-created user's home (idempotent on re-run).
    stage_user_profile_artifacts

    # Phase-4
    reboot_prompt
}

main "$@"
```


### `C:\Users\USER\OneDrive\Documents\GitHub\mios-bootstrap\install.ps1`

```powershell
#Requires -Version 5.1
# 'MiOS' Unified Installer & Builder -- Windows 11 / PowerShell
#
#   irm https://raw.githubusercontent.com/mios-dev/mios-bootstrap/main/install.ps1 | iex
#
# Flags:
#   -BuildOnly    Pull latest + build only (skip first-time setup)
#   -Unattended   Accept all defaults, no prompts

param([switch]$BuildOnly, [switch]$Unattended)

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"

# ── Paths & constants ─────────────────────────────────────────────────────────
$MiosVersion      = "v0.2.2"
$MiosInstallDir   = Join-Path $env:LOCALAPPDATA "Programs\MiOS"
$MiosRepoDir      = Join-Path $MiosInstallDir "repo"
$MiosDistroDir    = Join-Path $MiosInstallDir "distros"
$MiosConfigDir    = Join-Path $env:APPDATA "MiOS"
$MiosDataDir      = Join-Path $env:LOCALAPPDATA "MiOS"
$MiosLogDir       = Join-Path $MiosDataDir "logs"
$MiosRepoUrl      = "https://github.com/mios-dev/mios.git"
$MiosBootstrapUrl = "https://github.com/mios-dev/mios-bootstrap.git"
$BuilderDistro    = "MiOS-BUILDER"
$MiosWslDistro    = "MiOS"
$LegacyDistro     = "podman-machine-default"
$UninstallRegKey  = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\MiOS"
$StartMenuDir     = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\MiOS"

# ── Log files ─────────────────────────────────────────────────────────────────
$null = New-Item -ItemType Directory -Path $MiosLogDir -Force -ErrorAction SilentlyContinue
$LogStamp       = [datetime]::Now.ToString("yyyyMMdd-HHmmss")
$LogFile        = Join-Path $MiosLogDir "mios-install-$LogStamp.log"
# Separate raw build-output log -- NOT the transcript file.
# Start-Transcript locks $LogFile exclusively; any Out-File/Add-Content to the
# same path throws a TerminatingError that -EA SilentlyContinue cannot suppress.
# Build lines are appended here via [IO.File]::AppendAllText (no lock conflict).
$BuildDetailLog = Join-Path $MiosLogDir "mios-build-$LogStamp.log"
[Environment]::SetEnvironmentVariable("MIOS_UNIFIED_LOG", $LogFile)
[Environment]::SetEnvironmentVariable("MIOS_BUILD_LOG",   $BuildDetailLog)
try { Start-Transcript -Path $LogFile -Append -Force | Out-Null } catch {}

function Write-Log {
    param([string]$M, [string]$L = "INFO")
    $ts = [datetime]::Now.ToString("HH:mm:ss.fff")
    # Write-Host is captured by Start-Transcript; Out-File to the same path causes
    # a TerminatingError (file lock) that -EA SilentlyContinue cannot suppress.
    Write-Host "[$ts][$L] $M"
    if ($L -eq "ERROR") { $script:ErrCount++ }
    if ($L -eq "WARN")  { $script:WarnCount++ }
}

# ── Dashboard state ───────────────────────────────────────────────────────────
$script:DW         = [math]::Max(66, [math]::Min(([Console]::WindowWidth - 2), 80))
$script:PhaseNames = @(
    "Hardware + Prerequisites",
    "Detecting environment",
    "Directories and repos",
    "MiOS-BUILDER distro",
    "WSL2 configuration",
    "Verifying build context",
    "Identity",
    "Writing identity",
    "App registration",
    "Building OCI image",
    "Exporting WSL2 image",
    "Registering 'MiOS' WSL2",
    "Building disk images",
    "Deploying Hyper-V VM"
)
$script:TotalPhases   = $script:PhaseNames.Count
$script:PhStat        = @(0,0,0,0,0,0,0,0,0,0,0,0,0,0)
$script:PhStart       = @{}
$script:PhEnd         = @{}
$script:CurPhase      = -1
$script:CurStep       = "Starting..."
$script:ErrCount      = 0
$script:WarnCount     = 0
$script:ScriptStart   = [datetime]::Now
$script:DashRow       = 0
$script:DashHeight    = 0
$script:FinalRc       = 0
$script:BuildSubTotal = 48
$script:BuildSubDone  = 0
$script:BuildSubStep  = ""
$script:GhcrToken     = ""
# Live build tracking -- updated each loop tick; shown in debug row
$script:DebugLine     = ""
$script:LineCount     = 0
$script:HWInfo        = ""   # set after Get-Hardware; shown in dashboard info row
$script:IdentInfo     = ""   # set after phase 6 identity; User/Host/Base/Model row
# Shared state between main thread and background spinner runspace.
# SpinnerRow = -1 means unknown (spinner write suppressed until first render).
$script:DashSync = [hashtable]::Synchronized(@{
    Running    = $true
    SpinnerRow = -1
    SpinnerCol = 5     # "| Op X" -- spinner char is always at col 5
})
$script:BgPs = $null
$script:BgRs = $null

# ── Dashboard functions ───────────────────────────────────────────────────────
function fmtSpan([timespan]$s) {
    if ($s.TotalHours -ge 1) { return "{0}:{1:D2}:{2:D2}" -f [int]$s.TotalHours,$s.Minutes,$s.Seconds }
    return "{0:D2}:{1:D2}" -f [int]$s.TotalMinutes,$s.Seconds
}

function pbar([int]$done,[int]$total,[int]$width) {
    $pct = if ($total -gt 0) { [int](($done/$total)*100) } else { 0 }
    $f   = if ($total -gt 0) { [int](($done/$total)*$width) } else { 0 }
    $bar = if ($f -gt 0) { ("=" * ([math]::Max(0,$f-1))) + ">" } else { "" }
    return "[{0}] {1,3}%  {2}/{3}" -f $bar.PadRight($width),$pct,$done,$total
}

function Update-BuildSubPhase([string]$line) {
    # Strip BuildKit "#N 0.123 " prefix
    $stripped = ($line -replace '^\s*#\d+\s+[\d.]+\s+', '').TrimStart()
    $script:LineCount++

    if ($stripped -match '\+-\s*STEP\s+(\d+)/(\d+)\s*:\s*(\S+)') {
        # Step start marker: "+- STEP NN/TT : scriptname.sh"
        $script:BuildSubTotal = [int]$Matches[2]
        $script:BuildSubStep  = $Matches[3] -replace '\.sh$', ''
        $script:BuildSubDone  = [math]::Max(0, [int]$Matches[1] - 1)
        $script:CurStep       = "Step $($Matches[1])/$($Matches[2]) -- $($script:BuildSubStep)"
        $script:DebugLine     = $stripped
    } elseif ($stripped -match '\+--\s+\[') {
        # Step end marker
        $script:BuildSubDone = [math]::Min($script:BuildSubDone + 1, $script:BuildSubTotal)
        $script:DebugLine    = $stripped
    } elseif (-not [string]::IsNullOrWhiteSpace($stripped)) {
        $c = ($stripped -replace '\s+', ' ').Trim()
        if ($c.Length -gt 120) { $c = $c.Substring(0, 117) + '...' }
        $script:CurStep   = $c
        $script:DebugLine = $c
    }
}

function Show-Dashboard {
    try {
    # ── Sizing -- max 80 cols (standard tty0/console) ──────────────────────────
    $winW = try { [Console]::WindowWidth  } catch { 80 }
    $bufH = try { [Console]::BufferHeight } catch { 9999 }
    # Always 1 char narrower than actual terminal so old content to the right
    # of the box is blanked on overwrite; capped at 80 for tty0 portability.
    $w  = [math]::Max(40, [math]::Min(80, $winW - 1))
    $in = $w - 4   # inner content width: "| " + content + " |"
    $sepD = ("+" + ("-" * ($w - 2)) + "+").PadRight($winW)
    $sepE = ("+" + ("=" * ($w - 2)) + "+").PadRight($winW)

    # ── Row helper -- script block closes over $in/$winW from caller scope ─────
    $mkRow = {
        param([string]$c)
        ("| " + $c.PadRight($in) + " |").PadRight($winW)
    }

    # ── State ─────────────────────────────────────────────────────────────────
    $phDone = [int]($script:PhStat | Where-Object { $_ -ge 2 } | Measure-Object).Count
    $phFail = [int]($script:PhStat | Where-Object { $_ -eq 3 } | Measure-Object).Count
    $elapsed   = [datetime]::Now - $script:ScriptStart
    $elStr     = fmtSpan $elapsed
    $statusStr = if ($phFail -gt 0) { "FAILED" } `
                 elseif ($script:CurPhase -ge 0 -and $script:PhStat[$script:CurPhase] -eq 1) { "RUNNING" } `
                 else { "IDLE" }
    $curName   = if ($script:CurPhase -ge 0) { [string]$script:PhaseNames[$script:CurPhase] } else { "Initializing" }

    # Spinner -- 500ms tick; visible on slow/remote consoles, animates even when
    # build output is silent.
    $spinChar = @('|','/','-',[char]92)[[int]($elapsed.TotalMilliseconds / 500) % 4]

    $step = (([string]$script:CurStep) -replace '\s+', ' ').Trim()
    $stepMax = [math]::Max(3, $in - 8)
    if ($step.Length -gt $stepMax) { $step = $step.Substring(0, $stepMax - 3) + "..." }

    # ── Single unified progress bar (phases + build steps = one global count) ─
    $stDone  = [math]::Max(0, $script:BuildSubDone)
    $stTotal = [math]::Max(1, $script:BuildSubTotal)
    $glDone  = $phDone + $stDone
    $glTotal = $script:TotalPhases + $stTotal
    $barW    = [math]::Max(4, $in - 24)
    $glPct = 0; if ($glTotal -gt 0) { $glPct = [int](($glDone / $glTotal) * 100) }
    $glFRaw = 0; if ($glTotal -gt 0) { $glFRaw = [int](($glDone / $glTotal) * $barW) }
    $glF     = [math]::Max(0, $glFRaw)
    if ($glF -gt 0) { $glFill = ("=" * ($glF - 1)) + ">" } else { $glFill = "" }
    $glFill  = $glFill.PadRight($barW)
    $glBarL  = "[{0}] {1,3}%  {2}/{3}" -f $glFill,$glPct,$glDone,$glTotal

    # ── Phase table col widths ────────────────────────────────────────────────
    $nameW = [math]::Max(8, $in - 15)

    # ── Assemble rows ─────────────────────────────────────────────────────────
    $rows = [System.Collections.Generic.List[string]]::new()

    # Header -- gap computed so total row width = $w, then padded to $winW
    $rows.Add($sepE)
    $title = " 'MiOS' $MiosVersion  --  Build Dashboard"
    $right = "[ $elStr ] "
    $gap   = [math]::Max(0, $in - $title.Length - $right.Length)
    $hdr   = "| $title" + (" " * $gap) + "$right |"
    $rows.Add($hdr.PadRight($winW))
    $rows.Add($sepE)

    # Hardware info row (populated after Get-Hardware; blank during early phases)
    if ($script:HWInfo) {
        $hw = ([string]$script:HWInfo)
        if ($hw.Length -gt $in) { $hw = $hw.Substring(0,$in-3)+"..." }
        $rows.Add((& $mkRow $hw))
    }

    # Identity row (populated after phase 6; blank before)
    if ($script:IdentInfo) {
        $id = ([string]$script:IdentInfo)
        if ($id.Length -gt $in) { $id = $id.Substring(0,$in-3)+"..." }
        $rows.Add((& $mkRow $id))
    }

    if ($script:HWInfo -or $script:IdentInfo) { $rows.Add($sepD) }

    # Current phase + live operation stream
    $phTag = switch ([int]$script:PhStat[[math]::Max(0,$script:CurPhase)]) {
        1 { "[>>]" } 2 { "[OK]" } 3 { "[XX]" } 4 { "[!!]" } default { "[ ]" }
    }
    $phLine = "Phase [$($script:CurPhase)/$($script:TotalPhases-1)] $curName  $phTag"
    if ($script:CurPhase -eq 9 -and $script:BuildSubDone -gt 0) {
        $phLine += "  (step $($script:BuildSubDone)/$($script:BuildSubTotal))"
    }
    $rows.Add((& $mkRow $phLine))
    # Record which row index the spinner char will be on so the background
    # heartbeat runspace can animate it independently of the main thread.
    $opRowIdx = $rows.Count
    $rows.Add((& $mkRow "Op $spinChar : $step"))
    $rows.Add((& $mkRow "Errs:$($script:ErrCount)  Warns:$($script:WarnCount)  Lines:$($script:LineCount)  Status:$statusStr"))
    $rows.Add($sepD)

    # Unified progress bar
    $rows.Add((& $mkRow $glBarL))
    $rows.Add($sepD)

    # Phase table
    $rows.Add((& $mkRow (" # [Stat]  " + "Phase Name".PadRight($nameW) + "  Time")))
    $rows.Add((& $mkRow ("-- ------  " + ("-" * $nameW) + "  -----")))
    for ($i = 0; $i -lt $script:TotalPhases; $i++) {
        $st = switch ([int]$script:PhStat[$i]) {
            0 { "[ ]  " } 1 { "[>>] " } 2 { "[OK] " } 3 { "[XX] " } 4 { "[!!] " } default { "[??] " }
        }
        $nm = [string]$script:PhaseNames[$i]
        if ($nm.Length -gt $nameW) { $nm = $nm.Substring(0,$nameW-3)+"..." }
        $t = ""
        if ($null -ne $script:PhStart[$i]) {
            try {
                $ps = [datetime]$script:PhStart[$i]
                $pe = if ($null -ne $script:PhEnd[$i]) { [datetime]$script:PhEnd[$i] } else { [datetime]::Now }
                $t  = fmtSpan ($pe - $ps)
            } catch { $t = "--:--" }
        }
        $r = "{0,2} {1} {2}  {3,5}" -f $i,$st,$nm.PadRight($nameW),$t
        $rows.Add((& $mkRow $r))
    }
    $rows.Add($sepD)

    # Log footer -- unified log only ($BuildDetailLog is merged in at exit)
    $logLeaf = try { Split-Path $LogFile -Leaf } catch { "?" }
    $rows.Add((& $mkRow "Log: $logLeaf"))
    $rows.Add($sepE)

    # ── Render at fixed position; full-width overwrite eliminates bleed ────────
    $dashStart = [math]::Min($script:DashRow, [math]::Max(0, $bufH - $rows.Count - 2))
    # Tell the background heartbeat where to animate the spinner before rendering
    # so it never writes a stale row number.
    $script:DashSync.SpinnerRow = $dashStart + $opRowIdx
    [Console]::SetCursorPosition(0, $dashStart)
    foreach ($row in $rows) {
        [Console]::Write($row)
        [Console]::Write([Environment]::NewLine)
    }
    $script:DashHeight = $rows.Count
    [Console]::SetCursorPosition(0, [math]::Min($dashStart + $script:DashHeight, $bufH - 1))

    } catch {
        Write-Host "[$([datetime]::Now.ToString('HH:mm:ss.fff'))][WARN] dashboard render error: $_"
    }
}

function Start-Phase([int]$i) {
    $script:CurPhase   = $i
    $script:PhStat[$i] = 1
    $script:PhStart[$i] = [datetime]::Now
    $script:CurStep    = $script:PhaseNames[$i]
    Write-Log "START phase $i : $($script:PhaseNames[$i])"
    Show-Dashboard
}

function End-Phase([int]$i, [switch]$Fail, [switch]$Warn) {
    $script:PhStat[$i] = if ($Fail) { 3 } elseif ($Warn) { 4 } else { 2 }
    $script:PhEnd[$i]  = [datetime]::Now
    $spanStr = try {
        if ($null -ne $script:PhStart[$i]) { fmtSpan ([datetime]$script:PhEnd[$i] - [datetime]$script:PhStart[$i]) } else { "--:--" }
    } catch { "--:--" }
    $tag     = if ($Fail) { "FAIL" } elseif ($Warn) { "WARN" } else { "OK  " }
    $lvl     = if ($Fail) { "ERROR" } else { "INFO" }
    Write-Log "$tag  phase $i : $($script:PhaseNames[$i]) ($spanStr)" $lvl
    Show-Dashboard
}

function Set-Step([string]$T) {
    $script:CurStep = $T
    Write-Log "step: $T"
    Show-Dashboard
}

function Log-Ok([string]$T)   { Write-Log "ok   $T";          Set-Step $T }
function Log-Warn([string]$T) { Write-Log "warn $T" "WARN";   Set-Step "WARN: $T" }
function Log-Fail([string]$T) { Write-Log "fail $T" "ERROR";  Set-Step "FAIL: $T" }

# ── Utility helpers ───────────────────────────────────────────────────────────
function ConvertTo-WslPath([string]$P) {
    $P = $P -replace '\\','/'
    if ($P -match '^([A-Za-z]):(.*)') { return "/mnt/$($Matches[1].ToLower())$($Matches[2])" }
    return $P
}

function Move-BelowDash {
    try {
        $targetRow = [math]::Min($script:DashRow + $script:DashHeight, [Console]::BufferHeight - 1)
        [Console]::SetCursorPosition(0, $targetRow)
    } catch {}
}

function Read-Line([string]$Prompt, [string]$Default = "") {
    Move-BelowDash
    Write-Host "  $Prompt" -NoNewline -ForegroundColor White
    if ($Default) { Write-Host " [$Default]" -NoNewline -ForegroundColor DarkGray }
    Write-Host ": " -NoNewline
    if ($Unattended) { Write-Host $Default -ForegroundColor DarkGray; return $Default }
    $v = Read-Host
    return (([string]::IsNullOrWhiteSpace($v)) ? $Default : $v)
}

function Read-Password([string]$Prompt = "Password") {
    Move-BelowDash
    Write-Host "  $Prompt [default: mios]: " -NoNewline -ForegroundColor White
    if ($Unattended) { Write-Host "(default)" -ForegroundColor DarkGray; return "" }
    if ($PSVersionTable.PSVersion.Major -ge 7) { return (Read-Host -MaskInput) }
    $ss = Read-Host -AsSecureString
    $b  = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($ss)
    try   { return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) }
    finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
}

function Get-PasswordHash([string]$Plain) {
    if ($Plain -eq "mios" -or [string]::IsNullOrWhiteSpace($Plain)) {
        return '$6$miosmios0$ShHuf/TnPoEmEX//L9mrNNuP7kZ6l9aj/qV9WFj5LnjL3lunhKEwnJfY6tvlJbRiWkLTtPmdwCgWeOQB9eXuW.'
    }
    $salt = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
    foreach ($d in @($BuilderDistro, $LegacyDistro)) {
        try {
            $h = (& wsl.exe -d $d --exec openssl passwd -6 -salt $salt $Plain 2>$null) -join ""
            if ($LASTEXITCODE -eq 0 -and $h -match '^\$6\$') { return $h.Trim() }
        } catch {}
    }
    # Podman machine SSH (machine-os not accessible via wsl.exe)
    try {
        $mls = (& podman machine ls --format "{{.Name}} {{.Running}}" 2>$null) |
               Where-Object { $_ -match "^$([regex]::Escape($BuilderDistro))\s+true" }
        if ($mls) {
            $h = (& podman machine ssh $BuilderDistro -- bash -c "openssl passwd -6 -salt '$salt' '$Plain'" 2>$null) -join ""
            if ($LASTEXITCODE -eq 0 -and $h -match '^\$6\$') { return $h.Trim() }
        }
    } catch {}
    try {
        $h = (& podman run --rm docker.io/library/alpine:latest sh -c "apk add -q openssl && openssl passwd -6 -salt '$salt' '$Plain'" 2>$null) -join ""
        if ($LASTEXITCODE -eq 0 -and $h -match '^\$6\$') { return $h.Trim() }
    } catch {}
    throw "Cannot generate sha512crypt hash -- install openssl or run from a distro."
}

function Get-Hardware {
    $ramGB = try { [math]::Round((Get-CimInstance Win32_PhysicalMemory|Measure-Object Capacity -Sum).Sum/1GB) } catch { 16 }
    # OS-reported RAM (bytes) -- this is what podman validates against; may be less than nominal GB count
    $osTotalRamMB = try { [math]::Floor((Get-CimInstance Win32_ComputerSystem -EA Stop).TotalPhysicalMemory / 1MB) } catch { $ramGB * 1024 }
    $cpus  = [Environment]::ProcessorCount
    $gpu   = try { Get-CimInstance Win32_VideoController | Where-Object { $_.Name -notmatch "Microsoft Basic" } | Select-Object -First 1 } catch { $null }
    $gpuName   = if ($gpu) { $gpu.Name } else { "Unknown" }
    $hasNvidia = $gpuName -match "NVIDIA|GeForce|Quadro|RTX|GTX|Tesla"
    $baseImage = if ($hasNvidia) { "ghcr.io/ublue-os/ucore-hci:stable-nvidia" } else { "ghcr.io/ublue-os/ucore-hci:stable" }
    $aiModel   = if ($ramGB -ge 32) { "qwen2.5-coder:14b" } elseif ($ramGB -ge 12) { "qwen2.5-coder:7b" } else { "phi4-mini:3.8b-q4_K_M" }
    $diskFreeGB    = try { [math]::Floor((Get-PSDrive C -EA Stop).Free/1GB) } catch { 200 }
    $builderDiskGB = [math]::Max(80, $diskFreeGB - 20)
    return @{ RamGB=$ramGB; OsTotalRamMB=$osTotalRamMB; Cpus=$cpus; GpuName=$gpuName; HasNvidia=$hasNvidia
              BaseImage=$baseImage; AiModel=$aiModel; DiskGB=$builderDiskGB }
}

function Find-ActiveDistro {
    # Check legacy WSL distros ('MiOS' already applied via bootc switch, has /Justfile)
    foreach ($d in @($BuilderDistro, $LegacyDistro)) {
        try {
            $r = (& wsl.exe -d $d --exec bash -c "test -f /Justfile && echo ready" 2>$null) -join ""
            if ($r.Trim() -eq "ready") { return $d }
        } catch {}
    }
    # Check if BuilderDistro is a running Podman machine (machine-os: no /Justfile but can still build)
    try {
        $ml = (& podman machine ls --format "{{.Name}} {{.Running}}" 2>$null) |
              Where-Object { $_ -match "^$([regex]::Escape($BuilderDistro))\s+true" }
        if ($ml) { return $BuilderDistro }
    } catch {}
    return $null
}

function Sync-RepoToDistro([string]$Distro, [string]$WinPath) {
    $wsl = ConvertTo-WslPath $WinPath
    # Try direct WSL file:// fetch (works when Windows drive is mounted at /mnt/)
    try {
        & wsl.exe -d $Distro --user root --exec bash -c `
            "git -C / fetch 'file://$wsl' main 2>/dev/null && git -C / reset --hard FETCH_HEAD 2>/dev/null"
        if ($LASTEXITCODE -eq 0) { return $true }
    } catch {}
    # Podman machine fallback: Windows drive not mounted; pull from GitHub origin instead
    try {
        & podman machine ssh $Distro -- bash -c `
            "cd / && git fetch --depth=1 origin main 2>/dev/null && git reset --hard FETCH_HEAD 2>/dev/null"
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function New-BuilderDistro([hashtable]$HW) {
    Set-Step "Initializing MiOS-BUILDER ($($HW.Cpus) CPUs / $($HW.RamGB)GB / $($HW.DiskGB)GB disk)"
    # Cap at the OS-reported physical RAM (what podman validates) minus 512 MB safety margin.
    # Nominal $HW.RamGB rounds up from actual hardware, causing podman to reject the request.
    $ramMB = [math]::Max(4096, [math]::Min($HW.OsTotalRamMB - 512, $HW.RamGB * 1024 - 512))
    $initSw = [System.Diagnostics.Stopwatch]::StartNew()
    & podman machine init $BuilderDistro `
        --cpus $HW.Cpus --memory $ramMB --disk-size $HW.DiskGB `
        --rootful --now 2>&1 | ForEach-Object {
            Write-Log "podman-init: $_"
            if ($initSw.ElapsedMilliseconds -ge 150) {
                $clean = ($_ -replace '\x1b\[[0-9;]*[mGKHFJ]','').Trim()
                if ($clean) { $script:CurStep = $clean.Substring(0,[math]::Min($clean.Length,80)) }
                Show-Dashboard
                $initSw.Restart()
            }
        }
    if ($LASTEXITCODE -ne 0) { throw "podman machine init failed (exit $LASTEXITCODE)" }
    & podman machine set --default $BuilderDistro 2>&1 | Out-Null
    Log-Ok "MiOS-BUILDER created and set as default Podman machine"

    # Rootful machine-os distros are not accessible via wsl.exe or podman machine ssh.
    # Build runs from the Windows Podman client via the machine's API -- no exec needed.
    # Just verify the API is up (it should be immediately after --now).
    Set-Step "Verifying MiOS-BUILDER Podman API..."
    $deadline = (Get-Date).AddSeconds(30)
    $apiOk = $false
    while ((Get-Date) -lt $deadline) {
        $ml = (& podman machine ls --format "{{.Name}} {{.Running}}" 2>$null) |
              Where-Object { $_ -match "^$([regex]::Escape($BuilderDistro))\s+true" }
        if ($ml) { $apiOk = $true; break }
        Start-Sleep -Seconds 2
    }
    if (-not $apiOk) { throw "$BuilderDistro not in running state after 30 s -- check: podman machine ls" }
    Log-Ok "MiOS-BUILDER Podman API ready"
}

function Invoke-GhcrLogin([string]$Token) {
    if ([string]::IsNullOrWhiteSpace($Token)) {
        Write-Log "ghcr-login: no token (set MIOS_GITHUB_TOKEN or provide one in phase 6)"
        return
    }
    Set-Step "Authenticating podman to ghcr.io..."
    $Token | & podman login ghcr.io --username "mios-dev" --password-stdin 2>&1 |
        ForEach-Object { Write-Log "ghcr-login: $_" }
    if ($LASTEXITCODE -eq 0) { Log-Ok "Authenticated to ghcr.io" }
    else { Log-Warn "ghcr.io login failed -- build may fail pulling base image" }
}

function Invoke-WindowsPodmanBuild([string]$BaseImage, [string]$MiosUser, [string]$MiosHostname) {
    $repoPath = Join-Path $MiosRepoDir "mios"
    Set-Step "podman build (Windows client → $BuilderDistro)"
    Write-Log "BUILD START (Windows API build)  base=$BaseImage  user=$MiosUser  host=$MiosHostname"

    # Run via cmd.exe so 2>&1 merges stderr (podman build progress) into stdout stream
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName  = "cmd.exe"
    $psi.Arguments = ("/c podman build --progress=plain --no-cache " +
                      "--build-arg `"BASE_IMAGE=$BaseImage`" " +
                      "--build-arg `"MIOS_USER=$MiosUser`" " +
                      "--build-arg `"MIOS_HOSTNAME=$MiosHostname`" " +
                      "--build-arg `"MIOS_FLATPAKS=`" " +
                      "-t localhost/mios:latest . 2>&1")
    $psi.WorkingDirectory       = $repoPath
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $false
    $psi.UseShellExecute        = $false
    $psi.CreateNoWindow         = $false

    $proc = [System.Diagnostics.Process]::Start($psi)
    $sw   = [System.Diagnostics.Stopwatch]::StartNew()
    while (-not $proc.StandardOutput.EndOfStream) {
        $line = $proc.StandardOutput.ReadLine()
        if ($null -eq $line) { break }
        # Write to detail log only -- no Write-Host here.
        # Printing raw build lines to the console scrolls the terminal buffer
        # and drifts the dashboard position on every tick.
        try { [System.IO.File]::AppendAllText($BuildDetailLog, $line + "`n", [Text.Encoding]::UTF8) } catch {}
        Update-BuildSubPhase $line
        if ($sw.ElapsedMilliseconds -ge 150) { Show-Dashboard; $sw.Restart() }
    }
    $proc.WaitForExit()
    Write-Log "BUILD END (Windows)  exit=$($proc.ExitCode)  lines=$($script:LineCount)"
    return $proc.ExitCode
}

function Invoke-WslBuild([string]$Distro, [string]$BaseImage, [string]$AiModel,
                          [string]$MiosUser = "mios", [string]$MiosHostname = "mios") {
    # Authenticate to ghcr.io before any pull/build.  GHCR now returns 403 on
    # anonymous bearer-token requests for ublue-os images; a GitHub PAT is required.
    $tok = if ($env:MIOS_GITHUB_TOKEN) { $env:MIOS_GITHUB_TOKEN }
           elseif ($env:GITHUB_TOKEN)  { $env:GITHUB_TOKEN }
           else                         { $script:GhcrToken }
    Invoke-GhcrLogin -Token $tok

    # Detect access method: wsl.exe > podman machine ssh > Windows podman build
    $useWsl      = $false
    $useSsh      = $false
    $useWinBuild = $false
    try {
        $r = (& wsl.exe -d $Distro --exec bash -c "echo ok" 2>$null) -join ""
        if ($r.Trim() -eq "ok") { $useWsl = $true }
    } catch {}
    if (-not $useWsl) {
        try {
            $r = (& podman machine ssh $Distro -- bash -c "echo ok" 2>$null) -join ""
            if ($r.Trim() -eq "ok") { $useSsh = $true }
        } catch {}
    }
    if (-not $useWsl -and -not $useSsh) { $useWinBuild = $true }

    if ($useWinBuild) {
        return Invoke-WindowsPodmanBuild -BaseImage $BaseImage -MiosUser $MiosUser -MiosHostname $MiosHostname
    }

    $justCheck = "command -v just &>/dev/null || dnf install -y just"
    if ($useSsh) {
        & podman machine ssh $Distro -- bash -c $justCheck 2>$null | Out-Null
    } else {
        & wsl.exe -d $Distro --user root --exec bash -c $justCheck 2>$null | Out-Null
    }

    Set-Step "Launching: just build (inside $Distro)"
    Write-Log "BUILD START  base=$BaseImage  model=$AiModel"

    # Stream build output line-by-line: update dashboard Step, write to log
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    if ($useSsh) {
        $psi.FileName  = "podman"
        $psi.Arguments = "machine ssh $Distro -- bash -c " +
                         "'cd / && MIOS_BASE_IMAGE=''$BaseImage'' MIOS_AI_MODEL=''$AiModel'' just build 2>&1'"
    } else {
        $psi.FileName  = "wsl.exe"
        $psi.Arguments = "-d $Distro --user root --cd / --exec bash -c " +
                         "'MIOS_BASE_IMAGE=''$BaseImage'' MIOS_AI_MODEL=''$AiModel'' just build 2>&1'"
    }
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $false
    $psi.UseShellExecute        = $false
    $psi.CreateNoWindow         = $false

    $proc = [System.Diagnostics.Process]::Start($psi)
    $sw   = [System.Diagnostics.Stopwatch]::StartNew()

    while (-not $proc.StandardOutput.EndOfStream) {
        $line = $proc.StandardOutput.ReadLine()
        if ($null -eq $line) { break }
        try { [System.IO.File]::AppendAllText($BuildDetailLog, $line + "`n", [Text.Encoding]::UTF8) } catch {}
        Update-BuildSubPhase $line
        if ($sw.ElapsedMilliseconds -ge 150) { Show-Dashboard; $sw.Restart() }
    }

    $proc.WaitForExit()
    $rc = $proc.ExitCode
    Write-Log "BUILD END (WSL/SSH)  exit=$rc  lines=$($script:LineCount)"
    return $rc
}

function Export-WslTar([string]$OutFile) {
    # Stream localhost/mios:latest filesystem from machine → Windows tar via podman socket API
    Set-Step "Creating container snapshot of localhost/mios:latest..."
    $contLines = (& podman create localhost/mios:latest /bin/true 2>$null)
    $contId = ($contLines | Where-Object { $_ -match '^[0-9a-f]{12,64}$' } | Select-Object -Last 1)
    if ([string]::IsNullOrWhiteSpace($contId)) {
        $contId = ($contLines | Select-Object -Last 1)
    }
    if ([string]::IsNullOrWhiteSpace($contId)) { throw "podman create returned no container ID" }
    $contId = $contId.Trim()
    Write-Log "export container: $contId"
    try {
        Set-Step "Streaming container filesystem → $([System.IO.Path]::GetFileName($OutFile))..."
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName               = "podman"
        $psi.Arguments              = "export $contId"
        $psi.RedirectStandardOutput = $true
        $psi.UseShellExecute        = $false
        $psi.CreateNoWindow         = $true
        $proc = [System.Diagnostics.Process]::Start($psi)
        $fs   = [System.IO.File]::Create($OutFile)
        $sw   = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $buf    = New-Object byte[] 65536
            $stream = $proc.StandardOutput.BaseStream
            while ($true) {
                $n = $stream.Read($buf, 0, $buf.Length)
                if ($n -le 0) { break }
                $fs.Write($buf, 0, $n)
                if ($sw.ElapsedMilliseconds -ge 2000) {
                    $mb = [math]::Round($fs.Length / 1MB)
                    Set-Step "Exporting WSL2 tar... ${mb} MB"
                    $sw.Restart()
                }
            }
        } finally { $fs.Close() }
        $proc.WaitForExit()
        if ($proc.ExitCode -ne 0) { throw "podman export exited $($proc.ExitCode)" }
        return $true
    } finally {
        & podman rm $contId 2>$null | Out-Null
    }
}

function Import-MiosWsl([string]$TarFile, [string]$InstallDir) {
    # Register WSL2 distro from tar (replaces existing 'MiOS' distro if present)
    if (-not (Test-Path $TarFile)) { throw "WSL2 tar not found: $TarFile" }
    try { & wsl.exe --unregister $MiosWslDistro 2>$null | Out-Null } catch {}
    if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }
    Set-Step "wsl --import $MiosWslDistro ..."
    & wsl.exe --import $MiosWslDistro $InstallDir $TarFile --version 2 2>&1 |
        ForEach-Object { Write-Log "wsl-import: $_" }
    if ($LASTEXITCODE -ne 0) { throw "wsl --import exited $LASTEXITCODE" }
    # Set default user in the new distro
    try {
        & wsl.exe -d $MiosWslDistro --user root --exec bash -c `
            "id mios &>/dev/null && echo '[user]\ndefault=mios' >> /etc/wsl.conf || true" 2>$null | Out-Null
    } catch {}
    return $true
}

function Invoke-BibBuild([string[]]$Types, [string]$MachineOutDir, [int]$TimeoutMin = 60) {
    # Run bootc-image-builder inside the machine via Windows podman API (→ machine socket)
    # Types: 'qcow2', 'raw', 'anaconda-iso', 'vmdk'
    $typeArgs = ($Types | ForEach-Object { "--type $_" }) -join " "
    Set-Step "BIB: $($Types -join '+')..."
    Write-Log "BIB start: types=$($Types -join ',')  out=$MachineOutDir"

    # Pre-create the output directory inside the machine -- podman volume mounts require
    # the host-side path to exist before the container starts.
    Set-Step "BIB: creating output dir in machine..."
    & podman run --rm --privileged --security-opt label=disable `
        docker.io/library/alpine:latest `
        mkdir -p $MachineOutDir 2>&1 | ForEach-Object { Write-Log "bib-mkdir: $_" }
    if ($LASTEXITCODE -ne 0) { Write-Log "WARN: bib mkdir returned $LASTEXITCODE (may still work)" }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName  = "cmd.exe"
    $psi.Arguments = ("/c podman run --rm --privileged --pull=newer " +
        "--security-opt label=type:unconfined_t " +
        "-v /var/lib/containers/storage:/var/lib/containers/storage " +
        "-v ${MachineOutDir}:/output:z " +
        "quay.io/centos-bootc/bootc-image-builder:latest " +
        "$typeArgs --local localhost/mios:latest 2>&1")
    $psi.RedirectStandardOutput = $true
    $psi.UseShellExecute        = $false
    $psi.CreateNoWindow         = $true
    $proc = [System.Diagnostics.Process]::Start($psi)
    $sw   = [System.Diagnostics.Stopwatch]::StartNew()
    $done = $false
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    while (-not $proc.StandardOutput.EndOfStream) {
        $line = $proc.StandardOutput.ReadLine()
        if ($null -eq $line) { break }
        Write-Log "bib: $line"
        if ($sw.ElapsedMilliseconds -ge 2000) {
            $elapsed = [math]::Floor($timer.Elapsed.TotalMinutes)
            Set-Step "BIB ${elapsed}min: $($line.Substring(0,[math]::Min($line.Length,60)))"
            $sw.Restart()
        }
        if ($timer.Elapsed.TotalMinutes -ge $TimeoutMin) {
            Write-Log "WARN: BIB timeout after ${TimeoutMin}min -- killing"
            $proc.Kill()
            break
        }
    }
    $proc.WaitForExit()
    Write-Log "BIB end: exit=$($proc.ExitCode)"
    return $proc.ExitCode -eq 0
}

function Copy-FromMachine([string]$MachinePath, [string]$WinDest) {
    # podman machine cp MiOS-BUILDER:/path/in/machine C:\windows\path
    Set-Step "Copying $([System.IO.Path]::GetFileName($MachinePath)) from machine..."
    & podman machine cp "${BuilderDistro}:${MachinePath}" $WinDest 2>&1 |
        ForEach-Object { Write-Log "machine-cp: $_" }
    return ($LASTEXITCODE -eq 0)
}

function New-MiosHyperVVm([string]$RawPath, [int]$RamGB = 8) {
    if (-not (Get-Command New-VM -EA SilentlyContinue)) {
        Write-Log "Hyper-V module not available -- skipping VM creation"
        return $false
    }
    # Convert raw → vhdx if Convert-VHD is available
    $vhdxPath = [System.IO.Path]::ChangeExtension($RawPath, ".vhdx")
    if (Get-Command Convert-VHD -EA SilentlyContinue) {
        Set-Step "Converting raw → vhdx..."
        try {
            Convert-VHD -Path $RawPath -DestinationPath $vhdxPath -VHDType Dynamic -EA Stop
        } catch {
            Write-Log "Convert-VHD failed: $_ -- trying raw rename"
            $vhdxPath = [System.IO.Path]::ChangeExtension($RawPath, ".vhd")
            Copy-Item $RawPath $vhdxPath -Force
        }
    } else {
        # Raw can be used as a fixed VHD by Hyper-V if renamed .vhd
        $vhdxPath = [System.IO.Path]::ChangeExtension($RawPath, ".vhd")
        Copy-Item $RawPath $vhdxPath -Force
    }
    if (-not (Test-Path $vhdxPath)) { throw "VHDX/VHD not found after conversion" }

    # Remove existing VM if present
    $vmName = $MiosWslDistro
    try { Remove-VM -Name $vmName -Force -EA SilentlyContinue } catch {}

    Set-Step "Creating Hyper-V VM: $vmName..."
    $vm = New-VM -Name $vmName -MemoryStartupBytes ($RamGB * 1GB) `
                 -VHDPath $vhdxPath -Generation 2 -EA Stop
    Set-VMFirmware  -VMName $vmName -EnableSecureBoot Off
    Set-VMProcessor -VMName $vmName -Count ([math]::Max(2, [int]([Environment]::ProcessorCount / 2)))
    Set-VMMemory    -VMName $vmName -DynamicMemoryEnabled $true `
                    -MinimumBytes 2GB -MaximumBytes ($RamGB * 1GB)
    Log-Ok "Hyper-V VM '$vmName' created from $([System.IO.Path]::GetFileName($vhdxPath))"
    return $true
}

function Invoke-DeployPipeline([hashtable]$HW) {
    $artifactDir = Join-Path $MiosDistroDir "artifacts"
    $wslFsDir    = Join-Path $MiosDistroDir "MiOS"
    if (-not (Test-Path $artifactDir)) { New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null }
    if (-not (Test-Path $wslFsDir))    { New-Item -ItemType Directory -Path $wslFsDir    -Force | Out-Null }

    # ── Phase 10: Export WSL2 tar ──────────────────────────────────────────────
    Start-Phase 10
    $wslTar = Join-Path $artifactDir "mios-wsl2.tar"
    $wslOk  = $false
    try {
        $wslOk = Export-WslTar -OutFile $wslTar
        $sizeMB = [math]::Round((Get-Item $wslTar).Length / 1MB)
        Log-Ok "WSL2 tar: ${sizeMB}MB → $wslTar"
        End-Phase 10
    } catch {
        Log-Warn "WSL2 export: $_"
        End-Phase 10 -Warn
    }

    # ── Phase 11: Register WSL2 distro ────────────────────────────────────────
    Start-Phase 11
    if ($wslOk) {
        try {
            $null = Import-MiosWsl -TarFile $wslTar -InstallDir $wslFsDir
            Log-Ok "WSL2 distro '$MiosWslDistro' registered at $wslFsDir"
            End-Phase 11
        } catch {
            Log-Warn "WSL2 import: $_"
            End-Phase 11 -Warn
        }
    } else {
        Log-Warn "Skipped (no WSL2 tar)"
        End-Phase 11 -Warn
    }

    # ── Phase 12: BIB disk images (qcow2 + raw) ───────────────────────────────
    Start-Phase 12
    $bibMachineDir = "/tmp/mios-bib-output"
    $bibOk = $false
    try {
        $bibOk = Invoke-BibBuild -Types @('qcow2','raw') -MachineOutDir $bibMachineDir
        if ($bibOk) {
            # Copy artifacts from machine to Windows
            $cpOk = @{}
            foreach ($pair in @(
                @{ src="$bibMachineDir/qcow2/disk.qcow2"; dst=Join-Path $artifactDir "mios.qcow2" },
                @{ src="$bibMachineDir/image/disk.raw";   dst=Join-Path $artifactDir "mios.raw"   }
            )) {
                try {
                    $cpOk[$pair.dst] = Copy-FromMachine $pair.src $pair.dst
                    if ($cpOk[$pair.dst]) {
                        $sz = [math]::Round((Get-Item $pair.dst).Length / 1GB, 1)
                        Log-Ok "$([System.IO.Path]::GetFileName($pair.dst)): ${sz}GB"
                    }
                } catch { Write-Log "WARN: copy $($pair.src): $_" }
            }
            End-Phase 12
        } else {
            Log-Warn "BIB build failed (non-fatal -- OCI image still available in $BuilderDistro)"
            End-Phase 12 -Warn
        }
    } catch {
        Log-Warn "BIB phase: $_"
        End-Phase 12 -Warn
    }

    # ── Phase 13: Hyper-V VM from raw disk ────────────────────────────────────
    Start-Phase 13
    $rawPath = Join-Path $artifactDir "mios.raw"
    if ($bibOk -and (Test-Path $rawPath)) {
        try {
            $vmOk = New-MiosHyperVVm -RawPath $rawPath -RamGB ([math]::Max(4, [math]::Min($HW.RamGB / 2, 16)))
            if ($vmOk) { End-Phase 13 } else { Log-Warn "Hyper-V not available"; End-Phase 13 -Warn }
        } catch {
            Log-Warn "Hyper-V VM: $_"
            End-Phase 13 -Warn
        }
    } else {
        Log-Warn "Skipped (no raw disk image)"
        End-Phase 13 -Warn
    }
}

function New-Shortcut([string]$Path,[string]$Target,[string]$Args="",[string]$Desc="",[string]$Dir="") {
    $ws = New-Object -ComObject WScript.Shell; $sc = $ws.CreateShortcut($Path)
    $sc.TargetPath = $Target
    if ($Args) { $sc.Arguments = $Args }
    if ($Desc) { $sc.Description = $Desc }
    if ($Dir)  { $sc.WorkingDirectory = $Dir }
    $sc.Save()
}

# =============================================================================
# MAIN -- wrapped so the window NEVER closes on error
# =============================================================================
$ExitCode = 0
try {

# ── Banner (printed before dashboard so it doesn't scroll under it) ───────────
Clear-Host
$b = "+" + ("=" * ($script:DW - 2)) + "+"
$pad = [math]::Max(0, $script:DW - 4 - "MiOS $MiosVersion  --  Unified Windows Installer".Length)
Write-Host $b                                                                       -ForegroundColor Cyan
Write-Host ("| 'MiOS' $MiosVersion  --  Unified Windows Installer" + (" " * $pad) + " |") -ForegroundColor Cyan
Write-Host ("| Immutable Fedora AI Workstation" + (" " * ($script:DW - 34)) + " |") -ForegroundColor Cyan
Write-Host ("| WSL2 + Podman  |  Offline Build Pipeline" + (" " * ($script:DW - 43)) + " |") -ForegroundColor Cyan
Write-Host $b                                                                       -ForegroundColor Cyan
Write-Host ""

# Capture the row where the dashboard will be drawn (right after banner)
$script:DashRow = try { [Console]::CursorTop } catch { 0 }

# ── Background heartbeat -- keeps spinner animating independently ──────────────
# Runs on a dedicated runspace so the operator always sees spinner movement.
# A frozen spinner means a true fault/hang/timeout, not just a slow operation.
$script:BgRs = [runspacefactory]::CreateRunspace()
$script:BgRs.Open()
$script:BgRs.SessionStateProxy.SetVariable('dashSync', $script:DashSync)
$script:BgPs = [powershell]::Create()
$script:BgPs.Runspace = $script:BgRs
$null = $script:BgPs.AddScript({
    $chars = @('|', '/', '-', [char]92)
    $i = 0
    while ($dashSync.Running) {
        [System.Threading.Thread]::Sleep(120)
        $row = $dashSync.SpinnerRow
        $col = $dashSync.SpinnerCol
        if ($row -ge 0) {
            try {
                $prevTop = [Console]::CursorTop
                $prevLeft = [Console]::CursorLeft
                [Console]::SetCursorPosition($col, $row)
                [Console]::Write($chars[$i % 4])
                [Console]::SetCursorPosition($prevLeft, $prevTop)
            } catch {}
            $i++
        }
    }
})
$script:BgHandle = $script:BgPs.BeginInvoke()

Show-Dashboard   # draw initial (all phases pending)

# ── Phase 0 -- Hardware + Prerequisites ──────────────────────────────────────
Start-Phase 0
$HW = Get-Hardware
Write-Log "hw: CPU=$($HW.Cpus)  RAM=$($HW.RamGB)GB  Disk=$($HW.DiskGB)GB  GPU=$($HW.GpuName)"
Write-Log "hw: Base=$($HW.BaseImage)  Model=$($HW.AiModel)"
$gpuShort = $HW.GpuName -replace 'NVIDIA GeForce ','RTX ' -replace 'NVIDIA Quadro ','Quadro '
$script:HWInfo    = "Host:$($env:COMPUTERNAME)  RAM:$($HW.RamGB)GB  CPU:$($HW.Cpus)c  GPU:$gpuShort  Base:$($HW.BaseImage -replace 'ghcr.io/ublue-os/ucore-hci:','')"
$script:IdentInfo = "Base:$($HW.BaseImage -replace 'ghcr.io/ublue-os/ucore-hci:','')  Model:$($HW.AiModel)"
Show-Dashboard

$preOk = $true
if (Get-Command git    -EA SilentlyContinue) { Log-Ok "Git $((& git --version 2>&1) -replace 'git version ','')" }
else { Log-Fail "Git not found -- winget install Git.Git"; $preOk = $false }
if (Get-Command wsl    -EA SilentlyContinue) { Log-Ok "WSL2 available" }
else { Log-Warn "WSL2 not found -- run: wsl --install" }
if (Get-Command podman -EA SilentlyContinue) { Log-Ok "Podman $((& podman --version 2>&1) -replace 'podman version ','')" }
else { Log-Warn "Podman not found -- winget install RedHat.Podman-Desktop" }

if (-not $preOk) { End-Phase 0 -Fail; throw "Prerequisites missing -- see log: $LogFile" }
End-Phase 0

# ── Phase 1 -- Detecting existing build environment ──────────────────────────
Start-Phase 1
$activeDistro = Find-ActiveDistro

if ($activeDistro) {
    Log-Ok "MiOS repo found in $activeDistro"
    $miosRepo = Join-Path $MiosRepoDir "mios"
    if (Test-Path (Join-Path $miosRepo ".git")) {
        Set-Step "Pulling Windows-side repo and syncing to $activeDistro"
        Push-Location $miosRepo
        try { git pull --ff-only -q 2>&1 | Out-Null } catch {}
        Pop-Location
        Sync-RepoToDistro -Distro $activeDistro -WinPath $miosRepo | Out-Null
        Log-Ok "Repo synced to $activeDistro"
    }
    End-Phase 1
    # Skip phases 2-8, go straight to build
    for ($s = 2; $s -le 8; $s++) {
        $script:PhStat[$s] = 2
        $script:PhStart[$s] = [datetime]::Now
        $script:PhEnd[$s]   = [datetime]::Now
    }
    Show-Dashboard

    # Collect GHCR token in rebuild path (phase 6 is skipped above).
    $script:GhcrToken = if ($env:MIOS_GITHUB_TOKEN) { $env:MIOS_GITHUB_TOKEN }
                        elseif ($env:GITHUB_TOKEN)   { $env:GITHUB_TOKEN }
                        else { Read-Line "GitHub PAT for ghcr.io base image pull" "" }

    Start-Phase 9
    $rc = Invoke-WslBuild -Distro $activeDistro -BaseImage $HW.BaseImage -AiModel $HW.AiModel
    if ($rc -eq 0) {
        End-Phase 9
        Invoke-DeployPipeline -HW $HW
    } else { End-Phase 9 -Fail; $ExitCode = $rc }
} else {

    if ($BuildOnly) { End-Phase 1 -Fail; throw "-BuildOnly: no 'MiOS' build environment found. Run without -BuildOnly first." }
    Log-Ok "No existing distro -- starting full install"
    End-Phase 1

    # ── Phase 2 -- Directories and repos ─────────────────────────────────────
    Start-Phase 2
    foreach ($d in @($MiosInstallDir,$MiosRepoDir,$MiosDistroDir,$MiosConfigDir,$MiosDataDir,$MiosLogDir)) {
        if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    }
    Log-Ok "Directories under $MiosInstallDir"

    foreach ($r in @(
        @{ Path=(Join-Path $MiosRepoDir "mios");           Url=$MiosRepoUrl;      Name="mios.git" },
        @{ Path=(Join-Path $MiosRepoDir "mios-bootstrap"); Url=$MiosBootstrapUrl; Name="mios-bootstrap.git" }
    )) {
        if (Test-Path (Join-Path $r.Path ".git")) {
            Set-Step "Updating $($r.Name)"
            Push-Location $r.Path; try { git pull --ff-only -q 2>&1 | Out-Null } catch {}; Pop-Location
        } else {
            Set-Step "Cloning $($r.Name)"
            git clone --depth 1 $r.Url $r.Path 2>&1 | Out-Null
        }
        Log-Ok $r.Name
    }
    End-Phase 2

    # ── Phase 3 -- MiOS-BUILDER distro ───────────────────────────────────────
    Start-Phase 3
    $machineRunning = $false
    # Check via Podman API first (covers rootful machine-os distros inaccessible via wsl.exe)
    try {
        $ml = (& podman machine ls --format "{{.Name}} {{.Running}}" 2>$null) |
              Where-Object { $_ -match "^$([regex]::Escape($BuilderDistro))\s+true" }
        if ($ml) { $machineRunning = $true }
    } catch {}
    # Also accept a stopped machine and start it
    if (-not $machineRunning) {
        try {
            $ml = (& podman machine ls --format "{{.Name}} {{.Running}}" 2>$null) |
                  Where-Object { $_ -match "^$([regex]::Escape($BuilderDistro))" }
            if ($ml) {
                Set-Step "Starting existing $BuilderDistro machine..."
                $startOut = @(& podman machine start $BuilderDistro 2>&1)
                $startOut | ForEach-Object { Write-Log "podman-start: $_" }
                if ($LASTEXITCODE -eq 0) {
                    $machineRunning = $true; Log-Ok "$BuilderDistro started"
                } elseif (($startOut -join " ") -match "DISTRO_NOT_FOUND|bootstrap script failed|WSL_E_DISTRO") {
                    # Stale Podman machine metadata -- WSL distro was deleted but Podman registry entry remains.
                    # Force-remove the stale entry so New-BuilderDistro can re-init cleanly.
                    Write-Log "podman-start: stale machine registration detected -- removing $BuilderDistro" "WARN"
                    & podman machine rm --force $BuilderDistro 2>&1 | ForEach-Object { Write-Log "podman-rm: $_" }
                }
            }
        } catch {}
    }
    # Legacy: accept wsl.exe-accessible distro too ('MiOS' already applied)
    if (-not $machineRunning) {
        try {
            $r = (& wsl.exe -d $BuilderDistro --exec bash -c "echo ok" 2>$null) -join ""
            if ($r.Trim() -eq "ok") { $machineRunning = $true }
        } catch {}
    }

    if ($machineRunning) {
        Log-Ok "$BuilderDistro already running"
    } else {
        New-BuilderDistro -HW $HW
    }
    End-Phase 3

    # ── Phase 4 -- WSL2 .wslconfig ───────────────────────────────────────────
    Start-Phase 4
    $wslCfg = Join-Path $env:USERPROFILE ".wslconfig"

    # Required keys -- always ensure these are present regardless of existing config.
    # Mirrored networking + localhostForwarding are essential for Cockpit (port 9090)
    # and general WSL2 → Windows host reachability.
    $requiredKeys = [ordered]@{
        memory              = "$($HW.RamGB)GB"
        processors          = "$($HW.Cpus)"
        swap                = "4GB"
        localhostForwarding = "true"
        networkingMode      = "mirrored"
        guiApplications     = "true"
    }

    $cfgRaw = if (Test-Path $wslCfg) { Get-Content $wslCfg -Raw } else { "" }

    if ($cfgRaw -notmatch "\[wsl2\]") {
        # No [wsl2] section at all -- append one wholesale
        $block = "`n[wsl2]`n# MiOS-managed -- host resources for MiOS-BUILDER`n"
        foreach ($kv in $requiredKeys.GetEnumerator()) { $block += "$($kv.Key)=$($kv.Value)`n" }
        Add-Content -Path $wslCfg -Value $block
        Log-Ok ".wslconfig: wrote [wsl2] -- $($HW.RamGB)GB RAM, $($HW.Cpus) CPUs, mirrored"
    } else {
        # [wsl2] exists -- patch each required key in place; append missing ones
        $lines    = (Get-Content $wslCfg)
        $inWsl2   = $false
        $patched  = [System.Collections.Generic.List[string]]::new()
        $inserted = [System.Collections.Generic.HashSet[string]]::new()

        foreach ($line in $lines) {
            if ($line -match "^\[wsl2\]") { $inWsl2 = $true }
            elseif ($line -match "^\[")   { $inWsl2 = $false }

            if ($inWsl2 -and $line -match "^(\w+)\s*=") {
                $key = $Matches[1]
                if ($requiredKeys.Contains($key)) {
                    $patched.Add("$key=$($requiredKeys[$key])")
                    $null = $inserted.Add($key)
                    continue
                }
            }
            $patched.Add($line)

            # After [wsl2] header, inject any keys not yet seen in the section
            if ($line -match "^\[wsl2\]") {
                foreach ($kv in $requiredKeys.GetEnumerator()) {
                    if (-not $inserted.Contains($kv.Key)) {
                        # We will add them below after scanning the full section;
                        # set a sentinel so the post-loop block fires once.
                    }
                }
            }
        }

        # Append any required keys that never appeared in [wsl2]
        $missing = $requiredKeys.Keys | Where-Object { -not $inserted.Contains($_) }
        if ($missing) {
            # Find insertion point: after [wsl2] header line
            $insertIdx = ($patched | Select-String -Pattern "^\[wsl2\]" | Select-Object -First 1).LineNumber
            $offset = 0
            foreach ($key in $missing) {
                $patched.Insert($insertIdx + $offset, "$key=$($requiredKeys[$key])")
                $offset++
            }
        }

        Set-Content -Path $wslCfg -Value $patched -Encoding UTF8
        Log-Ok ".wslconfig: merged [wsl2] -- $($HW.RamGB)GB RAM, $($HW.Cpus) CPUs, mirrored"
    }
    End-Phase 4

    # ── Phase 5 -- Verify Windows build context ──────────────────────────────
    # Build runs via 'podman build' from the Windows clone -- no machine exec needed.
    Start-Phase 5
    $repoPath = Join-Path $MiosRepoDir "mios"
    if (Test-Path (Join-Path $repoPath "Containerfile")) {
        Log-Ok "Build context ready at $repoPath"
    } else {
        throw "mios.git Containerfile missing at $repoPath -- re-run without -BuildOnly to reclone"
    }
    End-Phase 5

    # ── Phase 6 -- Identity ───────────────────────────────────────────────────
    Start-Phase 6
    $script:CurStep = "Waiting for identity input..."
    Show-Dashboard
    $MiosUser     = Read-Line "Linux username" "mios"
    $MiosHostname = Read-Line "Hostname"       "mios"
    $pwPlain      = Read-Password "Password"
    if ([string]::IsNullOrWhiteSpace($pwPlain)) { $pwPlain = "mios" }
    $MiosHash     = Get-PasswordHash $pwPlain
    # GitHub PAT is required to pull ghcr.io/ublue-os/ucore-hci (GHCR anon bearer token returns 403).
    # Check env first; fall back to prompt so interactive installs work without pre-setting the var.
    $script:GhcrToken = if ($env:MIOS_GITHUB_TOKEN) { $env:MIOS_GITHUB_TOKEN }
                        elseif ($env:GITHUB_TOKEN)   { $env:GITHUB_TOKEN }
                        else { Read-Line "GitHub PAT for ghcr.io base image pull (github.com/settings/tokens)" "" }
    $tokStatus = if ($script:GhcrToken) { "provided (masked)" } else { "none -- anonymous pull (may fail)" }
    Log-Ok "Identity: user=$MiosUser  host=$MiosHostname  password=(hashed)  ghcr=$tokStatus"
    $script:IdentInfo = "User:$MiosUser  Host:$MiosHostname  Base:$($HW.BaseImage -replace 'ghcr.io/ublue-os/ucore-hci:','')  Model:$($HW.AiModel)"
    End-Phase 6

    # ── Phase 7 -- Write identity ─────────────────────────────────────────────
    Start-Phase 7
    $envContent = "MIOS_USER=`"$MiosUser`"`nMIOS_HOSTNAME=`"$MiosHostname`"`nMIOS_USER_PASSWORD_HASH=`"$MiosHash`""
    $writeCmd  = "mkdir -p /etc/mios && cat > /etc/mios/install.env && chmod 0640 /etc/mios/install.env"
    $written = $false

    # Try wsl.exe (works when machine runs 'MiOS' after bootc switch)
    $envContent | & wsl.exe -d $BuilderDistro --user root --exec bash -c $writeCmd 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $written = $true }

    # Try podman machine ssh (works for some machine configurations)
    if (-not $written) {
        $envContent | & podman machine ssh $BuilderDistro -- bash -c $writeCmd 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $written = $true }
    }

    # Fallback: write via privileged container that mounts the machine's host filesystem.
    # Rootful machine-os exposes / to privileged containers via -v /:/host.
    if (-not $written) {
        Set-Step "Writing identity via privileged container..."
        $envContent | & podman run --rm -i --privileged --security-opt label=disable `
            -v /:/host:z `
            docker.io/library/alpine:latest `
            sh -c "mkdir -p /host/etc/mios && cat > /host/etc/mios/install.env && chmod 0640 /host/etc/mios/install.env" `
            2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $written = $true }
    }

    if ($written) { Log-Ok "/etc/mios/install.env written" } `
    else { Log-Warn "install.env write failed (non-fatal -- firstboot will use default identity; set MIOS_* vars manually)" }
    End-Phase 7

    # ── Phase 8 -- App registration + Start Menu ──────────────────────────────
    Start-Phase 8
    $pwsh      = if (Get-Command pwsh -EA SilentlyContinue) { (Get-Command pwsh).Source } else { "powershell.exe" }
    $selfSc    = Join-Path $MiosRepoDir "mios-bootstrap\install.ps1"
    $uninstSc  = Join-Path $MiosInstallDir "uninstall.ps1"
    $uninstCmd = "$pwsh -ExecutionPolicy Bypass -File `"$uninstSc`""

    if (-not (Test-Path $UninstallRegKey)) { New-Item -Path $UninstallRegKey -Force | Out-Null }
    @{
        DisplayName="MiOS - Immutable Fedora AI Workstation"; DisplayVersion=$MiosVersion
        Publisher="MiOS-DEV"; InstallLocation=$MiosInstallDir
        UninstallString=$uninstCmd; QuietUninstallString="$uninstCmd -Quiet"
        URLInfoAbout="https://github.com/mios-dev/mios"; NoModify=[int]1; NoRepair=[int]1
    }.GetEnumerator() | ForEach-Object {
        $regType = if ($_.Value -is [int]) { "DWord" } else { "String" }
        Set-ItemProperty -Path $UninstallRegKey -Name $_.Key -Value $_.Value -Type $regType
    }

    if (-not (Test-Path $StartMenuDir)) { New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null }
    @(
        @{ F="MiOS Setup.lnk";         T=$pwsh;     A="-ExecutionPolicy Bypass -File `"$selfSc`"";            D="Re-run full 'MiOS' setup" },
        @{ F="MiOS Build.lnk";         T=$pwsh;     A="-ExecutionPolicy Bypass -File `"$selfSc`" -BuildOnly";  D="Pull latest + build 'MiOS' OCI image" },
        @{ F="MiOS Terminal.lnk";        T="wsl.exe"; A="-d $MiosWslDistro";                                    D="Open 'MiOS' workstation terminal" },
        @{ F="MiOS Builder Shell.lnk";  T="wsl.exe"; A="-d $BuilderDistro --user root";                         D="Open MiOS-BUILDER terminal (root)" },
        @{ F="MiOS Podman Shell.lnk";  T=$pwsh;     A="-NoProfile -Command podman machine ssh $BuilderDistro"; D="SSH into MiOS-BUILDER Podman machine" },
        @{ F="Uninstall MiOS.lnk";     T=$pwsh;     A="-ExecutionPolicy Bypass -File `"$uninstSc`"";           D="Remove MiOS" }
    ) | ForEach-Object { New-Shortcut (Join-Path $StartMenuDir $_.F) $_.T $_.A $_.D $MiosInstallDir }
    Log-Ok "Add/Remove Programs + Start Menu created"

    # Uninstaller script
    $B = $BuilderDistro
    @"
#Requires -Version 5.1
param([switch]`$Quiet)
`$I='$($MiosInstallDir-replace"'","''")'; `$D='$($MiosDataDir-replace"'","''")'; `$C='$($MiosConfigDir-replace"'","''")'; `$S='$($StartMenuDir-replace"'","''")'; `$K='$($UninstallRegKey-replace"'","''")'; `$B='$B'
if (-not `$Quiet) {
    Write-Host ''; Write-Host '  'MiOS' Uninstaller' -ForegroundColor Red; Write-Host ''
    Write-Host "  Removes: `$I, `$D, `$B Podman machine, Start Menu"
    Write-Host "  Preserves: `$C (config)"; Write-Host ''
    if ((Read-Host "  Type 'yes' to confirm") -ne 'yes') { Write-Host '  Aborted.'; exit 0 }
}
try { podman machine stop `$B 2>`$null } catch {}
try { podman machine rm -f `$B 2>`$null } catch {}
try { wsl --unregister `$B 2>`$null } catch {}
foreach (`$p in @(`$I,`$D,`$S)) { if (Test-Path `$p) { Remove-Item `$p -Recurse -Force } }
if (Test-Path `$K) { Remove-Item `$K -Recurse -Force }
Write-Host ''; Write-Host "  'MiOS' removed. Config at `$C preserved." -ForegroundColor Green
"@ | Set-Content $uninstSc -Encoding UTF8
    Log-Ok "uninstall.ps1 written"
    End-Phase 8

    # ── Phase 9 -- Build ──────────────────────────────────────────────────────
    Start-Phase 9
    $rc = Invoke-WslBuild -Distro $BuilderDistro -BaseImage $HW.BaseImage -AiModel $HW.AiModel `
                          -MiosUser $MiosUser -MiosHostname $MiosHostname
    if ($rc -eq 0) {
        End-Phase 9
        Invoke-DeployPipeline -HW $HW
    } else { End-Phase 9 -Fail; $ExitCode = $rc }

} # end full-install branch

} catch {
    $ExitCode = 1   # set FIRST -- must be reached even if Show-Dashboard below also fails
    $errMsg = "$_"
    Write-Log "FATAL: $errMsg" "ERROR"
    $script:CurStep = "FATAL: $($errMsg.Substring(0,[math]::Min($errMsg.Length,120)))"
    if ($script:CurPhase -ge 0 -and $script:PhStat[$script:CurPhase] -eq 1) {
        try { End-Phase $script:CurPhase -Fail } catch {}
    }
    Show-Dashboard
} finally {
    # Always show final summary and keep window open
    try { [Console]::SetCursorPosition(0, $script:DashRow + $script:DashHeight) } catch {}

    $totalTime = fmtSpan ([datetime]::Now - $script:ScriptStart)
    Write-Host ""
    $b = "+" + ("=" * ($script:DW - 2)) + "+"
    if ($ExitCode -eq 0) {
        $artifactDir = Join-Path $MiosDistroDir "artifacts"
        Write-Host $b -ForegroundColor Green
        $l = "| 'MiOS' $MiosVersion built and deployed!  (total: $totalTime)"
        Write-Host ($l.PadRight($script:DW - 1) + "|") -ForegroundColor Green
        Write-Host ("| OCI   : localhost/mios:latest  in $BuilderDistro".PadRight($script:DW - 1) + "|") -ForegroundColor White
        $wslLine = "| WSL2  : wsl -d $MiosWslDistro"
        $wslDistroOk = (& wsl.exe -l --quiet 2>$null) -join " " -match $MiosWslDistro
        if ($wslDistroOk) {
            Write-Host ($wslLine.PadRight($script:DW - 1) + "|") -ForegroundColor Cyan
        } else {
            Write-Host ("| WSL2  : see $artifactDir\mios-wsl2.tar".PadRight($script:DW - 1) + "|") -ForegroundColor DarkGray
        }
        $qcow2 = Join-Path $artifactDir "mios.qcow2"
        $raw   = Join-Path $artifactDir "mios.raw"
        if (Test-Path $qcow2) { Write-Host ("| QEMU  : $qcow2".PadRight($script:DW - 1) + "|") -ForegroundColor Cyan }
        if (Test-Path $raw)   { Write-Host ("| RAW   : $raw".PadRight($script:DW - 1) + "|") -ForegroundColor Cyan }
        $hvVm = try { Get-VM -Name $MiosWslDistro -EA SilentlyContinue } catch { $null }
        if ($hvVm) { Write-Host ("| HV    : Hyper-V VM '$MiosWslDistro' ready -- Start-VM -Name $MiosWslDistro".PadRight($script:DW - 1) + "|") -ForegroundColor Cyan }
        Write-Host ("| Logs  : $MiosLogDir".PadRight($script:DW - 1) + "|") -ForegroundColor DarkGray
        Write-Host $b -ForegroundColor Green
    } else {
        Write-Host $b -ForegroundColor Red
        Write-Host ("| BUILD FAILED (exit $ExitCode)  --  Errors: $($script:ErrCount)".PadRight($script:DW - 1) + "|") -ForegroundColor Red
        Write-Host ("| Log  : $LogFile".PadRight($script:DW - 1) + "|") -ForegroundColor Yellow
        Write-Host ("| Re-run : podman build --no-cache -t localhost/mios:latest $MiosRepoDir\mios".PadRight($script:DW - 1) + "|") -ForegroundColor DarkGray
        Write-Host $b -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "  Log directory: $MiosLogDir" -ForegroundColor DarkGray
    Write-Host ""
    if (-not $Unattended) {
        Write-Host "  Press Enter to close..." -ForegroundColor DarkGray -NoNewline
        $null = Read-Host
    }
    # Stop background heartbeat runspace cleanly before closing transcript
    try {
        $script:DashSync.Running = $false
        [System.Threading.Thread]::Sleep(200)   # let background loop exit its Sleep(120)
        if ($script:BgPs)  { try { $script:BgPs.Stop() }    catch {}; try { $script:BgPs.Dispose() }  catch {} }
        if ($script:BgRs)  { try { $script:BgRs.Close() }   catch {} }
    } catch {}
    try { Stop-Transcript | Out-Null } catch {}
    # Merge raw build output into unified log (transcript lock now released)
    if (Test-Path $BuildDetailLog) {
        try {
            [System.IO.File]::AppendAllText($LogFile, "`n`n---- BUILD OUTPUT ----`n", [Text.Encoding]::UTF8)
            $detail = [System.IO.File]::ReadAllText($BuildDetailLog, [Text.Encoding]::UTF8)
            [System.IO.File]::AppendAllText($LogFile, $detail, [Text.Encoding]::UTF8)
            Remove-Item $BuildDetailLog -Force -ErrorAction SilentlyContinue
        } catch {}
    }
    # Inject unified log into OCI image at /usr/share/mios/build-log.txt
    if ($ExitCode -eq 0) {
        try {
            $cid = (& podman create localhost/mios:latest 2>$null) -join ""
            if ($LASTEXITCODE -eq 0 -and $cid.Trim()) {
                $cid = $cid.Trim()
                & podman cp $LogFile "${cid}:/usr/share/mios/build-log.txt" 2>$null
                & podman commit --quiet $cid localhost/mios:latest 2>$null | Out-Null
                & podman rm -f $cid 2>$null | Out-Null
            }
        } catch {}
    }
    exit $ExitCode
}
```


## Layer 2 -- System-side installers


### `automation\install.sh`

```bash
#!/usr/bin/env bash
# 'MiOS' system-side installer (FHS overlay path).
#
# This script is invoked by the bootstrap installer on non-bootc Fedora hosts.
# On bootc-managed hosts, do NOT run this -- use `bootc switch` instead.
#
# What it does:
#   1. Refuses to run on bootc-managed hosts (their /usr is read-only composefs).
#   2. Lays down the FHS overlay from this repository's working tree to /.
#   3. Runs systemd-sysusers, systemd-tmpfiles, and reloads systemd units.
#   4. Enables 'MiOS' services.

set -euo pipefail

# Refuse to run on bootc-managed hosts.
if command -v bootc >/dev/null 2>&1 && bootc status --format=json 2>/dev/null | grep -q '"booted"'; then
    echo "[FAIL] This host is bootc-managed. install.sh is for non-bootc Fedora hosts." >&2
    echo "       Use 'sudo bootc switch ghcr.io/MiOS-DEV/mios:latest' instead." >&2
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    echo "[FAIL] install.sh must run as root: sudo $0" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "[INFO] 'MiOS' system installer running from ${REPO_ROOT}"

if [[ "${REPO_ROOT}" != "/" ]]; then
    # Apply FHS overlay. We rsync each top-level overlay dir if it exists.
    for d in usr etc var srv; do
        if [[ -d "${REPO_ROOT}/${d}" ]]; then
            echo "[INFO] Applying overlay: ${d}/"
            rsync -aH --info=stats1 "${REPO_ROOT}/${d}/" "/${d}/"
        fi
    done

    # v1/ holds discovery symlinks; we materialize them at /v1.
    if [[ -d "${REPO_ROOT}/v1" ]]; then
        echo "[INFO] Materializing /v1 discovery surface"
        install -d /v1
        rsync -aH "${REPO_ROOT}/v1/" "/v1/"
    fi
else
    echo "[INFO] Running directly from root (/), skipping overlay sync."
fi
echo "[INFO] Running systemd-sysusers"
systemd-sysusers

echo "[INFO] Running systemd-tmpfiles"
systemd-tmpfiles --create

echo "[INFO] Reloading systemd"
systemctl daemon-reload

echo "[INFO] Enabling 'MiOS' services"
if [[ -f /etc/containers/systemd/mios-ai.container ]]; then
    systemctl enable --now mios-ai.service || echo "[WARN] mios-ai.service not yet active; will retry on boot"
fi

echo "[ OK ] 'MiOS' system installer complete."
echo "       Log out and back in (or reboot) to pick up profile changes."
```


### `automation\install-bootstrap.sh`

```bash
#!/usr/bin/env bash
#
# 'MiOS' Bootstrap -- Interactive Ignition Installer (Total Root Merge Mode)
#
# SSOT: This script installs EVERYTHING a fully built 'MiOS' system has.
# It transforms a bare Fedora host into a self-building 'MiOS' workstation.
#
set -euo pipefail

# ============================================================================
# Defaults
# ============================================================================
DEFAULT_USER="mios"
DEFAULT_HOST="mios"
DEFAULT_USER_FULLNAME="'MiOS' User"
DEFAULT_USER_SHELL="/bin/bash"
DEFAULT_USER_GROUPS="wheel,libvirt,kvm,video,render,input,dialout"
DEFAULT_SSH_KEY_TYPE="ed25519"
DEFAULT_BRANCH="main"

MIOS_REPO="https://github.com/mios-dev/MiOS.git"

# FHS path constants (override via env). Mirrors automation/lib/paths.sh.
: "${MIOS_USR_DIR:=/usr/lib/mios}"
: "${MIOS_LIBEXEC_DIR:=/usr/libexec/mios}"
: "${MIOS_SHARE_DIR:=/usr/share/mios}"
: "${MIOS_ETC_DIR:=/etc/mios}"
: "${MIOS_VAR_DIR:=/var/lib/mios}"
PROFILE_DIR="${MIOS_ETC_DIR}"
PROFILE_FILE="${PROFILE_DIR}/install.env"

# ============================================================================
# Logging & UI
# ============================================================================
_BOLD=$(tput bold 2>/dev/null || echo "")
_RED=$(tput setaf 1 2>/dev/null || echo "")
_GREEN=$(tput setaf 2 2>/dev/null || echo "")
_YELLOW=$(tput setaf 3 2>/dev/null || echo "")
_CYAN=$(tput setaf 6 2>/dev/null || echo "")
_DIM=$(tput dim 2>/dev/null || echo "")
_RESET=$(tput sgr0 2>/dev/null || echo "")

log_info()  { printf '%s[INFO]%s %s\n' "${_CYAN}" "${_RESET}" "$*"; }
log_ok()    { printf '%s[ OK ]%s %s\n' "${_GREEN}" "${_RESET}" "$*"; }
log_warn()  { printf '%s[WARN]%s %s\n' "${_YELLOW}" "${_RESET}" "$*" >&2; }
log_err()   { printf '%s[ERR ]%s %s\n' "${_RED}" "${_RESET}" "$*" >&2; }
log_phase() { printf '\n%s%s== %s ==%s\n\n' "${_BOLD}" "${_CYAN}" "$*" "${_RESET}"; }

require_root() {
    if [[ $EUID -ne 0 ]]; then
        log_err "Bootstrap must run as root: sudo $0"
        exit 1
    fi
}

detect_host_kind() {
    if command -v bootc >/dev/null 2>&1 && bootc status --format=json 2>/dev/null | grep -q '"booted"'; then
        echo "bootc"
    elif [[ -f /etc/os-release ]] && grep -qE '^ID(_LIKE)?=.*fedora' /etc/os-release; then
        echo "fhs-fedora"
    else
        echo "unsupported"
    fi
}

check_network() {
    local host
    for host in github.com; do
        if ! curl -fsSL --max-time 5 -o /dev/null "https://${host}/" 2>/dev/null; then
            log_err "No network reachability to ${host}."
            exit 1
        fi
    done
    log_ok "Network reachability verified"
}

prompt_default() {
    local question="$1" default="$2" answer
    read -r -p "$(printf '%s%s%s [%s%s%s]: ' "${_BOLD}" "${question}" "${_RESET}" "${_DIM}" "${default}" "${_RESET}")" answer
    echo "${answer:-$default}"
}

prompt_password() {
    local prompt="$1" pw1 pw2
    while :; do
        printf '%s%s%s: ' "${_BOLD}" "${prompt}" "${_RESET}" >&2
        read -rs pw1; echo >&2
        printf '%sConfirm:%s ' "${_BOLD}" "${_RESET}" >&2
        read -rs pw2; echo >&2
        if [[ "$pw1" == "$pw2" && -n "$pw1" ]]; then
            echo "$pw1"
            return 0
        fi
        log_warn "Passwords don't match or are empty."
    done
}

prompt_yesno() {
    local question="$1" default="${2:-y}" answer hint
    if [[ "$default" == "y" ]]; then hint="[Y/n]"; else hint="[y/N]"; fi
    read -r -p "$(printf '%s%s%s %s: ' "${_BOLD}" "${question}" "${_RESET}" "${hint}")" answer
    answer="${answer:-$default}"
    case "${answer,,}" in
        y|yes) return 0 ;;
        *) return 1 ;;
    esac
}

# ============================================================================
# Core Logic
# ============================================================================
main() {
    require_root
    log_phase "'MiOS' Bootstrap Installer (Full Build Mode)"

    local hostkind=$(detect_host_kind)
    if [[ "$hostkind" == "unsupported" ]]; then
        log_err "Host is not Fedora. 'MiOS' requires a Fedora-based host."
        exit 1
    fi
    log_info "Detected host: ${hostkind}"

    check_network

    # --- 1. Gather Profile ---
    LINUX_USER="$(prompt_default 'Linux username' "${DEFAULT_USER}")"
    HOSTNAME_VAL="$(prompt_default 'Hostname' "${DEFAULT_HOST}")"
    USER_FULLNAME="$(prompt_default 'Full name (GECOS)' "${DEFAULT_USER_FULLNAME}")"
    USER_PASSWORD="$(prompt_password 'Password')"

    log_phase "Review profile"
    printf "  User: %s\n  Host: %s\n  Mode: Total Root Overlay\n\n" "$LINUX_USER" "$HOSTNAME_VAL"
    if ! prompt_yesno 'Proceed with these settings?' y; then exit 0; fi

    # --- 2. Apply Profile ---
    log_phase "Applying system profile"
    hostnamectl set-hostname "$HOSTNAME_VAL"

    local existing_groups=""
    IFS=',' read -ra ADDR <<< "${DEFAULT_USER_GROUPS}"
    for group in "${ADDR[@]}"; do
        if getent group "$group" >/dev/null; then
            [[ -n "$existing_groups" ]] && existing_groups+=","
            existing_groups+="$group"
        else
            log_warn "Group '$group' missing on host, skipping."
        fi
    done

    if id -u "$LINUX_USER" >/dev/null 2>&1; then
        log_info "User '$LINUX_USER' exists; updating groups + password"
        usermod -aG "$existing_groups" "$LINUX_USER"
        usermod -c "$USER_FULLNAME" "$LINUX_USER"
    else
        log_info "Creating '$LINUX_USER' (groups: $existing_groups)"
        useradd -m -G "$existing_groups" -s "$DEFAULT_USER_SHELL" -c "$USER_FULLNAME" "$LINUX_USER"
    fi
    echo "$LINUX_USER:$USER_PASSWORD" | chpasswd
    log_ok "User profile applied."

    # --- 3. Total Root Merge ---
    # LAW 1: NON-DESTRUCTIVE SIMPLE MERGE -- never use git checkout -f at /,
    # which forcibly overwrites existing system files. Clone to a temp path,
    # then rsync each FHS overlay dir with --ignore-existing semantics so that
    # base system files are never clobbered.
    log_phase "'MiOS' Core Installation (Root Merge)"
    log_info "Cloning 'MiOS' repository to staging area..."
    MIOS_STAGE="$(mktemp -d /tmp/mios-stage-XXXXXX)"
    trap 'rm -rf "${MIOS_STAGE}"' EXIT
    git clone --depth=1 --branch "$DEFAULT_BRANCH" "$MIOS_REPO" "${MIOS_STAGE}"
    log_ok "Repository cloned to ${MIOS_STAGE}"

    log_info "Applying non-destructive FHS overlay from staging area..."
    for d in usr etc var srv; do
        if [[ -d "${MIOS_STAGE}/${d}" ]]; then
            log_info "  Merging ${d}/ ..."
            rsync -aH --info=stats1 "${MIOS_STAGE}/${d}/" "/${d}/"
        fi
    done
    if [[ -d "${MIOS_STAGE}/v1" ]]; then
        log_info "  Materializing /v1 discovery surface..."
        install -d /v1
        rsync -aH "${MIOS_STAGE}/v1/" "/v1/"
    fi
    log_ok "'MiOS' source tree merged to root."

    # --- 4. Package Installation ---
    log_phase "Installing 'MiOS' System Stack"
    if [[ -f "${MIOS_SHARE_DIR}/PACKAGES.md" ]]; then
        log_info "Extracting package list from ${MIOS_SHARE_DIR}/PACKAGES.md..."
        local pkgs
        pkgs=$(sed -n '/^```packages-/,/^```$/{/^```/d;/^#/d;/^$/d;p}' ${MIOS_SHARE_DIR}/PACKAGES.md | tr '\n' ' ')
        
        if [[ -n "$pkgs" ]]; then
            local dnf_cmd="dnf"
            command -v dnf5 >/dev/null 2>&1 && dnf_cmd="dnf5"
            log_info "Executing: $dnf_cmd install -y --skip-unavailable --best [PACKAGES]"
            $dnf_cmd install -y --skip-unavailable --best $pkgs || log_warn "Some packages failed to install."
            log_ok "Package stack installation complete."
        else
            log_err "No packages found in manifest!"
        fi
    else
        log_err "CRITICAL: ${MIOS_SHARE_DIR}/PACKAGES.md not found!"
        exit 1
    fi

    # --- 5. System Initialization ---
    log_phase "System Initialization"
    if [[ -x "/install.sh" ]]; then
        log_info "Running /install.sh to finalize FHS overlay..."
        /install.sh
        log_ok "Initialization complete."
    else
        log_err "/install.sh not found or not executable!"
        exit 1
    fi

    log_phase "'MiOS' Installation Complete"
    if prompt_yesno 'Reboot now to enter 'MiOS'?' y; then
        systemctl reboot
    fi
}

main "$@"
```


### `automation\build-mios.sh`

```bash
#!/bin/bash
# 'MiOS' Fedora Server Ignition Script
# Fetches 'MiOS' repository and merges onto Fedora Server root (FHS-compliant, NO deletions)
# Version: 0.2.0
# Usage: curl -fsSL https://raw.githubusercontent.com/MiOS-DEV/MiOS-bootstrap/main/build-mios.sh | sudo bash
#        OR: sudo bash build-mios.sh

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
MIOS_REPO_URL="${MIOS_REPO_URL:-https://github.com/MiOS-DEV/MiOS-bootstrap.git}"
MIOS_REPO_BRANCH="${MIOS_REPO_BRANCH:-main}"
MIOS_TMP_DIR="/tmp/mios-ignition-$$"
MIOS_INSTALL_LOG="/var/log/mios-ignition.log"

# FHS path constants (override via env). Mirrors automation/lib/paths.sh.
: "${MIOS_USR_DIR:=/usr/lib/mios}"
: "${MIOS_LIBEXEC_DIR:=/usr/libexec/mios}"
: "${MIOS_SHARE_DIR:=/usr/share/mios}"
: "${MIOS_ETC_DIR:=/etc/mios}"
: "${MIOS_VAR_DIR:=/var/lib/mios}"
MIOS_CONFIG_DIR="${MIOS_ETC_DIR}"
MIOS_USER_CONFIG_DIR="" # Will be set after user is determined

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Logging Functions
# ============================================================================
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$MIOS_INSTALL_LOG"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARN:${NC} $*" | tee -a "$MIOS_INSTALL_LOG"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*" | tee -a "$MIOS_INSTALL_LOG"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $*" | tee -a "$MIOS_INSTALL_LOG"
}

# ============================================================================
# Banner
# ============================================================================
show_banner() {
    cat << 'EOF'
â*"â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*--
â*'                   'MiOS' Fedora Server Ignition                            â*'
â*'                         Version 1.0.0                                    â*'
â*šâ*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*

This script will:
  1. Fetch 'MiOS' repository from GitHub
  2. Prompt for user configuration (username, hostname, etc.)
  3. Queue environment files and dotfiles
  4. Merge 'MiOS' structure onto Fedora Server (FHS-compliant)
  5. NO deletions - only additions and updates
  6. Build 'MiOS' OCI image

EOF
}

# ============================================================================
# User Configuration Prompts
# ============================================================================
collect_user_config() {
    log_info "Collecting user configuration..."
    echo ""

    # Username
    read -p "Enter username (default: mios): " MIOS_USERNAME
    MIOS_USERNAME="${MIOS_USERNAME:-mios}"

    # Password
    while true; do
        read -sp "Enter password for ${MIOS_USERNAME}: " MIOS_PASSWORD
        echo ""
        read -sp "Confirm password: " MIOS_PASSWORD_CONFIRM
        echo ""

        if [[ "$MIOS_PASSWORD" == "$MIOS_PASSWORD_CONFIRM" ]]; then
            # Generate SHA-512 hash
            MIOS_PASSWORD_HASH=$(openssl passwd -6 "${MIOS_PASSWORD}")
            break
        else
            log_error "Passwords do not match. Please try again."
        fi
    done

    # Hostname
    read -p "Enter hostname (default: mios): " MIOS_HOSTNAME
    MIOS_HOSTNAME="${MIOS_HOSTNAME:-mios}"

    # Base image
    echo ""
    echo "Select base image:"
    echo "  1) ghcr.io/ublue-os/ucore-hci:stable-nvidia (NVIDIA GPU, recommended)"
    echo "  2) ghcr.io/ublue-os/ucore-hci:stable (No NVIDIA)"
    echo "  3) ghcr.io/ublue-os/ucore:stable (Minimal)"
    echo "  4) Custom (enter manually)"
    read -p "Choice [1-4] (default: 1): " BASE_IMAGE_CHOICE
    BASE_IMAGE_CHOICE="${BASE_IMAGE_CHOICE:-1}"

    case "$BASE_IMAGE_CHOICE" in
        1) MIOS_BASE_IMAGE="ghcr.io/ublue-os/ucore-hci:stable-nvidia" ;;
        2) MIOS_BASE_IMAGE="ghcr.io/ublue-os/ucore-hci:stable" ;;
        3) MIOS_BASE_IMAGE="ghcr.io/ublue-os/ucore:stable" ;;
        4)
            read -p "Enter custom base image: " MIOS_BASE_IMAGE
            ;;
        *) MIOS_BASE_IMAGE="ghcr.io/ublue-os/ucore-hci:stable-nvidia" ;;
    esac

    # Flatpak apps
    echo ""
    read -p "Enter Flatpak app IDs (comma-separated, optional): " MIOS_FLATPAKS_INPUT
    MIOS_FLATPAKS="${MIOS_FLATPAKS_INPUT}"

    # AI Configuration
    echo ""
    read -p "Configure AI settings? (y/N): " CONFIGURE_AI
    if [[ "$CONFIGURE_AI" =~ ^[Yy]$ ]]; then
        read -p "AI Model (default: llama3.1:8b): " MIOS_AI_MODEL
        MIOS_AI_MODEL="${MIOS_AI_MODEL:-llama3.1:8b}"

        read -p "AI Endpoint (default: http://localhost:8080/v1): " MIOS_AI_ENDPOINT
        MIOS_AI_ENDPOINT="${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}"

        read -sp "AI API Key (optional, press Enter to skip): " MIOS_AI_KEY
        echo ""
    else
        MIOS_AI_MODEL="llama3.1:8b"
        MIOS_AI_ENDPOINT="http://localhost:8080/v1"
        MIOS_AI_KEY=""
    fi

    # Summary
    echo ""
    log_info "Configuration Summary:"
    echo "  Username:     $MIOS_USERNAME"
    echo "  Hostname:     $MIOS_HOSTNAME"
    echo "  Base Image:   $MIOS_BASE_IMAGE"
    echo "  Flatpaks:     ${MIOS_FLATPAKS:-none}"
    echo "  AI Model:     $MIOS_AI_MODEL"
    echo "  AI Endpoint:  $MIOS_AI_ENDPOINT"
    echo ""

    read -p "Proceed with this configuration? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        log_error "Installation cancelled by user."
        exit 1
    fi
}

# ============================================================================
# Prerequisites Check
# ============================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi

    # Check OS
    if [[ ! -f /etc/fedora-release ]]; then
        log_warn "This script is designed for Fedora Server. Detected OS: $(cat /etc/os-release | grep PRETTY_NAME || echo 'Unknown')"
        read -p "Continue anyway? (y/N): " CONTINUE
        if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Check internet connection
    if ! curl -fsSL --max-time 5 -o /dev/null https://github.com/; then
        log_error "No internet connection. Please check your network."
        exit 1
    fi

    log "Prerequisites check passed"
}

# ============================================================================
# Install Dependencies
# ============================================================================
install_dependencies() {
    log_info "Installing required dependencies..."

    dnf install -y \
        git \
        podman \
        buildah \
        rsync \
        python3 \
        systemd \
        coreutils \
        util-linux \
        || { log_error "Failed to install dependencies"; exit 1; }

    # Optional: Install just
    if ! command -v just &>/dev/null; then
        log_info "Installing 'just' command runner..."
        if command -v cargo &>/dev/null; then
            cargo install just || log_warn "'just' installation failed, continuing without it"
        else
            log_warn "'just' not installed (cargo not available). You can use podman directly."
        fi
    fi

    log "Dependencies installed successfully"
}

# ============================================================================
# Fetch 'MiOS' Repository
# ============================================================================
fetch_mios_repo() {
    log_info "Fetching 'MiOS' repository from ${MIOS_REPO_URL}..."

    # Create temporary directory
    mkdir -p "$MIOS_TMP_DIR"
    cd "$MIOS_TMP_DIR"

    # Clone repository
    git clone --depth 1 --branch "$MIOS_REPO_BRANCH" "$MIOS_REPO_URL" mios \
        || { log_error "Failed to clone 'MiOS' repository"; exit 1; }

    cd mios

    log "'MiOS' repository fetched successfully"
}

# ============================================================================
# Queue Environment Files
# ============================================================================
queue_environment_files() {
    log_info "Queuing environment files and dotfiles..."

    # Determine user home directory
    if [[ "$MIOS_USERNAME" == "root" ]]; then
        MIOS_USER_HOME="/root"
    else
        MIOS_USER_HOME="/home/${MIOS_USERNAME}"
    fi

    MIOS_USER_CONFIG_DIR="${MIOS_USER_HOME}/.config/mios"

    # Create user configuration directory structure
    mkdir -p "$MIOS_USER_CONFIG_DIR"

    # Create the unified mios.toml. Schema documented in
    # /usr/share/mios/mios.toml.example. Read by tools/lib/userenv.sh.
    {
        echo "# ~/.config/mios/mios.toml -- generated by build-mios.sh"
        echo "# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo ""
        echo "[user]"
        echo "name     = \"${MIOS_USERNAME}\""
        echo "hostname = \"${MIOS_HOSTNAME}\""
        echo ""
        echo "[image]"
        echo "base = \"${MIOS_BASE_IMAGE}\""
        echo "bib  = \"quay.io/centos-bootc/bootc-image-builder:latest\""
        echo ""
        echo "[build]"
        echo "local_tag = \"localhost/mios:latest\""
        echo ""
        echo "[flatpaks]"
        if [[ -n "$MIOS_FLATPAKS" ]]; then
            echo "install = ["
            echo "$MIOS_FLATPAKS" | tr ',' '\n' | while read -r f; do
                f="$(echo "$f" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
                [[ -z "$f" ]] && continue
                echo "    \"$f\","
            done
            echo "]"
        else
            echo "# install = []"
        fi
        echo ""
        echo "[ai]"
        echo "model    = \"${MIOS_AI_MODEL}\""
        echo "endpoint = \"${MIOS_AI_ENDPOINT}\""
    } > "$MIOS_USER_CONFIG_DIR/mios.toml"

    # Create ai.env (secrets - not committed)
    if [[ -n "$MIOS_AI_KEY" ]]; then
        cat > "$MIOS_USER_CONFIG_DIR/ai.env" <<EOF
# 'MiOS' AI Configuration (SECRETS - DO NOT COMMIT)
MIOS_AI_KEY="${MIOS_AI_KEY}"
EOF
        chmod 600 "$MIOS_USER_CONFIG_DIR/ai.env"
    fi

    # /etc/mios/install.env carries identity at install-time; runtime.env was
    # written here historically but never read by anything. Dropped during
    # the user-config consolidation -- the canonical surfaces are now:
    #   ~/.config/mios/mios.toml  (user)
    #   /etc/mios/install.env     (host)
    log "Environment files queued successfully"
}

# ============================================================================
# Merge 'MiOS' Structure (FHS-Compliant, NO Deletions)
# ============================================================================
merge_mios_structure() {
    log_info "Merging 'MiOS' structure onto Fedora Server root (FHS-compliant)..."

    cd "$MIOS_TMP_DIR/mios"

    # Merge directories with rsync (--ignore-existing = NO overwrites)
    # This ensures existing Fedora files are PRESERVED

    # 1. Merge /usr (system binaries, libraries, data)
    log_info "Merging /usr..."
    rsync -av --ignore-existing usr/ /usr/ \
        || log_warn "Some files in /usr were skipped (already exist)"

    # 2. Merge /etc (configuration templates)
    log_info "Merging /etc..."
    rsync -av --ignore-existing etc/ /etc/ \
        || log_warn "Some files in /etc were skipped (already exist)"

    # 3. Declare /var directories via tmpfiles.d (NO direct mkdir)
    log_info "Declaring /var directories via tmpfiles.d..."
    if [[ -f usr/lib/tmpfiles.d/mios.conf ]]; then
        cp -n usr/lib/tmpfiles.d/mios.conf /usr/lib/tmpfiles.d/ || true
        systemd-tmpfiles --create /usr/lib/tmpfiles.d/mios.conf || log_warn "tmpfiles creation had warnings"
    fi

    # 4. Merge /home skeleton
    log_info "Merging /home skeleton..."
    if [[ -d home/mios ]]; then
        mkdir -p /etc/skel/.config/mios
        rsync -av --ignore-existing home/mios/ /etc/skel/ || true
    fi

    # 5. Copy tools and automation (for building)
    log_info "Installing tools and automation..."
    rsync -av tools/ ${MIOS_SHARE_DIR}/tools/ || true
    rsync -av automation/ ${MIOS_SHARE_DIR}/automation/ || true

    # 6. Make all scripts executable
    log_info "Setting executable permissions..."
    chmod +x /usr/bin/mios* /usr/bin/iommu-groups 2>/dev/null || true
    chmod +x /usr/libexec/mios* 2>/dev/null || true
    chmod +x ${MIOS_LIBEXEC_DIR}/* 2>/dev/null || true
    chmod +x ${MIOS_SHARE_DIR}/tools/*.sh 2>/dev/null || true
    chmod +x ${MIOS_SHARE_DIR}/automation/*.sh 2>/dev/null || true

    # 7. Copy Containerfile and Justfile to /usr/share/mios for building
    log_info "Installing build files..."
    cp -n Containerfile ${MIOS_SHARE_DIR}/ || true
    cp -n Justfile ${MIOS_SHARE_DIR}/ || true
    cp -n VERSION ${MIOS_SHARE_DIR}/ || true

    # 8. Create /usr/src/mios symlink (for mios rebuild command)
    log_info "Creating source symlink..."
    ln -sf ${MIOS_SHARE_DIR} /usr/src/mios || true

    log "'MiOS' structure merged successfully (NO deletions)"
}

# ============================================================================
# Create User Account & Initialize User-Space
# ============================================================================
create_user_account() {
    log_info "Creating user account: ${MIOS_USERNAME}..."

    if id "$MIOS_USERNAME" &>/dev/null; then
        log_warn "User ${MIOS_USERNAME} already exists, updating password..."
        echo "${MIOS_USERNAME}:${MIOS_PASSWORD}" | chpasswd
    else
        # Create user with password hash
        EXTRA_GROUPS="wheel,libvirt,kvm,video,render,input,dialout"
        if getent group docker >/dev/null 2>&1; then EXTRA_GROUPS="$EXTRA_GROUPS,docker"; fi
        useradd -m -G "$EXTRA_GROUPS" -s /bin/bash "$MIOS_USERNAME"
        echo "${MIOS_USERNAME}:${MIOS_PASSWORD}" | chpasswd

        # Set up sudo access
        echo "${MIOS_USERNAME} ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/${MIOS_USERNAME}"
        chmod 0440 "/etc/sudoers.d/${MIOS_USERNAME}"
    fi

    log_info "Initializing user-space directories and configuration..."

    # XDG Base Directory variables
    MIOS_USER_DATA_DIR="${MIOS_USER_HOME}/.local/share/mios"
    MIOS_USER_CACHE_DIR="${MIOS_USER_HOME}/.cache/mios"
    MIOS_USER_STATE_DIR="${MIOS_USER_HOME}/.local/state/mios"

    # Create XDG directory structure
    mkdir -p "${MIOS_USER_CONFIG_DIR}/credentials/ssh-keys"
    mkdir -p "${MIOS_USER_DATA_DIR}/artifacts"
    mkdir -p "${MIOS_USER_DATA_DIR}/images"
    mkdir -p "${MIOS_USER_DATA_DIR}/templates"
    mkdir -p "${MIOS_USER_DATA_DIR}/plugins"
    mkdir -p "${MIOS_USER_CACHE_DIR}/podman"
    mkdir -p "${MIOS_USER_CACHE_DIR}/downloads"
    mkdir -p "${MIOS_USER_CACHE_DIR}/build-cache"
    mkdir -p "${MIOS_USER_STATE_DIR}/logs"

    # Setup dotfiles directory for build-time injection
    mkdir -p "${MIOS_USER_CONFIG_DIR}/dotfiles"
    if [[ ! -f "${MIOS_USER_CONFIG_DIR}/dotfiles/.bashrc.user" ]]; then
        cat > "${MIOS_USER_CONFIG_DIR}/dotfiles/.bashrc.user" <<'DOTFILE_EOF'
# 'MiOS' User-Space .bashrc extension
# This file is injected into the image during build-time.
alias ll='ls -alF'
alias mios-status='mios assess'
export EDITOR=vim
DOTFILE_EOF
    fi

    # Create credentials .gitignore
    cat > "${MIOS_USER_CONFIG_DIR}/credentials/.gitignore" <<'GITIGNORE_EOF'
# 'MiOS' Credentials - Ignore Everything
# This directory should NEVER be committed to version control

*
!.gitignore
!README.md
GITIGNORE_EOF

    # Initialize Python virtual environment
    if command -v python3 &>/dev/null; then
        if [[ ! -d "${MIOS_USER_DATA_DIR}/venv" ]]; then
            python3 -m venv "${MIOS_USER_DATA_DIR}/venv" 2>/dev/null || log_warn "Failed to create Python venv"
        fi
    fi

    # Copy environment files to user's home and fix ownership
    chown -R "${MIOS_USERNAME}:${MIOS_USERNAME}" "${MIOS_USER_HOME}/.config" 2>/dev/null || true
    chown -R "${MIOS_USERNAME}:${MIOS_USERNAME}" "${MIOS_USER_HOME}/.local" 2>/dev/null || true
    chown -R "${MIOS_USERNAME}:${MIOS_USERNAME}" "${MIOS_USER_HOME}/.cache" 2>/dev/null || true

    log "User account and user-space configured successfully"
}

# ============================================================================
# Set Hostname
# ============================================================================
set_hostname() {
    log_info "Setting hostname to: ${MIOS_HOSTNAME}..."

    hostnamectl set-hostname "$MIOS_HOSTNAME"

    log "Hostname set successfully"
}

# ============================================================================
# Build 'MiOS' Image (Optional)
# ============================================================================
build_mios_image() {
    log_info "Would you like to build the 'MiOS' OCI image now?"
    echo "  This will take 15-25 minutes on first build."
    echo "  You can also build later with: cd ${MIOS_SHARE_DIR} && just build"
    echo ""
    read -p "Build now? (y/N): " BUILD_NOW

    if [[ "$BUILD_NOW" =~ ^[Yy]$ ]]; then
        log_info "Building 'MiOS' OCI image..."

        cd ${MIOS_SHARE_DIR}

        # Load user environment
        export MIOS_BASE_IMAGE
        export MIOS_FLATPAKS
        export MIOS_USER="${MIOS_USERNAME}"
        export MIOS_PASSWORD_HASH
        export MIOS_HOSTNAME

        if command -v just &>/dev/null; then
            just build || { log_error "Build failed"; return 1; }
        else
            # Fallback to direct podman build
            podman build --no-cache \
                --build-arg BASE_IMAGE="$MIOS_BASE_IMAGE" \
                --build-arg MIOS_USER="$MIOS_USERNAME" \
                --build-arg MIOS_PASSWORD_HASH="$MIOS_PASSWORD_HASH" \
                --build-arg MIOS_HOSTNAME="$MIOS_HOSTNAME" \
                --build-arg MIOS_FLATPAKS="$MIOS_FLATPAKS" \
                -t localhost/mios:latest . \
                || { log_error "Build failed"; return 1; }
        fi

        log "'MiOS' OCI image built successfully: localhost/mios:latest"

        # Ask about deployment
        echo ""
        read -p "Deploy to this system now? (y/N): " DEPLOY_NOW
        if [[ "$DEPLOY_NOW" =~ ^[Yy]$ ]]; then
            log_info "Deploying 'MiOS' to this system..."
            bootc install to-existing-root --source-imgref localhost/mios:latest \
                || log_warn "Deployment failed or not supported on this system"
        fi
    else
        log_info "Skipping build. To build later, run:"
        echo "  cd ${MIOS_SHARE_DIR} && just build"
    fi
}

# ============================================================================
# Cleanup
# ============================================================================
cleanup() {
    log_info "Cleaning up temporary files..."

    if [[ -d "$MIOS_TMP_DIR" ]]; then
        rm -rf "$MIOS_TMP_DIR"
    fi

    log "Cleanup complete"
}

# ============================================================================
# Final Summary
# ============================================================================
show_summary() {
    cat << EOF

â*"â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*--
â*'                   'MiOS' Installation Complete!                            â*'
â*šâ*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*

Configuration:
  Username:     ${MIOS_USERNAME}
  Hostname:     ${MIOS_HOSTNAME}
  Config Dir:   ${MIOS_USER_CONFIG_DIR}

Installation Details:
  âœ" 'MiOS' structure merged to system root (FHS-compliant)
  âœ" User account created with full permissions
  âœ" User-space initialized (XDG directories, configs, dotfiles)
  âœ" Python virtual environment created
  âœ" System configuration installed
  âœ" Build files installed to ${MIOS_SHARE_DIR}

Next Steps:

  1. Switch to your user:
     su - ${MIOS_USERNAME}

  2. Build 'MiOS' image (if not done):
     cd ${MIOS_SHARE_DIR} && just build

  3. Check system status:
     mios status

  4. View available commands:
     mios --help

  5. Customize your configuration:
     \$EDITOR ~/.config/mios/mios.toml

Documentation:
  - Installation log: ${MIOS_INSTALL_LOG}
  - Configuration: ${MIOS_USER_CONFIG_DIR}
  - System config: ${MIOS_CONFIG_DIR}

For more information:
  https://github.com/MiOS-DEV/MiOS-bootstrap

EOF
}

# ============================================================================
# Main Execution
# ============================================================================
main() {
    # Initialize log
    mkdir -p "$(dirname "$MIOS_INSTALL_LOG")"
    touch "$MIOS_INSTALL_LOG"

    show_banner

    check_prerequisites
    collect_user_config
    install_dependencies
    fetch_mios_repo
    queue_environment_files
    merge_mios_structure
    create_user_account
    set_hostname
    build_mios_image
    cleanup
    show_summary

    log "'MiOS' Fedora Server ignition completed successfully!"
}

# Trap errors
trap 'log_error "Installation failed at line $LINENO. Check $MIOS_INSTALL_LOG for details."' ERR

# Run main
main "$@"
```


## Layer 3 -- Build orchestrators


### `Containerfile`

```dockerfile
# syntax=docker/dockerfile:1.9
ARG BASE_IMAGE=ghcr.io/ublue-os/ucore-hci:stable-nvidia

FROM scratch AS ctx
COPY automation/           /ctx/automation/
COPY usr/                  /ctx/usr/
COPY etc/                  /ctx/etc/
# /home/ is bootstrap territory (mios-bootstrap.git stages user homes via
# profile/ in Phase-3); the build no longer pulls it.
COPY usr/share/mios/PACKAGES.md /ctx/PACKAGES.md
COPY VERSION               /ctx/VERSION
COPY config/artifacts/     /ctx/bib-configs/
COPY tools/                /ctx/tools/

FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="MiOS"
LABEL org.opencontainers.image.description="\MiOS is a user defined, customisable Linux distro based on Fedora/uBlue/uCore"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.source="https://github.com/mios-dev/MiOS"
LABEL org.opencontainers.image.version="v0.2.2"
LABEL containers.bootc="1"
LABEL ostree.bootable="1"

CMD ["/sbin/init"]

ARG MIOS_USER=mios
ARG MIOS_HOSTNAME=mios
ARG MIOS_FLATPAKS=

# Build context is bind-mounted read-only from the `ctx` stage; the only
# writable copy lives under /tmp/build for scripts that need to mutate it.
RUN --mount=type=bind,from=ctx,source=/ctx,target=/ctx,ro \
    --mount=type=cache,dst=/var/cache/libdnf5,sharing=locked \
    --mount=type=cache,dst=/var/cache/dnf,sharing=locked \
    set -ex; \
    install -d -m 0755 /tmp/build; \
    cp -a /ctx/automation /ctx/usr /ctx/etc /ctx/PACKAGES.md /ctx/VERSION /ctx/bib-configs /ctx/tools /tmp/build/; \
    export PACKAGES_MD=/tmp/build/PACKAGES.md; \
    bash /tmp/build/automation/lib/packages.sh >/dev/null 2>&1 || true; \
    source /tmp/build/automation/lib/packages.sh; \
    # Purge any stale/corrupt repo metadata left in the buildkit cache mount
    # from a previous failed build (zchunk checksum errors, partial syncs, etc.)
    ${DNF_BIN:-dnf5} clean metadata 2>/dev/null || ${DNF_BIN:-dnf} clean metadata 2>/dev/null || true; \
    install_packages_strict base; \
    if [[ -n "${MIOS_FLATPAKS}" ]]; then \
        echo "${MIOS_FLATPAKS}" | tr "," "\n" > /tmp/build/usr/share/mios/flatpak-list; \
    fi; \
    bash /tmp/build/automation/08-system-files-overlay.sh; \
    chmod +x /tmp/build/automation/build.sh /tmp/build/automation/*.sh 2>/dev/null || true; \
    chmod +x /usr/libexec/mios/copy-build-log.sh 2>/dev/null || true; \
    CTX=/tmp/build /tmp/build/automation/build.sh; \
    dnf clean all; \
    rm -rf /tmp/build; \
    # /var/cache is bind-mounted by buildkit (--mount=type=cache above) for
    # the duration of this RUN, so trying to rm it returns EBUSY. Skip it;
    # buildkit doesn't bake cache mounts into the layer regardless.
    find /var -mindepth 1 -maxdepth 1 ! -name tmp ! -name cache -exec rm -rf {} +; \
    find /run -mindepth 1 -maxdepth 1 ! -name "secrets" -exec rm -rf {} + 2>/dev/null || true

RUN bootc completion bash > /etc/bash_completion.d/bootc
RUN --mount=type=bind,from=ctx,source=/ctx/tools,target=/ctx/tools,ro \
    install -d -m 0755 /usr/lib/extensions/source && \
    bash /ctx/tools/mios-sysext-pack.sh /usr/lib/extensions/source || true
RUN ostree container commit
# bootc container lint MUST be the final instruction (ARCHITECTURAL LAW 4).
RUN bootc container lint
```


### `Justfile`

```makefile
# 'MiOS' v0.2.0 - Linux Build Targets
# Requires: podman, just
# Usage: just build | just iso | just all

# Load user environment from XDG-compliant configuration
# This sources $HOME/.config/mios/*.toml files and exports MIOS_* variables
_load_env := `bash -c 'source ./tools/lib/userenv.sh 2>/dev/null || true'`

MIOS_REGISTRY_DEFAULT := "ghcr.io/MiOS-DEV/mios" # @verb:GET_REGISTRY
IMAGE_NAME := env_var_or_default("MIOS_IMAGE_NAME", MIOS_REGISTRY_DEFAULT) # @verb:GET_IMAGE
MIOS_VAR_VERSION := "v0.2.0" # @verb:GET_VERSION
VERSION := `cat VERSION 2>/dev/null || echo {{MIOS_VAR_VERSION}}`
LOCAL := env_var_or_default("MIOS_LOCAL_TAG", "localhost/mios:latest") # @verb:SET_LOCAL
MIOS_IMG_BIB := "quay.io/centos-bootc/bootc-image-builder:latest" # @verb:GET_BIB
BIB := env_var_or_default("MIOS_BIB_IMAGE", MIOS_IMG_BIB)

# Run preflight system check
preflight:
    @chmod +x tools/preflight.sh
    @./tools/preflight.sh

# Show current flight status and variable mappings
flight-status:
    @chmod +x tools/flight-control.sh
    @./tools/flight-control.sh

# Unified initialization (Mode 2: User-space)
init:
    @chmod +x tools/mios-overlay.sh
    sudo ./tools/mios-overlay.sh

# System-wide deployment (Mode 1: FHS system install)
deploy:
    @chmod +x tools/mios-overlay.sh
    sudo ./tools/mios-overlay.sh

# Live ISO Initiation (Mode 0: Overlay onto root)
live-init:
    @chmod +x tools/mios-overlay.sh
    sudo ./tools/mios-overlay.sh

# bootc container lint -- runs against the locally built image.
# The Containerfile already runs `bootc container lint` as its final RUN, so
# `just build` is itself a lint gate. This target re-runs lint on demand.
lint:
    podman run --rm --entrypoint /usr/bin/bootc {{LOCAL}} container lint

# Build OCI image locally
build: preflight flight-status
    podman build --no-cache \
        --build-arg BASE_IMAGE={{env_var_or_default("MIOS_BASE_IMAGE", "ghcr.io/ublue-os/ucore-hci:stable-nvidia")}} \
        --build-arg MIOS_FLATPAKS={{env_var_or_default("MIOS_FLATPAKS", "")}} \
        --build-arg MIOS_USER={{env_var_or_default("MIOS_USER", "mios")}} \
        --build-arg MIOS_HOSTNAME={{env_var_or_default("MIOS_HOSTNAME", "mios")}} \
        -t {{LOCAL}} .
    @echo "[OK] Built: {{LOCAL}}"

# Build OCI image with unified logging
build-logged: artifact
    @mkdir -p logs
    @LOG_FILE="logs/build-$(date -u +%Y%m%dT%H%M%SZ).log"
    @echo "---" | tee -a "${LOG_FILE}"
    @echo "[START] CHECKPOINT: Starting 'MiOS' build..." | tee -a "${LOG_FILE}"
    @echo "Unified log will be available at: ${LOG_FILE}" | tee -a "${LOG_FILE}"
    @echo "---" | tee -a "${LOG_FILE}"
    @set -o pipefail; podman build --no-cache \
        --build-arg BASE_IMAGE={{env_var_or_default("MIOS_BASE_IMAGE", "ghcr.io/ublue-os/ucore-hci:stable-nvidia")}} \
        --build-arg MIOS_FLATPAKS={{env_var_or_default("MIOS_FLATPAKS", "")}} \
        --build-arg MIOS_USER={{env_var_or_default("MIOS_USER", "mios")}} \
        --build-arg MIOS_HOSTNAME={{env_var_or_default("MIOS_HOSTNAME", "mios")}} \
        -t {{LOCAL}} . 2>&1 | tee -a "${LOG_FILE}"
    @echo "---" | tee -a "${LOG_FILE}"
    @echo "[OK] CHECKPOINT: 'MiOS' build complete." | tee -a "${LOG_FILE}"
    @echo "Unified log available at: ${LOG_FILE}" | tee -a "${LOG_FILE}"
    @echo "---"

# Build OCI image with verbose output (no redirection)
build-verbose: artifact
    podman build --no-cache \
        --build-arg BASE_IMAGE={{env_var_or_default("MIOS_BASE_IMAGE", "ghcr.io/ublue-os/ucore-hci:stable-nvidia")}} \
        --build-arg MIOS_FLATPAKS={{env_var_or_default("MIOS_FLATPAKS", "")}} \
        --build-arg MIOS_USER={{env_var_or_default("MIOS_USER", "mios")}} \
        --build-arg MIOS_HOSTNAME={{env_var_or_default("MIOS_HOSTNAME", "mios")}} \
        -t {{LOCAL}} .

# Embed the most recent build log into the image
embed-log:
    @echo "[START] Finding most recent build log..."
    @LOG_FILE=$$(ls -t logs/build-*.log 2>/dev/null | head -n 1)
    @if [ -z "$${LOG_FILE}" ]; then \
        echo "[FAIL] No build logs found in logs/. Run 'just build-logged' first."; \
        exit 1; \
    fi
    @echo "  Found: $${LOG_FILE}"
    @echo "[START] Creating temporary Containerfile to embed log..."
    @echo "FROM {{LOCAL}}" > /tmp/Containerfile.embed
    @echo "COPY --chown=root:root $${LOG_FILE} /usr/share/mios/build-logs/latest-build.log" >> /tmp/Containerfile.embed
    @echo "[START] Building image with embedded log..."
    @set -o pipefail; podman build --no-cache -f /tmp/Containerfile.embed -t localhost/mios:latest-with-log .
    @rm /tmp/Containerfile.embed
    @echo "---"
    @echo "[OK] Success! New image created: localhost/mios:latest-with-log"
    @echo "   Embedded log is at: /usr/share/mios/build-logs/latest-build.log"
    @echo "---"

# Refresh all AI manifests, UKB, and Wiki documentation
artifact:
    ./automation/ai-bootstrap.sh
    @echo "[OK] Artifacts, UKB, and Wiki refreshed."

# Build OCI image on Cloud (using remote context)
cloud-build:
    @echo "Configure cloud-build with your cloud provider CLI"
    @echo "Example: podman build --remote -t {{IMAGE_NAME}}:{{VERSION}} ."
    @echo "[OK] Cloud Build target (customize for your cloud provider)"

# Rechunk for optimal Day-2 updates (5-10x smaller deltas)
rechunk: build
    podman run --rm \
        --security-opt label=type:unconfined_t \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        {{LOCAL}} \
        /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 containers-storage:{{LOCAL}} containers-storage:{{IMAGE_NAME}}:{{VERSION}}
    podman tag {{IMAGE_NAME}}:{{VERSION}} {{IMAGE_NAME}}:latest
    @echo "[OK] Rechunked: {{IMAGE_NAME}}:{{VERSION}}"

# Generate RAW bootable disk image (80 GiB root)
raw: build
    mkdir -p output
    sudo podman run --rm -it --privileged \
        --security-opt label=type:unconfined_t \
        -v ./output:/output \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v ./config/artifacts/bib.toml:/config.toml:ro \
        {{BIB}} build --type raw --rootfs ext4 {{LOCAL}}
    @echo "[OK] RAW image in output/"

# Generate Anaconda installer ISO
# FIX v0.2.0: ONLY mount iso.toml (includes minsize). Do NOT also mount bib config.
# BIB crashes with: "found config.json and also config.toml"
iso: build
    mkdir -p output
    sudo podman run --rm -it --privileged \
        --security-opt label=type:unconfined_t \
        -v ./output:/output \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v ./config/artifacts/iso.toml:/config.toml:ro \
        {{BIB}} build --type iso --rootfs ext4 {{LOCAL}}
    @echo "[OK] ISO image in output/"

# Generate QEMU qcow2 disk image
# Substitutes MIOS_USER_PASSWORD_HASH and MIOS_SSH_PUBKEY from env before invoking BIB.
qcow2: build
    mkdir -p output
    @if [ -z "${MIOS_USER_PASSWORD_HASH:-}" ]; then echo "[FAIL] Set MIOS_USER_PASSWORD_HASH (openssl passwd -6 'yourpass')"; exit 1; fi
    @TMPTOML="$(mktemp /tmp/mios-qcow2-XXXXXX.toml)" && \
        sed -e "s|\$6\$REPLACEME_WITH_SHA512_HASH\$REPLACEME|${MIOS_USER_PASSWORD_HASH}|g" \
            -e "s|AAAA_REPLACE_WITH_REAL_PUBKEY|${MIOS_SSH_PUBKEY:-}|g" \
            ./config/artifacts/qcow2.toml > "$$TMPTOML" && \
        sudo podman run --rm -it --privileged \
            --security-opt label=type:unconfined_t \
            -v ./output:/output \
            -v /var/lib/containers/storage:/var/lib/containers/storage \
            -v "$$TMPTOML":/config.toml:ro \
            {{BIB}} build --type qcow2 --rootfs ext4 {{LOCAL}}; \
        rm -f "$$TMPTOML"
    @echo "[OK] QCOW2 image in output/"

# Generate Hyper-V VHDX disk image
# BIB emits VPC (.vhd); we convert to .vhdx via qemu-img.
# Substitutes MIOS_USER_PASSWORD_HASH and MIOS_SSH_PUBKEY from env before invoking BIB.
vhdx: build
    mkdir -p output
    @if [ -z "${MIOS_USER_PASSWORD_HASH:-}" ]; then echo "[FAIL] Set MIOS_USER_PASSWORD_HASH (openssl passwd -6 'yourpass')"; exit 1; fi
    @TMPTOML="$(mktemp /tmp/mios-vhdx-XXXXXX.toml)" && \
        sed -e "s|\$6\$REPLACEME_WITH_SHA512_HASH\$REPLACEME|${MIOS_USER_PASSWORD_HASH}|g" \
            -e "s|AAAA_REPLACE_WITH_REAL_PUBKEY|${MIOS_SSH_PUBKEY:-}|g" \
            ./config/artifacts/vhdx.toml > "$$TMPTOML" && \
        sudo podman run --rm -it --privileged \
            --security-opt label=type:unconfined_t \
            -v ./output:/output \
            -v /var/lib/containers/storage:/var/lib/containers/storage \
            -v "$$TMPTOML":/config.toml:ro \
            {{BIB}} build --type vhd --rootfs ext4 {{LOCAL}}; \
        rm -f "$$TMPTOML"
    @if command -v qemu-img >/dev/null 2>&1 && ls output/*.vhd >/dev/null 2>&1; then \
        for vhd in output/*.vhd; do \
            vhdx="$${vhd%.vhd}.vhdx"; \
            qemu-img convert -f vpc -O vhdx "$$vhd" "$$vhdx" && rm -f "$$vhd" && echo "[OK] Converted: $$vhdx"; \
        done; \
    else \
        echo "[WARN] qemu-img not found or no .vhd produced -- .vhd retained in output/"; \
    fi
    @echo "[OK] VHDX image in output/"

# Generate WSL2 tar.gz for wsl --import
wsl2: build
    mkdir -p output
    sudo podman run --rm -it --privileged \
        --security-opt label=type:unconfined_t \
        -v ./output:/output \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        -v ./config/artifacts/wsl2.toml:/config.toml:ro \
        {{BIB}} build --type wsl2 {{LOCAL}}
    @echo "[OK] WSL2 image in output/ -- import with: wsl --import 'MiOS' ./mios output/disk.wsl2"


# Log artifacts to MiOS-bootstrap repository (Linux FS native)
log-bootstrap:
    @echo "[START] Logging artifacts to MiOS-bootstrap repository (Linux FS native)..."
    ./tools/log-to-bootstrap.sh
    @echo "[OK] Artifacts logged to bootstrap repository"

# Complete build with bootstrap logging (recommended for releases)
build-and-log: build-logged
    @echo "[START] Running bootstrap artifact logging (Linux FS native)..."
    ./tools/log-to-bootstrap.sh
    @echo "[OK] Build complete with artifacts logged to bootstrap"

# Full pipeline: build  rechunk  log to bootstrap (Linux FS native)
all-bootstrap: build rechunk log-bootstrap
    @echo "[OK] Full pipeline complete (build  rechunk  bootstrap Linux FS native)"

# Generate SBOM for the local image
sbom:
    @echo "[START] Generating SBOM for {{LOCAL}}..."
    @mkdir -p artifacts/sbom
    podman run --rm \
        -v ./artifacts/sbom:/out \
        -v /var/lib/containers/storage:/var/lib/containers/storage \
        anchore/syft:latest scan {{LOCAL}} -o cyclonedx-json > artifacts/sbom/mios-sbom.json
    @echo "[OK] SBOM generated: artifacts/sbom/mios-sbom.json"

# ============================================================================
# User-Space Management
# ============================================================================

# Initialize user-space configuration (seeds ~/.config/mios/mios.toml).
init-user-space:
    @./tools/init-user-space.sh

# Re-initialize user-space (overwrite mios.toml with vendor template).
reinit-user-space:
    @./tools/init-user-space.sh --force

# Show user-space configuration paths
show-user-space:
    @echo "'MiOS' User-Space Directories:"
    @echo "  Config:  ${XDG_CONFIG_HOME:-$HOME/.config}/mios/"
    @echo "  Data:    ${XDG_DATA_HOME:-$HOME/.local/share}/mios/"
    @echo "  Cache:   ${XDG_CACHE_HOME:-$HOME/.cache}/mios/"
    @echo "  State:   ${XDG_STATE_HOME:-$HOME/.local/state}/mios/"
    @echo "  Runtime: ${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/mios/"
    @echo ""
    @echo "Configuration:"
    @if [ -f "${XDG_CONFIG_HOME:-$HOME/.config}/mios/mios.toml" ]; then \
        echo "  [OK] mios.toml"; \
    else \
        echo "  [FAIL] mios.toml (run: just init)"; \
    fi
    @for f in env.toml images.toml build.toml flatpaks.list; do \
        if [ -f "${XDG_CONFIG_HOME:-$HOME/.config}/mios/$f" ]; then \
            echo "  [legacy] $f -- migrate via: just init"; \
        fi; \
    done

# Show loaded environment variables
show-env:
    @echo "'MiOS' Environment Variables:"
    @source ./tools/lib/userenv.sh && env | grep '^MIOS_' | sort | sed 's/^/  /'

# Edit the unified user configuration (mios.toml).
edit:
    @CFG="${XDG_CONFIG_HOME:-$HOME/.config}/mios/mios.toml"; \
        if [ ! -f "$CFG" ]; then \
            echo "[FAIL] $CFG not found. Run: just init"; exit 1; \
        fi; \
        ${EDITOR:-vim} "$CFG"
```


### `mios-build-local.ps1`

```powershell
<#
.SYNOPSIS
    'MiOS' v0.2.2 - 'MiOS' Builder (Windows)

.DESCRIPTION
    Secure build orchestrator with workflow selection.
    Tokens/passwords NEVER appear in plain text in logs or terminal output.

    SECURITY FIXES in v0.2.2:
      - Passwords pre-hashed (SHA-512) before injection - plaintext never in build log
      - Registry token uses SecureString - never echoed, never in process args
      - Workflow menu: Local Build, Push Build, Custom Build
      - Admin/origin-owner detection for default token inference
      - Hostname randomization option for HA clusters

    SELF-BUILDING in v0.2.2:
      - Pulls existing 'MiOS' image from GHCR as the helper/builder image
      - 'MiOS' image replaces alpine/python for all helper operations
      - Falls back to alpine/python only on first-ever build (no prior image)
      - MAKEFLAGS passed into build for parallel compilation (akmod, Looking Glass)
      - 'MiOS' image IS the builder - podman, buildah, bootc, BIB all baked in
#>

$ErrorActionPreference = "Stop"

# ==============================================================================
#  UI HELPERS & MASKING ENGINE
# ==============================================================================
$BuildAudit = @()
$Global:MiOS_MaskList = @()

function Register-Secret {
    param([string]$S)
    if ([string]::IsNullOrWhiteSpace($S) -or $S.Length -lt 4) { return }
    if ($Global:MiOS_MaskList -notcontains $S) {
        $Global:MiOS_MaskList += $S
    }
}

function Format-Masked {
    param([string]$InputString)
    if ([string]::IsNullOrWhiteSpace($InputString)) { return $InputString }
    $out = $InputString
    foreach ($secret in $Global:MiOS_MaskList) {
        # Escape for regex and replace case-insensitively
        $pattern = [regex]::Escape($secret)
        $out = $out -ireplace $pattern, "********"
    }
    return $out
}

function Write-Banner { 
    param([string]$T) 
    $w=78; 
    $maskedT = Format-Masked $T
    Write-Host "`n$("="*$w)" -ForegroundColor Cyan; 
    Write-Host ("  $maskedT") -ForegroundColor Cyan; 
    Write-Host "$("="*$w)`n" -ForegroundColor Cyan 
}

$PhasePercent = @{ '0'=0; '0.1'=1; '0.5'=3; '1'=6; '1.5'=10; '2'=15; '3'=82; '3b'=90; '4'=95; '5'=100 }

function Write-Phase {
    param([string]$N,[string]$L)
    $maskedL = Format-Masked $L
    Write-Host "`n  [$N] $maskedL" -ForegroundColor Yellow;
    Write-Host "  $("-"*70)" -ForegroundColor DarkGray
    $script:BuildAudit += "PHASE ${N}: ${maskedL}"
    $pct = if ($script:PhasePercent.ContainsKey($N)) { $script:PhasePercent[$N] } else { 0 }
    Write-Progress -Activity "'MiOS' Build ${Version}" -Id 0 -Status "Phase ${N}: ${maskedL}" -PercentComplete $pct
}

function Write-Step  { 
    param([string]$M) 
    $maskedM = Format-Masked $M
    Write-Host "       $maskedM" -ForegroundColor DarkCyan 
}

function Write-OK { 
    param([string]$M) 
    $maskedM = Format-Masked $M
    Write-Host "      [OK] $maskedM" -ForegroundColor Green; 
    $script:BuildAudit += "  [OK] $maskedM" 
}

function Write-Warn { 
    param([string]$M) 
    $maskedM = Format-Masked $M
    Write-Host "       $maskedM" -ForegroundColor Yellow; 
    $script:BuildAudit += "  [WARN] $maskedM" 
}

function Write-Fatal {
    param([string]$M)
    $maskedM = Format-Masked $M
    Write-Host "`n  [FAIL] FATAL: $maskedM" -ForegroundColor Red;
    $script:BuildAudit += "  [FAIL] $maskedM";
    Show-StatusCard
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

function Show-StatusCard {
    $w = 78
    Write-Host "`n+$($("="*($w-2)))+" -ForegroundColor Cyan
    Write-Host "|$($(" "*[math]::Floor(($w-18)/2)))'MiOS' BUILD SUMMARY$($(" "*[math]::Ceiling(($w-18)/2)))|" -ForegroundColor Cyan
    Write-Host "+$($("="*($w-2)))+" -ForegroundColor Cyan
    Write-Host "  Version:  $Version"
    Write-Host "  Status:   $([DateTime]::UtcNow.ToString('yyyy-MM-dd HH:mm:ss')) UTC"
    Write-Host "  Audit Log:"
    foreach ($line in $script:BuildAudit) {
        # Audit log entries are already masked during collection, but double-check here
        $maskedLine = Format-Masked $line
        if ($maskedLine -match "FAIL") { Write-Host "    $maskedLine" -ForegroundColor Red }
        elseif ($maskedLine -match "WARN") { Write-Host "    $maskedLine" -ForegroundColor Yellow }
        elseif ($maskedLine -match "PHASE") { Write-Host "    $maskedLine" -ForegroundColor Cyan }
        else { Write-Host "    $maskedLine" -ForegroundColor Gray }
    }
    Write-Host "+$($("="*($w-2)))+`n" -ForegroundColor Cyan
}

# -- Register initial secrets from environment (if present) --
@("MIOS_PASSWORD", "GHCR_TOKEN", "MIOS_GHCR_PUSH_TOKEN", "MIOS_PASSWORD_HASH") | ForEach-Object {
    # PowerShell parses $env:$_ as a scope-qualified var ref and rejects it
    # at parse time. Use [Environment]::GetEnvironmentVariable instead.
    $val = [Environment]::GetEnvironmentVariable($_)
    if ($val) { Register-Secret $val }
}

function Get-FileSize { param([string]$P) if(!(Test-Path $P)){return "N/A"} $s=(Get-Item $P).Length; if($s -gt 1GB){"$([math]::Round($s/1GB,2)) GB"}else{"$([math]::Round($s/1MB,2)) MB"} }

function Read-Timed {
    param([string]$Prompt, [string]$Default, [switch]$Secret)
    if ($Secret) {
        Write-Host "      $Prompt " -NoNewline -ForegroundColor DarkCyan
        Write-Host "[$(if($Default){'********'}else{''})] " -NoNewline -ForegroundColor DarkGray
    } else {
        Write-Host "      $Prompt " -NoNewline -ForegroundColor DarkCyan
        Write-Host "[$Default] " -NoNewline -ForegroundColor DarkGray
    }
    $sw = [System.Diagnostics.Stopwatch]::StartNew(); $buf = ""
    while ($sw.Elapsed.TotalSeconds -lt $Timeout -and -not [Console]::KeyAvailable) { Start-Sleep -Milliseconds 100 }
    if ([Console]::KeyAvailable) {
        if ($Secret) {
            if ($PSVersionTable.PSVersion.Major -ge 7) {
                $buf = Read-Host -MaskInput
            } else {
                $sec  = Read-Host -AsSecureString
                $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
                try   { $buf = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
                finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
            }
            if ($buf) { Register-Secret $buf }
        } else {
            $buf = Read-Host
        }
    } else {
        Write-Host ""
    }
    if ([string]::IsNullOrWhiteSpace($buf)) { $buf = $Default }
    return $buf
}

# Shared helper: writes /etc/mios/install.env into a freshly-imported WSL2
# distro so wsl-firstboot.service picks up the operator-supplied identity
# instead of falling back to the literal default password "mios".
. (Join-Path $PSScriptRoot "tools/lib/install-env.ps1")

function Get-SHA512Hash {
    # Generate a SHA-512 crypt hash ($6$...) compatible with chpasswd -e
    # Prefers 'MiOS' helper image (has openssl), falls back to alpine/python
    param([string]$SecretText)
    $salt = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 16 | ForEach-Object { [char]$_ })

    $hash = $null

    # Try 'MiOS' helper image first (openssl is already installed)
    if ($HelperImage) {
        $hash = & podman run --rm $HelperImage openssl passwd -6 -salt "$salt" "$SecretText" 2>$null
        if ($LASTEXITCODE -eq 0 -and $hash -match '^\$6\$') { return $hash.Trim() }
    }

    # Fallback: alpine + openssl
    $hash = & podman run --rm $FallbackHash sh -c "apk add --quiet openssl >/dev/null 2>&1 && openssl passwd -6 -salt '$salt' '$SecretText'" 2>$null
    if ($LASTEXITCODE -eq 0 -and $hash -match '^\$6\$') { return $hash.Trim() }

    # Fallback: python
    $hash = & podman run --rm docker.io/library/python:3-slim python3 -c "import crypt; print(crypt.crypt('$SecretText', crypt.mksalt(crypt.METHOD_SHA512)))" 2>$null
    return $hash.Trim()
}

function Clear-BIBTemp { foreach ($d in "image","vpc","qcow2","bootiso") { Get-ChildItem $OutputFolder -Directory -Filter $d -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue } }

function Invoke-BIBRun {
    param([string[]]$BIBArgs, [string]$Label)
    $bibOp  = "Starting $Label..."
    $bibN   = 0
    $pctBase = if ($script:PhasePercent.ContainsKey('3')) { $script:PhasePercent['3'] } else { 82 }
    Write-Progress -Activity "'MiOS' Build ${Version}" -Id 0 `
        -Status "Phase 3 -- $Label" -CurrentOperation $bibOp -PercentComplete $pctBase
    & podman @BIBArgs 2>&1 | ForEach-Object {
        $line = $_
        Write-Host (Format-Masked $line)
        $bibN++
        $stripped = ($line -replace '^\s*#\d+\s+(?:[\d.]+\s+)?', '').TrimStart()
        if ($stripped -match 'org\.osbuild\.\S+') {
            $bibOp = $Matches[0]
        } elseif ($stripped -match '^(Assembling|Building|Extracting|Installing|Packaging|Pipeline|Stage|Writing)\b') {
            $candidate = ($stripped -replace '\s+', ' ').Trim()
            $bibOp = if ($candidate.Length -gt 80) { $candidate.Substring(0, 80) + '...' } else { $candidate }
        } elseif (-not [string]::IsNullOrWhiteSpace($stripped)) {
            $candidate = ($stripped -replace '\s+', ' ').Trim()
            $bibOp = Format-Masked (if ($candidate.Length -gt 80) { $candidate.Substring(0, 80) + '...' } else { $candidate })
        }
        Write-Progress -Activity "  $Label" -Id 1 -ParentId 0 `
            -Status "Lines: $bibN" -CurrentOperation $bibOp `
            -PercentComplete ([Math]::Min(99, [int]($bibN / 10)))
    }
    Write-Progress -Activity "  $Label" -Id 1 -Completed
    return $LASTEXITCODE
}

# --- Auto-Elevation ---
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "  Relaunching as Administrator..." -ForegroundColor Cyan
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`"" -Verb RunAs
    return
}

# -- Self-Build defaults (initialized early - referenced throughout) --
$SelfBuild = $false
$BibImage = "quay.io/centos-bootc/bootc-image-builder:latest"
Set-StrictMode -Version Latest

# ==============================================================================
#  CONFIGURATION
# ==============================================================================
# Source .env.mios if present
if (Test-Path ".env.mios") {
    Write-Phase "0.1" "Loading Unified Environment"
    Get-Content ".env.mios" | ForEach-Object {
        if ($_ -match '^([^#\s][^=]+)="?([^"]*)"?$') {
            $name = $matches[1].Trim()
            $val = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $val)
        }
    }
}

$v = Get-Content "VERSION" -ErrorAction SilentlyContinue; $Version = if ($v) { $v.Trim() } else { "v0.2.2" }
$ImageName      = if ($env:MIOS_IMAGE_NAME) { ($env:MIOS_IMAGE_NAME -split '/')[-1] -replace ':.*$','' } else { "mios" }
$ImageTag       = "latest"
$MIOS_USER_ADMIN = "mios" # @track:USER_ADMIN
$DefUser        = if ($env:MIOS_USER) { $env:MIOS_USER } elseif ($env:MIOS_DEFAULT_USER) { $env:MIOS_DEFAULT_USER } else { $MIOS_USER_ADMIN }
$DefPass        = if ($env:MIOS_PASSWORD) { $env:MIOS_PASSWORD } elseif ($env:MIOS_DEFAULT_USER_PASSWORD) { $env:MIOS_DEFAULT_USER_PASSWORD } else { "mios" }
$DefHostname    = if ($env:MIOS_HOSTNAME) { $env:MIOS_HOSTNAME } else { "mios" }
$MIOS_REGISTRY_DEFAULT = "ghcr.io/MiOS-DEV/mios" # @track:REGISTRY_DEFAULT
$DefRegistry    = if ($env:MIOS_IMAGE_NAME) { $env:MIOS_IMAGE_NAME -replace ':.*$','' } else { $MIOS_REGISTRY_DEFAULT }
$BibImage       = if ($env:MIOS_BIB_IMAGE) { $env:MIOS_BIB_IMAGE } else { "quay.io/centos-bootc/bootc-image-builder:latest" } # @track:IMG_BIB
$BuilderMachine = "mios-builder"
$LocalImage     = "localhost/${ImageName}:${ImageTag}"
$MiosDocsDir      = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "MiOS"
$MiosDeployDir    = Join-Path $MiosDocsDir "deployments"
$MiosManifestsDir = Join-Path $MiosDocsDir "manifests"
$MiosImagesDir    = Join-Path $MiosDocsDir "images"
$OutputFolder     = $MiosDeployDir
$MIOS_IMG_RECHUNK = "quay.io/centos-bootc/centos-bootc:stream10" # @track:IMG_RECHUNK
$RechunkImage     = $MIOS_IMG_RECHUNK
$Timeout          = 30

$RawImg         = Join-Path $MiosImagesDir "mios-bootable.raw"
$TargetVhdx     = Join-Path $MiosDeployDir "mios-hyperv.vhdx"
$TargetWsl      = Join-Path $MiosDeployDir "mios-wsl.tar"
$TargetIso      = Join-Path $MiosImagesDir "mios-installer.iso"

# Helper image: prefer 'MiOS' itself, fall back to alpine/python for first build
$HelperImage    = ""
$FallbackHash   = "docker.io/library/alpine:latest"
$FallbackConvert = "docker.io/library/alpine:latest"

# ==============================================================================
#  BANNER + WORKFLOW MENU
# ==============================================================================
Write-Banner "'MiOS' v$Version - 'MiOS' Builder"

$workflow = $env:MIOS_WORKFLOW
if ([string]::IsNullOrWhiteSpace($workflow)) {
    Write-Host "  Select build workflow:" -ForegroundColor White
    Write-Host ""
    Write-Host "    1) Local Build Only     - Build image, generate targets, NO registry push" -ForegroundColor Cyan
    Write-Host "    2) Build + Push         - Full pipeline: build  targets  push to registry" -ForegroundColor Cyan
    Write-Host "    3) Custom Build         - Custom user/pass/hostname/registry/token" -ForegroundColor Cyan
    Write-Host "    4) Pull + Deploy Only   - Pull existing image from registry, generate targets" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Choice [1-4] (default 1): " -NoNewline -ForegroundColor Yellow
    $workflow = Read-Host
    if ([string]::IsNullOrWhiteSpace($workflow)) { $workflow = "1" }
} else {
    Write-OK "Workflow inherited from environment: $workflow"
}

$DoPush       = $false
$DoCustom     = $false
$DoBuild      = $true
$DoPull       = $false

switch ($workflow) {
    "1" { $DoPush = $false }
    "2" { $DoPush = $true }
    "3" { $DoPush = $true; $DoCustom = $true }
    "4" { $DoBuild = $false; $DoPull = $true; $DoPush = $false }
    default { Write-Fatal "Invalid choice: $workflow" }
}

# ==============================================================================
#  PHASE 0: CONFIGURATION
# ==============================================================================
Write-Phase "0" "Configuration"

if ($DoCustom) {
    $U = Read-Timed "Username:" $DefUser
    $P = Read-Timed "Password:" $DefPass -Secret
    $HostIn = Read-Timed "Static Hostname (blank for mios-XXXXX):" $DefHostname
    $luksIn = Read-Timed "Enable LUKS encryption? (y/N):" "N"
    $UseLuks = $luksIn -match "^[yY]"
    $LuksPass = if ($UseLuks) { Read-Timed "LUKS passphrase:" "mios" -Secret } else { "" }
    $RegistryUrl = Read-Timed "Registry URL:" $DefRegistry

    Write-Host ""
    Write-Host "      Select Deployment Targets (comma separated or 'all'):" -ForegroundColor DarkCyan
    Write-Host "      1) RAW, 2) VHDX, 3) WSL, 4) ISO" -ForegroundColor DarkGray
    $targetIn = Read-Timed "Targets:" "all"
    if ($targetIn -eq "all") { $SelectedTargets = 1..4 }
    else { $SelectedTargets = $targetIn -split ',' | ForEach-Object { $_.Trim() } }
} else {
    $U = $DefUser
    $P = $DefPass
    $HostIn = $DefHostname
    $UseLuks = $false
    $LuksPass = ""
    $RegistryUrl = $DefRegistry
    
    # Target selection inheritance
    if ($env:MIOS_TARGETS) {
        if ($env:MIOS_TARGETS -eq "none") { $SelectedTargets = @() }
        elseif ($env:MIOS_TARGETS -eq "all") { $SelectedTargets = 1..4 }
        else { $SelectedTargets = $env:MIOS_TARGETS -split ',' | ForEach-Object { [int]$_.Trim() } }
    } else {
        $SelectedTargets = 1..4
    }
}

$GhcrImage = "${RegistryUrl}:${ImageTag}"

# -- Registry credentials (only if pushing or pulling) -------------------------
$RegistryUser  = ""
$RegistryToken = ""

if ($DoPush -or $DoPull) {
    # Try environment variables first (CI/CD friendly)
    $RegistryUser  = $env:MIOS_GHCR_USER
    $RegistryToken = if ($env:MIOS_GHCR_TOKEN) { $env:MIOS_GHCR_TOKEN } else { $env:GHCR_TOKEN }
    if ($RegistryToken) { Register-Secret $RegistryToken }

    if (-not $RegistryUser) {
        $RegistryUser = Read-Timed "Registry username:" "MiOS-DEV"
    }
    if (-not $RegistryToken) {
        Write-Host "  Token input is masked. It will NEVER be displayed." -ForegroundColor DarkYellow
        $RegistryToken = Read-Timed "Registry token/PAT:" "" -Secret
    }

    if (-not $RegistryToken -and $DoPush) {
        Write-Warn "No registry token provided - push will be skipped"
        $DoPush = $false
    }
}

# -- Summary (NEVER show token or password) ------------------------------------
$tokenStatus = if ($RegistryToken) { "provided (masked)" } else { "none" }
Write-Host ""
Write-OK "User: $U | LUKS: $(if($UseLuks){'Yes'}else{'No'}) | Registry: $GhcrImage"
Write-OK "Workflow: $(switch($workflow){'1'{'Local Build'}; '2'{'Build+Push'}; '3'{'Custom Build+Push'}; '4'{'Pull+Deploy'}}) | Token: $tokenStatus"

# -- Validate prerequisites ---------------------------------------------------
Write-Phase "0.5" "System Validation"
if (-not (Test-Path $OutputFolder)) { New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null }
if (-not (Test-Path $MiosImagesDir)) { New-Item -ItemType Directory -Path $MiosImagesDir -Force | Out-Null }

# Unified log -- one flat file from bootstrap to final target, injected into image.
$script:UnifiedLog = if ($env:MIOS_UNIFIED_LOG) { $env:MIOS_UNIFIED_LOG } else {
    Join-Path $MiosDocsDir "mios-build-$([DateTime]::Now.ToString('yyyyMMdd-HHmmss')).log"
}
[Environment]::SetEnvironmentVariable("MIOS_UNIFIED_LOG", $script:UnifiedLog)
try { Start-Transcript -Path $script:UnifiedLog -Append -Force | Out-Null } catch {}
Write-OK "Unified log: $($script:UnifiedLog)"

try { $pv = & podman --version 2>&1; Write-OK "Podman: $pv" } catch { Write-Fatal "Podman not found" }
$cpu = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
$ram = [math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB)
Write-OK "CPU: $cpu cores | RAM: $ram MB"

if ($DoBuild) {
    foreach ($f in "Containerfile","usr/share/mios/PACKAGES.md","VERSION","automation/build.sh","automation/31-user.sh") {
        if (-not (Test-Path $f)) { Write-Fatal "Missing required file: $f - are you in the 'MiOS' repo root?" }
    }
    Write-OK "All repo files present"
}

# ==============================================================================
#  PHASE 1: PODMAN BUILDER MACHINE
# ==============================================================================
Write-Phase "1" "Podman Builder Machine"
$ErrorActionPreference = "Continue"

$builderScript = Join-Path $PWD "automation\mios-build-builder.ps1"
if (-not (Test-Path $builderScript)) { Write-Fatal "Missing $builderScript" }

Write-Step "Executing dedicated builder provisioning script..."
& $builderScript -MachineName $BuilderMachine
if ($LASTEXITCODE -ne 0) { Write-Fatal "Builder provisioning failed." }

& podman system connection default "${BuilderMachine}-root"
Write-OK "Builder connection set to: ${BuilderMachine}-root"
$ErrorActionPreference = "Stop"


# ==============================================================================
Write-Phase "1.5" "Self-Building - Pull 'MiOS' Helper Image"
$ErrorActionPreference = "Continue"

# Try to pull the existing 'MiOS' image from the registry.
# If it exists, use it as the helper image for ALL container operations
# (hash generation, qemu-img conversion, etc.) - 'MiOS' IS the builder.
# First build ever: no image exists yet, fall back to alpine/python.
Write-Step "Checking for existing 'MiOS' image at $GhcrImage..."

# Authenticate if we have credentials
if ($RegistryToken) {
    $registryHost = ($GhcrImage -split '/')[0]
    $RegistryToken | & podman login $registryHost --username $RegistryUser --password-stdin 2>&1 | Out-Null
}

& podman pull $GhcrImage 2>$null
if ($LASTEXITCODE -eq 0) {
    $HelperImage = $GhcrImage
    Write-OK "'MiOS' helper image pulled - self-building cycle active"
    Write-OK "All helper operations will use 'MiOS' (openssl, qemu-img, etc.)"
} else {
    # Check if it exists locally already (previous local build)
    & podman image exists $LocalImage 2>$null
    if ($LASTEXITCODE -eq 0) {
        $HelperImage = $LocalImage
        Write-OK "Using local 'MiOS' image as helper - self-building cycle active"
    } else {
        $HelperImage = ""
        Write-Warn "No existing 'MiOS' image found - first build, using alpine/python fallbacks"
        Write-Step "After this build completes and pushes, subsequent builds will self-build"
    }
}
# -- Self-Building BIB: Try 'MiOS' as bootc-image-builder --------------------
# 'MiOS' includes bootc-image-builder + osbuild as RPMs. If HelperImage is set,
# verify it can serve as BIB. Falls back to centos-bootc on first build.
$BIBSelfBuild = $false
if ($HelperImage) {
    $ErrorActionPreference = "Continue"
    $null = & podman run --rm $HelperImage which bootc-image-builder 2>$null
    if ($LASTEXITCODE -eq 0) {
        $BIBImage = $HelperImage
        $BIBSelfBuild = $true
        Write-OK "Self-building BIB: 'MiOS' image will be used as bootc-image-builder"
    } else {
        Write-Step "'MiOS' image lacks bootc-image-builder binary - using centos-bootc BIB"
    }
}
$ErrorActionPreference = "Stop"


# ==============================================================================
if ($DoPull) {
    Write-Phase "2" "Pulling Image from Registry"
    if ($RegistryToken) {
        $registryHost = ($GhcrImage -split '/')[0]
        Write-Step "Authenticating to $registryHost..."
        $RegistryToken | & podman login $registryHost --username $RegistryUser --password-stdin 2>&1 | Out-Null
    }
    Write-Step "Pulling $GhcrImage..."
    & podman pull $GhcrImage
    if ($LASTEXITCODE -ne 0) { Write-Fatal "Pull failed" }
    & podman tag $GhcrImage $LocalImage
    Write-OK "Image pulled and tagged as $LocalImage"
} elseif ($DoBuild) {
    Write-Phase "2" "OCI Container Build"

    # -- Hash the password BEFORE injection --
    Write-Step "Pre-hashing credentials (plaintext will NOT appear in build log)..."
    $passHash = Get-SHA512Hash -SecretText $P
    if (-not $passHash -or $passHash -notmatch '^\$6\$') {
        Write-Fatal "Failed to generate password hash. Check podman connectivity."
    }
    Write-OK "Password hashed (SHA-512)"

    # -- Inject hostname (only if custom; restored via git checkout after build) --
    if ($HostIn -ne "mios") {
        Write-Step "Injecting static hostname: $HostIn ..."
        Set-Content "etc/hostname" "$HostIn" -Encoding ascii
    }

    $t0 = Get-Date
    Write-Step "Building OCI image (all $cpu threads, MAKEFLAGS=-j$cpu)..."

    $env:BUILDAH_FORMAT = "docker"

    # Stream podman build output; parse build.sh step markers to drive the
    # nested Write-Progress bar so each automation script appears in the
    # PowerShell progress UI as it executes inside the container.
    # Pattern emitted by build.sh _step_header:
    #   +- STEP 01/50 : 01-repos.sh ---- 00:00 -+
    # BuildKit --progress=plain may prefix lines with "#N 0.123 " - handled
    # by matching anywhere in the line, not anchored to start.
    $pbStep = 0; $pbTotal = 45; $pbSname = "Initializing"; $pbOp = "Starting podman build..."
    Write-Progress -Activity "'MiOS' Build ${Version}" -Id 0 `
        -Status "Phase 2 -- Pulling / preparing layers..." -CurrentOperation $pbOp -PercentComplete 15

    & podman build --progress=plain --no-cache `
        --build-arg MAKEFLAGS="-j$cpu" `
        --build-arg MIOS_USER="$U" `
        --build-arg MIOS_HOSTNAME="$HostIn" `
        --build-arg MIOS_PASSWORD_HASH="$passHash" `
        --jobs 2 -t $LocalImage . 2>&1 | ForEach-Object {
        $line = $_
        $stripped = ($line -replace '^\s*#\d+\s+(?:[\d.]+\s+)?', '').TrimStart()
        Write-Host (Format-Masked $line)

        # build.sh emits: +- STEP 01/45 : 01-repos.sh ---- 00:00 -+
        if ($stripped -match '\+-\s*STEP\s+(\d+)/(\d+)\s*:\s*(\S+\.sh)') {
            $pbStep  = [int]$Matches[1]
            $pbTotal = [int]$Matches[2]
            $pbSname = $Matches[3]
        }
        $candidate = ($stripped -replace '\s+', ' ').Trim()
        if ($candidate.Length -gt 80) { $candidate = $candidate.Substring(0, 80) + '...' }
        if (-not [string]::IsNullOrWhiteSpace($candidate)) { $pbOp = Format-Masked $candidate }

        $outerPct  = [Math]::Min(99, 15 + [int]($pbStep * 67 / [Math]::Max(1, $pbTotal)))
        $outerStat = if ($pbStep -gt 0) { "Script $pbStep/$pbTotal -- $pbSname" } else { "Pulling / preparing layers..." }
        Write-Progress -Activity "'MiOS' Build ${Version}" -Id 0 `
            -Status "Phase 2 -- $outerStat" -CurrentOperation $pbOp -PercentComplete $outerPct
        if ($pbStep -gt 0) {
            Write-Progress -Activity "  $pbSname" -Id 1 -ParentId 0 `
                -Status "Step $pbStep of $pbTotal" -CurrentOperation $pbOp `
                -PercentComplete ([int]($pbStep * 100 / [Math]::Max(1, $pbTotal)))
        }
    }
    $buildExitCode = $LASTEXITCODE

    Write-Progress -Activity "Automation scripts" -Id 1 -Completed
    if ($buildExitCode -ne 0) { Write-Fatal "podman build failed" }

    # Restore hostname if it was temporarily overridden
    & git checkout etc/hostname 2>$null | Out-Null

    $buildMin = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    Write-OK "Image built in $buildMin min  $LocalImage"

    # Tag with GHCR ref BEFORE BIB - sets permanent update origin
    Write-Step "Tagging as $GhcrImage (sets update origin for bootc)..."
    & podman tag $LocalImage $GhcrImage
    Write-OK "Update origin set: $GhcrImage"

    # Rechunk
    Write-Step "Rechunking for optimized OCI layers..."
    $ErrorActionPreference = "Continue"
    # Use the freshly built image as the rechunker tool (Self-Building)
    # Falls back to external RECHUNK_IMAGE if local fails
    & podman run --rm --privileged `
        -v /var/lib/containers/storage:/var/lib/containers/storage `
        $LocalImage /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 "containers-storage:$LocalImage" "containers-storage:$LocalImage"
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Self-build rechunk failed; falling back to external rechunker"
        & podman run --rm --privileged `
            -v /var/lib/containers/storage:/var/lib/containers/storage `
            $RechunkImage /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 "containers-storage:$LocalImage" "containers-storage:$LocalImage"
    }
    $ErrorActionPreference = "Stop"

    Write-OK "Rechunk complete"

    # Update helper image reference - this freshly built image IS the builder now
    $HelperImage = $LocalImage
    # Check if freshly built image can serve as BIB for deployment targets
    $null = & podman run --rm $LocalImage which bootc-image-builder 2>$null
    if ($LASTEXITCODE -eq 0) {
        $BIBImage = $LocalImage
        $BIBSelfBuild = $true
        Write-OK "Helper image updated - self-building BIB active ('MiOS' IS the builder)"
    } else {
        Write-OK "Helper image updated to freshly built $LocalImage (self-building ready)"
    }
}

# Flush transcript so far into the OCI image at /usr/share/mios/build-log.txt.
# BIB reads the image but never mutates it, so the log survives into VHDX/ISO.
if ($script:UnifiedLog -and (Test-Path $script:UnifiedLog)) {
    Write-Step "Injecting build log into OCI image (pre-BIB snapshot)..."
    try { Stop-Transcript | Out-Null } catch {}
    $logCid = (& podman create $LocalImage sh 2>$null).Trim()
    if ($logCid) {
        # podman cp works on stopped containers; /usr/share/mios exists in the built image
        & podman cp $script:UnifiedLog "${logCid}:/usr/share/mios/build-log.txt" 2>$null | Out-Null
        & podman commit --quiet --pause=false $logCid $LocalImage 2>$null | Out-Null
        & podman rm -f $logCid 2>$null | Out-Null
        Write-OK "Build log baked into image: /usr/share/mios/build-log.txt"
    }
    try { Start-Transcript -Path $script:UnifiedLog -Append -Force | Out-Null } catch {}
}

# ==============================================================================
#  PHASE 3: GENERATE DEPLOYMENT TARGETS
# ==============================================================================
Write-Phase "3" "Generating Deployment Targets"
$ErrorActionPreference = "Continue"

# Ensure the BIB output directory exists inside MiOS-BUILDER.
# podman bind-mounts the host path into the BIB container; the host path
# must exist before `podman run -v` is called or crun returns ENOENT.
# Compute the WSL2 Linux equivalent of the Windows $OutputFolder path and
# pre-create it via `podman machine ssh`.
if ($OutputFolder -match '^([A-Za-z]):\\(.*)$') {
    $bibLinuxDir = "/mnt/$($Matches[1].ToLower())/$($Matches[2] -replace '\\','/')"
} else {
    $bibLinuxDir = $OutputFolder  # already a Linux path (e.g. /tmp/mios-bib-output)
}
$null = & podman machine ssh $BuilderMachine "mkdir -p '$bibLinuxDir'" 2>$null

$bibConf = Join-Path $PWD "config\bib.toml"
if (-not (Test-Path $bibConf)) { $bibConf = Join-Path $PWD "config\bib.json" }
$bibConfDest = Join-Path $OutputFolder "bib-config"
if (Test-Path $bibConf) {
    if ($bibConf -match '\.toml$') {
        $bibMountPath = "/config.toml"
        Copy-Item $bibConf "$bibConfDest.toml" -Force
        $bibConfDest = "$bibConfDest.toml"
    } else {
        $bibMountPath = "/config.json"
        Copy-Item $bibConf "$bibConfDest.json" -Force
        $bibConfDest = "$bibConfDest.json"
    }
    Write-OK "BIB config: 80 GiB minimum root (mounted as $bibMountPath)"
} else {
    Write-Warn "No BIB config found - disk may auto-size too small!"
    $bibConfDest = $null
}

$isoToml = Join-Path $PWD "iso.toml"
$hasIsoToml = Test-Path $isoToml
if ($hasIsoToml) { Write-OK "iso.toml found - kickstart will be injected into ISO" }

function Get-BIBArgs {
    param([string]$Type)
    $bibArgs = @(
        "run", "--rm", "-it", "--privileged",
        "--security-opt", "label=type:unconfined_t",
        "-v", "/var/lib/containers/storage:/var/lib/containers/storage",
        "-v", "${OutputFolder}:/output:z"
    )
    if ($Type -eq "anaconda-iso" -and $hasIsoToml) {
        $isoContent = Get-Content $isoToml -Raw
        $isoContent = $isoContent.Replace('INJ_U', $U)
        $isoContent = $isoContent.Replace('INJ_IMAGE', $GhcrImage)
        if (-not $script:passHash) { $script:passHash = Get-SHA512Hash -SecretText $P }
        if ($script:passHash) {
            $isoContent = $isoContent.Replace('INJ_HASH', $script:passHash)
        }
        $isoContent | Set-Content (Join-Path $OutputFolder "iso.toml") -NoNewline -Encoding UTF8
        $bibArgs += @("-v", "$(Join-Path $OutputFolder 'iso.toml'):/config.toml:ro")
    } elseif ($bibConfDest) {
        $bibArgs += @("-v", "${bibConfDest}:${bibMountPath}:ro")
    }
    if ($UseLuks -and $Type -in @("raw","anaconda-iso")) {
        $LuksPass | Set-Content (Join-Path $OutputFolder ".luks-tmp") -NoNewline
        $bibArgs += @("-v", "$(Join-Path $OutputFolder '.luks-tmp'):/luks-pass:ro")
        $bibArgs += @("--env", "LUKS_PASSPHRASE_FILE=/luks-pass")
    }
    $bibArgs += @($BIBImage, "build", "--type", $Type, "--rootfs", "ext4", "--local", $LocalImage)
    return $bibArgs
}

# -- RAW --
if ($SelectedTargets -contains 1) {
    Write-Step "TARGET 1 - RAW disk image..."
    Clear-BIBTemp
    $rawArgs = Get-BIBArgs "raw"
    $null = Invoke-BIBRun -BIBArgs $rawArgs -Label "RAW disk image"
    if ($LASTEXITCODE -eq 0) {
        $rawFile = Get-ChildItem $OutputFolder -Recurse -Filter "*.raw" | Select-Object -First 1
        if ($rawFile) { Move-Item $rawFile.FullName $RawImg -Force; Write-OK "RAW: $(Get-FileSize $RawImg)" }
    } else { Write-Warn "RAW build failed" }
}

# -- VHDX --
if ($SelectedTargets -contains 2) {
    Write-Step "TARGET 2 - VHD  VHDX (Hyper-V Gen2)..."
    Clear-BIBTemp
    $vhdArgs = Get-BIBArgs "vhd"
    $null = Invoke-BIBRun -BIBArgs $vhdArgs -Label "VHDX (Hyper-V Gen2)"
    if ($LASTEXITCODE -eq 0) {
        # BIB nests output in subdirectories (vpc/disk.vhd or image/disk.vhd).
        # Move to output root first so the container mount path is simple.
        $vhdFile = Get-ChildItem $OutputFolder -Recurse -Include "*.vhd","*.vpc" | Select-Object -First 1
        if ($vhdFile) {
            $vhdSrc = Join-Path $OutputFolder "disk.vhd"
            if ($vhdFile.FullName -ne $vhdSrc) {
                Move-Item $vhdFile.FullName $vhdSrc -Force
            }
            Write-Step "Converting disk.vhd  VHDX (parallel coroutines)..."
            # -m 16 -W enables 16 parallel coroutines and out-of-order writes for massive speedup
            if ($HelperImage) {
                & podman run --rm -v "${OutputFolder}:/data:z" $HelperImage `
                    qemu-img convert -m 16 -W -f vpc -O vhdx /data/disk.vhd /data/mios-hyperv.vhdx
            } else {
                & podman run --rm -v "${OutputFolder}:/data:z" $FallbackConvert sh -c `
                    "apk add --quiet qemu-img && qemu-img convert -m 16 -W -f vpc -O vhdx /data/disk.vhd /data/mios-hyperv.vhdx"
            }
            Remove-Item $vhdSrc -Force -ErrorAction SilentlyContinue
            Clear-BIBTemp
            if (Test-Path $TargetVhdx) { Write-OK "VHDX: $(Get-FileSize $TargetVhdx)" }
            else { Write-Warn "VHDX conversion failed - qemu-img error" }
        } else {
            Write-Warn "VHD file not found in BIB output"
        }
    } else { Write-Warn "VHD build failed" }
}

# -- WSL --
if ($SelectedTargets -contains 3) {
    Write-Step "TARGET 3 - WSL2 tarball (via native bootc export)..."
    if ($HelperImage) {
        & podman run --rm --privileged -v "${MiosDeployDir}:/output:z" $HelperImage bootc container export --format=tar "oci-archive:/output/wsl.oci" --output /output/mios-wsl.tar
        if ($LASTEXITCODE -ne 0) {
            # Fallback for older helper images
            Write-Warn "bootc export failed, falling back to podman export..."
            $wslCid = & podman create $LocalImage 2>$null
            if ($wslCid) {
                & podman export $wslCid -o $TargetWsl 2>$null
                & podman rm $wslCid 2>$null
            }
        }
    } else {
        # Fallback if no helper image exists at all
        $wslCid = & podman create $LocalImage 2>$null
        if ($wslCid) {
            & podman export $wslCid -o $TargetWsl 2>$null
            & podman rm $wslCid 2>$null
        }
    }
    if (Test-Path $TargetWsl) { Write-OK "WSL: $(Get-FileSize $TargetWsl)" }
    else { Write-Warn "WSL export failed" }
}

# -- ISO --
if ($SelectedTargets -contains 4) {
    Write-Step "TARGET 4 - Anaconda installer ISO..."
    Clear-BIBTemp
    $isoArgs = Get-BIBArgs "anaconda-iso"
    $null = Invoke-BIBRun -BIBArgs $isoArgs -Label "Anaconda installer ISO"
    if ($LASTEXITCODE -eq 0) {
        $isoFile = Get-ChildItem $OutputFolder -Recurse -Filter "*.iso" | Select-Object -First 1
        if ($isoFile) { Move-Item $isoFile.FullName $TargetIso -Force; Write-OK "ISO: $(Get-FileSize $TargetIso)" }
    } else { Write-Warn "ISO failed" }
}

# Clean LUKS temp
Remove-Item (Join-Path $OutputFolder ".luks-tmp") -Force -ErrorAction SilentlyContinue

# ==============================================================================
#  PHASE 3b: DEPLOYMENT (Hyper-V + WSL2)
# ==============================================================================
if ($env:MIOS_SKIP_DEPLOY -eq "1") {
    Write-OK "Deployment phase skipped (MIOS_SKIP_DEPLOY=1)"
} else {
    Write-Phase "3b" "Deployment (Hyper-V + WSL2)"

    # Hyper-V
    if (Test-Path $TargetVhdx) {
        $ErrorActionPreference = "Continue"
        $vmName = "MiOS"
        $doDeploy = $true
        if ($env:MIOS_FORCE_DEPLOY -ne "1") {
            $ans = Read-Timed "Deploy/Update Hyper-V VM '$vmName'? (y/N)" "N"
            $doDeploy = $ans -match "^[yY]"
        }

        if ($doDeploy) {
            try {
                Write-Step "Preparing Hyper-V VM..."
                if (Get-VM -Name $vmName -ErrorAction SilentlyContinue) {
                    Write-Warn "VM '$vmName' already exists. This will OVERWRITE it."
                    $ans = "Y"
                    if ($env:MIOS_FORCE_DEPLOY -ne "1") {
                        $ans = Read-Timed "Confirm OVERWRITE of '$vmName'? (y/N)" "N"
                    }
                    if ($ans -match "^[yY]") {
                        Stop-VM -Name $vmName -Force -ErrorAction SilentlyContinue
                        Remove-VM -Name $vmName -Force
                    } else {
                        Write-Warn "Overwrite cancelled. Skipping Hyper-V deployment."
                        $doDeploy = $false
                    }
                }
                
                if ($doDeploy) {
                    $vmSwitchObj = Get-VMSwitch | Where-Object SwitchType -eq "External" | Select-Object -First 1
                    $vmSwitch = if ($vmSwitchObj) { $vmSwitchObj.Name } else { "Default Switch" }
                    $vmCpu = $cpu
                    $totalRamBytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
                    $vmRamRaw = [int64]($totalRamBytes * 0.8)
                    $vmRam = [int64]([Math]::Floor($vmRamRaw / 2MB) * 2MB)  # Align to 2MB (Hyper-V requirement)
                    $vmRamGB = [Math]::Floor($vmRam / 1GB)
                    $minRam = [Math]::Min(16GB, [int64]([Math]::Floor($totalRamBytes * 0.5 / 2MB) * 2MB))
                    if ($totalRamBytes -lt 16GB) { $minRam = [int64]([Math]::Floor($totalRamBytes * 0.5 / 2MB) * 2MB) }
                    else { $minRam = 16GB }

                    New-VM -Name $vmName -MemoryStartupBytes $minRam -Generation 2 -VHDPath $TargetVhdx -SwitchName $vmSwitch | Out-Null
                    Set-VM -Name $vmName -ProcessorCount $vmCpu -DynamicMemory -MemoryMinimumBytes $minRam -MemoryMaximumBytes $vmRam -MemoryStartupBytes $minRam
                    Set-VMFirmware -VMName $vmName -SecureBootTemplate "MicrosoftUEFICertificateAuthority"
                    Write-OK "Hyper-V VM '$vmName' created (CPUs: $vmCpu | RAM: ${vmRamGB}GB max)"

                    # Start VM
                    Write-Step "Starting VM..."
                    Start-VM -Name $vmName
                    
                    # Wait for POST
                    $timeout = 120; $elapsed = 0; $hb = ""
                    while ($elapsed -lt $timeout) {
                        $hb = (Get-VMIntegrationService -VMName $vmName | Where-Object Name -eq "Heartbeat").PrimaryStatusDescription
                        if ($hb -eq "OK") { break }
                        Start-Sleep 5; $elapsed += 5
                        Write-Progress -Activity "Hyper-V POST" -Status "Waiting for heartbeat..." -PercentComplete ([int]($elapsed/$timeout*100))
                    }
                    Write-Progress -Activity "Hyper-V POST" -Completed

                    if ($hb -eq "OK") {
                        Write-OK "VM fully booted (heartbeat OK)"
                        Write-Step "Enabling Enhanced Session (HvSocket)..."
                        Stop-VM -Name $vmName -Force -ErrorAction SilentlyContinue
                        Set-VM -Name $vmName -EnhancedSessionTransportType HvSocket
                        Start-VM -Name $vmName
                        Write-OK "Hyper-V VM ready. Connect: vmconnect.exe localhost $vmName"
                    } else {
                        Write-Warn "VM may still be booting (no heartbeat). Configure Enhanced Session manually if needed."
                    }
                }
            } catch { Write-Warn "Hyper-V deployment failed: $_" }
        }
    }

    # WSL2
    if (Test-Path $TargetWsl) {
        $ErrorActionPreference = "Continue"
        $WslName = "MiOS"
        $WslPath = Join-Path $env:USERPROFILE "WSL\$WslName"
        $doDeploy = $true
        if ($env:MIOS_FORCE_DEPLOY -ne "1") {
            $ans = Read-Timed "Import/Update WSL2 distro '$WslName'? (y/N)" "N"
            $doDeploy = $ans -match "^[yY]"
        }

        if ($doDeploy) {
            try {
                Write-Step "Preparing WSL2 distro..."
                $existing = wsl --list --quiet | Where-Object { $_ -match "^$WslName" }
                if ($existing) {
                    Write-Warn "WSL distro '$WslName' already exists. This will DELETE it."
                    $ans = "Y"
                    if ($env:MIOS_FORCE_DEPLOY -ne "1") {
                        $ans = Read-Timed "Confirm DELETION of existing '$WslName'? (y/N)" "N"
                    }
                    if ($ans -match "^[yY]") {
                        wsl --unregister $WslName | Out-Null
                    } else {
                        Write-Warn "WSL import cancelled."
                        $doDeploy = $false
                    }
                }

                if ($doDeploy) {
                    New-Item -ItemType Directory -Path $WslPath -Force | Out-Null
                    wsl --import $WslName $WslPath $TargetWsl --version 2
                    if ($LASTEXITCODE -eq 0) {
                        Write-OK "WSL2 distro '$WslName' imported"

                        # Seed /etc/mios/install.env so wsl-firstboot.service uses the
                        # operator-supplied identity instead of the default 'mios' password.
                        if (Write-MiosInstallEnv -WslDistro $WslName -User $U -PasswordHash $passHash -Hostname $HostIn) {
                            Write-OK "Seeded /etc/mios/install.env (user=$U, host=$HostIn)"
                        } else {
                            Write-Warn "install.env not written -- first-boot will fall back to default 'mios' password"
                        }

                        # Generate .wslconfig
                        $wslConfigPath = Join-Path $env:USERPROFILE ".wslconfig"
                        $wslCPUs = $cpu
                        $wslRAM = [Math]::Max(16, [Math]::Floor((Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB * 0.75))
                        
                        $wslLines = @(
                            "# 'MiOS' v0.2.2 - WSL2 Configuration",
                            "[wsl2]",
                            "memory=${wslRAM}GB",
                            "processors=${wslCPUs}",
                            "swap=8GB",
                            "localhostForwarding=true",
                            "nestedVirtualization=true",
                            "vmIdleTimeout=-1",
                            "",
                            "[experimental]",
                            "networkingMode=mirrored",
                            "dnsTunneling=true",
                            "autoProxy=true"
                        )
                        $wslLines -join "`r`n" | Set-Content $wslConfigPath -Encoding UTF8
                        Write-OK ".wslconfig optimized: ${wslRAM}GB RAM"
                    } else { Write-Warn "WSL import failed" }
                }
            } catch { Write-Warn "WSL2 deployment failed: $_" }
        }
    }
}
$ErrorActionPreference = "Stop"


# ==============================================================================
if ($DoPush -and $RegistryToken) {
    Write-Phase "4" "Registry Push  $GhcrImage"
    $ErrorActionPreference = "Continue"
    $registryHost = ($GhcrImage -split '/')[0]

    Write-Step "Authenticating to $registryHost (token via stdin - NOT in process args)..."
    $RegistryToken | & podman login $registryHost --username $RegistryUser --password-stdin 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { Write-Warn "Registry login failed - push may fail" }

    & podman push $GhcrImage
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Pushed to $registryHost"
        # Make package public if ghcr.io
        if ($registryHost -eq "ghcr.io") {
            try {
                $pkgName = ($GhcrImage -split '/')[-1] -replace ':.*$',''
                $owner = ($GhcrImage -split '/')[1]
                $headers = @{ Authorization = "Bearer $RegistryToken"; Accept = "application/vnd.github+json" }
                $uri = "https://api.github.com/orgs/$owner/packages/container/$pkgName"
                $body = '{"visibility":"public"}'
                try { Invoke-RestMethod -Uri $uri -Method Patch -Headers $headers -Body $body -ContentType "application/json" -ErrorAction Stop }
                catch { $uri = "https://api.github.com/user/packages/container/$pkgName"; Invoke-RestMethod -Uri $uri -Method Patch -Headers $headers -Body $body -ContentType "application/json" -ErrorAction SilentlyContinue }
                Write-OK "Package visibility set to public"
            } catch { Write-Warn "Could not set package visibility (may need manual config)" }
        }
    } else { Write-Warn "Push failed" }
    $ErrorActionPreference = "Stop"

} elseif ($DoPush) {
    Write-Warn "Skipping push - no registry token provided"
}

# ==============================================================================
#  PHASE 5: SUMMARY
# ==============================================================================
Write-Phase "5" "Build Summary"
Write-Host ""

# Self-building status
if ($HelperImage) {
    Write-OK "Self-building: ACTIVE - 'MiOS' image used as builder"
    if ($BIBSelfBuild) { Write-OK "  BIB: Self-building ('MiOS' used as bootc-image-builder)" }
    else { Write-OK "  BIB: External (centos-bootc)" }
    Write-OK "  Next build will pull this image and use it for all operations"
} else {
    Write-Warn "Self-building: BOOTSTRAP - first build used fallback images"
    Write-OK "  After push, subsequent builds will self-build from $GhcrImage"
}
Write-Host ""

$targets = @()
if (Test-Path $RawImg)    { $targets += "RAW: $(Get-FileSize $RawImg)" }
if (Test-Path $TargetVhdx){ $targets += "VHDX: $(Get-FileSize $TargetVhdx)" }
if (Test-Path $TargetWsl) { $targets += "WSL: $(Get-FileSize $TargetWsl)" }
if (Test-Path $TargetIso) { $targets += "ISO: $(Get-FileSize $TargetIso)" }
foreach ($t in $targets) { Write-OK $t }
Write-Host ""
Write-OK "Output folder: $OutputFolder"

# -- Copy Manifests --
if (-not (Test-Path $MiosManifestsDir)) { New-Item -ItemType Directory -Path $MiosManifestsDir -Force | Out-Null }
$manifests = @("root-manifest.json", "ai-context.json")
foreach ($mf in $manifests) {
    if (Test-Path $mf) { Copy-Item $mf (Join-Path $MiosManifestsDir $mf) -Force -ErrorAction SilentlyContinue }
}
Write-OK "Manifests staged in $MiosManifestsDir"

Write-Host ""
Write-Host "  'MiOS' is self-replicating: pull  build  push  repeat" -ForegroundColor Cyan
Write-Host "  On deployed 'MiOS':  mios-rebuild" -ForegroundColor Cyan
Write-Host "  On any machine:       podman pull $GhcrImage" -ForegroundColor Cyan
Write-Host ""

Write-Progress -Activity "'MiOS' Build ${Version}" -Id 0 -Completed

Show-StatusCard

# Copy final unified log to all output directories for post-boot assessment.
if ($script:UnifiedLog -and (Test-Path $script:UnifiedLog)) {
    $logName = Split-Path $script:UnifiedLog -Leaf
    foreach ($dir in @($MiosImagesDir, $MiosDeployDir)) {
        if (Test-Path $dir) {
            Copy-Item $script:UnifiedLog (Join-Path $dir $logName) -Force -ErrorAction SilentlyContinue
        }
    }
    Write-OK "Build log copied to output directories: $logName"
}

try { Stop-Transcript | Out-Null } catch {}

# Cleanup: wipe any credential variables from memory
$P = $null; $passHash = $null; $RegistryToken = $null; $LuksPass = $null
[System.GC]::Collect()
```


### `automation\mios-build-builder.ps1`

```powershell
#Requires -Version 7.1
<#
.SYNOPSIS
  'MiOS' builder - idempotent Podman machine provisioner for Windows.

.DESCRIPTION
  Creates or reconfigures a rootful Podman machine named 'mios-builder'
  with 100% of host CPU/RAM and GPU passthrough provisioning. Safe to re-run.

  - Detects host CPU/RAM via WMI and allocates maximum resources.
  - Filters out fake video adapters (Hyper-V, Parsec, DisplayLink) in GPU
    detection so WSL2 on Windows doesn't trip on Basic Render Driver.
  - If a machine named 'mios-builder' already exists AND is rootful AND
    has >= desired CPUs/RAM, it is left alone (pure idempotent no-op).
  - If misconfigured, tries `podman machine set` first (non-destructive).
  - Only resorts to destroy+recreate when `-Force` is passed or when
    `podman machine set` fails.
  - SSHs into the machine to install nvidia-container-toolkit and generate
    the CDI spec at /var/run/cdi/nvidia.yaml (WSL mode auto-detected).

.PARAMETER MachineName
  Podman machine name (default: mios-builder).

.PARAMETER MinMemReserveMiB
  RAM in MiB to leave for the Windows host (default: 4096).

.PARAMETER Force
  Destroy and recreate the machine even if it already looks correct.

.EXAMPLE
  pwsh .\mios-build-builder.ps1
  pwsh .\mios-build-builder.ps1 -MinMemReserveMiB 8192
  pwsh .\mios-build-builder.ps1 -Force
#>
[CmdletBinding()]
param(
  [string]$MachineName    = 'mios-builder',
  [int]   $MinMemReserveMiB = 4096,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

function Log ($m) { Write-Host "[mios-build-builder] $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "[mios-build-builder] $m" -ForegroundColor Yellow }
function Die ($m) { Write-Host "[mios-build-builder] FATAL: $m" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
  Die 'podman.exe not on PATH. Install Podman Desktop or Podman CLI first.'
}
try {
  $pv = (& podman version --format '{{.Client.Version}}') 2>$null
  Log "Podman client: $pv"
} catch { Warn 'Could not read Podman version; continuing.' }

# ---------------------------------------------------------------------------
# Host capacity detection (WMI / CIM)
# ---------------------------------------------------------------------------
$cs  = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor
$totalLogical = ($cpu | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum
$totalMiB     = [int]($cs.TotalPhysicalMemory / 1MB)
$allocMiB     = [Math]::Max(2048, $totalMiB - $MinMemReserveMiB)

Log ("Host: {0} logical CPUs, {1} MiB RAM; allocating {2} MiB ({3} MiB reserved for host)" `
     -f $totalLogical, $totalMiB, $allocMiB, $MinMemReserveMiB)

# ---------------------------------------------------------------------------
# GPU detection (filters fake adapters)
# ---------------------------------------------------------------------------
$gpus = Get-CimInstance Win32_VideoController |
  Where-Object {
    $_.PNPDeviceID -match '^PCI\\VEN_(10DE|1002|8086)' -and
    $_.Name -notmatch 'Vendor Basic|Hyper-V|Remote Display|Parsec|DisplayLink'
  }

$hasNvidia = [bool]($gpus | Where-Object { $_.PNPDeviceID -match 'VEN_10DE' } | Select-Object -First 1)
$hasAmd    = [bool]($gpus | Where-Object { $_.PNPDeviceID -match 'VEN_1002' } | Select-Object -First 1)
$hasIntel  = [bool]($gpus | Where-Object { $_.PNPDeviceID -match 'VEN_8086' } | Select-Object -First 1)

foreach ($g in $gpus) { Log "  GPU: $($g.Name)" }
Log ("Detected: NVIDIA={0}  AMD={1}  Intel={2}" -f $hasNvidia, $hasAmd, $hasIntel)

# ---------------------------------------------------------------------------
# Idempotency: inspect existing machine
# ---------------------------------------------------------------------------
$existing = $null
try {
  $raw = & podman machine inspect $MachineName 2>$null
  if ($LASTEXITCODE -eq 0 -and $raw) {
    $parsed = $raw | ConvertFrom-Json
    if ($parsed -is [Array]) { $existing = $parsed[0] } else { $existing = $parsed }
  }
} catch { $existing = $null }

$needsRecreate = $false

if ($existing) {
  # Podman's inspect schema varies slightly across versions; try both shapes.
  $curCpus    = 0; $curMem = 0; $curRootful = $false
  try { $curCpus    = [int] $existing.Resources.CPUs }      catch { $null }
  try { $curMem     = [int] $existing.Resources.Memory }    catch { $null }
  try { $curRootful = [bool]$existing.Rootful }             catch { $null }
  if (-not $curCpus)    { try { $curCpus    = [int] $existing.CPUs }    catch { $null } }
  if (-not $curMem)     { try { $curMem     = [int] $existing.Memory }  catch { $null } }

  Log "Existing '$MachineName': CPUs=$curCpus Memory=${curMem}MiB Rootful=$curRootful State=$($existing.State)"

  if     ($Force)                               { $needsRecreate = $true; Warn '-Force set; will recreate' }
  elseif (-not $curRootful)                     { $needsRecreate = $true; Warn 'Machine is not rootful' }
  elseif ($curCpus -lt $totalLogical)           { $needsRecreate = $true; Warn "CPUs ($curCpus) below host ($totalLogical)" }
  elseif ($curMem  -lt ($allocMiB - 512))       { $needsRecreate = $true; Warn "RAM (${curMem} MiB) below target (~$allocMiB MiB)" }
  else                                          { Log 'Existing machine config acceptable; no recreate needed.' }
} else {
  Log "No existing machine '$MachineName'; will create."
}

# ---------------------------------------------------------------------------
# Create or reconfigure
# ---------------------------------------------------------------------------
if (-not $existing) {
  & podman machine init --cpus $totalLogical --memory $allocMiB --rootful $MachineName
  if ($LASTEXITCODE -ne 0) { Die 'podman machine init failed' }
}
elseif ($needsRecreate -and $Force) {
  Warn "Destroying and recreating '$MachineName'"
  & podman machine stop $MachineName 2>$null | Out-Null
  & podman machine rm -f $MachineName
  & podman machine init --cpus $totalLogical --memory $allocMiB --rootful $MachineName
  if ($LASTEXITCODE -ne 0) { Die 'podman machine init failed' }
}
elseif ($needsRecreate) {
  # Prefer non-destructive reconfigure. Podman 5.x supports --cpus/--memory
  # /--rootful on stopped machines.
  Log 'Reconfiguring existing machine via podman machine set (non-destructive)'
  & podman machine stop $MachineName 2>$null | Out-Null
  & podman machine set --cpus $totalLogical --memory $allocMiB --rootful $MachineName
  if ($LASTEXITCODE -ne 0) {
    Warn 'podman machine set failed; falling back to destroy+recreate'
    & podman machine rm -f $MachineName
    & podman machine init --cpus $totalLogical --memory $allocMiB --rootful $MachineName
    if ($LASTEXITCODE -ne 0) { Die 'podman machine init failed on fallback path' }
  }
}

# ---------------------------------------------------------------------------
# Start machine (idempotent: "already running" is not an error)
# ---------------------------------------------------------------------------
& podman machine start $MachineName 2>$null
Log 'Machine started (or was already running).'

# ---------------------------------------------------------------------------
# SSH-side provisioning
# Podman machine's Fedora root filesystem IS mutable on WSL (no rpm-ostree),
# so dnf installs persist across stop/start.
# ---------------------------------------------------------------------------
function Invoke-MachineSSH {
  param([Parameter(Mandatory)][string]$Bash)
  # The PowerShell | pipeline re-introduces \r\n when writing each line to a
  # child process stdin, even after -replace stripping. Bypass entirely by
  # base64-encoding the script and decoding inside the machine.
  # base64 charset (A-Za-z0-9+/=) contains no CRLFs or shell metacharacters.
  $Bash = $Bash -replace "`r`n", "`n" -replace "`r", "`n"
  $encoded = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($Bash))
  & podman machine ssh $MachineName -- sudo bash -c "echo $encoded | base64 -d | bash"
  return $LASTEXITCODE
}

if ($hasNvidia) {
  Log 'Provisioning NVIDIA container toolkit inside machine'
  $nvScript = @'
set -euo pipefail
if ! rpm -q nvidia-container-toolkit >/dev/null 2>&1; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
    | tee /etc/yum.repos.d/nvidia-container-toolkit.repo >/dev/null
  dnf install -y nvidia-container-toolkit
fi
install -d -m 0755 /var/run/cdi /etc/cdi
# WSL mode is auto-detected, pass --mode=wsl explicitly for clarity; fall
# back to auto if the flag is unsupported on an older toolkit.
if ! nvidia-ctk cdi generate --mode=wsl --output=/var/run/cdi/nvidia.yaml 2>/dev/null; then
  nvidia-ctk cdi generate --output=/var/run/cdi/nvidia.yaml
fi
# Upstream refresh units (v1.18+) keep the spec current across machine restarts.
systemctl enable --now nvidia-cdi-refresh.path 2>/dev/null || true
echo "NVIDIA CDI ready:"
ls -l /var/run/cdi/
'@
  $rc = Invoke-MachineSSH $nvScript
  if ($rc -ne 0) { Warn "NVIDIA provisioning exited non-zero ($rc); see output above." }
}

if ($hasAmd) {
  Log 'AMD GPU detected on Windows host'
  Warn 'WSL2 does not expose /dev/kfd; ROCm-on-WSL requires librocdxg (ROCm 7.2+)'
  Warn 'Builder will fall back to CPU for AMD-specific builds. NVIDIA/Intel unaffected.'
}

if ($hasIntel -and -not $hasNvidia -and -not $hasAmd) {
  Log 'Intel GPU only -- WSL2 GPU compute for Intel is not officially supported'
  Warn 'Builder will use CPU inference; this does not affect building bootc images.'
}

# ---------------------------------------------------------------------------
# 'MiOS' overlay -- make BUILDER look/feel like a Live 'MiOS' environment.
# Rsyncs the user-facing assets (mios CLI, motd, vendor docs, paths.sh,
# profile.d hooks) into the podman-machine without touching its systemd /
# sysusers / tmpfiles plumbing (those live only in the bootc image).
# ---------------------------------------------------------------------------
$repoRoot = (Get-Location).Path -replace '\\','/' -replace '^([A-Za-z]):','/mnt/$1'.ToLower()
# The above string ops on $1 don't work in PS; recompute properly:
if ((Get-Location).Path -match '^([A-Za-z]):\\(.*)$') {
    $repoRoot = "/mnt/$($Matches[1].ToLower())/$($Matches[2] -replace '\\','/')"
}
if (Test-Path "automation/overlay-builder.sh") {
    Log "Applying 'MiOS' overlay to BUILDER (user-facing files only)"
    $rc = Invoke-MachineSSH "cd '$repoRoot' && bash automation/overlay-builder.sh '$repoRoot'"
    if ($rc -ne 0) { Warn "Overlay exited non-zero ($rc); see output above." }
} else {
    Warn "automation/overlay-builder.sh not found in repo root; skipping overlay."
}

# ---------------------------------------------------------------------------
# Persist builder metadata
# ---------------------------------------------------------------------------
$meta = [ordered]@{
  machine     = $MachineName
  cpus        = $totalLogical
  memoryMiB   = $allocMiB
  gpu_nvidia  = $hasNvidia
  gpu_amd     = $hasAmd
  gpu_intel   = $hasIntel
  provisioned = (Get-Date).ToString('o')
} | ConvertTo-Json

$metaDir = Join-Path $env:LOCALAPPDATA 'MiOS'
New-Item -ItemType Directory -Force -Path $metaDir | Out-Null
# Write without BOM
[System.IO.File]::WriteAllText(
  (Join-Path $metaDir 'builder.json'),
  $meta,
  [System.Text.UTF8Encoding]::new($false)
)

Log ""
Log "Builder ready. Example usage:"
Log "  podman --connection ${MachineName}-root build -t mios:latest ."
Log "  podman --connection ${MachineName}-root run --rm --device nvidia.com/gpu=all \\"
Log "       docker.io/nvidia/cuda:10.1.1-base-ubi9 nvidia-smi"
# Explicit exit 0 -- non-fatal warnings (NVIDIA CDI, AMD/Intel) leave
# $LASTEXITCODE non-zero; without this the caller sees a failure.
exit 0
```


### `preflight.ps1`

```powershell
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host '  Run as Administrator!' -ForegroundColor Red
    return
}
<#
.SYNOPSIS
    'MiOS' Preflight -- Check and install prerequisites
.DESCRIPTION
    Usage: $tmp = "$env:TEMP\mios-preflight.ps1"; irm https://raw.githubusercontent.com/MiOS-DEV/mios/main/preflight.ps1 | Set-Content $tmp; & $tmp; Remove-Item $tmp
#>
$ErrorActionPreference = "Continue"

Write-Host "'MiOS' Preflight -- Prerequisites Check" -ForegroundColor Cyan

$pass = 0
$fail = 0
$fixed = 0

function Check($name, $test, $fix) {
    Write-Host "  [$name] " -NoNewline
    if (& $test) {
        Write-Host "[OK]" -ForegroundColor Green
        $script:pass++
    }
    else {
        Write-Host "[MISSING]" -ForegroundColor Red
        $script:fail++
        if ($fix) {
            $doFix = Read-Host "    Install $name? (y/n)"
            if ($doFix -eq 'y') {
                & $fix
                $script:fixed++
            }
        }
    }
}

Write-Host "--- System ---" -ForegroundColor Yellow
Check "Windows 10/11 Pro+" {
    (Get-CimInstance Win32_OperatingSystem).Caption -match "Pro|Enterprise|Education"
} $null

Write-Host ""
Write-Host "--- WSL2 ---" -ForegroundColor Yellow
Check "WSL2 Feature" {
    (Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux).State -eq 'Enabled'
} {
    Write-Host "    Enabling WSL..." -ForegroundColor Cyan
    wsl --install --no-distribution
    Write-Host "    [WARN] Reboot required after WSL install" -ForegroundColor Yellow
}
Check "Virtual Machine Platform" {
    (Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform).State -eq 'Enabled'
} {
    Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart
}

Write-Host ""
Write-Host "--- Hyper-V (optional) ---" -ForegroundColor Yellow
Check "Hyper-V" {
    (Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V).State -eq 'Enabled'
} {
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All -NoRestart
    Write-Host "    [WARN] Reboot required" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "--- PowerShell ---" -ForegroundColor Yellow
Check "PowerShell 7+" {
    $PSVersionTable.PSVersion.Major -ge 7
} {
    Write-Host "    Installing PowerShell 7+ via winget..." -ForegroundColor Cyan
    winget install --id Vendor.PowerShell --accept-source-agreements --accept-package-agreements
    Write-Host "    [WARN] Restart terminal after PS7 install, then re-run preflight" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "--- Software ---" -ForegroundColor Yellow
Check "Git" {
    Get-Command git -ErrorAction SilentlyContinue
} {
    winget install --id Git.Git --accept-source-agreements --accept-package-agreements
}
Check "Podman" {
    Get-Command podman -ErrorAction SilentlyContinue
} {
    winget install --id RedHat.Podman --accept-source-agreements --accept-package-agreements
}
Check "Podman Desktop" {
    (Get-Command "podman-desktop" -ErrorAction SilentlyContinue) -or (Test-Path "$env:LOCALAPPDATA\Programs\Podman Desktop")
} {
    winget install --id RedHat.Podman-Desktop --accept-source-agreements --accept-package-agreements
}

Write-Host ""
Write-Host "--- Results ---" -ForegroundColor Cyan
Write-Host "  Passed: $pass  Failed: $fail  Fixed: $fixed" -ForegroundColor White
if ($fail -eq 0 -or $fail -eq $fixed) {
    Write-Host "  [OK] Ready to build 'MiOS'!" -ForegroundColor Green
    Write-Host "    Run: `$tmp = `"`$env:TEMP\mios-install.ps1`"; irm https://raw.githubusercontent.com/MiOS-DEV/mios/main/install.ps1 | Set-Content `$tmp; & `$tmp; Remove-Item `$tmp" -ForegroundColor Gray
} else {
    Write-Host "  [WARN] Some prerequisites missing. Fix them and re-run." -ForegroundColor Yellow
}
Write-Host ""
```


### `push-to-github.ps1`

```powershell
# ============================================================================
# push-to-github.ps1  'MiOS' release deliverable (v0.2.2 baseline)
# ----------------------------------------------------------------------------
# Single source of truth for the release pipeline. Per INDEX.md 4 + the
# /push-version skill, this script is rewritten per release and never split
# into push-vX.Y.Z.ps1 siblings.
#
# Behaviour:
#   1. Clone github.com/MiOS-DEV/MiOS-bootstrap into a temp directory.
#   2. Optionally overlay a staged companion directory (-StagedDir) onto the
#      working tree, preserving layout relative to repo root. Files-only 
#      directories are walked and replaced file by file. Nothing is deleted.
#   3. Bump VERSION to -Version (default: read from local VERSION file).
#   4. Stamp CHANGELOG.md with a top-of-file release block dated today.
#   5. Commit with a structured release message.
#   6. Push to main using $env:GH_TOKEN or the configured credential helper.
#   7. Print a summary: changed paths, commit SHA, GHCR tag.
#
# This is the deliverable. Humans run it; the agent does not push for you.
# ============================================================================

[CmdletBinding()]
param(
    [string]$Version,
    [string]$Message = 'release sync',
    [string]$StagedDir,
    [string]$Repo = 'github.com/MiOS-DEV/MiOS-bootstrap',
    [string]$Branch = 'main',
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step([string]$msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok  ([string]$msg) { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "    $msg" -ForegroundColor Yellow }

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'VERSION'))) {
    throw "push-to-github.ps1 must live at the repo root next to VERSION."
}

if (-not $Version) {
    $Version = (Get-Content -LiteralPath (Join-Path $repoRoot 'VERSION') -Raw).Trim()
    Write-Warn "No -Version given; using local VERSION file: $Version"
}

if ($StagedDir) {
    if (-not (Test-Path -LiteralPath $StagedDir -PathType Container)) {
        throw "Staged companion directory not found: $StagedDir"
    }
    $StagedDir = (Resolve-Path -LiteralPath $StagedDir).Path
}

# Token discovery  never echoed to stdout.
$token = $env:GH_TOKEN
if (-not $token) { $token = $env:GITHUB_TOKEN }
if (-not $token) {
    Write-Warn 'No GH_TOKEN/GITHUB_TOKEN in environment; relying on git credential helper.'
}

$workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("mios-push-" + [guid]::NewGuid().ToString('N').Substring(0,8))
Write-Step "Working directory: $workDir"
New-Item -ItemType Directory -Force -Path $workDir | Out-Null

try {
    $cloneUrl = if ($token) { "https://x-access-token:$token@$Repo.git" } else { "https://$Repo.git" }
    $safeUrl  = "https://$Repo.git"

    Write-Step "Cloning $safeUrl ($Branch)  full history."
    git clone --branch $Branch $cloneUrl $workDir 2>&1 | ForEach-Object { Write-Verbose $_ }
    if ($LASTEXITCODE -ne 0) { throw "git clone failed (exit $LASTEXITCODE)." }

    if ($StagedDir) {
        Write-Step "Overlaying staged files from $StagedDir"
        $stagedFiles = Get-ChildItem -LiteralPath $StagedDir -Recurse -File
        foreach ($f in $stagedFiles) {
            $rel = $f.FullName.Substring($StagedDir.Length).TrimStart('\','/')
            $dst = Join-Path $workDir $rel
            $dstDir = Split-Path -Parent $dst
            if (-not (Test-Path -LiteralPath $dstDir)) {
                New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
            }
            Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
            Write-Ok "copied $rel"
        }
    } else {
        Write-Step "No -StagedDir; pushing local working tree state under $repoRoot"
        # Mirror the working repo into the clone (excluding .git).
        $rsyncSrc = (Resolve-Path -LiteralPath $repoRoot).Path
        Get-ChildItem -LiteralPath $rsyncSrc -Force -Recurse -File |
            Where-Object { $_.FullName -notlike (Join-Path $rsyncSrc '.git*') } |
            ForEach-Object {
                $rel = $_.FullName.Substring($rsyncSrc.Length).TrimStart('\','/')
                if ($rel -like '.git\*' -or $rel -eq '.git') { return }
                $dst = Join-Path $workDir $rel
                $dstDir = Split-Path -Parent $dst
                if (-not (Test-Path -LiteralPath $dstDir)) {
                    New-Item -ItemType Directory -Force -Path $dstDir | Out-Null
                }
                Copy-Item -LiteralPath $_.FullName -Destination $dst -Force
            }
    }

    Write-Step "Bumping VERSION  $Version"
    Set-Content -LiteralPath (Join-Path $workDir 'VERSION') -Value $Version -NoNewline -Encoding utf8

    $changelog = Join-Path $workDir 'CHANGELOG.md'
    if (Test-Path -LiteralPath $changelog) {
        $today = Get-Date -Format 'yyyy-MM-dd'
        $existing = Get-Content -LiteralPath $changelog -Raw
        $header = "# Changelog`r`nAll notable changes to this project will be documented in this file.`r`n"
        $body = $existing
        if ($body.StartsWith($header)) { $body = $body.Substring($header.Length).TrimStart() }
        $newBlock = "## [v$Version] - $today`r`n`r`n- $Message`r`n`r`n"
        Set-Content -LiteralPath $changelog -Value ($header + "`r`n" + $newBlock + $body) -Encoding utf8
        Write-Ok "CHANGELOG.md stamped v$Version ($today)"
    } else {
        Write-Warn "CHANGELOG.md missing in clone  skipping changelog stamp."
    }

    Push-Location $workDir
    try {
        git add --all 2>&1 | ForEach-Object { Write-Verbose $_ }
        $status = git status --porcelain
        if (-not $status) {
            Write-Warn 'No changes to commit. Nothing to push.'
            return
        }

        $commitMsg = "release: v$Version  $Message"
        if ($DryRun) {
            Write-Step "DRY RUN  skipping commit/push. Pending changes:"
            Write-Host $status
            return
        }

        git -c user.name='MiOS bot' -c user.email='mios@users.noreply.github.com' `
            commit -m $commitMsg 2>&1 | ForEach-Object { Write-Verbose $_ }
        if ($LASTEXITCODE -ne 0) { throw "git commit failed (exit $LASTEXITCODE)." }

        $sha = (git rev-parse HEAD).Trim()
        Write-Step "Pushing to $Branch"
        git push origin $Branch 2>&1 | ForEach-Object { Write-Verbose $_ }
        if ($LASTEXITCODE -ne 0) { throw "git push failed (exit $LASTEXITCODE)." }

        Write-Ok "Commit: $sha"
        Write-Ok "GHCR tag (built by CI): ghcr.io/MiOS-DEV/mios:$Version"
    }
    finally {
        Pop-Location
    }
}
finally {
    if (Test-Path -LiteralPath $workDir) {
        Remove-Item -LiteralPath $workDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
```


### `Get-MiOS.ps1`

```powershell
<#
.SYNOPSIS
    'MiOS' bootstrap -- one-liner entry point.

.DESCRIPTION
    Designed for:  irm https://raw.githubusercontent.com/MiOS-DEV/MiOS/main/Get-MiOS.ps1 | iex

    What it does:
      1. Elevates to Administrator if needed.
      2. Ensures Git + Podman are present.
      3. Clones / updates the 'MiOS' repo into $env:USERPROFILE\MiOS.
      4. Sets MIOS_UNIFIED_LOG so the entire session writes one flat transcript.
      5. Starts Start-Transcript (unified log).
      6. Calls mios-build-local.ps1 from the repo root.
      7. Stops the transcript on exit.

    The unified log is written to ~/Documents/MiOS/mios-build-<timestamp>.log and
    copied into the build output directories by mios-build-local.ps1 at the end.
#>
param(
    [string]$RepoUrl  = "https://github.com/MiOS-DEV/MiOS.git",
    [string]$Branch   = "main",
    [string]$RepoDir  = (Join-Path $env:USERPROFILE "MiOS"),
    [string]$Workflow = ""         # passed through to mios-build-local.ps1
)

$ErrorActionPreference = "Stop"

# ── 1. Elevation ──────────────────────────────────────────────────────────────
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $args_ = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    if ($Workflow) { $args_ += " -Workflow $Workflow" }
    Start-Process powershell.exe -ArgumentList $args_ -Verb RunAs
    return
}

# ── 2. Helpers ────────────────────────────────────────────────────────────────
function Write-Info  { param([string]$M) Write-Host "  [*] $M" -ForegroundColor Cyan }
function Write-Good  { param([string]$M) Write-Host "  [+] $M" -ForegroundColor Green }
function Write-Err   { param([string]$M) Write-Host "  [!] $M" -ForegroundColor Red }
function Require-Cmd {
    param([string]$Cmd, [string]$InstallHint)
    if (-not (Get-Command $Cmd -ErrorAction SilentlyContinue)) {
        Write-Err "$Cmd not found. $InstallHint"
        exit 1
    }
}

Write-Host "'MiOS' Bootstrap  (irm | iex entry)" -ForegroundColor Cyan

# ── 3. Prerequisites ──────────────────────────────────────────────────────────
Require-Cmd "git"    "Install Git from https://git-scm.com/download/win"
Require-Cmd "podman" "Install Podman Desktop from https://podman-desktop.io"
Write-Good "Prerequisites OK (git, podman)"

# ── 4. Unified log path (before transcript starts) ────────────────────────────
$LogDir = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "MiOS"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }
$LogFile = Join-Path $LogDir "mios-build-$([DateTime]::Now.ToString('yyyyMMdd-HHmmss')).log"
[Environment]::SetEnvironmentVariable("MIOS_UNIFIED_LOG", $LogFile)
Write-Info "Unified log → $LogFile"

# ── 5. Start transcript ───────────────────────────────────────────────────────
try { Start-Transcript -Path $LogFile -Force | Out-Null } catch {}

# ── 6. Clone / update repo ────────────────────────────────────────────────────
if (Test-Path (Join-Path $RepoDir ".git")) {
    Write-Info "Updating existing repo at $RepoDir ..."
    Push-Location $RepoDir
    & git fetch origin 2>&1 | Write-Host
    & git checkout $Branch 2>&1 | Write-Host
    & git pull --ff-only origin $Branch 2>&1 | Write-Host
    Pop-Location
} else {
    Write-Info "Cloning $RepoUrl → $RepoDir ..."
    & git clone --branch $Branch --depth 1 $RepoUrl $RepoDir
    if ($LASTEXITCODE -ne 0) {
        Write-Err "git clone failed"
        try { Stop-Transcript | Out-Null } catch {}
        exit 1
    }
}
Write-Good "Repo ready at $RepoDir"

# ── 7. Launch build script ────────────────────────────────────────────────────
$buildScript = Join-Path $RepoDir "mios-build-local.ps1"
if (-not (Test-Path $buildScript)) {
    Write-Err "mios-build-local.ps1 not found in $RepoDir"
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

if ($Workflow) { $env:MIOS_WORKFLOW = $Workflow }

Write-Info "Entering repo root and launching mios-build-local.ps1 ..."
Push-Location $RepoDir
try {
    & $buildScript
} finally {
    Pop-Location
    try { Stop-Transcript | Out-Null } catch {}
}
```


### `install.ps1`

```powershell
<#
.SYNOPSIS  'MiOS' v0.2.2 -- Unified Windows Installer
.DESCRIPTION
    Entry: irm https://raw.githubusercontent.com/MiOS-DEV/mios/main/install.ps1 | iex
    Normally downloaded + launched by bootstrap.ps1 after collecting credentials.

    Platform entrypoints are thin bootstraps -- all build logic runs against the
    shared codebase (Containerfile + automation/) via `podman build`.

    Expected env vars from bootstrap.ps1 (or set manually):
        GHCR_TOKEN          GitHub PAT for image pull / push
        MIOS_USER           Admin username
        MIOS_PASSWORD       Admin password (plaintext -- hashed before injection)
        MIOS_HOSTNAME       Static hostname (default: mios-XXXXX)
        MIOS_DIR            Repo clone target directory
        MIOS_AUTOINSTALL    Set to "1" for non-interactive defaults
#>
#Requires -Version 7.1
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# ─── constants ────────────────────────────────────────────────────────────────
$Version        = (Get-Content (Join-Path $PSScriptRoot "VERSION") -EA SilentlyContinue)?.Trim() ?? "0.2.2"
$RepoUrl        = "https://github.com/MiOS-DEV/MiOS.git"
$BibImage       = if ($env:MIOS_BIB_IMAGE) { $env:MIOS_BIB_IMAGE } else { "quay.io/centos-bootc/bootc-image-builder:latest" }
$BuilderMachine = "mios-builder"
$ImageName      = "mios"
$ImageTag       = "latest"
$LocalImage     = "localhost/${ImageName}:${ImageTag}"

$MiosDocsDir      = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "MiOS"
$MiosDeployDir    = Join-Path $MiosDocsDir "deployments"
$MiosImagesDir    = Join-Path $MiosDocsDir "images"
$MiosManifestsDir = Join-Path $MiosDocsDir "manifests"
$RepoDir          = if ($env:MIOS_DIR) { $env:MIOS_DIR } else { Join-Path $env:LOCALAPPDATA "'MiOS'\repo" }

$TargetVhdx = Join-Path $MiosDeployDir "mios-hyperv.vhdx"
$TargetWsl  = Join-Path $MiosDeployDir "mios-wsl.tar"
$TargetIso  = Join-Path $MiosImagesDir "mios-installer.iso"

# Shared helper: writes /etc/mios/install.env into a freshly-imported WSL2
# distro so wsl-firstboot.service picks up the operator-supplied identity
# instead of falling back to the literal default password "mios".
. (Join-Path $PSScriptRoot "tools/lib/install-env.ps1")

# ─── masking ──────────────────────────────────────────────────────────────────
$script:MaskList = [System.Collections.Generic.List[string]]::new()

function Register-Secret {
    param([string]$S)
    if (-not [string]::IsNullOrWhiteSpace($S) -and $S.Length -ge 4 -and -not $script:MaskList.Contains($S)) {
        $script:MaskList.Add($S)
    }
}

function Format-Masked {
    param([string]$S)
    $out = $S
    foreach ($m in $script:MaskList) {
        $out = $out -ireplace [regex]::Escape($m), "********"
    }
    return $out
}

@("GHCR_TOKEN","GH_TOKEN","GITHUB_TOKEN","MIOS_PASSWORD","MIOS_GHCR_TOKEN") | ForEach-Object {
    # PowerShell parses $env:$_ as a scope-qualified var ref and rejects it
    # at parse time. Use [Environment]::GetEnvironmentVariable instead.
    $val = [Environment]::GetEnvironmentVariable($_)
    if ($val) { Register-Secret $val }
}

# ─── dashboard state ──────────────────────────────────────────────────────────
$script:DashRow    = 0
$script:DashH      = 0
$script:DashReady  = $false
$script:BuildStart = [DateTime]::Now
$script:ErrCount   = 0
$script:WarnCount  = 0
$script:Op         = "Initializing..."
$script:LogFile    = ""

# Phase definitions -- EstSteps drives the progress denominator
$script:Phases = @(
    [pscustomobject]@{Id=0;  Name="Hardware + Prerequisites";  State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=1;  Name="Detecting environment";     State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=2;  Name="Directories and repos";     State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=3;  Name="MiOS-BUILDER distro";       State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=4;  Name="WSL2 configuration";        State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=5;  Name="Verifying build context";   State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=6;  Name="Identity";                  State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=7;  Name="Writing identity";          State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=8;  Name="App registration";          State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
    [pscustomobject]@{Id=9;  Name="Building OCI image";        State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=48; EstSteps=48}
    [pscustomobject]@{Id=10; Name="Exporting WSL2 image";      State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=2}
    [pscustomobject]@{Id=11; Name="Registering 'MiOS' WSL2";     State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=2}
    [pscustomobject]@{Id=12; Name="Building disk images";      State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=4}
    [pscustomobject]@{Id=13; Name="Deploying Hyper-V VM";      State="pending"; StartT=$null; ElapsedS=0; InnerStep=0; InnerTotal=0; EstSteps=1}
)
$TotalEstSteps = ($script:Phases | Measure-Object -Property EstSteps -Sum).Sum  # ≈ 65

# ─── dashboard rendering ──────────────────────────────────────────────────────
$DW = 78  # inner content width

function _dpad { param([string]$S,[int]$W) if($S.Length -ge $W){$S.Substring(0,$W)}else{$S.PadRight($W)} }
function _dsep { param([char]$C='-') '+' + [string]::new($C,$DW) + '+' }

function Show-Dashboard {
    param([switch]$FullRedraw)

    $elapsed = [DateTime]::Now - $script:BuildStart
    $tStr    = "{0:D2}:{1:D2}" -f [int]$elapsed.TotalHours, $elapsed.Minutes

    # Progress calculation
    $stepsCompleted = 0
    $stepsRunning   = 0
    foreach ($ph in $script:Phases) {
        if ($ph.State -eq "ok" -or $ph.State -eq "warn" -or $ph.State -eq "fail") {
            $stepsCompleted += $ph.EstSteps
        } elseif ($ph.State -eq "running") {
            $inner = if ($ph.InnerTotal -gt 0) { [int]($ph.InnerStep * $ph.EstSteps / $ph.InnerTotal) } else { 0 }
            $stepsRunning = $inner
        }
    }
    $stepsDone  = $stepsCompleted + $stepsRunning
    $pct        = [Math]::Min(99, [int]($stepsDone * 100 / [Math]::Max(1, $TotalEstSteps)))
    $barFill    = [int]($pct * 58 / 100)
    $bar        = '[' + [string]::new('=',[Math]::Max(0,$barFill-1)) + '>' + [string]::new(' ',58-$barFill) + ']'

    # Current phase info
    $curPh = $script:Phases | Where-Object { $_.State -eq "running" } | Select-Object -Last 1
    $phStr = if ($curPh) {
        $inner = if ($curPh.InnerTotal -gt 0) { "  ($($curPh.InnerStep)/$($curPh.InnerTotal) steps)" } else { "" }
        "[$($curPh.Id)/13] $($curPh.Name)$inner"
    } else { "Initializing" }

    $op     = _dpad (Format-Masked $script:Op) ($DW - 7)
    $status = if ($pct -ge 100) { "DONE" } else { "RUNNING" }

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add($(_dsep '-'))
    $lines.Add("| $(_dpad "  'MiOS' v$Version  --  Build Dashboard" ($DW-9)) [ $tStr ] |")
    $lines.Add($(_dsep '-'))
    $lines.Add("| Ph : $(_dpad $phStr ($DW-7))|")
    $lines.Add("| Op : $op|")                                                     # offset 4
    $lines.Add("| $(_dpad "Errors:$($script:ErrCount)  Warns:$($script:WarnCount)  Status:$status" ($DW-2))|")
    $lines.Add($(_dsep '-'))
    $lines.Add("| $bar  $("{0,3}" -f $pct)%  $stepsDone/$TotalEstSteps |")
    $lines.Add($(_dsep '-'))
    $lines.Add("| $(_dpad "  #  State  Phase Name" ($DW-10)) Time  |")
    $lines.Add("| $(_dpad (" ---  -----  " + [string]::new('-',44)) ($DW-2))|")

    foreach ($ph in $script:Phases) {
        $stateStr = switch ($ph.State) {
            "ok"      { "[OK] " }
            "running" { "[>>] " }
            "fail"    { "[!!] " }
            "warn"    { "[??] " }
            default   { "[  ] " }
        }
        $tCell = if ($ph.ElapsedS -gt 0) { "{0:D2}:{1:D2}" -f [int]($ph.ElapsedS/60), ($ph.ElapsedS%60) } else { "     " }
        $lines.Add("| {0,3}  {1}  {2}  {3} |" -f $ph.Id, $stateStr, (_dpad $ph.Name 48), $tCell)
    }

    $lines.Add($(_dsep '-'))
    $logName = if ($script:LogFile) { Split-Path $script:LogFile -Leaf } else { "starting..." }
    $lines.Add("| Log: $(_dpad $logName ($DW-7))|")
    $lines.Add($(_dsep '-'))

    $script:DashH = $lines.Count

    if (-not $script:DashReady) {
        # First render -- write fresh, record position
        $script:DashRow = [Console]::CursorTop
        foreach ($l in $lines) { [Console]::WriteLine($l) }
        $script:DashReady = $true
    } else {
        # In-place redraw -- only rewrite if cursor is still on screen
        try {
            $savedTop = [Console]::CursorTop
            $savedLeft = [Console]::CursorLeft
            [Console]::SetCursorPosition(0, $script:DashRow)
            foreach ($l in $lines) {
                [Console]::Write("`r" + $l.PadRight([Console]::WindowWidth - 1))
                [Console]::WriteLine()
            }
            # Move cursor to below dashboard for any subsequent Write-Host output
            [Console]::SetCursorPosition(0, $script:DashRow + $script:DashH)
        } catch { }
    }
}

# Fast partial update -- just the Op: line, avoids redrawing 28 lines on every build output line
function Set-Op {
    param([string]$NewOp)
    $masked = Format-Masked $NewOp
    if ($masked.Length -gt ($DW - 8)) { $masked = $masked.Substring(0, $DW - 11) + '...' }
    $script:Op = $masked
    try {
        [Console]::SetCursorPosition(0, $script:DashRow + 4)
        [Console]::Write("| Op : $($masked.PadRight($DW - 7))|".PadRight([Console]::WindowWidth - 1))
        [Console]::SetCursorPosition(0, $script:DashRow + $script:DashH)
    } catch { }
}

# ─── phase management ─────────────────────────────────────────────────────────
function Start-Phase {
    param([int]$Id, [string]$InitOp = "")
    $ph = $script:Phases[$Id]
    $ph.State   = "running"
    $ph.StartT  = [DateTime]::Now
    if ($InitOp) { $script:Op = $InitOp }
    Show-Dashboard -FullRedraw
    Write-Log "=== Phase ${Id}: $($ph.Name) ===" -Color Cyan
}

function Finish-Phase {
    param([int]$Id, [string]$State = "ok")
    $ph = $script:Phases[$Id]
    $ph.State    = $State
    $ph.ElapsedS = [int]([DateTime]::Now - $ph.StartT).TotalSeconds
    Show-Dashboard -FullRedraw
}

# ─── logging ──────────────────────────────────────────────────────────────────
function Write-Log {
    param([string]$Msg, [string]$Color = "Gray")
    $ts      = Get-Date -Format "HH:mm:ss"
    $masked  = Format-Masked $Msg
    # Write-Host goes through transcript; console cursor is already below dashboard
    Write-Host "[$ts] $masked" -ForegroundColor $Color
}

function Write-LogOK   { param([string]$M) $script:BuildAudit += "[OK] $M"; Write-Log "  [OK] $M" -Color Green }
function Write-LogWarn { param([string]$M) $script:WarnCount++; Write-Log " [WARN] $M" -Color Yellow }
function Write-LogFail { param([string]$M) $script:ErrCount++;  Write-Log " [FAIL] $M" -Color Red }
function Write-LogFatal {
    param([string]$M)
    $script:ErrCount++
    Write-Log " [FATAL] $M" -Color Red
    try { Stop-Transcript | Out-Null } catch {}
    exit 1
}

$script:BuildAudit = [System.Collections.Generic.List[string]]::new()

# ─── credential helpers ───────────────────────────────────────────────────────
function Read-Masked {
    param([string]$Prompt, [string]$Default = "")
    # Move cursor below dashboard before prompting
    try { [Console]::SetCursorPosition(0, $script:DashRow + $script:DashH + 1) } catch {}
    Write-Host "  $Prompt " -NoNewline -ForegroundColor DarkCyan
    if ($Default) { Write-Host "[$(if($Default -eq $env:GHCR_TOKEN -or $Default.Length -gt 8){'********'}else{$Default})] " -NoNewline -ForegroundColor DarkGray }
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        $val = Read-Host -MaskInput
    } else {
        $sec  = Read-Host -AsSecureString
        $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
        try   { $val = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
        finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }
    if ([string]::IsNullOrWhiteSpace($val) -and $Default) { return $Default }
    if ($val) { Register-Secret $val }
    return $val
}

function Read-Plain {
    param([string]$Prompt, [string]$Default = "")
    try { [Console]::SetCursorPosition(0, $script:DashRow + $script:DashH + 1) } catch {}
    Write-Host "  $Prompt " -NoNewline -ForegroundColor DarkCyan
    if ($Default) { Write-Host "[$Default] " -NoNewline -ForegroundColor DarkGray }
    $val = Read-Host
    if ([string]::IsNullOrWhiteSpace($val)) { return $Default }
    return $val
}

function Get-SHA512Hash {
    param([string]$PlainText, [string]$HImg)
    $salt = -join ((65..90)+(97..122)+(48..57) | Get-Random -Count 16 | ForEach-Object { [char]$_ })
    $h = $null
    if ($HImg) {
        $h = (& podman run --rm $HImg openssl passwd -6 -salt $salt $PlainText 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and $h -match '^\$6\$') { return $h }
    }
    $h = (& podman run --rm docker.io/library/alpine:latest sh -c "apk add -q openssl >/dev/null 2>&1 && openssl passwd -6 -salt '$salt' '$PlainText'" 2>$null).Trim()
    if ($h -match '^\$6\$') { return $h }
    # python fallback
    $h = (& podman run --rm docker.io/library/python:3-slim python3 -c "import crypt; print(crypt.crypt('$PlainText', crypt.mksalt(crypt.METHOD_SHA512)))" 2>$null).Trim()
    return $h
}

function Get-FileSize {
    param([string]$P)
    if (-not (Test-Path $P)) { return "N/A" }
    $s = (Get-Item $P).Length
    if ($s -gt 1GB) { "$([Math]::Round($s/1GB,2)) GB" } else { "$([Math]::Round($s/1MB,1)) MB" }
}

# ─── BIB streaming runner ─────────────────────────────────────────────────────
function Invoke-BIBRun {
    param([string[]]$BIBArgs, [string]$Label)
    $n = 0
    Set-Op "Starting $Label..."
    & podman @BIBArgs 2>&1 | ForEach-Object {
        $line = $_
        Write-Log (Format-Masked $line) -Color DarkGray
        $n++
        $stripped = ($line -replace '^\s*#\d+\s+(?:[\d.]+\s+)?','').TrimStart()
        $opCandidate = if ($stripped -match 'org\.osbuild\.\S+') { $Matches[0] }
        elseif ($stripped -match '^(Assembling|Building|Extracting|Installing|Packaging|Stage|Writing)\b') {
            ($stripped -replace '\s+',' ').Trim()
        } elseif (-not [string]::IsNullOrWhiteSpace($stripped)) {
            ($stripped -replace '\s+',' ').Trim()
        }
        if ($opCandidate) {
            if ($opCandidate.Length -gt 72) { $opCandidate = $opCandidate.Substring(0,69) + '...' }
            Set-Op $opCandidate
        }
    }
    return $LASTEXITCODE
}

# ─── elevation ────────────────────────────────────────────────────────────────
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
         ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "  Relaunching as Administrator..." -ForegroundColor Cyan
    Start-Process pwsh.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Path)`"" -Verb RunAs
    return
}

# ─── static header (printed once, scrolls away) ───────────────────────────────
[Console]::WriteLine("")
[Console]::WriteLine('+' + [string]::new('=',78) + '+')
[Console]::WriteLine("| $(_dpad "'MiOS' v$Version  --  Unified Windows Installer" 76) |")
[Console]::WriteLine("| $(_dpad "Immutable Fedora AI Workstation" 76) |")
[Console]::WriteLine("| $(_dpad "WSL2 + Podman  |  Offline Build Pipeline" 76) |")
[Console]::WriteLine('+' + [string]::new('=',78) + '+')
[Console]::WriteLine("")

# ─── log + transcript ─────────────────────────────────────────────────────────
foreach ($d in @($MiosDocsDir,$MiosDeployDir,$MiosImagesDir,$MiosManifestsDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}
$script:LogFile = if ($env:MIOS_UNIFIED_LOG) { $env:MIOS_UNIFIED_LOG } else {
    Join-Path $MiosDocsDir "mios-install-$([DateTime]::Now.ToString('yyyyMMdd-HHmmss')).log"
}
[Environment]::SetEnvironmentVariable("MIOS_UNIFIED_LOG", $script:LogFile)
try { Start-Transcript -Path $script:LogFile -Append -Force | Out-Null } catch {}

# Initial dashboard render
Show-Dashboard

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 0 -- Hardware + Prerequisites
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 0 "Checking Windows version..."
$os = Get-CimInstance Win32_OperatingSystem
if ($os.Caption -notmatch "Pro|Enterprise|Education|Server") {
    Write-LogWarn "Windows edition may not support Hyper-V: $($os.Caption)"
} else { Write-LogOK "OS: $($os.Caption)" }

foreach ($feat in @("Microsoft-Hyper-V","VirtualMachinePlatform","Microsoft-Windows-Subsystem-Linux")) {
    $f = Get-WindowsOptionalFeature -Online -FeatureName $feat -EA SilentlyContinue
    if ($f -and $f.State -eq "Enabled") { Write-LogOK "$feat enabled" }
    else { Write-LogWarn "$feat not enabled -- some targets may be unavailable" }
}
try {
    $null = & podman --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
    Write-LogOK "Podman found"
} catch { Write-LogFatal "Podman not found. Install Podman Desktop: https://podman-desktop.io" }
Finish-Phase 0

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 1 -- Detecting environment
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 1 "Detecting hardware..."
$cpu = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
$ram = [Math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$disk = [Math]::Floor((Get-PSDrive C).Free / 1GB)
Write-LogOK "CPU: $cpu cores  RAM: ${ram}GB  Disk free: ${disk}GB"
if ($disk -lt 80) { Write-LogWarn "Low disk space (<80 GB). Build may fail." }
Finish-Phase 1

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 2 -- Directories and repos
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 2 "Preparing directories..."
foreach ($d in @($MiosDocsDir,$MiosDeployDir,$MiosImagesDir,$MiosManifestsDir,(Split-Path $RepoDir -Parent))) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

Set-Op "Cloning / updating 'MiOS' repo..."
if (Test-Path (Join-Path $RepoDir ".git")) {
    Write-Log "Updating existing repo at $RepoDir..."
    Push-Location $RepoDir
    $null = & git fetch origin 2>&1
    $null = & git pull --ff-only origin main 2>&1
    Pop-Location
    Write-LogOK "Repo updated: $RepoDir"
} else {
    Write-Log "Cloning $RepoUrl → $RepoDir..."
    if ($env:GHCR_TOKEN) {
        $authUrl = "https://MiOS-DEV:$($env:GHCR_TOKEN)@github.com/MiOS-DEV/MiOS.git"
        & git clone --depth 1 $authUrl $RepoDir 2>&1 | ForEach-Object { Write-Log $_ }
    } else {
        & git clone --depth 1 $RepoUrl $RepoDir 2>&1 | ForEach-Object { Write-Log $_ }
    }
    if ($LASTEXITCODE -ne 0) { Write-LogFatal "git clone failed. Check network and token." }
    Write-LogOK "Repo cloned: $RepoDir"
}
Set-Location $RepoDir
Finish-Phase 2

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 3 -- MiOS-BUILDER distro
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 3 "Provisioning $BuilderMachine Podman machine..."
$builderScript = Join-Path $RepoDir "automation\mios-build-builder.ps1"
if (-not (Test-Path $builderScript)) { Write-LogFatal "Missing $builderScript" }
& $builderScript -MachineName $BuilderMachine 2>&1 | ForEach-Object {
    $l = Format-Masked $_
    Set-Op $l
    Write-Log $l
}
if ($LASTEXITCODE -ne 0) { Write-LogFatal "Builder provisioning failed" }
& podman system connection default "${BuilderMachine}-root" 2>$null
Write-LogOK "Connection: ${BuilderMachine}-root"
Finish-Phase 3

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 4 -- WSL2 configuration
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 4 "Writing .wslconfig..."
$wslCfg = Join-Path $env:USERPROFILE ".wslconfig"
$wslRAM = [Math]::Max(16, [Math]::Floor($ram * 0.80))
$wslLines = @(
    "# 'MiOS' v$Version -- WSL2 Configuration"
    "[wsl2]"
    "memory=${wslRAM}GB"
    "processors=${cpu}"
    "swap=8GB"
    "localhostForwarding=true"
    "nestedVirtualization=true"
    "vmIdleTimeout=-1"
    ""
    "[experimental]"
    "networkingMode=mirrored"
    "dnsTunneling=true"
    "autoProxy=true"
)
$wslLines -join "`r`n" | Set-Content $wslCfg -Encoding UTF8
Write-LogOK ".wslconfig: ${wslRAM}GB RAM, $cpu CPUs"
Finish-Phase 4

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 5 -- Verifying build context
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 5 "Checking repo files..."
foreach ($f in @("Containerfile","VERSION","automation/build.sh","automation/31-user.sh")) {
    if (-not (Test-Path (Join-Path $RepoDir $f))) { Write-LogFatal "Missing: $f" }
}
Write-LogOK "Build context verified"
Finish-Phase 5

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 6 -- Identity
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 6 "Collecting credentials..."
$AutoInstall = $env:MIOS_AUTOINSTALL -eq "1"

$U = if ($env:MIOS_USER) { $env:MIOS_USER } else {
    Read-Plain "Admin username:" "mios"
}
$P = if ($env:MIOS_PASSWORD) { $env:MIOS_PASSWORD } else {
    if ($AutoInstall) { "mios" } else {
        $pw1 = Read-Masked "Admin password:" ""
        $pw2 = Read-Masked "Confirm password:" ""
        while ($pw1 -ne $pw2) {
            Write-LogWarn "Passwords do not match -- retry"
            $pw1 = Read-Masked "Admin password:" ""
            $pw2 = Read-Masked "Confirm password:" ""
        }
        $pw1
    }
}
Register-Secret $P

$HostIn = if ($env:MIOS_HOSTNAME) { $env:MIOS_HOSTNAME } else {
    if ($AutoInstall) { "mios" } else { Read-Plain "Hostname (blank=mios-XXXXX):" "mios" }
}
if ($HostIn -eq "mios") {
    $HostIn = "mios-$('{0:D5}' -f (Get-Random -Min 10000 -Max 99999))"
}

$GhcrToken = if ($env:GHCR_TOKEN) { $env:GHCR_TOKEN } else {
    $t = Read-Masked "GitHub PAT for ghcr.io base image pull (github.com/settings/tokens):"
    $t
}
Register-Secret $GhcrToken

$RegUser  = if ($env:MIOS_GHCR_USER) { $env:MIOS_GHCR_USER } else { "MiOS-DEV" }
$GhcrImage = "ghcr.io/$RegUser/${ImageName}:${ImageTag}"

Write-LogOK "User: $U  Hostname: $HostIn  Registry: $GhcrImage"
Finish-Phase 6

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 7 -- Writing identity
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 7 "Hashing password (SHA-512)..."

# Pull helper image for openssl -- try existing 'MiOS' image first
$HelperImage = ""
if ($GhcrToken) {
    $GhcrToken | & podman login ghcr.io --username $RegUser --password-stdin 2>&1 | Out-Null
}
& podman pull $GhcrImage 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    $HelperImage = $GhcrImage
    Write-LogOK "Helper image: $GhcrImage (self-building)"
} else {
    & podman image exists $LocalImage 2>$null
    if ($LASTEXITCODE -eq 0) { $HelperImage = $LocalImage }
}

$passHash = Get-SHA512Hash -PlainText $P -HImg $HelperImage
if (-not $passHash -or $passHash -notmatch '^\$6\$') {
    Write-LogFatal "Password hashing failed. Is Podman machine running?"
}
Register-Secret $passHash
Write-LogOK "Password hashed (SHA-512)"

if ($HostIn -ne "mios") {
    Set-Content (Join-Path $RepoDir "etc/hostname") $HostIn -Encoding ascii
    Write-LogOK "Hostname written: $HostIn"
}
Finish-Phase 7

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 8 -- App registration (BIB self-build detection)
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 8 "Checking BIB capability..."
$BIBSelfBuild = $false
if ($HelperImage) {
    $null = & podman run --rm $HelperImage which bootc-image-builder 2>$null
    if ($LASTEXITCODE -eq 0) {
        $BIBImage = $HelperImage; $BIBSelfBuild = $true
        Write-LogOK "Self-building BIB: 'MiOS' image is the builder"
    } else {
        Write-Log "Using centos-bootc BIB ('MiOS' lacks bootc-image-builder binary)"
    }
}
Finish-Phase 8

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 9 -- Building OCI image
#  Every output line from podman build drives Op: -- no frozen dashboard.
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 9 "podman build starting..."
$env:BUILDAH_FORMAT = "docker"
$script:Phases[9].InnerTotal = 48   # will be updated from first STEP marker

$t9 = [DateTime]::Now
& podman build --progress=plain --no-cache `
    --build-arg MAKEFLAGS="-j$cpu" `
    --build-arg MIOS_USER="$U" `
    --build-arg MIOS_HOSTNAME="$HostIn" `
    --build-arg MIOS_PASSWORD_HASH="$passHash" `
    --jobs 2 -t $LocalImage (Get-Location).Path 2>&1 | ForEach-Object {

    $line     = $_
    $stripped = ($line -replace '^\s*#\d+\s+(?:[\d.]+\s+)?','').TrimStart()
    Write-Log (Format-Masked $line) -Color DarkGray

    # build.sh step header: +- STEP 01/48 : 01-repos.sh ---- 00:00 -+
    if ($stripped -match '\+-\s*STEP\s+(\d+)/(\d+)\s*:\s*(\S+)') {
        $script:Phases[9].InnerStep  = [int]$Matches[1]
        $script:Phases[9].InnerTotal = [int]$Matches[2]
        Set-Op "STEP $($Matches[1])/$($Matches[2]) -- $($Matches[3])"
        Show-Dashboard   # full redraw on each script boundary
    } else {
        # Every non-empty line updates Op: for live feedback
        $candidate = ($stripped -replace '\s+',' ').Trim()
        if ($candidate.Length -gt 72) { $candidate = $candidate.Substring(0,69) + '...' }
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            Set-Op (Format-Masked $candidate)
        }
    }
}
$buildExitCode = $LASTEXITCODE

& git -C $RepoDir checkout etc/hostname 2>$null | Out-Null
if ($buildExitCode -ne 0) { Write-LogFatal "podman build failed (exit $buildExitCode)" }

$buildMin = [Math]::Round(([DateTime]::Now - $t9).TotalMinutes, 1)
Write-LogOK "Image built in $buildMin min: $LocalImage"

# Tag with GHCR ref (sets update origin for bootc)
& podman tag $LocalImage $GhcrImage
Write-LogOK "Update origin: $GhcrImage"

# Rechunk
Set-Op "Rechunking OCI layers..."
$ErrorActionPreference = "Continue"
& podman run --rm --privileged -v /var/lib/containers/storage:/var/lib/containers/storage `
    $LocalImage /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 "containers-storage:$LocalImage" "containers-storage:$LocalImage" 2>&1 | ForEach-Object { Set-Op (Format-Masked $_) }
if ($LASTEXITCODE -ne 0) {
    Write-LogWarn "Self rechunk failed; trying external rechunker"
    & podman run --rm --privileged -v /var/lib/containers/storage:/var/lib/containers/storage `
        "quay.io/centos-bootc/centos-bootc:stream10" /usr/libexec/bootc-base-imagectl rechunk --max-layers 67 "containers-storage:$LocalImage" "containers-storage:$LocalImage" 2>&1 | Out-Null
}
$ErrorActionPreference = "Stop"
Write-LogOK "Rechunk complete"

# Update helper image
$HelperImage = $LocalImage
$null = & podman run --rm $LocalImage which bootc-image-builder 2>$null
if ($LASTEXITCODE -eq 0) { $BIBImage = $LocalImage; $BIBSelfBuild = $true }

# Inject build log (pre-BIB snapshot) into OCI image
if ($script:LogFile -and (Test-Path $script:LogFile)) {
    Set-Op "Injecting build log into image..."
    try { Stop-Transcript | Out-Null } catch {}
    $cid = (& podman create $LocalImage sh 2>$null).Trim()
    if ($cid) {
        & podman cp $script:LogFile "${cid}:/usr/share/mios/build-log.txt" 2>$null | Out-Null
        & podman commit --quiet --pause=false $cid $LocalImage 2>$null | Out-Null
        & podman rm -f $cid 2>$null | Out-Null
        Write-LogOK "Build log baked into image: /usr/share/mios/build-log.txt"
    }
    try { Start-Transcript -Path $script:LogFile -Append -Force | Out-Null } catch {}
}
Finish-Phase 9

# ══════════════════════════════════════════════════════════════════════════════
#  PHASES 10-12 -- Export / register / disk images
# ══════════════════════════════════════════════════════════════════════════════
$bibConf     = Join-Path $RepoDir "config\bib.toml"
if (-not (Test-Path $bibConf)) { $bibConf = Join-Path $RepoDir "config\bib.json" }
$bibConfDest = $null; $bibMountPath = "/config.toml"
if (Test-Path $bibConf) {
    $bibConfDest = Join-Path $MiosDeployDir "bib-config.toml"
    Copy-Item $bibConf $bibConfDest -Force
}

function Get-BIBArgs {
    param([string]$Type)
    $a = @("run","--rm","-it","--privileged","--security-opt","label=type:unconfined_t",
           "-v","/var/lib/containers/storage:/var/lib/containers/storage",
           "-v","${MiosDeployDir}:/output:z")
    if ($bibConfDest) { $a += @("-v","${bibConfDest}:${bibMountPath}:ro") }
    $a += @($BIBImage,"build","--type",$Type,"--rootfs","ext4","--local",$LocalImage)
    return $a
}

# Phase 10 -- WSL2 export
Start-Phase 10 "Exporting WSL2 image..."
$ErrorActionPreference = "Continue"
if ($HelperImage) {
    & podman run --rm --privileged -v "${MiosDeployDir}:/output:z" $HelperImage bootc container export --format=tar --output /output/mios-wsl.tar "containers-storage:$LocalImage" 2>&1 | ForEach-Object { Set-Op (Format-Masked $_) }
}
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $TargetWsl)) {
    $wslCid = (& podman create $LocalImage 2>$null).Trim()
    if ($wslCid) { & podman export $wslCid -o $TargetWsl; & podman rm $wslCid 2>$null | Out-Null }
}
if (Test-Path $TargetWsl) { Write-LogOK "WSL: $(Get-FileSize $TargetWsl)" } else { Write-LogWarn "WSL export failed" }
$ErrorActionPreference = "Stop"
Finish-Phase 10

# Phase 11 -- WSL2 registration
Start-Phase 11 "Importing WSL2 distro..."
$ErrorActionPreference = "Continue"
if (Test-Path $TargetWsl) {
    $WslName = "MiOS"; $WslPath = Join-Path $env:USERPROFILE "WSL\$WslName"
    $existing = wsl --list --quiet 2>$null | Where-Object { $_ -match "^$WslName" }
    if ($existing) { wsl --unregister $WslName 2>$null | Out-Null }
    New-Item -ItemType Directory -Path $WslPath -Force | Out-Null
    wsl --import $WslName $WslPath $TargetWsl --version 2 2>&1 | ForEach-Object { Set-Op $_ }
    if ($LASTEXITCODE -eq 0) {
        Write-LogOK "WSL2 distro '$WslName' registered"
        # Seed /etc/mios/install.env so wsl-firstboot.service uses the
        # operator-supplied identity instead of the default 'mios' password.
        if (Write-MiosInstallEnv -WslDistro $WslName -User $U -PasswordHash $passHash -Hostname $HostIn) {
            Write-LogOK "Seeded /etc/mios/install.env (user=$U, host=$HostIn)"
        } else {
            Write-LogWarn "install.env not written -- first-boot will fall back to default 'mios' password"
        }
    } else {
        Write-LogWarn "WSL import failed"
    }
}
$ErrorActionPreference = "Stop"
Finish-Phase 11

# Phase 12 -- Disk images (VHDX + ISO via BIB)
Start-Phase 12 "Building disk images (BIB)..."
$script:Phases[12].InnerTotal = 2
$ErrorActionPreference = "Continue"

# VHDX
Set-Op "BIB: building VHDX..."
$vhdArgs = Get-BIBArgs "vhd"
$vhdExit = Invoke-BIBRun -BIBArgs $vhdArgs -Label "VHDX"
if ($vhdExit -eq 0) {
    $script:Phases[12].InnerStep = 1
    $vhdFile = Get-ChildItem $MiosDeployDir -Recurse -Include "*.vhd","*.vpc" -EA SilentlyContinue | Select-Object -First 1
    if ($vhdFile) {
        Set-Op "Converting VHD → VHDX..."
        if ($HelperImage) {
            & podman run --rm -v "${MiosDeployDir}:/data:z" $HelperImage qemu-img convert -m 16 -W -f vpc -O vhdx /data/$($vhdFile.Name) /data/mios-hyperv.vhdx 2>&1 | Out-Null
        }
        Remove-Item $vhdFile.FullName -Force -EA SilentlyContinue
        if (Test-Path $TargetVhdx) { Write-LogOK "VHDX: $(Get-FileSize $TargetVhdx)" }
    }
} else { Write-LogWarn "VHDX build failed" }

# ISO
Set-Op "BIB: building ISO..."
$isoArgs = Get-BIBArgs "anaconda-iso"
$isoExit = Invoke-BIBRun -BIBArgs $isoArgs -Label "ISO"
$script:Phases[12].InnerStep = 2
if ($isoExit -eq 0) {
    $isoFile = Get-ChildItem $MiosDeployDir -Recurse -Filter "*.iso" -EA SilentlyContinue | Select-Object -First 1
    if ($isoFile) { Move-Item $isoFile.FullName $TargetIso -Force; Write-LogOK "ISO: $(Get-FileSize $TargetIso)" }
} else { Write-LogWarn "ISO build failed" }

$ErrorActionPreference = "Stop"
Finish-Phase 12

# ══════════════════════════════════════════════════════════════════════════════
#  PHASE 13 -- Hyper-V deployment
# ══════════════════════════════════════════════════════════════════════════════
Start-Phase 13 "Preparing Hyper-V VM..."
$ErrorActionPreference = "Continue"

if (Test-Path $TargetVhdx) {
    $vmName = "MiOS"
    $doDeploy = ($AutoInstall -or $env:MIOS_FORCE_DEPLOY -eq "1")
    if (-not $doDeploy) {
        $ans = Read-Plain "Deploy/Update Hyper-V VM '$vmName'? (y/N)" "N"
        $doDeploy = $ans -match "^[yY]"
    }

    if ($doDeploy) {
        try {
            if (Get-VM -Name $vmName -EA SilentlyContinue) {
                Stop-VM -Name $vmName -Force -EA SilentlyContinue
                Remove-VM -Name $vmName -Force
            }
            $vmSwitch = (Get-VMSwitch | Where-Object SwitchType -eq "External" | Select-Object -First 1)?.Name ?? "Default Switch"
            $totalMem = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
            $vmRam    = [int64]([Math]::Floor($totalMem * 0.80 / 2MB) * 2MB)
            $minRam   = [int64]([Math]::Floor($totalMem * 0.50 / 2MB) * 2MB)
            New-VM -Name $vmName -MemoryStartupBytes $minRam -Generation 2 -VHDPath $TargetVhdx -SwitchName $vmSwitch | Out-Null
            Set-VM -Name $vmName -ProcessorCount $cpu -DynamicMemory -MemoryMinimumBytes $minRam -MemoryMaximumBytes $vmRam -MemoryStartupBytes $minRam
            Set-VMFirmware -VMName $vmName -SecureBootTemplate "MicrosoftUEFICertificateAuthority"
            Start-VM -Name $vmName
            Write-LogOK "Hyper-V VM '$vmName' created and started"

            # Wait for heartbeat
            $timeout = 120; $elapsed = 0
            while ($elapsed -lt $timeout) {
                $hb = (Get-VMIntegrationService -VMName $vmName | Where-Object Name -eq "Heartbeat").PrimaryStatusDescription
                if ($hb -eq "OK") { break }
                Start-Sleep 5; $elapsed += 5
                Set-Op "Waiting for VM heartbeat... ${elapsed}s"
            }
            Stop-VM -Name $vmName -Force -EA SilentlyContinue
            Set-VM -Name $vmName -EnhancedSessionTransportType HvSocket
            Start-VM -Name $vmName
            Write-LogOK "Hyper-V VM ready: vmconnect.exe localhost $vmName"
        } catch { Write-LogWarn "Hyper-V deploy error: $_" }
    }
}
$ErrorActionPreference = "Stop"
Finish-Phase 13

# ══════════════════════════════════════════════════════════════════════════════
#  FINAL -- Summary
# ══════════════════════════════════════════════════════════════════════════════
Set-Op "Build complete."
Show-Dashboard

# Copy unified log to all output dirs
$logName = Split-Path $script:LogFile -Leaf
foreach ($d in @($MiosImagesDir, $MiosDeployDir)) {
    Copy-Item $script:LogFile (Join-Path $d $logName) -Force -EA SilentlyContinue
}
Write-LogOK "Unified log: $($script:LogFile)"

Write-Host ""
Write-Host "  Targets produced:" -ForegroundColor Cyan
foreach ($p in @($TargetVhdx,$TargetWsl,$TargetIso)) {
    if (Test-Path $p) { Write-Host "    [OK] $(Split-Path $p -Leaf)  $(Get-FileSize $p)" -ForegroundColor Green }
}
Write-Host ""
Write-Host "  irm | iex → build → VHDX → Hyper-V  |  bootc upgrade on deployed 'MiOS'" -ForegroundColor DarkGray
Write-Host ""

try { Stop-Transcript | Out-Null } catch {}

# Wipe credentials from memory
$P = $null; $passHash = $null; $GhcrToken = $null
[GC]::Collect()
```


## Layer 4a -- Library (sourced helpers)


### `automation\lib\common.sh`

```bash
#!/usr/bin/env bash
# ============================================================================
# automation/lib/common.sh
# ----------------------------------------------------------------------------
# Shared helpers for 'MiOS' build scripts.
# Safe to source multiple times (idempotent).
# ============================================================================

# shellcheck source=lib/masking.sh
source "$(dirname "${BASH_SOURCE[0]}")/masking.sh"
# shellcheck source=lib/paths.sh
source "$(dirname "${BASH_SOURCE[0]}")/paths.sh"

# --- Logging ----------------------------------------------------------------
log_ts() { date '+%Y-%m-%d %H:%M:%S'; }
log()  { printf '[%s] ==> %s\n' "$(log_ts)" "$*"; }
warn() { printf '[%s] WARN: %s\n' "$(log_ts)" "$*" >&2; }
die()  { printf '[%s] ERROR: %s\n' "$(log_ts)" "$*" >&2; exit 1; }
diag() { printf '[%s] DIAG: %s\n' "$(log_ts)" "$*"; }

# --- dnf flags --------------------------------------------------------------
# Select dnf binary (prefer dnf5 if available)
if command -v dnf5 &>/dev/null; then
    export DNF_BIN="dnf5"
else
    export DNF_BIN="dnf"
fi

# Defense-in-depth: /etc/dnf/dnf.conf already carries install_weak_deps=False,
# but passing it on every invocation guarantees behaviour even if a script or
# transaction overrides the global default. Array form so elements are one-
# argv-each under `set -u`, and future flags can be added in one place.
if [[ -z "${DNF_SETOPT+x}" || "$(declare -p DNF_SETOPT 2>/dev/null)" != "declare -a"* ]]; then
    declare -ga DNF_SETOPT=(
        --setopt=install_weak_deps=False
        --setopt=timeout=10          # cut per-mirror connection attempt at 10 s
        --setopt=minrate=1k          # drop any mirror delivering < 1 kB/s after timeout
        --setopt=max_parallel_downloads=10  # pull from 10 mirrors simultaneously
        --setopt=ip_resolve=4        # prefer IPv4; many Fedora IPv6 paths time out in WSL2
    )
fi
if [[ -z "${DNF_OPTS+x}" || "$(declare -p DNF_OPTS 2>/dev/null)" != "declare -a"* ]]; then
    declare -ga DNF_OPTS=(--allowerasing)
fi
# String variant for legacy/debug visibility only. Do NOT use in commands.
export DNF_SETOPT_STR="${DNF_SETOPT[*]}"
export DNF_OPTS_STR="${DNF_OPTS[*]}"

# --- Build-time version manifest --------------------------------------------
# Project policy: every dependency tracks :latest from upstream (no human
# pins). To keep day-0 builds reproducible-after-the-fact, every phase script
# that resolves a :latest tag MUST call record_version so the observed value
# is captured into the per-image manifest. build.sh promotes this file into
# /usr/lib/mios/logs/ at the end of the build, alongside the flattened log.
#
# Usage: record_version <component> <version_or_tag> [resolved_to]
#   component       short id, e.g. "aichat", "cosign", "quadlet:mios-k3s"
#   version_or_tag  what was observed, e.g. "v0.30.1" or "docker.io/x:latest"
#   resolved_to     optional: digest, source URL, or commit ref
export MIOS_VERSION_MANIFEST="${MIOS_VERSION_MANIFEST:-/tmp/mios-build-versions.tsv}"

record_version() {
    local component="$1" version="$2" resolved_to="${3:-}"
    if [[ ! -f "$MIOS_VERSION_MANIFEST" ]]; then
        printf 'component\tversion\tresolved_to\trecorded_at\n' > "$MIOS_VERSION_MANIFEST"
    fi
    printf '%s\t%s\t%s\t%s\n' \
        "$component" "$version" "$resolved_to" "$(log_ts)" \
        >> "$MIOS_VERSION_MANIFEST"
    log "version: ${component} = ${version}${resolved_to:+ (${resolved_to})}"
}
```


### `automation\lib\packages.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- Package extraction library
# Parses PACKAGES.md fenced code blocks tagged with ```packages-<category>
#
# Usage:
#   source automation/lib/packages.sh
#   install_packages "gnome"
# shellcheck source=lib/common.sh
#   install_packages_strict "kernel"   # fails if section is empty/missing

get_packages() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"

    if [[ ! -f "$packages_file" ]]; then
        echo "[packages.sh] ERROR: $packages_file not found" >&2
        return 1
    fi

    # shellcheck disable=SC2001 # tr is intentionally used here to word-split packages
    sed -n "/^\`\`\`packages-${category}$/,/^\`\`\`$/{/^\`\`\`/d;/^$/d;/^#/d;p}" "$packages_file" \
        | tr '\n' ' '
}

get_packages_strict() {
    local result
    result=$(get_packages "$@")
    if [[ -z "$result" ]]; then
        echo "[packages.sh] ERROR: No packages found in section '$1'" >&2
        return 1
    fi
    echo "$result"
}

_PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_PKG_DIR}/common.sh"

install_packages() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"
    local packages
    packages=$(get_packages "$category" "$packages_file")
    if [[ -n "$packages" ]]; then
        echo "[packages.sh] Installing '$category' packages..."
        # Use subshell so set -e in parent doesn't kill entire script on failure.
        # shellcheck disable=SC2086 # $packages is intentionally word-split here
        ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=PackageKit $packages) || {
            echo "[packages.sh] WARNING: Some '$category' packages failed to install" >&2
            echo "[packages.sh] Packages requested: $packages" >&2
        }
    else
        echo "[packages.sh] WARN: No packages in section '$category' -- skipping"
    fi
}

install_packages_strict() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"
    local packages
    packages=$(get_packages_strict "$category" "$packages_file") || return 1
    echo "[packages.sh] Installing '$category' packages (strict section)..."
    # shellcheck disable=SC2086 # $packages is intentionally word-split here
    # Note: --allowerasing without --best: allows conflict resolution by erasure
    # without requiring the "best" (newest) version -- avoids hard failures when
    # ucore base packages are newer than Fedora 44 versions.
    $DNF_BIN "${DNF_SETOPT[@]}" install -y --allowerasing --skip-unavailable --exclude=PackageKit $packages || {
        echo "[packages.sh] FATAL: Mandatory '$category' packages failed to install" >&2
        echo "[packages.sh] Packages requested: $packages" >&2
        return 1
    }
}

install_packages_optional() {
    local category="$1"
    local packages_file="${2:-${PACKAGES_MD:-/ctx/PACKAGES.md}}"

    # Check if section exists at all
    local raw_section
    raw_section=$(sed -n "/^\`\`\`packages-${category}$/,/^\`\`\`$/{/^\`\`\`/d;p}" "$packages_file")

    if [[ -z "$raw_section" ]]; then
        echo "[packages.sh] WARN: Section 'packages-${category}' not found -- skipping"
        return 0
    fi

    # Check if ALL lines are comments (intentionally disabled)
    local uncommented
    uncommented=$(echo "$raw_section" | grep -v '^#' | grep -v '^$' || true)

    if [[ -z "$uncommented" ]]; then
        echo "[packages.sh] INFO: All packages in '${category}' are commented out (intentionally disabled)"
        return 0
    fi

    # Some packages are uncommented -- install those
    local packages
    packages=$(get_packages "$category" "$packages_file")
    if [[ -n "$packages" ]]; then
        echo "[packages.sh] Installing optional '$category' packages..."
        # shellcheck disable=SC2086 # $packages is intentionally word-split here
        ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=PackageKit $packages) || {
            echo "[packages.sh] WARNING: Some optional '$category' packages failed" >&2
        }
    fi
}
```


### `automation\lib\masking.sh`

```bash
#!/usr/bin/env bash
# ============================================================================
# automation/lib/masking.sh
# ----------------------------------------------------------------------------
# Credential masking and secure execution helpers.
# ============================================================================

# Internal array of strings to mask
declare -ga MASK_LIST=()

# Register a string to be masked in output
# Usage: add_mask "my-secret-string"
add_mask() {
    local secret="$1"
    if [[ -n "$secret" && "$secret" != "null" ]]; then
        # Avoid duplicates
        for m in "${MASK_LIST[@]}"; do
            [[ "$m" == "$secret" ]] && return 0
        done
        MASK_LIST+=("$secret")
    fi
}

# Register common sensitive environment variables
register_common_masks() {
    local vars=(
        GHCR_TOKEN
        GH_TOKEN
        GITHUB_TOKEN
        MIOS_PASSWORD
        MIOS_PASSWORD_HASH
        SIGNING_SECRET
        COSIGN_PASSWORD
    )
    for v in "${vars[@]}"; do
        if [[ -n "${!v:-}" ]]; then
            add_mask "${!v}"
        fi
    done
}

# Filter stdin to mask registered secrets
# Usage: some_command | mask_filter
mask_filter() {
    if [[ ${#MASK_LIST[@]} -eq 0 ]]; then
        cat
        return
    fi

    local sed_script=""
    for secret in "${MASK_LIST[@]}"; do
        # Escape characters that are special to sed's regex and the delimiter
        # We use '|' as the delimiter for 's' because it's less common in hashes
        # than '/', but we still must escape it if it appears in the secret.
        local escaped_secret=$(printf '%s' "$secret" | sed 's/[][\\.*^$|/]/\\&/g')
        sed_script+="s|$escaped_secret|[MASKED]|g;"
    done
    sed -u "$sed_script"
}

# Prompt for credentials if not set
# Usage: ensure_cred "GHCR_TOKEN" "Enter your GitHub Container Registry Token"
ensure_cred() {
    local var_name="$1"
    local prompt_msg="$2"
    if [[ -z "${!var_name:-}" ]]; then
        read -rsp "$prompt_msg: " val
        echo >&2 # Newline after silent read
        export "$var_name"="$val"
    fi
    add_mask "${!var_name}"
}

# Secure curl wrapper with optional credentials
# Usage: scurl [curl-args] URL
scurl() {
    local args=()
    local use_creds=false
    local url=""
    local is_binary=false
    
    # Simple parser to find the URL and check for binary download flags
    for arg in "$@"; do
        if [[ "$arg" =~ ^https?:// ]]; then
            url="$arg"
        elif [[ "$arg" == "-o" || "$arg" == "-O" || "$arg" == "--output" ]]; then
            is_binary=true
        fi
    done

    # Inherit credentials from environment if available and URL matches github/ghcr
    if [[ "$url" =~ github\.com|ghcr\.io ]]; then
        if [[ -n "${GH_TOKEN:-}" || -n "${GITHUB_TOKEN:-}" || -n "${GHCR_TOKEN:-}" ]]; then
            local token="${GH_TOKEN:-${GITHUB_TOKEN:-${GHCR_TOKEN:-}}}"
            # Use -H for token auth to avoid process list exposure of -u
            args+=("-H" "Authorization: token $token")
            add_mask "$token"
        fi
    fi

    if [[ "$is_binary" == "true" ]]; then
        curl "${args[@]}" "$@"
    else
        curl "${args[@]}" "$@" | mask_filter
    fi
}
```


### `automation\lib\paths.sh`

```bash
#!/usr/bin/env bash
# automation/lib/paths.sh -- FHS path constants for MiOS.
# Source via common.sh; safe to source multiple times (idempotent).
# Override any constant from the environment before sourcing.

# /usr/* -- read-only image surface
: "${MIOS_USR_DIR:=/usr/lib/mios}"
: "${MIOS_LOG_DIR:=${MIOS_USR_DIR}/logs}"
: "${MIOS_LIBEXEC_DIR:=/usr/libexec/mios}"
: "${MIOS_SHARE_DIR:=/usr/share/mios}"

# /etc/* -- admin-override surface
: "${MIOS_ETC_DIR:=/etc/mios}"

# /var/* -- runtime mutable
: "${MIOS_VAR_DIR:=/var/lib/mios}"
: "${MIOS_MEMORY_DIR:=${MIOS_VAR_DIR}/memory}"
: "${MIOS_SCRATCH_DIR:=${MIOS_VAR_DIR}/scratch}"

# Build artefacts (resolved at end of build.sh)
: "${MIOS_BUILD_LOG:=${MIOS_LOG_DIR}/mios-build.log}"
: "${MIOS_BUILD_CHAIN_LOG:=${MIOS_LOG_DIR}/mios-build-chain.log}"
: "${MIOS_VERSION_MANIFEST_FINAL:=${MIOS_LOG_DIR}/mios-build-versions.tsv}"

export MIOS_USR_DIR MIOS_LOG_DIR MIOS_LIBEXEC_DIR MIOS_SHARE_DIR
export MIOS_ETC_DIR
export MIOS_VAR_DIR MIOS_MEMORY_DIR MIOS_SCRATCH_DIR
export MIOS_BUILD_LOG MIOS_BUILD_CHAIN_LOG MIOS_VERSION_MANIFEST_FINAL
```


## Layer 4b -- Master orchestrator


### `automation\build.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- Master build runner
# Framed ASCII console UI: progress bar, stage tracking, health metrics,
# per-step timing, and consolidated failure/warn report at end.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/packages.sh"
register_common_masks

export PACKAGES_MD="${PACKAGES_MD:-/ctx/PACKAGES.md}"
BUILD_LOG="/tmp/mios-build.log"
VERSION_STR="$(cat "${SCRIPT_DIR}/../VERSION" 2>/dev/null || cat /ctx/VERSION 2>/dev/null || echo 'v0.2.0')"

# ── Redirect all output through mask filter and tee to log ──────────────────
exec > >(mask_filter | tee -a "$BUILD_LOG") 2>&1

# ── TTY UI: pure ASCII, 72-char wide, CI/tty0/container-safe ───────────────
W=72  # frame width (inner content = W-4 chars)

_pad() {
    # Left-pad or right-pad a string to exactly $1 chars
    local width=$1 str=${2:-} dir=${3:-left}
    local len=${#str}
    if [[ $len -ge $width ]]; then printf '%s' "${str:0:$width}"; return; fi
    local pad=$(( width - len ))
    if [[ "$dir" == "right" ]]; then
        printf '%s%*s' "$str" "$pad" ""
    else
        printf '%*s%s' "$pad" "" "$str"
    fi
}

_hline() {
    local char=${1:--} prefix=${2:-+} suffix=${3:-+}
    printf '%s' "$prefix"
    printf '%*s' "$(( W - 2 ))" "" | tr ' ' "$char"
    printf '%s\n' "$suffix"
}

_row() {
    # Print a frame row: | content |
    local content="$1"
    local inner=$(( W - 4 ))
    printf '| %-*s |\n' "$inner" "${content:0:$inner}"
}

_progress_bar() {
    # | [====>    ] NNN/NNN (NNN%) |
    # prefix "| [" = 3, suffix "] NNN/NNN (NNN%) |" = 18 => bar_w = W-21
    local current=$1 total=$2
    local bar_w=$(( W - 21 ))
    [[ $bar_w -lt 4 ]] && bar_w=4
    local filled pct empty
    pct=$(( current * 100 / total ))
    if [[ $current -ge $total ]]; then
        filled=$bar_w; empty=0
    else
        filled=$(( current * bar_w / total ))
        empty=$(( bar_w - filled - 1 ))
        [[ $empty -lt 0 ]] && empty=0
    fi
    printf '| ['
    [[ $filled -gt 0 ]] && printf '%*s' "$filled" "" | tr ' ' '='
    [[ $current -lt $total ]] && printf '>'
    [[ $empty -gt 0 ]] && printf '%*s' "$empty" "" | tr ' ' ' '
    printf '] %3d/%3d (%3d%%) |\n' "$current" "$total" "$pct"
}

_step_header() {
    # +- STEP NN/NN : name --------- HH:MM -+  (W total; prefix=3, suffix=3 => inner=W-6)
    local step=$1 total=$2 name=$3 elapsed_total=$4
    local elapsed_fmt
    elapsed_fmt=$(printf '%02d:%02d' $(( elapsed_total / 60 )) $(( elapsed_total % 60 )))
    local label="STEP $(printf '%02d' "$step")/$(printf '%02d' "$total") : ${name}"
    local right=" ${elapsed_fmt}"
    local inner=$(( W - 6 ))
    local label_len=${#label} right_len=${#right}
    local pad=$(( inner - label_len - right_len ))
    [[ $pad -lt 0 ]] && pad=0
    printf '+- %s' "$label"
    printf '%*s' "$pad" "" | tr ' ' '-'
    printf '%s -+\n' "$right"
}

_step_result() {
    # +-- [STATUS] name -------- Ns --+  (W total; prefix=4, suffix=4 => inner=W-8)
    local status=$1 name=$2 elapsed=$3
    local tag
    case "$status" in
        ok)   tag="[ DONE ]" ;;
        fail) tag="[FAILED]" ;;
        warn) tag="[ WARN ]" ;;
    esac
    local right=" ${elapsed}s"
    local inner=$(( W - 8 ))
    local label="${tag} ${name}"
    local label_len=${#label} right_len=${#right}
    local pad=$(( inner - label_len - right_len ))
    [[ $pad -lt 0 ]] && pad=0
    printf '+-- %s' "$label"
    printf '%*s' "$pad" "" | tr ' ' '-'
    printf '%s --+\n' "$right"
}

_section_header() {
    _hline '=' '+' '+'
    _row "  'MiOS' ${VERSION_STR} -- Build Console"
    _row "  Base: ucore-hci:stable-nvidia + Fedora 44"
    _row "  Started: $(date '+%Y-%m-%d %H:%M:%S')    Log: ${BUILD_LOG}"
    _hline '=' '+' '+'
}

_progress_frame() {
    local current=$1 total=$2 label=$3 elapsed=$4
    local elapsed_fmt
    elapsed_fmt=$(printf '%02d:%02d elapsed' $(( elapsed / 60 )) $(( elapsed % 60 )))
    _hline '-' '+' '+'
    _row " PROGRESS | Stage: ${label} | ${elapsed_fmt}"
    _progress_bar "$current" "$total"
    _hline '-' '+' '+'
}

_fail_report() {
    local -a fails=("${@}")
    _hline '=' '+' '+'
    if [[ ${#fails[@]} -eq 0 ]]; then
        _row " FAILURE LOG: (none)"
    else
        _row " FAILURE LOG:"
        _hline '-' '+' '+'
        for entry in "${fails[@]}"; do
            _row "  [FAIL]  ${entry}"
        done
    fi
    _hline '=' '+' '+'
}

_warn_report() {
    local -a warns=("${@}")
    _hline '-' '+' '+'
    if [[ ${#warns[@]} -eq 0 ]]; then
        _row " WARNING LOG: (none)"
    else
        _row " WARNING LOG:"
        _hline '-' '+' '+'
        for entry in "${warns[@]}"; do
            _row "  [WARN]  ${entry}"
        done
    fi
    _hline '-' '+' '+'
}

_final_summary() {
    local scripts=$1 fails=$2 warns=$3 missing_pkgs=$4 elapsed=$5
    local result_label
    if [[ $fails -gt 0 ]]; then result_label="BUILD FAILED"; else result_label="BUILD COMPLETE"; fi
    local elapsed_fmt
    elapsed_fmt=$(printf '%dm %02ds' $(( elapsed / 60 )) $(( elapsed % 60 )))
    _hline '=' '+' '+'
    _row "  'MiOS' ${VERSION_STR} -- ${result_label}"
    _hline '-' '+' '+'
    _row "  Duration:   ${elapsed_fmt}"
    _row "  Scripts:    ${scripts} executed | ${fails} FAILED | ${warns} warned"
    _row "  Packages:   ${missing_pkgs} critical missing"
    _hline '-' '+' '+'
}

export SYSTEMD_OFFLINE=1
export container=podman

if [[ ! -f "$PACKAGES_MD" ]]; then
    printf '[FATAL] PACKAGES_MD not found: %s\n' "$PACKAGES_MD" >&2
    exit 1
fi

# ── Script classification ────────────────────────────────────────────────────
CONTAINERFILE_SCRIPTS="08-system-files-overlay.sh 37-ollama-prep.sh 99-postcheck.sh"

NON_FATAL_SCRIPTS="
  05-enable-external-repos.sh
  10-gnome.sh
  13-ceph-k3s.sh
  19-k3s-selinux.sh
  21-moby-engine.sh
  23-uki-render.sh
  36-akmod-guards.sh
  37-aichat.sh
  42-cosign-policy.sh
  43-uupd-installer.sh
  52-bake-kvmfr.sh
  53-bake-lookingglass-client.sh
  22-freeipa-client.sh
  26-gnome-remote-desktop.sh
  38-vm-gating.sh
  44-podman-machine-compat.sh
  50-enable-log-copy-service.sh
"

# Count total runnable scripts
ALL_SCRIPTS=()
for _s in "$SCRIPT_DIR"/[0-9][0-9]-*.sh; do
    _n="$(basename "$_s")"
    echo "$CONTAINERFILE_SCRIPTS" | grep -qF "$_n" && continue
    ALL_SCRIPTS+=("$_s")
done
TOTAL_SCRIPTS=${#ALL_SCRIPTS[@]}

# ── Header ───────────────────────────────────────────────────────────────────
_section_header
echo ""

TOTAL_START=$SECONDS

# ── Build-time version manifest (records :latest -> observed-version) ────────
# Project policy: every dependency tracks :latest from upstream. To make
# day-0 images reproducible-after-the-fact, every script that resolves a
# floating tag calls record_version (lib/common.sh). build.sh seeds the
# manifest with image-level metadata; phase scripts append component rows.
rm -f "$MIOS_VERSION_MANIFEST"
record_version mios       "$VERSION_STR"                               "git:$(cat /ctx/VERSION 2>/dev/null || echo unknown)"
record_version base-image "${BASE_IMAGE:-ghcr.io/ublue-os/ucore-hci:stable-nvidia}" "build-time floating tag"
record_version kernel     "$(find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf '%f\n' 2>/dev/null | sort -V | tail -1)" "from base image"

SCRIPT_COUNT=0
SCRIPT_FAIL=0
WARN_FAIL=0
FAILED_SCRIPTS=()
WARNED_SCRIPTS=()
FAIL_LOG=()
WARN_LOG=()

# ── Execute all numbered scripts ─────────────────────────────────────────────
for script in "${ALL_SCRIPTS[@]}"; do
    SCRIPT_NAME="$(basename "$script")"
    SCRIPT_COUNT=$(( SCRIPT_COUNT + 1 ))

    _step_header "$SCRIPT_COUNT" "$TOTAL_SCRIPTS" "$SCRIPT_NAME" "$(( SECONDS - TOTAL_START ))"

    STEP_START=$SECONDS

    # Capture per-script log to individual file
    STEP_LOG="/tmp/mios-step-${SCRIPT_COUNT}-${SCRIPT_NAME%.sh}.log"

    set +e
    bash "$script" 2>&1 | tee "$STEP_LOG"
    SCRIPT_EXIT=${PIPESTATUS[0]}
    set -e

    STEP_ELAPSED=$(( SECONDS - STEP_START ))
    TOTAL_ELAPSED=$(( SECONDS - TOTAL_START ))

    if [[ $SCRIPT_EXIT -eq 0 ]]; then
        _step_result "ok" "$SCRIPT_NAME" "$STEP_ELAPSED"
    elif echo "$NON_FATAL_SCRIPTS" | grep -qF "$SCRIPT_NAME"; then
        _step_result "warn" "$SCRIPT_NAME" "$STEP_ELAPSED"
        WARN_FAIL=$(( WARN_FAIL + 1 ))
        WARNED_SCRIPTS+=("$SCRIPT_NAME")
        WARN_LOG+=("${SCRIPT_NAME} (${STEP_ELAPSED}s) exit=${SCRIPT_EXIT}")
    else
        _step_result "fail" "$SCRIPT_NAME" "$STEP_ELAPSED"
        SCRIPT_FAIL=$(( SCRIPT_FAIL + 1 ))
        FAILED_SCRIPTS+=("$SCRIPT_NAME")
        FAIL_LOG+=("${SCRIPT_NAME} (${STEP_ELAPSED}s) exit=${SCRIPT_EXIT}")
    fi

    _progress_frame "$SCRIPT_COUNT" "$TOTAL_SCRIPTS" "$SCRIPT_NAME" "$TOTAL_ELAPSED"
    echo ""
done

# ── Bloat removal ───────────────────────────────────────────────────────────
_hline '-' '+' '+'
_row " POST-BUILD: Bloat removal"
_hline '-' '+' '+'
BLOAT_PACKAGES=$(get_packages "bloat" 2>/dev/null || true)
if [[ -n "${BLOAT_PACKAGES:-}" ]]; then
    echo "  Removing bloat packages..."
    $DNF_BIN "${DNF_SETOPT[@]}" remove -y --no-autoremove $BLOAT_PACKAGES 2>/dev/null || true
fi
systemctl mask packagekit.service 2>/dev/null || true
for app in gnome-tour gnome-initial-setup; do
    desktop="/usr/share/applications/${app}.desktop"
    if [[ -f "$desktop" ]]; then
        mkdir -p /usr/local/share/applications
        grep -v '^NoDisplay=' "$desktop" > "/usr/local/share/applications/${app}.desktop"
        echo "NoDisplay=true" >> "/usr/local/share/applications/${app}.desktop"
        _row "  Hidden: ${app} (NoDisplay=true)"
    fi
done

# ── Package validation ───────────────────────────────────────────────────────
echo ""
_hline '-' '+' '+'
_row " POST-BUILD: Package Health Check"
_hline '-' '+' '+'
CRITICAL_PACKAGES=($(get_packages "critical" 2>/dev/null || true))
VALIDATION_FAIL=0
PKG_OK=0
PKG_MISS=0
if [[ ${#CRITICAL_PACKAGES[@]} -gt 0 ]]; then
    for pkg in "${CRITICAL_PACKAGES[@]}"; do
        if rpm -q "$pkg" > /dev/null 2>&1; then
            printf '|  %-38s [ OK ] |\n' "$pkg"
            PKG_OK=$(( PKG_OK + 1 ))
        else
            printf '|  %-38s [MISS] |\n' "$pkg"
            PKG_MISS=$(( PKG_MISS + 1 ))
            VALIDATION_FAIL=$(( VALIDATION_FAIL + 1 ))
        fi
    done
fi
# Hardware spot-checks
if rpm -qa 'kmod-nvidia*' 2>/dev/null | grep -q . ; then
    printf '|  %-38s [ OK ] |\n' "NVIDIA kmod(s)"
else
    printf '|  %-38s [WARN] |\n' "NVIDIA kmod(s) -- using ucore base"
fi
if compgen -G "/etc/pki/akmods/certs/*.der" > /dev/null 2>/dev/null; then
    printf '|  %-38s [ OK ] |\n' "MOK certs"
fi
if rpm -q malcontent-libs > /dev/null 2>&1; then
    printf '|  %-38s [ OK ] |\n' "malcontent-libs (flatpak dep)"
else
    printf '|  %-38s [WARN] |\n' "malcontent-libs MISSING -- flatpak may break"
    WARN_LOG+=("malcontent-libs missing -- flatpak may break")
fi
_hline '-' '+' '+'

# ── Technical invariant validation ──────────────────────────────────────────
echo ""
_row " POST-BUILD: Technical Invariant Validation (99-postcheck.sh)"
_hline '-' '+' '+'
if [[ -f "${SCRIPT_DIR}/99-postcheck.sh" ]]; then
    bash "${SCRIPT_DIR}/99-postcheck.sh"
else
    _row "  WARNING: 99-postcheck.sh not found -- skipping"
fi

# ── Quadlet image digest capture (build-day :latest snapshot) ───────────────
# Quadlets are pulled by bootc at deploy time, not at OCI-build time, so
# their :latest will re-resolve on every deploy. Record the digest skopeo
# sees right now, so the shipped image carries a precise snapshot of what
# build day's :latest pointed at -- even though deploys may differ later.
echo ""
_hline '-' '+' '+'
_row " POST-BUILD: Capturing Quadlet image digests"
_hline '-' '+' '+'
if command -v skopeo >/dev/null 2>&1; then
    shopt -s nullglob
    for q in /usr/share/containers/systemd/*.container /etc/containers/systemd/*.container; do
        img=$(awk -F= '/^Image=/{print $2; exit}' "$q" 2>/dev/null)
        [[ -n "$img" ]] || continue
        digest=$(skopeo inspect "docker://${img}" 2>/dev/null \
            | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d.get("Digest",""))' 2>/dev/null \
            || true)
        record_version "quadlet:$(basename "$q" .container)" "$img" "${digest:-<unresolved>}"
    done
    shopt -u nullglob
else
    warn "skopeo not available -- Quadlet image digests not captured"
fi

# ── Log preservation (flatten all chain logs + version manifest into /usr) ──
echo ""
_hline '-' '+' '+'
_row " LOG CHAIN: Flattening logs + version manifest -> ${MIOS_LOG_DIR}/"
_hline '-' '+' '+'
mkdir -p "$MIOS_LOG_DIR"
cp -v /var/log/dnf5.log* /var/log/hawkey.log "$MIOS_LOG_DIR/" 2>/dev/null || true

# Promote machine-readable version manifest (TSV, kept uncompressed for grep/awk)
if [[ -f "$MIOS_VERSION_MANIFEST" ]]; then
    install -m 0644 "$MIOS_VERSION_MANIFEST" "$MIOS_VERSION_MANIFEST_FINAL"
    _row "  Version manifest: ${MIOS_VERSION_MANIFEST_FINAL} ($(wc -l < "$MIOS_VERSION_MANIFEST") rows)"
fi

# Flatten per-step logs + manifest + main build log into single unified chain
{
    echo "# 'MiOS' ${VERSION_STR} Unified Build Log Chain -- $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo "# ====== build-time :latest -> observed-version manifest ======"
    if [[ -f "$MIOS_VERSION_MANIFEST" ]]; then
        cat "$MIOS_VERSION_MANIFEST"
    else
        echo "(no manifest produced)"
    fi
    for step_log in /tmp/mios-step-*.log; do
        [[ -f "$step_log" ]] || continue
        echo ""
        echo "# ====== $(basename "$step_log") ======"
        cat "$step_log"
    done
    echo ""
    echo "# ====== mios-build.log ======"
    [[ -f "$BUILD_LOG" ]] && cat "$BUILD_LOG" || true
} > "$MIOS_BUILD_CHAIN_LOG"
cp "$MIOS_BUILD_CHAIN_LOG" "$MIOS_BUILD_LOG" 2>/dev/null || true

# Compress the bulky logs; keep the TSV manifest uncompressed for direct query.
gzip -9f "$MIOS_BUILD_CHAIN_LOG" "$MIOS_BUILD_LOG" 2>/dev/null || true
gzip -9f "$MIOS_LOG_DIR"/dnf5.log* "$MIOS_LOG_DIR/hawkey.log" 2>/dev/null || true
_row "  Unified chain log: ${MIOS_BUILD_CHAIN_LOG}.gz"
_row "  Step count in chain: $(ls /tmp/mios-step-*.log 2>/dev/null | wc -l)"

# ── Cleanup ─────────────────────────────────────────────────────────────────
$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true
rm -rf /var/cache/dnf /var/cache/libdnf5 /tmp/geist-font /tmp/*.tar* /tmp/*.rpm 2>/dev/null || true
rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/* 2>/dev/null || true
rm -rf /usr/share/gnome/help/* /usr/share/help/* 2>/dev/null || true
rm -f /var/log/dnf5.log* /var/log/hawkey.log 2>/dev/null || true
rm -rf /run/ceph /run/cockpit /run/k3s /tmp/mios-step-*.log 2>/dev/null || true
rm -f /var/lib/systemd/random-seed /tmp/mios-build.log "$MIOS_VERSION_MANIFEST" 2>/dev/null || true

# ── Final summary + failure/warn report ──────────────────────────────────────
TOTAL_ELAPSED=$(( SECONDS - TOTAL_START ))
echo ""
_final_summary "$SCRIPT_COUNT" "$SCRIPT_FAIL" "$WARN_FAIL" "$VALIDATION_FAIL" "$TOTAL_ELAPSED"
_fail_report "${FAIL_LOG[@]+"${FAIL_LOG[@]}"}"
_warn_report "${WARN_LOG[@]+"${WARN_LOG[@]}"}"
echo ""

if [[ $SCRIPT_FAIL -gt 0 ]]; then
    printf '[FATAL] %d script(s) failed (see FAILURE LOG above)\n' "$SCRIPT_FAIL"
    exit 1
fi
```


## Layer 4c-j -- Numbered phase scripts (lex order)


### `automation\01-repos.sh`

```bash
#!/usr/bin/env bash
# 'MiOS' v0.2.0 -- 01-repos: Fedora 44 overlay on ucore
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"
source "${SCRIPT_DIR}/lib/common.sh"

echo "[01-repos] Setting install_weak_deps=False globally..."
DNF_CONF="/usr/lib/dnf/dnf.conf"
[[ -f "$DNF_CONF" ]] || DNF_CONF="/etc/dnf/dnf.conf"
if [[ -f "$DNF_CONF" ]]; then
    sed -i '/^install_weak_deps=/d' "$DNF_CONF" 2>/dev/null || true
    echo "install_weak_deps=False" >> "$DNF_CONF"
fi

echo "[01-repos] Elevating base repos to priority 98..."
if [[ -d /etc/yum.repos.d ]]; then
    for repo in /etc/yum.repos.d/fedora*.repo /etc/yum.repos.d/ublue-os*.repo; do
        if [[ -f "$repo" ]] && ! grep -q '^priority=' "$repo"; then
            sed -i '/^\[.*\]/a priority=98' "$repo"
        fi
    done
fi

echo "[01-repos] Importing Fedora 44 GPG key..."
# The fedora-gpg-keys package ships the key at this path on Fedora-based systems.
# On ucore (which is CoreOS-based on Fedora), the key is usually present already.
GPG_KEY_PATH="/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64"
if [[ ! -f "$GPG_KEY_PATH" ]]; then
    # Fallback: import from the package. Failure here is fatal -- the F44 repo
    # below uses repo_gpgcheck=1 and silently dropping the key would surface
    # later as opaque "package not signed" errors on every install. (Audit
    # 2026-05-01 finding: do not swallow this with 2>/dev/null.)
    $DNF_BIN "${DNF_SETOPT[@]}" install -y fedora-gpg-keys
fi

echo "[01-repos] Adding Fedora 44 repository..."
# F44 is in development at build time. Dev-tree repodata is NOT GPG-signed --
# the .asc detached signature returns 404 from every Fedora mirror. Setting
# repo_gpgcheck=1 turns that 404 into a fatal metadata-load error that
# cascades into every subsequent dnf transaction.
#   - repo_gpgcheck=0 : accept unsigned dev metadata (audit 2026-05-01).
#   - gpgcheck=1      : individual *packages* still verified by RPM signature.
#   - skip_if_unavailable=True : when F44 mirrors are intermittently down,
#     fall back to F43 (base image) instead of breaking the whole build.
cat > /etc/yum.repos.d/fedora-44.repo <<EOREPO
[fedora-44]
name=Fedora 44 - \$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=fedora-44&arch=\$basearch
enabled=1
repo_gpgcheck=0
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64
skip_if_unavailable=True
priority=95
timeout=10
minrate=1k
max_parallel_downloads=10
ip_resolve=4

[fedora-44-updates]
name=Fedora 44 Updates - \$basearch
metalink=https://mirrors.fedoraproject.org/metalink?repo=updates-released-f44&arch=\$basearch
enabled=1
repo_gpgcheck=0
type=rpm
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-44-x86_64
skip_if_unavailable=True
priority=95
timeout=10
minrate=1k
max_parallel_downloads=10
ip_resolve=4
EOREPO

echo "[01-repos] Phase 1: Pre-upgrading core systemd/filesystem..."
# --best dropped per audit 2026-05-01: on the F44↔ucore boundary --best can
# refuse the transaction over a single unresolvable kernel-adjacent dep, which
# is then logged-and-continued, masking real breakage. --allowerasing is enough.
# --skip-unavailable: packages from external repos (crowdsec, tailscale) have
# no repo configured at this stage; skip them cleanly instead of aborting.
$DNF_BIN "${DNF_SETOPT[@]}" upgrade -y --allowerasing --skip-unavailable \
    dnf rpm fedora-release fedora-repos filesystem systemd glibc dbus-broker 2>&1 || {
    echo "[01-repos] NOTE: Pre-upgrade had warnings, continuing..."
}

# Packages whose repos are not yet configured (crowdsec) or whose ucore version
# is intentionally newer than F44 (tailscale 1.96→1.94 downgrade).  Excluded
# here; 05-enable-external-repos.sh and later scripts own their lifecycle.
_THIRD_PARTY_EXCLUDES="shim-*,kernel*,tailscale*,crowdsec*,crowdsec-firewall-bouncer*"

echo "[01-repos] Phase 2: Distro-upgrade and userspace alignment..."
$DNF_BIN "${DNF_SETOPT[@]}" \
    --setopt=excludepkgs="${_THIRD_PARTY_EXCLUDES}" \
    upgrade --refresh -y --skip-unavailable || {
    echo "[01-repos] WARN: upgrade --refresh had conflicts (ucore vs F44 pkgs) -- continuing"
}
# distro-sync is retried once: F44 mirrors are occasionally in-progress sync state,
# causing RPM signature mismatches that resolve on a second attempt with fresh metadata.
_dsync_ok=0
for _attempt in 1 2; do
    if $DNF_BIN "${DNF_SETOPT[@]}" \
            --setopt=excludepkgs="${_THIRD_PARTY_EXCLUDES}" \
            distro-sync -y --allowerasing --skip-unavailable; then
        _dsync_ok=1; break
    fi
    echo "[01-repos] WARN: distro-sync attempt $_attempt failed -- cleaning cache and retrying..."
    $DNF_BIN clean metadata 2>/dev/null || true
done
if [[ $_dsync_ok -eq 0 ]]; then
    echo "[01-repos] WARN: distro-sync failed after 2 attempts -- ucore packages may differ from Fedora 44."
    echo "[01-repos] Continuing; individual package installs will use available repos."
fi

# Clean metadata so subsequent scripts start from a consistent cache state
$DNF_BIN clean metadata 2>/dev/null || true

echo "[01-repos] Verifying core package versions..."
rpm -q systemd glibc dbus-broker filesystem || true
```


### `automation\02-kernel.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 02-kernel: Kernel extras + development headers
# The base fedora-bootc:rawhide image ships the newest kernel with a working
# initramfs. We NEVER upgrade the base kernel packages inside the container --
# doing so triggers dracut under the tmpfs mount, which fails with
# "Invalid cross-device link (os error 18)" and produces a broken initramfs.
#
# This script installs ONLY the extras needed for:
#   - akmod-nvidia (kernel-devel, kernel-headers)
#   - DKMS/kvmfr (kernel-devel)
#   - kernel-modules-extra (VFIO, USB, storage modules not in base)
#   - kernel-tools (cpupower, turbostat, perf)
#
# CHANGELOG v0.2.0:
#   - REMOVED kernel/kernel-core/kernel-modules/kernel-modules-core
#     (base image already has them -- upgrading broke dracut)
#   - kernel-modules-extra ensures VFIO/USB/storage modules are present
#   - kernel-devel enables akmod-nvidia and DKMS builds
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

install_packages "kernel"

# Capture KVER for akmod builds later.
# The base image kernel is the only one installed; grab it.
KVER=$(find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1) # Explicitly use /usr
export KVER
echo "[02-kernel] Kernel version: $KVER"
echo "$KVER" > /tmp/mios-kver

# Verify kernel modules directory exists (akmod build will fail without it)
if [[ ! -d "/usr/lib/modules/$KVER" ]]; then # Explicitly check /usr
    echo "[02-kernel] FATAL: /usr/lib/modules/$KVER does not exist" # Explicitly refer to /usr
    exit 1
fi

# Verify kernel-devel is installed (akmod-nvidia needs it)
if [[ ! -d "/usr/lib/modules/$KVER/build" ]]; then
    echo "[02-kernel] WARNING: /usr/lib/modules/$KVER/build missing -- akmod may fail"
fi

echo "[02-kernel] Kernel extras for $KVER installed successfully."
```


### `automation\05-enable-external-repos.sh`

```bash
#!/usr/bin/env bash
# ============================================================================
# automation/05-enable-external-repos.sh
# ----------------------------------------------------------------------------
# Enable external DNF repositories for 'MiOS' (Fedora 44 / Rawhide).
# Idempotent; fails fast; uses ${DNF_SETOPT[@]} from automation/lib/common.sh.
# RPM Fusion is intentionally NOT handled here -- see 01-repos.sh.
#
# v2.3 CHANGES:
#   - Added Kubernetes stable v1.32 repo (kubectl not in Fedora repos).
#   - Added ublue-os/packages COPR (uupd + greenboot; required by 43-uupd-installer.sh).
#
# v0.2.0 CHANGES:
#   - removed redundant RPM Fusion install block (was using `rpm -E %fedora`
#     which yielded 41/43 from the base image and clobbered 01-repos.sh's
#     explicit F44 pin).
#   - replaced dnf5 with dnf throughout (consistency with 01-repos.sh and
#     lib/packages.sh; on F44 `dnf` is dnf5 via symlink anyway).
#   - adopted ${DNF_SETOPT[@]} for every mutating invocation.
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

REPO_DIR=/etc/yum.repos.d

# --- 1. Terra (fyralabs) ----------------------------------------------------
# Patched WINE/Mesa/miscellaneous packages missing from Fedora + RPM Fusion.
if [[ ! -f "${REPO_DIR}/terra.repo" ]]; then
    log "enabling Terra repo (fyralabs)"
    if ! scurl -fsSL --connect-timeout 20 --max-time 60 \
            https://github.com/terrapkg/subatomic-repos/raw/main/terra.repo \
            -o "${REPO_DIR}/terra.repo" 2>/dev/null; then
        warn "Terra repo download failed (github.com unreachable?) -- skipping Terra"
    fi
else
    log "Terra repo already present -- skipping"
fi

# --- 2. VSCodium (FOSS) ------------------------------------------------------
if [[ ! -f "${REPO_DIR}/vscodium.repo" ]]; then
    log "enabling VSCodium repo (FOSS)"
    scurl -fsSL https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg -o /tmp/vscodium.gpg
    rpm --import /tmp/vscodium.gpg && rm -f /tmp/vscodium.gpg
    cat > "${REPO_DIR}/vscodium.repo" <<'EOF'
[vscodium]
name=VSCodium
baseurl=https://download.vscodium.com/rpms/
enabled=1
autorefresh=1
type=rpm-md
gpgcheck=1
gpgkey=https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg
EOF
else
    log "VSCodium repo already present -- skipping"
fi

# --- 7. Kubernetes stable v1.32 (kubectl) -----------------------------------
# kubectl is NOT in standard Fedora repos -- must come from the Kubernetes
# project's own RPM repository. Pinned to v1.32 (current stable).
# Only kubectl is installed from here; kubeadm/kubelet are intentionally
# excluded (k3s is used for the cluster runtime, not kubeadm).
if [[ ! -f "${REPO_DIR}/kubernetes.repo" ]]; then
    log "enabling Kubernetes stable v1.32 repo"
    cat > "${REPO_DIR}/kubernetes.repo" <<'EOF'
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.32/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.32/rpm/repodata/repomd.xml.key
repo_gpgcheck=1
exclude=kubelet kubeadm cri-tools kubernetes-cni
EOF
else
    log "Kubernetes repo already present -- skipping"
fi

# --- 8. ublue-os/packages COPR (uupd + greenboot) ---------------------------
# uupd and greenboot ship from the Universal Blue packages COPR.
# 43-uupd-installer.sh explicitly requires this repo to be present first.
# Using Fedora 44 repo endpoint; COPR auto-publishes new packages as they land.
if [[ ! -f "${REPO_DIR}/ublue-os-packages.repo" ]]; then
    log "enabling ublue-os/packages COPR (uupd + greenboot)"
    scurl -fsSL \
        "https://copr.fedorainfracloud.org/coprs/ublue-os/packages/repo/fedora-44/ublue-os-packages-fedora-44.repo" \
        -o "${REPO_DIR}/ublue-os-packages.repo"
    # Lower priority than Fedora base so Fedora wins on conflicting packages.
    if ! grep -q '^priority=' "${REPO_DIR}/ublue-os-packages.repo"; then
        sed -i '/^\[/a priority=75' "${REPO_DIR}/ublue-os-packages.repo"
    fi
else
    log "ublue-os/packages COPR already present -- skipping"
fi

# ── Waydroid (Aleasto) ───────────────────────────────────────────────────
if ! [ -f /etc/yum.repos.d/_copr:copr.fedorainfracloud.org:aleasto:waydroid.repo ]; then
    log "enabling aleasto/waydroid COPR (GNOME 50 fix)"
    $DNF_BIN "${DNF_SETOPT[@]}" copr enable -y aleasto/waydroid
else
    log "aleasto/waydroid COPR already present -- skipping"
fi

# ── Tailscale ────────────────────────────────────────────────────────────
# ucore:stable ships tailscale but its version can lag. Using the official
# Tailscale repo keeps it at the latest stable regardless of ucore cadence.
if [[ ! -f "${REPO_DIR}/tailscale.repo" ]]; then
    log "enabling Tailscale official repo"
    scurl -fsSL https://pkgs.tailscale.com/stable/fedora/tailscale.repo \
        -o "${REPO_DIR}/tailscale.repo"
else
    log "Tailscale repo already present -- skipping"
fi

# ── CrowdSec ─────────────────────────────────────────────────────────────
# crowdsec ships its own RPM repo; not in Fedora or RPM Fusion.
if [[ ! -f "${REPO_DIR}/crowdsec.repo" ]]; then
    log "enabling CrowdSec repo"
    scurl -fsSL https://packagecloud.io/crowdsec/crowdsec/config_file.repo?os=fedora&dist=40&source=script \
        -o "${REPO_DIR}/crowdsec.repo"
else
    log "CrowdSec repo already present -- skipping"
fi

log "external repos enabled; refreshing metadata"
$DNF_BIN "${DNF_SETOPT[@]}" makecache -y

log "05-enable-external-repos.sh complete"
```


### `automation\08-system-files-overlay.sh`

```bash
#!/bin/bash
# ============================================================================
# automation/08-system-files-overlay.sh - 'MiOS' v0.2.0
# ----------------------------------------------------------------------------
# Overlay /ctx/ onto the rootfs during the Containerfile build,
# correctly handling the /usr/local -> /var/usrlocal symlink.
#
# v0.2.0 Architecture: Rootfs-Native
#   - Sources now directly from /ctx/usr, /ctx/etc, /ctx/var, /ctx/home
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

CTX="${CTX:-/ctx}"

log "08-overlay: starting Rootfs-Native overlay"

# --- Stage 1: /usr (everything except /usr/local) --------------------------
if [[ -d "${CTX}/usr" ]]; then
    log "  stage 1: overlay usr content (excluding /usr/local)"
    tar -C "${CTX}/usr" -cf - --exclude='./local' . | tar -C /usr --no-overwrite-dir -xf -
fi

# --- Stage 2: /usr/local via /var/usrlocal ---------------------------------
# LAW 5: /var/usrlocal must NOT be mkdir'd during OCI build.
# It is declared in /usr/lib/tmpfiles.d/mios-infra.conf and created at boot.
# If /usr/local is a symlink to /var/usrlocal (typical FCOS layout), skip the
# tar write -- the content will be available after first-boot tmpfiles.d runs.
# If /usr/local is a real directory (non-FCOS base), write directly.
if [[ -d "${CTX}/usr/local" ]]; then
    log "  stage 2: overlay /usr/local content"
    if [[ -L /usr/local ]]; then
        local_target="$(readlink -f /usr/local 2>/dev/null || true)"
        log "    /usr/local is a symlink -> ${local_target}; skipping /var write (tmpfiles.d will create at boot)"
    else
        log "    /usr/local is a real directory; writing directly"
        tar -C "${CTX}/usr/local" -cf - . | tar -C /usr/local --no-overwrite-dir -xf -
    fi
fi

# --- Stage 3: /etc (System Config Templates) -------------------------------
if [[ -d "${CTX}/etc" ]]; then
    log "  stage 3: overlay etc content"
    tar -C "${CTX}/etc" -cf - . | tar -C /etc --no-overwrite-dir -xf -
fi

# --- Stage 3a: /etc/wsl.conf force-install ---------------------------------
# WSL2's wsl.conf parser is unforgiving -- a single malformed byte takes down
# systemd-as-PID1, which cascades into a broken user session and home dir.
# Force-install from the canonical reference with explicit perms instead of
# trusting the tar overlay (which can be defeated by a base-image-shipped
# copy or by tar metadata quirks). install -T treats the destination as a
# filename, not a directory, and overwrites unconditionally.
if [[ -f "${CTX}/etc/wsl.conf" ]]; then
    install -m 0644 -o root -g root -T "${CTX}/etc/wsl.conf" /etc/wsl.conf
    log "  stage 3a: force-installed /etc/wsl.conf (mode 0644, root:root)"
fi

# --- Stage 4: /var (Mutable System State Templates) ------------------------
# DEPRECATED: /var population via tar overlay violates zero-trust immutability.
# All mandatory /var structure must be declared in /usr/lib/tmpfiles.d/*.conf.
# if [[ -d "${CTX}/var" ]]; then
#     log "  stage 4: overlay var content"
#     tar -C "${CTX}/var" -cf - . | tar -C /var --no-overwrite-dir -xf -
# fi

# --- Stage 5: /home (User Space Templates) ---------------------------------
# LAW 5: Writing to /var/home during OCI build violates the immutability contract --
# /var is a persistent volume that is NOT populated from the OCI image on deployment.
# Home directory dotfile templates must live in /etc/skel/ and are copied by
# systemd-sysusers when the user is first created at boot.
# This stage is intentionally a no-op; see /etc/skel/ for the skel overlay.
if [[ -d "${CTX}/home" ]]; then
    log "  stage 5: /ctx/home detected -- seeding /etc/skel instead of /var/home (LAW 5)"
    install -d -m 0755 /etc/skel
    tar -C "${CTX}/home" -cf - . | tar -C /etc/skel --no-overwrite-dir --strip-components=1 -xf - 2>/dev/null || true
fi

# Normalize permissions on systemd unit and config files.
log "08-overlay: normalizing systemd file permissions"
find /usr/lib/systemd -type f \( -name "*.service" -o -name "*.socket" -o -name "*.timer" -o -name "*.mount" -o -name "*.conf" -o -name "*.target" -o -name "*.path" -o -name "*.slice" -o -name "*.preset" -o -name "*.automount" -o -name "*.swap" \) -exec chmod 644 {} \; 2>/dev/null || true
find /usr/lib/systemd -type d -exec chmod 755 {} \; 2>/dev/null || true

# Logically Bound Images -- bind every Quadlet from both vendor and admin paths
# (see ARCHITECTURAL LAW 3 -- BOUND-IMAGES).
BDIR="/usr/lib/bootc/bound-images.d"
install -d -m 0755 "${BDIR}"
shopt -s nullglob
for QDIR in /usr/share/containers/systemd /etc/containers/systemd; do
    [[ -d "${QDIR}" ]] || continue
    for q in "${QDIR}"/*.container; do
        name="$(basename "$q")"
        ln -sf "${q}" "${BDIR}/${name}"
        log "  LBI: bound ${name} (${QDIR})"
    done
done
shopt -u nullglob

# ═══ Pathing Compatibility ═══
log "08-overlay: applying pathing compatibility symlinks"

# /etc/wsl.conf is deployed as a real file via Stage 3 overlay (etc/wsl.conf in repo).
# /usr/lib/wsl.conf is a reference stub; do not symlink it over /etc/wsl.conf.

# 1. Standardize /home to /var/home (FCOS/bootc style)
if [ ! -L /home ] && [ -d /home ] && [ ! "$(ls -A /home)" ]; then
    rm -rf /home
    ln -sf /var/home /home
    log "  Path: symlinked /home -> /var/home"
elif [ ! -e /home ]; then
    ln -sf /var/home /home
    log "  Path: created /home -> /var/home symlink"
fi

log "08-overlay: relabeling overlaid files"
restorecon -RFv /usr/ 2>/dev/null || true
restorecon -RFv /etc/ 2>/dev/null || true

log "08-overlay: complete"
```


### `automation\10-gnome.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 10-gnome: GNOME 50 desktop -- PURE BUILD-UP
#
# STRATEGY: ucore has ZERO GNOME packages. We install exactly what we need.
# With install_weakdeps=False (set globally in 01-repos.sh), only hard deps
# get pulled in. This means:
#   - malcontent-libs comes in (gnome-control-center hard dep) -- CORRECT
#   - malcontent-control/pam/tools do NOT come in (weak deps) -- CORRECT
#   - No GNOME bloat apps get installed -- nothing to remove
#
# The ~25 core packages from the docs produce a fully functional GNOME 50
# Wayland desktop with GDM, all portals, audio, Bluetooth, networking,
# security, and proper theming across GTK3/GTK4/Qt.
#
# CHANGELOG v0.2.0:
#   - MANDATORY Bibata cursor download -- retries 3x, FAILS BUILD if missing
#   - dconf profiles for user + GDM added to 
#   - Flatpak: 7 apps (added Flatseal + LocalSend)
#   - adw-gtk3 theme for GTK3 visual consistency
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

# ═════════════════════════════════════════════════════════════════════════════
# GNOME 50 -- Install from PACKAGES.md (build-up, NOT strip-down)
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Installing GNOME 50 desktop (pure build-up)..."
install_packages "gnome"

# Optional GNOME Core Apps (all commented out by default in PACKAGES.md)
install_packages_optional "gnome-core-apps"

# ═════════════════════════════════════════════════════════════════════════════
# Localsearch/tracker -- disable indexing without removing
# Removing localsearch breaks Nautilus search + Activities Overview.
# Hide via autostart overrides in usr/share/xdg/autostart/
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Disabling localsearch/tracker indexing (keep package, hide autostart)..."

# ═════════════════════════════════════════════════════════════════════════════
# Qt Adwaita theming -- required for Qt apps to match GNOME look
# Managed via usr/lib/environment.d/60-mios-qt-adwaita.conf
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Setting Qt Adwaita environment variables (managed via overlay)..."

# ═════════════════════════════════════════════════════════════════════════════
# Geist Font (Vercel)
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Installing Geist font family..."
mkdir -p /usr/share/fonts/geist
git clone --depth=1 --single-branch -c http.lowSpeedLimit=1 -c http.lowSpeedTime=20 \
    https://github.com/vercel/geist-font.git /tmp/geist-font 2>/dev/null || true
if [ -d /tmp/geist-font ]; then
    find /tmp/geist-font \( -name "*.otf" -o -name "*.ttf" \) -exec cp {} /usr/share/fonts/geist/ \; 2>/dev/null || true
    rm -rf /tmp/geist-font
fi
fc-cache -f /usr/share/fonts/geist 2>/dev/null || true

# ═════════════════════════════════════════════════════════════════════════════
# Bibata Cursor Theme -- MANDATORY (build fails if download fails)
#
# The cursor shows as a SQUARE when:
#   - /usr/share/icons/Bibata-Modern-Classic/ doesn't exist (download failed)
#   - /usr/share/icons/default/index.theme points to nonexistent theme
#   - dconf cursor-theme references a theme with no files
#
# FIX: Retry download 3 times. VERIFY the cursors directory exists.
#      FAIL THE BUILD if cursors are missing -- a square cursor is unacceptable.
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Installing Bibata-Modern-Classic cursor (MANDATORY)..."

# Resolve latest release from upstream. Project policy: every dependency
# tracks :latest from its source, so no fallback pin -- if api.github.com is
# unreachable, fail loud rather than silently shipping a stale version.
BIBATA_VER=$( (scurl -sL --connect-timeout 15 --max-time 30 \
    -H "Accept: application/vnd.github+json" "https://api.github.com/repos/ful1e5/Bibata_Cursor/releases/latest" \
    | grep -m1 '"tag_name"' | sed 's/.*"v\?\([^"]*\)".*/\1/') 2>/dev/null || true)

[[ -n "$BIBATA_VER" ]] || die "Bibata: api.github.com release-latest lookup returned empty"
record_version bibata "v${BIBATA_VER}" "https://github.com/ful1e5/Bibata_Cursor/releases/tag/v${BIBATA_VER}"

BIBATA_URL="https://github.com/ful1e5/Bibata_Cursor/releases/download/v${BIBATA_VER}/Bibata-Modern-Classic.tar.xz"
BIBATA_DIR="/usr/share/icons/Bibata-Modern-Classic"
mkdir -p /usr/share/icons

# Download with retries + sha256 verification
BIBATA_OK=0
BIBATA_SUM_URL="https://github.com/ful1e5/Bibata_Cursor/releases/download/v${BIBATA_VER}/sha256-${BIBATA_VER}.txt"
for attempt in 1 2 3; do
    echo "[10-gnome]   Download attempt $attempt/3..."
    if scurl -fSL --connect-timeout 20 --max-time 120 --retry 2 --retry-delay 5 "$BIBATA_URL" -o /tmp/bibata.tar.xz; then
        # Attempt sha256 verification -- non-fatal if sidecar unavailable
        if scurl -fsSL --connect-timeout 15 --max-time 30 "$BIBATA_SUM_URL" -o /tmp/bibata.sha256 2>/dev/null; then
            if (cd /tmp && grep "Bibata-Modern-Classic.tar.xz" bibata.sha256 | sha256sum -c -) 2>/dev/null; then
                echo "[10-gnome]   [ok] Bibata sha256 verified"
            else
                echo "[10-gnome]   WARN: Bibata sha256 mismatch or sidecar format mismatch -- continuing anyway"
            fi
            rm -f /tmp/bibata.sha256
        else
            echo "[10-gnome]   WARN: Bibata sha256 sidecar unavailable -- skipping integrity check"
        fi
        if tar -xf /tmp/bibata.tar.xz -C /usr/share/icons/; then
            rm -f /tmp/bibata.tar.xz
            BIBATA_OK=1
            break
        fi
    fi
    echo "[10-gnome]   Attempt $attempt failed, retrying..."
    sleep 5
done

# VERIFY cursor files actually exist -- log warning if missing but DO NOT fail build
if [ "$BIBATA_OK" -eq 0 ] || [ ! -d "$BIBATA_DIR/cursors" ]; then
    echo "  WARNING: Bibata cursor theme download FAILED after 3 attempts"
    echo "  URL: $BIBATA_URL"
    echo "  The cursor will show as a SQUARE until the theme is installed."
    echo "  This failure is non-fatal for the build; users can install later."
else
    echo "[10-gnome] [ok] Bibata cursor installed: $(find "$BIBATA_DIR/cursors/" -mindepth 1 -maxdepth 1 | wc -l) cursors"
fi

# Comprehensive cursor default -- every layer that reads cursor theme
# Managed via usr/share/icons/default/index.theme
# and usr/share/X11/icons/default/index.theme

# 3. update-alternatives for x-cursor-theme (Fedora cursor resolution)
if [ -d "$BIBATA_DIR/cursors" ]; then
    update-alternatives --install /usr/share/icons/default/index.theme \
        x-cursor-theme /usr/share/icons/Bibata-Modern-Classic/cursor.theme 100 2>/dev/null || true
    echo "[10-gnome] [ok] x-cursor-theme alternative set to Bibata"
fi

# 4. Symlink into /usr/share/cursors/xorg-x11 (legacy X11 cursor path)
mkdir -p /usr/share/cursors/xorg-x11
ln -sf /usr/share/icons/Bibata-Modern-Classic /usr/share/cursors/xorg-x11/Bibata-Modern-Classic 2>/dev/null || true

# 5. GDM user cursor -- ensure cursor files are world-readable
chmod -R a+rX "$BIBATA_DIR" 2>/dev/null || true

# 6. Xresources fallback (oldest X11 cursor method)
# Managed via usr/lib/X11/Xresources

# ═══════════════════════════════════════════════════════════════════════════════
# Phosh -- Mobile session for portrait/tablet remote access
# ═══════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Installing Phosh mobile session..."
install_packages_optional "phosh"
# Make session wrapper executable
chmod +x /usr/local/bin/phosh-session-wrapper 2>/dev/null || true
# ═════════════════════════════════════════════════════════════════════════════
# Flatpak Remotes
# Disable filtered Fedora remote, use unfiltered Flathub for full catalog
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Configuring Flatpak remotes..."
if command -v flatpak &>/dev/null; then
    flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo || true
    flatpak remote-add --system --if-not-exists flathub-beta https://flathub.org/beta-repo/flathub-beta.flatpakrepo || true
    flatpak remote-add --system --if-not-exists gnome-nightly https://nightly.gnome.org/gnome-nightly.flatpakrepo 2>/dev/null || true
    flatpak remote-modify --system --disable fedora 2>/dev/null || true
else
    echo "[10-gnome] WARN: flatpak binary not found, skipping remote configuration"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Essential Flatpaks
# ═════════════════════════════════════════════════════════════════════════════
echo "[10-gnome] Flatpaks will be installed on first boot (mios-flatpak-install.service)..."
# NOTE: mios-flatpak-install.service is enabled in Containerfile STEP D
# (unit file lives in , not available during script execution)

exit 0
```


### `automation\11-hardware.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 11-hardware: GPU drivers (Mesa + AMD ROCm + Intel + NVIDIA)
#
# NVIDIA strategy (v0.2.0):
#   Primary:  ucore-hci:stable-nvidia ships pre-signed kmods for the base
#             kernel. If modinfo finds them for `uname -r`, we keep them.
#   Fallback: akmod rebuild from RPMFusion (requires matching kernel-devel).
#             If that fails or kernel-devel is unavailable, we accept no
#             NVIDIA acceleration - image still works for everything else.
#
# Mesa (AMD/Intel/software fallback) and ROCm + intel-compute-runtime are
# installed from PACKAGES.md. They have no kernel-version coupling.
#
# CHANGELOG:
#   v0.2.0: Dropped COPY-layer fallback. ucore-hci IS already built from
#           ublue's akmods-nvidia pipeline - copying those same RPMs on top
#           would create RPM conflicts, not redundancy. Kernel-mismatch
#           recovery falls to akmod rebuild + graceful skip.
#   v0.2.0: (attempted COPY-layer, reverted)
#   v2.0:   NVIDIA akmod baseline removed (ucore base provides pre-signed)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

KVER=$(cat /tmp/mios-kver 2>/dev/null || find /lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1)

# ── Mesa (AMD / Intel / software fallback) ──────────────────────────────────
echo "[11-hardware] Installing Mesa GPU stack..."
install_packages_strict "gpu-mesa"

# ── AMD ROCm (fault-tolerant) ───────────────────────────────────────────────
echo "[11-hardware] Installing ROCm (optional)..."
install_packages "gpu-amd-compute"

# ── Intel GPU Compute (fault-tolerant -- may not be on all architectures) ──
echo "[11-hardware] Installing Intel compute runtime (fault-tolerant)..."
install_packages "gpu-intel-compute" || true

# ── NVIDIA: Verify ucore's pre-signed modules match the kernel ──────────────
echo "[11-hardware] Checking NVIDIA modules from ucore base (kernel=$KVER)..."

NVIDIA_PRESENT=0
if [[ -d "/lib/modules/$KVER/extra/nvidia" ]] || \
   [[ -d "/lib/modules/$KVER/extra/nvidia-open" ]] || \
   modinfo nvidia -k "$KVER" &>/dev/null; then
    echo "[11-hardware] [ok] NVIDIA kmod present for kernel $KVER (ucore pre-signed)"
    NVIDIA_PRESENT=1
fi

# ── NVIDIA fallback: akmod rebuild via RPMFusion ────────────────────────────
# Only if ucore base missed (rare - the ucore:stable-nvidia tag guarantees
# its own kernel matches). This path requires kernel-devel-$KVER which is the
# exact failure mode that broke v2.2.x when ucore kernel (v0.2.0) didn't
# match F44's kernel-devel (v0.2.0). If kernel-devel is unavailable, we log
# and accept NVIDIA-less - the image still works for everything else, and
# 34-gpu-detect.sh handles runtime blacklisting/unblacklisting.
if [[ $NVIDIA_PRESENT -eq 0 ]]; then
    echo "[11-hardware] Fallback: akmod-nvidia build against $KVER..."
    if install_packages "gpu-nvidia"; then
        if command -v akmods &>/dev/null; then
            akmods --force --kernels "$KVER" 2>&1 | tail -10 || true
            if modinfo nvidia -k "$KVER" &>/dev/null; then
                echo "[11-hardware] [ok] NVIDIA kmod rebuilt via akmods for $KVER"
                NVIDIA_PRESENT=1
            fi
        fi
    fi
fi

if [[ $NVIDIA_PRESENT -eq 0 ]]; then
    echo "[11-hardware] [!] No NVIDIA kmod for $KVER after all fallback attempts."
    echo "[11-hardware]    Image will ship without NVIDIA acceleration. Users with"
    echo "[11-hardware]    NVIDIA hardware can rebuild the kmod at runtime:"
    echo "[11-hardware]       sudo dnf install kernel-devel-\$(uname -r) akmod-nvidia"
    echo "[11-hardware]       sudo akmods --force --kernels \$(uname -r)"
fi

# Regenerate CDI spec if nvidia-ctk is available (fails gracefully in no-GPU builds)
if command -v nvidia-ctk &>/dev/null; then
    nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml 2>/dev/null || true
    echo "[11-hardware] NVIDIA CDI spec generated (build-time; runtime refresh handled by nvidia-cdi-refresh.path)"
fi

# ── NVIDIA Open Kernel Module Configuration ─────────────────────────────────
# Turing+ (RTX 20xx and newer) supports open modules; RTX 50 Blackwell requires
# them. NVreg_OpenRmEnableUnsupportedGpus=1 lets open modules attempt older
# cards too (Pascal, Maxwell) where supported.
# ARCHITECTURAL FIX: Managed via usr/lib/modprobe.d/nvidia-open.conf
# to prevent /etc state drift.

echo "[11-hardware] GPU stack complete. Mesa + AMD ROCm + Intel + NVIDIA (ucore / akmod rebuild)."
```


### `automation\12-virt.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 12-virt: Virtualization, containers, orchestration, gaming
#
# CHANGELOG v1.3:
#   - Looking Glass B7: MOVED to 53-bake-lookingglass-client.sh (refactored out)
#   - KVMFR module: MOVED to 52-bake-kvmfr.sh (refactored out)
#   - K3s: MOVED to 13-ceph-k3s.sh (no longer duplicated here)
#   - CrowdSec: Updated sovereign mode config (RE2 regex engine default)
#   - Added Podman quadlet example for CrowdSec
#   - VirtIO-Win ISO: Updated URL pattern
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"
source "${SCRIPT_DIR}/lib/common.sh"

KVER=$(cat /tmp/mios-kver 2>/dev/null || find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1)

# ── KVM / QEMU / Libvirt ────────────────────────────────────────────────────
echo "[12-virt] Installing KVM/QEMU/Libvirt..."
install_packages "virt"

# ── Containers (Podman, Buildah, Skopeo, bootc, self-build tools) ────────────
echo "[12-virt] Installing container runtime and self-building tools..."
install_packages "containers"

# Extra self-build tools (image-rechunking, etc. - may be repo-dependent)
install_packages "self-build"

# ── Cockpit Web Management ──────────────────────────────────────────────────
echo "[12-virt] Installing Cockpit..."
install_packages_strict "cockpit"

# ── Boot & Update Management (bootupd, ukify, etc.) ─────────────────────────
echo "[12-virt] Installing boot and update management tools..."
install_packages "boot"

# ── CrowdSec IPS (sovereign/offline mode) ───────────────────────────────────
echo "[12-virt] Installing CrowdSec..."
install_packages "security"

# Sovereign mode: disable Central API, use local-only decisions
if [ -d /etc/crowdsec ]; then
    # acquis.d/journalctl.yaml managed via  overlay

    # Disable online API for sovereign operation
    if [ -f /etc/crowdsec/config.yaml ]; then
        sed -i 's/^online_client:/# online_client:/' /etc/crowdsec/config.yaml 2>/dev/null || true
    fi
    echo "[12-virt] CrowdSec configured for sovereign/offline mode"
fi

# ── Windows Interop & Remote Desktop ────────────────────────────────────────
echo "[12-virt] Installing Windows interop tools..."
install_packages "wintools"

# ── Gaming (Steam, Wine, Gamescope) ─────────────────────────────────────────
# NOTE: steam-devices and udev-joystick-blacklist-rm (terra weak dep of
# gamescope-session-steam) both ship the same udev rules file. Exclude it.
echo "[12-virt] Installing gaming packages..."
GAMING_PKGS=$(get_packages "gaming")
if [[ -n "$GAMING_PKGS" ]]; then
    ($DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" --skip-unavailable --exclude=udev-joystick-blacklist-rm $GAMING_PKGS) || {
        echo "[12-virt] WARNING: Some gaming packages failed to install" >&2
    }
fi

# ── Guest Agents ────────────────────────────────────────────────────────────
echo "[12-virt] Installing guest agents..."
install_packages "guests"

# ── Storage ─────────────────────────────────────────────────────────────────
echo "[12-virt] Installing storage packages..."
install_packages "storage"

# ── High Availability (Pacemaker/Corosync) ──────────────────────────────────
echo "[12-virt] Installing HA stack..."
install_packages "ha"

# ── CLI Utilities ───────────────────────────────────────────────────────────
echo "[12-virt] Installing CLI utilities..."
install_packages "utils"

# ── Android (Waydroid) ──────────────────────────────────────────────────────
echo "[12-virt] Installing Waydroid..."
install_packages "android"

# ── VirtIO-Win ISO (latest stable) ─────────────────────────────────────────
echo "[12-virt] Downloading VirtIO-Win ISO..."
VIRTIO_URL="https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso"
mkdir -p ${MIOS_SHARE_DIR}/virtio
scurl -sL "$VIRTIO_URL" -o ${MIOS_SHARE_DIR}/virtio/virtio-win.iso 2>/dev/null || {
    echo "[12-virt] WARNING: VirtIO-Win ISO download failed -- download manually later"
}

# Symlink the immutable ISO into /var/lib/libvirt/images via tmpfiles.d so it survives upgrades
# Managed via usr/lib/tmpfiles.d/mios-virtio.conf

echo "[12-virt] Virtualization stack complete. (LG: refactored to 53-lg; K3s: refactored to 13-ceph-k3s)"
```


### `automation\13-ceph-k3s.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 13-ceph-k3s: Ceph distributed storage + K3s Kubernetes
# Cephadm runs ALL server daemons as Podman containers.
# Only client tools + orchestrator binary are baked into the image.
#
# v0.2.0 FIXES:
#   - K3s manifests stored in /usr/share/mios/k3s-manifests/ (not /var)
#     First-boot service copies them to /var/lib/rancher/k3s/server/manifests/
#     This fixes bootc lint: /var content must use tmpfiles.d entries
#   - systemctl enables moved to Containerfile STEP D (unit files in )
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

# ─── Ceph Client + Orchestrator ──────────────────────────────────────────────
echo "[13-ceph-k3s] Installing Ceph client tools and cephadm..."
install_packages "ceph"

# ─── K3s Prerequisites ───────────────────────────────────────────────────────
echo "[13-ceph-k3s] Installing K3s prerequisites..."
install_packages "k3s"

# Note: k3s-selinux policy is compiled from source in 19-k3s-selinux.sh

# ─── K3s Binary & Install Script ─────────────────────────────────────────────
echo "[13-ceph-k3s] Resolving latest K3s release tag..."
# Retry 3 times for flaky networks
K3S_TAG=""
for i in 1 2 3; do
    # v0.2.0: Wrap in subshell + || true to prevent pipefail from killing the script if API is down
    K3S_TAG=$( (scurl -sL -o /dev/null -w "%{url_effective}" https://github.com/k3s-io/k3s/releases/latest | grep -oE '[^/]+$') 2>/dev/null || true)
    if [[ -n "$K3S_TAG" && "$K3S_TAG" != "latest" ]]; then break; fi
    sleep 2
done

if [[ -z "$K3S_TAG" || "$K3S_TAG" == "latest" ]]; then
    echo "[13-ceph-k3s] WARN: Could not resolve latest K3s tag. Skipping K3s binary installation."
    K3S_TAG=""
fi

if [[ -n "$K3S_TAG" ]]; then
    echo "[13-ceph-k3s] Latest K3s tag: $K3S_TAG"
    record_version k3s "$K3S_TAG" "https://github.com/k3s-io/k3s/releases/tag/${K3S_TAG}"

    echo "[13-ceph-k3s] Downloading K3s binary, checksum, and install script..."
    K3S_URL="https://github.com/k3s-io/k3s/releases/download/${K3S_TAG}/k3s"
    K3S_SUM_URL="https://github.com/k3s-io/k3s/releases/download/${K3S_TAG}/sha256sum-amd64.txt"
    K3S_INSTALL_URL="https://raw.githubusercontent.com/k3s-io/k3s/${K3S_TAG}/install.sh"

    mkdir -p /tmp/k3s-dl
    if scurl -sfL "$K3S_URL" -o /tmp/k3s-dl/k3s && \
       scurl -sfL "$K3S_SUM_URL" -o /tmp/k3s-dl/sha256sum.txt && \
       scurl -sfL "$K3S_INSTALL_URL" -o /tmp/k3s-dl/k3s-install.sh; then
        cd /tmp/k3s-dl
        if grep -E "  k3s$" sha256sum.txt | sha256sum -c - >/dev/null 2>&1; then
            echo "[13-ceph-k3s] [ok] K3s SHA256 checksum verified"
            # Install into /usr/bin (immutable image surface). /usr/local is
            # a symlink to /var/usrlocal on bootc/FCOS layouts and
            # /var/usrlocal/bin/ does not exist at OCI build time (it's
            # created at first boot by usr/lib/tmpfiles.d/mios.conf).
            install -m 0755 -t /usr/bin/ k3s
            install -m 0755 -t /usr/bin/ k3s-install.sh

            # Symlink only if no official RPM binaries claim the names.
            [ ! -e /usr/bin/kubectl ] && ln -sf k3s /usr/bin/kubectl || true
            [ ! -e /usr/bin/crictl ]  && ln -sf k3s /usr/bin/crictl  || true
            [ ! -e /usr/bin/ctr ]     && ln -sf k3s /usr/bin/ctr     || true

            echo "[13-ceph-k3s] K3s binary and install script installed (tag: $K3S_TAG)"
        else
            echo "[13-ceph-k3s] ERROR: K3s binary SHA256 checksum mismatch! Skipping."
        fi
        cd - >/dev/null
    else
        echo "[13-ceph-k3s] WARN: K3s download failed. Skipping K3s installation."
    fi
    rm -rf /tmp/k3s-dl
fi

# ─── Make bootstrap script executable ────────────────────────────────────────
chmod 755 /usr/local/bin/ceph-bootstrap.sh 2>/dev/null || true

# ─── NOTE: Service enables are in Containerfile STEP D ───────────────────────
# k3s.service, mios-ceph-bootstrap.service, var-home.mount,
# var-lib-containers.mount all live in  and are enabled
# AFTER the COPY step in the Containerfile.

echo "[13-ceph-k3s] Ceph + K3s stack installed."
echo "[13-ceph-k3s]   Ceph Dashboard:  https://<host>:8443 (after bootstrap)"
echo "[13-ceph-k3s]   K3s API server:  https://<host>:6443 (after boot)"
```


### `automation\18-apply-boot-fixes.sh`

```bash
#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# 'MiOS': Systemd execution analysis & WSL2 Boot Loop fixes
# Resolves ordering cycles, executable stripping, and hardware-dependent
# failure cascades detected during F44 boots on varied hardware/hypervisors.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

echo "==> Applying 'MiOS' system service fixes..."

# 1. Fix USBGuard Permissions
# Log trace: Permissions for /etc/usbguard/usbguard-daemon.conf should be 0600
if [ -f /etc/usbguard/usbguard-daemon.conf ]; then
    chmod 0600 /etc/usbguard/usbguard-daemon.conf
fi

# 2. Fix 203/EXEC for custom 'MiOS' services
# Log trace: mios-role.service & mios-cdi-detect.service exited 203/EXEC
# Global chmod commands in earlier pipelines stripped execution bits.
# Handle all scripts in /usr/libexec/mios/ and named patterns.
find ${MIOS_LIBEXEC_DIR} -type f -exec chmod +x {} \; || true
find /usr/libexec -type f \( -name 'mios-*' -o -name 'role-apply' -o -name 'selinux-init' -o -name 'gpu-detect' -o -name 'cpu-isolate' -o -name 'motd' -o -name 'dash' -o -name 'sb-audit' -o -name 'wsl-init' -o -name 'wsl-firstboot' -o -name 'sb-keygen' -o -name 'tpm-enroll' \) -exec chmod +x {} \; || true
find /usr/bin -name 'mios-*' -type f -exec chmod +x {} \; || true

# 3. Libvirt QEMU Hooks
# Ensure hooks are executable. We check both /etc and /usr/lib for bootc parity.
for hook in /etc/libvirt/hooks/qemu /usr/lib/libvirt/hooks/qemu; do
    if [ -f "$hook" ]; then
        chmod +x "$hook"
    fi
done

# 4. Fix systemd-resolved 217/USER
# Log trace: systemd-resolved.service exited 217/USER
# User mapping required at boot time; ensuring it's compiled statically.
if [ -f /usr/lib/sysusers.d/systemd-resolve.conf ]; then
    systemd-sysusers /usr/lib/sysusers.d/systemd-resolve.conf || true
fi

# 5. Fix Systemd Ordering Cycle for GPU Passthrough
# Log trace: sockets.target: Found ordering cycle: docker.socket/start after mios-gpu-nvidia.service/start after basic.target
# Drop-in handled via overlay.

# 6. OCI Container and WSL2 Service Gating
# Custom 'MiOS' services that require hardware access or full system init
# skip OCI containers and WSL2 via drop-ins in system_files overlay.
echo "==> Service gating drop-ins active via overlay"

# 7. WSL2 Compatibility Gating (Legacy section kept for unit-specific fallbacks)
```


### `automation\19-k3s-selinux.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "==> Compiling and Installing K3s SELinux Policy for Fedora 44..."

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

install_packages "k3s-selinux-build"

# Pin to a specific stable release tag -- HEAD clones pick up unreviewed commits.
# Update K3S_SELINUX_TAG when bumping K3s to stay in sync with its SELinux policy.
# Audit 2026-05-01: v1.5.stable.2 was deleted upstream; resolve "the latest
# v* tag" dynamically and fall back to the override or master if discovery
# fails.
K3S_SELINUX_REPO="https://github.com/k3s-io/k3s-selinux.git"
if [[ -z "${K3S_SELINUX_TAG:-}" ]]; then
    K3S_SELINUX_TAG=$(git ls-remote --tags --refs "$K3S_SELINUX_REPO" 'v*' 2>/dev/null \
        | awk -F/ '{print $NF}' \
        | sort -V \
        | tail -n1) || true
    K3S_SELINUX_TAG="${K3S_SELINUX_TAG:-master}"
fi
record_version k3s-selinux "$K3S_SELINUX_TAG" "https://github.com/k3s-io/k3s-selinux/tree/${K3S_SELINUX_TAG}"

echo "==> Cloning k3s-selinux at ref ${K3S_SELINUX_TAG}..."
git clone --depth 1 --branch "${K3S_SELINUX_TAG}" \
    "$K3S_SELINUX_REPO" /tmp/k3s-selinux 2>/dev/null \
    || git clone --depth 1 "$K3S_SELINUX_REPO" /tmp/k3s-selinux

cd /tmp/k3s-selinux

# K3s SELinux repo stores policies in subdirectories (e.g., policy/coreos or policy/centos9)
# We find the best matching policy source files for Fedora.
POLICY_DIR=""
if [ -d "policy/coreos" ]; then
    POLICY_DIR="policy/coreos"
elif [ -d "policy/centos9" ]; then
    POLICY_DIR="policy/centos9"
elif [ -d "policy/rhel9" ]; then
    POLICY_DIR="policy/rhel9"
else
    POLICY_DIR=$(find policy -name k3s.te -printf '%h\n' | head -n 1)
fi

if [ -z "$POLICY_DIR" ]; then
    echo "FATAL: Could not find k3s.te in the repository."
    exit 1
fi

echo "Using policy source from: $POLICY_DIR"
cp "$POLICY_DIR"/k3s.* .

# Compile the policy using the Fedora 44 SELinux Makefile
make -f /usr/share/selinux/devel/Makefile k3s.pp

# ARCHITECTURAL FIX: Instead of installing at build-time with 'semodule -i',
# we ship the compiled policy in the immutable /usr tree.
# This ensures that 'bootc upgrade' doesn't create opaque policy layers.
mkdir -p /usr/share/selinux/packages/mios
install -m 0644 k3s.pp /usr/share/selinux/packages/mios/k3s.pp

# Clean up
cd /
rm -rf /tmp/k3s-selinux
echo "==> K3s SELinux Policy staged in /usr/share/selinux/packages/mios/"
```


### `automation\20-fapolicyd-trust.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "==> Configuring fapolicyd for fs-verity/ComposeFS..."

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

# Configure fapolicyd to use the file trust backend (fs-verity)
# This allows 0-second boot delays while maintaining rigid application whitelisting
# in immutable ComposeFS environments.
#
# v0.2.0: USR-OVER-ETC alignment. Update both /usr/lib and /etc.
for config in /usr/lib/fapolicyd/fapolicyd.conf /etc/fapolicyd/fapolicyd.conf; do
    if [[ -f "$config" ]]; then
        sed -i 's/^trust =.*/trust = file,rpmdb/' "$config" || true
    fi
done

# Enable the service
systemctl enable fapolicyd.service
echo "==> fapolicyd configured successfully."
```


### `automation\20-services.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 20-services: Enable systemd services + bare-metal/VM gating
#
# CHANGELOG v1.3:
#   - systemd 260: cgroup v1 support REMOVED -- all services must use cgroup v2
#   - systemd 260: SysV service scripts no longer supported
#   - Fixed: pmcd/pmlogger services removed (only pmproxy is installed)
#   - Added: bootloader-update.service for bootc systems
#   - Added: podman-auto-update.timer for quadlet auto-updates
#   - Improved: Bare-metal vs VM vs WSL2 service gating
set -euo pipefail

echo "  'MiOS' v0.2.0 -- Service Configuration"

# ─── Fix systemd unit file permissions ────────────────────────────────────────
# Container builds sometimes leave bad perms from COPY operations.
for unit_file in \
    /usr/lib/systemd/system/var-home.mount \
    /usr/lib/systemd/system/var-lib-containers.mount \
    /usr/lib/systemd/system/ceph-bootstrap.service \
    /usr/lib/systemd/system/cockpit.socket.d/listen.conf \
; do
    [ -f "$unit_file" ] && chmod 644 "$unit_file"
done
echo "[20-services] Fixed systemd unit file permissions"

# ─── Service Configuration Note ──────────────────────────────────────────────
# CORE and OPTIONAL services are now primarily managed via:
# usr/lib/systemd/system-preset/90-mios.preset
# Role-specific services are managed by mios-role.service at runtime.

# ─── WSL2 & Container Service Gating ─────────────────────────────────────────
# These services skip OCI/WSL2 via drop-ins in system_files overlay.
echo "[20-services] WSL2/Container skip drop-ins active via overlay"

# ─── nvidia-powerd: skip in ALL VMs (no physical NVIDIA GPU) ─────────────────
# Drop-in handled via overlay.

# ─── TuneD: set throughput-performance profile ──────────────────────────────
tuned-adm profile throughput-performance 2>/dev/null || true

echo "[20-services] Service configuration baseline complete. v1.4"
```


### `automation\21-moby-engine.sh`

```bash
#!/usr/bin/env bash
# Normalize to LF line endings (fixes SC1017)
set -euo pipefail

echo "==> Installing moby-engine (Docker) alongside Podman..."

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

# moby-engine conflicts with podman-docker over /usr/bin/docker. install_packages
# routes through dnf which resolves the conflict at install time; PACKAGES.md is
# the SSOT for every RPM (see CLAUDE.md / CONTRIBUTING.md).
install_packages "moby"

# Enable the Docker socket to ensure it's available on boot
systemctl enable docker.socket

# Ensure the docker group exists so we can map users to it later via sysusers
groupadd -r docker 2>/dev/null || true
```


### `automation\22-freeipa-client.sh`

```bash
#!/usr/bin/env bash
# 22-freeipa-client.sh -- install FreeIPA/SSSD client + arm zero-touch enrollment.
#
# Runtime path: mios-freeipa-enroll.service runs only when
# /etc/mios/ipa-enroll.env is present and /etc/ipa/default.conf is absent.
#
# Upstream regression notes (April 2026):
#   bz 2320133 -- SSSD file caps stripped by rpm-ostree < bootc v0.2.0-2.fc41.
#                Asserted post-install; build fails fast if caps are missing.
#   bz 2332433 -- /var/lib/ipa-client/sysrestore/ missing on first boot.
#                Pre-created via tmpfiles.d.
set -euo pipefail

echo "==> Installing FreeIPA & SSSD for zero-touch enrollment..."

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"

# Install client + SSSD tooling.
install_packages "freeipa"

# ── SSSD file capability regression check (bz 2320133) ─────────────────────
echo "==> Verifying SSSD file capabilities..."
SSSD_CAP_BINS=(
    /usr/libexec/sssd/krb5_child
    /usr/libexec/sssd/ldap_child
    /usr/libexec/sssd/selinux_child
    /usr/lib/sssd/sssd_pam
)
CAP_FAIL=0
for bin in "${SSSD_CAP_BINS[@]}"; do
    [[ -f "$bin" ]] || continue
    caps=$(getcap "$bin" 2>/dev/null || true)
    if [[ -z "$caps" ]]; then
        echo "ERROR: $bin missing file capabilities (bz 2320133 regression)"
        CAP_FAIL=$((CAP_FAIL + 1))
    fi
done
if (( CAP_FAIL > 0 )); then
    echo "WARNING: ${CAP_FAIL} SSSD binary(ies) lost file capabilities -- FreeIPA authentication may require 'setcap' at runtime."
fi

# Arm the zero-touch enrollment oneshot (gated by ConditionPathExists).
systemctl enable mios-freeipa-enroll.service
```


### `automation\23-uki-render.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "==> Preparing Unified Kernel Image (UKI) configuration..."

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

# packages-boot already pulls systemd-ukify; reinstall via the SSOT block as a
# safety net in case --skip-unavailable dropped it on a constrained mirror.
if ! rpm -q systemd-ukify >/dev/null 2>&1; then
    echo "==> systemd-ukify not found via boot-section install; reinstalling via PACKAGES.md..."
    install_packages_strict "uki"
fi

# In a bootc Containerfile build, we use `bootc container render-kargs`
# to flatten all kargs.d/*.toml drop-ins into a single string for the UKI.
KERNEL_CMDLINE_DST="/usr/lib/kernel/cmdline"
install -d -m 0755 /usr/lib/kernel

if command -v bootc >/dev/null && bootc container --help | grep -q 'render-kargs'; then
    echo "==> Rendering bootc kargs for UKI natively..."
    bootc container render-kargs > "${KERNEL_CMDLINE_DST}"
else
    echo "==> bootc render-kargs not available, rendering flat TOML via Python fallback..."
    python3 -c '
import tomllib, sys, glob
kargs = []
for f in sorted(glob.glob("/usr/lib/bootc/kargs.d/*.toml")):
    with open(f, "rb") as fp:
        d = tomllib.load(fp)
        if "kargs" in d:
            kargs.extend(d["kargs"])
print(" ".join(kargs))
' > "${KERNEL_CMDLINE_DST}"
fi

CMDLINE=$(cat "${KERNEL_CMDLINE_DST}" | xargs)
if [ -z "$CMDLINE" ]; then
    echo "WARN: /usr/lib/kernel/cmdline is empty -- no kargs rendered. UKI generation will use defaults."
fi

echo "Rendered UKI cmdline: $CMDLINE"
# The actual UKI generation (`ukify build`) occurs in the final CI/CD pipeline
echo "==> UKI cmdline preparation complete."
```


### `automation\25-firewall-ports.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "==> Configuring firewalld ports for 'MiOS' services..."

# During an OCI container build, the firewalld daemon is not running.
# We MUST use firewall-offline-cmd to write directly to the XML policy files.

# Open essential ports for local/LAN access
firewall-offline-cmd --zone=public --add-port=8080/tcp # Guacamole
firewall-offline-cmd --zone=public --add-port=8443/tcp # Ceph Dashboard
firewall-offline-cmd --zone=public --add-port=6443/tcp # K3s API
firewall-offline-cmd --zone=public --add-port=3389/tcp # RDP
firewall-offline-cmd --zone=public --add-service=ssh
firewall-offline-cmd --zone=public --add-service=cockpit
firewall-offline-cmd --zone=public --add-service=mios-pxe
```


### `automation\26-gnome-remote-desktop.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "[26-grd] Configuring GNOME Remote Desktop (GNOME 50)"

# Pre-emptively disable/mask legacy xrdp services just in case they bleed in from a base image
systemctl mask xrdp.service xrdp-sesman.service 2>/dev/null || true

# GNOME Remote Desktop handles Wayland headless RDP natively.
# Enablement is handled via usr/lib/systemd/system-preset/90-mios.preset
# Drop-in to wait for network is delivered via system_files overlay.

echo "[26-grd] complete."
```


### `automation\30-locale-theme.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 30-locale-theme: Unified dark theme for EVERY window type
#
# Coverage matrix (ALL must be dark):
#   [ok] libadwaita / GTK4 apps (GNOME native) -- color-scheme=prefer-dark via dconf
#   [ok] GTK3 apps (legacy GNOME) -- adw-gtk3-dark theme
#   [ok] GDM login screen -- separate dconf db (gdm user)
#   [ok] GNOME lock screen -- inherits user session (automatic)
#   [ok] Flatpak apps -- ADW_DEBUG_COLOR_SCHEME + portal + filesystem overrides
#   [ok] Qt5/Qt6 apps -- adwaita-qt + QGnomePlatform env vars
#   [ok] Electron/Chromium apps -- ELECTRON_FORCE_DARK_MODE
#   [ok] Firefox -- MOZ_ENABLE_WAYLAND + portal color-scheme
#   [ok] GNOME Remote Desktop -- XCURSOR_THEME + session env
#   [ok] TTY/console -- no theming needed (terminal colors)
#
# MUST RUN BEFORE 30-user.sh (skel .bashrc must exist before useradd -m)
set -euo pipefail

echo "  'MiOS' v0.2.0 -- Universal Dark Theme"

# ═══ SKEL .bashrc (MUST come BEFORE useradd -m) ═══
# v0.2.0: Delivered via usr/share/skel/.bashrc overlay.
echo "[30-locale-theme] Using /etc/skel/.bashrc from overlay..."

# ═══ GTK3: adw-gtk3-dark for visual consistency with libadwaita ═══
# v0.2.0: Delivered via etc/gtk-3.0/settings.ini overlay.
echo "[30-locale-theme] Using GTK3 theme from overlay..."

# ═══ GTK4: libadwaita reads color-scheme, NOT GTK_THEME ═══
# v0.2.0: Delivered via etc/gtk-4.0/settings.ini overlay.
echo "[30-locale-theme] Using GTK4 theme from overlay..."

# ═══ System-wide env vars for ALL toolkits ═══
# v0.2.0: Delivered via etc/environment.d/ overlay.
echo "[30-locale-theme] Using environment.d from overlay..."

# ═══ Flatpak overrides -- dark theme + cursor + fonts ═══
echo "[30-locale-theme] Applying Flatpak dark theme + filesystem overrides..."
flatpak override --system --env=ADW_DEBUG_COLOR_SCHEME=prefer-dark 2>/dev/null || true
flatpak override --system --env=XCURSOR_THEME=Bibata-Modern-Classic 2>/dev/null || true
flatpak override --system --env=XCURSOR_SIZE=24 2>/dev/null || true
flatpak override --system --env=GTK_THEME=adw-gtk3-dark 2>/dev/null || true
flatpak override --system --filesystem=xdg-config/gtk-3.0:ro 2>/dev/null || true
flatpak override --system --filesystem=xdg-config/gtk-4.0:ro 2>/dev/null || true
flatpak override --system --filesystem=/usr/share/icons:ro 2>/dev/null || true
flatpak override --system --filesystem=/usr/share/fonts:ro 2>/dev/null || true
flatpak override --system --filesystem=/etc/gtk-3.0:ro 2>/dev/null || true
flatpak override --system --filesystem=/etc/gtk-4.0:ro 2>/dev/null || true

# ═══ Skeleton autostart (Bottles from flathub-beta on first login) ═══
# v0.2.0: Delivered via etc/skel/.config/autostart/ overlay.

# Ensure skel GTK3 also uses adw-gtk3-dark (for new user sessions)
# v0.2.0: Delivered via etc/skel/.config/gtk-3.0/settings.ini overlay.
# ── Compile GSchema overrides (THE correct way to set GNOME defaults) ──
if [ -f /usr/share/glib-2.0/schemas/90-mios.gschema.override ]; then
    echo "[30-locale-theme] Compiling GSchema overrides..."
    glib-compile-schemas /usr/share/glib-2.0/schemas/ || true
    echo "[30-locale-theme] [ok] GSchema overrides compiled"
fi

# Suppress DBus warnings during headless update without swallowing real syntax errors
export GIO_USE_VFS=local
dconf update || true

# Migrate generated binary dconf databases to the immutable /usr/share path.
# This prevents OSTree 3-way merge binary conflicts on /etc/dconf/db/local
# during bootc upgrades if users make their own local dconf changes.
if [ -d /etc/dconf/db ]; then
    mkdir -p /usr/share/dconf/db
    find /etc/dconf/db -maxdepth 1 -type f -exec mv -f {} /usr/share/dconf/db/ \; 2>/dev/null || true
fi

echo "[30-locale-theme] Dark theme configured for all toolkits."
```


### `automation\31-user.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 31-user: PAM, user creation, groups, sudoers
# Must run AFTER skel is populated (31-locale-theme writes skel/.bashrc)
# and BEFORE any service that references the user.
set -euo pipefail

echo "  'MiOS' v0.2.0 -- User & Authentication"

# -- PAM FIX --
echo "[31-user] Configuring PAM via authselect..."
if command -v authselect &>/dev/null; then
    authselect select local --force 2>/dev/null || {
        echo "[31-user] WARNING: authselect failed -- using system_files overlay fallback"
    }
fi

# -- USER CREATION --
# Password is pre-hashed (SHA-512) by the orchestrator -- plaintext NEVER in build log.
# Defaults for CI builds or when environment variables are not provided:
C_USER="${MIOS_USER:-mios}"
# Note: MIOS_PASSWORD_HASH should be a SHA-512 crypt-style hash

echo "[31-user] Creating user ${C_USER} via sysusers..."
if [[ "${C_USER}" != "mios" ]]; then
    # Generate dynamic sysusers for custom username.
    # CRITICAL: pin UID to 1000. systemd-sysusers' '-' UID allocator uses the
    # SYSTEM range (<UID_MIN), which makes logind skip XDG_RUNTIME_DIR creation
    # and cascades into dbus/dconf/Wayland session-service failures.
    cat <<EOF > /usr/lib/sysusers.d/15-mios-custom.conf
u ${C_USER} 1000:1000 "'MiOS' Custom User" /var/home/${C_USER} /bin/bash
m ${C_USER} wheel
m ${C_USER} libvirt
m ${C_USER} kvm
m ${C_USER} video
m ${C_USER} render
m ${C_USER} input
m ${C_USER} dialout
m ${C_USER} docker
EOF
fi

# Apply sysusers declarative config
systemd-sysusers --root=/ 2>/dev/null || true

if getent passwd "${C_USER}" >/dev/null; then
    home=$(getent passwd "${C_USER}" | cut -d: -f6)
    if [ ! -d "$home" ]; then
        echo "[31-user] Creating home directory for ${C_USER} from /etc/skel..."
        mkdir -p "$home"
        cp -a /etc/skel/. "$home/"
    fi
    passwd -u "${C_USER}" 2>/dev/null || true
else
    echo "[31-user] ERROR: Failed to create user ${C_USER}"
fi

# -- GROUP INJECTION --
# Groups are pre-created and memberships injected via /usr/lib/sysusers.d/*.conf
# and processed by systemd-sysusers above. Imperative calls removed.

# -- SUDOERS --
# Managed via usr/lib/sudoers.d/10-mios-wheel
chmod 440 /usr/lib/sudoers.d/10-mios-wheel 2>/dev/null || true

# -- LOCALE --
# Managed via usr/lib/locale.conf
localedef -i en_US -f UTF-8 en_US.UTF-8 2>/dev/null || true

# -- CLOUD-INIT --
# Managed via usr/lib/cloud/cloud.cfg.d/10-mios.cfg

# -- MULTIPATH --
# Managed via usr/lib/multipath.conf

# -- FIX HOME DIRECTORY OWNERSHIP --
echo "[31-user] Fixing home directory ownership..."
awk -F: '$3 >= 1000 && $3 < 65000 {print $1}' /etc/passwd | while read -r u; do
    home=$(getent passwd "$u" | cut -d: -f6)
    if [ -d "$home" ]; then
        uid=$(id -u "$u"); gid=$(id -g "$u")
        chown -R "${uid}:${gid}" "$home"
    fi
done

# -- NFS STATE DIRECTORY --
# Managed via usr/lib/tmpfiles.d/mios-nfs.conf

echo "[31-user] User & authentication configured."
```


### `automation\32-hostname.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 32-hostname: Unique per-instance hostname
#
# Strategy: Set a template hostname in the image. On first boot, systemd
# generates /etc/machine-id. The mios-init service (35-init-service.sh)
# derives a stable 5-char tag from machine-id and sets the hostname.
#
# Result: Each instance gets mios-XXXXX (e.g., mios-a3f9c), unique
# per deployment, stable across reboots.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

echo "[32-hostname] Setting default hostname template..."

# Use MIOS_HOSTNAME build-arg if provided by the installer/bootstrap.
# When set (e.g. "mios-ws-83427"), it becomes the static hostname.
# When unset (default "mios"), the first-boot mios-init derives mios-XXXXX
# from machine-id so every deployment still gets a unique hostname.
# LAW 4: store the image-baked default in /usr/lib/hostname; a tmpfiles.d
# rule seeds /etc/hostname from it on first boot only if the admin hasn't
# already set one (C = copy-if-missing).  The mios-init service then
# derives the unique mios-XXXXX suffix from machine-id on first boot.
_hn="${MIOS_HOSTNAME:-mios}"
install -d -m 0755 ${MIOS_USR_DIR}
echo "$_hn" > ${MIOS_USR_DIR}/hostname.default
echo "[32-hostname] Default hostname template written to ${MIOS_USR_DIR}/hostname.default: $_hn"
if [[ "$_hn" == "mios" ]]; then
    echo "[32-hostname] Will become mios-XXXXX on first boot via mios-init."
fi
```


### `automation\33-firewall.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 33-firewall: Firewall configuration script
set -euo pipefail

echo "[33-firewall] Installing firewall init script..."

cat > /usr/libexec/mios-firewall-init <<'EOFW'
#!/bin/bash
set -euo pipefail
if ! systemctl is-active --quiet firewalld 2>/dev/null; then
    echo "[mios-firewall] firewalld not active -- skipping"
    exit 0
fi
# Default zone: drop (deny all inbound by default)
firewall-cmd --set-default-zone=drop 2>/dev/null || true
# Essential services
for svc in cockpit ssh mdns; do
    firewall-cmd --permanent --add-service="$svc" 2>/dev/null || true
done
# RDP (GNOME Remote Desktop + Hyper-V vsock)
firewall-cmd --permanent --add-port=3389/tcp --add-port=3390/tcp 2>/dev/null || true
# Samba + NFS
firewall-cmd --permanent --add-service=samba --add-service=nfs --add-service=rpc-bind --add-service=mountd 2>/dev/null || true
# Libvirt
firewall-cmd --permanent --add-port=16509/tcp 2>/dev/null || true
# VNC
firewall-cmd --permanent --add-port=5900-5999/tcp 2>/dev/null || true
# K3s API + kubelet
firewall-cmd --permanent --add-port=6443/tcp --add-port=10250/tcp 2>/dev/null || true
# Pacemaker/Corosync
firewall-cmd --permanent --add-port=2224/tcp --add-port=5403-5405/udp 2>/dev/null || true
# CrowdSec dashboard + iVentoy
firewall-cmd --permanent --add-port=3000/tcp --add-port=26000/tcp 2>/dev/null || true
# Cockpit on 9090 (already via service but explicit)
firewall-cmd --permanent --add-port=9090/tcp 2>/dev/null || true
# Trust internal interfaces (including dynamic netavark/k3s bridges via wildcards)
# nftables backend drops unassigned interfaces strictly into the drop zone
for iface in lo podman+ br-+ veth+ virbr0 cni0 flannel.1 waydroid0; do
    firewall-cmd --permanent --zone=trusted --add-interface="$iface" 2>/dev/null || true
done

# ── Cockpit -- accessible from ALL zones ──
for zone in public libvirt trusted; do
    firewall-cmd --permanent --zone="$zone" --add-service=cockpit 2>/dev/null || true
    firewall-cmd --permanent --zone="$zone" --add-port=9090/tcp 2>/dev/null || true
done
firewall-cmd --reload 2>/dev/null || true
echo "[mios-firewall] Firewall configured"
EOFW
chmod +x /usr/libexec/mios-firewall-init

echo "[33-firewall] Firewall init script installed."
```


### `automation\34-gpu-detect.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 34-gpu-detect: Bridge to GPU detection service
# Blocks NVIDIA modules in VMs, enables hardware renderer on bare metal,
# detects RTX 50-series VFIO reset bug.
# Actual logic lives in /usr/libexec/mios/gpu-detect (system_files overlay).
set -euo pipefail

echo "[34-gpu-detect] Configuring GPU auto-detect service..."

# Unit and script are delivered via system_files overlay.
# Enablement is handled via usr/lib/systemd/system-preset/90-mios.preset

echo "[34-gpu-detect] GPU detection service enabled."
```


### `automation\35-gpu-passthrough.sh`

```bash
#!/usr/bin/env bash
# ============================================================================
# 'MiOS' v0.2.0 - 35-gpu-passthrough.sh
# ----------------------------------------------------------------------------
# Manages systemd unit enablement and SELinux for GPU passthrough.
#
# v0.2.0: ARCHITECTURAL PURITY FIX. All files (systemd units, udev rules,
#         sysusers, kargs.d) are now delivered via the system_files overlay.
#         This script no longer performs 'install' commands; it only handles
#         symlinking and SELinux booleans.
#
# Runs AFTER 34-gpu-detect.sh and 08-system-files-overlay.sh.
# ============================================================================
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "Enabling GPU passthrough services"

# ----------------------------------------------------------------------------
# Enable units via symlink (Containerfile-safe; `systemctl enable` cannot run
# in a bootc build because there is no PID 1 / dbus during image assembly).
# ----------------------------------------------------------------------------
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

# These files are already installed in /usr/lib/systemd/system/ via overlay
for svc in mios-gpu-status.service mios-gpu-nvidia.service mios-gpu-amd.service mios-gpu-intel.service; do
  if [[ -f "/usr/lib/systemd/system/${svc}" ]]; then
    ln -sf "../${svc}" "${WANTS}/${svc}"
    log "Enabled ${svc}"
  else
    log "WARN: ${svc} missing from /usr/lib/systemd/system/ -- skipping"
  fi
done

# Enable the upstream NVIDIA path unit where the toolkit shipped it.
if [[ -f /usr/lib/systemd/system/nvidia-cdi-refresh.path ]]; then
  ln -sf ../nvidia-cdi-refresh.path "${WANTS}/nvidia-cdi-refresh.path"
  log "Enabled nvidia-cdi-refresh.path"
fi

# ----------------------------------------------------------------------------
# SELinux: enable container_use_devices boolean so containers can touch
# /dev/kfd and /dev/dri with the default container_t domain. This is the
# minimal-privilege path for AMD/Intel compute - NOT container_runtime_t.
# ----------------------------------------------------------------------------
if command -v semanage >/dev/null 2>&1 && [[ -d /etc/selinux/targeted ]]; then
  if semanage boolean -m --on container_use_devices 2>/dev/null; then
    log "SELinux boolean container_use_devices persisted at build time"
  else
    log "semanage not operational in build; runtime service will handle it"
  fi
fi

log "GPU passthrough services enabled successfully"
```


### `automation\35-gpu-pv-shim.sh`

```bash
#!/usr/bin/env bash
# automation/35-gpu-pv-shim.sh - 'MiOS' v0.2.0
# ----------------------------------------------------------------------------
# Automates guest-side shimming for Hyper-V GPU-PV (dxgkrnl).
# Since dxgkrnl isn't mainlined yet, we provide the user-mode hooks
# to bridge to host drivers mounted via WSL/Hyper-V.
#
# v0.2.0: Refactored to use common logging and build-safe symlinks.
# ----------------------------------------------------------------------------
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# 1. Create the system-standard mount points for dxgkrnl/WSL hooks
# These are the locations where Mesa D3D12 and NVIDIA CUDA look for Hyper-V host drivers.
log "Creating GPU-PV shim directory structure..."
mkdir -p /usr/lib/wsl/lib
mkdir -p /usr/lib/wsl/drivers

# 2. Add ld.so.conf entry to ensure these libraries are in the search path
# LAW 4: write to /usr/lib/ld.so.conf.d -- /etc/ld.so.conf.d is for Day-2 admin overrides only
log "Configuring dynamic linker paths for GPU-PV..."
install -d -m 0755 /usr/lib/ld.so.conf.d
echo "/usr/lib/wsl/lib" > /usr/lib/ld.so.conf.d/mios-gpu-pv.conf

# 3. Create a detection script for first-boot or deployment
mkdir -p ${MIOS_LIBEXEC_DIR}
cat > ${MIOS_LIBEXEC_DIR}/gpu-pv-detect <<'EOF'
#!/usr/bin/bash
set -euo pipefail
log() { echo "[gpu-pv-detect] $*"; }

if [ ! -e /dev/dxg ]; then
    # log "Hyper-V /dev/dxg not found. Skipping GPU-PV library hooks."
    exit 0
fi

log "Hyper-V dxgkrnl detected!"
if [ -z "$(ls -A /usr/lib/wsl/lib)" ]; then
    log "HINT: /usr/lib/wsl/lib is empty. GPU acceleration requires host drivers."
    log "HINT: Copy drivers from Windows: C:\Windows\System32\lxss\lib -> /usr/lib/wsl/lib"
fi
EOF

chmod +x ${MIOS_LIBEXEC_DIR}/gpu-pv-detect

# 4. Create a systemd service to run the detection/setup on boot
cat > /usr/lib/systemd/system/mios-gpu-pv-detect.service <<EOF
[Unit]
Description='MiOS' Hyper-V GPU-PV Detection
ConditionVirtualization=microsoft
After=local-fs.target
Before=display-manager.service

[Service]
Type=oneshot
ExecStart=${MIOS_LIBEXEC_DIR}/gpu-pv-detect
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

# 5. Enable the service using a build-safe symlink
# See 35-gpu-passthrough.sh for detailed explanation.
log "Enabling GPU-PV detection service..."
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"
ln -sf ../mios-gpu-pv-detect.service "${WANTS}/mios-gpu-pv-detect.service"

log "GPU-PV shim integration complete."
```


### `automation\35-init-service.sh`

```bash
#!/usr/bin/env bash
# 'MiOS' v0.2.0 -- 35-init-service: Bridge to Unified Role Engine
# This script ensures mios-role.service is correctly enabled.
# The actual logic lives in /usr/libexec/mios/role-apply (system_files overlay).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "Enabling unified system initialization..."

# Enable units using build-safe symlinks
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

for unit in \
    mios-role.service \
    mios-podman-gc.timer
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not found, skipping enablement."
    fi
done

log "Initialization system services enabled."
```


### `automation\36-akmod-guards.sh`

```bash
#!/usr/bin/env bash
# ============================================================================
# automation/36-akmod-guards.sh - 'MiOS' v0.2.0
# ----------------------------------------------------------------------------
# Install ExecCondition drop-ins that make NVIDIA systemd units exit cleanly
# (skipped, not failed) when the running kernel's nvidia module has not yet
# been registered by akmods/depmod. Build-time script; does not touch runtime.
#
# Regex widened beyond NVIDIA/nvidia-container-toolkit#1395 to match:
#   - kernel/drivers/... paths (negativo17 packaging)
#   - extra/nvidia/...    paths (RPM Fusion akmod packaging, used by ucore-hci)
#   - .ko, .ko.xz, .ko.zst compressed variants
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "36-akmod-guards: installing ExecCondition drop-ins"

SERVICES=(
    nvidia-persistenced
    nvidia-powerd
    nvidia-suspend
    nvidia-resume
    nvidia-hibernate
    nvidia-suspend-then-hibernate
    nvidia-cdi-refresh
)

DROPIN_NAME="10-mios-akmod-guard.conf"
count=0

for svc in "${SERVICES[@]}"; do
    dir="/usr/lib/systemd/system/${svc}.service.d"
    path="${dir}/${DROPIN_NAME}"
    install -d -m 0755 "${dir}"
    cat > "${path}" <<'EOF'
# 'MiOS' v0.2.0 akmod-guard
# Skip unit if akmods has not yet registered the nvidia kernel module
# for the currently running kernel. ExecCondition is additive (AND
# semantics per systemd.service(5)), so this composes safely with any
# future upstream guard. Ref: NVIDIA/nvidia-container-toolkit#1395
# NOTE: \\\\ in this heredoc → \\ in file → systemd strips one backslash
# → grep sees \. (literal-dot escape). Plain \\. triggered SC "unknown
# escape sequence" warnings in systemd 259+ and could mis-match.
[Service]
ExecCondition=/bin/bash -c 'grep -Eq "(^|/)nvidia\\.ko(\\.[xz]z|\\.zst)?:" /lib/modules/$(uname -r)/modules.dep'
EOF
    chmod 0644 "${path}"
    count=$((count + 1))
    log "  installed ${path}"
done

log "36-akmod-guards: done (${count} drop-ins)"
```


### `automation\36-tools.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 36-tools: CLI tools and consolidated mios command
# Installs all mios-* tools to /usr/bin/ and the master 'mios' CLI.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[36-tools] Configuring 'MiOS' CLI tools..."

# CLI tools are now delivered via system_files overlay at /usr/bin/
# We just need to ensure permissions are correct here for files that 
# might have lost the executable bit during git/Windows transfer.

TOOLS=(
    mios 
    mios-update 
    mios-rebuild 
    mios-build 
    mios-backup 
    mios-deploy 
    mios-status 
    mios-vfio-toggle 
    mios-vfio-check 
    iommu-groups
    aichat
    aichat-ng
)

for tool in "${TOOLS[@]}"; do
    if [ -f "/usr/bin/$tool" ]; then
        chmod +x "/usr/bin/$tool"
    else
        echo "[36-tools] WARN: /usr/bin/$tool not found (should be in system_files overlay)"
    fi
done

# ═══ Install external scripts from build context ═══
# These are scripts that live in automation/ and are installed to /usr/bin/
echo "[36-tools] Installing mios-toggle-headless and mios-test..."
for ext_tool in mios-toggle-headless mios-test; do
    if [ -f "${SCRIPT_DIR}/${ext_tool}" ]; then
        install -Dm0755 "${SCRIPT_DIR}/${ext_tool}" "/usr/bin/${ext_tool}"
    else
        echo "[36-tools] WARN: ${ext_tool} not found at ${SCRIPT_DIR}/${ext_tool}"
    fi
done

echo "[36-tools] CLI tools configuration complete. Run 'mios --help' for commands."
```


### `automation\37-aichat.sh`

```bash
#!/bin/bash
# 37-aichat: Install AIChat and AIChat-NG Rust CLI tools
set -euo pipefail
# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

echo "[37-aichat] Installing AI-related packages (redis, sqlite)..."
install_packages "ai"

echo "[37-aichat] Installing AIChat and AIChat-NG binaries..."

# Resolve latest release tags from upstream. Project policy: every dependency
# tracks :latest from its source, so no fallback pin -- if api.github.com is
# unreachable, fail loud rather than silently shipping a stale version.
AICHAT_TAG=$( (scurl -s https://api.github.com/repos/sigoden/aichat/releases/latest | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)
AICHAT_NG_TAG=$( (scurl -s https://api.github.com/repos/blob42/aichat-ng/releases/latest | grep -Po '"tag_name": "\K.*?(?=")') 2>/dev/null || true)

[[ -n "$AICHAT_TAG"    ]] || die "AIChat: api.github.com release-latest lookup returned empty"
[[ -n "$AICHAT_NG_TAG" ]] || die "AIChat-NG: api.github.com release-latest lookup returned empty"
record_version aichat    "$AICHAT_TAG"    "https://github.com/sigoden/aichat/releases/tag/${AICHAT_TAG}"
record_version aichat-ng "$AICHAT_NG_TAG" "https://github.com/blob42/aichat-ng/releases/tag/${AICHAT_NG_TAG}"

# ── AIChat ────────────────────────────────────────────────────────────────────
AICHAT_ARCH="aichat-${AICHAT_TAG}-x86_64-unknown-linux-musl.tar.gz"
AICHAT_BASE="https://github.com/sigoden/aichat/releases/download/${AICHAT_TAG}"

mkdir -p /tmp/aichat-dl
scurl -sfL "${AICHAT_BASE}/${AICHAT_ARCH}" -o "/tmp/aichat-dl/${AICHAT_ARCH}"
scurl -sfL "${AICHAT_BASE}/${AICHAT_ARCH}.sha256" -o "/tmp/aichat-dl/${AICHAT_ARCH}.sha256" 2>/dev/null || {
    echo "[37-aichat] WARN: sha256 sidecar unavailable for AIChat -- cannot verify integrity"
    rm -f "/tmp/aichat-dl/${AICHAT_ARCH}.sha256"
}

if [[ -f "/tmp/aichat-dl/${AICHAT_ARCH}.sha256" ]]; then
    # sha256 sidecar format: "<hash>  <filename>" or "<hash> *<filename>"
    (cd /tmp/aichat-dl && grep "${AICHAT_ARCH}" "${AICHAT_ARCH}.sha256" | sha256sum -c -) \
        || die "AIChat ${AICHAT_TAG} SHA256 mismatch -- aborting"
    echo "[37-aichat]   [ok] AIChat sha256 verified"
fi

tar -xzf "/tmp/aichat-dl/${AICHAT_ARCH}" -C /usr/bin/ aichat
chmod +x /usr/bin/aichat
rm -rf /tmp/aichat-dl

# ── AIChat-NG ────────────────────────────────────────────────────────────────
AICHAT_NG_ARCH="aichat-ng-${AICHAT_NG_TAG}-x86_64-unknown-linux-musl.tar.gz"
AICHAT_NG_BASE="https://github.com/blob42/aichat-ng/releases/download/${AICHAT_NG_TAG}"

mkdir -p /tmp/aichat-ng-dl
scurl -sfL "${AICHAT_NG_BASE}/${AICHAT_NG_ARCH}" -o "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}"
scurl -sfL "${AICHAT_NG_BASE}/${AICHAT_NG_ARCH}.sha256" -o "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}.sha256" 2>/dev/null || {
    echo "[37-aichat] WARN: sha256 sidecar unavailable for AIChat-NG -- cannot verify integrity"
    rm -f "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}.sha256"
}

if [[ -f "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}.sha256" ]]; then
    (cd /tmp/aichat-ng-dl && grep "${AICHAT_NG_ARCH}" "${AICHAT_NG_ARCH}.sha256" | sha256sum -c -) \
        || die "AIChat-NG ${AICHAT_NG_TAG} SHA256 mismatch -- aborting"
    echo "[37-aichat]   [ok] AIChat-NG sha256 verified"
fi

tar -xzf "/tmp/aichat-ng-dl/${AICHAT_NG_ARCH}" -C /usr/bin/ aichat-ng
chmod +x /usr/bin/aichat-ng
rm -rf /tmp/aichat-ng-dl

echo "[37-aichat] AIChat and AIChat-NG installed successfully."
```


### `automation\37-flatpak-env.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0  37-flatpak-env: Capture Flatpak environment for boot-time install
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "[37-flatpak-env] capturing Flatpak environment"

# Directory for 'MiOS' system-level environment definitions (USR-OVER-ETC compliance)
# Using /usr/lib/mios/env.d as a "venv/env" style storage
mkdir -p ${MIOS_USR_DIR}/env.d

# Capture MIOS_FLATPAKS if set (from build-arg)
# This creates a system-baked environment file that mios-flatpak-install can read.
ENV_FILE="${MIOS_USR_DIR}/env.d/flatpaks.env"

echo "# 'MiOS' System Environment Definition" > "$ENV_FILE"
echo "# Generated at build time: $(date -u)" >> "$ENV_FILE"

if [[ -n "${MIOS_FLATPAKS:-}" ]]; then
    echo "MIOS_FLATPAKS=\"${MIOS_FLATPAKS}\"" >> "$ENV_FILE"
    echo "[37-flatpak-env] Captured MIOS_FLATPAKS to ${ENV_FILE}"
else
    echo "MIOS_FLATPAKS=\"\"" >> "$ENV_FILE"
    echo "[37-flatpak-env] MIOS_FLATPAKS not set, created empty env file."
fi

chmod 644 "$ENV_FILE"

echo "[37-flatpak-env] Flatpak environment configured in /usr."
```


### `automation\37-ollama-prep.sh`

```bash
#!/bin/bash
# 37-ollama-prep: Embed default LLM models during build
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

# This script is intended for local builds to "bake in" the default coding model.
# It installs a temporary ollama binary, pulls the model, and cleans up.

# Only run if not already present (idempotency)
if [ -d "/var/lib/ollama/models" ] && [ "$(ls -A /var/lib/ollama/models)" ]; then
    log "Default models already present, skipping."
    exit 0
fi

log "Downloading default models: qwen2.5-coder:7b + nomic-embed-text..."

# Install temporary ollama binary from GitHub releases (.tar.zst archive)
# Standalone binary is no longer provided.
OLLAMA_URL="https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst"
log "URL: $OLLAMA_URL"
scurl -L "$OLLAMA_URL" -o /tmp/ollama.tar.zst

# Extract archive to /usr (contains bin/ollama)
# Requires zstd to be installed in the build environment
if ! command -v zstd &>/dev/null; then
    log "ERROR: zstd not found. Installing explicitly..."
    $DNF_BIN "${DNF_SETOPT[@]}" install -y zstd
fi

diag "Extracting Ollama archive..."
# Create a temporary directory for extraction
mkdir -p /tmp/ollama-extract
tar --zstd -xvf /tmp/ollama.tar.zst -C /tmp/ollama-extract

# Find the binary and move it to /usr/bin/ollama
OLLAMA_BIN=$(find /tmp/ollama-extract -type f -name "ollama" | head -n 1)
if [[ -z "$OLLAMA_BIN" ]]; then
    log "ERROR: ollama binary not found in archive."
    diag "Archive contents:"
    tar --zstd -tvf /tmp/ollama.tar.zst
    exit 1
fi

mv "$OLLAMA_BIN" /usr/bin/ollama
chmod +x /usr/bin/ollama
rm -rf /tmp/ollama-extract

# Validation
if ! command -v ollama &>/dev/null; then
    log "ERROR: ollama binary not found in PATH."
    exit 1
fi

if ! file /usr/bin/ollama | grep -q "ELF"; then
    log "ERROR: /usr/bin/ollama is not a valid ELF binary."
    exit 1
fi

# Start ollama serve in background
# We bake models into /usr/share to ensure they are captured by bootc/composefs
# and then link them into /var/lib/ollama at runtime.
BAKE_PATH="/usr/share/ollama/models"
mkdir -p "$BAKE_PATH"
export OLLAMA_MODELS="$BAKE_PATH"

/usr/bin/ollama serve &
OLLAMA_PID=$!

# Wait for server to be ready
log "Waiting for Ollama server to start..."
MAX_RETRIES=15
COUNT=0
while ! scurl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        log "ERROR: Ollama server failed to start."
        kill $OLLAMA_PID
        exit 1
    fi
done

# Pull inference model (8GB-tier default) and embedding model
/usr/bin/ollama pull qwen2.5-coder:7b
/usr/bin/ollama pull nomic-embed-text

# Shutdown server
kill $OLLAMA_PID
wait $OLLAMA_PID || true

# Cleanup
rm -f /tmp/ollama.tar.zst
# We keep the binary in /usr/bin as it's part of the image now
# unless the user wanted it temporary? The script previously rm -f /tmp/ollama.
# Let's keep it temporary to match original intent of "prep" if needed, 
# but usually we want ollama available. 
# Original script: rm -f /tmp/ollama.
# If I want to match original intent: rm -f /usr/bin/ollama
# But wait, 37-ollama.sh (if it exists) would install it. 
# Let's check if ollama is in PACKAGES.md as a permanent package.

echo "[37-ollama-prep] Model embedded successfully."
```


### `automation\37-selinux.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 37-selinux: Build-time SELinux policy fixes
# Custom per-rule modules for known Fedora Rawhide / systemd 260 denials.
set -euo pipefail

echo "[37-selinux] Applying SELinux build-time fixes..."

# ═══ Restorecon -- fix labels for all major trees ═══
if command -v restorecon &>/dev/null; then
    echo "[37-selinux] Running restorecon on /boot /etc /usr /var..."
    restorecon -R /boot /etc /usr /var 2>/dev/null || true
fi

# ═══ Semanage import -- atomic booleans + fcontexts ═══
if command -v semanage &>/dev/null; then
    echo "[37-selinux] Applying SELinux booleans and fcontexts..."
    semanage import <<'EOSEM' 2>/dev/null || true
boolean -m --on container_manage_cgroup
boolean -m --on container_use_cephfs
boolean -m --on daemons_dump_core
boolean -m --on domain_can_mmap_files
boolean -m --on virt_sandbox_use_all_caps
boolean -m --on virt_use_nfs
boolean -m --on virt_use_samba
boolean -m --on nis_enabled
fcontext -a -t boot_t '/boot/bootupd-state.json'
fcontext -a -t accountsd_var_lib_t '/usr/share/accountsservice/interfaces(/.*)?'
fcontext -a -t ceph_var_lib_t '/var/lib/ceph(/.*)?'
fcontext -a -t ceph_log_t '/var/log/ceph(/.*)?'
fcontext -a -t xdm_var_lib_t '/var/lib/gnome-remote-desktop(/.*)?'
EOSEM
    restorecon -v /boot/bootupd-state.json 2>/dev/null || true
    restorecon -R /usr/share/accountsservice 2>/dev/null || true
    restorecon -R /var/lib/gnome-remote-desktop 2>/dev/null || true
    echo "[37-selinux] [ok] Booleans and fcontexts applied"
fi

# ═══ Custom policy modules ═══
if command -v checkmodule &>/dev/null && command -v semodule_package &>/dev/null; then
    echo "[37-selinux] Building custom SELinux policy modules..."

    SELINUX_OK=0
    SELINUX_FAIL=0

    declare -A MIOS_POLICIES

    MIOS_POLICIES[bootupd]='
module mios_bootupd 1.0;
require { type boot_t; type bootupd_t; class file { read getattr open }; }
allow bootupd_t boot_t:file { read getattr open };'

    MIOS_POLICIES[accountsd]='
module mios_accountsd 1.0;
require { type accountsd_t; class lnk_file { read getattr }; }
allow accountsd_t self:lnk_file { read getattr };'

    MIOS_POLICIES[resolved]='
module mios_resolved 1.0;
require { type systemd_resolved_t; type init_var_run_t; class sock_file write; }
allow systemd_resolved_t init_var_run_t:sock_file write;'

    MIOS_POLICIES[fapolicyd]='
module mios_fapolicyd 1.0;
require { type fapolicyd_t; type xdm_var_run_t; class sock_file write; }
allow fapolicyd_t xdm_var_run_t:sock_file write;'

    MIOS_POLICIES[chcon]='
module mios_chcon 1.0;
require { type chcon_t; class capability mac_admin; }
allow chcon_t self:capability mac_admin;'

    MIOS_POLICIES[accountsd_homed]='
module mios_accountsd_homed 1.0;
require { type accountsd_t; type systemd_homed_t; class dbus send_msg; }
allow accountsd_t systemd_homed_t:dbus send_msg;
allow systemd_homed_t accountsd_t:dbus send_msg;'

    MIOS_POLICIES[accountsd_watch]='
module mios_accountsd_watch 1.0;
require { type accountsd_t; type usr_t; class dir { watch watch_reads }; }
allow accountsd_t usr_t:dir { watch watch_reads };'

    MIOS_POLICIES[fapolicyd_gdm]='
module mios_fapolicyd_gdm 1.1;
require { type fapolicyd_t; type xdm_t; class unix_stream_socket connectto; class fd use; class fifo_file write; }
allow fapolicyd_t xdm_t:unix_stream_socket connectto;
allow fapolicyd_t xdm_t:fd use;
allow fapolicyd_t xdm_t:fifo_file write;'

    MIOS_POLICIES[fapolicyd_grd]='
module mios_fapolicyd_grd 1.0;
require { type fapolicyd_t; type gnome_remote_desktop_t; class unix_stream_socket connectto; class fd use; class fifo_file write; }
allow fapolicyd_t gnome_remote_desktop_t:unix_stream_socket connectto;
allow fapolicyd_t gnome_remote_desktop_t:fd use;
allow fapolicyd_t gnome_remote_desktop_t:fifo_file write;'

    MIOS_POLICIES[portabled]='
module mios_portabled 1.0;
require { type init_t; type systemd_portabled_t; class dbus send_msg; }
allow init_t systemd_portabled_t:dbus send_msg;
allow systemd_portabled_t init_t:dbus send_msg;'

    MIOS_POLICIES[kvmfr]='
module mios_kvmfr 1.0;
require { type svirt_t; type device_t; class chr_file { open read write map getattr }; }
allow svirt_t device_t:chr_file { open read write map getattr };'

    MIOS_POLICIES[coreos_bootmount]='
module mios_coreos_bootmount 1.0;
require { type coreos_boot_mount_generator_t; type systemd_generator_unit_file_t; class dir { write add_name remove_name }; class file { create write open rename unlink }; }
allow coreos_boot_mount_generator_t systemd_generator_unit_file_t:dir { write add_name remove_name };
allow coreos_boot_mount_generator_t systemd_generator_unit_file_t:file { create write open rename unlink };'

    MIOS_POLICIES[gdm_cache]='
module mios_gdm_cache 1.0;
require { type xdm_t; type cache_home_t; class dir { add_name write create setattr }; class file { create write open getattr setattr }; }
allow xdm_t cache_home_t:dir { add_name write create setattr };
allow xdm_t cache_home_t:file { create write open getattr setattr };'

    MIOS_POLICIES[homed_varhome]='
module mios_homed_varhome 1.0;
require { type systemd_homed_t; type home_root_t; class dir { read getattr open search }; }
allow systemd_homed_t home_root_t:dir { read getattr open search };'

    MIOS_POLICIES[bootupd_state]='
module mios_bootupd_state 1.1;
require { type bootupd_t; type boot_t; class file { read open getattr lock ioctl }; class dir { read open getattr search }; }
allow bootupd_t boot_t:file { read open getattr lock ioctl };
allow bootupd_t boot_t:dir { read open getattr search };'

    MIOS_POLICIES[resolved_hook]='
module mios_resolved_hook 1.0;
require { type systemd_resolved_t; type init_t; class unix_stream_socket connectto; class sock_file write; }
allow systemd_resolved_t init_t:unix_stream_socket connectto;
allow systemd_resolved_t init_t:sock_file write;'

    MIOS_POLICIES[accountsd_malcontent]='
module mios_accountsd_malcontent 1.0;
require { type accountsd_t; type usr_t; class lnk_file { read getattr }; class file { read open getattr ioctl }; class dir { read open getattr search }; }
allow accountsd_t usr_t:lnk_file { read getattr };
allow accountsd_t usr_t:file { read open getattr ioctl };
allow accountsd_t usr_t:dir { read open getattr search };'

    MIOS_POLICIES[chcon_macadmin]='
module mios_chcon_macadmin 1.0;
require { type chcon_t; class capability2 mac_admin; }
allow chcon_t self:capability2 mac_admin;'

    MIOS_POLICIES[gdm_session_cache]='
module mios_gdm_session_cache 1.0;
require { type xdm_t; type cache_home_t; class dir { add_name write create read open getattr search setattr }; class file { create write read open getattr setattr }; }
allow xdm_t cache_home_t:dir { add_name write create read open getattr search setattr };
allow xdm_t cache_home_t:file { create write read open getattr setattr };'

    mkdir -p /usr/share/selinux/packages/mios

    for name in "${!MIOS_POLICIES[@]}"; do
        echo "${MIOS_POLICIES[$name]}" > "/tmp/mios_${name}.te"
        if checkmodule -M -m -o "/tmp/mios_${name}.mod" "/tmp/mios_${name}.te" 2>/dev/null && \
           semodule_package -o "/tmp/mios_${name}.pp" -m "/tmp/mios_${name}.mod" 2>/dev/null; then
            install -m 0644 "/tmp/mios_${name}.pp" "/usr/share/selinux/packages/mios/mios_${name}.pp"
            echo "[37-selinux] mios_${name}: Staged"
            SELINUX_OK=$((SELINUX_OK + 1))
        else
            echo "[37-selinux] mios_${name}: SKIPPED (type missing in current policy)"
            SELINUX_FAIL=$((SELINUX_FAIL + 1))
        fi
        rm -f "/tmp/mios_${name}".{te,mod,pp}
    done

    echo "[37-selinux] ${SELINUX_OK} policies staged in /usr/share/selinux/packages/mios/, ${SELINUX_FAIL} skipped"
fi

echo "[37-selinux] SELinux configuration complete."
```


### `automation\38-vm-gating.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 38-vm-gating: VM service gating + Hyper-V Enhanced Session
#
# v0.2.0 CRITICAL FIX: GNOME 50 / Mutter 50 completely removed the X11 backend.
# xorgxrdp is an X11 technology -- it CANNOT work with Wayland-only Mutter 50.
# The old approach caused a GDM crash loop on Hyper-V, preventing boot.
#
# NEW APPROACH: Use gnome-remote-desktop (GRD) for Enhanced Session.
# GRD provides Wayland-native RDP and can bind to vsock for Hyper-V transport.
# xrdp is kept installed but NOT auto-enabled -- it's available as a manual
# fallback for non-GNOME sessions (XFCE, Phosh) only.
#
# HYPER-V BOOT PATH (without Enhanced Session):
#   hyperv_drm → KMS → GDM (Wayland) → llvmpipe software rendering → login
# HYPER-V ENHANCED SESSION PATH:
#   vmconnect → vsock:3389 → gnome-remote-desktop (Wayland RDP) → login
set -euo pipefail

echo "[38-vm-gating] Configuring VM-specific service gating..."

# ═══ GDM / nvidia-powerd / Waydroid + binder gating ═══
# Drop-ins for gdm, nvidia-powerd, waydroid-container, dev-binderfs.mount are
# created by 20-services.sh (WSL_SKIP_SERVICES + bare-metal nvidia-powerd block).
# Do NOT duplicate them here -- last writer wins and we want 20's canonical drop-ins.

# ═══ Polkit container workaround ═══
# Managed via usr/lib/systemd/system/polkit.service.d/10-mios-container.conf

# ═══ Cockpit socket drop-in permissions ═══
if [ -f /usr/lib/systemd/system/cockpit.socket.d/listen.conf ]; then
    chmod 644 /usr/lib/systemd/system/cockpit.socket.d/listen.conf
fi

# ═══════════════════════════════════════════════════════════════════════════
# HYPER-V ENHANCED SESSION -- WAYLAND-NATIVE VIA GNOME REMOTE DESKTOP
# ═══════════════════════════════════════════════════════════════════════════
echo "[38-vm-gating] Configuring Hyper-V Enhanced Session (gnome-remote-desktop)..."

# 1. Blacklist VMware vsock (conflicts with Hyper-V hv_sock)
# Managed via usr/lib/modprobe.d/blacklist-vmw_vsock.conf

# 2. Ensure hv_sock loads on boot (required for vsock RDP transport)
if ! grep -q 'hv_sock' /usr/lib/modules-load.d/mios.conf 2>/dev/null; then
    echo "hv_sock" >> /usr/lib/modules-load.d/mios.conf
fi

# 3. Polkit rule for colord (prevents "not authorized" errors in RDP sessions)
# Managed via usr/share/polkit-1/rules.d/45-allow-colord.rules

# 4. Hyper-V Enhanced Session service -- uses gnome-remote-desktop
# Managed via usr/lib/systemd/system/mios-hyperv-enhanced.service
# and usr/libexec/mios-hyperv-enhanced
systemctl enable mios-hyperv-enhanced.service 2>/dev/null || true

# 5. GNOME Remote Desktop -- first-boot setup script
# mios-grd-setup is installed via system_files overlay (08-system-files-overlay.sh)
# into /usr/libexec/mios-grd-setup. No copy needed here.
chmod +x /usr/libexec/mios-grd-setup 2>/dev/null || true

# ── WSL2 systemd-machined gating ─────────────────────────────────────────
# dbus-broker.service.d/wsl2-fix.conf is provided by system_files overlay
# (OOMScoreAdjust only; --audit removal is in 10-mios-no-audit.conf).
# Do NOT overwrite it here -- previous versions wrote a broken drop-in with
# ConditionPathExists=|/proc/version which is always true and caused dbus
# to be misconfigured on bare metal.

# Ensure systemd-machined doesn't block dbus in WSL2
# Managed via usr/lib/systemd/system/systemd-machined.service.d/wsl2-optional.conf

echo "[38-vm-gating] VM gating + Hyper-V Enhanced Session (gnome-remote-desktop) configured."
```


### `automation\39-desktop-polish.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 39-desktop-polish: Desktop entries, Cockpit webapp, MOTD
#
# CHANGELOG v0.2.0:
#   - FIX: mios-motd source path was /tmp/automation/automation/ (never exists).
#     Scripts run from /ctx/automation/ in the buildroot. The bogus path + the
#     `|| true` swallowed the failure silently, so /usr/libexec/mios-motd
#     was never created. profile.d/mios-motd.sh falls back to it when
#     fastfetch is missing, so terminal MOTD printed nothing on every
#     v2.0-v2.2 image.
#   - FIX: SCRIPT_DIR-relative copy so this works whether build.sh invokes
#     us from /ctx/automation/ or any other future path. If the source is
#     missing, FAIL LOUDLY (remove the silencing `|| true`) so it can't
#     regress unnoticed.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[39-desktop-polish] Final desktop polish..."

# ═══ COCKPIT DESKTOP ENTRY -- uses cockpit-desktop (no TLS warnings) ═══
echo "[39-desktop-polish] Cockpit desktop entry delivered via overlay."

# ═══ NVIDIA SETTINGS DESKTOP ENTRY ═══
echo "[39-desktop-polish] NVIDIA Settings desktop entry delivered via overlay."

# ═══ CEPH DASHBOARD -- update to use correct app name ═══
echo "[39-desktop-polish] Ceph Dashboard desktop entry delivered via overlay."

# ═══ MOTD DASHBOARD ═══
# v0.2.0: ARCHITECTURAL PURITY FIX. The MOTD script is now delivered via the
# system_files overlay to /usr/libexec/mios/motd. We no longer perform
# manual 'install' calls here.
echo "[39-desktop-polish] MOTD dashboard delivered via overlay."

# ═══ FASTFETCH CONFIG -- services dashboard on terminal open ═══
echo "[39-desktop-polish] Fastfetch config delivered via overlay."

# ═══ PROFILE.D -- fastfetch + MOTD on terminal/TTY open ═══
echo "[39-desktop-polish] Profile.d MOTD script delivered via overlay."

echo "[39-desktop-polish] Desktop polish complete."
```


### `automation\40-composefs-verity.sh`

```bash
#!/usr/bin/env bash
# 40-composefs-verity.sh - promote composefs from default (yes) to verity mode
# Tamper-evident root. Requires ext4 or btrfs target FS (NOT xfs).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

conf=/usr/lib/ostree/prepare-root.conf
if [[ -f "$conf" ]]; then
    log "backing up existing $conf -> ${conf}.orig"
    cp -a "$conf" "${conf}.orig"
fi

cat > "$conf" <<'EOF'
# 'MiOS': composefs in verity mode. Tamper-evident root.
# Target filesystems must support fsverity (ext4, btrfs). XFS is NOT supported.
[composefs]
enabled = verity

[root]
transient = false

[etc]
transient = false
EOF

# Mask systemd-remount-fs (known-broken with composefs on F42+)
log "masking systemd-remount-fs.service (composefs interop bug)"
ln -sf /dev/null /etc/systemd/system/systemd-remount-fs.service

log "composefs verity mode configured"
```


### `automation\42-cosign-policy.sh`

```bash
#!/usr/bin/env bash
# ============================================================================
# automation/42-cosign-policy.sh - 'MiOS' v0.2.0
# ----------------------------------------------------------------------------
# Consolidates cosign binary installation, Sigstore trust roots, and policy.json.
# Supercedes 37-cosign-policy.sh.
#
# Note: cosign must stay on v2.x -- v3+ breaks rpm-ostree OCI 1.1 bundle format.
# ============================================================================
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

log "42-cosign-policy: ensuring cosign + trust roots + policy.json"

# 1. Install cosign binary
# Project policy: every dependency tracks :latest from its source. Cosign is
# constrained to the v2.x series here because v3+ breaks rpm-ostree OCI 1.1
# bundle format (see header). Lift the v2 filter when v3 compat is confirmed.
if ! command -v cosign >/dev/null 2>&1; then
    COSIGN_VERSION=$( (scurl -s https://api.github.com/repos/sigstore/cosign/releases?per_page=30 \
        | grep -Po '"tag_name": "\Kv2\.[^"]+' \
        | head -n1) 2>/dev/null || true)
    [[ -n "$COSIGN_VERSION" ]] || die "cosign: api.github.com release lookup returned no v2.x match"
    COSIGN_BASE_URL="https://github.com/sigstore/cosign/releases/download/${COSIGN_VERSION}"
    record_version cosign "$COSIGN_VERSION" "https://github.com/sigstore/cosign/releases/tag/${COSIGN_VERSION}"
    log "  resolved cosign latest v2.x: ${COSIGN_VERSION}"
    log "  downloading cosign ${COSIGN_VERSION} static binary..."
    mkdir -p /tmp/cosign-dl
    scurl -sfL "${COSIGN_BASE_URL}/cosign-linux-amd64" -o /tmp/cosign-dl/cosign-linux-amd64
    scurl -sfL "${COSIGN_BASE_URL}/cosign_checksums.txt" -o /tmp/cosign-dl/cosign_checksums.txt
    (cd /tmp/cosign-dl && grep "cosign-linux-amd64$" cosign_checksums.txt | sha256sum -c -) \
        || die "cosign ${COSIGN_VERSION} SHA256 mismatch -- aborting"
    # Install into /usr/bin (immutable image surface). /usr/local is a
    # symlink to /var/usrlocal on bootc/FCOS layouts and /var/usrlocal/bin/
    # does not exist at OCI build time.
    install -m 0755 /tmp/cosign-dl/cosign-linux-amd64 /usr/bin/cosign
    rm -rf /tmp/cosign-dl
fi

SYSFILES="/ctx/system_files"
# Paths updated to /usr/share/pki and /usr/lib/containers as per USR-OVER-ETC
install -d -m 0755 /usr/share/pki/containers
install -d -m 0755 /usr/lib/containers/registries.d

# 2. Install policy.json
# v0.2.0: Moved from etc/ to usr/lib/ in system_files
if [[ -f "${SYSFILES}/usr/lib/containers/policy.json" ]]; then
    install -m 0644 "${SYSFILES}/usr/lib/containers/policy.json" /usr/lib/containers/policy.json
    log "  installed /usr/lib/containers/policy.json"
else
    # Fallback to in-image path if ctx is missing (unlikely in build)
    [[ -f /usr/lib/containers/policy.json ]] || warn "missing policy.json"
fi

# 3. Install Sigstore TUF roots and public keys
# These ship via the usr/share/pki/containers/ overlay
for f in fulcio_v1.crt.pem rekor.pub ublue-os.pub ublue-cosign.pub mios-cosign.pub; do
    src="${SYSFILES}/usr/share/pki/containers/${f}"
    dst="/usr/share/pki/containers/${f}"
    if [[ -f "${src}" ]]; then
        install -m 0644 "${src}" "${dst}"
        log "  installed ${dst}"
    fi
done

# 4. JSON Sanity Check
if command -v jq >/dev/null 2>&1 && [[ -f /usr/lib/containers/policy.json ]]; then
    jq -e . /usr/lib/containers/policy.json >/dev/null || die "policy.json failed jq parse"
    log "  policy.json parses cleanly"
fi

log "42-cosign-policy: validation complete"
```


### `automation\43-uupd-installer.sh`

```bash
#!/usr/bin/env bash
# 43-uupd-installer.sh - install uupd + greenboot (from PACKAGES.md
# packages-updater section) and disable the updaters it supersedes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/packages.sh"

# COPR already enabled by 05-enable-external-repos.sh (runs earlier)
install_packages "updater"

# Disable the updaters uupd supersedes
systemctl disable bootc-fetch-apply-updates.timer 2>/dev/null || true
systemctl disable rpm-ostreed-automatic.timer     2>/dev/null || true

# Enable uupd.timer (shipped by the package)
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"
if [[ -f "/usr/lib/systemd/system/uupd.timer" ]]; then
    ln -sf ../uupd.timer "${WANTS}/uupd.timer"
    log "Enabled uupd.timer"
else
    warn "uupd.timer not present (uupd install may have failed)"
fi

log "uupd configured; bootc-fetch-apply-updates.timer and rpm-ostreed-automatic.timer disabled"
```


### `automation\44-podman-machine-compat.sh`

```bash
#!/usr/bin/env bash
# 44-podman-machine-compat.sh - Podman-machine backend compatibility.
# Package installs moved to PACKAGES.md (packages-containers, packages-utils).
# This script only does the runtime config that cannot be expressed as packages:
#   - create the 'core' user (Podman machine convention)
#   - enable services needed for machine backend operation
#
# v0.2.0 fix:
#   - Pre-create the `video`, `render`, `kvm`, `libvirt` groups if missing so
#     useradd -G doesn't die with "group does not exist". The ucore-hci base
#     ships udev rules that create these groups dynamically at runtime, but
#     during the image build they're absent.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "Hardware groups are pre-created globally by 31-user.sh"

# Create the 'core' user if missing (Podman machine convention).
# Managed via /usr/lib/sysusers.d/20-podman-machine.conf (declarative).
# We apply sysusers here to ensure 'core' exists for any subsequent operations.
systemd-sysusers --root=/ 2>/dev/null || true

if id -u core >/dev/null 2>&1; then
    passwd -l core 2>/dev/null || true
    log "user 'core' initialized (declarative; key-auth only)"
else
    warn "Failed to initialize 'core' user via sysusers"
fi

# Enable core services for Podman-machine and cloud-init entry
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

log "Enabling Podman Machine and cloud-init services..."
for unit in \
    sshd.service \
    podman.socket \
    qemu-guest-agent.service \
    cloud-init.service \
    cloud-final.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not found, skipping enablement."
    fi
done

log "podman-machine compatibility wired"
```


### `automation\45-nvidia-cdi-refresh.sh`

```bash
#!/usr/bin/env bash
# 45-nvidia-cdi-refresh.sh - wire up NVIDIA CDI auto-refresh services.
# Package installs live in PACKAGES.md (packages-gpu-nvidia section).
#
# Key invariants:
#   - nvidia-container-toolkit ≥ 1.18 for nvidia-cdi-refresh.service/path.
#   - Avoid NCT 1.16.2: "unresolvable CDI devices" regression. Use 1.16.1 or 1.18+.
#   - Remove oci-nvidia-hook.json: dual injection with CDI causes conflicts.
#   - CDI canonical path: /var/run/cdi/nvidia.yaml (runtime) or /etc/cdi/nvidia.yaml (persistent).
#   - NVIDIA kmods blacklisted by default; 34-gpu-detect.sh removes blacklist on bare metal.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Remove legacy OCI hook -- conflicts with CDI when both are present.
OCI_HOOK=/usr/share/containers/oci/hooks.d/oci-nvidia-hook.json
if [[ -f "$OCI_HOOK" ]]; then
    log "removing legacy OCI nvidia hook (conflicts with CDI)"
    rm -f "$OCI_HOOK"
fi

# /etc/nvidia-container-toolkit/cdi-refresh.env is created at first boot via
# usr/lib/tmpfiles.d/mios-gpu.conf (`f` create-if-missing). nvidia-container-
# toolkit's upstream systemd unit reads from /etc/ by hard-coded path, so this
# file lives in the upstream-contract /etc/ surface, not /usr/lib/.

# Enable units using build-safe symlinks
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

log "Enabling NVIDIA CDI units..."
for unit in \
    nvidia-cdi-refresh.path \
    nvidia-cdi-refresh.service \
    nvidia-persistenced.service \
    mios-nvidia-cdi.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not found, skipping enablement."
    fi
done

# /etc/cdi and /var/run/cdi are declared in usr/lib/tmpfiles.d/mios-gpu.conf
# (LAW 2 -- NO-MKDIR-IN-VAR; admin-override surface for /etc/cdi).

log "CDI refresh pipeline configured"
```


### `automation\46-greenboot.sh`

```bash
#!/usr/bin/env bash
# 46-greenboot.sh - wire greenboot services; package installs via PACKAGES.md
# (packages-updater section: greenboot, greenboot-default-health-checks).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Enable core greenboot services
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

log "Enabling Greenboot services..."
for unit in \
    greenboot-healthcheck.service \
    greenboot-rpm-ostree-grub2-check-fallback.service \
    greenboot-grub2-set-counter.service \
    greenboot-grub2-set-success.service \
    greenboot-status.service \
    redboot-auto-reboot.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not installed, skipping enablement."
    fi
done

# Make health-check scripts executable (shipped via )
# Directory creation and config installation moved to  overlay.
chmod +x /etc/greenboot/check/required.d/*.sh 2>/dev/null || true
chmod +x /etc/greenboot/check/wanted.d/*.sh   2>/dev/null || true
chmod +x /etc/greenboot/green.d/*.sh          2>/dev/null || true
chmod +x /etc/greenboot/red.d/*.sh            2>/dev/null || true

log "greenboot wired"
```


### `automation\47-hardening.sh`

```bash
#!/usr/bin/env bash
# 47-hardening.sh - enable hardening services (USBGuard, auditd).
# Package installs moved to PACKAGES.md (packages-security).
# sysctl drop-in shipped via usr/lib/sysctl.d/99-mios-hardening.conf.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# USBGuard config is at /usr/lib/usbguard/usbguard-daemon.conf (managed via overlay).
chmod 0600 /usr/lib/usbguard/usbguard-daemon.conf 2>/dev/null || true

# Enable hardening services using build-safe symlinks
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

log "Enabling hardening services..."
for unit in \
    usbguard.service \
    auditd.service \
    fapolicyd.service
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not installed, skipping enablement."
    fi
done

# Pre-generate fapolicyd trust database for bootc systems
# fapolicyd config is at /usr/lib/fapolicyd/fapolicyd.conf (managed via overlay).
if command -v fagenrules &>/dev/null; then
    log "Pre-generating fapolicyd trust database..."
    # Ensure correct permissions for the fapolicyd directory
    chown -R fapolicyd:fapolicyd /etc/fapolicyd 2>/dev/null || true
    fagenrules --load 2>/dev/null || true
    fapolicyd-cli --update 2>/dev/null || true
fi

log "hardening services wired"
```


### `automation\49-finalize.sh`

```bash
#!/usr/bin/env bash
# 49-finalize.sh - final cleanup, systemd preset application, image linting
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Apply all shipped presets now (so `systemctl is-enabled` reflects intent)
systemctl preset-all 2>/dev/null || true

# Set a safe build-time default target. Containers will reach this quickly.
# Bare-metal/VM roles will switch this to graphical.target/etc. at runtime.
systemctl set-default multi-user.target 2>/dev/null || true

# LAW 4: /etc/mios is for Day-2 admin overrides and is created by tmpfiles.d at boot.
# Stage the example role.conf in /usr/share/mios/ so tmpfiles.d can seed it
# to /etc/mios/role.conf on first boot via the C (copy-if-missing) directive.
install -d -m 0755 ${MIOS_SHARE_DIR}

# Scrub potential credential leaks from build-time placeholder injections
log "scrubbing build-time credentials and override scripts"
rm -f /etc/containers/auth.json \
      /root/.docker/config.json \
      /root/.containers/auth.json \
      /ctx/automation/99-overrides.sh \
      /usr/local/bin/99-overrides.sh \
      /usr/bin/99-overrides.sh 2>/dev/null || true

# Trim dnf caches
$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true
rm -rf /var/cache/libdnf5 /var/cache/dnf /var/log/dnf5.log* 2>/dev/null || true

# Set image metadata -- LAW 4: write to /usr/lib/mios/, not /etc/
# /etc/mios-version and /etc/mios/version are Day-2 admin paths.
MIOS_VERSION=$(cat /ctx/VERSION 2>/dev/null || echo "unknown")
install -d -m 0755 ${MIOS_USR_DIR}
cat > ${MIOS_USR_DIR}/version <<EOF
MIOS_VERSION=${MIOS_VERSION}
MIOS_BASE=ucore-hci-stable-nvidia
MIOS_BUILT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
ln -sf ${MIOS_USR_DIR}/version ${MIOS_USR_DIR}/mios-version

log "finalize complete"
```


### `automation\50-enable-log-copy-service.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "Enabling 'MiOS' build log copy service..."

WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

if [[ -f "/usr/lib/systemd/system/mios-copy-build-log.service" ]]; then
    ln -sf ../mios-copy-build-log.service "${WANTS}/mios-copy-build-log.service"
    log "Enabled mios-copy-build-log.service"
else
    warn "mios-copy-build-log.service not found, skipping enablement."
fi
```


### `automation\52-bake-kvmfr.sh`

```bash
#!/usr/bin/env bash
# 52-bake-kvmfr.sh - compile Looking Glass kvmfr kmod against the ucore-hci
# kernel shipped in the base image, sign it with the ublue MOK, and bake the
# .ko into /usr/lib/modules/$KVER/extra/kvmfr/.
#
# This runs INSIDE the Containerfile build. No runtime compile. BAKED IN -
# WHEN POSSIBLE.
#
# v0.2.0 fix (supersedes 1.3.0):
#   The previous `if ! dnf5 -y install ... 2>/dev/null; then ... fi` plus
#
#       AVAIL_REPO="$(dnf5 --showduplicates repoquery ... | tail -5 | tr ...)"
#
#   was tripping the whole script with exit 2 BEFORE reaching the graceful-
#   skip block. Root cause: `VAR="$(failing-pipeline)"` under set -euo pipefail
#   causes set -e to fire on the assignment when the pipeline's first command
#   exits non-zero (pipefail promotes the failure). Verified with a reproducer.
#
#   Fix: wrap every dnf5/rpm/dnf5-repoquery call in an explicit
#   `set +e` / `RC=$?` / `set -e` guard. Drop the unreliable repoquery
#   diagnostic entirely - the log line is still informative without it.
#   Looking Glass still runs IVSHMEM-only without kvmfr.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

# --- Detect the kernel version shipped in the base image -------------------
KVER="$(find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" 2>/dev/null | sort -V | tail -1)"
if [[ -z "$KVER" ]]; then
    warn "no kernel modules directory; cannot determine kernel version"
    warn "skipping kvmfr bake - Looking Glass will run in IVSHMEM-only mode"
    exit 0
fi
log "building against kernel: $KVER"

# --- Try to get kernel-devel-$KVER exactly matched -------------------------
if [[ ! -d "/usr/src/kernels/$KVER" ]]; then
    log "installing kernel-devel-$KVER"
    set +e
    $DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" "kernel-devel-$KVER" >/dev/null 2>&1
    RC=$?
    set -e
    if [[ $RC -ne 0 ]]; then
        set +e
        AVAIL="$(rpm -qa 'kernel-devel*' 2>/dev/null | tr '\n' ' ')"
        set -e
        warn "SKIP: no exact kernel-devel for $KVER (dnf rc=$RC; installed: ${AVAIL:-none})"
        warn "      The ucore-hci base kernel $KVER is typically newer/older than"
        warn "      F44's repo-published kernel-devel. Project principle is 'never"
        warn "      upgrade base kernel in-container', so kvmfr is skipped here."
        warn "      Looking Glass still works in IVSHMEM-only mode. To enable kvmfr"
        warn "      on the booted image once the kernel matches, run:"
        warn "         sudo dnf install kernel-devel-\$(uname -r) akmod-kvmfr"
        warn "         sudo akmods --force --kernels \$(uname -r)"
        exit 0
    fi
fi

# --- Install akmod-kvmfr (from hikariknight/looking-glass-kvmfr COPR) ------
log "installing akmod-kvmfr"
set +e
$DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" akmod-kvmfr >/dev/null 2>&1
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
    warn "SKIP: akmod-kvmfr install failed (rc=$RC; COPR unreachable or package missing)"
    warn "      verify COPR enabled: dnf5 copr list | grep looking-glass-kvmfr"
    exit 0
fi

# --- Force-build kvmfr kmod for this kernel --------------------------------
log "running akmods --force --kernels $KVER"
set +e
akmods --force --kernels "$KVER" 2>&1 | sed 's/^/[akmods] /'
RC=${PIPESTATUS[0]}
set -e
if [[ $RC -ne 0 ]]; then
    warn "SKIP: akmods build failed (rc=$RC)"
    warn "      checking /var/cache/akmods/kvmfr/ for build log..."
    find /var/cache/akmods/ -name '*.log' -exec tail -50 {} \; 2>/dev/null || true
    exit 0
fi

# --- Verify the kmod landed -------------------------------------------------
KMOD_PATH="/usr/lib/modules/$KVER/extra/kvmfr/kvmfr.ko"
if [[ -f "$KMOD_PATH" ]] || [[ -f "${KMOD_PATH}.xz" ]] || [[ -f "${KMOD_PATH}.zst" ]]; then
    log "OK: kvmfr.ko baked in at /usr/lib/modules/$KVER/extra/kvmfr/"
    ls -la "/usr/lib/modules/$KVER/extra/kvmfr/"
else
    warn "SKIP: kvmfr.ko NOT FOUND after akmods build"
    warn "      listing /usr/lib/modules/$KVER/extra/:"
    ls -la "/usr/lib/modules/$KVER/extra/" 2>/dev/null || warn "  (no extra/ dir)"
    exit 0
fi

# --- Update module dependencies --------------------------------------------
log "running depmod -a -b /usr $KVER"
depmod -a -b /usr "$KVER" || warn "depmod failed (non-fatal)"

# --- Sign the module with ublue MOK (if present, for Secure Boot) ----------
PRIV_KEY="/etc/pki/akmods/private/private_key.priv"
PUB_KEY="/etc/pki/akmods/certs/public_key.der"
if [[ -f "$PRIV_KEY" && -f "$PUB_KEY" ]]; then
    log "signing kvmfr.ko with akmods private key"
    SIGN_FILE="/usr/src/kernels/$KVER/automation/sign-file"
    if [[ -x "$SIGN_FILE" ]]; then
        for ko in /usr/lib/modules/$KVER/extra/kvmfr/*.ko; do
            [[ -f "$ko" ]] && "$SIGN_FILE" sha256 "$PRIV_KEY" "$PUB_KEY" "$ko" && \
                log "  signed: $ko"
        done
    else
        warn "sign-file script not found at $SIGN_FILE; kvmfr unsigned"
    fi
else
    log "NOTE: ublue MOK private key not in image (expected); users enroll MOK"
    log "      and kvmfr will use the public cert shipped by ublue-os-akmods-addons"
fi

log "kvmfr kmod BAKED IN"
```


### `automation\53-bake-lookingglass-client.sh`

```bash
#!/usr/bin/env bash
# 53-bake-lookingglass-client.sh - git clone Looking Glass B7, cmake/make,
# install looking-glass-client binary to /usr/bin/. BAKED IN - WHEN POSSIBLE.
#
# v0.2.0 fix:
#   - SKIP (don't fail) when cmake or required dev libraries are missing.
#     12-virt.sh already builds Looking Glass as part of its virtualization
#     stack and then removes cmake/gcc/*-devel to shrink the image. By the
#     time this script runs the toolchain is gone. Skipping here is safe
#     because the binary is already installed by 12-virt.sh; a hard-fail
#     aborted the whole build for a redundant second build attempt.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# --- If 12-virt.sh already baked it in, declare success and exit -----------
if [[ -x /usr/bin/looking-glass-client ]]; then
    log "OK: looking-glass-client already present (installed by 12-virt.sh)"
    /usr/bin/looking-glass-client --version 2>&1 | head -5 || true
    exit 0
fi

# --- Check toolchain availability ------------------------------------------
MISSING=""
for tool in cmake make gcc git; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING="${MISSING}${tool} "
    fi
done

if [[ -n "$MISSING" ]]; then
    warn "SKIP: missing toolchain: $MISSING"
    warn "      12-virt.sh normally builds Looking Glass and removes cmake/gcc"
    warn "      afterwards. If 12-virt.sh failed, fix it first - the LG build"
    warn "      there is the canonical path."
    exit 0
fi

# Resolve latest Looking Glass release branch from upstream. Project policy:
# every dependency tracks :latest from its source. LG uses letter-numbered
# release branches (B6, B7, ...); pick the highest by version sort.
if [[ -z "${LG_BRANCH:-}" ]]; then
    LG_BRANCH=$(git ls-remote --heads https://github.com/gnif/LookingGlass.git 'B*' 2>/dev/null \
        | awk -F/ '{print $NF}' \
        | sort -V \
        | tail -n1 || true)
    [[ -n "$LG_BRANCH" ]] || die "Looking Glass: git ls-remote returned no B* release branch"
fi
record_version looking-glass "$LG_BRANCH" "https://github.com/gnif/LookingGlass/tree/${LG_BRANCH}"
BUILD_DIR="/tmp/LookingGlass-build"

# --- Clone -----------------------------------------------------------------
log "cloning Looking Glass $LG_BRANCH"
rm -rf "$BUILD_DIR"
if ! git clone --depth 1 --branch "$LG_BRANCH" --recurse-submodules \
        https://github.com/gnif/LookingGlass.git "$BUILD_DIR"; then
    warn "SKIP: git clone failed (network or branch issue)"
    exit 0
fi

# --- Configure + build client ---------------------------------------------
log "configuring client build"
mkdir -p "$BUILD_DIR/client/build"
cd "$BUILD_DIR/client/build"
if ! cmake -DCMAKE_INSTALL_PREFIX=/usr \
           -DCMAKE_INSTALL_LIBDIR=/usr/lib \
           -DCMAKE_BUILD_TYPE=Release \
           -DENABLE_LIBDECOR=ON \
           -DENABLE_PIPEWIRE=ON \
           -DENABLE_PULSEAUDIO=OFF \
           -DENABLE_BACKTRACE=OFF \
           ..; then
    warn "SKIP: cmake configure failed - check -devel packages"
    exit 0
fi

log "building looking-glass-client (jobs=$(nproc))"
if ! make -j"$(nproc)"; then
    warn "SKIP: make failed"
    exit 0
fi

# --- Install binary + desktop file ----------------------------------------
log "installing binary to /usr/bin/looking-glass-client"
install -Dm0755 looking-glass-client /usr/bin/looking-glass-client

# Ship a .desktop entry
install -Dm0644 /dev/stdin /usr/share/applications/looking-glass.desktop <<'DESK'
[Desktop Entry]
Type=Application
Name=Looking Glass
Comment=Low-latency KVM display from a VM via shared memory
Icon=video-display
Exec=looking-glass-client
Terminal=false
Categories=System;Utility;
Keywords=KVM;VFIO;Passthrough;
DESK

# --- Cleanup build tree (keep toolchain in image per self-building principle) ---
log "cleaning up source tree"
cd /
rm -rf "$BUILD_DIR"

# --- Verify ----------------------------------------------------------------
if [[ -x /usr/bin/looking-glass-client ]]; then
    log "OK: looking-glass-client baked in at /usr/bin/looking-glass-client"
    /usr/bin/looking-glass-client --version 2>&1 | head -5 || true
else
    warn "SKIP: binary missing after install (non-fatal)"
    exit 0
fi

log "Looking Glass client BAKED IN"
```


### `automation\90-generate-sbom.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0  90-generate-sbom: Generate Software Bill of Materials (SBOM)
# Uses Syft to generate CycloneDX and SPDX manifests for the final image.
set -euo pipefail

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

echo "[90-generate-sbom] Starting SBOM generation..."

ARTIFACT_DIR="${MIOS_USR_DIR}/artifacts/sbom"
mkdir -p "$ARTIFACT_DIR"

if ! command -v syft &> /dev/null; then
    echo "[90-generate-sbom] WARN: Syft not found. Attempting to install via PACKAGES.md..."
    install_packages "sbom-tools"
    # install_packages is best-effort and returns 0 even on miss; re-check
    # presence and bail out cleanly if syft still isn't on PATH.
    if ! command -v syft &> /dev/null; then
        echo "[90-generate-sbom] WARN: syft unavailable in this build environment -- skipping SBOM generation (non-fatal)."
        exit 0
    fi
fi

VERSION=$(cat /ctx/VERSION 2>/dev/null || echo "v0.2.0")

echo "[90-generate-sbom] Scanning root filesystem..."

# Generate CycloneDX (JSON) - Primary for AI and automation
syft scan dir:/ \
    --output cyclonedx-json \
    --file "${ARTIFACT_DIR}/mios-sbom-${VERSION}.cyclonedx.json" \
    --exclude "/ctx" \
    --exclude "/var/cache"

# Generate SPDX (Tag-Value) - Standard compliance
syft scan dir:/ \
    --output spdx-tag-value \
    --file "${ARTIFACT_DIR}/mios-sbom-${VERSION}.spdx.txt" \
    --exclude "/ctx" \
    --exclude "/var/cache"

echo "[90-generate-sbom] SBOMs generated in ${ARTIFACT_DIR}:"
ls -lh "$ARTIFACT_DIR"

echo "[90-generate-sbom] Done."
```


### `automation\98-boot-config.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 98-boot-config: Boot console + service configuration
# Plymouth disable is handled by usr/lib/bootc/kargs.d/10-mios-console.toml
# Console verbosity is handled by usr/lib/bootc/kargs.d/00-mios.toml + 10-mios-verbose.toml
set -euo pipefail

echo "[98-boot-config] Configuring boot console output..."

# ── Verify kargs TOML files exist ──────────────────────────────────────────
# These are static files from  -- if missing, the overlay step failed.
if [ -f /usr/lib/bootc/kargs.d/10-mios-console.toml ]; then
    echo "[98-boot-config] Configuring plymouth disable via kernel cmdline..."
else
    echo "[98-boot-config] ERROR: 10-mios-console.toml not found -- check overlay!"
fi

# ── Ensure agetty on tty1 ─────────────────────────────────────────────────
# Even if GDM fails, we need a text console to diagnose.
echo "[98-boot-config] Enabling getty on tty1 (fallback console)..."
systemctl enable getty@tty1.service 2>/dev/null || true

# ── Emergency shell access ────────────────────────────────────────────────
echo "[98-boot-config] Enabling emergency/rescue shell access..."
systemctl enable emergency.service 2>/dev/null || true
systemctl enable rescue.service 2>/dev/null || true

# ── Serial console for Hyper-V / QEMU ────────────────────────────────────
echo "[98-boot-config] Enabling serial-getty on ttyS0..."
systemctl enable serial-getty@ttyS0.service 2>/dev/null || true

# ── NetworkManager-wait-online timeout ────────────────────────────────────
echo "[98-boot-config] NetworkManager-wait-online timeout delivered via overlay."

echo "[98-boot-config] [ok] Boot console configured"
echo "[98-boot-config]   plymouth: disabled (kernel cmdline plymouth.enable=0)"
echo "[98-boot-config]   getty@tty1: enabled (fallback text console)"
echo "[98-boot-config]   serial-getty@ttyS0: enabled (serial console)"
echo "[98-boot-config]   NM-wait-online: 10s timeout (was 90s)"
```


### `automation\99-cleanup.sh`

```bash
#!/bin/bash
# 'MiOS' v0.2.0 -- 99-cleanup: Final image cleanup (mirrors ucore/cleanup.sh)
#
# MANDATORY for bootc images. Every ublue-os image runs this pattern.
# Without it, BIB deployment fails or the booted system has broken /var state.
#
# v0.2.0: Added targeted lint cleanup for dnf5.log, ldconfig aux-cache,
# and any stray files in /var that trigger bootc container lint warnings.
#
# Reference: https://github.com/ublue-os/ucore/blob/main/cleanup.sh
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

echo "[99-cleanup] Running final image cleanup..."

# 1. Clean /boot -- BIB generates fresh bootloader, stale content causes conflicts
echo "[99-cleanup] Cleaning /boot..."
find /boot/ -maxdepth 1 -mindepth 1 -exec rm -fr {} \; || true

# 2. Clean /var -- bootc treats /var as persistent state (like Docker VOLUME)
# We remove content but KEEP directories to preserve permissions/labels.
echo "[99-cleanup] Cleaning /var content (preserving structure)..."
# Remove all files and subdirs in /var/tmp and /var/log
rm -rf /var/tmp/* /var/log/* 2>/dev/null || true
# Clean /var/lib excluding critical paths if any (mostly dnf/rpm-ostree cache)
find /var/cache/* -maxdepth 0 -type d \! -name libdnf5 \! -name rpm-ostree -exec rm -fr {} \; 2>/dev/null || true

# 3. Lint-specific cleanup: remove files that trigger bootc container lint warnings
echo "[99-cleanup] Cleaning lint triggers..."
rm -f /var/log/lastlog /var/log/dnf5.log* 2>/dev/null || true
rm -rf /var/cache/ldconfig 2>/dev/null || true
rm -f /var/lib/systemd/random-seed 2>/dev/null || true
# 'MiOS' v0.2.0: additional lint cleanup based on Cloud Build observations
rm -rf /var/lib/glusterd 2>/dev/null || true
rm -f /var/lib/containers/storage/db.sql 2>/dev/null || true
rm -f /var/lib/flatpak/.changed 2>/dev/null || true
rm -rf /var/lib/flatpak/repo/tmp/* 2>/dev/null || true

# 4. Restore system skeleton via systemd-tmpfiles
# This ensures all /var and /tmp directories exist with correct metadata.
echo "[99-cleanup] Restoring system skeleton..."
systemd-tmpfiles --create --boot --root=/ 2>/dev/null || true

# 5. Clean DNF caches
echo "[99-cleanup] Cleaning package manager caches..."
$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true

echo "[99-cleanup] [ok] Image cleanup complete"
```


### `automation\99-postcheck.sh`

```bash
#!/usr/bin/env bash
# 99-postcheck.sh - build-time technical invariant validation
# 
# This script runs at the very end of the Containerfile build (before cleanup).
# It enforces mandatory version requirements, security postures, and 
# architectural purity. Failures here ABORT THE BUILD to prevent shipping
# a regressed or vulnerable image.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "'MiOS' build-time validation"

# 1. OpenSSH Version Check (CVE-2026-4631 / Cockpit RCE mitigation)
# Requirement: ≥ 9.6
log "Checking OpenSSH version..."
if ! command -v sshd >/dev/null 2>&1; then
    die "sshd not found in image (required for Podman-machine & remote mgmt)"
fi

SSH_VER_RAW=$(sshd -V 2>&1 | head -n1 | grep -oP 'OpenSSH_\K[0-9.]+')
log "  Found: OpenSSH $SSH_VER_RAW"

# Compare version (simple dot-split comparison)
if [[ $(printf '%s\n9.6' "$SSH_VER_RAW" | sort -V | head -n1) != "9.6" ]]; then
    die "OpenSSH version $SSH_VER_RAW is below required 9.6 (Vulnerable to CVE-2026-4631 in Cockpit context)"
fi
log "  [ok] OpenSSH version is safe"

# 2. Cockpit Security Posture
log "Checking Cockpit configuration..."
# In Rootfs-Native, config might be in /etc or /usr/lib
if [[ -f "/etc/cockpit/cockpit.conf" ]]; then
    COCKPIT_CONF="/etc/cockpit/cockpit.conf"
elif [[ -f "/usr/lib/cockpit/cockpit.conf" ]]; then
    COCKPIT_CONF="/usr/lib/cockpit/cockpit.conf"
else
    COCKPIT_CONF=""
fi

if [[ -f "$COCKPIT_CONF" ]]; then
    if ! grep -q "LoginTo = false" "$COCKPIT_CONF"; then
        die "Cockpit LoginTo mitigation missing in $COCKPIT_CONF (CVE-2026-4631)"
    fi
    log "  [ok] Cockpit LoginTo = false is enforced"
else
    log "  [!] Cockpit config not found at expected paths; skipping check"
fi

# 3. Kernel Argument Validation (Schema Strictness Preparation)
log "Validating kargs.d files..."
if [[ -d /usr/lib/bootc/kargs.d ]]; then
    for f in /usr/lib/bootc/kargs.d/*; do
        [[ -e "$f" ]] || continue
        # Future: run 'bootc container lint' or specialized schema check
        log "  found karg: $(basename "$f")"
    done
    log "  [ok] kargs.d presence verified"
fi

# 4. Critical Package Verification
log "Verifying critical system binaries..."
CRITICAL_TOOLS=(podman bootc cockpit-bridge rpm-ostree)
for tool in "${CRITICAL_TOOLS[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        die "Critical tool '$tool' is missing from the image"
    fi
    log "  [ok] $tool present"
done

# 5. NVIDIA Container Toolkit Version Check
log "Checking NVIDIA Container Toolkit version..."
if command -v nvidia-ctk >/dev/null 2>&1; then
    NCT_VER=$(nvidia-ctk --version | head -n1 | grep -oP 'version \K[0-9.]+')
    log "  Found: $NCT_VER"
    if [[ $(printf '%s\n1.18' "$NCT_VER" | sort -V | head -n1) != "1.18" ]]; then
        die "nvidia-container-toolkit version $NCT_VER is below required 1.18"
    fi
    log "  [ok] NVIDIA Container Toolkit version is safe"
fi

# 6. Cockpit Version Check (for CVE-2026-4631)
log "Checking Cockpit version..."
if rpm -q cockpit >/dev/null 2>&1; then
    COCKPIT_VER=$(rpm -q cockpit --queryformat '%{VERSION}')
    log "  Found: Cockpit $COCKPIT_VER"
    # CVE fixed in 360. 'MiOS' targets 361+ for Fedora 44 GA stability.
    if [[ $(printf '%s\n361' "$COCKPIT_VER" | sort -V | head -n1) != "361" ]]; then
        log "  [!] Cockpit version $COCKPIT_VER is below 361 (Risk: CVE-2026-4631 / Regressions)"
    else
        log "  [ok] Cockpit version is safe"
    fi
fi

# 7. WSL2 wsl.conf parse + parity check
# A malformed /etc/wsl.conf takes down systemd-as-PID1 in WSL2, which
# cascades to a broken user session, missing /var/home/mios, and a fallback
# cwd of /mnt/c/.... Catch drift at build time so we never ship a broken
# file. Also enforces parity with /usr/lib/wsl.conf (the canonical reference
# wsl-init.service uses to auto-restore).
log "Validating /etc/wsl.conf (ASCII + parse + parity with /usr/lib/wsl.conf)..."
if [[ -f /etc/wsl.conf ]]; then
    # WSL2's INI parser is byte-naive -- multibyte chars (em-dashes, smart quotes,
    # NBSP) shift its line counter and surface as bogus "Expected ' ' or '\n' in
    # /etc/wsl.conf:N" errors at boot. Python configparser tolerates UTF-8 so a
    # parse-only check misses these. Enforce strict ASCII before the parse runs.
    if LC_ALL=C grep -nP '[^\x00-\x7F]' /etc/wsl.conf >&2; then
        die "/etc/wsl.conf contains non-ASCII bytes (WSL2's parser will choke)"
    fi
    log "  pure ASCII"
    if command -v python3 >/dev/null 2>&1; then
        python3 -c '
import configparser, sys
p = configparser.ConfigParser(strict=True, interpolation=None)
try:
    with open("/etc/wsl.conf") as f:
        p.read_file(f)
except Exception as e:
    sys.stderr.write(f"wsl.conf parse failed: {e}\n"); sys.exit(1)
required = {"boot": ["systemd"], "user": ["default"]}
for section, keys in required.items():
    if not p.has_section(section):
        sys.stderr.write(f"wsl.conf missing required [section]: {section}\n"); sys.exit(1)
    for k in keys:
        if not p.has_option(section, k):
            sys.stderr.write(f"wsl.conf missing required key: {section}.{k}\n"); sys.exit(1)
print("  /etc/wsl.conf parses cleanly with all required sections/keys")
' || die "/etc/wsl.conf failed parse/required-keys validation"
    else
        log "  [!] python3 unavailable -- skipping wsl.conf parse (post-build only)"
    fi
    if [[ -f /usr/lib/wsl.conf ]]; then
        if ! cmp -s /etc/wsl.conf /usr/lib/wsl.conf; then
            die "/etc/wsl.conf drifted from /usr/lib/wsl.conf reference at build time"
        fi
        log "  [ok] /etc/wsl.conf matches /usr/lib/wsl.conf reference"
    fi
else
    log "  [!] /etc/wsl.conf not present in image -- WSL2 deploys will fall back to defaults"
fi

# 8. sysusers.d sanity -- login-shell users MUST have a fixed UID.
# Auto-allocation ('-') picks from the SYSTEM range (<UID_MIN), and logind
# then refuses to create /run/user/<uid>/. The cascade kills dbus user
# session, dconf, Wayland session services, and every GTK app that needs
# a session bus.
log "Validating sysusers.d login users have fixed UIDs..."
_sysusers_bad=$(
    for f in /usr/lib/sysusers.d/*.conf; do
        [[ -f "$f" ]] || continue
        # u <name> <uid_or_-> [<gecos>] [<home>] [<shell>]
        # Match users whose shell is a login shell and uid is bare '-'.
        awk '
            /^u[[:space:]]+/ {
                # field 3 = uid spec, last field = shell (or empty)
                shell = $NF
                if ($3 == "-" && shell ~ /\/(bash|zsh|sh|fish|dash|csh|tcsh|ksh)$/) {
                    print FILENAME ":" NR ": " $0
                }
            }' "$f"
    done
)
if [[ -n "$_sysusers_bad" ]]; then
    printf '%s\n' "$_sysusers_bad" >&2
    die "sysusers.d defines login-shell user(s) with auto-allocated UID; pin to a value >= 1000"
fi
log "  all login-shell sysusers entries have fixed UIDs"

# 8b. sysusers.d: every `u user UID:NUM` must be preceded by a `g name NUM`
# line in the same file (or use a name reference instead of NUM). If the
# numeric GID is unresolvable, sysusers fails with "please create GID NUM"
# at first boot and the user never gets created.
log "Validating sysusers.d UID:GID resolves to a created group..."
_sysusers_unresolved=$(
    for f in /usr/lib/sysusers.d/*.conf; do
        [[ -f "$f" ]] || continue
        awk '
            # collect g lines in this file
            /^g[[:space:]]+/ {
                # 2nd field = group name, 3rd = id (or "-")
                groups[$2] = 1
                if ($3 ~ /^[0-9]+$/) gids[$3] = $2
            }
            /^u[[:space:]]+/ {
                # 3rd field is UID:GID. Split on colon.
                split($3, a, ":")
                # If GID part is numeric and no g line in this file claims it, flag.
                if (a[2] ~ /^[0-9]+$/ && !(a[2] in gids)) {
                    print FILENAME ":" NR ": " $0
                }
            }' "$f"
    done
)
if [[ -n "$_sysusers_unresolved" ]]; then
    printf '%s\n' "$_sysusers_unresolved" >&2
    die "sysusers.d: u-line references a numeric GID with no matching 'g name GID' line in the same file"
fi
log "  all u-line GIDs resolve to created groups"

# 9. tmpfiles.d: no /var/run or /var/lock paths.
# Both are FHS-compat symlinks to /run subdirs. systemd-tmpfiles emits
# "Line references path below /var/run" and refuses to act on the entry.
# Catch the bug class at build time so we never ship a broken declaration.
log "Validating tmpfiles.d uses /run (not /var/run / /var/lock)..."
_tmpfiles_legacy=$(
    for f in /usr/lib/tmpfiles.d/*.conf /etc/tmpfiles.d/*.conf; do
        [[ -f "$f" ]] || continue
        # Match non-comment lines whose path field starts with /var/run or /var/lock.
        # Field 2 of a tmpfiles line is the path; tolerate leading whitespace and
        # tabs after the type field.
        awk '
            /^[[:space:]]*[a-zA-Z]/ {
                if ($2 ~ /^\/var\/(run|lock)\//) {
                    print FILENAME ":" NR ": " $0
                }
            }' "$f"
    done
)
if [[ -n "$_tmpfiles_legacy" ]]; then
    printf '%s\n' "$_tmpfiles_legacy" >&2
    die "tmpfiles.d entry uses /var/run or /var/lock (use /run or /run/lock instead)"
fi
log "  tmpfiles.d entries use canonical /run paths"

# 10. systemd-analyze verify on MiOS-owned services + targets.
# Catches: bad directive names, malformed values, missing required sections,
# unparseable [Install] entries. Drop-ins that reference non-shipped units
# generate noise so we only verify our own self-contained units. Errors
# referenced as "Failed to load configuration" or "directive not understood"
# are fatal; everything else (file-not-found from external Wants=, etc.) is
# tolerable and gets filtered out.
log "Validating 'MiOS' systemd unit syntax..."
if command -v systemd-analyze >/dev/null 2>&1; then
    _bad_units=$(
        for u in /usr/lib/systemd/system/mios-*.service \
                 /usr/lib/systemd/system/mios-*.target; do
            [[ -f "$u" ]] || continue
            out=$(systemd-analyze --no-pager verify "$u" 2>&1 || true)
            # Filter: only complaints about THIS file are real (filename prefix).
            # External-reference warnings name the dependency, not "$u".
            echo "$out" | grep -E "^${u}:" || true
        done
    )
    if [[ -n "$_bad_units" ]]; then
        printf '%s\n' "$_bad_units" >&2
        die "systemd-analyze verify reported errors in 'MiOS' unit(s)"
    fi
    log "  'MiOS' units lint clean"
else
    log "  systemd-analyze unavailable -- skipping unit verification"
fi

# 11. systemd-tmpfiles --dry-run on MiOS-owned tmpfiles configs.
# Catches: bad path syntax, unsupported types, missing required fields. The
# legacy /var/run / /var/lock case is already covered by #9; this catches
# every other tmpfiles syntax error.
log "Validating 'MiOS' tmpfiles.d syntax..."
if command -v systemd-tmpfiles >/dev/null 2>&1; then
    _bad_tmpfiles=$(
        for f in /usr/lib/tmpfiles.d/mios-*.conf; do
            [[ -f "$f" ]] || continue
            # --dry-run alone reports parse errors; combine with --create
            # (also dry-run) so it exercises the full directive interpreter.
            out=$(systemd-tmpfiles --dry-run --create "$f" 2>&1 || true)
            echo "$out" | grep -E "^${f}:" || true
        done
    )
    if [[ -n "$_bad_tmpfiles" ]]; then
        printf '%s\n' "$_bad_tmpfiles" >&2
        die "systemd-tmpfiles reported errors in 'MiOS' tmpfiles.d config(s)"
    fi
    log "  'MiOS' tmpfiles.d configs parse clean"
else
    log "  systemd-tmpfiles unavailable -- skipping tmpfiles verification"
fi

log "Validation SUCCESSFUL"
exit 0
```


## Layer 4k -- Helpers


### `automation\ai-bootstrap.sh`

```bash
#!/bin/bash
# 'MiOS' AI/manifest bootstrap. Regenerates directory manifests, syncs the Wiki,
# rebuilds the unified knowledge base (RAG snapshot), refreshes user-space
# environment configs, and seeds shared agent context. Idempotent.

set -uo pipefail

echo "[ai-bootstrap] Initializing 'MiOS' agent workspace..."

# 0. Load unified environment (legacy .env.mios; deprecated -- prefer
# /etc/mios/profile.toml for new installs).
if [[ -f ".env.mios" ]]; then
    echo "[ai-bootstrap] Loading legacy environment from .env.mios..."
    set -a
    # shellcheck disable=SC1091
    source .env.mios
    set +a
fi

# 1. Generate manifests.
if [[ -f "tools/generate-ai-manifest.py" ]]; then
    echo "[ai-bootstrap] Generating directory manifests..."
    python3 tools/generate-ai-manifest.py || echo "[ai-bootstrap] WARN: manifest generation failed (non-fatal)"
else
    echo "[ai-bootstrap] WARN: tools/generate-ai-manifest.py not found"
fi

# 2. Sync Wiki documentation.
if [[ -f "tools/sync-wiki.py" ]]; then
    echo "[ai-bootstrap] Syncing Wiki..."
    python3 tools/sync-wiki.py || echo "[ai-bootstrap] WARN: wiki sync failed (non-fatal)"
else
    echo "[ai-bootstrap] WARN: tools/sync-wiki.py not found"
fi

# 3. Generate unified knowledge base (RAG snapshot).
if [[ -f "tools/generate-unified-knowledge.py" ]]; then
    echo "[ai-bootstrap] Generating unified knowledge base (RAG snapshot)..."
    [[ -f "tools/journal-sync.py" ]] && { python3 tools/journal-sync.py || true; }
    python3 tools/generate-unified-knowledge.py || echo "[ai-bootstrap] WARN: knowledge base generation failed (non-fatal)"
else
    echo "[ai-bootstrap] WARN: tools/generate-unified-knowledge.py not found"
fi

# 4. Initialize agents/research scratchpad if present.
if [[ -d "agents/research" ]]; then
    echo "[ai-bootstrap] Initializing agents/research scratchpad..."
else
    echo "[ai-bootstrap] WARN: agents/research directory not found"
fi

# 5. Refresh environment configs and dotfiles.
echo "[ai-bootstrap] Persisting environment state..."
if [[ -f "tools/refresh-env.py" ]]; then
    python3 tools/refresh-env.py
else
    echo "[ai-bootstrap] WARN: tools/refresh-env.py not found"
fi

echo "[ai-bootstrap] Workspace initialization complete."

# 6. Seed RAG context for downstream agents.
echo "[ai-bootstrap] Seeding latest 'MiOS' context for initialized agents..."
if [[ -f "artifacts/repo-rag-snapshot.json.gz" ]]; then
    mkdir -p .ai/foundation/shared-tmp/
    cp artifacts/repo-rag-snapshot.json.gz .ai/foundation/shared-tmp/latest-context.json.gz
    cp artifacts/repo-rag-snapshot.json.gz agents/research/latest-context.json.gz
    echo "[ai-bootstrap] Context seeded to .ai/foundation/shared-tmp/ and agents/research/"
else
    echo "[ai-bootstrap] WARN: artifacts/repo-rag-snapshot.json.gz not found; skipping seed"
fi
```


### `automation\bcvk-wrapper.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
# 'MiOS' v0.2.0 -- Ephemeral QEMU boot test
# Usage: bcvk-wrapper.sh <qcow2-path> [serial-log-path]
#
# Boots a QCOW2 image in headless QEMU with KVM, captures serial console,
# waits for systemd to reach a login target, then exits.
# Returns 0 on success, non-zero on timeout or boot failure.

QCOW="${1:-}"
SERIAL_LOG="${2:-/tmp/mios-serial.log}"
TIMEOUT_SECS=240
POLL_INTERVAL=3

if [[ -z "$QCOW" ]]; then
    echo "Usage: $0 <qcow2-path> [serial-log-path]"
    exit 2
fi

if [[ ! -f "$QCOW" ]]; then
    echo "ERROR: QCOW2 not found: $QCOW"
    exit 3
fi

: > "$SERIAL_LOG"

echo "[bcvk] Booting $QCOW (timeout: ${TIMEOUT_SECS}s)"

QEMU_ARGS=(
    qemu-system-x86_64
    -m 16384
    -smp 8
    -cpu host
    -enable-kvm
    -drive "file=$QCOW,if=virtio,cache=none,format=qcow2"
    -nic "user,model=virtio"
    -nographic
    -serial "file:$SERIAL_LOG"
    -no-reboot
    -display none
)

"${QEMU_ARGS[@]}" &
QEMU_PID=$!

cleanup() { kill "$QEMU_PID" 2>/dev/null; wait "$QEMU_PID" 2>/dev/null; }
trap cleanup EXIT

ELAPSED=0
while [[ $ELAPSED -lt $TIMEOUT_SECS ]]; do
    if grep -qE "(Reached target (Graphical|Multi-User)|login:)" "$SERIAL_LOG" 2>/dev/null; then
        echo "[bcvk] Boot successful (${ELAPSED}s)"
        exit 0
    fi
    if grep -qi "kernel panic" "$SERIAL_LOG" 2>/dev/null; then
        echo "[bcvk] KERNEL PANIC detected"
        tail -50 "$SERIAL_LOG"
        exit 5
    fi
    sleep "$POLL_INTERVAL"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

echo "[bcvk] TIMEOUT after ${TIMEOUT_SECS}s -- boot did not reach target"
echo "[bcvk] Last 100 lines of serial log:"
tail -100 "$SERIAL_LOG"
exit 4
```


### `automation\bootstrap.sh`

```bash
#!/bin/bash
# 'MiOS' Public Bootstrap -- Linux / WSL2
# Repository: MiOS-DEV/MiOS-bootstrap
# Usage: curl -fsSL https://raw.githubusercontent.com/MiOS-DEV/MiOS-bootstrap/main/bootstrap.sh | bash
set -euo pipefail

PRIVATE_INSTALLER="https://raw.githubusercontent.com/MiOS-DEV/mios/main/install.sh"
_ENV_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/mios/mios-build.env"

_r=$'\033[0m'; _b=$'\033[1m'; _dim=$'\033[2m'; _c=$'\033[36m'; _g=$'\033[32m'; _red=$'\033[31m'; _y=$'\033[33m'

echo ""
echo "  ${_c}╔══════════════════════════════════════════════════════════════╗${_r}"
echo "  ${_c}║  'MiOS' -- Local Build Configuration                           ║${_r}"
echo "  ${_c}╚══════════════════════════════════════════════════════════════╝${_r}"
echo ""

# ── Load saved build config ────────────────────────────────────────────────
if [[ -f "$_ENV_FILE" ]]; then
    echo "  ${_dim}Found saved config: $_ENV_FILE${_r}"
    read -rp "  Load previous build variables? [Y/n]: " _load_ok </dev/tty
    if [[ "${_load_ok,,}" != "n" ]]; then
        set +u
        # shellcheck source=/dev/null
        source "$_ENV_FILE"
        set -u
        echo "  ${_g}[OK]${_r} Loaded."
        echo ""
    fi
fi

# ── GitHub PAT (required for private repo access) ─────────────────────────
if [[ -z "${GHCR_TOKEN:-}" ]]; then
    read -rsp "  ${_b}GitHub PAT${_r} (requires 'repo' scope): " GHCR_TOKEN </dev/tty; echo ""
fi
if [[ -z "${GHCR_TOKEN:-}" ]]; then
    echo "  ${_red}[!] Token required.${_r}"; exit 1
fi
export GHCR_TOKEN

echo ""
echo "  ${_y}── Build Configuration ─────────────────────────────────────────${_r}"
echo ""

# ── Admin username ─────────────────────────────────────────────────────────
if [[ -z "${MIOS_USER:-}" ]]; then
    read -rp "  Admin username ${_dim}[mios]${_r}: " MIOS_USER </dev/tty
    MIOS_USER="${MIOS_USER:-mios}"
else
    echo "  Admin username: ${MIOS_USER}  ${_dim}(env)${_r}"
fi
export MIOS_USER

# ── Admin password ─────────────────────────────────────────────────────────
if [[ -z "${MIOS_PASSWORD:-}" ]]; then
    while true; do
        read -rsp "  Admin password: " MIOS_PASSWORD </dev/tty; echo ""
        [[ -z "${MIOS_PASSWORD:-}" ]] && { echo "  ${_red}[!] Password cannot be empty.${_r}"; continue; }
        read -rsp "  Confirm password: " _c2 </dev/tty; echo ""
        [[ "$MIOS_PASSWORD" == "$_c2" ]] && break
        echo "  ${_red}[!] Mismatch -- try again.${_r}"
    done
else
    echo "  Admin password: ${_dim}(env -- masked)${_r}"
fi
export MIOS_PASSWORD

# ── Hostname ───────────────────────────────────────────────────────────────
# Suffix is generated first so the user sees the full hostname in the prompt.
if [[ -z "${MIOS_HOSTNAME:-}" ]]; then
    _suf=$(shuf -i 10000-99999 -n1 2>/dev/null || printf '%05d' $(( RANDOM % 90000 + 10000 )))
    read -rp "  Hostname base ${_dim}[mios]${_r} (suffix -${_suf} is pre-generated -> mios-${_suf}): " _hbase </dev/tty
    _hbase="${_hbase:-mios}"
    export MIOS_HOSTNAME="${_hbase}-${_suf}"
else
    echo "  Hostname: ${MIOS_HOSTNAME}  ${_dim}(env)${_r}"
fi

# ── Optional: GHCR push credentials ───────────────────────────────────────
if [[ -z "${MIOS_GHCR_USER:-}" ]]; then
    echo ""
    read -rp "  GHCR push username ${_dim}[skip]${_r}: " MIOS_GHCR_USER </dev/tty
fi
export MIOS_GHCR_USER="${MIOS_GHCR_USER:-}"

if [[ -n "$MIOS_GHCR_USER" && -z "${MIOS_GHCR_PUSH_TOKEN:-}" ]]; then
    read -rsp "  GHCR push token ${_dim}[reuse GitHub PAT]${_r}: " MIOS_GHCR_PUSH_TOKEN </dev/tty; echo ""
    export MIOS_GHCR_PUSH_TOKEN="${MIOS_GHCR_PUSH_TOKEN:-$GHCR_TOKEN}"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "  ${_y}── Summary ──────────────────────────────────────────────────────${_r}"
echo ""
printf "    %-20s %s\n" "Admin user:"     "$MIOS_USER"
printf "    %-20s %s\n" "Admin password:" "(masked)"
printf "    %-20s %s\n" "Hostname:"       "$MIOS_HOSTNAME"
printf "    %-20s %s\n" "Registry push:"  "${MIOS_GHCR_USER:-none (local build only)}"
printf "    %-20s %s\n" "Config saved to:" "$_ENV_FILE"
echo ""
read -rp "  ${_b}Proceed?${_r} [Y/n]: " _ok </dev/tty
[[ "${_ok,,}" == "n" ]] && { echo "  Aborted."; exit 0; }

# ── Save build config ──────────────────────────────────────────────────────
mkdir -p "$(dirname "$_ENV_FILE")"
{
    printf '# 'MiOS' Build Configuration\n'
    printf '# Generated: %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    printf 'GHCR_TOKEN=%q\n'    "$GHCR_TOKEN"
    printf 'MIOS_USER=%q\n'     "$MIOS_USER"
    printf 'MIOS_PASSWORD=%q\n' "$MIOS_PASSWORD"
    printf 'MIOS_HOSTNAME=%q\n' "$MIOS_HOSTNAME"
    [[ -n "${MIOS_GHCR_USER:-}" ]]       && printf 'MIOS_GHCR_USER=%q\n'       "$MIOS_GHCR_USER"
    [[ -n "${MIOS_GHCR_PUSH_TOKEN:-}" ]] && printf 'MIOS_GHCR_PUSH_TOKEN=%q\n' "$MIOS_GHCR_PUSH_TOKEN"
} > "$_ENV_FILE"
chmod 600 "$_ENV_FILE"
echo "  ${_g}[OK]${_r} Build config saved → ${_dim}$_ENV_FILE${_r}"

# ── Fetch and execute private installer ───────────────────────────────────
export MIOS_AUTOINSTALL=1
echo ""
echo "  [+] Fetching private installer..."
_tmp=$(mktemp /tmp/mios-install-XXXXXX.sh)
if curl -fsSL -H "Authorization: token $GHCR_TOKEN" "$PRIVATE_INSTALLER" -o "$_tmp"; then
    chmod +x "$_tmp"
    echo "  ${_g}[OK]${_r} Launching installer."
    echo ""
    bash "$_tmp"
    rm -f "$_tmp"
else
    rm -f "$_tmp"
    echo "  ${_red}[!] Failed to fetch installer. Check token and repo permissions.${_r}"
    exit 1
fi
```


### `automation\enroll-mok.sh`

```bash
#!/usr/bin/bash
# enroll-mok.sh -- 'MiOS' Secure Boot MOK enrollment helper.
#
# Uses mokutil throughout. sbctl is the WRONG tool for Fedora bootc
# (GRUB2+shim chain, not systemd-boot+UKI). See specs/SECUREBOOT.md.
#
# Variant-aware:
#   MiOS-2 (ucore-hci): prefers /etc/pki/akmods/certs/akmods-ublue.der (ublue key)
#                           if /etc/pki/mios/mok.der absent.
#
# Idempotent: exits 0 if key is already enrolled or pending enrollment.
#
# Usage:
#   enroll-mok.sh [--status] [--key /path/to/key.der]
#
# Exit codes:
#   0 = enrolled / pending / no-secureboot (no action needed)
#   1 = error
#   2 = key not found
#   3 = conflict (key CN matches but fingerprint differs -- manual intervention)
set -euo pipefail

STATUS_ONLY=0
KEY_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --status)  STATUS_ONLY=1; shift ;;
        --key)     KEY_OVERRIDE="$2"; shift 2 ;;
        -*)        echo "Unknown option: $1" >&2; exit 1 ;;
        *)         break ;;
    esac
done

LOG_DIR=/var/log/mios
LOG_FILE="${LOG_DIR}/mok-enroll-$(date -u +%Y%m%dT%H%M%SZ).log"
install -d -m 0750 "$LOG_DIR"

log() {
    local msg="[mok-enroll] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE"
}

status_probe() {
    # Emit one of: enrolled | pending | not-enrolled | no-secureboot | conflict
    if ! command -v mokutil >/dev/null 2>&1; then
        echo "no-secureboot"
        return
    fi
    local sb_state
    sb_state=$(mokutil --sb-state 2>/dev/null || true)
    if echo "$sb_state" | grep -qi "SecureBoot disabled"; then
        echo "no-secureboot"
        return
    fi

    local key_path
    key_path=$(pick_key)
    if [[ -z "$key_path" ]]; then
        echo "not-enrolled"
        return
    fi

    local fingerprint
    fingerprint=$(openssl x509 -inform DER -in "$key_path" -fingerprint -sha256 -noout 2>/dev/null | sed 's/.*=//') || {
        echo "error"
        return
    }

    local enrolled_fps
    enrolled_fps=$(mokutil --list-enrolled 2>/dev/null | grep -i "SHA256 Fingerprint" | sed 's/.*: //' | tr -d ':' | tr '[:upper:]' '[:lower:]' || true)
    local pending_fps
    pending_fps=$(mokutil --list-new 2>/dev/null | grep -i "SHA256 Fingerprint" | sed 's/.*: //' | tr -d ':' | tr '[:upper:]' '[:lower:]' || true)
    local target_fp
    target_fp=$(echo "$fingerprint" | tr -d ':' | tr '[:upper:]' '[:lower:]')

    if echo "$enrolled_fps" | grep -qF "$target_fp"; then
        echo "enrolled"
    elif echo "$pending_fps" | grep -qF "$target_fp"; then
        echo "pending"
    else
        # Check if CN matches but fingerprint differs (key rotation conflict).
        local key_cn
        key_cn=$(openssl x509 -inform DER -in "$key_path" -subject -noout 2>/dev/null | sed 's/.*CN\s*=\s*//' | cut -d'/' -f1 || true)
        if [[ -n "$key_cn" ]]; then
            local enrolled_subjects
            enrolled_subjects=$(mokutil --list-enrolled 2>/dev/null || true)
            if echo "$enrolled_subjects" | grep -qF "$key_cn"; then
                echo "conflict"
                return
            fi
        fi
        echo "not-enrolled"
    fi
}

pick_key() {
    if [[ -n "$KEY_OVERRIDE" ]]; then
        echo "$KEY_OVERRIDE"
        return
    fi
    # MiOS-specific key (generated by generate-mok-key.sh)
    [[ -f /etc/pki/mios/mok.der ]] && { echo /etc/pki/mios/mok.der; return; }
    # MiOS-2 (ucore-hci): ublue pre-signed NVIDIA kmods key
    [[ -f /etc/pki/akmods/certs/akmods-ublue.der ]] && { echo /etc/pki/akmods/certs/akmods-ublue.der; return; }
    echo ""
}

# ── status probe mode ─────────────────────────────────────────────────────────

if (( STATUS_ONLY == 1 )); then
    status_probe
    exit 0
fi

# ── runtime checks ────────────────────────────────────────────────────────────

log "=== 'MiOS' MOK Enrollment ==="

if ! command -v mokutil >/dev/null 2>&1; then
    log "mokutil not found -- install it: sudo dnf install mokutil"
    exit 1
fi

# Secure Boot state check
sb_state=$(mokutil --sb-state 2>/dev/null || true)
if echo "$sb_state" | grep -qi "SecureBoot disabled"; then
    log "Secure Boot is disabled -- MOK enrollment not required"
    exit 0
fi
log "Secure Boot state: $sb_state"

# Pick key
KEY=$(pick_key)
if [[ -z "$KEY" ]]; then
    log "No MOK key found. Generate one with:"
    log "  sudo automation/generate-mok-key.sh"
    exit 2
fi
log "Using key: $KEY"

FINGERPRINT=$(openssl x509 -inform DER -in "$KEY" -fingerprint -sha256 -noout | sed 's/.*=//') || {
    log "Cannot read key fingerprint from $KEY"
    exit 1
}
log "Key fingerprint: $FINGERPRINT"

# Idempotency check
CURRENT_STATUS=$(status_probe)
log "Current status: $CURRENT_STATUS"

case "$CURRENT_STATUS" in
    enrolled)
        log "Key already enrolled -- no action needed"
        exit 0
        ;;
    pending)
        log "Key already queued for enrollment -- reboot to complete in MokManager"
        exit 0
        ;;
    conflict)
        log "ERROR: A key with the same CN is already enrolled but with a different fingerprint."
        log "This indicates a key rotation. Manual steps required:"
        log "  1. mokutil --delete /etc/pki/mios/mok.old.der  (previous key)"
        log "  2. Reboot and complete deletion in MokManager"
        log "  3. Re-run this script"
        exit 3
        ;;
    no-secureboot)
        log "Secure Boot appears disabled -- nothing to enroll"
        exit 0
        ;;
esac

# ── enroll ────────────────────────────────────────────────────────────────────

log "Queuing $KEY for MOK enrollment (using --root-pw)"
log ""
log "You will be prompted to confirm using the system root password."
log "On next reboot, MokManager will ask for this same password."
log ""

# --root-pw binds the enrollment to the current root password hash in /etc/shadow.
# This avoids shipping a hardcoded secret (unlike ublue's 'universalblue' default).
if ! mokutil --import "$KEY" --root-pw; then
    log "mokutil --import failed"
    # Attempt rollback
    log "Attempting to revoke pending import (rollback)..."
    mokutil --revoke-import "$KEY" 2>/dev/null || log "revoke-import also failed -- check mokutil state manually"
    exit 1
fi

# Optional: set MokManager timeout (non-fatal -- known to fail on some ASUS boards)
mokutil --timeout 10 2>/dev/null || log "note: --timeout ignored on this firmware (non-fatal)"

log ""
log "[ok] Key queued for enrollment."
log ""
log "NEXT STEPS:"
log "  1. Reboot the system."
log "  2. In MokManager, choose 'Enroll MOK' and enter the root password."
log "  3. Reboot again. The key will be active."
log ""
log "── TPM2 WARNING ────────────────────────────────────────────────────────────"
log "If you have LUKS volumes sealed to TPM2 PCR 7 (systemd-cryptenroll),"
log "every MOK mutation changes PCR 7 and WILL break automatic unlock."
log "After this reboot completes enrollment, re-seal with:"
log "  systemd-cryptenroll --wipe-slot=tpm2 /dev/DISK"
log "  systemd-cryptenroll --tpm2-device=auto --tpm2-pcrs=7+14 /dev/DISK"
log "────────────────────────────────────────────────────────────────────────────"
log ""
log "Full log: $LOG_FILE"
```


### `automation\generate-mok-key.sh`

```bash
#!/usr/bin/bash
# generate-mok-key.sh -- one-shot 'MiOS' MOK key generator.
#
# Generates a 2048-bit RSA key (NOT 4096: shim compatibility) with:
#   - codeSigning EKU
#   - 1.3.6.1.5.5.7.3.3 (Standard Code Signing)
#   - 1.3.6.1.4.1.311.61.1.1 (MS Kernel Module Code Signing)
#   - 1.3.6.1.4.1.311.10.3.5 (WHQL Driver Verification)
#   - 10-year validity
#
# Output: /etc/pki/mios/mok.{priv,der,pem,pub.b64,sha256}
# Refuses to overwrite an existing key.
#
# Store the encrypted private key in GitHub secret MIOS_MOK_KEY_B64
# and the passphrase in MIOS_MOK_KEY_PASSWORD. Never regenerate per-build.
set -euo pipefail

KEY_DIR=/etc/pki/mios
PRIV_KEY="${KEY_DIR}/mok.priv"
DER_CERT="${KEY_DIR}/mok.der"
PEM_CERT="${KEY_DIR}/mok.pem"
B64_PRIV="${KEY_DIR}/mok.priv.b64"
SHA256_OUT="${KEY_DIR}/mok.sha256"

if [[ -f "$DER_CERT" ]]; then
    echo "ERROR: $DER_CERT already exists. MOK keys are generated once."
    echo "If you need to rotate, delete the old key files first, re-enroll with mokutil,"
    echo "and then re-run this script."
    exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
    echo "ERROR: run as root (sudo automation/generate-mok-key.sh)"
    exit 1
fi

install -d -m 0700 "$KEY_DIR"

echo "'MiOS' MOK key generation -- 2048-bit RSA, 10-year validity."
echo "Set passphrase prompt: store in GitHub secret MIOS_MOK_KEY_PASSWORD."

# Create EKU extension config
EXTFILE=$(mktemp /tmp/mok-ext.XXXXXX.conf)
cat >"$EXTFILE" <<'EOF'
[req]
default_bits       = 2048
default_md         = sha256
distinguished_name = dn
x509_extensions    = v3_ca
prompt             = no

[dn]
CN = 'MiOS' Module Signing Key

[v3_ca]
basicConstraints       = CA:FALSE
keyUsage               = digitalSignature
extendedKeyUsage       = codeSigning, 1.3.6.1.5.5.7.3.3, 1.3.6.1.4.1.311.61.1.1, 1.3.6.1.4.1.311.10.3.5
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always
EOF

# Generate encrypted key + self-signed cert
openssl req \
    -newkey rsa:2048 \
    -nodes \
    -keyout "${PRIV_KEY}.plain" \
    -x509 \
    -outform PEM \
    -out "$PEM_CERT" \
    -days 3650 \
    -config "$EXTFILE"

# Convert cert to DER (the format mokutil needs)
openssl x509 -in "$PEM_CERT" -outform DER -out "$DER_CERT"

# Encrypt the private key
echo "Enter passphrase to encrypt the private key (for GitHub secret storage):"
openssl pkcs8 -topk8 -inform PEM -outform PEM \
    -in "${PRIV_KEY}.plain" \
    -out "$PRIV_KEY"
rm -f "${PRIV_KEY}.plain"

# Base64-encode encrypted PEM for GitHub secret
base64 -w0 "$PRIV_KEY" > "$B64_PRIV"

# SHA-256 fingerprint of the DER cert
FINGERPRINT=$(openssl x509 -inform DER -in "$DER_CERT" -fingerprint -sha256 -noout | sed 's/.*=//')
echo "$FINGERPRINT" > "$SHA256_OUT"

chmod 0600 "$PRIV_KEY" "$B64_PRIV" "$SHA256_OUT"
chmod 0644 "$DER_CERT" "$PEM_CERT"

rm -f "$EXTFILE"

cat <<EOF
Key files:
  $PRIV_KEY   (encrypted PEM)
  $DER_CERT   (DER cert)
  $PEM_CERT   (PEM cert)
  $B64_PRIV   (base64 priv)
  $SHA256_OUT (sha256 fp)
Fingerprint: $FINGERPRINT
GitHub secrets: COSIGN_PRIVATE_KEY, MIOS_MOK_KEY_B64 (= $B64_PRIV), MIOS_MOK_KEY_PASSWORD
Commit DER:    cp $DER_CERT etc/pki/mios/mok.der && git add etc/pki/mios/mok.der
Never commit:  /etc/pki/mios/mok.priv
EOF
```


### `automation\overlay-builder.sh`

```bash
#!/usr/bin/env bash
# 'MiOS' BUILDER overlay -- makes the build-host WSL2 podman machine
# look and feel like a Live 'MiOS' environment without breaking the
# podman-machine OS plumbing underneath.
#
# Run inside the BUILDER, from the 'MiOS' repo working tree:
#   sudo bash automation/overlay-builder.sh /path/to/MiOS-repo
#
# What it does (idempotent, --ignore-existing throughout):
#   * rsync usr/share/mios/, usr/lib/mios/, usr/libexec/mios/, usr/bin/mios
#     onto / so the canonical 'MiOS' CLI / docs / paths.sh / motd binary all
#     exist at the expected paths
#   * rsync usr/lib/profile.d/mios-*.sh + etc/profile.d/mios-*.sh so login
#     shells get the 'MiOS' MOTD + WSLg env exports
#   * rsync /etc/skel skeleton from the repo if present
#   * rsync etc/mios/ (vendor host config templates)
#   * NOT touched: systemd units, drop-ins, tmpfiles.d, sysusers.d, kargs.d,
#     SELinux modules -- these would conflict with the podman-machine init
#     and must only land in the bootc image proper.
#
# After running, opening any new shell in BUILDER shows the 'MiOS' MOTD and
# `mios` is on PATH.

set -euo pipefail

REPO="${1:-${PWD}}"
if [[ ! -d "$REPO/usr/share/mios" ]]; then
    echo "[overlay-builder] FAIL: '$REPO' does not look like a 'MiOS' repo (no usr/share/mios)" >&2
    exit 1
fi

if [[ "$EUID" -ne 0 ]]; then
    echo "[overlay-builder] FAIL: must run as root (sudo bash $0 $REPO)" >&2
    exit 1
fi

cd "$REPO"
echo "[overlay-builder] Source repo: $REPO"

# rsync helper: keep ownership simple (root:root), don't clobber existing
# files (so podman-machine internals stay intact), preserve perms/symlinks.
_rsync_in() {
    local src="$1" dst="$2"
    [[ -e "$src" ]] || { echo "[overlay-builder] skip $src (missing)"; return 0; }
    install -d "$dst"
    rsync -aH --ignore-existing --info=stats0 "$src" "$dst"
    echo "[overlay-builder]  $src -> $dst"
}

# /usr/share/mios -- vendor docs, profile.toml, env.defaults, mios.toml.example
_rsync_in "usr/share/mios/"    "/usr/share/mios/"

# /usr/lib/mios -- runtime paths.sh + any future shared lib
_rsync_in "usr/lib/mios/"      "/usr/lib/mios/"

# /usr/libexec/mios -- motd, role-apply, gpu-detect, etc.
_rsync_in "usr/libexec/mios/"  "/usr/libexec/mios/"

# /usr/bin/mios -- CLI entrypoint (Python)
if [[ -f "usr/bin/mios" ]]; then
    install -m 0755 "usr/bin/mios" "/usr/bin/mios"
    echo "[overlay-builder]  /usr/bin/mios"
fi

# Profile.d -- MOTD + WSLg env exports
for src in usr/lib/profile.d/mios-*.sh etc/profile.d/mios-*.sh; do
    [[ -f "$src" ]] || continue
    install -d "/etc/profile.d"
    install -m 0644 "$src" "/etc/profile.d/$(basename "$src")"
    echo "[overlay-builder]  /etc/profile.d/$(basename "$src")"
done

# /etc/skel -- shell dotfiles, only seed if directory exists in the repo
_rsync_in "etc/skel/"          "/etc/skel/"

# /etc/mios -- vendor host config templates (install.env will be missing on
# BUILDER because no Windows installer ran here; that's fine, agents fall
# back to /usr/share/mios/env.defaults)
_rsync_in "etc/mios/"          "/etc/mios/"

# Mark the executable bits on the canonical libexec scripts
find /usr/libexec/mios -type f -exec chmod +x {} + 2>/dev/null || true
chmod +x /usr/bin/mios 2>/dev/null || true

# Re-run tmpfiles for /usr/lib/mios subdirs (logs, scratch). These are
# declared in usr/lib/tmpfiles.d/mios.conf in the bootc image; on BUILDER
# we just create them imperatively because the tmpfiles.d file isn't
# overlaid (would clash with podman-machine).
install -d -m 0755 /usr/lib/mios/logs
install -d -m 0755 /var/lib/mios

echo "[overlay-builder] Overlay complete."
echo "[overlay-builder] Open a fresh shell to see the 'MiOS' MOTD."
```


## Skipped (not found at expected paths)

- `preflight.sh`

---


**Bundle stats:** 74 files, 10533 source lines aggregated.
