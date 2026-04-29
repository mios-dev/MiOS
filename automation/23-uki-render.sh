#!/usr/bin/env bash
set -euo pipefail

echo "==> Preparing Unified Kernel Image (UKI) configuration..."

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

# systemd-ukify and binutils are required for this step.
# Ensure they are declared in specs/engineering/2026-04-26-Artifact-ENG-001-Packages.md per the single-source-of-truth rules.
# The packages-boot section installs ukify via install_packages (--skip-unavailable),
# so install explicitly here as a safety net to guarantee it ends up in the image.
if ! rpm -q systemd-ukify >/dev/null 2>&1; then
    echo "==> systemd-ukify not found via boot-section install; installing explicitly..."
    $DNF_BIN "${DNF_SETOPT[@]}" install -y "${DNF_OPTS[@]}" systemd-ukify
fi

# In a bootc Containerfile build, we use `bootc container render-kargs`
# to flatten all kargs.d/*.toml drop-ins into a single string for the UKI.
if command -v bootc >/dev/null && bootc container --help | grep -q 'render-kargs'; then
    echo "==> Rendering bootc kargs for UKI natively..."
    bootc container render-kargs > /etc/kernel/cmdline
else
    echo "==> bootc render-kargs not available, rendering flat TOML via Python fallback..."
    python3 -c '
import tomllib, sys, glob
kargs = []
for f in sorted(glob.glob("/usr/lib/bootc/kargs.d/*.toml")):
    with open(f, "rb") as fp:
        d = tomllib.load(fp)
        if "kargs" in d:
            kargs.extend(d["kargs"])
print(" ".join(kargs))
' > /etc/kernel/cmdline
fi

CMDLINE=$(cat /etc/kernel/cmdline | xargs)
if [ -z "$CMDLINE" ]; then
    echo "FATAL: /etc/kernel/cmdline is empty! UKI generation will fail."
    exit 1
fi

echo "Rendered UKI cmdline: $CMDLINE"
# The actual UKI generation (`ukify build`) occurs in the final CI/CD pipeline
echo "==> UKI cmdline preparation complete."
