// AI-hint: Library entry point for the mios-node edge micro-node daemon.
// AI-related: src/mios-rs/mios-node/src/main.rs, src/mios-rs/mios-node/src/node.rs
//! MiOS ("My OS" / "MyOS") Distributed Edge Micro-Node Library

pub mod ble;
pub mod buffer_pool;
pub mod capabilities;
pub mod cgroups;
pub mod crypto;
pub mod executor;
pub mod hardware;
pub mod heartbeat;
pub mod net;
pub mod node;
pub mod overlay;
pub mod protocol;
pub mod scheduler;
pub mod state_sync;
pub mod watchdog;
