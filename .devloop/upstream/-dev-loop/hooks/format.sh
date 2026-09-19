#!/bin/sh
# PostToolUse(Edit|Write): non-truncation + parse check on the written file; format only if the project's formatter is configured (never introduce one)
. "$(dirname "$0")/_lib.sh"; IN=$(cat); P=$(json_get "$IN" .tool_input.file_path); [ -f "$P" ] || exit 0
[ -s "$P" ] || { printf '{"decision":"block","reason":"dev-loop: %s is now EMPTY (0 bytes) — never truncate files (SKILL §6). Restore it."}\n' "$P"; exit 0; }
case "$P" in
  *.py) python3 -m py_compile "$P" 2>/tmp/devloop-fmt.err || { printf '{"decision":"block","reason":"dev-loop: %s does not compile: %s"}\n' "$P" "$(tr '\n' ' ' </tmp/devloop-fmt.err | sed 's/"/\\"/g' | tail -c 300)"; exit 0; }
        R=$(git rev-parse --show-toplevel 2>/dev/null); [ -n "$R" ] && { [ -f "$R/ruff.toml" ] || grep -q '\[tool.ruff\]' "$R/pyproject.toml" 2>/dev/null; } && command -v ruff >/dev/null && ruff format -q "$P" 2>/dev/null;;
  *.sh) sh -n "$P" 2>/tmp/devloop-fmt.err || { printf '{"decision":"block","reason":"dev-loop: %s has a shell syntax error: %s"}\n' "$P" "$(tr '\n' ' ' </tmp/devloop-fmt.err | sed 's/"/\\"/g' | tail -c 300)"; exit 0; };;
  *.json) python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$P" 2>/dev/null || { printf '{"decision":"block","reason":"dev-loop: %s is not valid JSON"}\n' "$P"; exit 0; };;
  *.ts|*.tsx|*.js|*.jsx) R=$(git rev-parse --show-toplevel 2>/dev/null); [ -n "$R" ] && [ -f "$R/.prettierrc" -o -f "$R/prettier.config.js" ] && command -v prettier >/dev/null && prettier --log-level silent -w "$P" 2>/dev/null;;
  *.rs) command -v rustfmt >/dev/null && rustfmt --edition 2021 -q "$P" 2>/dev/null;;
  *.go) command -v gofmt >/dev/null && gofmt -w "$P" 2>/dev/null;;
esac
exit 0
