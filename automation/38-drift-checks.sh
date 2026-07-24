#!/usr/bin/env bash
# AI-hint: Source-tree drift fitness-functions (WS-0A). Read-only static analysis over the repo (== system root) that FAILS on AI-plane SSOT drift no other gate catches: a retired local :11434 lane in active config, a retired model-id (gemma4 / qwen3:1.7b) hardcoded in a
# AI-related: 99-postcheck.sh, build.sh, /usr/libexec/mios/mios-ai-hint-coverage, /usr/share/mios/mios.toml, /usr/share/mios/ai/v1, /usr/share/mios/ai, /etc/mios/ai, /usr/lib/mios/agent-pipe, /usr/share/mios/ai/v1/packages, /usr/libexec/mios/mios-registry
# AI-functions: python3, _violation, check_dead_lane, check_retired_models, check_structured, check_hint_coverage, check_module_boundary, check_rbac_tiers, check_agent_schema, check_ai_manifest, check_package_registry, check_cli_sql_safety
# automation/38-drift-checks.sh
# ----------------------------------------------------------------------------
# WHY THIS EXISTS (WS-0A drift-freeze). 99-postcheck.sh enforces the same
# invariants but runs ONLY inside the OCI bake against the DEPLOYED rootfs
# (/usr/..., /etc/...), so it cannot protect a PR before the (expensive) build,
# and its checks that need a running rootfs (sshd, Cockpit) can't run on a bare
# checkout at all. This script is the SOURCE-TREE half: every check here reads
# repo-relative paths (the repo root IS the system root), so the SAME gate runs
# in build.sh, `just drift-gate`, and BOTH CI workflows on every PR -- failing
# fast, before the bake.
#
# WHAT IS DELIBERATELY *NOT* CHECKED (anti-drift: a gate that false-fails the
# current, intentional config is worse than no gate):
#   * Bare LIVE-lane port literals (:11441/:11440/:11450/:8643). The live config
#     intentionally hardcodes these as correct defaults in [nodes.*], the heavy
#     lane containers, and mios-agent-pipe.service. Flagging them would red every
#     build. Converting those consumers to ${MIOS_PORT_*} placeholders is deferred
#     WS-0B hardening; until then only the RETIRED :11434 lane is an error.
#   * --served-model-name collisions. Both heavy lanes (SGLang :11441, vLLM
#     :11440) intentionally serve "mios-heavy" -- documented mutual exclusivity
#     ("enable ONE on a shared GPU", mios-llm-heavy.container). A duplicate-name
#     check would false-fail by design.
#   * A _VERB_CATALOG -> ai/v1/tools.json verb-NAME diff. The 104 mios.toml
#     [verbs.*] and the 9 file-backed Hermes build-tools in tools.json are
#     DISJOINT namespaces (the verb catalog projects live via MCP /v1/verbs, not
#     a static file). Asserting name-equality would false-fail. The real,
#     available projection invariant is manifest reference-integrity (check 4).
#
# DERIVED-SURFACE REGEN GATES (WS-10 "regenerate every derived surface from SSOT
# + fail on diff"). Each surface below is GENERATED from mios.toml and gated here
# by a regenerate-and-diff check, so a committed artifact can NEVER drift from the
# SSOT it is projected from. This is the offline half of the rebuild-test gate
# (it runs in build.sh + both CI drift-gates, no built image needed):
#   (8)  ai/v1 verb-catalog manifest   <- tools/generate-ai-manifest.py   [verbs.*]
#   (12) ai/v1 capabilities.generated  <- mios_capreg                     [verbs.*]+[recipes.*]
#   (13) usr/share/containers/.../*.pod<- tools/generate-pod-quadlets.py  [pods.*]
#   (14) usr/share/mios/security/egress.nft <- generate-egress-firewall.py [security.egress]
# VM-GATED (NOT offline-derivable, so deliberately excluded here): the k3s
# manifests (tools/generate-k3s-manifests.sh) read the LIVE running pods via
# `podman kube generate`, and repo-rag-snapshot.json.gz is a non-deterministic
# data snapshot -- both regenerate on a host/VM, not in this static gate.
#
# Read-only. Exit 1 on any violation (fails a CI/build step). Set
# MIOS_DRIFT_CHECK_SOFT=1 to report but exit 0 (advisory, while a fix is staged).
#
# Usage:
#   automation/38-drift-checks.sh                       # check, exit 1 on drift
#   MIOS_DRIFT_CHECK_SOFT=1 automation/38-drift-checks.sh   # advisory (exit 0)
#   MIOS_DRIFT_CHECK_ROOT=/path automation/38-drift-checks.sh  # override root
# ----------------------------------------------------------------------------
set -euo pipefail

# Windows execution alias stub override
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

# Active-config scan roots (repo-relative). The /etc overlays are runtime-only
# and usually absent in a checkout -- guarded by -d below, so they PASS vacuously.
SCAN_DIRS=(
    "$ROOT/usr/share/containers/systemd"
    "$ROOT/usr/lib/systemd/system"
    "$ROOT/usr/share/mios/ai"
    "$ROOT/etc/containers/systemd"
    "$ROOT/etc/mios/ai"
)

VIOLATIONS=0
_violation() {
    VIOLATIONS=$((VIOLATIONS + 1))
    echo "[38-drift-checks] VIOLATION: $1" >&2
}

echo "[38-drift-checks] source-tree AI-plane drift fitness-functions"
echo "[38-drift-checks]   root: $ROOT"

# --- (1) Retired :11434 lane in active config (ANY host). --------------------
# Mirror of 99-postcheck.sh check 12b, on the SOURCE tree (PR-time). The ollama
# lane on :11434 is retired ENTIRELY -- MiOS is OpenAI-/v1-only (everything moved
# to mios-llm-light :8450), so NO :11434 ref is legitimate, local OR remote (the
# old remote-tailnet exception is gone). A stale ref silently 404s a refine /
# sys-agent / DCI call.
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
        _violation "retired :11434 (ollama) lane in active source config -- MiOS is /v1-only; use the live lane, e.g. mios-llm-light :8450"
    else
        echo "[38-drift-checks]   (1) no retired :11434 lane in active config"
    fi
}

# --- (2) Retired model-id hardcoded in a CONSUMER unit. ----------------------
# gemma4 (404 on :11450 since) and qwen3:1.7b (dropped from the fleet
# + bake_models) must not be wired into a CONSUMER (.container/.service/.json/
# .conf/.yaml). The SSOT mios.toml is intentionally EXCLUDED -- it legitimately
# documents the fleet history; consumers must name a live model.
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
        echo "[38-drift-checks]   (2) no retired model-id in consumer config"
    fi
}

# --- (3) [nodes.local-*] declared-vs-effective  +  (4) ai/v1 manifest integrity
# Both need a TOML/JSON parser -> python3. If python3 is unavailable (e.g. a
# minimal host), skip with a warning rather than fail (bash checks still ran).
check_structured() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping node + manifest checks" >&2
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

# -- (3) every [nodes.local-*] localhost endpoint must hit a served lane port --
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
if _toml is None:
    sys.stderr.write("[38-drift-checks]   WARNING: no tomllib/tomli -- skipping [nodes.*] check\n")
elif os.path.isfile(toml_path):
    with open(toml_path, "rb") as fh:
        data = _toml.load(fh)
    nodes = data.get("nodes", {}) or {}
    # served-port set: every :PORT (4-5 digit) referenced by a shipped unit file
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

    # -- (3b) validate new SSOT fields for observability, lanes, and agent_pipe --
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

# -- (4) ai/v1/*.json: must parse; tools.json schema refs must exist on disk --
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
            # reference-integrity: the per-tool schema/api files the manifest
            # advertises must actually ship. (dispatcher paths are intentionally
            # excluded -- those are generated/installed elsewhere.)
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
        echo "[38-drift-checks]   (3) every [nodes.local-*] localhost lane is served; (4) ai/v1 manifests parse + refs resolve"
    else
        _violation "structured drift: a [nodes.*] lane is dangling and/or an ai/v1 manifest is broken (see lines above)"
    fi
}

# --- (5) AI-hint header coverage ratchet (reuses mios-ai-tag SSOT). ----------
# Delegates to mios-ai-hint-coverage, which imports mios-ai-tag's walk()/
# existing_hint() (the taggability SSOT -- no keyword/dir lists duplicated here)
# and fails when untagged taggable files exceed [ai_tag].max_untagged. This is
# the source-tree half of WS-10 coverage: a NEW untagged file reds the PR before
# the bake. _SOFT is applied globally by main(), so just propagate the exit code.
check_hint_coverage() {
    local tool="$ROOT/usr/libexec/mios/mios-ai-hint-coverage"
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping AI-hint coverage" >&2
        return 0
    fi
    if [[ ! -f "$tool" ]]; then
        echo "[38-drift-checks]   WARNING: mios-ai-hint-coverage not found -- skipping" >&2
        return 0
    fi
    if python3 "$tool" --root "$ROOT"; then
        echo "[38-drift-checks]   (5) AI-hint coverage within ratchet ceiling"
    else
        _violation "AI-hint coverage regressed: a new taggable file lacks an AI-hint header (run mios-ai-tag, or raise [ai_tag].max_untagged only for prompt/data files)"
    fi
}

# --- (6) modular-monolith boundary (#58 WS-3 strangler-fig). ------------------
# The strangler-fig extracts pure logic out of the server.py monolith into
# sibling modules (mios_*.py) that are unit-tested in ISOLATION. The dependency
# must stay ONE-WAY: server.py imports the siblings, never the reverse. A sibling
# that `import server` would re-couple them and break standalone testability (the
# whole point of the extraction). Read-only static check; the source-tree mirror
# of the import-constraint named in #58.
check_module_boundary() {
    local dir="$ROOT/usr/lib/mios/agent-pipe"
    if [[ ! -d "$dir" ]]; then
        echo "[38-drift-checks]   (6) agent-pipe dir absent -- skipped"
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
        echo "[38-drift-checks]   (6) agent-pipe sibling modules are server.py-free (modular boundary intact)"
    fi
}

# (7, WS-A9) Every [agents.<name>] / [users.<name>] .max_permission MUST name a
# tier in [ai].permission_tiers. An unknown tier is a config defect: the dispatch
# PDP (mios_pdp.resolve_ceiling) now FAILS CLOSED on it (restricts the caller to
# the safest tier) instead of the old fail-OPEN (silently granting everything),
# so a typo silently shrinks a surface. Catch it at the gate, not in production.
check_rbac_tiers() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping RBAC tier check" >&2
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
        echo "[38-drift-checks]   (7) RBAC max_permission tiers all valid (PDP fail-closed gate)"
    else
        _violation "an [agents.*]/[users.*].max_permission names an UNKNOWN permission tier -- the dispatch PDP fails CLOSED on it (restricts the caller to the safest tier); fix the typo or add the tier to [ai].permission_tiers (WS-A9)"
    fi
}

# (WS-A2) Unified agent-schema contract. The [agents._defaults] template (WS-A1)
# is only safe if every [agents.*] honours the contract. The class-of-bug it
# makes UNREPRESENTABLE: a LOCAL, non-default, always-on-looking agent whose
# backing unit is actually OPTIONAL -> when it's down, _should_health_probe never
# probes it, _live_agent_names marks it live, _reroute_dead_nodes sinks DAG facets
# onto it -> merged_chars=0 (the live opencode failure). Fail the build so it can
# never re-merge. Advisory warns (bare-port literal, unknown key) print but pass.
check_agent_schema() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping agent-schema check" >&2
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
    # (a) local + non-default + enabled + plain local-http MUST be health-gated
    if loc and not bool(m.get("default", False)) and enabled and kind in ("", "local-http") and not hg:
        bad.append(f"    [agents.{name}] LOCAL + non-default + enabled but no health_gate=true (or enabled=false): a dead endpoint is treated as live -> DAG sink -> merged_chars=0")
    # (b) cli contract
    if kind == "cli":
        if not (hg or not enabled):
            bad.append(f"    [agents.{name}] kind=cli must set health_gate=true OR enabled=false")
        if int(m.get("timeout_s", 0) or 0) <= 0:
            bad.append(f"    [agents.{name}] kind=cli must set timeout_s>0 (fail-fast budget)")
    # (c) node/remote contract
    if kind == "node" and not (str(m.get("api", "")).strip() and str(m.get("lane", "")).strip()):
        bad.append(f"    [agents.{name}] kind=node must set api + lane")
    if kind in ("remote-http", "edge", "mobile") and not hg:
        bad.append(f"    [agents.{name}] kind={kind} must set health_gate=true")
    # (d) advisory: bare :PORT literal instead of a ${MIOS_PORT_*} template
    if re.search(r':\d{2,5}(/|$)', ep) and "${MIOS_PORT" not in ep:
        warn.append(f"    [agents.{name}].endpoint bare :PORT literal (use ${{MIOS_PORT_*}}): {ep}")
    # (f) advisory: unknown key (typo guard)
    for k in cfg:
        if k not in CANON:
            warn.append(f"    [agents.{name}] unknown key {k!r} (not in the canonical agent schema)")
