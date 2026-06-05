#!/bin/bash
# Probe mios-launch's resolution decisions WITHOUT actually launching.
# Set MIOS_LAUNCHER_SOCK to /dev/null so broker_dispatch fails fast +
# we see the resolution chain output before exec.
set -euo pipefail
export MIOS_LAUNCHER_SOCK=/dev/null

echo "== alias_resolve output (step 0 only) =="
for q in "browser" "my web browser" "web" "files" "chromedev" "terminal"; do
    # Run mios-launch with MIOS_TRACE=1 if it honors it; else parse stderr
    out=$(timeout 3 /usr/libexec/mios/mios-launch "$q" 2>&1 | head -3)
    echo "--- query: '$q' ---"
    echo "$out"
    echo
done
