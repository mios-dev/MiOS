#!/usr/bin/zsh
set -e

echo "Applying MiOS FHS Symlink Overlay..."

# Define the source (the repo mount)
REPO_ROOT="/mios"

# 1. Symlink .git to root
if [ -d "${REPO_ROOT}/.git" ]; then
    echo "  Symlinking /.git -> ${REPO_ROOT}/.git"
    ln -sf "${REPO_ROOT}/.git" /.git
fi

# 2. Soft-merge FHS directories from the repository into the container root
# This makes the repository "act" as the system root.
for dir in etc usr var srv home; do
    if [ -d "${REPO_ROOT}/$dir" ]; then
        echo "  Merging ${REPO_ROOT}/$dir -> /$dir"
        mkdir -p "/$dir"
        # Use find to get all top-level items and symlink them
        find "${REPO_ROOT}/$dir" -maxdepth 1 -mindepth 1 | while read item; do
            target="/$dir/$(basename "$item")"
            # We use ln -sf. This will replace existing symlinks but skip 
            # real files/directories that already exist in the base image 
            # to prevent system breakage (like /etc/passwd).
            if [ -e "$target" ] && [ ! -L "$target" ]; then
                echo "    Skipping existing real path: $target"
            else
                ln -sf "$item" "$target" 2>/dev/null || true
            fi
        done
    fi
done

echo "✓ MiOS Root Overlay Active"