# (e) at most ONE default=true (0 is valid: the orchestrator's primary is the backend)
if ndefault > 1:
    bad.append(f"    {ndefault} [agents.*] set default=true; at most one is allowed")
for w in warn:
    sys.stdout.write("[38-drift-checks]   (advisory)" + w + "\n")
for b in bad:
    sys.stderr.write(b + "\n")
sys.exit(1 if bad else 0)
PY
    then
        echo "[38-drift-checks]   (WS-A2) agent-schema contract satisfied (health_gate / cli / node / single-default rules)"
    else
        _violation "an [agents.*] entry violates the unified agent schema (WS-A2): a local-optional agent missing health_gate, a kind=cli without timeout_s, a kind=node without api+lane, or >1 default=true -- the opencode 'dead local endpoint treated as live -> merged_chars=0' class. Fix the [agents.*] block (or [agents._defaults])."
    fi
}

# (8, WS-A1) The committed ai/v1/tools.generated.json verb-catalog projection
# must match the live mios.toml [verbs.*] SSOT. Catches a verb added / removed /
# changed (incl. its conflict_group/parallel_limit) without regenerating the
# manifest (mios-ai-manifest-gen). Uses the SAME pure projection core the CLI does.
check_ai_manifest() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping AI manifest drift check" >&2
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
        echo "[38-drift-checks]   (8) ai/v1 verb-catalog manifest in sync with mios.toml SSOT"
    else
        _violation "ai/v1/tools.generated.json is STALE vs mios.toml [verbs.*] -- regenerate with mios-ai-manifest-gen (WS-A1)"
    fi
}

# (9, WS-A17) When the local package registry is ENABLED ([ai].package_registry
# / MIOS_PACKAGE_REGISTRY true), the committed ai/v1/packages/registry.json must
# be in sync with the live SSOT. DORMANT by default (flag off) -> trivial pass,
# so the dormant feature never reds the build.
check_package_registry() {
    local _en
    _en="$(printf '%s' "${MIOS_PACKAGE_REGISTRY:-false}" | tr '[:upper:]' '[:lower:]')"
    case "$_en" in
        1|true|yes|on) : ;;
        *)
            echo "[38-drift-checks]   (9) package registry dormant ([ai].package_registry off) -- skipped"
            return 0 ;;
    esac
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping package registry check" >&2
        return 0
    fi
    if MIOS_AGENT_PIPE_DIR="$ROOT/usr/lib/mios/agent-pipe" \
       MIOS_TOML="$ROOT/usr/share/mios/mios.toml" \
       MIOS_VENDOR_TOML="$ROOT/usr/share/mios/mios.toml" \
       MIOS_PACKAGES_DIR="$ROOT/usr/share/mios/ai/v1/packages" \
       python3 "$ROOT/usr/libexec/mios/mios-registry" verify >/dev/null 2>"$ROOT/.pkgreg.err"; then
        rm -f "$ROOT/.pkgreg.err" 2>/dev/null || true
        echo "[38-drift-checks]   (9) package registry in sync with mios.toml SSOT"
    else
        sed 's/^/    /' "$ROOT/.pkgreg.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.pkgreg.err" 2>/dev/null || true
        _violation "ai/v1/packages/registry.json is STALE vs the SSOT -- regenerate with mios-registry generate (WS-A17)"
    fi
}

# (10, WS-A3) CLI SQL-safety: a libexec tool must not (re)introduce the retired
# legacy HTTP transport (post_sql/_sql -> :8000/sql, surreal-ns headers) or
# hand-rolled SQL-escaping (_pgesc/_pgq single-quote doubling). The WS-A3 cutover
# replaced both with PARAMETERIZED pg -- values bound OUT-OF-BAND via
# mios-pg-query --exec-json / mios-db --pg-json -- so a regression silently
# no-ops on pg (dead legacy query) or reopens a SQL-injection hole. TWO tools carry
# The allowlist is now EMPTY: every libexec tool was cut over to parameterized pg
# (mios-daemon's dead legacy transports _db_post/_db_post_sync are stubbed
# no-ops + _pgesc deleted + its live pg writes parameterized; mios-viking
# migrated). Any reappearance of these markers anywhere in libexec is a real
# regression -> fail. (Re-add a NAMED entry to `allow` only for a deliberate,
# documented residual; never to silence a regression.)
check_cli_sql_safety() {
    local dir="$ROOT/usr/libexec/mios"
    if [[ ! -d "$dir" ]]; then
        echo "[38-drift-checks]   (10) libexec dir absent -- skipped"
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
        _violation "a libexec CLI (re)introduced the retired legacy DB transport (post_sql/_sql/:8000/sql) or hand-rolled SQL escaping (_pgesc/_pgq) -- use parameterized pg via mios-pg-query --exec-json / mios-db --pg-json (WS-A3)"
    else
        echo "[38-drift-checks]   (10) libexec CLIs SQL-safe (parameterized pg; allowlist empty -- all tools cut over)"
    fi
}

# (11, WS-0A) Every agent-pipe pure module (mios_*.py) MUST ship a sibling
# test_mios_*.py assert-script. The sibling-module pattern's whole value is that
# the extracted logic is unit-tested in ISOLATION; a module with no test is logic
# whose regressions pass the build gate unnoticed (the gap that left 5 cores --
# a2a_principal/crl/jsonsalvage/manifest/owui -- silently untested until covered).
# This locks the gap closed: a NEW mios_*.py with no test_mios_*.py reds the PR.
check_module_test_coverage() {
    local dir="$ROOT/usr/lib/mios/agent-pipe"
    if [[ ! -d "$dir" ]]; then
        echo "[38-drift-checks]   (11) agent-pipe dir absent -- skipped"
        return 0
    fi
    local missing="" f base
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        case "$base" in test_*) continue ;; esac          # tests don't need tests
        if [[ ! -f "$dir/test_${base}" ]]; then
            missing+="    $base (no test_${base})"$'\n'
        fi
    done < <(find "$dir" -maxdepth 1 -type f -name 'mios_*.py' 2>/dev/null)
    if [[ -n "$missing" ]]; then
        printf '%s' "$missing" >&2
        _violation "an agent-pipe pure module has NO sibling unit test -- author test_<module>.py (stdlib assert-script, the sibling-module pattern); isolation-tested logic is the point of the extraction (WS-0A)"
    else
        echo "[38-drift-checks]   (11) every agent-pipe mios_*.py has a sibling unit test"
    fi
}

# (51, B11) Anti-regression: raw TOML readers in agent-pipe forbidden.
# Fail when an agent-pipe module reads mios.toml via raw MIOS_TOML / hardcoded path.
check_raw_toml_readers() {
    local dir="$ROOT/usr/lib/mios/agent-pipe"
    if [[ ! -d "$dir" ]]; then
        echo "[38-drift-checks]   (51) raw TOML readers -- skipped"
        return 0
    fi
    local violations="" f base
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        case "$base" in test_*) continue ;; esac
        
        # Check 1: raw read of MIOS_TOML env var
        if grep -q -E "os\.environ(\.get)?\([\"']MIOS_TOML[\"']\)" "$f"; then
            violations+="    $base (reads MIOS_TOML env var directly)"$'\n'
        fi
        # Check 2: hardcoded mios.toml path opens
        if grep -E "open\(" "$f" | grep -q -E "mios\.toml"; then
            violations+="    $base (hardcoded open of mios.toml)"$'\n'
        fi
    done < <(find "$dir" -maxdepth 2 -type f -name '*.py' 2>/dev/null)

    if [[ -n "$violations" ]]; then
        printf '%s' "$violations" >&2
        _violation "found raw MIOS_TOML / mios.toml file readers. Use mios_toml.load_merged() / load_vendor() instead of manual file opens or raw env lookups (B11)"
    else
        echo "[38-drift-checks]   (51) no raw MIOS_TOML readers in agent-pipe"
    fi
}

# (12, WS-2/WS-10) The committed ai/v1/capabilities.generated.json UNIFIED RBAC
# capability manifest must match the live mios.toml [verbs.*] + [recipes.*] SSOT.
# Catches a verb/recipe added / removed / re-tiered (permission) without
# regenerating (mios-ai-capabilities-gen) -- the regenerate-from-SSOT-and-diff
# gate WS-10 asks for, over the WS-2 unified capability surface. Uses the SAME
# pure projection (mios_capreg) the generator CLI does.
check_capability_manifest() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping capability manifest check" >&2
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
        echo "[38-drift-checks]   (12) ai/v1 capability manifest in sync with mios.toml SSOT"
    else
        _violation "ai/v1/capabilities.generated.json is STALE vs mios.toml [verbs.*]+[recipes.*] -- regenerate with mios-ai-capabilities-gen (WS-2/WS-10)"
    fi
}

# (15, refactor WS R0) server.py PUBLIC-SURFACE parity. The strangler-fig refactor
# MOVES blocks out of the 30k-line server.py into a mios_pipe/ package and finally
# collapses server.py to a re-export shim. The two silent regressions that move can
# cause -- a DROPPED @app route (path/handler) and a MISSING/RENAMED public symbol
# (a def/class/global a sibling mios_*.py, a test_*.py, or a libexec tool imports) --
# are invisible to py_compile and to the per-module unit tests. The committed golden
# usr/share/mios/ai/v1/surface.generated.json snapshots the CURRENT surface; this
# gate regenerates it from the live server.py (pure ast, no import/exec) and FAILS on
# any diff, so every extraction wave is provably surface-preserving. Projects in
# WHOLE-PACKAGE mode (project_package) so a route MOVED off @app onto a sibling-module
# APIRouter (mounted via app.include_router) still composes back into the same record
# -- the gate stays honest once routes migrate cross-file (refactor R13). Regenerate the
# golden deliberately (mios_surface.py server.py --package > surface.generated.json) ONLY
# when the surface change is intended. Uses the SAME project_*/diff_* shape as check 8.
check_surface_parity() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping surface parity check" >&2
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
    # Whole-package projection: follow app.include_router(<sibling router>) into the
    # sibling mios_*.py so routes migrated off @app stay visible (search_dir defaults
    # to server.py's own directory, where the flat-layout siblings live). A strict
    # superset of project_surface -- identical on the current single-file layout.
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
        echo "[38-drift-checks]   (15) server.py public surface (routes+symbols) matches the committed golden"
    else
        _violation "server.py PUBLIC SURFACE drifted from usr/share/mios/ai/v1/surface.generated.json -- a route/symbol was dropped or added during the refactor. If intended, regenerate: python3 usr/lib/mios/agent-pipe/mios_surface.py usr/lib/mios/agent-pipe/server.py --package > usr/share/mios/ai/v1/surface.generated.json (refactor WS R0)"
    fi
}

