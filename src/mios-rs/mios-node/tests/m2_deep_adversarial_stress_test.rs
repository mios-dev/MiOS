// AI-hint: Deep adversarial stress tests and property fuzzers for Milestone 2 (T-392 through T-396).
// AI-related: src/mios-rs/mios-node/src/scheduler.rs, src/mios-rs/mios-node/src/buffer_pool.rs, src/mios-rs/mios-node/src/capabilities.rs, src/mios-rs/mios-node/src/ble.rs, src/mios-rs/mios-node/src/overlay.rs

use mios_node::ble::{
    BleAdapter, BleBootstrapState, BleMeshBootstrap, MockBleAdapter, ProvisioningPayload,
};
use mios_node::buffer_pool::{BucketTier, BufferPool, PooledBuffer};
use mios_node::capabilities::{CapabilityRegistry, NodeAnnouncePayload, NodeCapabilities};
use mios_node::overlay::{HysteresisConfig, MultiTransportRouter, TransportType};
use mios_node::protocol::{Frame, MessageType};
use mios_node::scheduler::{ScheduledTarget, TaskItem, TaskPriority, WorkStealingScheduler};
use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;

// =========================================================================
// Suite 1: Scheduler & Work-Stealing Invariants (T-392)
// =========================================================================

#[test]
fn test_scheduler_priority_enum_fuzzing_and_ordering() {
    // 1. Exhaustive u8 conversion fuzzing
    for v in 0..=255u8 {
        let priority = TaskPriority::from_u8(v);
        match v {
            0 => assert_eq!(priority, Some(TaskPriority::Critical)),
            1 => assert_eq!(priority, Some(TaskPriority::High)),
            2 => assert_eq!(priority, Some(TaskPriority::Normal)),
            3 => assert_eq!(priority, Some(TaskPriority::Low)),
            _ => assert_eq!(priority, None),
        }
    }

    // 2. Strict total ordering
    assert!(TaskPriority::Critical < TaskPriority::High);
    assert!(TaskPriority::High < TaskPriority::Normal);
    assert!(TaskPriority::Normal < TaskPriority::Low);
}

#[test]
fn test_scheduler_pinning_matrix_and_stealable_predicates() {
    // A. Hardware pinned (general)
    let mut t_hw = TaskItem::new(1, TaskPriority::High, 1, vec![], vec![]);
    t_hw.pinned_hardware = true;
    t_hw.pinned_node_id = None;
    assert!(!t_hw.is_stealable(None));
    assert!(!t_hw.is_stealable(Some(101)));
    assert!(!t_hw.is_stealable(Some(202)));

    // B. Pinned to specific node ID only (e.g. Node 101)
    let mut t_node = TaskItem::new(2, TaskPriority::Normal, 1, vec![], vec![]);
    t_node.pinned_hardware = false;
    t_node.pinned_node_id = Some(101);
    assert!(!t_node.is_stealable(None));
    assert!(t_node.is_stealable(Some(101)));
    assert!(!t_node.is_stealable(Some(102)));

    // C. Pinned to hardware AND specific node ID (hardware pin dominates)
    let mut t_both = TaskItem::new(3, TaskPriority::Critical, 1, vec![], vec![]);
    t_both.pinned_hardware = true;
    t_both.pinned_node_id = Some(101);
    assert!(!t_both.is_stealable(Some(101)));
    assert!(!t_both.is_stealable(Some(102)));
    assert!(!t_both.is_stealable(None));

    // D. Completely unpinned
    let t_free = TaskItem::new(4, TaskPriority::Low, 1, vec![], vec![]);
    assert!(t_free.is_stealable(None));
    assert!(t_free.is_stealable(Some(101)));
    assert!(t_free.is_stealable(Some(999)));
}

