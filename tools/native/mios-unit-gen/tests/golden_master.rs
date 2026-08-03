use mios_unit_gen::verify_golden_master;
use std::path::Path;

#[test]
fn test_golden_master_matches_systemd_tree() {
    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap();
    let root = Path::new(&manifest_dir).join("../../../");
    let systemd_dir = root.join("usr/lib/systemd/system");
    let golden_dir = Path::new(&manifest_dir).join("tests/golden");

    let result = verify_golden_master(&systemd_dir, &golden_dir);
    assert!(
        result.is_ok(),
        "Golden master baseline diff detected: {:?}",
        result.err()
    );
}