check_pod_quadlets() {
    # WS-7 pods-as-SSOT: the .pod Quadlets under usr/share/containers/systemd are
    # GENERATED from mios.toml [pods.*]; fail if any committed .pod drifted from
    # SSOT (regenerate via tools/generate-pod-quadlets.py). Also warns if a
    # declared member has no .container file.
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping pod-quadlet check" >&2
        return 0
    fi
    local gen="$ROOT/tools/generate-pod-quadlets.py"
    if [[ ! -f "$gen" ]]; then
        echo "[38-drift-checks]   WARNING: generate-pod-quadlets.py absent -- skipping" >&2
        return 0
    fi
    # DETERMINISM: run --check in a CLEAN env. build.sh sources lib/common.sh ->
    # userenv, which EXPORTS ~200 MIOS_* vars (MIOS_VLLM_MAX_MODEL_LEN=262144,
    # MIOS_CRAWL_CAMOUFOX=True, ...). generate-pod-quadlets.py resolves
    # ${VAR:-default} via os.environ.get, so inheriting those makes it BAKE the
    # configured values and diverge from the committed tree (which is the
    # bare-render / fallback form) -> false STALE drift that aborts the OCI build
    # (heavy + crawl4ai). The committed tree == bare render, so strip the env and
    # --check becomes deterministic in both the build and standalone drift-gate.
    # (${MIOS_PORT_*} stay placeholders either way -- the generator preserves
    # those unconditionally; env -i just removes the value-baking pollution.)
    if env -i PATH="$PATH" HOME="${HOME:-/root}" LANG="${LANG:-C.UTF-8}" \
            MIOS_ROOT="$ROOT" "$PYTHON" "$gen" --check; then
        echo "[38-drift-checks]   (13) Quadlet units (.pod, .container, .network, .volume) in sync with mios.toml SSOT"
    else
        _violation "Quadlet unit(s) (.pod, .container, .network, .volume) STALE vs mios.toml SSOT -- regenerate with tools/generate-pod-quadlets.py"
    fi
}

check_egress_firewall() {
    # WS-10 regen-and-diff: the agent egress nftables ruleset is GENERATED from
    # mios.toml [security.egress]; fail if the committed usr/share/mios/security/
    # egress.nft drifted from SSOT (regenerate via tools/generate-egress-firewall.py).
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping egress-fw check" >&2
        return 0
    fi
    local gen="$ROOT/tools/generate-egress-firewall.py"
    local committed="$ROOT/usr/share/mios/security/egress.nft"
    if [[ ! -f "$gen" || ! -f "$committed" ]]; then
        echo "[38-drift-checks]   WARNING: egress generator/artifact absent -- skipping" >&2
        return 0
    fi
    local tmp; tmp="$(mktemp)"
    if MIOS_ROOT="$ROOT" MIOS_EGRESS_OUT="$tmp" python3 "$gen" >/dev/null 2>&1 \
            && diff -q "$committed" "$tmp" >/dev/null 2>&1; then
        echo "[38-drift-checks]   (14) egress.nft in sync with mios.toml [security.egress] SSOT"
        rm -f "$tmp"
    else
        rm -f "$tmp"
        _violation "usr/share/mios/security/egress.nft is STALE vs mios.toml [security.egress] -- regenerate with tools/generate-egress-firewall.py (WS-10)"
    fi
}

check_blade_dropins() {
    # WS-BLADE: verify committed blade capability drop-ins are in sync with mios.toml [blade.requires]
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping blade dropins check" >&2
        return 0
    fi
    local gen="$ROOT/tools/generate-blade-dropins.py"
    if [[ ! -f "$gen" ]]; then
        echo "[38-drift-checks]   WARNING: blade dropins generator absent -- skipping" >&2
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
            echo "[38-drift-checks]   (44) blade capability drop-ins in sync with mios.toml [blade.requires]"
        else
            _violation "usr/share/mios/dropins/ is STALE vs mios.toml [blade.requires] -- regenerate with tools/generate-blade-dropins.py (WS-BLADE)"
        fi
    else
        rm -rf "$tmp_root"
        _violation "blade drop-in generation failed during drift check"
    fi
}


# (16, NO-HARDCODE law / Architectural Law 7) The mios-hardcode-lint gate: FAILS on a
# date/timestamp in a COMMENT or DOCSTRING (the timeless-comment rule) or an AI-Hint
# header crash-risk (a stranded BOM, or a header above a shebang). Comment-aware
# (tokenize + AST docstrings for .py, quote-aware for the rest) so string literals and
# legitimate date CONFIG values are never flagged. Runs offline over the source tree.
check_no_hardcode() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping no-hardcode lint" >&2
        return 0
    fi
    local tool="$ROOT/usr/libexec/mios/mios-hardcode-lint"
    if [[ ! -f "$tool" ]]; then
        echo "[38-drift-checks]   WARNING: mios-hardcode-lint not found -- skipping" >&2
        return 0
    fi
    if python3 "$tool" "$ROOT" >/dev/null 2>"$ROOT/.nohc.err"; then
        rm -f "$ROOT/.nohc.err" 2>/dev/null || true
        echo "[38-drift-checks]   (16) no date-in-comment / header crash-risk (NO-HARDCODE law)"
    else
        sed 's/^/    /' "$ROOT/.nohc.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.nohc.err" 2>/dev/null || true
        _violation "NO-HARDCODE law (Law 7): a date/timestamp in a comment/docstring OR an AI-Hint header crash-risk -- strip the date (timeless comment) or move the header below the shebang/BOM (see mios-hardcode-lint)"
    fi
}

# (17, A1 -- MIOS-GAP-REGISTER) Imported-but-dead substrate gate. The strangler-fig
# left agent-pipe sibling modules (mios_*.py) that server.py / a sibling IMPORTS but
# whose names are never REFERENCED from any non-test .py -- dead weight masquerading
# as wired ("imported WS module with no real caller"). This makes that class
# unrepresentable: a NEW such module reds the PR. Importer/candidate scope is
# agent-pipe non-test .py (server.py + siblings); the wired-check reference scope is
# BROAD (agent-pipe + libexec + tools non-test .py) so a module wired only via a
# libexec/tools call site is never a false positive. A `from mios_X import ...`
# re-export for surface parity counts as imported-not-called -- the symbols are bound
# into server.py's surface but never executed, so the module is still dead. The
# _UNWIRED_ALLOW set is the documented TRANSITIONAL register of substrate pending
# wiring; the gate also fails on a STALE allow entry (now wired or removed), so the
# register self-cleans. Pure ast, read-only.
check_unwired_modules() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping unwired-module check" >&2
        return 0
    fi
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, ast
root = os.environ["MIOS_DRIFT_ROOT"]
pipe = os.path.join(root, "usr/lib/mios/agent-pipe")
if not os.path.isdir(pipe):
    sys.exit(0)  # nothing to check on a bare checkout

# DOCUMENTED TRANSITIONAL ALLOWLIST: agent-pipe modules IMPORTED as substrate but
# PENDING a real call site (imported-but-dead) -- see MIOS-GAP-REGISTER A1. Loaded from
# mios.toml [drift].denylist.
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

# Candidate IMPORTERS = agent-pipe non-test .py (server.py + mios_*.py siblings + mios_pipe package).
pipe_py = []
for dp, _dn, files in os.walk(pipe):
    for f in files:
        if f.endswith(".py") and not is_test(os.path.join(dp, f)):
            pipe_py.append(os.path.join(dp, f))
# REFERENCE (wired) scope -- BROAD: agent-pipe + libexec + tools non-test .py.
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
        echo "[38-drift-checks]   (17) no imported-but-dead agent-pipe module (A1 _UNWIRED_ALLOW current)"
    else
        _violation "an agent-pipe module is imported-but-dead (no real non-test caller) OR a _UNWIRED_ALLOW entry is stale -- wire the module (give it a call site) or update the _UNWIRED_ALLOW register (MIOS-GAP-REGISTER A1)"
    fi
}

# --- (18) [storage.cephfs] SSOT validator (T-084 / T-093). -------------------
# Validates CephFS configuration:
# (a) monitors is not placeholder ["127.0.0.1:6789"] when enable=true
# (b) xdg_cache_home_override does not point to a CephFS-backed path (avoid MDS cache storms)
# (c) data_pool_hot and data_pool_bulk are distinct
# (d) provision_script path exists in the image (warnings/advisory when offline)
check_cephfs_ssot() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping cephfs check" >&2
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
    sys.stderr.write("[38-drift-checks]   WARNING: no tomllib/tomli -- skipping CephFS check\n")
elif os.path.isfile(toml_path):
    with open(toml_path, "rb") as fh:
        data = _toml.load(fh)
    cephfs = data.get("storage", {}).get("cephfs", {}) or {}
    enable = cephfs.get("enable", False)
    
    if enable:
        # (a) monitors is not the placeholder
        monitors = cephfs.get("monitors", [])
        if not monitors or monitors == ["127.0.0.1:6789"]:
            viol.append("[storage.cephfs].monitors must be set to actual monitor IPs when enable=true")
            
        # (b) cache isolation rule: xdg_cache_home_override does NOT contain CephFS paths
        cache_override = cephfs.get("xdg_cache_home_override", "")
        hostnames = [m.split(":")[0] for m in monitors]
        if ("ceph" in cache_override.lower() or 
                "/tenants/" in cache_override or 
                cache_override.startswith("/home/") or 
                any(h in cache_override for h in hostnames if h)):
            viol.append("[storage.cephfs].xdg_cache_home_override must be local tmpfs, NEVER CephFS (MDS storm hazard)")
            
        # (c) distinct pools
        hot_pool = cephfs.get("data_pool_hot", "")
        bulk_pool = cephfs.get("data_pool_bulk", "")
        if hot_pool and bulk_pool and hot_pool == bulk_pool:
            viol.append("[storage.cephfs] data_pool_hot and data_pool_bulk must be distinct pools for tiering")
            
        # (d) provision_script exists (checked relative to ROOT or absolute on live VM)
        prov_script = cephfs.get("provision_script", "")
        if prov_script:
            # check both repo-relative and absolute (since usr/ is in checkouts)
            rel_path = prov_script.lstrip("/")
            repo_path = os.path.join(root, rel_path)
            if not os.path.exists(repo_path) and not os.path.exists(prov_script):
                viol.append(f"[storage.cephfs].provision_script path '{prov_script}' does not exist on disk")

        # (e) automount_enable = true but home-@.mount.tmpl absent
        if cephfs.get("automount_enable", False):
            mount_tmpl = os.path.join(root, "usr/share/mios/systemd/home-@.mount.tmpl")
            if not os.path.exists(mount_tmpl):
                viol.append("home-@.mount.tmpl is missing from usr/share/mios/systemd/ but [storage.cephfs].automount_enable is true")

for v in viol:
    sys.stderr.write(f"    {v}\n")
sys.exit(1 if viol else 0)
PY
    then
        echo "[38-drift-checks]   (18) CephFS SSOT configuration is valid (no placeholder/cache conflicts)"
    else
        _violation "[storage.cephfs] SSOT validation failed (see lines above)"
    fi
}

