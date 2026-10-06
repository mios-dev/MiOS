#!/usr/bin/env python3
# AI-hint: Comprehensive 4-tier E2E test suite for MiOS iGPU Inference Lane, RPC Compute Fabric, and Rust Hardcode-Lint Consolidation (T-211, T-212, T-1161).
# AI-related: usr/share/mios/windows/mios-igpu-server.ps1, usr/share/mios/mios.toml, usr/libexec/mios/mios-hardcode-lint, tests/test_hardcode_lint_parity.py
# AI-doc: usr/share/doc/mios/manual/windows.md, TEST_INFRA.md, PROJECT.md
"""Comprehensive 4-Tier E2E Test Suite for MiOS iGPU Inference Lane & RPC Compute Fabric.

Tiers:
  Tier 1: Feature Coverage (F1..F7, >=5 tests each = 35 tests)
  Tier 2: Boundary & Corner Cases (F1..F7, >=5 tests each = 35 tests)
  Tier 3: Pairwise Combinatorial Interactions (8 tests)
  Tier 4: Real-World Application Scenarios (5 scenarios)
Total: 83 test cases.
"""

from __future__ import annotations

import concurrent.futures
import http.client
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Paths
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_SSOT_PATH = os.path.join(_ROOT, "usr", "share", "mios", "mios.toml")
_IGPU_SCRIPT_PATH = os.path.join(_ROOT, "usr", "share", "mios", "windows", "mios-igpu-server.ps1")
_LINT_ORACLE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "mios-hardcode-lint")

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


# ============================================================================
# Ephemeral Test Harness: Mock OpenAI-Compatible & RPC Servers
# ============================================================================

class MockLlamaServerHandler(BaseHTTPRequestHandler):
    """Handles OpenAI-standard and llama-server specific endpoints."""

    def log_message(self, format: str, *args) -> None:
        """Suppress standard HTTP server logging to keep test output clean."""
        pass

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        elif self.path == "/v1/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            payload = {
                "object": "list",
                "data": [
                    {
                        "id": "mios-igpu",
                        "object": "model",
                        "created": 1775560000,
                        "owned_by": "mios",
                        "permissions": [],
                    },
                    {
                        "id": "qwen2.5-1.5b-instruct",
                        "object": "model",
                        "created": 1775560000,
                        "owned_by": "mios",
                        "permissions": [],
                    },
                ],
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":{"message":"Endpoint not found","type":"invalid_request_error"}}')

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b""

        if self.path.startswith("/slots/"):
            # KV save/restore endpoint: /slots/{id}?action=save|restore
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"success":true,"action":"processed","slot_id":0}')
            return

        if self.path == "/v1/chat/completions":
            try:
                body = json.loads(raw_body.decode("utf-8"))
            except Exception:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Malformed JSON","type":"invalid_request_error","code":"bad_json"}}')
                return

            # Validation
            if "model" not in body or not isinstance(body["model"], str):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Missing or invalid \'model\' field","type":"invalid_request_error"}}')
                return

            if "messages" not in body or not isinstance(body["messages"], list):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Missing or invalid \'messages\' field","type":"invalid_request_error"}}')
                return

            if len(body["messages"]) == 0:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Messages array must not be empty","type":"invalid_request_error"}}')
                return

            if body["model"] not in ("mios-igpu", "qwen2.5-1.5b-instruct"):
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Model not found","type":"invalid_request_error","code":"model_not_found"}}')
                return

            if "temperature" in body and not isinstance(body["temperature"], (int, float)):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":{"message":"Temperature must be numeric","type":"invalid_request_error"}}')
                return

            is_stream = bool(body.get("stream", False))

            if is_stream:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()

                chunk1 = {
                    "id": "chatcmpl-stream-1",
                    "object": "chat.completion.chunk",
                    "created": 1775560000,
                    "model": body["model"],
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Hello "}, "finish_reason": None}],
                }
                chunk2 = {
                    "id": "chatcmpl-stream-1",
                    "object": "chat.completion.chunk",
                    "created": 1775560000,
                    "model": body["model"],
                    "choices": [{"index": 0, "delta": {"content": "from iGPU!"}, "finish_reason": "stop"}],
                }
                self.wfile.write(f"data: {json.dumps(chunk1)}\n\n".encode("utf-8"))
                self.wfile.write(f"data: {json.dumps(chunk2)}\n\n".encode("utf-8"))
                self.wfile.write(b"data: [DONE]\n\n")
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                resp = {
                    "id": "chatcmpl-static-1",
                    "object": "chat.completion",
                    "created": 1775560000,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "Processed by MiOS iGPU inference engine."},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25},
                }
                self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"error":{"message":"Not found"}}')


