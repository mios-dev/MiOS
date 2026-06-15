#!/usr/bin/env bash
# AI-hint: SSOT-render conformance lint -- asserts every ${MIOS_*} placeholder referenced in a Quadlet Exec=/Environment= line has BOTH a typed export/mapping in tools/lib/userenv.sh AND an allowlist entry in automation/15-render-quadlets.sh, so no placeholder silently relies only on its inline shell default (a dead key). Runs standalone or as a build sub-phase; pure bash + grep, no python deps.
# AI-related: ./tools/lib/userenv.sh, ./automation/15-render-quadlets.sh, ./usr/share/containers/systemd, /usr/share/mios/mios.toml
# AI-functions: _norm_refs, _in_userenv, _in_render, main
# automation/38-ssot-lint.sh
# ----------------------------------------------------------------------------
# THE META-FIX (W0-T1). The render pipeline (15-render-quadlets.sh) bakes
# ${MIOS_*:-default} placeholders in the Quadlet *.container files with the
# values resolved from mios.toml by userenv.sh. For that flow to actually
# carry an operator's mios.toml value through to a running container, a
# placeholder MUST be wired on BOTH ends:
#
#   (a) tools/lib/userenv.sh         -- a typed slot ("section.field","MIOS_X")
#                                       (or an explicit export) that EMITS the
#                                       MIOS_X env var from mios.toml; AND
#   (b) automation/15-render-quadlets.sh -- an allowlist entry (the envsubst
#                                       '${MIOS_X}' list AND/OR the bash-
#                                       fallback `for var in ...` list) so the
#                                       renderer actually substitutes MIOS_X.
#
# A placeholder wired on neither (or only one) end is a DEAD KEY: at render
# time it silently collapses to its inline `:-default`, so editing mios.toml
# does nothing and the value is un-tunable. This lint walks every Quadlet
# Exec=/Environment= line, pulls each referenced ${MIOS_*}, and asserts the
# two-sided wiring. It retroactively catches the known dead keys
# (MIOS_SGLANG_TOOL_PARSER, MIOS_PORT_CPU_NODE, MIOS_CPU_NODE_THREADS, ...).
#
# Default behaviour: emit a per-key error for every orphan and exit 1 if any
# orphan is found (so it can fail a CI/build step). It NEVER mutates anything
# -- read-only static analysis. Set MIOS_SSOT_LINT_SOFT=1 to report orphans
# but still exit 0 (advisory mode, e.g. while a fix is staged).
#
# Usage:
#   automation/38-ssot-lint.sh              # lint, exit 1 on any orphan
#   MIOS_SSOT_LINT_SOFT=1 automation/38-ssot-lint.sh   # advisory (exit 0)
#   MIOS_SSOT_LINT_ROOT=/path automation/38-ssot-lint.sh  # override repo root
#
# User-agnostic: no User=/uid assumptions, no network, no python.
# ----------------------------------------------------------------------------
set -euo pipefail

# --- Resolve the repo/system root (repo root IS system root). -----------------
# Standalone: derive from this script's location (automation/ -> repo root).
# As a build sub-phase the cwd is the build tree; the same derivation holds.
# MIOS_SSOT_LINT_ROOT overrides for out-of-tree invocation.
_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="${MIOS_SSOT_LINT_ROOT:-$(cd "$_self_dir/.." && pwd)}"

USERENV="$ROOT/tools/lib/userenv.sh"
RENDER="$ROOT/automation/15-render-quadlets.sh"
QUADLET_DIR="$ROOT/usr/share/containers/systemd"

_SOFT="${MIOS_SSOT_LINT_SOFT:-0}"

# Pre-flight: the three inputs must exist. Missing inputs is a hard error
# (the lint cannot make any assertion) -- but stay degrade-friendly: if the
# Quadlet dir is simply absent (e.g. a minimal checkout), PASS vacuously.
if [[ ! -f "$USERENV" ]]; then
    echo "[38-ssot-lint] FATAL: userenv.sh not found at $USERENV" >&2
    exit 2
fi
if [[ ! -f "$RENDER" ]]; then
    echo "[38-ssot-lint] FATAL: 15-render-quadlets.sh not found at $RENDER" >&2
    exit 2
fi
if [[ ! -d "$QUADLET_DIR" ]]; then
    echo "[38-ssot-lint] No Quadlet dir at $QUADLET_DIR -- nothing to lint (PASS)."
    exit 0
fi

echo "[38-ssot-lint] SSOT-render conformance lint"
echo "[38-ssot-lint]   quadlets: $QUADLET_DIR"
echo "[38-ssot-lint]   userenv:  $USERENV"
echo "[38-ssot-lint]   render:   $RENDER"

