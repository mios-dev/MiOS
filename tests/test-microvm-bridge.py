#!/usr/bin/env python3
# AI-hint: MicroVM sub-50ms boot latency and VSOCK IPC throughput benchmark suite.
# AI-related: usr/libexec/mios/virt/microvm_bridge.py, usr/share/mios/mios.toml
"""Unit and benchmark test suite for Ephemeral Cloud-Hypervisor microVM orchestrator and Virtio-VSOCK bridge (T-570)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "virt", "microvm_bridge.py")

spec = importlib.util.spec_from_file_location("microvm_bridge", _TARGET_PATH)
if spec and spec.loader:
    microvm_bridge = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = microvm_bridge
    spec.loader.exec_module(microvm_bridge)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")

class TestMicroVMBridge(unittest.TestCase):
    """Test suite for microVM direct-boot configuration, ephemeral lifecycle, VSOCK IPC, and boot latency SLA."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="mios-vm-test-")
        self.orchestrator = microvm_bridge.CloudHypervisorOrchestrator(
            mock=True,
            runtime_dir=self.tmpdir.name,
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_config_generation_and_cmd_builder(self) -> None:
        cfg = microvm_bridge.MicroVMConfig(
            vm_id="vm-test-01",
            vcpus=4,
            memory_mb=1024,
            kernel_path="/boot/vmlinuz-custom",
            initramfs_path="/boot/initramfs-custom.img",
            cmdline="console=ttyS0 quiet panic=1",
            vsock_cid=5,
            vsock_port=5200,
            vsock_socket_path="/run/mios/vm.vsock",
            virtiofs_socket="/run/mios/virtiofs.sock",
            dax=True,
        )

        cmd = self.orchestrator.build_launch_cmd(cfg)
        self.assertIn("cloud-hypervisor", cmd)
        self.assertIn("--cpus", cmd)
        self.assertIn("boot=4", cmd)
        self.assertIn("--memory", cmd)
        self.assertIn("size=1024M,shared=on", cmd)
        self.assertIn("--kernel", cmd)
        self.assertIn("/boot/vmlinuz-custom", cmd)
        self.assertIn("--vsock", cmd)
        self.assertIn("cid=5,socket=/run/mios/vm.vsock", cmd)
        self.assertIn("--fs", cmd)
        self.assertIn("tag=workspace,socket=/run/mios/virtiofs.sock,num_queues=1,queue_size=1024", cmd)

    def test_spawn_and_sub_50ms_boot_latency(self) -> None:
        cfg = microvm_bridge.MicroVMConfig(vm_id="vm-perf-01", memory_mb=512)
        ok, boot_ms, msg = self.orchestrator.spawn_microvm(cfg)
        self.assertTrue(ok)
        # SLA: Ephemeral microVM must boot in <50ms
        self.assertLess(boot_ms, 50.0)
        self.assertIn("vm-perf-01", self.orchestrator.active_vms)

        # Cleanup
        self.orchestrator.cleanup_microvm("vm-perf-01")
        self.assertNotIn("vm-perf-01", self.orchestrator.active_vms)

    def test_exec_tool_lifecycle(self) -> None:
        res = self.orchestrator.exec_tool(
            command="python3 -c 'print(\"hello microvm\")'",
            memory_mb=512,
            vcpus=2,
        )
        self.assertEqual(res.exit_code, 0)
        self.assertIn("hello microvm", res.stdout)
        self.assertLess(res.boot_latency_ms, 50.0)
        self.assertTrue(res.cleaned_up)
        # Verify active VMs are cleaned up
        self.assertEqual(len(self.orchestrator.active_vms), 0)

    def test_benchmark_performance_sla(self) -> None:
        bench = self.orchestrator.benchmark_performance(iterations=5)
        self.assertEqual(bench["status"], "PASS")
        self.assertTrue(bench["boot_sla_passed"])
        self.assertTrue(bench["throughput_sla_passed"])
        self.assertLess(bench["avg_boot_latency_ms"], 50.0)
        self.assertGreaterEqual(bench["vsock_throughput_gbps"], 1.0)

    def test_vsock_bridge_mock_rpc(self) -> None:
        bridge = microvm_bridge.VSOCKBridge(mock=True)
        resp = bridge.send_rpc(
            cid=3,
            port=5200,
            payload={"id": "test-req", "action": "exec", "command": "uname -r"},
        )
        self.assertEqual(resp["status"], "success")
        self.assertEqual(resp["exit_code"], 0)
        self.assertIn("uname -r", resp["stdout"])

    def test_cli_execution(self) -> None:
        # CLI --benchmark --json
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = microvm_bridge.main(["--benchmark", "--json", "--mock"])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertEqual(data["status"], "PASS")
            self.assertTrue(data["boot_sla_passed"])

        # CLI --exec --command "echo test" --json
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = microvm_bridge.main(["--exec", "--command", "echo test", "--json", "--mock"])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertEqual(data["exit_code"], 0)
            self.assertIn("echo test", data["stdout"])

        # CLI --spawn and --cleanup
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = microvm_bridge.main(["--spawn", "--vm-id", "vm-cli-01", "--json", "--mock"])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertTrue(data["success"])

        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            ret = microvm_bridge.main(["--cleanup", "--vm-id", "vm-cli-01", "--json", "--mock"])
            self.assertEqual(ret, 0)
            data = json.loads(stdout_buf.getvalue())
            self.assertTrue(data["success"])

if __name__ == "__main__":
    unittest.main()
