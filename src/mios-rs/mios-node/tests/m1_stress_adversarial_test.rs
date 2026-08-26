// AI-hint: Milestone 1 Adversarial Empirical Stress Test Suite (T-389, T-390, T-391, T-400).
// AI-related: src/mios-rs/mios-node/src/hardware.rs, src/mios-rs/mios-node/src/cgroups.rs, src/mios-rs/mios-node/src/state_sync.rs, src/mios-rs/mios-node/src/watchdog.rs

use anyhow::Result;
use mios_node::cgroups::{
    filter_safe_worker_cores, AffinityPolicy, CgroupV2Controller, NodeResourceLimits,
    WorkerAffinityController,
};
use mios_node::hardware::{
    HardwareAllowlist, HardwareErrorCode, SandboxedHardwareController,
};
use mios_node::state_sync::{StateElement, StateStore};
use mios_node::watchdog::{MockWatchdogDriver, WatchdogConfig, WatchdogSupervisor};
use std::sync::{Arc, Mutex};
use std::thread;
use tempfile::NamedTempFile;

// =========================================================================
// Task 1 (T-389): Hardware HAL & Wasm Sandbox Allowlist Stress Tests
// =========================================================================

#[test]
fn test_stress_gpio_unauthorized_pins_and_boundaries() {
    let mut allowlist = HardwareAllowlist::default();
    allowlist.allowed_gpio_pins = [4, 17, 27, 22].into_iter().collect();
    allowlist.read_only_gpio_pins = [4].into_iter().collect();

    let (controller, mock) = SandboxedHardwareController::new_mock(allowlist);

    // Test extreme and unauthorized pin IDs
    let unauthorized_pins = [0, 1, 2, 3, 5, 18, 99, 255, 1024, 65535, u32::MAX];
    for &pin in &unauthorized_pins {
        // Read attempt
        let read_res = controller.mios_sys_gpio_read(pin);
        assert_eq!(
            read_res,
            Err(HardwareErrorCode::PermissionDenied),
            "Pin {} read must be denied",
            pin
        );

        // Write attempt
        let write_res = controller.mios_sys_gpio_write(pin, 1);
        assert_eq!(
            write_res,
            Err(HardwareErrorCode::PermissionDenied),
            "Pin {} write must be denied",
            pin
        );
    }

    // Mock driver should remain empty
    for &pin in &unauthorized_pins {
        assert_eq!(mock.get_mock_gpio(pin), None);
    }
}

#[test]
fn test_stress_gpio_read_only_violation() {
    let mut allowlist = HardwareAllowlist::default();
    allowlist.allowed_gpio_pins = [4, 17].into_iter().collect();
    allowlist.read_only_gpio_pins = [4].into_iter().collect();

    let (controller, mock) = SandboxedHardwareController::new_mock(allowlist);

    // Preset mock value on read-only pin 4
    mock.set_mock_gpio(4, 1);

    // Read should succeed
    assert_eq!(controller.mios_sys_gpio_read(4), Ok(1));

    // Write must fail with ReadOnlyPin
    assert_eq!(
        controller.mios_sys_gpio_write(4, 0),
        Err(HardwareErrorCode::ReadOnlyPin)
    );

    // Mock state must be preserved
    assert_eq!(mock.get_mock_gpio(4), Some(1));
}

#[test]
fn test_stress_i2c_bus_and_address_boundary_violations() {
    let mut allowlist = HardwareAllowlist::default();
    allowlist.allowed_i2c_buses = [1].into_iter().collect();
    allowlist.allowed_i2c_addresses = [0x48, 0x68].into_iter().collect();
    allowlist.max_i2c_transfer_len = 128;

    let (controller, mock) = SandboxedHardwareController::new_mock(allowlist);
    mock.set_mock_i2c_register(1, 0x68, 0x00, 0x42);

    let write_buf = [0x00u8];
    let mut read_buf = [0u8; 1];

    // Invalid Buses (0, 2, 255)
    for &bus in &[0u8, 2, 3, 255] {
        let res = controller.mios_sys_i2c_transfer(bus, 0x68, &write_buf, &mut read_buf);
        assert_eq!(res, Err(HardwareErrorCode::PermissionDenied));
    }

    // Invalid Addresses (0x00, 0x49, 0x55, 0x77, 0x3FF)
    for &addr in &[0x00u16, 0x49, 0x55, 0x77, 0x3FF] {
        let res = controller.mios_sys_i2c_transfer(1, addr, &write_buf, &mut read_buf);
        assert_eq!(res, Err(HardwareErrorCode::PermissionDenied));
    }
}

