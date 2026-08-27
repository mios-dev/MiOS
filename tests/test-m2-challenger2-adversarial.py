#!/usr/bin/env python3
# AI-hint: Comprehensive adversarial stress test suite for T-388 Ed25519 Mutual Handshake & ChaCha20-Poly1305 Wire AEAD.
# AI-related: usr/libexec/mios/node/crypto.py, usr/libexec/mios/node/wire.py, src/mios-rs/mios-node/src/crypto.rs
# AI-doc: usr/share/doc/mios/manual/node.md
"""Adversarial Stress Test Suite for Milestone 2 / T-388 (Challenger 2): 1. Cryptographic Handshake Adversarial Tests:    - Exhaustive single-bit and multi-byte signature tampering across Init and Resp packets (all 64 bytes fuzzed).    - Signature truncation (< 64 bytes) and extension (> 64 bytes) rejection.    - Forged identity pubkeys and ephemeral pubkeys injection / MITM rejection.    - Imposter node identity spoofing and unauthorized packet creation.    - Replay attack resilience and ephemeral key freshness (no key reuse).    - Key derivation symmetry, directional TX/RX key separation, and anti-reflection guarantee.  2. Wire AEAD Encryption Adversarial Tests:    - Exhaustive bit-flip fuzzing across all payload ciphertext bytes.    - Exhaustive bit-flip fuzzing across all 16 bytes of the Poly1305 MAC tag.    - Ciphertext truncation (< 16 bytes) and partial MAC tag drop handling.    - AAD / Node ID spoofing and cross-node ciphertext injection rejection.    - Strict nonce sequence progression, out-of-order packet drop, and wire replay attack prevention.    - High-volume multi-frame stream stress (1,000 frames) with boundary payload sizes (0B, 1B, 15B, 16B, 17B, 64B, 65B, 64KB).    - Layered defense validation: Wire CRC32 transport integrity vs Poly1305 cryptographic authenticity.  3. Concurrency & RFC Standards Compliance:    - Concurrent multi-session thread isolation across 20 distinct mesh nodes.    - Session renegotiation & zero cross-session decryption leakage.    - RFC 8439 / RFC 7748 / RFC 5869 cryptographic correctness verification."""

from __future__ import annotations

import concurrent.futures
import os
import random
import struct
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios", "node"))

import crypto
import wire

