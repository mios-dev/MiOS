#!/usr/bin/env bash
set -euo pipefail

echo "==> Preparing Unified Kernel Image (UKI) configuration..."

# shellcheck source=lib/packages.sh
source "$(dirname "$0")/lib/packages.sh"
source "$(dirname "$0")/lib/common.sh"

# packages-boot already pulls systemd-ukify; reinstall via the SSOT block as a
# safety net in case --skip-unavailable dropped it on a constrained mirror.
if ! rpm -q systemd-ukify >/dev/null 2>&1; then
    echo "==> systemd-ukify not found via boot-section install; reinstalling via PACKAGES.md..."
    install_packages_strict "uki"
fi

# In a bootc Containerfile build, we use `bootc container render-kargs`
# to flatten all kargs.d/*.toml drop-ins into a single string for the UKI.
KERNEL_CMDLINE_DST="/usr/lib/kernel/cmdline"
install -d -m 0755 /usr/lib/kernel

if command -v bootc >/dev/null && bootc container --help | grep -q 'render-kargs'; then
    echo "==> Rendering bootc kargs for UKI natively..."
    bootc container render-kargs > "${KERNEL_CMDLINE_DST}"
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
' > "${KERNEL_CMDLINE_DST}"
fi

CMDLINE=$(cat "${KERNEL_CMDLINE_DST}" | xargs)
if [ -z "$CMDLINE" ]; then
    echo "WARN: /usr/lib/kernel/cmdline is empty — no kargs rendered. UKI generation will use defaults."
fi

echo "Rendered UKI cmdline: $CMDLINE"
# The actual UKI generation (`ukify build`) occurs in the final CI/CD pipeline
echo "==> UKI cmdline preparation complete."