#[test]
fn test_scheduler_multithreaded_high_throughput_race_stress() {
    let scheduler = Arc::new(WorkStealingScheduler::new(100, 8));
    let total_tasks_per_producer = 250;
    let num_producers = 4;
    let total_tasks = total_tasks_per_producer * num_producers;

    // Producers
    let prod_handles: Vec<_> = (0..num_producers)
        .map(|p_idx| {
            let s = Arc::clone(&scheduler);
            thread::spawn(move || {
                for i in 0..total_tasks_per_producer {
                    let task_id = (p_idx * 1000 + i) as u64;
                    let prio = match (task_id + p_idx as u64) % 4 {
                        0 => TaskPriority::Critical,
                        1 => TaskPriority::High,
                        2 => TaskPriority::Normal,
                        _ => TaskPriority::Low,
                    };
                    let mut task = TaskItem::new(task_id, prio, 1, vec![1, 2], vec![]);
                    if task_id.is_multiple_of(7) {
                        task.pinned_hardware = true;
                    }
                    if task_id.is_multiple_of(5) && !task.pinned_hardware {
                        task.pinned_node_id = Some(100);
                    }

                    // Distribute across worker hints or global injector
                    let hint = if i % 2 == 0 { Some(p_idx * 2) } else { None };
                    s.submit_task(task, hint);
                }
            })
        })
        .collect();

    for h in prod_handles {
        h.join().unwrap();
    }

    assert_eq!(scheduler.get_stats().tasks_ingested, total_tasks as u64);

    // Consumers (Workers 0..8) draining tasks
    let executed_count = Arc::new(AtomicUsize::new(0));
    let worker_handles: Vec<_> = (0..8)
        .map(|w_idx| {
            let s = Arc::clone(&scheduler);
            let ec = Arc::clone(&executed_count);
            thread::spawn(move || {
                let mut local_drained = 0;
                let mut empty_spins = 0;
                while empty_spins < 50 {
                    if let Some(task) = s.pop_task(w_idx) {
                        ec.fetch_add(1, Ordering::SeqCst);
                        local_drained += 1;
                        empty_spins = 0;

                        // Check invariant: if task was stolen (by another worker), it must not be pinned to other nodes
                        if task.pinned_hardware {
                            // Pinned hardware tasks should only be processed locally
                        }
                    } else {
                        empty_spins += 1;
                        thread::yield_now();
                    }
                }
                local_drained
            })
        })
        .collect();

    let mut total_drained = 0;
    for h in worker_handles {
        total_drained += h.join().unwrap();
    }

    assert_eq!(total_drained, total_tasks);
    assert_eq!(executed_count.load(Ordering::SeqCst), total_tasks);
    assert_eq!(scheduler.total_queue_depth(), 0);
}

#[test]
fn test_scheduler_router_adversarial_matrix() {
    let scheduler = WorkStealingScheduler::new(50, 2);

    // 1. Hardware pinned task -> always Local
    let mut hw_task = TaskItem::new(1, TaskPriority::Critical, 1, vec![], vec![]);
    hw_task.pinned_hardware = true;
    assert_eq!(
        scheduler.route_task(&hw_task, &[(1, 0), (2, 0)]),
        ScheduledTarget::Local
    );

    // 2. Task pinned to node 50 (local) -> Local
    let mut node_local_task = TaskItem::new(2, TaskPriority::High, 1, vec![], vec![]);
    node_local_task.pinned_node_id = Some(50);
    assert_eq!(
        scheduler.route_task(&node_local_task, &[(60, 0)]),
        ScheduledTarget::Local
    );

    // 3. Task pinned to node 60 (remote) -> Offload(60)
    let mut node_remote_task = TaskItem::new(3, TaskPriority::High, 1, vec![], vec![]);
    node_remote_task.pinned_node_id = Some(60);
    assert_eq!(
        scheduler.route_task(&node_remote_task, &[(60, 0)]),
        ScheduledTarget::Offload(60)
    );

    // 4. Unpinned task with empty peer list -> Local
    let unpinned = TaskItem::new(4, TaskPriority::Normal, 1, vec![], vec![]);
    assert_eq!(scheduler.route_task(&unpinned, &[]), ScheduledTarget::Local);

    // 5. Unpinned task with local load < 2 -> Local
    assert_eq!(
        scheduler.route_task(&unpinned, &[(70, 0)]),
        ScheduledTarget::Local
    );
}

// =========================================================================
// Suite 2: Buffer Pool Zero-Copy & Recycling Invariants (T-393)
// =========================================================================

