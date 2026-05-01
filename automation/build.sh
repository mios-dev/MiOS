#!/bin/bash
# MiOS v0.2.0 — Master build runner
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
    _row "  MiOS ${VERSION_STR} -- Build Console"
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
    _row "  MiOS ${VERSION_STR} -- ${result_label}"
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
    WARN_LOG+=("malcontent-libs missing — flatpak may break")
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

# ── Log preservation (flatten all chain logs into /usr/lib/mios/logs/) ──────
echo ""
_hline '-' '+' '+'
_row " LOG CHAIN: Flattening all build logs -> /usr/lib/mios/logs/"
_hline '-' '+' '+'
mkdir -p /usr/lib/mios/logs
cp -v /var/log/dnf5.log* /var/log/hawkey.log /usr/lib/mios/logs/ 2>/dev/null || true
# Flatten per-step logs into single unified chain log
UNIFIED_LOG="/usr/lib/mios/logs/mios-build-chain.log"
echo "# MiOS ${VERSION_STR} Unified Build Log Chain — $(date '+%Y-%m-%d %H:%M:%S')" > "$UNIFIED_LOG"
for step_log in /tmp/mios-step-*.log; do
    [[ -f "$step_log" ]] || continue
    echo "" >> "$UNIFIED_LOG"
    echo "# ====== $(basename "$step_log") ======" >> "$UNIFIED_LOG"
    cat "$step_log" >> "$UNIFIED_LOG"
done
# Append main build log
echo "" >> "$UNIFIED_LOG"
echo "# ====== mios-build.log ======" >> "$UNIFIED_LOG"
[[ -f "$BUILD_LOG" ]] && cat "$BUILD_LOG" >> "$UNIFIED_LOG" || true
cp "$UNIFIED_LOG" /usr/lib/mios/logs/mios-build.log 2>/dev/null || true
_row "  Unified chain log: /usr/lib/mios/logs/mios-build-chain.log"
_row "  Step count in chain: $(ls /tmp/mios-step-*.log 2>/dev/null | wc -l)"

# ── Cleanup ─────────────────────────────────────────────────────────────────
$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true
rm -rf /var/cache/dnf /var/cache/libdnf5 /tmp/geist-font /tmp/*.tar* /tmp/*.rpm 2>/dev/null || true
rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/* 2>/dev/null || true
rm -rf /usr/share/gnome/help/* /usr/share/help/* 2>/dev/null || true
rm -f /var/log/dnf5.log* /var/log/hawkey.log 2>/dev/null || true
rm -rf /run/ceph /run/cockpit /run/k3s /tmp/mios-step-*.log 2>/dev/null || true
rm -f /var/lib/systemd/random-seed /tmp/mios-build.log 2>/dev/null || true

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
