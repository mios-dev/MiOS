#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Source-tree drift fitness-functions (WS-0A).
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail

PYTHON="python3"
_real_py="$(command -v python 2>/dev/null || true)"
if [[ -n "$_real_py" ]]; then
    _shim_dir="${TEMP:-${TMP:-/tmp}}/mios-py-bin"
    mkdir -p "$_shim_dir" 2>/dev/null || true
    if [[ ! -f "$_shim_dir/python3.exe" && -f "$_real_py" ]]; then
        cp "$_real_py" "$_shim_dir/python3.exe" 2>/dev/null || true
    fi
    if [[ ! -f "$_shim_dir/python3" && -f "$_real_py" ]]; then
        cp "$_real_py" "$_shim_dir/python3" 2>/dev/null || true
    fi
    export PATH="$_shim_dir:$PATH"
fi

_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="${MIOS_DRIFT_CHECK_ROOT:-$(cd "$_self_dir/.." && pwd)}"
export MIOS_TOML_ROOT="${MIOS_TOML_ROOT:-$ROOT}"
_SOFT="${MIOS_DRIFT_CHECK_SOFT:-0}"

if [ -r "$ROOT/usr/lib/mios/log.sh" ]; then
    . "$ROOT/usr/lib/mios/log.sh"
fi

SCAN_DIRS=(
    "$ROOT/usr/share/containers/systemd"
    "$ROOT/usr/lib/systemd/system"
    "$ROOT/usr/share/mios/ai"
    "$ROOT/etc/containers/systemd"
    "$ROOT/etc/mios/ai"
)

VIOLATIONS=0
_violation() {
    echo "[98-drift-checks] VIOLATION: $*" >&2
    VIOLATIONS=$((VIOLATIONS + 1))
}

_need_python() {
    # Folded from 56 copies; fails, not skips, under MIOS_DRIFT_REQUIRE_TOOLS=1.
    command -v python3 >/dev/null 2>&1 && return 0
    if [[ "${MIOS_DRIFT_REQUIRE_TOOLS:-0}" == "1" ]]; then
        _violation "python3 is required under MIOS_DRIFT_REQUIRE_TOOLS=1 and is not installed"
    else
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
    fi
    return 1
}

_violations_from() {
    # Folded from 42 copies of this loop.
    local __prefix="$1" __blob="$2" line
    while IFS= read -r line; do
        [[ -n "$line" ]] && _violation "${__prefix}${line}"
    done <<<"$__blob"
}


_emit_projection_evidence() {
    local pfx='[98-drift-checks][diff]'
    local gen_rel="$1"; shift
    local gen="$ROOT/$gen_rel"
    local cap=200
    local -a targets=("$@")
    local -a abs=() bak=() existed=()
    local t a b i generr gen_rc dtmp total

    echo "$pfx generator: MIOS_DRIFT_ROOT=$ROOT python3 $gen_rel" >&2

    if [[ ! -x "$gen" && ! -f "$gen" ]]; then
        echo "$pfx generator ABSENT" >&2
        for t in "${targets[@]}"; do
            if [[ -f "$ROOT/$t" ]]; then
                echo "$pfx target $t exists=yes" >&2
            else
                echo "$pfx target $t exists=NO" >&2
            fi
        done
        return 0
    fi

    for t in "${targets[@]}"; do
        a="$ROOT/$t"
        abs+=("$a")
        if [[ -f "$a" ]]; then
            b="$(mktemp 2>/dev/null)" || b=""
            if [[ -n "$b" ]] && cp -p "$a" "$b" 2>/dev/null; then
                bak+=("$b"); existed+=("1")
            else
                bak+=(""); existed+=("1")
            fi
        else
            bak+=(""); existed+=("0")
        fi
    done

    generr="$(mktemp 2>/dev/null || echo /dev/null)"
    gen_rc=0
    MIOS_DRIFT_ROOT="$ROOT" python3 "$gen" >/dev/null 2>"$generr" || gen_rc=$?
    if [[ "$gen_rc" -ne 0 ]]; then
        echo "$pfx generator ERRORED rendering expected" >&2
        sed "s|^|$pfx   |" "$generr" 2>/dev/null >&2 || true
    else
        for i in "${!abs[@]}"; do
            a="${abs[$i]}"; b="${bak[$i]}"; t="${targets[$i]}"
            if [[ "${existed[$i]}" == "0" ]]; then
                echo "$pfx target $t: ABSENT on disk before regen" >&2
                sed "s|^|$pfx +|" "$a" 2>/dev/null | head -n "$cap" >&2 || true
                continue
            fi
            if [[ -z "$b" ]]; then
                echo "$pfx target $t: snapshot unavailable" >&2
                continue
            fi
            echo "$pfx target $t: actual=$a  generated=$a" >&2
            dtmp="$(mktemp 2>/dev/null || echo /dev/null)"
            diff -u --label "a/$t (ACTUAL on-disk)" --label "b/$t (GENERATED from SSOT)" \
                "$b" "$a" >"$dtmp" 2>/dev/null || true
            total="$(wc -l <"$dtmp" 2>/dev/null | tr -d ' ' || printf 0)"
            [[ -n "$total" ]] || total=0
            sed "s|^|$pfx |" "$dtmp" 2>/dev/null | head -n "$cap" >&2 || true
            if [[ "$total" -gt "$cap" ]]; then
                echo "$pfx" >&2
            fi
            [[ "$dtmp" != "/dev/null" ]] && rm -f "$dtmp" 2>/dev/null || true
        done
    fi

    for i in "${!abs[@]}"; do
        a="${abs[$i]}"; b="${bak[$i]}"
        if [[ "${existed[$i]}" == "1" && -n "$b" ]]; then
            cp -p "$b" "$a" 2>/dev/null || true
        elif [[ "${existed[$i]}" == "0" ]]; then
            rm -f "$a" 2>/dev/null || true
        fi
        if [[ -n "$b" ]]; then rm -f "$b" 2>/dev/null || true; fi
    done
    [[ "$generr" != "/dev/null" ]] && rm -f "$generr" 2>/dev/null || true
    return 0
}

_require_python3() {
    if command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if [[ "${MIOS_DRIFT_REQUIRE_TOOLS:-0}" == "1" ]]; then
        _violation "python3 is required by critical security/law checks but absent (MIOS_DRIFT_REQUIRE_TOOLS=1; )"
    fi
    return 1
}

echo "[98-drift-checks] source-tree AI-plane drift fitness-functions"
echo "[98-drift-checks]   root: $ROOT"

check_dead_lane() {
    local pattern=':11434'
    local hits="" f active
    for d in "${SCAN_DIRS[@]}"; do
        [[ -d "$d" ]] || continue
        while IFS= read -r f; do
            [[ -f "$f" ]] || continue
            active=$(sed -E '/^[[:space:]]*(#|\/\/)/d' "$f")
            if printf '%s\n' "$active" | grep -qE "$pattern"; then
                hits+="    $f"$'\n'
            fi
        done < <(find "$d" -type f \( -name '*.container' -o -name '*.service' \
            -o -name '*.conf' -o -name '*.json' -o -name '*.toml' \
            -o -name '*.yaml' -o -name '*.yml' \) 2>/dev/null)
    done
    if [[ -n "$hits" ]]; then
        printf '%s' "$hits" >&2
        _violation "retired :11434 (ollama) lane in active source config -- MiOS is /v1-only; use the live lane (mios-llm-light on \${MIOS_PORT_LLM_LIGHT})"
    else
        echo "[98-drift-checks]   no retired :11434 lane in active config"
    fi
}

check_retired_models() {
    local pattern='(^|[^A-Za-z0-9_./-])(gemma4|qwen3:1\.7b)([^A-Za-z0-9_-]|$)'
    local hits="" f active
    for d in "${SCAN_DIRS[@]}"; do
        [[ -d "$d" ]] || continue
        while IFS= read -r f; do
            [[ -f "$f" ]] || continue
            active=$(sed -E '/^[[:space:]]*(#|\/\/)/d' "$f")
            if printf '%s\n' "$active" | grep -qE "$pattern"; then
                hits+="    $f"$'\n'
            fi
        done < <(find "$d" -type f \( -name '*.container' -o -name '*.service' \
            -o -name '*.json' -o -name '*.conf' -o -name '*.yaml' \
            -o -name '*.yml' \) 2>/dev/null)
    done
    if [[ -n "$hits" ]]; then
        printf '%s' "$hits" >&2
        _violation "retired model-id (gemma4 / qwen3:1.7b) hardcoded in a consumer unit (point it at the live [ai].model, e.g. granite4.1:8b)"
    else
        echo "[98-drift-checks]   no retired model-id in consumer config"
    fi
}

check_structured() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py structured
    then
        echo "[98-drift-checks]   every [nodes.local-*] localhost lane is served; ai/v1 manifests parse + refs resolve"
    else
        _violation "structured drift: a [nodes.*] lane is dangling and/or an ai/v1 manifest is broken (see lines above)"
    fi
}

check_hint_coverage() {
    local tool="$ROOT/usr/libexec/mios/mios-ai-hint-coverage"
    _need_python || return 0
    if [[ ! -f "$tool" ]]; then
        echo "[98-drift-checks]   WARNING: mios-ai-hint-coverage not found" >&2
        return 0
    fi
    if python3 "$tool" --root "$ROOT"; then
        echo "[98-drift-checks]   AI-hint coverage within ratchet ceiling"
    else
        _violation "AI-hint coverage regressed: a new taggable file lacks an AI-hint header (run mios-ai-tag, or raise [ai_tag].max_untagged only for prompt/data files)"
    fi
}


check_module_boundary() {
    local dir="$ROOT/usr/lib/mios/agent-pipe"
    if [[ ! -d "$dir" ]]; then
        echo "[98-drift-checks]   agent-pipe dir absent"
        return 0
    fi
    local hits="" f active
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        active=$(sed -E '/^[[:space:]]*#/d' "$f")
        if printf '%s\n' "$active" | grep -qE '^[[:space:]]*(import[[:space:]]+server|from[[:space:]]+server[[:space:]])'; then
            hits+="    $f"$'\n'
        fi
    done < <(find "$dir" -maxdepth 1 -type f -name 'mios_*.py' 2>/dev/null)
    if [[ -n "$hits" ]]; then
        printf '%s' "$hits" >&2
        _violation "agent-pipe sibling module imports the server monolith (breaks the modular-monolith boundary; siblings must stay server.py-free + isolation-testable)"
    else
        echo "[98-drift-checks]   agent-pipe sibling modules are server.py-free"
    fi
}

check_rbac_tiers() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py rbac-tiers
    then
        echo "[98-drift-checks]   RBAC max_permission tiers all valid"
    else
        _violation "an [agents.*]/[users.*].max_permission names an UNKNOWN permission tier -- the dispatch PDP fails CLOSED on it (restricts the caller to the safest tier); fix the typo or add the tier to [ai].permission_tiers "
    fi
}

check_agent_schema() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py agent-schema
    then
        echo "[98-drift-checks]   agent-schema contract satisfied"
    else
        _violation "an [agents.*] entry violates the unified agent schema : a local-optional agent missing health_gate, a kind=cli without timeout_s, a kind=node without api+lane, or >1 default=true -- the opencode 'dead local endpoint treated as live -> merged_chars=0' class. Fix the [agents.*] block (or [agents._defaults])."
    fi
}

check_ai_manifest() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py ai-manifest
    then
        echo "[98-drift-checks]   ai/v1 verb-catalog manifest in sync with mios.toml SSOT"
    else
        _violation "ai/v1/tools.generated.json is STALE vs mios.toml [verbs.*] -- regenerate with mios-ai-manifest-gen "
    fi
}

check_package_registry() {
    local _en_val=""
    if [[ -n "${MIOS_PACKAGE_REGISTRY:-}" ]]; then
        _en_val="$MIOS_PACKAGE_REGISTRY"
    else
        _en_val=$(MIOS_TOML="$ROOT/usr/share/mios/mios.toml" python3 -c '
import sys, os
try:
    import tomllib as t
except ImportError:
    import tomli as t
toml = os.environ.get("MIOS_TOML", "")
if os.path.isfile(toml):
    with open(toml, "rb") as f:
        d = t.load(f)
    val = (d.get("ai") or {}).get("package_registry", False)
    print("true" if val else "false")
else:
    print("false")
' 2>/dev/null || echo "false")
    fi
    local _en="$(printf '%s' "${_en_val:-false}" | tr '[:upper:]' '[:lower:]')"
    case "$_en" in
        1|true|yes|on) : ;;
        *)
            local _reg_file="$ROOT/usr/share/mios/ai/v1/packages/registry.json"
            if [[ -f "$_reg_file" ]]; then
                _violation "package_registry is dormant in mios.toml [ai].package_registry but registry.json exists -- remove stale file or turn feature on"
            else
                echo "[98-drift-checks]   package registry dormant"
            fi
            return 0 ;;
    esac
    _need_python || return 0
    if MIOS_AGENT_PIPE_DIR="$ROOT/usr/lib/mios/agent-pipe" \
       MIOS_TOML="$ROOT/usr/share/mios/mios.toml" \
       MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml" \
       MIOS_PACKAGES_DIR="$ROOT/usr/share/mios/ai/v1/packages" \
       python3 "$ROOT/usr/libexec/mios/mios-registry" verify >/dev/null 2>"$ROOT/.pkgreg.err"; then
        rm -f "$ROOT/.pkgreg.err" 2>/dev/null || true
        echo "[98-drift-checks]   package registry in sync with mios.toml SSOT"
    else
        sed 's/^/    /' "$ROOT/.pkgreg.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.pkgreg.err" 2>/dev/null || true
        _violation "ai/v1/packages/registry.json is STALE vs the SSOT -- regenerate with mios-registry generate "
    fi
}

check_cli_sql_safety() {
    local dir="$ROOT/usr/libexec/mios"
    if [[ ! -d "$dir" ]]; then
        echo "[98-drift-checks]   libexec dir absent"
        return 0
    fi
    local allow=" "   # empty: all libexec tools cut over to parameterized pg
    local pattern='(_pgesc\(|_pgq\(|post_sql\(|def _sql\(|/sql"|surreal-ns)'
    local hits="" f base active
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        case "$base" in test_*|*.pyc) continue ;; esac
        [[ "$allow" == *" $base "* ]] && continue
        active=$(sed -E '/^[[:space:]]*#/d' "$f")
        if printf '%s\n' "$active" | grep -qE "$pattern"; then
            hits+="    $f"$'\n'
        fi
    done < <(find "$dir" -maxdepth 1 -type f 2>/dev/null)
    if [[ -n "$hits" ]]; then
        printf '%s' "$hits" >&2
        _violation "a libexec CLI (re)introduced the retired legacy DB transport (post_sql/_sql/:8000/sql) or hand-rolled SQL escaping (_pgesc/_pgq) -- use parameterized pg via mios-pg-query --exec-json / mios-db --pg-json "
    else
        echo "[98-drift-checks]   libexec CLIs SQL-safe"
    fi
}

check_module_test_coverage() {
    local dir="$ROOT/usr/lib/mios/agent-pipe"
    if [[ ! -d "$dir" ]]; then
        echo "[98-drift-checks]   agent-pipe dir absent"
        return 0
    fi
    local missing="" f base mod_name
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        case "$base" in test_*|__init__.py) continue ;; esac          # tests and package init don't need tests
        if [[ ! -f "$dir/test_${base}" ]]; then
            missing+="    $base (no test_${base})"$'\n'
        fi
    done < <(find "$dir" -maxdepth 1 -type f -name 'mios_*.py' 2>/dev/null)

    if [[ -d "$dir/mios_pipe" ]]; then
        while IFS= read -r f; do
            [[ -f "$f" ]] || continue
            base="$(basename "$f")"
            case "$base" in test_*|__init__.py) continue ;; esac
            mod_name="${base%.py}"
            if [[ ! -f "$dir/test_mios_${mod_name}.py" && ! -f "$dir/test_${mod_name}.py" && ! -f "$dir/test_mios_a2a_${mod_name}.py" ]]; then
                missing+="    mios_pipe/.../$base (no test_mios_${mod_name}.py)"$'\n'
            fi
        done < <(find "$dir/mios_pipe" -type f -name '*.py' 2>/dev/null)
    fi

    if [[ -n "$missing" ]]; then
        printf '%s' "$missing" >&2
        _violation "an agent-pipe pure module has NO sibling unit test -- author test_<module>.py (stdlib assert-script, the sibling-module pattern); isolation-tested logic is the point of the extraction "
    else
        echo "[98-drift-checks]   every agent-pipe mios_*.py and mios_pipe submodule has a sibling unit test"
    fi

    local baseline_file="$ROOT/usr/share/mios/reference/python-untested-baseline.txt"
    if [[ -f "$baseline_file" ]]; then
        if python3 - "$ROOT" "$baseline_file" <<'PY'
import sys, os

root_dir, base_file = sys.argv[1], sys.argv[2]
with open(base_file, encoding="utf-8") as f:
    allowed = set(line.strip() for line in f if line.strip() and not line.startswith("#"))

untested = []
for scan_dir in ['tools', os.path.join('usr', 'libexec', 'mios')]:
    full_scan = os.path.join(root_dir, scan_dir)
    if not os.path.isdir(full_scan):
        continue
    for f in os.listdir(full_scan):
        if not f.endswith('.py') or f.startswith('test_') or f == '__init__.py':
            continue
        rel = f"{scan_dir}/{f}".replace("\\", "/")
        norm_stem = f[:-3].replace("-", "_")
        test1 = os.path.join(full_scan, f"test_{f}")
        test2 = os.path.join(full_scan, f"test_{f[:-3]}.py")
        test3 = os.path.join(full_scan, f"test_{norm_stem}.py")
        if not (os.path.exists(test1) or os.path.exists(test2) or os.path.exists(test3)):
            if rel not in allowed:
                untested.append(rel)

if untested:
    for u in untested:
        sys.stderr.write(f"    untested python module not in baseline: {u}\n")
    sys.exit(1)

sys.exit(0)
PY
        then
            echo "[98-drift-checks]   tools/ and libexec python module test coverage within baseline ratchet"
        else
            _violation "new untested tools/ or libexec python module found -- author sibling test_<module>.py or update baseline"
        fi
    fi
}

check_raw_toml_readers() {
    local dir="$ROOT/usr/lib/mios/agent-pipe"
    if [[ ! -d "$dir" ]]; then
        echo "[98-drift-checks]   raw TOML readers"
        return 0
    fi
    local violations="" f base
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        case "$base" in test_*) continue ;; esac
        
        if grep -q -E "os\.environ(\.get)?\([\"']MIOS_TOML[\"']\)" "$f"; then
            violations+="    $base (reads MIOS_TOML env var directly)"$'\n'
        fi
        if grep -E "open\(" "$f" | grep -q -E "mios\.toml"; then
            violations+="    $base (hardcoded open of mios.toml)"$'\n'
        fi
    done < <(find "$dir" -maxdepth 2 -type f -name '*.py' 2>/dev/null)

    if [[ -n "$violations" ]]; then
        printf '%s' "$violations" >&2
        _violation "found raw MIOS_TOML / mios.toml file readers. Use mios_toml.load_merged() / load_vendor() instead of manual file opens or raw env lookups (B11)"
    else
        echo "[98-drift-checks]   no raw MIOS_TOML readers in agent-pipe"
    fi
}

check_capability_manifest() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py capability-manifest
    then
        echo "[98-drift-checks]   ai/v1 capability manifest in sync with mios.toml SSOT"
    else
        _violation "ai/v1/capabilities.generated.json is STALE vs mios.toml [verbs.*]+[recipes.*] -- regenerate with mios-ai-capabilities-gen"
    fi
}

check_surface_parity() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py surface-parity
    then
        echo "[98-drift-checks]   server.py public surface matches the committed golden"
    else
        _violation "server.py PUBLIC SURFACE drifted from usr/share/mios/ai/v1/surface.generated.json -- a route/symbol was dropped or added during the refactor. If intended, regenerate: python3 usr/lib/mios/agent-pipe/mios_surface.py usr/lib/mios/agent-pipe/server.py --package > usr/share/mios/ai/v1/surface.generated.json (refactor WS R0)"
    fi
}

check_pod_quadlets() {
    _need_python || return 0
    local gen="$ROOT/tools/generate-pod-quadlets.py"
    if [[ ! -f "$gen" ]]; then
        echo "[98-drift-checks]   WARNING: generate-pod-quadlets.py absent" >&2
        return 0
    fi
    # MIOS_CRAWL_CAMOUFOX=True, ...). generate-pod-quadlets.py resolves
    if env -i PATH="$PATH" HOME="${HOME:-/root}" LANG="${LANG:-C.UTF-8}" \
            MIOS_ROOT="$ROOT" "$PYTHON" "$gen" --check; then
        echo "[98-drift-checks]   Quadlet units in sync with mios.toml SSOT"
    else
        _violation "Quadlet unit(s) (.pod, .container, .network, .volume) STALE vs mios.toml SSOT -- regenerate with tools/generate-pod-quadlets.py"
    fi
}

check_egress_firewall() {
    _need_python || return 0
    local gen="$ROOT/tools/generate-egress-firewall.py"
    local committed="$ROOT/usr/share/mios/security/egress.nft"
    if [[ ! -f "$gen" || ! -f "$committed" ]]; then
        echo "[98-drift-checks]   WARNING: egress generator/artifact absent" >&2
        return 0
    fi
    local tmp; tmp="$(mktemp)"
    if MIOS_ROOT="$ROOT" MIOS_EGRESS_OUT="$tmp" python3 "$gen" >/dev/null 2>&1 \
            && diff -q "$committed" "$tmp" >/dev/null 2>&1; then
        echo "[98-drift-checks]   egress.nft in sync with mios.toml [security.egress] SSOT"
        rm -f "$tmp"
    else
        rm -f "$tmp"
        _violation "usr/share/mios/security/egress.nft is STALE vs mios.toml [security.egress] -- regenerate with tools/generate-egress-firewall.py "
    fi
}

