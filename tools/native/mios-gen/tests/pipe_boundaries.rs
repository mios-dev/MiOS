// AI-hint: Two-sided integration test suite for mios-gen pipe-boundaries (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/pipe_boundaries.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

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
fn test_pipe_boundaries_cli_e2e() {
    let root = get_repo_root();
    let bin_path = bin();

    // 1. Positive control: standard check mode passes with exit code 0
    let output = Command::new(bin_path)
        .arg("pipe-boundaries")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen pipe-boundaries --check");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert!(
        output.status.success(),
        "pipe-boundaries --check failed with code {:?}\nstdout: {}\nstderr: {}",
        output.status.code(),
        stdout,
        stderr
    );
    assert!(
        stdout.contains("usr/share/mios/pipe-boundaries.manifest.json matches the tree (108 modules)."),
        "Expected success message not found in stdout: {}",
        stdout
    );

    // 2. Positive control: structured JSON output format
    let output_json = Command::new(bin_path)
        .arg("--format")
        .arg("json")
        .arg("pipe-boundaries")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen --format json pipe-boundaries --check");

    assert!(
        output_json.status.success(),
        "pipe-boundaries --format json --check failed"
    );
    let json_val: serde_json::Value =
        serde_json::from_slice(&output_json.stdout).expect("Failed to parse JSON output");
    assert_eq!(json_val["status"], "clean");
    assert_eq!(json_val["subcommand"], "pipe-boundaries");
    assert_eq!(json_val["violations"], 0);

    // 3. Negative control: mutate pipe-boundaries.manifest.json with stale content
    let manifest_path = root.join("usr/share/mios/pipe-boundaries.manifest.json");
    {
        let _restorer = Restorer::new(&manifest_path);
        let mut mutated = fs::read_to_string(&manifest_path).expect("read manifest");
        mutated.push('\n');
        fs::write(&manifest_path, mutated.as_bytes()).expect("write mutated manifest");

        let neg_output = Command::new(bin_path)
            .arg("pipe-boundaries")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute negative control");

        assert!(
            !neg_output.status.success(),
            "Expected failure on corrupted manifest, but got exit code 0"
        );
        let neg_stderr = String::from_utf8_lossy(&neg_output.stderr);
        assert!(
            neg_stderr.contains("[gen-pipe-boundary-manifest] STALE:"),
            "Expected STALE message in stderr, got: {}",
            neg_stderr
        );
    }

    // 4. Negative control: missing manifest file
    {
        let _restorer = Restorer::new(&manifest_path);
        fs::remove_file(&manifest_path).expect("remove manifest");

        let neg_output = Command::new(bin_path)
            .arg("pipe-boundaries")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute missing manifest control");

        assert!(
            !neg_output.status.success(),
            "Expected failure on missing manifest, but got exit code 0"
        );
        let neg_stderr = String::from_utf8_lossy(&neg_output.stderr);
        assert!(
            neg_stderr.contains("MISSING "),
            "Expected MISSING message in stderr, got: {}",
            neg_stderr
        );
    }

    // 5. Negative control: nonexistent root
    let missing_output = Command::new(bin_path)
        .arg("pipe-boundaries")
        .arg("--root")
        .arg(root.join("nonexistent_path_42"))
        .arg("--check")
        .output()
        .expect("Failed to execute missing root control");

    assert!(
        !missing_output.status.success(),
        "Expected failure on nonexistent root, but got exit code 0"
    );
    let missing_stderr = String::from_utf8_lossy(&missing_output.stderr);
    assert!(
        missing_stderr.contains("agent-pipe directory not found:"),
        "Expected directory not found error in stderr, got: {}",
        missing_stderr
    );

    // 6. Post-restoration check: tree passes cleanly
    let restored_output = Command::new(bin_path)
        .arg("pipe-boundaries")
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
