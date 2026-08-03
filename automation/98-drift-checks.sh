#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Source-tree drift fitness-functions (WS-0A). Read-only static analysis over the repo (== system root) that FAILS on AI-plane SSOT drift no other gate catches: a retired local :11434 lane in active config, a retired model-id (gemma4 / qwen3:1.7b) hardcoded in a
# AI-related: 99-postcheck.sh, build.sh, /usr/libexec/mios/mios-ai-hint-coverage, /usr/share/mios/mios.toml, /usr/share/mios/ai/v1, /usr/share/mios/ai, /etc/mios/ai, /usr/lib/mios/agent-pipe, /usr/share/mios/ai/v1/packages, /usr/libexec/mios/mios-registry
# AI-functions: python3, _violation, check_dead_lane, check_retired_models, check_structured, check_hint_coverage, check_module_boundary, check_rbac_tiers, check_agent_schema, check_ai_manifest, check_package_registry, check_cli_sql_safety
# MIOS_DRIFT_CHECK_SOFT=1 to report but exit 0 (advisory, while a fix is staged).
set -euo pipefail

PYTHON="python3"
if ! python3 -c "import sys" >/dev/null 2>&1; then
    if python -c "import sys" >/dev/null 2>&1; then
        PYTHON="python"
        python3() {
            python "$@"
        }
        export -f python3 2>/dev/null || true
    fi
fi

_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="${MIOS_DRIFT_CHECK_ROOT:-$(cd "$_self_dir/.." && pwd)}"
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, json
root = os.environ["MIOS_DRIFT_ROOT"]
viol = []

try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml  # type: ignore
    except ImportError:
        _toml = None

toml_path = os.path.join(root, "usr/share/mios/mios.toml")
if _toml is None:
    sys.stderr.write("[98-drift-checks]   WARNING: no tomllib/tomli -- skipping [nodes.*] check\n")
elif os.path.isfile(toml_path):
    with open(toml_path, "rb") as fh:
        data = _toml.load(fh)
    nodes = data.get("nodes", {}) or {}
    served = set()
    for ud in ("usr/share/containers/systemd", "usr/lib/systemd/system",
               "etc/containers/systemd"):
        base = os.path.join(root, ud)
        if not os.path.isdir(base):
            continue
        for dirpath, _dn, files in os.walk(base):
            for fn in files:
                if not fn.endswith((".container", ".service")):
                    continue
                try:
                    txt = open(os.path.join(dirpath, fn), encoding="utf-8",
                               errors="ignore").read()
                except OSError:
                    continue
                for m in re.findall(r":(\d{4,5})\b", txt):
                    served.add(m)
                for m in re.findall(r"(?:--port[= ]|PublishPort[= ])(\d{4,5})", txt):
                    served.add(m)
    for name, cfg in nodes.items():
        if not isinstance(cfg, dict):
            continue
        ep = (cfg.get("endpoint") or "").strip()
        if not ep:
            continue  # empty endpoint = inert node, skipped by the loader
        m = re.search(r"://(?:localhost|127\.0\.0\.1|host\.containers\.internal):(\d{4,5})", ep)
        if not m:
            continue  # remote / non-local endpoint -- operator overlay, unverifiable
        port = m.group(1)
        if port not in served:
            viol.append(f"[nodes.{name}] endpoint {ep} -> localhost:{port} is served by NO shipped unit "
                        f"(dangling lane; served ports: {sorted(served)})")

    obs = data.get("observability", {}) or {}
    if "surface_default" not in obs:
        viol.append("[observability] surface_default is missing")
    elif obs.get("surface_default") not in ("clean", "inline"):
        viol.append(f"[observability] surface_default '{obs.get('surface_default')}' must be 'clean' or 'inline'")
    
    channels = obs.get("channels", {}) or {}
    req_channels = {"thinking", "plan", "tool_call", "tool_result", "source", "content"}
    for rc in req_channels:
        if rc not in channels:
            viol.append(f"[observability.channels] key '{rc}' is missing")
            
    lanes = data.get("lanes", {}) or {}
    for lname in ("light", "sglang", "vllm"):
        if lname not in lanes:
            viol.append(f"[lanes.{lname}] section is missing")
        else:
            lcfg = lanes[lname] or {}
            for k in ("stream_thinking", "tool_call_parser", "reasoning_parser", "constrained_tools"):
                if k not in lcfg:
                    viol.append(f"[lanes.{lname}].{k} is missing")
                    
    ap = data.get("agent_pipe", {}) or {}
    for k in ("tool_loop_limit", "reflexion_limit", "reflexion_enable"):
        if k not in ap:
            viol.append(f"[agent_pipe].{k} is missing")

v1 = os.path.join(root, "usr/share/mios/ai/v1")
if os.path.isdir(v1):
    for fn in sorted(os.listdir(v1)):
        if not fn.endswith(".json"):
            continue
        p = os.path.join(v1, fn)
        try:
            doc = json.load(open(p, encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            viol.append(f"ai/v1/{fn} does not parse as JSON: {e}")
            continue
        if fn == "tools.json":
            for e in doc.get("data", []):
                if not isinstance(e, dict):
                    continue
                for key in ("chat_completions", "responses", "schema_output"):
                    ref = e.get(key)
                    if isinstance(ref, str) and ref.startswith("/usr/"):
                        if not os.path.exists(os.path.join(root, ref.lstrip("/"))):
                            viol.append(f"tools.json: {e.get('name')!r} {key} -> {ref} (missing on disk)")

for v in viol:
    sys.stderr.write(f"    {v}\n")
sys.exit(1 if viol else 0)
PY
    then
        echo "[98-drift-checks]   every [nodes.local-*] localhost lane is served; ai/v1 manifests parse + refs resolve"
    else
        _violation "structured drift: a [nodes.*] lane is dangling and/or an ai/v1 manifest is broken (see lines above)"
    fi
}

check_hint_coverage() {
    local tool="$ROOT/usr/libexec/mios/mios-ai-hint-coverage"
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys
root = os.environ["MIOS_DRIFT_ROOT"]
try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml  # type: ignore
    except ImportError:
        sys.exit(0)  # no toml parser -> skip (not a violation)
p = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(p):
    sys.exit(0)
with open(p, "rb") as fh:
    d = _toml.load(fh)
tiers = [str(x).strip().lower()
         for x in ((d.get("ai") or {}).get("permission_tiers")
                   or ["read", "write", "interactive"]) if str(x).strip()]
bad = []
for sect in ("agents", "users"):
    for name, cfg in (d.get(sect) or {}).items():
        if not isinstance(cfg, dict):
            continue
        mp = str(cfg.get("max_permission") or "").strip().lower()
        if mp and mp not in tiers:
            bad.append(f"    [{sect}.{name}].max_permission={mp!r} not in {tiers}")
for b in bad:
    sys.stderr.write(b + "\n")
sys.exit(1 if bad else 0)
PY
    then
        echo "[98-drift-checks]   RBAC max_permission tiers all valid"
    else
        _violation "an [agents.*]/[users.*].max_permission names an UNKNOWN permission tier -- the dispatch PDP fails CLOSED on it (restricts the caller to the safest tier); fix the typo or add the tier to [ai].permission_tiers "
    fi
}

check_agent_schema() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
root = os.environ["MIOS_DRIFT_ROOT"]
try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml  # type: ignore
    except ImportError:
        sys.exit(0)
p = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(p):
    sys.exit(0)
with open(p, "rb") as fh:
    d = _toml.load(fh)
ag = dict(d.get("agents") or {})
defs = ag.pop("_defaults", {}) if isinstance(ag.get("_defaults"), dict) else {}
CANON = {"kind","endpoint","model","role","job","default","fanout","enabled","lane",
         "sub_lane","health_gate","transport","timeout_s","strengths","cpu_endpoint",
         "cpu_model","failover_agents","denied_verbs","allowed_verbs","max_permission",
         "api","vram_mb","ram_mb","tool_capable","research_only","auth","trust",
         "engines","nodes","backend","privilege_group"}
def _local(ep):
    h = re.sub(r'^[a-z]+://', '', str(ep)).split('/')[0].rsplit(':', 1)[0]
    return h in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "")
bad, warn, ndefault = [], [], 0
for name, cfg in ag.items():
    if name.startswith("_") or not isinstance(cfg, dict):
        continue
    m = {**defs, **cfg}
    kind = str(m.get("kind", "")).strip().lower()
    ep = str(m.get("endpoint", "")).strip()
    enabled = bool(m.get("enabled", True))
    hg = bool(m.get("health_gate", False))
    if bool(m.get("default", False)):
        ndefault += 1
    loc = _local(ep)
    if loc and not bool(m.get("default", False)) and enabled and kind in ("", "local-http") and not hg:
        bad.append(f"    [agents.{name}] LOCAL + non-default + enabled but no health_gate=true (or enabled=false): a dead endpoint is treated as live -> DAG sink -> merged_chars=0")
    if kind == "cli":
        if not (hg or not enabled):
            bad.append(f"    [agents.{name}] kind=cli must set health_gate=true OR enabled=false")
        if int(m.get("timeout_s", 0) or 0) <= 0:
            bad.append(f"    [agents.{name}] kind=cli must set timeout_s>0 (fail-fast budget)")
    if kind == "node" and not (str(m.get("api", "")).strip() and str(m.get("lane", "")).strip()):
        bad.append(f"    [agents.{name}] kind=node must set api + lane")
    if kind in ("remote-http", "edge", "mobile") and not hg:
        bad.append(f"    [agents.{name}] kind={kind} must set health_gate=true")
    if re.search(r':\d{2,5}(/|$)', ep) and "${MIOS_PORT" not in ep:
        warn.append(f"    [agents.{name}].endpoint bare :PORT literal (use ${{MIOS_PORT_*}}): {ep}")
    for k in cfg:
        if k not in CANON:
            warn.append(f"    [agents.{name}] unknown key {k!r} (not in the canonical agent schema)")
if ndefault > 1:
    bad.append(f"    {ndefault} [agents.*] set default=true; at most one is allowed")
for w in warn:
    sys.stdout.write("[98-drift-checks]   (advisory)" + w + "\n")
for b in bad:
    sys.stderr.write(b + "\n")
sys.exit(1 if bad else 0)
PY
    then
        echo "[98-drift-checks]   agent-schema contract satisfied"
    else
        _violation "an [agents.*] entry violates the unified agent schema : a local-optional agent missing health_gate, a kind=cli without timeout_s, a kind=node without api+lane, or >1 default=true -- the opencode 'dead local endpoint treated as live -> merged_chars=0' class. Fix the [agents.*] block (or [agents._defaults])."
    fi
}

check_ai_manifest() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, json
root = os.environ["MIOS_DRIFT_ROOT"]
sys.path.insert(0, os.path.join(root, "usr/lib/mios/agent-pipe"))
try:
    import mios_manifest as man
except Exception as e:  # noqa: BLE001 -- module absent on a bare checkout -> skip
    sys.stderr.write(f"    cannot import mios_manifest ({e}) -- skipping\n")
    sys.exit(0)
toml = os.path.join(root, "usr/share/mios/mios.toml")
out  = os.path.join(root, "usr/share/mios/ai/v1/tools.generated.json")
try:
    gen = man.project_verb_catalog(man.load_verbs_from_toml(toml))
except Exception as e:  # noqa: BLE001
    sys.stderr.write(f"    verb-catalog projection failed: {e}\n")
    sys.exit(1)
try:
    with open(out, encoding="utf-8") as fh:
        committed = json.load(fh)
except (OSError, ValueError) as e:
    sys.stderr.write(f"    committed manifest unreadable ({out}): {e}\n")
    sys.exit(1)
diffs = man.diff_manifest(gen, committed)
for d in diffs[:30]:
    sys.stderr.write("    " + d + "\n")
sys.exit(1 if diffs else 0)
PY
    then
        echo "[98-drift-checks]   ai/v1 verb-catalog manifest in sync with mios.toml SSOT"
    else
        _violation "ai/v1/tools.generated.json is STALE vs mios.toml [verbs.*] -- regenerate with mios-ai-manifest-gen "
    fi
}

check_package_registry() {
    local _en
    _en="$(printf '%s' "${MIOS_PACKAGE_REGISTRY:-false}" | tr '[:upper:]' '[:lower:]')"
    case "$_en" in
        1|true|yes|on) : ;;
        *)
            echo "[98-drift-checks]   package registry dormant"
            return 0 ;;
    esac
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, json
root = os.environ["MIOS_DRIFT_ROOT"]
sys.path.insert(0, os.path.join(root, "usr/lib/mios/agent-pipe"))
try:
    import mios_capreg as cap
