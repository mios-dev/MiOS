#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-SEC / MCP-01 bubblewrap and namespace sandboxing (T-377 / AGY-1975).
# AI-related: usr/libexec/mios/mcp/sandbox.py, usr/lib/mios/agent-pipe/server.py
"""
Automated unit tests for Model Context Protocol (MCP) process isolation, mount sandboxing,
and capability dropping.
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_LIBEXEC_MCP = os.path.join(_ROOT, "usr", "libexec", "mios", "mcp")
if _LIBEXEC_MCP not in sys.path:
    sys.path.insert(0, _LIBEXEC_MCP)

try:
    import sandbox
except ImportError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location("sandbox", os.path.join(_LIBEXEC_MCP, "sandbox.py"))
    sandbox = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(sandbox)

class TestMcpSandbox(unittest.TestCase):
    """Validates bubblewrap command construction, filesystem isolation, and policy enforcement."""

    def test_bwrap_argument_generation(self):
        """Verify bubblewrap arguments, default flags, and read-only mounts."""
        sb = sandbox.McpSandbox(server_name="test-server", allow_net=False)
        cmd = sb.build_command(["python3", "server.py"])

        self.assertEqual(cmd[0], "bwrap")
        self.assertIn("--die-with-parent", cmd)
        self.assertIn("--new-session", cmd)
        self.assertIn("--unshare-all", cmd)
        self.assertIn("--unshare-net", cmd)
        self.assertNotIn("--share-net", cmd)

        # Core system read-only mounts
        self.assertIn("--ro-bind", cmd)
        self.assertIn("/usr", cmd)
        self.assertIn("/etc", cmd)
        self.assertIn("/lib64", cmd)

        # Virtual filesystems
        self.assertIn("--dev", cmd)
        self.assertIn("/dev", cmd)
        self.assertIn("--proc", cmd)
        self.assertIn("/proc", cmd)
        self.assertIn("--tmpfs", cmd)
        self.assertIn("/tmp", cmd)

        # Inner command appended at end
        self.assertEqual(cmd[-2:], ["python3", "server.py"])

    def test_network_isolation_toggle(self):
        """Verify --unshare-net and --share-net toggle based on allow_net parameter."""
        sb_nonet = sandbox.McpSandbox(server_name="isolated", allow_net=False)
        cmd_nonet = sb_nonet.build_command(["run"])
        self.assertIn("--unshare-net", cmd_nonet)
        self.assertNotIn("--share-net", cmd_nonet)

        sb_net = sandbox.McpSandbox(server_name="networked", allow_net=True)
        cmd_net = sb_net.build_command(["run"])
        self.assertIn("--share-net", cmd_net)
        self.assertNotIn("--unshare-net", cmd_net)

    def test_disallowed_host_write_paths(self):
        """Verify that attempting to mount protected system directories as writable raises ValueError."""
        sb = sandbox.McpSandbox(server_name="test-server")

        disallowed = [
            "/etc",
            "/usr",
            "/boot",
            "/sys",
            "/root",
            "/bin",
            "/sbin",
            "/lib",
            "/lib64",
            "/dev",
            "/proc",
            "/etc/passwd",
            "/usr/local/bin",
            "/boot/efi",
            "/sys/fs/cgroup",
            "/var/lib/mios/../../../etc",
            "/var/../usr/bin",
        ]

        for path in disallowed:
            with self.assertRaises(ValueError, msg=f"Should reject writable mount for {path}"):
                sb.add_custom_bind(path, writable=True)

            with self.assertRaises(ValueError, msg=f"Should reject direct add_rw_bind for {path}"):
                sb.add_rw_bind(path)

            with self.assertRaises(ValueError, msg=f"Should reject workspace_dir for {path}"):
                sb.set_workspace_dir(path)

    def test_custom_ro_binds(self):
        """Verify custom read-only bind mounts can be added and rendered in bwrap command."""
        sb = sandbox.McpSandbox(
            server_name="test-ro",
            custom_ro_binds=[
                "/usr/share/custom-data",
                ("/opt/models", "/var/models"),
            ],
        )
        sb.add_ro_bind("/opt/extra-docs")
        sb.add_custom_bind("/opt/configs", "/etc/local-config", writable=False)

        cmd = sb.build_command(["run"])

        # Check ro mounts present in sequence
        def find_subseq(seq, sub):
            for i in range(len(seq) - len(sub) + 1):
                if seq[i : i + len(sub)] == sub:
                    return True
            return False

        self.assertTrue(find_subseq(cmd, ["--ro-bind", "/usr/share/custom-data", "/usr/share/custom-data"]))
        self.assertTrue(find_subseq(cmd, ["--ro-bind", "/opt/models", "/var/models"]))
        self.assertTrue(find_subseq(cmd, ["--ro-bind", "/opt/extra-docs", "/opt/extra-docs"]))
        self.assertTrue(find_subseq(cmd, ["--ro-bind", "/opt/configs", "/etc/local-config"]))

    def test_custom_rw_binds(self):
        """Verify authorized writable bind mounts are accepted and added with --bind."""
        sb = sandbox.McpSandbox(
            server_name="test-rw",
            custom_rw_binds=[
                "/var/lib/mios/ai/workspace",
                ("/var/tmp/mcp-cache", "/cache"),
            ],
        )
        sb.add_rw_bind("/tmp/mcp-scratch")
        sb.add_custom_bind("/home/user/project", writable=True)

        cmd = sb.build_command(["node", "index.js"])

        def find_subseq(seq, sub):
            for i in range(len(seq) - len(sub) + 1):
                if seq[i : i + len(sub)] == sub:
                    return True
            return False

        self.assertTrue(find_subseq(cmd, ["--bind", "/var/lib/mios/ai/workspace", "/var/lib/mios/ai/workspace"]))
        self.assertTrue(find_subseq(cmd, ["--bind", "/var/tmp/mcp-cache", "/cache"]))
        self.assertTrue(find_subseq(cmd, ["--bind", "/tmp/mcp-scratch", "/tmp/mcp-scratch"]))
        self.assertTrue(find_subseq(cmd, ["--bind", "/home/user/project", "/home/user/project"]))

    def test_workspace_dir_configuration(self):
        """Verify workspace_dir configuration sets --bind and --chdir."""
        sb = sandbox.McpSandbox(
            server_name="test-ws",
            workspace_dir="/var/lib/mios/workspace",
        )
        cmd = sb.build_command(["cargo", "run"])

        self.assertIn("--bind", cmd)
        self.assertIn("/var/lib/mios/workspace", cmd)
        self.assertIn("--chdir", cmd)

        idx_chdir = cmd.index("--chdir")
        self.assertEqual(cmd[idx_chdir + 1], "/var/lib/mios/workspace")

    def test_initialization_edge_cases(self):
        """Verify input validation during McpSandbox initialization and command generation."""
        # Empty server name
        with self.assertRaises(ValueError):
            sandbox.McpSandbox(server_name="")

        with self.assertRaises(ValueError):
            sandbox.McpSandbox(server_name="   ")

        # Invalid bind type
        with self.assertRaises(TypeError):
            sandbox.McpSandbox(server_name="test", custom_ro_binds=[123])  # type: ignore

        with self.assertRaises(TypeError):
            sandbox.McpSandbox(server_name="test", custom_rw_binds=[{"bad": "type"}])  # type: ignore

        # Empty inner command
        sb = sandbox.McpSandbox(server_name="test")
        with self.assertRaises(ValueError):
            sb.build_command([])

    def test_to_dict_serialization(self):
        """Verify dictionary export contains all configuration properties."""
        sb = sandbox.McpSandbox(
            server_name="export-test",
            allow_net=True,
            workspace_dir="/var/tmp/workspace",
            custom_ro_binds=["/usr/share/dict"],
            custom_rw_binds=["/var/tmp/scratch"],
        )
        d = sb.to_dict()

        self.assertEqual(d["server_name"], "export-test")
        self.assertTrue(d["allow_net"])
        self.assertEqual(d["workspace_dir"], "/var/tmp/workspace")
        self.assertEqual(d["ro_binds"], [("/usr/share/dict", "/usr/share/dict")])
        self.assertEqual(d["rw_binds"], [("/var/tmp/scratch", "/var/tmp/scratch")])

    def test_parse_bind_arg(self):
        """Verify parsing of command-line bind mount syntax."""
        self.assertEqual(sandbox.parse_bind_arg("/usr/share"), ("/usr/share", "/usr/share"))
        self.assertEqual(sandbox.parse_bind_arg("/host/path:/container/path"), ("/host/path", "/container/path"))

    def test_cli_dry_run_command(self):
        """Verify CLI --dry-run prints generated bwrap command as JSON."""
        captured_stdout = io.StringIO()
        with patch("sys.stdout", captured_stdout):
            exit_code = sandbox.main([
                "--server-name", "cli-test",
                "--allow-net",
                "--workspace-dir", "/var/lib/mios/ws",
                "--ro-bind", "/usr/share/locale",
                "--rw-bind", "/var/tmp/scratch:/scratch",
                "--dry-run",
                "--", "python3", "-m", "mcp_server",
            ])

        self.assertEqual(exit_code, 0)
        output = captured_stdout.getvalue()
        cmd_list = json.loads(output)

        self.assertIsInstance(cmd_list, list)
        self.assertEqual(cmd_list[0], "bwrap")
        self.assertIn("--share-net", cmd_list)
        self.assertIn("/var/lib/mios/ws", cmd_list)
        self.assertIn("--chdir", cmd_list)
        self.assertEqual(cmd_list[-3:], ["python3", "-m", "mcp_server"])

    def test_cli_dry_run_config_dump(self):
        """Verify CLI --dry-run without inner command prints config JSON."""
        captured_stdout = io.StringIO()
        with patch("sys.stdout", captured_stdout):
            exit_code = sandbox.main([
                "--server-name", "config-dump",
                "--allow-net",
                "--dry-run",
            ])

        self.assertEqual(exit_code, 0)
        output = captured_stdout.getvalue()
        cfg = json.loads(output)
        self.assertEqual(cfg["server_name"], "config-dump")
        self.assertTrue(cfg["allow_net"])

    def test_validate_rw_path_direct(self):
        """Verify direct calls to validate_rw_path with various path formats."""
        sb = sandbox.McpSandbox(server_name="validate-test")
        # Valid paths
        self.assertEqual(sb.validate_rw_path("/var/lib/mios/data"), "/var/lib/mios/data")
        self.assertEqual(sb.validate_rw_path("/home/mios/projects"), "/home/mios/projects")
        self.assertEqual(sb.validate_rw_path("/tmp/scratch"), "/tmp/scratch")

        # Invalid empty or non-string
        with self.assertRaises(ValueError):
            sb.validate_rw_path("")
        with self.assertRaises(ValueError):
            sb.validate_rw_path(None)  # type: ignore

    def test_custom_bwrap_binary(self):
        """Verify custom bubblewrap binary path is used in command generation."""
        sb = sandbox.McpSandbox(server_name="custom-bin", bwrap_binary="/usr/local/bin/bwrap-hardened")
        cmd = sb.build_command(["echo", "test"])
        self.assertEqual(cmd[0], "/usr/local/bin/bwrap-hardened")

    def test_property_immutability(self):
        """Verify ro_binds and rw_binds property getters return copies."""
        sb = sandbox.McpSandbox(server_name="prop-test")
        sb.add_ro_bind("/usr/share/doc")
        ro_list = sb.ro_binds
        ro_list.append(("/injected", "/injected"))
        self.assertEqual(len(sb.ro_binds), 1)

    def test_cli_disallowed_write_returns_error(self):
        """Verify CLI execution with forbidden writable path exits with non-zero error."""
        captured_stderr = io.StringIO()
        with patch("sys.stderr", captured_stderr):
            exit_code = sandbox.main([
                "--server-name", "bad-cli",
                "--rw-bind", "/etc",
                "--dry-run",
                "--", "ls",
            ])

        self.assertEqual(exit_code, 1)
        self.assertIn("Disallowed writable bind path", captured_stderr.getvalue())

    def test_execute_invokes_subprocess(self):
        """Verify execute method constructs command and invokes subprocess.run."""
        sb = sandbox.McpSandbox(server_name="exec-test")
        mock_proc = MagicMock()
        mock_proc.returncode = 0

        with patch("subprocess.run", return_value=mock_proc) as mock_run:
            res = sb.execute(["echo", "hello"], capture_output=True)
            self.assertEqual(res.returncode, 0)
            mock_run.assert_called_once()
            called_args = mock_run.call_args[0][0]
            self.assertEqual(called_args[0], "bwrap")
            self.assertEqual(called_args[-2:], ["echo", "hello"])

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMcpSandbox)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
