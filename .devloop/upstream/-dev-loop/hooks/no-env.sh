#!/bin/sh
# PreToolUse(Edit|Write): refuse writes to secret-bearing or contract files from a lane
. "$(dirname "$0")/_lib.sh"; IN=$(cat); P=$(json_get "$IN" .tool_input.file_path); AG=$(json_get "$IN" .agent_type)
case "$(basename "$P")" in .env|.env.*|*.pem|*.key|id_rsa|id_ed25519|credentials|credentials.json) deny "dev-loop: refusing to write a secret-bearing file ($P). Reference secrets by env NAME.";; esac
case "$AG" in *lane-worker*) case "$(basename "$P")" in AGENTS.md|CLAUDE.md|GEMINI.md) deny "dev-loop: lanes never edit contract files; report the rule under contract_updates and the host writes it (SKILL §3).";; esac;; esac
exit 0