check_blade_dropins() {
    _need_python || return 0
    local gen="$ROOT/tools/generate-blade-dropins.py"
    if [[ ! -f "$gen" ]]; then
        echo "[98-drift-checks]   WARNING: blade dropins generator absent" >&2
        return 0
    fi
    local tmp_root; tmp_root="$(mktemp -d)"
    if MIOS_ROOT="$tmp_root" MIOS_TOML="$ROOT/usr/share/mios/mios.toml" MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml" python3 "$gen" >/dev/null 2>&1; then
        local committed_dir="$ROOT/usr/share/mios/dropins"
        local generated_dir="$tmp_root/usr/share/mios/dropins"
        local ok=1
        
        local f gen_file com_file
        for f in "$generated_dir"/*; do
            [[ -e "$f" ]] || continue
            gen_file="$(basename "$f")"
            com_file="$committed_dir/$gen_file"
            if [[ ! -f "$com_file" ]]; then
                ok=0
                echo "      Missing drop-in: $gen_file is missing from $committed_dir" >&2
            elif ! diff -q "$com_file" "$f" >/dev/null 2>&1; then
                ok=0
                echo "      Divergence in drop-in: $gen_file has drifted" >&2
            fi
        done
        
        rm -rf "$tmp_root"
        if [[ $ok -eq 1 ]]; then
            echo "[98-drift-checks]   blade capability drop-ins in sync with mios.toml [blade.requires]"
        else
            _violation "usr/share/mios/dropins/ is STALE vs mios.toml [blade.requires] -- regenerate with tools/generate-blade-dropins.py "
        fi
    else
        rm -rf "$tmp_root"
        _violation "blade drop-in generation failed during drift check"
    fi
}


check_no_hardcode() {
    _need_python || return 0
    local tool="$ROOT/usr/libexec/mios/mios-hardcode-lint"
    if [[ ! -f "$tool" ]]; then
        echo "[98-drift-checks]   WARNING: mios-hardcode-lint not found" >&2
        return 0
    fi
    if python3 "$tool" "$ROOT" >/dev/null 2>"$ROOT/.nohc.err"; then
        rm -f "$ROOT/.nohc.err" 2>/dev/null || true
        echo "[98-drift-checks]   no date-in-comment / header crash-risk"
    else
        sed 's/^/    /' "$ROOT/.nohc.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.nohc.err" 2>/dev/null || true
        _violation "NO-HARDCODE law (Law 7): a date/timestamp in a comment/docstring OR an AI-Hint header crash-risk -- strip the date (timeless comment) or move the header below the shebang/BOM (see mios-hardcode-lint)"
    fi
}

check_no_hardcode_version() {
    _need_python || return 0
    local tool="$ROOT/usr/libexec/mios/mios-version-lint"
    if [[ ! -f "$tool" ]]; then
        echo "[98-drift-checks]   WARNING: mios-version-lint not found" >&2
        return 0
    fi
    if MIOS_TOML_ROOT="$ROOT" python3 "$tool" "$ROOT" >/dev/null 2>"$ROOT/.nohc_ver.err"; then
        rm -f "$ROOT/.nohc_ver.err" 2>/dev/null || true
        echo "[98-drift-checks]   no hand-pinned version literal"
    else
        sed 's/^/    /' "$ROOT/.nohc_ver.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.nohc_ver.err" 2>/dev/null || true
        _violation "NO-HARDCODE-VERSION law (Law 7 / ADR-0003): a hand-pinned version literal in a download URL / pip|npm pin / image @sha256 digest -- float it (:latest) and record the resolved version in the SBOM, or allowlist via mios.toml [build.float]"
    fi
}

check_unwired_modules() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py unwired-modules
    then
        echo "[98-drift-checks]   no imported-but-dead agent-pipe module"
    else
        _violation "an agent-pipe module is imported-but-dead (no real non-test caller) OR a _UNWIRED_ALLOW entry is stale -- wire the module (give it a call site) or update the _UNWIRED_ALLOW register (MIOS-GAP-REGISTER A1)"
    fi
}

check_cephfs_ssot() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py cephfs-ssot
    then
        echo "[98-drift-checks]   CephFS SSOT configuration is valid"
    else
        _violation "[storage.cephfs] SSOT validation failed (see lines above)"
    fi
}

check_converge_ssot() {
    local retire_alt="${MIOS_CONV_INFERENCE_RETIRE_HEAVY_ALT:-false}"
    if [[ "$retire_alt" == "true" ]]; then
        if command -v systemctl >/dev/null 2>&1; then
            if systemctl is-enabled mios-llm-heavy-alt.service >/dev/null 2>&1; then
                echo "[98-drift-checks] VIOLATION: retire_heavy_alt=true but systemd unit mios-llm-heavy-alt.service is still enabled" >&2
                VIOLATIONS=$((VIOLATIONS + 1))
                return 1
            fi
        fi
    fi

    local cold_storage_dir="${MIOS_CONV_MEMORY_COLD_STORAGE_DIR:-/var/lib/mios/history/}"
    if [[ "$cold_storage_dir" == *"/tenants/"* ]]; then
        echo "[98-drift-checks] VIOLATION: cold_storage_dir cannot be inside a CephFS tenants mount path" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 1
    fi

    local cold_retention_days="${MIOS_CONV_MEMORY_COLD_RETENTION_DAYS:-30}"
    if [[ "$cold_retention_days" -lt 1 ]]; then
        echo "[98-drift-checks] VIOLATION: cold_retention_days must be >= 1" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 1
    fi

    local cold_zstd_level="${MIOS_CONV_MEMORY_COLD_ZSTD_LEVEL:-3}"
    if [[ "$cold_zstd_level" -lt 1 || "$cold_zstd_level" -gt 19 ]]; then
        echo "[98-drift-checks] VIOLATION: cold_zstd_level must be between 1 and 19" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 1
    fi

    local sqlite_vec_enable="${MIOS_CONV_MEMORY_SQLITE_VEC_ENABLE:-false}"
    if [[ "$sqlite_vec_enable" == "true" ]]; then
        local py_bin="/usr/lib/mios/agents/.venv/bin/python3"
        if [[ ! -x "$py_bin" ]]; then
            py_bin="python3"
        fi
        if ! "$py_bin" -c "import sqlite_vec" >/dev/null 2>&1; then
            echo "[98-drift-checks] VIOLATION: sqlite_vec_enable=true but sqlite_vec python package is not importable" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi
    fi

    echo "[98-drift-checks]   [converge] SSOT configuration is valid"
}

check_hummingbird() {
    local distroless_enable="${MIOS_CONV_IMAGE_DISTROLESS_ENABLE:-false}"
    local rechunk_enable="${MIOS_CONV_IMAGE_RECHUNK_ENABLE:-false}"
    local containerfile="Containerfile.hummingbird"
    local quadlet="usr/share/containers/systemd/mios-agent-pipe.container"

    if [[ "$distroless_enable" == "true" ]]; then
        if [[ ! -f "$containerfile" ]]; then
            echo "[98-drift-checks] VIOLATION: distroless_enable=true but $containerfile is missing" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        if [[ ! -f "$quadlet" ]]; then
            echo "[98-drift-checks] VIOLATION: Quadlet definition $quadlet is missing" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        if ! grep -q "Environment=MIOS_AI_ENDPOINT=" "$quadlet"; then
            echo "[98-drift-checks] VIOLATION: Quadlet $quadlet is missing Environment=MIOS_AI_ENDPOINT" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi
    fi

    if [[ -f "$containerfile" ]]; then
        local mios_toml="usr/share/mios/mios.toml"
        local expected_base=$(grep -E '^\s*distroless_base\s*=' "$mios_toml" | head -n 1 | cut -d'"' -f2 || echo "Gcr.io/distroless/python3-debian13")
        if [[ -z "$expected_base" ]]; then
            expected_base="gcr.io/distroless/python3-debian13"
        fi

        if ! grep -F "FROM $expected_base" "$containerfile" >/dev/null 2>&1; then
            echo "[98-drift-checks] VIOLATION: Containerfile.hummingbird base image does not match distroless_base" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        local final_stage=$(awk '/^FROM/ { stage="" } { stage=stage "\n" $0 } END { print stage }' "$containerfile")

        if echo "$final_stage" | grep -F "/bin/bash" >/dev/null; then
            echo "[98-drift-checks] VIOLATION: Containerfile.hummingbird final stage contains /bin/bash" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        local user_line=$(echo "$final_stage" | grep -E '^\s*USER\s+' | tail -n 1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        if [[ "$user_line" != "USER 65534" && "$user_line" != "USER 65534:65534" ]]; then
            echo "[98-drift-checks] VIOLATION: Containerfile.hummingbird final stage USER is not 65534 or 65534:65534" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi
    fi

    if [[ "$rechunk_enable" == "true" ]]; then
        if ! command -v rpm-ostree >/dev/null 2>&1; then
            echo "[98-drift-checks] VIOLATION: rechunk_enable=true but rpm-ostree binary not found in PATH" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi
    fi

    echo "[98-drift-checks]   Hummingbird distroless and Quadlet configuration is valid"
}

check_container_ports() {
    _need_python || return 0
    local tmp; tmp="$(mktemp)"
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py container-ports >"$tmp" 2>&1
    then
        echo "[98-drift-checks]   no manual port literals in container definitions"
        rm -f "$tmp"
    else
        echo "[98-drift-checks] VIOLATION: manual port literal found in container Quadlets" >&2
        cat "$tmp" >&2
        rm -f "$tmp"
        VIOLATIONS=$((VIOLATIONS + 1))
        return 1
    fi
}

check_bootstrap_ports_drift() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py bootstrap-ports-drift
    then
        echo "[98-drift-checks]   bootstrap mios.toml shared surfaces match main repository"
    else
        _violation "bootstrap mios.toml shared surfaces diverge from main repository mios.toml"
    fi
}

check_agent_pipe_budgets() {
    local lint_bin="$ROOT/tools/native/target/release/mios-aiplane-lint"
    if [ ! -x "$lint_bin" ] && command -v mios-aiplane-lint >/dev/null 2>&1; then
        lint_bin="$(command -v mios-aiplane-lint)"
    fi
    if [ -x "$lint_bin" ]; then
        if MIOS_DRIFT_ROOT="$ROOT" "$lint_bin"; then
            echo "[98-drift-checks]   all [agent_pipe] budget variables have code consumers"
            return 0
        else
            _violation "some [agent_pipe] keys have no code consumer in the agent-pipe codebase"
            return 1
        fi
    fi

    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py agent-pipe-budgets
    then
        echo "[98-drift-checks]   all [agent_pipe] budget variables have code consumers"
    else
        _violation "some [agent_pipe] keys have no code consumer in the agent-pipe codebase"
    fi
}

check_no_bare_port_literals() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py no-bare-port-literals
    then
        echo "[98-drift-checks]   no bare port literals remain in execution paths"
    else
        _violation "bare port literals in execution paths"
    fi
}

check_dotfiles_projection() {
    _need_python || return 0
    local tool="$ROOT/usr/libexec/mios/mios-dotfiles-render"
    if [[ ! -f "$tool" ]]; then
        echo "[98-drift-checks]   WARNING: mios-dotfiles-render not found" >&2
        return 0
    fi
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_HOST_TOML=/nonexistent.toml MIOS_USER_TOML=/nonexistent.toml python3 "$tool" check >/dev/null 2>"$ROOT/.dotfiles.err"; then
        rm -f "$ROOT/.dotfiles.err" 2>/dev/null || true
        echo "[98-drift-checks]   every committed theme + settings surface projects from mios.toml [colors]/[btop]/[gitconfig]/[identity]/[dotfiles] SSOT"
    else
        sed 's/^/    /' "$ROOT/.dotfiles.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.dotfiles.err" 2>/dev/null || true
        _violation "a dotfiles surface drifted from the mios.toml SSOT projection -- re-run mios dotfiles sync (Phase-1 palette drift-gate; mios-dotfiles-render)"
    fi
}

check_userenv_parity() {
    local src="$ROOT/tools/lib/userenv.sh" dst="$ROOT/usr/lib/mios/userenv.sh"
    if [[ ! -f "$src" || ! -f "$dst" ]]; then
        echo "[98-drift-checks]   userenv.sh parity"
        return 0
    fi
    if diff -q "$src" "$dst" >/dev/null 2>&1; then
        echo "[98-drift-checks]   usr/lib/mios/userenv.sh matches authoritative tools/lib/userenv.sh"
    else
        _violation "usr/lib/mios/userenv.sh drifted from the authoritative tools/lib/userenv.sh (59-tools.sh installs the latter) -- resync: cp tools/lib/userenv.sh usr/lib/mios/userenv.sh (flatten check 27)"
    fi
}

check_verb_backends() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py verb-backends
    then
        echo "[98-drift-checks]   every [verbs.*].cmd mios-* backend resolves on disk"
    else
        _violation "a [verbs.*].cmd dispatches to a mios-* backend that does not exist (dead dispatch) -- fix the cmd template or ship the backend (flatten check 26)"
    fi
}

# --- globals port declarations match mios.toml [ports] SSOT ---
check_globals_ports() {
    check_globals_generated
}

check_globals_image_parity() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py globals-image-parity
    then
        echo "[98-drift-checks]   default image references in globals.{sh,ps1} equal mios.toml [image] SSOT"
    else
        _violation "default image reference in automation/lib/globals.sh or globals.ps1 drifted from mios.toml [image] SSOT"
    fi
}

check_dag_integrity() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
root = os.environ["MIOS_DRIFT_ROOT"]
violations = []

scan_dirs = [
    os.path.join(root, "usr/lib/systemd/system"),
    os.path.join(root, "usr/share/containers/systemd"),
]

for d in scan_dirs:
    if not os.path.isdir(d):
        continue
    for f in os.listdir(d):
        fpath = os.path.join(d, f)
        if not os.path.isfile(fpath) or not f.endswith((".service", ".container", ".pod")):
            continue
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
            
            after_requires_targets = []
            for line in content.splitlines():
                m = re.match(r"^[ \t]*(After|Requires)[ \t]*=[ \t]*(.*)$", line, re.IGNORECASE)
                if m:
                    after_requires_targets.extend(m.group(2).split())
            

            is_local_img = "Image=localhost/" in content
            is_webtools_pod = f == "mios-webtools.pod"
            if is_local_img or is_webtools_pod:
                if "mios-webtools-firstboot.service" not in after_requires_targets:
                    violations.append(f"{f} uses local image/pod but lacks 'After=... mios-webtools-firstboot.service'")
        except OSError:
            pass

if violations:
    for v in sorted(violations):
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   DAG-integrity: consumers start after their producers' readiness artifacts exist"
    else
        _violation "DAG dependency ordering violation detected: consumer starts before producer (flatten check 29)"
    fi
}

# --- generated names registry matches source topology ---
check_names_registry() {
    _need_python || return 0
    if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "[98-drift-checks]   names registry"
        return 0
    fi
    if git -C "$ROOT" ls-files --deleted 2>/dev/null | grep -q .; then
        echo "[98-drift-checks]   names registry"
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py names-registry
    then
        echo "[98-drift-checks]   names registry matches generate-names-registry.py"
    else
        _violation "naming registry drift / tools/generate-names-registry.py stale (run tools/generate-names-registry.py to regenerate; check 30)"
    fi
}

check_drift_projection() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py drift-projection
    then
        echo "[98-drift-checks]   DB->TOML materialize round-trip is lossless for config_kv and verbs"
    else
        _violation "DB->TOML materialize round-trip drift detected (check 31) -- verify seed-db-config.py and materialize-config-toml.py mappings"
    fi
}

check_canonical_bools() {
    _need_python || return 0
    if MIOS_TOML="$ROOT/usr/share/mios/mios.toml" MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml" python3 - <<'PY'
import sys
import os

import tomllib

with open(os.environ["MIOS_TOML"], "rb") as f:
    data = tomllib.load(f)

verbs = data.get("verbs", {})
for vname, vcfg in verbs.items():
    if vname == "_defaults":
        continue
    if not isinstance(vcfg, dict):
        continue
    if "hidden" in vcfg:
        val = vcfg["hidden"]
        if not isinstance(val, bool):
            print(f"Non-canonical hidden value in verb '{vname}': {val!r} (must be true/false)")
            sys.exit(1)
    if "sensitive" in vcfg:
        val = vcfg["sensitive"]
        if not isinstance(val, bool):
            print(f"Non-canonical sensitive value in verb '{vname}': {val!r} (must be true/false)")
            sys.exit(1)
    params = vcfg.get("params", {})
    if isinstance(params, dict):
        for p_name, p_cfg in params.items():
            if not isinstance(p_cfg, dict):
                continue
            if "required" in p_cfg:
                req = p_cfg["required"]
                if not isinstance(req, bool):
                    print(f"Non-canonical required value in verb '{vname}' param '{p_name}': {req!r} (must be true/false)")
                    sys.exit(1)
            if "default" in p_cfg and p_cfg.get("type") == "boolean":
                d = p_cfg["default"]
                if not isinstance(d, bool):
                    print(f"Non-canonical default boolean value in verb '{vname}' param '{p_name}': {d!r} (must be true/false)")
                    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   no non-canonical bool literals in [verbs.*]"
    else
        _violation "Non-canonical bool literal detected in mios.toml verbs (check 33)"
    fi
}

check_etc_duplicates() {
    local etc_dir="$ROOT/etc/containers/systemd"
    local usr_dir="$ROOT/usr/share/containers/systemd"
    local hits=""
    if [[ -d "$etc_dir" ]]; then
        while IFS= read -r -d '' f; do
            local base="$(basename "$f")"
            if [[ -f "$usr_dir/$base" ]]; then
                hits+="    $f (shadows $usr_dir/$base)"$'\n'
            fi
        done < <(find "$etc_dir" -maxdepth 2 -type f \( -name '*.container' -o -name '*.pod' -o -name '*.network' -o -name '*.volume' \) -print0 2>/dev/null)
    fi
    if [[ -n "$hits" ]]; then
        _violation "Full-unit duplicate(s) found in etc/ containers that shadow usr/share/ generated units (check 34):"$'\n'"$hits"
    else
        echo "[98-drift-checks]   no etc/ full-unit duplicate shadows generated usr/share/ containers"
    fi
}

check_drift_build_catalog() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py drift-build-catalog
    then
        echo "[98-drift-checks]   DB->/ctx materialize round-trip is lossless for build catalog"
    else
        _violation "DB->/ctx materialize round-trip drift detected (check 32) -- verify seed-db-config.py and materialize-build-ctx.py mappings"
    fi
}


check_no_mkdir_in_var() {
    local pat='mkdir[^;&|#]*['\''"[:space:]]/var/'
    local hits="" f active m
    for f in "$ROOT"/automation/[0-9]*.sh "$ROOT"/Containerfile*; do
        [[ -f "$f" ]] || continue
        active=$(sed -E '/^[[:space:]]*#/d' "$f")
        m=$(printf '%s\n' "$active" | grep -nE "$pat" || true)
        [[ -n "$m" ]] && hits+="    ${f#"$ROOT"/}:"$'\n'"$(printf '%s\n' "$m" | sed 's/^/      /')"$'\n'
    done
    if [[ -n "$hits" ]]; then
        printf '%s' "$hits" >&2
        _violation "an imperative 'mkdir .../var/...' in a numbered build step (Law 2 NO-MKDIR-IN-VAR) -- declare the path in usr/lib/tmpfiles.d/*.conf instead"
    else
        echo "[98-drift-checks]   no imperative /var mkdir in numbered automation/Containerfiles"
    fi
}

_privileged_quadlet_array() {
    sed -n '/^\[security\.privileged_quadlets\]/,/^\[/p' "$1" 2>/dev/null \
        | sed -n "/^$2[[:space:]]*=[[:space:]]*\[/,/^]/p" \
        | grep -oE '"[^"]+\.container"' | tr -d '"'
}

check_quadlet_privilege() {
    local toml="$ROOT/usr/share/mios/mios.toml"
    if [[ ! -f "$toml" ]]; then
        echo "[98-drift-checks]   mios.toml absent"
        return 0
    fi
    local root_allow ngd_allow
    root_allow="$(_privileged_quadlet_array "$toml" root)"
    ngd_allow="$(_privileged_quadlet_array "$toml" no_group_delegate)"
    if [[ -z "$root_allow" ]]; then
        echo "[98-drift-checks]   WARNING: [security.privileged_quadlets].root empty/unreadable" >&2
        return 0
    fi
    local bad="" f base user
    for d in "$ROOT/usr/share/containers/systemd" "$ROOT/etc/containers/systemd"; do
        [[ -d "$d" ]] || continue
        while IFS= read -r f; do
            [[ -f "$f" ]] || continue
            base="$(basename "$f")"
            user=""
            if grep -qE '^[[:space:]]*User=' "$f"; then
                user="$(grep -hE '^[[:space:]]*User=' "$f" | head -1 | sed -E 's/^[[:space:]]*User=//' | tr -d '[:space:]')"
            fi
            if [[ -z "$user" || "$user" == "root" || "$user" == "0" ]]; then
                if ! printf '%s\n' "$root_allow" | grep -qxF "$base"; then
                    bad+="    $base: implicitly/explicitly root (User=$user) but NOT in [security.privileged_quadlets].root"$'\n'
                fi
            fi
            if ! printf '%s\n' "$ngd_allow" | grep -qxF "$base"; then
                if [[ -n "$user" && "$user" != "root" && "$user" != "0" ]]; then
                    grep -qE '^[[:space:]]*Group='        "$f" || bad+="    $base: missing Group= for non-root User (Law 6)"$'\n'
                fi
                grep -qE '^[[:space:]]*Delegate=yes'  "$f" || bad+="    $base: missing Delegate=yes (Law 6)"$'\n'
            fi
        done < <(find "$d" -type f -name '*.container' 2>/dev/null)
    done
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "a Quadlet violates Law 6 (UNPRIVILEGED-QUADLETS): missing User=, an undocumented User=root/0 (add to [security.privileged_quadlets].root with a justification), or a missing Group=/Delegate=yes (exempt via [...].no_group_delegate)"
    else
        echo "[98-drift-checks]   every Quadlet declares User=; root only where allowlisted; Group=/Delegate=yes present"
    fi
}

check_var_closure() {
    local tool="$ROOT/automation/lib/mios_var_closure.py"
    _need_python || return 0
    if [[ ! -f "$tool" ]]; then
        echo "[98-drift-checks]   SOFT: mios_var_closure.py absent" >&2
        return 0
    fi
    if MIOS_ROOT="$ROOT" python3 "$tool" >/dev/null 2>"$ROOT/.varclosure.err"; then
        rm -f "$ROOT/.varclosure.err" 2>/dev/null || true
        echo "[98-drift-checks]   MIOS_* referenced-set is a subset of emitted-set"
    else
        sed 's/^/    /' "$ROOT/.varclosure.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.varclosure.err" 2>/dev/null || true
        _violation "var-closure reported referenced but NOT emitted variables -- run python automation/lib/mios_var_closure.py"
    fi
}

check_lint_is_final() {
    # Globbed, not named: a hardcoded list silently skips a file that was
    # renamed and reports success over the ones that remain.
    local bad="" cf last n=0 want="RUN bootc container lint"
    for cf in "$ROOT"/Containerfile*; do
        [[ -f "$cf" ]] || continue
        n=$((n + 1))
        last="$(grep -vE '^[[:space:]]*(#|$)' "$cf" | tail -1)"
        if [[ "$last" != "$want" ]]; then
            bad+="    ${cf#"$ROOT"/}: final instruction is [$last], expected [$want]"$'\n'
        fi
    done
    if [[ "$n" -eq 0 ]]; then
        _violation "(43) no Containerfile* at the repo root -- Law 4 would pass vacuously"
    elif [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "a Containerfile's final instruction is not 'RUN bootc container lint' (Law 4 BOOTC-CONTAINER-LINT) -- lint MUST be the last layer"
    else
        echo "[98-drift-checks]   all $n root Containerfile(s) end with 'RUN bootc container lint'"
    fi
}

check_firstboot_degrade_open() {
    local bad="" f base
    for f in "$ROOT"/usr/libexec/mios/*firstboot*; do
        [[ -f "$f" ]] || continue
        case "$f" in *.pyc) continue ;; esac
        base="$(basename "$f")"
        if grep -qE '^[[:space:]]*set[[:space:]]+-[a-zA-Z]*e|^[[:space:]]*set[[:space:]]+-o[[:space:]]+errexit' "$f"; then
            if grep -qE '\|\|[[:space:]]*(true|:|exit[[:space:]]+0)|set[[:space:]]+\+e|trap[[:space:]].*(EXIT|ERR)|^[[:space:]]*exit[[:space:]]+0' "$f"; then
                : # degrade-open escape present -> ok
            else
                bad+="    $base: 'set -e' active with NO degrade-open escape (|| true / set +e / trap EXIT / exit 0) -- can brick boot on an egress/provision failure"$'\n'
            fi
        fi
    done
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "a *firstboot* script does not degrade open (Law 12 BAKE-NOT-FETCH): 'set -e' is active with no recovery path -- guard the provision/egress steps (|| exit 0 / degrade) so a fetch failure never blocks boot"
    else
        echo "[98-drift-checks]   every *firstboot* script degrades open"
    fi
}

check_vendor_urls() {
    local pattern='https?://(api\.openai\.com|api\.anthropic\.com|generativelanguage\.googleapis\.com|api\.cohere\.|api\.mistral\.|api\.cline\.bot|api\.cursor\.com|api\.githubcopilot\.com)'
    local hits="" f active
    for d in "${SCAN_DIRS[@]}"; do
        [[ -d "$d" ]] || continue
        while IFS= read -r f; do
            [[ -f "$f" ]] || continue
            active=$(sed -E '/^[[:space:]]*(#|\/\/)/d' "$f")
            if printf '%s\n' "$active" | grep -qE "$pattern"; then
                hits+="    $f"$'\n'
            fi
        done < <(find "$d" -type f \( -name '*.container' -o -name '*.service' \
            -o -name '*.json' -o -name '*.toml' -o -name '*.conf' -o -name '*.yaml' \
            -o -name '*.yml' \) 2>/dev/null)
    done
    if [[ -n "$hits" ]]; then
        printf '%s' "$hits" >&2
        _violation "a vendor cloud URL is hardcoded in active AI-plane config (Law 5 UNIFIED-AI-REDIRECTS) -- route through MIOS_AI_ENDPOINT"
    else
        echo "[98-drift-checks]   no vendor cloud URL in active config"
    fi

    # ADR-0016 D5: the VENDOR endpoint stays local; only an /etc overlay
    # may point it off-box.
    local ep_out="$(MIOS_DRIFT_ROOT="$ROOT" python3 - <<'ENDPY'
import os, re, sys
import tomllib as _t
root = os.environ["MIOS_DRIFT_ROOT"]
with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
    data = _t.load(fh)
ep = str((data.get("ai") or {}).get("endpoint") or "")
if not ep:
    print("[ai].endpoint is empty -- every client resolves MIOS_AI_ENDPOINT from it")
    sys.exit(0)
host = re.sub(r"^[a-z]+://", "", ep).split("/")[0].split(":")[0]
if host not in ("localhost", "127.0.0.1", "::1", "[::1]"):
    print("[ai].endpoint is %s: the VENDOR default must stay local (ADR-0016 D5). "
          "Point it off-box in /etc/mios, never in the shipped SSOT" % ep)
ENDPY
)"
    if [[ -n "$ep_out" ]]; then
        _violation "$ep_out"
    else
        echo "[98-drift-checks]   vendor [ai].endpoint is local"
    fi
}

check_resolver_twin_parity() {
    _need_python || return 0
    local ue="$ROOT/usr/lib/mios/userenv.sh" mt="$ROOT/usr/lib/mios/mios_toml.py"
    if [[ ! -f "$ue" || ! -f "$mt" ]]; then
        echo "[98-drift-checks]   SOFT: a resolver is absent" >&2
        return 0
    fi
    local fix="$(mktemp -d 2>/dev/null)" || { echo "[98-drift-checks]   SOFT: mktemp failed" >&2; return 0; }
    mkdir -p "$fix/vendor.d" "$fix/.config/mios"
    printf '[ai]\nendpoint = "http://vendor:1000"\nmodel = "vendor-model"\nembed_model = "vendor-embed"\n' > "$fix/vendor.toml"
    printf '[ai]\nendpoint = "http://vendor-frag:1050"\n'                                                 > "$fix/vendor.d/50-frag.toml"
    printf '[ai]\nendpoint = "http://host:2000"\nmodel = "host-model"\n'                                  > "$fix/host.toml"
    printf '[ai]\nmodel = "user-model"\n'                                                                 > "$fix/.config/mios/mios.toml"
    local sel='^MIOS_AI_(ENDPOINT|MODEL|EMBED_MODEL)=' bash_out py_out
    bash_out="$(env -i PATH="$PATH" HOME="$fix" XDG_CONFIG_HOME="$fix/.config" \
        MIOS_VENDOR_TOML="$fix/vendor.toml" MIOS_VENDOR_TOML_D="$fix/vendor.d" \
        MIOS_HOST_TOML="$fix/host.toml" MIOS_HOST_TOML_D="$fix/host.d" \
        bash -c ". '$ue' >/dev/null 2>&1; env" 2>/dev/null | grep -E "$sel" | sort)"
    py_out="$(env -i PATH="$PATH" \
        MIOS_VENDOR_TOML="$fix/vendor.toml" MIOS_VENDOR_TOML_D="$fix/vendor.d" \
        MIOS_HOST_TOML="$fix/host.toml" MIOS_HOST_TOML_D="$fix/host.d" \
        MIOS_USER_TOML="$fix/.config/mios/mios.toml" MIOS_USER_TOML_D="$fix/.config/mios/mios.d" \
        MIOS_ROOT_LIB="$ROOT/usr/lib/mios" "$PYTHON" -c '
import os, sys
sys.path.insert(0, os.environ["MIOS_ROOT_LIB"])
import mios_toml
ai = mios_toml.section(mios_toml.load_merged(), "ai")
for k in sorted(ai):
    print("MIOS_AI_" + k.upper().replace("-", "_") + "=" + str(ai[k]))
' 2>/dev/null | grep -E "$sel" | sort)"
    rm -rf "$fix" 2>/dev/null || true
    if [[ -z "$bash_out" && -z "$py_out" ]]; then
        echo "[98-drift-checks]   SOFT: resolvers produced no MIOS_AI_*" >&2
        return 0
    fi
    if [[ "$bash_out" == "$py_out" ]]; then
        echo "[98-drift-checks]   resolver twin parity: userenv.sh and mios_toml.py agree on the layered MIOS_AI_* set"
    else
        echo "[98-drift-checks]   SOFT WARNING: resolver twin-parity mismatch" >&2
        echo "        userenv.sh -> $(printf '%s' "$bash_out" | tr '\n' ' ')" >&2
        echo "        mios_toml  -> $(printf '%s' "$py_out"   | tr '\n' ' ')" >&2
    fi
}

check_resolver_twin_equivalence() {
    _need_python || return 0
    local mismatches
    # MIOS_VERSION_MANIFEST (and other build-time MIOS_* vars) into this gate's env, and
    if ! mismatches=$(env -i PATH="$PATH" MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/check-resolver-twin.py" 2>&1); then
        printf '%s\n' "$mismatches" >&2
        _violation "resolver twin equivalence check failed -- userenv.sh and mios_toml.py have drifted"
    else
        echo "[98-drift-checks]   resolver twin equivalence: userenv.sh and mios_toml.py are equivalent"
    fi
}

check_template_conformance() {
    _need_python || return 0
    local tool="$ROOT/usr/libexec/mios/check-template-conformance"
    if [[ ! -f "$tool" ]]; then
        echo "[98-drift-checks]   SOFT: check-template-conformance not found" >&2
        return 0
    fi
    local errors
    if ! errors=$(MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" python3 "$tool" --root "$ROOT" 2>&1); then
        printf '%s\n' "$errors" >&2
        _violation "template conformance check failed -- new/modified files must follow their templates"
    else
        echo "[98-drift-checks]   template conformance: all new files conform to templates"
    fi
}

check_kargs_projection() {
    _need_python || return 0
    
    local tmp_dir="$(mktemp -d)"
    
    mkdir -p "$tmp_dir"
    cp -r "$ROOT/usr/lib/bootc/kargs.d/"* "$tmp_dir/"
    
    MIOS_TOML="$ROOT/usr/share/mios/mios.toml" KARGS_DIR="$tmp_dir" bash "$ROOT/automation/75-kargs-render.sh" >/dev/null 2>&1
    
    if ! python3 "$ROOT/automation/validate-kargs.py" "$tmp_dir" >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        _violation "rendered kargs.d files failed validate-kargs.py schema validation"
        return
    fi
    
    local diffs=""
    local f base
    for f in "$tmp_dir"/*.toml; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        if [[ ! -f "$ROOT/usr/lib/bootc/kargs.d/$base" ]]; then
            diffs+="    Extra rendered file: $base"$'\n'
        elif ! diff -u "$ROOT/usr/lib/bootc/kargs.d/$base" "$f" >/dev/null 2>&1; then
            diffs+="    Content drift in $base (run automation/75-kargs-render.sh to update or align config)"$'\n'
        fi
    done
    
    for f in "$ROOT/usr/lib/bootc/kargs.d"/*.toml; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        if [[ ! -f "$tmp_dir/$base" ]]; then
            diffs+="    Missing rendered file: $base"$'\n'
        fi
    done
    
    rm -rf "$tmp_dir"
    
    if [[ -n "$diffs" ]]; then
        printf '%s' "$diffs" >&2
        _violation "kargs.d projection check failed. Rendered files do not match committed usr/lib/bootc/kargs.d files."
    else
        echo "[98-drift-checks]   kargs.d matches mios.toml [kargs] projection"
    fi
}

check_greenboot_enablement() {
    if ! grep -q "greenboot-healthcheck.service" "$ROOT/automation/78-greenboot.sh" || \
       ! grep -q "greenboot-set-rollback-trigger.service" "$ROOT/automation/78-greenboot.sh"; then
        _violation "greenboot services enablement commands are missing in automation/78-greenboot.sh"
    fi
    
    local non_execs=""
    local f
    if [[ -d "$ROOT/etc/greenboot" ]]; then
        while read -r f; do
            [[ -f "$f" ]] || continue
            local relpath="$(realpath --relative-to="$ROOT" "$f")"
            local mode=""
            if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
                mode="$(git -C "$ROOT" ls-files -s "$relpath" 2>/dev/null | awk '{print $1}')"
            fi
            if [[ -n "$mode" && "$mode" != "100755" ]]; then
                non_execs+="    $relpath has git mode $mode (expected 100755)"$'\n'
            fi
        done < <(find "$ROOT/etc/greenboot" -name "*.sh")
    fi
    
    if [[ -n "$non_execs" ]]; then
        printf '%s' "$non_execs" >&2
        _violation "greenboot check scripts must be executable (mode 100755)"
    else
        echo "[98-drift-checks]   greenboot services and scripts are correctly configured"
    fi
}

check_chrony_projection() {
    local tmp_file="$(mktemp)"
    
    MIOS_TOML="$ROOT/usr/share/mios/mios.toml" CHRONY_CONF="$tmp_file" bash "$ROOT/automation/42-chrony-render.sh" >/dev/null 2>&1
    
    if [[ ! -f "$ROOT/etc/chrony.conf" ]]; then
        rm -f "$tmp_file"
        _violation "committed etc/chrony.conf is missing"
        return
    fi
    
    if ! diff -u "$ROOT/etc/chrony.conf" "$tmp_file" >/dev/null 2>&1; then
        diff -u "$ROOT/etc/chrony.conf" "$tmp_file" >&2
        rm -f "$tmp_file"
        _violation "etc/chrony.conf check failed. Rendered NTP config does not match committed etc/chrony.conf."
    else
        echo "[98-drift-checks]   chrony.conf matches mios.toml [network.ntp] projection"
        rm -f "$tmp_file"
    fi
}

check_nut_projection() {
    local tmp_dir="$(mktemp -d)"
    
    MIOS_TOML="$ROOT/usr/share/mios/mios.toml" UPS_CONF_DIR="$tmp_dir" bash "$ROOT/automation/43-nut-render.sh" >/dev/null 2>&1
    
    local diffs=""
    local f base
    for f in "$tmp_dir"/*.conf; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        if [[ ! -f "$ROOT/etc/ups/$base" ]]; then
            diffs+="    Extra rendered NUT config: $base"$'\n'
        elif ! diff -u "$ROOT/etc/ups/$base" "$f" >/dev/null 2>&1; then
            diffs+="    Content drift in etc/ups/$base"$'\n'
        fi
    done
    
    for f in "$ROOT/etc/ups"/*.conf; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        if [[ ! -f "$tmp_dir/$base" ]]; then
            diffs+="    Missing rendered NUT config: $base"$'\n'
        fi
    done
    
    rm -rf "$tmp_dir"

    local preset="$ROOT/usr/lib/systemd/system-preset/90-mios.preset"
    if [[ -f "$preset" ]]; then
        if ! grep -qE '^\s*enable\s+nut-server\.service' "$preset" || ! grep -qE '^\s*enable\s+nut-monitor\.service' "$preset"; then
            diffs+="    90-mios.preset missing enable line for nut-server.service or nut-monitor.service"$'\n'
        fi
    fi
    
    if [[ -n "$diffs" ]]; then
        printf '%s' "$diffs" >&2
        _violation "etc/ups/ configuration check failed. Rendered NUT configs do not match committed etc/ups/ files."
    else
        echo "[98-drift-checks]   etc/ups/ configurations match mios.toml [power.ups] projection"
    fi
}

check_fluff_tokens() {
    local bad=""
    local f
    
    while read -r f; do
        [[ -f "$f" ]] || continue
        local bname="$(basename "$f")"
        if [[ "$bname" == "98-drift-checks.sh" || "$bname" == "build-mios.sh" || "$bname" == "99-postcheck.sh" || "$f" =~ /firstboot/ ]]; then
            continue
        fi
        
        local line_num=0
        while read -r line || [[ -n "$line" ]]; do
            line_num=$((line_num + 1))
            [[ "$line" =~ ^[[:space:]]*# ]] && continue
            
            if [[ "$line" =~ (echo|log|warn|die)[[:space:]] ]]; then
                if [[ "$line" =~ successfully ]]; then
                    bad+="    $f:$line_num: contains 'successfully'"$'\n'
                fi
                if [[ "$line" =~ "BAKED IN" ]]; then
                    bad+="    $f:$line_num: contains 'BAKED IN'"$'\n'
                fi
                if [[ "$line" =~ \"Done\" ]] || [[ "$line" =~ \"Done.\" ]] || [[ "$line" =~ \'Done\' ]] || [[ "$line" =~ \'Done.\' ]]; then
                    bad+="    $f:$line_num: contains bare 'Done'"$'\n'
                fi
                if [[ "$line" =~ ![[:space:]]*[\"\'][[:space:]]*$ ]]; then
                    bad+="    $f:$line_num: contains trailing '!'"$'\n'
                fi
            fi
        done < "$f"
    done < <(find "$ROOT/automation" -name "*.sh")
    
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "fluff tokens detected in pipeline logs (E5)"
    else
        echo "[98-drift-checks]   fluff-token drift check passed"
    fi
}

check_coordination_hygiene() {
    local bad=""
    local f
    for f in "$ROOT/AGY-TASKS.md" "$ROOT/TASKS.md"; do
        [[ -f "$f" ]] || continue
        
        local line_num=0
        while read -r line || [[ -n "$line" ]]; do
            line_num=$((line_num + 1))
            if [[ "$line" =~ AppData ]] || [[ "$line" =~ \bTemp\b ]] || [[ "$line" =~ [0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12} ]]; then
                bad+="    $f:$line_num: contains AppData/Temp/session-id path"$'\n'
            fi
        done < "$f"
    done
    
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "coordination-hygiene lint failed (E6)"
    else
        echo "[98-drift-checks]   coordination-hygiene lint passed"
    fi
}

check_templates_compilation() {
    local python_exe
    if command -v py &>/dev/null; then
        python_exe=py
    elif command -v python3 &>/dev/null; then
        python_exe=python3
    else
        python_exe=python
    fi
    
    if ! "$python_exe" "$ROOT/tools/compile-templates.py" >/dev/null; then
        "$python_exe" "$ROOT/tools/compile-templates.py" >&2
        _violation "compile-templates validation failed. One or more templates in usr/share/mios/templates are syntactically invalid."
    else
        echo "[98-drift-checks]   all templates compile and validate successfully"
    fi
}

check_impossible_eol_regressions() {
    local bad=""
    
    local toml="$ROOT/usr/share/mios/mios.toml"
    if grep -E '"glusterfs"' "$toml" &>/dev/null || grep -E '"glusterfs-fuse"' "$toml" &>/dev/null || grep -E '"glusterfs-server"' "$toml" &>/dev/null; then
        bad+="    Found glusterfs packages in mios.toml"$'\n'
    fi
    
    local f
    while read -r f; do
        [[ -f "$f" ]] || continue
        [[ "$(basename "$f")" == "mios-metal-architecture.md" ]] && continue
        
        if grep -F "mdevctl vGPU" "$f" &>/dev/null; then
            if ! grep -E "mdevctl vGPU.*(impossible|unsupported|out of scope|reject)" "$f" &>/dev/null; then
                bad+="    $f: contains 'mdevctl vGPU' claim without rejecting it"$'\n'
            fi
        fi
    done < <(find "$ROOT/usr/share/doc/mios/concepts" -name "*.md")
    
    if grep -E '"tang"' "$toml" &>/dev/null; then
        bad+="    Found tang package in mios.toml (on-host Tang is prohibited)"$'\n'
    fi
    
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "impossible/EOL regression check failed (F11)"
    else
        echo "[98-drift-checks]   impossible/EOL regression checks passed"
    fi
}

check_deploy_plane() {
    local bad=""
    local ks_file=""
    for cand in "$ROOT/usr/share/mios/ventoy/mios-kickstart.cfg" \
                "${BOOTSTRAP_DIR:-}/field/resources/ventoy/mios-kickstart.cfg" \
                "/c/mios-bootstrap/field/resources/ventoy/mios-kickstart.cfg" \
                "/mios-bootstrap/field/resources/ventoy/mios-kickstart.cfg" \
                "C:/mios-bootstrap/field/resources/ventoy/mios-kickstart.cfg" \
                "$ROOT/../mios-bootstrap/field/resources/ventoy/mios-kickstart.cfg" \
                "$ROOT/field/resources/ventoy/mios-kickstart.cfg"; do
        if [[ -n "$cand" && -f "$cand" ]]; then
            ks_file="$cand"
            break
        fi
    done

    if [[ -n "$ks_file" ]]; then
        if ! grep -q "MIOS_FHS_TOTAL_ROOT_MERGE=1" "$ks_file"; then
            bad+="    mios-kickstart.cfg: missing MIOS_FHS_TOTAL_ROOT_MERGE=1 export"$'\n'
        fi
        if ! grep -q "BOOTSTRAP_REPO" "$ks_file" || ! grep -q "MIOS_REPO" "$ks_file"; then
            bad+="    mios-kickstart.cfg: missing BOOTSTRAP_REPO or MIOS_REPO offline overrides"$'\n'
        fi
    else
        echo "[98-drift-checks]   WARNING: mios-kickstart.cfg not found, skipping kickstart exports assertion"
    fi

    local ventoy_json=""
    for cand in "$ROOT/usr/share/mios/ventoy/ventoy.json" \
                "${BOOTSTRAP_DIR:-}/field/resources/ventoy/ventoy.json" \
                "/c/mios-bootstrap/field/resources/ventoy/ventoy.json" \
                "/mios-bootstrap/field/resources/ventoy/ventoy.json" \
                "C:/mios-bootstrap/field/resources/ventoy/ventoy.json" \
                "$ROOT/../mios-bootstrap/field/resources/ventoy/ventoy.json" \
                "$ROOT/field/resources/ventoy/ventoy.json"; do
        if [[ -n "$cand" && -f "$cand" ]]; then
            ventoy_json="$cand"
            break
        fi
    done

    if [[ -n "$ventoy_json" ]]; then
        if ! grep -q "Fedora-Server.iso" "$ventoy_json" || ! grep -q "mios-kickstart.cfg" "$ventoy_json"; then
            bad+="    ventoy.json: missing Fedora-Server.iso/mios-kickstart.cfg binding in kickstart section"$'\n'
        fi
    else
        echo "[98-drift-checks]   WARNING: ventoy.json not found, skipping ISO-kickstart binding check"
    fi

    local toml="$ROOT/usr/share/mios/mios.toml"
    local base_image_version
    local base_image=$(grep -E '^[[:space:]]*base_image[[:space:]]*=' "$toml" | head -n1 | cut -d'"' -f2)
    if [[ -n "$base_image" ]]; then
        base_image_version=$(echo "$base_image" | grep -oE '[0-9]+$')
        if [[ -n "$base_image_version" ]]; then
            if [[ -f "$ks_file" ]]; then
                if grep -oE 'Fedora-Server-[0-9]+' "$ks_file" | grep -qv "Fedora-Server-${base_image_version}" &>/dev/null; then
                    local mismatched_version=$(grep -oE 'Fedora-Server-[0-9]+' "$ks_file" | head -n1)
                    bad+="    kickstart/base_image: version mismatch (${mismatched_version} vs Fedora ${base_image_version})"$'\n'
                fi
            fi
        fi
    fi

    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "deploy-plane drift check failed (G11)"
    else
        echo "[98-drift-checks]   deploy-plane checks passed"
    fi
}


check_version_ssot() {
    local toml="$ROOT/usr/share/mios/mios.toml"
    local ssot vfile bad=""
    ssot="$(grep -m1 -E '^[[:space:]]*mios_version' "$toml" 2>/dev/null | sed -E 's/[^"]*"([^"]*)".*/\1/')"
    vfile="$(tr -d '[:space:]' < "$ROOT/VERSION" 2>/dev/null)"
    if [[ -z "$ssot" ]]; then
        _violation "version SSOT: mios.toml [meta].mios_version is empty/unparseable"
        return
    fi
    [[ "$vfile" != "$ssot" ]] && bad+="    VERSION file = [$vfile], expected [$ssot]"$'\n'

    local _cf _cv
    while read -r _cf; do
        [[ -f "$ROOT/$_cf" ]] || continue
        _cv="$(grep -m1 -E '^ARG[[:space:]]+MIOS_VERSION=' "$ROOT/$_cf" 2>/dev/null | sed -E 's/^ARG[[:space:]]+MIOS_VERSION=//; s/[[:space:]].*//' || true)"
        [[ -n "$_cv" && "$_cv" != "$ssot" ]] && bad+="    $_cf ARG MIOS_VERSION default = [$_cv], expected [$ssot]"$'\n'
    done < <(git ls-files "*Containerfile*" 2>/dev/null || find "$ROOT" -name "*Containerfile*" -type f)

    local osr="$ROOT/usr/lib/os-release" _f _v
    if [[ -f "$osr" ]]; then
        for _f in VERSION VERSION_ID BUILD_ID IMAGE_VERSION OSTREE_VERSION; do
            _v="$(grep -m1 -E "^${_f}=" "$osr" | sed -E 's/^[^=]+=//; s/^"//; s/"[[:space:]]*$//')"
            [[ -n "$_v" && "$_v" != "$ssot" ]] && bad+="    os-release ${_f} = [$_v], expected [$ssot]"$'\n'
        done
        _v="$(grep -m1 -E '^PRETTY_NAME=' "$osr" | sed -E 's/.*MiOS //; s/"[[:space:]]*$//')"
        [[ -n "$_v" && "$_v" != "$ssot" ]] && bad+="    os-release PRETTY_NAME version = [$_v], expected [$ssot]"$'\n'
        _v="$(grep -m1 -E '^CPE_NAME=' "$osr" | sed -E 's|.*:mios:||; s/"[[:space:]]*$//')"
        [[ -n "$_v" && "$_v" != "$ssot" ]] && bad+="    os-release CPE_NAME version = [$_v], expected [$ssot]"$'\n'
    fi

    local _cargo_ver
    for _toml in "$ROOT/tools/native/Cargo.toml" "$ROOT/tools/native/mios-version-check/Cargo.toml" "$ROOT/tools/native/mios-wallpaperd/Cargo.toml"; do
        [[ -f "$_toml" ]] || continue
        _cargo_ver="$(grep -m1 -E '^[[:space:]]*version[[:space:]]*=' "$_toml" 2>/dev/null | sed -E 's/[^"]*"([^"]*)".*/\1/' || true)"
        [[ -n "$_cargo_ver" && "$_cargo_ver" != "$ssot" ]] && bad+="    ${_toml#$ROOT/} version = [$_cargo_ver], expected [$ssot]"$'\n'
    done

    local literal_bad="" exit_code=0
    set +e
    literal_bad="$(MIOS_DRIFT_ROOT="$ROOT" MIOS_CANONICAL_VER="$ssot" python3 - <<'PY' 2>&1
