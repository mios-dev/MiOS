#!/usr/bin/env python3
# AI-hint: Comprehensive adversarial test suite authored by Challenger 2 for T-377..T-381.
# AI-related: usr/libexec/mios/mcp/sandbox.py, usr/libexec/mios/sec/approval.py, usr/libexec/mios/graph/traversal.py, usr/libexec/mios/prompt/pruning.py, usr/libexec/mios/a2a/attestation.py
"""
MiOS Empirical Adversarial Test Harness (Challenger 2).

Executes stress-testing, boundary attacks, cyclic recursion tests, cryptographic
malleability checks, AST preservation tests, and fuzzing payloads against:
- MCP Bubblewrap Sandbox Engine (T-377 / MCP-01)
- Interactive HITL Permission Escalation & Approval Engine (T-378 / SEC-06)
- Recursive CTE Knowledge Graph Traversal Engine (T-379 / GRAPH-01)
- Contextual Prompt Compression & Token Pruning Engine (T-380 / PROMPT-01)
- A2A Cryptographic Capability Attestation Engine (T-381 / A2A-01)
"""

from __future__ import annotations

import base64
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import secrets
import sys
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional

_HERE = os.path.abspath(os.path.dirname(__file__)) if "__file__" in globals() else os.path.abspath(".")
_ROOT = os.path.normpath(os.path.join(_HERE, "..")) if os.path.basename(_HERE) == "tests" else _HERE


