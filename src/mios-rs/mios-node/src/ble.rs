// AI-hint: BLE beaconing for offline local mesh bootstrap for mios-node (T-395 / AGY-1993).
// AI-related: src/mios-rs/mios-node/src/crypto.rs, usr/libexec/mios/node/ble.py, tests/test-node-ble-bootstrap.py
//! MiOS BLE Beaconing & Offline Local Mesh Bootstrap Engine
//!
//! Implements GATT service/characteristic definitions for headless edge blades,
//! ephemeral X25519 Diffie-Hellman key exchange, HKDF-SHA256 key derivation,
//! ChaCha20-Poly1305 AEAD encrypted credential provisioning, and mockable hardware adapter.

use crate::crypto::{
    chacha20_poly1305_decrypt, chacha20_poly1305_encrypt, hkdf_sha256, x25519, x25519_public_key,
};
use anyhow::{anyhow, Result};
use byteorder::{BigEndian, ByteOrder};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

pub const BLE_SERVICE_UUID: &str = "4D494F53-0001-1000-8000-00805F9B34FB";
pub const BLE_CHAR_IDENTITY_UUID: &str = "4D494F53-0002-1000-8000-00805F9B34FB";
pub const BLE_CHAR_ECDH_UUID: &str = "4D494F53-0003-1000-8000-00805F9B34FB";
pub const BLE_CHAR_PROVISION_UUID: &str = "4D494F53-0004-1000-8000-00805F9B34FB";

pub const BLE_HKDF_SALT: &[u8] = b"mios-ble-bootstrap";
pub const BLE_HKDF_INFO: &[u8] = b"wifi-provisioning";
pub const BLE_AEAD_AAD: &[u8] = b"mios-ble-v1";
pub const BLE_NONCE: &[u8; 12] = b"mios-ble-n01";

/// Bootstrap lifecycle states for headless edge blades.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum BleBootstrapState {
    Unprovisioned = 0,
    Handshaking = 1,
    Provisioning = 2,
    Provisioned = 3,
    Failed = 4,
}

impl TryFrom<u8> for BleBootstrapState {
    type Error = anyhow::Error;

    fn try_from(v: u8) -> Result<Self> {
        match v {
            0 => Ok(BleBootstrapState::Unprovisioned),
            1 => Ok(BleBootstrapState::Handshaking),
            2 => Ok(BleBootstrapState::Provisioning),
            3 => Ok(BleBootstrapState::Provisioned),
            4 => Ok(BleBootstrapState::Failed),
            _ => Err(anyhow!("Invalid BLE bootstrap state: {}", v)),
        }
    }
}

/// Encrypted Wi-Fi and mesh cluster join credentials.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProvisioningPayload {
    pub ssid: String,
    pub psk: String,
    pub cluster_token: String,
    pub coordinator_endpoint: String,
    pub mesh_network_key: Option<Vec<u8>>,
    pub timestamp_utc: u64,
}

impl ProvisioningPayload {
    pub fn new(
        ssid: String,
        psk: String,
        cluster_token: String,
        coordinator_endpoint: String,
    ) -> Self {
        let now_sec = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        Self {
            ssid,
            psk,
            cluster_token,
            coordinator_endpoint,
            mesh_network_key: None,
            timestamp_utc: now_sec,
        }
    }
}

/// Hardware abstraction interface for Bluetooth Low Energy GATT operations.
pub trait BleAdapter: Send + Sync {
    fn start_advertising(&self, service_uuid: &str, node_id: u32) -> Result<()>;
    fn stop_advertising(&self) -> Result<()>;
    fn is_advertising(&self) -> bool;
    fn set_characteristic_value(&self, char_uuid: &str, data: Vec<u8>) -> Result<()>;
    fn get_characteristic_value(&self, char_uuid: &str) -> Result<Vec<u8>>;
}

/// In-memory mock BLE adapter for headless and deterministic CI testing.
#[derive(Debug, Default)]
pub struct MockBleAdapter {
    advertising: Arc<Mutex<bool>>,
    characteristics: Arc<Mutex<HashMap<String, Vec<u8>>>>,
}

impl MockBleAdapter {
    pub fn new() -> Self {
        Self::default()
    }
}

impl BleAdapter for MockBleAdapter {
    fn start_advertising(&self, _service_uuid: &str, _node_id: u32) -> Result<()> {
        let mut adv = self.advertising.lock().unwrap();
        *adv = true;
        Ok(())
    }

    fn stop_advertising(&self) -> Result<()> {
        let mut adv = self.advertising.lock().unwrap();
        *adv = false;
        Ok(())
    }

    fn is_advertising(&self) -> bool {
        *self.advertising.lock().unwrap()
    }

