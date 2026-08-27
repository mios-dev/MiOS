#!/usr/bin/env python3
# AI-hint: Automated unit test suite for GPU Compute Stream Priority Scheduler (T-631, T-632).
# AI-related: usr/libexec/mios/ai/gpu_sched.py, tests/test-gpu-sched.py
"""Automated unit test suite for MiOS GPU Compute Stream Priority Scheduler."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "ai"))

from gpu_sched import (
    HIGH_PRIO_LATENCY_TARGET_MS,
    GPUComputeStreamScheduler,
    StreamPriority,
)


class TestGPUSched(unittest.TestCase):
    def setUp(self):
        self.sched = GPUComputeStreamScheduler(gpu_id=0, dry_run=True)

    def test_job_submission_and_priority_mapping(self):
        """Test compute job creation and priority classification."""
        j_voice = self.sched.submit_job("whisper_stt", StreamPriority.HIGH)
        j_chat = self.sched.submit_job("daily_chat", StreamPriority.NORMAL)
        j_train = self.sched.submit_job("qlora_llama3", StreamPriority.LOW)

        self.assertEqual(j_voice.priority, StreamPriority.HIGH)
        self.assertEqual(j_chat.priority, StreamPriority.NORMAL)
        self.assertEqual(j_train.priority, StreamPriority.LOW)
        self.assertFalse(j_train.is_paused)

    def test_high_priority_preemption_and_sub_50ms_latency(self):
        """Test high-priority turn preempts background tasks and achieves <50ms TTFT."""
        bg_job = self.sched.submit_job("synthetic_qa_gen", StreamPriority.LOW, total_steps=50)
        self.sched.step_background_job(bg_job.job_id, step_count=15)
        self.assertEqual(bg_job.completed_steps, 15)

        # Trigger high-priority voice interaction
        job, ttft_ms = self.sched.execute_high_prio_turn("kokoro_tts_stream", steps=10)
        self.assertTrue(job.is_completed)
        self.assertLess(ttft_ms, HIGH_PRIO_LATENCY_TARGET_MS)

        # Background job must have been paused and then resumed
        self.assertFalse(bg_job.is_paused)
        self.assertEqual(bg_job.completed_steps, 15)

    def test_background_job_resumption_and_completion(self):
        """Test background job advances to 100% completion across multiple preemption events."""
        bg_job = self.sched.submit_job("qlora_batch", StreamPriority.LOW, total_steps=100)

        # Step 1: Run 30 steps
        self.sched.step_background_job(bg_job.job_id, step_count=30)
        self.assertEqual(bg_job.completed_steps, 30)

        # Interrupt 1
        self.sched.execute_high_prio_turn("voice_turn_1")

        # Step 2: Run 40 steps
        self.sched.step_background_job(bg_job.job_id, step_count=40)
        self.assertEqual(bg_job.completed_steps, 70)

        # Interrupt 2
        self.sched.execute_high_prio_turn("voice_turn_2")

        # Step 3: Run remaining 30 steps -> Complete
        self.sched.step_background_job(bg_job.job_id, step_count=30)
        self.assertEqual(bg_job.completed_steps, 100)
        self.assertTrue(bg_job.is_completed)

    def test_scheduler_status_metrics(self):
        """Test scheduler status reporting and preemption event metrics."""
        self.sched.submit_job("bg_task", StreamPriority.LOW, total_steps=20)
        self.sched.execute_high_prio_turn("fast_inference")

        status = self.sched.get_status()
        self.assertEqual(status["gpu_id"], 0)
        self.assertEqual(status["preemption_event_count"], 1)
        self.assertTrue(status["sub_50ms_target_met"])


if __name__ == "__main__":
    unittest.main()