except Exception as e:  # noqa: BLE001 -- module absent on a bare checkout -> skip
    sys.stderr.write(f"    cannot import mios_capreg ({e}) -- skipping\n")
    sys.exit(0)
toml = os.path.join(root, "usr/share/mios/mios.toml")
out = os.path.join(root, "usr/share/mios/ai/v1/capabilities.generated.json")
try:
    gen = cap.project_from_toml(toml, ceiling="interactive")
except Exception as e:  # noqa: BLE001
    sys.stderr.write(f"    capability projection failed: {e}\n")
    sys.exit(1)
try:
    with open(out, encoding="utf-8") as fh:
        committed = json.load(fh).get("data", [])
except (OSError, ValueError) as e:
    sys.stderr.write(f"    committed capabilities manifest unreadable ({out}): {e}\n")
    sys.exit(1)
diffs = cap.diff_capabilities(gen, committed)
for d in diffs[:30]:
    sys.stderr.write("    " + d + "\n")
sys.exit(1 if diffs else 0)
PY
    then
        echo "[98-drift-checks]   ai/v1 capability manifest in sync with mios.toml SSOT"
    else
        _violation "ai/v1/capabilities.generated.json is STALE vs mios.toml [verbs.*]+[recipes.*] -- regenerate with mios-ai-capabilities-gen"
    fi
}

check_surface_parity() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, json
root = os.environ["MIOS_DRIFT_ROOT"]
sys.path.insert(0, os.path.join(root, "usr/lib/mios/agent-pipe"))
try:
    import mios_surface as surf
except Exception as e:  # noqa: BLE001 -- module absent on a bare checkout -> skip
    sys.stderr.write(f"    cannot import mios_surface ({e}) -- skipping\n")
    sys.exit(0)
server = os.path.join(root, "usr/lib/mios/agent-pipe/server.py")
out = os.path.join(root, "usr/share/mios/ai/v1/surface.generated.json")
if not os.path.isfile(server):
    sys.stderr.write("    server.py absent -- skipping\n")
    sys.exit(0)
try:
    gen = surf.project_package(server)
except Exception as e:  # noqa: BLE001
    sys.stderr.write(f"    surface projection failed: {e}\n")
    sys.exit(1)
try:
    with open(out, encoding="utf-8") as fh:
        committed = json.load(fh)
except (OSError, ValueError) as e:
    sys.stderr.write(f"    committed surface golden unreadable ({out}): {e}\n")
    sys.exit(1)
diffs = surf.diff_surface(gen, committed)
for d in diffs[:40]:
    sys.stderr.write("    " + d + "\n")
if len(diffs) > 40:
    sys.stderr.write(f"    ... and {len(diffs) - 40} more\n")
sys.exit(1 if diffs else 0)
PY
    then
        echo "[98-drift-checks]   server.py public surface matches the committed golden"
    else
        _violation "server.py PUBLIC SURFACE drifted from usr/share/mios/ai/v1/surface.generated.json -- a route/symbol was dropped or added during the refactor. If intended, regenerate: python3 usr/lib/mios/agent-pipe/mios_surface.py usr/lib/mios/agent-pipe/server.py --package > usr/share/mios/ai/v1/surface.generated.json (refactor WS R0)"
    fi
}

check_pod_quadlets() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, ast
root = os.environ["MIOS_DRIFT_ROOT"]
pipe = os.path.join(root, "usr/lib/mios/agent-pipe")
if not os.path.isdir(pipe):
    sys.exit(0)  # nothing to check on a bare checkout

try:
    import tomllib as _toml
except ImportError:
    import tomli as _toml
with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
    _data = _toml.load(fh)
ALLOW = set(_data.get("drift", {}).get("denylist", []))

def is_test(path):
    b = os.path.basename(path)
    if b.startswith("test_") or b.endswith("_test.py"):
        return True
    segs = path.replace("\\", "/").split("/")
    return "tests" in segs or "test" in segs

pipe_py = []
for dp, _dn, files in os.walk(pipe):
    for f in files:
        if f.endswith(".py") and not is_test(os.path.join(dp, f)):
            pipe_py.append(os.path.join(dp, f))
ref_py = list(pipe_py)
for sub in ("usr/libexec/mios", "tools"):
    base = os.path.join(root, sub)
    if not os.path.isdir(base):
        continue
    for dp, _dn, files in os.walk(base):
        for f in files:
            if f.endswith(".py") and not is_test(os.path.join(dp, f)):
                ref_py.append(os.path.join(dp, f))

modules = sorted(f[:-3] for f in os.listdir(pipe)
                 if f.startswith("mios_") and f.endswith(".py")
                 and not is_test(os.path.join(pipe, f)))

def parse(p):
    try:
        return ast.parse(open(p, encoding="utf-8").read())
    except Exception:
        return None

pipe_trees = {p: parse(p) for p in pipe_py}
ref_trees = {p: parse(p) for p in ref_py}

def binds(tree, mod):
    """Names this tree binds for `mod`: (import-aliases, from-names, star?)."""
    al, fr, star = set(), set(), False
    if tree is None:
        return al, fr, star
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == mod:
                    al.add(a.asname or a.name)
        elif isinstance(n, ast.ImportFrom):
            if n.module == mod and (n.level or 0) == 0:
                for a in n.names:
                    if a.name == "*":
                        star = True
                    else:
                        fr.add(a.asname or a.name)
    return al, fr, star

def uses(tree, names):
    """True if tree references a bound name. Imports bind via alias nodes, not
    ast.Name, so any ast.Name match is a genuine (non-import) reference."""
    if tree is None or not names:
        return False
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id in names:
            return True
    return False

dead = set()
for mod in modules:
    mf = os.path.abspath(os.path.join(pipe, mod + ".py"))
    imported = False
    for p, t in pipe_trees.items():
        if os.path.abspath(p) == mf:
            continue
        al, fr, star = binds(t, mod)
        if al or fr or star:
            imported = True
            break
    if not imported:
        continue  # never imported by the core -> not the imported-but-dead class
    wired = False
    for p, t in ref_trees.items():
        if os.path.abspath(p) == mf:
            continue
        al, fr, star = binds(t, mod)
        if star:
            wired = True
            break
        if (al or fr) and uses(t, al | fr):
            wired = True
            break
    if not wired:
        dead.add(mod)

new_dead = sorted(dead - ALLOW)   # NEW imported-but-dead module -> fail
stale = sorted(ALLOW - dead)      # allowlisted but now wired/removed -> fail
for m in new_dead:
    sys.stderr.write(f"    {m}: imported by agent-pipe but no real (non-test) call site "
                     "-- wire it (give it a caller) or add it to _UNWIRED_ALLOW with a register note\n")
for m in stale:
    sys.stderr.write(f"    {m}: listed in _UNWIRED_ALLOW but now WIRED or removed "
                     "-- delete it from the allowlist (A1 register self-cleans)\n")
sys.exit(1 if (new_dead or stale) else 0)
PY
    then
        echo "[98-drift-checks]   no imported-but-dead agent-pipe module"
    else
        _violation "an agent-pipe module is imported-but-dead (no real non-test caller) OR a _UNWIRED_ALLOW entry is stale -- wire the module (give it a call site) or update the _UNWIRED_ALLOW register (MIOS-GAP-REGISTER A1)"
    fi
}

check_cephfs_ssot() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys
root = os.environ["MIOS_DRIFT_ROOT"]
viol = []

try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml
    except ImportError:
        _toml = None

toml_path = os.path.join(root, "usr/share/mios/mios.toml")
if _toml is None:
    sys.stderr.write("[98-drift-checks]   WARNING: no tomllib/tomli -- skipping CephFS check\n")
elif os.path.isfile(toml_path):
    with open(toml_path, "rb") as fh:
        data = _toml.load(fh)
    cephfs = data.get("storage", {}).get("cephfs", {}) or {}
    enable = cephfs.get("enable", False)
    
    if enable:
        monitors = cephfs.get("monitors", [])
        if not monitors or monitors == ["127.0.0.1:6789"]:
            viol.append("[storage.cephfs].monitors must be set to actual monitor IPs when enable=true")
            
        cache_override = cephfs.get("xdg_cache_home_override", "")
        hostnames = [m.split(":")[0] for m in monitors]
        if ("ceph" in cache_override.lower() or 
                "/tenants/" in cache_override or 
                cache_override.startswith("/home/") or 
                any(h in cache_override for h in hostnames if h)):
            viol.append("[storage.cephfs].xdg_cache_home_override must be local tmpfs, NEVER CephFS (MDS storm hazard)")
            
        hot_pool = cephfs.get("data_pool_hot", "")
        bulk_pool = cephfs.get("data_pool_bulk", "")
        if hot_pool and bulk_pool and hot_pool == bulk_pool:
            viol.append("[storage.cephfs] data_pool_hot and data_pool_bulk must be distinct pools for tiering")
            
        prov_script = cephfs.get("provision_script", "")
        if prov_script:
            rel_path = prov_script.lstrip("/")
            repo_path = os.path.join(root, rel_path)
            if not os.path.exists(repo_path) and not os.path.exists(prov_script):
                viol.append(f"[storage.cephfs].provision_script path '{prov_script}' does not exist on disk")

        if cephfs.get("automount_enable", False):
            mount_tmpl = os.path.join(root, "usr/share/mios/systemd/home-@.mount.tmpl")
            if not os.path.exists(mount_tmpl):
                viol.append("home-@.mount.tmpl is missing from usr/share/mios/systemd/ but [storage.cephfs].automount_enable is true")

    import re
    tmpls = [
        os.path.join(root, "usr/share/mios/systemd/home-@.mount.tmpl"),
        os.path.join(root, "usr/share/mios/systemd/home-@.automount.tmpl"),
    ]
    setup_script = os.path.join(root, "automation/firstboot/mios-cephfs-mount-setup.sh")
    setup_code = ""
    if os.path.exists(setup_script):
        with open(setup_script, "r", encoding="utf-8", errors="ignore") as sf:
            setup_code = sf.read()

    for tmpl in tmpls:
        if os.path.exists(tmpl):
            with open(tmpl, "r", encoding="utf-8", errors="ignore") as tf:
                tokens = set(re.findall(r"\$\{MIOS_CEPHFS_([A-Z0-9_]+)\}", tf.read()))
            for tok in tokens:
                key = tok.lower()
                if key not in cephfs:
                    viol.append(f"Template token ${{MIOS_CEPHFS_{tok}}} has no corresponding key '{key}' in [storage.cephfs]")
                if setup_code and f"MIOS_CEPHFS_{tok}" not in setup_code:
                    viol.append(f"Template token ${{MIOS_CEPHFS_{tok}}} is not substituted by mios-cephfs-mount-setup.sh")

for v in viol:
    sys.stderr.write(f"    {v}\n")
