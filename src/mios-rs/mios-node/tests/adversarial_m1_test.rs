// AI-hint: Comprehensive adversarial stress tests for Milestone 1 components in mios-node.
// AI-related: src/mios-rs/mios-node/src/crypto.rs, src/mios-rs/mios-node/src/hardware.rs, src/mios-rs/mios-node/src/cgroups.rs, src/mios-rs/mios-node/src/state_sync.rs, src/mios-rs/mios-node/src/watchdog.rs

use mios_node::cgroups::{
    filter_safe_worker_cores, AffinityPolicy, CgroupV2Controller, NodeResourceLimits,
    WorkerAffinityController,
};
use mios_node::crypto::{
    chacha20_poly1305_decrypt, chacha20_poly1305_encrypt, CryptoHandshake, NodeIdentity,
};
use mios_node::hardware::{
    HardwareAllowlist, HardwareErrorCode, SandboxedHardwareController,
};
use mios_node::state_sync::{StateElement, StateStore};
use mios_node::watchdog::{
    LinuxHardwareWatchdog, WatchdogConfig, WatchdogDriver, WatchdogSupervisor,
};
use tempfile::NamedTempFile;

// ============================================================================
// 1. ADVERSARIAL CRYPTO TESTS (RFC 7539, RFC 7748, Handshake, Bit-Flip Fuzzing)
// ============================================================================

#[test]
fn test_adversarial_crypto_rfc7539_test_vectors() {
    // Official RFC 7539 Section 2.8.2 Test Vector for ChaCha20-Poly1305 AEAD
    let key: [u8; 32] = [
        0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87,
        0x88, 0x89, 0x8a, 0x8b, 0x8c, 0x8d, 0x8e, 0x8f,
        0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97,
        0x98, 0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f,
    ];
    let nonce: [u8; 12] = [
        0x07, 0x00, 0x00, 0x00,
        0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
    ];
    let aad: [u8; 12] = [
        0x50, 0x51, 0x52, 0x53, 0xc0, 0xc1, 0xc2, 0xc3, 0xc4, 0xc5, 0xc6, 0xc7,
    ];
    let plaintext = b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it.";

    let expected_tag: [u8; 16] = [
        0x1a, 0xe1, 0x0b, 0x59, 0x4f, 0x09, 0xe2, 0x6a,
        0x7e, 0x90, 0x2e, 0xcb, 0xd0, 0x60, 0x06, 0x91,
    ];

    let ciphertext_with_tag = chacha20_poly1305_encrypt(&key, &nonce, &aad, plaintext);
    assert_eq!(ciphertext_with_tag.len(), plaintext.len() + 16);

    let actual_tag = &ciphertext_with_tag[plaintext.len()..];
    assert_eq!(actual_tag, &expected_tag, "Poly1305 MAC tag must match RFC 7539 vector");

    // Decrypt and verify exact plaintext
    let decrypted = chacha20_poly1305_decrypt(&key, &nonce, &aad, &ciphertext_with_tag)
        .expect("Decryption must succeed");
    assert_eq!(decrypted, plaintext);
}

#[test]
fn test_adversarial_crypto_bit_flip_tamper_fuzzing() {
    let key = [0x33u8; 32];
    let nonce = [0x77u8; 12];
    let aad = b"authenticated_header_bytes_v1";
    let plaintext = b"Adversarial payload containing confidential operational state.";

    let ciphertext_with_tag = chacha20_poly1305_encrypt(&key, &nonce, aad, plaintext);

    // 1. Bit-flip every single byte in the ciphertext payload
    for byte_idx in 0..(ciphertext_with_tag.len() - 16) {
        let mut tampered = ciphertext_with_tag.clone();
        tampered[byte_idx] ^= 0x01; // flip 1 bit
        let res = chacha20_poly1305_decrypt(&key, &nonce, aad, &tampered);
        assert!(res.is_err(), "Bit-flip at ciphertext offset {} must fail decryption", byte_idx);
    }

    // 2. Bit-flip every single byte in the 16-byte Poly1305 MAC tag
    for tag_offset in 0..16 {
        let mut tampered = ciphertext_with_tag.clone();
        let idx = ciphertext_with_tag.len() - 16 + tag_offset;
        tampered[idx] ^= 0x80;
        let res = chacha20_poly1305_decrypt(&key, &nonce, aad, &tampered);
        assert!(res.is_err(), "Bit-flip at MAC tag offset {} must fail decryption", tag_offset);
    }

    // 3. Bit-flip in AAD
    for aad_idx in 0..aad.len() {
        let mut tampered_aad = aad.to_vec();
        tampered_aad[aad_idx] ^= 0x02;
        let res = chacha20_poly1305_decrypt(&key, &nonce, &tampered_aad, &ciphertext_with_tag);
        assert!(res.is_err(), "Bit-flip at AAD offset {} must fail decryption", aad_idx);
    }

    // 4. Truncated payloads (shorter than tag size 16)
    for len in 0..16 {
        let truncated = &ciphertext_with_tag[..len];
        let res = chacha20_poly1305_decrypt(&key, &nonce, aad, truncated);
        assert!(res.is_err(), "Payload of length {} must be rejected (< 16)", len);
    }
}

