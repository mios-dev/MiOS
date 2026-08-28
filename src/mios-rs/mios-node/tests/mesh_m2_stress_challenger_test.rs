// AI-hint: Milestone 2 Empirical Challenger Stress & Adversarial Test Suite.
// AI-related: src/mios-rs/mios-node/src/scheduler.rs, src/mios-rs/mios-node/src/buffer_pool.rs, src/mios-rs/mios-node/src/capabilities.rs, src/mios-rs/mios-node/src/ble.rs, src/mios-rs/mios-node/src/overlay.rs

use mios_node::ble::{
    provision_remote_node, BleAdapter, BleBootstrapState, BleMeshBootstrap, MockBleAdapter,
    ProvisioningPayload, BLE_CHAR_ECDH_UUID, BLE_CHAR_PROVISION_UUID,
};
use mios_node::buffer_pool::BufferPool;
use mios_node::capabilities::{CapabilityRegistry, NodeAnnouncePayload, NodeCapabilities};
use mios_node::overlay::{HysteresisConfig, MultiTransportRouter, TransportType};
use mios_node::protocol::{Frame, MessageType};
use mios_node::scheduler::{ScheduledTarget, TaskItem, TaskPriority, WorkStealingScheduler};
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use std::thread;
use std::time::Duration;

// =========================================================================
// 1. T-392: Stress & Invariant Tests for Work-Stealing Scheduler
// =========================================================================

#[test]
fn test_stress_concurrent_work_stealing_with_pinned_invariants() {
    const NUM_WORKERS: usize = 8;
    const NUM_TASKS: usize = 2000;
    let scheduler = Arc::new(WorkStealingScheduler::new(101, NUM_WORKERS));

    // Submit tasks with mixed priorities and pin configurations
    for i in 0..NUM_TASKS {
        let prio = match i % 4 {
            0 => TaskPriority::Critical,
            1 => TaskPriority::High,
            2 => TaskPriority::Normal,
            _ => TaskPriority::Low,
        };

        let mut task = TaskItem::new(
            i as u64,
            prio,
            1,
            vec![(i % 255) as u8; 32],
            vec![(i % 128) as u8; 16],
        );

        if i % 3 == 0 {
            task.pinned_hardware = true;
        } else if i % 5 == 0 {
            task.pinned_node_id = Some(101); // local node
        } else if i % 7 == 0 {
            task.pinned_node_id = Some(999); // foreign node
        }

        let worker_hint = Some(i % NUM_WORKERS);
        scheduler.submit_task(task, worker_hint);
    }

    let completed_tasks = Arc::new(AtomicUsize::new(0));
    let stop_signal = Arc::new(AtomicBool::new(false));

    // Spawn worker threads that continuously pop tasks
    let mut handles = Vec::new();
    for w_id in 0..NUM_WORKERS {
        let sched = Arc::clone(&scheduler);
        let done = Arc::clone(&completed_tasks);
        let stop = Arc::clone(&stop_signal);

        handles.push(thread::spawn(move || {
            while !stop.load(Ordering::Relaxed) {
                if let Some(task) = sched.pop_task(w_id) {
                    // Invariant check: If pinned to hardware, must be executed on local scheduler
                    if task.pinned_hardware {
                        assert!(
                            !task.is_stealable(Some(999)),
                            "Hardware pinned task must not be stealable by foreign node"
                        );
                    }
                    // Invariant check: If pinned to node 999, it should never be popped by node 101 unless local pop
                    if let Some(target) = task.pinned_node_id {
                        if target != 101 {
                            assert!(
                                !task.is_stealable(Some(101)),
                                "Task pinned to node 999 must not be stealable by node 101"
                            );
                        }
                    }
                    done.fetch_add(1, Ordering::SeqCst);
                } else {
                    thread::yield_now();
                }
            }
        }));
    }

    // Spawn 2 simulated remote peer stealers concurrently
    for peer_id in [201, 202] {
        let sched = Arc::clone(&scheduler);
        let done = Arc::clone(&completed_tasks);
        let stop = Arc::clone(&stop_signal);

        handles.push(thread::spawn(move || {
            while !stop.load(Ordering::Relaxed) {
                let stolen = sched.handle_remote_steal_request(peer_id, 4);
                for task in &stolen {
                    assert!(
                        !task.pinned_hardware,
                        "CRITICAL: Remote peer {} stole hardware-pinned task {}",
                        peer_id, task.task_id
                    );
                    if let Some(target) = task.pinned_node_id {
                        assert_eq!(
                            target, peer_id,
                            "Remote peer {} stole task pinned to node {}",
                            peer_id, target
                        );
                    }
                }
                done.fetch_add(stolen.len(), Ordering::SeqCst);
                thread::yield_now();
            }
        }));
    }

    // Wait until all tasks are consumed or timeout
    let start = std::time::Instant::now();
    while completed_tasks.load(Ordering::SeqCst) < NUM_TASKS
        && start.elapsed() < Duration::from_secs(5)
    {
        thread::sleep(Duration::from_millis(10));
    }

    stop_signal.store(true, Ordering::Relaxed);
    for h in handles {
        let _ = h.join();
    }

    let stats = scheduler.get_stats();
    assert_eq!(stats.tasks_ingested, NUM_TASKS as u64);
    assert_eq!(completed_tasks.load(Ordering::SeqCst), NUM_TASKS);
}

