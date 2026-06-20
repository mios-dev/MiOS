#!/usr/bin/env bash
# AI-hint: Source-tree drift fitness-functions (WS-0A). Read-only static analysis over the repo (== system root) that FAILS on AI-plane SSOT drift no other gate catches: a retired local :11434 lane in active config, a retired model-id (gemma4 / qwen3:1.7b) hardcoded in a CONSUMER unit, a [nodes.local-*] lane pointing at a localhost port no shipped unit serves, an ai/v1/*.json manifest that won't parse or references a missing schema file, (check 5, WS-10) AI-hint header coverage regressing past [ai_tag].max_untagged, and (check 6, WS-3) an agent-pipe sibling module importing the server.py monolith (modular-monolith boundary). Sibling to 38-ssot-lint.sh; runs standalone, as a build sub-phase, and as a CI/PR drift-gate (needs NO built image). bash + grep + (optional) python3 for the toml/json/coverage checks.
# AI-related: ./automation/38-ssot-lint.sh, ./automation/99-postcheck.sh, ./usr/libexec/mios/mios-ai-hint-coverage, ./usr/share/mios/mios.toml, ./usr/share/mios/ai/v1
# AI-functions: _violation, check_dead_lane, check_retired_models, check_structured, check_hint_coverage, check_module_boundary, main
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
# gemma4 (404 on :11450 since 2026-06-18) and qwen3:1.7b (dropped from the fleet
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

main() {
    check_dead_lane
    check_retired_models
    check_structured
    check_hint_coverage
    check_module_boundary

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
