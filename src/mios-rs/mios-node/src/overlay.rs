// AI-hint: Automated fallback to Tailscale and WireGuard overlay when LAN broadcast is partitioned (T-396 / AGY-1994).
// AI-related: src/mios-rs/mios-node/src/heartbeat.rs, usr/libexec/mios/node/overlay.py, tests/test-node-overlay.py
//! MiOS Multi-Transport Router & LAN Partition Overlay Failover Engine
//!
//! Implements multi-transport routing across Direct LAN, WireGuard overlay, Tailscale mesh,
//! and Direct TCP, featuring 3-strike LAN partition failure detection and asymmetric
//! anti-flap recovery hysteresis (120s recovery dwell from `[blade.collapse]`).

use anyhow::{anyhow, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

/// Supported network transport types in order of preferred priority.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum TransportType {
    LanBroadcast = 1, // Tier 1: Local subnet UDP broadcast / direct TCP (<2ms)
    WireGuard = 2,    // Tier 2: Encrypted kernel WireGuard overlay (<10ms)
    Tailscale = 3,    // Tier 3: Tailscale tailnet mesh / DERP relay (<30ms)
    DirectTcp = 4,    // Tier 4: Fallback direct TCP / remote coordinator (<50ms)
}

impl TransportType {
    pub fn as_str(&self) -> &'static str {
        match self {
            TransportType::LanBroadcast => "lan_broadcast",
            TransportType::WireGuard => "wireguard",
            TransportType::Tailscale => "tailscale",
            TransportType::DirectTcp => "direct_tcp",
        }
    }
}

/// Dynamic health telemetry for an individual transport link.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TransportHealth {
    pub consecutive_success: u32,
    pub consecutive_misses: u32,
    pub last_success_ms: u64,
    pub last_miss_ms: u64,
    pub latency_ms: u32,
    pub is_healthy: bool,
}

impl Default for TransportHealth {
    fn default() -> Self {
        Self {
            consecutive_success: 0,
            consecutive_misses: 0,
            last_success_ms: 0,
            last_miss_ms: 0,
            latency_ms: 0,
            is_healthy: true,
        }
    }
}

/// Routing state and failover tracking for a specific peer node.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PeerRoute {
    pub node_id: u32,
    pub endpoints: HashMap<TransportType, String>,
    pub active_transport: TransportType,
    pub transport_health: HashMap<TransportType, TransportHealth>,
    pub is_lan_partitioned: bool,
    pub last_failover_ms: u64,
    pub last_lan_recovery_start_ms: Option<u64>,
}

impl PeerRoute {
    pub fn new(node_id: u32, endpoints: HashMap<TransportType, String>) -> Self {
        let mut health = HashMap::new();
        for &t in endpoints.keys() {
            health.insert(t, TransportHealth::default());
        }

        let active = if endpoints.contains_key(&TransportType::LanBroadcast) {
            TransportType::LanBroadcast
        } else if endpoints.contains_key(&TransportType::WireGuard) {
            TransportType::WireGuard
        } else if endpoints.contains_key(&TransportType::Tailscale) {
            TransportType::Tailscale
        } else {
            TransportType::DirectTcp
        };

        Self {
            node_id,
            endpoints,
            active_transport: active,
            transport_health: health,
            is_lan_partitioned: false,
            last_failover_ms: 0,
            last_lan_recovery_start_ms: None,
        }
    }
}

/// Anti-flap hysteresis configuration parameters (aligning with `[blade.collapse]`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HysteresisConfig {
    pub fail_strikes_threshold: u32, // Failover after N consecutive missed heartbeats (e.g. 3)
    pub recovery_dwell_ms: u64,      // Revert dwell time in ms (e.g. 120_000 ms = 120s)
    pub recovery_strikes_threshold: u32, // Consecutive healthy probes required during recovery (e.g. 3)
}

impl Default for HysteresisConfig {
    fn default() -> Self {
        Self {
            fail_strikes_threshold: 3,
            recovery_dwell_ms: 120_000,
            recovery_strikes_threshold: 3,
        }
    }
}

/// Route summary snapshot for peer inspection.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RouteSummary {
    pub node_id: u32,
    pub active_transport: TransportType,
    pub active_endpoint: String,
    pub is_lan_partitioned: bool,
    pub latency_ms: u32,
}