#[test]
fn test_stress_i2c_buffer_overflow_attempts() {
    let mut allowlist = HardwareAllowlist::default();
    allowlist.allowed_i2c_buses = [1].into_iter().collect();
    allowlist.allowed_i2c_addresses = [0x68].into_iter().collect();
    allowlist.max_i2c_transfer_len = 64; // Max 64 bytes

    let (controller, _mock) = SandboxedHardwareController::new_mock(allowlist);

    // 1. Write buffer overflow (65 bytes > 64)
    let overflow_write = vec![0x00u8; 65];
    let mut small_read = [0u8; 1];
    let res1 = controller.mios_sys_i2c_transfer(1, 0x68, &overflow_write, &mut small_read);
    assert_eq!(res1, Err(HardwareErrorCode::InvalidParameter));

    // 2. Read buffer overflow (65 bytes > 64)
    let small_write = [0x00u8];
    let mut overflow_read = vec![0u8; 65];
    let res2 = controller.mios_sys_i2c_transfer(1, 0x68, &small_write, &mut overflow_read);
    assert_eq!(res2, Err(HardwareErrorCode::InvalidParameter));

    // 3. Exact boundary (64 bytes) must succeed
    let boundary_write = vec![0x00u8; 64];
    let mut boundary_read = vec![0u8; 64];
    let res3 = controller.mios_sys_i2c_transfer(1, 0x68, &boundary_write, &mut boundary_read);
    assert_eq!(res3, Ok(64));
}

#[test]
fn test_stress_dynamic_hardware_allowlist_updates() {
    let initial_allowlist = HardwareAllowlist {
        allowed_gpio_pins: [17].into_iter().collect(),
        read_only_gpio_pins: [].into_iter().collect(),
        allowed_i2c_buses: [1].into_iter().collect(),
        allowed_i2c_addresses: [0x48].into_iter().collect(),
        max_i2c_transfer_len: 32,
    };

    let (controller, _mock) = SandboxedHardwareController::new_mock(initial_allowlist);

    // Pin 27 initially denied
    assert_eq!(
        controller.mios_sys_gpio_write(27, 1),
        Err(HardwareErrorCode::PermissionDenied)
    );

    // Update allowlist dynamically to include Pin 27
    let mut updated_allowlist = controller.get_allowlist();
    updated_allowlist.allowed_gpio_pins.insert(27);
    controller.update_allowlist(updated_allowlist);

    // Pin 27 now allowed
    assert_eq!(controller.mios_sys_gpio_write(27, 1), Ok(()));
    assert_eq!(controller.mios_sys_gpio_read(27), Ok(1));
}

// =========================================================================
// Task 2 (T-390): Dynamic CPU Pinning & Cgroups Stress Tests
// =========================================================================

#[test]
fn test_stress_cpu_topologies_core_zero_isolation() {
    // 1-Core Topology: Core 0 is the ONLY core -> must be retained
    let c1 = filter_safe_worker_cores(1, None, true);
    assert_eq!(c1, vec![0], "1-core system must retain Core 0");

    // 2-Core Topology: Multi-core -> Core 0 must be stripped, leaving [1]
    let c2 = filter_safe_worker_cores(2, None, true);
    assert_eq!(c2, vec![1], "2-core system must strip Core 0");
    assert!(!c2.contains(&0));

    // 4-Core Topology: [1, 2, 3]
    let c4 = filter_safe_worker_cores(4, None, true);
    assert_eq!(c4, vec![1, 2, 3]);
    assert!(!c4.contains(&0));

    // 64-Core Topology: 63 cores (1..=63), Core 0 NEVER present
    let c64 = filter_safe_worker_cores(64, None, true);
    assert_eq!(c64.len(), 63);
    assert_eq!(c64[0], 1);
    assert_eq!(*c64.last().unwrap(), 63);
    assert!(!c64.contains(&0));

    // Filtering out-of-bounds and Core 0 from requested list
    let requested = vec![0, 5, 12, 63, 64, 128];
    let filtered_64 = filter_safe_worker_cores(64, Some(&requested), true);
    assert_eq!(filtered_64, vec![5, 12, 63]);
}

