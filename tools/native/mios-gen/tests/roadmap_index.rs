// AI-hint: Two-sided integration test suite for mios-gen roadmap-index (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/roadmap_index.rs, ROADMAP.md, tools/roadmap-index.py

use std::fs;
use std::path::PathBuf;
use std::process::Command;

fn get_repo_root() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .and_then(|p| p.parent())
        .and_then(|p| p.parent())
        .expect("Failed to find repo root from CARGO_MANIFEST_DIR")
        .to_path_buf()
}

fn bin() -> &'static str {
    env!("CARGO_BIN_EXE_mios-gen")
}

#[test]
fn test_roadmap_index_render_and_check() {
    let root = get_repo_root();

    // 1. Positive check on the clean repository
    let output = Command::new(bin())
        .args([
            "roadmap-index",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen roadmap-index");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    println!("stdout:\n{stdout}");
    println!("stderr:\n{stderr}");

    assert!(
        output.status.success(),
        "Expected clean exit 0 for roadmap-index check, got: {:?}\nstderr: {}",
        output.status.code(),
        stderr
    );
    assert!(
        stdout.contains("ROADMAP.md index is in sync"),
        "Expected sync confirmation message, got: {stdout}"
    );

    // 2. Negative check: intentional mutation in repo ROADMAP.md, restored cleanly via RAII guard
    let roadmap_path = root.join("ROADMAP.md");
    let original = fs::read_to_string(&roadmap_path).expect("Failed to read ROADMAP.md");

    struct Restorer(std::path::PathBuf, String);
    impl Drop for Restorer {
        fn drop(&mut self) {
            let _ = fs::write(&self.0, &self.1);
        }
    }
    let _restorer = Restorer(roadmap_path.clone(), original.clone());

    let mutated = original.replace("- **Done**:", "- **Done**: 99999");
    assert_ne!(original, mutated, "Mutation must change content");
    fs::write(&roadmap_path, mutated).expect("Failed to write mutated ROADMAP.md");

    let output_neg = Command::new(bin())
        .args([
            "roadmap-index",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen roadmap-index on mutated copy");

    let stderr_neg = String::from_utf8_lossy(&output_neg.stderr);
    assert!(
        !output_neg.status.success(),
        "Expected failure for mutated ROADMAP.md, got exit code 0"
    );
    assert!(
        stderr_neg.contains("DRIFT detected: ROADMAP.md index is stale"),
        "Expected drift error message, got: {stderr_neg}"
    );
}

#[test]
fn test_roadmap_index_json_format() {
    let root = get_repo_root();

    let output = Command::new(bin())
        .args([
            "--format",
            "json",
            "roadmap-index",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen --format json roadmap-index");

    assert!(
        output.status.success(),
        "Expected exit code 0, got: {:?}\nstderr: {}",
        output.status.code(),
        String::from_utf8_lossy(&output.stderr)
    );

    let stdout = String::from_utf8_lossy(&output.stdout);
    let parsed: serde_json::Value =
        serde_json::from_str(stdout.trim()).expect("Output must be valid JSON");
    assert_eq!(parsed["status"], "clean");
    assert_eq!(parsed["subcommand"], "roadmap-index");
    assert_eq!(parsed["target"], "ROADMAP.md");
    assert_eq!(parsed["violations"], 0);
}

#[test]
fn test_roadmap_index_negative_missing_root() {
    let temp_empty = tempfile::tempdir().expect("Failed to create empty tempdir");

    let output = Command::new(bin())
        .args([
            "roadmap-index",
            "--root",
            &temp_empty.path().to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen on empty root");

    assert!(
        !output.status.success(),
        "Expected non-zero exit code for missing ROADMAP.md"
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("ERROR: ROADMAP.md not found"),
        "Expected error message indicating missing ROADMAP.md, got: {stderr}"
    );
}
