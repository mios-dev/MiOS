#!/usr/bin/env bash
set -e

if command -v miosd >/dev/null 2>&1; then
    exec miosd greenboot
else
    echo "miosd not found, skipping native health checks"
    exit 0
fi