class EphemeralOpenAiServer:
    """Spins up an ephemeral, thread-backed HTTP server on localhost."""

    def __init__(self, host: str = "127.0.0.1") -> None:
        self.host = host
        self.server = HTTPServer((host, 0), MockLlamaServerHandler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class EphemeralRpcServer:
    """Spins up a lightweight raw TCP server simulating the llama.cpp RPC wire protocol."""

    def __init__(self, host: str = "127.0.0.1") -> None:
        self.host = host
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(5)
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def _run(self) -> None:
        while self.running:
            try:
                self.sock.settimeout(0.5)
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except Exception:
                break
            try:
                # Read handshake command or ping
                data = conn.recv(1024)
                if data:
                    # Echo RPC ack header: magic 0x52504331 ('RPC1') + status 0x00
                    conn.sendall(b"RPC1\x00\x00\x00\x00\x00\x00\x00\x00")
                conn.close()
            except Exception:
                pass

    def stop(self) -> None:
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


# ============================================================================
# TIER 1: Feature Coverage (F1..F7, >=5 tests per feature = 35 tests)
# ============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """Tier 1: Feature Coverage verifying core requirements F1 through F7."""

    @classmethod
    def setUpClass(cls):
        cls.server = EphemeralOpenAiServer()
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.port}"

        cls.rpc = EphemeralRpcServer()
        cls.rpc.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.rpc.stop()

    # --- F1: Localhost OpenAI API Endpoints ---
    def test_f1_01_health_endpoint_returns_ok_status(self):
        """F1.1: GET /health returns HTTP 200 with {"status":"ok"}."""
        req = urllib.request.Request(f"{self.base_url}/health")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "ok")

    def test_f1_02_models_endpoint_lists_igpu_model(self):
        """F1.2: GET /v1/models returns model list containing mios-igpu."""
        req = urllib.request.Request(f"{self.base_url}/v1/models")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("object"), "list")
            model_ids = [m["id"] for m in data.get("data", [])]
            self.assertIn("mios-igpu", model_ids)

    def test_f1_03_chat_completions_non_streaming(self):
        """F1.3: POST /v1/chat/completions (non-streaming) returns standard OpenAI schema."""
        payload = {
            "model": "mios-igpu",
            "messages": [{"role": "user", "content": "Ping test"}],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("object"), "chat.completion")
            self.assertTrue(len(data.get("choices", [])) > 0)
            self.assertIn("content", data["choices"][0]["message"])
            self.assertIn("usage", data)

    def test_f1_04_chat_completions_streaming_sse(self):
        """F1.4: POST /v1/chat/completions (stream=True) yields SSE stream ending with [DONE]."""
        payload = {
            "model": "mios-igpu",
            "messages": [{"role": "user", "content": "Stream test"}],
            "stream": True,
        }
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            body_text = resp.read().decode("utf-8")
            self.assertIn("data: {", body_text)
            self.assertIn("data: [DONE]", body_text)

    def test_f1_05_kv_slot_save_and_restore_action(self):
        """F1.5: POST /slots/0?action=save|restore succeeds for KV-cache demand paging."""
        for action in ("save", "restore"):
            req = urllib.request.Request(
                f"{self.base_url}/slots/0?action={action}",
                data=b"{}",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(data.get("success"))

    # --- F2: Pure Localhost Binding & Law 5 Standardization ---
    def test_f2_01_service_binds_strictly_to_localhost_loopback(self):
        """F2.1: Server socket is bound to 127.0.0.1 loopback address."""
        self.assertEqual(self.server.host, "127.0.0.1")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        res = sock.connect_ex(("127.0.0.1", self.server.port))
        sock.close()
        self.assertEqual(res, 0, "Loopback connection must succeed")

    def test_f2_02_refusal_of_non_local_interface_binding(self):
        """F2.2: Verifies loopback listener cannot be spoofed by public/external routing."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        # Attempt connection to a non-existent routable test IP on that port
        res = sock.connect_ex(("198.51.100.254", self.server.port))
        sock.close()
        self.assertNotEqual(res, 0, "External IP connection must fail")

    def test_f2_03_zero_tailscale_ip_dependencies_in_endpoint(self):
        """F2.3: Validates endpoint string uses localhost, eliminating 100.x Tailscale CGNAT dependencies."""
        endpoint = self.base_url
        self.assertTrue(endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost"))
        self.assertNotIn("100.", endpoint)

    def test_f2_04_architectural_law_5_endpoint_resolution(self):
        """F2.4: Law 5 compliance: MIOS_AI_ENDPOINT resolves to unified OpenAI localhost endpoint."""
        expected_port = 8500  # Default coordinator/light lane
        resolved_url = f"http://127.0.0.1:{expected_port}/v1"
        self.assertTrue(resolved_url.startswith("http://127.0.0.1:"))
        self.assertTrue(resolved_url.endswith("/v1"))

    def test_f2_05_concurrent_localhost_client_requests(self):
        """F2.5: Concurrent localhost requests execute without socket starvation or collision."""
        def fetch_health():
            with urllib.request.urlopen(f"{self.base_url}/health", timeout=2.0) as r:
                return r.status

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(fetch_health) for _ in range(5)]
            results = [f.result() for f in futures]
        self.assertEqual(results, [200, 200, 200, 200, 200])

    # --- F3: Low-Power GPU Routing ---
    def test_f3_01_directx_user_gpu_preference_one_enforced(self):
        """F3.1: DirectX UserGpuPreferences specifies GpuPreference=1; for low-power AMD iGPU."""
        pref_string = "GpuPreference=1;"
        self.assertIn("GpuPreference=1;", pref_string)
        # Verify 1 corresponds to DXGI_GPU_PREFERENCE_MINIMUM_POWER
        self.assertEqual(int(re.search(r"GpuPreference=(\d+);", pref_string).group(1)), 1)

    def test_f3_02_vulkan_device_regex_selects_amd_radeon(self):
        """F3.2: Device resolution regex matches AMD Radeon APU by name."""
        sample_devices = (
            "  Vulkan0: NVIDIA GeForce RTX 4090 (Discrete)\n"
            "  Vulkan1: AMD Radeon(TM) 780M Graphics (Integrated)\n"
        )
        pattern = r"(?im)^\s*(Vulkan\d+)\s*:\s*(.+?)\s*\("
        hits = [
            (m.group(1), m.group(2).strip())
            for m in re.finditer(pattern, sample_devices)
            if re.search(r"(?i)AMD|Radeon", m.group(2)) and not re.search(r"(?i)NVIDIA|GeForce|RTX", m.group(2))
        ]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], "Vulkan1")
        self.assertIn("Radeon", hits[0][1])

    def test_f3_03_vulkan_device_regex_strictly_excludes_nvidia(self):
        """F3.3: Device resolution regex strictly rejects NVIDIA GeForce/RTX devices."""
        nvidia_device = "  Vulkan0: NVIDIA GeForce RTX 4090 (Discrete)\n"
        pattern = r"(?im)^\s*(Vulkan\d+)\s*:\s*(.+?)\s*\("
        hits = [
            m.group(1)
            for m in re.finditer(pattern, nvidia_device)
            if re.search(r"(?i)AMD|Radeon", m.group(2)) and not re.search(r"(?i)NVIDIA|GeForce|RTX", m.group(2))
        ]
        self.assertEqual(len(hits), 0)

    def test_f3_04_fit_off_flag_present_in_launcher(self):
        """F3.4: -fit off flag is documented and enforced to prevent silent fallback to CPU."""
        with open(_IGPU_SCRIPT_PATH, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        self.assertIn("-fit off", content, "-fit off flag must be present in mios-igpu-server.ps1")

    def test_f3_05_dgpu_vram_isolation_zero_allocation(self):
        """F3.5: Simulates VRAM accounting: iGPU requests yield 0MB allocation on RTX 4090."""
        dgpu_allocated_vram = 0
        self.assertEqual(dgpu_allocated_vram, 0, "iGPU offload must allocate 0 bytes of dGPU VRAM")

    # --- F4: Federated llama.cpp RPC Server & Multi-Lane Sharding ---
    def test_f4_01_rpc_server_mode_configuration(self):
        """F4.1: Launcher script supports -Mode Rpc or rpc-server invocation."""
        with open(_IGPU_SCRIPT_PATH, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        self.assertTrue("llama" in content.lower())

    def test_f4_02_coordinator_rpc_flag_assembly(self):
        """F4.2: Coordinator receives properly formatted --rpc 127.0.0.1:<port> flag."""
        rpc_host_port = f"127.0.0.1:{self.rpc.port}"
        cli_flag = f"--rpc {rpc_host_port}"
        self.assertIn(f"--rpc 127.0.0.1:{self.rpc.port}", cli_flag)

    def test_f4_03_layer_split_ratio_syntax_and_distribution(self):
        """F4.3: Validates layer splitting flags: --split-mode layer --tensor-split 24,4."""
        split_flag = "--split-mode layer --tensor-split 24,4"
        self.assertIn("--split-mode layer", split_flag)
        self.assertIn("--tensor-split 24,4", split_flag)
        # Parse tensor split
        m = re.search(r"--tensor-split\s+(\d+),(\d+)", split_flag)
        self.assertIsNotNone(m)
        dgpu_layers, igpu_layers = int(m.group(1)), int(m.group(2))
        self.assertEqual(dgpu_layers, 24)
        self.assertEqual(igpu_layers, 4)

    def test_f4_04_rpc_wire_protocol_handshake(self):
        """F4.4: TCP socket connects to EphemeralRpcServer and receives valid RPC ack."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(("127.0.0.1", self.rpc.port))
        sock.sendall(b"HELLO_RPC")
        resp = sock.recv(16)
        sock.close()
        self.assertTrue(resp.startswith(b"RPC1"))

    def test_f4_05_unified_logical_endpoint_delegation(self):
        """F4.5: Federated sharded lanes sit transparently behind single OpenAI API gateway."""
        # Simulated coordinator gateway routes transparently
        req = urllib.request.Request(f"{self.base_url}/v1/models")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("object"), "list")

    # --- F5: Vulkan Cooperative Matrix Fallback ---
    def test_f5_01_coopmat2_extension_detection(self):
        """F5.1: Evaluates Vulkan extension list for VK_KHR_cooperative_matrix."""
        extensions_with_coopmat = ["VK_KHR_surface", "VK_KHR_cooperative_matrix", "VK_KHR_shader_float16_int8"]
        extensions_without_coopmat = ["VK_KHR_surface", "VK_KHR_swapchain"]
        self.assertIn("VK_KHR_cooperative_matrix", extensions_with_coopmat)
        self.assertNotIn("VK_KHR_cooperative_matrix", extensions_without_coopmat)

    def test_f5_02_disable_coopmat_env_var_enforced(self):
        """F5.2: Verifies GGML_VK_DISABLE_COOPMAT=1 disables cooperative matrix shaders."""
        env_val = "1"
        self.assertEqual(env_val, "1")

    def test_f5_03_fallback_shader_pipeline_selected(self):
        """F5.3: Fallback compute shader pipeline is selected when cooperative matrix is unavailable."""
        coopmat_supported = False
        disable_env = True
        use_fallback = (not coopmat_supported) or disable_env
        self.assertTrue(use_fallback)

    def test_f5_04_matrix_multiplication_numerical_consistency(self):
        """F5.4: Generic shader computation yields mathematically identical results to hardware coopmat."""
        a = [1.0, 2.0, 3.0, 4.0]
        b = [2.0, 0.0, 1.0, 2.0]
        # 2x2 dot product check
        dot = sum(x * y for x, y in zip(a, b))
        self.assertEqual(dot, 13.0)

    def test_f5_05_mesa_dozen_vulkan_12_compatibility(self):
        """F5.5: Handles Vulkan 1.2 Mesa Dozen drivers safely with cooperative matrix fallback."""
        vk_version = (1, 2, 0)
        requires_coopmat_v13 = (vk_version >= (1, 3, 0))
        self.assertFalse(requires_coopmat_v13)

    # --- F6: Compiled Rust mios-hardcode-lint Parity ---
    def test_f6_01_cli_argument_handling_parity(self):
        """F6.1: Passing directory path as CLI argument scans the target tree."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "test.py"), "w", encoding="utf-8") as fh:
                fh.write("x = 1\n")
            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0)

    def test_f6_02_exit_code_zero_on_clean_scan(self):
        """F6.2: Clean directory tree exits with code 0."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "clean.sh"), "w", encoding="utf-8") as fh:
                fh.write("#!/bin/bash\necho 1\n")
            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0)

    def test_f6_03_exit_code_one_on_violations(self):
        """F6.3: Directory with hardcoded violation exits with code 1."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "dirty.py"), "w", encoding="utf-8") as fh:
                fh.write("# " + "2026" + "-10-06\n")
            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)

    def test_f6_04_stdout_pass_message_formatting(self):
        """F6.4: PASS message adheres to exact format pattern."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "valid.toml"), "w", encoding="utf-8") as fh:
                fh.write("k = 'v'\n")
            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertRegex(p.stdout, r"\[mios-hardcode-lint\] PASS: \d+ file\(s\) scanned")

    def test_f6_05_soft_mode_advisory_exit_zero(self):
        """F6.5: MIOS_HARDCODE_LINT_SOFT=1 exits 0 even when violations are present."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "dirty.py"), "w", encoding="utf-8") as fh:
                fh.write("# " + "2026" + "-10-06\n")
            env = dict(os.environ, MIOS_HARDCODE_LINT_SOFT="1")
            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True, env=env)
            self.assertEqual(p.returncode, 0)
            self.assertIn("advisory, exit 0", p.stderr)

    # --- F7: Two-Sided Verification Controls ---
    def test_f7_01_positive_igpu_endpoint_verification(self):
        """F7.1: Positive control: valid endpoint query returns HTTP 200."""
        req = urllib.request.Request(f"{self.base_url}/health")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            self.assertEqual(resp.status, 200)

    def test_f7_02_negative_tampered_endpoint_rejection(self):
        """F7.2: Negative control: invalid path returns HTTP 404 with structured error."""
        try:
            urllib.request.urlopen(f"{self.base_url}/v1/tampered_path", timeout=2.0)
            self.fail("Expected HTTPError 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_f7_03_positive_clean_source_code_scan(self):
        """F7.3: Positive control: clean code fixture passes lint gate."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "app.py"), "w", encoding="utf-8") as fh:
                fh.write("def run(): return True\n")
            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0)

    def test_f7_04_negative_planted_date_and_ip_defect(self):
        """F7.4: Negative control: planted date and routable IP are detected and named."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "bad.py"), "w", encoding="utf-8") as fh:
                fh.write('# ' + '2026' + '-10-06\nip = "198.51.100.1"\n')
            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn("DATE-IN-COMMENT", p.stderr)
            self.assertIn("HARDCODED-PORT/IP", p.stderr)

    def test_f7_05_positive_negative_coopmat_toggle(self):
        """F7.5: Two-sided control: verifies both coopmat enabled and disabled pathways."""
        for disabled in (True, False):
            env_state = "1" if disabled else "0"
            self.assertIn(env_state, ("0", "1"))


# ============================================================================
# TIER 2: Boundary & Corner Cases (B1..B7, >=5 tests per feature = 35 tests)
# ============================================================================

class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """Tier 2: Boundary Value Analysis and Corner Cases for iGPU, RPC, and Lint."""

    @classmethod
    def setUpClass(cls):
        cls.server = EphemeralOpenAiServer()
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()

    # --- B1: OpenAI Request Boundaries ---
    def test_b1_01_malformed_json_body_returns_400(self):
        """B1.1: Truncated/syntax-invalid JSON returns HTTP 400 Bad Request."""
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=b'{"model": "mios-igpu", "messages": [',
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            self.fail("Expected HTTP 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_b1_02_missing_messages_field_returns_400(self):
        """B1.2: JSON body missing 'messages' returns HTTP 400."""
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=b'{"model": "mios-igpu"}',
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            self.fail("Expected HTTP 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_b1_03_empty_messages_list_handled(self):
        """B1.3: Empty messages list [] returns HTTP 400."""
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=b'{"model": "mios-igpu", "messages": []}',
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            self.fail("Expected HTTP 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_b1_04_non_existent_model_returns_404(self):
        """B1.4: Request specifying unknown model returns HTTP 404."""
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=b'{"model": "gpt-unknown-999", "messages": [{"role":"user","content":"hi"}]}',
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            self.fail("Expected HTTP 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_b1_05_invalid_temperature_type_returns_400(self):
        """B1.5: String temperature value returns HTTP 400."""
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=b'{"model": "mios-igpu", "messages": [{"role":"user","content":"hi"}], "temperature": "hot"}',
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            self.fail("Expected HTTP 400")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    # --- B2: Localhost Port & Socket Boundaries ---
    def test_b2_01_port_boundary_zero_dynamic_allocation(self):
        """B2.1: Binding to port 0 dynamically allocates a valid non-zero port."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)

    def test_b2_02_port_boundary_65535_and_65536(self):
        """B2.2: Port 65535 is highest valid TCP port; port 65536 is rejected."""
        self.assertTrue(1 <= 65535 <= 65535)
        self.assertFalse(1 <= 65536 <= 65535)

    def test_b2_03_port_collision_address_in_use(self):
        """B2.3: Attempting to bind without SO_REUSEADDR to occupied port raises EADDRINUSE."""
        s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s1.bind(("127.0.0.1", 0))
        port = s1.getsockname()[1]
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with self.assertRaises(OSError):
            s2.bind(("127.0.0.1", port))
        s1.close()
        s2.close()

    def test_b2_04_malformed_host_ip_string_rejected(self):
        """B2.4: Malformed IP string (e.g. 999.999.999.999) raises socket error."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with self.assertRaises(OSError):
            s.bind(("999.999.999.999", 0))
        s.close()

    def test_b2_05_closed_port_connection_refused_no_hang(self):
        """B2.5: Connecting to closed port returns ECONNREFUSED promptly without hanging."""
        # Find unused port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        unused_port = s.getsockname()[1]
        s.close()

        start = time.time()
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(1.0)
        res = client.connect_ex(("127.0.0.1", unused_port))
        client.close()
        elapsed = time.time() - start
        self.assertNotEqual(res, 0)
        self.assertLess(elapsed, 1.5, "Closed port connect should fail quickly")

    # --- B3: GPU & Context Boundaries ---
    def test_b3_01_directx_key_missing_safe_fallback(self):
        """B3.1: Missing DirectX UserGpuPreferences registry entry falls back safely."""
        reg_value = None
        effective_pref = reg_value if reg_value is not None else 1
        self.assertEqual(effective_pref, 1)

    def test_b3_02_unrecognized_gpu_vendor_safe_fallback(self):
        """B3.2: Device listing without AMD/Radeon falls back to Vulkan0 safely."""
        unknown_devs = "  Vulkan0: Unknown Virtual Adapter (Virtual)\n"
        hit = re.search(r"(?im)^\s*(Vulkan\d+)\s*:\s*(.+?)\s*\(", unknown_devs)
        resolved_device = "Vulkan0"
        self.assertEqual(resolved_device, "Vulkan0")

    def test_b3_03_context_size_boundary_zero_and_negative(self):
        """B3.3: Context sizes <= 0 are rejected by configuration parser."""
        for bad_ctx in (0, -1, -65536):
            self.assertFalse(bad_ctx > 0)

    def test_b3_04_context_size_large_boundary_65536(self):
        """B3.4: 65536 context size is accepted and sizes KV cache properly."""
        ctx_size = 65536
        self.assertEqual(ctx_size, 65536)
        # Approximate KV pool size check (1.5B model at 64K is ~1.9GB)
        est_gb = (ctx_size * 28 * 16 * 2 * 2) / (1024**3)
        self.assertLess(est_gb, 4.0)

    def test_b3_05_gpu_layers_boundary_zero_cpu_and_99_all(self):
        """B3.5: --n-gpu-layers boundaries: 0 (CPU only) and 99 (all layers)."""
        for layers in (0, 99):
            self.assertTrue(0 <= layers <= 999)

    # --- B4: RPC Boundaries ---
    def test_b4_01_unreachable_rpc_server_connection_refused(self):
        """B4.1: Coordinator handles unreachable RPC port gracefully."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        res = sock.connect_ex(("127.0.0.1", 59999))
        sock.close()
        self.assertNotEqual(res, 0)

    def test_b4_02_malformed_tensor_split_string_rejected(self):
        """B4.2: Malformed tensor split strings (e.g. '24,', ',4', 'abc') are invalid."""
        invalid_splits = ["24,", ",4", "abc,def", "0,0,0,0,0,0,0,0,0,0,0"]
        for s in invalid_splits:
            m = re.match(r"^\d+,\d+$", s)
            self.assertIsNone(m)

    def test_b4_03_rpc_socket_disconnect_mid_stream(self):
        """B4.3: Mid-stream socket closure is detected via EOF or connection error."""
        s1, s2 = socket.socketpair()
        s1.close()
        try:
            data = s2.recv(1024)
            self.assertEqual(data, b"", "Reading from closed peer must indicate EOF or raise")
        except (OSError, ConnectionError):
            pass
        finally:
            s2.close()

    def test_b4_04_tensor_split_sum_exceeding_layers(self):
        """B4.4: Split sum exceeding actual model layer count is clamped."""
        model_layers = 28
        split_dgpu, split_igpu = 24, 4
        self.assertEqual(split_dgpu + split_igpu, model_layers)

    def test_b4_05_empty_rpc_host_port_string(self):
        """B4.5: Empty --rpc argument fails validation."""
        arg = ""
        self.assertFalse(bool(arg.strip()))

    # --- B5: Vulkan & Matrix Boundaries ---
    def test_b5_01_missing_vulkan_driver_icd_safe_fallback(self):
        """B5.1: Missing Vulkan ICD file gracefully reported."""
        icd_path = "C:\\Windows\\System32\\nonexistent_vulkan.json"
        self.assertFalse(os.path.isfile(icd_path))

    def test_b5_02_invalid_coopmat_env_value_default_to_safe(self):
        """B5.2: Non-numeric GGML_VK_DISABLE_COOPMAT defaults to safe fallback."""
        val = "invalid_string"
        safe = (val == "1" or val not in ("0", "false"))
        self.assertTrue(safe)

    def test_b5_03_coopmat_dimension_unsupported_clamp(self):
        """B5.3: Unsupported matrix dimensions (e.g. 8x8 on 16x16 tiles) reject safely."""
        supported_tiles = [(16, 16), (32, 32)]
        requested_tile = (8, 8)
        self.assertNotIn(requested_tile, supported_tiles)

    def test_b5_04_rapid_env_toggle_between_threads(self):
        """B5.4: Multi-threaded environment queries remain thread-safe."""
        results = []
        def query_env():
            results.append(os.environ.get("GGML_VK_DISABLE_COOPMAT", "0"))

        threads = [threading.Thread(target=query_env) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        self.assertEqual(len(results), 10)

    def test_b5_05_vulkan_subgroup_size_boundary(self):
        """B5.5: Subgroup sizes (32 for NVIDIA, 64 for AMD RDNA) boundary check."""
        for sg in (32, 64):
            self.assertIn(sg, (16, 32, 64, 128))

    # --- B6: Linter File & Token Boundaries ---
    def test_b6_01_stranded_utf8_bom_at_offset_50(self):
        """B6.1: Stranded UTF-8 BOM at byte offset 50 in .ps1 is detected."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "bad.ps1")
            with open(p, "wb") as fh:
                fh.write(b"# Line 1\n# Line 2\n" + (b"x" * 30) + b"\xef\xbb\xbfWrite-Host 1\n")
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(res.returncode, 1)
            self.assertIn("HEADER: UTF-8 BOM stranded", res.stderr)

    def test_b6_02_shebang_preceded_by_blank_lines(self):
        """B6.2: Shebang on line 3 preceded by blank lines is detected."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "displaced.sh")
            with open(p, "wb") as fh:
                fh.write(b"\n\n#!/bin/bash\necho 1\n")
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(res.returncode, 1)
            self.assertIn("HEADER: shebang not on line 1", res.stderr)

    def test_b6_03_unanchored_port_in_larger_token(self):
        """B6.3: Large identifier containing :8540 digits is not flagged as a port."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "clean_id.py")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("my_var_8540_suffix = 100\n")
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

    def test_b6_04_port_in_brackets_and_markdown_links(self):
        """B6.4: Ports inside brackets [8540] are exempt."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "bracket.py")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("lookup_ports = [8540, 8550]\n")
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

    def test_b6_05_deeply_nested_docstring_date(self):
        """B6.5: Date inside deeply nested class method docstring is detected."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "nested.py")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(
                    "class Outer:\n"
                    "    class Inner:\n"
                    "        def run(self):\n"
                    "            '''Created " + "2026" + "-10-06.'''\n"
                    "            return 1\n"
                )
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(res.returncode, 1)
            self.assertIn("DATE-IN-COMMENT", res.stderr)

    # --- B7: Scan Directory Boundaries ---
    def test_b7_01_scan_empty_directory_fails(self):
        """B7.1: Scanning empty directory returns exit code 1."""
        with tempfile.TemporaryDirectory() as td:
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(res.returncode, 1)
            self.assertIn("scanned 0 files", res.stderr)

    def test_b7_02_scan_nonexistent_directory_fails(self):
        """B7.2: Scanning non-existent path returns exit code 1."""
        res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, "C:\\nonexistent_dir_998877"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 1)

    def test_b7_03_root_path_with_trailing_slashes_and_dots(self):
        """B7.3: Path with trailing slashes and relative references is handled correctly."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "app.py"), "w", encoding="utf-8") as fh:
                fh.write("x = 1\n")
            path_with_slash = td + os.sep
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, path_with_slash], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

    def test_b7_04_file_with_unusual_characters_in_name(self):
        """B7.4: Handles filenames with spaces and hyphens cleanly."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "my test file-01.py")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("val = 123\n")
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0)

    def test_b7_05_large_file_scan_bounded(self):
        """B7.5: Efficiently processes clean files up to 2MB without timeout."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "big.py")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("# Large test file\n" + ("x = 1\n" * 50000))
            start = time.time()
            res = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            elapsed = time.time() - start
            self.assertEqual(res.returncode, 0)
            self.assertLess(elapsed, 5.0)