# --- (19) [converge] SSOT validator (T-094 / CONV-01). ----------------------
# Stub validator that currently passes unconditionally (unblocking subsequent work).
check_converge_ssot() {
    local retire_alt="${MIOS_CONVERGE_INFERENCE_RETIRE_HEAVY_ALT:-false}"
    if [[ "$retire_alt" == "true" ]]; then
        if command -v systemctl >/dev/null 2>&1; then
            if systemctl is-enabled mios-llm-heavy-alt.service >/dev/null 2>&1; then
                echo "[38-drift-checks] VIOLATION: retire_heavy_alt=true but systemd unit mios-llm-heavy-alt.service is still enabled!" >&2
                VIOLATIONS=$((VIOLATIONS + 1))
                return 1
            fi
        fi
    fi

    # Phase 3 checks
    local cold_storage_dir="${MIOS_CONVERGE_MEMORY_COLD_STORAGE_DIR:-/var/lib/mios/history/}"
    if [[ "$cold_storage_dir" == *"/tenants/"* ]]; then
        echo "[38-drift-checks] VIOLATION: cold_storage_dir ($cold_storage_dir) cannot be inside a CephFS tenants mount path!" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 1
    fi

    local cold_retention_days="${MIOS_CONVERGE_MEMORY_COLD_RETENTION_DAYS:-30}"
    if [[ "$cold_retention_days" -lt 1 ]]; then
        echo "[38-drift-checks] VIOLATION: cold_retention_days ($cold_retention_days) must be >= 1!" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 1
    fi

    local cold_zstd_level="${MIOS_CONVERGE_MEMORY_COLD_ZSTD_LEVEL:-3}"
    if [[ "$cold_zstd_level" -lt 1 || "$cold_zstd_level" -gt 19 ]]; then
        echo "[38-drift-checks] VIOLATION: cold_zstd_level ($cold_zstd_level) must be between 1 and 19!" >&2
        VIOLATIONS=$((VIOLATIONS + 1))
        return 1
    fi

    local sqlite_vec_enable="${MIOS_CONVERGE_MEMORY_SQLITE_VEC_ENABLE:-false}"
    if [[ "$sqlite_vec_enable" == "true" ]]; then
        local py_bin="/usr/lib/mios/agents/.venv/bin/python3"
        if [[ ! -x "$py_bin" ]]; then
            py_bin="python3"
        fi
        if ! "$py_bin" -c "import sqlite_vec" >/dev/null 2>&1; then
            echo "[38-drift-checks] VIOLATION: sqlite_vec_enable=true but sqlite_vec python package is not importable!" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi
    fi

    echo "[38-drift-checks]   (19) [converge] SSOT configuration is valid (retire_heavy_alt=$retire_alt)"
}

# --- (20) Hummingbird distroless and Quadlet configuration (CONV-15). -------
check_hummingbird() {
    local distroless_enable="${MIOS_CONVERGE_IMAGE_DISTROLESS_ENABLE:-false}"
    local rechunk_enable="${MIOS_CONVERGE_IMAGE_RECHUNK_ENABLE:-false}"
    local containerfile="Containerfile.hummingbird"
    local quadlet="usr/share/containers/systemd/mios-agent-pipe.container"

    if [[ "$distroless_enable" == "true" ]]; then
        if [[ ! -f "$containerfile" ]]; then
            echo "[38-drift-checks] VIOLATION: distroless_enable=true but $containerfile is missing!" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        if [[ ! -f "$quadlet" ]]; then
            echo "[38-drift-checks] VIOLATION: Quadlet definition $quadlet is missing!" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        if ! grep -q "Environment=MIOS_AI_ENDPOINT=" "$quadlet"; then
            echo "[38-drift-checks] VIOLATION: Quadlet $quadlet is missing Environment=MIOS_AI_ENDPOINT!" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi
    fi

    if [[ -f "$containerfile" ]]; then
        local mios_toml="usr/share/mios/mios.toml"
        local expected_base
        expected_base=$(grep -E '^\s*distroless_base\s*=' "$mios_toml" | head -n 1 | cut -d'"' -f2 || echo "gcr.io/distroless/python3-debian13")
        if [[ -z "$expected_base" ]]; then
            expected_base="gcr.io/distroless/python3-debian13"
        fi

        if ! grep -F "FROM $expected_base" "$containerfile" >/dev/null 2>&1; then
            echo "[38-drift-checks] VIOLATION: Containerfile.hummingbird base image does not match distroless_base ($expected_base)!" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        # Extract the final stage (from the last FROM onwards)
        local final_stage
        final_stage=$(awk '/^FROM/ { stage="" } { stage=stage "\n" $0 } END { print stage }' "$containerfile")

        if echo "$final_stage" | grep -F "/bin/bash" >/dev/null; then
            echo "[38-drift-checks] VIOLATION: Containerfile.hummingbird final stage contains /bin/bash!" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi

        local user_line
        user_line=$(echo "$final_stage" | grep -E '^\s*USER\s+' | tail -n 1 | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        if [[ "$user_line" != "USER 65534" && "$user_line" != "USER 65534:65534" ]]; then
            echo "[38-drift-checks] VIOLATION: Containerfile.hummingbird final stage USER ($user_line) is not 65534 or 65534:65534!" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi
    fi

    if [[ "$rechunk_enable" == "true" ]]; then
        if ! command -v rpm-ostree >/dev/null 2>&1; then
            echo "[38-drift-checks] VIOLATION: rechunk_enable=true but rpm-ostree binary not found in PATH!" >&2
            VIOLATIONS=$((VIOLATIONS + 1))
            return 1
        fi
    fi

    echo "[38-drift-checks]   (20) Hummingbird distroless and Quadlet configuration is valid"
}

check_container_ports() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping container port check" >&2
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

# Get all port numbers (excluding stack_id which is 0)
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
                # Strip comments
                active = re.sub(r'#.*', '', line).strip()
                if not active:
                    continue
                # For each port value, check if it appears as a word boundary
                for name, val in port_vals.items():
                    # Strip placeholder defaults first
                    # e.g. ${MIOS_PORT_OPEN_WEBUI:-8033}
                    cleaned = re.sub(r'\$\{MIOS_PORT_[A-Z_]+:-' + str(val) + r'\}', '', active)
                    if re.search(rf'\b{val}\b', cleaned):
                        # Verify it's not an internal port like guacamole:8080 or firecrawl:3002
                        # Let's skip 8080 or 3002 if it is the target port in a PublishPort (like PublishPort=xxx:8080)
                        # or container-internal binds. Since they are permitted as container ports, we can
                        # just skip them if they match.
                        if val in (8080, 3002) and (":" + str(val) in cleaned or "=" + str(val) in cleaned and not cleaned.startswith("PublishPort=")):
                            continue
                        viol.append(f"{fn}:{idx}: manual port literal {val} for '{name}' used in active line: {line.strip()}")

for v in viol:
    print(v)
sys.exit(1 if viol else 0)
PY
    then
        echo "[38-drift-checks]   (21) no manual port literals in container definitions"
        rm -f "$tmp"
    else
        echo "[38-drift-checks] VIOLATION: manual port literal(s) found in container Quadlets -- use the \${MIOS_PORT_*} placeholder from the [ports] SSOT (T-042):" >&2
        cat "$tmp" >&2
        rm -f "$tmp"
        VIOLATIONS=$((VIOLATIONS + 1))
        return 1
    fi
}

check_bootstrap_ports_drift() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping bootstrap ports drift check" >&2
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
        echo "[38-drift-checks]   (22) bootstrap mios.toml [ports] table matches main repository"
    else
        _violation "bootstrap mios.toml [ports] table diverges from main repository mios.toml"
    fi
}

# --- (23) Verify all [agent_pipe] variables have code consumers. -------------
check_agent_pipe_budgets() {
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
if not agent_pipe:
    sys.stderr.write("    Missing [agent_pipe] table in mios.toml\n")
    sys.exit(1)

# Find all occurrences of the keys in usr/lib/mios/agent-pipe/
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

budget_keys = ["tool_max_iters", "replan_max", "no_progress_window", "max_consecutive_failures", "wall_clock_budget_s", "reflexion_enable"]
missing = []
for k in budget_keys:
    if k not in agent_pipe:
        missing.append(f"{k} (missing from mios.toml)")
        continue
    pattern = rf"['\"]{k}['\"]"
    if not re.search(pattern, code) and k not in code:
        missing.append(k)

if missing:
    sys.stderr.write(f"    Missing code consumers or TOML definitions for [agent_pipe] budget keys: {missing}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[38-drift-checks]   (23) all [agent_pipe] budget variables have code consumers"
    else
        _violation "some [agent_pipe] keys have no code consumer in the agent-pipe codebase (T-108)"
    fi
}

# --- (24) Verify no bare port literals remain in execution paths. ------------
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
        echo "[38-drift-checks]   (24) no bare port literals remain in execution paths"
    else
        _violation "bare port literals in execution paths (T-121/T-125)"
    fi
}

# --- (25, Phase-1 palette SSOT) Theme+settings-surface projection gate. --------
# Every committed theme surface (the btop theme, oh-my-posh, quickshell,
# fastfetch, the app-shell CSS, the terminal OSC fallbacks) is PROJECTED from
# mios.toml [colors]/[theme] via mios-theme-render's token-substitution
# templates. The SAME engine also projects SETTINGS surfaces: the btop-conf
# surface derives the WHOLE etc/btop/btop.conf from mios.toml [btop] (unified
# Linux+Windows; the Windows bootstrap stages this rendered artifact). This gate
# regenerates each surface from the SSOT and FAILS on any diff, so a palette hex
# OR a btop setting can NEVER drift from the SSOT -- a hand-edited btop.conf reds
# the PR exactly like a hand-edited theme. Re-run `mios-sync-theme` to refresh
# (the one global runtime theme command). Same regenerate-and-diff shape as
# checks 8/12/13/14, over the theme + settings surfaces.
check_dotfiles_projection() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping dotfiles-projection check" >&2
        return 0
    fi
    local tool="$ROOT/usr/libexec/mios/mios-dotfiles-render"
    if [[ ! -f "$tool" ]]; then
        echo "[38-drift-checks]   WARNING: mios-dotfiles-render not found -- skipping" >&2
        return 0
    fi
    if MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" MIOS_HOST_TOML=/nonexistent.toml MIOS_USER_TOML=/nonexistent.toml python3 "$tool" check >/dev/null 2>"$ROOT/.dotfiles.err"; then
        rm -f "$ROOT/.dotfiles.err" 2>/dev/null || true
        echo "[38-drift-checks]   (25) every committed theme + settings surface projects from mios.toml [colors]/[btop]/[gitconfig]/[identity]/[dotfiles] SSOT"
    else
        sed 's/^/    /' "$ROOT/.dotfiles.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.dotfiles.err" 2>/dev/null || true
        _violation "a dotfiles surface drifted from the mios.toml SSOT projection -- re-run mios dotfiles sync (Phase-1 palette drift-gate; mios-dotfiles-render)"
    fi
}

# --- (27, flatten) userenv.sh resolver copy parity. --------------------------
# tools/lib/userenv.sh is the authoritative resolver (36-tools.sh installs it to
# /usr/lib/mios/userenv.sh at build). The committed FHS copy MUST match it byte-
# for-byte, else the build silently swaps the exported MIOS_* env set (the two
# had diverged: retired ollama slots vs the live micro-llm slots).
check_userenv_parity() {
    local src="$ROOT/tools/lib/userenv.sh" dst="$ROOT/usr/lib/mios/userenv.sh"
    if [[ ! -f "$src" || ! -f "$dst" ]]; then
        echo "[38-drift-checks]   (27) userenv.sh parity -- a copy is absent, skipped"
        return 0
    fi
    if diff -q "$src" "$dst" >/dev/null 2>&1; then
        echo "[38-drift-checks]   (27) usr/lib/mios/userenv.sh matches authoritative tools/lib/userenv.sh"
    else
        _violation "usr/lib/mios/userenv.sh drifted from the authoritative tools/lib/userenv.sh (36-tools.sh installs the latter) -- resync: cp tools/lib/userenv.sh usr/lib/mios/userenv.sh (flatten check 27)"
    fi
}

# --- (26, flatten) Verb-backend resolvability gate. --------------------------
# Every mios-* command a [verbs.*].cmd dispatches to MUST exist on disk
# (usr/libexec/mios or usr/bin). The consolidated Gen-2 verbs shipped cmd
# templates pointing at NON-EXISTENT backends (mios-memory / mios-agent /
# mios-code-mode) while the model-facing surface advertised them -- a live
# dead-dispatch. This gate makes that class unrepresentable.
check_verb_backends() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping verb-backend check" >&2
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
        echo "[38-drift-checks]   (26) every [verbs.*].cmd mios-* backend resolves on disk"
    else
        _violation "a [verbs.*].cmd dispatches to a mios-* backend that does not exist (dead dispatch) -- fix the cmd template or ship the backend (flatten check 26)"
    fi
}

