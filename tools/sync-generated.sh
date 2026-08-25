#!/usr/bin/env bash
# AI-hint: bash One entry point that regenerates EVERY SSOT projection in dependency order (ports -> globals -> quadlets -> names -> env-baseline -> AI manifests), ...
# AI-doc: usr/share/doc/mios/manual/tools.md
set -euo pipefail

ROOT="${MIOS_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$ROOT"

PY=""
_mios_pythons="${PYTHON:-}"
if [ -n "${LOCALAPPDATA:-}" ]; then
    # MSYS/Git-Bash sees the Windows var; translate to a POSIX path.
    _lad="$(printf '%s' "$LOCALAPPDATA" | sed 's|\\|/|g; s|^\([A-Za-z]\):|/\L\1|')"
    _mios_pythons="$_mios_pythons $_lad/Programs/Python/Python314/python.exe"
fi
for _cand in $_mios_pythons python3 python py; do
    [ -n "$_cand" ] || continue
    if "$_cand" -c 'import sys; sys.exit(0)' >/dev/null 2>&1; then
        PY="$_cand"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "[sync-generated] FATAL: no working python. Python is a declared MiOS" >&2
    echo "  dependency (mios.toml [apps.winget].pkgs -> Python.Python.3.14;" >&2
    echo "  python3 on Linux). Install it, or set \$PYTHON." >&2
    exit 1
fi

export MIOS_ROOT="$ROOT"
export MIOS_TOML_ROOT="$ROOT"
export MIOS_TOML="$ROOT/usr/share/mios/mios.toml"
export MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml"
export MIOS_VENDOR_TOML_D="$ROOT/usr/lib/mios/mios.d"
export MIOS_HOST_TOML="$ROOT/etc/mios/mios.toml"
export MIOS_HOST_TOML_D="$ROOT/etc/mios/mios.d"
export MIOS_USER_TOML="$ROOT/.mios-absent.toml"
export MIOS_USER_TOML_D="$ROOT/.mios-absent.d"

step() { printf '[sync-generated] %s\n' "$1"; }

# Steps 6 and 7 census `git ls-files`, so a file git does not yet TRACK is
# invisible to both. Intent-to-add makes it visible without staging content, so
# one pass suffices. Without this, sync and the gate pass locally and CI goes
# red on the commit that finally tracked the file. See TASKS.md T-326.
_register_new_files() {
    command -v git >/dev/null 2>&1 || return 0
    git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 || return 0
    local new f
    new="$(git -C "$ROOT" ls-files --others --exclude-standard \
        -- automation tools usr etc srv tests 2>/dev/null || true)"
    [[ -n "$new" ]] || return 0
    while IFS= read -r f; do
        [[ -n "$f" ]] || continue
        step "     new file registered so the census can see it: $f"
        git -C "$ROOT" add -N -- "$f" >/dev/null 2>&1 || true
    done <<< "$new"
}

main() {
    step "0/7 registering untracked files (the census reads the git index)"
    _register_new_files

    step "1/6 ports  -- [ports.categories] projection + fallbacks"
    "$PY" tools/render-ports.py

    step "2/6 globals -- automation/lib/globals.{sh,ps1}"
    "$PY" tools/render-globals.py

    step "2b/6 desktop -- usr/share/applications/*.desktop"
    "$PY" tools/render-desktop.py

    step "2c/6 man    -- usr/share/man (native roff, man(1) reads it directly)"
    "$PY" tools/render-manpages.py --validate

    step "3/6 quadlets"
    "$PY" tools/generate-pod-quadlets.py >/dev/null

    step "4/6 names registry"
    "$PY" tools/generate-names-registry.py >/dev/null

    # Index generators. Both were missing here, so adding a drift check or a
    # numbered automation phase left their index stale and the gate red on a
    # tree that otherwise looked synced.
    step "4a/6 seat-vs-blade comparison (derived from [blade.*])"
    MIOS_ROOT="$ROOT" "$PY" tools/generate-metal-vs-hosted.py >/dev/null

    step "4b/6 gate + pipeline + ADR + roadmap indexes"
    "$PY" tools/generate-gate-index.py >/dev/null
    "$PY" tools/generate-pipeline-index.py >/dev/null
    "$PY" tools/generate-adr-index.py >/dev/null
    "$PY" tools/roadmap-index.py >/dev/null

    step "4c/6 blade projections (drop-ins + the deploy-time karg)"
    "$PY" tools/generate-blade-dropins.py >/dev/null
    "$PY" tools/generate-blade-karg.py >/dev/null

    # AFTER the kargs.d producers: the UKI cmdline is derived from every
    # kargs.d/*.toml, and it was gated without ever being regenerated here.
    step "4d/6 UKI cmdline (derived from kargs.d)"
    "$PY" tools/generate-uki-cmdline.py >/dev/null

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

    step "6/7 AI manifests (they embed automation/ + tools/ content)"
    "$PY" tools/generate-ai-manifest.py >/dev/null

    # LAST: it censuses every TRACKED source file, so anything above moves it.
    # `git add` a new file BEFORE syncing, or its blocks land only once
    # committed -- green locally, red in CI.
    step "7/7 manual corpus ledger (last: it censuses every tracked source file)"
    if [ -r usr/libexec/mios/mios-manual ]; then
        # MIOS-GEN marker blocks first: api.md, ports-and-laws.md and tool-index.md
        # are DERIVED and gated, but `render` lived outside this pipeline, so any
        # SSOT or tools/ change left them stale and the gate red on a synced tree.
        MIOS_ROOT="$ROOT" "$PY" usr/libexec/mios/mios-manual --root "$ROOT" render >/dev/null
        MIOS_ROOT="$ROOT" "$PY" usr/libexec/mios/mios-manual --root "$ROOT" ledger --write >/dev/null
        MIOS_ROOT="$ROOT" "$PY" usr/libexec/mios/mios-manual --root "$ROOT" coverage --write-floor >/dev/null
    else
        step "     (mios-manual absent -- skipped)"
    fi

    step "done -- 'git status' should now show only intended changes"
}

main "$@"