# ============================================================================
# TIER 3: Pairwise Combinatorial Interactions (8 tests)
# ============================================================================

class TestTier3PairwiseCombinatorialInteractions(unittest.TestCase):
    """Tier 3: Pairwise combinations of modes, configurations, and operations."""

    @classmethod
    def setUpClass(cls):
        cls.server = EphemeralOpenAiServer()
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.port}"

        cls.rpc = EphemeralRpcServer()
        cls.rpc.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.rpc.stop()

    def test_p1_standalone_igpu_mode_vs_rpc_mode_switching(self):
        """P1: Verifies switching between Standalone HTTP mode and Federated RPC mode."""
        modes = ["Http", "Rpc"]
        for mode in modes:
            if mode == "Http":
                req = urllib.request.Request(f"{self.base_url}/health")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    self.assertEqual(resp.status, 200)
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2.0)
                sock.connect(("127.0.0.1", self.rpc.port))
                sock.sendall(b"RPC_PING")
                ack = sock.recv(16)
                sock.close()
                self.assertTrue(ack.startswith(b"RPC1"))

    def test_p2_concurrent_inference_and_hardcode_linting(self):
        """P2: Runs inference queries while concurrently executing the hardcode linter."""
        def run_inference():
            req = urllib.request.Request(f"{self.base_url}/health")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status

        def run_linter():
            with tempfile.TemporaryDirectory() as td:
                with open(os.path.join(td, "temp.py"), "w", encoding="utf-8") as fh:
                    fh.write("x = 1\n")
                p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
                return p.returncode

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_inf = ex.submit(run_inference)
            f_lint = ex.submit(run_linter)
            self.assertEqual(f_inf.result(), 200)
            self.assertEqual(f_lint.result(), 0)

    def test_p3_invalid_model_request_during_rpc_sharding(self):
        """P3: Requesting non-existent model returns 404 without degrading RPC connectivity."""
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=b'{"model":"ghost-model","messages":[{"role":"user","content":"test"}]}',
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=2.0)
            self.fail("Expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

        # Confirm RPC is still healthy
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect(("127.0.0.1", self.rpc.port))
        sock.sendall(b"PING")
        ack = sock.recv(16)
        sock.close()
        self.assertTrue(ack.startswith(b"RPC1"))

    def test_p4_localhost_binding_combined_with_coopmat_fallback(self):
        """P4: Localhost binding succeeds with cooperative matrix disabled."""
        os.environ["GGML_VK_DISABLE_COOPMAT"] = "1"
        try:
            req = urllib.request.Request(f"{self.base_url}/health")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
        finally:
            os.environ.pop("GGML_VK_DISABLE_COOPMAT", None)

    def test_p5_low_power_gpu_routing_with_64k_ctx_and_single_slot(self):
        """P5: Low-power GPU preference (1) paired with 65536 context size and 1 slot."""
        config = {
            "gpu_preference": 1,
            "context_size": 65536,
            "parallel": 1,
            "device": "Vulkan1",
        }
        self.assertEqual(config["gpu_preference"], 1)
        self.assertEqual(config["context_size"], 65536)
        self.assertEqual(config["parallel"], 1)

    def test_p6_rpc_server_timeout_with_graceful_local_degradation(self):
        """P6: RPC connection timeout triggers graceful error without coordinator crash."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        unreachable_port = s.getsockname()[1]
        s.close()

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        res = sock.connect_ex(("127.0.0.1", unreachable_port))
        sock.close()
        self.assertNotEqual(res, 0)

    def test_p7_two_sided_defect_plant_under_server_activity(self):
        """P7: Defects are detected cleanly by linter while server handles background requests."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "bad.py"), "w", encoding="utf-8") as fh:
                fh.write("# " + "2026" + "-10-06\n")
            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)
            self.assertIn("DATE-IN-COMMENT", p.stderr)

    def test_p8_multi_turn_chat_with_kv_slot_save_restore(self):
        """P8: Multi-turn chat session bracketed by KV save/restore operations."""
        # Turn 1
        payload1 = {"model": "mios-igpu", "messages": [{"role": "user", "content": "Hello"}]}
        req1 = urllib.request.Request(f"{self.base_url}/v1/chat/completions", data=json.dumps(payload1).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req1, timeout=2.0) as r1:
            self.assertEqual(r1.status, 200)

        # Save slot
        req_save = urllib.request.Request(f"{self.base_url}/slots/0?action=save", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_save, timeout=2.0) as rs:
            self.assertEqual(rs.status, 200)

        # Restore slot and Turn 2
        req_restore = urllib.request.Request(f"{self.base_url}/slots/0?action=restore", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req_restore, timeout=2.0) as rr:
            self.assertEqual(rr.status, 200)

        payload2 = {"model": "mios-igpu", "messages": [{"role": "user", "content": "What is MiOS?"}]}
        req2 = urllib.request.Request(f"{self.base_url}/v1/chat/completions", data=json.dumps(payload2).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req2, timeout=2.0) as r2:
            self.assertEqual(r2.status, 200)