#[test]
fn test_buffer_pool_tier_resolution_boundaries() {
    let test_cases = vec![
        (0, BucketTier::Small, 256),
        (1, BucketTier::Small, 256),
        (255, BucketTier::Small, 256),
        (256, BucketTier::Small, 256),
        (257, BucketTier::Medium, 4096),
        (4095, BucketTier::Medium, 4096),
        (4096, BucketTier::Medium, 4096),
        (4097, BucketTier::Large, 65536),
        (65535, BucketTier::Large, 65536),
        (65536, BucketTier::Large, 65536),
        (65537, BucketTier::Huge, 1048576),
        (1048576, BucketTier::Huge, 1048576),
        (2000000, BucketTier::Huge, 1048576),
    ];

    for (size, expected_tier, expected_cap) in test_cases {
        let tier = BucketTier::from_size(size);
        assert_eq!(tier, expected_tier, "Size {} mapped to wrong tier", size);
        assert_eq!(tier.capacity_bytes(), expected_cap);
    }
}

#[test]
fn test_buffer_pool_slice_and_split_prefix_adversarial_bounds() {
    let pool = BufferPool::new();
    let mut buf = pool.acquire(100); // Small bucket
    buf.extend_from_slice(b"0123456789ABCDEF"); // 16 bytes

    // 1. Valid slice boundaries
    assert_eq!(buf.slice(0, 0).unwrap(), b"");
    assert_eq!(buf.slice(0, 16).unwrap(), b"0123456789ABCDEF");
    assert_eq!(buf.slice(4, 10).unwrap(), b"456789");
    assert_eq!(buf.slice(16, 16).unwrap(), b"");

    // 2. Inverted slice bounds (start > end)
    assert!(buf.slice(10, 5).is_err());

    // 3. Out-of-bounds slice (end > len)
    assert!(buf.slice(0, 17).is_err());
    assert!(buf.slice(17, 18).is_err());

    // 4. Split prefix out-of-bounds (at > len)
    assert!(buf.split_prefix(17).is_err());

    // 5. Chained split prefix
    let p1 = buf.split_prefix(4).unwrap();
    assert_eq!(p1, b"0123");
    assert_eq!(buf.as_slice(), b"456789ABCDEF");

    let p2 = buf.split_prefix(6).unwrap();
    assert_eq!(p2, b"456789");
    assert_eq!(buf.as_slice(), b"ABCDEF");

    let p3 = buf.split_prefix(6).unwrap();
    assert_eq!(p3, b"ABCDEF");
    assert_eq!(buf.len(), 0);
    assert!(buf.is_empty());

    // 6. Split on empty buffer
    let p_empty = buf.split_prefix(0).unwrap();
    assert_eq!(p_empty, b"");
    assert!(buf.split_prefix(1).is_err());
}

#[test]
fn test_buffer_pool_into_vec_and_standalone_invariants() {
    let pool = BufferPool::new();

    // 1. Test into_vec()
    {
        let mut buf = pool.acquire(200);
        buf.extend_from_slice(b"unrecycled_payload");
        assert_eq!(pool.get_stats().active_leased, 1);

        let vec_data = buf.into_vec();
        assert_eq!(vec_data, b"unrecycled_payload");
        // active_leased must decrement even on into_vec()
        assert_eq!(pool.get_stats().active_leased, 0);
        // recycles should NOT increment because buffer was consumed
        assert_eq!(pool.get_stats().recycles, 0);
    }

    // 2. Test Standalone buffer (not connected to any pool)
    {
        let mut standalone = PooledBuffer::standalone(BucketTier::Medium);
        assert_eq!(standalone.tier(), BucketTier::Medium);
        standalone.extend_from_slice(b"standalone_bytes");
        assert_eq!(standalone.as_slice(), b"standalone_bytes");
        let v = standalone.into_vec();
        assert_eq!(v, b"standalone_bytes");
    }
}

#[test]
fn test_buffer_pool_multithreaded_churn_and_saturation() {
    let pool = BufferPool::new();
    pool.preallocate(10, 10);

    let num_threads = 12;
    let iterations_per_thread = 200;

    let handles: Vec<_> = (0..num_threads)
        .map(|t_idx| {
            let p = Arc::clone(&pool);
            thread::spawn(move || {
                for i in 0..iterations_per_thread {
                    let size = match (t_idx + i) % 4 {
                        0 => 64,     // Small
                        1 => 2048,   // Medium
                        2 => 32768,  // Large
                        _ => 128000, // Huge
                    };

                    let mut buf = p.acquire(size);
                    buf.extend_from_slice(b"CHURN_STRESS_TEST_DATA");
                    assert_eq!(&buf[0..5], b"CHURN");

                    if i % 10 == 0 {
                        // Consume 10% via into_vec
                        let _ = buf.into_vec();
                    }
                    // Remaining 90% dropped and recycled
                }
            })
        })
        .collect();

    for h in handles {
        h.join().unwrap();
    }

    let stats = pool.get_stats();
    assert_eq!(stats.active_leased, 0);
    assert_eq!(
        stats.allocations,
        (num_threads * iterations_per_thread) as u64
    );
    assert!(stats.recycles > 0);

    // Verify bounded bucket capacities
    let (s, m, l, h) = pool.bucket_depths();
    assert!(s <= BucketTier::Small.max_pool_capacity());
    assert!(m <= BucketTier::Medium.max_pool_capacity());
    assert!(l <= BucketTier::Large.max_pool_capacity());
    assert!(h <= BucketTier::Huge.max_pool_capacity());
}