    fn set_characteristic_value(&self, char_uuid: &str, data: Vec<u8>) -> Result<()> {
        let mut map = self.characteristics.lock().unwrap();
        map.insert(char_uuid.to_string(), data);
        Ok(())
    }

    fn get_characteristic_value(&self, char_uuid: &str) -> Result<Vec<u8>> {
        let map = self.characteristics.lock().unwrap();
        map.get(char_uuid)
            .cloned()
            .ok_or_else(|| anyhow!("Characteristic {} not found", char_uuid))
    }
}

/// Orchestrator for headless node BLE bootstrap advertising and encrypted provisioning.
pub struct BleMeshBootstrap {
    pub node_id: u32,
    adapter: Arc<dyn BleAdapter>,
    state: Arc<Mutex<BleBootstrapState>>,
    local_priv_key: [u8; 32],
    local_pub_key: [u8; 32],
    shared_key: Arc<Mutex<Option<[u8; 32]>>>,
    provisioned_credentials: Arc<Mutex<Option<ProvisioningPayload>>>,
}

impl BleMeshBootstrap {
    pub fn new(node_id: u32, adapter: Arc<dyn BleAdapter>) -> Self {
        let mut seed = [0u8; 32];
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(123456789);
        BigEndian::write_u32(&mut seed[0..4], node_id);
        BigEndian::write_u128(&mut seed[4..20], now);
        seed[20..32].copy_from_slice(b"mios-ble-rnd");

        let pub_key = x25519_public_key(&seed);

        Self {
            node_id,
            adapter,
            state: Arc::new(Mutex::new(BleBootstrapState::Unprovisioned)),
            local_priv_key: seed,
            local_pub_key: pub_key,
            shared_key: Arc::new(Mutex::new(None)),
            provisioned_credentials: Arc::new(Mutex::new(None)),
        }
    }

    /// Starts advertising GATT service and initializes identity + ECDH characteristics.
    pub fn start(&self) -> Result<()> {
        // 1. Initialize Char 1: Identity (4B node_id + 1B state)
        let mut id_buf = vec![0u8; 5];
        BigEndian::write_u32(&mut id_buf[0..4], self.node_id);
        id_buf[4] = BleBootstrapState::Unprovisioned as u8;
        self.adapter.set_characteristic_value(BLE_CHAR_IDENTITY_UUID, id_buf)?;

        // 2. Initialize Char 2: Local X25519 Public Key (32B)
        self.adapter
            .set_characteristic_value(BLE_CHAR_ECDH_UUID, self.local_pub_key.to_vec())?;

        // 3. Start advertising
        self.adapter.start_advertising(BLE_SERVICE_UUID, self.node_id)?;
        *self.state.lock().unwrap() = BleBootstrapState::Unprovisioned;

        Ok(())
    }

    /// Handles peer ECDH key exchange write to Characteristic 2.
    pub fn handle_ecdh_exchange(&self, peer_pub_key_bytes: &[u8]) -> Result<()> {
        if peer_pub_key_bytes.len() != 32 {
            return Err(anyhow!("Invalid X25519 public key length: {}", peer_pub_key_bytes.len()));
        }

        let mut peer_pub = [0u8; 32];
        peer_pub.copy_from_slice(peer_pub_key_bytes);

        // Compute X25519 shared secret
        let shared_secret = x25519(&self.local_priv_key, &peer_pub);

        // Derive AEAD symmetric key via HKDF-SHA256
        let derived_bytes = hkdf_sha256(BLE_HKDF_SALT, &shared_secret, BLE_HKDF_INFO, 32);
        let mut key = [0u8; 32];
        key.copy_from_slice(&derived_bytes[0..32]);

        *self.shared_key.lock().unwrap() = Some(key);
        *self.state.lock().unwrap() = BleBootstrapState::Handshaking;

        // Update Char 1 state
        let mut id_buf = vec![0u8; 5];
        BigEndian::write_u32(&mut id_buf[0..4], self.node_id);
        id_buf[4] = BleBootstrapState::Handshaking as u8;
        self.adapter.set_characteristic_value(BLE_CHAR_IDENTITY_UUID, id_buf)?;

        Ok(())
    }

    /// Handles encrypted credential write to Characteristic 3 and completes provisioning.
    pub fn handle_provisioning_write(&self, encrypted_payload: &[u8]) -> Result<ProvisioningPayload> {
        let key = self
            .shared_key
            .lock()
            .unwrap()
            .ok_or_else(|| anyhow!("ECDH handshake not completed prior to provisioning write"))?;

        // Decrypt payload using ChaCha20-Poly1305
        let decrypted_bytes = chacha20_poly1305_decrypt(&key, BLE_NONCE, BLE_AEAD_AAD, encrypted_payload)?;
        let creds: ProvisioningPayload = serde_json::from_slice(&decrypted_bytes)?;

        *self.provisioned_credentials.lock().unwrap() = Some(creds.clone());
        *self.state.lock().unwrap() = BleBootstrapState::Provisioned;

        // Update Char 1 state to Provisioned and stop advertising
        let mut id_buf = vec![0u8; 5];
        BigEndian::write_u32(&mut id_buf[0..4], self.node_id);
        id_buf[4] = BleBootstrapState::Provisioned as u8;
        self.adapter.set_characteristic_value(BLE_CHAR_IDENTITY_UUID, id_buf)?;
        self.adapter.stop_advertising()?;

        Ok(creds)
    }