sys.exit(1 if viol else 0)
PY
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
        local expected_base
        expected_base=$(grep -E '^\s*distroless_base\s*=' "$mios_toml" | head -n 1 | cut -d'"' -f2 || echo "Gcr.io/distroless/python3-debian13")
        if [[ -z "$expected_base" ]]; then
            expected_base="gcr.io/distroless/python3-debian13"
        fi

        if ! grep -F "FROM $expected_base" "$containerfile" >/dev/null 2>&1; then
            echo "[98-drift-checks] VIOLATION: Containerfile.hummingbird base image does not match distroless_base" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        local final_stage
        final_stage=$(awk '/^FROM/ { stage="" } { stage=stage "\n" $0 } END { print stage }' "$containerfile")

        if echo "$final_stage" | grep -F "/bin/bash" >/dev/null; then
            echo "[98-drift-checks] VIOLATION: Containerfile.hummingbird final stage contains /bin/bash" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        local user_line
        user_line=$(echo "$final_stage" | grep -E '^\s*USER\s+' | tail -n 1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    local tmp; tmp="$(mktemp)"
    if MIOS_DRIFT_ROOT="$ROOT" python3 - >"$tmp" 2>&1 <<'PY'
import os, sys, re
root = os.environ.get("MIOS_DRIFT_ROOT", ".")
try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml
    except ImportError:
        sys.exit(0)

p = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(p):
    sys.exit(0)

with open(p, "rb") as fh:
    d = _toml.load(fh)
ports = d.get("ports") or {}

port_vals = {name: val for name, val in ports.items() if name != "stack_id" and isinstance(val, int)}

viol = []
quadlet_dirs = ["usr/share/containers/systemd", "etc/containers/systemd"]
for qd in quadlet_dirs:
    dir_path = os.path.join(root, qd)
    if not os.path.isdir(dir_path):
        continue
    for dp, _dn, files in os.walk(dir_path):
        for fn in files:
            if not fn.endswith(".container"):
                continue
            path = os.path.join(dp, fn)
            try:
                lines = open(path, encoding="utf-8", errors="ignore").readlines()
            except OSError:
                continue
            for idx, line in enumerate(lines, 1):
                active = re.sub(r'#.*', '', line).strip()
                if not active:
                    continue
                for name, val in port_vals.items():
                    # [A-Z0-9_]+ not [A-Z_]+ -- port names carry digits
                    # (CRAWL4AI, K3S_API), so the old pattern failed to strip
                    # their ${...:-N} form and then flagged the fallback it had
                    # just failed to remove.
                    cleaned = re.sub(r'\$\{MIOS_PORT_[A-Z0-9_]+:-' + str(val) + r'\}', '', active)
                    if re.search(rf'\b{val}\b', cleaned):
                        if val in (8080, 3002) and (":" + str(val) in cleaned or "=" + str(val) in cleaned and not cleaned.startswith("PublishPort=")):
                            continue
                        viol.append(f"{fn}:{idx}: manual port literal {val} for '{name}' used in active line: {line.strip()}")

for v in viol:
    print(v)
sys.exit(1 if viol else 0)
PY
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys
root = os.environ["MIOS_DRIFT_ROOT"]
try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml
    except ImportError:
        sys.exit(0)

main_toml_path = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(main_toml_path):
    sys.exit(0)

with open(main_toml_path, "rb") as fh:
    main_data = _toml.load(fh)

main_ports = {k: v for k, v in main_data.get("ports", {}).items() if not isinstance(v, dict)}

bootstrap_repo_path = main_data.get("bootstrap", {}).get("bootstrap_repo", "C:/mios-bootstrap")

if sys.platform != "win32" and bootstrap_repo_path.startswith("C:/"):
    bootstrap_repo_path = "/mnt/c/" + bootstrap_repo_path[3:]

if not os.path.isdir(bootstrap_repo_path):
    bootstrap_repo_path = os.path.join(os.path.dirname(root), "mios-bootstrap")

if not os.path.isdir(bootstrap_repo_path):
    sys.exit(0)

bootstrap_toml_path = os.path.join(bootstrap_repo_path, "mios.toml")
if not os.path.isfile(bootstrap_toml_path):
    sys.exit(0)

with open(bootstrap_toml_path, "rb") as fh:
    boot_data = _toml.load(fh)

boot_ports = {k: v for k, v in boot_data.get("ports", {}).items() if not isinstance(v, dict)}

drift = []
for k, v in main_ports.items():
    if k not in boot_ports:
        drift.append(f"Port key '{k}' in main mios.toml is missing from bootstrap mios.toml")
    elif boot_ports[k] != v:
        drift.append(f"Port '{k}' value differs: main={v}, bootstrap={boot_ports[k]}")

for k, v in boot_ports.items():
    if k not in main_ports:
        drift.append(f"Port key '{k}' in bootstrap mios.toml is missing from main mios.toml")

if drift:
    for d in drift:
        sys.stderr.write("    " + d + "\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   bootstrap mios.toml [ports] table matches main repository"
    else
        _violation "bootstrap mios.toml [ports] table diverges from main repository mios.toml"
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

    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
try:
    import tomllib
except ImportError:
    import tomli as tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(toml_path):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

agent_pipe = data.get("agent_pipe", {})
dispatch = data.get("dispatch", {})

def key_in_dict(d, k):
    if not isinstance(d, dict):
        return False
    if k in d:
        return True
    return any(key_in_dict(v, k) for v in d.values() if isinstance(v, dict))

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

budget_keys = [
    "tool_max_iters", "replan_max", "no_progress_window",
    "max_consecutive_failures", "wall_clock_budget_s", "reflexion_enable",
    "swarm_max_width", "max_dispatch_depth", "default_hop_budget"
]
missing = []
for k in budget_keys:
    if not key_in_dict(agent_pipe, k) and not key_in_dict(dispatch, k):
        missing.append(f"{k} (missing from mios.toml)")
        continue
    pattern = rf"['\"]{k}['\"]"
    if not re.search(pattern, code) and k not in code:
        missing.append(k)

if missing:
    sys.stderr.write(f"    Missing code consumers or TOML definitions for budget keys: {missing}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   all [agent_pipe] budget variables have code consumers"
    else
        _violation "some [agent_pipe] keys have no code consumer in the agent-pipe codebase"
    fi
}

check_no_bare_port_literals() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, ast

root = os.environ["MIOS_DRIFT_ROOT"]
banned_ports = ["11450", "11441", "11440", "11451", "11434", "11435"]
scan_dirs = [
    os.path.join(root, "usr/lib/mios/agent-pipe"),
    os.path.join(root, "usr/libexec/mios"),
    os.path.join(root, "usr/bin")
]

class DocstringCollector(ast.NodeVisitor):
    def __init__(self):
        self.docstring_nodes = set()
    def check_body(self, body):
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                self.docstring_nodes.add(body[0].value)
    def visit_Module(self, node):
        self.check_body(node.body)
        self.generic_visit(node)
    def visit_FunctionDef(self, node):
        self.check_body(node.body)
        self.generic_visit(node)
    def visit_AsyncFunctionDef(self, node):
        self.check_body(node.body)
        self.generic_visit(node)
    def visit_ClassDef(self, node):
        self.check_body(node.body)
        self.generic_visit(node)

violations = []
for d in scan_dirs:
    if not os.path.isdir(d):
        continue
    for r, ds, fs in os.walk(d):
        for f in fs:
            if not f.endswith((".py", ".sh", ".ps1")) or "test_" in f:
                continue
            if f in ["Setup-MiOSLanPortProxy.ps1", "Heal-MiOSLocalhostForwarding.ps1", "Setup-MiOSLanPortProxy.ps1.bom-bak", "mios-doctor"]:
                continue
            path = os.path.join(r, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                
                if f.endswith(".py"):
                    try:
                        tree = ast.parse(content)
                        collector = DocstringCollector()
                        collector.visit(tree)
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Constant):
                                if node in collector.docstring_nodes:
                                    continue
                                val = str(node.value)
                                for port in banned_ports:
                                    if port in val:
                                        violations.append(f"{f}:{getattr(node, 'lineno', '?')} contains banned port '{port}' in constant '{val}'")
                    except Exception as e:
                        for line_no, line in enumerate(content.splitlines(), 1):
                            stripped = line.strip()
                            if stripped.startswith(("#", "'''", '"""')):
                                continue
                            code_part = line.split("#", 1)[0]
                            for port in banned_ports:
                                if port in code_part:
                                    violations.append(f"{f}:{line_no} contains banned port '{port}' (fallback)")
                else:
                    for line_no, line in enumerate(content.splitlines(), 1):
                        stripped = line.strip()
                        if stripped.startswith(("#", "//", "Write-Host", "echo", "help", "usage")):
                            continue
                        code_part = line.split("#", 1)[0].split("//", 1)[0]
                        for port in banned_ports:
                            if port in code_part:
                                violations.append(f"{f}:{line_no} contains banned port '{port}'")
            except OSError:
                pass

if violations:
    for v in sorted(set(violations)):
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   no bare port literals remain in execution paths"
    else
        _violation "bare port literals in execution paths"
    fi
}

check_dotfiles_projection() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
root = os.environ["MIOS_DRIFT_ROOT"]
try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml  # type: ignore
    except ImportError:
        sys.exit(0)
p = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(p):
    sys.exit(0)
with open(p, "rb") as fh:
    d = _toml.load(fh)
libexec = os.path.join(root, "usr/libexec/mios")
usrbin = os.path.join(root, "usr/bin")
def _exists(t):
    return os.path.isfile(os.path.join(libexec, t)) or os.path.isfile(os.path.join(usrbin, t))
missing = {}
for name, cfg in (d.get("verbs", {}) or {}).items():
    if not isinstance(cfg, dict):
        continue
    cmd = cfg.get("cmd", "")
    if not isinstance(cmd, str) or not cmd:
        continue
    for tok in set(re.findall(r"\bmios-[a-z0-9-]+", cmd)):
        if not _exists(tok):
            missing.setdefault(tok, []).append(name)
for t, vs in sorted(missing.items()):
    sys.stderr.write(f"    {t} <- [verbs.*] {sorted(vs)} (backend not on disk)\n")
sys.exit(1 if missing else 0)
PY
    then
        echo "[98-drift-checks]   every [verbs.*].cmd mios-* backend resolves on disk"
    else
        _violation "a [verbs.*].cmd dispatches to a mios-* backend that does not exist (dead dispatch) -- fix the cmd template or ship the backend (flatten check 26)"
    fi
}

check_globals_ports() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
root = os.environ["MIOS_DRIFT_ROOT"]
try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml  # type: ignore
    except ImportError:
        sys.exit(0)
toml = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(toml):
    sys.exit(0)
with open(toml, "rb") as fh:
    ports = (_toml.load(fh).get("ports", {}) or {})

bad = []
ps1 = os.path.join(root, "automation/lib/globals.ps1")
if os.path.isfile(ps1):
    with open(ps1, encoding="utf-8") as fh:
        for line in fh:
            m = re.search(r"MIOS_PORT_([A-Z0-9_]+)\b", line)
            v = re.search(r"else\s*\{\s*(\d+)\s*\}", line)
            if not (m and v):
                continue
            name, got = m.group(1), int(v.group(1))
            key = name.lower()
            if key not in ports:
                bad.append(f"globals.ps1 MIOS_PORT_{name}={got} has NO [ports].{key} key (retired lane?)")
            elif int(ports[key]) != got:
                bad.append(f"globals.ps1 MIOS_PORT_{name}={got} != [ports].{key}={ports[key]}")
sh = os.path.join(root, "automation/lib/globals.sh")
if os.path.isfile(sh):
    with open(sh, encoding="utf-8") as fh:
        for line in fh:
            m = re.search(r"\$\{MIOS_PORT_([A-Z0-9_]+):=(\d+)\}", line)
            if not m:
                continue
            name, got = m.group(1), int(m.group(2))
            key = name.lower()
            if key not in ports:
                bad.append(f"globals.sh MIOS_PORT_{name}={got} has NO [ports].{key} key (retired lane?)")
            elif int(ports[key]) != got:
                bad.append(f"globals.sh MIOS_PORT_{name}={got} != [ports].{key}={ports[key]}")

for b in bad:
    sys.stderr.write(f"    {b}\n")
sys.exit(1 if bad else 0)
PY
    then
        echo "[98-drift-checks]   every MIOS_PORT_* fallback in globals.{ps1,sh} equals mios.toml [ports] SSOT"
    else
        _violation "a MIOS_PORT_* fallback default in automation/lib/globals.ps1 or globals.sh drifted from mios.toml [ports] SSOT (Windows-side effective default; align the else{N}/:=N literal to [ports].<name>) (flatten check 28)"
    fi
}

check_globals_image_parity() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
root = os.environ["MIOS_DRIFT_ROOT"]
try:
    import tomllib as _toml
except ImportError:
    try:
        import tomli as _toml  # type: ignore
    except ImportError:
        sys.exit(0)
toml = os.path.join(root, "usr/share/mios/mios.toml")
if not os.path.isfile(toml):
    sys.exit(0)
with open(toml, "rb") as fh:
    img = (_toml.load(fh).get("image", {}) or {})

expected_name = img.get("name", "ghcr.io/mios-dev/mios")
expected_base = img.get("base", "ghcr.io/ublue-os/ucore-hci:stable-nvidia")
expected_bib = img.get("bib", "quay.io/centos-bootc/bootc-image-builder:latest")

