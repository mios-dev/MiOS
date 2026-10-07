// AI-hint: Two-sided integration test suite for mios-gen render-manpages (ADR-0021, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/render_manpages.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

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
fn test_render_manpages_cli_e2e() {
    let root = get_repo_root();

    // 1. Positive control: check clean repository with --check and --validate
    let output = Command::new(bin())
        .args([
            "render-manpages",
            "--root",
            &root.to_string_lossy(),
            "--check",
            "--validate",
        ])
        .output()
        .expect("Failed to execute mios-gen render-manpages");

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);

    assert!(
        output.status.success(),
        "Expected exit 0 for render-manpages --check --validate on clean tree, got: {:?}\nstderr: {}",
        output.status.code(),
        stderr
    );
    assert!(
        stdout.contains("page(s) validated"),
        "Expected validation confirmation message in stdout, got:\n{stdout}"
    );
    assert!(
        stdout.contains("page(s) verified"),
        "Expected verified confirmation message in stdout, got:\n{stdout}"
    );

    // 2. Positive control: JSON format check
    let output_json = Command::new(bin())
        .args([
            "--format",
            "json",
            "render-manpages",
            "--root",
            &root.to_string_lossy(),
            "--check",
            "--validate",
        ])
        .output()
        .expect("Failed to execute mios-gen --format json render-manpages");

    assert!(
        output_json.status.success(),
        "Expected exit 0 for json output"
    );
    let stdout_json = String::from_utf8_lossy(&output_json.stdout);
    let parsed_json: serde_json::Value =
        serde_json::from_str(&stdout_json).expect("Expected valid json output");
    assert_eq!(parsed_json["status"], "clean");
    assert_eq!(parsed_json["subcommand"], "render-manpages");
    assert_eq!(parsed_json["violations"], 0);

    // 3. Negative control: inject content mutation into an existing manpage
    let target_manpage = root.join("usr/share/man/man1/mios.1");
    assert!(
        target_manpage.exists(),
        "Expected usr/share/man/man1/mios.1 to exist at {:?}",
        target_manpage
    );
    {
        let _restorer = Restorer::new(&target_manpage);

        let original_content = fs::read_to_string(&target_manpage).expect("Read mios.1");
        let mutated_content = format!("{original_content}\n.PP\nan edit the SSOT does not describe\n");
        fs::write(&target_manpage, &mutated_content).expect("Write mutated mios.1");

        let output_neg = Command::new(bin())
            .args([
                "render-manpages",
                "--root",
                &root.to_string_lossy(),
                "--check",
            ])
            .output()
            .expect("Failed to execute mios-gen on mutated manpage");

        let stderr_neg = String::from_utf8_lossy(&output_neg.stderr);
        let stdout_neg = String::from_utf8_lossy(&output_neg.stdout);

        assert!(
            !output_neg.status.success(),
            "Expected failure on mutated manpage, but succeeded:\nstdout: {stdout_neg}\nstderr: {stderr_neg}"
        );
        assert!(
            stderr_neg.contains("man pages out of sync") || stderr_neg.contains("usr/share/man/man1/mios.1"),
            "Expected drift error in stderr, got:\n{stderr_neg}"
        );
    }

    // 4. Negative control: inject an orphan manpage
    let orphan_manpage = root.join("usr/share/man/man1/mios-rogue-orphan-test.1");
    {
        let _deleter = FileDeleter::new(&orphan_manpage);
        fs::write(&orphan_manpage, ".TH MIOS-ROGUE 1 \"\" \"MiOS 0.3.0\" \"MiOS Verbs\"\n.SH NAME\nmios-rogue\n.SH DESCRIPTION\nRogue\n")
            .expect("Write orphan manpage");

        let output_orphan = Command::new(bin())
            .args([
                "render-manpages",
                "--root",
                &root.to_string_lossy(),
                "--check",
            ])
            .output()
            .expect("Failed to execute mios-gen on orphan manpage tree");

        let stderr_orp = String::from_utf8_lossy(&output_orphan.stderr);
        let stdout_orp = String::from_utf8_lossy(&output_orphan.stdout);

        assert!(
            !output_orphan.status.success(),
            "Expected failure on orphan manpage, but succeeded:\nstdout: {stdout_orp}\nstderr: {stderr_orp}"
        );
        assert!(
            stderr_orp.contains("no verb declares it") || stderr_orp.contains("man pages out of sync"),
            "Expected orphan error in stderr, got:\n{stderr_orp}"
        );
    }
}