/// Multi-transport routing controller with automated WAN overlay failover.
pub struct MultiTransportRouter {
    peers: Arc<Mutex<HashMap<u32, PeerRoute>>>,
    config: HysteresisConfig,
}

impl MultiTransportRouter {
    pub fn new(config: Option<HysteresisConfig>) -> Self {
        Self {
            peers: Arc::new(Mutex::new(HashMap::new())),
            config: config.unwrap_or_default(),
        }
    }

    /// Registers a peer with its configured network endpoints across transport tiers.
    pub fn register_peer(&self, node_id: u32, endpoints: HashMap<TransportType, String>) {
        let mut map = self.peers.lock().unwrap();
        map.insert(node_id, PeerRoute::new(node_id, endpoints));
    }

    /// Records a successful heartbeat received from a peer on a given transport.
    pub fn record_heartbeat(
        &self,
        node_id: u32,
        transport: TransportType,
        latency_ms: u32,
        now_ms: u64,
    ) {
        let mut map = self.peers.lock().unwrap();
        if let Some(peer) = map.get_mut(&node_id) {
            let h = peer.transport_health.entry(transport).or_default();
            h.consecutive_success += 1;
            h.consecutive_misses = 0;
            h.last_success_ms = now_ms;
            h.latency_ms = latency_ms;
            h.is_healthy = true;

            // Asymmetric Anti-Flap Recovery: If LAN was partitioned and LAN heartbeat recovered
            if transport == TransportType::LanBroadcast && peer.is_lan_partitioned {
                if peer.last_lan_recovery_start_ms.is_none() {
                    peer.last_lan_recovery_start_ms = Some(now_ms);
                }

                let recovery_start = peer.last_lan_recovery_start_ms.unwrap_or(now_ms);
                let elapsed_dwell = now_ms.saturating_sub(recovery_start);

                // Both dwell timer AND consecutive success threshold must be satisfied
                if elapsed_dwell >= self.config.recovery_dwell_ms
                    && h.consecutive_success >= self.config.recovery_strikes_threshold
                {
                    peer.is_lan_partitioned = false;
                    peer.active_transport = TransportType::LanBroadcast;
                    peer.last_lan_recovery_start_ms = None;
                }
            }
        }
    }

    /// Records a missed heartbeat or connect failure for a peer on a given transport.
    pub fn record_missed_heartbeat(&self, node_id: u32, transport: TransportType, now_ms: u64) {
        let mut map = self.peers.lock().unwrap();
        if let Some(peer) = map.get_mut(&node_id) {
            let h = peer.transport_health.entry(transport).or_default();
            h.consecutive_misses += 1;
            h.consecutive_success = 0;
            h.last_miss_ms = now_ms;

            if h.consecutive_misses >= self.config.fail_strikes_threshold {
                h.is_healthy = false;

                // If LAN failed, trigger automated WAN overlay failover
                if transport == TransportType::LanBroadcast && !peer.is_lan_partitioned {
                    peer.is_lan_partitioned = true;
                    peer.last_failover_ms = now_ms;
                    peer.last_lan_recovery_start_ms = None;

                    // Select next available transport tier: WireGuard -> Tailscale -> DirectTcp
                    if peer.endpoints.contains_key(&TransportType::WireGuard) {
                        peer.active_transport = TransportType::WireGuard;
                    } else if peer.endpoints.contains_key(&TransportType::Tailscale) {
                        peer.active_transport = TransportType::Tailscale;
                    } else if peer.endpoints.contains_key(&TransportType::DirectTcp) {
                        peer.active_transport = TransportType::DirectTcp;
                    }
                }
            }
        }
    }

    /// Queries the currently active transport and endpoint for routing frames to a peer.
    pub fn select_route(&self, node_id: u32) -> Result<(TransportType, String)> {
        let map = self.peers.lock().unwrap();
        let peer = map
            .get(&node_id)
            .ok_or_else(|| anyhow!("Peer node {} not registered in router", node_id))?;

        let endpoint = peer
            .endpoints
            .get(&peer.active_transport)
            .cloned()
            .ok_or_else(|| {
                anyhow!(
                    "No endpoint available for active transport {:?} to node {}",
                    peer.active_transport,
                    node_id
                )
            })?;

        Ok((peer.active_transport, endpoint))
    }

