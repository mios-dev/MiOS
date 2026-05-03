#!/usr/bin/bash
# 10-mios-composefs.sh -- greenboot required check: composefs root verification.
# Non-zero exit causes greenboot retry/rollback.
set -euo pipefail
exec /usr/libexec/mios/verify-root.sh
