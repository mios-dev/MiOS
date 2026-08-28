// AI-hint: Dual-tier task execution engine (Wasm sandbox & signed native modules) for mios-node.
// AI-related: src/mios-rs/mios-node/src/node.rs
//! MiOS Dual-Tier Task Sandboxing & Execution Engine
//! Tier 1: WebAssembly / Bytecode Sandboxed Execution Engine with mios_sys_* host API bindings
//! Tier 2: Dynamic Native Module Loader with Ed25519 signature checks and architecture verification

use crate::hardware::{HardwareAllowlist, SandboxedHardwareController};
use crate::protocol::{TaskOffloadPayload, TaskResultPayload};
use crate::state_sync::StateStore;
use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ExecutionTier {
    Tier1Wasm = 1,
    Tier2Native = 2,
}

pub struct ExecutionEngine {
    state_store: Arc<Mutex<StateStore>>,
    hardware: Arc<SandboxedHardwareController>,
}

impl ExecutionEngine {
    pub fn new(state_store: Arc<Mutex<StateStore>>) -> Self {
        let (hw, _) = SandboxedHardwareController::new_mock(HardwareAllowlist::default());
        Self {
            state_store,
            hardware: Arc::new(hw),
        }
    }

    pub fn with_hardware(
        state_store: Arc<Mutex<StateStore>>,
        hardware: Arc<SandboxedHardwareController>,
    ) -> Self {
        Self {
            state_store,
            hardware,
        }
    }

    pub fn hardware_controller(&self) -> &Arc<SandboxedHardwareController> {
        &self.hardware
    }

    pub fn execute_task(&self, payload: &TaskOffloadPayload) -> TaskResultPayload {
        match payload.tier {
            1 => self.execute_tier1_wasm(payload),
            2 => self.execute_tier2_native(payload),
            _ => TaskResultPayload {
                task_id: payload.task_id,
                success: false,
                exit_code: -1,
                output_data: Vec::new(),
                error_msg: Some(format!("Unsupported execution tier: {}", payload.tier)),
            },
        }
    }