    pub fn is_peer_partitioned(&self, node_id: u32) -> bool {
        let map = self.peers.lock().unwrap();
        map.get(&node_id).is_some_and(|p| p.is_lan_partitioned)
    }

    pub fn get_route_summary(&self, node_id: u32) -> Option<RouteSummary> {
        let map = self.peers.lock().unwrap();
        let peer = map.get(&node_id)?;
        let endpoint = peer.endpoints.get(&peer.active_transport).cloned()?;
        let latency = peer
            .transport_health
            .get(&peer.active_transport)
            .map_or(0, |h| h.latency_ms);

        Some(RouteSummary {
            node_id,
            active_transport: peer.active_transport,
            active_endpoint: endpoint,
            is_lan_partitioned: peer.is_lan_partitioned,
            latency_ms: latency,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lan_partition_failover_to_wireguard() {
        let config = HysteresisConfig {
            fail_strikes_threshold: 3,
            recovery_dwell_ms: 10_000,
            recovery_strikes_threshold: 3,
        };
        let router = MultiTransportRouter::new(Some(config));

        let mut endpoints = HashMap::new();
        endpoints.insert(TransportType::LanBroadcast, "192.168.1.50:8650".to_string());
        endpoints.insert(TransportType::WireGuard, "10.0.0.50:8650".to_string());
        endpoints.insert(TransportType::Tailscale, "100.64.0.50:8650".to_string());

        router.register_peer(201, endpoints);

        // Initial state: LanBroadcast
        let (t1, ep1) = router.select_route(201).unwrap();
        assert_eq!(t1, TransportType::LanBroadcast);
        assert_eq!(ep1, "192.168.1.50:8650");

        // 2 misses on LAN: should still remain LAN
        router.record_missed_heartbeat(201, TransportType::LanBroadcast, 1000);
        router.record_missed_heartbeat(201, TransportType::LanBroadcast, 2000);
        assert!(!router.is_peer_partitioned(201));
        assert_eq!(
            router.select_route(201).unwrap().0,
            TransportType::LanBroadcast
        );

        // 3rd miss on LAN: triggers partition and switches to WireGuard
        router.record_missed_heartbeat(201, TransportType::LanBroadcast, 3000);
        assert!(router.is_peer_partitioned(201));
        let (t2, ep2) = router.select_route(201).unwrap();
        assert_eq!(t2, TransportType::WireGuard);
        assert_eq!(ep2, "10.0.0.50:8650");
    }

    #[test]
    fn test_asymmetric_anti_flap_recovery_dwell() {
        let config = HysteresisConfig {
            fail_strikes_threshold: 3,
            recovery_dwell_ms: 5000, // 5s dwell for test
            recovery_strikes_threshold: 3,
        };
        let router = MultiTransportRouter::new(Some(config));

        let mut endpoints = HashMap::new();
        endpoints.insert(TransportType::LanBroadcast, "192.168.1.50:8650".to_string());
        endpoints.insert(TransportType::Tailscale, "100.64.0.50:8650".to_string());

        router.register_peer(202, endpoints);

        // Fail over to Tailscale
        router.record_missed_heartbeat(202, TransportType::LanBroadcast, 1000);
        router.record_missed_heartbeat(202, TransportType::LanBroadcast, 2000);
        router.record_missed_heartbeat(202, TransportType::LanBroadcast, 3000);
        assert_eq!(
            router.select_route(202).unwrap().0,
            TransportType::Tailscale
        );

        // LAN probes resume at t=4000
        router.record_heartbeat(202, TransportType::LanBroadcast, 2, 4000);
        router.record_heartbeat(202, TransportType::LanBroadcast, 2, 5000);
        router.record_heartbeat(202, TransportType::LanBroadcast, 2, 6000);

        // 3 strikes achieved, but dwell elapsed is only 2000ms (< 5000ms) -> Still Tailscale!
        assert_eq!(
            router.select_route(202).unwrap().0,
            TransportType::Tailscale
        );

        // Probe at t=9500 (dwell elapsed = 5500ms >= 5000ms) -> Restores LAN!
        router.record_heartbeat(202, TransportType::LanBroadcast, 2, 9500);
        assert_eq!(
            router.select_route(202).unwrap().0,
            TransportType::LanBroadcast
        );
        assert!(!router.is_peer_partitioned(202));
    }
}