def load_module(name: str, rel_path: str) -> Any:
    full_path = os.path.join(_ROOT, rel_path)
    spec = importlib.util.spec_from_file_location(name, full_path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    loader = importlib.machinery.SourceFileLoader(name, full_path)
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios"))
sys.path.insert(0, os.path.join(_ROOT, "lib", "mios"))

mcp_mod = load_module("mcp_sandbox", "usr/libexec/mios/mcp/sandbox.py")
approval_mod = load_module("hitl_approval", "usr/libexec/mios/sec/approval.py")
graph_mod = load_module("graph_traversal", "usr/libexec/mios/graph/traversal.py")
prompt_mod = load_module("prompt_pruning", "usr/libexec/mios/prompt/pruning.py")
a2a_mod = load_module("a2a_attestation", "usr/libexec/mios/a2a/attestation.py")


class TestAdversarialMcpSandbox(unittest.TestCase):
    """Adversarial testing on McpSandbox path traversal, argument injection, and policy isolation."""

    def test_path_traversal_and_disallowed_roots(self) -> None:
        sb = mcp_mod.McpSandbox(server_name="test-adversary")

        # Disallowed system root paths must raise ValueError
        disallowed_paths = [
            "/etc",
            "/etc/shadow",
            "/etc/../etc/passwd",
            "/usr",
            "/usr/bin/../../etc",
            "/boot",
            "/boot/efi",
            "/sys",
            "/sys/kernel",
            "/root",
            "/root/.ssh/id_rsa",
            "/bin",
            "/sbin",
            "/lib",
            "/lib64",
            "/dev",
            "/dev/sda",
            "/proc",
            "/proc/sys/net",
            "C:\\etc\\shadow",
            "C:/usr/local/bin",
            "C:\\boot\\grub2",
        ]

        for path in disallowed_paths:
            with self.assertRaises(ValueError, msg=f"Path {path!r} should be disallowed for writable mounting"):
                sb.validate_rw_path(path)

            with self.assertRaises(ValueError, msg=f"add_rw_bind should fail for path {path!r}"):
                sb.add_rw_bind(path)

            with self.assertRaises(ValueError, msg=f"set_workspace_dir should fail for path {path!r}"):
                sb.set_workspace_dir(path)

    def test_allowed_custom_and_workspace_paths(self) -> None:
        sb = mcp_mod.McpSandbox(server_name="test-allowed")

        allowed_paths = [
            "/var/lib/mios/workspace",
            "/var/tmp/mcp-test",
            "/tmp/custom_scratch",
            "/home/mios/project",
            "/opt/app/data",
        ]

        for path in allowed_paths:
            norm = sb.validate_rw_path(path)
            self.assertTrue(norm.startswith("/"))

        sb.add_rw_bind("/var/data", "/var/data")
        sb.add_ro_bind("/opt/models", "/opt/models")
        sb.set_workspace_dir("/var/tmp/mcp-test")

        cmd = sb.build_command(["python3", "server.py"])
        self.assertIn("--bind", cmd)
        self.assertIn("/var/data", cmd)
        self.assertIn("--ro-bind", cmd)
        self.assertIn("/opt/models", cmd)
        self.assertIn("--chdir", cmd)
        self.assertIn("/var/tmp/mcp-test", cmd)

    def test_network_isolation_and_flag_integrity(self) -> None:
        # Default: network unshared
        sb_isolated = mcp_mod.McpSandbox(server_name="isolated", allow_net=False)
        cmd_iso = sb_isolated.build_command(["ls"])
        self.assertIn("--unshare-net", cmd_iso)
        self.assertNotIn("--share-net", cmd_iso)
        self.assertIn("--die-with-parent", cmd_iso)
        self.assertIn("--new-session", cmd_iso)
        self.assertIn("--unshare-all", cmd_iso)

        # Allow network
        sb_net = mcp_mod.McpSandbox(server_name="networked", allow_net=True)
        cmd_net = sb_net.build_command(["ls"])
        self.assertIn("--share-net", cmd_net)
        self.assertNotIn("--unshare-net", cmd_net)

    def test_invalid_parameters_and_injection_payloads(self) -> None:
        # Empty server name
        with self.assertRaises(ValueError):
            mcp_mod.McpSandbox(server_name="")
        with self.assertRaises(ValueError):
            mcp_mod.McpSandbox(server_name="   ")

        sb = mcp_mod.McpSandbox(server_name="test")
        # Empty inner command
        with self.assertRaises(ValueError):
            sb.build_command([])

        # Empty src for ro_bind
        with self.assertRaises(ValueError):
            sb.add_ro_bind("")

        # Empty workspace_dir
        with self.assertRaises(ValueError):
            sb.set_workspace_dir("")

        # Invalid tuple types in constructor
        with self.assertRaises(TypeError):
            mcp_mod.McpSandbox(server_name="test", custom_ro_binds=[123])  # type: ignore

        # Command with malicious argument payloads
        malicious_cmd = ["bash", "-c", "rm -rf /", "; reboot", "$(cat /etc/shadow)"]
        cmd = sb.build_command(malicious_cmd)
        # Verify arguments are appended at the end intact without shell interpretation
        self.assertEqual(cmd[-5:], malicious_cmd)


class TestAdversarialHITLApproval(unittest.TestCase):
    """Adversarial testing on HITL ApprovalEngine cryptographic token integrity, state transitions, and patterns."""

    def test_cryptographic_token_forgery_attacks(self) -> None:
        engine = approval_mod.ApprovalEngine(secret_key=b"A" * 32, ttl_seconds=120)
        req = engine.create_request(tool_name="bash_exec", command="rm -rf /var/cache/temp")
        valid_token = engine.approve(req.request_id, operator="admin")

        # 1. Authentic token validates
        self.assertTrue(engine.validate_token(req.request_id, valid_token))

        # 2. Token replay on wrong request_id
        req2 = engine.create_request(tool_name="bash_exec", command="rm -rf /var/cache/temp")
        self.assertFalse(engine.validate_token(req2.request_id, valid_token))

        # 3. Token replay on modified command (command injection after approval)
        req_tampered_cmd = approval_mod.ApprovalRequest(
            request_id=req.request_id,
            tool_name="bash_exec",
            command="rm -rf /",  # Attacker modified command
            status=approval_mod.Status.APPROVED,
            token=valid_token,
            ttl_seconds=120,
        )
        engine._requests[req.request_id] = req_tampered_cmd
        self.assertFalse(engine.validate_token(req.request_id, valid_token))

        # 4. Bit-flip attack in token signature
        raw_b64 = valid_token + "=" * (-len(valid_token) % 4)
        raw_bytes = bytearray(base64.urlsafe_b64decode(raw_b64))
        raw_bytes[-1] ^= 0x01  # Flip one bit in signature
        forged_token = base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")
        self.assertFalse(engine.validate_token(req.request_id, forged_token))

        # 5. Token generated with different secret key
        rogue_engine = approval_mod.ApprovalEngine(secret_key=b"B" * 32, ttl_seconds=120)
        rogue_token = rogue_engine._generate_token(req.request_id, "admin", time.time(), "rm -rf /var/cache/temp")
        self.assertFalse(engine.validate_token(req.request_id, rogue_token))

        # 6. Truncated / malformed tokens
        self.assertFalse(engine.validate_token(req.request_id, ""))
        self.assertFalse(engine.validate_token(req.request_id, "invalid_token_string"))
        self.assertFalse(engine.validate_token(req.request_id, valid_token[:10]))

    def test_state_machine_and_expiration_transitions(self) -> None:
        engine = approval_mod.ApprovalEngine(ttl_seconds=10)
        req = engine.create_request(tool_name="bash", command="wipefs -a /dev/sdb")

        # Initial state: PENDING
        self.assertEqual(req.status, approval_mod.Status.PENDING)
        self.assertFalse(engine.is_executable(req.request_id))

        # Reject request
        self.assertTrue(engine.reject(req.request_id, reason="Denied by policy"))
        self.assertEqual(req.status, approval_mod.Status.REJECTED)
        self.assertFalse(engine.is_executable(req.request_id))

        # Cannot approve rejected request
        with self.assertRaises(ValueError):
            engine.approve(req.request_id)

        # Create fresh request and approve
        req2 = engine.create_request(tool_name="bash", command="wipefs -a /dev/sdb")
        tok2 = engine.approve(req2.request_id)
        self.assertEqual(req2.status, approval_mod.Status.APPROVED)
        self.assertTrue(engine.is_executable(req2.request_id))
        self.assertTrue(engine.validate_token(req2.request_id, tok2))

        # Cannot approve already approved request a second time
        with self.assertRaises(ValueError):
            engine.approve(req2.request_id)

        # Cannot reject already approved request
        self.assertFalse(engine.reject(req2.request_id))

        # Simulate expiration
        req2.expires_at = time.time() - 10
        self.assertTrue(req2.is_expired())
        self.assertFalse(engine.is_executable(req2.request_id))
        self.assertFalse(engine.validate_token(req2.request_id, tok2))

        # Purge expired requests
        purged = engine.purge_expired()
        self.assertGreaterEqual(purged, 1)
        self.assertIsNone(engine.get_request(req2.request_id))

    def test_high_risk_pattern_detection_fuzzing(self) -> None:
        engine = approval_mod.ApprovalEngine()

        high_risk_samples = [
            "rm -rf /",
            "rm -fr /home/user",
            "rm -r /var/log",
            "rm --recursive --force /tmp/test",
            "mkfs.ext4 /dev/nvme0n1p1",
            "mkfs.xfs /dev/sda",
            "fdisk /dev/sdb",
            "gdisk /dev/sdc",
            "parted /dev/sdd mklabel gpt",
            "sfdisk /dev/sde",
            "wipefs -a /dev/sdf",
            "dd if=/dev/zero of=/dev/sda bs=1M",
            "dd if=/dev/urandom of=/dev/nvme0n1",
            "bootc switch quay.io/repo/img:tag",
            "bootc rollback",
            "bootc edit",
            "cryptsetup luksFormat /dev/loop0",
            "cryptsetup luksErase /dev/loop0",
            "iptables -F",
            "iptables --flush",
            "ip6tables -X",
            "nft flush ruleset",
            "nft delete table inet filter",
            "lvremove -f /dev/vg0/lv0",
            "vgremove vg0",
            "pvremove /dev/sdb1",
            "btrfs subvolume delete /mnt/subvol",
            "zpool destroy tank",
            "zfs destroy -r pool/dataset",
            "reboot",
            "shutdown -h now",
            "poweroff",
            "halt",
            "init 0",
            "init 6",
        ]

        for cmd in high_risk_samples:
            self.assertTrue(engine.requires_approval(cmd), msg=f"Command {cmd!r} must require approval")

        safe_samples = [
            "ls -la /etc",
            "cat /etc/os-release",
            "grep -rn 'TODO' .",
            "python3 -m unittest",
            "git status",
            "git log -n 5",
            "podman ps -a",
            "systemctl status mios-llm-light",
            "echo 'hello world'",
            "find . -name '*.py'",
        ]

        for cmd in safe_samples:
            self.assertFalse(engine.requires_approval(cmd), msg=f"Command {cmd!r} should be safe")


class TestAdversarialKnowledgeGraph(unittest.TestCase):
    """Adversarial testing on KnowledgeGraph cyclic graphs, depth bounds, SQL injection, and CTE generation."""

    def setUp(self) -> None:
        self.kg = graph_mod.KnowledgeGraph(db_path=":memory:")

    def tearDown(self) -> None:
        self.kg.close()

    def test_cyclic_graph_termination_and_cycle_prevention(self) -> None:
        # Construct multi-node cyclic graph:
        # A -> B -> C -> A (cycle)
        # B -> D -> E -> B (sub-cycle)
        # C -> F -> G (tail)
        # A -> A (self-loop)
        triples = [
            ("A", "depends_on", "B"),
            ("B", "depends_on", "C"),
            ("C", "depends_on", "A"),  # Cycle 1
            ("B", "depends_on", "D"),
            ("D", "depends_on", "E"),
            ("E", "depends_on", "B"),  # Cycle 2
            ("C", "depends_on", "F"),
            ("F", "depends_on", "G"),
            ("A", "depends_on", "A"),  # Self loop
        ]
        self.kg.add_triples(triples)

        # 1. Traversal from A with max_depth=10 must terminate without infinite loop
        steps = self.kg.traverse(root="A", max_depth=10, direction="forward")
        self.assertIsInstance(steps, list)
        self.assertLessEqual(len(steps), 20)

        # 2. get_recursive_dependencies deduplicates reachable nodes
        deps = self.kg.get_recursive_dependencies(root="A", max_depth=10)
        self.assertIn("B", deps)
        self.assertIn("C", deps)
        self.assertIn("D", deps)
        self.assertIn("E", deps)
        self.assertIn("F", deps)
        self.assertIn("G", deps)
        # Root "A" is not in its own dependencies list
        self.assertNotIn("A", deps)
        # List elements are strictly unique
        self.assertEqual(len(deps), len(set(deps)))

    def test_depth_ceiling_boundaries(self) -> None:
        # Linear chain: N0 -> N1 -> N2 -> ... -> N20
        chain = [(f"N_{i}", "links", f"N_{i+1}") for i in range(20)]
        self.kg.add_triples(chain)

        # Depth = 1
        deps_1 = self.kg.get_recursive_dependencies(root="N_0", max_depth=1)
        self.assertEqual(deps_1, ["N_1"])

        # Depth = 3
        deps_3 = self.kg.get_recursive_dependencies(root="N_0", max_depth=3)
        self.assertEqual(deps_3, ["N_1", "N_2", "N_3"])

        # Depth = 5
        deps_5 = self.kg.get_recursive_dependencies(root="N_0", max_depth=5)
        self.assertEqual(deps_5, ["N_1", "N_2", "N_3", "N_4", "N_5"])

    def test_reverse_backward_traversal(self) -> None:
        triples = [
            ("app", "requires", "db"),
            ("db", "requires", "storage"),
            ("storage", "requires", "disk"),
        ]
        self.kg.add_triples(triples)

        # Reverse traversal from disk
        steps = self.kg.traverse(root="disk", max_depth=5, direction="backward")
        self.assertTrue(any(s["subject"] == "storage" for s in steps))
        self.assertTrue(any(s["subject"] == "db" for s in steps))
        self.assertTrue(any(s["subject"] == "app" for s in steps))

    def test_sql_injection_payloads_and_unicode_safety(self) -> None:
        malicious_triples = [
            ("node' OR '1'='1", "predicate\"; DROP TABLE knowledge_graph; --", "target'--"),
            ("MiOS_🚀_AI", "speaks", "日本語_Prompt_🤖"),
            ("<xml>test & 'quote'</xml>", "relates_to", '{"json": "value"}'),
        ]

        props = {"key'": "val\"ue", "nested": {"count": 100}}
        emb = [0.1, -0.2, 0.5, 0.999]

        for s, p, o in malicious_triples:
            row_id = self.kg.add_triple(s, p, o, properties=props, embedding=emb)
            self.assertGreater(row_id, 0)

        # Verify table integrity (not dropped by SQL injection attempt)
        deps = self.kg.get_dependencies("node' OR '1'='1")
        self.assertEqual(deps, ["target'--"])

        # Check export
        exported = self.kg.export_graph()
        self.assertEqual(exported["count"], 3)
        self.assertIn("MiOS_🚀_AI", exported["nodes"])

    def test_recursive_cte_sql_generation(self) -> None:
        pg_sql = self.kg.generate_recursive_cte_sql(root="agent_pipe", max_depth=4, dialect="postgres")
        self.assertIn("WITH RECURSIVE graph_walk AS", pg_sql)
        self.assertIn("ARRAY[subject, object]", pg_sql)
        self.assertIn("NOT (kg.object = ANY(gw.path))", pg_sql)

        sqlite_sql = self.kg.generate_recursive_cte_sql(root="agent_pipe", max_depth=4, dialect="sqlite")
        self.assertIn("WITH RECURSIVE graph_walk", sqlite_sql)
        self.assertIn("instr(gw.path, ',' || kg.object || ',') = 0", sqlite_sql)


class TestAdversarialPromptPruning(unittest.TestCase):
    """Adversarial testing on PromptPruner AST/code preservation, multilingual support, and edge cases."""

    def setUp(self) -> None:
        self.pruner = prompt_mod.PromptPruner()

    def test_code_block_keyword_and_ast_preservation(self) -> None:
        # Code containing identical text to boilerplate phrases
        code_sample = '''```python
def please_note_that():
    """In order to test AST preservation."""
    let_me_know = True
    if due_to_the_fact_that:
        # Please be advised that code comments must be preserved
        return "Hope this helps!"
    return "Cheers,"
```'''

        input_text = f"""Please note that here is the code:
{code_sample}
I hope this helps you out! Feel free to ask if you have any questions."""

        compressed, stats = self.pruner.compress(input_text, target_ratio=0.25, preserve_code=True)

        # Code block MUST be preserved character-for-character
        self.assertIn(code_sample, compressed)
        # Conversational outer boilerplate must be stripped
        self.assertNotIn("Feel free to ask", compressed)
        self.assertNotIn("I hope this helps", compressed)
        self.assertGreater(stats["reduction_ratio"], 0.10)

    def test_inline_code_preservation(self) -> None:
        input_text = "In order to run the tool, please note that you must execute `rm -rf in order to clean`."
        compressed, _ = self.pruner.compress(input_text, target_ratio=0.25, preserve_code=True)
        self.assertIn("`rm -rf in order to clean`", compressed)
        self.assertTrue(compressed.startswith("To run the tool"))

    def test_multilingual_unicode_and_emojis(self) -> None:
        multilingual_text = "Please note that MiOS 🚀 是一个 self-replicating agentic AI 操作系统。In order to build it, use `mios build`."
        compressed, stats = self.pruner.compress(multilingual_text, target_ratio=0.20, preserve_code=True)

        self.assertIn("MiOS 🚀 是一个 self-replicating agentic AI 操作系统。", compressed)
        self.assertIn("`mios build`", compressed)
        self.assertGreaterEqual(stats["reduction_ratio"], 0.0)

    def test_extreme_inputs_and_fuzzing(self) -> None:
        # Empty string
        c_empty, s_empty = self.pruner.compress("")
        self.assertEqual(c_empty, "")
        self.assertEqual(s_empty["reduction_ratio"], 0.0)

        # Whitespace-only string returns as-is with 0 reduction ratio
        ws_input = "   \n\n\t   \n  "
        c_ws, s_ws = self.pruner.compress(ws_input)
        self.assertEqual(c_ws, ws_input)
        self.assertEqual(s_ws["reduction_ratio"], 0.0)

        # Massive text (50,000 chars)
        repeated = "Please note that in order to verify system state, it is critically necessary to check status.\n" * 500
        c_huge, s_huge = self.pruner.compress(repeated, target_ratio=0.30)
        self.assertGreater(s_huge["reduction_ratio"], 0.20)
        self.assertLess(len(c_huge), len(repeated))

    def test_chat_messages_array_pruning(self) -> None:
        messages = [
            {"role": "system", "content": "Please note that you must follow Architectural Laws."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "In order to deploy the container, what is the command?"},
                    {"type": "image_url", "image_url": {"url": "http://example.com/img.png"}},
                ],
            },
        ]

        pruned_msgs, stats = self.pruner.prune_messages(messages, target_ratio=0.25)
        self.assertEqual(len(pruned_msgs), 2)
        self.assertIn("You must follow Architectural Laws.", pruned_msgs[0]["content"])
        self.assertEqual(pruned_msgs[1]["content"][1]["type"], "image_url")
        self.assertGreater(stats["reduction_ratio"], 0.10)