#[test]
fn test_stress_affinity_controller_exhaustion_and_recovery() {
    let limits = NodeResourceLimits::default();
    let mut controller = WorkerAffinityController::new(4, limits); // safe: [1, 2, 3]

    // Allocate 3 exclusive cores
    let c1 = controller
        .allocate_cores_for_policy(AffinityPolicy::Exclusive, 2)
        .unwrap();
    assert_eq!(c1, vec![1, 2]);

    let c2 = controller
        .allocate_cores_for_policy(AffinityPolicy::Exclusive, 1)
        .unwrap();
    assert_eq!(c2, vec![3]);

    // Exhausted: requesting 1 more should return error
    let err_alloc = controller.allocate_cores_for_policy(AffinityPolicy::Exclusive, 1);
    assert!(err_alloc.is_err());

    // Release core 2
    controller.release_cores(&[2]);

    // Now allocation for 1 core succeeds and gives core 2
    let c3 = controller
        .allocate_cores_for_policy(AffinityPolicy::Exclusive, 1)
        .unwrap();
    assert_eq!(c3, vec![2]);

    // Low priority always targets highest safe core (3)
    let low = controller
        .allocate_cores_for_policy(AffinityPolicy::LowPriority, 0)
        .unwrap();
    assert_eq!(low, vec![3]);
    assert!(!low.contains(&0));

    // Shared policy always returns all safe cores [1, 2, 3]
    let shared = controller
        .allocate_cores_for_policy(AffinityPolicy::Shared, 0)
        .unwrap();
    assert_eq!(shared, vec![1, 2, 3]);
    assert!(!shared.contains(&0));
}

#[test]
fn test_stress_cgroup_formatting_edge_cases() {
    // None quota -> "max <period>"
    assert_eq!(
        CgroupV2Controller::format_cpu_max(None, 100_000),
        "max 100000"
    );

    // Zero quota pct -> "0 <period>"
    assert_eq!(
        CgroupV2Controller::format_cpu_max(Some(0), 100_000),
        "0 100000"
    );

    // Standard 80% quota -> "80000 100000"
    assert_eq!(
        CgroupV2Controller::format_cpu_max(Some(80), 100_000),
        "80000 100000"
    );

    // Multi-core 400% quota -> "400000 100000"
    assert_eq!(
        CgroupV2Controller::format_cpu_max(Some(400), 100_000),
        "400000 100000"
    );

    // Small period (1000us)
    assert_eq!(
        CgroupV2Controller::format_cpu_max(Some(50), 1_000),
        "500 1000"
    );
}

// =========================================================================
// Task 3 (T-391): CRDT State Compaction & Snapshot GC Stress Tests
// =========================================================================