#[test]
fn test_adversarial_crypto_x25519_and_session_handshake() {
    let id_alice = NodeIdentity::from_bytes(1001, &[0xAA; 32]);
    let id_bob = NodeIdentity::from_bytes(2002, &[0xBB; 32]);

    let eph_alice = [0x11; 32];
    let eph_bob = [0x22; 32];

    let init = CryptoHandshake::create_init(&id_alice, &eph_alice);

    // Malicious tampering with init ephemeral pubkey
    let mut tampered_init = init.clone();
    tampered_init.ephemeral_pubkey[0] ^= 0xFF;
    let tamper_res = CryptoHandshake::process_init_and_respond(&id_bob, &eph_bob, &tampered_init);
    assert!(tamper_res.is_err(), "Tampered ephemeral pubkey must fail signature check");

    // Legitimate handshake
    let (resp, mut session_bob) = CryptoHandshake::process_init_and_respond(&id_bob, &eph_bob, &init)
        .expect("Bob should process init");

    // Malicious tampering with response signature
    let mut tampered_resp = resp.clone();
    tampered_resp.signature[0] ^= 0x01;
    let finalize_tamper_res = CryptoHandshake::finalize_init(&id_alice, &eph_alice, &tampered_resp);
    assert!(finalize_tamper_res.is_err(), "Tampered responder signature must fail");

    // Legitimate finalization
    let mut session_alice = CryptoHandshake::finalize_init(&id_alice, &eph_alice, &resp)
        .expect("Alice should finalize session");

    // Sequential multi-message transmission & Nonce monotonicity check
    for msg_idx in 0..50 {
        let msg = format!("Message seq #{}", msg_idx).into_bytes();
        let enc = session_alice.encrypt_payload(&msg);
        let dec = session_bob.decrypt_payload(&enc).expect("Bob should decrypt sequential msg");
        assert_eq!(dec, msg);
    }
}

// ============================================================================
// 2. ADVERSARIAL HARDWARE & WASM HAL TESTS (T-389)
// ============================================================================

