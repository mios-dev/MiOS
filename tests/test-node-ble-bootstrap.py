#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE BLE beaconing and offline local mesh bootstrap.
# AI-related: usr/libexec/mios/node/ble.py, src/mios-rs/mios-node/src/ble.rs
"""Automated tests for WS-NODE BLE GATT bootstrap, X25519 ECDH key exchange, and ChaCha20-Poly1305 provisioning."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_BLE_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "ble.py")

spec = importlib.util.spec_from_file_location("ble", _BLE_PATH)
if spec and spec.loader:
    ble = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = ble
    spec.loader.exec_module(ble)
else:
    raise ImportError(f"Could not load ble module from {_BLE_PATH}")


class TestNodeBleBootstrap(unittest.TestCase):
    """Validates BLE GATT service specification, ECDH ephemeral key exchange, and AEAD credential decryption."""

    def test_ble_constants_and_state_definitions(self):
        self.assertEqual(ble.BLE_SERVICE_UUID, "4D494F53-0001-1000-8000-00805F9B34FB")
        self.assertEqual(ble.BLE_CHAR_IDENTITY_UUID, "4D494F53-0002-1000-8000-00805F9B34FB")
        self.assertEqual(ble.BLE_CHAR_ECDH_UUID, "4D494F53-0003-1000-8000-00805F9B34FB")
        self.assertEqual(ble.BLE_CHAR_PROVISION_UUID, "4D494F53-0004-1000-8000-00805F9B34FB")

        self.assertEqual(ble.BleBootstrapState.UNPROVISIONED, 0)
        self.assertEqual(ble.BleBootstrapState.HANDSHAKING, 1)
        self.assertEqual(ble.BleBootstrapState.PROVISIONED, 3)

    def test_full_encrypted_ble_provisioning_flow(self):
        adapter = ble.MockBleAdapter()
        node = ble.BleMeshBootstrap(node_id=42, adapter=adapter)

        # 1. Node starts offline advertising
        node.start()
        self.assertTrue(adapter.is_advertising())
        self.assertEqual(node.state, ble.BleBootstrapState.UNPROVISIONED)

        # 2. Provisioner creates credentials payload
        creds = ble.ProvisioningPayload(
            ssid="MiOS-Edge-Mesh",
            psk="SuperSecretWifiP@ss123",
            cluster_token="tok_alpha_cluster_99",
            coordinator_endpoint="192.168.1.1:8650",
        )

        # 3. Provisioner executes client provisioning handshake
        ble.provision_remote_node(adapter, creds)

        # 4. Offline node accepts peer ECDH public key
        peer_pub_bytes = adapter.get_characteristic_value(ble.BLE_CHAR_ECDH_UUID)
        node.handle_ecdh_exchange(peer_pub_bytes)
        self.assertEqual(node.state, ble.BleBootstrapState.HANDSHAKING)

        # 5. Offline node accepts encrypted provisioning payload
        enc_payload = adapter.get_characteristic_value(ble.BLE_CHAR_PROVISION_UUID)
        provisioned = node.handle_provisioning_write(enc_payload)

        self.assertEqual(provisioned.ssid, "MiOS-Edge-Mesh")
        self.assertEqual(provisioned.psk, "SuperSecretWifiP@ss123")
        self.assertEqual(provisioned.cluster_token, "tok_alpha_cluster_99")
        self.assertEqual(provisioned.coordinator_endpoint, "192.168.1.1:8650")

        # 6. Verify terminal state and advertising shutdown
        self.assertEqual(node.state, ble.BleBootstrapState.PROVISIONED)
        self.assertFalse(adapter.is_advertising())

    def test_tampered_encrypted_payload_rejection(self):
        adapter = ble.MockBleAdapter()
        node = ble.BleMeshBootstrap(node_id=88, adapter=adapter)
        node.start()

        creds = ble.ProvisioningPayload(
            ssid="MiOS-Edge-Mesh",
            psk="P@ss",
            cluster_token="tok_1",
            coordinator_endpoint="127.0.0.1:8650",
        )
        ble.provision_remote_node(adapter, creds)

        peer_pub_bytes = adapter.get_characteristic_value(ble.BLE_CHAR_ECDH_UUID)
        node.handle_ecdh_exchange(peer_pub_bytes)

        # Tamper with encrypted ciphertext
        enc_payload = bytearray(adapter.get_characteristic_value(ble.BLE_CHAR_PROVISION_UUID))
        enc_payload[10] ^= 0xFF  # Flip bit

        # Decryption should fail AEAD authentication
        with self.assertRaises(Exception):
            node.handle_provisioning_write(bytes(enc_payload))

        self.assertNotEqual(node.state, ble.BleBootstrapState.PROVISIONED)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeBleBootstrap)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