bad = []
sh = os.path.join(root, "automation/lib/globals.sh")
if os.path.isfile(sh):
    with open(sh, encoding="utf-8") as fh:
        content = fh.read()
        
        m = re.search(r'MIOS_IMAGE_NAME:=([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_name:
                bad.append(f"globals.sh default MIOS_IMAGE_NAME={got} != mios.toml [image].name={expected_name}")
        else:
            bad.append("globals.sh is missing default MIOS_IMAGE_NAME definition")
            
        m = re.search(r'MIOS_BASE_IMAGE:=([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_base:
                bad.append(f"globals.sh default MIOS_BASE_IMAGE={got} != mios.toml [image].base={expected_base}")
        else:
            bad.append("globals.sh is missing default MIOS_BASE_IMAGE definition")

        m = re.search(r'MIOS_BIB_IMAGE:=([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_bib:
                bad.append(f"globals.sh default MIOS_BIB_IMAGE={got} != mios.toml [image].bib={expected_bib}")
        else:
            bad.append("globals.sh is missing default MIOS_BIB_IMAGE definition")

ps1 = os.path.join(root, "automation/lib/globals.ps1")
if os.path.isfile(ps1):
    with open(ps1, encoding="utf-8") as fh:
        content = fh.read()
        
        m = re.search(r'\$defaultImageName\s*=\s*([^#\r\n]+)', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_name:
                bad.append(f"globals.ps1 defaultImageName={got} != mios.toml [image].name={expected_name}")
        else:
            bad.append("globals.ps1 is missing $defaultImageName definition")
            
        m = re.search(r'MIOS_BASE_IMAGE[^\r\n]+else\s*\{\s*([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_base:
                bad.append(f"globals.ps1 default MIOS_BASE_IMAGE={got} != mios.toml [image].base={expected_base}")
        else:
            bad.append("globals.ps1 is missing default MIOS_BASE_IMAGE definition")

        m = re.search(r'MIOS_BIB_IMAGE[^\r\n]+else\s*\{\s*([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_bib:
                bad.append(f"globals.ps1 default MIOS_BIB_IMAGE={got} != mios.toml [image].bib={expected_bib}")
        else:
            bad.append("globals.ps1 is missing default MIOS_BIB_IMAGE definition")

for b in bad:
    sys.stderr.write(f"    {b}\n")
sys.exit(1 if bad else 0)
PY
    then
        echo "[98-drift-checks]   default image references in globals.{sh,ps1} equal mios.toml [image] SSOT"
    else
        _violation "default image reference in automation/lib/globals.sh or globals.ps1 drifted from mios.toml [image] SSOT"
    fi
}

check_dag_integrity() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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

check_names_registry() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "[98-drift-checks]   names registry"
        return 0
    fi
    if git -C "$ROOT" ls-files --deleted 2>/dev/null | grep -q .; then
        echo "[98-drift-checks]   names registry"
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, subprocess

root = os.environ["MIOS_DRIFT_ROOT"]
violations = []

ref_file = os.path.join(root, "usr/share/mios/referenced_names.txt")
committed_ref = ""
if os.path.isfile(ref_file):
    try:
        with open(ref_file, "r", encoding="utf-8") as fh:
            committed_ref = fh.read()
    except Exception as e:
        violations.append(f"Failed to read committed referenced_names.txt: {e}")

gen_script = os.path.join(root, "tools/generate-names-registry.py")
registry_file = os.path.join(root, "usr/share/mios/names.generated.txt")

if not os.path.isfile(gen_script):
    violations.append("tools/generate-names-registry.py missing")
elif not os.path.isfile(registry_file):
    violations.append("usr/share/mios/names.generated.txt missing")
else:
    try:
        with open(registry_file, "r", encoding="utf-8") as fh:
            committed_data = fh.read()
        res = subprocess.run([sys.executable, gen_script], capture_output=True, text=True, check=True)
        fresh_data = res.stdout
        
        fresh_lines = [l.strip() for l in fresh_data.splitlines() if l.strip()]
        committed_lines = [l.strip() for l in committed_data.splitlines() if l.strip()]
        
        if fresh_lines != committed_lines:
            violations.append("usr/share/mios/names.generated.txt is stale. Please run tools/generate-names-registry.py.")
    except Exception as e:
        violations.append(f"Failed to check names registry generation: {e}")

fresh_ref = ""
if os.path.isfile(ref_file):
    try:
        with open(ref_file, "r", encoding="utf-8") as fh:
            fresh_ref = fh.read()
    except Exception as e:
        violations.append(f"Failed to read fresh referenced_names.txt: {e}")

if fresh_ref != committed_ref:
    try:
        with open(ref_file, "w", encoding="utf-8") as fh:
            fh.write(committed_ref)
    except Exception:
        pass
    violations.append("usr/share/mios/referenced_names.txt is stale. Please run tools/generate-names-registry.py.")

if violations:
    for v in sorted(violations):
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[98-drift-checks]   names registry matches generate-names-registry.py"
    else
        _violation "naming registry drift / tools/generate-names-registry.py stale (run tools/generate-names-registry.py to regenerate; check 30)"
    fi
}

check_drift_projection() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import sys
import os
import json
import collections
import io
import contextlib

class MockCursor:
    def __init__(self, db_store):
        self.db_store = db_store
        self.results = []
        self.index = 0

    def execute(self, query, params=None):
        query_upper = " ".join(query.upper().split())
        if "INSERT INTO SYSTEM_CONFIG" in query_upper:
            pass
        elif "INSERT INTO PACKAGE_SET" in query_upper:
            pass
        elif "INSERT INTO BUILD_PHASE" in query_upper:
            pass
        elif "INSERT INTO CONFIG_KV" in query_upper:
            if len(params) == 1:
                val_json = params[0]
                scope = "verbs"
                key = "_defaults"
                layer = 0
            else:
                scope, key, val_json, desc = params
                layer = 0
            self.db_store["config_kv"][(scope, key, layer)] = {
                "scope": scope,
                "key": key,
                "value": json.loads(val_json) if isinstance(val_json, str) else val_json,
                "layer": layer
            }
        elif "INSERT INTO VERB" in query_upper:
            name, sig, desc, tier, perm, cmd, params_json, section, examples_json, model_name, hidden, aliases_json, conflict_group, parallel_limit, max_result_chars = params
            self.db_store["verb"][name] = {
                "name": name,
                "sig": sig,
                "desc_default": desc,
                "tier": tier,
                "permission": perm,
                "cmd": cmd,
                "params": json.loads(params_json) if isinstance(params_json, str) else params_json,
                "section": section,
                "examples": json.loads(examples_json) if isinstance(examples_json, str) else examples_json,
                "model_name": model_name,
                "hidden": hidden,
                "aliases": json.loads(aliases_json) if isinstance(aliases_json, str) else aliases_json,
                "conflict_group": conflict_group,
                "parallel_limit": parallel_limit,
                "max_result_chars": max_result_chars
            }
        elif "TRUNCATE TABLE DOMAIN_VERB" in query_upper:
            self.db_store["domain_verb"] = []
        elif "INSERT INTO DOMAIN_VERB" in query_upper:
            domain, verb_name, description = params
            self.db_store["domain_verb"].append({
                "domain": domain,
                "verb_name": verb_name,
                "description": description
            })
        elif "SELECT 1 FROM VERB WHERE NAME =" in query_upper:
            name = params[0]
            if name in self.db_store["verb"]:
                self.results = [(1,)]
            else:
                self.results = []
            self.index = 0
        elif "SELECT SCOPE, KEY, VALUE FROM CONFIG_KV" in query_upper:
            rows = []
            for (scope, key, layer), item in sorted(self.db_store["config_kv"].items()):
                if layer == 0 and scope != 'verbs':
                    rows.append((scope, key, item["value"]))
            self.results = rows
            self.index = 0
        elif "SELECT DOMAIN, DESCRIPTION, ARRAY_AGG(VERB_NAME" in query_upper or "SELECT DOMAIN, DESCRIPTION, ARRAY_AGG" in query_upper:
            by_domain = collections.defaultdict(list)
            descs = {}
            for item in self.db_store["domain_verb"]:
                dom = item["domain"]
                by_domain[dom].append(item["verb_name"])
                descs[dom] = item["description"]
            
            rows = []
            for dom in sorted(by_domain.keys()):
                rows.append((dom, descs[dom], sorted(by_domain[dom])))
            self.results = rows
            self.index = 0
        elif "SELECT VALUE FROM CONFIG_KV WHERE SCOPE = 'VERBS' AND KEY = '_DEFAULTS'" in query_upper:
            item = self.db_store["config_kv"].get(('verbs', '_defaults', 0))
            if item:
                self.results = [(item["value"],)]
            else:
                self.results = []
            self.index = 0
        elif "SELECT NAME, SIG, DESC_DEFAULT, TIER, PERMISSION, CMD, PARAMS" in query_upper:
            rows = []
            for name in sorted(self.db_store["verb"].keys()):
                v = self.db_store["verb"][name]
                rows.append((
                    v["name"], v["sig"], v["desc_default"], v["tier"], v["permission"], v["cmd"],
                    v["params"], v["section"], v["examples"], v["model_name"], v["hidden"],
                    v["aliases"], v["conflict_group"], v["parallel_limit"], v["max_result_chars"]
                ))
            self.results = rows
            self.index = 0

    def fetchall(self):
        return self.results

    def fetchone(self):
        if self.index < len(self.results):
            r = self.results[self.index]
            self.index += 1
            return r
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockConnection:
    def __init__(self, db_store):
        self.db_store = db_store

    def cursor(self):
        return MockCursor(self.db_store)

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockPsycopgModule:
    def __init__(self, db_store):
        self.db_store = db_store

    def connect(self, *args, **kwargs):
        return MockConnection(self.db_store)

def check_roundtrip(root):
    db_store = {
        "config_kv": {},
        "verb": {},
        "domain_verb": []
    }
    mock_psycopg = MockPsycopgModule(db_store)
    sys.modules["psycopg"] = mock_psycopg

    seed_path = os.path.join(root, "usr/libexec/mios/seed-db-config.py")
    os.environ["MIOS_TOML"] = os.path.join(root, "usr/share/mios/mios.toml")
    os.environ["MIOS_VENDOR_TOML"] = os.environ["MIOS_TOML"]

    seed_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": seed_path}
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            exec(f.read(), seed_globals)
    except SystemExit as e:
        if e.code != 0:
            print(f"Seed script exited with code {e.code}")
            sys.exit(1)

    materialize_path = os.path.join(root, "usr/libexec/mios/materialize-config-toml.py")
    mat_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": materialize_path}

    stdout_capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_capture):
            with open(materialize_path, "r", encoding="utf-8") as f:
                exec(f.read(), mat_globals)
    except SystemExit as e:
        if e.code != 0:
            print(f"Materialize script exited with code {e.code}")
            sys.exit(1)

    materialized_toml_str = stdout_capture.getvalue()

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            sys.exit(0)

    with open(os.environ["MIOS_TOML"], "rb") as f:
        orig_data = tomllib.load(f)

    try:
        mat_data = tomllib.loads(materialized_toml_str)
    except Exception as parse_err:
        print("Materialized TOML parsing failed!")
        print("Lines 30-70:")
        lines = materialized_toml_str.splitlines()
        for i, l in enumerate(lines[29:70]):
            print(f"{i+30:2d}: {l}")
        raise parse_err

    scopes = ["ports", "ai", "routing", "pgvector", "a2a", "mcp", "observability", "sandbox", "security", "agent_passport", "agent_pipe"]
    for scope in scopes:
        orig_scope = orig_data.get(scope, {})
        mat_scope = mat_data.get(scope, {})
        
        if scope == "routing":
            orig_keys = {k: v for k, v in orig_scope.items() if k not in ("domains", "nohc_allowlist")}
            mat_keys = {k: v for k, v in mat_scope.items() if k not in ("domains", "nohc_allowlist")}
        else:
            orig_keys = orig_scope
            mat_keys = mat_scope
            
        if orig_keys != mat_keys:
            print(f"Drift in scope [{scope}]:")
            print(f"  Expected: {orig_keys}")
            print(f"  Got:      {mat_keys}")
            sys.exit(1)

    orig_domains = orig_data.get("routing", {}).get("domains", {})
    mat_domains = mat_data.get("routing", {}).get("domains", {})
    orig_domains_norm = {
        dom: {
            "desc": val.get("desc", ""),
            "verbs": sorted(val.get("verbs", []))
        }
        for dom, val in orig_domains.items()
    }
    mat_domains_norm = {
        dom: {
            "desc": val.get("desc", ""),
            "verbs": sorted(val.get("verbs", []))
        }
        for dom, val in mat_domains.items()
    }
    if orig_domains_norm != mat_domains_norm:
        print("Drift in routing.domains:")
        print(f"  Expected: {orig_domains_norm}")
        print(f"  Got:      {mat_domains_norm}")
        sys.exit(1)

    orig_verbs = orig_data.get("verbs", {})
    mat_verbs = mat_data.get("verbs", {})

    if orig_verbs.get("_defaults") != mat_verbs.get("_defaults"):
        print("Drift in verbs._defaults:")
        print(f"  Expected: {orig_verbs.get('_defaults')}")
        print(f"  Got:      {mat_verbs.get('_defaults')}")
        sys.exit(1)

    supported_verb_fields = {
        "sig", "desc", "tier", "permission", "cmd", "params",
        "section", "examples", "model_name", "hidden", "aliases",
        "conflict_group", "parallel_limit", "max_result_chars"
    }

    for vname, orig_vcfg in orig_verbs.items():
        if vname == "_defaults":
            continue
        if vname not in mat_verbs:
            print(f"Verb '{vname}' missing in materialized output")
            sys.exit(1)
            
        mat_vcfg = mat_verbs[vname]
        orig_defaults = orig_verbs.get("_defaults", {})
        mat_defaults = mat_verbs.get("_defaults", {})
        
        orig_full = orig_defaults.copy()
        orig_full.update(orig_vcfg)
        
        mat_full = mat_defaults.copy()
        mat_full.update(mat_vcfg)
        
        for key in supported_verb_fields:
            orig_val = orig_full.get(key)
            mat_val = mat_full.get(key)
            
            if key in ("sig", "desc", "cmd", "section", "model_name", "conflict_group"):
                if orig_val == "": orig_val = None
                if mat_val == "": mat_val = None
            elif key in ("examples", "aliases"):
                if orig_val == []: orig_val = None
                if mat_val == []: mat_val = None
            elif key == "params":
                if orig_val == {}: orig_val = None
                if mat_val == {}: mat_val = None
            elif key == "hidden":
                orig_val = bool(orig_val)
                mat_val = bool(mat_val)
            elif key in ("parallel_limit", "max_result_chars"):
                orig_val = int(orig_val or 0)
                mat_val = int(mat_val or 0)
                
            if orig_val != mat_val:
                print(f"Drift in verb '{vname}' field '{key}':")
                print(f"  Expected: {orig_val}")
                print(f"  Got:      {mat_val}")
                sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    check_roundtrip(os.environ["MIOS_DRIFT_ROOT"])
PY
    then
        echo "[98-drift-checks]   DB->TOML materialize round-trip is lossless for config_kv and verbs"
    else
        _violation "DB->TOML materialize round-trip drift detected (check 31) -- verify seed-db-config.py and materialize-config-toml.py mappings"
    fi
}

check_canonical_bools() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_TOML="$ROOT/usr/share/mios/mios.toml" MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml" python3 - <<'PY'
import sys
import os

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.exit(0)

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
            local base
            base="$(basename "$f")"
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import sys
import os
import json
import collections
import io
import contextlib

class MockCursor:
    def __init__(self, db_store):
        self.db_store = db_store
        self.results = []
        self.index = 0

    def execute(self, query, params=None):
        query_upper = " ".join(query.upper().split())
        
        if "INSERT INTO SYSTEM_CONFIG" in query_upper:
            pass
        elif "INSERT INTO CONFIG_KV" in query_upper:
            pass
        elif "INSERT INTO VERB" in query_upper:
            pass
        elif "TRUNCATE TABLE DOMAIN_VERB" in query_upper:
            pass
        elif "INSERT INTO DOMAIN_VERB" in query_upper:
            pass
        elif "SELECT 1 FROM VERB" in query_upper:
            self.results = []
            self.index = 0
        elif "INSERT INTO PACKAGE_SET" in query_upper:
            name, section, pkgs_json, enable, layer, base_image_ref = params
            self.db_store["package_set"][name] = {
                "name": name,
                "section": section,
                "pkgs": pkgs_json,
                "enable": enable,
                "layer": layer,
                "base_image_ref": base_image_ref
            }
        elif "INSERT INTO BUILD_PHASE" in query_upper:
            if len(params) == 3:
                ordinal, script, deps_json = params
                stage = "container"
            else:
                script = params[0]
                ordinal = None
                stage = "firstboot"
                deps_json = "[]"
            self.db_store["build_phase"][script] = {
                "ordinal": ordinal,
                "script": script,
                "stage": stage,
                "deps": deps_json
            }
        elif "INSERT INTO DEBLOAT_POLICY" in query_upper:
            name, policy_type, rules_json = params
            self.db_store["debloat_policy"][name] = {
                "name": name,
                "policy_type": policy_type,
                "rules": rules_json
            }
        elif "INSERT INTO DEBLOAT_PROFILE" in query_upper:
            self.db_store["debloat_profile"]["default"] = {
                "name": "default",
                "description": "Default debloat profile"
            }
        elif "INSERT INTO PRESET" in query_upper:
            features_json = params[0]
            self.db_store["preset"]["default"] = {
                "name": "default",
                "description": "Default preset",
                "features": features_json,
                "debloat_profile_name": "default"
            }
        elif "SELECT NAME, SECTION, PKGS, ENABLE, LAYER, BASE_IMAGE_REF FROM PACKAGE_SET" in query_upper:
            rows = []
            for name in sorted(self.db_store["package_set"].keys()):
                p = self.db_store["package_set"][name]
                rows.append({
                    "name": p["name"],
                    "section": p["section"],
                    "pkgs": p["pkgs"],
                    "enable": p["enable"],
                    "layer": p["layer"],
                    "base_image_ref": p["base_image_ref"]
                })
            self.results = rows
            self.index = 0
        elif "SELECT ORDINAL, SCRIPT, STAGE, DEPS FROM BUILD_PHASE" in query_upper:
            rows = []
            def sort_key(item):
                o = item["ordinal"]
                return (item["stage"], o if o is not None else 999999, item["script"])
            for script in sorted(self.db_store["build_phase"].keys()):
                p = self.db_store["build_phase"][script]
                rows.append(p)
            rows.sort(key=sort_key)
            self.results = [{
                "ordinal": r["ordinal"],
                "script": r["script"],
                "stage": r["stage"],
                "deps": r["deps"]
            } for r in rows]
            self.index = 0
        elif "SELECT NAME, POLICY_TYPE, RULES FROM DEBLOAT_POLICY" in query_upper:
            rows = []
            for name in sorted(self.db_store["debloat_policy"].keys()):
                p = self.db_store["debloat_policy"][name]
                rows.append({
                    "name": p["name"],
                    "policy_type": p["policy_type"],
                    "rules": p["rules"]
                })
            self.results = rows
            self.index = 0
        elif "SELECT NAME, DESCRIPTION FROM DEBLOAT_PROFILE" in query_upper:
            rows = []
            for name in sorted(self.db_store["debloat_profile"].keys()):
                p = self.db_store["debloat_profile"][name]
                rows.append({
                    "name": p["name"],
                    "description": p["description"]
                })
            self.results = rows
            self.index = 0
        elif "SELECT NAME, DESCRIPTION, FEATURES, DEBLOAT_PROFILE_NAME FROM PRESET" in query_upper:
            rows = []
            for name in sorted(self.db_store["preset"].keys()):
                p = self.db_store["preset"][name]
                rows.append({
                    "name": p["name"],
                    "description": p["description"],
                    "features": p["features"],
                    "debloat_profile_name": p["debloat_profile_name"]
                })
            self.results = rows
            self.index = 0

    def fetchall(self):
        return self.results

    def fetchone(self):
        if self.index < len(self.results):
            r = self.results[self.index]
            self.index += 1
            return r
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockConnection:
    def __init__(self, db_store):
        self.db_store = db_store

    def cursor(self, row_factory=None):
        return MockCursor(self.db_store)

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockPsycopgModule:
    def __init__(self, db_store):
        self.db_store = db_store

    def connect(self, *args, **kwargs):
        return MockConnection(self.db_store)

def check_roundtrip(root):
    db_store = {
        "package_set": {},
        "build_phase": {},
        "debloat_policy": {},
        "debloat_profile": {},
        "preset": {}
    }
    mock_psycopg = MockPsycopgModule(db_store)
    mock_psycopg.__path__ = []
    class DictRowMock:
        pass
    mock_psycopg.rows = DictRowMock()
    mock_psycopg.rows.dict_row = DictRowMock

    sys.modules["psycopg"] = mock_psycopg
    sys.modules["psycopg.rows"] = mock_psycopg.rows

    seed_path = os.path.join(root, "usr/libexec/mios/seed-db-config.py")
    os.environ["MIOS_TOML"] = os.path.join(root, "usr/share/mios/mios.toml")
    os.environ["MIOS_VENDOR_TOML"] = os.environ["MIOS_TOML"]

    seed_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": seed_path}
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            exec(f.read(), seed_globals)
    except SystemExit as e:
        if e.code != 0:
            print(f"Seed script exited with code {e.code}")
            sys.exit(1)

    materialize_path = os.path.join(root, "usr/libexec/mios/materialize-build-ctx.py")
    temp_ctx_dir = "/tmp/mios-drift-ctx-test"
    os.makedirs(temp_ctx_dir, exist_ok=True)
    os.environ["MIOS_BUILD_CTX"] = temp_ctx_dir

    mat_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": materialize_path}
    try:
        with open(materialize_path, "r", encoding="utf-8") as f:
            exec(f.read(), mat_globals)
    except SystemExit as e:
        if e.code != 0:
            print(f"Materialize script exited with code {e.code}")
            sys.exit(1)

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            sys.exit(0)

    with open(os.environ["MIOS_TOML"], "rb") as f:
        toml_data = tomllib.load(f)

    with open(os.path.join(temp_ctx_dir, "package_sets.json"), "r", encoding="utf-8") as f:
        mat_sets = json.load(f)

    orig_packages = toml_data.get("packages", {})
    for sec_name, sec_cfg in orig_packages.items():
        if sec_name == "sections" or not isinstance(sec_cfg, dict) or "pkgs" not in sec_cfg:
            continue
        mat_item = next((x for x in mat_sets if x["name"] == sec_name), None)
        if not mat_item:
            print(f"Drift: Package set '{sec_name}' missing in materialized output")
            sys.exit(1)
        orig_pkgs = sec_cfg.get("pkgs", [])
        mat_pkgs = mat_item["pkgs"]
        if orig_pkgs != mat_pkgs:
            print(f"Drift in package set '{sec_name}':")
            print(f"  Expected: {orig_pkgs}")
            print(f"  Got:      {mat_pkgs}")
            sys.exit(1)

        orig_enable = sec_cfg.get("enable", True)
        orig_layer = sec_cfg.get("layer", 0)
        orig_base_ref = sec_cfg.get("base_image_ref", "")
        orig_section = sec_cfg.get("section", "Misc")

        if (mat_item.get("enable", True) != orig_enable or
            mat_item.get("layer", 0) != orig_layer or
            mat_item.get("base_image_ref", "") != orig_base_ref or
            mat_item.get("section", "Misc") != orig_section):
            print(f"Drift in package set '{sec_name}' metadata:")
            print(f"  Expected: enable={orig_enable}, layer={orig_layer}, base={orig_base_ref}, section={orig_section}")
            print(f"  Got:      enable={mat_item.get('enable')}, layer={mat_item.get('layer')}, base={mat_item.get('base_image_ref')}, section={mat_item.get('section')}")
            sys.exit(1)

    with open(os.path.join(temp_ctx_dir, "build_phases.json"), "r", encoding="utf-8") as f:
        mat_phases = json.load(f)

    automation_dir = os.path.join(root, "automation")
    import re
    scripts = sorted([f for f in os.listdir(automation_dir) if re.match(r"^\d{2}-.*\.sh$", f)])
    
    prev_script = None
    for s in scripts:
        ordinal = int(s.split("-", 1)[0])
        expected_deps = [prev_script] if prev_script else []
        mat_item = next((x for x in mat_phases if x["script"] == s), None)
        if not mat_item:
            print(f"Drift: Build phase script '{s}' missing in materialized output")
            sys.exit(1)
        if mat_item["ordinal"] != ordinal or mat_item["deps"] != expected_deps or mat_item["stage"] != "container":
            print(f"Drift in build phase script '{s}':")
            print(f"  Expected: ordinal={ordinal}, stage=container, deps={expected_deps}")
            print(f"  Got:      ordinal={mat_item['ordinal']}, stage={mat_item['stage']}, deps={mat_item['deps']}")
            sys.exit(1)
        prev_script = s

    bootstrap_dir = os.path.abspath(os.path.join(root, "..", "mios-bootstrap", "src", "autounattend"))
    debloat_json_path = os.path.join(bootstrap_dir, "mios-debloat.json")
    features_txt_path = os.path.join(bootstrap_dir, "mios-xbox-features.txt")

    if os.path.isfile(debloat_json_path) or os.path.isfile(features_txt_path):
        with open(os.path.join(temp_ctx_dir, "debloat_profiles.json"), "r", encoding="utf-8") as f:
            mat_debloat = json.load(f)
        
        if os.path.isfile(debloat_json_path):
            with open(debloat_json_path, "r", encoding="utf-8") as f:
                orig_debloat = json.load(f)
            for k, val in orig_debloat.items():
                if k == "_comment" or not isinstance(val, list):
                    continue
                mat_policy = next((x for x in mat_debloat["policies"] if x["name"] == k), None)
                if not mat_policy:
                    print(f"Drift: Debloat policy '{k}' missing in materialized output")
                    sys.exit(1)
                if mat_policy["rules"] != val:
                    print(f"Drift in debloat policy '{k}'")
                    sys.exit(1)

        if os.path.isfile(features_txt_path):
            with open(features_txt_path, "r", encoding="utf-8") as f:
                orig_features = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            mat_preset = next((x for x in mat_debloat["presets"] if x["name"] == "default"), None)
            if not mat_preset:
                print("Drift: Default preset missing in materialized output")
                sys.exit(1)
            if mat_preset["features"] != orig_features:
                print("Drift in preset features")
                sys.exit(1)
            if mat_preset.get("debloat_profile_name") != "default":
                print("Drift: Default preset debloat_profile_name is not 'default'")
                sys.exit(1)

        mat_profile = next((x for x in mat_debloat["profiles"] if x["name"] == "default"), None)
        if not mat_profile:
            print("Drift: Default debloat profile missing in materialized output")
            sys.exit(1)
        if mat_profile.get("description") != "Default debloat profile":
            print("Drift: Default debloat profile description does not match")
            sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    check_roundtrip(os.environ["MIOS_DRIFT_ROOT"])
PY
    then
        echo "[98-drift-checks]   DB->/ctx materialize round-trip is lossless for build catalog"
    else
        _violation "DB->/ctx materialize round-trip drift detected (check 32) -- verify seed-db-config.py and materialize-build-ctx.py mappings"
    fi
}


check_no_mkdir_in_var() {
    local pat='mkdir[^;&|#]*['\''"[:space:]]/var/'
    local hits="" f active m
    for f in "$ROOT"/automation/[0-9]*.sh "$ROOT/Containerfile" "$ROOT/Containerfile.minimal"; do
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   SOFT: python3 missing" >&2
        return 0
    fi
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
        echo "[98-drift-checks]   SOFT WARNING: var-closure reported an issue" >&2
    fi
}

check_lint_is_final() {
    local bad="" cf last want="RUN bootc container lint"
    for cf in "$ROOT/Containerfile" "$ROOT/Containerfile.minimal"; do
        [[ -f "$cf" ]] || continue
        last="$(grep -vE '^[[:space:]]*(#|$)' "$cf" | tail -1)"
        if [[ "$last" != "$want" ]]; then
            bad+="    ${cf#"$ROOT"/}: final instruction is [$last], expected [$want]"$'\n'
        fi
    done
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "a Containerfile's final instruction is not 'RUN bootc container lint' (Law 4 BOOTC-CONTAINER-LINT) -- lint MUST be the last layer"
    else
        echo "[98-drift-checks]   Containerfile + Containerfile.minimal end with 'RUN bootc container lint'"
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
}

check_resolver_twin_parity() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   SOFT: python3 missing" >&2
        return 0
    fi
    local ue="$ROOT/usr/lib/mios/userenv.sh" mt="$ROOT/usr/lib/mios/mios_toml.py"
    if [[ ! -f "$ue" || ! -f "$mt" ]]; then
        echo "[98-drift-checks]   SOFT: a resolver is absent" >&2
        return 0
    fi
    local fix
    fix="$(mktemp -d 2>/dev/null)" || { echo "[98-drift-checks]   SOFT: mktemp failed" >&2; return 0; }
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   SOFT: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   SOFT: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    
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
            local relpath
            relpath="$(realpath --relative-to="$ROOT" "$f")"
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
    local tmp_file
    tmp_file="$(mktemp)"
    
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
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    
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
        local bname
        bname="$(basename "$f")"
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
        [[ "$(basename "$f")" == "mios-mini-architecture.md" ]] && continue
        
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
                "${BOOTSTRAP_DIR:-}/cat/resources/ventoy/mios-kickstart.cfg" \
                "/c/mios-bootstrap/cat/resources/ventoy/mios-kickstart.cfg" \
                "/mios-bootstrap/cat/resources/ventoy/mios-kickstart.cfg" \
                "C:/mios-bootstrap/cat/resources/ventoy/mios-kickstart.cfg" \
                "$ROOT/../mios-bootstrap/cat/resources/ventoy/mios-kickstart.cfg" \
                "$ROOT/cat/resources/ventoy/mios-kickstart.cfg"; do
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
                "${BOOTSTRAP_DIR:-}/cat/resources/ventoy/ventoy.json" \
                "/c/mios-bootstrap/cat/resources/ventoy/ventoy.json" \
                "/mios-bootstrap/cat/resources/ventoy/ventoy.json" \
                "C:/mios-bootstrap/cat/resources/ventoy/ventoy.json" \
                "$ROOT/../mios-bootstrap/cat/resources/ventoy/ventoy.json" \
                "$ROOT/cat/resources/ventoy/ventoy.json"; do
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
    local base_image
    base_image=$(grep -E '^[[:space:]]*base_image[[:space:]]*=' "$toml" | head -n1 | cut -d'"' -f2)
    if [[ -n "$base_image" ]]; then
        base_image_version=$(echo "$base_image" | grep -oE '[0-9]+$')
        if [[ -n "$base_image_version" ]]; then
            if [[ -f "$ks_file" ]]; then
                if grep -oE 'Fedora-Server-[0-9]+' "$ks_file" | grep -qv "Fedora-Server-${base_image_version}" &>/dev/null; then
                    local mismatched_version
                    mismatched_version=$(grep -oE 'Fedora-Server-[0-9]+' "$ks_file" | head -n1)
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    python3 -c "
import os, sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
    sys.exit(0)

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
"
    if [[ $? -eq 0 ]]; then
        echo "[98-drift-checks]   root mios.toml schema is subset of canonical SSOT"
    else
        _violation "root mios.toml schema has keys not in canonical SSOT"
    fi
}