#[test]
fn test_scheduler_route_task_extreme_load_and_boundaries() {
    let scheduler = WorkStealingScheduler::new(100, 2);

    // Empty scheduler + empty peer loads -> Local
    let t_normal = TaskItem::new(1, TaskPriority::Normal, 1, vec![], vec![]);
    assert_eq!(scheduler.route_task(&t_normal, &[]), ScheduledTarget::Local);

    // Pinned to foreign node -> Offload to that node
    let mut t_foreign = TaskItem::new(2, TaskPriority::Normal, 1, vec![], vec![]);
    t_foreign.pinned_node_id = Some(500);
    assert_eq!(
        scheduler.route_task(&t_foreign, &[(500, 10)]),
        ScheduledTarget::Offload(500)
    );

    // Hardware pinned task -> Local even if foreign pinned is set or peer load is zero
    let mut t_pinned_hw = TaskItem::new(3, TaskPriority::Critical, 1, vec![], vec![]);
    t_pinned_hw.pinned_hardware = true;
    t_pinned_hw.pinned_node_id = Some(500);
    assert_eq!(
        scheduler.route_task(&t_pinned_hw, &[(500, 0)]),
        ScheduledTarget::Local
    );
}

// =========================================================================
// 2. T-393: Stress & Invariant Tests for Zero-Copy Buffer Pool
// =========================================================================

#[test]
fn test_stress_buffer_pool_concurrency_and_into_vec_accounting() {
    let pool = BufferPool::new();
    pool.preallocate(64, 32);

    const NUM_THREADS: usize = 16;
    const OPS_PER_THREAD: usize = 200;

    let handles: Vec<_> = (0..NUM_THREADS)
        .map(|tid| {
            let p = Arc::clone(&pool);
            thread::spawn(move || {
                for i in 0..OPS_PER_THREAD {
                    let size = match (tid + i) % 4 {
                        0 => 128,     // Small
                        1 => 2048,    // Medium
                        2 => 32768,   // Large
                        _ => 200_000, // Huge
                    };

                    let mut buf = p.acquire(size);
                    let payload = vec![(i % 256) as u8; 64];
                    buf.extend_from_slice(&payload);

                    // Slice testing
                    let sub = buf.slice(0, 32).unwrap();
                    assert_eq!(sub, &payload[0..32]);

                    // Split prefix testing
                    let pref = buf.split_prefix(16).unwrap();
                    assert_eq!(pref, &payload[0..16]);
                    assert_eq!(buf.len(), 48);

                    // 50% RAII drop recycling, 50% consumption via into_vec
                    if (tid + i) % 2 == 0 {
                        let consumed_vec = buf.into_vec();
                        assert_eq!(consumed_vec.len(), 48);
                    }
                    // else normal drop
                }
            })
        })
        .collect();

    for h in handles {
        h.join().unwrap();
    }

    let stats = pool.get_stats();
    assert_eq!(
        stats.active_leased, 0,
        "Active leased count leaked! Stats: {:?}",
        stats
    );
    assert_eq!(stats.allocations, (NUM_THREADS * OPS_PER_THREAD) as u64);
    assert_eq!(stats.allocations, stats.pool_hits + stats.pool_misses);
}

