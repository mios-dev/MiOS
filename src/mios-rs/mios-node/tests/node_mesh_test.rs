// AI-hint: Integration and unit tests for mios-node wire protocol, dual-tier executor, and CRDT state sync.
// AI-related: src/mios-rs/mios-node/src/lib.rs, src/mios-rs/mios-node/src/node.rs
use anyhow::Result;
use ed25519_dalek::{Signer, SigningKey};
use mios_node::executor::ExecutionEngine;
use mios_node::protocol::{Frame, Header, MessageType, TaskOffloadPayload, HEADER_SIZE};
use mios_node::state_sync::StateStore;
use std::sync::{Arc, Mutex};
use tempfile::NamedTempFile;

#[test]
fn test_full_protocol_header_and_frame_validation() -> Result<()> {
    let header = Header::new(MessageType::Heartbeat, 202, 128, 0xABCDEF01);
    let mut header_buf = [0u8; HEADER_SIZE];
    header.encode(&mut header_buf)?;

    let decoded_header = Header::decode(&header_buf)?;
    assert_eq!(decoded_header.magic, 0x4D49);
    assert_eq!(decoded_header.version, 0x01);
    assert_eq!(decoded_header.msg_type, MessageType::Heartbeat);
    assert_eq!(decoded_header.node_id, 202);
    assert_eq!(decoded_header.payload_len, 128);
    assert_eq!(decoded_header.checksum, 0xABCDEF01);

    let payload = b"Distributed Edge Task Payload".to_vec();
    let frame = Frame::new(MessageType::TaskOffload, 202, payload.clone());

    let encoded_bytes = frame.encode()?;
    let decoded_frame = Frame::decode(&encoded_bytes)?;
    assert_eq!(decoded_frame.header.node_id, 202);
    assert_eq!(decoded_frame.payload, payload);

    Ok(())
}

#[test]
fn test_protocol_invalid_header_rejection() {
    let mut buf = [0u8; HEADER_SIZE];
    // Invalid magic bytes
    buf[0] = 0xDE;
    buf[1] = 0xAD;

    let res = Header::decode(&buf);
    assert!(res.is_err());
    assert!(res.unwrap_err().to_string().contains("Invalid MiOS magic"));
}

#[test]
fn test_tier1_wasm_sandbox_execution() -> Result<()> {
    let state_store = Arc::new(Mutex::new(StateStore::new(1)));
    let engine = ExecutionEngine::new(state_store.clone());

    let task_payload = TaskOffloadPayload {
        task_id: 5001,
        tier: 1,
        target_arch: 0,
        memory_limit_bytes: 32 * 1024 * 1024,
        execution_timeout_ms: 2000,
        code_bytes: b"WASM_INTERPRETER_BYTECODE".to_vec(),
        input_data: b"temperature=22.4".to_vec(),
        signature: None,
        public_key: None,
    };

    let result = engine.execute_task(&task_payload);
    assert!(result.success);
    assert_eq!(result.exit_code, 0);

    let store = state_store.lock().unwrap();
    assert_eq!(store.get("task.5001.status"), Some(&b"COMPLETED".to_vec()));

    Ok(())
}

#[test]
fn test_tier2_native_ed25519_signature_verification() -> Result<()> {
    let state_store = Arc::new(Mutex::new(StateStore::new(2)));
    let engine = ExecutionEngine::new(state_store.clone());

    let secret_bytes = [42u8; 32];
    let signing_key = SigningKey::from_bytes(&secret_bytes);
    let verifying_key = signing_key.verifying_key();

    let code_binary = b"ELF_NATIVE_EXEC_MODULE".to_vec();
    let signature = signing_key.sign(&code_binary);

    let valid_payload = TaskOffloadPayload {
        task_id: 6001,
        tier: 2,
        target_arch: if cfg!(target_arch = "x86_64") { 1 } else { 0 },
        memory_limit_bytes: 64 * 1024 * 1024,
        execution_timeout_ms: 1000,
        code_bytes: code_binary.clone(),
        input_data: Vec::new(),
        signature: Some(signature.to_bytes().to_vec()),
        public_key: Some(verifying_key.to_bytes().to_vec()),
    };

    let valid_result = engine.execute_task(&valid_payload);
    assert!(valid_result.success);

    let mut tampered_code = code_binary.clone();
    tampered_code[0] ^= 0xFF;

    let invalid_payload = TaskOffloadPayload {
        task_id: 6002,
        tier: 2,
        target_arch: if cfg!(target_arch = "x86_64") { 1 } else { 0 },
        memory_limit_bytes: 64 * 1024 * 1024,
        execution_timeout_ms: 1000,
        code_bytes: tampered_code,
        input_data: Vec::new(),
        signature: Some(signature.to_bytes().to_vec()),
        public_key: Some(verifying_key.to_bytes().to_vec()),
    };

    let invalid_result = engine.execute_task(&invalid_payload);
    assert!(!invalid_result.success);
    assert!(invalid_result
        .error_msg
        .unwrap()
        .contains("verification failed"));

    Ok(())
}

#[test]
fn test_crdt_tombstone_deletion_and_convergence() -> Result<()> {
    let mut node_1 = StateStore::new(101);
    let mut node_2 = StateStore::new(102);

    node_1.set("network.domain".to_string(), b"mios.local".to_vec());
    node_2.merge_remote_store(node_1.vector_clock.clone(), node_1.replicable_elements());
    assert_eq!(node_2.get("network.domain"), Some(&b"mios.local".to_vec()));

    // Node 1 deletes the key
    node_1.delete("network.domain");
    assert_eq!(node_1.get("network.domain"), None);

    // Merge deletion tombstone into Node 2
    node_2.merge_remote_store(node_1.vector_clock.clone(), node_1.replicable_elements());
    assert_eq!(node_2.get("network.domain"), None);

    Ok(())
}

#[test]
fn test_crdt_multi_node_state_convergence_and_persistence() -> Result<()> {
    let mut node_1 = StateStore::new(101);
    let mut node_2 = StateStore::new(102);

    node_1.set("network.domain".to_string(), b"mios.local".to_vec());
    node_2.set("network.domain".to_string(), b"mios.mesh".to_vec());

    node_2.merge_remote_store(node_1.vector_clock.clone(), node_1.replicable_elements());
    assert!(node_2.get("network.domain").is_some());

    let tmp = NamedTempFile::new()?;
    let path = tmp.path().to_str().unwrap();

    node_2.save_to_disk(path)?;
    let restored = StateStore::load_from_disk(path, 102)?;

    assert_eq!(restored.get("network.domain"), node_2.get("network.domain"));

    Ok(())
}
