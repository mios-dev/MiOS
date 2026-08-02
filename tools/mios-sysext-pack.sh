#!/usr/bin/bash
# AI-hint: Consolidates multiple .sysext directories into a single mios-accelerator.raw SquashFS image to bypass kernel overlayfs stacking depth limits during bootc system initialization.
# AI-related: mios-accelerator, mios-sysext-pack

set -euo pipefail

SOURCE_DIRS=("$@")
OUTPUT_IMG="/usr/lib/extensions/mios-accelerator.raw"

echo "[mios-sysext-pack] Starting monolithic system extension compilation"

if [ ${#SOURCE_DIRS[@]} -eq 0 ]; then
    echo "Usage: $0 <dir1> <dir2> "
    exit 1
fi

TMP_STAGE=$(mktemp -d)

for dir in "${SOURCE_DIRS[@]}"; do
    echo "  -> Merging: $dir"
    rsync -a "$dir/" "$TMP_STAGE/"
done

if [ -z "$(ls -A "$TMP_STAGE")" ]; then
    echo "[mios-sysext-pack] No files found in source directories. Skipping image creation"
    rm -rf "$TMP_STAGE"
    exit 0
fi

echo "  -> Compiling SquashFS image: $OUTPUT_IMG"
mksquashfs "$TMP_STAGE" "$OUTPUT_IMG" -comp zstd -Xcompression-level 19 -b 1048576 -noappend -no-progress

rm -rf "$TMP_STAGE"

echo "[mios-sysext-pack] Compilation complete. Extension ready for systemd-sysext merge"
