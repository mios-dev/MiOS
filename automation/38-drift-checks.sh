#!/usr/bin/env bash
# AI-hint: Source-tree drift fitness-functions (WS-0A). Read-only static analysis over the repo (== system root) that FAILS on AI-plane SSOT drift no other gate catches: a retired local :11434 lane in active config, a retired model-id (gemma4 / qwen3:1.7b) hardcoded in a CONSUMER unit, a [nodes.local-*] lane pointing at a localhost port no shipped unit serves, an ai/v1/*.json manifest that won't parse or references a missing schema file, (check 5, WS-10) AI-hint header coverage regressing past [ai_tag].max_untagged, and (check 6, WS-3) an agent-pipe sibling module importing the server.py monolith (modular-monolith boundary). Sibling to 38-ssot-lint.sh; runs standalone, as a build sub-phase, and as a CI/PR drift-gate (needs NO built image). bash + grep + (optional) python3 for the toml/json/coverage checks.
# AI-related: ./automation/38-ssot-lint.sh, ./automation/99-postcheck.sh, ./usr/libexec/mios/mios-ai-hint-coverage, ./usr/share/mios/mios.toml, ./usr/share/mios/ai/v1
# AI-functions: _violation, check_dead_lane, check_retired_models, check_structured, check_hint_coverage, check_module_boundary, check_rbac_tiers, check_ai_manifest, check_package_registry, check_cli_sql_safety, check_module_test_coverage, check_capability_manifest, check_pod_quadlets, check_egress_firewall, check_unwired_modules, check_globals_ports, main
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

# --- (1) Retired local :11434 lane in active config. -------------------------
# Mirror of 99-postcheck.sh check 12b, on the SOURCE tree (PR-time). The local
# ollama lane on :11434 was retired (everything moved to mios-llm-light :11450);
# a stale local ref silently 404s a refine / sys-agent / DCI call. Only LOCAL
# forms match -- remote tailnet :11434 lane templates are legitimate.
check_dead_lane() {
    local pattern='(localhost|127\.0\.0\.1|host\.containers\.internal):11434'
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
        _violation "retired local :11434 lane in active source config (use the live lane, e.g. mios-llm-light :11450)"
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
         "engines","nodes","backend"}
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
# SurrealDB HTTP transport (post_sql/_sql -> :8000/sql, surreal-ns headers) or
# hand-rolled SQL-escaping (_pgesc/_pgq single-quote doubling). The WS-A3 cutover
# replaced both with PARAMETERIZED pg -- values bound OUT-OF-BAND via
# mios-pg-query --exec-json / mios-db --pg-json -- so a regression silently
# no-ops on pg (dead SurrealQL) or reopens a SQL-injection hole. TWO tools carry
# The allowlist is now EMPTY: every libexec tool was cut over to parameterized pg
# (mios-daemon's dead SurrealQL transports _db_post/_db_post_sync are stubbed
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
        _violation "a libexec CLI (re)introduced the retired SurrealDB transport (post_sql/_sql/:8000/sql) or hand-rolled SQL escaping (_pgesc/_pgq) -- use parameterized pg via mios-pg-query --exec-json / mios-db --pg-json (WS-A3)"
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
    if MIOS_ROOT="$ROOT" python3 "$gen" --check; then
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
        _violation "bootstrap mios.toml [ports] table diverges from main repository mios.toml (drift detected)"
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
        _violation "some [agent_pipe] keys do not have code consumers inside the agent-pipe codebase (T-108 drift detected)"
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
        _violation "bare port literals detected in execution paths (T-121/T-125 drift detected)"
    fi
}

