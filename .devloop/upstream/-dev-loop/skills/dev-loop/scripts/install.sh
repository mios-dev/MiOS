#!/usr/bin/env sh
# Install dev-loop into every harness found (or --all): the skill (+scripts/references/assets) and ALL command shims
# (/dev-loop /goal /research /review /ship /triage /websearch), project scope by default.
#   sh skills/dev-loop/scripts/install.sh [--all] [--user|--global] [--project] [--dry-run] [--scaffold]
#                                            [--harness claude,antigravity,gemini,codex,cursor,copilot,opencode,hermes]
# Claude Code: prefer the plugin —  claude plugin marketplace add <path-or-repo> && claude plugin install dev-loop@dev-loop-marketplace
#              (or `claude --plugin-dir <this repo>` for local dev). The copy below is the fallback for skills-only setups.
set -eu
SRC=$(cd "$(dirname "$0")/.." && pwd)            # skills/dev-loop
PLUG=$(cd "$SRC/../.." && pwd)                    # plugin root (shims/, agents/, hooks/)
ALL=0; USER_SCOPE=0; DRY=0; ONLY=""; SCAF=0
while [ $# -gt 0 ]; do case "$1" in --all) ALL=1;; --user|--global) USER_SCOPE=1;; --project) USER_SCOPE=0;; --dry-run) DRY=1;; --scaffold) SCAF=1;; --harness) ONLY=$2; shift;; *) echo "unknown $1" >&2; exit 64;; esac; shift; done
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd); H=${HOME:-~}
# name | detect | project skills root | user skills root | project cmd dir | user cmd dir | extra routes (ext=dir;...) — cmd dirs relative to ROOT / absolute for user
# Antigravity: its skills dirs give first-class /<name> slash commands on their own, so the
# shims are belt-and-braces. Upstream calls workflows deprecated (its own `migrate-workflows`
# builtin skill says so) and scans .agents|_agents|.agent|_agent/workflows/ in a workspace and
# ~/.gemini/config/{workflows,global_workflows}/ globally — NOT ~/.gemini/antigravity/workflows,
# where these used to land unread.
TABLE='
claude|claude|.claude/skills|'"$H"'/.claude/skills|.claude/commands|'"$H"'/.claude/commands|
antigravity|agy|.agents/skills|'"$H"'/.gemini/config/skills|.agents/workflows|'"$H"'/.gemini/config/workflows|
gemini|gemini|.gemini/skills|'"$H"'/.gemini/skills|.gemini/commands|'"$H"'/.gemini/commands|
codex|codex|.agents/skills|'"$H"'/.agents/skills|.codex/prompts|'"$H"'/.codex/prompts|
cursor|.cursor|.cursor/skills|'"$H"'/.cursor/skills|.cursor/commands|'"$H"'/.cursor/commands|mdc=.cursor/rules
copilot|.github|.github/skills|'"$H"'/.copilot/skills|.github/prompts|'"$H"'/.copilot/prompts|agent.md=.github/agents
opencode|opencode|.opencode/skills|'"$H"'/.config/opencode/skills|.opencode/command|'"$H"'/.config/opencode/command|
hermes|hermes|'"$H"'/.hermes/skills|'"$H"'/.hermes/skills|-|-|
'
echo "$TABLE" | while IFS='|' read -r name det pskill uskill pcmd ucmd extra; do
  [ -n "$name" ] || continue
  case ",$ONLY," in ",,"|*",$name,"*) ;; *) continue;; esac
  if [ "$ALL" = 0 ] && [ -z "$ONLY" ] && ! command -v "$det" >/dev/null 2>&1 && [ ! -e "$ROOT/$det" ] && [ ! -e "$H/$det" ]; then continue; fi
  if [ "$USER_SCOPE" = 1 ]; then SK="$uskill"; CM="$ucmd"; else case "$pskill" in /*) SK="$pskill";; *) SK="$ROOT/$pskill";; esac; case "$pcmd" in -|/*) CM="$pcmd";; *) CM="$ROOT/$pcmd";; esac; fi
  echo "[$name] skills -> $SK ; commands -> $CM"
  [ "$DRY" = 1 ] && continue
  mkdir -p "$SK"
  for s in "$PLUG"/skills/*/; do n=$(basename "$s"); rm -rf "$SK/$n"; cp -R "$s" "$SK/$n"
    [ "$name" = claude ] || python3 "$SRC/scripts/artifacts.py" strip-frontmatter "$SK/$n/SKILL.md" >/dev/null   # agentskills.io six-key conformance outside Claude Code
  done
  [ "$CM" = "-" ] && continue
  for f in "$PLUG/shims/$name"/*; do
    b=$(basename "$f"); dest="$CM"
    for route in $(printf '%s' "$extra" | tr ';' ' '); do ext=${route%%=*}; dir=${route#*=}; case "$b" in *.$ext) dest="$ROOT/$dir";; esac; done
    mkdir -p "$dest"; cp "$f" "$dest/$b"
  done
done
[ "$SCAF" = 1 ] && [ "$DRY" = 0 ] && { python3 "$SRC/scripts/artifacts.py" scaffold --root "$ROOT"; python3 "$SRC/scripts/artifacts.py" bridges --root "$ROOT"; }
python3 "$SRC/scripts/adapters.py" probe 2>/dev/null || echo "(probe: some harness binaries missing or flags drifted — see above)"
echo "done. Put real content in AGENTS.md; CLAUDE.md first line '@AGENTS.md'; GEMINI.md / .agents/rules point at it."