#[test]
fn test_adversarial_buffer_pool_slicing_and_split_boundaries() {
    let pool = BufferPool::new();
    let mut buf = pool.acquire(512); // Medium tier
    buf.extend_from_slice(b"0123456789ABCDEF"); // 16 bytes

    // 1. Exact range 0..16
    assert_eq!(buf.slice(0, 16).unwrap(), b"0123456789ABCDEF");

    // 2. Empty range 5..5
    assert_eq!(buf.slice(5, 5).unwrap(), b"");

    // 3. Out of bounds start > end
    assert!(buf.slice(10, 5).is_err());

    // 4. Out of bounds end > len
    assert!(buf.slice(0, 17).is_err());

    // 5. Split prefix at 0
    let pref0 = buf.split_prefix(0).unwrap();
    assert!(pref0.is_empty());
    assert_eq!(buf.len(), 16);

    // 6. Split prefix out of bounds
    assert!(buf.split_prefix(17).is_err());

    // 7. Split prefix exact len
    let pref_all = buf.split_prefix(16).unwrap();
    assert_eq!(pref_all, b"0123456789ABCDEF");
    assert_eq!(buf.len(), 0);
    assert!(buf.is_empty());
}

// =========================================================================
// 3. T-394: Adversarial Capability Probing, Filtering & Corrupted Payloads
// =========================================================================

#[test]
fn test_adversarial_capability_registry_extreme_queries() {
    let registry = CapabilityRegistry::new();

    // Query on empty registry
    let empty_res = registry.find_eligible_nodes(1024, 1024, true, true, true, true);
    assert!(empty_res.is_empty());
    assert_eq!(registry.active_node_count(), 0);
    assert_eq!(registry.evict_stale(100, 1000), 0);

    // Add node with maximum capabilities
    let mut max_caps = NodeCapabilities::default();
    max_caps.hardware.ram_available_kb = 64 * 1024 * 1024;
    max_caps.vram.vram_available_mb = 32768;
    max_caps.has_gpio = true;
    max_caps.has_i2c = true;

    let payload = NodeAnnouncePayload::new(99, "behemoth-01".to_string(), max_caps);
    registry.register_announce(payload, 5000);

    // Query matching
    let matched = registry.find_eligible_nodes(32 * 1024 * 1024, 16384, true, true, true, true);
    assert_eq!(matched, vec![99]);

    // Query with unreachable criteria
    let impossible = registry.find_eligible_nodes(u64::MAX, u32::MAX, true, true, true, true);
    assert!(impossible.is_empty());

    // Stale eviction with timestamp before last_seen (no underflow)
    let evicted_before = registry.evict_stale(100, 4000);
    assert_eq!(evicted_before, 0);

    // Eviction after TTL
    let evicted_after = registry.evict_stale(100, 5200);
    assert_eq!(evicted_after, 1);
    assert_eq!(registry.active_node_count(), 0);
}