#[test]
fn test_adversarial_hardware_allowlist_boundaries() {
    let mut allowlist = HardwareAllowlist::default();
    allowlist.allowed_gpio_pins = [17, 27].into_iter().collect();
    allowlist.read_only_gpio_pins = [27].into_iter().collect();
    allowlist.allowed_i2c_buses = [1].into_iter().collect();
    allowlist.allowed_i2c_addresses = [0x68].into_iter().collect();
    allowlist.max_i2c_transfer_len = 8; // Small 8-byte transfer limit

    let (controller, mock) = SandboxedHardwareController::new_mock(allowlist);

    // 1. Extreme GPIO Pin Values
    assert_eq!(
        controller.mios_sys_gpio_read(0),
        Err(HardwareErrorCode::PermissionDenied)
    );
    assert_eq!(
        controller.mios_sys_gpio_read(u32::MAX),
        Err(HardwareErrorCode::PermissionDenied)
    );
    assert_eq!(
        controller.mios_sys_gpio_write(u32::MAX, 1),
        Err(HardwareErrorCode::PermissionDenied)
    );

    // 2. Read-Only Pin Enforcement
    assert_eq!(controller.mios_sys_gpio_read(27), Ok(0));
    assert_eq!(
        controller.mios_sys_gpio_write(27, 1),
        Err(HardwareErrorCode::ReadOnlyPin)
    );

    // 3. Read/Write Pin
    assert_eq!(controller.mios_sys_gpio_write(17, 1), Ok(()));
    assert_eq!(controller.mios_sys_gpio_read(17), Ok(1));
    assert_eq!(mock.get_mock_gpio(17), Some(1));

    // 4. I2C Maximum Transfer Length Boundary (8 bytes max)
    let valid_write = [0x10, 1, 2, 3, 4, 5, 6, 7]; // 8 bytes -> OK
    let mut valid_read = [0u8; 8]; // 8 bytes -> OK
    assert_eq!(
        controller.mios_sys_i2c_transfer(1, 0x68, &valid_write, &mut valid_read),
        Ok(8)
    );

    let too_large_write = [0u8; 9]; // 9 bytes -> InvalidParameter
    assert_eq!(
        controller.mios_sys_i2c_transfer(1, 0x68, &too_large_write, &mut valid_read),
        Err(HardwareErrorCode::InvalidParameter)
    );

    let mut too_large_read = [0u8; 9]; // 9 bytes -> InvalidParameter
    assert_eq!(
        controller.mios_sys_i2c_transfer(1, 0x68, &valid_write, &mut too_large_read),
        Err(HardwareErrorCode::InvalidParameter)
    );

    // 5. I2C Register Address Wrapping Arithmetic
    mock.set_mock_i2c_register(1, 0x68, 255, 0xAA);
    mock.set_mock_i2c_register(1, 0x68, 0, 0xBB);
    mock.set_mock_i2c_register(1, 0x68, 1, 0xCC);

    let mut wrap_read = [0u8; 3];
    let start_at_255 = [255u8];
    assert_eq!(
        controller.mios_sys_i2c_transfer(1, 0x68, &start_at_255, &mut wrap_read),
        Ok(3)
    );
    assert_eq!(wrap_read, [0xAA, 0xBB, 0xCC], "Wrapping from 255 to 0, 1 must be handled cleanly");
}

// ============================================================================
// 3. ADVERSARIAL CPU PINNING & CGROUP BOUNDARY TESTS (T-390)
// ============================================================================

#[test]
fn test_adversarial_cgroup_core_filtering_invariants() {
    // 1. Zero system cores edge case
    assert_eq!(filter_safe_worker_cores(0, None, true), Vec::<usize>::new());

    // 2. Single-core system: Invariant requires retaining Core 0
    assert_eq!(filter_safe_worker_cores(1, None, true), vec![0]);
    assert_eq!(filter_safe_worker_cores(1, None, false), vec![0]);

    // 3. Dual-core system: Core 0 stripped when exclude_core_zero = true
    assert_eq!(filter_safe_worker_cores(2, None, true), vec![1]);
    assert_eq!(filter_safe_worker_cores(2, None, false), vec![0, 1]);

    // 4. Large multi-core system (128 cores)
    let cores_128 = filter_safe_worker_cores(128, None, true);
    assert_eq!(cores_128.len(), 127);
    assert!(!cores_128.contains(&0));
    assert_eq!(cores_128.first(), Some(&1));
    assert_eq!(cores_128.last(), Some(&127));

    // 5. Requested cores with out-of-range, negative simulation, and duplicates
    let req = vec![0, 2, 4, 100, 999];
    let filtered = filter_safe_worker_cores(8, Some(&req), true);
    assert_eq!(filtered, vec![2, 4], "Must strip 0 and any core >= 8");
}

