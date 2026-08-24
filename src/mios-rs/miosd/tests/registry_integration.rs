// AI-hint: Integration test suite for miosd drift check registry
// AI-related: src/mios-rs/miosd/src/drift/mod.rs

use miosd::drift::{Check, DriftCtx, Registry, SSOTParseCheck, Verdict};
use std::path::PathBuf;

#[test]
fn test_full_registry_instantiation() {
    let reg = Registry::new();
    assert!(
        !reg.checks.is_empty(),
        "Registry must contain registered checks"
    );
    // Duplicate ids silently break `miosd drift --only <id>` (the filter would
    // select several checks) and make the run summary ambiguous.
    let mut seen = std::collections::BTreeSet::new();
    for c in &reg.checks {
        assert!(
            !c.id().is_empty(),
            "every registered check needs a non-empty id"
        );
        assert!(
            seen.insert(c.id()),
            "duplicate check id registered: {}",
            c.id()
        );
    }
}

#[test]
fn test_ssot_parse_check_live_repo() {
    // CARGO_MANIFEST_DIR is <repo>/src/mios-rs/miosd, so the repo root is three
    // levels up. It was two, which pointed at <repo>/src -- where mios.toml does
    // not exist, so the guard below skipped the whole assertion and this test
    // could never fail.
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let root = manifest_dir.join("../../../");
    let mios_toml = root.join("usr/share/mios/mios.toml");
    assert!(
        mios_toml.exists(),
        "Live SSOT not found at {} -- this test must exercise the real repo, not skip",
        mios_toml.display()
    );
    let ctx = DriftCtx::new(root, false);
    let check = SSOTParseCheck;
    let verdict = check.run(&ctx);
    assert!(
        matches!(verdict, Verdict::Pass(_)),
        "Live SSOT parse check failed: {:?}",
        verdict
    );
}
