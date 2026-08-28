// AI-hint: Comprehensive adversarial integration tests for Milestone 2 (T-392 through T-396).
// AI-related: src/mios-rs/mios-node/src/scheduler.rs, src/mios-rs/mios-node/src/buffer_pool.rs, src/mios-rs/mios-node/src/capabilities.rs, src/mios-rs/mios-node/src/ble.rs, src/mios-rs/mios-node/src/overlay.rs

use mios_node::ble::{
    provision_remote_node, BleAdapter, BleBootstrapState, BleMeshBootstrap, MockBleAdapter,
    ProvisioningPayload, BLE_CHAR_ECDH_UUID, BLE_CHAR_PROVISION_UUID,
};
use mios_node::buffer_pool::{BucketTier, BufferPool};
use mios_node::capabilities::{CapabilityRegistry, NodeAnnouncePayload, NodeCapabilities};
use mios_node::overlay::{HysteresisConfig, MultiTransportRouter, TransportType};
use mios_node::scheduler::{TaskItem, TaskPriority, WorkStealingScheduler};
use std::collections::HashMap;
use std::sync::Arc;
use std::thread;

#[test]
fn test_adversarial_work_stealing_pinned_invariants() {
    let scheduler = WorkStealingScheduler::new(101, 4);

    // Enqueue 10 pinned tasks and 10 unpinned tasks
    for i in 0..10 {
        let mut pinned = TaskItem::new(i, TaskPriority::Critical, 1, vec![1, 2, 3], vec![4, 5]);
        pinned.pinned_hardware = true;
        scheduler.submit_task(pinned, Some(0)); // assign to worker 0
    }

    for i in 10..20 {
        let unpinned = TaskItem::new(i, TaskPriority::Normal, 1, vec![7, 8], vec![9]);
        scheduler.submit_task(unpinned, Some(0)); // assign to worker 0
    }

    // Workers 1, 2, 3 try to steal from worker 0
    let mut stolen_task_ids = Vec::new();
    for w in 1..4 {
        while let Some(task) = scheduler.pop_task(w) {
            stolen_task_ids.push(task.task_id);
            // Verify INVARIANT: Pinned tasks must NEVER be stolen!
            assert!(
                !task.pinned_hardware,
                "Invariant violated: Stole task {} with pinned_hardware=true",
                task.task_id
            );
        }
    }

    // All stolen tasks must be from the unpinned set (10..20)
    for id in &stolen_task_ids {
        assert!(*id >= 10 && *id < 20);
    }

    // Worker 0 should now execute all 10 pinned tasks locally
    let mut local_executed_ids = Vec::new();
    while let Some(task) = scheduler.pop_task(0) {
        local_executed_ids.push(task.task_id);
        assert!(task.pinned_hardware);
    }
    assert_eq!(local_executed_ids.len(), 10);
}

#[test]
fn test_adversarial_buffer_pool_saturation_and_zero_copy_slicing() {
    let pool = BufferPool::new();

    // Multithreaded stress acquisition and recycling
    let handles: Vec<_> = (0..8)
        .map(|_| {
            let p = Arc::clone(&pool);
            thread::spawn(move || {
                for _ in 0..100 {
                    let mut buf = p.acquire(1024); // Medium bucket
                    assert_eq!(buf.tier(), BucketTier::Medium);
                    buf.extend_from_slice(b"TEST_HEADER_16B_DATA_PAYLOAD_CHUNK");

                    let sub = buf.slice(0, 16).unwrap();
                    assert_eq!(sub, b"TEST_HEADER_16B_");

                    let prefix = buf.split_prefix(16).unwrap();
                    assert_eq!(prefix, b"TEST_HEADER_16B_");
                    assert_eq!(buf.as_slice(), b"DATA_PAYLOAD_CHUNK");
                }
            })
        })
        .collect();

    for h in handles {
        h.join().unwrap();
    }

    let stats = pool.get_stats();
    assert_eq!(stats.active_leased, 0);
    assert_eq!(stats.allocations, 800);
    assert!(stats.recycles > 0 && stats.recycles <= stats.allocations);

    // Bounded capacity check
    let (s, m, l, h) = pool.bucket_depths();
    assert!(s <= BucketTier::Small.max_pool_capacity());
    assert!(m <= BucketTier::Medium.max_pool_capacity());
    assert!(l <= BucketTier::Large.max_pool_capacity());
    assert!(h <= BucketTier::Huge.max_pool_capacity());
}