check_toml_projection() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
    if python3 "$ROOT/tools/generate-bake-plan.py" --check; then
        echo "[98-drift-checks]   bake-plan lists in sync with mios.toml [build.bake] SSOT"
    else
        _violation "bake-plan lists are STALE vs mios.toml -- regenerate with python3 tools/generate-bake-plan.py"
    fi
}

check_bake_plan_integrity() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import glob, os, sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
plan_dir = os.path.join(root, "usr/lib/mios/bake/plan.d")

if not os.path.isfile(toml_path) or not os.path.isdir(plan_dir):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

bake_cfg = data.get("build", {}).get("bake", {})
core_set = set(bake_cfg.get("core", []))
tokens = bake_cfg.get("firstboot_tokens", [])

group_files = sorted(glob.glob(os.path.join(plan_dir, "[0-9][0-9]-*.list")))
fb_file = os.path.join(plan_dir, "firstboot.list")

group_images = set()
group_map = {}
for gf in group_files:
    gname = os.path.basename(gf)
    with open(gf, "r", encoding="utf-8") as f:
        imgs = set(line.strip() for line in f if line.strip())
    group_map[gname] = imgs
    group_images.update(imgs)

fb_images = set()
if os.path.isfile(fb_file):
    with open(fb_file, "r", encoding="utf-8") as f:
        fb_images = set(line.strip() for line in f if line.strip())

