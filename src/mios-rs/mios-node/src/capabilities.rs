// AI-hint: Edge node capability advertising in Announce frames for mios-node (T-394 / AGY-1992).
// AI-related: src/mios-rs/mios-node/src/protocol.rs, usr/libexec/mios/node/capabilities.py, tests/test-node-capabilities.py
//! MiOS Edge Node Capability Advertising & Telemetry Engine
//!
//! Encapsulates Opcode 0x02 `NodeAnnounce` payloads with CPU, RAM, GPU/VRAM telemetry,
//! execution tiers (Wasm, Native), active mesh transports, hardware interfaces (GPIO/I2C),
//! capability probing, and cluster capability registry.

use crate::protocol::{Frame, MessageType};
use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::sync::{Arc, Mutex};

/// Host CPU and system memory telemetry.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HardwareSpecs {
    pub cpu_arch: String,
    pub cpu_cores: u32,
    pub cpu_frequency_mhz: u32,
    pub ram_total_kb: u64,
    pub ram_available_kb: u64,
}

impl Default for HardwareSpecs {
    fn default() -> Self {
        Self {
            cpu_arch: std::env::consts::ARCH.to_string(),
            cpu_cores: num_cpus_detected(),
            cpu_frequency_mhz: 2400,
            ram_total_kb: 8 * 1024 * 1024,
            ram_available_kb: 4 * 1024 * 1024,
        }
    }
}

/// GPU, VRAM, and NPU accelerator telemetry.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct VramTelemetry {
    pub gpu_vendor: String,        // "NVIDIA", "AMD", "Intel", "Apple", "None"
    pub gpu_model: Option<String>,
    pub vram_total_mb: u32,
    pub vram_available_mb: u32,
    pub has_npu: bool,
}

impl Default for VramTelemetry {
    fn default() -> Self {
        Self {
            gpu_vendor: "None".to_string(),
            gpu_model: None,
            vram_total_mb: 0,
            vram_available_mb: 0,
            has_npu: false,
        }
    }
}

/// Sandboxing execution tiers supported by the edge node.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EngineTiers {
    pub wasm_tier: bool,
    pub native_tier: bool,
    pub llm_inference: bool,
    pub supported_task_types: Vec<String>,
}

impl Default for EngineTiers {
    fn default() -> Self {
        Self {
            wasm_tier: true,
            native_tier: true,
            llm_inference: false,
            supported_task_types: vec![
                "wasm".to_string(),
                "native_elf".to_string(),
                "crdt_sync".to_string(),
            ],
        }
    }
}

/// Transport network connectivity options active on the edge node.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ActiveTransports {
    pub lan_broadcast: bool,
    pub direct_tcp: bool,
    pub tailscale: bool,
    pub wireguard: bool,
    pub ble_mesh: bool,
    pub endpoints: Vec<String>,
}

impl Default for ActiveTransports {
    fn default() -> Self {
        Self {
            lan_broadcast: true,
            direct_tcp: true,
            tailscale: false,
            wireguard: false,
            ble_mesh: false,
            endpoints: vec!["127.0.0.1:8650".to_string()],
        }
    }
}

/// Consolidated capabilities profile of an edge node.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, Default)]
pub struct NodeCapabilities {
    pub hardware: HardwareSpecs,
    pub vram: VramTelemetry,
    pub engines: EngineTiers,
    pub transports: ActiveTransports,
    pub has_gpio: bool,
    pub has_i2c: bool,
}

/// Opcode 0x02 `NodeAnnounce` full wire payload.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NodeAnnouncePayload {
    pub node_id: u32,
    pub hostname: String,
    pub capabilities: NodeCapabilities,
    pub timestamp_utc: u64,
    pub version: String,
}

impl NodeAnnouncePayload {
    pub fn new(node_id: u32, hostname: String, capabilities: NodeCapabilities) -> Self {
        let now_sec = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        Self {
            node_id,
            hostname,
            capabilities,
            timestamp_utc: now_sec,
            version: "0.3.0".to_string(),
        }
    }

    pub fn to_frame(&self) -> Result<Frame> {
        let json_bytes = serde_json::to_vec(self)?;
        Ok(Frame::new(MessageType::NodeAnnounce, self.node_id, json_bytes))
    }

    pub fn from_frame(frame: &Frame) -> Result<Self> {
        if frame.header.msg_type != MessageType::NodeAnnounce {
            return Err(anyhow!(
                "Invalid message type for NodeAnnounce: {:?}",
                frame.header.msg_type
            ));
        }
        let payload = serde_json::from_slice(&frame.payload)?;
        Ok(payload)
    }
}

fn num_cpus_detected() -> u32 {
    let count = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4);
    count as u32
}

/// Probes the local operating environment for hardware, VRAM, and peripheral interfaces.
pub fn probe_node_capabilities() -> NodeCapabilities {
    let mut caps = NodeCapabilities::default();

    // 1. Probe CPU & RAM via /proc if on Linux
    if Path::new("/proc/meminfo").exists() {
        if let Ok(content) = fs::read_to_string("/proc/meminfo") {
            for line in content.lines() {
                if line.starts_with("MemTotal:") {
                    if let Some(kb_str) = line.split_whitespace().nth(1) {
                        if let Ok(val) = kb_str.parse::<u64>() {
                            caps.hardware.ram_total_kb = val;
                        }
                    }
                } else if line.starts_with("MemAvailable:") {
                    if let Some(kb_str) = line.split_whitespace().nth(1) {
                        if let Ok(val) = kb_str.parse::<u64>() {
                            caps.hardware.ram_available_kb = val;
                        }
                    }
                }
            }
        }
    }

    // 2. Probe GPIO & I2C
    caps.has_gpio = Path::new("/dev/gpiochip0").exists() || Path::new("/sys/class/gpio").exists();
    caps.has_i2c = Path::new("/dev/i2c-0").exists() || Path::new("/dev/i2c-1").exists();

    // 3. Probe GPU
    if Path::new("/sys/class/drm").exists() || Path::new("/dev/nvidia0").exists() {
        if Path::new("/dev/nvidia0").exists() {
            caps.vram.gpu_vendor = "NVIDIA".to_string();
            caps.vram.gpu_model = Some("NVIDIA GPU Accelerator".to_string());
            caps.vram.vram_total_mb = 8192;
            caps.vram.vram_available_mb = 6144;
            caps.engines.llm_inference = true;
        } else {
            caps.vram.gpu_vendor = "Generic DRM".to_string();
        }
    }

    caps
}