#[test]
fn test_adversarial_node_announce_corrupt_frame_decoding() {
    // 1. Wrong message type in frame (Heartbeat 0x01 instead of NodeAnnounce 0x02)
    let bad_header_frame = Frame::new(MessageType::Heartbeat, 42, vec![b'{', b'}']);
    let err = NodeAnnouncePayload::from_frame(&bad_header_frame);
    assert!(err.is_err());

    // 2. Corrupted JSON payload
    let corrupt_json_frame = Frame::new(
        MessageType::NodeAnnounce,
        42,
        b"{\"node_id\": 42, BAD_JSON".to_vec(),
    );
    assert!(NodeAnnouncePayload::from_frame(&corrupt_json_frame).is_err());

    // 3. Empty payload
    let empty_frame = Frame::new(MessageType::NodeAnnounce, 42, vec![]);
    assert!(NodeAnnouncePayload::from_frame(&empty_frame).is_err());
}

// =========================================================================
// 4. T-395: Adversarial BLE AEAD Bit-Flip Fuzzing & Invalid Keys
// =========================================================================

#[test]
fn test_adversarial_ble_bit_flip_fuzzing_and_key_validation() {
    let adapter: Arc<dyn BleAdapter> = Arc::new(MockBleAdapter::new());
    let bootstrap = BleMeshBootstrap::new(88, Arc::clone(&adapter));
    bootstrap.start().unwrap();

    // 1. Invalid ECDH public key lengths
    assert!(bootstrap.handle_ecdh_exchange(&[]).is_err());
    assert!(bootstrap.handle_ecdh_exchange(&[0u8; 16]).is_err());
    assert!(bootstrap.handle_ecdh_exchange(&[0u8; 31]).is_err());
    assert!(bootstrap.handle_ecdh_exchange(&[0u8; 33]).is_err());
    assert!(bootstrap.handle_ecdh_exchange(&[0u8; 64]).is_err());

    // 2. Premature provisioning write without handshake
    assert!(bootstrap.handle_provisioning_write(&[0u8; 32]).is_err());

    // 3. Execute legitimate handshake
    let creds = ProvisioningPayload::new(
        "FuzzSSID".to_string(),
        "FuzzPassword123".to_string(),
        "token-999".to_string(),
        "10.0.0.5:8650".to_string(),
    );
    provision_remote_node(adapter.as_ref(), &creds).unwrap();

    let peer_pub = adapter
        .get_characteristic_value(BLE_CHAR_ECDH_UUID)
        .unwrap();
    bootstrap.handle_ecdh_exchange(&peer_pub).unwrap();

    let valid_ciphertext = adapter
        .get_characteristic_value(BLE_CHAR_PROVISION_UUID)
        .unwrap();
    assert!(!valid_ciphertext.is_empty());

    // 4. Exhaustive single-byte bit flip fuzzing across all ciphertext bytes
    for i in 0..valid_ciphertext.len() {
        let mut corrupted = valid_ciphertext.clone();
        corrupted[i] ^= 0x01; // flip 1 bit

        let res = bootstrap.handle_provisioning_write(&corrupted);
        assert!(
            res.is_err(),
            "Poly1305 MAC check passed on corrupted byte index {}!",
            i
        );
    }

    // 5. Truncated ciphertext payloads (less than 16B MAC tag)
    for len in 0..16 {
        let truncated = &valid_ciphertext[0..len];
        assert!(bootstrap.handle_provisioning_write(truncated).is_err());
    }

    // 6. Valid ciphertext succeeds
    let prov = bootstrap
        .handle_provisioning_write(&valid_ciphertext)
        .unwrap();
    assert_eq!(prov.ssid, "FuzzSSID");
    assert_eq!(bootstrap.state(), BleBootstrapState::Provisioned);
}

// =========================================================================
// 5. T-396: Stress & Boundary Tests for Multi-Transport Flapping & Hysteresis
// =========================================================================