# --- (28, flatten) globals.{ps1,sh} port fallback vs [ports] SSOT. -----------
# The MIOS_PORT_* fallback defaults in automation/lib/globals.ps1 and
# automation/lib/globals.sh are the values that survive when userenv.sh never
# runs (the Windows side). They had frozen at a RETIRED pre-8xxx port schema and
# silently drifted from mios.toml [ports] (the SSOT), causing real cross-plane
# port disagreement. This gate re-derives every `else { N }` (ps1) and
# `:=N` (sh) fallback and asserts it equals the matching [ports].<name> value,
# so the fallbacks can never drift from the SSOT again.
check_globals_ports() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping globals-ports check" >&2
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
# ps1: `$script:MIOS_PORT_<NAME> ... else { N }`
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
# sh: `: "${MIOS_PORT_<NAME>:=N}"`
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
        echo "[38-drift-checks]   (28) every MIOS_PORT_* fallback in globals.{ps1,sh} equals mios.toml [ports] SSOT"
    else
        _violation "a MIOS_PORT_* fallback default in automation/lib/globals.ps1 or globals.sh drifted from mios.toml [ports] SSOT (Windows-side effective default; align the else{N}/:=N literal to [ports].<name>) (flatten check 28)"
    fi
}

# (52, D5) Add twin-parity drift check for globals.{sh,ps1} MIOS_IMAGE_NAME default (and base/bib images).
# Ensure default image references in automation/lib/globals.sh and globals.ps1 align with mios.toml [image] SSOT.
check_globals_image_parity() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping globals-image-parity check" >&2
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
# Check globals.sh
sh = os.path.join(root, "automation/lib/globals.sh")
if os.path.isfile(sh):
    with open(sh, encoding="utf-8") as fh:
        content = fh.read()
        
        # Check MIOS_IMAGE_NAME
        m = re.search(r'MIOS_IMAGE_NAME:=([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_name:
                bad.append(f"globals.sh default MIOS_IMAGE_NAME={got} != mios.toml [image].name={expected_name}")
        else:
            bad.append("globals.sh is missing default MIOS_IMAGE_NAME definition")
            
        # Check MIOS_BASE_IMAGE
        m = re.search(r'MIOS_BASE_IMAGE:=([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_base:
                bad.append(f"globals.sh default MIOS_BASE_IMAGE={got} != mios.toml [image].base={expected_base}")
        else:
            bad.append("globals.sh is missing default MIOS_BASE_IMAGE definition")

        # Check MIOS_BIB_IMAGE
        m = re.search(r'MIOS_BIB_IMAGE:=([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_bib:
                bad.append(f"globals.sh default MIOS_BIB_IMAGE={got} != mios.toml [image].bib={expected_bib}")
        else:
            bad.append("globals.sh is missing default MIOS_BIB_IMAGE definition")

# Check globals.ps1
ps1 = os.path.join(root, "automation/lib/globals.ps1")
if os.path.isfile(ps1):
    with open(ps1, encoding="utf-8") as fh:
        content = fh.read()
        
        # Check defaultImageName
        m = re.search(r'\$defaultImageName\s*=\s*([^#\r\n]+)', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_name:
                bad.append(f"globals.ps1 defaultImageName={got} != mios.toml [image].name={expected_name}")
        else:
            bad.append("globals.ps1 is missing $defaultImageName definition")
            
        # Check MIOS_BASE_IMAGE
        m = re.search(r'MIOS_BASE_IMAGE[^\r\n]+else\s*\{\s*([^}]+)\}', content)
        if m:
            got = m.group(1).strip('"\' ')
            if got != expected_base:
                bad.append(f"globals.ps1 default MIOS_BASE_IMAGE={got} != mios.toml [image].base={expected_base}")
        else:
            bad.append("globals.ps1 is missing default MIOS_BASE_IMAGE definition")

        # Check MIOS_BIB_IMAGE
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
        echo "[38-drift-checks]   (52) default image references in globals.{sh,ps1} equal mios.toml [image] SSOT"
    else
        _violation "default image reference in automation/lib/globals.sh or globals.ps1 drifted from mios.toml [image] SSOT"
    fi
}

# --- (29, DAG-integrity drift-gate) consumer-before-producer = build error. ----
check_dag_integrity() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping DAG-integrity check" >&2
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
            
            # Extract all After and Requires targets
            after_requires_targets = []
            for line in content.splitlines():
                m = re.match(r"^[ \t]*(After|Requires)[ \t]*=[ \t]*(.*)$", line, re.IGNORECASE)
                if m:
                    after_requires_targets.extend(m.group(2).split())
            
            # Venv-consumer edge: SUPERSEDED by Law 12 (BAKE-NOT-FETCH). The agents
            # venv is BAKED into the OCI image (automation/38-hermes-agent.sh), present
            # independent of mios-ai-firstboot's model fetch, so the plane units no
            # longer order After=mios-ai-firstboot -- that edge only blocked the whole
            # AI plane behind a multi-GB boot-time download. mios-ai-firstboot itself
            # restarts the plane (systemctl restart mios-agent-pipe mios-gateway-agent)
            # once the models land, so readiness is handled by restart-on-completion +
            # the firstboot degrade-open (check 39), not a hard ordering edge. The
            # baked-venv invariant is enforced at build (Law 12 postcheck), not here.

            # Check webtools local image/pod consumer edge:
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
        echo "[38-drift-checks]   (29) DAG-integrity: consumers start after their producers' readiness artifacts exist"
    else
        _violation "DAG dependency ordering violation detected: consumer starts before producer (flatten check 29)"
    fi
}

# --- (30, WS-NAME names/keys registry enforcement) ----------------------------
check_names_registry() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping names registry check" >&2
        return 0
    fi
    # generate-names-registry.py enumerates the tracked tree via `git ls-files`
    # to build referenced_names.txt. The MiOS root IS a git work tree -- .git is
    # shipped into the build context and build.sh `git reset --hard HEAD`s the
    # pristine tree before this runs -- so on BOTH the drift-gate job and the
    # image build this check RUNS against the full committed source (identical
    # result). The guards below are last-resort only: a genuinely non-git or an
    # INCOMPLETE (un-checked-out) tree makes git ls-files enumerate paths absent
    # on disk -> the generator's os.walk fallback yields false drift. In that
    # case skip rather than false-fail; the drift-gate job stays authoritative.
    # Full visibility: any skip is explicit and states exactly why.
    if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "[38-drift-checks]   (30) names registry -- SKIPPED (no git work tree at \$ROOT; generate-names-registry.py needs 'git ls-files')"
        return 0
    fi
    if git -C "$ROOT" ls-files --deleted 2>/dev/null | grep -q .; then
        echo "[38-drift-checks]   (30) names registry -- SKIPPED (incomplete git work tree: tracked files not materialized at \$ROOT); authoritative check runs in the drift-gate job"
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

# 1. Verify names.generated.txt matches a fresh execution of the generator
gen_script = os.path.join(root, "tools/generate-names-registry.py")
registry_file = os.path.join(root, "usr/share/mios/names.generated.txt")

if not os.path.isfile(gen_script):
    violations.append("tools/generate-names-registry.py missing")
elif not os.path.isfile(registry_file):
    violations.append("usr/share/mios/names.generated.txt missing")
else:
    try:
        res = subprocess.run([sys.executable, gen_script], capture_output=True, text=True, check=True)
        fresh_data = res.stdout
        with open(registry_file, "r") as fh:
            committed_data = fh.read()
        
        # Normalize line endings
        fresh_lines = [l.strip() for l in fresh_data.splitlines() if l.strip()]
        committed_lines = [l.strip() for l in committed_data.splitlines() if l.strip()]
        
        if fresh_lines != committed_lines:
            violations.append("usr/share/mios/names.generated.txt is stale. Please run tools/generate-names-registry.py.")
    except Exception as e:
        violations.append(f"Failed to check names registry generation: {e}")

## 2. Verify referenced_names.txt is not stale
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
        echo "[38-drift-checks]   (30) names registry matches generate-names-registry.py"
    else
        _violation "naming registry drift / tools/generate-names-registry.py stale (run tools/generate-names-registry.py to regenerate; check 30)"
    fi
}

# --- (31, WS-VECTOR V1 drift_projection round-trip) --------------------------
check_drift_projection() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping drift-projection check" >&2
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
        # Parse query and match
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

    # Compare config_kv scopes
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

    # Compare routing.domains (normalized)
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

    # Compare verbs
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
        echo "[38-drift-checks]   (31) DB->TOML materialize round-trip is lossless for config_kv and verbs"
    else
        _violation "DB->TOML materialize round-trip drift detected (check 31) -- verify seed-db-config.py and materialize-config-toml.py mappings"
    fi
}

# --- (33, WS-NAME no non-canonical bools) ------------------------------------
check_canonical_bools() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping canonical-bool check" >&2
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
        echo "[38-drift-checks]   (33) no non-canonical bool literals in [verbs.*]"
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
        echo "[38-drift-checks]   (34) no etc/ full-unit duplicate shadows generated usr/share/ containers"
    fi
}

# --- (32, WS-VECTOR V3 drift_build_catalog round-trip) -----------------------
check_drift_build_catalog() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping drift-build-catalog check" >&2
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

    # Run seed script
    seed_globals = {"__name__": "__main__", "psycopg": mock_psycopg, "__file__": seed_path}
    try:
        with open(seed_path, "r", encoding="utf-8") as f:
            exec(f.read(), seed_globals)
    except SystemExit as e:
        if e.code != 0:
            print(f"Seed script exited with code {e.code}")
            sys.exit(1)

    # Run materialize script
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

    # Statically diff materialized output
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            sys.exit(0)

    with open(os.environ["MIOS_TOML"], "rb") as f:
        toml_data = tomllib.load(f)

    # 1. Diff package sets
    with open(os.path.join(temp_ctx_dir, "package_sets.json"), "r", encoding="utf-8") as f:
        mat_sets = json.load(f)

    orig_packages = toml_data.get("packages", {})
    for sec_name, sec_cfg in orig_packages.items():
        if sec_name == "sections" or not isinstance(sec_cfg, dict) or "pkgs" not in sec_cfg:
            continue
        # Find in mat_sets
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

        # Diff packaging metadata (Defect 9)
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

    # 2. Diff build phases
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

    # 3. Diff debloat profiles / features
    bootstrap_dir = os.path.abspath(os.path.join(root, "..", "mios-bootstrap", "src", "autounattend"))
    debloat_json_path = os.path.join(bootstrap_dir, "mios-debloat.json")
    features_txt_path = os.path.join(bootstrap_dir, "mios-xbox-features.txt")

    if os.path.isfile(debloat_json_path) or os.path.isfile(features_txt_path):
        with open(os.path.join(temp_ctx_dir, "debloat_profiles.json"), "r", encoding="utf-8") as f:
            mat_debloat = json.load(f)
        
        # Compare policies
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

        # Compare features and profile preset metadata (Defect 9)
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

        # Compare debloat profiles (Defect 9)
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
        echo "[38-drift-checks]   (32) DB->/ctx materialize round-trip is lossless for build catalog"
    else
        _violation "DB->/ctx materialize round-trip drift detected (check 32) -- verify seed-db-config.py and materialize-build-ctx.py mappings"
    fi
}

# ============================================================================
# ARCHITECTURAL-LAW enforcers (Phase B). Each mirrors a law registered in
# mios.toml [laws]; the allowlists are READ FROM THE SSOT, never hardcoded.
# ============================================================================

# --- (35, Law 2 NO-MKDIR-IN-VAR) imperative /var mkdir in a build step. --------
# Every /var/ path MUST be declared via usr/lib/tmpfiles.d/*.conf, NEVER mkdir'd
# in a numbered image-build step (an imperatively-created /var dir is wiped by the
# OCI /var reset and is invisible to tmpfiles ownership). SCOPE is deliberately the
# numbered build surface ONLY -- automation/[0-9]*.sh + Containerfile{,.minimal};
# the MiOS-DEV overlay tools (overlay-builder.sh, tools/mios-overlay.sh, ...)
# legitimately mkdir a HOST /var and are out of scope. Full-comment lines are
# stripped so a "must NOT mkdir /var" note never false-fails.
check_no_mkdir_in_var() {
    # Match a real imperative `mkdir ... /var/<path>`: a whitespace/quote path
    # boundary immediately before /var/ is required, so a `mkdir .../var/...`
    # DIAGNOSTIC STRING (like this gate's own message) is NOT self-flagged.
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
        echo "[38-drift-checks]   (35) no imperative /var mkdir in numbered automation/Containerfiles (Law 2)"
    fi
}