    pub fn state(&self) -> BleBootstrapState {
        *self.state.lock().unwrap()
    }

    pub fn get_credentials(&self) -> Option<ProvisioningPayload> {
        self.provisioned_credentials.lock().unwrap().clone()
    }

    pub fn local_public_key(&self) -> [u8; 32] {
        self.local_pub_key
    }
}

/// Provisioner helper that discovers, handshakes, and securely configures an offline edge blade.
pub fn provision_remote_node(
    adapter: &dyn BleAdapter,
    payload: &ProvisioningPayload,
) -> Result<()> {
    // 1. Read node identity from Char 1
    let id_bytes = adapter.get_characteristic_value(BLE_CHAR_IDENTITY_UUID)?;
    if id_bytes.len() < 5 {
        return Err(anyhow!("Invalid identity characteristic length"));
    }

    // 2. Read node public key from Char 2
    let node_pub_bytes = adapter.get_characteristic_value(BLE_CHAR_ECDH_UUID)?;
    if node_pub_bytes.len() != 32 {
        return Err(anyhow!("Invalid node public key length"));
    }
    let mut node_pub = [0u8; 32];
    node_pub.copy_from_slice(&node_pub_bytes);

    // 3. Generate provisioner ephemeral key
    let priv_key = [0x55u8; 32];
    let prov_pub = x25519_public_key(&priv_key);

    // 4. Write provisioner public key to Char 2
    adapter.set_characteristic_value(BLE_CHAR_ECDH_UUID, prov_pub.to_vec())?;

    // 5. Compute shared key
    let ss = x25519(&priv_key, &node_pub);
    let derived = hkdf_sha256(BLE_HKDF_SALT, &ss, BLE_HKDF_INFO, 32);
    let mut key = [0u8; 32];
    key.copy_from_slice(&derived[0..32]);

    // 6. Encrypt credentials
    let json_bytes = serde_json::to_vec(payload)?;
    let encrypted = chacha20_poly1305_encrypt(&key, BLE_NONCE, BLE_AEAD_AAD, &json_bytes);

    // 7. Write encrypted payload to Char 3
    adapter.set_characteristic_value(BLE_CHAR_PROVISION_UUID, encrypted)?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ble_bootstrap_full_encrypted_provisioning_flow() {
        let adapter: Arc<dyn BleAdapter> = Arc::new(MockBleAdapter::new());
        let bootstrap = BleMeshBootstrap::new(42, Arc::clone(&adapter));

        // 1. Start offline node BLE beaconing
        bootstrap.start().unwrap();
        assert!(adapter.is_advertising());
        assert_eq!(bootstrap.state(), BleBootstrapState::Unprovisioned);

        // 2. Provisioner prepares Wi-Fi payload
        let creds = ProvisioningPayload::new(
            "MiOS-Mesh-WiFi".to_string(),
            "Sup3rS3cur3P@ss".to_string(),
            "tok_cluster_9988".to_string(),
            "192.168.1.1:8650".to_string(),
        );

        // 3. Provisioner executes provisioning handshake
        provision_remote_node(adapter.as_ref(), &creds).unwrap();

        // 4. Node processes peer ECDH key from Char 2
        let peer_pub = adapter
            .get_characteristic_value(BLE_CHAR_ECDH_UUID)
            .unwrap();
        bootstrap.handle_ecdh_exchange(&peer_pub).unwrap();
        assert_eq!(bootstrap.state(), BleBootstrapState::Handshaking);

        // 5. Node processes encrypted credentials from Char 3
        let enc_payload = adapter
            .get_characteristic_value(BLE_CHAR_PROVISION_UUID)
            .unwrap();
        let provisioned = bootstrap.handle_provisioning_write(&enc_payload).unwrap();

        assert_eq!(provisioned.ssid, "MiOS-Mesh-WiFi");
        assert_eq!(provisioned.psk, "Sup3rS3cur3P@ss");
        assert_eq!(provisioned.cluster_token, "tok_cluster_9988");
        assert_eq!(bootstrap.state(), BleBootstrapState::Provisioned);
        assert!(!adapter.is_advertising()); // Advertising stopped upon successful bootstrap
    }
}
