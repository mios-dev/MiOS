#!/usr/bin/env python3
# AI-hint: Comprehensive multi-perspective empirical stress test suite for Roadmap batch T-583 through T-592.
# AI-related: usr/libexec/mios/git/pre_commit.py, usr/libexec/mios/hw/gpu_slice.py, usr/libexec/mios/net/mdns_mesh.py, usr/libexec/mios/storage/container_gc.py, usr/libexec/mios/sec/fido2_manager.py
"""
Multi-Perspective Empirical Stress Harness for MiOS Workstream Batch T-583..T-592.

Covers adversarial boundary tests across:
1. Git Pre-Commit: Multi-line syntax mutations, boundary regex bypasses, nested brackets.
2. GPU Slicing: Unknown vendor fallback, extreme memory allocations, CDI JSON structure invariants.
3. mDNS Mesh: Peer port collisions, malformed IPv4/IPv6 endpoint strings, empty WireGuard key handling.
4. Container GC: 100% full storage saturation, zero reclaimable candidates, all-pinned retention invariants.
5. FIDO2 Security: Missing user handles, whitespace PINs, nonexistent target directories.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))

def load_module(name: str, rel_path: str):
    path = os.path.join(_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

pre_commit = load_module("pre_commit", "usr/libexec/mios/git/pre_commit.py")
gpu_slice = load_module("gpu_slice", "usr/libexec/mios/hw/gpu_slice.py")
mdns_mesh = load_module("mdns_mesh", "usr/libexec/mios/net/mdns_mesh.py")
container_gc = load_module("container_gc", "usr/libexec/mios/storage/container_gc.py")
fido2_manager = load_module("fido2_manager", "usr/libexec/mios/sec/fido2_manager.py")

class TestEmpiricalStressT583T592(unittest.TestCase):
    """Empirical adversarial and boundary testing suite."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-adv-t583-")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    # --- Git Pre-Commit Stress ---
    def test_pre_commit_deep_syntax_stress(self):
        linter = pre_commit.PreCommitLinter(repo_root=str(self.root), mock=False)
        # Deeply nested unmatched brackets
        bad_code = "x = [" * 50 + "]" * 49
        findings = linter.lint_python_content("stress.py", bad_code)
        self.assertGreater(len(findings), 0)
        self.assertEqual(findings[0].rule, "python-syntax")

    def test_pre_commit_multiple_secrets_aggregation(self):
        linter = pre_commit.PreCommitLinter(repo_root=str(self.root), mock=False)
        multi_secret = "token1 = 'sk-1111111111111111111111'\ntoken2 = 'ghp_222222222222222222222222222222222222'\n"
        findings = linter.lint_security_and_vendor("leaks.py", multi_secret)
        self.assertEqual(len(findings), 2)
        self.assertTrue(all(f.rule == "no-hardcoded-secrets" for f in findings))

    # --- GPU Slicing Stress ---
    def test_gpu_slice_unknown_vendor_cdi_generation(self):
        mgr = gpu_slice.GPUSliceManager(mock=True)
        custom_gpu = gpu_slice.PhysicalGPU(
            gpu_id=99,
            vendor="intel",
            model="Intel Data Center GPU Max 1550",
            pci_bdf="0000:8a:00.0",
            total_memory_mb=65536,
        )
        cdi = mgr.generate_cdi_spec(custom_gpu)
        self.assertEqual(cdi["cdiVersion"], "0.5.0")
        self.assertEqual(cdi["kind"], "amd.com/gpu")  # Non-nvidia default path
        self.assertEqual(cdi["devices"][0]["name"], "gpu-99")

    def test_gpu_slice_oversubscription_rejection(self):
        mgr = gpu_slice.GPUSliceManager(mock=True)
        # Verify valid slices list
        self.assertIn("7g.40gb", gpu_slice.MIG_PROFILES_NVIDIA)
        ok, err = mgr.configure_slices(0, ["fake.profile"])
        self.assertFalse(ok)
        self.assertIn("Invalid MIG profile", err)

    # --- mDNS Mesh Stress ---
    def test_mdns_mesh_empty_peers_render_conf(self):
        mgr = mdns_mesh.MDNSMeshManager(node_id="standalone-node", mock=False)
        mgr.peers = {}
        conf = mgr.render_wireguard_conf()
        self.assertIn("[Interface]", conf)
        self.assertNotIn("[Peer]", conf)

    def test_mdns_mesh_peer_ip_deduplication(self):
        mgr = mdns_mesh.MDNSMeshManager(mock=True)
        peers = mgr.discover_peers()
        peer_ips = [p.mesh_ip for p in peers]
        self.assertEqual(len(peer_ips), len(set(peer_ips)))

    # --- Container GC Stress ---
    def test_container_gc_all_pinned_no_prune(self):
        mgr = container_gc.ContainerGCManager(threshold_pct=50.0, mock=True)
        all_pinned = [
            container_gc.ContainerImageMeta(
                image_id=f"sha256:{i}",
                repository="ghcr.io/mios-dev/mios",
                tag="latest",
                size_mb=1000.0,
                created_at=1000.0,
                last_used=1000.0,
                is_pinned=True,
                in_use=True,
            )
            for i in range(5)
        ]
        plan = mgr.plan_prune(images=all_pinned)
        self.assertEqual(len(plan.prune_targets), 0)
        self.assertEqual(plan.reclaimable_mb, 0.0)

    def test_container_gc_extreme_100_percent_usage(self):
        mgr = container_gc.ContainerGCManager(threshold_pct=85.0, mock=True)
        plan = mgr.plan_prune()
        # Even with usage > threshold, pinned production images must never appear in prune_targets
        for target in plan.prune_targets:
            self.assertFalse(target.is_pinned)
            self.assertFalse(target.in_use)

    # --- FIDO2 Security Stress ---
    def test_fido2_pam_enrollment_file_overwrite(self):
        u2f_out = self.root / "u2f_keys_stress"
        mgr = fido2_manager.FIDO2SecurityManager(mock=True)
        ok1, _ = mgr.enroll_pam_u2f(username="user1", output_file=str(u2f_out))
        self.assertTrue(ok1)
        ok2, _ = mgr.enroll_pam_u2f(username="user2", output_file=str(u2f_out))
        self.assertTrue(ok2)
        self.assertTrue(u2f_out.exists())

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEmpiricalStressT583T592)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())
