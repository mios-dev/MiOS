// AI-hint: Two-sided integration test suite for mios-gen render-globals (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/render_globals.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

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
    original_content: Vec<u8>,
}

impl Restorer {
    fn new(path: &Path) -> Self {
        let original_content =
            fs::read(path).expect("Failed to read original content for restorer");
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
fn test_render_globals_cli_e2e() {
    let root = get_repo_root();

    // 1. Positive control: check clean repository with --check
    let output = Command::new(bin())
        .args([
            "render-globals",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen render-globals");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert!(
        output.status.success(),
        "Expected exit 0 for render-globals --check on clean tree, got: {:?}\nstderr: {}",
        output.status.code(),
        stderr
    );
    assert!(
        stdout.contains("both resolvers match SSOT"),
        "Expected match confirmation message in stdout, got:\n{stdout}"
    );

    // 2. Positive control: JSON format check
    let output_json = Command::new(bin())
        .args([
            "--format",
            "json",
            "render-globals",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen --format json render-globals");

    assert!(
        output_json.status.success(),
        "Expected exit 0 for render-globals --format json --check, got: {:?}",
        output_json.status.code()
    );
    let json_val: serde_json::Value =
        serde_json::from_slice(&output_json.stdout).expect("Valid JSON output from --format json");
    assert_eq!(json_val["status"], "clean");
    assert_eq!(json_val["subcommand"], "render-globals");
    assert_eq!(json_val["violations"], 0);

    // 3. Negative control 1: Mutate automation/lib/globals.sh
    let sh_path = root.join("automation/lib/globals.sh");
    assert!(sh_path.exists(), "globals.sh must exist");
    {
        let _restorer = Restorer::new(&sh_path);
        let mut mutated = fs::read_to_string(&sh_path).unwrap();
        mutated.push_str("\n# CANARY MUTATION FOR DRIFT TEST\n");
        fs::write(&sh_path, mutated).unwrap();

        let output_neg = Command::new(bin())
            .args([
                "render-globals",
                "--root",
                &root.to_string_lossy(),
                "--check",
            ])
            .output()
            .expect("Failed to execute mios-gen render-globals on mutated sh");

        assert!(
            !output_neg.status.success(),
            "Expected failure for mutated globals.sh, but succeeded"
        );
        let err_text = String::from_utf8_lossy(&output_neg.stderr);
        assert!(
            err_text.contains("automation/lib/globals.sh"),
            "Expected error naming globals.sh, got:\n{err_text}"
        );
    }

    // 4. Negative control 2: Mutate automation/lib/globals.ps1
    let ps_path = root.join("automation/lib/globals.ps1");
    assert!(ps_path.exists(), "globals.ps1 must exist");
    {
        let _restorer = Restorer::new(&ps_path);
        let mut mutated_bytes = fs::read(&ps_path).unwrap();
        mutated_bytes.extend_from_slice(b"\r\n# CANARY MUTATION FOR DRIFT TEST\r\n");
        fs::write(&ps_path, mutated_bytes).unwrap();

        let output_neg = Command::new(bin())
            .args([
                "render-globals",
                "--root",
                &root.to_string_lossy(),
                "--check",
            ])
            .output()
            .expect("Failed to execute mios-gen render-globals on mutated ps1");

        assert!(
            !output_neg.status.success(),
            "Expected failure for mutated globals.ps1, but succeeded"
        );
        let err_text = String::from_utf8_lossy(&output_neg.stderr);
        assert!(
            err_text.contains("automation/lib/globals.ps1"),
            "Expected error naming globals.ps1, got:\n{err_text}"
        );
    }
}
