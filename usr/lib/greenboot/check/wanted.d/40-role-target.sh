#!/usr/bin/bash
set -euo pipefail
tgt=$(systemctl get-default)
case "$tgt" in
    mios-*.target|graphical.target|multi-user.target) exit 0 ;;
    *) echo "unexpected default target: $tgt"; exit 1 ;;
esac