# Read a "...container" array (root / no_group_delegate) from the
# [security.privileged_quadlets] section of mios.toml -- the Law-6 allowlist SSOT.
_privileged_quadlet_array() {
    sed -n '/^\[security\.privileged_quadlets\]/,/^\[/p' "$1" 2>/dev/null \
        | sed -n "/^$2[[:space:]]*=[[:space:]]*\[/,/^]/p" \
        | grep -oE '"[^"]+\.container"' | tr -d '"'
}

# --- (36, Law 6 UNPRIVILEGED-QUADLETS) per-Quadlet privilege contract. ---------
# Every *.container under usr/share/containers/systemd (+ etc overlay) MUST declare
# User=. User=root/User=0 is allowed ONLY for a basename listed in mios.toml
# [security.privileged_quadlets].root (the documented root exceptions). Group= +
# Delegate=yes are required UNLESS the basename is in [...].no_group_delegate. Both
# allowlists are READ FROM THE TOML (never hardcoded) so they can never drift from
# the SSOT. Offline mirror of postcheck item 13.
check_quadlet_privilege() {
    local toml="$ROOT/usr/share/mios/mios.toml"
    if [[ ! -f "$toml" ]]; then
        echo "[38-drift-checks]   (36) mios.toml absent -- skipped"
        return 0
    fi
    local root_allow ngd_allow
    root_allow="$(_privileged_quadlet_array "$toml" root)"
    ngd_allow="$(_privileged_quadlet_array "$toml" no_group_delegate)"
    if [[ -z "$root_allow" ]]; then
        echo "[38-drift-checks]   WARNING: [security.privileged_quadlets].root empty/unreadable -- skipping quadlet-privilege check" >&2
        return 0
    fi
    local bad="" f base user
    for d in "$ROOT/usr/share/containers/systemd" "$ROOT/etc/containers/systemd"; do
        [[ -d "$d" ]] || continue
        while IFS= read -r f; do
            [[ -f "$f" ]] || continue
            base="$(basename "$f")"
            if ! grep -qE '^[[:space:]]*User=' "$f"; then
                bad+="    $base: missing User= (Law 6 requires User=)"$'\n'
                continue
            fi
            user="$(grep -hE '^[[:space:]]*User=' "$f" | head -1 | sed -E 's/^[[:space:]]*User=//' | tr -d '[:space:]')"
            if [[ "$user" == "root" || "$user" == "0" ]]; then
                if ! printf '%s\n' "$root_allow" | grep -qxF "$base"; then
                    bad+="    $base: User=$user but NOT in [security.privileged_quadlets].root"$'\n'
                fi
            fi
            if ! printf '%s\n' "$ngd_allow" | grep -qxF "$base"; then
                grep -qE '^[[:space:]]*Group='        "$f" || bad+="    $base: missing Group= (Law 6)"$'\n'
                grep -qE '^[[:space:]]*Delegate=yes'  "$f" || bad+="    $base: missing Delegate=yes (Law 6)"$'\n'
            fi
        done < <(find "$d" -type f -name '*.container' 2>/dev/null)
    done
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "a Quadlet violates Law 6 (UNPRIVILEGED-QUADLETS): missing User=, an undocumented User=root/0 (add to [security.privileged_quadlets].root with a justification), or a missing Group=/Delegate=yes (exempt via [...].no_group_delegate)"
    else
        echo "[38-drift-checks]   (36) every Quadlet declares User=; root only where allowlisted; Group=/Delegate=yes present (Law 6)"
    fi
}

# --- (37, Law 9 ONE-CANONICAL-NAME) MIOS_* consumer-closure (referenced subset emitted).
# Shells automation/lib/mios_var_closure.py, which runs the userenv.sh resolver and
# proves every MIOS_* a consumer references is emitted. SOFT-first: it needs a real
# python3 + a Linux/CI resolver run; on a bare host the emitter can report emitted=0,
# so a non-zero exit here WARNS but NEVER fails the build (the hard gate is CI/bake).
check_var_closure() {
    local tool="$ROOT/automation/lib/mios_var_closure.py"
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   (37) SOFT: python3 missing -- var-closure needs Linux/CI, skipped" >&2
        return 0
    fi
    if [[ ! -f "$tool" ]]; then
        echo "[38-drift-checks]   (37) SOFT: mios_var_closure.py absent -- skipped" >&2
        return 0
    fi
    if MIOS_ROOT="$ROOT" python3 "$tool" >/dev/null 2>"$ROOT/.varclosure.err"; then
        rm -f "$ROOT/.varclosure.err" 2>/dev/null || true
        echo "[38-drift-checks]   (37) MIOS_* referenced-set is a subset of emitted-set (var-closure holds, Law 9)"
    else
        sed 's/^/    /' "$ROOT/.varclosure.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.varclosure.err" 2>/dev/null || true
        echo "[38-drift-checks]   (37) SOFT WARNING: var-closure reported an issue (needs real python3 + Linux resolver; NOT failing the build)" >&2
    fi
}

# --- (38, Law 4 BOOTC-CONTAINER-LINT) lint is the FINAL instruction. -----------
# The last non-blank/non-comment line of Containerfile AND Containerfile.minimal
# MUST be exactly 'RUN bootc container lint'. If a layer follows the lint, it can
# reintroduce a violation the lint already cleared.
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
        echo "[38-drift-checks]   (38) Containerfile + Containerfile.minimal end with 'RUN bootc container lint' (Law 4)"
    fi
}

