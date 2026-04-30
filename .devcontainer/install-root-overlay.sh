#!/usr/bin/zsh
set -e

echo "Applying MiOS FHS Symlink Overlay..."

# 1. Symlink .git to root
if [ -d /mios/.git ]; then
    echo "  Symlinking /.git -> /mios/.git"
    ln -sf /mios/.git /.git
fi

# 2. Soft-merge FHS directories
for dir in etc usr var srv home; do
    if [ -d "/mios/$dir" ]; then
        echo "  Merging /mios/$dir -> /$dir"
        # Using -as for symbolic links of the structure
        # Use rsync to create the directory structure and symlink files
        # Alternatively, a simple loop:
        find "/mios/$dir" -maxdepth 1 -mindepth 1 | while read item; do
            target="/$dir/$(basename "$item")"
            ln -sf "$item" "$target" 2>/dev/null || true
        done
    fi
done

echo "✓ MiOS Root Overlay Active"
