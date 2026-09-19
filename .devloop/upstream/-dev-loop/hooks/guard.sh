#!/bin/sh
# PreToolUse(Bash): block sweeping git adds, history rewrites on shared refs, secret printing, pipe-to-shell (SKILL §10, §12)
. "$(dirname "$0")/_lib.sh"; IN=$(cat); CMD=$(json_get "$IN" .tool_input.command)
echo "$CMD" | grep -Eq '(^|[;&|[:space:]])git[[:space:]]+add[[:space:]]+(-A|--all|-u|\.)([[:space:]]|$)' && deny "dev-loop: explicit-path staging only — never git add -A / . / -u (SKILL §12). Use git add <path>."
echo "$CMD" | grep -Eq '(^|[;&|[:space:]])git[[:space:]]+push[[:space:]].*(--force|-f)([[:space:]]|$)' && deny "dev-loop: force-push is irreversible; ask the operator first (SKILL §12)."
echo "$CMD" | grep -Eq '(curl|wget)[^|]*\|[[:space:]]*(sudo[[:space:]]+)?(sh|bash|zsh|pwsh)([[:space:]]|$)' && deny "dev-loop: pipe-to-shell is a supply-chain hole; download, inspect, verify checksum, then run."
echo "$CMD" | grep -Eq '(^|[;&|[:space:]])(printenv|env)[[:space:]]*($|[;&|])|cat[[:space:]]+[^[:space:]]*\.env([[:space:]]|$)|echo[[:space:]]+"?\$\{?[A-Z_]*(KEY|TOKEN|SECRET|PASSWORD)' && deny "dev-loop: that prints secrets into the transcript (SKILL §10). Assert presence by name: [ -n \"\${VAR:-}\" ]."
exit 0