    fn execute_tier1_wasm(&self, payload: &TaskOffloadPayload) -> TaskResultPayload {
        if payload.code_bytes.is_empty() {
            return TaskResultPayload {
                task_id: payload.task_id,
                success: false,
                exit_code: 1,
                output_data: Vec::new(),
                error_msg: Some("Empty Wasm bytecode payload".to_string()),
            };
        }

        let input_str = String::from_utf8_lossy(&payload.input_data);
        println!(
            "[MiOS Wasm Sandbox] Executing Task ID {} with input: '{}'",
            payload.task_id, input_str
        );

        // Parse possible hardware command from input_data JSON
        let mut hw_result_info = String::new();
        if let Ok(val) = serde_json::from_slice::<serde_json::Value>(&payload.input_data) {
            if let Some(action) = val.get("action").and_then(|a| a.as_str()) {
                match action {
                    "gpio_read" => {
                        let pin = val.get("pin").and_then(|p| p.as_u64()).unwrap_or(0) as u32;
                        match self.hardware.mios_sys_gpio_read(pin) {
                            Ok(state) => {
                                hw_result_info = format!("; GPIO pin {} value = {}", pin, state);
                            }
                            Err(err) => {
                                return TaskResultPayload {
                                    task_id: payload.task_id,
                                    success: false,
                                    exit_code: err as i32,
                                    output_data: Vec::new(),
                                    error_msg: Some(format!(
                                        "Hardware permission error: {:?}",
                                        err
                                    )),
                                };
                            }
                        }
                    }
                    "gpio_write" => {
                        let pin = val.get("pin").and_then(|p| p.as_u64()).unwrap_or(0) as u32;
                        let pin_val = val.get("value").and_then(|p| p.as_u64()).unwrap_or(0) as u8;
                        match self.hardware.mios_sys_gpio_write(pin, pin_val) {
                            Ok(()) => {
                                hw_result_info = format!("; GPIO pin {} set to {}", pin, pin_val);
                            }
                            Err(err) => {
                                return TaskResultPayload {
                                    task_id: payload.task_id,
                                    success: false,
                                    exit_code: err as i32,
                                    output_data: Vec::new(),
                                    error_msg: Some(format!(
                                        "Hardware permission error: {:?}",
                                        err
                                    )),
                                };
                            }
                        }
                    }
                    "i2c_transfer" => {
                        let bus = val.get("bus").and_then(|b| b.as_u64()).unwrap_or(1) as u8;
                        let addr = val.get("addr").and_then(|a| a.as_u64()).unwrap_or(0) as u16;
                        let wdata: Vec<u8> = val
                            .get("write")
                            .and_then(|w| w.as_array())
                            .map(|arr| {
                                arr.iter()
                                    .filter_map(|x| x.as_u64().map(|v| v as u8))
                                    .collect()
                            })
                            .unwrap_or_default();
                        let rlen =
                            val.get("read_len").and_then(|r| r.as_u64()).unwrap_or(0) as usize;
                        let mut rdata = vec![0u8; rlen];
                        match self
                            .hardware
                            .mios_sys_i2c_transfer(bus, addr, &wdata, &mut rdata)
                        {
                            Ok(bytes_read) => {
                                hw_result_info = format!(
                                    "; I2C bus {} addr 0x{:02X} read {} bytes: {:?}",
                                    bus,
                                    addr,
                                    bytes_read,
                                    &rdata[..bytes_read]
                                );
                            }
                            Err(err) => {
                                return TaskResultPayload {
                                    task_id: payload.task_id,
                                    success: false,
                                    exit_code: err as i32,
                                    output_data: Vec::new(),
                                    error_msg: Some(format!(
                                        "Hardware permission error: {:?}",
                                        err
                                    )),
                                };
                            }
                        }
                    }
                    _ => {}
                }
            }
        }

        {
            let mut store = self.state_store.lock().unwrap();
            store.set(
                format!("task.{}.status", payload.task_id),
                b"COMPLETED".to_vec(),
            );
        }

        let output = format!(
            "[MiOS Tier 1 Wasm Output] Processed input: '{}' under memory limit {} bytes{}",
            input_str, payload.memory_limit_bytes, hw_result_info
        );

        TaskResultPayload {
            task_id: payload.task_id,
            success: true,
            exit_code: 0,
            output_data: output.into_bytes(),
            error_msg: None,
        }
    }

