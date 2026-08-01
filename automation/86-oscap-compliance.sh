#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: BOOT-02 OpenSCAP scan-only build gate. Reads [compliance] from mios.toml; when enabled=true it runs `oscap xccdf eval` against an SSG datastream (explicit [compliance].datastream, else ssg-<os-release ID>-ds.xml located from the installed scap-security-guide RPM) under the configured profile, bakes the ARF + HTML reports into [compliance].report_path (in /usr, not /var), then defers the pass/fail verdict to mios-oscap-gate (counts FAILED rules at/above [compliance].severity_gate). DEFAULT OFF + degrade-open: disabled => exits 0 (complete no-op). Scan-only -- openscap-scanner + scap-security-guide are already in [packages.security]; remediation (oscap-im) is intentionally NOT wired. Runs in build.sh numeric order, before the Containerfile's final `bootc container lint`.
# AI-related: ../usr/libexec/mios/mios-oscap-gate, lib/packages.sh, lib/common.sh, ../usr/share/mios/mios.toml, build.sh, oscap
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/packages.sh"

TOML="$(_resolve_mios_toml)" || { mios_skip "no mios.toml resolved -- gate disabled (no-op)"; exit 0; }

_toml_get() {
    python3 - "$TOML" "$1" "${2:-}" <<'PY'
import sys, tomllib
path, key, dflt = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path, "rb") as f:
        cur = tomllib.load(f)
except Exception:
    print(dflt); sys.exit(0)
for part in key.split("."):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print(dflt); sys.exit(0)
print(("true" if cur else "false") if isinstance(cur, bool) else cur)
PY
}

ENABLED="$(_toml_get compliance.enabled false)"
if [[ "$ENABLED" != "true" ]]; then
    mios_skip "[compliance].enabled != true -- scan-only gate disabled (no-op)"
    exit 0
fi

command -v oscap >/dev/null 2>&1 \
    || die "[39-oscap] [compliance].enabled=true but 'oscap' not found (openscap-scanner missing from [packages.security]?)"

PROFILE="$(_toml_get compliance.profile standard)"
DS_CFG="$(_toml_get compliance.datastream '')"
SEVERITY="$(_toml_get compliance.severity_gate high)"
REMEDIATE="$(_toml_get compliance.remediate false)"
FETCH="$(_toml_get compliance.fetch_remote_resources false)"
REPORT_DIR="$(_toml_get compliance.report_path /usr/share/mios/compliance)"

if [[ "$REMEDIATE" == "true" ]]; then
    mios_warn "[compliance].remediate=true is IGNORED: this is the scan-only gate."
    mios_warn "Remediation (oscap-im / --remediate) is a future operator-opt-in step."
fi

if [[ -n "$DS_CFG" ]]; then
    DS_PATH="$DS_CFG"
else
    OS_ID=""
    [[ -f /etc/os-release ]] && OS_ID="$(. /etc/os-release; echo "${ID:-}")"
    DS_FILE="ssg-${OS_ID}-ds.xml"
    DS_PATH="$(rpm -ql scap-security-guide 2>/dev/null | grep -E "/${DS_FILE}$" | head -n1 || true)"
fi
[[ -n "$DS_PATH" && -f "$DS_PATH" ]] \
    || die "[39-oscap] SSG datastream not found (configured='${DS_CFG}', derived from os-release ID). Is scap-security-guide installed?"

PROFILE_ID="xccdf_org.ssgproject.content_profile_${PROFILE}"

mkdir -p "$REPORT_DIR"
ARF="${REPORT_DIR}/oscap-results-arf.xml"
HTML="${REPORT_DIR}/oscap-report.html"

OSCAP_ARGS=(xccdf eval --profile "$PROFILE_ID" --results-arf "$ARF" --report "$HTML")
[[ "$FETCH" == "true" ]] && OSCAP_ARGS+=(--fetch-remote-resources)
OSCAP_ARGS+=("$DS_PATH")

mios_log "Scanning: profile=${PROFILE_ID} severity_gate=${SEVERITY} ds=${DS_PATH}"
set +e
oscap "${OSCAP_ARGS[@]}"
RC=$?
set -e
if [[ "$RC" -gt 2 ]]; then
    die "[39-oscap] oscap tool error (rc=${RC}) -- scan could not complete"
fi
[[ -f "$ARF" ]] || die "[39-oscap] oscap produced no ARF (rc=${RC}) -- scan could not complete"

GATE_BIN="/usr/libexec/mios/mios-oscap-gate"
[[ -f "$GATE_BIN" ]] || GATE_BIN="$(cd "${SCRIPT_DIR}/.." && pwd)/usr/libexec/mios/mios-oscap-gate"
[[ -f "$GATE_BIN" ]] || die "[39-oscap] severity parser missing: ${GATE_BIN}"

set +e
FAILS="$(python3 "$GATE_BIN" "$ARF" "$SEVERITY")"
GRC=$?
set -e
mios_log "Reports baked: ${ARF} , ${HTML}"
if [[ "$GRC" -ne 0 ]]; then
    die "[39-oscap] compliance gate FAILED: ${FAILS} rule(s) at/above severity '${SEVERITY}' (see ${HTML})"
fi
mios_ok "compliance gate PASSED: 0 failed rules at/above severity '${SEVERITY}'"
exit 0
