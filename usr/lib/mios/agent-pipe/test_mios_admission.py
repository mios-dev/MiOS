# AI-hint: Unit tests for mios_pipe.scheduler.admission (AGY-345).
"""Unit tests for admission control and lane semaphore management."""

import unittest

from mios_pipe.scheduler.admission import (
    _SloShed,
    _endpoint_key,
    _lane_sem,
    configure,
)


class TestAdmission(unittest.TestCase):

    def setUp(self):
        configure(
            agent_concurrency=4,
            endpoint_concurrency=2,
        )

    def test_sloshed_exception_class(self):
        err = _SloShed("slo_test")
        self.assertIsInstance(err, Exception)

    def test_lane_sem_cache_identity(self):
        sem1 = _lane_sem("gpu_test")
        sem2 = _lane_sem("gpu_test")
        self.assertIs(sem1, sem2)

    def test_endpoint_key_parsing(self):
        self.assertEqual(_endpoint_key("http://localhost:11434/v1"), "localhost:11434")
        self.assertEqual(_endpoint_key("https://127.0.0.1:8000/api/chat"), "127.0.0.1:8000")


if __name__ == "__main__":
    unittest.main()
