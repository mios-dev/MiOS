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

# One platform-aware lookup for every native projection. A Windows checkout
# can contain Linux build artifacts too; select a runnable host suffix first.
native_bin() {
    local name="$1" override="${2:-}" suffix candidate
    local suffixes=("")
    case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) suffixes=(".exe");; esac
    if [[ -n "${MIOS_NATIVE_BIN_DIR:-}" ]]; then
        for suffix in "${suffixes[@]}"; do
            candidate="$MIOS_NATIVE_BIN_DIR/$name$suffix"
            [[ -x "$candidate" ]] && { printf '%s' "$candidate"; return 0; }
        done
        return 1
    fi
    if [[ -n "$override" && -x "$override" ]]; then
        printf '%s' "$override"
        return 0
    fi
    for suffix in "${suffixes[@]}"; do
        for candidate in "$ROOT/tools/native/target/release/$name$suffix" \
            "$ROOT/tools/native/target/debug/$name$suffix" \
            "/usr/bin/$name$suffix" "/usr/libexec/mios/$name$suffix" "/opt/mios/bin/$name$suffix"; do
            [[ -x "$candidate" ]] && { printf '%s' "$candidate"; return 0; }
        done
    done
    candidate="$(command -v "$name" || true)"
    [[ -n "$candidate" && -x "$candidate" ]] && { printf '%s' "$candidate"; return 0; }
    return 1
}

# Steps 6 and 7 census `git ls-files`, so a file git does not yet TRACK is
# invisible to both. Intent-to-add makes it visible without staging content, so
# one pass suffices. Without this, sync and the gate pass locally and CI goes
# red on the commit that finally tracked the file. See tasks.jsonl T-326.
_register_new_files() {
    command -v git >/dev/null 2>&1 || return 0
    git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 || return 0
    local new f
    # No path filter. The old list -- automation tools usr etc srv tests --
    # omitted src/, so a new crate under src/mios-rs was invisible to the
    # census: the tree looked synced locally and CI failed on a stale
    # manual-corpus.tsv. --exclude-standard already honours .gitignore, which
    # is what keeps target/ and friends out, so the list only added a trap.
    new="$(git -C "$ROOT" ls-files --others --exclude-standard 2>/dev/null || true)"
    [[ -n "$new" ]] || return 0
    while IFS= read -r f; do
        [[ -n "$f" ]] || continue
        step "     new file registered so the census can see it: $f"
        git -C "$ROOT" add -N -- "$f" >/dev/null 2>&1 || true
    done <<< "$new"
}