#[test]
fn test_stress_crdt_tombstone_ttl_and_resurrection_invariants() {
    let mut store = StateStore::new(10);

    // 1. Insert key A deleted at t = 1000
    store.merge_element(StateElement {
        key: "key_a".to_string(),
        value: Vec::new(),
        timestamp_ns: 1_000_000_000,
        originating_node_id: 10,
        is_deleted: true,
    });

    // 2. Insert key B deleted at t = 2000
    store.merge_element(StateElement {
        key: "key_b".to_string(),
        value: Vec::new(),
        timestamp_ns: 2_000_000_000,
        originating_node_id: 10,
        is_deleted: true,
    });

    // 3. Insert active key C at t = 2500
    store.merge_element(StateElement {
        key: "key_c".to_string(),
        value: b"val_c".to_vec(),
        timestamp_ns: 2_500_000_000,
        originating_node_id: 10,
        is_deleted: false,
    });

    // Run compaction at current_time = 2200 with TTL = 500
    // key_a age = 2200 - 1000 = 1200 > 500 -> PURGED
    // key_b age = 2200 - 2000 = 200 <= 500 -> RETAINED
    // key_c is active -> RETAINED
    let stats = store.compact_tombstones(2_200_000_000, 500_000_000);
    assert_eq!(stats.initial_elements, 3);
    assert_eq!(stats.active_elements, 1);
    assert_eq!(stats.tombstones_purged, 1);
    assert_eq!(stats.tombstones_retained, 1);

    assert_eq!(store.get("key_c"), Some(&b"val_c".to_vec()));
    assert_eq!(store.get("key_b"), None); // tombstone
    assert_eq!(store.get("key_a"), None); // purged

    // Invariant: Merging an older update for key_b (t = 1500 < tombstone t = 2000) does NOT resurrect key_b
    let stale_remote_b = StateElement {
        key: "key_b".to_string(),
        value: b"resurrect_attempt".to_vec(),
        timestamp_ns: 1_500_000_000,
        originating_node_id: 20,
        is_deleted: false,
    };
    assert!(!store.merge_element(stale_remote_b));
    assert_eq!(store.get("key_b"), None);

    // Invariant: Merging a NEWER update for key_b (t = 3000 > tombstone t = 2000) DOES resurrect key_b
    let fresh_remote_b = StateElement {
        key: "key_b".to_string(),
        value: b"new_resurrection".to_vec(),
        timestamp_ns: 3_000_000_000,
        originating_node_id: 20,
        is_deleted: false,
    };
    assert!(store.merge_element(fresh_remote_b));
    assert_eq!(store.get("key_b"), Some(&b"new_resurrection".to_vec()));
}

#[test]
fn test_stress_crdt_identical_timestamp_node_id_tie_breaking() {
    let mut store = StateStore::new(100);

    // Local element created by Node 100 with timestamp 5000
    let local = StateElement {
        key: "tie_key".to_string(),
        value: b"from_node_100".to_vec(),
        timestamp_ns: 5000,
        originating_node_id: 100,
        is_deleted: false,
    };
    store.merge_element(local);

    // Remote element with SAME timestamp 5000 from Node 50 (lower node ID) -> Should NOT overwrite
    let remote_lower = StateElement {
        key: "tie_key".to_string(),
        value: b"from_node_50".to_vec(),
        timestamp_ns: 5000,
        originating_node_id: 50,
        is_deleted: false,
    };
    assert!(!store.merge_element(remote_lower));
    assert_eq!(store.get("tie_key"), Some(&b"from_node_100".to_vec()));

    // Remote element with SAME timestamp 5000 from Node 200 (higher node ID) -> MUST overwrite
    let remote_higher = StateElement {
        key: "tie_key".to_string(),
        value: b"from_node_200".to_vec(),
        timestamp_ns: 5000,
        originating_node_id: 200,
        is_deleted: false,
    };
    assert!(store.merge_element(remote_higher));
    assert_eq!(store.get("tie_key"), Some(&b"from_node_200".to_vec()));
}