# --- (25, Phase-1 palette SSOT) Theme-surface projection gate. -----------------
# Every committed theme surface (btop, oh-my-posh, quickshell, fastfetch, the
# app-shell CSS, the terminal OSC fallbacks) is PROJECTED from mios.toml
# [colors]/[theme] via mios-theme-render's token-substitution templates. This
# gate regenerates each surface from the SSOT and FAILS on any diff, so a palette
# value can NEVER drift from the SSOT (re-run `mios-sync-theme` to refresh --
# it is the one global runtime theme command). Same regenerate-and-diff shape as
# checks 8/12/13/14, over the theme surfaces.
check_theme_projection() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "[38-drift-checks]   WARNING: python3 missing -- skipping theme-projection check" >&2
        return 0
    fi
    local tool="$ROOT/usr/libexec/mios/mios-theme-render"
    if [[ ! -f "$tool" ]]; then
        echo "[38-drift-checks]   WARNING: mios-theme-render not found -- skipping" >&2
        return 0
    fi
    if MIOS_THEME_ROOT="$ROOT" python3 "$tool" check >/dev/null 2>"$ROOT/.theme.err"; then
        rm -f "$ROOT/.theme.err" 2>/dev/null || true
        echo "[38-drift-checks]   (25) every committed theme surface projects from mios.toml [colors] SSOT"
    else
        sed 's/^/    /' "$ROOT/.theme.err" >&2 2>/dev/null || true
        rm -f "$ROOT/.theme.err" 2>/dev/null || true
        _violation "a theme surface drifted from the mios.toml [colors]/[theme] SSOT projection -- re-run mios-sync-theme (Phase-1 palette drift-gate; mios-theme-render)"
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
            
            # Check venv consumer edge:
            if "/usr/lib/mios/agents/.venv/" in content:
                if "mios-ai-firstboot.service" not in after_requires_targets:
                    violations.append(f"{f} uses agents venv but lacks 'After=... mios-ai-firstboot.service'")
            
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
    if MIOS_DRIFT_ROOT="$ROOT" python3 - <<'PY'
import os, sys, re, subprocess

root = os.environ["MIOS_DRIFT_ROOT"]
violations = []

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

# 2. Verify slots array in userenv.sh matches canonical or allowed legacy names
userenv_sh = os.path.join(root, "tools/lib/userenv.sh")
if not os.path.isfile(userenv_sh):
    violations.append("tools/lib/userenv.sh missing")
