#!/usr/bin/env python3
# AI-hint: Predictive S.M.A.R.T. drive health monitor and automated CephFS evacuation manager (T-639, T-640).
# AI-related: usr/libexec/mios/storage/disk_health.py, usr/libexec/mios/storage/smart_health.py, tests/test-smart-cephfs-evacuation.py
"""Predictive S.M.A.R.T. drive health monitor proxy module for MiOS."""

from __future__ import annotations

import sys
import os

from disk_health import (
    DEFAULT_WEAR_PERCENT_THRESHOLD,
    DEFAULT_SPARE_PERCENT_THRESHOLD,
    DEFAULT_TEMP_THRESHOLD_C,
    DriveHealth,
    SmartHealthMonitor,
    main,
)

__all__ = [
    "DEFAULT_WEAR_PERCENT_THRESHOLD",
    "DEFAULT_SPARE_PERCENT_THRESHOLD",
    "DEFAULT_TEMP_THRESHOLD_C",
    "DriveHealth",
    "SmartHealthMonitor",
    "main",
]

if __name__ == "__main__":
    main()
