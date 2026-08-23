#!/usr/bin/env bash
# AI-hint: bash Curated global MiOS logging template (ADR-0012, doc-unified-pipeline.md).
# AI-doc: usr/share/doc/mios/manual/mios.md

mios_tag() {
    if [ -n "${MIOS_LOG_TAG:-}" ]; then printf '%s' "$MIOS_LOG_TAG"; return; fi
    local i b
    for (( i=1; i<${#BASH_SOURCE[@]}; i++ )); do
        b=$(basename -- "${BASH_SOURCE[i]}" 2>/dev/null)
        case "$b" in
            [0-9][0-9]-*.sh) printf '%s' "${b%.sh}"; return ;;
        esac
    done
    b=$(basename -- "${BASH_SOURCE[1]:-${0:-mios}}" 2>/dev/null)
    printf '%s' "${b%.sh}"
}

mios_log()  { printf '[%s] %s\n'      "$(mios_tag)" "$*"; }
mios_ok()   { printf '[%s] OK %s\n'   "$(mios_tag)" "$*"; }
mios_step() { printf '[%s] STEP %s\n' "$(mios_tag)" "$*"; }
mios_skip() { printf '[%s] SKIP %s\n' "$(mios_tag)" "$*"; }
mios_warn() { printf '[%s] WARN %s\n' "$(mios_tag)" "$*" >&2; }
mios_err()  { printf '[%s] ERR %s\n'  "$(mios_tag)" "$*" >&2; }

MIOS_CHECK_INDEX="${MIOS_CHECK_INDEX:-/usr/share/mios/reference/drift-gate-index.tsv}"
declare -gA _MIOS_CHECK_ID=()
_mios_load_check_index() {
    [ "${#_MIOS_CHECK_ID[@]}" -gt 0 ] && return 0
    [ -r "$MIOS_CHECK_INDEX" ] || return 1
    local ord fn _rest
    while IFS=$'\t' read -r ord fn _rest; do
        case "$ord" in ''|'#'*) continue ;; esac
        _MIOS_CHECK_ID["$fn"]="$ord"
    done < "$MIOS_CHECK_INDEX"
}
mios_check_id() {
    _mios_load_check_index || { printf '??'; return; }
    local fn="${1:-}" i
    if [ -z "$fn" ]; then
        for (( i=1; i<${#FUNCNAME[@]}; i++ )); do
            case "${FUNCNAME[i]}" in check_*) fn="${FUNCNAME[i]}"; break ;; esac
        done
    fi
    printf '%s' "${_MIOS_CHECK_ID[$fn]:-??}"
}
mios_check_ok()  { printf '[%s:%s] OK %s\n'  "$(mios_tag)" "$(mios_check_id)" "$*"; }
mios_check_err() { printf '[%s:%s] ERR %s\n' "$(mios_tag)" "$(mios_check_id)" "$*" >&2; }
mios_check_skip(){ printf '[%s:%s] SKIP %s\n' "$(mios_tag)" "$(mios_check_id)" "$*"; }

if [ "${1:-}" = "--selftest" ]; then
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    cp "${BASH_SOURCE[0]}" "$tmp/log.sh"
    mkdir -p "$tmp/ref"
    echo -e "86\tcheck_test_func\ttest description" > "$tmp/ref/drift-gate-index.tsv"
    cat >"$tmp/42-chrony-render.sh" <<EOS
export MIOS_CHECK_INDEX="$tmp/ref/drift-gate-index.tsv"
. "\$(dirname "\$0")/log.sh"
check_test_func() {
    mios_check_ok "gate in sync"
}
mios_log "hi"; mios_ok "done"; mios_warn "Careful" 2>&1
check_test_func
EOS
    out=$(bash "$tmp/42-chrony-render.sh")
    if [ "$out" = "[42-chrony-render] hi
[42-chrony-render] OK done
[42-chrony-render] WARN careful
[42-chrony-render:86] OK gate in sync" ]; then
        echo "Log.sh selftest: PASS"
    else
        echo "Log.sh selftest: FAIL"; printf '%s\n' "$out"; exit 1
    fi
fi