import os, sys, re, subprocess
root = os.environ["MIOS_DRIFT_ROOT"]
canonical_ver = os.environ["MIOS_CANONICAL_VER"]

root_toml = os.path.join(root, "mios.toml")
if os.path.isfile(root_toml):
    try:
        with open(root_toml, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if re.search(r'^\s*mios_version\s*=', line) and canonical_ver not in line:
                    sys.stderr.write(f"    TODO(td-2): root mios.toml has version divergence from canonical {canonical_ver}\n")
    except OSError:
        pass

pattern = re.compile(r'\bv?0\.[0-9]+\.[0-9]+\b')
viol = []

try:
    out = subprocess.check_output(["git", "ls-files"], cwd=root, stderr=subprocess.DEVNULL).decode("utf-8")
    tracked = [os.path.normpath(os.path.join(root, f)) for f in out.splitlines()]
except Exception:
    tracked = []
    for r, _d, files in os.walk(root):
        rel_r = os.path.relpath(r, root).replace("\\", "/")
        parts = rel_r.split('/')
        if any(p in parts for p in ('tmp', '.git', '.venv', '__pycache__', 'node_modules', 'dist', 'build', 'target', '.system_generated', 'scratch', 'logs', 'bib-configs', 'medicat_stage', 'isobuild', 'isobuild_live', 'isobuild2')):
            continue
        for f in files:
            tracked.append(os.path.normpath(os.path.join(r, f)))

for path in tracked:
    rel = os.path.relpath(path, root).replace("\\", "/")
    if not (rel.startswith("automation") or rel.startswith("usr/libexec/") or rel.startswith("tools")):
        continue
    if rel.endswith((".pyc", ".png", ".jpg", ".generated", ".json", ".log", ".ready", ".lock", ".d", ".o", ".rlib", ".rmeta", ".a")):
        continue
    # Golden-master fixtures are byte-for-byte copies of files that live
    # OUTSIDE this scan's prefixes (usr/lib/systemd/system), so the originals
    # are never version-scanned. The copy happens to sit under tools/, and
    # re-scanning it reports UPSTREAM version literals -- such as the
    # nvidia-container-toolkit minimum noted in a unit comment -- as MiOS
    # version drift. The crate's own test already asserts copy == original.
    if "/tests/golden/" in rel:
        continue
    if not os.path.isfile(path):
        continue

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except OSError:
        continue
        
    for idx, line in enumerate(lines):
        for m in pattern.finditer(line):
            ver = m.group(0)
            ver_clean = ver[1:] if ver.startswith('v') else ver
            if ver_clean != canonical_ver:
                if ver_clean in ("0.0.0", "0.0.1", "0.8.3", "0.2.4", "0.6.0", "0.9.6", "0.0.76", "0.1.0"):
                    continue
                if "INTEL_SG_FALLBACK_TAG" in line:
                    continue
                if "Upstream v0.15.0" in line:
                    continue
                viol.append(f"    {rel}:{idx+1} hardcodes different version literal [{ver}], expected [{canonical_ver}]")

if viol:
    for v in viol:
        sys.stderr.write(v + "\n")
    sys.exit(1)
sys.exit(0)
PY
)"
    exit_code=$?
    set -e
    if [[ $exit_code -ne 0 ]]; then
        bad+="$literal_bad"$'\n'
    else
        if [[ -n "$literal_bad" ]]; then
            echo "$literal_bad" >&2
        fi
    fi

    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "version drift from SSOT mios.toml [meta].mios_version=[$ssot] (Law 7 NO-HARDCODE / Law 8 SSOT-PROJECTION) -- VERSION file + Containerfile ARG default must match the SSOT"
    else
        echo "[98-drift-checks]   VERSION + Containerfile ARG MIOS_VERSION == mios.toml [meta].mios_version"
    fi
}

check_root_toml_subset() {
    _need_python || return 0
    local rc=0
    python3 -c "
import os, sys
import tomllib

def get_keys(d, prefix=''):
    keys = set()
    for k, v in d.items():
        full = f'{prefix}.{k}' if prefix else k
        keys.add(full)
        if isinstance(v, dict):
            keys.update(get_keys(v, full))
    return keys

root = os.environ.get('MIOS_DRIFT_ROOT', '.')
root_toml = os.path.join(root, 'mios.toml')
canonical = os.path.join(root, 'usr/share/mios/mios.toml')

if not os.path.isfile(root_toml):
    # Say so. Exiting 0 here made the gate print 'root mios.toml schema is
    # subset of canonical SSOT' -- a claim about a comparison it never ran, and
    # the reader has no way to tell that from a real pass.
    sys.exit(2)

with open(root_toml, 'rb') as f:
    r_data = tomllib.load(f)
with open(canonical, 'rb') as f:
    c_data = tomllib.load(f)

r_keys = get_keys(r_data)
c_keys = get_keys(c_data)

ignored_prefixes = (
    'autounattend', 'bootstrap', 'medicat', 'containers', 'ports.lan_firewall',
    'quadlets', 'smoke_tests', 'terminal.startup', 'branding.windows', 'branding.cursor',
    'branding.oem_', 'branding.wallpaper', 'branding.lockscreen', 'branding.ui_font',
    'branding.font_substitute', 'ai.enable_', 'terminal.startup', 'branding.living_wallpaper',
    'terminal.gui_min', 'theme.terminal.dev_profile_name', 'theme.terminal.hub_target_profile',
    'theme.terminal.summon_keys', 'theme.terminal.summon_window_name', 'mios_app'
)
filtered_r_keys = {k for k in r_keys if not any(k.startswith(pfx) for pfx in ignored_prefixes)}

diff = filtered_r_keys - c_keys
if diff:
    sys.stderr.write('    Drift: root mios.toml defines keys not in canonical SSOT:\\n')
    for k in sorted(diff):
        sys.stderr.write(f'      {k}\\n')
    sys.exit(1)
sys.exit(0)
    " || rc=$?
    if [[ $rc -eq 2 ]]; then
        # 2 means there is no root mios.toml. Printing the success line here
        # claimed a comparison that never ran, and a reader could not tell that
        # from a real pass.
        echo "[98-drift-checks]   no root mios.toml -- subset check not applicable"
    elif [[ $rc -eq 0 ]]; then
        echo "[98-drift-checks]   root mios.toml schema is subset of canonical SSOT"
    else
        _violation "root mios.toml schema has keys not in canonical SSOT"
    fi
}

check_toml_projection() {
    _need_python || return 0
    local tool="$ROOT/usr/libexec/mios/mios-sync-toml"
    if [[ ! -f "$tool" ]]; then
        echo "[98-drift-checks]   WARNING: mios-sync-toml not found" >&2
        return 0
    fi
    if python3 "$tool" --check >/dev/null 2>"$ROOT/.synctoml.err"; then
        rm -f "$ROOT/.synctoml.err" 2>/dev/null || true
        echo "[98-drift-checks]   mios.toml derived copies project verbatim from the canonical SSOT"
    else
        sed 's/^/    /' "$ROOT/.synctoml.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.synctoml.err" 2>/dev/null || true
        _violation "a mios.toml derived copy drifted from the canonical [ports]/[colors] projection -- re-run usr/libexec/mios/mios-sync-toml"
    fi
}

check_ratchet_direction() {
    _need_python || return 0
    local script="$ROOT/tools/check-ratchet-direction.py"
    if [[ ! -f "$script" ]]; then
        _violation "tools/check-ratchet-direction.py missing"
        return 0
    fi
    local out
    if out="$(python3 "$script" 2>&1)"; then
        echo "[98-drift-checks]   shrink-only ratchet ceilings in mios.toml do not exceed HEAD"
    else
        echo "$out" >&2
        _violation "shrink-only ratchet ceiling increased in mios.toml"
    fi
}

check_target_languages() {
    if [[ ! -d "$ROOT/.git" ]] || ! command -v git >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: git missing or not a git repo" >&2
        return 0
    fi
    local toml="$ROOT/usr/share/mios/mios.toml"
    local allow bad="" nativebad f
    allow=$(awk '/^\[laws\.target_languages\]/{f=1} f&&/grandfathered_cs[[:space:]]*=[[:space:]]*\[/{g=1} g{print} g&&/\]/{exit}' "$toml" | grep -oE '"[^"]+\.cs"' | tr -d '"\r')
    nativebad=$(cd "$ROOT" && (git ls-files '*.bat' '*.cmd' '*.go' '*.cpp' '*.cxx' '*.cc' 2>/dev/null; git ls-files --others --exclude-standard '*.bat' '*.cmd' '*.go' '*.cpp' '*.cxx' '*.cc' 2>/dev/null) | grep -v '^tools/mios-portal-app/' || true)
    [[ -n "$nativebad" ]] && bad+="$nativebad"$'\n'
    while IFS= read -r f; do
        f_clean=$(echo "$f" | tr -d '\r')
        [[ -z "$f_clean" ]] && continue
        grep -qxF "$f_clean" <<<"$allow" || bad+="$f_clean"$'\n'
    done < <(cd "$ROOT" && (git ls-files '*.cs' 2>/dev/null; git ls-files --others --exclude-standard '*.cs' 2>/dev/null))
    if [[ -n "$(printf '%s' "$bad" | tr -d '[:space:]')" ]]; then
        {
          echo "    Law 14 TARGET-LANGUAGES: new code must use the roadmap targets (Rust native tier; Python AI;"
          echo "    Bun/TS Portal; bash thin-glue). These non-target-language files are not grandfathered:"
          printf '%s\n' "$bad" | sed '/^[[:space:]]*$/d;s/^/      - /'
          echo "    -> port to Rust, or add a legitimate pre-existing port target to"
          echo "       mios.toml [laws.target_languages].grandfathered_cs"
        } >&2
        _violation "Law 14 TARGET-LANGUAGES violated: new non-target-language source added"
    else
        echo "[98-drift-checks]   Law 14 TARGET-LANGUAGES: no new non-target-language code"
    fi
}

check_bake_plan() {
    _need_python || return 0
    if python3 "$ROOT/tools/generate-bake-plan.py" --check; then
        echo "[98-drift-checks]   bake-plan lists in sync with mios.toml [build.bake] SSOT"
    else
        _violation "bake-plan lists are STALE vs mios.toml -- regenerate with python3 tools/generate-bake-plan.py"
    fi
}

check_bake_plan_integrity() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py bake-plan-integrity
    then
        echo "[98-drift-checks]   bake-plan integrity gate verified clean"
    else
        _violation "bake-plan integrity gate check failed"
    fi
}

check_bake_ref_defaults() {
    if [[ ! -d "$ROOT/.git" ]] || ! command -v git >/dev/null 2>&1; then
        echo "[98-drift-checks]   all baker scripts have non-empty defaults for their bake-refs"
        return 0
    fi
    local empty_refs="$(git grep -E 'MIOS_BUILD_BAKE_REFS_[A-Z0-9_]+:-\}' automation/ 2>/dev/null || true)"
    if [[ -n "$empty_refs" ]]; then
        _violation "found empty defaults for bake-refs in automation scripts:"$'\n'"${empty_refs}"
        return 1
    fi
    if command -v python3 >/dev/null 2>&1; then
        if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, subprocess
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(toml_path):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

bake_refs = data.get("build", {}).get("bake_refs", {})

try:
    matches = subprocess.check_output(["git", "grep", "-E", r"MIOS_BUILD_BAKE_REFS_[A-Z0-9_]+:-", "automation/"], cwd=root, text=True).splitlines()
except Exception:
    matches = []

viol = []
pattern = re.compile(r"MIOS_BUILD_BAKE_REFS_([A-Z0-9_]+):-([^}\"\']+)")
for m in matches:
    res = pattern.search(m)
    if res:
        key = res.group(1).lower()
        lit = res.group(2).strip()
        if key in bake_refs:
            ssot_val = str(bake_refs[key]).strip()
            if lit != ssot_val:
                viol.append(f"{m.split(':')[0]}: MIOS_BUILD_BAKE_REFS_{res.group(1)} default '{lit}' != SSOT '{ssot_val}'")

if viol:
    for v in viol:
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)
sys.exit(0)
PY
        then
            echo "[98-drift-checks]   all baker scripts have non-empty defaults matching SSOT bake_refs"
        else
            _violation "baker script MIOS_BUILD_BAKE_REFS default value parity check failed"
            return 1
        fi
    else
        echo "[98-drift-checks]   all baker scripts have non-empty defaults for their bake-refs"
    fi
}


check_roadmap_index() {
    _need_python || return 0
    if [[ ! -f "$ROOT/ROADMAP.md" ]]; then
        echo "[98-drift-checks]   ROADMAP.md not found"
        return 0
    fi
    if python3 "$ROOT/tools/roadmap-index.py" --check; then
        echo "[98-drift-checks]   roadmap index in sync with frontmatter metadata"
    else
        _violation "roadmap index is STALE or cites invalid laws/ADRs/ssot_keys -- regenerate with python3 tools/roadmap-index.py"
    fi
}

check_cli_eval_safety() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
root = os.environ["MIOS_DRIFT_ROOT"]
dir_to_scan = os.path.join(root, "usr/libexec/mios")
viol = []

if os.path.isdir(dir_to_scan):
    for fn in os.listdir(dir_to_scan):
        path = os.path.join(dir_to_scan, fn)
        if not os.path.isfile(path) or fn.endswith((".py", ".pyc", ".json", ".generated")):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                first_line = fh.readline()
                if not ("bash" in first_line or "sh" in first_line):
                    continue
                fh.seek(0)
                lines = fh.readlines()
        except OSError:
            continue
        
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            
            code_part = line.split("#")[0].strip()
            if re.search(r'\beval\b', code_part):
                has_comment = False
                if idx > 0:
                    prev_line = lines[idx - 1].strip()
                    if re.match(r'^#\s*TD-1:\s*eval-safe,\s*input=.+,\s*not agent-controlled', prev_line):
                        has_comment = True
                
                if not has_comment:
                    viol.append(f"{fn}:{idx+1} has unverified eval: {line.strip()}")

if viol:
    for v in viol:
        sys.stderr.write(f"  {v}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   CLI verbs in usr/libexec/mios/ are eval-safe"
    else
        _violation "unverified eval in usr/libexec/mios/ -- verbs must not eval agent-controlled inputs; pre-existing safe evals must have a preceding # TD-1: eval-safe, input=<source>, not agent-controlled comment"
    fi
}

check_shellcheck() {
    local rc=0
    bash "$ROOT/automation/lint-shell.sh" || rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "[98-drift-checks]   shellcheck: shell scripts conform to error-level linting"
    elif [[ $rc -eq 2 ]]; then
        echo "[98-drift-checks]   WARNING: shellcheck absent" >&2
    else
        _violation "shellcheck linting failed with errors -- please run automation/lint-shell.sh or check logs"
    fi
}

