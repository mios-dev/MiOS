#!/usr/bin/bash
# AI-hint: Validates that the system's default systemd target is a recognized MiOS, graphical, or multi-user target to ensure the boot environment meets operational requirements.
# AI-related: graphical.target, multi-user.target
set -euo pipefail
tgt=$(systemctl get-default)
case "$tgt" in
    mios-*.target|graphical.target|multi-user.target) exit 0 ;;
    *) echo "unexpected default target: $tgt"; exit 1 ;;
esac