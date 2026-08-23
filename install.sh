#!/usr/bin/env bash
# MIOS_INSTALLER_ROLE=root-overlay-redirector
# AI-hint: Legacy redirector script that forwards execution to build-mios.sh to maintain backward compatibility for curl-based i...
# AI-doc: usr/share/doc/mios/manual/_harvest/install_sh.md
set -euo pipefail
target="$(dirname "${BASH_SOURCE[0]}")/build-mios.sh"
if [[ ! -x "$target" && ! -r "$target" ]]; then
    echo "[FAIL] build-mios.sh not found alongside this redirector" >&2
    echo "       Re-clone https://github.com/mios-dev/mios-bootstrap" >&2
    exit 1
fi
exec bash "$target" "$@"
