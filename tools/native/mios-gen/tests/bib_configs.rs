// AI-hint: Two-sided integration test suite for mios-gen bib-configs (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/bib_configs.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

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
fn test_bib_configs_cli_e2e() {
    let root = get_repo_root();
    let bin_path = bin();

    // 1. Positive control: standard check mode passes with exit code 0
    let output = Command::new(bin_path)
        .arg("bib-configs")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen bib-configs --check");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert!(
        output.status.success(),
        "bib-configs --check failed with code {:?}\nstdout: {}\nstderr: {}",
        output.status.code(),
        stdout,
        stderr
    );
    assert!(
        stdout.contains("PASS: BIB artifact configs in sync with mios.toml SSOT."),
        "Expected success message not found in stdout: {}",
        stdout
    );

    // 2. Positive control: structured JSON output format
    let output_json = Command::new(bin_path)
        .arg("--format")
        .arg("json")
        .arg("bib-configs")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen --format json bib-configs --check");

    assert!(
        output_json.status.success(),
        "bib-configs --format json --check failed"
    );
    let json_val: serde_json::Value =
        serde_json::from_slice(&output_json.stdout).expect("Failed to parse JSON output");
    assert_eq!(json_val["status"], "clean");
    assert_eq!(json_val["subcommand"], "bib-configs");
    assert_eq!(json_val["violations"], 0);

    // 3. Negative control: mutate config/artifacts/bib.toml minsize
    let bib_path = root.join("config/artifacts/bib.toml");
    {
        let _restorer = Restorer::new(&bib_path);
        let orig = fs::read_to_string(&bib_path).expect("read bib.toml");
        let mutated = orig.replace("80 GiB", "999 GiB");
        fs::write(&bib_path, mutated.as_bytes()).expect("write mutated bib.toml");

        let neg_output = Command::new(bin_path)
            .arg("bib-configs")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute mios-gen bib-configs negative control");

        assert!(
            !neg_output.status.success(),
            "Expected failure on mutated bib.toml, but got exit code 0"
        );
        let neg_stderr = String::from_utf8_lossy(&neg_output.stderr);
        assert!(
            neg_stderr.contains("ERROR: BIB artifact configs out of sync"),
            "Expected out of sync error message in stderr, got: {}",
            neg_stderr
        );
    }

    // 4. Negative control: mutate config/artifacts/iso.toml minsize
    let iso_path = root.join("config/artifacts/iso.toml");
    {
        let _restorer = Restorer::new(&iso_path);
        let orig = fs::read_to_string(&iso_path).expect("read iso.toml");
        let mutated = orig.replace("150 GiB", "999 GiB");
        fs::write(&iso_path, mutated.as_bytes()).expect("write mutated iso.toml");

        let neg_output = Command::new(bin_path)
            .arg("bib-configs")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute mios-gen bib-configs negative control");

        assert!(
            !neg_output.status.success(),
            "Expected failure on mutated iso.toml, but got exit code 0"
        );
        let neg_stderr = String::from_utf8_lossy(&neg_output.stderr);
        assert!(
            neg_stderr.contains("ERROR: BIB artifact configs out of sync"),
            "Expected out of sync error message in stderr, got: {}",
            neg_stderr
        );
    }

    // Verify post-restoration check passes
    let restored_output = Command::new(bin_path)
        .arg("bib-configs")
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