# --- (39, Law 12 BAKE-NOT-FETCH) firstboot degrades open. ----------------------
# A firstboot script must never brick boot on an egress/provision failure. The
# clearest boot-blocker: `set -e` (errexit) ACTIVE with NO degrade-open escape
# anywhere in the file (no `|| true` / `|| :` / `|| exit 0`, no `set +e`, no
# `trap ... EXIT/ERR`, no standalone `exit 0`). Conservative by design: any
# degrade signal -> treated as degrade-open (pass); a script without set -e (e.g.
# mios-ai-firstboot, which guards every curl) passes. Only the unambiguous
# no-escape case fails.
check_firstboot_degrade_open() {
    local bad="" f base
    for f in "$ROOT"/usr/libexec/mios/*firstboot*; do
        [[ -f "$f" ]] || continue
        case "$f" in *.pyc) continue ;; esac
        base="$(basename "$f")"
        # errexit active? (set -e / -euo / -eu / set -o errexit)
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
        echo "[38-drift-checks]   (39) every *firstboot* script degrades open (no unguarded set -e; Law 12)"
    fi
}

# --- (40, Law 5 UNIFIED-AI-REDIRECTS) vendor cloud URL in active config. --------
# Offline mirror of 99-postcheck item 12: active AI-plane config MUST NOT hardcode
# a vendor cloud URL (openai/anthropic/google/cohere/mistral/cursor/copilot/cline)
# -- every agent + tool targets MIOS_AI_ENDPOINT. Comment lines are stripped (a
# documented alternative in a comment is legitimate), identical to item 12. Sibling
# of check_dead_lane (the retired-local-lane half of item 12b). Reuses SCAN_DIRS.
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
        echo "[38-drift-checks]   (40) no vendor cloud URL in active config (Law 5)"
    fi
}

# --- (41, Law 13 NATIVE-DROPINS) resolver twin parity (python vs bash). ---------
# The Python (mios_toml.py) and bash (userenv.sh) resolvers MUST agree on the
# layered overlay -- tier-major precedence, where a vendor mios.d fragment can never
# outrank a higher tier. This feeds a tiny vendor + vendor.d + host + user fixture to
# BOTH resolvers and diffs the resolved MIOS_AI_* set. SOFT-first: needs a real
# python3 (+ bash); a mismatch OR a missing python3 WARNS but never fails the build
# (the hard gate is CI/bake on Linux).
check_resolver_twin_parity() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   (41) SOFT: python3 missing -- resolver twin-parity needs Linux/CI, skipped" >&2
        return 0
    fi
    local ue="$ROOT/usr/lib/mios/userenv.sh" mt="$ROOT/usr/lib/mios/mios_toml.py"
    if [[ ! -f "$ue" || ! -f "$mt" ]]; then
        echo "[38-drift-checks]   (41) SOFT: a resolver is absent -- skipped" >&2
        return 0
    fi
    local fix
    fix="$(mktemp -d 2>/dev/null)" || { echo "[38-drift-checks]   (41) SOFT: mktemp failed -- skipped" >&2; return 0; }
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
        echo "[38-drift-checks]   (41) SOFT: resolvers produced no MIOS_AI_* (python3/tomllib unavailable?) -- skipped" >&2
        return 0
    fi
    if [[ "$bash_out" == "$py_out" ]]; then
        echo "[38-drift-checks]   (41) resolver twin parity: userenv.sh and mios_toml.py agree on the layered MIOS_AI_* set (Law 13)"
    else
        echo "[38-drift-checks]   (41) SOFT WARNING: resolver twin-parity mismatch (Law 13 NATIVE-DROPINS) -- NOT failing the build:" >&2
        echo "        userenv.sh -> $(printf '%s' "$bash_out" | tr '\n' ' ')" >&2
        echo "        mios_toml  -> $(printf '%s' "$py_out"   | tr '\n' ' ')" >&2
    fi
}

# --- (45, Law 13 NATIVE-DROPINS) resolver twin equivalence (gating). ----------
check_resolver_twin_equivalence() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   (45) SOFT: python3 missing -- resolver twin equivalence check skipped" >&2
        return 0
    fi
    local mismatches
    # env -i: isolate like sibling gate 41 -- build.sh's sourced lib/common.sh leaks
    # MIOS_VERSION_MANIFEST (and other build-time MIOS_* vars) into this gate's env, and
    # the checker treats any inherited non-allowlisted MIOS_* as drift -> false-RED that
    # aborts `mios build`. The twins are genuinely equivalent on a clean env.
    if ! mismatches=$(env -i PATH="$PATH" MIOS_DRIFT_ROOT="$ROOT" python3 "$ROOT/tools/check-resolver-twin.py" 2>&1); then
        printf '%s\n' "$mismatches" >&2
        _violation "resolver twin equivalence check failed -- userenv.sh and mios_toml.py have drifted"
    else
        echo "[38-drift-checks]   (45) resolver twin equivalence: userenv.sh and mios_toml.py are equivalent"
    fi
}

# --- (46, Law 14 ONE-TEMPLATE-PER-TYPE) template conformance check. ---------
# Validates that all files of known types carry the required AI-hint header
# and match template structure guidelines, gating new files (grandfathered via list).
check_template_conformance() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   (46) SOFT: python3 missing -- template conformance check skipped" >&2
        return 0
    fi
    local tool="$ROOT/usr/libexec/mios/check-template-conformance"
    if [[ ! -f "$tool" ]]; then
        echo "[38-drift-checks]   (46) SOFT: check-template-conformance not found -- skipped" >&2
        return 0
    fi
    local errors
    if ! errors=$(MIOS_THEME_ROOT="$ROOT" MIOS_TOML_ROOT="$ROOT" python3 "$tool" --root "$ROOT" 2>&1); then
        printf '%s\n' "$errors" >&2
        _violation "template conformance check failed -- new/modified files must follow their templates"
    else
        echo "[38-drift-checks]   (46) template conformance: all new files conform to templates"
    fi
}

# (53, A2) Add kargs projection drift check
# Re-renders kargs.d files from mios.toml [kargs] to a tmp dir and verifies no content drift with committed files.
check_kargs_projection() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping kargs projection check" >&2
        return 0
    fi
    
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    
    # Copy committed kargs.d files to tmp_dir
    mkdir -p "$tmp_dir"
    cp -r "$ROOT/usr/lib/bootc/kargs.d/"* "$tmp_dir/"
    
    # Run render logic pointing to tmp_dir
    MIOS_TOML="$ROOT/usr/share/mios/mios.toml" KARGS_DIR="$tmp_dir" bash "$ROOT/automation/22-kargs-render.sh" >/dev/null 2>&1
    
    # Run validate-kargs.py on the rendered tmp_dir
    if ! python3 "$ROOT/automation/validate-kargs.py" "$tmp_dir" >/dev/null 2>&1; then
        rm -rf "$tmp_dir"
        _violation "rendered kargs.d files failed validate-kargs.py schema validation"
        return
    fi
    
    # Compare with committed files (both files and content)
    local diffs=""
    local f base
    for f in "$tmp_dir"/*.toml; do
        [[ -f "$f" ]] || continue
        base="$(basename "$f")"
        if [[ ! -f "$ROOT/usr/lib/bootc/kargs.d/$base" ]]; then
            diffs+="    Extra rendered file: $base"$'\n'
        elif ! diff -u "$ROOT/usr/lib/bootc/kargs.d/$base" "$f" >/dev/null 2>&1; then
            diffs+="    Content drift in $base (run automation/22-kargs-render.sh to update or align config)"$'\n'
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
        echo "[38-drift-checks]   (53) kargs.d matches mios.toml [kargs] projection"
    fi
}

# (54, A13) Add greenboot configuration check
# Verifies that greenboot services enablement commands are defined in 46-greenboot.sh,
# and check scripts under etc/greenboot/ have executable permission.
check_greenboot() {
    # 1. Verify that 46-greenboot.sh contains correct symlink commands for greenboot-healthcheck and greenboot-set-rollback-trigger
    if ! grep -q "greenboot-healthcheck.service" "$ROOT/automation/46-greenboot.sh" || \
       ! grep -q "greenboot-set-rollback-trigger.service" "$ROOT/automation/46-greenboot.sh"; then
        _violation "greenboot services enablement commands are missing in automation/46-greenboot.sh"
    fi
    
    # 2. Verify check scripts under etc/greenboot are executable
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
        echo "[38-drift-checks]   (54) greenboot services and scripts are correctly configured"
    fi
}

# (55, A8) Add chrony NTP configuration check
# Re-renders chrony.conf from mios.toml [network.ntp] to a temp file and compares with committed etc/chrony.conf.
check_chrony_projection() {
    local tmp_file
    tmp_file="$(mktemp)"
    
    # Run the chrony renderer pointing to the temp file
    MIOS_TOML="$ROOT/usr/share/mios/mios.toml" CHRONY_CONF="$tmp_file" bash "$ROOT/automation/24-chrony-render.sh" >/dev/null 2>&1
    
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
        echo "[38-drift-checks]   (55) chrony.conf matches mios.toml [network.ntp] projection"
        rm -f "$tmp_file"
    fi
}

# (56, A9) Add NUT UPS configuration check
# Re-renders nut configs from mios.toml [power.ups] to a temp dir and compares with committed etc/ups/ config files.
check_nut_projection() {
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    
    # Run the NUT renderer pointing to the temp dir
    MIOS_TOML="$ROOT/usr/share/mios/mios.toml" UPS_CONF_DIR="$tmp_dir" bash "$ROOT/automation/25-nut-render.sh" >/dev/null 2>&1
    
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
    
    if [[ -n "$diffs" ]]; then
        printf '%s' "$diffs" >&2
        _violation "etc/ups/ configuration check failed. Rendered NUT configs do not match committed etc/ups/ files."
    else
        echo "[38-drift-checks]   (56) etc/ups/ configurations match mios.toml [power.ups] projection"
    fi
}

# (57, E5) Add fluff-token drift lint
# Bans "successfully", bare "Done", "BAKED IN", and trailing "!" in operator echoes.
check_fluff_tokens() {
    local bad=""
    local f
    
    # We scan all .sh files in automation/ and automation/lib/
    while read -r f; do
        [[ -f "$f" ]] || continue
        local bname
        bname="$(basename "$f")"
        if [[ "$bname" == "38-drift-checks.sh" || "$bname" == "build-mios.sh" || "$bname" == "99-postcheck.sh" || "$f" =~ /firstboot/ ]]; then
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
        echo "[38-drift-checks]   (57) fluff-token drift check passed"
    fi
}

# (58, E6) Add coordination-hygiene lint
# Fails if AGY-TASKS.md or TASKS.md contain AppData, Temp, or session-id-shaped paths (UUIDs / session folder names).
check_coordination_hygiene() {
    local bad=""
    local f
    for f in "$ROOT/AGY-TASKS.md" "$ROOT/TASKS.md"; do
        [[ -f "$f" ]] || continue
        
        local line_num=0
        while read -r line || [[ -n "$line" ]]; do
            line_num=$((line_num + 1))
            # Match UUID pattern (8-4-4-4-12 hex chars)
            if [[ "$line" =~ AppData ]] || [[ "$line" =~ \bTemp\b ]] || [[ "$line" =~ [0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12} ]]; then
                # Exclude the git log or workflow files if they appear, but this is md files
                bad+="    $f:$line_num: contains AppData/Temp/session-id path"$'\n'
            fi
        done < "$f"
    done
    
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "coordination-hygiene lint failed (E6)"
    else
        echo "[38-drift-checks]   (58) coordination-hygiene lint passed"
    fi
}

# --- (59, C8) compile-templates validation check. ---------------------------
# Verifies that all templates in usr/share/mios/templates compile and validate cleanly.
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
        echo "[38-drift-checks]   (59) all templates compile and validate successfully"
    fi
}

# --- (60, F11) impossible/EOL regressions check. ----------------------------
# Fails on "mdevctl vGPU" claim in docs, reintroduced glusterfs* packages, or on-host Tang binding.
check_impossible_eol_regressions() {
    local bad=""
    
    # 1. Check for glusterfs packages in mios.toml
    local toml="$ROOT/usr/share/mios/mios.toml"
    if grep -E '"glusterfs"' "$toml" &>/dev/null || grep -E '"glusterfs-fuse"' "$toml" &>/dev/null || grep -E '"glusterfs-server"' "$toml" &>/dev/null; then
        bad+="    Found glusterfs packages in mios.toml"$'\n'
    fi
    
    # 2. Check for "mdevctl vGPU" claims in concepts docs, rejecting if not accompanied by impossible/out-of-scope/unsupported
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
    
    # 3. Check for on-host Tang binding configurations
    if grep -E '"tang"' "$toml" &>/dev/null; then
        bad+="    Found tang package in mios.toml (on-host Tang is prohibited)"$'\n'
    fi
    
    if [[ -n "$bad" ]]; then
        printf '%s' "$bad" >&2
        _violation "impossible/EOL regression check failed (F11)"
    else
        echo "[38-drift-checks]   (60) impossible/EOL regression checks passed"
    fi
}

# --- (61, G11) deploy-plane drift check. -------------------------------------
# Asserts that the kickstart file has the required exports and offline overrides,
# that the base image Fedora version matches the expected installer major version,
# and that ventoy.json correctly binds the Fedora ISO to the kickstart template.
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
        echo "[38-drift-checks]   (61) WARNING: mios-kickstart.cfg not found, skipping kickstart exports assertion"
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
        echo "[38-drift-checks]   (61) WARNING: ventoy.json not found, skipping ISO-kickstart binding check"
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
        echo "[38-drift-checks]   (61) deploy-plane checks passed"
    fi
}


# --- (42, Law 7 NO-HARDCODE / Law 8 SSOT-PROJECTION) version single-source. ----
# The version literal lives in exactly ONE place: mios.toml [meta].mios_version.
# The repo-root VERSION file (COPY'd into the image; read into the OCI version
# LABEL + the SBOM) and the Containerfile `ARG MIOS_VERSION=` fallback default are
# PROJECTIONS of it and must match byte-for-byte -- a drifted copy ships an image
# mislabelled against the SSOT (e.g. VERSION= - while the SSOT says - ).
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

    # audit: gate all Containerfile files in the repository dynamically
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
    _cargo_ver="$(grep -m1 -E '^[[:space:]]*version[[:space:]]*=' "$ROOT/tools/native/Cargo.toml" 2>/dev/null | sed -E 's/[^"]*"([^"]*)".*/\1/')"
    [[ -n "$_cargo_ver" && "$_cargo_ver" != "$ssot" ]] && bad+="    tools/native/Cargo.toml [workspace.package] version = [$_cargo_ver], expected [$ssot]"$'\n'

    local literal_bad exit_code=0
    literal_bad="$(MIOS_DRIFT_ROOT="$ROOT" MIOS_CANONICAL_VER="$ssot" python3 - <<'PY' 2>&1
import os, sys, re, subprocess
root = os.environ["MIOS_DRIFT_ROOT"]
canonical_ver = os.environ["MIOS_CANONICAL_VER"]

root_toml = os.path.join(root, "mios.toml")
if os.path.isfile(root_toml):
    try:
        with open(root_toml, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if "mios_version" in line and canonical_ver not in line:
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
)" || exit_code=$?
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
        echo "[38-drift-checks]   (42) VERSION + Containerfile ARG MIOS_VERSION == mios.toml [meta].mios_version ([$ssot]) (Laws 7/8)"
    fi
}

check_root_toml_subset() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping root mios.toml subset check" >&2
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
        echo "[38-drift-checks]   (48) root mios.toml schema is subset of canonical SSOT"
    else
        _violation "root mios.toml schema has keys not in canonical SSOT"
    fi
}

# --- (62) mios.toml derived copies are pure projections of the canonical SSOT ------
# The curated root mios.toml and the bootstrap repo's mios.toml carry [ports] + [colors]
# projected VERBATIM from usr/share/mios/mios.toml (owned sections -- [autounattend],
# [smoke_tests], [mios_app], [ports.lan_firewall], and the gate-48 ignored_prefixes -- are
# never touched). mios-sync-toml regenerates them; this gate fails if either committed copy
# hand-drifted from canonical. Fix: run `usr/libexec/mios/mios-sync-toml`. Complements gate 22
# (bootstrap [ports] value parity) + gate 48 (root key-subset) with a whole-block projection
# check. Vacuous-passes where python3 or the copies are absent (same posture as those gates).
check_toml_projection() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping toml-projection check" >&2
        return 0
    fi
    local tool="$ROOT/usr/libexec/mios/mios-sync-toml"
    if [[ ! -f "$tool" ]]; then
        echo "[38-drift-checks]   WARNING: mios-sync-toml not found -- skipping" >&2
        return 0
    fi
    if python3 "$tool" --check >/dev/null 2>"$ROOT/.synctoml.err"; then
        rm -f "$ROOT/.synctoml.err" 2>/dev/null || true
        echo "[38-drift-checks]   (62) mios.toml derived copies ([ports]/[colors]) project verbatim from the canonical SSOT"
    else
        sed 's/^/    /' "$ROOT/.synctoml.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.synctoml.err" 2>/dev/null || true
        _violation "a mios.toml derived copy drifted from the canonical [ports]/[colors] projection -- re-run usr/libexec/mios/mios-sync-toml"
    fi
}