#[test]
fn test_adversarial_capabilities_probing_and_filtering() {
    let registry = CapabilityRegistry::new();

    // Populate registry with 50 synthetic nodes
    for i in 1..=50 {
        let mut caps = NodeCapabilities::default();
        caps.hardware.ram_available_kb = (i as u64) * 512 * 1024;
        caps.vram.vram_available_mb = if i % 5 == 0 { i * 512 } else { 0 };
        caps.has_gpio = i % 2 == 0;
        caps.has_i2c = i % 3 == 0;

        let payload = NodeAnnouncePayload::new(i, format!("edge-node-{:02}", i), caps);
        registry.register_announce(payload, 1000);
    }

    // Filter nodes with VRAM >= 2048 MB AND GPIO == true
    let matched = registry.find_eligible_nodes(1024, 2048, false, false, true, false);
    for node_id in &matched {
        let caps = registry.get_capabilities(*node_id).unwrap();
        assert!(caps.vram.vram_available_mb >= 2048);
        assert!(caps.has_gpio);
    }
    assert!(!matched.is_empty());
}

#[test]
fn test_adversarial_ble_mesh_bootstrap_handshake_tamper() {
    let adapter: Arc<dyn BleAdapter> = Arc::new(MockBleAdapter::new());
    let bootstrap = BleMeshBootstrap::new(77, Arc::clone(&adapter));
    bootstrap.start().unwrap();

    let creds = ProvisioningPayload::new(
        "SecureMeshSSID".to_string(),
        "VerySecretKey123".to_string(),
        "cluster-token-xyz".to_string(),
        "10.0.0.1:8650".to_string(),
    );

    // Client provisioner prepares payload
    provision_remote_node(adapter.as_ref(), &creds).unwrap();

    // Node accepts ECDH key
    let peer_pub = adapter
        .get_characteristic_value(BLE_CHAR_ECDH_UUID)
        .unwrap();
    bootstrap.handle_ecdh_exchange(&peer_pub).unwrap();

    // Tamper with ciphertext in Char 3
    let mut tampered = adapter
        .get_characteristic_value(BLE_CHAR_PROVISION_UUID)
        .unwrap();
    let mid = tampered.len() / 2;
    tampered[mid] ^= 0xAA;

    // Decryption must fail AEAD verification
    let res = bootstrap.handle_provisioning_write(&tampered);
    assert!(res.is_err());
    assert_ne!(bootstrap.state(), BleBootstrapState::Provisioned);
}

#[test]
fn test_adversarial_overlay_multi_transport_flapping_stress() {
    let config = HysteresisConfig {
        fail_strikes_threshold: 3,
        recovery_dwell_ms: 10_000,
        recovery_strikes_threshold: 3,
    };
    let router = MultiTransportRouter::new(Some(config));

    let mut endpoints = HashMap::new();
    endpoints.insert(TransportType::LanBroadcast, "192.168.1.10:8650".to_string());
    endpoints.insert(TransportType::WireGuard, "10.0.0.10:8650".to_string());
    endpoints.insert(TransportType::Tailscale, "100.64.0.10:8650".to_string());

    router.register_peer(301, endpoints);

    // 1. Failover to WireGuard on 3 strikes
    for i in 1..=3 {
        router.record_missed_heartbeat(301, TransportType::LanBroadcast, i * 1000);
    }
    assert!(router.is_peer_partitioned(301));
    assert_eq!(
        router.select_route(301).unwrap().0,
        TransportType::WireGuard
    );

    // 2. Intermittent LAN probes during dwell time (at t=4000, 5000, 6000)
    for t in [4000, 5000, 6000] {
        router.record_heartbeat(301, TransportType::LanBroadcast, 1, t);
        // Must stay WireGuard because dwell time (10s) hasn't elapsed!
        assert_eq!(
            router.select_route(301).unwrap().0,
            TransportType::WireGuard
        );
    }

    // 3. Drop LAN again at t=7000 (resets recovery timer)
    router.record_missed_heartbeat(301, TransportType::LanBroadcast, 7000);
    assert_eq!(
        router.select_route(301).unwrap().0,
        TransportType::WireGuard
    );

    // 4. Clean recovery at t=8000, 9000, 19000 (dwell elapsed = 11000ms >= 10000ms)
    router.record_heartbeat(301, TransportType::LanBroadcast, 1, 8000);
    router.record_heartbeat(301, TransportType::LanBroadcast, 1, 9000);
    router.record_heartbeat(301, TransportType::LanBroadcast, 1, 19000);

    // Restores LAN
    assert_eq!(
        router.select_route(301).unwrap().0,
        TransportType::LanBroadcast
    );
    assert!(!router.is_peer_partitioned(301));
}
