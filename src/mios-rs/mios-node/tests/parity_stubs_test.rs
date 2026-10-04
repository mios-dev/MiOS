// AI-hint: Parity tests for mios-node Rust methods mirroring usr/libexec/mios/node/*.py twins (T-1188).
// AI-related: src/mios-rs/mios-node/src/lib.rs, usr/libexec/mios/node/
use anyhow::Result;
use mios_node::ble::{BleMeshBootstrap, MockBleAdapter};
use mios_node::capabilities::{probe_node_capabilities, CapabilityRegistry, NodeAnnouncePayload};
use mios_node::cgroups::{CgroupV2Controller, NodeResourceLimits};
use mios_node::crypto::{CryptoHandshake, NodeIdentity};
use mios_node::executor::ExecutionEngine;
use mios_node::hardware::{
    HardwareAllowlist, HardwareDriver, LinuxSysfsHardwareDriver, MockHardwareDriver,
    SandboxedHardwareController,
};
use mios_node::heartbeat::{HeartbeatMonitor, PeerHealth};
use mios_node::protocol::{Frame, MessageType};
use mios_node::scheduler::TaskPriority;
use mios_node::state_sync::StateStore;
use mios_node::watchdog::{LinuxHardwareWatchdog, MockWatchdogDriver, WatchdogDriver};
use std::net::SocketAddr;
use std::sync::{Arc, Mutex};
use tempfile::tempdir;

#[test]
fn test_parity_watchdog_timeout_stubs() {
    // Parity twin: usr/libexec/mios/node/watchdog.py (set_timeout, get_timeout)
    let mut mock = MockWatchdogDriver::new(true, 30);
    assert_eq!(mock.get_timeout().unwrap(), 30);
    assert_eq!(mock.set_timeout(45).unwrap(), 45);
    assert_eq!(mock.get_timeout().unwrap(), 45);

    let mut linux_wd = LinuxHardwareWatchdog::new("/dev/watchdog_nonexistent", 30);
    assert_eq!(linux_wd.get_timeout().unwrap(), 30);
    assert_eq!(linux_wd.set_timeout(60).unwrap(), 60);
    assert_eq!(linux_wd.get_timeout().unwrap(), 60);
}

#[test]
fn test_parity_capabilities_stubs() {
    // Parity twin: usr/libexec/mios/node/capabilities.py (probe_node_capabilities, get_announce)
    let caps = probe_node_capabilities();
    let registry = CapabilityRegistry::new();
    let announce = NodeAnnouncePayload::new(42, "node-42".to_string(), caps);
    registry.register_announce(announce.clone(), 1000);
    let retrieved = registry.get_announce(42);
    assert!(retrieved.is_some());
    assert_eq!(retrieved.unwrap().node_id, 42);
    assert!(registry.get_announce(999).is_none());
}

#[test]
fn test_parity_cgroups_stubs() -> Result<()> {
    // Parity twin: usr/libexec/mios/node/cgroups.py (apply_limits, attach_pid)
    let dir = tempdir()?;
    let controller = CgroupV2Controller::new(dir.path().to_str().unwrap());
    let limits = NodeResourceLimits {
        cpu_quota_pct: Some(50),
        cpu_period_us: 100_000,
        memory_high_bytes: Some(1024 * 1024 * 64),
        memory_max_bytes: Some(1024 * 1024 * 128),
        ..Default::default()
    };
    controller.apply_limits(&limits).map_err(|e| anyhow::anyhow!(e))?;

    let procs_file = dir.path().join("cgroup.procs");
    std::fs::write(&procs_file, "")?;
    controller.attach_pid(1234).map_err(|e| anyhow::anyhow!(e))?;
    let content = std::fs::read_to_string(&procs_file)?;
    assert_eq!(content.trim(), "1234");
    Ok(())
}

