#!/usr/bin/bash
# AI-hint: Validates that the podman.socket is active during greenboot checks to ensure container engine availability for containerized services.
# AI-related: podman.socket
set -euo pipefail
systemctl is-active --quiet podman.socket