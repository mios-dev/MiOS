#!/bin/bash
# AI-hint: Install MiOS-default AI assistant CLIs (Claude Code + Gemini CLI) as
# AI-related: /usr/libexec/mios/install-ai-clis.sh, /etc/mios/mios.toml, /usr/share/mios/mios.toml
# AI-functions: _resolve_npm_globals
set -euo pipefail

if [ "${MIOS_SKIP_AI_CLIS:-0}" = "1" ]; then
    echo "  [skip] MIOS_SKIP_AI_CLIS=1; not installing AI CLIs"
    exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "  [warn] npm not installed; cannot install AI CLIs. Add 'nodejs' + 'npm' to [packages.ai].pkgs"
    exit 0
fi

_resolve_npm_globals() {
    local toml extracted
    for toml in \
        "${HOME:-/var/home/mios}/.config/mios/mios.toml" \
        /etc/mios/mios.toml \
        /usr/share/mios/mios.toml; do
        [ -r "$toml" ] || continue
        extracted=$(awk '
            /^\[/ {
                line=$0; sub(/[[:space:]]*#.*$/, "", line)
                in_ai = (line == "[packages.ai]") ? 1 : 0
                next
            }
            in_ai && /^[[:space:]]*npm_globals[[:space:]]*=[[:space:]]*\[/ {
                capturing = 1
                if (match($0, /\[.*\]/)) {
                    body = substr($0, RSTART+1, RLENGTH-2)
                    print body
                    capturing = 0
                    next
                }
                next
            }
            capturing { buf = buf $0 "\n" }
            capturing && /^[[:space:]]*\][[:space:]]*$/ { print buf; capturing = 0; in_ai = 0; exit }
        ' "$toml" | grep -oE '"[^"]+"' | tr -d '"')
        if [ -n "$extracted" ]; then
            echo "$extracted"
            return 0
        fi
    done
    echo "@anthropic-ai/claude-code"
    echo "@google/gemini-cli"
}

mkdir -p /usr/local/lib/node_modules

npm config set prefix /usr/local 2>/dev/null || true

echo "  npm version: $"
echo "  node version: $"
echo "  installing AI CLIs "
_failed=0
_resolve_npm_globals | while read -r pkg; do
    [ -z "$pkg" ] && continue
    echo "    -> $pkg"
    if npm install -g "$pkg" 2>&1 | tail -8; then
        echo "      [ok] $pkg installed"
    else
        echo "      [warn] failed: $pkg"
        _failed=$((_failed + 1))
    fi
done

echo
echo "  installed binaries in /usr/local/bin:"
ls -la /usr/local/bin/claude /usr/local/bin/gemini 2>/dev/null || echo ""
echo "  PATH: $PATH"
echo
echo "  done.  Try: claude"
