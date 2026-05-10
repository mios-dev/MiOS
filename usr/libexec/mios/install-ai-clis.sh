#!/bin/bash
# /usr/libexec/mios/install-ai-clis.sh
#
# Install MiOS-default AI assistant CLIs (Claude Code + Gemini CLI) as
# global npm packages. Both are Node.js CLIs distributed via npm, so
# they don't fit RPM packaging. This script is invoked once by the
# build-mios.ps1 overlay phase and is also operator-re-runnable any
# time (idempotent: `npm install -g <pkg>` upgrades or installs as
# needed).
#
# Reads the npm_globals list from mios.toml [packages.ai] -- operator
# can extend by editing the list before `mios update`.
#
# Operator override: MIOS_SKIP_AI_CLIS=1 skips entirely.

set -e

if [ "${MIOS_SKIP_AI_CLIS:-0}" = "1" ]; then
    echo "  [skip] MIOS_SKIP_AI_CLIS=1; not installing AI CLIs."
    exit 0
fi

if ! command -v npm >/dev/null 2>&1; then
    echo "  [warn] npm not installed; cannot install AI CLIs. Add 'nodejs' + 'npm' to [packages.ai].pkgs."
    exit 0
fi

# Pull npm_globals from layered mios.toml (~/.config > /etc/mios > /usr/share/mios).
# Vendor fallback if the toml lookup fails: the two operator-canonical
# AI CLIs.
_resolve_npm_globals() {
    local toml
    for toml in \
        "${HOME:-/var/home/mios}/.config/mios/mios.toml" \
        /etc/mios/mios.toml \
        /usr/share/mios/mios.toml; do
        [ -r "$toml" ] || continue
        # Extract npm_globals = [ "...", "..." ] from [packages.ai] section.
        awk '
            /^\[/ {
                line=$0; sub(/[[:space:]]*#.*$/, "", line)
                in_ai = (line == "[packages.ai]") ? 1 : 0
                next
            }
            in_ai && /^[[:space:]]*npm_globals[[:space:]]*=[[:space:]]*\[/ {
                capturing = 1
                # On the same line?
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
        ' "$toml" | grep -oE '"[^"]+"' | tr -d '"' && return 0
    done
    # Vendor fallback
    echo "@anthropic-ai/claude-code"
    echo "@google/gemini-cli"
}

# Ensure npm prefix is a system path that's on $PATH for all users.
# Default `npm -g` prefix on Fedora is /usr/local; we use /usr/local
# so installed bins land at /usr/local/bin/ (which IS on PATH).
mkdir -p /usr/local/lib/node_modules

echo "  installing AI CLIs (npm -g) ..."
_failed=0
_resolve_npm_globals | while read -r pkg; do
    [ -z "$pkg" ] && continue
    echo "    -> $pkg"
    if ! npm install -g --silent "$pkg" 2>&1 | tail -3; then
        echo "      [warn] failed: $pkg"
        _failed=$((_failed + 1))
    fi
done

echo "  done.  Try: claude --version  /  gemini --version"
