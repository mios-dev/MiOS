#!/usr/bin/env bash
# AI-hint: Curated global MiOS logging template (ADR-0012, doc-unified-pipeline.md). Source this
# from any stage/tool; the [NN-name] label is DERIVED at runtime from the caller's own filename, so
# the stage number is one self-identifying coordinate (OCI layer == stage == step == label),
# renumber-immune and terse. Severity tags: OK/WARN/ERR/SKIP/STEP. Replaces per-script ad-hoc
# log()/echo "==> ..." functions. This is a MiOS-AI recipe surface (one shared logger, no re-impl).
# AI-related: docs/agy/doc-unified-pipeline.md, automation/build.sh, usr/libexec/mios/*.sh
# AI-functions: mios_tag, mios_log, mios_ok, mios_warn, mios_err, mios_skip, mios_step
# ----------------------------------------------------------------------------
# Usage:
#   . /usr/lib/mios/log.sh           # or automation/lib/log.sh in the build tree
#   mios_log  "resolving kargs"      # -> [42-chrony-render] resolving kargs
#   mios_ok   "3 units linked"       # -> [42-chrony-render] OK 3 units linked
#   mios_warn "no cdi profile"       # -> [42-chrony-render] WARN no cdi profile   (stderr)
#   mios_err  "render failed"        # -> [42-chrony-render] ERR render failed     (stderr)
#   mios_skip "vm-only, host build"  # -> [42-chrony-render] SKIP vm-only, host build
# Override the derived label (wrappers, sourced contexts): export MIOS_LOG_TAG=name
# ----------------------------------------------------------------------------

# mios_tag: the caller's [NN-name] coordinate. Prefer an explicit MIOS_LOG_TAG, else the nearest
# numbered-stage file on the call stack (NN-name.sh -> NN-name), else the entry script's basename.
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

# --selftest: assert the label derives from the caller filename (renumber-immune).
if [ "${1:-}" = "--selftest" ]; then
    tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
    cp "${BASH_SOURCE[0]}" "$tmp/log.sh"
    cat >"$tmp/42-chrony-render.sh" <<'EOS'
#!/usr/bin/env bash
. "$(dirname "$0")/log.sh"
mios_log "hi"; mios_ok "done"; mios_warn "careful" 2>&1
EOS
    out=$(bash "$tmp/42-chrony-render.sh")
    if [ "$out" = "[42-chrony-render] hi
[42-chrony-render] OK done
[42-chrony-render] WARN careful" ]; then
        echo "log.sh selftest: PASS (label derived from filename, terse, severity tags)"
    else
        echo "log.sh selftest: FAIL"; printf '%s\n' "$out"; exit 1
    fi
fi
