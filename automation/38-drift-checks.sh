#!/usr/bin/env bash
# AI-hint: Source-tree drift fitness-functions (WS-0A). Read-only static analysis over the repo (== system root) that FAILS on AI-plane SSOT drift no other gate catches: a retired local :11434 lane in active config, a retired model-id (gemma4 / qwen3:1.7b) hardcoded in a CONSUMER unit, a [nodes.local-*] lane pointing at a localhost port no shipped unit serves, an ai/v1/*.json manifest that won't parse or references a missing schema file, (check 5, WS-10) AI-hint header coverage regressing past [ai_tag].max_untagged, and (check 6, WS-3) an agent-pipe sibling module importing the server.py monolith (modular-monolith boundary). Sibling to 38-ssot-lint.sh; runs standalone, as a build sub-phase, and as a CI/PR drift-gate (needs NO built image). bash + grep + (optional) python3 for the toml/json/coverage checks.
# AI-related: ./automation/38-ssot-lint.sh, ./automation/99-postcheck.sh, ./usr/libexec/mios/mios-ai-hint-coverage, ./usr/share/mios/mios.toml, ./usr/share/mios/ai/v1
# AI-functions: _violation, check_dead_lane, check_retired_models, check_structured, check_hint_coverage, check_module_boundary, check_rbac_tiers, check_ai_manifest, check_package_registry, check_cli_sql_safety, check_module_test_coverage, check_capability_manifest, check_pod_quadlets, check_egress_firewall, check_unwired_modules, main
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
        echo "[38-drift-checks]   (13) .pod Quadlets in sync with mios.toml [pods.*] SSOT"
    else
        _violation ".pod Quadlet(s) STALE vs mios.toml [pods.*] -- regenerate with tools/generate-pod-quadlets.py (WS-7/WS-10)"
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
    echo "[38-drift-checks]   (19) [converge] SSOT configuration is valid (stub)"
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