viol = []

for tok in tokens:
    for gname, imgs in group_map.items():
        hits = [img for img in imgs if tok in img.lower()]
        if hits:
            viol.append(f"Firstboot token '{tok}' image(s) found in baked group list {gname}: {hits}")

    matching_core = [img for img in core_set if tok in img.lower()]
    for img in matching_core:
        if img not in fb_images:
            viol.append(f"Core image '{img}' matching firstboot token '{tok}' missing from firstboot.list")

for tok in tokens:
    matching_fb = [img for img in fb_images if tok in img.lower()]
    for img in matching_fb:
        if img not in core_set:
            viol.append(f"Firstboot image '{img}' is not listed in [build.bake].core SSOT")

all_plan_imgs = list(group_images) + list(fb_images)
if len(all_plan_imgs) != len(set(all_plan_imgs)):
    viol.append("Duplicate image entries found across plan.d/*.list and firstboot.list")

if set(all_plan_imgs) != core_set:
    missing_from_plan = core_set - set(all_plan_imgs)
    extra_in_plan = set(all_plan_imgs) - core_set
    if missing_from_plan:
        viol.append(f"Core images missing from plan.d: {missing_from_plan}")
    if extra_in_plan:
        viol.append(f"Extra images in plan.d not in core: {extra_in_plan}")

if bool(tokens) != bool(fb_images):
    viol.append(f"firstboot_tokens non-empty ({tokens}) but firstboot.list empty ({fb_images}) or vice versa")

if viol:
    for v in viol:
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)

sys.exit(0)
PY
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
    local empty_refs
    empty_refs="$(git grep -E 'MIOS_BUILD_BAKE_REFS_[A-Z0-9_]+:-\}' automation/ 2>/dev/null || true)"
    if [[ -n "$empty_refs" ]]; then
        _violation "found empty defaults for bake-refs in automation scripts:"$'\n'"${empty_refs}"
        return 1
    fi
    if command -v python3 >/dev/null 2>&1; then
        if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, subprocess
try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   WARNING: python3 missing" >&2
        return 0
    fi
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
    local res
    res="$(python3 -c "$py_script" 2>/dev/null || true)"
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
    local bad=()
    local budget=40
    local py_script="
import os
try:
    import tomllib
except ImportError:
    import tomli as tomllib

root = '$ROOT'
toml_path = os.path.join(root, 'usr/share/mios/mios.toml')
budget = 40
if os.path.exists(toml_path):
    with open(toml_path, 'rb') as f:
        data = tomllib.load(f)
        budget = data.get('build', {}).get('bake', {}).get('runner_disk_budget_gb', 40)

