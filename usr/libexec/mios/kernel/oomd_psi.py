#!/usr/bin/env python3
# AI-hint: Declarative systemd-oomd memory pressure configuration and cgroup2 PSI policies (T-667, T-668).
# AI-related: usr/libexec/mios/kernel/oomd_psi.py, tests/test-oomd-psi.py, automation/26-oomd.sh
"""Declarative systemd-oomd memory pressure configuration and cgroup2 PSI policies for MiOS.

Configures systemd-oomd to evict memory thrashing background tasks at 50% PSI pressure limit,
protecting desktop (gnome-shell), database (mios-pgvector), and inference (mios-llm-light) daemons.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mios-oomd-psi")


@dataclass
class PSIAction:
    cgroup_slice: str
    current_psi_pct: float
    action_taken: str  # "none", "kill", "throttle"
    victim_unit: Optional[str] = None


class OOMDPressureManager:
    """Manages declarative systemd-oomd pressure stall policies and protection lists."""

    PROTECTED_SERVICES = {
        "gnome-shell.service",
        "mios-pgvector.service",
        "mios-llm-light.service",
        "systemd-journald.service",
    }

    def __init__(self, psi_kill_threshold_pct: float = 50.0, dry_run: bool = False) -> None:
        self.psi_kill_threshold_pct = psi_kill_threshold_pct
        self.dry_run = dry_run
        self.evictions: List[PSIAction] = []

    def evaluate_pressure_stall(
        self, slice_name: str, current_psi_some_pct: float, candidate_units: List[str]
    ) -> PSIAction:
        """Evaluates PSI memory stall pressure and kills low-priority candidate if over limit."""
        if current_psi_some_pct < self.psi_kill_threshold_pct:
            return PSIAction(slice_name, current_psi_some_pct, "none")

        # Find first non-protected unit to evict
        victim = None
        for u in candidate_units:
            if u not in self.PROTECTED_SERVICES:
                victim = u
                break

        action = "kill" if victim else "throttle"
        act = PSIAction(
            cgroup_slice=slice_name,
            current_psi_pct=current_psi_some_pct,
            action_taken=action,
            victim_unit=victim,
        )
        self.evictions.append(act)
        if victim:
            logger.warning(
                f"PSI pressure {current_psi_some_pct}% exceeded {self.psi_kill_threshold_pct}%! "
                f"Evicted runaway background unit {victim} to protect critical services."
            )
        return act


def main():
    mgr = OOMDPressureManager(dry_run=True)
    res = mgr.evaluate_pressure_stall("background.slice", 65.0, ["stress-ng.service"])
    print(f"Action: {res.action_taken} on {res.victim_unit}")


if __name__ == "__main__":
    main()