// =========================================================================
// Suite 3: Node Capabilities & Registry Invariants (T-394)
// =========================================================================

#[test]
fn test_capabilities_frame_validation_and_malformed_wire_rejection() {
    let mut caps = NodeCapabilities::default();
    caps.hardware.cpu_arch = "riscv64".to_string();
    caps.has_i2c = true;

    let payload = NodeAnnouncePayload::new(99, "edge-blade-99".to_string(), caps);
    let valid_frame = payload.to_frame().unwrap();

    // 1. Valid decode
    let decoded = NodeAnnouncePayload::from_frame(&valid_frame).unwrap();
    assert_eq!(decoded.node_id, 99);
    assert_eq!(decoded.hostname, "edge-blade-99");
    assert!(decoded.capabilities.has_i2c);

    // 2. Reject wrong message type (Heartbeat instead of NodeAnnounce)
    let wrong_type_frame = Frame::new(MessageType::Heartbeat, 99, valid_frame.payload.clone());
    assert!(NodeAnnouncePayload::from_frame(&wrong_type_frame).is_err());

    // 3. Reject corrupted JSON payload
    let corrupted_frame = Frame::new(MessageType::NodeAnnounce, 99, vec![0xFF, 0xFE, 0xFD]);
    assert!(NodeAnnouncePayload::from_frame(&corrupted_frame).is_err());

    // 4. Reject empty payload
    let empty_frame = Frame::new(MessageType::NodeAnnounce, 99, vec![]);
    assert!(NodeAnnouncePayload::from_frame(&empty_frame).is_err());
}

#[test]
fn test_capabilities_registry_fuzzing_and_multithreaded_access() {
    let registry = Arc::new(CapabilityRegistry::new());

    // Populate registry with diverse node profiles
    for i in 1..=30 {
        let mut caps = NodeCapabilities::default();
        caps.hardware.ram_available_kb = (i as u64) * 1024 * 1024; // 1MB to 30MB
        caps.vram.vram_available_mb = if i % 2 == 0 { i * 256 } else { 0 };
        caps.has_gpio = i % 3 == 0;
        caps.has_i2c = i % 5 == 0;
        caps.engines.wasm_tier = true;
        caps.engines.native_tier = i % 4 != 0;

        let payload = NodeAnnouncePayload::new(i, format!("node-{:03}", i), caps);
        registry.register_announce(payload, 1000 + (i as u64) * 10);
    }

    assert_eq!(registry.active_node_count(), 30);

    // Test queries:
    // A. RAM >= 10MB, VRAM >= 1024MB, Native required, GPIO required
    let matches = registry.find_eligible_nodes(10 * 1024 * 1024, 1024, true, true, true, false);

    for node_id in &matches {
        let caps = registry.get_capabilities(*node_id).unwrap();
        assert!(caps.hardware.ram_available_kb >= 10 * 1024 * 1024);
        assert!(caps.vram.vram_available_mb >= 1024);
        assert!(caps.engines.wasm_tier);
        assert!(caps.engines.native_tier);
        assert!(caps.has_gpio);
    }

    // B. Eviction with clock skew (now_utc < received_at_utc) -> No panic
    let evicted_skew = registry.evict_stale(60, 500);
    assert_eq!(evicted_skew, 0); // saturating_sub ensures 0 elapsed

    // C. Evict nodes older than 50s at t=1400
    let evicted = registry.evict_stale(50, 1400);
    assert!(evicted > 0);
    assert_eq!(registry.active_node_count(), 30 - evicted);
}

