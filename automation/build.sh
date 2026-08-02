#!/bin/bash
# AI-hint: This script is the primary build runner for MiOS, managing the build lifecycle by parsing `mios.toml` configurations, enforcing environment constraints, and rendering a TTY-safe ASCII progress UI for the build process.
# AI-related: /etc/mios/mios.toml, /usr/share/mios/mios.toml, mios-bootstrap, mios-build, mios-step, packagekit.service
# AI-functions: _pad, _hline, _row, _progress_bar, _step_header, _step_result, _section_header, _progress_frame, _fail_report, _warn_report, _final_summary
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/packages.sh"
register_common_masks

export MIOS_TOML="${MIOS_TOML:-/ctx/usr/share/mios/mios.toml}"
export MIOS_VENDOR_TOML="${MIOS_VENDOR_TOML:-$MIOS_TOML}"
BUILD_LOG="/tmp/mios-build.log"
VERSION_STR="$(cat "${SCRIPT_DIR}/../VERSION" 2>/dev/null || cat /ctx/VERSION 2>/dev/null || grep -m1 -E '^[[:space:]]*mios_version' "${MIOS_TOML:-${SCRIPT_DIR}/../usr/share/mios/mios.toml}" 2>/dev/null | sed -E 's/[^"]*"([^"]*)".*/\1/')"

exec > >(mask_filter | tee -a "$BUILD_LOG") 2>&1

W=72  # frame width (inner content = W-4 chars)

_pad() {
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
    local content="$1"
    local inner=$(( W - 4 ))
    printf '| %-*s |\n' "$inner" "${content:0:$inner}"
}

_progress_bar() {
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

_build_root="$(cd "${SCRIPT_DIR}/.." && pwd)"
if [[ ! -d "${_build_root}/.git" ]] && command -v git >/dev/null 2>&1; then
    (
        cd "${_build_root}"
        git init -q 2>/dev/null || true
        _ssot_name="$(grep -m1 -E '^[[:space:]]*fullname[[:space:]]*=' "${MIOS_TOML:-/usr/share/mios/mios.toml}" 2>/dev/null | sed -E 's/[^"]*"([^"]*)".*/\1/' || echo "User")"
        _ssot_email="$(grep -m1 -E '^[[:space:]]*email[[:space:]]*=' "${MIOS_TOML:-/usr/share/mios/mios.toml}" 2>/dev/null | sed -E 's/[^"]*"([^"]*)".*/\1/' || echo "User@localhost")"
        git config user.name "${_ssot_name:-User}" 2>/dev/null || true
        git config user.email "${_ssot_email:-user@localhost}" 2>/dev/null || true
        git add -A 2>/dev/null || true
    ) 2>/dev/null || true
fi

if [[ ! -f "$MIOS_TOML" ]]; then
    printf '[FATAL] mios.toml SSOT not found: %s\n' "$MIOS_TOML" >&2
    printf '        Set $MIOS_TOML to the path of the package manifest\n' >&2
    printf '        (default: /ctx/usr/share/mios/mios.toml during OCI build)\n' >&2
    exit 1
fi

CONTAINERFILE_SCRIPTS="01-system-files-overlay.sh 97-ssot-lint.sh 98-drift-checks.sh 99-postcheck.sh"

NON_FATAL_SCRIPTS="
  06-enable-external-repos.sh
  57-gnome.sh
  36-ceph-k3s.sh
  13-accounts-db.sh
  37-k3s-selinux.sh
  39-moby-engine.sh
  76-uki-render.sh
  22-akmod-guards.sh
  37-aichat.sh
  62-oh-my-posh.sh
  61-flatpak-bake.sh
  49-cosign-policy.sh
  50-uupd-installer.sh
  68-bake-kvmfr.sh
  69-bake-lookingglass-client.sh
  15-freeipa-client.sh
  58-gnome-remote-desktop.sh
  27-vm-gating.sh
  14-podman-machine-compat.sh
  53-enable-log-copy-service.sh
  91-strip-build-toolchain.sh
  65-bake-hyprland.sh
  66-bake-quickshell.sh
  67-bake-surfer.sh