#[test]
fn test_parity_heartbeat_stubs() {
    // Parity twin: usr/libexec/mios/node/discovery.py (with_thresholds, record_announce, assess_peer_health, evict_peer, active_peers)
    let mut monitor = HeartbeatMonitor::with_thresholds(1, 5, 10, 20);
    let addr: SocketAddr = "127.0.0.1:8000".parse().unwrap();
    monitor.record_announce(2, addr, 100);

    let active = monitor.active_peers();
    assert_eq!(active.len(), 1);
    assert_eq!(active[0].node_id, 2);

    let (health, strikes) = monitor.assess_peer_health(12);
    assert_eq!(health, PeerHealth::Degraded);
    assert_eq!(strikes, 2);

    let eviction = monitor.evict_peer(2, "manual eviction", 150);
    assert!(eviction.is_some());
    assert_eq!(eviction.unwrap().node_id, 2);
    assert_eq!(monitor.active_peers().len(), 0);
}

#[test]
fn test_parity_crypto_session_cipher_frame_stubs() -> Result<()> {
    // Parity twin: usr/libexec/mios/node/crypto.py (encrypt_frame, decrypt_frame)
    let id_a = NodeIdentity::from_bytes(101, &[1u8; 32]);
    let id_b = NodeIdentity::from_bytes(202, &[2u8; 32]);
    let eph_a = [3u8; 32];
    let eph_b = [4u8; 32];

    let init = CryptoHandshake::create_init(&id_a, &eph_a);
    let (resp, mut session_b) = CryptoHandshake::process_init_and_respond(&id_b, &eph_b, &init)?;
    let mut session_a = CryptoHandshake::finalize_init(&id_a, &eph_a, &resp)?;

    let frame = Frame::new(MessageType::Heartbeat, 101, b"Payload for parity frame".to_vec());
    let encrypted = session_a.encrypt_frame(&frame)?;
    let decrypted = session_b.decrypt_frame(&encrypted)?;

    assert_eq!(decrypted.header.msg_type, MessageType::Heartbeat);
    assert_eq!(decrypted.payload, b"Payload for parity frame");
    Ok(())
}

#[test]
fn test_parity_executor_hardware_stubs() {
    // Parity twin: usr/libexec/mios/node/hardware.py (with_hardware, hardware_controller)
    let state_store = Arc::new(Mutex::new(StateStore::new(1)));
    let (hw, _) = SandboxedHardwareController::new_mock(HardwareAllowlist::default());
    let hw = Arc::new(hw);
    let engine = ExecutionEngine::with_hardware(state_store, hw.clone());
    let hw_ref = engine.hardware_controller();
    assert!(Arc::ptr_eq(hw_ref, &hw));
}

#[test]
fn test_parity_hardware_driver_stubs() {
    // Parity twin: usr/libexec/mios/node/hardware.py (with_custom_roots, get_mock_i2c_register)
    let mock_hw = MockHardwareDriver::new();
    mock_hw.set_mock_i2c_register(1, 0x48, 0x05, 42);
    assert_eq!(mock_hw.get_mock_i2c_register(1, 0x48, 0x05), Some(42));
    assert_eq!(mock_hw.get_mock_i2c_register(1, 0x48, 0x06), None);

    let sysfs = LinuxSysfsHardwareDriver::with_custom_roots("/custom/sys/gpio", "/custom/dev/i2c");
    let read_res = sysfs.gpio_read(18);
    assert!(read_res.is_err());
}

#[test]
fn test_parity_ble_and_scheduler_stubs() {
    // Parity twin: usr/libexec/mios/node/ble.py (get_credentials)
    let adapter = Arc::new(MockBleAdapter::new());
    let ble_session = BleMeshBootstrap::new(101, adapter);
    assert!(ble_session.get_credentials().is_none());

    // Parity twin: usr/libexec/mios/node/scheduler.py (TaskPriority.as_u8)
    assert_eq!(TaskPriority::Critical.as_u8(), 0);
    assert_eq!(TaskPriority::High.as_u8(), 1);
    assert_eq!(TaskPriority::Normal.as_u8(), 2);
    assert_eq!(TaskPriority::Low.as_u8(), 3);
}
