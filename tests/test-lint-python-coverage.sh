#!/usr/bin/env bash
# AI-hint: bash Coverage test for automation/lint-python.sh. Asserts the gate actually SEES a representative Python file from every payload area -- not t...
# AI-doc: usr/share/doc/mios/manual/tests.md

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LINT="${ROOT}/automation/lint-python.sh"

[ -f "$LINT" ] || { echo "ERROR: $LINT not found" >&2; exit 1; }

# Re-derive the gate's file set with its own logic, then assert membership.
# MIOS_LINT_PYTHON_LIST=1 makes lint-python print the set and exit 0.
mapfile -t seen < <(MIOS_LINT_PYTHON_LIST=1 bash "$LINT")

if [ "${#seen[@]}" -eq 0 ]; then
    echo "ERROR: lint-python.sh reported an EMPTY file set" >&2
    exit 1
fi

contains() {
    local needle="$1" f
    for f in "${seen[@]}"; do
        [ "$f" = "${ROOT}/${needle}" ] && return 0
    done
    return 1
}

# One representative per payload area. Each must be a file the gate can parse.
REQUIRED=(
    "usr/share/mios/owui/pipes/mios_agent_pipe.py"   # shipped INTO another program
    "usr/lib/mios/agent-pipe/server.py"              # the AI plane
    "tools/check-module-length.py"                   # build tooling
    "automation/validate-kargs.py"                   # build-step helper
    "tests/test-theme-merge.py"                      # the test suite itself
    "usr/bin/mios"                                   # extensionless entry point
)

missing=()
for rel in "${REQUIRED[@]}"; do
    [ -f "${ROOT}/${rel}" ] || continue        # tolerate a partial checkout
    contains "$rel" || missing+=("$rel")
done

if [ "${#missing[@]}" -gt 0 ]; then
    printf 'ERROR: lint-python.sh does not cover:\n' >&2
    printf '    %s\n' "${missing[@]}" >&2
    echo "A payload area dropped out of the gate's file set." >&2
    exit 1
fi

# The deliberate exclusions must still hold, or the gate reds on unrenderable
# input and someone "fixes" it by narrowing coverage again.
EXCLUDED=(
    "usr/libexec/mios/mios-dashboard"                # zipapp: not Python source
    "usr/share/mios/templates/python-tool"           # {{placeholders}}
    "tests/templates/golden/python-tool.snap"
)
wrongly_included=()
for rel in "${EXCLUDED[@]}"; do
    [ -f "${ROOT}/${rel}" ] || continue
    contains "$rel" && wrongly_included+=("$rel")
done

if [ "${#wrongly_included[@]}" -gt 0 ]; then
    printf 'ERROR: lint-python.sh wrongly includes unparseable input:\n' >&2
    printf '    %s\n' "${wrongly_included[@]}" >&2
    exit 1
fi

echo "[lint-python-coverage] PASS: ${#seen[@]} files, every payload area covered"
