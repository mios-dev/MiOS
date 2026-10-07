// AI-hint: Integration tests for mios-gen gate-index verb -- verifies TSV generation, ordinal numbering, --check verification, and negative controls.
// AI-related: tools/native/mios-gen/src/gate_index.rs, automation/98-drift-checks.sh, docs/design/doc-rust-static-port.md

use std::fs;
use std::process::Command;

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

#[test]
fn test_gate_index_render_and_check() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let auto_dir = root.join("automation");
    let ref_dir = root.join("usr/share/mios/reference");
    fs::create_dir_all(&auto_dir).unwrap();
    fs::create_dir_all(&ref_dir).unwrap();

    let script_content = r#"#!/usr/bin/env bash
# AI-hint: test script
check_alpha() {
    echo "[98-drift-checks] check alpha desc"
}
# --- check beta desc ---
check_beta() {
    true
}
main() {
    check_alpha
    check_beta
}
"#;
    fs::write(auto_dir.join("98-drift-checks.sh"), script_content).unwrap();

    // 1. Generation mode
    let out = Command::new(bin())
        .arg("gate-index")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));

    let tsv_path = ref_dir.join("drift-gate-index.tsv");
    assert!(tsv_path.is_file());
    let content = fs::read_to_string(&tsv_path).unwrap();
    let expected = "# Ordinal\tCheck Function\tDescription\n1\tcheck_alpha\tcheck alpha desc\n2\tcheck_beta\tcheck beta desc\n";
    assert_eq!(content, expected);

    // 2. Check mode - clean
    let out = Command::new(bin())
        .arg("gate-index")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(0));
    let stdout = String::from_utf8_lossy(&out.stdout);
    assert!(stdout.contains("PASS: drift-gate-index.tsv is in sync."));

    // 3. Check mode - tampered
    fs::write(&tsv_path, "# tampered\n").unwrap();
    let out = Command::new(bin())
        .arg("gate-index")
        .arg("--root")
        .arg(root)
        .arg("--check")
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("out of sync with 98-drift-checks.sh"));
}

#[test]
fn test_missing_main_fails() {
    let dir = tempfile::tempdir().unwrap();
    let root = dir.path();
    let auto_dir = root.join("automation");
    fs::create_dir_all(&auto_dir).unwrap();
    fs::write(auto_dir.join("98-drift-checks.sh"), "# no main\n").unwrap();

    let out = Command::new(bin())
        .arg("gate-index")
        .arg("--root")
        .arg(root)
        .output()
        .expect("must execute mios-gen");
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("main() function not found"));
}
