// AI-hint: Two-sided integration test suite for mios-gen render-tmux-theme (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/tmux_theme.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

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
fn test_render_tmux_theme_cli_e2e() {
    let root = get_repo_root();
    let bin_path = bin();

    // 1. Positive control: standard check mode passes with exit code 0
    let output = Command::new(bin_path)
        .arg("render-tmux-theme")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen render-tmux-theme --check");

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
        stdout.contains("[tmux-theme] tmux theme matches SSOT (rounded)"),
        "stdout should confirm match: {}",
        stdout
    );

    // 2. Positive control: legacy alias --check-fixture passes with exit code 0
    let fixture_output = Command::new(bin_path)
        .arg("render-tmux-theme")
        .arg("--check-fixture")
        .arg(&root)
        .output()
        .expect("Failed to execute mios-gen render-tmux-theme --check-fixture");

    assert!(
        fixture_output.status.success(),
        "Expected --check-fixture to exit 0"
    );

    // 3. Positive control: JSON output format
    let json_output = Command::new(bin_path)
        .arg("--format")
        .arg("json")
        .arg("render-tmux-theme")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen --format json render-tmux-theme --check");

    assert!(json_output.status.success(), "Expected json check to exit 0");
    let json_str = String::from_utf8_lossy(&json_output.stdout);
    assert!(
        json_str.contains("\"status\": \"clean\""),
        "JSON output should indicate clean status: {}",
        json_str
    );
    assert!(
        json_str.contains("\"violations\": 0"),
        "JSON output should indicate 0 violations: {}",
        json_str
    );

    // 4. Negative control: planted modification in target file triggers error exit code 1
    let target = root.join("usr/share/mios/tmux/mios-theme.tmux.conf");
    assert!(target.is_file(), "Target mios-theme.tmux.conf must exist");

    {
        let _guard = Restorer::new(&target);

        // Mutate target file
        let mut corrupted = fs::read_to_string(&target).unwrap();
        corrupted.push_str("\n# DEVLOOP-PLANTED-MUTATION\nset -g status off\n");
        fs::write(&target, corrupted.as_bytes()).unwrap();

        let fail_output = Command::new(bin_path)
            .arg("render-tmux-theme")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute corrupted check");

        assert_eq!(
            fail_output.status.code(),
            Some(1),
            "Expected exit code 1 on mutated target file"
        );
        let fail_stderr = String::from_utf8_lossy(&fail_output.stderr);
        assert!(
            fail_stderr.contains("mios-theme.tmux.conf: out of sync"),
            "stderr should name the out of sync file: {}",
            fail_stderr
        );
    }

    // 5. Verification after restore
    let restored_output = Command::new(bin_path)
        .arg("render-tmux-theme")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute check after restore");

    assert!(
        restored_output.status.success(),
        "Target must pass check after guard restored original content"
    );
}
