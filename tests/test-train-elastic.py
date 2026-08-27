#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Elastic Training Checkpoint & Preemption Resumption (T-669, T-670).
# AI-related: usr/lib/mios/ai/train_elastic.py, tests/test-train-elastic.py
"""Automated unit test suite for MiOS Elastic Training Manager."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "lib", "mios", "ai"))

from train_elastic import ElasticTrainingManager

class TestTrainElastic(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mios-train-test-")
        self.mgr = ElasticTrainingManager(checkpoint_dir=self.tmp_dir, dry_run=True)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_async_checkpoint_saving(self):
        """Test saving step checkpoint records loss and weight metadata."""
        ckpt = self.mgr.save_checkpoint_async(step=250, epoch=2, loss=0.315, weights_mock="layer_weights_250")
        self.assertEqual(ckpt.step, 250)
        self.assertEqual(len(self.mgr.saved_checkpoints), 1)

    def test_preemption_signal_flush_under_2_seconds(self):
        """Test preemption signal saves active step in <2s."""
        ok, duration = self.mgr.handle_preemption_signal(current_step=300, loss=0.298)
        self.assertTrue(ok)
        self.assertLess(duration, 2.0)

    def test_zero_loss_resumption_from_preemption(self):
        """Test restarting training resumes cleanly from exact preempted step."""
        self.mgr.handle_preemption_signal(current_step=450, loss=0.195)
        resumed = self.mgr.resume_from_latest_checkpoint()
        self.assertIsNotNone(resumed)
        self.assertEqual(resumed.step, 450)
        self.assertAlmostEqual(resumed.loss, 0.195)

if __name__ == "__main__":
    unittest.main()
