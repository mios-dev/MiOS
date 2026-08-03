#!/usr/bin/env bash
# AI-hint: One entry point that regenerates EVERY SSOT projection in dependency order (ports -> globals -> quadlets -> names -> env-baseline -> AI manifests), so a contributor cannot land a change with a stale generated artefact.
# AI-related: tools/render-ports.py, tools/render-globals.py, tools/generate-pod-quadlets.py, tools/generate-names-registry.py, tools/generate-ai-manifest.py, automation/98-drift-checks.sh
# AI-functions: main
#
# ORDER MATTERS and is the whole point of this script:
#   1. render-ports        [ports.categories] -> flat [ports] + ${MIOS_PORT_*:-N} fallbacks
#   2. render-globals      mios.toml -> automation/lib/globals.{sh,ps1}
#   3. pod-quadlets        mios.toml -> usr/share/containers/systemd/*
#   4. names-registry      -> referenced_names.txt + names.generated.txt
#   5. env-baseline        MUST run after 1-4, under a CLEAN env: a login shell
#                          sources /etc/profile.d/mios-env.sh and leaks the
#                          host's MIOS_* exports into the snapshot, which then
#                          can never match a CI regeneration.
#   6. AI manifests        LAST -- they embed the CONTENT of automation/ and
#                          tools/, so every step above invalidates them.
set -euo pipefail

ROOT="${MIOS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

step() { printf '[sync-generated] %s\n' "$1"; }

main() {
    step "1/6 ports  -- [ports.categories] projection + fallbacks"
    "$PY" tools/render-ports.py

    step "2/6 globals -- automation/lib/globals.{sh,ps1}"
    "$PY" tools/render-globals.py

    step "3/6 quadlets"
    "$PY" tools/generate-pod-quadlets.py >/dev/null

    step "4/6 names registry"
    "$PY" tools/generate-names-registry.py >/dev/null

    step "5/6 env-baseline (clean env)"
    if [ -x usr/libexec/mios/mios-env-snapshot ] || [ -r usr/libexec/mios/mios-env-snapshot ]; then
        env -i PATH="$PATH" HOME="${HOME:-/root}" \
            MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml" \
            MIOS_TOML_ROOT="$ROOT" \
            bash usr/libexec/mios/mios-env-snapshot \
            > usr/share/mios/reference/env-baseline.txt
    else
        step "     (mios-env-snapshot absent -- skipped)"
    fi

    step "6/6 AI manifests (last: they embed automation/ + tools/ content)"
    "$PY" tools/generate-ai-manifest.py >/dev/null

    step "done -- 'git status' should now show only intended changes"
}

main "$@"