#[test]
fn test_stress_crdt_wal_compaction_and_disk_reloading() -> Result<()> {
    let tmp = NamedTempFile::new()?;
    let path = tmp.path().to_str().unwrap().to_string();

    let mut store = StateStore::with_persistence(501, &path)?;

    // Insert 100 items: 40 active, 60 deleted with old timestamps
    for i in 0..40 {
        store.merge_element(StateElement {
            key: format!("sensor_{}", i),
            value: format!("val_{}", i).into_bytes(),
            timestamp_ns: 5000,
            originating_node_id: 501,
            is_deleted: false,
        });
    }

    for i in 40..100 {
        store.merge_element(StateElement {
            key: format!("sensor_{}", i),
            value: Vec::new(),
            timestamp_ns: 1000,
            originating_node_id: 501,
            is_deleted: true,
        });
    }

    assert_eq!(store.total_elements_count(), 100);
    assert_eq!(store.count_tombstones(), 60);

    // Compact with TTL = 1000 at current_time = 10000 (age 9000 > 1000 -> purged)
    let stats = store.compact_disk_storage(10_000, 1_000)?;
    assert_eq!(stats.tombstones_purged, 60);
    assert_eq!(stats.active_elements, 40);
    assert_eq!(store.total_elements_count(), 40);

    // Reload from disk and verify exact data integrity
    let reloaded = StateStore::load_from_disk(&path, 501)?;
    assert_eq!(reloaded.total_elements_count(), 40);
    assert_eq!(reloaded.count_tombstones(), 0);

    for i in 0..40 {
        let expected_val = format!("val_{}", i).into_bytes();
        assert_eq!(reloaded.get(&format!("sensor_{}", i)), Some(&expected_val));
    }

    for i in 40..100 {
        assert_eq!(reloaded.get(&format!("sensor_{}", i)), None);
    }

    Ok(())
}

// =========================================================================
// Task 4 (T-400): Hardware Watchdog Supervisor & Ping Stress Tests
// =========================================================================

#[test]
fn test_stress_watchdog_rapid_sequential_pings() {
    let config = WatchdogConfig {
        enabled: true,
        device_path: "/dev/watchdog".to_string(),
        timeout_secs: 30,
        ping_interval_secs: 5,
        use_systemd_notify: false,
    };
    let (supervisor, mock) = WatchdogSupervisor::new_mock(config);

    supervisor.arm().unwrap();
    assert!(supervisor.is_armed());

    // 10,000 rapid sequential pings
    for _ in 0..10_000 {
        assert!(supervisor.ping().is_ok());
    }

    let m = mock.lock().unwrap();
    assert_eq!(m.ping_count, 10_000);
    assert!(!m.disarmed_safely);
}

#[test]
fn test_stress_watchdog_concurrent_multithreaded_pings() {
    let config = WatchdogConfig::default();
    let (supervisor, mock) = WatchdogSupervisor::new_mock(config);

    supervisor.arm().unwrap();
    let sup_arc = Arc::new(supervisor);

    let mut handles = Vec::new();
    for _i in 0..4 {
        let sup_clone = sup_arc.clone();
        handles.push(thread::spawn(move || {
            for _j in 0..100 {
                let res = sup_clone.ping();
                assert!(res.is_ok());
            }
        }));
    }

    for h in handles {
        h.join().unwrap();
    }

    {
        let m = mock.lock().unwrap();
        assert_eq!(m.ping_count, 400);
    }

    assert!(sup_arc.disarm().is_ok());
    assert!(!sup_arc.is_armed());
}

#[test]
fn test_stress_watchdog_disarm_rearm_and_missing_recovery() {
    // Missing device recovery
    let mock_missing = Arc::new(Mutex::new(MockWatchdogDriver::new(false, 30)));
    let sup_missing = WatchdogSupervisor::new(WatchdogConfig::default(), mock_missing);
    assert!(!sup_missing.is_present());
    assert!(sup_missing.arm().is_err());
    assert!(!sup_missing.is_armed());

    // Lifecycle re-arming
    let (supervisor, mock) = WatchdogSupervisor::new_mock(WatchdogConfig::default());
    assert!(supervisor.arm().is_ok());
    assert!(supervisor.ping().is_ok());

    // Disarm
    assert!(supervisor.disarm().is_ok());
    assert!(!supervisor.is_armed());
    {
        let m = mock.lock().unwrap();
        assert!(m.disarmed_safely);
    }
    // Ping while disarmed fails
    assert!(supervisor.ping().is_err());

    // Re-arm
    assert!(supervisor.arm().is_ok());
    assert!(supervisor.is_armed());
    {
        let m = mock.lock().unwrap();
        assert!(!m.disarmed_safely);
        assert!(m.armed);
    }
    assert!(supervisor.ping().is_ok());
}