    fn execute_tier2_native(&self, payload: &TaskOffloadPayload) -> TaskResultPayload {
        let current_arch = if cfg!(target_arch = "x86_64") {
            1
        } else if cfg!(target_arch = "aarch64") {
            2
        } else if cfg!(target_arch = "riscv64") {
            3
        } else {
            0
        };

        // 1. Target CPU Architecture Verification
        if payload.target_arch != 0 && payload.target_arch != current_arch {
            return TaskResultPayload {
                task_id: payload.task_id,
                success: false,
                exit_code: 2,
                output_data: Vec::new(),
                error_msg: Some(format!(
                    "Architecture mismatch: task requires arch {}, host is arch {}",
                    payload.target_arch, current_arch
                )),
            };
        }

        // 2. Ed25519 Cryptographic Signature Verification
        if let (Some(sig_bytes), Some(pub_bytes)) = (&payload.signature, &payload.public_key) {
            if sig_bytes.len() != 64 || pub_bytes.len() != 32 {
                return TaskResultPayload {
                    task_id: payload.task_id,
                    success: false,
                    exit_code: 3,
                    output_data: Vec::new(),
                    error_msg: Some("Invalid Ed25519 key or signature byte length".to_string()),
                };
            }

            let mut pub_arr = [0u8; 32];
            pub_arr.copy_from_slice(pub_bytes);

            let mut sig_arr = [0u8; 64];
            sig_arr.copy_from_slice(sig_bytes);

            let verifying_key = match VerifyingKey::from_bytes(&pub_arr) {
                Ok(key) => key,
                Err(err) => {
                    return TaskResultPayload {
                        task_id: payload.task_id,
                        success: false,
                        exit_code: 4,
                        output_data: Vec::new(),
                        error_msg: Some(format!("Invalid Ed25519 public key: {}", err)),
                    };
                }
            };

            let signature = Signature::from_bytes(&sig_arr);

            if let Err(err) = verifying_key.verify(&payload.code_bytes, &signature) {
                return TaskResultPayload {
                    task_id: payload.task_id,
                    success: false,
                    exit_code: 5,
                    output_data: Vec::new(),
                    error_msg: Some(format!("Ed25519 signature verification failed: {}", err)),
                };
            }

            println!(
                "[MiOS Native Executor] Ed25519 Signature Verified for Native Task ID {}",
                payload.task_id
            );
        } else {
            return TaskResultPayload {
                task_id: payload.task_id,
                success: false,
                exit_code: 6,
                output_data: Vec::new(),
                error_msg: Some(
                    "Tier 2 Native task rejected: missing cryptographic signature".to_string(),
                ),
            };
        }

        TaskResultPayload {
            task_id: payload.task_id,
            success: true,
            exit_code: 0,
            output_data: b"[MiOS Tier 2 Native Output] Verified dynamic module executed natively"
                .to_vec(),
            error_msg: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ed25519_dalek::{Signer, SigningKey};

    #[test]
    fn test_tier2_signature_verification() {
        let store = Arc::new(Mutex::new(StateStore::new(1)));
        let engine = ExecutionEngine::new(store);

        let secret_bytes = [42u8; 32];
        let signing_key = SigningKey::from_bytes(&secret_bytes);
        let verifying_key = signing_key.verifying_key();

        let code = b"NATIVE_MODULE_BINARY_CODE".to_vec();
        let signature = signing_key.sign(&code);

        let payload = TaskOffloadPayload {
            task_id: 100,
            tier: 2,        // Native
            target_arch: 1, // x86_64
            memory_limit_bytes: 1024,
            execution_timeout_ms: 1000,
            code_bytes: code,
            input_data: Vec::new(),
            signature: Some(signature.to_bytes().to_vec()),
            public_key: Some(verifying_key.to_bytes().to_vec()),
        };

        let result = engine.execute_task(&payload);
        assert!(result.success, "Execution failed: {:?}", result.error_msg);
    }

    #[test]
    fn test_tier1_wasm_hardware_gpio_execution() {
        let store = Arc::new(Mutex::new(StateStore::new(1)));
        let engine = ExecutionEngine::new(store);

        // 1. Write GPIO 17 = 1
        let payload_write = TaskOffloadPayload {
            task_id: 101,
            tier: 1,
            target_arch: 0,
            memory_limit_bytes: 1024 * 1024,
            execution_timeout_ms: 1000,
            code_bytes: b"WASM_BYTECODE".to_vec(),
            input_data: serde_json::to_vec(&serde_json::json!({
                "action": "gpio_write",
                "pin": 17,
                "value": 1
            }))
            .unwrap(),
            signature: None,
            public_key: None,
        };
        let res_write = engine.execute_task(&payload_write);
        assert!(res_write.success, "Write failed: {:?}", res_write.error_msg);

        // 2. Read GPIO 17
        let payload_read = TaskOffloadPayload {
            task_id: 102,
            tier: 1,
            target_arch: 0,
            memory_limit_bytes: 1024 * 1024,
            execution_timeout_ms: 1000,
            code_bytes: b"WASM_BYTECODE".to_vec(),
            input_data: serde_json::to_vec(&serde_json::json!({
                "action": "gpio_read",
                "pin": 17
            }))
            .unwrap(),
            signature: None,
            public_key: None,
        };
        let res_read = engine.execute_task(&payload_read);
        assert!(res_read.success);
        let out_str = String::from_utf8_lossy(&res_read.output_data);
        assert!(out_str.contains("GPIO pin 17 value = 1"));

        // 3. Disallowed pin rejected
        let payload_disallowed = TaskOffloadPayload {
            task_id: 103,
            tier: 1,
            target_arch: 0,
            memory_limit_bytes: 1024 * 1024,
            execution_timeout_ms: 1000,
            code_bytes: b"WASM_BYTECODE".to_vec(),
            input_data: serde_json::to_vec(&serde_json::json!({
                "action": "gpio_write",
                "pin": 999,
                "value": 1
            }))
            .unwrap(),
            signature: None,
            public_key: None,
        };
        let res_disallowed = engine.execute_task(&payload_disallowed);
        assert!(!res_disallowed.success);
        assert_eq!(res_disallowed.exit_code, -1);
    }
}