class TestAdversarialA2AAttestation(unittest.TestCase):
    """Adversarial testing on A2AAuthenticator Ed25519 signatures, clock skew, tampering, and negotiation."""

    def test_ed25519_signature_tampering_attacks(self) -> None:
        auth = a2a_mod.A2AAuthenticator.generate_keypair(node_id=101)
        card = auth.create_card(
            agent_name="node-101-agent",
            capabilities=["chat", "inference", "storage"],
            ttl_seconds=3600,
        )

        # 1. Valid card verifies
        self.assertTrue(a2a_mod.verify_card(card, trusted_public_key=auth.public_key_hex))

        # 2. Modify capability after signing
        tampered_cap_card = dict(card)
        tampered_cap_card["capabilities"] = ["chat", "inference", "storage", "admin_root"]
        self.assertFalse(a2a_mod.verify_card(tampered_cap_card, trusted_public_key=auth.public_key_hex))

        # 3. Modify agent_name
        tampered_name_card = dict(card)
        tampered_name_card["agent_name"] = "imposter-agent"
        self.assertFalse(a2a_mod.verify_card(tampered_name_card, trusted_public_key=auth.public_key_hex))

        # 4. Modify node_id
        tampered_node_card = dict(card)
        tampered_node_card["node_id"] = 999
        self.assertFalse(a2a_mod.verify_card(tampered_node_card, trusted_public_key=auth.public_key_hex))

        # 5. Flip 1 bit in hex signature
        sig_hex = card["sig"]
        corrupted_sig = ("0" if sig_hex[0] != "0" else "1") + sig_hex[1:]
        tampered_sig_card = dict(card)
        tampered_sig_card["sig"] = corrupted_sig
        self.assertFalse(a2a_mod.verify_card(tampered_sig_card, trusted_public_key=auth.public_key_hex))

        # 6. Truncated / empty signature
        tampered_trunc_card = dict(card)
        tampered_trunc_card["sig"] = sig_hex[:32]
        self.assertFalse(a2a_mod.verify_card(tampered_trunc_card, trusted_public_key=auth.public_key_hex))

    def test_public_key_substitution_and_impersonation(self) -> None:
        auth_legit = a2a_mod.A2AAuthenticator.generate_keypair(node_id=1)
        auth_attacker = a2a_mod.A2AAuthenticator.generate_keypair(node_id=1)

        # Attacker signs a card claiming to be Node 1
        attacker_card = auth_attacker.create_card(
            agent_name="node-1-agent",
            capabilities=["admin"],
            ttl_seconds=3600,
            node_id=1,
        )

        # Verifying against legitimate node's public key MUST fail
        self.assertFalse(a2a_mod.verify_card(attacker_card, trusted_public_key=auth_legit.public_key_hex))

        # Attacker puts legit public key in card but signed with attacker private key
        forged_card = dict(attacker_card)
        forged_card["public_key"] = auth_legit.public_key_hex
        self.assertFalse(a2a_mod.verify_card(forged_card, trusted_public_key=auth_legit.public_key_hex))

    def test_clock_skew_and_timestamp_boundary_attacks(self) -> None:
        auth = a2a_mod.A2AAuthenticator.generate_keypair(node_id=2)
        now = time.time()

        # 1. Issued in the future (beyond clock skew limit)
        future_card = auth.create_card(
            agent_name="agent-fut",
            capabilities=["test"],
            issued_at=int(now + 300),  # +300s
            ttl_seconds=3600,
        )
        self.assertFalse(a2a_mod.verify_card(future_card, max_clock_skew=60, now_ts=now))

        # 2. Issued in the future (within clock skew limit)
        skew_allowed_card = auth.create_card(
            agent_name="agent-skew",
            capabilities=["test"],
            issued_at=int(now + 30),  # +30s
            ttl_seconds=3600,
        )
        self.assertTrue(a2a_mod.verify_card(skew_allowed_card, max_clock_skew=60, now_ts=now))

        # 3. Card expired
        expired_card = auth.create_card(
            agent_name="agent-exp",
            capabilities=["test"],
            issued_at=int(now - 4000),
            ttl_seconds=3600,  # expired 400s ago
        )
        self.assertFalse(a2a_mod.verify_card(expired_card, max_clock_skew=60, now_ts=now))

        # 4. Inverted timestamps (expires_at <= issued_at)
        inverted_card = auth.create_card(
            agent_name="agent-inv",
            capabilities=["test"],
            issued_at=int(now),
            ttl_seconds=-10,  # negative TTL
        )
        self.assertFalse(a2a_mod.verify_card(inverted_card, max_clock_skew=60, now_ts=now))

    def test_capability_negotiation(self) -> None:
        auth = a2a_mod.A2AAuthenticator.generate_keypair(node_id=3)
        card = auth.create_card(
            agent_name="agent-mesh",
            capabilities=["chat", "code_eval", "search"],
            ttl_seconds=3600,
        )

        # Exact match
        ok, caps = a2a_mod.negotiate_capabilities(card, ["chat", "code_eval"], trusted_key=auth.public_key_hex)
        self.assertTrue(ok)
        self.assertEqual(caps, ["chat", "code_eval"])

        # Missing required capability
        ok_fail, missing = a2a_mod.negotiate_capabilities(
            card, ["chat", "root_admin", "gpu_render"], trusted_key=auth.public_key_hex
        )
        self.assertFalse(ok_fail)
        self.assertEqual(missing, ["root_admin", "gpu_render"])

        # Tampered card negotiation
        tampered = dict(card)
        tampered["capabilities"] = ["chat", "root_admin"]
        ok_tampered, missing_tampered = a2a_mod.negotiate_capabilities(
            tampered, ["root_admin"], trusted_key=auth.public_key_hex
        )
        self.assertFalse(ok_tampered)
        self.assertEqual(missing_tampered, [])


if __name__ == "__main__":
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialMcpSandbox))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialHITLApproval))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialKnowledgeGraph))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialPromptPruning))
    suite.addTests(loader.loadTestsFromTestCase(TestAdversarialA2AAttestation))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