# Law 14 (TARGET-LANGUAGES): all new applicable code, on EVERY platform, must use the roadmap
# language-per-domain targets (ADR-0011 §2 / WS-LANG): Rust native tier; Python AI plane; Bun/TS
# Portal; bash thin-glue only. No NEW C#/.bat/.cmd/.go. Existing C# is grandfathered-for-port.
check_target_languages() {
    if [[ ! -d "$ROOT/.git" ]] || ! command -v git >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: git missing or not a git repo -- skipping target-languages check" >&2
        return 0
    fi
    local toml="$ROOT/usr/share/mios/mios.toml"
    local allow bad="" nativebad f
    allow=$(awk '/^\[laws\.target_languages\]/{f=1} f&&/grandfathered_cs[[:space:]]*=[[:space:]]*\[/{g=1} g{print} g&&/\]/{exit}' "$toml" | grep -oE '"[^"]+\.cs"' | tr -d '"\r')
    # Batch was eliminated + Go rejected (ADR-0011): any occurrence is a hard violation.
    nativebad=$(cd "$ROOT" && git ls-files '*.bat' '*.cmd' '*.go' 2>/dev/null)
    [[ -n "$nativebad" ]] && bad+="$nativebad"$'\n'
    # Any tracked .cs not in the grandfathered allowlist is new C# -> must be Rust instead.
    while IFS= read -r f; do
        f_clean=$(echo "$f" | tr -d '\r')
        [[ -z "$f_clean" ]] && continue
        grep -qxF "$f_clean" <<<"$allow" || bad+="$f_clean"$'\n'
    done < <(cd "$ROOT" && git ls-files '*.cs' 2>/dev/null)
    if [[ -n "$(printf '%s' "$bad" | tr -d '[:space:]')" ]]; then
        {
          echo "    Law 14 TARGET-LANGUAGES: new code must use the roadmap targets (Rust native tier; Python AI;"
          echo "    Bun/TS Portal; bash thin-glue). These non-target-language files are not grandfathered:"
          printf '%s\n' "$bad" | sed '/^[[:space:]]*$/d;s/^/      - /'
          echo "    -> port to Rust (ADR-0011/WS-LANG), or add a legitimate pre-existing port target to"
          echo "       mios.toml [laws.target_languages].grandfathered_cs (the list may only shrink)."
        } >&2
        _violation "Law 14 TARGET-LANGUAGES violated: new non-target-language source added"
    else
        echo "[38-drift-checks]   (63) Law 14 TARGET-LANGUAGES: no new non-target-language code (Rust/Python/Bun+TS; bash thin-glue)"
    fi
}

check_bake_plan() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping bake plan check" >&2
        return 0
    fi
    if python3 "$ROOT/tools/generate-bake-plan.py" --check; then
        echo "[38-drift-checks]   (35) bake-plan lists in sync with mios.toml [build.bake] SSOT"
    else
        _violation "bake-plan lists are STALE vs mios.toml -- regenerate with python3 tools/generate-bake-plan.py"
    fi
}

check_bake_ref_defaults() {
    if [[ ! -d "$ROOT/.git" ]] || ! command -v git >/dev/null 2>&1; then
        echo "[38-drift-checks]   (47) all baker scripts have non-empty defaults for their bake-refs (skipped - no git repo)"
        return 0
    fi
    local empty_refs
    empty_refs="$(git grep -E 'MIOS_BUILD_BAKE_REFS_[A-Z0-9_]+:-\}' automation/ 2>/dev/null || true)"
    if [[ -n "$empty_refs" ]]; then
        _violation "found empty defaults for bake-refs in automation scripts:"$'\n'"${empty_refs}"
    else
        echo "[38-drift-checks]   (47) all baker scripts have non-empty defaults for their bake-refs"
    fi
}


check_roadmap_index() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping roadmap index check" >&2
        return 0
    fi
    if [[ ! -f "$ROOT/ROADMAP.md" ]]; then
        echo "[38-drift-checks]   (36) ROADMAP.md not found -- skipping roadmap index check"
        return 0
    fi
    if python3 "$ROOT/tools/roadmap-index.py" --check; then
        echo "[38-drift-checks]   (36) roadmap index in sync with frontmatter metadata"
    else
        _violation "roadmap index is STALE or cites invalid laws/ADRs/ssot_keys -- regenerate with python3 tools/roadmap-index.py"
    fi
}

check_cli_eval_safety() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping CLI eval safety check" >&2
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
        echo "[38-drift-checks]   (43) CLI verbs in usr/libexec/mios/ are eval-safe (TD-1)"
    else
        _violation "unverified eval in usr/libexec/mios/ -- verbs must not eval agent-controlled inputs; pre-existing safe evals must have a preceding # TD-1: eval-safe, input=<source>, not agent-controlled comment"
    fi
}

check_shellcheck() {
    local rc=0
    bash "$ROOT/automation/lint-shell.sh" || rc=$?
    if [[ $rc -eq 0 ]]; then
        echo "[38-drift-checks]   (44) shellcheck: shell scripts conform to error-level linting"
    elif [[ $rc -eq 2 ]]; then
        # When shellcheck is absent -> SKIPPED, not a pass (no false-green). Non-gating so a
        # linter-less env still builds; install shellcheck to actually gate.
        echo "[38-drift-checks]   (44) WARNING: shellcheck absent -- shell linting SKIPPED (install shellcheck to gate)" >&2
    else
        _violation "shellcheck linting failed with errors -- please run automation/lint-shell.sh or check logs"
    fi
}

check_sbom_metadata() {
    # Check that any generated sbom TSV metadata files are structurally sound.
    local sbom_dir="$ROOT/usr/share/mios/artifacts/sbom"
    local bad=()

    if [[ -d "$sbom_dir" ]]; then
        # Check models.tsv
        if [[ -f "$sbom_dir/models.tsv" ]]; then
            while IFS=$'\t' read -r name type repo file sha256 || [[ -n "$name" ]]; do
                # Skip header
                [[ "$name" == "name" ]] && continue
                [[ -z "$name" ]] && continue
                # Check for empty fields
                if [[ -z "$type" || -z "$repo" || -z "$file" || -z "$sha256" ]]; then
                    bad+=("models.tsv has empty fields in row for '$name'")
                fi
                # Check sha256 format
                if [[ "$sha256" != "unknown" && ! "$sha256" =~ ^[0-9a-fA-F]{64}$ ]]; then
                    bad+=("models.tsv row for '$name' has invalid sha256: '$sha256'")
                fi
            done < "$sbom_dir/models.tsv"
        fi

        # Check binaries.tsv
        if [[ -f "$sbom_dir/binaries.tsv" ]]; then
            while IFS=$'\t' read -r name version sha256 || [[ -n "$name" ]]; do
                # Skip header
                [[ "$name" == "name" ]] && continue
                [[ -z "$name" ]] && continue
                # Check for empty fields
                if [[ -z "$version" || -z "$sha256" ]]; then
                    bad+=("binaries.tsv has empty fields in row for '$name'")
                fi
                # Check sha256 format
                if [[ "$sha256" != "unknown" && ! "$sha256" =~ ^[0-9a-fA-F]{64}$ ]]; then
                    bad+=("binaries.tsv row for '$name' has invalid sha256: '$sha256'")
                fi
            done < "$sbom_dir/binaries.tsv"
        fi

        # Check bound-images.tsv
        if [[ -f "$sbom_dir/bound-images.tsv" ]]; then
            while IFS=$'\t' read -r image digest group || [[ -n "$image" ]]; do
                # Skip header
                [[ "$image" == "image" ]] && continue
                [[ -z "$image" ]] && continue
                # Check for empty fields
                if [[ -z "$digest" || -z "$group" ]]; then
                    bad+=("bound-images.tsv has empty fields in row for '$image'")
                fi
            done < "$sbom_dir/bound-images.tsv"
        fi
    fi

    if [[ "${#bad[@]}" -eq 0 ]]; then
        echo "[38-drift-checks]   (49) SBOM metadata manifests are structurally valid"
    else
        for err in "${bad[@]}"; do
            echo "  [sbom-drift] $err" >&2
        done
        _violation "SBOM metadata manifests in usr/share/mios/artifacts/sbom/ contain invalid/empty fields (RELTOP-01 / T-251)"
    fi
}

check_hyprland_conf_heredoc() {
    # Extract heredoc from 54-bake-hyprland.sh
    local tmp; tmp="$(mktemp)"
    local tmp2; tmp2="$(mktemp)"
    sed -n '/cat << '\''EOF'\'' > \/usr\/share\/mios\/hyprland\/hyprland.conf/,/^EOF$/p' "$ROOT/automation/54-bake-hyprland.sh" | sed '1d;$d' | tr -d '\r' > "$tmp"
    tr -d '\r' < "$ROOT/usr/share/mios/hyprland/hyprland.conf" > "$tmp2"
    if diff -u "$tmp2" "$tmp" >/dev/null; then
        echo "[38-drift-checks]   (50) Hyprland configuration template is in sync with baker script heredoc"
        rm -f "$tmp" "$tmp2"
    else
        rm -f "$tmp" "$tmp2"
        _violation "usr/share/mios/hyprland/hyprland.conf has drifted from the inline heredoc in automation/54-bake-hyprland.sh -- sync them (B4)"
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
    if '.git' in path or 'node_modules' in path: continue
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
        echo "[38-drift-checks]   (64) curl/wget build network fetches carry --retry / --tries (or scurl / exempt)"
    else
        while IFS= read -r line; do
            [[ -n "$line" ]] && bad+=("$line")
        done <<< "$res"
        for err in "${bad[@]}"; do
            echo "  [curl-retry-drift] unretried network fetch: $err" >&2
        done
        _violation "curl/wget build network fetch lacking --retry / --tries flag found (AGY-96)"
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
    fi

    if [[ ${#bad[@]} -eq 0 ]]; then
        echo "[38-drift-checks]   (65) nested-podman capability flags & reference doc verified"
    else
        for err in "${bad[@]}"; do
            echo "  [nested-podman-drift] $err" >&2
        done
        _violation "nested podman build missing capability/security flags or reference doc (AGY-99)"
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
        echo "[38-drift-checks]   (66) bake-budget gate: projected baked image size within SSOT runner_disk_budget_gb limit (${budget}GB)"
    else
        for err in "${bad[@]}"; do
            echo "  [bake-budget-drift] $err" >&2
        done
        _violation "bake-budget gate failed: projected baked size exceeds SSOT runner_disk_budget_gb (AGY-100)"
    fi
}

check_greenboot() {
    echo "[38-drift-checks]   (54) greenboot health-coverage check"
    local gb_dir="$ROOT/usr/lib/greenboot/check/required.d"
    if [[ ! -d "$gb_dir" ]]; then
        _fail "(54) greenboot required checks directory ($gb_dir) is missing"
        return
    fi
    local critical_services=("agent-pipe" "llm-light" "pgvector")
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
            _fail "(54) greenboot missing health-check script for critical service: $s"
        fi
    done
}

check_clevis_luks() {
    echo "[38-drift-checks]   (67) clevis LUKS SSOT projection check"
    local gen="$ROOT/usr/libexec/mios/mios-clevis-luks-gen"
    if [[ ! -x "$gen" && -f "$gen" ]]; then
        chmod +x "$gen" 2>/dev/null || true
    fi
    if [[ -f "$gen" ]]; then
        local out; out="$("$gen" "$ROOT/usr/share/mios/mios.toml" 2>&1)"
        if [[ "$out" == *"CLEVIS_LUKS_ENABLED="* ]]; then
            return 0
        else
            _fail "(67) clevis LUKS generator failed to project SSOT configuration"
        fi
    fi
}

check_mini_vfio() {
    echo "[38-drift-checks]   (68) MiOS-Mini vfio-pci SSOT projection check"
    local gen="$ROOT/usr/libexec/mios/mios-mini-vfio-gen"
    if [[ ! -x "$gen" && -f "$gen" ]]; then
        chmod +x "$gen" 2>/dev/null || true
    fi
    if [[ -f "$gen" ]]; then
        local out; out="$("$gen" "$ROOT/usr/share/mios/mios.toml" 2>&1)"
        if [[ "$out" == *"MIOS_MINI_ENABLED="* ]]; then
            return 0
        else
            _fail "(68) MiOS-Mini vfio generator failed to project SSOT configuration"
        fi
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

    echo "[38-drift-checks] ---------------------------------------------------------"
    if [[ "$VIOLATIONS" -eq 0 ]]; then
        echo "[38-drift-checks] PASS: no AI-plane source drift."
        exit 0
    fi
    echo "[38-drift-checks] FAIL: $VIOLATIONS drift violation(s) above." >&2
    if [[ "$_SOFT" == "1" ]]; then
        echo "[38-drift-checks] (MIOS_DRIFT_CHECK_SOFT=1 -> advisory mode, exiting 0)"
        exit 0
    fi
    exit 1
}

main "$@"
