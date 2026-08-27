#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE work-stealing scheduler and priority offloading.
# AI-related: usr/libexec/mios/node/scheduler.py, src/mios-rs/mios-node/src/scheduler.rs
"""Automated tests for WS-NODE WorkStealingScheduler, priority tiers, and hardware pin invariants."""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_SCHED_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "scheduler.py")

spec = importlib.util.spec_from_file_location("scheduler", _SCHED_PATH)
if spec and spec.loader:
    scheduler = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = scheduler
    spec.loader.exec_module(scheduler)
else:
    raise ImportError(f"Could not load scheduler module from {_SCHED_PATH}")

class TestNodeScheduler(unittest.TestCase):
    """Validates work-stealing priority scheduling, pin invariants, and router offloading."""

    def test_priority_tier_ordering(self):
        self.assertLess(scheduler.TaskPriority.CRITICAL, scheduler.TaskPriority.HIGH)
        self.assertLess(scheduler.TaskPriority.HIGH, scheduler.TaskPriority.NORMAL)
        self.assertLess(scheduler.TaskPriority.NORMAL, scheduler.TaskPriority.LOW)

    def test_local_worker_priority_execution(self):
        sched = scheduler.WorkStealingScheduler(local_node_id=101, num_workers=2)

        t_low = scheduler.TaskItem(task_id=1, priority=scheduler.TaskPriority.LOW)
        t_crit = scheduler.TaskItem(task_id=2, priority=scheduler.TaskPriority.CRITICAL)
        t_norm = scheduler.TaskItem(task_id=3, priority=scheduler.TaskPriority.NORMAL)

        # Submit all to worker 0
        sched.submit_task(t_low, worker_hint=0)
        sched.submit_task(t_crit, worker_hint=0)
        sched.submit_task(t_norm, worker_hint=0)

        # Worker 0 pops in priority order: CRITICAL -> NORMAL -> LOW
        p1 = sched.pop_task(worker_id=0)
        self.assertIsNotNone(p1)
        self.assertEqual(p1.task_id, 2)
        self.assertEqual(p1.priority, scheduler.TaskPriority.CRITICAL)

        p2 = sched.pop_task(worker_id=0)
        self.assertIsNotNone(p2)
        self.assertEqual(p2.task_id, 3)
        self.assertEqual(p2.priority, scheduler.TaskPriority.NORMAL)

        p3 = sched.pop_task(worker_id=0)
        self.assertIsNotNone(p3)
        self.assertEqual(p3.task_id, 1)
        self.assertEqual(p3.priority, scheduler.TaskPriority.LOW)

        self.assertIsNone(sched.pop_task(worker_id=0))

    def test_worker_stealing_when_idle(self):
        sched = scheduler.WorkStealingScheduler(local_node_id=101, num_workers=2)

        t1 = scheduler.TaskItem(task_id=10, priority=scheduler.TaskPriority.NORMAL)
        t2 = scheduler.TaskItem(task_id=20, priority=scheduler.TaskPriority.LOW)

        # Submit tasks to worker 0 only
        sched.submit_task(t1, worker_hint=0)
        sched.submit_task(t2, worker_hint=0)

        # Worker 1 is idle; popping from worker 1 steals from worker 0
        stolen = sched.pop_task(worker_id=1)
        self.assertIsNotNone(stolen)
        self.assertIn(stolen.task_id, (10, 20))

        stats = sched.get_stats()
        self.assertEqual(stats.tasks_stolen_local, 1)

    def test_pinned_hardware_task_cannot_be_stolen(self):
        sched = scheduler.WorkStealingScheduler(local_node_id=101, num_workers=2)

        pinned_t = scheduler.TaskItem(
            task_id=99,
            priority=scheduler.TaskPriority.CRITICAL,
            pinned_hardware=True,
            pinned_node_id=101,
        )

        sched.submit_task(pinned_t, worker_hint=0)

        # Worker 1 cannot steal pinned task
        self.assertIsNone(sched.pop_task(worker_id=1))

        # Remote peer 202 cannot steal pinned task
        remote_stolen = sched.handle_remote_steal_request(requester_node_id=202, max_tasks=5)
        self.assertEqual(len(remote_stolen), 0)

        # Worker 0 can still execute it locally
        local_exec = sched.pop_task(worker_id=0)
        self.assertIsNotNone(local_exec)
        self.assertEqual(local_exec.task_id, 99)

    def test_router_hardware_pin_and_load_balance(self):
        sched = scheduler.WorkStealingScheduler(local_node_id=101, num_workers=2)

        pinned_t = scheduler.TaskItem(
            task_id=55,
            priority=scheduler.TaskPriority.HIGH,
            pinned_hardware=True,
        )
        peer_loads = [(201, 0), (202, 1)]

        # Pinned task must stay local even if peers have 0 load
        decision = sched.route_task(pinned_t, peer_loads)
        self.assertEqual(decision.target_type, scheduler.ScheduledTargetType.LOCAL)

        # Fill local queue to trigger unpinned offload
        for i in range(5):
            t = scheduler.TaskItem(task_id=100 + i, priority=scheduler.TaskPriority.NORMAL)
            sched.submit_task(t, worker_hint=0)

        unpinned_t = scheduler.TaskItem(task_id=77, priority=scheduler.TaskPriority.NORMAL)
        decision_unpinned = sched.route_task(unpinned_t, peer_loads)
        self.assertEqual(decision_unpinned.target_type, scheduler.ScheduledTargetType.OFFLOAD)
        self.assertEqual(decision_unpinned.node_id, 201)

    def test_concurrent_task_push_and_steal(self):
        sched = scheduler.WorkStealingScheduler(local_node_id=101, num_workers=4)
        total_tasks = 100

        # Push 100 tasks across global injector and workers
        for i in range(total_tasks):
            t = scheduler.TaskItem(task_id=i, priority=scheduler.TaskPriority(i % 4))
            sched.submit_task(t, worker_hint=(i % 4 if i % 2 == 0 else None))

        executed: list[int] = []
        lock = threading.Lock()

        def worker_loop(wid: int):
            while True:
                task = sched.pop_task(wid)
                if task is None:
                    break
                with lock:
                    executed.append(task.task_id)

        threads = [threading.Thread(target=worker_loop, args=(i,)) for i in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()

        self.assertEqual(len(executed), total_tasks)
        self.assertEqual(len(set(executed)), total_tasks)  # No duplicate execution

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeScheduler)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
