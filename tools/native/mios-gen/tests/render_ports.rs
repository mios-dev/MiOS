// AI-hint: Two-sided integration test suite for mios-gen render-ports (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/render_ports.rs, tests/drift-gate-negatives.sh

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
fn test_render_ports_cli_e2e() {
    let root = get_repo_root();

    // 1. Positive control: check clean repository
    let output = Command::new(bin())
        .args(["render-ports", "--root", &root.to_string_lossy(), "--check"])
        .output()
        .expect("Failed to execute mios-gen render-ports");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert!(
        output.status.success(),
        "Expected exit 0 for render-ports --check on clean tree, got: {:?}\nstderr: {}",
        output.status.code(),
        stderr
    );
    assert!(
        stdout.contains("ports derive cleanly from"),
        "Expected confirmation message in stdout, got:\n{stdout}"
    );

    // 2. Positive control: --print mode
    let output_print = Command::new(bin())
        .args(["render-ports", "--root", &root.to_string_lossy(), "--print"])
        .output()
        .expect("Failed to execute mios-gen render-ports --print");

    let stdout_print = String::from_utf8_lossy(&output_print.stdout);
    assert!(output_print.status.success(), "Expected exit 0 for --print");
    assert!(
        stdout_print.contains("53  adguard_dns"),
        "Expected adguard_dns port in output, got:\n{stdout_print}"
    );
    assert!(
        stdout_print.contains("8700  agent_pipe"),
        "Expected agent_pipe port in output, got:\n{stdout_print}"
    );

    // 3. Positive control: JSON format check
    let output_json = Command::new(bin())
        .args([
            "--format",
            "json",
            "render-ports",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen --format json render-ports");

    assert!(
        output_json.status.success(),
        "Expected exit 0 for json output"
    );
    let stdout_json = String::from_utf8_lossy(&output_json.stdout);
    let parsed_json: serde_json::Value =
        serde_json::from_str(&stdout_json).expect("Expected valid json output");
    assert_eq!(parsed_json["status"], "clean");
    assert_eq!(parsed_json["subcommand"], "render-ports");
    assert_eq!(parsed_json["violations"], 0);

    // 4. Negative control: inject category band collision
    let toml_path = root.join("usr/share/mios/mios.toml");
    let _restorer = Restorer::new(&toml_path);

    let original_toml = fs::read_to_string(&toml_path).expect("Read mios.toml");
    let mutated_toml = original_toml.replace("base    = 8800", "base    = 8700");
    assert_ne!(
        original_toml, mutated_toml,
        "Mutation failed to apply to mios.toml"
    );
    fs::write(&toml_path, &mutated_toml).expect("Write mutated mios.toml");

    let output_neg = Command::new(bin())
        .args(["render-ports", "--root", &root.to_string_lossy(), "--check"])
        .output()
        .expect("Failed to execute mios-gen on mutated tree");

    let stderr_neg = String::from_utf8_lossy(&output_neg.stderr);
    let stdout_neg = String::from_utf8_lossy(&output_neg.stdout);

    assert!(
        !output_neg.status.success(),
        "Expected failure on mutated category base, but succeeded:\nstdout: {stdout_neg}\nstderr: {stderr_neg}"
    );
    assert!(
        stderr_neg.contains("overlap") || stderr_neg.contains("collision"),
        "Expected collision or overlap error in stderr, got:\n{stderr_neg}"
    );

    // RAII Restorer will restore clean mios.toml when dropped at end of scope
}
