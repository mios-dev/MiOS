// AI-hint: Two-sided integration test suite for mios-gen pod-quadlets (ADR-0021, Law 6, Law 11, Law 14).
// AI-doc: usr/share/doc/mios/manual/tools.md
// AI-related: tools/native/mios-gen/src/pod_quadlets.rs, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh

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
fn test_pod_quadlets_cli_e2e() {
    let root = get_repo_root();
    let bin_path = bin();

    // 1. Positive control: standard check mode passes with exit code 0
    let output = Command::new(bin_path)
        .arg("pod-quadlets")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen pod-quadlets --check");

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
        stdout.contains("[pod-gen] all 35 Quadlet unit(s) match SSOT"),
        "stdout should confirm 35 units in sync: {}",
        stdout
    );

    // 2. Positive control: list mode outputs all 34 system-scope units
    let list_output = Command::new(bin_path)
        .arg("pod-quadlets")
        .arg("--root")
        .arg(&root)
        .arg("--list")
        .output()
        .expect("Failed to execute mios-gen pod-quadlets --list");

    assert!(list_output.status.success(), "Expected list mode to exit 0");
    let list_stdout = String::from_utf8_lossy(&list_output.stdout);
    assert!(
        list_stdout.contains("mios-ai.pod"),
        "list output should contain mios-ai.pod"
    );
    assert!(
        list_stdout.contains("bootc-image-builder.image"),
        "list output should contain bootc-image-builder.image"
    );
    assert!(
        list_stdout.contains("mios.network"),
        "list output should contain mios.network"
    );
    assert!(
        list_stdout.contains("mios-pgvector.container"),
        "list output should contain mios-pgvector.container"
    );

    // 3. Positive control: structured JSON check mode
    let json_output = Command::new(bin_path)
        .arg("--format")
        .arg("json")
        .arg("pod-quadlets")
        .arg("--root")
        .arg(&root)
        .arg("--check")
        .output()
        .expect("Failed to execute mios-gen --format json pod-quadlets --check");

    assert!(
        json_output.status.success(),
        "Expected JSON check to exit 0"
    );
    let json_val: serde_json::Value =
        serde_json::from_slice(&json_output.stdout).expect("Failed to parse JSON output");
    assert_eq!(json_val["status"], "clean");
    assert_eq!(json_val["subcommand"], "pod-quadlets");
    assert_eq!(json_val["violations"], 0);

    // 4. Negative control: mutate a quadlet file and verify check mode detects drift
    let quadlet_path = root.join("usr/share/containers/systemd/mios-pgvector.container");
    assert!(quadlet_path.exists(), "Target quadlet file must exist");
    {
        let _restorer = Restorer::new(&quadlet_path);
        let mut mutated = fs::read_to_string(&quadlet_path).expect("read quadlet");
        mutated.push_str("\n# planted drift line\n");
        fs::write(&quadlet_path, &mutated).expect("write mutated quadlet");

        let drift_output = Command::new(bin_path)
            .arg("pod-quadlets")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute mios-gen pod-quadlets --check");

        assert_eq!(
            drift_output.status.code(),
            Some(1),
            "Expected exit code 1 for drifted quadlet"
        );
        let drift_stderr = String::from_utf8_lossy(&drift_output.stderr);
        assert!(
            drift_stderr.contains("DRIFT") && drift_stderr.contains("mios-pgvector.container"),
            "stderr should report drift on mutated file: {}",
            drift_stderr
        );
    }

    // 5. Negative control: un-generated orphan file in SSOT dir
    let orphan_path = root.join("usr/share/containers/systemd/zz-orphan-test.container");
    fs::write(&orphan_path, "[Container]\nImage=alpine\n").expect("write orphan");
    {
        let orphan_output = Command::new(bin_path)
            .arg("pod-quadlets")
            .arg("--root")
            .arg(&root)
            .arg("--check")
            .output()
            .expect("Failed to execute mios-gen pod-quadlets --check");

        let _ = fs::remove_file(&orphan_path);

        assert_eq!(
            orphan_output.status.code(),
            Some(1),
            "Expected exit code 1 for orphan file"
        );
        let orphan_stderr = String::from_utf8_lossy(&orphan_output.stderr);
        assert!(
            orphan_stderr.contains("DRIFT: un-generated orphan Quadlet unit in SSOT dir: zz-orphan-test.container"),
            "stderr should report orphan file: {}",
            orphan_stderr
        );
    }
}
