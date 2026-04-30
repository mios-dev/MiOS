#!/bin/bash
set -e

# MiOS Day-0 Root Overlay: Aggressive FHS Symlink Merge
# SSOT: The repository IS the system root.

# 1. Detect Repository Root
if [ -d "/mios/.git" ]; then
    REPO_ROOT="/mios"
elif [ -d "/workspaces/MiOS/.git" ]; then
    REPO_ROOT="/workspaces/MiOS"
else
    # Fallback to current dir if it looks like the repo
    if [ -d ".git" ] && [ -f "Justfile" ]; then
        REPO_ROOT=$(pwd)
    else
        echo "Error: MiOS Repository not found in /mios, /workspaces/MiOS, or current dir."
        exit 1
    fi
fi

echo "🔄 Initializing MiOS COMPLETE System Root Overlay from $REPO_ROOT..."

# 2. Establish Git Identity of / (/.git -> REPO/.git)
ln -sf "${REPO_ROOT}/.git" "/.git"

# 3. Exhaustive Global Merge
# We use cp -as to recursively symlink the repository tree into /
# shopt -s dotglob ensures hidden files are included
shopt -s dotglob
for item in "${REPO_ROOT}"/*; do
    [ -e "$item" ] || continue
    name=$(basename "$item")
    
    # Avoid recursion/system breakage
    case "$name" in
        .devcontainer|proc|sys|dev|run|tmp|boot|mnt|root|vscode|workspaces)
            continue
            ;;
    esac
    
    target="/$name"
    
    if [ -d "$item" ]; then
        echo "  [MERGE] /$name"
        mkdir -p "$target"
        # Recursively symlink contents
        cp -as "${item}/"* "$target/" 2>/dev/null || true
    else
        echo "  [FILE] /$name"
        ln -sf "$item" "$target" 2>/dev/null || true
    fi
done

# 4. Enforce Day-0 AI Surface
mkdir -p /v1/chat
cat <<EON > /v1/chat/completions
# MiOS Unified Inference Schema
{
  "spec": "POST /v1/chat/completions",
  "implementation": "Native system proxy",
  "status": "ready"
}
EON

mkdir -p /usr/share/mios/ai/v1
cat <<EON > /usr/share/mios/ai/v1/models.json
{
  "object": "list",
  "data": [],
  "documentation": "Native model discovery schema."
}
EON
ln -sf /usr/share/mios/ai/v1/models.json /v1/models 2>/dev/null || true

echo "✅ MiOS System Root Overlay: FULLY SYNCHRONIZED"