main() {
    local _gen required
    # Every migrated renderer is mandatory before any projection changes files.
    for required in mios-gen mios-unit-gen generate-names-registry xtask mios-toolchain-pin mios-ai-config mios-size-ceiling; do
        if ! native_bin "$required" >/dev/null; then
            echo "[sync-generated] FATAL: required native tool $required is missing; run bash automation/55-native-build.sh" >&2
            return 1
        fi
    done
    _gen="$(native_bin mios-gen)"

    # 1. Untracked file registration for index visibility
    step "1/23 [index.untracked] register new files in git index"
    _register_new_files

    # 2. Port allocation schema projection
    step "2/23 [ports.projection] render category port definitions"
    "$_gen" render-ports --root "$ROOT" >/dev/null

    # 3. System-wide environment globals and constants
    step "3/23 [globals.projection] render shell and powershell constants"
    "$_gen" render-globals --root "$ROOT" >/dev/null

    # 4. Freedesktop application entries
    step "4/23 [desktop.projection] render desktop application entries"
    "$_gen" render-desktop --root "$ROOT" >/dev/null

    # 5. Native manual roff pages
    step "5/23 [manpages.projection] validate and render roff documentation"
    "$_gen" render-manpages --root "$ROOT" --validate >/dev/null

    # 6. User and system dotfile SSOT projection
    step "6/23 [dotfiles.projection] synchronize editor and environment dotfiles"
    "$PY" tools/sync-dotfiles.py
    "$_gen" render-tmux-theme --write-fixture "$ROOT" >/dev/null
    "$_gen" render-btop-theme --root "$ROOT" >/dev/null
    "$_gen" render-fastfetch --root "$ROOT" --mock --out "$ROOT/tests/golden/fastfetch/mock.jsonc" >/dev/null

    # 7. WSL host configuration mirror
    step "7/23 [wsl.reference] mirror etc/wsl.conf to usr/lib/wsl.conf"
    if [[ -f "${ROOT}/etc/wsl.conf" ]]; then
        mkdir -p "${ROOT}/usr/lib"
        cp "${ROOT}/etc/wsl.conf" "${ROOT}/usr/lib/wsl.conf"
    fi

    # 8. Systemd container Quadlets
    step "8/23 [quadlets.projection] render container unit specifications"
    "$_gen" pod-quadlets --root "$ROOT" >/dev/null

    # 9. Canonical system name registry (AGY-1073: native-only; the Python
    # generator is deleted in the same commit that proved byte parity).
    step "9/23 [names.registry] synchronize canonical system names"
    _nr="$(native_bin generate-names-registry)"
    MIOS_DRIFT_ROOT="$ROOT" "$_nr" >/dev/null

    # 10. Topology comparison matrix
    step "10/23 [topology.matrix] compare seat versus blade capabilities"
    _gen="$(native_bin mios-gen)"
    "$_gen" metal-vs-hosted --root "$ROOT" >/dev/null

    # 11. Core system and governance indexes
    step "11/23 [indexes.projection] generate gate, pipeline, adr, and roadmap indexes"
    _gen="$(native_bin mios-gen)"
    "$_gen" gate-index --root "$ROOT" >/dev/null
    "$_gen" pipeline-index --root "$ROOT" >/dev/null
    "$_gen" adr-index --root "$ROOT" >/dev/null
    "$_gen" roadmap-index --root "$ROOT" >/dev/null

    # 12. Agent-pipe module boundary manifest
    step "12/23 [boundaries.manifest] project agent-pipe boundary manifest"
    _gen="$(native_bin mios-gen)"
    "$_gen" pipe-boundaries --root "$ROOT" >/dev/null

    # 13. Cargo native workspace members
    step "13/23 [workspace.manifest] synchronize cargo workspace member manifests"
    _gen="$(native_bin mios-gen)"
    "$_gen" cargo-manifests --root "$ROOT" >/dev/null

    # 14. Native deployment units (blade, UKI, and services)
    step "14/23 [deployment.projection] generate blade, uki, and service drop-ins"
    _unit_gen="$(native_bin mios-unit-gen || true)"
    if [[ -z "$_unit_gen" ]]; then
        echo "[sync-generated] FATAL: mios-unit-gen is required; build it in MiOS-DEV: cd tools/native && cargo build -p mios-unit-gen" >&2
        return 1
    fi
    for _projection in blade-dropins blade-karg uki-cmdline cockpit ipa-enroll bootc-install keybindings; do
        if ! "$_unit_gen" --list-projections | tr -d '\r' | grep -Fxq "$_projection"; then
            echo "[sync-generated] FATAL: mios-unit-gen does not advertise $_projection; rebuild it from this checkout" >&2
            return 1
        fi
        "$_unit_gen" "$_projection" --root "$ROOT" >/dev/null
    done

    # 15. Container image signature verification policy & egress firewall
    step "15/23 [security.policy] generate container image signature policy, egress firewall & bib configs"
    _gen="$(native_bin mios-gen)"
    "$_gen" cosign-policy --root "$ROOT" >/dev/null
    "$_gen" egress-firewall --root "$ROOT" >/dev/null
    "$_gen" bib-configs --root "$ROOT" >/dev/null

    # 16. Daily artifact release prompt template
    step "16/23 [artifacts.prompt] generate daily release prompt template"
    _ap="$(native_bin xtask)"
    "$_ap" artifact-prompt --root "$ROOT" >/dev/null

    # 17. Rust toolchain version pin
    step "17/23 [toolchain.pin] project rust toolchain version pin"
    _tp="$(native_bin mios-toolchain-pin)"
    "$_tp" >/dev/null

    # 18. AI client endpoint configurations
    step "18/23 [ai.config] project client and runtime ai endpoint configurations"
    _ac="$(native_bin mios-ai-config)"
    "$_ac" --root "$ROOT" >/dev/null

    # 19. Tracked repository size ceiling
    step "19/23 [metrics.ceiling] record tracked repository size ceiling"
    _sc="$(native_bin mios-size-ceiling)"
    "$_sc" >/dev/null

    # 20. Clean system environment baseline
    step "20/23 [env.baseline] snapshot clean system environment variables"
    if [ -x usr/libexec/mios/mios-env-snapshot ] || [ -r usr/libexec/mios/mios-env-snapshot ]; then
        env -i PATH="$PATH" HOME="${HOME:-/root}" \
            MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml" \
            MIOS_TOML_ROOT="$ROOT" \
            bash usr/libexec/mios/mios-env-snapshot \
            > usr/share/mios/reference/env-baseline.txt
    else
        step "     (mios-env-snapshot absent -- skipped)"
    fi

    # 21. AI repository and tool manifests
    step "21/23 [ai.manifests] compile ai repository and tool manifests"
    _gen="$(native_bin mios-gen)"
    "$_gen" ai-manifest --root "$ROOT" >/dev/null

    # 22. AI header metadata and strict schema catalog
    step "22/23 [ai.metadata] catalog ai header metadata and strict schema"
    "$PY" usr/libexec/mios/mios-ai-metadata.py --root "$ROOT" --export "$ROOT/usr/share/mios/ai/v1/metadata.json" >/dev/null

    # 23. Manual documentation corpus and ledger
    step "23/23 [corpus.ledger] compile manual documentation corpus and ledger"
    if [ -r usr/libexec/mios/mios-manual ]; then
        MIOS_ROOT="$ROOT" "$PY" usr/libexec/mios/mios-manual --root "$ROOT" render >/dev/null
        MIOS_ROOT="$ROOT" "$PY" usr/libexec/mios/mios-manual --root "$ROOT" ledger --write >/dev/null
        MIOS_ROOT="$ROOT" "$PY" usr/libexec/mios/mios-manual --root "$ROOT" coverage --write-floor >/dev/null
    else
        step "     (mios-manual absent -- skipped)"
    fi

    step "done -- 'git status' should now show only intended changes"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then main "$@"; fi