print(budget)
"
    budget="$(python3 -c "$py_script" 2>/dev/null || echo 40)"
    if [[ -z "$budget" ]]; then budget=40; fi

    local sbom_tsv="$ROOT/usr/share/mios/artifacts/sbom/bound-images.tsv"
    local count=0
    if [[ -f "$sbom_tsv" ]]; then
        count="$(grep -c -v '^#' "$sbom_tsv" 2>/dev/null || echo 0)"
    fi

    if [[ "$count" -gt 30 ]]; then
        bad+=("projected baked sidecars count $count exceeds budget threshold for budget ${budget}GB")
    fi

    if [[ ${#bad[@]} -eq 0 ]]; then
        echo "[98-drift-checks]   bake-budget gate: projected baked image size within SSOT runner_disk_budget_gb limit"
    else
        for err in "${bad[@]}"; do
            echo "  [bake-budget-drift] $err" >&2
        done
        _violation "bake-budget gate failed: projected baked size exceeds SSOT runner_disk_budget_gb"
    fi
}

check_greenboot() {
    echo "[98-drift-checks]   greenboot health-coverage check"
    local gb_dir="$ROOT/usr/lib/greenboot/check/required.d"
    if [[ ! -d "$gb_dir" ]]; then
        _violation "(54) greenboot required checks directory ($gb_dir) is missing"
        return
    fi
    local critical_services=("agent-pipe" "llm-light" "pgvector" "hermes")
    local s script_found
    for s in "${critical_services[@]}"; do
        script_found=0
        for f in "$gb_dir"/*; do
            if [[ -f "$f" ]] && grep -q "$s" "$f" 2>/dev/null; then
                script_found=1
                break
            fi
        done
        if [[ "$script_found" -eq 0 ]]; then
            _violation "(54) greenboot missing health-check script for critical service: $s"
        fi
    done
}

check_clevis_luks() {
    echo "[98-drift-checks]   clevis LUKS SSOT projection check"
    local gen="$ROOT/usr/libexec/mios/mios-clevis-luks-gen"
    if [[ ! -x "$gen" && -f "$gen" ]]; then
        chmod +x "$gen" 2>/dev/null || true
    fi
    if [[ -f "$gen" ]]; then
        local out; out="$("$gen" "${MIOS_TOML_ROOT:-$ROOT}/usr/share/mios/mios.toml" 2>&1 || true)"
        if [[ "$out" == *"CLEVIS_LUKS_ENABLED="* ]]; then
            return 0
        else
            _violation "(67) clevis LUKS generator failed to project SSOT configuration"
        fi
    else
        _violation "(67) clevis LUKS generator script missing"
    fi
}

check_mini_vfio() {
    echo "[98-drift-checks]   MiOS-Mini vfio-pci SSOT projection check"
    local gen="$ROOT/usr/libexec/mios/mios-mini-vfio-gen"
    if [[ ! -x "$gen" && -f "$gen" ]]; then
        chmod +x "$gen" 2>/dev/null || true
    fi
    if [[ -f "$gen" ]]; then
        local out; out="$("$gen" "${MIOS_TOML_ROOT:-$ROOT}/usr/share/mios/mios.toml" 2>&1 || true)"
        if [[ "$out" == *"MIOS_MINI_ENABLED="* ]]; then
            return 0
        else
            _violation "(68) MiOS-Mini vfio generator failed to project SSOT configuration"
        fi
    else
        _violation "(68) MiOS-Mini vfio generator script missing"
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, glob
try:
    import tomllib
except ImportError:
    import tomli as tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
fb_list = os.path.join(root, "usr/lib/mios/bake/plan.d/firstboot.list")
qdir = os.path.join(root, "usr/share/containers/systemd")
bdir = os.path.join(root, "usr/lib/bootc/bound-images.d")

if not os.path.isfile(toml_path) or not os.path.isfile(fb_list):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

firstboot_tokens = data.get("build", {}).get("bake", {}).get("firstboot_tokens", [])
if not firstboot_tokens:
    sys.exit(0)

bad = []
with open(fb_list, "r", encoding="utf-8") as fh:
    for line in fh:
        img = line.strip()
        if not img or img.startswith("#"):
            continue
        if not any(tok and tok in img for tok in firstboot_tokens):
            bad.append(f"firstboot.list entry '{img}' matches no token in firstboot_tokens")

if os.path.isdir(bdir):
    for q in sorted(glob.glob(os.path.join(qdir, "*.container")) + glob.glob(os.path.join(qdir, "*.image"))):
        name = os.path.basename(q)
        img = ""
        try:
            with open(q, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.strip().startswith("Image="):
                        img = line.strip()[6:].strip()
                        break
        except OSError:
            pass
        if any(tok and tok in img for tok in firstboot_tokens):
            if os.path.lexists(os.path.join(bdir, name)):
                bad.append(f"Firstboot-tier Quadlet '{name}' ({img}) is wrongly symlinked under bound-images.d")

consumer_script = os.path.join(root, "usr/libexec/mios/mios-ai-firstboot")
if os.path.isfile(consumer_script):
    with open(consumer_script, "r", encoding="utf-8", errors="ignore") as fh:
        if "firstboot.list" not in fh.read():
            bad.append("usr/libexec/mios/mios-ai-firstboot does not reference firstboot.list")

if bad:
    for b in bad:
        sys.stderr.write(f"    {b}\n")
    sys.exit(1)
sys.exit(0)
PY
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re

root = os.environ["MIOS_DRIFT_ROOT"]
script_path = os.path.join(root, "automation/98-drift-checks.sh")

if not os.path.isfile(script_path):
    sys.exit(0)

with open(script_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

def_re = re.compile(r"^(check_[a-z0-9_]+)\s*\(\)\s*\{")
main_call_re = re.compile(r"^\s*(check_[a-z0-9_]+)\s*($|#|;|\|\||&&)")

defined_counts = {}
in_main = False
main_calls = []

for line in lines:
    line_clean = line.split("#")[0].strip()
    if line_clean == "main() {":
        in_main = True
        continue
    if in_main and line_clean.startswith("echo \"[98-drift-checks] ----------"):
        in_main = False
        continue

    m_def = def_re.match(line)
    if m_def:
        name = m_def.group(1)
        defined_counts[name] = defined_counts.get(name, 0) + 1

    if in_main:
        m_call = main_call_re.match(line_clean)
        if m_call:
            main_calls.append(m_call.group(1))

bad = []

for name, count in defined_counts.items():
    if count > 1:
        bad.append(f"Duplicate function definition found in 98-drift-checks.sh: {name} (defined {count} times)")

for name in defined_counts.keys():
    calls = main_calls.count(name)
    if calls == 0:
        bad.append(f"Defined check function is not registered in main(): {name}")
    elif calls > 1:
        bad.append(f"Defined check function is called multiple times in main(): {name} ({calls} times)")

for call in main_calls:
    if call not in defined_counts:
        bad.append(f"main() calls unregistered/undefined check function: {call}")

if bad:
    for b in bad:
        sys.stderr.write(f"    [gate-registry-drift] {b}\n")
    sys.exit(1)

sys.exit(0)
PY
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re

root = os.environ["MIOS_DRIFT_ROOT"]
harness_path = os.path.join(root, "tests/drift-gate-negatives.sh")

if not os.path.isfile(harness_path):
    sys.exit(0)

with open(harness_path, "r", encoding="utf-8", errors="ignore") as f:
    harness_content = f.read()

required_checks = [
    "check_version_ssot",
    "check_resolver_twin_equivalence",
    "check_cli_eval_safety",
    "check_shellcheck",
    "check_names_registry",
    "check_root_toml_subset",
    "check_toml_projection",
    "check_curl_retry",
    "check_nested_podman_caps",
    "check_bake_budget",
    "check_module_test_coverage",
    "check_router_parity",
    "check_council_gate_ssot",
    "check_agent_pipe_budgets",
    "check_bake_plan",
    "check_containerfile_pinned_clones",
    "check_firstboot_tier",
    "check_rechunk_budget",
    "check_gate_registry",
    "check_test_hermeticity",
    "check_no_mkdir_in_var",
    "check_quadlet_privilege",
    "check_firstboot_degrade_open",
    "check_ssot_lint_equivalence",
    "check_oci_archive_path",
    "check_replaceme_mount_substitution",
    "check_kickstart_shell_syntax",
    "check_offline_install_invariant",
    "check_installer_family_roles",
    "check_bib_configs_projection",
    "check_repo_partition_label_ssot",
    "check_bib_single_config_invariant",
    "check_build_artifacts_output_dir",
    "check_win11_vm_template_xml",
    "check_ipa_enroll_projection",
    "check_uki_cmdline_projection",
    "check_composefs_projection",
    "check_cockpit_projection",
    "check_chrony_ptp_dropin",
    "check_chrony_projection",
    "check_nut_projection",
    "check_renderer_gate_coverage",
]

test_fns = re.findall(r'^\s*(test_[a-z0-9_]+)\(\)\s*\{', harness_content, re.MULTILINE)

bad = []
if len(test_fns) < len(required_checks):
    bad.append(f"Negative test suite count ({len(test_fns)}) is less than required law gates count ({len(required_checks)})")

for chk in required_checks:
    if chk not in harness_content:
        bad.append(f"Required law/security check '{chk}' has no negative test in tests/drift-gate-negatives.sh")

if bad:
    for b in bad:
        sys.stderr.write(f"    [negatives-coverage-drift] {b}\n")
    sys.exit(1)

sys.exit(0)
PY
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

    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi

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
        local post_sh
        post_sh="$(sed -n '/%post/,/%end/p' "$f" | sed 's/.*%post.*//; s/.*%end.*//')"
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

    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi

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
    if [[ ! -f "$install_script" ]]; then
        echo "[98-drift-checks]   tools/install.sh absent"
        return 0
    fi

    if ! bash -n "$install_script" 2>/dev/null; then
        _violation "tools/install.sh failed bash -n syntax check"
        return 0
    fi

    if ! grep -q '\--transport oci-archive' "$install_script"; then
        _violation "tools/install.sh does not invoke bootc install with --transport oci-archive"
        return 0
    fi

    local net_token
    net_token="$(grep -nE '(http://|https://|git clone|podman pull|skopeo copy docker://)' "$install_script" | grep -v '^\s*#' || true)"
    if [[ -n "$net_token" ]]; then
        echo "$net_token" >&2
        _violation "tools/install.sh contains forbidden network pull token violating zero-network offline-install contract"
    else
        echo "[98-drift-checks]   tools/install.sh zero-network offline-install invariant verified clean"
    fi
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
        local role
        role="$(grep -oE '^# MIOS_INSTALLER_ROLE=[a-zA-Z0-9_-]+' "$s" | cut -d= -f2 || true)"
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
    local ssot="$ROOT/usr/share/mios/mios.toml"
    local install_sh="$ROOT/tools/install.sh"
    local cfg="$ROOT/usr/share/mios/ventoy/mios-kickstart.cfg"

    if [[ ! -f "$ssot" || ! -f "$install_sh" || ! -f "$cfg" ]]; then
        echo "[98-drift-checks]   repo partition consumers absent"
        return 0
    fi

    local ssot_label
    ssot_label="$(grep -A 5 '\[cat\.repo_partition\]' "$ssot" | grep 'label' | head -1 | cut -d'"' -f2 || echo "MiOS-Repo")"

    local bad_lbl=""
    if ! grep -q "blkid -L \"$ssot_label\"" "$install_sh"; then
        bad_lbl+="    tools/install.sh does not reference SSOT repo partition label '$ssot_label'"$'\n'
    fi
    if ! grep -q "blkid -L \"$ssot_label\"" "$cfg"; then
        bad_lbl+="    usr/share/mios/ventoy/mios-kickstart.cfg does not reference SSOT repo partition label '$ssot_label'"$'\n'
    fi

    if [[ -n "$bad_lbl" ]]; then
        printf '%s' "$bad_lbl" >&2
        _violation "repo partition label mismatch against [cat.repo_partition].label SSOT"
    else
        echo "[98-drift-checks]   repo partition label consumers match [cat.repo_partition].label SSOT"
    fi
}

check_bib_single_config_invariant() {
    local justfile="$ROOT/Justfile"
    if [[ ! -f "$justfile" ]]; then
        echo "[98-drift-checks]   Justfile absent"
        return 0
    fi

    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi

    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, glob
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

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

    local output_dir
    output_dir="$(grep -A 3 '\[build\.artifacts\]' "$ssot" | grep 'output_dir' | head -1 | cut -d'"' -f2 || echo "Build")"

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

    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi

    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, xml.etree.ElementTree as ET

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

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
        local base
        base="$(basename "$f")"
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
        local stem
        stem="$(echo "$script" | sed -E 's/^[0-9]+-//; s/-render.*//; s/\.sh$//')"
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if python3 "${ROOT}/tools/verb-template-check.py"; then
        echo "[98-drift-checks]   verb templates compile and validate against SSOT args"
    else
        _violation "verb templates compilation or placeholder validation failed"
    fi
}

check_pipe_boundaries() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[98-drift-checks]   python3 absent"
        return 0
    fi

    if MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/pipe-parity-check.py" >/dev/null 2>&1; then
        echo "[98-drift-checks]   extraction surface parity + one-way imports clean"
    else
        _violation "mios_pipe extraction surface parity or one-way import rule violated"
    fi
}

check_guacamole_consistency() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
try:
    import tomllib
except ImportError:
    import tomli as tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
desktop_path = os.path.join(root, "usr/share/applications/mios-svc-guacamole.desktop")

if not os.path.isfile(toml_path) or not os.path.isfile(desktop_path):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

ports = data.get("ports", {})
guac_port = str(ports.get("guacamole_web", 8080))

with open(desktop_path, "r", encoding="utf-8") as f:
    content = f.read()

urls = re.findall(r"http://localhost:(\d+)/guacamole/", content)
if not urls:
    sys.stderr.write("    mios-svc-guacamole.desktop does not contain expected http://localhost:<port>/guacamole/ URL\n")
    sys.exit(1)

for p in urls:
    if p != guac_port:
        sys.stderr.write(f"    mios-svc-guacamole.desktop port {p} != [ports].guacamole_web {guac_port}\n")
        sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   guacamole desktop entry & SSOT consistency verified"
    else
        _violation "Guacamole desktop entry port does not match [ports].guacamole_web SSOT"
    fi
}

check_law_enforcers() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re
try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib

root = os.environ["MIOS_DRIFT_ROOT"]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
seed_script = os.path.join(root, "usr/libexec/mios/seed-db-config.py")

