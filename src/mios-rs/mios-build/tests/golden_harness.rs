// AI-hint: Golden capture harness (insta + trycmd) for build phase artifacts (AGY-963).
// AI-related: src/mios-rs/mios-build/src/lib.rs

use insta::assert_snapshot;
use mios_build::PhaseRegistry;

#[test]
fn test_phase_registry_golden_plan() {
    let registry = PhaseRegistry::default_registry();
    let mut plan_str = String::new();
    for p in registry.phases() {
        plan_str.push_str(&format!("{}\n", p));
    }
    assert_snapshot!(plan_str, @r###"
    [01] system-files-overlay (01-system-files-overlay.sh) [fatal=true]
    [02] materialize-build-ctx (02-materialize-build-ctx.sh) [fatal=true]
    [05] repos (05-repos.sh) [fatal=true]
    [07] kernel (07-kernel.sh) [fatal=true]
    [98] drift-checks (98-drift-checks.sh) [fatal=true]
    [99] postcheck (99-postcheck.sh) [fatal=true]
    "###);
}