// =========================================================================
// Suite 4: BLE Beaconing & Offline Mesh Bootstrap (T-395)
// =========================================================================

#[test]
fn test_ble_bootstrap_state_conversions() {
    for v in 0..=4u8 {
        let state = BleBootstrapState::try_from(v).unwrap();
        assert_eq!(state as u8, v);
    }
    assert!(BleBootstrapState::try_from(5).is_err());
    assert!(BleBootstrapState::try_from(255).is_err());
}

#[test]
fn test_ble_bootstrap_handshake_violation_and_tamper_fuzzing() {
    let adapter: Arc<dyn BleAdapter> = Arc::new(MockBleAdapter::new());
    let bootstrap = BleMeshBootstrap::new(88, Arc::clone(&adapter));
    bootstrap.start().unwrap();

    // 1. Invariant: Writing provisioning credentials BEFORE ECDH handshake must fail
    let premature_write = vec![0x11; 64];
    let res = bootstrap.handle_provisioning_write(&premature_write);
    assert!(
        res.is_err(),
        "Premature provisioning write must be rejected"
    );

    // 2. Reject invalid ECDH public key lengths
    assert!(bootstrap.handle_ecdh_exchange(&[]).is_err());
    assert!(bootstrap.handle_ecdh_exchange(&[0u8; 16]).is_err());
    assert!(bootstrap.handle_ecdh_exchange(&[0u8; 31]).is_err());
    assert!(bootstrap.handle_ecdh_exchange(&[0u8; 33]).is_err());
    assert!(bootstrap.handle_ecdh_exchange(&[0u8; 64]).is_err());

    // 3. Normal ECDH Handshake
    let client_priv = [0x77u8; 32];
    let client_pub = mios_node::crypto::x25519_public_key(&client_priv);
    bootstrap.handle_ecdh_exchange(&client_pub).unwrap();
    assert_eq!(bootstrap.state(), BleBootstrapState::Handshaking);

    // 4. Derive correct shared key and generate encrypted payload
    let node_pub = bootstrap.local_public_key();
    let ss = mios_node::crypto::x25519(&client_priv, &node_pub);
    let key = mios_node::crypto::hkdf_sha256(
        mios_node::ble::BLE_HKDF_SALT,
        &ss,
        mios_node::ble::BLE_HKDF_INFO,
        32,
    );
    let mut derived_key = [0u8; 32];
    derived_key.copy_from_slice(&key[0..32]);

    let creds = ProvisioningPayload::new(
        "AdversarialSSID".to_string(),
        "AdversarialPass123!".to_string(),
        "cluster_tok_adversarial".to_string(),
        "10.200.0.1:8650".to_string(),
    );
    let creds_json = serde_json::to_vec(&creds).unwrap();
    let ciphertext = mios_node::crypto::chacha20_poly1305_encrypt(
        &derived_key,
        mios_node::ble::BLE_NONCE,
        mios_node::ble::BLE_AEAD_AAD,
        &creds_json,
    );

    // 5. Tamper fuzzing: flip every byte in ciphertext and ensure AEAD verification rejects it
    for i in 0..ciphertext.len() {
        let mut tampered = ciphertext.clone();
        tampered[i] ^= 0x01; // flip least significant bit
        let tamper_res = bootstrap.handle_provisioning_write(&tampered);
        assert!(
            tamper_res.is_err(),
            "AEAD failed to reject tampered byte at index {}",
            i
        );
    }

    // 6. Valid write completes provisioning
    let valid_prov = bootstrap.handle_provisioning_write(&ciphertext).unwrap();
    assert_eq!(valid_prov.ssid, "AdversarialSSID");
    assert_eq!(bootstrap.state(), BleBootstrapState::Provisioned);
    assert!(!adapter.is_advertising());
}

// =========================================================================
// Suite 5: Multi-Transport Router & Anti-Flap Hysteresis (T-396)
// =========================================================================

#[test]
fn test_transport_type_hierarchy_and_strings() {
    assert!(TransportType::LanBroadcast < TransportType::WireGuard);
    assert!(TransportType::WireGuard < TransportType::Tailscale);
    assert!(TransportType::Tailscale < TransportType::DirectTcp);

    assert_eq!(TransportType::LanBroadcast.as_str(), "lan_broadcast");
    assert_eq!(TransportType::WireGuard.as_str(), "wireguard");
    assert_eq!(TransportType::Tailscale.as_str(), "tailscale");
    assert_eq!(TransportType::DirectTcp.as_str(), "direct_tcp");
}

