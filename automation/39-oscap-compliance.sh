#!/usr/bin/env bash
# AI-hint: BOOT-02 OpenSCAP scan-only build gate. Reads [compliance] from mios.toml; when enabled=true it runs `oscap xccdf eval` against an SSG datastream (explicit [compliance].datastream, else ssg-<os-release ID>-ds.xml located from the installed scap-security-guide RPM) under the configured profile, bakes the ARF + HTML reports into [compliance].report_path (in /usr, not /var), then defers the pass/fail verdict to mios-oscap-gate (counts FAILED rules at/above [compliance].severity_gate). DEFAULT OFF + degrade-open: disabled => exits 0 (complete no-op). Scan-only -- openscap-scanner + scap-security-guide are already in [packages.security]; remediation (oscap-im) is intentionally NOT wired. Runs in build.sh numeric order, before the Containerfile's final `bootc container lint`.
# AI-related: ../usr/libexec/mios/mios-oscap-gate, lib/packages.sh, lib/common.sh, ../usr/share/mios/mios.toml, build.sh, oscap
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=automation/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=automation/lib/packages.sh
source "${SCRIPT_DIR}/lib/packages.sh"

# Resolve the layered mios.toml the same way every build step does (honors
# $MIOS_TOML). No toml at all -> treat as disabled (degrade-open, never fail a build
# because config is unreadable).
TOML="$(_resolve_mios_toml)" || { log "[39-oscap] no mios.toml resolved -- gate disabled (no-op)"; exit 0; }

# _toml_get <dotted.key> [default] -- scalar read via tomllib (booleans normalized
# to true/false). Missing key / parse error -> default. No awk TOML guessing.
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
    log "[39-oscap] [compliance].enabled != true -- scan-only gate disabled (no-op)"
    exit 0
fi

# ── Opted in: from here a failure FAILS the build (fail-closed) ──────────────
command -v oscap >/dev/null 2>&1 \
    || die "[39-oscap] [compliance].enabled=true but 'oscap' not found (openscap-scanner missing from [packages.security]?)"

PROFILE="$(_toml_get compliance.profile standard)"
DS_CFG="$(_toml_get compliance.datastream '')"
SEVERITY="$(_toml_get compliance.severity_gate high)"
REMEDIATE="$(_toml_get compliance.remediate false)"
FETCH="$(_toml_get compliance.fetch_remote_resources false)"
REPORT_DIR="$(_toml_get compliance.report_path /usr/share/mios/compliance)"

# Remediation is deliberately out of scope for this scan-only gate. Warn (don't act)
# if an operator flipped remediate on -- wiring oscap-im / `--remediate` is a future
# opt-in step that needs openscap-utils + CentOS-shaped remediation content.
if [[ "$REMEDIATE" == "true" ]]; then
    warn "[39-oscap] [compliance].remediate=true is IGNORED: this is the scan-only gate."
    warn "[39-oscap] Remediation (oscap-im / --remediate) is a future operator-opt-in step."
fi

# Resolve the datastream path. Explicit path wins; otherwise derive the filename
# from the OS id and LOCATE it via the scap-security-guide RPM manifest (no
# hardcoded SSG content directory).
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

# SSG profile-id namespace is a structural constant of the SSG content format; the
# operator picks only the suffix via [compliance].profile.
PROFILE_ID="xccdf_org.ssgproject.content_profile_${PROFILE}"

# Reports bake into the image (/usr), never /var. Build-time mkdir under /usr is fine.
mkdir -p "$REPORT_DIR"
ARF="${REPORT_DIR}/oscap-results-arf.xml"
HTML="${REPORT_DIR}/oscap-report.html"

OSCAP_ARGS=(xccdf eval --profile "$PROFILE_ID" --results-arf "$ARF" --report "$HTML")
[[ "$FETCH" == "true" ]] && OSCAP_ARGS+=(--fetch-remote-resources)
OSCAP_ARGS+=("$DS_PATH")

log "[39-oscap] scanning: profile=${PROFILE_ID} severity_gate=${SEVERITY} ds=${DS_PATH}"
set +e
oscap "${OSCAP_ARGS[@]}"
RC=$?
set -e
# oscap exit codes: 0 = all pass, 2 = >=1 rule failed (NORMAL -> the severity parser
# decides if those fails gate the build), 1/anything>2 = oscap could not evaluate
# (tool error) -> fail the build.
if [[ "$RC" -gt 2 ]]; then
    die "[39-oscap] oscap tool error (rc=${RC}) -- scan could not complete"
fi
[[ -f "$ARF" ]] || die "[39-oscap] oscap produced no ARF (rc=${RC}) -- scan could not complete"

# Severity-gated verdict. Prefer the installed gate; fall back to the source tree.
GATE_BIN="/usr/libexec/mios/mios-oscap-gate"
[[ -f "$GATE_BIN" ]] || GATE_BIN="$(cd "${SCRIPT_DIR}/.." && pwd)/usr/libexec/mios/mios-oscap-gate"
[[ -f "$GATE_BIN" ]] || die "[39-oscap] severity parser missing: ${GATE_BIN}"

set +e
FAILS="$(python3 "$GATE_BIN" "$ARF" "$SEVERITY")"
GRC=$?
set -e
log "[39-oscap] reports baked: ${ARF} , ${HTML}"
if [[ "$GRC" -ne 0 ]]; then
    die "[39-oscap] compliance gate FAILED: ${FAILS} rule(s) at/above severity '${SEVERITY}' (see ${HTML})"
fi
log "[39-oscap] compliance gate PASSED: 0 failed rules at/above severity '${SEVERITY}'"
exit 0