#[test]
fn test_stress_overlay_flapping_and_hysteresis_boundaries() {
    let config = HysteresisConfig {
        fail_strikes_threshold: 3,
        recovery_dwell_ms: 10_000,
        recovery_strikes_threshold: 3,
    };
    let router = MultiTransportRouter::new(Some(config));

    let mut endpoints = HashMap::new();
    endpoints.insert(TransportType::LanBroadcast, "192.168.1.20:8650".to_string());
    endpoints.insert(TransportType::WireGuard, "10.0.0.20:8650".to_string());
    endpoints.insert(TransportType::Tailscale, "100.64.0.20:8650".to_string());
    endpoints.insert(TransportType::DirectTcp, "192.168.1.20:9000".to_string());

    router.register_peer(501, endpoints);

    // 1. Rapid alternating 1 miss, 1 hit -> LAN should NEVER failover (consecutive misses never hit 3)
    for i in 0..100 {
        let t = (i * 100) as u64;
        if i % 2 == 0 {
            router.record_missed_heartbeat(501, TransportType::LanBroadcast, t);
        } else {
            router.record_heartbeat(501, TransportType::LanBroadcast, 1, t);
        }
        assert_eq!(
            router.select_route(501).unwrap().0,
            TransportType::LanBroadcast,
            "Flapping caused false failover at iteration {}",
            i
        );
        assert!(!router.is_peer_partitioned(501));
    }

    // 2. Exact 3 consecutive misses triggers failover
    router.record_missed_heartbeat(501, TransportType::LanBroadcast, 10_000);
    router.record_missed_heartbeat(501, TransportType::LanBroadcast, 11_000);
    assert!(!router.is_peer_partitioned(501)); // 2 misses -> still LAN

    router.record_missed_heartbeat(501, TransportType::LanBroadcast, 12_000);
    assert!(router.is_peer_partitioned(501)); // 3 misses -> WireGuard
    assert_eq!(
        router.select_route(501).unwrap().0,
        TransportType::WireGuard
    );

    // 3. Recovery: 3 hits at t=13_000, 14_000, 15_000 (dwell is only 2000ms < 10000ms) -> Still WireGuard
    router.record_heartbeat(501, TransportType::LanBroadcast, 1, 13_000);
    router.record_heartbeat(501, TransportType::LanBroadcast, 1, 14_000);
    router.record_heartbeat(501, TransportType::LanBroadcast, 1, 15_000);
    assert_eq!(
        router.select_route(501).unwrap().0,
        TransportType::WireGuard
    );

    // 4. At t=22_999 (dwell = 9999ms < 10000ms) -> Still WireGuard
    router.record_heartbeat(501, TransportType::LanBroadcast, 1, 22_999);
    assert_eq!(
        router.select_route(501).unwrap().0,
        TransportType::WireGuard
    );

    // 5. At t=23_000 (dwell = 10000ms >= 10000ms) -> Restores LAN
    router.record_heartbeat(501, TransportType::LanBroadcast, 1, 23_000);
    assert_eq!(
        router.select_route(501).unwrap().0,
        TransportType::LanBroadcast
    );
    assert!(!router.is_peer_partitioned(501));

    // 6. Failover hierarchy test: If LAN fails and WireGuard fails -> Tailscale
    router.record_missed_heartbeat(501, TransportType::LanBroadcast, 25_000);
    router.record_missed_heartbeat(501, TransportType::LanBroadcast, 26_000);
    router.record_missed_heartbeat(501, TransportType::LanBroadcast, 27_000);
    assert_eq!(
        router.select_route(501).unwrap().0,
        TransportType::WireGuard
    );

    // WireGuard misses 3 strikes
    router.record_missed_heartbeat(501, TransportType::WireGuard, 28_000);
    router.record_missed_heartbeat(501, TransportType::WireGuard, 29_000);
    router.record_missed_heartbeat(501, TransportType::WireGuard, 30_000);
    // Route summary check
    let summary = router.get_route_summary(501).unwrap();
    assert_eq!(summary.node_id, 501);
    assert!(summary.is_lan_partitioned);
}
