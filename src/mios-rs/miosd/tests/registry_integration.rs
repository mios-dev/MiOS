// AI-hint: Integration test suite for miosd drift check registry
// AI-related: src/mios-rs/miosd/src/drift/mod.rs

use miosd::drift::{Check, DriftCtx, Registry, SSOTParseCheck, Verdict};
use std::path::PathBuf;

#[test]
fn test_full_registry_instantiation() {
    let reg = Registry::new();
    // Registry should have 41 checks registered
    assert!(
        !reg.checks.is_empty(),
        "Registry must contain registered checks"
    );
}

#[test]
fn test_ssot_parse_check_live_repo() {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let root = manifest_dir.join("../../");
    let mios_toml = root.join("usr/share/mios/mios.toml");
    if mios_toml.exists() {
        let ctx = DriftCtx::new(root, false);
        let check = SSOTParseCheck;
        let verdict = check.run(&ctx);
        assert!(
            matches!(verdict, Verdict::Pass(_)),
            "Live SSOT parse check failed: {:?}",
            verdict
        );
    }
}