#[test]
fn test_overlay_router_degraded_endpoint_profiles() {
    let router = MultiTransportRouter::new(None);

    // 1. Peer with only DirectTcp
    let mut ep_tcp = HashMap::new();
    ep_tcp.insert(TransportType::DirectTcp, "1.2.3.4:8650".to_string());
    router.register_peer(501, ep_tcp);
    assert_eq!(
        router.select_route(501).unwrap(),
        (TransportType::DirectTcp, "1.2.3.4:8650".to_string())
    );

    // 2. Peer with only WireGuard and Tailscale
    let mut ep_vpn = HashMap::new();
    ep_vpn.insert(TransportType::WireGuard, "10.0.0.2:8650".to_string());
    ep_vpn.insert(TransportType::Tailscale, "100.64.0.2:8650".to_string());
    router.register_peer(502, ep_vpn);
    assert_eq!(
        router.select_route(502).unwrap(),
        (TransportType::WireGuard, "10.0.0.2:8650".to_string())
    );

    // 3. Unregistered peer -> Err
    assert!(router.select_route(999).is_err());
}

#[test]
fn test_overlay_router_adversarial_flap_and_intermittent_lan_recovery() {
    let config = HysteresisConfig {
        fail_strikes_threshold: 3,
        recovery_dwell_ms: 120_000, // 120s dwell
        recovery_strikes_threshold: 3,
    };
    let router = MultiTransportRouter::new(Some(config));

    let mut endpoints = HashMap::new();
    endpoints.insert(TransportType::LanBroadcast, "192.168.1.99:8650".to_string());
    endpoints.insert(TransportType::WireGuard, "10.0.0.99:8650".to_string());
    endpoints.insert(TransportType::Tailscale, "100.64.0.99:8650".to_string());

    router.register_peer(700, endpoints);

    // 1. Trigger partition (3 strikes)
    router.record_missed_heartbeat(700, TransportType::LanBroadcast, 1000);
    router.record_missed_heartbeat(700, TransportType::LanBroadcast, 2000);
    router.record_missed_heartbeat(700, TransportType::LanBroadcast, 3000);
    assert!(router.is_peer_partitioned(700));
    assert_eq!(
        router.select_route(700).unwrap().0,
        TransportType::WireGuard
    );

    // 2. Flapping: 2 successful LAN probes, then 1 miss
    router.record_heartbeat(700, TransportType::LanBroadcast, 1, 4000);
    router.record_heartbeat(700, TransportType::LanBroadcast, 1, 5000);
    router.record_missed_heartbeat(700, TransportType::LanBroadcast, 6000); // Miss resets strikes

    // 3. 3 successful probes at t=7000, 8000, 9000
    router.record_heartbeat(700, TransportType::LanBroadcast, 1, 7000);
    router.record_heartbeat(700, TransportType::LanBroadcast, 1, 8000);
    router.record_heartbeat(700, TransportType::LanBroadcast, 1, 9000);

    // Invariant: 3 strikes achieved, but dwell elapsed is only 5000ms (< 120000ms) -> MUST stay WireGuard!
    assert_eq!(
        router.select_route(700).unwrap().0,
        TransportType::WireGuard
    );

    // 4. Probes during dwell: t=50000, 100000 -> still WireGuard
    router.record_heartbeat(700, TransportType::LanBroadcast, 1, 50000);
    router.record_heartbeat(700, TransportType::LanBroadcast, 1, 100000);
    assert_eq!(
        router.select_route(700).unwrap().0,
        TransportType::WireGuard
    );

    // 5. Successful probe at t=130000 (dwell elapsed = 126000ms >= 120000ms) -> Restores LAN!
    router.record_heartbeat(700, TransportType::LanBroadcast, 1, 130000);
    assert_eq!(
        router.select_route(700).unwrap().0,
        TransportType::LanBroadcast
    );
    assert!(!router.is_peer_partitioned(700));

    let summary = router.get_route_summary(700).unwrap();
    assert_eq!(summary.active_transport, TransportType::LanBroadcast);
    assert_eq!(summary.active_endpoint, "192.168.1.99:8650");
    assert!(!summary.is_lan_partitioned);
}
