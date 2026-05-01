#!/usr/bin/env bash
# MiOS flight-control — shows active build variable mappings
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "${REPO_ROOT}/VERSION" 2>/dev/null || echo 'v0.2.0')"

echo "MiOS ${VERSION} — Flight Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  %-24s %s\n" "BASE_IMAGE:"   "${MIOS_BASE_IMAGE:-ghcr.io/ublue-os/ucore-hci:stable-nvidia}"
printf "  %-24s %s\n" "LOCAL_TAG:"    "${MIOS_LOCAL_TAG:-localhost/mios:latest}"
printf "  %-24s %s\n" "MIOS_USER:"    "${MIOS_USER:-mios}"
printf "  %-24s %s\n" "MIOS_HOSTNAME:" "${MIOS_HOSTNAME:-mios}"
printf "  %-24s %s\n" "MIOS_FLATPAKS:" "${MIOS_FLATPAKS:-(none)}"
printf "  %-24s %s\n" "BIB_IMAGE:"    "${MIOS_BIB_IMAGE:-quay.io/centos-bootc/bootc-image-builder:latest}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