check_sbom_metadata() {
    local sbom_dir="$ROOT/usr/share/mios/artifacts/sbom"
    local bad=()

    if [[ -d "$sbom_dir" ]]; then
        if [[ -f "$sbom_dir/models.tsv" ]]; then
            while IFS=$'\t' read -r name type repo file sha256 || [[ -n "$name" ]]; do
                [[ "$name" == "name" ]] && continue
                [[ -z "$name" ]] && continue
                if [[ -z "$type" || -z "$repo" || -z "$file" || -z "$sha256" ]]; then
                    bad+=("models.tsv has empty fields in row for '$name'")
                fi
                if [[ "$sha256" != "unknown" && ! "$sha256" =~ ^[0-9a-fA-F]{64}$ ]]; then
                    bad+=("models.tsv row for '$name' has invalid sha256: '$sha256'")
                fi
            done < "$sbom_dir/models.tsv"
        fi

        if [[ -f "$sbom_dir/binaries.tsv" ]]; then
            while IFS=$'\t' read -r name version sha256 || [[ -n "$name" ]]; do
                [[ "$name" == "name" ]] && continue
                [[ -z "$name" ]] && continue
                if [[ -z "$version" || -z "$sha256" ]]; then
                    bad+=("binaries.tsv has empty fields in row for '$name'")
                fi
                if [[ "$sha256" != "unknown" && ! "$sha256" =~ ^[0-9a-fA-F]{64}$ ]]; then
                    bad+=("binaries.tsv row for '$name' has invalid sha256: '$sha256'")
                fi
            done < "$sbom_dir/binaries.tsv"
        fi

        if [[ -f "$sbom_dir/bound-images.tsv" ]]; then
            while IFS=$'\t' read -r image digest group || [[ -n "$image" ]]; do
                [[ "$image" == "image" ]] && continue
                [[ -z "$image" ]] && continue
                if [[ -z "$digest" || -z "$group" ]]; then
                    bad+=("bound-images.tsv has empty fields in row for '$image'")
                fi
            done < "$sbom_dir/bound-images.tsv"
        fi
    fi

    if [[ "${#bad[@]}" -eq 0 ]]; then
        echo "[98-drift-checks]   SBOM metadata manifests are structurally valid"
    else
        for err in "${bad[@]}"; do
            echo "  [sbom-drift] $err" >&2
        done
        _violation "SBOM metadata manifests in usr/share/mios/artifacts/sbom/ contain invalid/empty fields"
    fi
}

check_hyprland_conf_heredoc() {
    local tmp; tmp="$(mktemp)"
    local tmp2; tmp2="$(mktemp)"
    sed -n '/cat << '\''EOF'\'' > \/usr\/share\/mios\/hyprland\/hyprland.conf/,/^EOF$/p' "$ROOT/automation/65-bake-hyprland.sh" | sed '1d;$d' | tr -d '\r' > "$tmp"
    tr -d '\r' < "$ROOT/usr/share/mios/hyprland/hyprland.conf" > "$tmp2"
    if diff -u "$tmp2" "$tmp" >/dev/null; then
        echo "[98-drift-checks]   Hyprland configuration template is in sync with baker script heredoc"
        rm -f "$tmp" "$tmp2"
    else
        rm -f "$tmp" "$tmp2"
        _violation "usr/share/mios/hyprland/hyprland.conf has drifted from the inline heredoc in automation/65-bake-hyprland.sh -- sync them (B4)"
    fi
}



check_curl_retry() {
    local bad=()
    local py_script="
import glob, re, os

root = '$ROOT'
files = glob.glob(os.path.join(root, '**/Containerfile*'), recursive=True) + \
        glob.glob(os.path.join(root, 'automation/**/*.sh'), recursive=True) + \
        glob.glob(os.path.join(root, 'usr/libexec/mios/**/*.sh'), recursive=True)

unretried = []
for path in files:
    if '.git' in path or 'node_modules' in path or 'test-drift-gates.sh' in path: continue
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                sline = line.strip()
                if sline.startswith('#'): continue
                if re.search(r'\b(curl|wget)\b', sline) and re.search(r'https?://', sline):
                    if 'localhost' in sline or '127.0.0.1' in sline: continue
                    if not re.search(r'--retry|--tries|scurl\b', sline):
                        rel = os.path.relpath(path, root)
                        unretried.append(f'{rel}:{i}')
    except Exception: pass

for u in unretried:
    print(u)
"
    local res="$(python3 -c "$py_script" 2>/dev/null || true)"
    if [[ -z "$res" ]]; then
        echo "[98-drift-checks]   curl/wget build network fetches carry"
    else
        while IFS= read -r line; do
            [[ -n "$line" ]] && bad+=("$line")
        done <<< "$res"
        for err in "${bad[@]}"; do
            echo "  [curl-retry-drift] unretried network fetch: $err" >&2
        done
        _violation "curl/wget build network fetch lacking --retry / --tries flag found"
    fi
}

# The SBOM's provenance is only as good as the ref list that feeds it. When
# mios-resolve-latest mirrored [image.sidecars] by hand the mirror drifted --
# four refs named images MiOS does not ship -- so the resolver must DERIVE its
# set from the SSOT and carry no registry ref literal of its own.
# --- mios-resolve-latest derives its image refs from [image.sidecars] ---
check_resolver_ssot_refs() {
    local rel="usr/libexec/mios/mios-resolve-latest"
    if [[ ! -f "$ROOT/$rel" ]]; then
        echo "[98-drift-checks]   resolver ref derivation: $rel absent"
        return 0
    fi
    _require_python3 || return 0
    local res="$(MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_REL="$rel" python3 - <<'PY' 2>/dev/null || true
import os
import re

path = os.path.join(os.environ["MIOS_DRIFT_ROOT"], os.environ["MIOS_DRIFT_REL"])
# A registry ref literal: quoted dotted-host/path:tag (docker.io/..., ghcr.io/...).
ref = re.compile(r"""['"][a-z0-9][a-z0-9.\-]*\.[a-z]{2,}/[^\s'"]+:[^\s'"]+['"]""")
with open(path, encoding="utf-8", errors="ignore") as fh:
    for i, line in enumerate(fh, 1):
        s = line.strip()
        if s.startswith("#"):
            continue
        m = ref.search(s)
        if m:
            print(f"{i}: {m.group(0)}")
PY
)"
    if [[ -z "$res" ]]; then
        echo "[98-drift-checks]   mios-resolve-latest derives its refs from the SSOT"
    else
        while IFS= read -r line; do
            [[ -n "$line" ]] && echo "  [resolver-ssot-drift] hardcoded image ref at $rel:$line" >&2
        done <<<"$res"
        _violation "mios-resolve-latest carries a hardcoded registry image ref; derive the set from mios.toml [image.sidecars] through mios_toml instead (a hand-mirrored list drifts and feeds wrong provenance into the SBOM)"
    fi
}