else:
    try:
        with open(userenv_sh, "r") as fh:
            content = fh.read()
            
        slots_match = re.search(r"slots\s*=\s*\[(.*?)\]\s*\n\s*(?:stack_id|for\s+dotted)", content, re.DOTALL)
        if not slots_match:
            violations.append("Could not find slots array in userenv.sh")
        else:
            slots_str = slots_match.group(1)
            slots = []
            for m in re.finditer(r'\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)', slots_str):
                slots.append((m.group(1), m.group(2)))
                
            legacy_allowed = {
                "identity.username": ["MIOS_USER", "MIOS_DEFAULT_USER"],
                "identity.fullname": "MIOS_USER_FULLNAME",
                "identity.hostname": ["MIOS_HOSTNAME", "MIOS_DEFAULT_HOST"],
                "identity.shell": ["MIOS_USER_SHELL", "MIOS_DEFAULT_SHELL"],
                "identity.groups": ["MIOS_USER_GROUPS", "MIOS_DEFAULT_GROUPS"],
                "identity.default_password": "MIOS_DEFAULT_PASSWORD",
                "accounts.db_backed": "MIOS_ACCOUNTS_DB_BACKED",
                "locale.timezone": ["MIOS_TIMEZONE", "MIOS_DEFAULT_TIMEZONE"],
                "locale.keyboard_layout": ["MIOS_KEYBOARD", "MIOS_DEFAULT_KEYBOARD"],
                "locale.language": ["MIOS_LOCALE", "MIOS_DEFAULT_LOCALE"],
                "auth.ssh_key_action": "MIOS_SSH_KEY_ACTION",
                "auth.password_policy": "MIOS_PASSWORD_POLICY",
                "network.firewalld_default_zone": "MIOS_FIREWALLD_ZONE",
                "ai.api_key": "MIOS_AI_KEY",
                "ai.chat_vision_model": "MIOS_AGENT_PIPE_VISION_MODEL",
                "ai.stack_model": "MIOS_STACK_MODEL",
                "ai.embed_model": ["MIOS_VERB_EMBED_MODEL", "MIOS_AI_EMBED_MODEL"],
                "desktop.flatpaks": "MIOS_FLATPAKS",
                "desktop.color_scheme": "MIOS_COLOR_SCHEME",
                "bootstrap.mios_repo": "MIOS_REPO_URL",
                "bootstrap.bootstrap_repo": "MIOS_BOOTSTRAP_REPO_URL",
                "ports.ssh": ["MIOS_PORT_SSH", "MIOS_SSH_PORT"],
                "ports.forge_http": ["MIOS_PORT_FORGE_HTTP", "MIOS_FORGE_HTTP_PORT"],
                "ports.forge_ssh": ["MIOS_PORT_FORGE_SSH", "MIOS_FORGE_SSH_PORT"],
                "ports.cockpit": ["MIOS_PORT_COCKPIT", "MIOS_COCKPIT_PORT"],
                "ports.cockpit_link": "MIOS_PORT_COCKPIT_LINK",
                "ports.searxng": ["MIOS_PORT_SEARXNG", "MIOS_SEARXNG_PORT"],
                "ports.crawl4ai": "MIOS_PORT_CRAWL4AI",
                "ports.firecrawl": "MIOS_PORT_FIRECRAWL",
                "ports.hermes": ["MIOS_PORT_HERMES", "MIOS_HERMES_PORT"],
                "ports.hermes_worker": "MIOS_PORT_HERMES_WORKER",
                "ports.hermes_dashboard": "MIOS_PORT_HERMES_DASHBOARD",
                "ports.open_webui": "MIOS_PORT_OPEN_WEBUI",
                "ports.code_server": "MIOS_PORT_CODE_SERVER",
                "ports.k3s_api": "MIOS_K3S_API_PORT",
                "ports.guacamole_web": "MIOS_GUACAMOLE_PORT",
                "ports.ceph_dashboard": "MIOS_CEPH_DASHBOARD_PORT",
                "ports.rdp": "MIOS_RDP_PORT",
                "ports.pgvector": "MIOS_PORT_PGVECTOR",
                "ports.llm_light": "MIOS_PORT_LLM_LIGHT",
                "ports.cpu_node": "MIOS_PORT_CPU_NODE",
                "ports.agent_pipe": "MIOS_PORT_AGENT_PIPE",
                "ports.adguard_dns": "MIOS_PORT_ADGUARD_DNS",
                "ports.adguard_ui": "MIOS_PORT_ADGUARD_UI",
                "ports.opencode_gateway": "MIOS_PORT_OPENCODE_GATEWAY",
                "ports.vllm": "MIOS_PORT_VLLM",
                "ports.sglang": "MIOS_PORT_SGLANG",
                "ports.prefilter": "MIOS_PORT_PREFILTER",
                "ports.arbiter": "MIOS_PORT_ARBITER",
                "ports.daemon_agent": "MIOS_PORT_DAEMON_AGENT",
                "ports.model_router": "MIOS_PORT_MODEL_ROUTER",
                "ports.oscontrol": "MIOS_PORT_OSCONTROL",
                "ports.mcp": "MIOS_PORT_MCP",
                "ports.ttyd_bash": "MIOS_PORT_TTYD_BASH",
                "ports.ttyd_powershell": "MIOS_PORT_TTYD_POWERSHELL",
                "hermes.endpoint": "MIOS_HERMES_ENDPOINT",
                "agents.hermes.endpoint": "MIOS_HERMES_WORKER_ENDPOINT",
                "a2a.discover_port": "MIOS_A2A_DISCOVER_PORT",
                "a2a.public_domain": "MIOS_PUBLIC_DOMAIN",
                "routing.model_modalities_embeddings": "MIOS_MODEL_MODALITIES_EMBEDDINGS",
                "routing.model_modalities_image": "MIOS_MODEL_MODALITIES_IMAGE",
                "routing.integer_param_keywords": "MIOS_INTEGER_PARAM_KEYWORDS",
                "routing.boolean_param_keywords": "MIOS_BOOLEAN_PARAM_KEYWORDS",
                "ai.opencode_gateway_workdir": "MIOS_OPENCODE_WORKDIR",
                "ai.agent_venv": "MIOS_HERMES_VENV",
                "ai.agent_install_dir": "MIOS_HERMES_DIR",
                "ai.vllm.v1_engine": "MIOS_VLLM_USE_V1",
                "ai.key": "MIOS_AI_KEY",
                "ai.hermes_agent_ref": "MIOS_HERMES_AGENT_REF",
                "ai.hermes_agent_repo": "MIOS_HERMES_AGENT_REPO",
                "ai.hermes_backend_url": "MIOS_HERMES_BACKEND_URL",
                "ai.mcp_registry": "MIOS_MCP_REGISTRY",
                "ai.system_prompt_file": "MIOS_SYSTEM_PROMPT_FILE",
                "ai.tokenizer_backend": "MIOS_TOKENIZER_BACKEND",
                "ai.tokenizer_cache_dir": "MIOS_TOKENIZER_CACHE_DIR",
                "ai.tokenizer_encoding": "MIOS_TOKENIZER_ENCODING",
                "ai.tokenizer_path": "MIOS_TOKENIZER_PATH",
                "bootstrap.dev_vm.base_image": "MIOS_DEV_VM_BASE_IMAGE",
                "bootstrap.dev_vm.cpus": "MIOS_DEV_VM_CPUS",
                "bootstrap.dev_vm.disk_size_gb": "MIOS_DEV_VM_DISK_GB",
                "bootstrap.dev_vm.gpu_passthrough": "MIOS_DEV_VM_GPU",
                "bootstrap.dev_vm.host_reserve.cpu_min": "MIOS_DEV_VM_CPU_RESERVE_MIN",
                "bootstrap.dev_vm.host_reserve.cpu_pct": "MIOS_DEV_VM_CPU_RESERVE_PCT",
                "bootstrap.dev_vm.host_reserve.disk_gb": "MIOS_DEV_VM_DISK_RESERVE_GB",
                "bootstrap.dev_vm.host_reserve.memory_gb": "MIOS_DEV_VM_MEMORY_RESERVE_GB",
                "bootstrap.dev_vm.host_reserve.memory_pct": "MIOS_DEV_VM_MEMORY_RESERVE_PCT",
                "bootstrap.dev_vm.machine_name": "MIOS_BUILDER_DISTRO",
                "bootstrap.dev_vm.memory_mb": "MIOS_DEV_VM_MEMORY_MB",
                "bootstrap.dev_vm.wsl_distro": "MIOS_WSL_DISTRO",
                "bootstrap.host_storage.drive_letter": "MIOS_DATA_DISK_LETTER",
                "bootstrap.host_storage.shrink_mb": "MIOS_DATA_DISK_MB",
                "code_mode.gid": "MIOS_CODEMODE_GID",
                "code_mode.uid": "MIOS_CODEMODE_UID",
                "image.base": "MIOS_BASE_IMAGE",
                "image.bib": "MIOS_BIB_IMAGE",
                "image.branch": "MIOS_BRANCH",
                "image.local_tag": "MIOS_LOCAL_TAG",
                "security.fapolicyd_observe.enable": "MIOS_FAPOLICYD_OBSERVE_ENABLE",
                # image.sidecars
                "image.sidecars.k3s_version": "MIOS_K3S_VERSION",
                "image.sidecars.k3s": "MIOS_K3S_IMAGE",
                "image.sidecars.ceph_version": "MIOS_CEPH_VERSION",
                "image.sidecars.ceph": "MIOS_CEPH_IMAGE",
                "image.sidecars.forge_version": "MIOS_FORGE_VERSION",
                "image.sidecars.forge": "MIOS_FORGE_IMAGE",
                "image.sidecars.searxng_version": "MIOS_SEARXNG_VERSION",
                "image.sidecars.searxng": "MIOS_SEARXNG_IMAGE",
                "image.sidecars.hermes_version": "MIOS_HERMES_VERSION",
                "image.sidecars.hermes": "MIOS_HERMES_IMAGE",
                "image.sidecars.open_webui_version": "MIOS_OPEN_WEBUI_VERSION",
                "image.sidecars.open_webui": "MIOS_OPEN_WEBUI_IMAGE",
                "image.sidecars.code_server_version": "MIOS_CODE_SERVER_VERSION",
                "image.sidecars.code_server": "MIOS_CODE_SERVER_IMAGE",
                "image.sidecars.guacamole_version": "MIOS_GUACAMOLE_VERSION",
                "image.sidecars.guacamole": "MIOS_GUACAMOLE_IMAGE",
                "image.sidecars.forge_runner_version": "MIOS_FORGE_RUNNER_VERSION",
                "image.sidecars.forge_runner": "MIOS_FORGE_RUNNER_IMAGE",
                "image.sidecars.crowdsec_version": "MIOS_CROWDSEC_VERSION",
                "image.sidecars.crowdsec": "MIOS_CROWDSEC_IMAGE",
                "image.sidecars.postgres_version": "MIOS_POSTGRES_VERSION",
                "image.sidecars.postgres": "MIOS_POSTGRES_IMAGE",
                "image.sidecars.guacd_version": "MIOS_GUACD_VERSION",
                "image.sidecars.guacd": "MIOS_GUACD_IMAGE",
                "image.sidecars.pxe_hub_version": "MIOS_PXE_HUB_VERSION",
                "image.sidecars.pxe_hub": "MIOS_PXE_HUB_IMAGE",
                "image.sidecars.bib_alpine": "MIOS_BIB_ALPINE_IMAGE",
                "image.sidecars.pgvector_version": "MIOS_PGVECTOR_VERSION",
                "image.sidecars.pgvector": "MIOS_PGVECTOR_IMAGE",
                "image.sidecars.llm_light_version": "MIOS_LLM_LIGHT_VERSION",
                "image.sidecars.llm_light": "MIOS_LLM_LIGHT_IMAGE",
                "image.sidecars.adguard_version": "MIOS_ADGUARD_VERSION",
                "image.sidecars.adguard": "MIOS_ADGUARD_IMAGE",
                # services
                "services.forge.user": "MIOS_FORGE_USER",
                "services.forge.uid": "MIOS_FORGE_UID",
                "services.forge.gid": "MIOS_FORGE_GID",
                "services.searxng.user": "MIOS_SEARXNG_USER",
                "services.searxng.uid": "MIOS_SEARXNG_UID",
                "services.searxng.gid": "MIOS_SEARXNG_GID",
                "services.ceph.user": "MIOS_CEPH_USER",
                "services.ceph.uid": "MIOS_CEPH_UID",
                "services.ceph.gid": "MIOS_CEPH_GID",
                "services.hermes.user": "MIOS_HERMES_USER",
                "services.hermes.uid": "MIOS_HERMES_UID",
                "services.hermes.gid": "MIOS_HERMES_GID",
                "services.open_webui.user": "MIOS_OPEN_WEBUI_USER",
                "services.open_webui.uid": "MIOS_OPEN_WEBUI_UID",
                "services.open_webui.gid": "MIOS_OPEN_WEBUI_GID",
                "services.pgvector.user": "MIOS_PGVECTOR_USER",
                "services.pgvector.uid": "MIOS_PGVECTOR_UID",
                "services.pgvector.gid": "MIOS_PGVECTOR_GID",
                "services.llamacpp.user": "MIOS_LLAMACPP_USER",
                "services.llamacpp.uid": "MIOS_LLAMACPP_UID",
                "services.llamacpp.gid": "MIOS_LLAMACPP_GID",
                "services.agent_pipe.user": "MIOS_AGENT_PIPE_USER",
                "services.agent_pipe.uid": "MIOS_AGENT_PIPE_UID",
                "services.agent_pipe.gid": "MIOS_AGENT_PIPE_GID",
                "services.webtools.user": ["MIOS_WEBTOOLS_USER", "MIOS_CRAWL4AI_USER"],
                "services.webtools.uid": ["MIOS_WEBTOOLS_UID", "MIOS_CRAWL4AI_UID"],
                "services.webtools.gid": ["MIOS_WEBTOOLS_GID", "MIOS_CRAWL4AI_GID"],
                "services.webtools.cdp_url": "MIOS_CRAWL_CDP_URL",
                "services.webtools.camoufox": "MIOS_CRAWL_CAMOUFOX",
                "services.webtools.min_chars": "MIOS_CRAWL_MIN_CHARS",
                "services.webtools.firecrawl_workers": "MIOS_FIRECRAWL_WORKERS",
                "services.webtools.firecrawl_bull_key": "MIOS_FIRECRAWL_BULL_KEY",
                "services.webtools.firecrawl_log_level": "MIOS_FIRECRAWL_LOG_LEVEL",
                "services.adguard.user": "MIOS_ADGUARD_USER",
                "services.adguard.uid": "MIOS_ADGUARD_UID",
                "services.adguard.gid": "MIOS_ADGUARD_GID",
                # storage.cephfs
                "storage.cephfs.enable": "MIOS_CEPHFS_ENABLE",
                "storage.cephfs.monitors": "MIOS_CEPHFS_MONITORS",
                "storage.cephfs.fs_name": "MIOS_CEPHFS_FS_NAME",
                "storage.cephfs.tenant_id": "MIOS_CEPHFS_TENANT_ID",
                "storage.cephfs.data_pool_hot": "MIOS_CEPHFS_DATA_POOL_HOT",
                "storage.cephfs.data_pool_bulk": "MIOS_CEPHFS_DATA_POOL_BULK",
                "storage.cephfs.xdg_cache_home_override": "MIOS_XDG_CACHE_LOCAL_PATH",
                "storage.cephfs.mount_options": "MIOS_CEPHFS_MOUNT_OPTIONS",
                "storage.cephfs.keyring_dir": "MIOS_CEPHFS_KEYRING_DIR",
                "storage.cephfs.automount_enable": "MIOS_CEPHFS_AUTOMOUNT_ENABLE",
                "storage.cephfs.automount_idle_timeout_s": "MIOS_CEPHFS_AUTOMOUNT_IDLE_TIMEOUT_S",
                # verity
                "uki.verity_uki_build": "MIOS_UKI_VERITY_BUILD",
                "verity.antifab_enable": "MIOS_ANTIFAB_ENABLE",
                "verity.antifab_min_entities": "MIOS_ANTIFAB_MIN_ENTITIES",
                "verity.antifab_ground_min": "MIOS_ANTIFAB_GROUND_MIN",
                # pgvector
                "pgvector.db_backend": "MIOS_DB_BACKEND",
                "pgvector.rls_enable": "MIOS_DB_RLS_ENABLE",
                "pgvector.host": "MIOS_PG_HOST",
                "pgvector.user": "MIOS_PG_USER",
                "pgvector.pass": "MIOS_PG_PASS",
                "pgvector.db": "MIOS_PG_DB",
                "pgvector.data_dir": "MIOS_PG_DATA_DIR",
                "pgvector.schema_init": "MIOS_PG_SCHEMA_INIT",
                "pgvector.embed_model": "MIOS_PG_EMBED_MODEL",
                "pgvector.enable": "MIOS_PG_ENABLE",
                "pgvector.pool_enable": "MIOS_PG_POOL_ENABLE",
                "pgvector.pool_min": "MIOS_PG_POOL_MIN",
                "pgvector.pool_max": "MIOS_PG_POOL_MAX",
                "pgvector.hnsw_iterative_scan": "MIOS_PG_HNSW_ITERATIVE_SCAN",
                "pgvector.hnsw_max_scan_tuples": "MIOS_PG_HNSW_MAX_SCAN_TUPLES",
                "pgvector.hnsw_scan_mem_multiplier": "MIOS_PG_HNSW_SCAN_MEM_MULTIPLIER",
                "pgvector.backup_enable": "MIOS_PG_BACKUP_ENABLE",
                "pgvector.backup_dir": "MIOS_PG_BACKUP_DIR",
                "pgvector.backup_keep": "MIOS_PG_BACKUP_KEEP",
                "pgvector.listen_loopback": "MIOS_PG_LISTEN_LOOPBACK",
                # llamacpp
                "llamacpp.cpu_node_threads": "MIOS_CPU_NODE_THREADS",
                # paths
                "paths.ai_dir": "MIOS_AI_DIR",
                "paths.ai_models_dir": "MIOS_AI_MODELS_DIR",
                "paths.ai_mcp_dir": "MIOS_AI_MCP_DIR",
                "paths.ai_scratch_dir": "MIOS_AI_SCRATCH_DIR",
                "paths.ai_memory_dir": "MIOS_AI_MEMORY_DIR",
                "paths.ai_journal": "MIOS_AI_JOURNAL",
                "paths.install_env": "MIOS_INSTALL_ENV",
                "paths.profile_toml_vendor": "MIOS_PROFILE_TOML_VENDOR",
                "paths.profile_toml_host": "MIOS_PROFILE_TOML_HOST",
                "paths.wsl_firstboot_done": "MIOS_WSLBOOT_DONE",
                "paths.mios_toml": "MIOS_TOML",
                # build
                "build.rechunk_max_layers": "MIOS_RECHUNK_MAX_LAYERS",
                "build.ai_ram_floor_gb": "MIOS_AI_RAM_FLOOR_GB",
                "build.local_tag": "MIOS_LOCAL_TAG",
                # network.quadlet
                "network.quadlet.network": "MIOS_QUADLET_NETWORK",
                "network.quadlet.subnet": "MIOS_QUADLET_SUBNET",
                "network.quadlet.core_subnet": "MIOS_CORE_NET_SUBNET",
                "network.quadlet.core_gateway": "MIOS_CORE_NET_GATEWAY",
                # frontier
                "frontier.orch_engine": "MIOS_A2O_ORCH_ENGINE",
                "frontier.orch_model": "MIOS_A2O_ORCH_MODEL",
                "frontier.orch_effort": "MIOS_A2O_ORCH_EFFORT",
                "frontier.lane_a_engine": "MIOS_A2O_LANE_A_ENGINE",
                "frontier.lane_a_model": "MIOS_A2O_LANE_A_MODEL",
                "frontier.lane_a_effort": "MIOS_A2O_LANE_A_EFFORT",
                "frontier.lane_a_role": "MIOS_A2O_LANE_A_ROLE",
                "frontier.lane_b_engine": "MIOS_A2O_LANE_B_ENGINE",
                "frontier.lane_b_model": "MIOS_A2O_LANE_B_MODEL",
                "frontier.lane_b_effort": "MIOS_A2O_LANE_B_EFFORT",
                "frontier.lane_b_role": "MIOS_A2O_LANE_B_ROLE",
                "frontier.lane_b_fallback_engine": "MIOS_A2O_LANE_B_FALLBACK_ENGINE",
                "frontier.lane_b_fallback_model": "MIOS_A2O_LANE_B_FALLBACK_MODEL",
                "frontier.lane_b_fallback_effort": "MIOS_A2O_LANE_B_FALLBACK_EFFORT",
                "frontier.lane_b_prefer_fallback": "MIOS_A2O_LANE_B_PREFER_FALLBACK",
                "frontier.claude_effort_flag": "MIOS_A2O_CLAUDE_EFFORT_FLAG",
                "frontier.agy_effort_flag": "MIOS_A2O_AGY_EFFORT_FLAG",
                "frontier.gemini_effort_flag": "MIOS_A2O_GEMINI_EFFORT_FLAG",
                "frontier.stream_to_reasoning": "MIOS_A2O_STREAM_REASONING",
                "frontier.stream_path": "MIOS_A2O_STREAM_PATH",
                # legacy fallback section keys
                "user.name": "MIOS_USER_FULLNAME",
                "user.hostname": "MIOS_HOSTNAME",
                "flatpaks.install": "MIOS_FLATPAKS",
                # wsl2
                "wsl2.networking_mode": "MIOS_WSL2_NETWORKING_MODE",
                "wsl2.localhost_forwarding": "MIOS_WSL2_LOCALHOST_FORWARDING",
                "wsl2.firewall": "MIOS_WSL2_FIREWALL",
                "wsl2.gui_applications": "MIOS_WSL2_GUI_APPLICATIONS",
                "wsl2.desktop_compat.gdk_backend": "MIOS_WSLG_GDK_BACKEND",
                "wsl2.desktop_compat.moz_wayland": "MIOS_WSLG_MOZ_WAYLAND",
                "wsl2.desktop_compat.qt_platform": "MIOS_WSLG_QT_PLATFORM",
                "wsl2.dev_vm.quadlet_network_mode": "MIOS_QUADLET_DEV_NETWORK_MODE",
                # fs_watcher
                "fs_watcher.watch_dirs": "MIOS_FS_WATCHER_DIRS",
                # refine / polish
                "refine.timeout_seconds": "MIOS_REFINE_TIMEOUT_S",
                "polish.timeout_seconds": "MIOS_POLISH_TIMEOUT_S",
                # portal
                "portal.public_host": "MIOS_PUBLIC_HOST",
                "portal.require_login": "MIOS_PORTAL_REQUIRE_LOGIN",
                "portal.user": "MIOS_PORTAL_USER",
                "portal.password": "MIOS_PORTAL_PASSWORD",
                "portal.session_ttl": "MIOS_PORTAL_SESSION_TTL",
                "portal.secret": "MIOS_PORTAL_SECRET",
                # meta
                "meta.mios_version": "MIOS_VERSION",
                # ai/sglang/vllm/micro/opencode
                "ai.bake_models": "MIOS_AI_BAKE_MODELS",
                "ai.vllm.served_name": "MIOS_VLLM_SERVED_NAME",
                "ai.vllm.gpu_util": "MIOS_VLLM_GPU_UTIL",
                "ai.vllm.max_model_len": "MIOS_VLLM_MAX_MODEL_LEN",
                "ai.vllm.bake_model": "MIOS_VLLM_BAKE_MODEL",
                "ai.vllm.kv_cache_dtype": "MIOS_VLLM_KV_CACHE_DTYPE",
                "ai.vllm.tool_call_parser": "MIOS_VLLM_TOOL_CALL_PARSER",
                "ai.sglang.served_name": "MIOS_SGLANG_SERVED_NAME",
                "ai.sglang.mem_fraction": "MIOS_SGLANG_MEM_FRACTION",
                "ai.sglang.max_model_len": "MIOS_SGLANG_MAX_MODEL_LEN",
                "ai.sglang.tool_parser": "MIOS_SGLANG_TOOL_PARSER",
                "ai.sglang.reasoning_parser": "MIOS_SGLANG_REASONING_PARSER",
                "ai.sglang.bake_model": "MIOS_SGLANG_BAKE_MODEL",
                "ai.sglang.unified_radix_tree": "MIOS_SGLANG_ENABLE_UNIFIED_RADIX_TREE",
                "ai.sglang.hierarchical_cache": "MIOS_SGLANG_ENABLE_HIERARCHICAL_CACHE",
                "ai.sglang.kv_cache_dtype": "MIOS_SGLANG_KV_CACHE_DTYPE",
                "ai.micro_model": "MIOS_MICRO_MODEL",
                "ai.micro_endpoint": "MIOS_MICRO_ENDPOINT",
                "ai.opencode_install_url": "MIOS_OPENCODE_INSTALL_URL",
                "ai.opencode_version": "MIOS_OPENCODE_VERSION",
                "ai.opencode_model": "MIOS_OPENCODE_MODEL",
                "ai.opencode_provider": "MIOS_OPENCODE_PROVIDER",
                "ai.opencode_bin": "MIOS_OPENCODE_BIN",
                "ai.opencode_config": "MIOS_OPENCODE_CONFIG",
                "ai.opencode_gateway_timeout_s": "MIOS_OPENCODE_TIMEOUT_S",
                "gpu.device": "MIOS_GPU_DEVICE",
            }
            
            def is_legacy_color_match(toml_key, env_var):
                if toml_key.startswith("colors.ansi_"):
                    suffix = toml_key[len("colors.ansi_"):].upper().replace(".", "_").replace("-", "_")
                    return env_var == f"MIOS_ANSI_{suffix}"
                elif toml_key.startswith("colors."):
                    suffix = toml_key[len("colors."):].upper().replace(".", "_").replace("-", "_")
                    return env_var == f"MIOS_COLOR_{suffix}"
                return False
                
            def check_legacy(toml_key, env_var):
                if toml_key not in legacy_allowed:
                    return False
                allowed = legacy_allowed[toml_key]
                if isinstance(allowed, str):
                    return allowed == env_var
                return env_var in allowed

            mapped_keys = []
            mapped_vars = []
            
            for toml_key, env_var in slots:
                canonical = "MIOS_" + toml_key.upper().replace(".", "_").replace("-", "_")
                
                # Check mapping correctness
                is_ok = (
                    env_var == canonical or
                    check_legacy(toml_key, env_var) or
                    is_legacy_color_match(toml_key, env_var)
                )
                
                if not is_ok:
                    violations.append(f"Invalid non-canonical env mapping in userenv.sh: '{toml_key}' maps to '{env_var}' (expected canonical '{canonical}')")
                
                mapped_keys.append(toml_key)
                mapped_vars.append(env_var)
            
            # Check duplicates (except allowed duplicates)
            allowed_duplicates = {
                "ai.embed_model",
                "identity.username",
                "identity.hostname",
                "identity.shell",
                "identity.groups",
                "locale.keyboard_layout",
                "locale.language",
                "locale.timezone",
                "ports.ssh",
                "ports.forge_http",
                "ports.forge_ssh",
                "ports.cockpit",
                "ports.searxng",
                "ports.hermes",
                "services.webtools.gid",
                "services.webtools.uid",
                "services.webtools.user",
            }
            uniq_keys = set()
            for tk in mapped_keys:
                if tk in allowed_duplicates:
                    continue
                if tk in uniq_keys:
                    violations.append(f"Duplicate mapping key in userenv.sh: '{tk}'")
                uniq_keys.add(tk)
                
            allowed_duplicate_vars = {
                "MIOS_USER_FULLNAME",
                "MIOS_HOSTNAME",
                "MIOS_LOCAL_TAG",
                "MIOS_FLATPAKS",
                "MIOS_AI_KEY",
            }
            uniq_vars = set()
            for ev in mapped_vars:
                if ev in allowed_duplicate_vars:
                    continue
                if ev in uniq_vars:
                    violations.append(f"Duplicate mapping target env var in userenv.sh: '{ev}'")
                uniq_vars.add(ev)
    except Exception as e:
        violations.append(f"Failed to check userenv.sh mappings: {e}")

if violations:
    for v in sorted(violations):
        sys.stderr.write(f"    {v}\n")
    sys.exit(1)
sys.exit(0)
PY
    then
        echo "[38-drift-checks]   (30) names registry matches generate-names-registry.py and userenv.sh maps cleanly"
    else
        _violation "naming registry drift / userenv translation table violation (flatten check 30)"
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
    scopes = ["ports", "ai", "routing", "surrealdb", "pgvector", "a2a", "mcp", "observability", "sandbox", "security", "agent_passport", "agent_pipe"]
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

main() {
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
    check_capability_manifest
    check_surface_parity
    check_no_hardcode
    check_pod_quadlets
    check_egress_firewall
    check_unwired_modules
    check_cephfs_ssot
    check_converge_ssot
    check_hummingbird
    check_container_ports
    check_bootstrap_ports_drift
    check_agent_pipe_budgets
    check_no_bare_port_literals
    check_theme_projection
    check_verb_backends
    check_userenv_parity
    check_globals_ports
    check_dag_integrity
    check_names_registry
    check_drift_projection
    check_drift_build_catalog

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
