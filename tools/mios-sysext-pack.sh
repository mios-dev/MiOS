#!/usr/bin/bash
# mios-sysext-pack: Consolidates multiple granular .sysext directories into a single monolithic SquashFS image
# Mitigates the kernel 'overlayfs: maximum fs stacking depth exceeded' error on bootc systems.

set -euo pipefail

SOURCE_DIRS=("$@")
OUTPUT_IMG="/usr/lib/extensions/mios-accelerator.raw"

echo "[mios-sysext-pack] Starting monolithic system extension compilation..."

if [ ${#SOURCE_DIRS[@]} -eq 0 ]; then
    echo "Usage: $0 <dir1> <dir2> ..."
    exit 1
fi

TMP_STAGE=$(mktemp -d)

# Flatten all source directories into a single staging tree
for dir in "${SOURCE_DIRS[@]}"; do
    echo "  -> Merging: $dir"
    rsync -a "$dir/" "$TMP_STAGE/"
done

# Check if staging directory has any files (including hidden ones)
if [ -z "$(ls -A "$TMP_STAGE")" ]; then
    echo "[mios-sysext-pack] No files found in source directories. Skipping image creation."
    rm -rf "$TMP_STAGE"
    exit 0
fi

# Compile the final monolithic squashfs image
echo "  -> Compiling SquashFS image: $OUTPUT_IMG"
mksquashfs "$TMP_STAGE" "$OUTPUT_IMG" -comp zstd -Xcompression-level 19 -b 1048576 -noappend -no-progress

rm -rf "$TMP_STAGE"

echo "[mios-sysext-pack] Compilation complete. Extension ready for systemd-sysext merge."
