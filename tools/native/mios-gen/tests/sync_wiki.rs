// AI-hint: Two-sided integration test suite for mios-gen sync-wiki (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/sync_wiki.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

use std::fs;
use std::path::{Path, PathBuf};
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

struct Restorer {
    target: PathBuf,
    original_content: String,
}

impl Restorer {
    fn new(path: &Path) -> Self {
        let original_content =
            fs::read_to_string(path).expect("Failed to read original content for restorer");
        Self {
            target: path.to_path_buf(),
            original_content,
        }
    }
}

impl Drop for Restorer {
    fn drop(&mut self) {
        let _ = fs::write(&self.target, &self.original_content);
    }
}

#[test]
fn test_sync_wiki_cli_e2e() {
    let root = get_repo_root();
    let bin_path = bin();
    let spec_file = root.join("specs/engineering/2026-04-26-Artifact-ENG-002-Scripts-Index.md");

    assert!(spec_file.exists(), "Target spec file must exist");
    let restorer = Restorer::new(&spec_file);

    // Ensure the spec file is synced first
    let setup = Command::new(bin_path)
        .arg("sync-wiki")
        .arg("--root")
        .arg(&root)
        .output()
        .expect("Failed to sync wiki before test");
    assert!(setup.status.success());

    // 1. Positive control: standard check mode passes with exit code 0
    let output = Command::new(bin_path)
        .arg("sync-wiki")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen sync-wiki --check");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        output.status.success(),
        "Expected exit code 0, got: {:?}\nstdout: {}\nstderr: {}",
        output.status.code(),
        stdout,
        stderr
    );
    assert!(
        stdout.contains("[sync-wiki] documentation embeds are in sync"),
        "stdout should confirm synced documentation: {}",
        stdout
    );

    // 2. Positive control: structured JSON check mode
    let json_output = Command::new(bin_path)
        .arg("--format")
        .arg("json")
        .arg("sync-wiki")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen --format json sync-wiki --check");

    assert!(
        json_output.status.success(),
        "Expected JSON check to exit 0"
    );
    let json_str = String::from_utf8_lossy(&json_output.stdout);
    let parsed: serde_json::Value =
        serde_json::from_str(&json_str).expect("Output should be valid JSON");
    assert_eq!(parsed["status"], "clean");
    assert_eq!(parsed["subcommand"], "sync-wiki");
    assert_eq!(parsed["violations"], 0);

    // 3. Negative control: mutated spec file with stale version triggers STALE error with exit code 1
    let original = fs::read_to_string(&spec_file).expect("Failed to read spec file");
    let corrupted = original.replace(r#""version": "0.3.0""#, r#""version": "0.0.1""#);
    assert_ne!(original, corrupted, "Replacement must modify the spec file");
    fs::write(&spec_file, corrupted.as_bytes()).expect("Failed to corrupt spec file");

    let neg_output = Command::new(bin_path)
        .arg("sync-wiki")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute negative check");

    let _neg_stdout = String::from_utf8_lossy(&neg_output.stdout);
    let neg_stderr = String::from_utf8_lossy(&neg_output.stderr);
    assert!(
        !neg_output.status.success(),
        "Mutated spec must fail check mode"
    );
    assert!(
        neg_stderr.contains("STALE"),
        "stderr should mention STALE file: {}",
        neg_stderr
    );

    // 4. Negative control: structured JSON reports violation
    let neg_json_output = Command::new(bin_path)
        .arg("--format")
        .arg("json")
        .arg("sync-wiki")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute negative JSON check");

    assert!(
        !neg_json_output.status.success(),
        "Mutated spec must fail JSON check mode"
    );
    let neg_json_str = String::from_utf8_lossy(&neg_json_output.stdout);
    let neg_parsed: serde_json::Value =
        serde_json::from_str(&neg_json_str).expect("Negative output should be valid JSON");
    assert_eq!(neg_parsed["status"], "violation");
    assert_eq!(neg_parsed["violations"], 1);

    // 5. Positive control: write mode synchronizes and heals the file
    let heal_output = Command::new(bin_path)
        .arg("sync-wiki")
        .arg("--root")
        .arg(&root)
        .output()
        .expect("Failed to run heal in write mode");
    assert!(heal_output.status.success());

    let post_heal_output = Command::new(bin_path)
        .arg("sync-wiki")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to run post-heal check");
    assert!(post_heal_output.status.success());

    // Clean up via drop
    drop(restorer);

    // Final clean check
    let clean_output = Command::new(bin_path)
        .arg("sync-wiki")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to run clean final check");
    assert!(clean_output.status.success());
}