# --- (1) Collect every ${MIOS_*} referenced in an Exec=/Environment= line. ----
# We scan recursively (the dir has a users/ subtree). Match the directive at
# line start (Exec=, ExecStart=, ExecStartPre=, ExecStartPost=, Environment=).
# From those lines, extract bare placeholder NAMES of the form ${MIOS_...}
# (with or without a ':-default' tail). Critically we extract only the
# PLACEHOLDER inside ${...}; the left-hand `Environment=MIOS_FOO=` literal
# (a container-internal env var name being SET) is NOT a placeholder and is
# correctly ignored because it is not wrapped in ${...}.
_collect_refs() {
    # grep matching directive lines across all container/quadlet unit files,
    # then pull every ${MIOS_...} token, then strip ${ , the :-default tail,
    # and the trailing }.
    grep -rhE '^(Exec|ExecStart|ExecStartPre|ExecStartPost|Environment)=' "$QUADLET_DIR" 2>/dev/null \
        | grep -oE '\$\{MIOS_[A-Z0-9_]+(:-[^}]*)?\}' \
        | sed -E 's/^\$\{//; s/(:-[^}]*)?\}$//' \
        | sort -u
}

mapfile -t REFS < <(_collect_refs)

if [[ "${#REFS[@]}" -eq 0 ]]; then
    echo "[38-ssot-lint] No \${MIOS_*} placeholders in any Exec=/Environment= line (PASS)."
    exit 0
fi

# --- (2) Build the userenv.sh wiring set. -------------------------------------
# A var is "wired in userenv" if it appears, on a NON-comment line, either as
# a typed slot target  ("section.field", "MIOS_X")  -> the quoted token
# "MIOS_X"  -- or as an explicit  export MIOS_X=  /  MIOS_X=  assignment, or
# named in a legacy for-loop. We strip full-line comments first so a var that
# is only *mentioned* in prose (e.g. MIOS_CRAWL_CDP_URL in a doc paragraph)
# does NOT count as wired.
_userenv_body() {
    # Drop lines whose first non-space char is '#'. Inline trailing comments
    # are fine to keep -- a quoted slot token or an assignment is real code on
    # those lines.
    grep -vE '^[[:space:]]*#' "$USERENV" || true
}

USERENV_BODY="$(_userenv_body)"

_in_userenv() {
    local v="$1"
    # (a) typed-slot target: a double-quoted "MIOS_X" token
    if printf '%s\n' "$USERENV_BODY" | grep -qE "\"$v\"[[:space:]]*\)?,?"; then
        return 0
    fi
    # (b) explicit export / bare assignment:  export MIOS_X=   |   MIOS_X=
    if printf '%s\n' "$USERENV_BODY" | grep -qE "(^|[[:space:];])(export[[:space:]]+)?$v="; then
        return 0
    fi
    # (c) named verbatim in a legacy for-loop var list (word-boundary)
    if printf '%s\n' "$USERENV_BODY" | grep -qE "(^|[[:space:]])$v([[:space:]]|;|\$)"; then
        return 0
    fi
    return 1
}

# --- (3) Build the render-quadlets.sh allowlist set. --------------------------
# A var is "wired in render" if it appears in the envsubst allowlist string
# ( ${MIOS_X} ) and/or the bash-fallback `for var in ...` list ( MIOS_X ),
# on a NON-comment line. Both forms reduce to: the bareword MIOS_X occurs in
# render-quadlets.sh code. (render-quadlets.sh also EXPORTS a couple vars
# dynamically -- e.g. MIOS_CODE_SERVER_UID via `id -u` -- which the bareword
# match likewise accepts.)
_render_body() {
    grep -vE '^[[:space:]]*#' "$RENDER" || true
}

RENDER_BODY="$(_render_body)"

_in_render() {
    local v="$1"
    # word-boundary match for the bare var name (covers ${MIOS_X} in the
    # envsubst string and MIOS_X in the for-loop list)
    printf '%s\n' "$RENDER_BODY" | grep -qE "(^|[^A-Z0-9_])$v([^A-Z0-9_]|\$)"
}

# --- (4) Assert two-sided wiring for every referenced placeholder. ------------
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
            miss="$miss + 15-render-quadlets.sh allowlist"
        else
            miss="15-render-quadlets.sh allowlist"
        fi
    fi
    echo "[38-ssot-lint] ERROR: dead key \$$v -- referenced in a Quadlet Exec=/Environment= line but MISSING from: $miss" >&2
done

# --- (5) Summary + exit. ------------------------------------------------------
echo "[38-ssot-lint] ---------------------------------------------------------"
echo "[38-ssot-lint] checked $checked placeholder(s); $orphans orphan(s)."
if [[ "$orphans" -eq 0 ]]; then
    echo "[38-ssot-lint] PASS: every \${MIOS_*} placeholder is wired on both ends."
    exit 0
fi

echo "[38-ssot-lint] FAIL: $orphans orphaned key(s) above are un-tunable (collapse to their inline :-default)." >&2
echo "[38-ssot-lint]   Fix each by (a) adding a typed slot in tools/lib/userenv.sh AND" >&2
echo "[38-ssot-lint]   (b) adding it to BOTH allowlists in automation/15-render-quadlets.sh." >&2
if [[ "$_SOFT" == "1" ]]; then
    echo "[38-ssot-lint] (MIOS_SSOT_LINT_SOFT=1 -> advisory mode, exiting 0)"
    exit 0
fi
exit 1
