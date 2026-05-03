#!/usr/bin/env bash
# 'MiOS' Agent Launcher Installer (vendor-neutral)
#
# Installs three thin wrappers under /usr/local/bin/ that pre-load the
# canonical 'MiOS' system prompt before launching an OpenAI-API-compatible
# CLI client:
#
#   mios-agent-claude  -- wraps the local 'claude' binary if present
#   mios-agent-gemini  -- wraps the local 'gemini' binary if present
#   mios-llm           -- generic OpenAI /v1/chat/completions client
#
# All three resolve through MIOS_AI_ENDPOINT (Architectural Law 5:
# UNIFIED-AI-REDIRECTS) and emit OpenAI-shaped requests. The first two
# wrappers exist only because their underlying CLI binaries take a
# system-prompt argument; the wrappers themselves do not contain any
# vendor logic beyond that single CLI invocation.
#
# Run: bash /path/to/install-mios-agents.sh
set -euo pipefail

MIOS_REPO="/mios"
PROMPT_SRC="${MIOS_REPO}/system-prompt.md"

# ── Verify source exists ──
if [[ ! -f "$PROMPT_SRC" ]]; then
    echo "Looking for system-prompt.md in cloned repo..."
    # Try alternate locations
    for try in /mios/system-prompt.md /mios-bootstrap/system-prompt.md ./system-prompt.md; do
        if [[ -f "$try" ]]; then
            PROMPT_SRC="$try"
            break
        fi
    done
fi

if [[ ! -f "$PROMPT_SRC" ]]; then
    echo "ERROR: Cannot find system-prompt.md anywhere." >&2
    echo "Clone the repo first: git clone https://github.com/mios-dev/mios.git /mios" >&2
    exit 1
fi

echo "Using prompt source: $PROMPT_SRC"

# ── Install prompt to canonical paths ──
sudo mkdir -p /usr/share/mios/ai /etc/mios/ai
sudo cp "$PROMPT_SRC" /usr/share/mios/ai/system.md
sudo cp "$PROMPT_SRC" /etc/mios/ai/system-prompt.md
echo "Installed system prompt to /usr/share/mios/ai/system.md"

# -- Install mios-agent-claude (wraps the 'claude' CLI if present) --
sudo tee /usr/local/bin/mios-agent-claude > /dev/null <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
PROMPT_FILE=""
for p in /usr/share/mios/ai/system.md /etc/mios/ai/system-prompt.md /system-prompt.md "${PWD}/system-prompt.md" "${PWD}/CLAUDE.md"; do
    [[ -r "$p" ]] && PROMPT_FILE="$p" && break
done
[[ -z "$PROMPT_FILE" ]] && { echo "mios-agent-claude: no system prompt found" >&2; exit 1; }
echo "[agent] launching with system prompt: $PROMPT_FILE" >&2
exec claude --append-system-prompt "$(cat "$PROMPT_FILE")" "$@"
SCRIPT
sudo chmod 755 /usr/local/bin/mios-agent-claude
echo "Installed /usr/local/bin/mios-agent-claude"

# -- Install mios-agent-gemini (wraps the 'gemini' CLI if present) --
sudo tee /usr/local/bin/mios-agent-gemini > /dev/null <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
PROMPT_FILE=""
for p in /usr/share/mios/ai/system.md /etc/mios/ai/system-prompt.md /system-prompt.md "${PWD}/system-prompt.md" "${PWD}/GEMINI.md"; do
    [[ -r "$p" ]] && PROMPT_FILE="$p" && break
done
[[ -z "$PROMPT_FILE" ]] && { echo "mios-agent-gemini: no system prompt found" >&2; exit 1; }
echo "[agent] launching with system prompt: $PROMPT_FILE" >&2
exec gemini --system-prompt "$(cat "$PROMPT_FILE")" "$@"
SCRIPT
sudo chmod 755 /usr/local/bin/mios-agent-gemini
echo "Installed /usr/local/bin/mios-agent-gemini"

# ── Install mios-llm ──
sudo tee /usr/local/bin/mios-llm > /dev/null <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail
PROMPT_FILE=""
for p in /usr/share/mios/ai/system.md /etc/mios/ai/system-prompt.md /system-prompt.md "${PWD}/system-prompt.md"; do
    [[ -r "$p" ]] && PROMPT_FILE="$p" && break
done
[[ -z "$PROMPT_FILE" ]] && { echo "mios-llm: no system prompt found" >&2; exit 1; }
ENDPOINT="${MIOS_AI_ENDPOINT:-http://localhost:8080/v1}"
MODEL="${MIOS_AI_MODEL:-mi-os-7b}"
USER_PROMPT="${*:-What are the six 'MiOS' Architectural Laws, in order?}"
echo "[agent] $MODEL @ $ENDPOINT (OpenAI /v1/chat/completions) prompt: $PROMPT_FILE" >&2
curl -sS "$ENDPOINT/chat/completions" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg model "$MODEL" --arg sys "$(cat "$PROMPT_FILE")" --arg user "$USER_PROMPT" \
        '{model:$model, messages:[{role:"system",content:$sys},{role:"user",content:$user}], temperature:0.3, stream:false}')" \
    | jq -r '.choices[0].message.content'
SCRIPT
sudo chmod 755 /usr/local/bin/mios-llm
echo "Installed /usr/local/bin/mios-llm"

# ── Verify ──
echo ""
echo "=== Verification ==="
echo "Prompt file:"
ls -la /usr/share/mios/ai/system.md
echo ""
echo "First line:"
head -1 /usr/share/mios/ai/system.md
echo ""
echo "Launcher path check (should show clean paths, no brackets):"
grep "for p in" /usr/local/bin/mios-agent-claude
echo ""
echo "Done. Run:"
echo "  mios-agent-claude     # if the 'claude' CLI binary is installed"
echo "  mios-agent-gemini     # if the 'gemini' CLI binary is installed"
echo "  mios-llm 'your question here'   # vendor-neutral, OpenAI /v1 only"