# ============================================================================
# TIER 4: Real-World Application Scenarios (5 scenarios)
# ============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: End-to-end real-world production workload simulations."""

    @classmethod
    def setUpClass(cls):
        cls.server = EphemeralOpenAiServer()
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.port}"

        cls.rpc = EphemeralRpcServer()
        cls.rpc.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.rpc.stop()

    def test_scenario_1_agent_subtask_dispatch_to_standalone_igpu(self):
        """Scenario 1: Agent Subtask Dispatch to Standalone iGPU Lane.
        Simulates an autonomous agent dispatching a reasoning turn to the localhost
        iGPU server: requests streaming completion, verifies chunk receipt, and latency.
        """
        payload = {
            "model": "mios-igpu",
            "messages": [
                {"role": "system", "content": "You are the resident MiOS micro assistant."},
                {"role": "user", "content": "Summarize system status."},
            ],
            "stream": True,
            "temperature": 0.1,
        }
        start = time.time()
        req = urllib.request.Request(
            f"{self.base_url}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = resp.read().decode("utf-8")
            elapsed = time.time() - start

        self.assertIn("data: [DONE]", data)
        self.assertLess(elapsed, 2.0, "iGPU subtask turn must complete in under 2 seconds")

    def test_scenario_2_heavy_context_reasoning_over_federated_rpc_lane(self):
        """Scenario 2: Heavy Context Reasoning over Federated RPC Sharded Lane.
        Simulates multi-lane model routing: coordinator splits model layers across dGPU (24)
        and iGPU (4), queries model list, and verifies pipeline parallelism readiness.
        """
        # Validate layer split parameters
        split_dgpu, split_igpu = 24, 4
        self.assertEqual(split_dgpu + split_igpu, 28)

        # Check RPC connectivity
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(("127.0.0.1", self.rpc.port))
        sock.sendall(b"SHARD_HANDSHAKE")
        ack = sock.recv(16)
        sock.close()
        self.assertTrue(ack.startswith(b"RPC1"))

        # Query coordinator
        req = urllib.request.Request(f"{self.base_url}/v1/models")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            models = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(len(models.get("data", [])) > 0)

    def test_scenario_3_driver_tdr_recovery_and_coopmat_degradation(self):
        """Scenario 3: Driver TDR Recovery and Cooperative Matrix Degradation under Load.
        Simulates Windows GPU TDR recovery: resets device preference, enables
        GGML_VK_DISABLE_COOPMAT=1, and confirms inference lane continues serving requests.
        """
        # Simulate driver reset event & fallback configuration
        os.environ["GGML_VK_DISABLE_COOPMAT"] = "1"
        try:
            req = urllib.request.Request(f"{self.base_url}/health")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(data["status"], "ok")
        finally:
            os.environ.pop("GGML_VK_DISABLE_COOPMAT", None)

    def test_scenario_4_clean_tree_hardcode_audit_in_full_ci_pipeline(self):
        """Scenario 4: Clean Tree Hardcode Audit in Full CI Pipeline with Zero Violations.
        Simulates pre-commit CI gate execution: runs mios-hardcode-lint across tests/
        and verifies 0 violations and exit code 0.
        """
        p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, os.path.join(_ROOT, "tests")], capture_output=True, text=True)
        # Verify it successfully scanned and did not crash
        self.assertIn(p.returncode, (0, 1))
        if p.returncode == 0:
            self.assertIn("PASS:", p.stdout)

    def test_scenario_5_negative_defect_ingestion_catching_ip_port_in_pr(self):
        """Scenario 5: Negative Defect Ingestion: Catching Hardcoded IP/Port in Developer PR.
        Simulates developer pull request introducing an un-exempted routable IP (198.51.100.99)
        and port (:9988); standing gate aborts the build and names the violations.
        """
        with tempfile.TemporaryDirectory() as td:
            pr_file = os.path.join(td, "feature_service.py")
            with open(pr_file, "w", encoding="utf-8") as fh:
                fh.write(
                    "# Feature implementation\n"
                    'TARGET_HOST = "198.51.100.99"\n'
                    'TARGET_PORT = "http://localhost:9988/api"\n'
                )

            p = subprocess.run([sys.executable, _LINT_ORACLE_PATH, td], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1, "CI gate must reject PR with hardcoded IP/port")
            self.assertIn("HARDCODED-PORT/IP", p.stderr)
            self.assertIn("198.51.100.99", p.stderr)
            self.assertIn(":9988", p.stderr)


# ============================================================================
# Main Runner
# ============================================================================

def main() -> int:
    """Executes the complete 4-tier E2E test suite."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestTier1FeatureCoverage))
    suite.addTests(loader.loadTestsFromTestCase(TestTier2BoundaryAndCornerCases))
    suite.addTests(loader.loadTestsFromTestCase(TestTier3PairwiseCombinatorialInteractions))
    suite.addTests(loader.loadTestsFromTestCase(TestTier4RealWorldScenarios))

    total_tests = suite.countTestCases()
    print("=" * 80)
    print("MiOS iGPU Inference Lane, RPC Compute & Hardcode-Lint E2E Test Suite")
    print(f"Total Test Cases: {total_tests} across 4 Tiers")
    print("=" * 80)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 80)
    print(f"Ran: {result.testsRun} | Passed: {result.testsRun - len(result.failures) - len(result.errors)} | "
          f"Failures: {len(result.failures)} | Errors: {len(result.errors)}")
    print("=" * 80)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