#[test]
fn test_adversarial_worker_affinity_allocation_exhaustion() {
    let limits = NodeResourceLimits::default();
    let mut controller = WorkerAffinityController::new(4, limits); // safe: [1, 2, 3]

    // Allocate 3 exclusive cores
    let c1 = controller.allocate_cores_for_policy(AffinityPolicy::Exclusive, 2).unwrap();
    assert_eq!(c1, vec![1, 2]);

    let c2 = controller.allocate_cores_for_policy(AffinityPolicy::Exclusive, 1).unwrap();
    assert_eq!(c2, vec![3]);

    // Pool is completely exhausted
    let c_fail = controller.allocate_cores_for_policy(AffinityPolicy::Exclusive, 1);
    assert!(c_fail.is_err());

    // Release unallocated / irrelevant core 99 (no-op)
    controller.release_cores(&[99]);
    assert!(controller.allocate_cores_for_policy(AffinityPolicy::Exclusive, 1).is_err());

    // Release core 2
    controller.release_cores(&[2]);
    let c_re = controller.allocate_cores_for_policy(AffinityPolicy::Exclusive, 1).unwrap();
    assert_eq!(c_re, vec![2]);

    // LowPriority always assigns the last safe core
    let low = controller.allocate_cores_for_policy(AffinityPolicy::LowPriority, 0).unwrap();
    assert_eq!(low, vec![3]);
}

#[test]
fn test_adversarial_cgroup_format_cpu_max_arithmetic() {
    // 0% quota
    assert_eq!(CgroupV2Controller::format_cpu_max(Some(0), 100_000), "0 100000");

    // 50% quota
    assert_eq!(CgroupV2Controller::format_cpu_max(Some(50), 100_000), "50000 100000");

    // 100% quota
    assert_eq!(CgroupV2Controller::format_cpu_max(Some(100), 100_000), "100000 100000");

    // 400% quota (4 full cores)
    assert_eq!(CgroupV2Controller::format_cpu_max(Some(400), 100_000), "400000 100000");

    // Max unlimited
    assert_eq!(CgroupV2Controller::format_cpu_max(None, 50_000), "max 50000");
}

// ============================================================================
// 4. ADVERSARIAL CRDT GC & CAUSALITY TESTS (T-391)
// ============================================================================

#[test]
fn test_adversarial_crdt_tombstone_gc_edge_cases() {
    let mut store = StateStore::new(42);

    // 1. Clock skew / Future timestamps: current_time < elem.timestamp
    store.merge_element(StateElement {
        key: "future.tombstone".to_string(),
        value: Vec::new(),
        timestamp_ns: 2_000_000_000_000, // In the future (2000s)
        originating_node_id: 42,
        is_deleted: true,
    });

    // Run compaction with current_time = 1000s, TTL = 100s
    // Age calculation saturates to 0, age <= TTL -> Tombstone must NOT be purged
    let stats = store.compact_tombstones(1_000_000_000_000, 100_000_000_000);
    assert_eq!(stats.tombstones_purged, 0);
    assert_eq!(stats.tombstones_retained, 1);
    assert_eq!(store.count_tombstones(), 1);

    // 2. Exact TTL boundary: age == TTL (retained) vs age == TTL + 1 (purged)
    store.merge_element(StateElement {
        key: "exact.ttl.retained".to_string(),
        value: Vec::new(),
        timestamp_ns: 900_000_000_000, // age = 1000 - 900 = 100s == TTL
        originating_node_id: 42,
        is_deleted: true,
    });

    store.merge_element(StateElement {
        key: "stale.ttl.purged".to_string(),
        value: Vec::new(),
        timestamp_ns: 899_999_999_999, // age = 1000.000000001s > TTL
        originating_node_id: 42,
        is_deleted: true,
    });

    let stats2 = store.compact_tombstones(1_000_000_000_000, 100_000_000_000);
    assert_eq!(stats2.tombstones_purged, 1);
    assert_eq!(store.count_tombstones(), 2); // future.tombstone + exact.ttl.retained

    // 3. Ancient active key (10 years old) must NEVER be purged
    store.merge_element(StateElement {
        key: "ancient.live.key".to_string(),
        value: b"never_die".to_vec(),
        timestamp_ns: 1, // ancient
        originating_node_id: 42,
        is_deleted: false,
    });

    let stats3 = store.compact_tombstones(1_000_000_000_000, 100_000_000_000);
    assert_eq!(store.get("ancient.live.key"), Some(&b"never_die".to_vec()));
    assert_eq!(stats3.active_elements, 1);

    // 4. Tombstone Resurrection / Re-animation
    store.set("resurrect.me".to_string(), b"v1".to_vec());
    store.delete("resurrect.me");
    assert_eq!(store.get("resurrect.me"), None);

    // Peer re-creates key with newer timestamp
    store.set("resurrect.me".to_string(), b"v2_alive".to_vec());
    assert_eq!(store.get("resurrect.me"), Some(&b"v2_alive".to_vec()));
}

