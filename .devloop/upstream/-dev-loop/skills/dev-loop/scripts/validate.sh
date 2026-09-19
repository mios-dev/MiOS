#!/usr/bin/env sh
# Conformance gate for the dev-loop plugin itself (run in CI): agentskills.io validator on every skill (portable copies),
# Claude Code plugin validation when the CLI is present, manifest/hook shapes, schemas, syntax. Exit non-zero on any failure.
set -u; PLUG=$(cd "$(dirname "$0")/../../.." && pwd); PY=${PYTHON:-python3}; FAIL=0; note() { printf '%s\n' "$*"; }
# 1. skills — the core must pass as-is; sub-skills must pass once Claude-only keys are stripped (what install.sh ships elsewhere)
T=$(mktemp -d); for s in "$PLUG"/skills/*/; do n=$(basename "$s"); mkdir -p "$T/$n"; cp "$s/SKILL.md" "$T/$n/"
  [ "$n" = dev-loop ] || "$PY" "$PLUG/skills/dev-loop/scripts/artifacts.py" strip-frontmatter "$T/$n/SKILL.md" >/dev/null
  if command -v agentskills >/dev/null 2>&1; then agentskills validate "$T/$n" >/dev/null 2>&1 && note "skill $n: ok (agentskills)" || { note "skill $n: FAIL (agentskills validate)"; agentskills validate "$T/$n"; FAIL=1; }
  else "$PY" - "$T/$n/SKILL.md" <<'PY' || FAIL=1
import sys,re; s=open(sys.argv[1]).read(); fm=s.split('---')[1]
keys=[l.split(':')[0] for l in fm.splitlines() if l and not l[0].isspace() and ':' in l]
bad=[k for k in keys if k not in ("name","description","license","compatibility","metadata","allowed-tools")]
name=re.search(r'^name:\s*(\S+)',fm,re.M).group(1); desc=re.search(r'^description:\s*(.+)$',fm,re.M).group(1)
assert not bad, f"non-spec keys {bad}"; assert re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*',name) and len(name)<=64, name; assert len(desc)<=1024, len(desc)
print("skill",name,": ok (structural; pip install skills-ref for the reference validator)")
PY
  fi; done; rm -rf "$T"
# 2. plugin manifest + hooks shape + agents frontmatter
"$PY" - "$PLUG" <<'PY' || FAIL=1
import json,sys,glob,re; P=sys.argv[1]
m=json.load(open(f"{P}/.claude-plugin/plugin.json")); assert "name" in m and "entrypoint" not in m, "plugin.json: name required, entrypoint invalid"
for k in ("skills","agents","hooks","commands","mcpServers"):
    if k in m: assert isinstance(m[k],(str,dict,list)), k
# hooks/hooks.json is auto-loaded; declaring it again makes the host refuse the whole plugin
# ("Duplicate hooks file detected"), so manifest.hooks may only name ADDITIONAL files.
_hk=m.get("hooks"); _hk=[_hk] if isinstance(_hk,str) else (_hk if isinstance(_hk,list) else [])
for _h in _hk:
    assert re.sub(r"^\./","",str(_h)) != "hooks/hooks.json", "plugin.json: remove \"hooks\": \"./hooks/hooks.json\" — the standard path is auto-loaded and declaring it fails plugin load"
h=json.load(open(f"{P}/hooks/hooks.json")); assert isinstance(h["hooks"],dict), "hooks.json must be keyed by event name"
EVENTS={"SessionStart","Setup","UserPromptSubmit","UserPromptExpansion","PreToolUse","PermissionRequest","PermissionDenied","PostToolUse","PostToolUseFailure","PostToolBatch","Notification","MessageDisplay","SubagentStart","SubagentStop","TaskCreated","TaskCompleted","Stop","StopFailure","TeammateIdle","InstructionsLoaded","ConfigChange","CwdChanged","DirectoryAdded","FileChanged","WorktreeCreate","WorktreeRemove","PreCompact","PostCompact","PreModelSwitch","PostModelSwitch","Elicitation","ElicitationResult","SessionEnd"}
for ev,groups in h["hooks"].items():
    assert ev in EVENTS, f"unknown hook event {ev}"
    for g in groups:
        for hk in g["hooks"]: assert hk.get("type") in ("command","http","mcp_tool","prompt","agent") and ("command" in hk or "url" in hk or "prompt" in hk or "server" in hk), f"{ev}: bad handler {hk}"
for a in glob.glob(f"{P}/agents/*.md"):
    s=open(a).read(); assert s.startswith("---"), f"{a}: no frontmatter"; fm=s.split("---")[1]
    assert re.search(r"^name:",fm,re.M) and re.search(r"^description:",fm,re.M), f"{a}: name/description required"
    for bad in ("hooks:","mcpServers:","permissionMode:"): assert not re.search(rf"^{bad}",fm,re.M), f"{a}: {bad} unsupported in plugin agents"
    iso=re.search(r"^isolation:\s*(\S+)",fm,re.M); assert not iso or iso.group(1)=="worktree", a
assert not (glob.glob(f"{P}/commands") ), "no root commands/ (shims live in shims/ to avoid auto-discovery)"
json.load(open(f"{P}/.mcp.json")); json.load(open(f"{P}/.claude-plugin/marketplace.json"))
print("plugin.json / hooks.json / agents / .mcp.json / marketplace.json: ok")
PY
# 3. schemas, tool strictness, python + shell syntax
"$PY" - "$PLUG" <<'PY' || FAIL=1
import json,sys; P=sys.argv[1]; A=f"{P}/skills/dev-loop/assets"
try:
    import jsonschema, glob; s=json.load(open(f"{A}/lane-schema.json")); jsonschema.Draft202012Validator.check_schema(s)
    ex=sorted(glob.glob(f"{A}/lanes*.json"))          # EVERY shipped plan, not just one: agy_host.sh validates before launching, so an example that fails the schema is an unlaunchable reference
    assert ex, f"no lanes*.json under {A} -- nothing validated"
    for f in ex: jsonschema.validate(json.load(open(f)),s)
    print(f"lane-schema + {len(ex)} example plan(s): ok")
except ImportError: print("lane-schema: jsonschema not installed (skipped)")
for t in json.load(open(f"{A}/openai-tools.json")):
    p=t["function"]["parameters"]; assert p["additionalProperties"] is False and set(p["required"])==set(p["properties"]), t["function"]["name"]
print("openai-tools strict: ok")
PY
for f in "$PLUG"/skills/dev-loop/scripts/*.py; do "$PY" -m py_compile "$f" || FAIL=1; done; rm -rf "$PLUG"/skills/dev-loop/scripts/__pycache__
for f in "$PLUG"/skills/dev-loop/scripts/*.sh "$PLUG"/hooks/*.sh; do sh -n "$f" || { note "syntax: $f"; FAIL=1; }; done; note "python/shell syntax: ok"
# 3b. behavioural tests — syntax checks above cannot see a criterion that reports PASSED unmeasured
for t in "$PLUG"/tests/test_*.py; do
  [ -f "$t" ] || continue
  "$PY" "$t" >/dev/null 2>&1 && note "tests: $(basename "$t") ok" || { note "tests: $(basename "$t") FAILED"; "$PY" "$t"; FAIL=1; }
done
# 4. Claude Code's own validator when available
command -v claude >/dev/null 2>&1 && { claude plugin validate "$PLUG" --strict || FAIL=1; } || note "claude CLI not present: run 'claude plugin validate . --strict' on a workstation"
[ "$FAIL" = 0 ] && note "== conformance: PASS" || note "== conformance: FAIL"; exit $FAIL
