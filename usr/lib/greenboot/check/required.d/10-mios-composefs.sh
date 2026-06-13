#!/usr/bin/bash
# AI-hint: Verifies the integrity of the composefs root filesystem; if this script returns non-zero, greenboot triggers a system rollback or retry.
# AI-related: /usr/libexec/mios/verify-root.sh, mios-composefs
# 10-mios-composefs.sh -- greenboot required check: composefs root verification.
# Non-zero exit causes greenboot retry/rollback.
set -euo pipefail
exec /usr/libexec/mios/verify-root.sh