/// In-memory cluster capability registry for tracking mesh peers and candidate scheduling.
#[derive(Debug, Default)]
pub struct CapabilityRegistry {
    peers: Arc<Mutex<HashMap<u32, (NodeAnnouncePayload, u64)>>>,
}

impl CapabilityRegistry {
    pub fn new() -> Self {
        Self {
            peers: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn register_announce(&self, payload: NodeAnnouncePayload, received_at_utc: u64) {
        let mut map = self.peers.lock().unwrap();
        map.insert(payload.node_id, (payload, received_at_utc));
    }

    pub fn get_capabilities(&self, node_id: u32) -> Option<NodeCapabilities> {
        let map = self.peers.lock().unwrap();
        map.get(&node_id).map(|(p, _)| p.capabilities.clone())
    }

    pub fn get_announce(&self, node_id: u32) -> Option<NodeAnnouncePayload> {
        let map = self.peers.lock().unwrap();
        map.get(&node_id).map(|(p, _)| p.clone())
    }

    /// Finds all registered node IDs matching specific hardware and execution requirements.
    pub fn find_eligible_nodes(
        &self,
        min_ram_kb: u64,
        min_vram_mb: u32,
        require_wasm: bool,
        require_native: bool,
        require_gpio: bool,
        require_i2c: bool,
    ) -> Vec<u32> {
        let map = self.peers.lock().unwrap();
        let mut candidates = Vec::new();

        for (&node_id, (payload, _)) in map.iter() {
            let caps = &payload.capabilities;
            if caps.hardware.ram_available_kb < min_ram_kb {
                continue;
            }
            if caps.vram.vram_available_mb < min_vram_mb {
                continue;
            }
            if require_wasm && !caps.engines.wasm_tier {
                continue;
            }
            if require_native && !caps.engines.native_tier {
                continue;
            }
            if require_gpio && !caps.has_gpio {
                continue;
            }
            if require_i2c && !caps.has_i2c {
                continue;
            }
            candidates.push(node_id);
        }

        candidates.sort();
        candidates
    }

    /// Evicts announces older than max_age_secs.
    pub fn evict_stale(&self, max_age_secs: u64, now_utc: u64) -> usize {
        let mut map = self.peers.lock().unwrap();
        let before_len = map.len();
        map.retain(|_, (_, last_seen)| now_utc.saturating_sub(*last_seen) <= max_age_secs);
        before_len - map.len()
    }

    pub fn active_node_count(&self) -> usize {
        self.peers.lock().unwrap().len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_node_announce_frame_roundtrip() {
        let mut caps = NodeCapabilities::default();
        caps.hardware.ram_total_kb = 16 * 1024 * 1024;
        caps.vram.vram_total_mb = 12288;
        caps.vram.gpu_vendor = "NVIDIA".to_string();
        caps.has_gpio = true;

        let payload = NodeAnnouncePayload::new(42, "edge-blade-01".to_string(), caps);
        let frame = payload.to_frame().unwrap();

        assert_eq!(frame.header.msg_type, MessageType::NodeAnnounce);
        assert_eq!(frame.header.node_id, 42);

        let decoded = NodeAnnouncePayload::from_frame(&frame).unwrap();
        assert_eq!(decoded.node_id, 42);
        assert_eq!(decoded.hostname, "edge-blade-01");
        assert_eq!(decoded.capabilities.vram.vram_total_mb, 12288);
        assert!(decoded.capabilities.has_gpio);
    }

    #[test]
    fn test_capability_registry_filtering_and_eviction() {
        let registry = CapabilityRegistry::new();

        let mut caps1 = NodeCapabilities::default();
        caps1.hardware.ram_available_kb = 2 * 1024 * 1024;
        caps1.vram.vram_available_mb = 0;
        caps1.has_gpio = true;

        let mut caps2 = NodeCapabilities::default();
        caps2.hardware.ram_available_kb = 8 * 1024 * 1024;
        caps2.vram.vram_available_mb = 4096;
        caps2.has_gpio = false;

        let node1 = NodeAnnouncePayload::new(101, "worker-iot".to_string(), caps1);
        let node2 = NodeAnnouncePayload::new(102, "worker-gpu".to_string(), caps2);

        registry.register_announce(node1, 1000);
        registry.register_announce(node2, 1000);

        // Find nodes with GPU VRAM >= 2048MB
        let gpu_nodes = registry.find_eligible_nodes(1024, 2048, false, false, false, false);
        assert_eq!(gpu_nodes, vec![102]);

        // Find nodes with GPIO support
        let gpio_nodes = registry.find_eligible_nodes(1024, 0, false, false, true, false);
        assert_eq!(gpio_nodes, vec![101]);

        // Test stale eviction at t=1050 with max_age=30s
        let evicted = registry.evict_stale(30, 1050);
        assert_eq!(evicted, 2);
        assert_eq!(registry.active_node_count(), 0);
    }
}
