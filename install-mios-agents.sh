# AI-hint: !/usr/bin/env bash Installs wrapper scripts for mios-agent-claude, mios-agent-gemini, and mios-llm to /usr/local/bin/ to inject the MiOS system prompt into various LLM ...
# AI-doc: usr/share/doc/mios/manual/_harvest/install_mios_agents_sh.md
set -euo pipefail

# MIOS_REQUIRE_AGREEMENT_ACK).
_repo_root_for_banner="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -r "${_repo_root_for_banner}/automation/lib/agreements-banner.sh" ]] && \
    . "${_repo_root_for_banner}/automation/lib/agreements-banner.sh" && \
    mios_print_agreement_banner "install-mios-agents.sh"
unset _repo_root_for_banner

MIOS_REPO="/mios"
PROMPT_SRC="${MIOS_REPO}/system-prompt.md"

if [[ ! -f "$PROMPT_SRC" ]]; then
    echo "Looking for system-prompt.md in cloned repo"
    for try in /mios/system-prompt.md /mios-bootstrap/system-prompt.md ./system-prompt.md; do
        if [[ -f "$try" ]]; then
            PROMPT_SRC="$try"
            break
        fi
    done
fi

if [[ ! -f "$PROMPT_SRC" ]]; then
    echo "ERROR: Cannot find system-prompt.md anywhere" >&2
    echo "Clone the repo first: git clone https://github.com/mios-dev/mios.git /mios" >&2
    exit 1
fi

echo "Using prompt source: $PROMPT_SRC"

sudo mkdir -p /usr/share/mios/ai /etc/mios/ai
sudo cp "$PROMPT_SRC" /usr/share/mios/ai/system.md
sudo cp "$PROMPT_SRC" /etc/mios/ai/system-prompt.md
echo "Installed system prompt to /usr/share/mios/ai/system.md"

sudo tee /usr/local/bin/mios-agent-claude > /dev/null <<'SCRIPT'
set -euo pipefail
PROMPT_FILE=""
for p in /usr/share/mios/ai/system.md /etc/mios/ai/system-prompt.md /system-prompt.md "${PWD}/system-prompt.md" "${PWD}/CLAUDE.md"; do
    [[ -r "$p" ]] && PROMPT_FILE="$p" && break
done
[[ -z "$PROMPT_FILE" ]] && { echo "Mios-agent-claude: no system prompt found" >&2; exit 1; }
echo "[agent] launching with system prompt: $PROMPT_FILE" >&2
exec claude --append-system-prompt "$(cat "$PROMPT_FILE")" "$@"
SCRIPT
sudo chmod 755 /usr/local/bin/mios-agent-claude
echo "Installed /usr/local/bin/mios-agent-claude"

sudo tee /usr/local/bin/mios-agent-gemini > /dev/null <<'SCRIPT'
set -euo pipefail
PROMPT_FILE=""
for p in /usr/share/mios/ai/system.md /etc/mios/ai/system-prompt.md /system-prompt.md "${PWD}/system-prompt.md" "${PWD}/GEMINI.md"; do
    [[ -r "$p" ]] && PROMPT_FILE="$p" && break
done
[[ -z "$PROMPT_FILE" ]] && { echo "Mios-agent-gemini: no system prompt found" >&2; exit 1; }
echo "[agent] launching with system prompt: $PROMPT_FILE" >&2
exec gemini --system-prompt "$(cat "$PROMPT_FILE")" "$@"
SCRIPT
sudo chmod 755 /usr/local/bin/mios-agent-gemini
echo "Installed /usr/local/bin/mios-agent-gemini"

sudo tee /usr/local/bin/mios-llm > /dev/null <<'SCRIPT'
set -euo pipefail
PROMPT_FILE=""
for p in /usr/share/mios/ai/system.md /etc/mios/ai/system-prompt.md /system-prompt.md "${PWD}/system-prompt.md"; do
    [[ -r "$p" ]] && PROMPT_FILE="$p" && break
done
[[ -z "$PROMPT_FILE" ]] && { echo "Mios-llm: no system prompt found" >&2; exit 1; }
ENDPOINT="${MIOS_AI_ENDPOINT:-http://localhost:8642/v1}"
MODEL="${MIOS_AI_MODEL:-mi-os-7b}"
USER_PROMPT="${*:-What are the six 'MiOS' Architectural Laws, in order?}"
echo "[agent] $MODEL @ $ENDPOINT prompt: $PROMPT_FILE" >&2
curl -sS "$ENDPOINT/chat/completions" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "$MODEL" --arg sys "$(cat "$PROMPT_FILE")" --arg user "$USER_PROMPT" \
        '{model:$model, messages:[{role:"system",content:$sys},{role:"user",content:$user}], temperature:0.3, stream:false}')" \
    | jq -r '.choices[0].message.content'
SCRIPT
sudo chmod 755 /usr/local/bin/mios-llm
echo "Installed /usr/local/bin/mios-llm"

echo ""
echo "=== Verification ==="
echo "Prompt file:"
ls -la /usr/share/mios/ai/system.md
echo ""
echo "First line:"
head -1 /usr/share/mios/ai/system.md
echo ""
echo "Launcher path check:"
grep "for p in" /usr/local/bin/mios-agent-claude
echo ""
echo "Done. Run:"
echo "  mios-agent-claude     # if the 'claude' CLI binary is installed"
echo "  mios-agent-gemini     # if the 'gemini' CLI binary is installed"
echo "  mios-llm 'your question here'   # vendor-neutral, OpenAI /v1 only"