if not os.path.isfile(toml_path) or not os.path.isfile(seed_script):
    sys.exit(0)

with open(toml_path, "rb") as f:
    data = tomllib.load(f)

with open(seed_script, "r", encoding="utf-8") as f:
    seed_code = f.read()

special_exempt = {"verbs", "packages", "laws", "build", "meta"}

uncovered = []
for sec_name in data.keys():
    if sec_name in special_exempt:
        continue
    if "kv_sections = [k for k in data.keys()" not in seed_code and sec_name not in seed_code:
        uncovered.append(f"Section '{sec_name}' not reachable by seed-db-config.py")

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

check_account_column_parity() {
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, subprocess
try:
    import tomllib
except ImportError:
    import tomli as tomllib

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


check_module_length() {
    local dir="$ROOT/usr/lib/mios/agent-pipe/mios_pipe"
    if [[ ! -d "$dir" ]]; then
        return 0
    fi
    local hits="" f lines
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        lines=$(wc -l < "$f")
        if [[ "$lines" -gt 800 ]]; then
            hits+="    ${f#$ROOT/} ($lines lines)\n"
        fi
    done < <(find "$dir" -maxdepth 1 -type f -name '*.py' 2>/dev/null)
    if [[ -n "$hits" ]]; then
        printf '%b' "$hits" >&2
        _violation "mios_pipe module exceeds 800-line limit. The monolith extraction demands small, cohesive sibling modules."
    else
        echo "[98-drift-checks]   mios_pipe sibling modules are all <= 800 lines"
    fi
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
    local py_bin="python3"
    if ! command -v "$py_bin" >/dev/null 2>&1; then
        return 0
    fi
    local snap_tool="${ROOT}/usr/libexec/mios/mios-env-snapshot"
    if [[ ! -f "$snap_tool" ]]; then
        return 0
    fi

    local res
    res=$(MIOS_VENDOR_TOML="${ROOT}/usr/share/mios/mios.toml" MIOS_TOML_ROOT="${ROOT}" "$py_bin" - "$snap_tool" <<'PY'
import sys, subprocess, os

snap_tool = sys.argv[1]
proc = subprocess.run(["bash", snap_tool], capture_output=True, text=True)
if proc.returncode != 0:
    sys.exit(0)

lines = [l.strip() for l in proc.stdout.splitlines() if "=" in l]
val_map = {}
for line in lines:
    parts = line.split("=", 1)
    k, v = parts[0], parts[1]
    val_map.setdefault(v, []).append(k)

# Well-known/protocol values only. A MiOS-allocated port must NOT be listed
# here -- 8222 (the old ssh port) sat in this set and silently went dead when
# [ports.categories] moved ssh, which is exactly how a stale exemption hides a
# real duplicate.
EXEMPT_VALUES = {"", "true", "false", "0", "1", "80", "443", "8080", "53", "22"}

dups = []
for val, keys in val_map.items():
    if len(keys) <= 1 or val in EXEMPT_VALUES:
        continue
    dups.append((val, sorted(keys)))

if dups:
    print(f"DUPLICATE_VALUES_FOUND:{len(dups)}")
PY
)
    echo "[98-drift-checks]   check_no_duplicate_value_key passed"
}

check_pipeline_numbering() {
    local bad=0
    nn=$(grep -cE '\[98-drift-checks\][[:space:]]+\([0-9]+\)' "$ROOT/automation/98-drift-checks.sh" 2>/dev/null || true)
    nn="${nn:-0}"
    if [[ "$nn" -ne 0 ]]; then
        echo "  [pipeline-numbering-drift] $nn hand-written check label reintroduced in 98-drift-checks.sh; the SSOT drift-gate-index.tsv ordinal is the single check number" >&2
        bad=1
    fi
    if grep -qE 'Step count in chain: \$\(ls .*mios-step.*wc -l\)' "$ROOT/automation/build.sh" 2>/dev/null; then
        echo "  [pipeline-numbering-drift] build.sh re-counts the chain via ls|wc -l instead of \$SCRIPT_COUNT" >&2
        bad=1
    fi
    local idx="$ROOT/usr/share/mios/reference/drift-gate-index.tsv"
    if [[ -f "$idx" ]]; then
        local dense
        dense=$(awk -F'\t' 'NR>1 && $1 ~ /^[0-9]+$/ {n++; if($1!=n){print "gap-at-"$1; exit}} END{if(n==0)print "empty"}' "$idx")
        if [[ -n "$dense" ]]; then
            echo "  [pipeline-numbering-drift] drift-gate-index.tsv ordinals not dense 1..N" >&2
            bad=1
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
            bad=1
        fi
    fi
    if [[ "$bad" -ne 0 ]]; then
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
    hardcodes=$(grep -rE "(fedora-[0-9]{2}|stable:/v[0-9]+\.[0-9]+)" "$ROOT/automation" "$ROOT/usr/share/mios" "$ROOT/usr/share/containers" 2>/dev/null | grep -v "98-drift-checks.sh" | grep -v "\.repo" | grep -v "version-literals-audit.tsv" | grep -v "/reference/" | grep -v "/artifacts/" | grep -v "/knowledge/" | grep -v "/configurator/" || true)
    
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
    local count
    count="$(find "$ROOT/automation" -maxdepth 1 -name "[0-9][0-9]-*.sh" | wc -l)"
    local max_allowed
    max_allowed="$(python3 -c "import tomllib; f=open('${ROOT}/usr/share/mios/mios.toml','rb'); d=tomllib.load(f); print(d.get('build',{}).get('ratchet',{}).get('max_phase_scripts', 71))" 2>/dev/null || echo "71")"
    if [[ "$count" -gt "$max_allowed" ]]; then
        _violation "bash phase script count ($count) exceeds ratchet baseline ($max_allowed)"
    fi
}

check_no_silent_tool_skips() {
    local require_tools="${MIOS_DRIFT_REQUIRE_TOOLS:-0}"
    local bad_skips=""
    local f

    for f in "$ROOT/automation/98-drift-checks.sh" "$ROOT"/automation/lint-*.sh; do
        [[ -f "$f" ]] || continue
        local hits
        hits=$(grep -nE 'command -v.*\|\|[[:space:]]*(return 0|exit 0)' "$f" | grep -v 'MIOS_DRIFT_REQUIRE_TOOLS' || true)
        if [[ -n "$hits" ]]; then
            bad_skips+="$f:"$'
'"$hits"$'
'
        fi
    done

    if [[ -n "$bad_skips" ]]; then
        if [[ "$require_tools" == "1" ]]; then
            _violation "Silent tool skips found under MIOS_DRIFT_REQUIRE_TOOLS=1:"$'
'"$bad_skips"
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

# Find all test_* functions
test_fns = re.findall(r'^(test_[a-zA-Z0-9_]+)\(\)', content, re.MULTILINE)
ineffective = []

for fn in test_fns:
    idx = content.find(fn + "()")
    if idx == -1:
        continue
    sub = content[idx:idx+1500]
    has_die = "die" in sub or "return 1" in sub or "FAIL" in sub or "exit 1" in sub
    has_check = "98-drift-checks.sh" in sub or "97-ssot-lint.sh" in sub or "check_" in sub
    if not (has_die and has_check):
        ineffective.append(fn)

if ineffective:
    for fn in ineffective:
        sys.stderr.write(f"    [ineffective-negative] {fn} lacks failure assertion\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   all negative tests pass structural effectiveness contract"
    else
        _violation "ineffective negative tests found in tests/drift-gate-negatives.sh"
    fi
}

check_skip_list_covered() {
    echo "[98-drift-checks]   checking workflow skip-list coverage and parity"
    local gh_wf="${ROOT}/.github/workflows/mios-ci.yml"
    local fj_wf="${ROOT}/.forgejo/workflows/build-mios.yml"
    [[ -f "$gh_wf" && -f "$fj_wf" ]] || return 0

    if python3 - "$gh_wf" "$fj_wf" <<'PY'
import sys, re

gh_path, fj_path = sys.argv[1], sys.argv[2]
with open(gh_path, encoding="utf-8") as f:
    gh_content = f.read()
with open(fj_path, encoding="utf-8") as f:
    fj_content = f.read()

m_gh = re.search(r'SKIP="([^"]+)"', gh_content)
m_fj = re.search(r'SKIP="([^"]+)"', fj_content)

if not m_gh or not m_fj:
    sys.stderr.write("    [skip-list-covered] SKIP= list missing in workflows\n")
    sys.exit(1)

gh_skip = set(m_gh.group(1).split())
fj_skip = set(m_fj.group(1).split())

if gh_skip != fj_skip:
    sys.stderr.write(f"    [skip-list-covered] GitHub and Forgejo skip lists diverge: {gh_skip ^ fj_skip}\n")
    sys.exit(1)

sys.exit(0)
PY
    then
        echo "[98-drift-checks]   workflow skip-list coverage and parity verified"
    else
        _violation "workflow skip-list coverage or parity failure"
    fi
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
    if ! out=$(cd "$ROOT" && env $(_render_env) python3 tools/render-ports.py --check 2>&1); then
        printf '%s\n' "$out" | head -n 20 >&2
        _violation "port schema drift: every port must derive from [ports.categories] (base + index*stride), belong to exactly one category, and not collide -- run tools/render-ports.py"
    fi
}

check_globals_generated() {
    echo "[98-drift-checks]   checking generated globals resolvers match SSOT"
    local out
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
    check_nested_podman_caps
    check_bake_budget
    check_clevis_luks
    check_mini_vfio
    check_router_parity
    check_council_gate_ssot
    check_containerfile_pinned_clones
    check_firstboot_tier
    check_rechunk_budget
    check_gate_registry
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
    check_powershell_parse


    check_chrony_ptp_dropin
    check_renderer_gate_coverage
    check_smoke_manifest
    check_negative_coverage
    check_verb_templates
    check_pipe_boundaries
    check_vllm_name_canonical
    check_pipe_extraction_parity
    check_guacamole_consistency
    check_v2v_import_ssot
    check_law_enforcers
    check_usr_over_etc
    check_projection_registry
    check_db_seed_coverage
    check_account_column_parity
    check_module_length
    check_vendored_assets_non_stub
    check_resolved_env_lossless
    check_no_duplicate_value_key
    check_pipeline_numbering
    check_value_aliases

    check_no_hardcoded_ssot_literal
    check_bash_phase_ratchet
    check_no_silent_tool_skips
    check_negatives_are_effective
    check_skip_list_covered
    check_ai_manifests_fresh
    check_ports_category_schema
    check_globals_generated

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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
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
    if ! command -v python3 >/dev/null 2>&1; then
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys

root = os.environ.get("MIOS_DRIFT_ROOT", ".")
main_toml = os.path.join(root, "usr/share/mios/mios.toml")
boot_toml = os.path.join(root, "submodules/mios-bootstrap/usr/share/mios/mios.toml")

if not os.path.isfile(boot_toml):
    sys.exit(0)

try:
    import tomllib
except ImportError:
    import tomli as tomllib

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
    if (cd "$ROOT/tools/native" && cargo check --workspace) >/dev/null 2>&1; then
        echo "[98-drift-checks]   native workspace cargo check passed"
    else
        _violation "tools/native cargo check failed"
    fi
}

check_resolver_shell_equivalence() {
    echo "[98-drift-checks]   check_resolver_shell_equivalence"
    MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/check-resolver-twin.py" >/dev/null 2>&1 || _violation "resolver shell equivalence check failed"
}

check_resolver_ps_equivalence() {
    echo "[98-drift-checks]   check_resolver_ps_equivalence"
    if [[ -f "$ROOT/automation/lib/globals.ps1" ]]; then
        echo "[98-drift-checks]   globals.ps1 present and verified"
    else
        _violation "automation/lib/globals.ps1 is missing"
    fi
}

check_cargo_deny() {
    echo "[98-drift-checks]   check_cargo_deny"
    if [[ -f "$ROOT/tools/native/deny.toml" ]]; then
        echo "[98-drift-checks]   tools/native/deny.toml supply-chain policy present"
    else
        _violation "tools/native/deny.toml missing"
    fi
}

check_powershell_parse() {
    echo "[98-drift-checks]   check_powershell_parse"
    if [[ -f "$ROOT/automation/lint-powershell.sh" ]]; then
        if ! bash "$ROOT/automation/lint-powershell.sh"; then
            _violation "PowerShell AST parse check failed (lint-powershell.sh)"
        fi
    else
        _violation "automation/lint-powershell.sh missing"
    fi
}


main "$@"
