// AI-hint: Two-sided integration test suite for mios-gen cargo-manifests (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/cargo_manifests.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

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
fn test_cargo_manifests_cli_e2e() {
    let source = get_repo_root();
    let fixture = tempfile::tempdir().expect("create isolated manifest fixture");
    let root = fixture.path().to_path_buf();
    // Negative controls must never remove a member from the workspace that
    // another build or test is reading. Only manifests participate in this
    // projection, so retain the real inputs in a private temporary tree.
    for relative in [
        "VERSION",
        "usr/share/mios/mios.toml",
        "tools/native/Cargo.toml",
    ] {
        let destination = root.join(relative);
        fs::create_dir_all(destination.parent().expect("fixture parent")).unwrap();
        fs::copy(source.join(relative), destination).expect("copy projection input");
    }
    for entry in fs::read_dir(source.join("tools/native")).expect("native members") {
        let entry = entry.expect("native member");
        let manifest = entry.path().join("Cargo.toml");
        if manifest.is_file() {
            let destination = root.join("tools/native").join(entry.file_name());
            fs::create_dir_all(&destination).expect("fixture member");
            fs::copy(manifest, destination.join("Cargo.toml")).expect("copy member manifest");
        }
    }
    let bin_path = bin();

    // 1. Positive control: standard check mode passes with exit code 0
    let output = Command::new(bin_path)
        .arg("cargo-manifests")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen cargo-manifests --check");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert!(
        output.status.success(),
        "cargo-manifests --check failed with code {:?}\nstdout: {}\nstderr: {}",
        output.status.code(),
        stdout,
        stderr
    );
    assert!(
        stdout.contains("PASS: tools/native/Cargo.toml matches its generator projection."),
        "Expected success message not found in stdout: {}",
        stdout
    );

    // 2. Positive control: structured JSON output format
    let output_json = Command::new(bin_path)
        .arg("--format")
        .arg("json")
        .arg("cargo-manifests")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen --format json cargo-manifests --check");

    assert!(
        output_json.status.success(),
        "cargo-manifests --format json --check failed"
    );
    let json_val: serde_json::Value =
        serde_json::from_slice(&output_json.stdout).expect("Failed to parse JSON output");
    assert_eq!(json_val["status"], "clean");
    assert_eq!(json_val["subcommand"], "cargo-manifests");
    assert_eq!(json_val["violations"], 0);

    // 3. Negative control: mutate tools/native/Cargo.toml by removing a workspace member
    let manifest_path = root.join("tools/native/Cargo.toml");
    {
        let _restorer = Restorer::new(&manifest_path);
        let orig = fs::read_to_string(&manifest_path).expect("read Cargo.toml");
        assert!(orig.contains("\"xtask\","), "Target member xtask not found");
        let mutated = orig.replace("    \"xtask\",\n", "");
        fs::write(&manifest_path, mutated.as_bytes()).expect("write mutated Cargo.toml");

        let neg_output = Command::new(bin_path)
            .arg("cargo-manifests")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute mios-gen cargo-manifests negative control");

        assert!(
            !neg_output.status.success(),
            "Expected failure on mutated Cargo.toml (dropped member), but got exit code 0"
        );
        let neg_stderr = String::from_utf8_lossy(&neg_output.stderr);
        assert!(
            neg_stderr.contains("[generate-cargo-manifests] FAIL: tools/native/Cargo.toml differs from its projection"),
            "Expected FAIL message in stderr, got: {}",
            neg_stderr
        );
    }

    // 4. Negative control: mutate tools/native/Cargo.toml by altering package version
    {
        let _restorer = Restorer::new(&manifest_path);
        let orig = fs::read_to_string(&manifest_path).expect("read Cargo.toml");
        assert!(
            orig.contains("version = \"0.3.0\""),
            "Target version not found"
        );
        let mutated = orig.replace("version = \"0.3.0\"", "version = \"9.9.9\"");
        fs::write(&manifest_path, mutated.as_bytes()).expect("write mutated Cargo.toml");

        let neg_output = Command::new(bin_path)
            .arg("cargo-manifests")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute mios-gen cargo-manifests negative control");

        assert!(
            !neg_output.status.success(),
            "Expected failure on mutated Cargo.toml (version drift), but got exit code 0"
        );
        let neg_stderr = String::from_utf8_lossy(&neg_output.stderr);
        assert!(
            neg_stderr.contains("[generate-cargo-manifests] FAIL: tools/native/Cargo.toml differs from its projection"),
            "Expected FAIL message in stderr, got: {}",
            neg_stderr
        );
    }

    // Verify post-restoration check passes
    let restored_output = Command::new(bin_path)
        .arg("cargo-manifests")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute post-restoration check");
    assert!(
        restored_output.status.success(),
        "Post-restoration check failed"
    );
}