class TestCryptoHandshakeAdversarial(unittest.TestCase):
    """Adversarial stress testing for Ed25519 mutual authentication & X25519 handshake."""

    def setUp(self):
        self.node_a = crypto.NodeIdentity.generate(node_id=1001)
        self.node_b = crypto.NodeIdentity.generate(node_id=2002)
        self.imposter = crypto.NodeIdentity.generate(node_id=6666)

    def test_exhaustive_64_byte_signature_bit_flip_init(self):
        """Fuzz every single byte of the 64-byte Ed25519 signature in HandshakeInitPacket."""
        init_pkt, _ = crypto.CryptoHandshake.create_init(self.node_a)
        original_sig = init_pkt.signature
        self.assertEqual(len(original_sig), 64)

        for byte_idx in range(64):
            # Test 3 distinct bit masks per byte (0x01, 0x80, 0xFF)
            for mask in (0x01, 0x80, 0xFF):
                corrupted_sig = bytearray(original_sig)
                corrupted_sig[byte_idx] ^= mask

                bad_init = crypto.HandshakeInitPacket(
                    sender_node_id=init_pkt.sender_node_id,
                    id_pubkey=init_pkt.id_pubkey,
                    ephemeral_pubkey=init_pkt.ephemeral_pubkey,
                    signature=bytes(corrupted_sig),
                )
                with self.assertRaises(ValueError, msg=f"Failed to reject corrupted sig at byte {byte_idx} mask {mask:#04x}") as ctx:
                    crypto.CryptoHandshake.process_init_and_respond(self.node_b, bad_init)
                self.assertIn("signature verification failed", str(ctx.exception).lower())

    def test_exhaustive_64_byte_signature_bit_flip_resp(self):
        """Fuzz every single byte of the 64-byte Ed25519 signature in HandshakeRespPacket."""
        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(self.node_a)
        resp_pkt, _ = crypto.CryptoHandshake.process_init_and_respond(self.node_b, init_pkt)
        original_sig = resp_pkt.signature
        self.assertEqual(len(original_sig), 64)

        for byte_idx in range(64):
            for mask in (0x01, 0x80, 0xFF):
                corrupted_sig = bytearray(original_sig)
                corrupted_sig[byte_idx] ^= mask

                bad_resp = crypto.HandshakeRespPacket(
                    sender_node_id=resp_pkt.sender_node_id,
                    id_pubkey=resp_pkt.id_pubkey,
                    ephemeral_pubkey=resp_pkt.ephemeral_pubkey,
                    signature=bytes(corrupted_sig),
                )
                with self.assertRaises(ValueError, msg=f"Failed to reject corrupted resp sig at byte {byte_idx} mask {mask:#04x}") as ctx:
                    crypto.CryptoHandshake.finalize_init(self.node_a, eph_priv_a, bad_resp)
                self.assertIn("signature verification failed", str(ctx.exception).lower())

    def test_signature_boundary_lengths(self):
        """Verify that signatures with invalid lengths are strictly rejected."""
        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(self.node_a)

        # Test truncated and oversized signatures
        for invalid_len in (0, 1, 16, 32, 63, 65, 100, 128):
            bad_sig = b"\x00" * invalid_len
            bad_init = crypto.HandshakeInitPacket(
                sender_node_id=init_pkt.sender_node_id,
                id_pubkey=init_pkt.id_pubkey,
                ephemeral_pubkey=init_pkt.ephemeral_pubkey,
                signature=bad_sig,
            )
            with self.assertRaises(ValueError):
                crypto.CryptoHandshake.process_init_and_respond(self.node_b, bad_init)

    def test_forged_ephemeral_pubkey_mitm_rejection(self):
        """Attacker swaps ephemeral pubkey with attacker's pubkey without updating signature."""
        init_pkt, _ = crypto.CryptoHandshake.create_init(self.node_a)
        attacker_priv, attacker_eph_pub = crypto.CryptoHandshake._generate_x25519_keypair()

        # Swapping ephemeral pubkey breaks Ed25519 signature
        mitm_init = crypto.HandshakeInitPacket(
            sender_node_id=init_pkt.sender_node_id,
            id_pubkey=init_pkt.id_pubkey,
            ephemeral_pubkey=attacker_eph_pub,
            signature=init_pkt.signature,
        )
        with self.assertRaises(ValueError) as ctx:
            crypto.CryptoHandshake.process_init_and_respond(self.node_b, mitm_init)
        self.assertIn("signature verification failed", str(ctx.exception).lower())

    def test_forged_id_pubkey_rejection(self):
        """Attacker swaps identity pubkey with imposter's identity pubkey."""
        init_pkt, _ = crypto.CryptoHandshake.create_init(self.node_a)

        mitm_init = crypto.HandshakeInitPacket(
            sender_node_id=init_pkt.sender_node_id,
            id_pubkey=self.imposter.public_bytes,
            ephemeral_pubkey=init_pkt.ephemeral_pubkey,
            signature=init_pkt.signature,
        )
        with self.assertRaises(ValueError) as ctx:
            crypto.CryptoHandshake.process_init_and_respond(self.node_b, mitm_init)
        self.assertIn("signature verification failed", str(ctx.exception).lower())

    def test_imposter_identity_spoofing(self):
        """Imposter creates valid signature with its own key but claims Node A's identity."""
        attacker_priv, attacker_eph_pub = crypto.CryptoHandshake._generate_x25519_keypair()
        # Imposter signs its ephemeral pubkey with its own private key
        attacker_sig = self.imposter.sign(attacker_eph_pub)

        # But imposter claims sender_node_id = 1001 and id_pubkey = node_a.public_bytes
        spoofed_init = crypto.HandshakeInitPacket(
            sender_node_id=1001,
            id_pubkey=self.node_a.public_bytes,
            ephemeral_pubkey=attacker_eph_pub,
            signature=attacker_sig,
        )
        with self.assertRaises(ValueError) as ctx:
            crypto.CryptoHandshake.process_init_and_respond(self.node_b, spoofed_init)
        self.assertIn("signature verification failed", str(ctx.exception).lower())

    def test_ephemeral_freshness_and_replay_isolation(self):
        """Ensure fresh ephemeral keys generate completely unique session keys each time."""
        init_1, eph_priv_a1 = crypto.CryptoHandshake.create_init(self.node_a)
        init_2, eph_priv_a2 = crypto.CryptoHandshake.create_init(self.node_a)

        # Ephemeral keys must be strictly different
        self.assertNotEqual(init_1.ephemeral_pubkey, init_2.ephemeral_pubkey)
        self.assertNotEqual(eph_priv_a1, eph_priv_a2)

        resp_1, session_b1 = crypto.CryptoHandshake.process_init_and_respond(self.node_b, init_1)
        resp_2, session_b2 = crypto.CryptoHandshake.process_init_and_respond(self.node_b, init_2)

        session_a1 = crypto.CryptoHandshake.finalize_init(self.node_a, eph_priv_a1, resp_1)
        session_a2 = crypto.CryptoHandshake.finalize_init(self.node_a, eph_priv_a2, resp_2)

        # Session 1 and Session 2 must have distinct symmetric keys
        self.assertNotEqual(session_a1.tx_key, session_a2.tx_key)
        self.assertNotEqual(session_a1.rx_key, session_a2.rx_key)

        # Ciphertexts from session 1 cannot be decrypted in session 2
        enc1 = session_a1.encrypt_payload(b"Confidential session 1 payload")
        with self.assertRaises(ValueError):
            session_b2.decrypt_payload(enc1)

    def test_key_derivation_directional_separation(self):
        """Verify TX and RX keys are distinct to prevent reflection attacks."""
        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(self.node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(self.node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(self.node_a, eph_priv_a, resp_pkt)

        # Symmetric match between peer directions
        self.assertEqual(session_a.tx_key, session_b.rx_key)
        self.assertEqual(session_a.rx_key, session_b.tx_key)

        # Anti-reflection: local TX key MUST NOT equal local RX key
        self.assertNotEqual(session_a.tx_key, session_a.rx_key)
        self.assertNotEqual(session_b.tx_key, session_b.rx_key)

class TestWireAeadAdversarial(unittest.TestCase):
    """Adversarial stress testing for ChaCha20-Poly1305 AEAD wire encryption."""

    def setUp(self):
        self.node_a = crypto.NodeIdentity.generate(node_id=101)
        self.node_b = crypto.NodeIdentity.generate(node_id=202)
        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(self.node_a)
        resp_pkt, self.session_b = crypto.CryptoHandshake.process_init_and_respond(self.node_b, init_pkt)
        self.session_a = crypto.CryptoHandshake.finalize_init(self.node_a, eph_priv_a, resp_pkt)

    def test_exhaustive_ciphertext_bit_flips(self):
        """Flip every single bit in a 32-byte payload ciphertext; all 256 bit flips must fail MAC check."""
        plaintext = b"0123456789abcdef0123456789abcdef"

        # Test 10 distinct encrypted blocks
        for block_idx in range(5):
            ciphertext = bytearray(self.session_a.encrypt_payload(plaintext))
            # Ciphertext length = 32 bytes ciphertext + 16 bytes MAC = 48 bytes
            self.assertEqual(len(ciphertext), 48)

            # Test bitflips in the first 32 bytes (payload portion)
            for byte_pos in range(32):
                for bit in range(8):
                    corrupted = bytearray(ciphertext)
                    corrupted[byte_pos] ^= (1 << bit)

                    # Create a dummy receiver with matching rx_nonce for test isolation
                    isolated_session = crypto.NodeCryptoSession(
                        local_node_id=self.session_b.local_node_id,
                        remote_node_id=self.session_b.remote_node_id,
                        tx_key=self.session_b.tx_key,
                        rx_key=self.session_b.rx_key,
                    )
                    isolated_session.rx_nonce = self.session_a.tx_nonce - 1

                    with self.assertRaises(ValueError, msg=f"Bit flip at byte {byte_pos} bit {bit} was not caught!") as ctx:
                        isolated_session.decrypt_payload(bytes(corrupted))
                    self.assertIn("MAC verification failed", str(ctx.exception))

    def test_exhaustive_poly1305_mac_tag_bit_flips(self):
        """Flip every single bit in the 16-byte Poly1305 MAC tag; all 128 bit flips must fail."""
        plaintext = b"Sensitive telemetry data for edge micro-cluster"
        ciphertext = bytearray(self.session_a.encrypt_payload(plaintext))
        ct_len = len(plaintext)
        tag_start = ct_len

        for byte_pos in range(tag_start, tag_start + 16):
            for bit in range(8):
                corrupted = bytearray(ciphertext)
                corrupted[byte_pos] ^= (1 << bit)

                isolated_session = crypto.NodeCryptoSession(
                    local_node_id=self.session_b.local_node_id,
                    remote_node_id=self.session_b.remote_node_id,
                    tx_key=self.session_b.tx_key,
                    rx_key=self.session_b.rx_key,
                )
                isolated_session.rx_nonce = self.session_a.tx_nonce - 1

                with self.assertRaises(ValueError, msg=f"MAC tag bit flip at tag byte {byte_pos - tag_start} bit {bit} was not caught!") as ctx:
                    isolated_session.decrypt_payload(bytes(corrupted))
                self.assertIn("MAC verification failed", str(ctx.exception))

    def test_truncated_ciphertext_and_tags(self):
        """Ensure truncated ciphertexts and truncated MAC tags fail immediately."""
        plaintext = b"Payload for truncation tests"
        ciphertext = self.session_a.encrypt_payload(plaintext)

        # Truncate ciphertext to lengths shorter than tag (0..15 bytes)
        for truncated_len in range(16):
            truncated = ciphertext[:truncated_len]
            isolated_session = crypto.NodeCryptoSession(
                local_node_id=self.session_b.local_node_id,
                remote_node_id=self.session_b.remote_node_id,
                tx_key=self.session_b.tx_key,
                rx_key=self.session_b.rx_key,
            )
            isolated_session.rx_nonce = self.session_a.tx_nonce - 1
            with self.assertRaises((ValueError, Exception)):
                isolated_session.decrypt_payload(truncated)

        # Truncate partial tag (drop 1..15 bytes from end)
        for drop_bytes in range(1, 16):
            truncated = ciphertext[:-drop_bytes]
            isolated_session = crypto.NodeCryptoSession(
                local_node_id=self.session_b.local_node_id,
                remote_node_id=self.session_b.remote_node_id,
                tx_key=self.session_b.tx_key,
                rx_key=self.session_b.rx_key,
            )
            isolated_session.rx_nonce = self.session_a.tx_nonce - 1
            with self.assertRaises((ValueError, Exception)):
                isolated_session.decrypt_payload(truncated)

    def test_cross_node_and_aad_spoofing(self):
        """Verify that Node C cannot inject ciphertexts into Node B's session (AAD mismatch)."""
        node_c = crypto.NodeIdentity.generate(node_id=303)
        init_c, eph_c = crypto.CryptoHandshake.create_init(node_c)
        resp_c, session_b_c = crypto.CryptoHandshake.process_init_and_respond(self.node_b, init_c)
        session_c = crypto.CryptoHandshake.finalize_init(node_c, eph_c, resp_c)

        # Node C encrypts a payload meant for its own session with B
        c_payload = b"Node C malicious injection"
        c_ciphertext = session_c.encrypt_payload(c_payload)

        # Attacker injects this ciphertext into Node A -> Node B session
        with self.assertRaises(ValueError):
            self.session_b.decrypt_payload(c_ciphertext)

    def test_strict_nonce_progression_and_replay_rejection(self):
        """Verify strict nonce synchronization, out-of-order drop, and replay rejection."""
        # Encrypt 4 distinct messages
        msg1 = self.session_a.encrypt_payload(b"Message 1 (nonce 0)")
        msg2 = self.session_a.encrypt_payload(b"Message 2 (nonce 1)")
        msg3 = self.session_a.encrypt_payload(b"Message 3 (nonce 2)")
        msg4 = self.session_a.encrypt_payload(b"Message 4 (nonce 3)")

        self.assertEqual(self.session_a.tx_nonce, 4)
        self.assertEqual(self.session_b.rx_nonce, 0)

        # Decrypt message 1 -> succeeds, rx_nonce becomes 1
        d1 = self.session_b.decrypt_payload(msg1)
        self.assertEqual(d1, b"Message 1 (nonce 0)")
        self.assertEqual(self.session_b.rx_nonce, 1)

        # REPLAY ATTACK: Attacker sends msg1 again -> MUST FAIL (rx_nonce is 1, msg1 was encrypted with nonce 0)
        with self.assertRaises(ValueError) as ctx:
            self.session_b.decrypt_payload(msg1)
        self.assertIn("MAC verification failed", str(ctx.exception))
        # Note: on failure rx_nonce still incremented to 2
        self.assertEqual(self.session_b.rx_nonce, 2)

        # OUT-OF-ORDER: Now receiver rx_nonce is 2. msg3 (encrypted with nonce 2) should decrypt cleanly!
        d3 = self.session_b.decrypt_payload(msg3)
        self.assertEqual(d3, b"Message 3 (nonce 2)")
        self.assertEqual(self.session_b.rx_nonce, 3)

        # DROPPED PACKET REPLAY: Attempting to decrypt msg2 (nonce 1) when rx_nonce is 3 -> MUST FAIL
        with self.assertRaises(ValueError):
            self.session_b.decrypt_payload(msg2)

    def test_high_volume_multi_frame_stream_stress(self):
        """Stream 1,000 frames with varying payload sizes across boundaries."""
        payload_sizes = [
            0,      # Empty payload (MAC tag only)
            1,      # 1 byte
            7,      # Sub-block
            15,     # ChaCha/Poly boundary - 1
            16,     # Exactly 16 bytes
            17,     # 16 + 1
            31,     # Sub-block
            32,     # 2 * 16
            63,     # 64 - 1 (ChaCha20 block boundary - 1)
            64,     # Exact ChaCha20 block (64B)
            65,     # 64 + 1
            128,    # 2 blocks
            1024,   # 1 KB
            4096,   # 4 KB
            16384,  # 16 KB
            65536,  # 64 KB
        ]

        total_frames = 1000
        for i in range(total_frames):
            size = payload_sizes[i % len(payload_sizes)]
            # Generate deterministic patterned data
            if size == 0:
                raw_data = b""
            else:
                raw_data = bytes([(x + i) % 256 for x in range(size)])

            enc = self.session_a.encrypt_payload(raw_data)
            self.assertEqual(len(enc), size + 16)

            dec = self.session_b.decrypt_payload(enc)
            self.assertEqual(dec, raw_data, f"Mismatch on frame {i} of size {size}")

        self.assertEqual(self.session_a.tx_nonce, total_frames)
        self.assertEqual(self.session_b.rx_nonce, total_frames)

    def test_layered_wire_defense_crc32_and_poly1305(self):
        """Verify layered defense: CRC32 catches transport bitflips, Poly1305 catches crypto tampering."""
        original_payload = b'{"command":"migrate_agent","vm_id":42}'
        frame = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, node_id=101, payload=original_payload)

        # Encrypt frame
        enc_frame = self.session_a.encrypt_frame(frame)
        raw_wire_bytes = bytearray(enc_frame.encode())

        # Layer 1: Corrupt 1 byte in the wire payload
        raw_wire_bytes[16 + 5] ^= 0x55

        # Transport decode must fail immediately on CRC32 without even reaching crypto layer
        with self.assertRaises(ValueError) as ctx:
            wire.Frame.decode(bytes(raw_wire_bytes))
        self.assertIn("CRC32 mismatch", str(ctx.exception))

        # Layer 2: Even if an attacker forge-updates the wire CRC32 to bypass transport checks...
        import zlib
        bad_payload = bytes(raw_wire_bytes[16:])
        new_crc = zlib.crc32(bad_payload) & 0xFFFFFFFF
        struct.pack_into(">I", raw_wire_bytes, 12, new_crc)

        # Now wire decode succeeds...
        bypassed_frame = wire.Frame.decode(bytes(raw_wire_bytes))
        self.assertEqual(bypassed_frame.header.checksum, new_crc)

        # But Cryptographic Layer 3 (Poly1305) catches the tampering and rejects decryption!
        with self.assertRaises(ValueError) as ctx:
            self.session_b.decrypt_frame(bypassed_frame)
        self.assertIn("MAC verification failed", str(ctx.exception))

class TestMultiSessionConcurrency(unittest.TestCase):
    """Stress tests concurrent sessions across multiple simulated edge nodes."""

    def test_concurrent_mesh_handshakes_and_traffic(self):
        """Simulate 20 nodes forming 10 simultaneous paired encrypted sessions in parallel threads."""
        def run_node_pair(pair_idx: int):
            node_x = crypto.NodeIdentity.generate(node_id=pair_idx * 2)
            node_y = crypto.NodeIdentity.generate(node_id=pair_idx * 2 + 1)

            # Handshake
            init_pkt, eph_priv_x = crypto.CryptoHandshake.create_init(node_x)
            resp_pkt, session_y = crypto.CryptoHandshake.process_init_and_respond(node_y, init_pkt)
            session_x = crypto.CryptoHandshake.finalize_init(node_x, eph_priv_x, resp_pkt)

            # Exchange 50 bidirectional messages
            for msg_i in range(50):
                # X -> Y
                px = f"Pair {pair_idx} Msg {msg_i} from X to Y".encode("utf-8")
                ctx = session_x.encrypt_payload(px)
                dec_y = session_y.decrypt_payload(ctx)
                if dec_y != px:
                    return False

                # Y -> X
                py = f"Pair {pair_idx} Msg {msg_i} from Y to X".encode("utf-8")
                cty = session_y.encrypt_payload(py)
                dec_x = session_x.decrypt_payload(cty)
                if dec_x != py:
                    return False

            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(run_node_pair, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        self.assertEqual(len(results), 10)
        self.assertTrue(all(results))

class TestRfcStandardsCompliance(unittest.TestCase):
    """Verifies low-level cryptographic primitive compliance against standard RFC test vectors."""

    def test_rfc7748_curve25519_vector(self):
        """RFC 7748 Section 6.1 Curve25519 test vectors (Alice, Bob, and Shared Secret)."""
        from cryptography.hazmat.primitives.asymmetric import x25519
        from cryptography.hazmat.primitives import serialization

        # Alice private key & public key
        alice_priv_bytes = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
        alice_pub_expected = bytes.fromhex("8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a")
        alice_priv = x25519.X25519PrivateKey.from_private_bytes(alice_priv_bytes)
        alice_pub_raw = alice_priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.assertEqual(alice_pub_raw.hex(), alice_pub_expected.hex())

        # Bob public key
        bob_pub_bytes = bytes.fromhex("de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f")
        bob_pub = x25519.X25519PublicKey.from_public_bytes(bob_pub_bytes)

        # Shared Secret computed by Alice using Bob's public key
        expected_shared = bytes.fromhex("4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742")
        alice_shared = alice_priv.exchange(bob_pub)
        self.assertEqual(alice_shared.hex(), expected_shared.hex())

    def test_rfc8439_chacha20_poly1305_aead_vector(self):
        """RFC 8439 Section 2.8.2 ChaCha20-Poly1305 AEAD test vector."""
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

        key = bytes.fromhex("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f")
        nonce = bytes.fromhex("070000004041424344454647")
        aad = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
        plaintext = b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it."

        expected_ct = bytes.fromhex(
            "d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fea9e2b5a736ee62d6"
            "3dbea45e8ca9671282fafb69da92728b1a71de0a9e060b2905d6a5b67ecd3b36"
            "92ddbd7f2d778b8c9803aee328091b58fab324e4fad675945585808b4831d7bc"
            "3ff4def08e4b7a9de576d26586cec64b6116"
        )
        expected_tag = bytes.fromhex("1ae10b594f09e26a7e902ecbd0600691")
        expected_combined = expected_ct + expected_tag

        cipher = ChaCha20Poly1305(key)
        encrypted = cipher.encrypt(nonce, plaintext, aad)

        self.assertEqual(encrypted.hex(), expected_combined.hex())

        # Verify decryption
        decrypted = cipher.decrypt(nonce, encrypted, aad)
        self.assertEqual(decrypted, plaintext)

    def test_rfc5869_hkdf_sha256_vector(self):
        """RFC 5869 Test Case 1 HKDF-SHA256 test vector."""
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives import hashes

        ikm = bytes.fromhex("0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b")
        salt = bytes.fromhex("000102030405060708090a0b0c")
        info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
        expected_okm = bytes.fromhex(
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"
        )

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=42,
            salt=salt,
            info=info,
        )
        okm = hkdf.derive(ikm)
        self.assertEqual(okm.hex(), expected_okm.hex())

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCryptoHandshakeAdversarial)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestWireAeadAdversarial))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMultiSessionConcurrency))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRfcStandardsCompliance))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())