"

auth=$(awk '/^[[:space:]]*build_catalog_authoritative[[:space:]]*=/ {
    if ($0 ~ /=[[:space:]]*true/) print "true"
}' "$MIOS_TOML" 2>/dev/null || true)

ALL_SCRIPTS=()
if command -v miosd >/dev/null 2>&1; then
    mapfile -t PHASE_SCRIPTS < <(miosd build --list 2>/dev/null | awk -F':' '{print $1}')
    if (( ${#PHASE_SCRIPTS[@]} > 0 )); then
        for _n in "${PHASE_SCRIPTS[@]}"; do
            echo "$CONTAINERFILE_SCRIPTS" | grep -qF "$_n" && continue
            if [[ -f "$SCRIPT_DIR/$_n" ]]; then
                ALL_SCRIPTS+=("$SCRIPT_DIR/$_n")
            fi
        done
    fi
fi

if (( ${#ALL_SCRIPTS[@]} == 0 )); then
    if [[ "$auth" == "true" && -f "$(dirname "$MIOS_TOML")/build_phases.json" ]]; then
        mapfile -t PHASE_SCRIPTS < <(python3 -c "import json, os; d = json.load(open('$(dirname "$MIOS_TOML")/build_phases.json')); [print(os.path.basename(p['script'])) for p in d]" 2>/dev/null)
        for _n in "${PHASE_SCRIPTS[@]}"; do
            echo "$CONTAINERFILE_SCRIPTS" | grep -qF "$_n" && continue
            if [[ -f "$SCRIPT_DIR/$_n" ]]; then
                ALL_SCRIPTS+=("$SCRIPT_DIR/$_n")
            fi
        done
    else
        for _s in "$SCRIPT_DIR"/[0-9][0-9]-*.sh; do
            _n="$(basename "$_s")"
            echo "$CONTAINERFILE_SCRIPTS" | grep -qF "$_n" && continue
            ALL_SCRIPTS+=("$_s")
        done
    fi
fi
TOTAL_SCRIPTS=${#ALL_SCRIPTS[@]}

_section_header
echo ""

TOTAL_START=$SECONDS

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
WARNED_JSON=()

for script in "${ALL_SCRIPTS[@]}"; do
    SCRIPT_NAME="$(basename "$script")"
    SCRIPT_COUNT=$(( SCRIPT_COUNT + 1 ))

    _step_header "$SCRIPT_COUNT" "$TOTAL_SCRIPTS" "$SCRIPT_NAME" "$(( SECONDS - TOTAL_START ))"

    STEP_START=$SECONDS

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
        WARNED_JSON+=("{\"script\":\"${SCRIPT_NAME}\",\"exit_code\":${SCRIPT_EXIT}}")
    else
        _step_result "fail" "$SCRIPT_NAME" "$STEP_ELAPSED"
        SCRIPT_FAIL=$(( SCRIPT_FAIL + 1 ))
        FAILED_SCRIPTS+=("$SCRIPT_NAME")
        FAIL_LOG+=("${SCRIPT_NAME} (${STEP_ELAPSED}s) exit=${SCRIPT_EXIT}")
    fi

    _progress_frame "$SCRIPT_COUNT" "$TOTAL_SCRIPTS" "$SCRIPT_NAME" "$TOTAL_ELAPSED"
    echo ""
done

_hline '-' '+' '+'
_row " POST-BUILD: Bloat removal"
_hline '-' '+' '+'
BLOAT_PACKAGES=$(get_packages "bloat" 2>/dev/null || true)
if [[ -n "${BLOAT_PACKAGES:-}" ]]; then
    echo "  Removing bloat packages"
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

echo ""
_row " POST-BUILD: Technical Invariant Validation (99-postcheck.sh)"
_hline '-' '+' '+'
if [[ -f "${SCRIPT_DIR}/99-postcheck.sh" ]]; then
    bash "${SCRIPT_DIR}/99-postcheck.sh"
else
    _row "  WARNING: 99-postcheck.sh not found -- skipping"
fi

echo ""
_row " POST-BUILD: SSOT-render conformance lint (97-ssot-lint.sh)"
_hline '-' '+' '+'
if [[ -f "${SCRIPT_DIR}/97-ssot-lint.sh" ]]; then
    bash "${SCRIPT_DIR}/97-ssot-lint.sh"
else
    _row "  WARNING: 97-ssot-lint.sh not found -- skipping"
fi

echo ""
_row " POST-BUILD: AI-plane source drift checks (98-drift-checks.sh)"
_hline '-' '+' '+'
if [[ -f "${SCRIPT_DIR}/98-drift-checks.sh" ]]; then
    _drift_root="$(cd "${SCRIPT_DIR}/.." && pwd)"
    git config --global --add safe.directory "${_drift_root}" 2>/dev/null || true
    git config --global --add safe.directory '*' 2>/dev/null || true
    if git -C "${_drift_root}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "${_drift_root}" config --local --unset-all http.https://github.com/.extraheader 2>/dev/null || true
        git -C "${_drift_root}" reset --hard HEAD -q 2>/dev/null || true
    fi
    if command -v python3 >/dev/null 2>&1; then
        for _proj in generate-ipa-enroll-env.py generate-uki-cmdline.py generate-cockpit-conf.py; do
            if [ -f "${_drift_root}/tools/${_proj}" ]; then
                if python3 "${_drift_root}/tools/${_proj}" >/dev/null 2>&1; then
                    echo "[reproject] ${_proj}: OK"
                else
                    echo "[reproject] WARN: ${_proj} failed"
                fi
            else
                echo "[reproject] WARN: ${_drift_root}/tools/${_proj} not found"
            fi
        done
    else
        echo "[reproject] WARN: python3 unavailable"
    fi
    bash "${SCRIPT_DIR}/98-drift-checks.sh"
else
    _row "  WARNING: 98-drift-checks.sh not found -- skipping"
fi

echo ""
_row " POST-BUILD: Agent-pipe unit tests (test_mios_*.py)"
_hline '-' '+' '+'
_agent_pipe_dir="$(cd "${SCRIPT_DIR}/.." && pwd)/usr/lib/mios/agent-pipe"
_test_py="/usr/lib/mios/agents/.venv/bin/python3"
if [[ -d "$_agent_pipe_dir" ]] && [[ -x "$_test_py" ]]; then
    _test_fails=0
    _DB_INTEGRATION_TESTS=" test_mios_db_config.py test_mios_build_catalog.py test_mios_config_audit.py test_mios_redact.py test_mios_vector.py "
    shopt -s nullglob
    for _t in "$_agent_pipe_dir"/test_mios_*.py; do
        _tb="$(basename "$_t")"
        if [[ "$_DB_INTEGRATION_TESTS" == *" $_tb "* ]]; then
            _row "  [SKIP] $_tb (DB-integration -- needs live pgvector; runs in CI/runtime)"
            continue
        fi
        if _tout="$( cd "$_agent_pipe_dir" && { unset $(compgen -v MIOS_ 2>/dev/null); "$_test_py" "$_tb"; } 2>&1 | tr -d '\0' )"; then
            _row "  [ OK ] $_tb"
        else
            _row "  [FAIL] $_tb"
            printf '%s\n' "$_tout" | sed 's/^/      /' >&2
            _test_fails=$((_test_fails + 1))
        fi
    done
    shopt -u nullglob
    if [[ "$_test_fails" -gt 0 ]]; then
        die "Agent-pipe unit tests: ${_test_fails} test script failed"
    fi
    _row "  all agent-pipe unit tests passed"
else
    _row "  WARNING: agent venv absent (or agent-pipe dir missing) -- skipping agent-pipe unit tests (non-fatal; venv retries next boot)"
fi

_libexec_dir="$(cd "${SCRIPT_DIR}/.." && pwd)/usr/libexec/mios"
if [[ -d "$_libexec_dir" ]] && command -v python3 >/dev/null 2>&1; then
    _lx_fails=0
    shopt -s nullglob
    for _t in "$_libexec_dir"/test_mios_*.py; do
        # MIOS_* resolver exports so hermetic libexec tests match the drift-gate.
        if _lxout="$( cd "$_libexec_dir" && { unset $(compgen -v MIOS_ 2>/dev/null); PYTHONIOENCODING=utf-8 python3 "$(basename "$_t")"; } 2>&1 )"; then
            _row "  [ OK ] $(basename "$_t")"
        else
            _row "  [FAIL] $(basename "$_t")"
            printf '%s\n' "$_lxout" | sed 's/^/      /' >&2
            _lx_fails=$((_lx_fails + 1))
        fi
    done
    shopt -u nullglob
    if [[ "$_lx_fails" -gt 0 ]]; then
        die "Libexec unit tests: ${_lx_fails} test script failed"
    fi
else
    _row "  WARNING: libexec dir or python3 missing -- skipping libexec unit tests"
fi

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
    warn "Skopeo not available"
fi

echo ""
_hline '-' '+' '+'
_row " LOG CHAIN: Flattening logs + version manifest -> ${MIOS_LOG_DIR}/"
_hline '-' '+' '+'
mkdir -p "$MIOS_LOG_DIR"
cp -v /var/log/dnf5.log* /var/log/hawkey.log "$MIOS_LOG_DIR/" 2>/dev/null || true

if [[ -f "$MIOS_VERSION_MANIFEST" ]]; then
    install -m 0644 "$MIOS_VERSION_MANIFEST" "$MIOS_VERSION_MANIFEST_FINAL"
    _row "  Version manifest: ${MIOS_VERSION_MANIFEST_FINAL} ($(wc -l < "$MIOS_VERSION_MANIFEST") rows)"
fi

{
    echo "# 'MiOS' ${VERSION_STR} Unified Build Log Chain"
    echo ""
    echo "# ====== build-time :latest -> observed-version manifest ======"
    if [[ -f "$MIOS_VERSION_MANIFEST" ]]; then
        cat "$MIOS_VERSION_MANIFEST"
    else
        echo ""
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

gzip -9f "$MIOS_BUILD_CHAIN_LOG" "$MIOS_BUILD_LOG" 2>/dev/null || true
gzip -9f "$MIOS_LOG_DIR"/dnf5.log* "$MIOS_LOG_DIR/hawkey.log" 2>/dev/null || true
_row "  Unified chain log: ${MIOS_BUILD_CHAIN_LOG}.gz"
_row "  Step count in chain: ${SCRIPT_COUNT}"

SBOM_ARTIFACTS_DIR="${MIOS_USR_DIR:-/usr/share/mios}/artifacts/sbom"
mkdir -p "$SBOM_ARTIFACTS_DIR" 2>/dev/null || true
MARKER_FILE="${SBOM_ARTIFACTS_DIR}/non-fatal-failures.json"
if [[ -d "$SBOM_ARTIFACTS_DIR" ]]; then
    if [[ ${#WARNED_JSON[@]} -gt 0 ]]; then
        (
            echo "["
            i=0
            len=${#WARNED_JSON[@]}
            for item in "${WARNED_JSON[@]}"; do
                i=$((i + 1))
                if [[ $i -eq $len ]]; then
                    echo "  $item"
                else
                    echo "  $item,"
                fi
            done
            echo "]"
        ) > "$MARKER_FILE"
    else
        echo "[]" > "$MARKER_FILE"
    fi
    _row "  Non-fatal failures marker: ${MARKER_FILE}"
fi

$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true
rm -rf /var/cache/dnf /var/cache/libdnf5 /tmp/geist-font /tmp/*.tar* /tmp/*.rpm 2>/dev/null || true
rm -rf /usr/share/doc/* /usr/share/man/* /usr/share/info/* 2>/dev/null || true
rm -rf /usr/share/gnome/help/* /usr/share/help/* 2>/dev/null || true
rm -f /var/log/dnf5.log* /var/log/hawkey.log 2>/dev/null || true
rm -rf /run/ceph /run/cockpit /run/k3s /tmp/mios-step-*.log 2>/dev/null || true
rm -f /var/lib/systemd/random-seed /tmp/mios-build.log "$MIOS_VERSION_MANIFEST" 2>/dev/null || true

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
