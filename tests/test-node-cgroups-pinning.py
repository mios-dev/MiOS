#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-390 dynamic CPU core pinning and cgroup v2 controller.
# AI-related: usr/libexec/mios/node/cgroups.py, src/mios-rs/mios-node/src/cgroups.rs
"""Automated tests for WS-NODE worker CPU core affinity, Core 0 exclusion, and cgroup v2 limits."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_CGROUPS_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "cgroups.py")

spec = importlib.util.spec_from_file_location("cgroups", _CGROUPS_PATH)
if spec and spec.loader:
    cgroups = importlib.util.module_from_spec(spec)
    sys.modules["cgroups"] = cgroups
    sys.modules["usr.libexec.mios.node.cgroups"] = cgroups
    spec.loader.exec_module(cgroups)
else:
    raise ImportError(f"Could not load cgroups module from {_CGROUPS_PATH}")


class TestNodeCgroupsPinning(unittest.TestCase):
    """Validates CPU core affinity allocation, Core 0 system reservation, and cgroup v2 formatting."""

    def test_core_zero_exclusion_invariant(self):
        # 4-core machine: safe worker pool must exclude Core 0
        safe_4 = cgroups.filter_safe_worker_cores(4, None, exclude_core_zero=True)
        self.assertEqual(safe_4, [1, 2, 3])
        self.assertNotIn(0, safe_4)

        # 1-core machine: single core must remain usable
        safe_1 = cgroups.filter_safe_worker_cores(1, None, exclude_core_zero=True)
        self.assertEqual(safe_1, [0])

        # Explicit requested cores [0, 2, 3] on 4 cores -> 0 filtered out
        safe_req = cgroups.filter_safe_worker_cores(4, [0, 2, 3], exclude_core_zero=True)
        self.assertEqual(safe_req, [2, 3])

    def test_affinity_policy_allocations(self):
        controller = cgroups.WorkerAffinityController(
            total_system_cores=4, limits=cgroups.NodeResourceLimits()
        )
        self.assertEqual(controller.available_worker_cores, [1, 2, 3])

        # Allocate exclusive core
        c1 = controller.allocate_cores_for_policy(cgroups.AffinityPolicy.EXCLUSIVE, 1)
        self.assertEqual(c1, [1])

        c2 = controller.allocate_cores_for_policy(cgroups.AffinityPolicy.EXCLUSIVE, 2)
        self.assertEqual(c2, [2, 3])

        # Pool exhausted
        with self.assertRaises(RuntimeError):
            controller.allocate_cores_for_policy(cgroups.AffinityPolicy.EXCLUSIVE, 1)

        # Release core 1 and re-allocate
        controller.release_cores([1])
        c_realloc = controller.allocate_cores_for_policy(cgroups.AffinityPolicy.EXCLUSIVE, 1)
        self.assertEqual(c_realloc, [1])

        # Shared policy returns all available worker cores
        shared = controller.allocate_cores_for_policy(cgroups.AffinityPolicy.SHARED)
        self.assertEqual(shared, [1, 2, 3])

        # Low priority returns highest index core
        low = controller.allocate_cores_for_policy(cgroups.AffinityPolicy.LOW_PRIORITY)
        self.assertEqual(low, [3])

    def test_cgroup_v2_cpu_max_formatting(self):
        f80 = cgroups.CgroupV2Controller.format_cpu_max(80, 100_000)
        self.assertEqual(f80, "80000 100000")

        fmax = cgroups.CgroupV2Controller.format_cpu_max(None, 100_000)
        self.assertEqual(fmax, "max 100000")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeCgroupsPinning)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
