#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: SSOT-render conformance lint -- asserts every ${MIOS_*} placeholder referenced in a Quadlet Exec=/Environment= line has BOTH a typed export/mapping in tools/lib/userenv.sh AND an allowlist entry in automation/34-render-quadlets.sh, so no placeholder silently relies only on its inline shell default (a dead key). Runs standalone or as a build sub-phase; pure bash + grep, no python deps.
# AI-related: ./tools/lib/userenv.sh, ./automation/34-render-quadlets.sh, ./usr/share/containers/systemd, /usr/share/mios/mios.toml
# AI-functions: _norm_refs, _in_userenv, _in_render, main
set -euo pipefail

# MIOS_SSOT_LINT_ROOT overrides for out-of-tree invocation.
_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="${MIOS_SSOT_LINT_ROOT:-$(cd "$_self_dir/.." && pwd)}"

USERENV="$ROOT/tools/lib/userenv.sh"
RENDER="$ROOT/automation/34-render-quadlets.sh"
QUADLET_DIR="$ROOT/usr/share/containers/systemd"

_SOFT="${MIOS_SSOT_LINT_SOFT:-0}"

if [[ ! -f "$USERENV" ]]; then
    echo "[97-ssot-lint] FATAL: userenv.sh not found at $USERENV" >&2
    exit 2
fi
if [[ ! -f "$RENDER" ]]; then
    echo "[97-ssot-lint] FATAL: 34-render-quadlets.sh not found at $RENDER" >&2
    exit 2
fi
if [[ ! -d "$QUADLET_DIR" ]]; then
    echo "[97-ssot-lint] No Quadlet dir at $QUADLET_DIR"
    exit 0
fi

echo "[97-ssot-lint] SSOT-render conformance lint"
echo "[97-ssot-lint]   quadlets: $QUADLET_DIR"
echo "[97-ssot-lint]   userenv:  $USERENV"
echo "[97-ssot-lint]   render:   $RENDER"

_collect_refs() {
    grep -rhE '^(Exec|ExecStart|ExecStartPre|ExecStartPost|Environment)=' "$QUADLET_DIR" 2>/dev/null \
        | grep -oE '\$\{MIOS_[A-Z0-9_]+(:-[^}]*)?\}' \
        | sed -E 's/^\$\{//; s/(:-[^}]*)?\}$//' \
        | sort -u
}

mapfile -t REFS < <(_collect_refs)

if [[ "${#REFS[@]}" -eq 0 ]]; then
    echo "[97-ssot-lint] No \${MIOS_*} placeholders in any Exec=/Environment= line"
    exit 0
fi

_userenv_body() {
    grep -vE '^[[:space:]]*#' "$USERENV" || true
}

USERENV_BODY="$(_userenv_body)"

_in_userenv() {
    local v="$1"
    if printf '%s\n' "$USERENV_BODY" | grep -qE "\"$v\"[[:space:]]*\)?,?"; then
        return 0
    fi
    if printf '%s\n' "$USERENV_BODY" | grep -qE "(^|[[:space:];])(export[[:space:]]+)?$v="; then
        return 0
    fi
    if printf '%s\n' "$USERENV_BODY" | grep -qE "(^|[[:space:]])$v([[:space:]]|;|\$)"; then
        return 0
    fi
    return 1
}

_render_body() {
    grep -vE '^[[:space:]]*#' "$RENDER" || true
}

RENDER_BODY="$(_render_body)"

_in_render() {
    local v="$1"
    printf '%s\n' "$RENDER_BODY" | grep -qE "(^|[^A-Z0-9_])$v([^A-Z0-9_]|\$)"
}

orphans=0
checked=0
for v in "${REFS[@]}"; do
    checked=$((checked + 1))
    in_ue=0; in_rq=0
    _in_userenv "$v" && in_ue=1
    _in_render  "$v" && in_rq=1
    if [[ "$in_ue" -eq 1 && "$in_rq" -eq 1 ]]; then
        continue
    fi
    orphans=$((orphans + 1))
    miss=""
    [[ "$in_ue" -eq 0 ]] && miss="userenv.sh slot/export"
    if [[ "$in_rq" -eq 0 ]]; then
        if [[ -n "$miss" ]]; then
            miss="$miss + 34-render-quadlets.sh allowlist"
        else
            miss="34-render-quadlets.sh allowlist"
        fi
    fi
    echo "[97-ssot-lint] ERROR: dead key \$$v" >&2
done

echo "[97-ssot-lint]"
echo "[97-ssot-lint] checked $checked placeholder; $orphans orphan"
if [[ "$orphans" -eq 0 ]]; then
    echo "[97-ssot-lint] PASS: every \${MIOS_*} placeholder is wired on both ends"
    exit 0
fi

echo "[97-ssot-lint] FAIL: $orphans orphaned key above are un-tunable" >&2
echo "[97-ssot-lint]   Fix each by adding a typed slot in tools/lib/userenv.sh AND" >&2
echo "[97-ssot-lint] adding it to BOTH allowlists in automation/34-render-quadlets.sh" >&2
if [[ "$_SOFT" == "1" ]]; then
    echo "[97-ssot-lint]"
    exit 0
fi
exit 1
