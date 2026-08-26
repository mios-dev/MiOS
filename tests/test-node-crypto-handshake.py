#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-388 / AGY-1986 Ed25519 mutual handshake and ChaCha20-Poly1305 wire encryption.
# AI-doc: usr/share/doc/mios/manual/node.md
"""
Unit test suite for WS-NODE: Ed25519 node identity signing/verification, X25519 Diffie-Hellman
key exchange, HKDF-SHA256 session key derivation, ChaCha20-Poly1305 authenticated symmetric payload
encryption, MAC tag validation, tamper detection, and imposter rejection.
"""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "libexec", "mios", "node"))

import crypto
import wire


class TestNodeCryptoHandshake(unittest.TestCase):
    """Validates mutual Ed25519 authentication, X25519 ECDH, HKDF derivation, and AEAD frame encryption."""

    def test_ed25519_identity_keypair_and_signatures(self):
        id_1 = crypto.NodeIdentity.generate(node_id=101)
        self.assertEqual(id_1.node_id, 101)
        self.assertEqual(len(id_1.public_bytes), 32)
        self.assertEqual(len(id_1.private_bytes), 32)

        msg = b"Authentication challenge test payload"
        sig = id_1.sign(msg)
        self.assertEqual(len(sig), 64)

        # Valid signature verification
        self.assertTrue(crypto.NodeIdentity.verify(id_1.public_bytes, msg, sig))

    def test_ed25519_signature_tamper_rejection(self):
        id_1 = crypto.NodeIdentity.generate(node_id=101)
        msg = b"Authentic payload"
        sig = bytearray(id_1.sign(msg))

        # Corrupt 1 byte in signature
        sig[0] ^= 0xFF
        self.assertFalse(crypto.NodeIdentity.verify(id_1.public_bytes, msg, bytes(sig)))

        # Corrupt message
        self.assertFalse(crypto.NodeIdentity.verify(id_1.public_bytes, b"Forged payload", id_1.sign(msg)))

    def test_mutual_handshake_session_establishment(self):
        node_a = crypto.NodeIdentity.generate(node_id=10)
        node_b = crypto.NodeIdentity.generate(node_id=20)

        # 1. Node A creates HandshakeInit
        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        self.assertEqual(init_pkt.sender_node_id, 10)
        self.assertEqual(len(init_pkt.id_pubkey), 32)
        self.assertEqual(len(init_pkt.ephemeral_pubkey), 32)
        self.assertEqual(len(init_pkt.signature), 64)

        # 2. Node B processes HandshakeInit, derives session keys, and responds with HandshakeResp
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        self.assertEqual(resp_pkt.sender_node_id, 20)
        self.assertEqual(session_b.local_node_id, 20)
        self.assertEqual(session_b.remote_node_id, 10)

        # 3. Node A finalizes handshake using HandshakeResp
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)
        self.assertEqual(session_a.local_node_id, 10)
        self.assertEqual(session_a.remote_node_id, 20)

        # Verify key derivation symmetry: A's TX key == B's RX key, A's RX key == B's TX key
        self.assertEqual(session_a.tx_key, session_b.rx_key)
        self.assertEqual(session_a.rx_key, session_b.tx_key)

    def test_bidirectional_payload_encryption_and_decryption(self):
        node_a = crypto.NodeIdentity.generate(node_id=1)
        node_b = crypto.NodeIdentity.generate(node_id=2)

        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)

        # Message A -> B
        plain_a = b"Secure payload from node A to node B"
        enc_a = session_a.encrypt_payload(plain_a)
        self.assertNotEqual(enc_a, plain_a)
        self.assertEqual(len(enc_a), len(plain_a) + 16)  # 16-byte Poly1305 auth tag

        dec_b = session_b.decrypt_payload(enc_a)
        self.assertEqual(dec_b, plain_a)

        # Message B -> A
        plain_b = b"Secure acknowledgement from node B to node A"
        enc_b = session_b.encrypt_payload(plain_b)
        dec_a = session_a.decrypt_payload(enc_b)
        self.assertEqual(dec_a, plain_b)

    def test_payload_tamper_detection_mac_failure(self):
        node_a = crypto.NodeIdentity.generate(node_id=1)
        node_b = crypto.NodeIdentity.generate(node_id=2)

        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)

        plain = b"Critical financial or cryptographic state data"
        ciphertext = bytearray(session_a.encrypt_payload(plain))

        # Tamper with 1 byte in ciphertext body
        ciphertext[5] ^= 0x01

        with self.assertRaises(ValueError) as ctx:
            session_b.decrypt_payload(bytes(ciphertext))
        self.assertIn("MAC verification failed", str(ctx.exception))

        # Tamper with 1 byte in authentication tag (last 16 bytes)
        ciphertext = bytearray(session_a.encrypt_payload(plain))
        ciphertext[-1] ^= 0x01
        with self.assertRaises(ValueError) as ctx:
            session_b.decrypt_payload(bytes(ciphertext))
        self.assertIn("MAC verification failed", str(ctx.exception))

    def test_imposter_handshake_rejection(self):
        node_a = crypto.NodeIdentity.generate(node_id=10)
        node_b = crypto.NodeIdentity.generate(node_id=20)
        imposter = crypto.NodeIdentity.generate(node_id=99)

        init_pkt, _ = crypto.CryptoHandshake.create_init(node_a)

        # Imposter attempts to sign Node A's ephemeral pubkey with imposter's identity
        forged_sig = imposter.sign(init_pkt.ephemeral_pubkey)
        forged_init = crypto.HandshakeInitPacket(
            sender_node_id=10,
            id_pubkey=node_a.public_bytes,  # Claims to be Node A
            ephemeral_pubkey=init_pkt.ephemeral_pubkey,
            signature=forged_sig,  # Forged signature
        )

        with self.assertRaises(ValueError) as ctx:
            crypto.CryptoHandshake.process_init_and_respond(node_b, forged_init)
        self.assertIn("signature verification failed", str(ctx.exception))

    def test_wire_frame_encryption_roundtrip(self):
        node_a = crypto.NodeIdentity.generate(node_id=100)
        node_b = crypto.NodeIdentity.generate(node_id=200)

        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)

        # Original frame
        original_payload = b'{"task_id":9001,"compute":"matrix_multiply"}'
        frame = wire.Frame.create(wire.Opcode.TASK_OFFLOAD, node_id=100, payload=original_payload)

        # Encrypt frame
        enc_frame = session_a.encrypt_frame(frame)
        self.assertEqual(enc_frame.header.opcode, wire.Opcode.TASK_OFFLOAD)
        self.assertEqual(enc_frame.header.node_id, 100)
        self.assertEqual(len(enc_frame.payload), len(original_payload) + 16)
        self.assertNotEqual(enc_frame.payload, original_payload)

        # Encode and decode over wire
        raw_wire_bytes = enc_frame.encode()
        wire_decoded_frame = wire.Frame.decode(raw_wire_bytes)
        self.assertEqual(wire_decoded_frame.header.payload_len, len(enc_frame.payload))

        # Decrypt frame on receiving node
        dec_frame = session_b.decrypt_frame(wire_decoded_frame)
        self.assertEqual(dec_frame.header.opcode, wire.Opcode.TASK_OFFLOAD)
        self.assertEqual(dec_frame.header.node_id, 100)
        self.assertEqual(dec_frame.payload, original_payload)

    def test_nonce_increment_progression(self):
        node_a = crypto.NodeIdentity.generate(node_id=1)
        node_b = crypto.NodeIdentity.generate(node_id=2)

        init_pkt, eph_priv_a = crypto.CryptoHandshake.create_init(node_a)
        resp_pkt, session_b = crypto.CryptoHandshake.process_init_and_respond(node_b, init_pkt)
        session_a = crypto.CryptoHandshake.finalize_init(node_a, eph_priv_a, resp_pkt)

        self.assertEqual(session_a.tx_nonce, 0)
        self.assertEqual(session_b.rx_nonce, 0)

        # Encrypt 3 consecutive packets
        ct1 = session_a.encrypt_payload(b"packet 1")
        self.assertEqual(session_a.tx_nonce, 1)

        ct2 = session_a.encrypt_payload(b"packet 2")
        self.assertEqual(session_a.tx_nonce, 2)

        ct3 = session_a.encrypt_payload(b"packet 3")
        self.assertEqual(session_a.tx_nonce, 3)

        # Decrypt in order
        p1 = session_b.decrypt_payload(ct1)
        self.assertEqual(session_b.rx_nonce, 1)
        self.assertEqual(p1, b"packet 1")

        p2 = session_b.decrypt_payload(ct2)
        self.assertEqual(session_b.rx_nonce, 2)
        self.assertEqual(p2, b"packet 2")

        p3 = session_b.decrypt_payload(ct3)
        self.assertEqual(session_b.rx_nonce, 3)
        self.assertEqual(p3, b"packet 3")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeCryptoHandshake)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