#[test]
fn test_adversarial_crdt_scale_and_persistence_truncation() {
    let tmp = NamedTempFile::new().unwrap();
    let path = tmp.path().to_str().unwrap().to_string();

    let mut store = StateStore::with_persistence(10, &path).unwrap();

    // Insert 500 active keys
    for i in 0..500 {
        store.set(format!("key.{}", i), format!("val.{}", i).into_bytes());
    }

    // Insert 500 tombstones (half stale, half fresh)
    for i in 500..1000 {
        let k = format!("tomb.{}", i);
        let ts = if i < 750 {
            100_000_000_000 // Stale (100s)
        } else {
            950_000_000_000 // Fresh (950s)
        };
        store.merge_element(StateElement {
            key: k,
            value: Vec::new(),
            timestamp_ns: ts,
            originating_node_id: 10,
            is_deleted: true,
        });
    }

    assert_eq!(store.total_elements_count(), 1000);
    assert_eq!(store.count_tombstones(), 500);

    // Compact at t = 1000s, TTL = 200s
    let current_time_ns = 1_000_000_000_000;
    let ttl_ns = 200_000_000_000;

    let stats = store.compact_disk_storage(current_time_ns, ttl_ns).unwrap();
    assert_eq!(stats.initial_elements, 1000);
    assert_eq!(stats.active_elements, 500);
    assert_eq!(stats.tombstones_purged, 250);
    assert_eq!(stats.tombstones_retained, 250);
    assert_eq!(store.total_elements_count(), 750);

    // Verify snapshot reload matches compacted state
    let reloaded = StateStore::load_from_disk(&path, 10).unwrap();
    assert_eq!(reloaded.total_elements_count(), 750);
    assert_eq!(reloaded.get("key.0"), Some(&b"val.0".to_vec()));
    assert_eq!(reloaded.get("key.499"), Some(&b"val.499".to_vec()));
}

// ============================================================================
// 5. ADVERSARIAL WATCHDOG TESTS (T-400)
// ============================================================================

#[test]
fn test_adversarial_watchdog_supervisor_and_mock_driver() {
    let config = WatchdogConfig {
        enabled: true,
        device_path: "/dev/watchdog".to_string(),
        timeout_secs: 15,
        ping_interval_secs: 2,
        use_systemd_notify: true,
    };

    let (supervisor, mock) = WatchdogSupervisor::new_mock(config.clone());

    // 1. Initial State
    assert!(supervisor.is_present());
    assert!(!supervisor.is_armed());
    assert!(supervisor.ping().is_err(), "Ping on un-armed supervisor must return Err");

    // 2. Arm and Ping Loop
    assert!(supervisor.arm().is_ok());
    assert!(supervisor.is_armed());

    for _ in 0..10 {
        assert!(supervisor.ping().is_ok());
    }

    {
        let m = mock.lock().unwrap();
        assert_eq!(m.ping_count, 10);
        assert!(!m.disarmed_safely);
    }

    // 3. Graceful Disarm with 'V' invariant
    assert!(supervisor.disarm().is_ok());
    assert!(!supervisor.is_armed());

    {
        let m = mock.lock().unwrap();
        assert!(m.disarmed_safely, "Watchdog must be marked safely disarmed");
    }

    // 4. Ping after disarm fails
    assert!(supervisor.ping().is_err());
}

#[test]
fn test_adversarial_linux_watchdog_nonexistent_device() {
    let mut driver = LinuxHardwareWatchdog::new("/tmp/phantom_watchdog_9999", 30);
    assert!(!driver.is_hardware_present());
    assert!(!driver.is_armed());

    // Arming absent device fails with clear Err
    let arm_res = driver.arm();
    assert!(arm_res.is_err());
    assert!(arm_res.unwrap_err().contains("not found"));

    // Ping fails
    assert!(driver.ping().is_err());

    // Disarm and close on unopened driver succeeds as a no-op
    assert!(driver.disarm_and_close().is_ok());
}
