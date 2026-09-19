#!/bin/sh
# Build a throwaway sandbox repo for the mixed-lane e2e test: two seeded bugs,
# two dependency-free test scripts, and a lanes file pairing one Antigravity
# lane with one Claude Code lane. Prints the sandbox path and the exact
# commands for the two ways to run the test (direct orchestrator / AGY manager).
#
#   sh tests/e2e-mixed-lanes/setup-sandbox.sh [target-dir]
#
# Default target is <repo-root>/.sandbox-e2e (kept out of git via
# .git/info/exclude, per SKILL.md §11 — never a repo change). Re-running
# recreates the sandbox from scratch.
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
SB=${1:-"$ROOT/.sandbox-e2e"}

case "$SB" in "$ROOT"/*)
    rel="${SB#"$ROOT"/}/"
    grep -qxF "$rel" "$ROOT/.git/info/exclude" 2>/dev/null || echo "$rel" >> "$ROOT/.git/info/exclude"
esac

rm -rf "$SB"
mkdir -p "$SB/tests"
cd "$SB"
git init -q -b main
git config user.email "devloop-e2e@example.invalid"
git config user.name "devloop e2e"

# Seed checks and lane runs import these modules; without this the resulting
# __pycache__/ dirties the tree and devloop.sh (correctly) refuses to start.
printf '__pycache__/\n' > .gitignore

cat > calc.py <<'EOF'
def add(a, b):
    return a - b
EOF

cat > util.py <<'EOF'
def shout(s):
    return s
EOF

cat > tests/test_calc.py <<'EOF'
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from calc import add
assert add(2, 3) == 5, f"add(2,3) expected 5, got {add(2, 3)}"
assert add(-1, 1) == 0, f"add(-1,1) expected 0, got {add(-1, 1)}"
print("test_calc OK")
EOF

cat > tests/test_util.py <<'EOF'
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from util import shout
assert shout("hi") == "HI!", f"shout('hi') expected 'HI!', got {shout('hi')!r}"
print("test_util OK")
EOF

cat > lanes.e2e.json <<'EOF'
{
  "version": "2",
  "objective": "E2E: mixed AGY + Claude Code lanes fix two seeded bugs; both two-sided gates must hold.",
  "base_ref": "main",
  "worktree_root": ".worktrees",
  "terminal_layout": "detached",
  "integration_cmd": "python3 tests/test_calc.py && python3 tests/test_util.py",
  "worker": { "max_turns": 30, "timeout_s": 480 },
  "lanes": [
    {
      "id": "agy-calc",
      "domain": "backend",
      "objective": "calc.py: add(a, b) must return the sum of a and b. Fix ONLY calc.py so that `python3 tests/test_calc.py` passes. Do not modify tests. Do not run any git command.",
      "owned_paths": ["calc.py"],
      "worker": { "harness": "antigravity" },
      "positive_cmd": "python3 tests/test_calc.py",
      "negative_control_cmd": "cp calc.py .nc-calc.bak; trap 'mv .nc-calc.bak calc.py' EXIT; printf 'def add(a, b):\\n    return 0\\n' > calc.py; python3 tests/test_calc.py",
      "negative_expect": "expected 5|AssertionError"
    },
    {
      "id": "cc-util",
      "domain": "backend",
      "objective": "util.py: shout(s) must return s.upper() plus a trailing exclamation mark. Fix ONLY util.py so that `python3 tests/test_util.py` passes. Do not modify tests. Do not run any git command.",
      "owned_paths": ["util.py"],
      "worker": {
        "harness": "claude-code",
        "allowed_tools": "Read,Edit,Write,Glob,Grep,Bash"
      },
      "positive_cmd": "python3 tests/test_util.py",
      "negative_control_cmd": "cp util.py .nc-util.bak; trap 'mv .nc-util.bak util.py' EXIT; printf 'def shout(s):\\n    return s\\n' > util.py; python3 tests/test_util.py",
      "negative_expect": "HI!|AssertionError"
    }
  ]
}
EOF

git add -- .gitignore calc.py util.py tests/test_calc.py tests/test_util.py lanes.e2e.json
git commit -q -m "e2e sandbox: seeded bugs + tests + mixed lane plan"

# Prove the seeds are really broken (a sandbox whose tests already pass would
# make every lane a no-op and the whole e2e vacuous).
python3 tests/test_calc.py >/dev/null 2>&1 && { echo "SEED ERROR: test_calc already passes" >&2; exit 1; }
python3 tests/test_util.py >/dev/null 2>&1 && { echo "SEED ERROR: test_util already passes" >&2; exit 1; }

cat <<EOF
sandbox ready: $SB   (seeds verified failing)

Run it two ways:
  A. direct orchestrator (any host):
     cd $SB && sh $ROOT/skills/dev-loop/scripts/devloop.sh lanes.e2e.json
  B. AGY as L0 manager (topology A):
     cd $SB && AGY_HOST_TIMEOUT=30m AGY_HOST_PRINT_TIMEOUT=25m \\
       sh $ROOT/skills/dev-loop/scripts/agy_host.sh lanes.e2e.json --headless --yolo

Success = exit 0, both lanes merged --no-ff onto main, integration green,
reports in .devloop/run-*/report-*.json with both controls held.
EOF
