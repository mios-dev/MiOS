#!/bin/bash
set -e

REPO_ROOT="/mios"
SYSTEM_ROOT="/"

echo "🔄 Initializing MiOS COMPLETE System Root Overlay..."

# 1. Mandatory Git Identity (The System Root IS the Git Repository)
echo "  [ROOT] Mapping /.git -> ${REPO_ROOT}/.git"
ln -sf "${REPO_ROOT}/.git" "${SYSTEM_ROOT}.git"

# 2. Aggressive Global Merge
# We include ALL files and directories from the repo root
shopt -s dotglob
for item in "${REPO_ROOT}"/*; do
    [ -e "$item" ] || continue
    name=$(basename "$item")
    
    # Avoid self-recursion and sensitive container mounts
    case "$name" in
        .devcontainer|vscode|workspaces|proc|sys|dev|run|tmp|boot|mnt|root)
            continue
            ;;
    esac
    
    target="${SYSTEM_ROOT}${name}"
    
    if [ -d "$item" ]; then
        # For FHS-standard directories, we merge the contents
        if [[ "$name" =~ ^(usr|etc|var|srv|home|v1|bin|lib|lib64|sbin)$ ]]; then
            echo "  [MERGE] /$name"
            mkdir -p "$target"
            cp -as "${item}/"* "$target/" 2>/dev/null || true
        else
            # For project-specific directories (automation, tools, etc.), link them directly
            echo "  [LINK] /$name"
            ln -sfn "$item" "$target"
        fi
    else
        # For all root-level files (Justfile, Containerfile, VERSION, etc.)
        echo "  [FILE] /$name"
        ln -sf "$item" "$target"
    fi
done

echo "✅ MiOS System Root Overlay: FULLY MERGED"
