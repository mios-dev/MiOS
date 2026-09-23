// AI-hint: Library module exports for miosd crate.
// AI-related: src/mios-rs/miosd/src/main.rs

// Same robustness lints as the binary target: without these the lint only
// covered `mod drift` reached via main.rs, so lib-only modules were never
// checked.
#![warn(clippy::unwrap_used, clippy::panic, clippy::todo)]

pub mod cli;
pub mod daemon;
pub mod drift;
pub mod secret;
pub mod server;