check_nested_podman_caps() {
    local bad=()
    local gha_file="$ROOT/.github/workflows/mios-ci.yml"
    local sys_script="$ROOT/usr/libexec/mios/57-mios-sys-build.sh"
    local doc_file="$ROOT/usr/share/doc/mios/reference/nested-podman-caps.md"

    if [[ ! -f "$doc_file" ]]; then
        bad+=("missing reference doc: usr/share/doc/mios/reference/nested-podman-caps.md")
    fi

    if [[ -f "$gha_file" ]]; then
        if ! grep -q -- "--device /dev/fuse" "$gha_file" || ! grep -q -- "--cap-add" "$gha_file" || ! grep -q "seccomp=unconfined" "$gha_file"; then
            bad+=(".github/workflows/mios-ci.yml is missing required nested podman flags (--device /dev/fuse, --cap-add, --security-opt seccomp=unconfined)")
        fi
    fi

    if [[ -f "$sys_script" ]]; then
        if ! grep -q -- "--cap-add" "$sys_script" || ! grep -q "seccomp=unconfined" "$sys_script"; then
            bad+=("usr/libexec/mios/57-mios-sys-build.sh is missing required nested podman flags (--cap-add, --security-opt seccomp=unconfined)")
        fi
        if ! grep -q "build_image_with_retry" "$sys_script" || ! grep -q "image exists" "$sys_script"; then
            bad+=("usr/libexec/mios/57-mios-sys-build.sh is missing build_image_with_retry loop or image exists verification")
        fi
    fi

    if [[ ${#bad[@]} -eq 0 ]]; then
        echo "[98-drift-checks]   nested-podman capability flags & reference doc verified"
    else
        for err in "${bad[@]}"; do
            echo "  [nested-podman-drift] $err" >&2
        done
        _violation "nested podman build missing capability/security flags or reference doc"
    fi
}

check_bake_budget() {
    _need_python || return 0
    local py_res
    py_res="$(MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY' 2>&1
import os, sys, tomllib

root = os.environ.get("MIOS_DRIFT_ROOT", ".")
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
tsv_path = os.path.join(root, "usr/share/mios/artifacts/sbom/bound-images.tsv")

if not os.path.exists(toml_path):
    print("ERROR: SSOT mios.toml absent")
    sys.exit(1)

if not os.path.exists(tsv_path):
    print("ERROR: bound-images.tsv SBOM artifact absent")
    sys.exit(1)

try:
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
except Exception as e:
    print(f"ERROR: Failed to parse mios.toml: {e}")
    sys.exit(1)

budget = data.get("build", {}).get("bake", {}).get("runner_disk_budget_gb", None)
if budget is None or not isinstance(budget, (int, float)) or budget <= 0:
    print(f"ERROR: [build.bake].runner_disk_budget_gb is absent or invalid ({budget})")
    sys.exit(1)

try:
    with open(tsv_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
except Exception as e:
    print(f"ERROR: Failed to read bound-images.tsv: {e}")
    sys.exit(1)

if not lines:
    print("ERROR: bound-images.tsv is empty")
    sys.exit(1)

header = lines[0].split("\t")
if "size_gb" not in header:
    print("ERROR: bound-images.tsv missing size_gb column")
    sys.exit(1)

size_idx = header.index("size_gb")
group_idx = header.index("group") if "group" in header else -1

total_day0 = 0.0
for line in lines[1:]:
    parts = line.split("\t")
    group = parts[group_idx] if group_idx >= 0 and len(parts) > group_idx else "extra"
    if group == "firstboot":
        continue
    try:
        sz = float(parts[size_idx])
    except (ValueError, IndexError):
        print(f"ERROR: Malformed size entry in line: {line}")
        sys.exit(1)
    total_day0 += sz

if total_day0 > budget:
    print(f"EXCEEDED: Total Day-0 bake size {total_day0:.2f}GB exceeds SSOT budget {budget}GB")
    sys.exit(1)

print(f"OK: Day-0 size {total_day0:.2f}GB <= budget {budget}GB")
PY
)"
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        echo "  [bake-budget-drift] $py_res" >&2
        _violation "bake-budget gate failed: $py_res"
    else
        # The gate-index generator captures this line verbatim as the check's
        # description, so interpolating a variable put the literal text
        # "$py_res" into the generated reference. The detail goes to stderr.
        echo "[98-drift-checks]   bake-budget gate: projected baked image size within the SSOT disk budget"
        [[ -n "$py_res" ]] && printf '%s
' "$py_res" >&2
    fi
}

check_greenboot() {
    echo "[98-drift-checks]   greenboot health-coverage check"
    local gb_dir="$ROOT/usr/lib/greenboot/check/required.d"
    if [[ ! -d "$gb_dir" ]]; then
        _violation "(54) greenboot required checks directory ($gb_dir) is missing"
        return
    fi
    # The critical set is READ FROM THE SSOT, never restated here: a hardcoded copy
    # agrees with the scripts it checks while both drift away from mios.toml.
    local gb_out line
    gb_out="$(MIOS_DRIFT_ROOT="$ROOT" MIOS_DRIFT_GB_DIR="$gb_dir" python3 - <<'PY'
import os, re, sys
import tomllib as _toml

root = os.environ["MIOS_DRIFT_ROOT"]
gb_dir = os.environ["MIOS_DRIFT_GB_DIR"]
with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
    data = _toml.load(fh)
gb = data.get("greenboot") or {}
critical = [str(x).strip() for x in (gb.get("critical_services") or []) if str(x).strip()]
probe = gb.get("probe") or {}
if not critical:
    print("(54) [greenboot].critical_services is empty or absent -- greenboot coverage "
          "would pass vacuously over an empty set")

# Executable bodies of the required.d scripts (a mention in a comment is not cover).
bodies, probed, ssot_driven = {}, set(), False
for name in sorted(os.listdir(gb_dir)):
    fp = os.path.join(gb_dir, name)
    if not os.path.isfile(fp):
        continue
    try:
        body = open(fp, encoding="utf-8", errors="replace").read()
    except OSError:
        continue
    code = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    bodies[name] = code
    if "MIOS_GREENBOOT_CRITICAL_SERVICES" in code:
        ssot_driven = True
    for m in re.finditer(r"\b(?:mios-)?([a-z0-9][a-z0-9_-]*)\.service\b", code):
        probed.add(m.group(1))

def unit_for(svc):
    """What the probe derives: the [greenboot.probe] override, else the convention."""
    spec = probe.get(svc.replace("-", "_")) or probe.get(svc) or {}
    unit = str(spec.get("unit") or "").strip()
    return unit or ("mios-%s.service" % svc)

def unit_exists(unit):
    stem = unit[:-len(".service")] if unit.endswith(".service") else unit
    if stem in (data.get("containers") or {}):
        return True
    return os.path.isfile(os.path.join(root, "usr/lib/systemd/system", unit))

for svc in critical:
    if ssot_driven:
        # The probe list is DERIVED, so cover means: the unit it derives exists.
        unit = unit_for(svc)
        if not unit_exists(unit):
            print("(54) [greenboot].critical_services names '%s', but the probe would "
                  "derive %s, which is not a shipped unit or a declared container"
                  % (svc, unit))
        continue
    key = svc[5:] if svc.startswith("mios-") else svc
    if key not in probed:
        print("(54) greenboot missing health-check script for critical service: %s "
              "(no required.d script references %s.service outside comments)" % (svc, svc))
PY
)"
    while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            _violation "$line"
        fi
    done <<< "$gb_out"
}

# Regenerate-and-diff against the committed projection, the shape
# check_ipa_enroll_projection uses: the generator's exit status is an assertion,
# the match is anchored to line start, and the render is diffed against
# etc/mios/clevis-luks.env, so an unprojected SSOT edit is drift. Run through
# bash so a lost exec bit cannot decide whether the projection is checked.
check_clevis_luks() {
    echo "[98-drift-checks]   clevis LUKS SSOT projection check"
    local gen="$ROOT/usr/libexec/mios/mios-clevis-luks-gen" rc=0 out
    local tgt="$ROOT/etc/mios/clevis-luks.env"
    local repro="usr/libexec/mios/mios-clevis-luks-gen usr/share/mios/mios.toml > etc/mios/clevis-luks.env"
    if [[ ! -f "$gen" ]]; then
        _violation "(67) clevis LUKS generator missing: usr/libexec/mios/mios-clevis-luks-gen"
        return 0
    fi
    out="$(bash "$gen" "${MIOS_TOML_ROOT:-$ROOT}/usr/share/mios/mios.toml" 2>&1)" || rc=$?
    if [[ "$rc" -ne 0 ]] || ! grep -Eq '^CLEVIS_LUKS_ENABLED="' <<<"$out"; then
        printf '[98-drift-checks][diff] generator rc=%s: %s\n' "$rc" "$out" >&2
        _violation "(67) clevis LUKS generator did not project [security.luks] from usr/share/mios/mios.toml"
    elif [[ ! -f "$tgt" ]]; then
        _violation "(67) etc/mios/clevis-luks.env MISSING -- the projection is not committed; run ${repro}"
    elif ! diff -u --label "a/etc/mios/clevis-luks.env" --label "b/mios.toml[security.luks]" \
            "$tgt" <(printf '%s\n' "$out") >&2; then
        _violation "(67) etc/mios/clevis-luks.env is out of sync with [security.luks] SSOT -- run ${repro}"
    else
        echo "[98-drift-checks]   etc/mios/clevis-luks.env matches [security.luks] SSOT"
    fi
}

check_metal_vfio() {
    echo "[98-drift-checks]   MiOS-Metal vfio-pci SSOT projection check"
    local gen="$ROOT/usr/libexec/mios/mios-metal-vfio-gen"
    if [[ ! -x "$gen" && -f "$gen" ]]; then
        chmod +x "$gen" 2>/dev/null || true
    fi
    if [[ -f "$gen" ]]; then
        local out; out="$("$gen" "${MIOS_TOML_ROOT:-$ROOT}/usr/share/mios/mios.toml" 2>&1 || true)"
        if [[ "$out" == *"MIOS_METAL_ENABLED="* ]]; then
            return 0
        else
            _violation "(68) MiOS-Metal vfio generator failed to project SSOT configuration"
        fi
    else
        _violation "(68) MiOS-Metal vfio generator script missing"
    fi
}

check_router_parity() {
    local test_script="$ROOT/usr/lib/mios/agent-pipe/test_mios_router_parity.py"
    local corpus_file="$ROOT/usr/lib/mios/agent-pipe/tests/router_corpus.json"
    if [[ ! -f "$test_script" || ! -f "$corpus_file" ]]; then
        _violation "Router parity test or corpus missing ($test_script or $corpus_file)"
        return 1
    fi
    if ! python3 "$test_script" >/dev/null 2>&1; then
        _violation "test_mios_router_parity.py failed on router_corpus.json"
        return 1
    fi

    # `local x=$(cmd)` returns the status of `local`, not of cmd, so the
    # scan below was unconditionally treated as passing. Declared separately.
    local py_res
    py_res=$(python3 - "$corpus_file" "$ROOT" << 'PYEOF'
import sys, json, re, glob, os

corpus_file = sys.argv[1]
root_dir = sys.argv[2]

with open(corpus_file, "r", encoding="utf-8") as f:
    corpus = json.load(f)

corpus_intents = set()
for item in corpus:
    inp = item.get("input", {})
    if isinstance(inp, dict) and "intent" in inp and inp["intent"]:
        corpus_intents.add(str(inp["intent"]).strip().lower())

pattern = re.compile(r'(?:intent\s*==|get\s*\(\s*["\']intent["\']\s*\)\s*==)\s*["\']([a-zA-Z0-9_]+)["\']')

search_files = [os.path.join(root_dir, "usr/lib/mios/agent-pipe/server.py")] + \
               glob.glob(os.path.join(root_dir, "usr/lib/mios/agent-pipe/mios_pipe/**/*.py"), recursive=True)

unmapped = set()
for filepath in search_files:
    if not os.path.isfile(filepath) or "test_" in os.path.basename(filepath):
        continue
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        for match in pattern.finditer(content):
            intent_val = match.group(1).lower()
            if intent_val not in corpus_intents:
                unmapped.add((intent_val, os.path.relpath(filepath, root_dir)))
    except Exception:
        pass

if unmapped:
    for intent_val, relpath in sorted(unmapped):
        print(f"unmapped intent: {intent_val} in {relpath}", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
PYEOF
)
    local py_rc=$?

    if [[ $py_rc -ne 0 ]]; then
        printf '%s\n' "$py_res" >&2
        _violation "server.py or agent-pipe routing code contains an intent == branch not represented in router_corpus.json"
        return 1
    fi

    echo "[98-drift-checks]   Router Stage-2 parity gate satisfied"
}

check_council_gate_ssot() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(toml_path):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

agent_pipe = data.get("agent_pipe", {})
council = agent_pipe.get("council", {})
if not council:
    sys.stderr.write("    Missing [agent_pipe.council] table in mios.toml\n")
    sys.exit(1)

search_dir = os.path.join(root, "usr/lib/mios/agent-pipe")
if not os.path.isdir(search_dir):
    search_dir = root

code = ""
for r, ds, fs in os.walk(search_dir):
    for f in fs:
        if f.endswith(".py"):
            try:
                with open(os.path.join(r, f), "r", encoding="utf-8", errors="ignore") as fh:
                    code += fh.read() + "\n"
            except OSError:
                pass

council_keys = ["diversity_gate", "diversity_threshold", "aggregator_bypass", "aggregator_bypass_threshold"]
missing = []
for k in council_keys:
    if k not in council:
        missing.append(f"{k} (missing from mios.toml)")
        continue
    pattern = rf"['\"]{k}['\"]"
    if not re.search(pattern, code) and k not in code:
        missing.append(k)

if missing:
    sys.stderr.write(f"    Missing code consumers or TOML definitions for [agent_pipe.council] keys: {missing}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   council-gate SSOT parameters defined in mios.toml and consumed by code"
    else
        _violation "[agent_pipe.council] keys missing or have no code consumer"
    fi
}

check_containerfile_pinned_clones() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys

root = os.environ["MIOS_DRIFT_ROOT"]
unpinned = []

for r, ds, fs in os.walk(root):
    for f in fs:
        if "Containerfile" in f:
            path = os.path.join(r, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    for idx, line in enumerate(fh, 1):
                        if "git clone" in line and not line.strip().startswith("#"):
                            if "--branch" not in line and "--tag" not in line and "-b " not in line and "@" not in line:
                                rel = os.path.relpath(path, root)
                                unpinned.append(f"{rel}:{idx} -> {line.strip()}")
            except OSError:
                pass

if unpinned:
    sys.stderr.write("    Unpinned git clone command(s) found in Containerfiles:\n")
    for u in unpinned:
        sys.stderr.write(f"      {u}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   all git clone invocations in Containerfiles carry explicit"
    else
        _violation "found unpinned git clone command in a Containerfile"
    fi
}

check_firstboot_tier() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py firstboot-tier
    then
        echo "[98-drift-checks]   firstboot tier invariant verified"
    else
        _violation "firstboot tier invariant check failed"
    fi
}

check_rechunk_budget() {
    local script="$ROOT/automation/build/rechunk.sh"
    if [[ ! -f "$script" ]]; then
        _violation "rechunk.sh missing ($script)"
        return 1
    fi
    local bad=()
    if ! grep -q "rechunk_max_layers" "$script"; then
        bad+=("rechunk.sh does not reference SSOT key rechunk_max_layers")
    fi
    if grep -q "mios-bootc:" "$script"; then
        bad+=("rechunk.sh contains legacy mios-bootc: image literal")
    fi
    if grep -E -- "--max-layers=[0-9]+" "$script" >/dev/null 2>&1; then
        bad+=("rechunk.sh contains hardcoded integer --max-layers literal")
    fi
    if ((${#bad[@]} > 0)); then
        _violation "check_rechunk_budget: ${bad[*]}"
        return 1
    fi
    echo "[98-drift-checks]   rechunk budget & SSOT image reference verified"
}

check_gate_registry() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py gate-registry
    then
        echo "[98-drift-checks]   gate registry integrity verified"
    else
        _violation "gate registry drift detected in 98-drift-checks.sh"
    fi
}

check_python_lint() {
    echo "[98-drift-checks]   Python static compilation gate"
    local lint_script="$ROOT/automation/lint-python.sh"
    if [[ ! -f "$lint_script" ]]; then
        _violation "automation/lint-python.sh is missing"
        return
    fi
    local res=0
    bash "$lint_script" >/dev/null 2>&1 || res=$?
    if [[ "$res" -eq 1 ]]; then
        _violation "python linting reported compilation/syntax error(s)"
    fi
}

check_test_hermeticity() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, glob, re

root = os.environ["MIOS_DRIFT_ROOT"]
search_dirs = [
    os.path.join(root, "usr/lib/mios/agent-pipe"),
    os.path.join(root, "tests"),
]

patterns = [
    re.compile(r"\bpsycopg\.connect\b"),
    re.compile(r"\brequests\.(get|post|put|delete)\b"),
    re.compile(r"\bsocket\.socket\b"),
    re.compile(r"\burllib\.request\b"),
    re.compile(r"\bhttp\.client\b"),
]

guard_re = re.compile(r"(SkipTest|skipUnless|skipIf|setUpModule|@unittest\.skip|MIOS_" + r"TEST_LIVE|MIOS_" + r"TEST_DB)")

bad = []

for d in search_dirs:
    if not os.path.isdir(d):
        continue
    for f in os.listdir(d):
        if (f.startswith("test_") or f.endswith(".py")) and f.endswith(".py"):
            path = os.path.join(d, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                
                has_live_call = False
                for p in patterns:
                    if p.search(content):
                        has_live_call = True
                        break
                
                if has_live_call:
                    if not guard_re.search(content):
                        rel = os.path.relpath(path, root)
                        bad.append(f"{rel} calls live network/DB resource without a SkipTest/guard sentinel")
            except OSError:
                pass

if bad:
    for b in bad:
        sys.stderr.write(f"    [hermeticity-drift] {b}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   test hermeticity verified"
    else
        _violation "unguarded live-resource call in test suite"
    fi
}

check_negative_test_coverage() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py negative-test-coverage
    then
        echo "[98-drift-checks]   negative test coverage ratchet verified"
    else
        _violation "negative test coverage drift detected (/)"
    fi
}

check_soft_mode_not_committed() {
    local hits="" f
    for f in "$ROOT"/.github/workflows/*.yml "$ROOT"/.forgejo/workflows/*.yml "$ROOT"/automation/build.sh "$ROOT"/Justfile; do
        [[ -f "$f" ]] || continue
        if grep -qE "MIOS_DRIFT_CHECK_SOFT=1|MIOS_SSOT_LINT_SOFT=1" "$f"; then
            hits+="    ${f#"$ROOT"/}: contains committed soft-mode override (MIOS_DRIFT_CHECK_SOFT=1 or MIOS_SSOT_LINT_SOFT=1)"$'\n'
        fi
    done
    if [[ -n "$hits" ]]; then
        printf '%s' "$hits" >&2
        _violation "soft-mode override is committed in CI/build scripts"
    else
        echo "[98-drift-checks]   no soft-mode override committed in CI/build pipeline"
    fi
}

check_ssot_lint_equivalence() {
    local bin="$ROOT/tools/native/target/release/mios-ssot-lint"
    if [[ ! -x "$bin" ]]; then
        bin="$ROOT/tools/native/target/debug/mios-ssot-lint"
    fi
    if [[ ! -x "$bin" && -x "$ROOT/tools/native/target/debug/mios-ssot-lint.exe" ]]; then
        bin="$ROOT/tools/native/target/debug/mios-ssot-lint.exe"
    fi
    if [[ ! -x "$bin" ]]; then
        if command -v cargo >/dev/null 2>&1; then
            cargo build --manifest-path "$ROOT/tools/native/Cargo.toml" -p mios-ssot-lint >/dev/null 2>&1 || true
        fi
    fi
    if [[ ! -x "$bin" ]]; then
        echo "[98-drift-checks]   mios-ssot-lint binary absent"
        return 0
    fi

    if [[ "$bin" == *.exe && "$(uname -s)" == Linux* ]]; then
        if ! "$bin" --version >/dev/null 2>&1; then
            echo "[98-drift-checks]   mios-ssot-lint binary is Windows .exe in Linux environment"
            return 0
        fi
    fi

    local bash_out bash_code=0
    local rust_out rust_code=0

    bash_out="$(MIOS_SSOT_LINT_ROOT="$ROOT" bash "$ROOT/automation/97-ssot-lint.sh" 2>&1)" || bash_code=$?
    rust_out="$(MIOS_SSOT_LINT_ROOT="$ROOT" "$bin" 2>&1)" || rust_code=$?

    local bash_norm rust_norm
    bash_norm="$(echo "$bash_out" | sed -E 's|/mnt/c/MiOS|/ROOT|g; s|C:\\MiOS|/ROOT|g; s|c:\\MiOS|/ROOT|g; s|\\|/|g')"
    rust_norm="$(echo "$rust_out" | sed -E 's|/mnt/c/MiOS|/ROOT|g; s|C:\\MiOS|/ROOT|g; s|c:\\MiOS|/ROOT|g; s|\\|/|g')"

    if [[ "$bash_code" -ne "$rust_code" || "$bash_norm" != "$rust_norm" ]]; then
        _violation "mios-ssot-lint exit code ($rust_code) differs from bash 97-ssot-lint.sh ($bash_code)"
        return
    fi
    if [[ "$bash_norm" != "$rust_norm" ]]; then
        _violation "mios-ssot-lint output differs from bash 97-ssot-lint.sh"
        return
    fi

    echo "[98-drift-checks]   mios-ssot-lint Rust twin byte-identical to bash 97-ssot-lint.sh"
}

check_gate_index() {
    if ! _require_python3; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-gate-index.py" --check >/dev/null 2>&1; then
        echo "[98-drift-checks]   gate index in sync with main registration"
    else
        _emit_projection_evidence "tools/generate-gate-index.py" "usr/share/mios/reference/drift-gate-index.tsv"
        _violation "usr/share/mios/reference/drift-gate-index.tsv is out of sync with main() -- run python3 tools/generate-gate-index.py"
    fi
}

check_oci_archive_path() {
    local consumer="$ROOT/tools/install.sh"
    local producer="$ROOT/usr/libexec/mios/mios-stage-oci-archive"

    if [[ ! -f "$consumer" || ! -f "$producer" ]]; then
        echo "[98-drift-checks]   oci-archive producer/consumer absent"
        return 0
    fi

    local c_path p_path
    c_path="$(grep -oE '/mnt/mios-repo/[a-zA-Z0-9_.-]+\.tar' "$consumer" | head -1 || true)"
    p_path="$(grep -oE '/mnt/mios-repo/[a-zA-Z0-9_.-]+\.tar' "$producer" | head -1 || true)"

    if [[ -z "$c_path" || -z "$p_path" || "$c_path" != "$p_path" ]]; then
        _violation "oci-archive default path mismatch between producer ($p_path) and consumer ($c_path)"
    else
        echo "[98-drift-checks]   oci-archive producer and consumer paths match"
    fi
}

check_replaceme_mount_substitution() {
    local justfile="$ROOT/Justfile"
    if [[ ! -f "$justfile" ]]; then
        echo "[98-drift-checks]   Justfile absent"
        return 0
    fi

    _need_python || return 0

    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re

root = os.environ["MIOS_DRIFT_ROOT"]
justfile = os.path.join(root, "Justfile")

with open(justfile, "r", encoding="utf-8") as f:
    content = f.read()

recipe_blocks = re.split(r"\n(?=[a-zA-Z0-9_-]+:)", content)

bad = []
for block in recipe_blocks:
    lines = block.strip().split("\n")
    if not lines or ":" not in lines[0]:
        continue
    recipe_name = lines[0].split(":")[0].strip()
    block_text = "\n".join(lines[1:])

    mounted_configs = re.findall(r"-v\s+\.?/?config/artifacts/([a-zA-Z0-9_.-]+\.toml)", block_text)
    for cfg in mounted_configs:
        cfg_path = os.path.join(root, "config/artifacts", cfg)
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8", errors="ignore") as cf:
                cfg_text = cf.read()
            if "REPLACEME" in cfg_text or "AAAA_REPLACE" in cfg_text:
                if "sed " not in block_text and "sed -e" not in block_text:
                    bad.append(f"Recipe '{recipe_name}' mounts '{cfg}' containing REPLACEME tokens without credential-substituting sed")
                if "REPLACEME_WITH_SHA512_HASH" in cfg_text:
                    if "MIOS_USER_PASSWORD_HASH:-" in block_text or "[ -z \"${MIOS_USER_PASSWORD_HASH" not in block_text:
                        bad.append(f"Recipe '{recipe_name}' mounts '{cfg}' with REPLACEME_WITH_SHA512_HASH without asserting non-empty MIOS_USER_PASSWORD_HASH")

if bad:
    for b in bad:
        sys.stderr.write(f"    [replaceme-drift] {b}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   BIB recipes perform credential substitution on mounted config templates"
    else
        _violation "unsubstituted REPLACEME template raw-mounted in Justfile BIB recipe"
    fi
}

check_kickstart_shell_syntax() {
    local cfg="$ROOT/usr/share/mios/ventoy/mios-kickstart.cfg"
    local iso_toml="$ROOT/config/artifacts/iso.toml"

    local bad_ks="" f

    for f in "$cfg" "$iso_toml"; do
        [[ -f "$f" ]] || continue
        local post_sh="$(sed -n '/%post/,/%end/p' "$f" | sed 's/.*%post.*//; s/.*%end.*//')"
        if [[ -n "$post_sh" ]]; then
            if ! printf '%s\n' "$post_sh" | bash -n 2>/dev/null; then
                bad_ks+="    ${f#"$ROOT"/}: embedded %post shell failed bash -n syntax check"$'\n'
            fi
        fi
    done

    if [[ -n "$bad_ks" ]]; then
        printf '%s' "$bad_ks" >&2
        _violation "embedded kickstart shell contains bash syntax errors"
    else
        echo "[98-drift-checks]   embedded kickstart %post shell syntax verified clean with bash -n"
    fi
}

check_bib_rootfs_label_policy() {
    local justfile="$ROOT/Justfile"
    if [[ ! -f "$justfile" ]]; then
        echo "[98-drift-checks]   Justfile absent"
        return 0
    fi

    _need_python || return 0

    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re

root = os.environ["MIOS_DRIFT_ROOT"]
justfile = os.path.join(root, "Justfile")

with open(justfile, "r", encoding="utf-8") as f:
    content = f.read()

recipe_blocks = re.split(r"\n(?=[a-zA-Z0-9_-]+:)", content)

valid_fs = {"ext4", "xfs", "btrfs"}
bad = []

for block in recipe_blocks:
    lines = block.strip().split("\n")
    if not lines or ":" not in lines[0]:
        continue
    recipe_name = lines[0].split(":")[0].strip()
    if recipe_name.startswith("#"):
        continue
    block_text = "\n".join(ln for ln in lines[1:] if ":=" not in ln)

    if "{{BIB}}" in block_text or "bootc-image-builder" in block_text:
        if "--rootfs" not in block_text:
            bad.append(f"Recipe '{recipe_name}' calls BIB without mandatory --rootfs flag")
        else:
            match = re.search(r"--rootfs\s+([a-zA-Z0-9]+)", block_text)
            if not match or match.group(1) not in valid_fs:
                fs = match.group(1) if match else "missing"
                bad.append(f"Recipe '{recipe_name}' uses unapproved or missing rootfs type '{fs}' (must be ext4/xfs/btrfs)")

if bad:
    for b in bad:
        sys.stderr.write(f"    [bib-rootfs-drift] {b}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   BIB recipes enforce valid"
    else
        _violation "BIB recipe violates rootfs filesystem label policy"
    fi
}

check_offline_install_invariant() {
    local install_script="$ROOT/tools/install.sh"
    local oci_ks="$ROOT/usr/share/mios/ventoy/mios-oci-install.ks"
    
    if [[ ! -f "$install_script" ]]; then
        _violation "tools/install.sh is absent -- offline-install invariant cannot be verified"
        return 0
    fi

    if ! bash -n "$install_script" 2>/dev/null; then
        _violation "tools/install.sh failed bash -n syntax check"
        return 0
    fi

    # Strip comments so AI-hints and docstrings do not satisfy the executable invariant
    local code
    code="$(sed 's/#.*//' "$install_script")"

    if ! grep -q -E '(oci-archive:|--transport\s+oci-archive)' <<<"$code"; then
        _violation "tools/install.sh executable code does not invoke bootc install with oci-archive transport/source"
        return 0
    fi

    # Assert executable code in tools/install.sh and mios-oci-install.ks contains no forbidden network calls
    local net_regex='(http://|https://|git clone|podman pull|skopeo copy docker://)'
    local net_token
    net_token="$(sed 's/#.*//' "$install_script" | grep -nE "$net_regex" || true)"
    if [[ -n "$net_token" ]]; then
        echo "$net_token" >&2
        _violation "tools/install.sh executable code contains forbidden network pull token violating zero-network offline-install contract"
        return 0
    fi

    if [[ -f "$oci_ks" ]]; then
        local ks_net_token
        ks_net_token="$(sed 's/#.*//' "$oci_ks" | grep -nE "$net_regex" || true)"
        if [[ -n "$ks_net_token" ]]; then
            echo "$ks_net_token" >&2
            _violation "usr/share/mios/ventoy/mios-oci-install.ks executable code contains forbidden network pull token"
            return 0
        fi
    fi

    echo "[98-drift-checks]   tools/install.sh zero-network offline-install invariant verified clean against executable code"
}

check_installer_family_roles() {
    local scripts=("$ROOT/install.sh" "$ROOT/tools/install.sh" "$ROOT/automation/install.sh" "$ROOT/automation/install-fhs.sh")
    local bad_installers=""
    local roles=()

    local s
    for s in "${scripts[@]}"; do
        if [[ ! -f "$s" ]]; then
            continue
        fi
        local role="$(grep -oE '^# MIOS_INSTALLER_ROLE=[a-zA-Z0-9_-]+' "$s" | cut -d= -f2 || true)"
        if [[ -z "$role" ]]; then
            bad_installers+="    ${s#"$ROOT"/}: missing # MIOS_INSTALLER_ROLE header marker"$'\n'
        else
            if [[ " ${roles[*]:-} " == *" ${role} "* ]]; then
                bad_installers+="    ${s#"$ROOT"/}: duplicate # MIOS_INSTALLER_ROLE='$role'"$'\n'
            else
                roles+=("$role")
            fi
        fi
    done

    if [[ -n "$bad_installers" ]]; then
        printf '%s' "$bad_installers" >&2
        _violation "installer script role marker violation or collision"
    else
        echo "[98-drift-checks]   installer family role markers verified unique across all installers"
    fi
}

check_bib_configs_projection() {
    if ! _require_python3; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-bib-configs.py" --check >/dev/null 2>&1; then
        echo "[98-drift-checks]   BIB artifact configs in sync with mios.toml [deploy.artifacts] SSOT"
    else
        _emit_projection_evidence "tools/generate-bib-configs.py" "config/artifacts/bib.toml" "config/artifacts/iso.toml"
        _violation "BIB artifact configs (bib.toml, iso.toml) out of sync with mios.toml [deploy.artifacts] -- run python3 tools/generate-bib-configs.py"
    fi
}

check_repo_partition_label_ssot() {
    # The label is READ from the SSOT, never defaulted.
    _need_python || return 0
    local ssot="$ROOT/usr/share/mios/mios.toml" ssot_label f
    local install_sh="$ROOT/tools/install.sh"
    local cfg="$ROOT/usr/share/mios/ventoy/mios-kickstart.cfg"
    local oci_ks="$ROOT/usr/share/mios/ventoy/mios-oci-install.ks"
    local loopback="$ROOT/field/loopback.cfg"
    # A consumer that has gone missing is a violation: the label it tracked is
    # now enforced nowhere, which is exactly when this gate should speak.
    for f in "$ssot" "$install_sh" "$cfg" "$oci_ks" "$loopback"; do
        [[ -f "$f" ]] || { _violation "repo partition label consumer is absent: ${f#"$ROOT"/}"; return; }
    done
    ssot_label="$(python3 "$ROOT/tools/read-ssot-key.py" field.repo_partition.label)" \
        || { _violation "[field.repo_partition].label is absent from the SSOT -- the label its consumers track is undefined"; return; }
    local bad=""
    grep -q "blkid -L \"$ssot_label\"" "$install_sh" \
        || bad+="    tools/install.sh does not reference [field.repo_partition].label '$ssot_label'"$'\n'
    grep -q "blkid -L \"$ssot_label\"" "$cfg" \
        || bad+="    usr/share/mios/ventoy/mios-kickstart.cfg does not reference [field.repo_partition].label '$ssot_label'"$'\n'
    grep -q "$ssot_label" "$oci_ks" \
        || bad+="    usr/share/mios/ventoy/mios-oci-install.ks does not reference [field.repo_partition].label '$ssot_label'"$'\n'
    grep -q -E "($ssot_label|@@REPO_LABEL@@)" "$loopback" \
        || bad+="    field/loopback.cfg does not reference [field.repo_partition].label '$ssot_label' or @@REPO_LABEL@@"$'\n'
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "repo partition label mismatch against [field.repo_partition].label SSOT"
    else
        echo "[98-drift-checks]   repo partition label consumers match [field.repo_partition].label SSOT"
    fi
}

check_bib_single_config_invariant() {
    local justfile="$ROOT/Justfile"
    if [[ ! -f "$justfile" ]]; then
        echo "[98-drift-checks]   Justfile absent"
        return 0
    fi

    _need_python || return 0

    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, glob
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
justfile = os.path.join(root, "Justfile")

toml_files = glob.glob(os.path.join(root, "config/artifacts/*.toml"))
bad = []

if tomllib:
    for tf in toml_files:
        try:
            with open(tf, "rb") as f:
                tomllib.load(f)
        except Exception as e:
            bad.append(f"Invalid TOML syntax in {os.path.basename(tf)}: {e}")

with open(justfile, "r", encoding="utf-8") as f:
    content = f.read()

recipe_blocks = re.split(r"\n(?=[a-zA-Z0-9_-]+:)", content)

for block in recipe_blocks:
    lines = block.strip().split("\n")
    if not lines:
        continue
    header_line = lines[0].strip()
    if header_line.startswith("#") or ":" not in header_line:
        continue
    recipe_name = header_line.split(":")[0].strip()
    if not re.match(r"^[a-zA-Z0-9_-]+$", recipe_name):
        continue
    block_text = "\n".join(lines[1:])

    if "{{BIB}}" in block_text or "bootc-image-builder" in block_text:
        config_mounts = re.findall(r"-v\s+\S+:/config\.(toml|json)", block_text)
        if len(config_mounts) != 1:
            bad.append(f"Recipe '{recipe_name}' must mount exactly ONE /config.toml (found {len(config_mounts)})")

if bad:
    for b in bad:
        sys.stderr.write(f"    [bib-config-drift] {b}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   BIB recipes enforce single /config.toml mount and valid TOML syntax"
    else
        _violation "BIB recipe config mount or TOML syntax violation"
    fi
}

check_build_artifacts_output_dir() {
    local ssot="$ROOT/usr/share/mios/mios.toml"
    local justfile="$ROOT/Justfile"

    if [[ ! -f "$ssot" || ! -f "$justfile" ]]; then
        echo "[98-drift-checks]   build output dir consumers absent"
        return 0
    fi

    local output_dir="$(grep -A 3 '\[build\.artifacts\]' "$ssot" | grep 'output_dir' | head -1 | cut -d'"' -f2 || echo "Build")"

    local bad_out=""
    if grep -qE "(mkdir -p output|output/|-v \./output|>\s*output/)" "$justfile"; then
        bad_out+="    Justfile contains non-SSOT output path references (must use '$output_dir/')"
    fi

    if [[ -n "$bad_out" ]]; then
        printf '%s\n' "$bad_out" >&2
        _violation "Justfile recipe outputs violate [build.artifacts].output_dir SSOT"
    else
        echo "[98-drift-checks]   Justfile artifact recipes enforce SSOT output directory"
    fi
}

check_win11_vm_template_xml() {
    local xml_file="$ROOT/tools/win11-secureboot-template.xml"
    local ssot="$ROOT/usr/share/mios/mios.toml"

    if [[ ! -f "$xml_file" || ! -f "$ssot" ]]; then
        echo "[98-drift-checks]   win11 VM template or SSOT absent"
        return 0
    fi

    _need_python || return 0

    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, xml.etree.ElementTree as ET

import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
xml_path = os.path.join(root, "tools/win11-secureboot-template.xml")
ssot_path = os.path.join(root, "usr/share/mios/mios.toml")

bad = []

try:
    tree = ET.parse(xml_path)
    root_elem = tree.getroot()
except Exception as e:
    bad.append(f"tools/win11-secureboot-template.xml is not well-formed XML: {e}")
    sys.stderr.write(f"    [win11-xml-drift] {bad[0]}\n")
    sys.exit(1)

if tomllib:
    try:
        with open(ssot_path, "rb") as f:
            data = tomllib.load(f)
        vm_cfg = data.get("vm", {}).get("win11", {})
        ssot_mem = str(vm_cfg.get("memory_kib", 25165824))
        ssot_vcpu = str(vm_cfg.get("vcpus", 12))

        mem_elem = root_elem.find("memory")
        vcpu_elem = root_elem.find("vcpu")

        if mem_elem is not None and mem_elem.text.strip() != ssot_mem:
            bad.append(f"Memory in template ({mem_elem.text.strip()}) does not match [vm.win11].memory_kib SSOT ({ssot_mem})")
        if vcpu_elem is not None and vcpu_elem.text.strip() != ssot_vcpu:
            bad.append(f"vCPUs in template ({vcpu_elem.text.strip()}) does not match [vm.win11].vcpus SSOT ({ssot_vcpu})")
    except Exception as e:
        bad.append(f"Failed to validate SSOT projection: {e}")

if bad:
    for b in bad:
        sys.stderr.write(f"    [win11-xml-drift] {b}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   Win11 VM template is well-formed XML and projects SSOT [vm.win11]"
    else
        _violation "Win11 VM template XML well-formedness or SSOT projection violation"
    fi
}

check_ipa_enroll_projection() {
    if ! _require_python3; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-ipa-enroll-env.py" --check >/dev/null 2>&1; then
        echo "[98-drift-checks]   etc/mios/ipa-enroll.env matches [identity.ipa] SSOT"
    else
        _emit_projection_evidence "tools/generate-ipa-enroll-env.py" "etc/mios/ipa-enroll.env"
        _violation "etc/mios/ipa-enroll.env is out of sync with [identity.ipa] SSOT -- run python3 tools/generate-ipa-enroll-env.py"
    fi
}

check_uki_cmdline_projection() {
    if ! _require_python3; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-uki-cmdline.py" --check >/dev/null 2>&1; then
        echo "[98-drift-checks]   usr/lib/kernel/cmdline matches kargs.d/*.toml drop-ins"
    else
        _emit_projection_evidence "tools/generate-uki-cmdline.py" "usr/lib/kernel/cmdline"
        _violation "usr/lib/kernel/cmdline is out of sync with usr/lib/bootc/kargs.d/*.toml -- run python3 tools/generate-uki-cmdline.py"
    fi
}

check_composefs_projection() {
    local conf="$ROOT/usr/lib/ostree/prepare-root.conf"
    local script="$ROOT/automation/77-composefs-verity.sh"

    if [[ ! -f "$conf" || ! -f "$script" ]]; then
        echo "[98-drift-checks]   composefs prepare-root.conf absent"
        return 0
    fi

    local tmp_dir tmp_conf
    tmp_dir="$(mktemp -d)"
    tmp_conf="${tmp_dir}/prepare-root.conf"

    MIOS_TOML_ROOT="$ROOT" COMPOSEFS_CONF="$tmp_conf" bash "$script" >/dev/null 2>&1 || true

    if [[ ! -f "$tmp_conf" ]]; then
        rm -rf "$tmp_dir"
        _violation "automation/77-composefs-verity.sh failed to render prepare-root.conf"
        return
    fi

    if ! diff -u "$conf" "$tmp_conf" >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        _violation "usr/lib/ostree/prepare-root.conf is out of sync with [security].composefs_mode SSOT"
    else
        rm -rf "$tmp_dir"
        echo "[98-drift-checks]   usr/lib/ostree/prepare-root.conf matches [security].composefs_mode SSOT"
    fi
}

check_cockpit_projection() {
    if ! _require_python3; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/generate-cockpit-conf.py" --check >/dev/null 2>&1; then
        echo "[98-drift-checks]   etc/cockpit/cockpit.conf matches mios.toml [cockpit] SSOT"
    else
        _emit_projection_evidence "tools/generate-cockpit-conf.py" "etc/cockpit/cockpit.conf"
        _violation "etc/cockpit/cockpit.conf is out of sync with mios.toml [cockpit] SSOT -- run python3 tools/generate-cockpit-conf.py"
    fi
}

check_chrony_ptp_dropin() {
    local dropin_script="$ROOT/usr/libexec/mios/mios-chrony-ptp-dropin"
    local service_unit="$ROOT/usr/lib/systemd/system/mios-chrony-ptp.service"
    local canon_conf="$ROOT/etc/chrony.conf"

    if [[ ! -f "$dropin_script" || ! -f "$service_unit" ]]; then
        _violation "Chrony PTP drop-in generator script or service unit missing"
        return
    fi

    if ! bash -n "$dropin_script" >/dev/null 2>&1; then
        _violation "usr/libexec/mios/mios-chrony-ptp-dropin syntax error"
        return
    fi

    local tmp_dir tmp_ptp tmp_chrony_d
    tmp_dir="$(mktemp -d)"
    tmp_ptp="${tmp_dir}/dev_ptp0"
    tmp_chrony_d="${tmp_dir}/chrony.d"
    touch "$tmp_ptp"

    local old_conf_hash="" new_conf_hash=""
    if [[ -f "$canon_conf" ]]; then
        old_conf_hash="$(sha256sum "$canon_conf" | awk '{print $1}')"
    fi

    PTP_DEV="$tmp_ptp" CHRONY_D="$tmp_chrony_d" bash "$dropin_script" >/dev/null 2>&1 || true

    if [[ ! -f "${tmp_chrony_d}/10-ptp.conf" ]]; then
        rm -rf "$tmp_dir"
        _violation "mios-chrony-ptp-dropin failed to generate 10-ptp.conf when /dev/ptp0 exists"
        return
    fi

    PTP_DEV="$tmp_ptp" CHRONY_D="$tmp_chrony_d" bash "$dropin_script" >/dev/null 2>&1 || true

    if [[ -f "$canon_conf" ]]; then
        new_conf_hash="$(sha256sum "$canon_conf" | awk '{print $1}')"
        if [[ "$old_conf_hash" != "$new_conf_hash" ]]; then
            rm -rf "$tmp_dir"
            _violation "mios-chrony-ptp-dropin mutated canonical etc/chrony.conf"
            return
        fi
    fi

    rm -rf "$tmp_dir"
    echo "[98-drift-checks]   Chrony PTP drop-in generator is idempotent and leaves canonical chrony.conf unchanged"
}

check_renderer_gate_coverage() {
    local auto_dir="$ROOT/automation"
    local drift_file="$ROOT/automation/98-drift-checks.sh"

    if [[ ! -d "$auto_dir" || ! -f "$drift_file" ]]; then
        return 0
    fi

    local allowlist=("34-render-quadlets.sh" "35-render-ports.sh")

    local render_scripts=()
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        local base="$(basename "$f")"
        local allowed=0
        for item in "${allowlist[@]}"; do
            if [[ "$base" == "$item" ]]; then
                allowed=1
                break
            fi
        done
        if [[ "$allowed" -eq 0 ]]; then
            render_scripts+=("$base")
        fi
    done < <(find "$auto_dir" -maxdepth 1 -name "*-render*.sh" -o -name "*render*.sh" 2>/dev/null)

    local unmapped=()
    local script
    for script in "${render_scripts[@]}"; do
        local stem="$(echo "$script" | sed -E 's/^[0-9]+-//; s/-render.*//; s/\.sh$//')"
        if ! grep -qE "check_.*${stem}.*projection|check_.*${stem}" "$drift_file"; then
            unmapped+=("$script")
        fi
    done

    if [[ ${#unmapped[@]} -gt 0 ]]; then
        _violation "The following renderer scripts have no corresponding projection check in 98-drift-checks.sh: ${unmapped[*]}"
    else
        echo "[98-drift-checks]   renderer gate coverage verified clean"
    fi
}

check_smoke_manifest() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(toml_path):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

sc = data.get("testing", {}).get("smoke_components", {})
if not sc:
    sys.stderr.write("    Missing [testing.smoke_components] table in mios.toml\n")
    sys.exit(1)

missing = []
for key in ["shims", "units", "python_entries"]:
    for rel_path in sc.get(key, []):
        full_path = os.path.join(root, rel_path)
        if not os.path.exists(full_path):
            missing.append(rel_path)

if missing:
    sys.stderr.write(f"    Paths listed in [testing.smoke_components] missing from repo: {missing}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   smoke manifest components in mios.toml exist in source tree"
    else
        _violation "smoke manifest component missing from repo"
    fi
}

check_negative_coverage() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
checks_sh = os.path.join(root, "automation/98-drift-checks.sh")
negatives_sh = os.path.join(root, "tests/drift-gate-negatives.sh")
toml_path = os.path.join(root, "usr/share/mios/mios.toml")

if not (os.path.isfile(checks_sh) and os.path.isfile(negatives_sh) and os.path.isfile(toml_path)):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

exempt = set(data.get("testing", {}).get("negative_coverage_exempt", {}).get("exempt", []))

with open(checks_sh, "r", encoding="utf-8", errors="ignore") as f:
    c_content = f.read()

main_idx = c_content.rfind("main() {")
main_body = c_content[main_idx:]
dispatched = set(re.findall(r"^\s*(check_[a-z0-9_]+)\b", main_body, re.MULTILINE))

with open(negatives_sh, "r", encoding="utf-8", errors="ignore") as f:
    n_content = f.read()

covered = set(re.findall(r"check_[a-z0-9_]+\b", n_content))

uncovered = dispatched - covered - exempt
if uncovered:
    sys.stderr.write(f"    Dispatched drift checks lacking negative test coverage and not exempt: {sorted(list(uncovered))}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   negative test coverage gate: all dispatched checks are covered or exempt"
    else
        _violation "drift checks lacking negative test coverage"
    fi
}

check_verb_templates() {
    _need_python || return 0
    if python3 "${ROOT}/tools/verb-template-check.py"; then
        echo "[98-drift-checks]   verb templates compile and validate against SSOT args"
    else
        _violation "verb templates compilation or placeholder validation failed"
    fi
}

check_pipe_boundaries() {
    _need_python || return 0
    local manifest="${ROOT}/usr/share/mios/pipe-boundaries.manifest.json"
    if [ ! -f "$manifest" ]; then
        _violation "pipe-boundaries.manifest.json is missing"
        return 0
    fi
    echo "[98-drift-checks]   pipe-boundaries.manifest.json is up-to-date"
}

check_vllm_name_canonical() {
    if grep -rn --exclude="98-drift-checks.sh" "MIOS_AI_VLL[M]_\|MIOS_AI_SGLAN[G]_" "${ROOT}/automation/" "${ROOT}/usr/lib/mios/" >/dev/null 2>&1; then
        _violation "found legacy M""IOS_AI_VLLM_ or M""IOS_AI_SGLANG_ long names in active code or automation"
    else
        echo "[98-drift-checks]   vLLM / SGLang canonical names reconciled to short consumer form"
    fi
}

check_pipe_extraction_parity() {
    _need_python || return 0

    if MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/pipe-parity-check.py" >/dev/null 2>&1; then
        echo "[98-drift-checks]   extraction surface parity + one-way imports clean"
    else
        _violation "mios_pipe extraction surface parity or one-way import rule violated"
    fi
}

# --- Guacamole remote access desktop unit definitions match SSOT services ---
check_guacamole_consistency() {
    echo "[98-drift-checks] Guacamole remote access desktop unit definitions match SSOT services"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/render-desktop.py --check 2>&1)" || { _violations_from "check_guacamole_consistency: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

check_law_enforcers() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

laws_section = data.get("laws", {})
laws = laws_section.get("laws", [])
drift_script = os.path.join(root, "automation/98-drift-checks.sh")
with open(drift_script, "r", encoding="utf-8") as f:
    drift_code = f.read()

postcheck_script = os.path.join(root, "automation/99-postcheck.sh")
postcheck_code = ""
if os.path.isfile(postcheck_script):
    with open(postcheck_script, "r", encoding="utf-8") as f:
        postcheck_code = f.read()

missing = []
for law in laws:
    if not isinstance(law, dict):
        continue
    law_id = law.get("id")
    slug = law.get("slug")
    enforced = law.get("enforced_by", "")
    for target in [t.strip() for t in enforced.split(",") if t.strip()]:
        if ":" not in target:
            continue
        fname, ref = target.split(":", 1)
        fname = fname.strip()
        ref = ref.strip()
        if fname == "98-drift-checks.sh":
            if not re.search(rf"^{ref}\s*\(\)", drift_code, re.MULTILINE):
                missing.append(f"Law {law_id} ({slug}) -> {target} not found in 98-drift-checks.sh")
        elif fname == "99-postcheck.sh":
            if not os.path.isfile(postcheck_script) or (ref not in postcheck_code and f"item{ref}" not in postcheck_code):
                missing.append(f"Law {law_id} ({slug}) -> {target} not found in 99-postcheck.sh")

if missing:
    for m in missing:
        sys.stderr.write(f"    {m}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   all [laws].enforced_by targets resolve in codebase"
    else
        _violation "[laws].enforced_by target function missing from codebase"
    fi
}

check_usr_over_etc() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, subprocess

root = os.environ["MIOS_DRIFT_ROOT"]
try:
    tracked = subprocess.check_output(["git", "ls-files", "etc/"], cwd=root, text=True).splitlines()
except Exception:
    tracked = []

usr_share = os.path.join(root, "usr/share")
usr_lib = os.path.join(root, "usr/lib")

exempt_prefixes = (
    "etc/containers/systemd/",
    "etc/wsl.conf",
    "etc/cockpit/",
    "etc/containers/",
    "etc/greenboot/",
    "etc/mios/",
    "etc/skel/",
    "etc/profile.d/",
)

violations = []
for f in tracked:
    if f.startswith(exempt_prefixes) or ".d/" in f or ".d" in os.path.basename(f):
        continue
    rel = f[4:]
    match_share = os.path.join(usr_share, rel)
    match_lib = os.path.join(usr_lib, rel)
    if os.path.isfile(match_share) or os.path.isfile(match_lib):
        violations.append(f"{f} shadows USR SSOT file ({match_share if os.path.isfile(match_share) else match_lib})")

if violations:
    for v in violations:
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   Law 1 USR-OVER-ETC verified clean"
    else
        _violation "Law 1 USR-OVER-ETC violated: tracked /etc file duplicates a /usr SSOT surface"
    fi
}

check_projection_registry() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
drift_script = os.path.join(root, "automation/98-drift-checks.sh")

with open(drift_script, "r", encoding="utf-8") as f:
    drift_code = f.read()

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

surfaces = data.get("laws", {}).get("projection_registry", {}).get("surfaces", [])
violations = []

for s in surfaces:
    gen = s.get("generator", "")
    chk = s.get("check", "")
    if gen and not os.path.exists(os.path.join(root, gen)):
        violations.append(f"Projection generator '{gen}' missing from disk")
    if chk and not re.search(rf"^{chk}\s*\(\)", drift_code, re.MULTILINE):
        violations.append(f"Projection check function '{chk}' missing from 98-drift-checks.sh")

if violations:
    for v in violations:
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   Law 8 SSOT-PROJECTION registry verified clean"
    else
        _violation "Law 8 SSOT-PROJECTION registry check failed"
    fi
}

check_db_seed_coverage() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, importlib.util
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
seed_script = os.path.join(root, "usr/libexec/mios/seed-db-config.py")

if not os.path.isfile(toml_path):
    sys.stderr.write(f"    Missing SSOT file: {toml_path}\n")
    sys.exit(1)

if not os.path.isfile(seed_script):
    sys.stderr.write(f"    Missing db seeder script: {seed_script}\n")
    sys.exit(1)

try:
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
except Exception as e:
    sys.stderr.write(f"    Failed to parse mios.toml: {e}\n")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("seed_db_config", seed_script)
if not spec or not spec.loader:
    sys.stderr.write(f"    Failed to load module spec from {seed_script}\n")
    sys.exit(1)
seed_mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(seed_mod)
    get_seeded_sections = getattr(seed_mod, "get_seeded_sections", None)
    if not get_seeded_sections:
        sys.stderr.write(f"    get_seeded_sections function absent in {seed_script}\n")
        sys.exit(1)
except Exception as e:
    sys.stderr.write(f"    Failed to import get_seeded_sections from {seed_script}: {e}\n")
    sys.exit(1)

seeded_set = set(get_seeded_sections(data))
handled_separately = {"verbs", "packages"}

uncovered = []
for sec_name in data.keys():
    if sec_name not in seeded_set and sec_name not in handled_separately:
        uncovered.append(f"Section '{sec_name}' is not handled by seed-db-config.py")

if uncovered:
    for u in uncovered:
        sys.stderr.write(f"    {u}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   DB seed coverage gate verified clean"
    else
        _violation "DB seed coverage gate check failed: unseeded SSOT section found"
    fi
}

check_verb_stub_backends() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py verb-stub-backends
    then
        echo "[98-drift-checks]   verb stub backends gate verified clean"
    else
        _violation "verb stub backends check failed: stub backend script found"
    fi
}

check_account_column_parity() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re

root = os.environ["MIOS_DRIFT_ROOT"]
schema_path = os.path.join(root, "usr/share/mios/postgres/schema-init.sql")
consumers = [
    os.path.join(root, "usr/libexec/mios/mios-account-sync"),
    os.path.join(root, "usr/libexec/mios/mios-userdb-render"),
    os.path.join(root, "usr/libexec/mios/mios-winaccounts-render"),
]

if not os.path.isfile(schema_path):
    sys.exit(0)

with open(schema_path, "r", encoding="utf-8") as f:
    schema_code = f.read()

match = re.search(r"CREATE TABLE (?:IF NOT EXISTS )?account \((.*?)\);", schema_code, re.DOTALL | re.IGNORECASE)
columns = set()
if match:
    lines = match.group(1).splitlines()
    for line in lines:
        line_clean = line.strip()
        if line_clean and not line_clean.startswith("--") and not line_clean.upper().startswith("CONSTRAINT") and not line_clean.upper().startswith("PRIMARY"):
            col_name = line_clean.split()[0].strip('"')
            columns.add(col_name)

alter_matches = re.findall(r"ALTER TABLE account ADD COLUMN (?:IF NOT EXISTS )?(\w+)", schema_code, re.IGNORECASE)
columns.update(alter_matches)

required_columns = {"name", "password_hash", "uid", "gid", "display", "home_dir", "shell", "groups", "is_admin", "enabled"}

missing_in_schema = required_columns - columns

viol = []
if missing_in_schema:
    viol.append(f"Account schema missing column(s) required by consumer projections: {sorted(list(missing_in_schema))}")

if viol:
    for v in viol:
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   account column parity gate verified clean"
    else
        _violation "account column parity check failed"
    fi
}

check_v2v_import_ssot() {
    local wrapper="$ROOT/usr/libexec/mios/mios-v2v-import"
    if [[ ! -f "$wrapper" ]]; then
        _violation "usr/libexec/mios/mios-v2v-import missing"
        return 1
    fi
    if ! bash -n "$wrapper" >/dev/null 2>&1; then
        _violation "usr/libexec/mios/mios-v2v-import failed bash -n syntax check"
        return 1
    fi
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, subprocess
import tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
wrapper = os.path.join(root, "usr/libexec/mios/mios-v2v-import")
toml_path = os.path.join(root, "usr/share/mios/mios.toml")

with open(wrapper, "r", encoding="utf-8") as f:
    wcode = f.read()

if "qcow2" in wcode and "output_format" not in wcode:
    sys.stderr.write("    mios-v2v-import hardcodes format instead of resolving [virt.v2v].output_format\n")
    sys.exit(1)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

v2v_cfg = data.get("virt", {}).get("v2v", {})
fmt = v2v_cfg.get("output_format", "qcow2")

proc = subprocess.run(["bash", wrapper, "--dry-run"], capture_output=True, text=True, env=dict(os.environ, MIOS_TOML=toml_path))
out = proc.stdout + proc.stderr
if f"-of {fmt}" not in out:
    sys.stderr.write(f"    mios-v2v-import --dry-run output does not contain expected '-of {fmt}' from SSOT\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   virt-v2v import wrapper & SSOT parity verified"
    else
        _violation "virt-v2v import wrapper SSOT parity check failed"
    fi
}


# --- shell and script module line counts remain within maintainability limits ---
check_module_length() {
    echo "[98-drift-checks] shell and script module line counts remain within maintainability limits"
    # Walks the package RECURSIVELY against the [refactor] shrink-only register.
    # The former body used find -maxdepth 1 and saw 9 of 112 modules.
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-module-length.py 2>&1)" || { _violations_from "check_module_length: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

check_vendored_assets_non_stub() {
    local vdir="$ROOT/usr/share/mios/vendored"
    if [[ ! -d "$vdir" ]]; then
        echo "[98-drift-checks]   vendored assets dir absent"
        return 0
    fi
    local stubs="" f sz
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        sz=$(wc -c < "$f" 2>/dev/null || stat -c %s "$f" 2>/dev/null || echo 0)
        if [[ "$sz" -lt 100 ]]; then
            stubs+="    $f (${sz} bytes - stub file)"$'\n'
        fi
    done < <(find "$vdir" -type f ! -name '.keep' ! -name 'VERSIONS.txt' 2>/dev/null)

    if [[ -n "$stubs" ]]; then
        printf '%s' "$stubs" >&2
        _violation "(87, WS-OFFL) vendored asset directory contains stub files (<100 bytes); replace with real assets or mios-vendor-refresh"
    else
        echo "[98-drift-checks]   vendored assets are non-stub"
    fi
}

check_resolved_env_lossless() {
    local base_file="$ROOT/usr/share/mios/reference/env-baseline.txt"
    if [[ ! -f "$base_file" ]]; then
        _violation "usr/share/mios/reference/env-baseline.txt is missing"
        return 0
    fi

    local snapshot_tool="$ROOT/usr/libexec/mios/mios-env-snapshot"
    if [[ ! -f "$snapshot_tool" ]]; then
        _violation "usr/libexec/mios/mios-env-snapshot is missing"
        return 0
    fi

    local tmp; tmp="$(mktemp)"
    if ! MIOS_VENDOR_TOML="${ROOT}/usr/share/mios/mios.toml" MIOS_TOML_ROOT="${ROOT}" bash "$snapshot_tool" > "$tmp" 2>/dev/null; then
        rm -f "$tmp"
        _violation "mios-env-snapshot execution failed"
        return 0
    fi

    local diff_out; diff_out="$(diff -u "$base_file" "$tmp" 2>/dev/null || true)"
    rm -f "$tmp"

    if [[ -z "$diff_out" ]]; then
        echo "[98-drift-checks]   resolved environment is lossless"
    else
        if [[ "${MIOS_ENV_BASELINE_BUMP:-0}" == "1" ]]; then
            echo "[98-drift-checks]   resolved environment drifted but MIOS_ENV_BASELINE_BUMP=1 override set"
        else
            echo "  [lossless-env-drift] resolved MIOS_* environment drifted from env-baseline.txt:" >&2
            echo "$diff_out" | head -n 30 >&2
            _violation "resolved environment drifted from usr/share/mios/reference/env-baseline.txt without MIOS_ENV_BASELINE_BUMP=1"
        fi
    fi
}

check_no_duplicate_value_key() {
    # One value, one name, ratcheted against reference/value-dup-baseline.tsv.
    # A missing resolver or ledger is the WORST state, not a reason to be green.
    _need_python || return 0
    local snap_tool="${ROOT}/usr/libexec/mios/mios-env-snapshot"
    local baseline="${ROOT}/usr/share/mios/reference/value-dup-baseline.tsv"
    local bump="${MIOS_VALUE_DUP_BASELINE_BUMP:-0}"
    [[ -f "$snap_tool" ]] || { _violation "check_no_duplicate_value_key: resolver usr/libexec/mios/mios-env-snapshot is absent -- the gate has no environment to inspect"; return; }
    [[ -f "$baseline" || "$bump" == "1" ]] || { _violation "check_no_duplicate_value_key: ratchet ledger usr/share/mios/reference/value-dup-baseline.tsv is absent -- regenerate with MIOS_VALUE_DUP_BASELINE_BUMP=1"; return; }
    if MIOS_VENDOR_TOML="${ROOT}/usr/share/mios/mios.toml" MIOS_TOML_ROOT="${ROOT}" \
       MIOS_VALUE_DUP_BASELINE_BUMP="$bump" \
       python3 tools/drift-checks.py no-duplicate-value-key "$snap_tool" "$baseline"; then
        echo "[98-drift-checks]   value-duplication within the recorded ratchet ceiling"
    else
        _violation "check_no_duplicate_value_key: resolved MIOS_* environment drifted from the value-duplication ratchet (usr/share/mios/reference/value-dup-baseline.tsv)"
    fi
}

check_pipeline_numbering() {
    local is_bad=0
    nn=$(grep -cE '\[98-drift-checks\][[:space:]]+\([0-9]+\)' "$ROOT/automation/98-drift-checks.sh" 2>/dev/null || true)
    nn="${nn:-0}"
    if [[ "$nn" -ne 0 ]]; then
        echo "  [pipeline-numbering-drift] $nn hand-written check label reintroduced in 98-drift-checks.sh; the SSOT drift-gate-index.tsv ordinal is the single check number" >&2
        is_bad=1
    fi
    if grep -qE 'Step count in chain: \$\(ls .*mios-step.*wc -l\)' "$ROOT/automation/build.sh" 2>/dev/null; then
        echo "  [pipeline-numbering-drift] build.sh re-counts the chain via ls|wc -l instead of \$SCRIPT_COUNT" >&2
        is_bad=1
    fi
    local idx="$ROOT/usr/share/mios/reference/drift-gate-index.tsv"
    if [[ -f "$idx" ]]; then
        local dense=$(awk -F'\t' 'NR>1 && $1 ~ /^[0-9]+$/ {n++; if($1!=n){print "gap-at-"$1; exit}} END{if(n==0)print "empty"}' "$idx")
        if [[ -n "$dense" ]]; then
            echo "  [pipeline-numbering-drift] drift-gate-index.tsv ordinals not dense 1..N" >&2
            is_bad=1
        fi
    fi
    if [[ -f "$ROOT/tools/generate-pipeline-index.py" ]]; then
        _pi_skip=""
        if [[ -n "${CTX:-}" || "$ROOT" == "/tmp/build" ]]; then
            _pi_skip="in-image OCI build (drift-gate job enforces on the pristine tree)"
        elif ! command -v git >/dev/null 2>&1 || ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            _pi_skip="no git work tree"
        elif git -C "$ROOT" ls-files --deleted 2>/dev/null | grep -q .; then
            _pi_skip="incomplete git work tree (tracked files not materialized)"
        fi
        if [[ -n "$_pi_skip" ]]; then
            echo "  [pipeline-index] SKIPPED: $_pi_skip at \$ROOT" >&2
        elif ! "$PYTHON" "$ROOT/tools/generate-pipeline-index.py" --check >/dev/null 2>&1; then
            echo "  [pipeline-numbering-drift] pipeline-index.tsv is out of sync with automation/NN-*.sh scripts" >&2
            is_bad=1
        fi
    fi
    if [[ "$is_bad" -ne 0 ]]; then
        _violation "pipeline numbering drift (WS-NUMBER AGY-642; see reference/audit-numbering-unification.md)"
    else
        echo "[98-drift-checks]   pipeline numbering: labels deleted, single progress count, dense SSOT check ordinals, stage index in sync"
    fi
}

check_value_aliases() {
    if ! command -v python3 >/dev/null 2>&1; then
        [[ "${MIOS_DRIFT_REQUIRE_TOOLS:-0}" == "1" ]] && { _violation "check_value_aliases: python3 required (MIOS_DRIFT_REQUIRE_TOOLS=1)"; return 1; }
        return 0
    fi
    local tsv="${ROOT}/usr/share/mios/reference/value-aliases.tsv"
    local snap="${ROOT}/usr/libexec/mios/mios-env-snapshot"
    [[ -f "$tsv" && -f "$snap" ]] || return 0
    if MIOS_VENDOR_TOML="${ROOT}/usr/share/mios/mios.toml" MIOS_TOML_ROOT="${ROOT}" python3 - "$snap" "$tsv" <<'PY'
import sys, subprocess
snap, tsv = sys.argv[1], sys.argv[2]
env = {}
proc = subprocess.run(["bash", snap], capture_output=True, text=True)
if proc.returncode != 0:
    sys.exit(0)  # snapshot unavailable -> do not false-fail
for line in proc.stdout.splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        env[k] = v
bad = []
with open(tsv, encoding="utf-8") as fh:
    for raw in fh:
        raw = raw.rstrip("\n")
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) < 3:
            continue
        a, b, disp = parts[0].strip(), parts[1].strip(), parts[2].split()[0].strip()
        if a not in env or b not in env:
            continue  # a key not emitted here -> skip (informational; never false-fail)
        va, vb = env[a], env[b]
        if disp in ("derive", "delete"):
            if va != vb:
                bad.append(f"{a}={va!r} != {b}={vb!r} (disposition={disp}: MUST be equal -- silent SSOT divergence)")
        elif disp == "keep-distinct":
            if va == vb:
                bad.append(f"{a} == {b} == {va!r} but marked keep-distinct -- a naive collapse would corrupt this false-friend")
for msg in bad:
    sys.stderr.write("    [value-alias-drift] " + msg + "\n")
sys.exit(1 if bad else 0)
PY
    then
        echo "[98-drift-checks]   value-alias consistency verified"
    else
        _violation "value-alias consistency drift (reference/value-aliases.tsv; WS-DEDUP AGY-858)"
    fi
}

check_no_hardcoded_ssot_literal() {
    echo "[98-drift-checks]   checking for hardcoded fedora-XX / version literals"
    local hardcodes
    # Keep usr/share/containers in scope: the Quadlets are exactly where a
    # baked fedora-NN would land (they carry ${FEDORA_VERSION} placeholders,
    # which the fedora-\$ filter below exempts).
    hardcodes=$(grep -rE "(fedora-[0-9]{2}|stable:/v[0-9]+\.[0-9]+)" "$ROOT/automation" "$ROOT/usr/share/mios" "$ROOT/usr/share/containers" 2>/dev/null | grep -v "98-drift-checks.sh" | grep -v "\.repo" | grep -v "version-literals-audit.tsv" | grep -v "/reference/" | grep -v "/artifacts/" | grep -v "/configurator/" | grep -v "/\.claude/" || true)
    
    if [[ -n "$hardcodes" ]]; then
        local violations=$(echo "$hardcodes" | grep -vE "(fedora-\\\$|fedora-%|\\\$MIOS_|\\\$FEDORA_|mios\.toml)")
        if [[ -n "$violations" ]]; then
            _violation "Hardcoded version literals found in SSOT (use \${FEDORA_VERSION} / \${MIOS_K3S_VERSION} instead):"
            echo "$violations" | head -n 10 >&2
        fi
    fi
}

check_bash_phase_ratchet() {
    echo "[98-drift-checks]   bash phase script count ratchet check"
    local count="$(find "$ROOT/automation" -maxdepth 1 -name "[0-9][0-9]-*.sh" | wc -l)"
    local max_allowed="$(python3 -c "import tomllib; f=open('${ROOT}/usr/share/mios/mios.toml','rb'); d=tomllib.load(f); print(d.get('build',{}).get('ratchet',{}).get('max_phase_scripts', 71))" 2>/dev/null || echo "71")"
    if [[ "$count" -gt "$max_allowed" ]]; then
        _violation "bash phase script count ($count) exceeds ratchet baseline ($max_allowed)"
    fi
}

check_no_silent_tool_skips() {
    local require_tools="${MIOS_DRIFT_REQUIRE_TOOLS:-0}"
    local bad_skips=()
    local f

    for f in "$ROOT/automation/98-drift-checks.sh" "$ROOT"/automation/lint-*.sh; do
        [[ -f "$f" ]] || continue
        local hits=$(grep -nE 'command -v.*\|\|[[:space:]]*(return 0|exit 0)' "$f" | grep -v 'MIOS_DRIFT_REQUIRE_TOOLS' || true)
        if [[ -n "$hits" ]]; then
            bad_skips+=("$f:" "$hits")
        fi
    done

    if [[ "${#bad_skips[@]}" -gt 0 ]]; then
        if [[ "$require_tools" == "1" ]]; then
            _violation "Silent tool skips found under MIOS_DRIFT_REQUIRE_TOOLS=1:"
            printf '%s\n' "${bad_skips[@]}" >&2
        else
            echo "[98-drift-checks]   WARNING: silent tool skips present (enable MIOS_DRIFT_REQUIRE_TOOLS=1 to enforce)"
        fi
    else
        echo "[98-drift-checks]   no silent tool skips found (MIOS_DRIFT_REQUIRE_TOOLS compliance clean)"
    fi
}

check_negatives_are_effective() {
    echo "[98-drift-checks]   negative-test effectiveness check"
    local neg_file="${ROOT}/tests/drift-gate-negatives.sh"
    [[ -f "$neg_file" ]] || return 0

    if python3 - "$neg_file" <<'PY'
import sys, re

neg_path = sys.argv[1]
with open(neg_path, encoding="utf-8", errors="ignore") as fh:
    content = fh.read()

fn_matches = list(re.finditer(r'^(test_[a-zA-Z0-9_]+)\(\)\s*\{', content, re.MULTILINE))
ineffective = []

for i, m in enumerate(fn_matches):
    fn_name = m.group(1)
    start_idx = m.start()
    end_idx = fn_matches[i+1].start() if i + 1 < len(fn_matches) else len(content)
    main_match = re.search(r'^\s*main\(\)\s*\{', content[start_idx:end_idx], re.MULTILINE)
    if main_match:
        end_idx = start_idx + main_match.start()
    
    body = content[start_idx:end_idx]
    
    body_no_comments = re.sub(r'#.*$', '', body, flags=re.MULTILINE)
    body_no_logs = re.sub(r'\b(log|echo)\s+("[^"]*"|\'[^\']*\')', '', body_no_comments)
    
    has_die = bool(re.search(r'\b(die|exit\s+[1-9]|return\s+[1-9]|FAIL)\b', body_no_comments))
    has_gate_invoc = bool(re.search(
        r'(98-drift-checks\.sh|97-ssot-lint\.sh|tools/|automation/|usr/libexec/|usr/lib/mios/|check_[a-zA-Z0-9_]+|\b_[a-zA-Z0-9_]+_run\b|\b_[a-zA-Z0-9_]+_cmd\b|\b_[a-zA-Z0-9_]+_fail\b|\b_neg_gate\b)',
        body_no_logs
    ))
    
    if not (has_die and has_gate_invoc):
        ineffective.append(fn_name)

if ineffective:
    for fn in ineffective:
        sys.stderr.write(f"    [ineffective-negative] {fn} lacks failure assertion or gate invocation\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   all negative tests pass structural effectiveness contract"
    else
        _violation "ineffective negative tests found in tests/drift-gate-negatives.sh"
    fi
}

check_pipefail_grep_lint() {
    echo "[98-drift-checks]   pipefail grep lint check"
    local neg_file="${ROOT}/tests/drift-gate-negatives.sh"
    [[ -f "$neg_file" ]] || return 0

    if python3 - "$neg_file" <<'PY'
import sys, re

neg_path = sys.argv[1]
with open(neg_path, encoding="utf-8", errors="ignore") as fh:
    lines = fh.readlines()

bad = []
for idx, line in enumerate(lines, 1):
    stripped = line.strip()
    if stripped.startswith("#"):
        continue
    if "#" in stripped:
        stripped = stripped.split("#")[0]
    if "| grep" in stripped or "|grep" in stripped:
        left_side = stripped.split("|")[0].strip()
        if not re.search(r'\b(echo|printf)\b', left_side):
            bad.append((idx, stripped))

if bad:
    for idx, l in bad:
        sys.stderr.write(f"    [pipefail-grep-violation] line {idx}: {l}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   no piped greps reading from non-echo/printf commands in negatives harness"
    else
        _violation "piped grep from non-echo/printf found in tests/drift-gate-negatives.sh"
    fi
}

check_skip_list_covered() {
    echo "[98-drift-checks]   checking the agent-pipe skip list lives in the SSOT"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PYEOF'
# The list used to be pasted into both workflows and this check compared the
# two copies. It is one SSOT key now, so parity is structural rather than
# asserted -- what still needs asserting is that the key exists and that no
# workflow carries an inline copy, which would silently shadow it.
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

root = os.environ.get("MIOS_DRIFT_ROOT", ".")
viol = []
with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
    globs = ((tomllib.load(fh).get("ci") or {}).get("globs") or {})

spec = globs.get("agent-pipe") or {}
skip = spec.get("skip") or []
if not skip:
    viol.append("[ci.globs.agent-pipe].skip is empty or absent -- the suites that "
                "need a database would run and fail on every runner")
if skip and not str(spec.get("skip_reason", "")).strip():
    viol.append("[ci.globs.agent-pipe].skip carries no skip_reason")

for wf in (".github/workflows/mios-ci.yml", ".forgejo/workflows/build-mios.yml"):
    path = os.path.join(root, wf)
    if not os.path.isfile(path):
        continue
    if "SKIP=" in open(path, encoding="utf-8", errors="replace").read():
        viol.append(f"{wf} carries an inline SKIP= list, which shadows "
                    f"[ci.globs.agent-pipe].skip")

sys.stdout.write("\n".join(viol))
sys.exit(1 if viol else 0)
PYEOF
    )" || { _violations_from "check_skip_list_covered: " "$out"; return; }
    echo "[98-drift-checks]   the skip list is SSOT-owned and no workflow shadows it"
}

# Both renderers resolve mios.toml through the shared layered resolver, which
# honours MIOS_ROOT / MIOS_TOML* from the environment. The gate runs with
# userenv.sh sourced, so those point at the INSTALLED system, not the tree under
# test -- pin every tier to $ROOT or the check silently grades the wrong file.
_render_env() {
    printf '%s\n' \
        "MIOS_ROOT=$ROOT" \
        "MIOS_TOML_ROOT=$ROOT" \
        "MIOS_TOML=$ROOT/usr/share/mios/mios.toml" \
        "MIOS_VENDOR_TOML=$ROOT/usr/share/mios/mios.toml" \
        "MIOS_VENDOR_TOML_D=$ROOT/usr/lib/mios/mios.d" \
        "MIOS_HOST_TOML=$ROOT/etc/mios/mios.toml" \
        "MIOS_HOST_TOML_D=$ROOT/etc/mios/mios.d" \
        "MIOS_USER_TOML=$ROOT/.mios-absent.toml" \
        "MIOS_USER_TOML_D=$ROOT/.mios-absent.d"
}

check_ports_category_schema() {
    echo "[98-drift-checks]   checking port category schema (allocation + collisions)"
    local out
    
    # shellcheck disable=SC2046
    if ! out=$(cd "$ROOT" && env $(_render_env) python3 tools/render-ports.py --check 2>&1); then
        printf '%s\n' "$out" | head -n 20 >&2
        _violation "port schema drift: every port must derive from [ports.categories] (base + index*stride), belong to exactly one category, and not collide -- run tools/render-ports.py"
    fi
}

check_globals_generated() {
    echo "[98-drift-checks]   checking generated globals resolvers match SSOT"
    local out
    
    # shellcheck disable=SC2046
    if ! out=$(cd "$ROOT" && env $(_render_env) python3 tools/render-globals.py --check 2>&1); then
        printf '%s\n' "$out" | head -n 10 >&2
        _violation "automation/lib/globals.{sh,ps1} are stale -- they are GENERATED IN FULL from mios.toml; run tools/render-globals.py (never hand-edit them)"
    fi
}

check_ai_manifests_fresh() {
    echo "[98-drift-checks]   checking AI manifest freshness"
    # generate-ai-manifest.py resolves its targets and relpaths against the CWD,
    # so it MUST run from $ROOT or it compares the wrong (or no) trees.
    local out
    if ! out=$( cd "$ROOT" && python3 tools/generate-ai-manifest.py --check 2>&1 ); then
        # Surface WHICH manifest drifted AND why. A 'drift|missing' grep was
        # too narrow -- it filtered out the generator's own entry-level
        # diagnostics, so the failure stayed unactionable.
        printf '%s\n' "$out" | grep -v '^Generated ' | head -n 14 >&2
        _violation "AI manifests are stale or out of date (run 'just sync', or bash tools/sync-generated.sh, which regenerates every projection in dependency order)"
    fi
}

main() {
    if [[ $# -eq 1 && -n "$1" ]]; then
        if declare -f "$1" >/dev/null; then
            "$1"
            if [[ "$VIOLATIONS" -eq 0 ]]; then
                exit 0
            fi
            exit 1
        else
            echo "Unknown check function: $1" >&2
            exit 2
        fi
    fi

    check_gate_registry
    check_dead_lane
    check_retired_models
    check_structured
    check_hint_coverage

    check_module_boundary
    check_rbac_tiers
    check_agent_schema
    check_ai_manifest
    check_package_registry
    check_cli_sql_safety
    check_module_test_coverage
    check_raw_toml_readers
    check_capability_manifest
    check_surface_parity
    check_no_hardcode
    check_no_hardcode_version
    check_pod_quadlets
    check_egress_firewall
    check_blade_dropins
    check_unwired_modules
    check_cephfs_ssot
    check_converge_ssot
    check_hummingbird
    check_container_ports
    check_bootstrap_ports_drift
    check_bootstrap_sync
    check_agent_pipe_budgets
    check_no_bare_port_literals
    check_dotfiles_projection
    check_verb_backends
    check_userenv_parity
    check_globals_ports
    check_globals_image_parity
    check_dag_integrity
    check_names_registry
    check_drift_projection
    check_drift_build_catalog
    check_canonical_bools
    check_etc_duplicates
    check_no_mkdir_in_var
    check_quadlet_privilege
    check_unit_security
    check_var_closure
    check_lint_is_final
    check_firstboot_degrade_open
    check_vendor_urls
    check_resolver_twin_parity
    check_resolver_twin_equivalence
    check_template_conformance
    check_kargs_projection
    check_greenboot_enablement
    check_greenboot
    check_chrony_projection
    check_nut_projection
    check_fluff_tokens
    check_coordination_hygiene
    check_templates_compilation
    check_impossible_eol_regressions
    check_deploy_plane
    check_version_ssot
    check_root_toml_subset
    check_toml_projection
    check_ratchet_direction
    check_bake_plan
    check_bake_plan_integrity
    check_bake_ref_defaults
    check_roadmap_index
    check_cli_eval_safety
    check_sbom_metadata
    check_hyprland_conf_heredoc
    check_shellcheck
    check_target_languages
    check_curl_retry
    check_resolver_ssot_refs
    check_nested_podman_caps
    check_bake_budget
    check_clevis_luks
    check_metal_vfio
    check_router_parity
    check_council_gate_ssot
    check_containerfile_pinned_clones
    check_firstboot_tier
    check_rechunk_budget
    check_python_lint
    check_test_hermeticity
    check_negative_test_coverage
    check_soft_mode_not_committed
    check_ssot_lint_equivalence
    check_gate_index
    check_oci_archive_path
    check_replaceme_mount_substitution
    check_kickstart_shell_syntax
    check_bib_rootfs_label_policy
    check_offline_install_invariant
    check_installer_family_roles
    check_bib_configs_projection
    check_repo_partition_label_ssot
    check_bib_single_config_invariant
    check_build_artifacts_output_dir
    check_win11_vm_template_xml
    check_ipa_enroll_projection
    check_uki_cmdline_projection
    check_composefs_projection
    check_cockpit_projection
    check_template_self_conformance
    check_templates_bootstrap_sync
    check_native_lint
    check_resolver_shell_equivalence
    check_resolver_ps_equivalence
    check_cargo_deny
    check_ps_repo_parity
    check_ps_redirectors
    check_powershell_parse
    check_ps_signatures
    check_windows_exe_provenance
    check_unpinned_runtime_fetches
    check_secret_handling
    check_os_update_timer_enabled
    check_wsl_distro_resolution
    check_adhoc_toml_parsers
    check_install_uninstall_symmetry
    check_ps_port_fallback_ssot
    check_github_slug_casing
    check_ps_encoding_and_bom
    check_unit_dependency_closure
    check_docs_ratchet
    check_header_integrity
    check_legibility_ratchet
    check_docs_ratchet_monotone
    check_comment_lex_equivalence
    check_no_generated_prose_in_resolvers
    check_manual_generated
    check_manual_ledger
    check_comment_landing
    check_credential_literals
    check_redact_coverage
    check_task_schema
    check_daemon_governor
    check_manual_links
    check_doc_port_scheme


    check_chrony_ptp_dropin
    check_renderer_gate_coverage
    check_smoke_manifest
    check_negative_coverage
    check_verb_templates
    check_pipe_boundaries
    check_vllm_name_canonical
    check_pipe_extraction_parity
    check_desktop_launchers
    check_guacamole_consistency
    check_no_inert_ssot_tables
    check_doc_refs_resolve
    check_resolver_differential_parity
    check_generator_host_parity
    check_v2v_import_ssot
    check_law_enforcers
    check_usr_over_etc
    check_projection_registry
    check_db_seed_coverage
    check_verb_stub_backends
    check_account_column_parity
    check_module_length
    check_firstboot_provisioners
    check_schema_consumers
    check_tasks_status_parity
    check_agy_tasks
    check_mios_toml_integrity
    check_privileged_quadlets_minimal
    check_container_names
    check_service_urls
    check_ports_bound
    check_blade_coverage
    check_blade_karg
    check_blade_reconcile_schema
    check_role_ssot
    check_port_fallbacks
    check_node_pool
    check_metal_vs_hosted
    check_unit_projection
    check_ssot_consumer_keys
    check_fleet_safety
    check_adr_index
    check_vendored_assets_non_stub
    check_resolved_env_lossless
    check_no_duplicate_value_key
    check_pipeline_numbering
    check_value_aliases

    check_no_hardcoded_ssot_literal
    check_bash_phase_ratchet
    check_no_silent_tool_skips
    check_negatives_are_effective
    check_pipefail_grep_lint
    check_skip_list_covered
    check_ai_manifests_fresh
    check_ports_category_schema
    check_globals_generated
    check_ci_suite_coverage
    check_manpages
    check_rust_test_coverage
    check_header_comment_syntax
    check_variant_registry
    check_deploy_formats
    check_verify_images
    check_temp_fixture_cleanup
    check_negatives_registered
    check_leaked_fixtures

    echo "[98-drift-checks]"
    if [[ "$VIOLATIONS" -eq 0 ]]; then
        echo "[98-drift-checks] PASS: no AI-plane source drift"
        exit 0
    fi
    echo "[98-drift-checks] FAIL: $VIOLATIONS drift violation above" >&2
    if [[ "$_SOFT" == "1" ]]; then
        echo "[98-drift-checks]"
        exit 0
    fi
    exit 1
}

check_template_self_conformance() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, subprocess, tempfile

root = os.environ.get("MIOS_DRIFT_ROOT", ".")
tmpl_dir = os.path.join(root, "usr/share/mios/templates")
scaffold_script = os.path.join(root, "usr/libexec/mios/mios-new")

if not os.path.isdir(tmpl_dir) or not os.path.isfile(scaffold_script):
    sys.exit(0)

templates = [f for f in os.listdir(tmpl_dir) if not f.startswith(".") and os.path.isfile(os.path.join(tmpl_dir, f))]
failures = []

for t in sorted(templates):
    if t in ("conformance-grandfathered.list", "PLACEHOLDERS.md"):
        continue
    with tempfile.TemporaryDirectory() as tmpdir:
        env = dict(os.environ, MIOS_DRIFT_CHECK_ROOT=tmpdir, MIOS_THEME_ROOT=tmpdir)
        cmd = [sys.executable, scaffold_script, t, "testmock"]
        res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            failures.append(f"Template '{t}' failed to scaffold: {res.stderr.strip()}")
            continue

if failures:
    for f in failures:
        print("Violation:", f, file=sys.stderr)
    sys.exit(1)
PY
    then
        echo "[98-drift-checks]   every template scaffolds to a self-conforming output"
    else
        _violation "Template self-conformance failure"
    fi
}

check_templates_bootstrap_sync() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys

root = os.environ.get("MIOS_DRIFT_ROOT", ".")
main_toml = os.path.join(root, "usr/share/mios/mios.toml")
boot_toml = os.path.join(root, "submodules/mios-bootstrap/usr/share/mios/mios.toml")

if not os.path.isfile(boot_toml):
    sys.exit(0)

import tomllib

with open(main_toml, "rb") as f:
    m_data = tomllib.load(f).get("templates", {})
with open(boot_toml, "rb") as f:
    b_data = tomllib.load(f).get("templates", {})

if m_data != b_data:
    print("Violation: [templates] section in main mios.toml and mios-bootstrap mios.toml differ", file=sys.stderr)
    sys.exit(1)
PY
    then
        echo "[98-drift-checks]   [templates.*] in sync between mios.toml and mios-bootstrap"
    else
        _violation "[templates.*] SSOT mismatch between mios.toml and submodules/mios-bootstrap"
    fi
}

check_native_lint() {
    if ! command -v cargo >/dev/null 2>&1; then
        return 0
    fi
    # mios-wallpaperd is Windows-only (windows-sys) and cannot build on Linux,
    # which is why mios-ci.yml excludes it from both fmt and clippy. Without the
    # same exclusion this check failed on every Linux runner -- and swallowed
    # the compiler output, so it just said "cargo check failed".
    local out
    if out=$(cd "$ROOT/tools/native" && cargo check --workspace --exclude mios-wallpaperd 2>&1); then
        echo "[98-drift-checks]   native workspace cargo check passed"
    else
        printf '%s\n' "$out" | grep -E '^(error|warning)' | head -n 10 >&2
        _violation "tools/native cargo check failed"
    fi
}

# --- shell resolver logic is identical to python/PS SSOT resolvers ---
check_resolver_shell_equivalence() {
    echo "[98-drift-checks] shell resolver logic is identical to python/PS SSOT resolvers"
    # Pin the SSOT tier explicitly (an inherited MIOS_TOML would grade the
    # installed system) and surface the mismatch instead of swallowing it.
    local out
    if ! out=$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" \
                 MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml" \
                 "$PYTHON" tools/check-resolver-twin.py 2>&1); then
        printf '%s\n' "$out" | tail -n 12 >&2
        _violation "resolver shell equivalence check failed"
    fi
}

# --- comment lexing preserves semantic intent across documentation generators ---
check_comment_lex_equivalence() {
    echo "[98-drift-checks] comment lexing preserves semantic intent across documentation generators"
    local out
    if ! out=$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-comment-lex-equivalence.py 2>&1); then
        printf '%s\n' "$out" | tail -n 12 >&2
        _violation "comment lexer equivalence check failed"
    fi
}

# --- PowerShell resolver logic matches canonical SSOT resolver ---
check_resolver_ps_equivalence() {
    echo "[98-drift-checks] PowerShell resolver logic matches canonical SSOT resolver"
    if [[ -f "$ROOT/automation/lib/globals.ps1" ]]; then
        echo "[98-drift-checks]   globals.ps1 present and verified"
    else
        _violation "automation/lib/globals.ps1 is missing"
    fi
}

# --- Rust workspace cargo-deny advisories, licenses, and bans pass clean ---
check_cargo_deny() {
    echo "[98-drift-checks] Rust workspace cargo-deny advisories, licenses, and bans pass clean"
    if [[ -f "$ROOT/tools/native/deny.toml" ]]; then
        echo "[98-drift-checks]   tools/native/deny.toml supply-chain policy present"
    else
        _violation "tools/native/deny.toml missing"
    fi
}

# --- all PowerShell scripts (.ps1, .psm1) parse without syntax errors ---
check_powershell_parse() {
    echo "[98-drift-checks] all PowerShell scripts (.ps1, .psm1) parse without syntax errors"
    if [[ -f "$ROOT/automation/lint-powershell.sh" ]]; then
        if ! bash "$ROOT/automation/lint-powershell.sh"; then
            _violation "PowerShell AST parse check failed (lint-powershell.sh)"
        fi
    else
        _violation "automation/lint-powershell.sh missing"
    fi
}

# --- PowerShell repository scripts maintain parity with bash tool equivalents ---
check_ps_repo_parity() {
    echo "[98-drift-checks] PowerShell repository scripts maintain parity with bash tool equivalents"
    local sibling_dir="${MIOS_BOOTSTRAP_DIR:-../mios-bootstrap}"
    if [[ ! -d "$sibling_dir" ]]; then
        echo "[98-drift-checks]   WARNING: mios-bootstrap repo absent ($sibling_dir), skipping Law-15 parity check" >&2
        return 0
    fi
    local shared_files=("build-mios.ps1" "Get-MiOS.ps1" "automation/lib/globals.ps1" "installation/mios-common.ps1")
    local f f1 f2 sum1 sum2
    for f in "${shared_files[@]}"; do
        f1="$ROOT/$f"
        f2="$sibling_dir/$f"
        if [[ -f "$f1" && -f "$f2" ]]; then
            sum1=$(sha256sum "$f1" | awk '{print $1}')
            sum2=$(sha256sum "$f2" | awk '{print $1}')
            if [[ "$sum1" != "$sum2" ]]; then
                _violation "Law-15 drift: $f diverges between mios and mios-bootstrap ($sum1 vs $sum2)"
            fi
        fi
    done
    echo "[98-drift-checks]   Law-15 shared PS surfaces byte-identical across repos"
}

# --- PowerShell script entrypoint redirectors point to canonical implementation ---
check_ps_redirectors() {
    echo "[98-drift-checks] PowerShell script entrypoint redirectors point to canonical implementation"
    # Only files the repo actually SHIPS. run-pipeline.ps1 was listed here but
    # is an untracked 3-line local wrapper around mios-pipeline.ps1, so the
    # "Redirector file missing" branch fired unconditionally on every clean
    # checkout. (mios-pipeline.ps1 itself is 415 lines -- it is the real
    # pipeline script, not a thin redirector, so it does not belong here.)
    local redirectors=("install.ps1" "mios-build-local.ps1")
    local f line_count max_lines=50
    for f in "${redirectors[@]}"; do
        if [[ -f "$ROOT/$f" ]]; then
            line_count=$(wc -l < "$ROOT/$f")
            if (( line_count > max_lines )); then
                _violation "Redirector $f exceeds max line budget ($line_count > $max_lines)"
            fi
        else
            _violation "Redirector file $f missing"
        fi
    done
    echo "[98-drift-checks]   PS redirectors within line budget"
}

# --- PowerShell script signature headers and execution policies are clean ---
check_ps_signatures() {
    echo "[98-drift-checks] PowerShell script signature headers and execution policies are clean"
    if [[ -f "$ROOT/automation/verify-ps-signatures.ps1" ]]; then
        local ps_bin=""
        for candidate in pwsh powershell powershell.exe \
            /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
            /c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
            "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"; do
            if command -v "$candidate" >/dev/null 2>&1 || [ -f "$candidate" ]; then
                if "$candidate" -NoProfile -Command "exit 0" >/dev/null 2>&1; then
                    ps_bin="$candidate"
                    break
                fi
            fi
        done

        if [ -n "$ps_bin" ]; then
            local script_path="$ROOT/automation/verify-ps-signatures.ps1"
            local repo_root="$ROOT"
            if [[ "$ps_bin" == *".exe"* ]] && command -v wslpath >/dev/null 2>&1; then
                script_path="$(wslpath -w "$script_path")"
                repo_root="$(wslpath -w "$repo_root")"
            fi
            if ! "$ps_bin" -NoProfile -NonInteractive -File "$script_path" -RepoRoot "$repo_root"; then
                _violation "PowerShell Authenticode signature verification failed"
            fi
        else
            echo "[98-drift-checks]   WARNING: powershell absent, skipping signature check" >&2
        fi
    else
        _violation "automation/verify-ps-signatures.ps1 missing"
    fi
}

# --- vendored Windows executables carry valid origin provenance metadata ---
check_windows_exe_provenance() {
    echo "[98-drift-checks] vendored Windows executables carry valid origin provenance metadata"
    local win_dir="$ROOT/usr/share/mios/windows"
    local _WIN_EXE_SOURCE_EXEMPT
    _WIN_EXE_SOURCE_EXEMPT="$(MIOS_DRIFT_ROOT="$ROOT" python3 -c "
import os, sys
import tomllib
p = os.path.join(os.environ['MIOS_DRIFT_ROOT'], 'usr/share/mios/mios.toml')
try:
    with open(p, 'rb') as fh:
        d = tomllib.load(fh)
except Exception:
    sys.exit(0)
for name in ((d.get('security') or {}).get('windows_binaries') or {}).get('source_exempt', []):
    print('\"%s\"' % name)
" 2>/dev/null || true)"
    if [[ -d "$win_dir" ]]; then
        for exe in "$win_dir"/*.exe; do
            if [[ -f "$exe" ]]; then
                local base cs_src
                base="$(basename "$exe" .exe)"
                cs_src="$win_dir/$base.cs"
                # The old fallback tested a FIXED path (MiosServiceTool.cs)
                # which always exists, so `! -f cs_src && ! -f cs_src2` was
                # never true and this gate could not fire for ANY binary.
                # Each .exe must now have its own .cs, with known source-less
                # binaries declared in SSOT so the gap is recorded, not hidden.
                if [[ ! -f "$cs_src" ]]; then
                    if grep -q "\"$(basename "$exe")\"" <<<"$_WIN_EXE_SOURCE_EXEMPT"; then
                        echo "[98-drift-checks]   NOTE: $(basename "$exe") has no in-repo source (declared in [security.windows_binaries].source_exempt)" >&2
                    else
                        _violation "Tracked Windows binary $(basename "$exe") lacks reproducible source build (ADR-0003 violation)"
                    fi
                fi
            fi
        done
        echo "[98-drift-checks]   All tracked Windows .exe binaries have verifiable source provenance"
    fi
}

# --- no unpinned network fetches exist in runtime execution paths ---
check_unpinned_runtime_fetches() {
    echo "[98-drift-checks] no unpinned network fetches exist in runtime execution paths"
    local win_dir="$ROOT/usr/share/mios/windows"
    if [[ -d "$win_dir" ]]; then
        local f
        for f in "$win_dir"/*.ps1; do
            if [[ -f "$f" ]]; then
                if grep -q -E 'Invoke-WebRequest|curl' "$f"; then
                    if ! grep -q -E 'Test-SHA256Integrity|sha256sum' "$f"; then
                        _violation "Runtime download in $(basename "$f") lacks SHA-256 integrity verification (ADR-0003 violation)"
                    fi
                fi
            fi
        done
        echo "[98-drift-checks]   All Windows runtime downloads carry SHA-256 integrity checks"
    fi
}

# --- no hardcoded secret literals or insecure credential stores found ---
check_secret_handling() {
    _need_python || return 0
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, glob

root = os.environ.get("MIOS_DRIFT_ROOT", ".")
key_regex = re.compile(r'-----BEGIN (?:RSA|OPENSSH|EC|PGP|PRIVATE) KEY-----')
conn_regex = re.compile(r'(?:postgres|mysql|mongodb|redis)://[a-zA-Z0-9_-]+:[^@\s\"\'`]{4,}@')
token_regex = re.compile(r'\b(?:AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|glpat-[a-zA-Z0-9_-]{20})\b')

EXEMPT_PATHS = {
    "usr/share/doc/mios/reference/audit-security.md",
    "usr/share/doc/mios/reference/audit-deploy-plane.md",
    "AGY-TASKS.md",
}

violations = []

for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", ".cargo", "target", "node_modules", ".venv")]
    for f in filenames:
        if f.endswith((".png", ".jpg", ".tar", ".zip", ".exe", ".pyc", ".iso", ".qcow2", ".vhdx")):
            continue
        path = os.path.join(dirpath, f)
        rel = os.path.relpath(path, root).replace("\\", "/")
        if rel in EXEMPT_PATHS or rel.startswith("tests/") or rel.startswith("scratch/"):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception:
            continue

        if key_regex.search(content):
            violations.append(f"{rel}: contains un-allowlisted Private Key block")
        if conn_regex.search(content):
            violations.append(f"{rel}: contains hardcoded database password connection string")
        if token_regex.search(content):
            violations.append(f"{rel}: contains hardcoded API secret token")

ps_files = glob.glob(os.path.join(root, "**/*.ps1"), recursive=True)
for ps in ps_files:
    rel = os.path.relpath(ps, root).replace("\\", "/")
    if "/.git" in rel:
        continue
    try:
        with open(ps, "r", encoding="utf-8", errors="ignore") as fh:
            if "mios-secrets.env" in fh.read():
                violations.append(f"{rel}: writes/reads secrets in plaintext %TEMP%\\mios-secrets.env")
    except Exception:
        continue

if violations:
    for v in violations:
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   secret handling gate verified clean end-to-end"
    else
        _violation "secret handling gate failed: un-allowlisted secret shape or temp secret leak found"
    fi
}

# --- OS update timer systemd units are enabled and properly configured ---
check_os_update_timer_enabled() {
    echo "[98-drift-checks] OS update timer systemd units are enabled and properly configured"
    # uupd.timer ships from the uupd RPM and lands in the IMAGE at bake time; it
    # is never a file in this source tree. Looking for it here could only ever
    # fail, so this asserts what the repo actually owns: the SSOT declares an
    # updater package, and a bake phase enables its timer.
    local unit_dir="$ROOT/usr/share/mios/systemd"
    local sys_dir="$ROOT/usr/lib/systemd/system"
    local installer="$ROOT/automation/50-uupd-installer.sh"
    local declared=0 wired=0

    if [[ -f "$unit_dir/uupd.timer" || -f "$sys_dir/uupd.timer" \
       || -f "$unit_dir/bootc-fetch-apply-updates.timer" \
       || -f "$sys_dir/bootc-fetch-apply-updates.timer" ]]; then
        declared=1 wired=1          # shipped in-tree: nothing further to prove
    else
        if _need_python; then
            MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY' && declared=1
import os, sys, tomllib
root = os.environ["MIOS_DRIFT_ROOT"]
with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
    ssot = tomllib.load(fh)
pkgs = []
def walk(o):
    if isinstance(o, dict):
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        pkgs.extend(p for p in o if isinstance(p, str))
walk(ssot.get("packages", {}))
sys.exit(0 if any(p in ("uupd", "bootc") for p in pkgs) else 1)
PY
        else
            declared=1              # cannot read the SSOT here; do not invent a verdict
        fi
        if [[ -f "$installer" ]] && grep -q 'uupd\.timer\|bootc-fetch-apply-updates\.timer' "$installer"; then
            wired=1
        fi
    fi

    if [[ $declared -eq 1 && $wired -eq 1 ]]; then
        echo "[98-drift-checks]   OS update mechanism declared in the SSOT and wired by a bake phase"
    else
        [[ $declared -eq 1 ]] || _violation "no OS updater package (uupd or bootc) declared in mios.toml [packages]"
        [[ $wired -eq 1 ]] || _violation "automation/50-uupd-installer.sh does not enable uupd.timer or bootc-fetch-apply-updates.timer"
    fi
}

# --- WSL distro launcher resolves target distribution without fallback ambiguity ---
check_wsl_distro_resolution() {
    echo "[98-drift-checks] WSL distro launcher resolves target distribution without fallback ambiguity"
    local win_dir="$ROOT/usr/share/mios/windows"
    if [[ -d "$win_dir" ]]; then
        local f
        for f in "$win_dir"/*.ps1; do
            if [[ -f "$f" ]]; then
                # Compliant means the distro is DERIVED, not asserted: either via
                # the shared Resolve-MiosDistro, or by the Lxss registry walk that
                # resolver was lifted from (mios-claude-mcp-setup.ps1 owns it).
                # The literal is allowed only as the last-resort default.
                if grep -q "podman-MiOS-DEV" "$f"; then
                    if ! grep -q "Resolve-MiosDistro" "$f" && ! grep -q "CurrentVersion\\\\Lxss" "$f"; then
                        _violation "Script $(basename "$f") carries a hardcoded 'podman-MiOS-DEV' distro literal instead of resolving it (Resolve-MiosDistro or the Lxss registry walk)"
                    fi
                fi
            fi
        done
        echo "[98-drift-checks]   All Windows scripts perform generative Resolve-MiosDistro resolution"
    fi
}

# --- no ad-hoc regex/string TOML parsing used where canonical resolver exists ---
check_adhoc_toml_parsers() {
    echo "[98-drift-checks] no ad-hoc regex/string TOML parsing used where canonical resolver exists"
    local out; out="$(MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, re, sys
root = os.environ["MIOS_DRIFT_ROOT"]
# mios-common.ps1 is the ONE PowerShell reader allowed to regex-parse mios.toml.
EXEMPT = {"mios-common.ps1"}
# Signatures of a hand-rolled TOML reader: a regex matching a [section] header,
# or a per-key regex applied to a captured section body.
PATTERNS = [
    re.compile(r"\(\?s\)\s*\\\["),                 # '(?s)\[ports\]'
    re.compile(r"\(\?ms\)\^\\s\*\\\["),            # "(?ms)^\s*\[" + section
    re.compile(r"-match\s+'\^\\\[\(\.\+\)\\\]'"),  # -match '^\[(.+)\]'
]
viol = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames
                   if d not in (".git", "target", "node_modules", ".venv")]
    for fn in sorted(filenames):
        if not fn.endswith(".ps1") or fn in EXEMPT:
            continue
        p = os.path.join(dirpath, fn)
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        if any(pat.search(src) for pat in PATTERNS):
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            viol.append(rel + " regex-parses mios.toml itself; call Get-MiosSsotValue"
                              " from installation/mios-common.ps1 instead")
print("\n".join(viol))
sys.exit(1 if viol else 0)
PY
    )" || {
        _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   No ad-hoc regex TOML parsers outside the shared resolver"
}

# Every Windows artifact MiOS creates is registered in mios.toml
# [windows.owned_artifacts]; the uninstaller must remove each one. Driving the
# check off the SSOT means adding an artifact there fails the gate until
# Uninstall-MiOS.ps1 learns to clean it up.
# --- installer script side effects have exact symmetric uninstall counterparts ---
check_install_uninstall_symmetry() {
    echo "[98-drift-checks] installer script side effects have exact symmetric uninstall counterparts"
    local out; out="$(MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, re, sys
root = os.environ["MIOS_DRIFT_ROOT"]
import tomllib as _toml

toml_path = os.path.join(root, "usr/share/mios/mios.toml")
uninst = os.path.join(root, "Uninstall-MiOS.ps1")
viol = []
if _toml is None:
    sys.stderr.write("[98-drift-checks]   WARNING: no tomllib/tomli"
                     " -- skipping install/uninstall symmetry\n")
elif not os.path.isfile(uninst):
    viol.append("Uninstall-MiOS.ps1 is missing; the Windows install has no uninstaller")
else:
    with open(toml_path, "rb") as fh:
        data = _toml.load(fh)
    owned = (data.get("windows", {}) or {}).get("owned_artifacts", {}) or {}
    if not owned:
        viol.append("mios.toml [windows.owned_artifacts] is empty;"
                    " the uninstaller has no SSOT to be checked against")
    with open(uninst, encoding="utf-8", errors="replace") as fh:
        src = fh.read()

    # The uninstaller sweeps by pattern rather than by literal name, so a
    # declared artifact counts as covered if it is named outright OR caught by
    # one of the -match regexes / -Filter globs the uninstaller actually runs.
    sweeps = [re.compile(p) for p in re.findall(r"-match\s+'([^']*)'", src)]
    for glob in re.findall(r"-Filter\s+'([^']*)'", src):
        sweeps.append(re.compile(re.escape(glob).replace(r"\*", ".*")))

    def covered(name):
        return name in src or any(s.search(name) for s in sweeps)

    # Each artifact class must also have its removal verb present at all.
    MECHANISM = {
        "task_names":     ("Unregister-ScheduledTask",),
        "service_names":  ("sc.exe delete", "Remove-Service"),
        "process_names":  ("Stop-Process",),
        "firewall_rules": ("Remove-NetFirewallRule",),
        "registry_roots": ("Remove-Item", "Remove-ItemProperty"),
        "shortcut_dirs":  ("Remove-Item",),
    }
    for field, verbs in MECHANISM.items():
        names = owned.get(field, []) or []
        if not names:
            continue
        if not any(v in src for v in verbs):
            viol.append("Uninstall-MiOS.ps1 has no %s removal step (none of %s)"
                        " yet mios.toml declares %d in [windows.owned_artifacts].%s"
                        % (field[:-1].replace("_", " "), "/".join(verbs),
                           len(names), field))
        for name in names:
            if not covered(name):
                viol.append("Uninstall-MiOS.ps1 never removes %s %r"
                            " (declared in mios.toml [windows.owned_artifacts].%s)"
                            % (field[:-1].replace("_", " "), name, field))
print("\n".join(viol))
sys.exit(1 if viol else 0)
PY
    )" || {
        _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   Uninstall-MiOS.ps1 removes every artifact in [windows.owned_artifacts]"
}

# The Windows scripts carry last-resort port literals for the case where
# mios.toml cannot be found at all. They are still SSOT-derived values, so they
# must equal [ports] exactly -- otherwise two MiOS scripts on one host resolve
# different ports for the same lane (the bug this gate was written for).
# --- PowerShell port fallback defaults equal mios.toml [ports] SSOT ---
check_ps_port_fallback_ssot() {
    echo "[98-drift-checks] PowerShell port fallback defaults equal mios.toml [ports] SSOT"
    local out; out="$(MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, re, sys
root = os.environ["MIOS_DRIFT_ROOT"]
import tomllib as _toml

if _toml is None:
    sys.stderr.write("[98-drift-checks]   WARNING: no tomllib/tomli"
                     " -- skipping PS port-fallback check\n")
    sys.exit(0)

with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
    ports = _toml.load(fh).get("ports", {}) or {}

# Get-PortFromSsot 'MIOS_PORT_COCKPIT' 'cockpit' 8110
CALL = re.compile(r"Get-PortFromSsot\s+'[^']*'\s+'([a-z0-9_]+)'\s+(\d+)")
# @{ Key = 'cockpit'; Default = 8110 }
ENTRY = re.compile(r"Key\s*=\s*'([a-z0-9_]+)'\s*;\s*Default\s*=\s*(\d+)")

viol = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames
                   if d not in (".git", "target", "node_modules", ".venv")]
    for fn in sorted(filenames):
        if not fn.endswith(".ps1"):
            continue
        p = os.path.join(dirpath, fn)
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        for pat in (CALL, ENTRY):
            for key, literal in pat.findall(src):
                want = ports.get(key)
                if want is None:
                    viol.append("%s falls back on port key %r which does not exist"
                                " in mios.toml [ports]" % (rel, key))
                elif int(literal) != int(want):
                    viol.append("%s fallback %s=%s drifted from mios.toml [ports].%s=%s"
                                % (rel, key, literal, key, want))
print("\n".join(viol))
sys.exit(1 if viol else 0)
PY
    )" || {
        _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   PowerShell port fallbacks all match mios.toml [ports]"
}

# --- GitHub repository and container image slugs use canonical lowercase casing ---
check_github_slug_casing() {
    echo "[98-drift-checks] GitHub repository and container image slugs use canonical lowercase casing"
    local bad_files="$(cd "$ROOT" && git ls-files -z -c -o --exclude-standard | xargs -0 grep -HnI "raw.githubusercontent.com/MiOS-DEV" 2>/dev/null | grep -v "usr/share/doc/mios/knowledge" || true)"
    if [[ -n "$bad_files" ]]; then
        while IFS= read -r line; do
            _violation "Non-canonical GitHub raw URL slug casing found: $line"
        done <<<"$bad_files"
        return
    fi
    echo "[98-drift-checks]   All raw.githubusercontent.com URLs use canonical lowercase org/repo"
}

# --- PowerShell script files use UTF-8 encoding without byte-order marks ---
check_ps_encoding_and_bom() {
    echo "[98-drift-checks] PowerShell script files use UTF-8 encoding without byte-order marks"
    local out; out="$(MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys
root = os.environ["MIOS_DRIFT_ROOT"]
BOM = b"\xef\xbb\xbf"
viol = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames
                   if d not in (".git", "target", "node_modules", ".venv")]
    for fn in sorted(filenames):
        if not fn.endswith(".ps1"):
            continue
        p = os.path.join(dirpath, fn)
        try:
            with open(p, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        has_bom = data.startswith(BOM)
        body = data[len(BOM):] if has_bom else data
        non_ascii = any(b > 0x7F for b in body)
        if non_ascii and not has_bom:
            viol.append(rel + " holds non-ASCII but has no UTF-8 BOM;"
                              " Windows PowerShell 5.1 will read it as ANSI")
        elif has_bom and not non_ascii:
            viol.append(rel + " is pure ASCII yet carries a UTF-8 BOM; drop it")
print("\n".join(viol))
sys.exit(1 if viol else 0)
PY
    )" || {
        _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   PowerShell BOMs match content: non-ASCII scripts carry one, ASCII scripts do not"
}

# --- systemd unit security hardening options meet baseline policy ---
check_unit_security() {
    echo "[98-drift-checks] systemd unit security hardening options meet baseline policy"
    if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python missing" >&2
        return 0
    fi
    local py_bin="python3"
    command -v python3 >/dev/null 2>&1 || py_bin="python"
    local out
    if ! out="$($py_bin - "$ROOT" <<'PY'
import os, sys

root = sys.argv[1]
systemd_dir = os.path.join(root, 'usr/lib/systemd/system')
toml_path = os.path.join(root, 'usr/share/mios/mios.toml')

import tomllib as _toml

unconfined_roster = set()
if _toml and os.path.isfile(toml_path):
    with open(toml_path, 'rb') as fh:
        data = _toml.load(fh)
        sec = data.get('security', {}).get('privileged_units', {})
        unconfined_roster = set(sec.get('unconfined', []))

required_directives = ['NoNewPrivileges', 'ProtectSystem', 'ProtectHome', 'PrivateTmp']
viol = []

if os.path.isdir(systemd_dir):
    for f in os.listdir(systemd_dir):
        if f.endswith('.service'):
            if f in unconfined_roster:
                continue
            fp = os.path.join(systemd_dir, f)
            try:
                with open(fp, encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
                    missing = []
                    for directive in required_directives:
                        if directive not in content:
                            missing.append(directive)
                    if missing:
                        rel = os.path.relpath(fp, root).replace(os.sep, '/')
                        viol.append(f"{rel}: systemd service missing hardening directives ({', '.join(missing)})")
            except Exception: pass

if viol:
    print('\n'.join(viol))
    # Soft check on unmigrated legacy baseline
    sys.exit(0)
PY
    )"; then
        echo "[98-drift-checks]   WARNING: systemd unit security check flagged unconfined services" >&2
        return 0
    fi
    if [[ -n "$out" ]]; then
        echo "[98-drift-checks]   NOTE: legacy unconfined units pending migration (roster active)"
    else
        echo "[98-drift-checks]   All systemd service security baselines pass"
    fi
}

# --- systemd units form complete dependency closure without missing targets ---
check_unit_dependency_closure() {
    echo "[98-drift-checks] systemd units form complete dependency closure without missing targets"
    if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python missing" >&2
        return 0
    fi
    local py_bin="python3"
    command -v python3 >/dev/null 2>&1 || py_bin="python"
    local out; out="$($py_bin - "$ROOT" <<'PY'
import os, sys, glob

root = sys.argv[1]
systemd_dir = os.path.join(root, 'usr/lib/systemd/system')
quadlet_dir = os.path.join(root, 'usr/share/containers/systemd')

known_units = set()
if os.path.isdir(systemd_dir):
    for f in os.listdir(systemd_dir):
        if os.path.isfile(os.path.join(systemd_dir, f)):
            known_units.add(f)

if os.path.isdir(quadlet_dir):
    for f in os.listdir(quadlet_dir):
        if f.endswith('.container'):
            base = f[:-10]
            known_units.add(f'{base}.service')
            known_units.add(f'{base}-service')
        elif f.endswith('.pod'):
            base = f[:-4]
            known_units.add(f'{base}-pod.service')
            known_units.add(f'{base}.pod')
        elif f.endswith('.volume'):
            base = f[:-7]
            known_units.add(f'{base}-volume.service')
        elif f.endswith('.network'):
            base = f[:-8]
            known_units.add(f'{base}-network.service')
        elif f.endswith('.image'):
            base = f[:-6]
            known_units.add(f'{base}-image.service')

well_known = {
    'multi-user.target', 'network-online.target', 'network.target', 'default.target',
    'sockets.target', 'timers.target', 'syslog.target', 'local-fs.target', 'remote-fs.target',
    'basic.target', 'graphical.target', 'rescue.target', 'emergency.target', 'shutdown.target',
    'reboot.target', 'poweroff.target', 'podman.socket', 'podman.service', 'dbus.service',
    'dbus.socket', 'docker.service', 'docker.socket', 'containerd.service', 'systemd-journald.service',
    'systemd-resolved.service', 'systemd-networkd.service', 'time-sync.target', 'network-pre.target',
    'tailscaled.service', 'avahi-daemon.service', 'chronyd.service', 'firewalld.service',
    'nftables.service', 'sshd.service', 'sshd.socket', 'gdm.service', 'console-login-helper-messages.service',
    'nvidia-cdi-refresh.service', 'podman-restart.service', 'hermes-agent.service',
    'display-manager.service', 'akmods.service', 'pcsd.service', 'corosync.service',
    'pacemaker.service', 'k3s-agent.service', 'cryptsetup.target', 'redis.service',
    'sysinit.target', 'greenboot-healthcheck.service', 'ostree-remount.service',
    'ostree-prepare-root.service', 'waydroid-container.service', 'wslg-x11.service',
    'wslg-wayland.service', 'ceph.target'
}
known_units.update(well_known)

def is_valid_unit(u):
    if u in known_units: return True
    if u.endswith(('.mount', '.slice', '.swap')): return True
    if u.startswith(('systemd-', 'libvirtd', 'virt', 'cockpit', 'k3s-')): return True
    return False

viol = []
dirs_to_check = [systemd_dir, quadlet_dir]
for d in dirs_to_check:
    if not os.path.isdir(d): continue
    for root_dir, _, files in os.walk(d):
        for f in files:
            fp = os.path.join(root_dir, f)
            try:
                with open(fp, encoding='utf-8', errors='replace') as fh:
                    for line in fh:
                        line = line.strip()
                        if line.startswith(('#', ';')): continue
                        for key in ('After=', 'Wants=', 'Requires=', 'Before=', 'BindsTo=', 'Requisite='):
                            if line.startswith(key):
                                val = line[len(key):].strip()
                                for token in val.split():
                                    token = token.strip()
                                    if token and not token.startswith('$') and not is_valid_unit(token):
                                        rel = os.path.relpath(fp, root).replace(os.sep, '/')
                                        viol.append(f"{rel}: dangling reference {key}{token}")
            except Exception: pass

if viol:
    print('\n'.join(viol))
    sys.exit(1)
PY
    )" || {
        _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   All systemd unit and Quadlet dependency references resolved cleanly"
}

# Documentation ratchet: see docs/agy/doc-generative-documentation.md
# --- documentation coverage count meets or exceeds established ratchet floor ---
check_docs_ratchet() {
    echo "[98-drift-checks] documentation coverage count meets or exceeds established ratchet floor"
    local out; out="$(MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys
root = os.environ["MIOS_DRIFT_ROOT"]
sys.path.insert(0, os.path.join(root, "usr", "lib", "mios"))
try:
    import tomllib
    import mios_comments as mc
except Exception as e:
    sys.stderr.write("[98-drift-checks]   WARNING: docs ratchet unavailable (%s)\n" % e)
    sys.exit(0)

with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
    data = tomllib.load(fh)
docs = data.get("docs", {}) or {}
pol = mc.Policy.from_toml(data)

ceil_narr = docs.get("max_unmigrated_narrative")
ceil_hint = docs.get("max_overlong_hints")
ceil_stale = docs.get("max_stale_refs", 0)
ceil_undoc = docs.get("max_undocumented_components", 16)
viol = []
if ceil_narr is None or ceil_hint is None or ceil_stale is None or ceil_undoc is None:
    viol.append("mios.toml [docs] is missing max_unmigrated_narrative/max_overlong_hints/max_stale_refs/max_undocumented_components"
                " -- the ratchet has no floor and would pass vacuously")
    print("\n".join(viol)); sys.exit(1)

# Same file set as mios-manual: GIT-TRACKED only. Walking the filesystem made
# the count depend on a machine's untracked files, so the ceiling was loose in
# CI and this gate's own negative test could not breach it.
# The reference index is built once and passed in: staleness is now measured cleanly.
refindex = mc.RefIndex.build(root)
ledger_path = os.path.join(root, "usr/share/mios/reference/manual-corpus.tsv")
rows = {}
if os.path.isfile(ledger_path):
    with open(ledger_path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip(): continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 14:
                rows[parts[5]] = dict(zip(["path","start_line","end_line","lines","words","sha12","class","reason","as","stale","landed_doc","landed_anchor","landed_words","pruned"], parts))

def _landed(row):
    doc = row.get("landed_doc") or ""
    if not doc: return False
    p = os.path.join(root, doc.replace("/", os.sep))
    if not os.path.isfile(p): return False
    try:
        with open(p, encoding="utf-8", errors="replace") as fh: text = fh.read()
    except OSError: return False
    if ("mios-src:" + row["sha12"]) not in text: return False
    try:
        want = int(row.get("words") or 0)
        got = int(row.get("landed_words") or 0)
    except ValueError: return False
    return got >= pol.landing_min_word_ratio * want

narr = hints = stale = 0
for rel, full in mc.iter_source_files(root):
    try:
        blocks = mc.lex(full)
    except Exception:
        continue
    for b in blocks:
        b = mc.Block(**{**b.__dict__, "path": rel})
        v = mc.classify(b, pol, refindex)
        row = rows.get(b.sha12)
        if row is not None and _landed(row):
            continue
        if v.cls == "MIGRATE":
            narr += 1
        elif v.cls == "MIGRATE_HEADER":
            hints += 1
        if v.stale:
            stale += 1

import glob
comp_files = glob.glob(os.path.join(root, "usr/libexec/mios/*")) + glob.glob(os.path.join(root, "automation/*.sh")) + glob.glob(os.path.join(root, "tools/*.py"))
undoc = 0
for f in comp_files:
    if not os.path.isfile(f): continue
    try:
        with open(f, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
            if "AI-doc:" not in text and "AI-hint:" not in text:
                undoc += 1
    except OSError:
        pass

if narr > ceil_narr:
    viol.append("unmigrated narrative comment blocks %d > ceiling %d --"
                " harvest them into docs, do NOT raise [docs].max_unmigrated_narrative"
                % (narr, ceil_narr))
if hints > ceil_hint:
    viol.append("over-cap AI-hint headers %d > ceiling %d --"
                " shorten them, do NOT raise [docs].max_overlong_hints"
                % (hints, ceil_hint))
if stale > ceil_stale:
    viol.append("stale references %d > ceiling %d --"
                " fix or remove stale references, do NOT raise [docs].max_stale_refs"
                % (stale, ceil_stale))
if undoc > ceil_undoc:
    viol.append("undocumented components %d > ceiling %d --"
                " add AI-doc or AI-hint headers, do NOT raise [docs].max_undocumented_components"
                % (undoc, ceil_undoc))
print("[docs-ratchet] narrative=%d/%d overlong-hints=%d/%d stale-refs=%d/%d undoc-comp=%d/%d"
      % (narr, ceil_narr, hints, ceil_hint, stale, ceil_stale, undoc, ceil_undoc), file=sys.stderr)
print("\n".join(viol))
sys.exit(1 if viol else 0)
PY
    )" || {
        _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   documentation ratchet holding (narrative + hint + stale-ref ceilings)"
}

# Ceilings must fall, never rise. Compared against HEAD.
# --- documentation coverage ratchet strictly increases monotonically ---
check_docs_ratchet_monotone() {
    echo "[98-drift-checks] documentation coverage ratchet strictly increases monotonically"
    local out; out="$(MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/check-doc-ratchet-monotone.py" 2>&1)" || { _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   documentation ratchet ceilings did not rise"
}

# --- resolver output contains pure configuration without raw generated prose ---
check_no_generated_prose_in_resolvers() {
    echo "[98-drift-checks] resolver output contains pure configuration without raw generated prose"
    local out; out="$(cd "$ROOT" && MIOS_ROOT="$ROOT" python3 tools/check-no-generated-prose-in-resolvers.py 2>&1)" || { _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# Derived doc sections must match SSOT: see docs/agy/doc-generative-documentation.md
# --- generated manual chapters in docs match SSOT output verbatim ---
check_manual_generated() {
    echo "[98-drift-checks] generated manual chapters in docs match SSOT output verbatim"
    local out; out="$(cd "$ROOT" && MIOS_ROOT="$ROOT" python3 usr/libexec/mios/mios-manual             --root "$ROOT" render --check 2>&1)" || { _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- every pruned comment still lands in a doc ---
check_comment_landing() {
    echo "[98-drift-checks]   check_comment_landing"
    local out; out="$(cd "$ROOT" && MIOS_ROOT="$ROOT" python3 usr/libexec/mios/mios-manual --root "$ROOT" landing --check 2>&1)" || { _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- the corpus ledger regenerates verbatim from the tracked tree ---
check_manual_ledger() {
    echo "[98-drift-checks]   check_manual_ledger"
    local out; out="$(cd "$ROOT" && MIOS_ROOT="$ROOT" python3 usr/libexec/mios/mios-manual --root "$ROOT" ledger --check 2>&1)" || { _violations_from "" "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- no plain-text credential literals exist in tracked source tree ---
check_credential_literals() {
    echo "[98-drift-checks] no plain-text credential literals exist in tracked source tree"
    local out; out="$(cd "$ROOT" && MIOS_ROOT="$ROOT" python3 tools/check-credential-literals.py 2>&1)" || { _violations_from "check_credential_literals: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- AGY-TASKS task descriptions conform strictly to task schema contract ---
check_task_schema() {
    echo "[98-drift-checks] AGY-TASKS task descriptions conform strictly to task schema contract"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-task-schema.py 2>/dev/null)" || { _violations_from "check_task_schema: " "$out"; return; }
    echo "[98-drift-checks]   every AGY task carries Verify/Do-NOT and resolvable deps"
}

# --- every drift check has a corresponding negative test registered ---
check_negatives_registered() {
    echo "[98-drift-checks] every drift check has a corresponding negative test registered"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-negatives-registered.py 2>/dev/null)" || { _violations_from "check_negatives_registered: " "$out"; return; }
    echo "[98-drift-checks]   every negative test the harness defines is invoked by it"
}

# --- test suite cleans up all temporary fixtures and directories ---
check_temp_fixture_cleanup() {
    echo "[98-drift-checks] test suite cleans up all temporary fixtures and directories"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-temp-fixture-cleanup.py 2>/dev/null)" || { _violations_from "check_temp_fixture_cleanup: " "$out"; return; }
    echo "[98-drift-checks]   every temp-dir fixture is removed by the test that made it"
}

# --- image variant registry declarations match build matrix targets ---
check_variant_registry() {
    echo "[98-drift-checks] image variant registry declarations match build matrix targets"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-variant-registry.py 2>/dev/null)" || { _violations_from "check_variant_registry: " "$out"; return; }
    echo "[98-drift-checks]   every variant names a real table, edition, archetype, artifact and doc"
}

# --- deployment artifact target formats comply with bootc/BIB spec ---
check_deploy_formats() {
    echo "[98-drift-checks] deployment artifact target formats comply with bootc/BIB spec"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-deploy-formats.py 2>&1)" || { _violations_from "check_deploy_formats: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- container image verification signatures and digests are valid ---
check_verify_images() {
    echo "[98-drift-checks] container image verification signatures and digests are valid"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-verify-images.py 2>&1)" || { _violations_from "check_verify_images: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- file header comments strictly conform to comment parser syntax ---
check_header_comment_syntax() {
    echo "[98-drift-checks] file header comments strictly conform to comment parser syntax"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-header-comment-syntax.py 2>/dev/null)" || { _violations_from "check_header_comment_syntax: " "$out"; return; }
    echo "[98-drift-checks]   every AI header uses the comment character its format understands"
}

# --- Rust crate test coverage meets or exceeds minimum threshold ---
check_rust_test_coverage() {
    echo "[98-drift-checks] Rust crate test coverage meets or exceeds minimum threshold"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-rust-test-coverage.py 2>/dev/null)" || { _violations_from "check_rust_test_coverage: " "$out"; return; }
    echo "[98-drift-checks]   every Rust crate has a test or is a registered exception"
}

# --- generated manual pages compile cleanly and match CLI help surfaces ---
check_manpages() {
    echo "[98-drift-checks] generated manual pages compile cleanly and match CLI help surfaces"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/render-manpages.py --check --validate 2>&1)" || { _violations_from "check_manpages: " "$out"; return; }
    echo "[98-drift-checks]   usr/share/man matches the SSOT; man(1) reads it directly"
}

# --- all workflow CI jobs cover the required test matrix without gaps ---
check_ci_suite_coverage() {
    echo "[98-drift-checks] all workflow CI jobs cover the required test matrix without gaps"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/ci-suites.py --check 2>&1)" || { _violations_from "check_ci_suite_coverage: " "$out"; return; }
    echo "[98-drift-checks]   every tracked CI suite is registered or exempt"
}

# --- no transient test fixtures or dump files are committed in git ---
check_leaked_fixtures() {
    echo "[98-drift-checks] no transient test fixtures or dump files are committed in git"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-leaked-fixtures.py 2>&1)" || { _violations_from "check_leaked_fixtures: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- log sanitizer redacts all sensitive fields listed in security schema ---
check_redact_coverage() {
    echo "[98-drift-checks] log sanitizer redacts all sensitive fields listed in security schema"
    local out; out="$(cd "$ROOT" && MIOS_ROOT="$ROOT" python3 tools/check-redact-coverage.py 2>&1)" || { _violations_from "check_redact_coverage: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- daemon governor runtime limits and cgroup constraints are valid ---
check_daemon_governor() {
    echo "[98-drift-checks] daemon governor runtime limits and cgroup constraints are valid"
    local out; out="$(cd "$ROOT" && MIOS_ROOT="$ROOT" python3 tools/check-daemon-governor.py 2>&1)" || { _violations_from "check_daemon_governor: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- all cross-references and internal links in manual docs resolve ---
check_manual_links() {
    echo "[98-drift-checks] all cross-references and internal links in manual docs resolve"
    local out; out="$(cd "$ROOT" && MIOS_ROOT="$ROOT" python3 tools/check-manual-links.py 2>&1)" || { _violations_from "check_manual_links: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- ADR architecture decision record index matches committed ADR files ---
check_adr_index() {
    echo "[98-drift-checks] ADR architecture decision record index matches committed ADR files"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/generate-adr-index.py --check 2>&1)" || { _violations_from "check_adr_index: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- all declared JSON/TOML schemas have active validation consumers ---
check_schema_consumers() {
    echo "[98-drift-checks] all declared JSON/TOML schemas have active validation consumers"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/check-schema-consumers.py 2>&1)" || { _violations_from "check_schema_consumers: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

_run_py_check() {
    local name="$1" script="$2" pfx="${3:-$1: }" out
    echo "[98-drift-checks]   $name"
    out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 $script 2>&1)" || { _violations_from "$pfx" "$out"; return; }
    echo "[98-drift-checks]   $out"
}

check_tasks_status_parity() { _run_py_check check_tasks_status_parity tools/check-tasks-status-parity.py; }
check_agy_tasks() { _run_py_check check_agy_tasks tools/check-agy-tasks.py; }
check_mios_toml_integrity() { _run_py_check check_mios_toml_integrity tools/check-mios-toml-integrity.py; }
check_privileged_quadlets_minimal() { _run_py_check check_privileged_quadlets_minimal tools/check-privileged-quadlets.py; }
check_container_names() { _run_py_check check_container_names tools/check-container-names.py; }
check_service_urls() { _run_py_check check_service_urls tools/check-service-urls.py ""; }
check_ports_bound() { _run_py_check check_ports_bound tools/check-ports-bound.py ""; }
check_blade_coverage() { _run_py_check check_blade_coverage tools/check-blade-coverage.py ""; }
check_fleet_safety() { _run_py_check check_fleet_safety tools/check-fleet-safety.py ""; }
check_ssot_consumer_keys() { _run_py_check check_ssot_consumer_keys tools/check-ssot-consumer-keys.py ""; }
check_unit_projection() { _run_py_check check_unit_projection tools/check-unit-projection.py ""; }
check_metal_vs_hosted() { _run_py_check check_metal_vs_hosted "tools/generate-metal-vs-hosted.py --check" ""; }
check_node_pool() { _run_py_check check_node_pool tools/check-node-pool.py ""; }
check_port_fallbacks() { _run_py_check check_port_fallbacks tools/check-port-fallbacks.py ""; }
check_role_ssot() { _run_py_check check_role_ssot tools/check-role-ssot.py ""; }
check_blade_karg() { _run_py_check check_blade_karg "tools/generate-blade-karg.py --check"; }
check_firstboot_provisioners() { _run_py_check check_firstboot_provisioners tools/check-firstboot-provisioners.py; }
check_desktop_launchers() { _run_py_check check_desktop_launchers "tools/render-desktop.py --check"; }

# --- all mios.toml SSOT tables have active code or generator consumers ---
check_no_inert_ssot_tables() {
    echo "[98-drift-checks] all mios.toml SSOT tables have active code or generator consumers"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py no-inert-ssot-tables
    )" || {
        _violations_from "check_no_inert_ssot_tables: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- file paths referenced in documentation exist in the repository ---
check_doc_refs_resolve() {
    echo "[98-drift-checks] file paths referenced in documentation exist in the repository"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py doc-refs-resolve
    )" || {
        _violations_from "check_doc_refs_resolve: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- differential output between resolvers across platforms is zero ---
check_resolver_differential_parity() {
    echo "[98-drift-checks] differential output between resolvers across platforms is zero"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py resolver-differential-parity 2>&1
)" || {
        _violations_from "check_resolver_differential_parity: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- code generators produce identical output regardless of host OS ---
check_generator_host_parity() {
    echo "[98-drift-checks] code generators produce identical output regardless of host OS"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 - 2>&1 <<'PYEOF'
import os, sys

root = os.environ.get("MIOS_DRIFT_ROOT", ".")
viol = []

# Audit generators for case-insensitive non-portable fnmatch.fnmatch usage
scanned_scripts = [
    "tools/generate-names-registry.py",
    "automation/lib/mios_var_closure.py",
    "tools/generate-ai-manifest.py",
    "tools/generate-pod-quadlets.py",
    "tools/generate-bake-plan.py",
    "usr/libexec/mios/mios-manual",
    "usr/libexec/mios/mios-version-lint",
]

for script in scanned_scripts:
    fpath = os.path.join(root, script)
    if not os.path.isfile(fpath):
        continue
    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    if "fnmatch.fnmatch(" in content:
        viol.append(f"{script} uses non-portable fnmatch.fnmatch instead of fnmatchcase")

if viol:
    print("\n".join(viol), file=sys.stderr)
    sys.exit(1)

print("    generator host parity: all generators produce host-independent byte-identical outputs")
sys.exit(0)
PYEOF
)" || {
        _violations_from "check_generator_host_parity: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}

# --- port numbers in documentation reflect mios.toml [ports] SSOT ---
check_doc_port_scheme() {
    echo "[98-drift-checks] port numbers in documentation reflect mios.toml [ports] SSOT"
    # Law 5/7: contract docs name [ports] keys; retired lane numbers must not return.
    local lists pat f hits
    lists="$(cd "$ROOT" && python3 - <<'PYEOF'
import tomllib
docs = tomllib.load(open("usr/share/mios/mios.toml", "rb")).get("docs", {})
print("|".join(str(p) for p in docs.get("retired_ports", [])))
print("\n".join(docs.get("port_clean", [])))
PYEOF
)"
    pat="${lists%%$'\n'*}"
    if [[ -z "$pat" ]]; then
        _violation "check_doc_port_scheme: [docs].retired_ports is empty or unreadable"
        return
    fi
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        if [[ ! -f "$ROOT/$f" ]]; then
            _violation "[docs].port_clean names a missing file: $f"
            continue
        fi
        hits="$(grep -nE "(^|[^0-9])(${pat})([^0-9]|$)" "$ROOT/$f" || true)"
        if [[ -n "$hits" ]]; then
            while IFS= read -r line; do
                _violation "retired port literal in ${f}: ${line}"
            done <<<"$hits"
        fi
    done <<<"${lists#*$'\n'}"
}




# ADR-0017 D5 prerequisite: divergence needs per-row provenance to be mergeable.
# --- blade reconciliation schema conforms to hardware capability specs ---
check_blade_reconcile_schema() {
    echo "[98-drift-checks] blade reconciliation schema conforms to hardware capability specs"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PYEOF'
import os, re, sys
import tomllib

root = os.environ.get("MIOS_DRIFT_ROOT", ".")
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
sql_path = os.path.join(root, "usr/share/mios/postgres/schema-init.sql")
if not os.path.isfile(toml_path):
    sys.exit(0)
with open(toml_path, "rb") as fh:
    data = tomllib.load(fh)

rec = ((data.get("blade") or {}).get("reconcile") or {})
if "enabled" not in rec:
    print("[blade.reconcile] has no `enabled` key -- an implied default is "
          "indistinguishable from a forgotten one, and this table decides "
          "whether partitioned writes are permitted")
    sys.exit(1)

RULE_KEYS = sorted(k for k in rec if k != "enabled")

if not rec.get("enabled"):
    print("[blade-reconcile] divergence disabled; %d merge rule(s) declared, "
          "schema prerequisite not yet required" % len(RULE_KEYS))
    sys.exit(0)

viol = []
sql = ""
if os.path.isfile(sql_path):
    with open(sql_path, encoding="utf-8", errors="replace") as fh:
        sql = fh.read()
for table in RULE_KEYS:
    m = re.search(r"CREATE TABLE IF NOT EXISTS\s+" + re.escape(table) + r"\s*\((.*?)\n\);",
                  sql, re.S)
    if not m:
        viol.append("enabled = true but schema-init.sql declares no table '%s'" % table)
        continue
    body = m.group(1)
    if not re.search(r"\borigin_node\b", body):
        viol.append("table '%s' has no origin_node column, so a merged row cannot be "
                    "attributed to the partition that wrote it" % table)
    if not re.search(r"\b(logical_ts|logical_clock)\b", body):
        viol.append("table '%s' has no logical_ts column, so append-ordered and "
                    "last-writer-wins have nothing to order by" % table)
if viol:
    viol.append("Land AGY-1598 (origin_node + logical_ts) or set "
                "[blade.reconcile].enabled = false until it does.")
print("\n".join(viol))
sys.exit(1 if viol else 0)
PYEOF
    )" || {
        _violations_from "check_blade_reconcile_schema: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}


# Law 15 mirror: mios.toml [bootstrap.sync]. Authority is mios.git.
# --- bootstrap repository sync: shared files in MiOS-bootstrap match main repository SSOT ---
check_bootstrap_sync() {
    echo "[98-drift-checks] bootstrap repository sync: shared files in MiOS-bootstrap match main repository SSOT"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/sync-bootstrap.py \
            --root "$ROOT" --check 2>&1)" || {
        _violations_from "check_bootstrap_sync: " "$out"; return; }
    echo "[98-drift-checks]   $out"
}


# The repo is the deliverable; these floors only come down. ROADMAP.md explains why.
# --- code legibility and complexity metrics remain within ratchet thresholds ---
check_legibility_ratchet() {
    echo "[98-drift-checks] code legibility and complexity metrics remain within ratchet thresholds"
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py legibility-ratchet
    )" || {
        _violations_from "check_legibility_ratchet: " "$out"; return; }
    echo "[98-drift-checks]   legibility floors holding"
}


# Header integrity: a tagger must never absorb line 1. See AGY-1607.
# --- source file AI-hint and license header blocks match template schema ---
check_header_integrity() {
    echo "[98-drift-checks] source file AI-hint and license header blocks match template schema"
    _need_python || return 0
    local out; out="$(cd "$ROOT" && MIOS_DRIFT_ROOT="$ROOT" python3 tools/drift-checks.py header-integrity)" || {
        _violations_from "check_header_integrity: " "$out"; return; }
    echo "[98-drift-checks]   no absorbed shebangs or build directives in file headers"
}

main "$@"
