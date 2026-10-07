// AI-hint: Two-sided integration test suite for mios-gen render-desktop (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/render_desktop.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

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

struct FileDeleter {
    target: PathBuf,
}

impl FileDeleter {
    fn new(path: &Path) -> Self {
        Self {
            target: path.to_path_buf(),
        }
    }
}

impl Drop for FileDeleter {
    fn drop(&mut self) {
        if self.target.exists() {
            let _ = fs::remove_file(&self.target);
        }
    }
}

#[test]
fn test_render_desktop_cli_e2e() {
    let root = get_repo_root();

    // 1. Positive control: check clean repository
    let output = Command::new(bin())
        .args([
            "render-desktop",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen render-desktop");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert!(
        output.status.success(),
        "Expected exit 0 for render-desktop --check on clean tree, got: {:?}\nstderr: {}",
        output.status.code(),
        stderr
    );
    assert!(
        stdout.contains("All .desktop launchers match SSOT"),
        "Expected confirmation message in stdout, got:\n{stdout}"
    );

    // 2. Positive control: JSON format check
    let output_json = Command::new(bin())
        .args([
            "--format",
            "json",
            "render-desktop",
            "--root",
            &root.to_string_lossy(),
            "--check",
        ])
        .output()
        .expect("Failed to execute mios-gen --format json render-desktop");

    assert!(
        output_json.status.success(),
        "Expected exit 0 for json output"
    );
    let stdout_json = String::from_utf8_lossy(&output_json.stdout);
    let parsed_json: serde_json::Value =
        serde_json::from_str(&stdout_json).expect("Expected valid json output");
    assert_eq!(parsed_json["status"], "clean");
    assert_eq!(parsed_json["subcommand"], "render-desktop");
    assert_eq!(parsed_json["violations"], 0);

    // 3. Negative control: inject content mutation into an existing .desktop file
    let target_desktop = root.join("usr/share/applications/mios-svc-searxng.desktop");
    assert!(
        target_desktop.exists(),
        "Expected mios-svc-searxng.desktop to exist at {:?}",
        target_desktop
    );
    {
        let _restorer = Restorer::new(&target_desktop);

        let original_content = fs::read_to_string(&target_desktop).expect("Read desktop file");
        let mutated_content = original_content.replace("Name=MiOS Search (SearXNG)", "Name=CorruptedSearXNG");
        assert_ne!(original_content, mutated_content);
        fs::write(&target_desktop, &mutated_content).expect("Write mutated desktop file");

        let output_neg = Command::new(bin())
            .args([
                "render-desktop",
                "--root",
                &root.to_string_lossy(),
                "--check",
            ])
            .output()
            .expect("Failed to execute mios-gen on mutated desktop");

        let stderr_neg = String::from_utf8_lossy(&output_neg.stderr);
        let stdout_neg = String::from_utf8_lossy(&output_neg.stdout);

        assert!(
            !output_neg.status.success(),
            "Expected failure on mutated desktop file, but succeeded:\nstdout: {stdout_neg}\nstderr: {stderr_neg}"
        );
        assert!(
            stderr_neg.contains("content drifted") || stderr_neg.contains("DRIFT:"),
            "Expected drift error in stderr, got:\n{stderr_neg}"
        );
    }

    // 4. Negative control: inject unmanaged .desktop file
    let unmanaged_desktop = root.join("usr/share/applications/mios-unmanaged-rogue-test.desktop");
    {
        let _deleter = FileDeleter::new(&unmanaged_desktop);
        fs::write(&unmanaged_desktop, "[Desktop Entry]\nName=Rogue\nType=Application\n")
            .expect("Write unmanaged desktop file");

        let output_unmanaged = Command::new(bin())
            .args([
                "render-desktop",
                "--root",
                &root.to_string_lossy(),
                "--check",
            ])
            .output()
            .expect("Failed to execute mios-gen on unmanaged desktop tree");

        let stderr_unm = String::from_utf8_lossy(&output_unmanaged.stderr);
        let stdout_unm = String::from_utf8_lossy(&output_unmanaged.stdout);

        assert!(
            !output_unmanaged.status.success(),
            "Expected failure on unmanaged desktop file, but succeeded:\nstdout: {stdout_unm}\nstderr: {stderr_unm}"
        );
        assert!(
            stderr_unm.contains("ships but no") || stderr_unm.contains("DRIFT:"),
            "Expected unmanaged error in stderr, got:\n{stderr_unm}"
        );
    }
}
